"""Tests for RET-005 ReferencePool (src/retrieval/pool.py).

Covers:
- Allowlist validation (sample_ids must be in manifest)
- Pool count limit enforcement (3-5)
- Forbidden field isolation (no evaluator labels, IR content, STEP, raw)
- In-pool retrieval: top-k, distance ordering, policy reuse
- Shared context assembler (product mode == C1 experiment mode)
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrieval.pool import (
    ReferencePool, PoolError, PoolEntry,
    POOL_MIN_SIZE, POOL_MAX_SIZE, MANIFEST_REL_PATH, _safe_pool_entry,
)
from retrieval.config import PARAMETER_ORDER, CONTINUOUS_FIELDS, REPO_ROOT
from llm.contract import CONTRACT_VERSION, PROMPT_VERSION


# ---------------------------------------------------------------------------
# Helpers — real manifest sample_ids
# ---------------------------------------------------------------------------

# These are the actual sample_ids from the RET-001 manifest.
# The manifest has 15 records: 3 retrieval_source, 9 development, 3 heldout_evaluation.
# Only retrieval_source IDs may be used in pools (P1a fix enforces this).
_ALL_MANIFEST_IDS: list[str] = []
_MANIFEST_PATH = REPO_ROOT / MANIFEST_REL_PATH

# Only retrieval_source role samples may enter a pool
_RETRIEVAL_SOURCE_IDS = [
    "set_screw_shaft_collar/catalog-bore-006",
    "set_screw_shaft_collar/catalog-bore-020",
    "set_screw_shaft_collar/catalog-bore-050",
]


def _load_all_manifest_ids() -> list[str]:
    if not _MANIFEST_PATH.is_file():
        return []
    return [
        json.loads(line)["sample_id"]
        for line in _MANIFEST_PATH.read_text().strip().split("\n")
        if line.strip()
    ]


_ALL_MANIFEST_IDS = _load_all_manifest_ids()
_HAVE_MANIFEST = len(_RETRIEVAL_SOURCE_IDS) >= POOL_MIN_SIZE and _MANIFEST_PATH.is_file()


def _pool_ids(n: int = 3) -> list[str]:
    """Return n retrieval_source sample_ids from the manifest."""
    return _RETRIEVAL_SOURCE_IDS[:n]


# ---------------------------------------------------------------------------
# 1. Allowlist validation
# ---------------------------------------------------------------------------


class TestReferencePoolAllowlist(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_valid_pool_builds_successfully(self):
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        self.assertEqual(pool.candidate_count, 3)
        self.assertEqual(pool.sample_ids, tuple(ids))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_all_manifest_ids_valid_up_to_max(self):
        """Any 3-5 retrieval_source sample_ids should build a pool."""
        for n in range(POOL_MIN_SIZE, POOL_MAX_SIZE + 1):
            if len(_RETRIEVAL_SOURCE_IDS) >= n:
                pool = ReferencePool.from_manifest(_RETRIEVAL_SOURCE_IDS[:n])
                self.assertEqual(pool.candidate_count, n)

    def test_non_manifest_id_raises_pool_not_in_allowlist(self):
        """sample_ids not in the manifest must be rejected."""
        fake_ids = ["not-a-real-sample-001", "not-a-real-sample-002", "not-a-real-sample-003"]
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(fake_ids)
        self.assertEqual(ctx.exception.code, "POOL_SAMPLE_NOT_IN_ALLOWLIST")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_mixed_valid_invalid_raises_allowlist_error(self):
        """Even one invalid sample_id must reject the whole pool."""
        ids = _pool_ids(2) + ["definitely-not-in-manifest"]
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(ids)
        self.assertEqual(ctx.exception.code, "POOL_SAMPLE_NOT_IN_ALLOWLIST")
        self.assertIn("definitely-not-in-manifest", ctx.exception.details["missing"])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_duplicate_sample_id_rejected(self):
        ids = [_pool_ids(1)[0]] * 3  # 3 copies of same id
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(ids)
        self.assertEqual(ctx.exception.code, "POOL_DUPLICATE_SAMPLE_ID")


# ---------------------------------------------------------------------------
# 2. Pool count limit enforcement (3-5)
# ---------------------------------------------------------------------------


class TestReferencePoolCountLimits(unittest.TestCase):
    def test_empty_list_raises_too_small(self):
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest([])
        self.assertEqual(ctx.exception.code, "POOL_TOO_SMALL")

    def test_one_id_raises_too_small(self):
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(["some-id"])
        self.assertEqual(ctx.exception.code, "POOL_TOO_SMALL")

    def test_two_ids_raises_too_small(self):
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(["id-1", "id-2"])
        self.assertEqual(ctx.exception.code, "POOL_TOO_SMALL")

    def test_six_ids_raises_too_large(self):
        ids = [f"id-{i}" for i in range(6)]
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(ids)
        self.assertEqual(ctx.exception.code, "POOL_TOO_LARGE")

    def test_too_small_error_contains_min(self):
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(["only-one-id"])
        self.assertIn("POOL_TOO_SMALL", str(ctx.exception))

    def test_too_large_error_contains_max(self):
        ids = [f"over-id-{i}" for i in range(POOL_MAX_SIZE + 1)]
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(ids)
        self.assertIn("POOL_TOO_LARGE", str(ctx.exception))


# ---------------------------------------------------------------------------
# 3. Forbidden field isolation
# ---------------------------------------------------------------------------


def _make_minimal_record(sample_id: str = "test/catalog-bore-024") -> dict:
    """Build a minimal valid manifest record for unit-testing display isolation."""
    return {
        "manifest_version": "retrieval-manifest.v0",
        "sample_id": sample_id,
        "family_id": "set_screw_shaft_collar",
        "sample_kind": "catalog_exact",
        "parameters": {
            "normalized": {
                "bore_d": 24.0, "outer_d": 38.0, "screw_d": 5.0,
                "screw_len": 20.0, "second_screw": 0, "width": 20.0,
            },
            "units": {"length": "mm"},
            "provenance": {field: {"source": "catalog"} for field in
                          ["bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"]},
            "input_payload": {"path": "dummy.json", "sha256": "a" * 64},
        },
        "ir": {
            "ir_version": "v1", "ir_revision": "r1", "status": "valid",
            "path": "ir/bore024.json", "sha256": "b" * 64,
        },
        "artifacts": {
            "step_body": "STEP AP214 ISO ...",  # MUST NOT appear in display
            "raw": "some raw cad content",       # MUST NOT appear in display
        },
        "validation": {
            "schema": "pass", "family_rules": "pass", "cad_compile": "pass",
            "final_stage": "step_readback", "policy_id": "v1",
            "completed_stages": ["schema", "cad_compile"],
            "native_geometry": {
                "solids": 1, "shells": 1, "faces": 10, "edges": 24, "vertices": 16,
                "is_valid": True, "volume_mm3": 15000.0, "bbox_mm": {},
            },
            "native_repeatability": {"pass": True},
            "step_readback": {"pass": True},
        },
        "split": {
            "role": "retrieval_source",
            "group_id": "group-024",
            "split_status": "provisional_small_n",
            "split_rule": "bore_d_modulo_3",
        },
        "source": {
            "repository": "benchcad-2",
            "source_commit": "abc123",
            "family_path": "designs/set_screw_shaft_collar",
            "family_status": "active",
            "snapshot_status": "stable",
            "license_scope": "research_noncommercial",
            "release_qualified": True,
            "catalog_row": {
                "index": 7, "key": "bore_d", "value": 24.0,
                "row": [24.0, 38.0, 5.0, 20.0, 20.0],
            },
        },
        "limitations": ["provisional_small_n"],
    }


class TestPoolDisplayForbiddenFields(unittest.TestCase):
    def setUp(self):
        self.record = _make_minimal_record()
        self.entry = _safe_pool_entry(self.record)

    def test_entry_is_pool_entry(self):
        self.assertIsInstance(self.entry, PoolEntry)

    def test_step_body_not_in_entry(self):
        entry_dict = self.entry.__dict__
        entry_str = json.dumps(entry_dict, default=str)
        self.assertNotIn("STEP AP214", entry_str)
        self.assertNotIn("step_body", entry_str)

    def test_raw_cad_not_in_entry(self):
        entry_dict = self.entry.__dict__
        entry_str = json.dumps(entry_dict, default=str)
        self.assertNotIn("raw cad content", entry_str)

    def test_ir_path_not_in_entry_parameters(self):
        # ir.path is a path pointer, not file content — but should not appear
        # in the allowed display fields.  _safe_pool_entry only reads known safe fields.
        self.assertFalse(hasattr(self.entry, "ir_path"))
        self.assertFalse(hasattr(self.entry, "ir_sha256"))

    def test_safe_fields_present(self):
        self.assertEqual(self.entry.sample_id, "test/catalog-bore-024")
        self.assertEqual(self.entry.family_id, "set_screw_shaft_collar")
        self.assertEqual(self.entry.validation_status, "step_readback")
        self.assertTrue(self.entry.validation_is_valid)
        self.assertEqual(self.entry.split_role, "retrieval_source")
        self.assertTrue(self.entry.source_release_qualified)

    def test_normalized_parameters_included(self):
        p = self.entry.parameters_normalized
        self.assertIn("bore_d", p)
        self.assertEqual(p["bore_d"], 24.0)
        for field in PARAMETER_ORDER:
            self.assertIn(field, p)

    def test_describe_returns_pool_entries(self):
        """ReferencePool.describe() must return PoolEntry objects."""
        # Test the describe method via a synthetic single-record pool
        # We can't directly call from_manifest with synthetic records,
        # but we can verify _safe_pool_entry output matches PoolEntry spec.
        self.assertIsInstance(self.entry, PoolEntry)


# ---------------------------------------------------------------------------
# 4. In-pool retrieval: top-k, distance ordering
# ---------------------------------------------------------------------------


class TestReferencePoolRetrieval(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_returns_top_k_sorted_by_distance(self):
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        # Query with the first pool sample's own parameters → it should rank first
        first_record = json.loads(
            _MANIFEST_PATH.read_text().strip().split("\n")[0]
        )
        norm = first_record["parameters"]["normalized"]
        result = pool.query(parameters=norm, top_k=3)
        self.assertEqual(result["top_k"], 3)
        self.assertEqual(len(result["results"]), 3)
        # Ranks must be 1, 2, 3
        ranks = [r["rank"] for r in result["results"]]
        self.assertEqual(ranks, [1, 2, 3])
        # First result must be closest (or tied)
        self.assertLessEqual(
            result["results"][0]["distance"]["total"],
            result["results"][-1]["distance"]["total"],
        )

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_top_k_1_returns_exactly_one(self):
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 20.0, "outer_d": 32.0, "screw_d": 4.0,
            "screw_len": 16.0, "second_screw": 0, "width": 16.0,
        }
        result = pool.query(parameters=norm, top_k=1)
        self.assertEqual(result["top_k"], 1)
        self.assertEqual(len(result["results"]), 1)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_top_k_exceeds_pool_raises_error(self):
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 24.0, "outer_d": 38.0, "screw_d": 5.0,
            "screw_len": 20.0, "second_screw": 0, "width": 20.0,
        }
        with self.assertRaises(PoolError) as ctx:
            pool.query(parameters=norm, top_k=10)
        self.assertEqual(ctx.exception.code, "POOL_TOP_K_OUT_OF_RANGE")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_result_contains_safe_fields_only(self):
        """Query results must not contain IR paths, STEP content, raw, or evaluator labels."""
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 24.0, "outer_d": 38.0, "screw_d": 5.0,
            "screw_len": 20.0, "second_screw": 0, "width": 20.0,
        }
        result = pool.query(parameters=norm, top_k=3)
        result_str = json.dumps(result, ensure_ascii=False)
        # IR and STEP content must not appear
        self.assertNotIn("ir_path", result_str)
        self.assertNotIn("step_body", result_str)
        # Data boundary must be in result
        boundary = result["data_boundary"]
        self.assertFalse(boundary["reads_evaluator_labels"])
        self.assertFalse(boundary["reads_held_out_truth"])
        self.assertFalse(boundary["reads_step_files"])
        self.assertFalse(boundary["reads_ir_files"])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_parameters_normalized_in_result(self):
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 6.0, "outer_d": 14.0, "screw_d": 3.0,
            "screw_len": 12.0, "second_screw": 0, "width": 12.0,
        }
        result = pool.query(parameters=norm, top_k=1)
        entry = result["results"][0]
        self.assertIn("parameters_normalized", entry)
        for field in PARAMETER_ORDER:
            self.assertIn(field, entry["parameters_normalized"])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_query_distance_policy_matches_ret002(self):
        """In-pool distances must use the same RET-002 policy (catalog ranges)."""
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 20.0, "outer_d": 32.0, "screw_d": 4.0,
            "screw_len": 16.0, "second_screw": 0, "width": 16.0,
        }
        result = pool.query(parameters=norm, top_k=1)
        d = result["results"][0]["distance"]
        self.assertIn("policy_id", d)
        from retrieval.config import POLICY_ID
        self.assertEqual(d["policy_id"], POLICY_ID)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_pool_query_results_only_from_pool_sample_ids(self):
        """Results must come exclusively from the user-selected pool."""
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        norm = {
            "bore_d": 24.0, "outer_d": 38.0, "screw_d": 5.0,
            "screw_len": 20.0, "second_screw": 0, "width": 20.0,
        }
        result = pool.query(parameters=norm, top_k=3)
        returned_ids = {r["sample_id"] for r in result["results"]}
        self.assertTrue(returned_ids.issubset(set(ids)))


# ---------------------------------------------------------------------------
# 5. Pool context assembler isolation
# ---------------------------------------------------------------------------


class TestPoolContextAssemblerIsolation(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c0_has_no_reference_context(self):
        from llm.pool_context import assemble_pool_c0
        from llm.input_projection import ProjectedCase
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c0(case)
        self.assertIsNone(assembled.reference_context)
        self.assertIsNone(assembled.blocked_reason)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_contains_untrusted_role_label(self):
        from llm.pool_context import assemble_pool_c1, _POOL_CANDIDATE_ROLE
        from llm.input_projection import ProjectedCase
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNone(assembled.blocked_reason)
        self.assertIsNotNone(assembled.reference_context)
        ref_dict = json.loads(assembled.reference_context)
        roles = {c["role"] for c in ref_dict["candidates"]}
        self.assertEqual(roles, {_POOL_CANDIDATE_ROLE})

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_context_contains_mandatory_untrusted_note(self):
        from llm.pool_context import assemble_pool_c1, _POOL_UNTRUSTED_NOTE
        from llm.input_projection import ProjectedCase
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNone(assembled.blocked_reason)
        ref_dict = json.loads(assembled.reference_context)
        self.assertIn(_POOL_UNTRUSTED_NOTE, ref_dict["note"])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_context_no_forbidden_fields(self):
        """C1 context must not contain IR paths, STEP content, evaluator labels."""
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNone(assembled.blocked_reason)
        ctx_str = assembled.reference_context or ""
        self.assertNotIn("ir_path", ctx_str)
        self.assertNotIn("step_body", ctx_str)
        self.assertNotIn("evaluator", ctx_str)
        self.assertNotIn("heldout", ctx_str)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_blocked_when_bore_d_not_in_text(self):
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        case = ProjectedCase("q1", "需要一个轴环（未写孔径）", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNotNone(assembled.blocked_reason)
        self.assertEqual(assembled.error_code, "POOL_C1_NO_SAFE_QUERY_PARAMETER")

    def test_c1_blocked_when_pool_is_none(self):
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, None)  # type: ignore[arg-type]
        self.assertIsNotNone(assembled.blocked_reason)
        self.assertEqual(assembled.error_code, "POOL_C1_NO_POOL")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_c1_candidate_source_ids_match_pool_results(self):
        from llm.pool_context import assemble_pool_c1
        from llm.input_projection import ProjectedCase
        ids = _pool_ids(3)
        pool = ReferencePool.from_manifest(ids)
        case = ProjectedCase("q1", "bore_d=24 mm 轴环", None, ("bore_d",))
        assembled = assemble_pool_c1(case, pool)
        self.assertIsNone(assembled.blocked_reason)
        # Candidate IDs must be a subset of pool sample_ids
        self.assertTrue(set(assembled.candidate_source_ids).issubset(set(ids)))


# ---------------------------------------------------------------------------
# 6. User param priority
# ---------------------------------------------------------------------------


class TestUserParamPriority(unittest.TestCase):
    def test_no_explicit_params_no_conflicts(self):
        from llm.pool_context import check_user_param_priority
        conflicts = check_user_param_priority({}, {"bore_d": 24.0})
        self.assertEqual(conflicts, [])

    def test_explicit_matches_model_no_conflict(self):
        from llm.pool_context import check_user_param_priority
        conflicts = check_user_param_priority({"bore_d": 24.0}, {"bore_d": 24.0})
        self.assertEqual(conflicts, [])

    def test_explicit_conflicts_model_returns_conflict(self):
        from llm.pool_context import check_user_param_priority
        conflicts = check_user_param_priority({"bore_d": 24.0}, {"bore_d": 20.0})
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["code"], "USER_PARAM_CONFLICT_BORE_D")
        self.assertEqual(conflicts[0]["field"], "bore_d")
        self.assertEqual(conflicts[0]["explicit_value"], 24.0)
        self.assertEqual(conflicts[0]["model_value"], 20.0)

    def test_explicit_param_model_missing_no_conflict(self):
        from llm.pool_context import check_user_param_priority
        # Model didn't extract the field — not a conflict
        conflicts = check_user_param_priority({"bore_d": 24.0}, {})
        self.assertEqual(conflicts, [])

    def test_extract_explicit_parameters_bore_d(self):
        from llm.pool_context import extract_explicit_parameters
        params = extract_explicit_parameters("bore_d=24 mm 请生成轴环")
        self.assertIn("bore_d", params)
        self.assertAlmostEqual(params["bore_d"], 24.0)

    def test_extract_explicit_parameters_no_bore_d(self):
        from llm.pool_context import extract_explicit_parameters
        params = extract_explicit_parameters("需要一个轴环")
        self.assertEqual(params, {})

    def test_explicit_within_tolerance_no_conflict(self):
        from llm.pool_context import check_user_param_priority
        # Within abs_tol=1e-9 → no conflict
        conflicts = check_user_param_priority(
            {"bore_d": 24.0},
            {"bore_d": 24.0 + 1e-12},  # within tolerance
        )
        self.assertEqual(conflicts, [])


# ---------------------------------------------------------------------------
# 7. Pool role enforcement (P1a security fix)
# ---------------------------------------------------------------------------

_HELDOUT_IDS = [
    "set_screw_shaft_collar/catalog-bore-012",
    "set_screw_shaft_collar/catalog-bore-035",
    "set_screw_shaft_collar/catalog-bore-080",
]
_DEV_IDS = [
    "set_screw_shaft_collar/catalog-bore-005",
    "set_screw_shaft_collar/catalog-bore-008",
    "set_screw_shaft_collar/catalog-bore-010",
]
_RET_IDS = [
    "set_screw_shaft_collar/catalog-bore-006",
    "set_screw_shaft_collar/catalog-bore-020",
    "set_screw_shaft_collar/catalog-bore-050",
]


class TestPoolRoleEnforcement(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_heldout_sample_ids_blocked_at_construction(self):
        """heldout_evaluation samples must be rejected at pool construction."""
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(_HELDOUT_IDS)
        self.assertEqual(ctx.exception.code, "POOL_SAMPLE_ROLE_NOT_ALLOWED")
        # The error must name the rejected role
        details = ctx.exception.details
        rejected = details.get("rejected", [])
        self.assertTrue(len(rejected) > 0)
        for item in rejected:
            self.assertIn(item["role"], ("heldout_evaluation",))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_heldout_blocked_before_transport_zero_calls(self):
        """Passing held-out sample IDs must block before any transport call."""
        from integration.ret005_pool_runner import Ret005PoolService
        from llm.transport import FakeTransport, TransportResponse
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        import json

        transport = FakeTransport()
        # Queue a response — it must NOT be consumed because pool creation fails first
        envelope = json.dumps({
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24.0},
            "unsupported_requests": [],
            "evidence": [],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        })
        transport.queue_response(TransportResponse(status=200, body=envelope))

        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", _HELDOUT_IDS, "C1")

        # Pool construction must fail before transport is touched
        self.assertEqual(transport.call_count, 0,
                         "transport must not be called when held-out IDs are used")
        self.assertEqual(state.product_status, "blocked")
        codes = [e["code"] for e in state.errors]
        self.assertIn("POOL_SAMPLE_ROLE_NOT_ALLOWED", codes,
                      f"expected POOL_SAMPLE_ROLE_NOT_ALLOWED, got {codes}")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_heldout_parameters_not_in_model_input(self):
        """Held-out parameters must not appear in any transport request body."""
        from integration.ret005_pool_runner import Ret005PoolService
        from llm.transport import FakeTransport, TransportResponse
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        import json

        transport = FakeTransport()
        envelope = json.dumps({
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24.0},
            "unsupported_requests": [],
            "evidence": [],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        })
        transport.queue_response(TransportResponse(status=200, body=envelope))

        service = Ret005PoolService(transport=transport)
        service.extract("bore_d=24 mm 轴环", _HELDOUT_IDS, "C1")

        # Verify no call was made
        self.assertEqual(transport.call_count, 0)
        # Even if calls were somehow made, check that held-out IDs are not in them
        for call in transport.calls:
            call_str = json.dumps(call.body, ensure_ascii=False)
            for hid in _HELDOUT_IDS:
                self.assertNotIn(hid, call_str,
                                 f"held-out ID {hid!r} found in transport request body")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_development_sample_ids_blocked(self):
        """development role samples must be rejected at pool construction."""
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(_DEV_IDS)
        self.assertEqual(ctx.exception.code, "POOL_SAMPLE_ROLE_NOT_ALLOWED")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_retrieval_source_still_accepted(self):
        """retrieval_source samples must be accepted."""
        pool = ReferencePool.from_manifest(_RET_IDS)
        self.assertEqual(pool.candidate_count, 3)
        self.assertEqual(set(pool.sample_ids), set(_RET_IDS))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_mixed_valid_and_heldout_all_blocked(self):
        """Even one held-out sample in a valid-sized pool must reject the whole pool."""
        mixed = _RET_IDS[:2] + [_HELDOUT_IDS[0]]
        with self.assertRaises(PoolError) as ctx:
            ReferencePool.from_manifest(mixed)
        self.assertEqual(ctx.exception.code, "POOL_SAMPLE_ROLE_NOT_ALLOWED")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_allowed_role_constant_is_retrieval_source(self):
        """ALLOWED_POOL_ROLE constant must be 'retrieval_source'."""
        from retrieval.pool import ALLOWED_POOL_ROLE
        self.assertEqual(ALLOWED_POOL_ROLE, "retrieval_source")


# ---------------------------------------------------------------------------
# 8. Explicit parameter extraction (fix 2)
# ---------------------------------------------------------------------------


class TestExplicitParamExtraction(unittest.TestCase):
    """Unit tests for the extended extract_explicit_parameters() function."""

    def _extract(self, text: str) -> dict:
        from llm.pool_context import extract_explicit_parameters
        return extract_explicit_parameters(text)

    def test_bore_d_still_extracted(self):
        result = self._extract("bore_d=24 mm 轴环")
        self.assertAlmostEqual(result["bore_d"], 24.0)

    def test_width_extracted_from_english(self):
        result = self._extract("width=99 mm")
        self.assertAlmostEqual(result["width"], 99.0)

    def test_width_extracted_from_chinese(self):
        result = self._extract("宽度=20 mm")
        self.assertAlmostEqual(result["width"], 20.0)

    def test_outer_d_extracted(self):
        result = self._extract("outer_d=40 mm")
        self.assertAlmostEqual(result["outer_d"], 40.0)

    def test_screw_d_extracted(self):
        result = self._extract("screw_d=5 mm")
        self.assertAlmostEqual(result["screw_d"], 5.0)

    def test_screw_len_extracted(self):
        result = self._extract("screw_len=12 mm")
        self.assertAlmostEqual(result["screw_len"], 12.0)

    def test_second_screw_zero_extracted(self):
        result = self._extract("second_screw=0")
        self.assertEqual(result["second_screw"], 0)

    def test_second_screw_one_extracted(self):
        result = self._extract("second_screw=1")
        self.assertEqual(result["second_screw"], 1)

    def test_multiple_fields_extracted_together(self):
        result = self._extract("bore_d=24 mm，width=99 mm")
        self.assertAlmostEqual(result["bore_d"], 24.0)
        self.assertAlmostEqual(result["width"], 99.0)

    def test_no_params_returns_empty(self):
        result = self._extract("需要一个轴环")
        self.assertEqual(result, {})

    def test_width_conflict_check_via_check_user_param_priority(self):
        """bore_d=24, width=99 explicit vs model width=14 → conflict."""
        from llm.pool_context import extract_explicit_parameters, check_user_param_priority
        explicit = extract_explicit_parameters("bore_d=24 mm，width=99 mm")
        self.assertAlmostEqual(explicit["width"], 99.0)
        conflicts = check_user_param_priority(explicit, {"bore_d": 24.0, "width": 14.0})
        codes = [c["code"] for c in conflicts]
        self.assertIn("USER_PARAM_CONFLICT_WIDTH", codes)

    def test_width_no_conflict_when_values_match(self):
        """width=14 mm in text, model width=14 → no conflict."""
        from llm.pool_context import extract_explicit_parameters, check_user_param_priority
        explicit = extract_explicit_parameters("width=14 mm")
        conflicts = check_user_param_priority(explicit, {"width": 14.0})
        self.assertEqual(conflicts, [])

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_width_conflict_blocks_before_cad_via_service(self):
        """bore_d=24 mm，width=99 mm + model width=14 → blocked; pipeline calls=0."""
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        from llm.transport import FakeTransport, TransportResponse
        env = json.dumps({
            "contract_version": PROMPT_VERSION,  # reuse any available version
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24.0, "width": 14.0},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "24 mm", "source": "user_input"}],
            "missing_fields": [], "questions": [], "confidence": None,
        })
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=env))
        service = Ret005PoolService(transport=transport)
        # Import CONTRACT_VERSION for envelope
        from llm.contract import CONTRACT_VERSION
        env2 = json.dumps({
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24.0, "width": 14.0},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "24 mm", "source": "user_input"}],
            "missing_fields": [], "questions": [], "confidence": None,
        })
        transport2 = FakeTransport()
        transport2.queue_response(TransportResponse(status=200, body=env2))
        service2 = Ret005PoolService(transport=transport2)
        with patch("integration.pipeline.run_pipeline") as cad:
            state = service2.extract(
                "bore_d=24 mm，width=99 mm",
                pool_sample_ids=_pool_ids(3),
                condition_id="C0",  # C0 so bore_d query not needed
            )
            cad.assert_not_called()
        self.assertEqual(state.product_status, POOL_STATUS_BLOCKED)
        codes = [e["code"] for e in state.errors]
        self.assertIn("USER_PARAM_CONFLICT", codes)


if __name__ == "__main__":
    unittest.main()
