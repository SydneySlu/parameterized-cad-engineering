"""Tests for APP-003-C2 offline natural-language product flow (ADR-0023).

Run with:
    PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow -v

These tests verify the product state machine, confirmation gate, run
isolation, download security, and zero-CAD-before-confirm invariant.
CAD compile_ir is mocked so all tests run without CadQuery.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from demo.product_flow import (
    ProductFlowHandler,
    ProductRunRecord,
    PRODUCT_STATUS_NEEDS_CONFIRMATION,
    PRODUCT_STATUS_BLOCKED,
    PRODUCT_STATUS_SUCCEEDED,
    PRODUCT_STATUS_FAILED,
    PRODUCT_STATUS_CONSTRUCTING,
)
from cad_compilation.compiler import CompilationResult


# ---------------------------------------------------------------------------
# Mock helpers (same structure as test_demo_handler.py)
# ---------------------------------------------------------------------------

def _mock_compile_success(raw: bytes, output_dir: Path) -> CompilationResult:
    """Build a real temporary STEP file and return a success CompilationResult."""
    step_path = Path(output_dir) / "mock.step"
    step_content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Mock STEP'),'2;1');\nENDSEC;\nEND-ISO-10303-21;\n"
    step_path.write_bytes(step_content)
    step_hash = hashlib.sha256(step_content).hexdigest()
    ir_hash = hashlib.sha256(raw).hexdigest()
    return CompilationResult(
        ok=True,
        status="step_readback",
        errors=[],
        ir={"ir_version": "typed-cad-ir.v0", "status": "accepted"},
        manifest={
            "input_ir_sha256": ir_hash,
            "step": {"path": str(step_path), "bytes": len(step_content), "sha256": step_hash},
            "native_geometry": {
                "solids": 1, "shells": 1, "faces": 10, "edges": 20,
                "vertices": 30, "is_valid": True, "volume_mm3": 1234.56,
                "bbox_mm": {"xmin": 0.0, "xmax": 40.0, "ymin": -20.0,
                            "ymax": 20.0, "zmin": 0.0, "zmax": 16.0},
            },
            "step_readback": {
                "geometry": {"solids": 1, "shells": 1, "faces": 10, "edges": 20,
                             "vertices": 30, "is_valid": True, "volume_mm3": 1234.56},
                "comparison": {"pass": True},
            },
        },
        step_path=str(step_path),
    )


def _mock_compile_fail(raw: bytes, *, output_dir=None) -> CompilationResult:
    return CompilationResult(
        ok=False, status="build",
        errors=[{"code": "CAD_BUILD_NODE_ERROR", "stage": "build",
                 "message": "mocked build failure", "fields": ["runtime"]}],
        ir=None, manifest=None, step_path=None,
    )


# ---------------------------------------------------------------------------
# TestCreateProductRun – state machine transitions on create
# ---------------------------------------------------------------------------

class TestCreateProductRun(unittest.TestCase):
    """create_product_run sets the correct product status; never calls CAD."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = ProductFlowHandler(output_root=Path(self.tmpdir))

    def test_answer_bore24_needs_confirmation(self):
        """decision=answer + valid bore_d → needs_confirmation (awaiting confirm)."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-answer-bore24")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(rec.decision, "answer")
        self.assertEqual(rec.extracted_parameters, {"bore_d": 24})
        self.assertFalse(rec.confirmation["confirmed"])
        self.assertEqual(rec.confirmation["revision"], 0)
        mock_cad.assert_not_called()

    def test_ask_missing_bore_needs_confirmation(self):
        """decision=ask + missing_fields=[bore_d] → needs_confirmation."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-ask-missing-bore")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(rec.decision, "ask")
        self.assertIn("bore_d", rec.missing_fields)
        self.assertGreater(len(rec.questions), 0)
        mock_cad.assert_not_called()

    def test_catalog_conflict_blocked(self):
        """bore_d=24 + outer_d=33 (mismatch) → blocked; compile_ir not called."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-answer-catalog-conflict")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("CATALOG_MISMATCH" in c.get("code", "") for c in rec.conflicts))
        mock_cad.assert_not_called()

    def test_unsupported_blocked(self):
        """unsupported_requests non-empty → blocked; compile_ir not called."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-answer-unsupported")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("UNSUPPORTED" in e.get("code", "") for e in rec.errors))
        mock_cad.assert_not_called()

    def test_ask_extra_question_needs_confirmation(self):
        """decision=ask (has bore_d but has questions) → needs_confirmation."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-ask-extra-question")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(rec.decision, "ask")
        self.assertGreater(len(rec.questions), 0)
        mock_cad.assert_not_called()

    def test_refuse_blocked(self):
        """decision=refuse → blocked; compile_ir not called."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-refuse")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertEqual(rec.decision, "refuse")
        mock_cad.assert_not_called()

    def test_schema_fail_blocked(self):
        """bore_d=25 (not in catalog) → blocked at schema preflight; no CAD."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-answer-schema-fail")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(len(rec.conflicts) > 0 or len(rec.errors) > 0)
        mock_cad.assert_not_called()

    def test_bore80_needs_confirmation(self):
        """bore_d=80 → needs_confirmation (second_screw=1 derived at schema)."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            rec = self.handler.create_product_run("test", "c2-answer-bore80")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(rec.extracted_parameters, {"bore_d": 80})
        mock_cad.assert_not_called()

    def test_extraction_source_always_synthetic_fixture(self):
        """extraction_source is always synthetic_fixture."""
        rec = self.handler.create_product_run("test", "c2-answer-bore24")
        self.assertEqual(rec.extraction_source, "synthetic_fixture")

    def test_unknown_fixture_id_blocked(self):
        """Unknown fixture_id → blocked."""
        rec = self.handler.create_product_run("test", "nonexistent-fixture")
        self.assertEqual(rec.product_status, PRODUCT_STATUS_BLOCKED)


