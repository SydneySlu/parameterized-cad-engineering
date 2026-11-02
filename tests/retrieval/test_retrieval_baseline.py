"""Tests for the RET-002 deterministic single-family retrieval baseline.

Run with:
    PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from retrieval import (  # noqa: E402
    CONTINUOUS_FIELDS,
    POLICY_ID,
    SPLIT_STATUS,
    DistancePolicy,
    RetrievalConfig,
    RetrievalError,
    RetrievalIndex,
    catalog_ranges,
)
from retrieval.config import PARAMETER_ORDER  # noqa: E402
from schema.set_screw_shaft_collar import CATALOG_ROWS, FAMILY_ID  # noqa: E402


MANIFEST = ROOT / "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"
CONFIG = ROOT / "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json"
SOURCE_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"
POLICY = "CAD-006.geometry-comparison.v1"


def sample_id(bore_d: int) -> str:
    return f"{FAMILY_ID}/catalog-bore-{bore_d:03d}"


def catalog_row(bore_d: int) -> tuple[int, int, int, int, int]:
    return next(row for row in CATALOG_ROWS if row[0] == bore_d)


def flat_parameters(bore_d: int, *, second_screw: int | None = None) -> dict[str, int]:
    row = catalog_row(bore_d)
    return {
        "bore_d": row[0],
        "outer_d": row[1],
        "screw_d": row[2],
        "screw_len": row[3],
        "second_screw": (1 if bore_d > 70 else 0) if second_screw is None else second_screw,
        "width": row[4],
    }


def manifest_records() -> list[dict]:
    return [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").rstrip("\n").split("\n")
    ]


def write_manifest(records: list[dict], directory: str) -> Path:
    path = Path(directory) / "manifest.jsonl"
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


class RetrievalBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = RetrievalIndex.from_manifest(MANIFEST, {"retrieval_source"})

    def _error(self, action, code: str) -> RetrievalError:
        with self.assertRaises(RetrievalError) as context:
            action()
        self.assertEqual(context.exception.code, code)
        return context.exception

    # ---- index construction and role boundary ---------------------------------

    def test_index_uses_only_explicit_retrieval_source_rows(self) -> None:
        self.assertEqual(self.index.candidate_count, 3)
        self.assertEqual(self.index.candidate_roles, ("retrieval_source",))
        self.assertEqual(
            self.index.describe()["candidate_sample_ids"],
            [sample_id(6), sample_id(20), sample_id(50)],
        )

    def test_candidate_roles_must_be_explicit(self) -> None:
        self._error(lambda: RetrievalIndex.from_manifest(MANIFEST), "RETRIEVAL_CANDIDATE_ROLES_REQUIRED")
        self._error(
            lambda: RetrievalIndex.from_manifest(MANIFEST, set()),
            "RETRIEVAL_EMPTY_CANDIDATE_ROLES",
        )
        self._error(
            lambda: RetrievalIndex.from_manifest(MANIFEST, "retrieval_source"),
            "RETRIEVAL_INVALID_CANDIDATE_ROLES",
        )
        error = self._error(
            lambda: RetrievalIndex.from_manifest(MANIFEST, {"typo_role"}),
            "RETRIEVAL_UNKNOWN_ROLE",
        )
        self.assertEqual(error.details["available"], ["development", "heldout_evaluation", "retrieval_source"])

    def test_duplicate_sample_id_is_rejected(self) -> None:
        records = manifest_records()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.jsonl"
            path.write_text(
                MANIFEST.read_text(encoding="utf-8").splitlines()[0] + "\n"
                + MANIFEST.read_text(encoding="utf-8").splitlines()[0] + "\n",
                encoding="utf-8",
            )
            self._error(
                lambda: RetrievalIndex.from_manifest(path, {"retrieval_source"}),
                "RETRIEVAL_DUPLICATE_SAMPLE_ID",
            )
        self.assertEqual(len(records), 15)

    def test_duplicate_group_id_is_rejected(self) -> None:
        records = manifest_records()
        record = records[6]
        clone = copy.deepcopy(record)
        clone["sample_id"] = record["sample_id"] + "-copy"
        with tempfile.TemporaryDirectory() as directory:
            path = write_manifest([record, clone], directory)
            self._error(
                lambda: RetrievalIndex.from_manifest(path, {"retrieval_source"}),
                "RETRIEVAL_DUPLICATE_GROUP_ID",
            )

    def test_equal_distance_ties_break_on_sample_id(self) -> None:
        records = manifest_records()
        record = records[6]
        clone = copy.deepcopy(record)
        clone["sample_id"] = record["sample_id"] + "z"
        clone["split"]["group_id"] = "catalog-row-bore-020z"
        with tempfile.TemporaryDirectory() as directory:
            path = write_manifest([clone, record], directory)
            index = RetrievalIndex.from_manifest(path, {"retrieval_source"})
            payload = index.query(FAMILY_ID, flat_parameters(20), top_k=2).as_dict()
        self.assertEqual(
            [entry["sample_id"] for entry in payload["results"]],
            [record["sample_id"], clone["sample_id"]],
        )
        self.assertEqual([entry["distance"]["total"] for entry in payload["results"]], [0.0, 0.0])

    # ---- normal, boundary and out-of-catalog queries --------------------------

    def test_in_catalog_flat_query_hits_same_row_with_zero_distance(self) -> None:
        payload = self.index.query(FAMILY_ID, flat_parameters(20), top_k=3).as_dict()
        self.assertEqual(payload["query"]["query_status"], "catalog_validated")
        self.assertEqual(payload["query"]["input_form"], "flat_parameters")
        self.assertEqual(payload["results"][0]["sample_id"], sample_id(20))
        self.assertEqual(payload["results"][0]["distance"]["total"], 0.0)
        self.assertTrue(payload["results"][0]["same_catalog_row_as_query"])
        self.assertEqual(len(payload["results"]), 3)

    def test_cad003_envelope_is_normalized_by_the_existing_schema(self) -> None:
        result = self.index.query(
            FAMILY_ID,
            {
                "schema_version": "set_screw_shaft_collar.v0",
                "family_id": FAMILY_ID,
                "parameters": {"bore_d": 20},
            },
            top_k=3,
        )
        payload = result.as_dict()
        self.assertEqual(payload["query"]["input_form"], "cad003_envelope")
        self.assertEqual(payload["query"]["query_status"], "catalog_validated")
        self.assertEqual(payload["query"]["parameters"], flat_parameters(20))
        provenance = payload["query"]["schema_check"]["provenance"]
        self.assertEqual(provenance["bore_d"], "user_explicit")
        self.assertEqual(provenance["outer_d"], "catalog_derived")
        self.assertEqual(provenance["second_screw"], "rule_derived")
        self.assertEqual(payload["results"][0]["sample_id"], sample_id(20))

    def test_envelope_with_non_catalog_bore_is_rejected_by_schema(self) -> None:
        error = self._error(
            lambda: self.index.query(
                FAMILY_ID,
                {"parameters": {"bore_d": 18}},
                top_k=3,
            ),
            "RETRIEVAL_SCHEMA_REJECTED",
        )
        self.assertEqual(error.stage, "query")
        self.assertIn("CATALOG_CHOICE", [item["code"] for item in error.details["schema_errors"]])

    def test_between_rows_query_is_marked_unvalidated_and_ranked(self) -> None:
        query = {
            "bore_d": 18,
            "outer_d": 30,
            "screw_d": 6,
            "screw_len": 8,
            "second_screw": 0,
            "width": 14,
        }
        payload = self.index.query(FAMILY_ID, query, top_k=3).as_dict()
        self.assertEqual(payload["query"]["query_status"], "out_of_catalog_or_unvalidated")
        self.assertFalse(payload["query"]["schema_check"]["ok"])
        self.assertEqual(
            [entry["sample_id"] for entry in payload["results"]],
            [sample_id(20), sample_id(6), sample_id(50)],
        )
        self.assertTrue(all(not entry["same_catalog_row_as_query"] for entry in payload["results"]))
        self.assertAlmostEqual(payload["results"][0]["distance"]["total"], 0.009333333333333334, places=15)
        self.assertTrue(
            any("out_of_catalog_or_unvalidated" in note for note in payload["notes"])
        )

    def test_bore_80_second_screw_boundary_excludes_heldout_row(self) -> None:
        payload = self.index.query(FAMILY_ID, flat_parameters(80), top_k=3).as_dict()
        self.assertEqual(payload["query"]["query_status"], "catalog_validated")
        self.assertEqual(
            [entry["sample_id"] for entry in payload["results"]],
            [sample_id(50), sample_id(20), sample_id(6)],
        )
        self.assertNotIn(sample_id(80), [entry["sample_id"] for entry in payload["results"]])
        for entry in payload["results"]:
            self.assertEqual(entry["split"]["role"], "retrieval_source")
            self.assertFalse(entry["distance"]["second_screw"]["match"])
            self.assertEqual(entry["distance"]["discrete_term"], 0.5)
        self.assertAlmostEqual(payload["results"][0]["distance"]["total"], 0.7844444444444445, places=15)

    def test_out_of_range_query_is_marked_and_distance_can_exceed_one(self) -> None:
        query = {
            "bore_d": 200,
            "outer_d": 210,
            "screw_d": 22,
            "screw_len": 30,
            "second_screw": 1,
            "width": 40,
        }
        payload = self.index.query(FAMILY_ID, query, top_k=3).as_dict()
        self.assertEqual(payload["query"]["query_status"], "out_of_catalog_or_unvalidated")
        top = payload["results"][0]
        self.assertEqual(top["sample_id"], sample_id(50))
        self.assertGreater(top["distance"]["fields"]["bore_d"]["normalized_abs_diff"], 1.0)
        self.assertGreater(top["distance"]["total"], 1.0)

    # ---- failure paths ---------------------------------------------------------

    def test_missing_field_is_rejected(self) -> None:
        query = flat_parameters(20)
        del query["outer_d"]
        error = self._error(
            lambda: self.index.query(FAMILY_ID, query, top_k=3),
            "RETRIEVAL_MISSING_FIELD",
        )
        self.assertEqual(error.fields, ("outer_d",))
        self.assertEqual(error.stage, "query")
        serialized = json.loads(error.to_json())
        self.assertEqual(serialized["error"]["code"], "RETRIEVAL_MISSING_FIELD")

    def test_unknown_field_is_rejected(self) -> None:
        error = self._error(
            lambda: self.index.query(FAMILY_ID, {**flat_parameters(20), "flange_d": 10}, top_k=3),
            "RETRIEVAL_UNKNOWN_FIELD",
        )
        self.assertEqual(error.fields, ("flange_d",))

    def test_unknown_family_is_rejected(self) -> None:
        error = self._error(
            lambda: self.index.query("flange_bracket", flat_parameters(20), top_k=3),
            "RETRIEVAL_UNKNOWN_FAMILY",
        )
        self.assertEqual(error.fields, ("family_id",))

    def test_non_finite_parameters_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(value=repr(value)):
                self._error(
                    lambda: self.index.query(
                        FAMILY_ID, {**flat_parameters(20), "bore_d": value}, top_k=3
                    ),
                    "RETRIEVAL_INVALID_PARAMETER",
                )

    def test_second_screw_must_be_integer_zero_or_one(self) -> None:
        for value in (2, -1, True, 0.0, "0"):
            with self.subTest(value=repr(value)):
                self._error(
                    lambda: self.index.query(
                        FAMILY_ID, {**flat_parameters(20), "second_screw": value}, top_k=3
                    ),
                    "RETRIEVAL_INVALID_PARAMETER",
                )

    def test_top_k_validation(self) -> None:
        for value in (0, -1, True, 1.5):
            with self.subTest(value=repr(value)):
                self._error(
                    lambda: self.index.query(FAMILY_ID, flat_parameters(20), top_k=value),
                    "RETRIEVAL_INVALID_TOP_K",
                )
        error = self._error(
            lambda: self.index.query(FAMILY_ID, flat_parameters(20), top_k=4),
            "RETRIEVAL_TOP_K_OUT_OF_RANGE",
        )
        self.assertEqual(error.details["candidate_count"], 3)
        self.assertEqual(self.index.query(FAMILY_ID, flat_parameters(20)).as_dict()["top_k"], 3)

    # ---- result contract, determinism and data boundary -----------------------

    def test_result_contract_and_provisional_split_notes(self) -> None:
        payload = self.index.query(FAMILY_ID, flat_parameters(20), top_k=3).as_dict()
        self.assertEqual(payload["policy_id"], POLICY_ID)
        self.assertEqual(payload["split_status"], SPLIT_STATUS)
        self.assertEqual(payload["manifest"]["records"], 15)
        self.assertEqual(payload["manifest"]["sha256"], hashlib.sha256(MANIFEST.read_bytes()).hexdigest())
        self.assertEqual(payload["data_boundary"]["reads_step"], False)
        self.assertEqual(payload["data_boundary"]["reads_render"], False)
        self.assertEqual(payload["data_boundary"]["reads_ir_files"], False)
        self.assertTrue(any("provisional_small_n" in note for note in payload["notes"]))
        self.assertTrue(any("not CAD geometry equivalence" in note for note in payload["notes"]))
        for entry in payload["results"]:
            self.assertEqual(entry["source"]["source_commit"], SOURCE_COMMIT)
            self.assertEqual(entry["validation_summary"]["policy_id"], POLICY)
            self.assertEqual(entry["split"]["split_status"], SPLIT_STATUS)
            self.assertEqual(len(entry["ir"]["sha256"]), 64)
            self.assertTrue(entry["ir"]["path"].endswith(".json"))
            self.assertEqual(
                set(entry["parameters"]["normalized"]),
                set(PARAMETER_ORDER),
            )

    def test_distance_breakdown_is_consistent(self) -> None:
        payload = self.index.query(FAMILY_ID, flat_parameters(20), top_k=3).as_dict()
        for entry in payload["results"]:
            distance = entry["distance"]
            self.assertEqual(set(distance["fields"]), set(CONTINUOUS_FIELDS))
            self.assertAlmostEqual(
                math.fsum(field["contribution"] for field in distance["fields"].values()),
                distance["continuous_mean"],
                places=15,
            )
            self.assertAlmostEqual(
                distance["continuous_mean"] + distance["discrete_term"],
                distance["total"],
                places=15,
            )
            for field in distance["fields"].values():
                self.assertAlmostEqual(field["contribution"], field["normalized_abs_diff"] * 0.2, places=15)

    def test_same_query_produces_identical_json(self) -> None:
        first = self.index.query(FAMILY_ID, flat_parameters(20), top_k=3)
        second = self.index.query(FAMILY_ID, flat_parameters(20), top_k=3)
        self.assertEqual(first.to_canonical_json(), second.to_canonical_json())
        self.assertEqual(first.sha256(), second.sha256())
        self.assertEqual(len(first.sha256()), 64)

    # ---- configuration ---------------------------------------------------------

    def test_config_loader_matches_frozen_policy(self) -> None:
        config = RetrievalConfig.from_path(CONFIG)
        self.assertEqual(config.candidate_roles, ("retrieval_source",))
        self.assertEqual(config.default_top_k, 3)
        self.assertEqual(config.range_map(), catalog_ranges())
        self.assertEqual(config.manifest_sha256, hashlib.sha256(MANIFEST.read_bytes()).hexdigest())
        index = RetrievalIndex.from_config(CONFIG)
        self.assertEqual(index.candidate_count, 3)
        self.assertEqual(index.manifest_sha256, config.manifest_sha256)

    def test_config_rejects_tampered_manifest_hash(self) -> None:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        data["manifest"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self._error(lambda: RetrievalConfig.from_path(path), "RETRIEVAL_MANIFEST_HASH_MISMATCH")

    def test_config_rejects_weight_and_range_changes(self) -> None:
        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            weight_data = copy.deepcopy(base)
            weight_data["weights"]["discrete_second_screw"] = 1.0
            weight_path = Path(directory) / "weight.json"
            weight_path.write_text(json.dumps(weight_data), encoding="utf-8")
            self._error(lambda: RetrievalConfig.from_path(weight_path), "RETRIEVAL_CONFIG_INVALID")

            range_data = copy.deepcopy(base)
            range_data["normalization_ranges_mm"]["bore_d"]["max"] = 81
            range_path = Path(directory) / "range.json"
            range_path.write_text(json.dumps(range_data), encoding="utf-8")
            self._error(lambda: RetrievalConfig.from_path(range_path), "RETRIEVAL_CONFIG_INVALID")

    def test_distance_policy_rejects_non_frozen_weight(self) -> None:
        policy = DistancePolicy(ranges=catalog_ranges(), discrete_weight=1.0)
        self._error(lambda: policy.validate(), "RETRIEVAL_CONFIG_INVALID")

    # ---- frozen distance policy contract --------------------------------------

    def test_distance_policy_rejects_changed_bore_range(self) -> None:
        ranges = catalog_ranges()
        ranges["bore_d"] = (0.0, 1.0)
        error = self._error(
            lambda: DistancePolicy(ranges=ranges).validate(),
            "RETRIEVAL_CONFIG_INVALID",
        )
        self.assertEqual(error.stage, "config")
        self.assertEqual(error.fields, ("bore_d",))
        self.assertEqual(error.details["policy_id"], POLICY_ID)
        self.assertEqual(error.details["expected"], [5.0, 80.0])

    def test_distance_policy_rejects_changed_other_continuous_ranges(self) -> None:
        for field in ("outer_d", "screw_d", "screw_len", "width"):
            with self.subTest(field=field):
                ranges = catalog_ranges()
                low, high = ranges[field]
                ranges[field] = (low, high + 1.0)
                error = self._error(
                    lambda: DistancePolicy(ranges=ranges).validate(),
                    "RETRIEVAL_CONFIG_INVALID",
                )
                self.assertEqual(error.stage, "config")
                self.assertIn(field, error.fields)

    def test_distance_policy_rejects_non_finite_non_numeric_and_approximate_ranges(self) -> None:
        cases = [
            (float("nan"), 80.0),
            (float("inf"), 80.0),
            (True, 80.0),
            ("5", 80.0),
            (5.0, 80.0 + 1e-12),
            (10**400, 80.0),
        ]
        for low, high in cases:
            with self.subTest(low=repr(low), high=repr(high)):
                ranges = catalog_ranges()
                ranges["bore_d"] = (low, high)
                error = self._error(
                    lambda: DistancePolicy(ranges=ranges).validate(),
                    "RETRIEVAL_CONFIG_INVALID",
                )
                self.assertEqual(error.stage, "config")
                self.assertEqual(error.fields, ("bore_d",))

    def test_from_manifest_rejects_custom_policy_range(self) -> None:
        ranges = catalog_ranges()
        ranges["bore_d"] = (0.0, 1.0)
        policy = DistancePolicy(ranges=ranges)
        error = self._error(
            lambda: RetrievalIndex.from_manifest(
                MANIFEST, {"retrieval_source"}, policy=policy
            ),
            "RETRIEVAL_CONFIG_INVALID",
        )
        self.assertEqual(error.stage, "config")
        self.assertEqual(error.fields, ("bore_d",))
        self.assertEqual(error.details["expected"], [5.0, 80.0])
        self.assertEqual(error.details["observed"], [0.0, 1.0])

    def test_frozen_catalog_ranges_build_index_and_match_default_results(self) -> None:
        policy = DistancePolicy(ranges=catalog_ranges())
        policy.validate()
        index = RetrievalIndex.from_manifest(MANIFEST, {"retrieval_source"}, policy=policy)
        between = {
            "bore_d": 18,
            "outer_d": 30,
            "screw_d": 6,
            "screw_len": 8,
            "second_screw": 0,
            "width": 14,
        }
        baseline = self.index.query(FAMILY_ID, between, top_k=3)
        explicit = index.query(FAMILY_ID, between, top_k=3)
        self.assertEqual(explicit.to_canonical_json(), baseline.to_canonical_json())
        self.assertEqual(explicit.sha256(), baseline.sha256())

    def test_policy_does_not_alias_caller_range_mapping(self) -> None:
        ranges = catalog_ranges()
        ranges["bore_d"] = [5.0, 80.0]
        policy = DistancePolicy(ranges=ranges)
        index = RetrievalIndex.from_manifest(MANIFEST, {"retrieval_source"}, policy=policy)
        ranges["bore_d"][0] = 0.0
        ranges["bore_d"][1] = 1.0
        ranges["outer_d"] = (0.0, 1.0)
        policy.validate()
        between = {
            "bore_d": 18,
            "outer_d": 30,
            "screw_d": 6,
            "screw_len": 8,
            "second_screw": 0,
            "width": 14,
        }
        payload = index.query(FAMILY_ID, between, top_k=3).as_dict()
        self.assertEqual(
            payload["results"][0]["distance"]["fields"]["bore_d"]["catalog_range_mm"],
            [5.0, 80.0],
        )
        self.assertAlmostEqual(
            payload["results"][0]["distance"]["total"],
            0.009333333333333334,
            places=15,
        )


if __name__ == "__main__":
    unittest.main()
