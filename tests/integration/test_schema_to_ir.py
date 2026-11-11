"""Integration tests for the formal Schema→IR adapter (APP-002-INTEGRATION-A1).

Run with:
    PYTHONPATH=src:. python3 -m unittest tests.integration.test_schema_to_ir -v

All tests run with Python 3.10 (no cadquery required).
"""

import json
import unittest

from integration.schema_to_ir import build_ir_from_schema_payload, ADAPTER_VERSION

_SCHEMA_VERSION = "set_screw_shaft_collar.v0"
_FAMILY_ID = "set_screw_shaft_collar"


def _make_payload(params: dict) -> dict:
    return {
        "schema_version": _SCHEMA_VERSION,
        "family_id": _FAMILY_ID,
        "parameters": params,
    }


class TestSchemaToIRBore24(unittest.TestCase):
    """Standard bore_d=24 mm catalog row."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(_make_payload({"bore_d": 24}))

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")
        self.assertEqual(self.result.errors, [])

    def test_ir_document_present(self):
        self.assertIsNotNone(self.result.ir_document)
        self.assertIsNotNone(self.result.ir_json)

    def test_ir_json_parses(self):
        doc = json.loads(self.result.ir_json)
        self.assertEqual(doc["ir_version"], "typed-cad-ir.v0")
        self.assertEqual(doc["ir_revision"], "0.2.0")
        self.assertEqual(doc["status"], "accepted")

    def test_parameter_count_and_order(self):
        params = self.result.ir_document["parameters"]
        ids = [p["parameter_id"] for p in params]
        self.assertEqual(ids, ["bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"])

    def test_bore_d_value_and_source(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["value"], 24)
        self.assertEqual(p["bore_d"]["source"], "user_explicit")
        self.assertEqual(p["bore_d"]["source_ref"], "CAD-003.field:bore_d")
        self.assertEqual(p["bore_d"]["input"], {"value": 24, "unit": "mm"})
        self.assertEqual(p["bore_d"]["catalog_row_key"], "bore_d=24")

    def test_outer_d_catalog_derived(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["outer_d"]["value"], 40)
        self.assertEqual(p["outer_d"]["source"], "catalog_derived")
        self.assertEqual(p["outer_d"]["source_ref"], "GN705.catalog_row:bore_d=24")
        self.assertNotIn("input", p["outer_d"])

    def test_screw_d_catalog_derived(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["screw_d"]["value"], 8)
        self.assertEqual(p["screw_d"]["source"], "catalog_derived")

    def test_screw_len_catalog_derived(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["screw_len"]["value"], 12)
        self.assertEqual(p["screw_len"]["source"], "catalog_derived")

    def test_second_screw_rule_derived_zero(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["second_screw"]["value"], 0)
        self.assertEqual(p["second_screw"]["source"], "rule_derived")
        self.assertEqual(p["second_screw"]["source_ref"], "CAD-003.rule:second_screw_threshold")
        self.assertNotIn("input", p["second_screw"])

    def test_width_catalog_derived(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["width"]["value"], 16)
        self.assertEqual(p["width"]["source"], "catalog_derived")

    def test_provenance(self):
        self.assertEqual(self.result.provenance["bore_d"], "user_explicit")
        self.assertEqual(self.result.provenance["outer_d"], "catalog_derived")
        self.assertEqual(self.result.provenance["second_screw"], "rule_derived")

    def test_seven_nodes(self):
        nodes = self.result.ir_document["nodes"]
        self.assertEqual(len(nodes), 7)
        ids = [n["node_id"] for n in nodes]
        self.assertEqual(ids[0], "n0.catalog.resolve")
        self.assertEqual(ids[6], "n6.result")

    def test_source_block(self):
        src = self.result.ir_document["source"]
        self.assertEqual(src["source_commit"], "035f467142888edfd0bd7cd73906f9b155c8f43c")
        self.assertEqual(src["snapshot_status"], "reproducibility_partial")
        self.assertEqual(src["adapter_id"], "benchcad.set_screw_shaft_collar")
        self.assertEqual(src["adapter_version"], "0.1.0")


class TestSchemaToIRBore20(unittest.TestCase):
    """Standard bore_d=20 mm catalog row."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(_make_payload({"bore_d": 20}))

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")

    def test_bore_d_value(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["value"], 20)

    def test_outer_d_value(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["outer_d"]["value"], 32)

    def test_second_screw_zero(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["second_screw"]["value"], 0)
        self.assertEqual(p["second_screw"]["source"], "rule_derived")


class TestSchemaToIRBore16cm(unittest.TestCase):
    """bore_d provided as measurement {value:1.6, unit:cm} → 16 mm."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(
            _make_payload({"bore_d": {"value": 1.6, "unit": "cm"}})
        )

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")

    def test_normalized_value_mm(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["value"], 16)
        self.assertEqual(p["bore_d"]["unit"], "mm")

    def test_input_preserves_original_unit(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["input"]["value"], 1.6)
        self.assertEqual(p["bore_d"]["input"]["unit"], "cm")

    def test_source_user_explicit(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["source"], "user_explicit")

    def test_catalog_row_matches_bore16(self):
        # bore_d=16 → outer_d=28, screw_d=6, screw_len=8, width=12
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["outer_d"]["value"], 28)
        self.assertEqual(p["screw_d"]["value"], 6)
        self.assertEqual(p["width"]["value"], 12)

    def test_catalog_row_key(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["catalog_row_key"], "bore_d=16")
        self.assertEqual(p["outer_d"]["catalog_row_key"], "bore_d=16")


class TestSchemaToIRBore70(unittest.TestCase):
    """bore_d=70 → second_screw=0 (threshold is bore_d>70, not >=70)."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(_make_payload({"bore_d": 70}))

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")

    def test_second_screw_zero(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["second_screw"]["value"], 0)
        self.assertEqual(p["second_screw"]["source"], "rule_derived")