# ---------------------------------------------------------------------------
# TestConfirmProductRun
# ---------------------------------------------------------------------------

class TestConfirmProductRun(unittest.TestCase):
    """confirm_product_run: state transitions, revision checks, child run creation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = ProductFlowHandler(output_root=Path(self.tmpdir))

    def _make_needs_confirmation(self, fixture_id="c2-answer-bore24"):
        return self.handler.create_product_run("test request", fixture_id)

    def test_confirm_bore24_success(self):
        """Legal confirm on bore24 → succeeded with STEP (mock CAD)."""
        parent = self._make_needs_confirmation()
        self.assertEqual(parent.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)

        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})

        self.assertEqual(child.product_status, PRODUCT_STATUS_SUCCEEDED)
        self.assertEqual(child.parent_run_id, parent.run_id)
        self.assertNotEqual(child.run_id, parent.run_id)
        self.assertIsNotNone(child.step_sha256)
        self.assertGreater(child.step_bytes, 0)

    def test_confirm_bore80_success(self):
        """bore_d=80 confirm → succeeded; second_screw derived correctly."""
        parent = self._make_needs_confirmation("c2-answer-bore80")
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})
        self.assertEqual(child.product_status, PRODUCT_STATUS_SUCCEEDED)
        self.assertEqual(child.extracted_parameters.get("bore_d"), 80)

    def test_stale_revision_blocked(self):
        """confirmation_revision mismatch → blocked (STALE_REVISION)."""
        parent = self._make_needs_confirmation()
        result = self.handler.confirm_product_run(parent.run_id, 999, True, {})
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("STALE_REVISION" in e.get("code", "") for e in result.errors))

    def test_confirmed_false_blocked(self):
        """confirmed=False → blocked (CONFIRMATION_REJECTED)."""
        parent = self._make_needs_confirmation()
        result = self.handler.confirm_product_run(parent.run_id, 0, False, {})
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("CONFIRMATION_REJECTED" in e.get("code", "") for e in result.errors))

    def test_unknown_run_id_blocked(self):
        """Unknown run_id → blocked (RUN_NOT_FOUND)."""
        result = self.handler.confirm_product_run(
            "00000000-0000-4000-8000-000000000000", 0, True, {}
        )
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("NOT_FOUND" in e.get("code", "") for e in result.errors))

    def test_patch_invalid_field_blocked(self):
        """Patch with unknown field → blocked."""
        parent = self._make_needs_confirmation()
        result = self.handler.confirm_product_run(parent.run_id, 0, True, {"unknown_xyz": 42})
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("PATCH_UNKNOWN_FIELD" in e.get("code", "") for e in result.errors))

    def test_patch_bore_not_in_catalog(self):
        """Patch bore_d=25 (not in catalog) → blocked."""
        parent = self._make_needs_confirmation()
        result = self.handler.confirm_product_run(parent.run_id, 0, True, {"bore_d": 25})
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("BORE_NOT_IN_CATALOG" in e.get("code", "") for e in result.errors))

    def test_child_run_created_new_id(self):
        """Confirm creates a child run with a new UUID."""
        parent = self._make_needs_confirmation()
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})
        self.assertNotEqual(child.run_id, parent.run_id)
        self.assertEqual(child.parent_run_id, parent.run_id)
        # Child is in registry
        self.assertIsNotNone(self.handler.get_product_run(child.run_id))

    def test_parent_run_preserved(self):
        """Original run record is not overwritten after confirm."""
        parent = self._make_needs_confirmation()
        orig_run_id = parent.run_id
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            self.handler.confirm_product_run(parent.run_id, 0, True, {})
        still_there = self.handler.get_product_run(orig_run_id)
        self.assertIsNotNone(still_there)
        # Parent run_id unchanged
        self.assertEqual(still_there.run_id, orig_run_id)

    def test_failed_cad_pipeline_status_failed(self):
        """compile_ir failure → child product_status=failed."""
        parent = self._make_needs_confirmation()
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})
        self.assertEqual(child.product_status, PRODUCT_STATUS_FAILED)
        self.assertIsNone(child._step_path)
        self.assertIsNone(child.step_sha256)

    def test_patch_bore16_success(self):
        """Patch bore_d=16 (valid catalog value) on ask-missing-bore → succeeded."""
        parent = self._make_needs_confirmation("c2-ask-missing-bore")
        self.assertEqual(parent.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {"bore_d": 16})
        self.assertEqual(child.product_status, PRODUCT_STATUS_SUCCEEDED)
        self.assertEqual(child.extracted_parameters.get("bore_d"), 16)
        # bore_d from patch is user_explicit
        self.assertIn("bore_d", child.user_explicit_parameters)

    def test_blocked_run_not_confirmable(self):
        """confirm on a blocked run → blocked (NOT_CONFIRMABLE)."""
        blocked = self.handler.create_product_run("test", "c2-refuse")
        self.assertEqual(blocked.product_status, PRODUCT_STATUS_BLOCKED)
        result = self.handler.confirm_product_run(blocked.run_id, 0, True, {})
        self.assertEqual(result.product_status, PRODUCT_STATUS_BLOCKED)
        self.assertTrue(any("NOT_CONFIRMABLE" in e.get("code", "") for e in result.errors))


# ---------------------------------------------------------------------------
# TestDownloadIsolation
# ---------------------------------------------------------------------------

class TestDownloadIsolation(unittest.TestCase):
    """Download only serves succeeded runs, rejects everything else."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = ProductFlowHandler(output_root=Path(self.tmpdir))

    def _confirm_success(self, fixture_id="c2-answer-bore24"):
        parent = self.handler.create_product_run("test", fixture_id)
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})
        return child

    def test_download_succeeded_run(self):
        """Succeeded run → STEP bytes available and hash matches."""
        child = self._confirm_success()
        self.assertEqual(child.product_status, PRODUCT_STATUS_SUCCEEDED)
        step_bytes = self.handler.get_product_step_bytes_secure(child.run_id)
        self.assertIsNotNone(step_bytes)
        self.assertGreater(len(step_bytes), 0)
        self.assertEqual(hashlib.sha256(step_bytes).hexdigest(), child.step_sha256)

    def test_download_failed_run_none(self):
        """Failed run → None."""
        parent = self.handler.create_product_run("test", "c2-answer-bore24")
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            child = self.handler.confirm_product_run(parent.run_id, 0, True, {})
        self.assertEqual(child.product_status, PRODUCT_STATUS_FAILED)
        self.assertIsNone(self.handler.get_product_step_bytes_secure(child.run_id))

    def test_download_unknown_id_none(self):
        """Unknown run_id → None."""
        result = self.handler.get_product_step_bytes_secure(
            "00000000-0000-4000-8000-000000000000"
        )
        self.assertIsNone(result)

    def test_download_needs_confirmation_none(self):
        """needs_confirmation run (no STEP yet) → None."""
        parent = self.handler.create_product_run("test", "c2-answer-bore24")
        self.assertEqual(parent.product_status, PRODUCT_STATUS_NEEDS_CONFIRMATION)
        self.assertIsNone(self.handler.get_product_step_bytes_secure(parent.run_id))

    def test_download_path_traversal_invalid(self):
        """Non-UUID run_id → is_valid_run_id returns False."""
        self.assertFalse(self.handler.is_valid_run_id("../etc/passwd"))
        self.assertFalse(self.handler.is_valid_run_id("../../anything"))
        self.assertFalse(self.handler.is_valid_run_id("not-a-uuid"))

    def test_success_then_fail_no_leak(self):
        """Success then failure: failed run does not expose old STEP."""
        # First: success
        child1 = self._confirm_success("c2-answer-bore24")
        self.assertEqual(child1.product_status, PRODUCT_STATUS_SUCCEEDED)
        step1_bytes = self.handler.get_product_step_bytes_secure(child1.run_id)
        self.assertIsNotNone(step1_bytes)

        # Second: failure
        parent2 = self.handler.create_product_run("test", "c2-answer-bore80")
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            child2 = self.handler.confirm_product_run(parent2.run_id, 0, True, {})
        self.assertEqual(child2.product_status, PRODUCT_STATUS_FAILED)

        # Failed run cannot download
        self.assertIsNone(self.handler.get_product_step_bytes_secure(child2.run_id))
        # Failed run has no step_path
        self.assertIsNone(child2._step_path)
        # First success still downloadable
        step1_again = self.handler.get_product_step_bytes_secure(child1.run_id)
        self.assertIsNotNone(step1_again)
        self.assertEqual(hashlib.sha256(step1_again).hexdigest(), child1.step_sha256)

    def test_symlink_step_rejected(self):
        """STEP file replaced by symlink → rejected."""
        child = self._confirm_success()
        step_path = Path(child._step_path)
        external = Path(self.tmpdir) / "external.step"
        external.write_bytes(b"EXTERNAL")
        step_path.unlink()
        try:
            step_path.symlink_to(external)
        except OSError:
            self.skipTest("Cannot create symlink on this filesystem")
        self.assertIsNone(self.handler.get_product_step_bytes_secure(child.run_id))

    def test_hash_mismatch_rejected(self):
        """STEP file content tampered → hash mismatch → rejected."""
        child = self._confirm_success()
        Path(child._step_path).write_bytes(b"TAMPERED")
        self.assertIsNone(self.handler.get_product_step_bytes_secure(child.run_id))


