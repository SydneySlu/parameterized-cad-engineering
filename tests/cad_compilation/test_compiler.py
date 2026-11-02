from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "work" / "benchcad-source" / "api-snapshot-035f467" / "framework"))
sys.path.insert(0, str(ROOT / "work" / "benchcad-source" / "api-snapshot-035f467"))

from cad_compilation import compile_ir, validate_ir
from cad_compilation.compiler import _cq_runtime, _shape
from cad_compilation.geometry import compare_roundtrip, summarize
from cad_compilation.ir import IR_ROOT


EXAMPLES = IR_ROOT / "examples"
SCHEMA = json.loads((IR_ROOT / "ir-v0.schema.json").read_text())


class CadCompilerTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((EXAMPLES / name).read_text())

    def compile(self, name: str, output: str) -> object:
        return compile_ir(json.dumps(self.load(name)), output_dir=output)

    def test_all_six_ir_examples_pass_schema_and_semantics(self):
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(SCHEMA)
        for path in sorted(EXAMPLES.glob("*.json")):
            document = json.loads(path.read_text())
            self.assertEqual(list(validator.iter_errors(document)), [], path.name)
            self.assertEqual(validate_ir(path.read_text()), [], path.name)

    def test_legitimate_ir_catalog_and_hard_boundary_compile_and_match_native_reference(self):
        cq, _ = _cq_runtime()
        from bench2.loader import load_family

        part, _ = load_family(ROOT / "work" / "benchcad-source" / "api-snapshot-035f467" / "designs" / "set_screw_shaft_collar")
        with tempfile.TemporaryDirectory() as output:
            for name in ("legal-catalog-row.json", "legal-second-screw.json"):
                raw = (EXAMPLES / name).read_text()
                result = compile_ir(raw, output_dir=output)
                self.assertTrue(result.ok, result.errors)
                self.assertEqual(result.status, "step_readback")
                self.assertEqual(result.manifest["native_repeatability"]["comparison"]["exact_equal"], True)
                self.assertTrue(result.manifest["step_readback"]["comparison"]["pass"])
                from jsonschema import Draft202012Validator
                self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(result.ir)), [])
                params = {entry["parameter_id"]: entry["value"] for entry in json.loads(raw)["parameters"]}
                reference = _shape(part.build(**params))
                reference_summary = summarize(reference)
                diff = compare_roundtrip(reference_summary, result.manifest["native_geometry"])
                self.assertTrue(diff["pass"], diff)
                self.assertEqual(result.manifest["native_geometry"]["solids"], 1)
                self.assertEqual(result.manifest["native_geometry"]["shells"], 1)

    def test_catalog_rule_rejected_before_build(self):
        rejected = compile_ir((EXAMPLES / "rule-rejected-second-screw.json").read_text())
        self.assertFalse(rejected.ok)
        self.assertEqual(rejected.status, "preflight")
        self.assertEqual(rejected.errors[0]["code"], "SECOND_SCREW_CONSTRAINT")
        self.assertIsNone(rejected.manifest)

    def test_multi_solid_build_is_rejected_at_post_geometry(self):
        cq, _ = _cq_runtime()
        from bench2.loader import load_family

        part, _ = load_family(ROOT / "work" / "benchcad-source" / "api-snapshot-035f467" / "designs" / "set_screw_shaft_collar")
        # Bypass preflight deliberately and feed the known 3-solid output to
        # the post-geometry gate; the gate must reject even valid B-Rep solids.
        shape = _shape(part.build(bore_d=20, outer_d=19, width=14, screw_d=6, screw_len=8, second_screw=0))
        with self.assertRaises(Exception) as caught:
            summarize(shape)
        self.assertEqual(caught.exception.error.code, "GEOMETRY_MULTI_SOLID")

    def test_duplicate_node_id_and_future_dependency_are_semantic_errors(self):
        document = self.load("legal-catalog-row.json")
        document["nodes"][1]["node_id"] = document["nodes"][0]["node_id"]
        errors = validate_ir(json.dumps(document))
        self.assertIn("IR_DUPLICATE_NODE_ID", {error.code for error in errors})

        document = self.load("legal-catalog-row.json")
        document["nodes"][1]["depends_on"] = [document["nodes"][2]["node_id"]]
        errors = validate_ir(json.dumps(document))
        self.assertIn("IR_DEPENDENCY_NOT_PREVIOUS", {error.code for error in errors})

    def test_unregistered_formula_wrong_source_and_duplicate_output_are_rejected(self):
        document = self.load("legal-catalog-row.json")
        document["nodes"][1]["inputs"]["chamfer"] = {
            "kind": "formula", "formula_id": "arbitrary_python", "args": {}
        }
        # The Schema may reject an unregistered formula ID before semantic
        # validation; either way it must not be accepted for execution.
        self.assertTrue(validate_ir(json.dumps(document)))

        document = self.load("legal-catalog-row.json")
        document["source"]["source_commit"] = "0" * 40
        self.assertTrue(validate_ir(json.dumps(document)))

        document = self.load("legal-catalog-row.json")
        document["nodes"][1]["outputs"][0]["output_id"] = document["nodes"][0]["outputs"][0]["output_id"]
        self.assertTrue(validate_ir(json.dumps(document)))

    def test_missing_node_input_and_invalid_validation_result_are_rejected(self):
        document = self.load("legal-catalog-row.json")
        del document["nodes"][1]["inputs"]["chamfer"]
        self.assertTrue(validate_ir(json.dumps(document)))

        document = self.load("legal-catalog-row.json")
        document["validation_result"] = {
            "stage": "step_export", "ok": False,
            "completed_stages": ["build", "post_geometry"],
            "errors": [{"code": "BAD", "stage": "build", "message": "wrong stage",
                        "severity": "error", "fields": [], "node_ids": [], "retryable": False}],
            "metrics": {},
        }
        self.assertTrue(validate_ir(json.dumps(document)))

    def test_build_failure_is_persisted_with_valid_stage_contract(self):
        from cad_compilation.errors import CadError, PipelineError

        with mock.patch("cad_compilation.compiler._native_build", side_effect=PipelineError(CadError("CAD_BUILD_NODE_ERROR", "build", "injected build failure", "nodes.n1"))):
            result = self.compile("legal-catalog-row.json", "/tmp/cad005006-build-failure")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "build")
        self.assertEqual(result.ir["validation_result"]["completed_stages"], [])
        from jsonschema import Draft202012Validator
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(result.ir)), [])

    def test_step_readback_failure_is_persisted_with_valid_stage_contract(self):
        with tempfile.TemporaryDirectory() as output:
            with mock.patch("cadquery.importers.importStep", side_effect=RuntimeError("injected readback failure")):
                result = self.compile("legal-catalog-row.json", output)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "step_readback")
        self.assertEqual(result.ir["validation_result"]["completed_stages"], ["build", "post_geometry", "step_export"])
        from jsonschema import Draft202012Validator
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(result.ir)), [])

    def test_step_export_failure_is_persisted_with_valid_stage_contract(self):
        cq, _ = _cq_runtime()
        from bench2.loader import load_family

        part, _ = load_family(ROOT / "work" / "benchcad-source" / "api-snapshot-035f467" / "designs" / "set_screw_shaft_collar")
        shape = _shape(part.build(bore_d=20, outer_d=32, width=14, screw_d=6, screw_len=8, second_screw=0))
        with mock.patch.object(type(shape), "exportStep", side_effect=RuntimeError("injected export failure")):
            result = self.compile("legal-catalog-row.json", "/tmp/cad005006-export-failure")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "step_export")
        self.assertEqual(result.ir["validation_result"]["completed_stages"], ["build", "post_geometry"])
        from jsonschema import Draft202012Validator
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(result.ir)), [])


if __name__ == "__main__":
    unittest.main()