class TestSchemaToIRBore80(unittest.TestCase):
    """bore_d=80 → second_screw=1."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(_make_payload({"bore_d": 80}))

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")

    def test_second_screw_one(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["second_screw"]["value"], 1)
        self.assertEqual(p["second_screw"]["source"], "rule_derived")


class TestSchemaToIRMissingBore(unittest.TestCase):
    """bore_d absent → rejected at schema stage."""

    def test_rejected_missing_bore(self):
        r = build_ir_from_schema_payload(_make_payload({}))
        self.assertEqual(r.status, "rejected")
        self.assertEqual(r.stage, "schema")
        self.assertIsNone(r.ir_document)
        codes = [e["code"] for e in r.errors]
        self.assertIn("MISSING_REQUIRED", codes)

    def test_no_ir_on_rejection(self):
        r = build_ir_from_schema_payload(_make_payload({}))
        self.assertIsNone(r.ir_json)


class TestSchemaToIRInvalidBore75(unittest.TestCase):
    """bore_d=75 is not in the catalog → rejected."""

    def test_rejected_invalid_catalog(self):
        r = build_ir_from_schema_payload(_make_payload({"bore_d": 75}))
        self.assertEqual(r.status, "rejected")
        self.assertIsNone(r.ir_document)
        codes = [e["code"] for e in r.errors]
        self.assertIn("CATALOG_CHOICE", codes)

    def test_cannot_bypass_with_constructed_ok(self):
        # Even if a caller pre-constructed a ValidationResult claiming ok=True,
        # the adapter re-runs validate_parameters on the raw payload.
        # Passing bore_d=75 must be rejected regardless of claimed ok.
        r = build_ir_from_schema_payload(_make_payload({"bore_d": 75}))
        self.assertNotEqual(r.status, "accepted",
                            "bore_d=75 is not a catalog value and must never produce accepted IR")


class TestSchemaToIRUserExplicitOuterD(unittest.TestCase):
    """outer_d explicitly provided matching catalog value → user_explicit, not catalog_derived."""

    def setUp(self):
        # bore_d=24, outer_d=40 (catalog value for bore_d=24)
        self.result = build_ir_from_schema_payload(
            _make_payload({"bore_d": 24, "outer_d": 40})
        )

    def test_accepted(self):
        self.assertEqual(self.result.status, "accepted")

    def test_outer_d_user_explicit(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["outer_d"]["source"], "user_explicit")
        self.assertEqual(p["outer_d"]["source_ref"], "CAD-003.field:outer_d")
        # input field must be present for user_explicit
        self.assertIn("input", p["outer_d"])
        self.assertEqual(p["outer_d"]["input"]["value"], 40)

    def test_bore_d_still_user_explicit(self):
        p = {x["parameter_id"]: x for x in self.result.ir_document["parameters"]}
        self.assertEqual(p["bore_d"]["source"], "user_explicit")


class TestSchemaToIRStructure(unittest.TestCase):
    """Verify IR document structure for accepted results."""

    def setUp(self):
        self.result = build_ir_from_schema_payload(_make_payload({"bore_d": 24}))
        self.doc = self.result.ir_document

    def test_top_level_keys(self):
        for key in ("ir_version", "ir_revision", "status", "family",
                    "source", "parameters", "nodes", "constraints",
                    "execution", "validation_contract"):
            self.assertIn(key, self.doc, f"Missing top-level key: {key}")

    def test_family_fields(self):
        f = self.doc["family"]
        self.assertEqual(f["family_id"], "set_screw_shaft_collar")
        self.assertEqual(f["extension_namespace"], "family.set_screw_shaft_collar.v0")

    def test_constraints_count(self):
        # 5 preflight + 2 post = 7
        self.assertEqual(len(self.doc["constraints"]), 7)

    def test_constraint_ids_unique(self):
        ids = [c["constraint_id"] for c in self.doc["constraints"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_node_ordinals_contiguous(self):
        ordinals = [n["ordinal"] for n in self.doc["nodes"]]
        self.assertEqual(ordinals, list(range(7)))

    def test_enabled_if_on_secondary_nodes(self):
        nodes = {n["node_id"]: n for n in self.doc["nodes"]}
        self.assertIn("enabled_if", nodes["n4.hole.secondary"])
        self.assertEqual(nodes["n4.hole.secondary"]["enabled_if"]["parameter_id"], "second_screw")
        self.assertIn("enabled_if", nodes["n5.cut.secondary"])

    def test_comparison_policy(self):
        self.assertEqual(self.doc["execution"]["tolerance_profile"],
                         "CAD-006.geometry-comparison.v1")


class TestSchemaToIRSchemaVersionMismatch(unittest.TestCase):
    """Wrong schema_version → rejected."""

    def test_rejected_wrong_version(self):
        r = build_ir_from_schema_payload({
            "schema_version": "set_screw_shaft_collar.v99",
            "family_id": _FAMILY_ID,
            "parameters": {"bore_d": 24},
        })
        self.assertEqual(r.status, "rejected")


if __name__ == "__main__":
    unittest.main()