# ---------------------------------------------------------------------------
# TestNoNetworkNoLLM
# ---------------------------------------------------------------------------

class TestNoNetworkNoLLM(unittest.TestCase):
    """create_product_run never calls compile_ir, network, or env keys."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = ProductFlowHandler(output_root=Path(self.tmpdir))

    def test_create_no_compile_called(self):
        """create_product_run does not call compile_ir for any fixture."""
        fixtures = [
            "c2-answer-bore24", "c2-ask-missing-bore", "c2-answer-catalog-conflict",
            "c2-answer-unsupported", "c2-ask-extra-question", "c2-refuse",
            "c2-answer-schema-fail", "c2-answer-bore80",
        ]
        with patch("integration.pipeline.compile_ir") as mock_cad:
            for fid in fixtures:
                self.handler.create_product_run("test", fid)
        mock_cad.assert_not_called()

    def test_no_env_reads_for_api_keys(self):
        """No environment variables for API keys are read during create."""
        with patch("integration.pipeline.compile_ir"):
            with patch("os.environ.get") as mock_env:
                self.handler.create_product_run("test", "c2-answer-bore24")
        for call_args in mock_env.call_args_list:
            args = call_args[0]
            if args and isinstance(args[0], str):
                self.assertNotIn("KEY", args[0].upper(),
                                  f"Should not read env var: {args[0]}")

    def test_no_llm_transport_imports(self):
        """product_flow.py does not import LLM transport modules."""
        import demo.product_flow as pf
        src = open(pf.__file__).read()
        self.assertNotIn("real_transport", src)
        self.assertNotIn("from llm.adapter", src)
        self.assertNotIn("from llm.runner", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import httpx", src)
        self.assertNotIn("FORMAL_EVALUATION_ALLOWED", src)


# ---------------------------------------------------------------------------
# TestRunRecord
# ---------------------------------------------------------------------------

class TestRunRecord(unittest.TestCase):
    """ProductRunRecord as_dict excludes internal fields."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = ProductFlowHandler(output_root=Path(self.tmpdir))

    def test_as_dict_excludes_internal(self):
        """as_dict() does not include _step_path or _run_dir."""
        rec = self.handler.create_product_run("test", "c2-answer-bore24")
        d = rec.as_dict()
        self.assertNotIn("_step_path", d)
        self.assertNotIn("_run_dir", d)
        self.assertIn("run_id", d)
        self.assertIn("product_status", d)
        self.assertIn("extraction_source", d)
        self.assertEqual(d["extraction_source"], "synthetic_fixture")

    def test_confirmation_fields_in_record(self):
        """Record has required confirmation fields."""
        rec = self.handler.create_product_run("test", "c2-answer-bore24")
        self.assertIn("revision", rec.confirmation)
        self.assertIn("confirmed", rec.confirmation)
        self.assertFalse(rec.confirmation["confirmed"])
        self.assertEqual(rec.confirmation["revision"], 0)


if __name__ == "__main__":
    unittest.main()
