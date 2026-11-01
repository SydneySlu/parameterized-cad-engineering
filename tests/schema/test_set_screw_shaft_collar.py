import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from schema.set_screw_shaft_collar import (  # noqa: E402
    CATALOG_ROWS,
    FAMILY_ID,
    SCHEMA_VERSION,
    schema_descriptor,
    validate_json,
    validate_parameters,
    ValidationResult,
)


class SetScrewShaftCollarSchemaTests(unittest.TestCase):
    def test_every_catalog_row_is_valid_and_derives_exactly(self):
        for bore_d, outer_d, screw_d, screw_len, width in CATALOG_ROWS:
            result = validate_parameters({"bore_d": bore_d})
            with self.subTest(bore_d=bore_d):
                self.assertTrue(result.ok, result.to_json())
                self.assertEqual(
                    result.normalized,
                    {
                        "bore_d": bore_d,
                        "outer_d": outer_d,
                        "width": width,
                        "screw_d": screw_d,
                        "screw_len": screw_len,
                        "second_screw": int(bore_d > 70),
                    },
                )
                self.assertEqual(result.provenance["bore_d"], "user_explicit")
                self.assertEqual(result.provenance["outer_d"], "catalog_derived")
                self.assertEqual(result.provenance["second_screw"], "rule_derived")

    def test_explicit_catalog_row_is_valid(self):
        result = validate_parameters(
            {
                "schema_version": SCHEMA_VERSION,
                "family_id": FAMILY_ID,
                "parameters": {
                    "bore_d": 20,
                    "outer_d": 32,
                    "width": 14,
                    "screw_d": 6,
                    "screw_len": 8,
                    "second_screw": 0,
                },
            }
        )
        self.assertTrue(result.ok, result.to_json())
        self.assertTrue(all(value == "user_explicit" for value in result.provenance.values()))

    def test_boundary_row_with_second_screw_is_valid(self):
        result = validate_parameters(
            {"bore_d": 80, "outer_d": 110, "width": 22, "screw_d": 12, "screw_len": 20, "second_screw": 1}
        )
        self.assertTrue(result.ok, result.to_json())

    def test_missing_critical_selector_is_rejected(self):
        result = validate_parameters({"outer_d": 32})
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_REQUIRED")
        self.assertEqual(result.errors[0].fields, ("bore_d",))

    def test_units_are_normalized_to_mm(self):
        result = validate_parameters({"bore_d": {"value": 2, "unit": "cm"}})
        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(result.normalized["bore_d"], 20)

    def test_second_screw_constraint_is_checked_before_build(self):
        result = validate_parameters({"bore_d": 20, "second_screw": 1})
        self.assertFalse(result.ok)
        self.assertIn("SECOND_SCREW_CONSTRAINT", {error.code for error in result.errors})

    def test_wall_thickness_invalid_case_is_rejected(self):
        result = validate_parameters(
            {"bore_d": 20, "outer_d": 19, "width": 14, "screw_d": 6, "screw_len": 8, "second_screw": 0}
        )
        self.assertFalse(result.ok)
        codes = {error.code for error in result.errors}
        self.assertIn("OUTER_DIAMETER_NOT_GREATER", codes)
        self.assertIn("WALL_THICKNESS_TOO_SMALL", codes)

    def test_width_support_rule_is_rejected(self):
        result = validate_parameters({"bore_d": 20, "width": 8, "screw_d": 6})
        self.assertFalse(result.ok)
        self.assertIn("WIDTH_SUPPORT_TOO_SMALL", {error.code for error in result.errors})

    def test_catalog_coupling_mismatch_is_explained(self):
        result = validate_parameters({"bore_d": 20, "outer_d": 33})
        self.assertFalse(result.ok)
        error = next(error for error in result.errors if error.code == "CATALOG_MISMATCH")
        self.assertEqual(error.fields, ("outer_d", "bore_d"))

    def test_unknown_field_and_invalid_option_are_stable_errors(self):
        result = validate_parameters({"bore_d": 20, "second_screw": 2, "extra": 1})
        self.assertFalse(result.ok)
        self.assertIn("UNKNOWN_FIELD", {error.code for error in result.errors})
        self.assertIn("OPTION_ERROR", {error.code for error in result.errors})

    def test_schema_descriptor_is_json_serializable(self):
        descriptor = schema_descriptor()
        encoded = json.dumps(descriptor, ensure_ascii=False, sort_keys=True)
        self.assertEqual(json.loads(encoded)["schema_version"], SCHEMA_VERSION)
        self.assertEqual(descriptor["fields"][0]["name"], "bore_d")
        self.assertEqual(descriptor["json_schema"]["additionalProperties"], False)
        artifact = json.loads(
            (ROOT / "agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json").read_text()
        )
        self.assertEqual(artifact, descriptor)

    def test_parameter_and_result_json_round_trip(self):
        result = validate_json(json.dumps({"bore_d": 20}))
        self.assertTrue(result.ok, result.to_json())
        restored = ValidationResult.from_json(result.to_json())
        self.assertEqual(restored.as_dict(), result.as_dict())

    def test_invalid_json_has_structured_error(self):
        result = validate_json("{not-json")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "INVALID_JSON")


if __name__ == "__main__":
    unittest.main()
