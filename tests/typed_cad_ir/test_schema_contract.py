"""Regression tests for Typed CAD IR v0 schema and result-stage semantics."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2] / "agent-work/typed-cad-ir/IR-001-v0"
SCHEMA = json.loads((ROOT / "ir-v0.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
EXPECTED_COMPLETED = {
    "build": [],
    "post_geometry": ["build"],
    "step_export": ["build", "post_geometry"],
    "step_readback": ["build", "post_geometry", "step_export"],
}


def semantic_stage_errors(ir: dict) -> list[str]:
    """Minimal contract oracle for stage identity and stage-order regressions."""
    errors = []
    result = ir.get("validation_result")
    if result is None:
        return errors
    if ir.get("status") != "accepted":
        errors.append("IR_VALIDATION_RESULT_ON_REJECTED")
    if result.get("completed_stages") != EXPECTED_COMPLETED.get(result.get("stage")):
        errors.append("IR_VALIDATION_STAGE_ORDER_INVALID")
    if any(error.get("stage") != result.get("stage") for error in result.get("errors", [])):
        errors.append("IR_VALIDATION_STAGE_MISMATCH")
    if result.get("ok") and result.get("errors"):
        errors.append("IR_VALIDATION_RESULT_ERRORS_INCONSISTENT")
    if not result.get("ok") and not result.get("errors"):
        errors.append("IR_VALIDATION_RESULT_ERRORS_INCONSISTENT")
    return errors


class IRSchemaContractTests(unittest.TestCase):
    def test_schema_and_all_examples(self):
        Draft202012Validator.check_schema(SCHEMA)
        example_paths = sorted((ROOT / "examples").glob("*.json"))
        self.assertEqual(len(example_paths), 6)
        for path in example_paths:
            with self.subTest(example=path.name):
                ir = json.loads(path.read_text())
                VALIDATOR.validate(ir)
                self.assertEqual(semantic_stage_errors(ir), [])

    def test_build_and_post_geometry_failures_are_distinct(self):
        build = json.loads((ROOT / "examples/build-failure.json").read_text())
        post = json.loads((ROOT / "examples/validation-failure.json").read_text())
        self.assertEqual(build["status"], "accepted")
        self.assertNotIn("errors", build)
        self.assertEqual(build["validation_result"]["stage"], "build")
        self.assertEqual(build["validation_result"]["errors"][0]["code"], "CAD_BUILD_NODE_ERROR")
        self.assertEqual(post["validation_result"]["stage"], "post_geometry")
        self.assertEqual(post["validation_result"]["errors"][0]["code"], "GEOMETRY_MULTI_SOLID")

    def test_axis_contract_and_stage_order_reject_mismatches(self):
        legal = json.loads((ROOT / "examples/legal-catalog-row.json").read_text())
        revolve = next(n for n in legal["nodes"] if n["node_type"] == "shape.revolve_profile")
        self.assertEqual(revolve["properties"]["workplane"], "XZ")
        self.assertEqual(revolve["properties"]["axis_local"], [0, 1, 0])
        self.assertEqual(revolve["properties"]["axis"], "Z")

        wrong_axis = copy.deepcopy(legal)
        next(n for n in wrong_axis["nodes"] if n["node_type"] == "shape.revolve_profile")["properties"]["axis"] = "Y"
        self.assertTrue(list(VALIDATOR.iter_errors(wrong_axis)))

        build = json.loads((ROOT / "examples/build-failure.json").read_text())
        mismatched_error = copy.deepcopy(build)
        mismatched_error["validation_result"]["errors"][0]["stage"] = "post_geometry"
        self.assertTrue(list(VALIDATOR.iter_errors(mismatched_error)))
        wrong_order = copy.deepcopy(build)
        wrong_order["validation_result"]["completed_stages"] = ["build"]
        self.assertTrue(list(VALIDATOR.iter_errors(wrong_order)))
        self.assertIn("IR_VALIDATION_STAGE_ORDER_INVALID", semantic_stage_errors(wrong_order))


if __name__ == "__main__":
    unittest.main()
