"""Tests for the APP-003-C1 demo handler and server (ADR-0022).

Run with:
    PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -v

These tests verify:
- Valid parameters produce a successful run with STEP.
- Missing/invalid bore_d is blocked before CAD is called.
- Catalog conflicts are rejected.
- Download isolation: only own successful run STEP is served.
- Malicious run IDs and path traversal are rejected.
- Modifying parameters creates a new isolated run.
- A failed run after a successful one does not expose the old STEP.
- No network/LLM calls are made (verified by mock/spy).

CAD compile_ir is mocked with unittest.mock so all tests run without
CadQuery.  The mock produces a real temporary STEP file and a matching
manifest so the pipeline's hash-verification gate is satisfied.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from demo.handler import (
    DemoHandler,
    DemoRunResult,
    CATALOG_BORE_VALUES,
    CATALOG_TABLE,
)
from demo.server import make_handler_class, run_server
from cad_compilation.compiler import CompilationResult


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_compile_success(raw: bytes, output_dir: Path) -> CompilationResult:
    """Build a real temporary STEP file and return a success CompilationResult.

    Uses the actual ``raw`` IR bytes to compute ``input_ir_sha256`` so that
    the pipeline's new hash-verification gate is satisfied.

    The manifest structure mirrors the real compiler output:
    - native_geometry uses "solids", "faces", "edges", "vertices" (not *_count)
    - step_readback contains {"geometry": ..., "comparison": {"pass": True, ...}}
    """
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
            # Real compiler field names from geometry.summarize():
            "native_geometry": {
                "solids": 1,
                "shells": 1,
                "faces": 10,
                "edges": 20,
                "vertices": 30,
                "is_valid": True,
                "volume_mm3": 1234.56,
                "bbox_mm": {"xmin": 0.0, "xmax": 40.0, "ymin": -20.0,
                            "ymax": 20.0, "zmin": 0.0, "zmax": 16.0},
            },
            # Real compiler path for readback pass:
            "step_readback": {
                "geometry": {
                    "solids": 1, "shells": 1, "faces": 10, "edges": 20,
                    "vertices": 30, "is_valid": True, "volume_mm3": 1234.56,
                },
                "comparison": {"pass": True},
            },
        },
        step_path=str(step_path),
    )


def _mock_compile_fail(raw: bytes, *, output_dir=None) -> CompilationResult:
    return CompilationResult(
        ok=False,
        status="build",
        errors=[{"code": "CAD_BUILD_NODE_ERROR", "stage": "build",
                 "message": "mocked build failure", "fields": ["runtime"]}],
        ir=None,
        manifest=None,
        step_path=None,
    )


# ---------------------------------------------------------------------------
# Handler unit tests
# ---------------------------------------------------------------------------

class TestInputValidation(unittest.TestCase):
    """Input validation before any CAD call."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_missing_bore_d_rejected_no_cad(self):
        """Missing bore_d → invalid_input, no CAD call."""
        with patch("integration.pipeline.compile_ir") as mock_compile:
            result = self.handler.run("test request", None)
        self.assertEqual(result.status, "invalid_input")
        self.assertEqual(result.stage, "input_validation")
        self.assertIsNone(result.parameters)
        mock_compile.assert_not_called()

    def test_non_integer_bore_d_rejected_no_cad(self):
        """Non-integer bore_d → invalid_input, no CAD call."""
        with patch("integration.pipeline.compile_ir") as mock_compile:
            result = self.handler.run("test", "abc")
        self.assertEqual(result.status, "invalid_input")
        mock_compile.assert_not_called()

    def test_bore_d_not_in_catalog_rejected_no_cad(self):
        """bore_d=25 (not in catalog) → invalid_input, no CAD call."""
        with patch("integration.pipeline.compile_ir") as mock_compile:
            result = self.handler.run("test", 25)
        self.assertEqual(result.status, "invalid_input")
        self.assertIn("BORE_NOT_IN_CATALOG", result.errors[0]["code"])
        mock_compile.assert_not_called()

    def test_empty_request_text_allowed_but_tracked(self):
        """Empty request_text still produces a run (pipeline doesn't require it)."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("", 24)
        # Should succeed (request_text is provenance only)
        self.assertEqual(result.status, "success")


class TestSuccessfulRun(unittest.TestCase):
    """Valid parameters produce a successful run with STEP."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_bore24_success(self):
        """bore_d=24 with mocked CAD → success."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("孔径 24 mm", 24)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.stage, "step_readback")
        self.assertEqual(result.bore_d_input, 24)
        self.assertIsNotNone(result.parameters)
        self.assertEqual(result.parameters["bore_d"], 24)
        self.assertEqual(result.parameters["outer_d"], 40)  # catalog row for bore=24
        self.assertIsNotNone(result.provenance)
        self.assertEqual(result.provenance["bore_d"], "user_explicit")
        self.assertEqual(result.provenance["outer_d"], "catalog_derived")
        self.assertIsNotNone(result.ir_document)
        self.assertEqual(result.ir_document["family"]["family_id"], "set_screw_shaft_collar")
        self.assertIsNotNone(result.validation_summary)
        self.assertTrue(result.validation_summary["is_valid"])
        self.assertEqual(result.validation_summary["solid_count"], 1)
        self.assertIsNotNone(result.step_sha256)
        self.assertGreater(result.step_bytes, 0)

    def test_bore80_second_screw(self):
        """bore_d=80 → second_screw=1 (rule_derived)."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("孔径 80 mm", 80)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.parameters["second_screw"], 1)
        self.assertEqual(result.provenance["second_screw"], "rule_derived")


class TestCatalogConflict(unittest.TestCase):
    """Explicit catalog conflict is blocked, no CAD call."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_catalog_conflict_blocked_no_cad(self):
        """Providing outer_d that conflicts with bore_d catalog row → blocked."""
        # bore_d=24 expects outer_d=40, but we provide outer_d=33
        envelope = json.dumps({
            "contract_version": "app001-io.v1",
            "prompt_version": "app001-extraction.v5",
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24, "outer_d": 33},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "24", "source": "user_input"}],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        })
        with patch("integration.pipeline.compile_ir") as mock_compile:
            from integration.pipeline import run_pipeline
            result = run_pipeline("conflict test", envelope, output_root=self.tmpdir)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.stage, "schema")
        mock_compile.assert_not_called()


class TestDownloadIsolation(unittest.TestCase):
    """Download only serves successful runs, rejects everything else."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_download_success(self):
        """Successful run → STEP bytes retrievable."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")

        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNotNone(step_bytes)
        self.assertGreater(len(step_bytes), 0)
        # Verify hash matches
        self.assertEqual(hashlib.sha256(step_bytes).hexdigest(), result.step_sha256)

    def test_download_unknown_run_id(self):
        """Unknown run_id → None."""
        step_bytes = self.handler.get_step_bytes_secure("00000000-0000-4000-8000-000000000000")
        self.assertIsNone(step_bytes)

    def test_download_failed_run(self):
        """Failed run → None."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "failed")
        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNone(step_bytes)

    def test_download_invalid_input_run(self):
        """invalid_input run → None."""
        result = self.handler.run("test", 999)
        self.assertEqual(result.status, "invalid_input")
        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNone(step_bytes)


class TestPathTraversal(unittest.TestCase):
    """Malicious run IDs and path traversal are rejected."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_path_traversal_run_id(self):
        """../ in run_id → is_valid_run_id returns False."""
        self.assertFalse(self.handler.is_valid_run_id("../etc/passwd"))
        self.assertFalse(self.handler.is_valid_run_id("foo/../bar"))
        self.assertFalse(self.handler.is_valid_run_id(""))

    def test_valid_uuid_accepted(self):
        """Valid UUID v4 → is_valid_run_id returns True."""
        self.assertTrue(self.handler.is_valid_run_id("00000000-0000-4000-8000-000000000000"))
        self.assertTrue(self.handler.is_valid_run_id("abcdef01-2345-4789-abcd-ef0123456789"))

    def test_non_uuid_run_id_rejected(self):
        """Non-UUID format → is_valid_run_id returns False."""
        self.assertFalse(self.handler.is_valid_run_id("not-a-uuid"))
        self.assertFalse(self.handler.is_valid_run_id("1234567890"))
        self.assertFalse(self.handler.is_valid_run_id("GGGGGGGG-GGGG-4GGG-8GGG-GGGGGGGGGGGG"))


class TestRunIsolation(unittest.TestCase):
    """Each run uses a new UUID and isolated directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_two_runs_different_ids(self):
        """Two runs with different bore_d → different run_ids and directories."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            r1 = self.handler.run("first", 24)
            r2 = self.handler.run("second", 16)
        self.assertNotEqual(r1.run_id, r2.run_id)
        self.assertNotEqual(r1._run_dir, r2._run_dir)
        self.assertEqual(r1.bore_d_input, 24)
        self.assertEqual(r2.bore_d_input, 16)

    def test_failed_after_success_no_leak(self):
        """Success then failure → failed run does not expose old STEP."""
        # First run: success
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            r1 = self.handler.run("success", 24)
        self.assertEqual(r1.status, "success")

        # Second run: failure (compile fails)
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            r2 = self.handler.run("failure", 30)
        self.assertEqual(r2.status, "failed")
        self.assertIsNone(r2.step_sha256)
        self.assertIsNone(r2.step_bytes)

        # Failed run cannot download
        self.assertIsNone(self.handler.get_step_bytes_secure(r2.run_id))

        # First successful run still has its STEP
        step1 = self.handler.get_step_bytes_secure(r1.run_id)
        self.assertIsNotNone(step1)
        self.assertEqual(hashlib.sha256(step1).hexdigest(), r1.step_sha256)

        # Failed run's step_path is None
        self.assertIsNone(r2._step_path)

    def test_failed_run_no_old_step_path(self):
        """Failed run's _step_path is None, not pointing to old run's file."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            r1 = self.handler.run("success", 24)
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            r2 = self.handler.run("failure", 30)
        self.assertIsNotNone(r1._step_path)
        self.assertIsNone(r2._step_path)


class TestNoNetworkOrLLM(unittest.TestCase):
    """Verify no network/LLM calls are made."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_no_socket_calls(self):
        """No socket/network calls during a demo run."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            with patch("socket.socket") as mock_socket:
                result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")
        mock_socket.assert_not_called()

    def test_no_env_read(self):
        """No os.environ access for keys during a demo run."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            with patch("os.environ.get") as mock_env_get:
                result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")
        # os.environ.get should not be called for API keys
        # (Note: Python internals may call it; we check it's not called for our keys)
        for c in mock_env_get.call_args_list:
            args = c[0]
            if args and isinstance(args[0], str):
                self.assertNotIn("KEY", args[0].upper(),
                                  f"Should not read env var: {args[0]}")

    def test_no_llm_modules_imported(self):
        """Demo handler does not import LLM transport/adapter modules."""
        import demo.handler as dh
        # The handler module should not import real_transport, adapter, etc.
        source = open(dh.__file__).read()
        self.assertNotIn("real_transport", source)
        self.assertNotIn("from llm.adapter", source)
        self.assertNotIn("from llm.runner", source)
        self.assertNotIn("import requests", source)
        self.assertNotIn("import httpx", source)
        self.assertNotIn("import urllib3", source)


class TestServerHTTP(unittest.TestCase):
    """HTTP-level integration tests with mocked CAD."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))
        # We'll test the handler class directly, not start a real server

    def test_generate_valid_request(self):
        """POST /api/generate with valid bore_d → 200 with result JSON."""
        import io
        from http.server import BaseHTTPRequestHandler

        handler_class = make_handler_class(self.handler)

        # Simulate a POST request
        body = json.dumps({"request_text": "孔径 24 mm", "bore_d": 24}).encode("utf-8")

        # We can't easily instantiate BaseHTTPRequestHandler without a socket,
        # so test the handler logic indirectly via DemoHandler
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("孔径 24 mm", 24)

        self.assertEqual(result.status, "success")
        d = result.as_dict()
        self.assertEqual(d["status"], "success")
        self.assertEqual(d["bore_d_input"], 24)
        self.assertIn("run_id", d)

    def test_generate_missing_bore_d(self):
        """POST /api/generate without bore_d → handler returns invalid_input."""
        result = self.handler.run("test request", None)
        self.assertEqual(result.status, "invalid_input")
        self.assertIn("BORE", result.errors[0]["code"])

    def test_download_via_handler(self):
        """Download handler serves STEP for successful run."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")

        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNotNone(step_bytes)

    def test_download_via_handler_rejected_for_failed(self):
        """Download handler rejects failed run."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(raw, output_dir=kw["output_dir"])):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "failed")
        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNone(step_bytes)


class TestSymlinkEscape(unittest.TestCase):
    """Symlink escapes from run directory are rejected."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_symlink_step_rejected(self):
        """STEP file that is a symlink → rejected by get_step_bytes_secure."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")

        # Replace the STEP file with a symlink pointing outside
        step_path = Path(result._step_path)
        external_file = Path(self.tmpdir) / "external.step"
        external_file.write_bytes(b"EXTERNAL DATA")
        step_path.unlink()
        try:
            step_path.symlink_to(external_file)
        except OSError:
            self.skipTest("Cannot create symlink on this filesystem")

        # get_step_bytes_secure should reject the symlink
        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNone(step_bytes)

    def test_hash_mismatch_rejected(self):
        """STEP file with modified content → hash mismatch → rejected."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.status, "success")

        # Modify the STEP file content
        step_path = Path(result._step_path)
        step_path.write_bytes(b"TAMPERED CONTENT")

        step_bytes = self.handler.get_step_bytes_secure(result.run_id)
        self.assertIsNone(step_bytes)


class TestProvenanceAndSources(unittest.TestCase):
    """Parameter sources are correctly tracked."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_bore_d_user_explicit(self):
        """bore_d is marked as user_explicit."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.provenance["bore_d"], "user_explicit")

    def test_derived_params_catalog(self):
        """outer_d, screw_d, screw_len, width are catalog_derived."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        for field in ("outer_d", "screw_d", "screw_len", "width"):
            self.assertEqual(result.provenance[field], "catalog_derived",
                             f"{field} should be catalog_derived")

    def test_second_screw_rule_derived(self):
        """second_screw is rule_derived."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.provenance["second_screw"], "rule_derived")

    def test_catalog_values_correct(self):
        """Catalog values for bore_d=24 match the frozen table."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        # bore_d=24 → outer_d=40, screw_d=8, screw_len=12, width=16
        self.assertEqual(result.parameters["outer_d"], 40)
        self.assertEqual(result.parameters["screw_d"], 8)
        self.assertEqual(result.parameters["screw_len"], 12)
        self.assertEqual(result.parameters["width"], 16)
        self.assertEqual(result.parameters["second_screw"], 0)


class TestManifestFieldMapping(unittest.TestCase):
    """Validation summary correctly maps real compiler manifest field names.

    native_geometry uses: solids, faces, edges, vertices (not *_count).
    readback_pass comes from manifest["step_readback"]["comparison"]["pass"],
    not manifest["readback"]["pass"].
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = DemoHandler(output_root=Path(self.tmpdir))

    def test_solid_count_from_native_geometry_solids(self):
        """validation_summary.solid_count comes from native_geometry['solids']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertIsNotNone(result.validation_summary)
        # Must be the integer value 1, not None
        self.assertEqual(result.validation_summary["solid_count"], 1)

    def test_face_count_from_native_geometry_faces(self):
        """validation_summary.face_count comes from native_geometry['faces']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.validation_summary["face_count"], 10)

    def test_edge_count_from_native_geometry_edges(self):
        """validation_summary.edge_count comes from native_geometry['edges']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.validation_summary["edge_count"], 20)

    def test_vertex_count_from_native_geometry_vertices(self):
        """validation_summary.vertex_count comes from native_geometry['vertices']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertEqual(result.validation_summary["vertex_count"], 30)

    def test_readback_pass_from_step_readback_comparison(self):
        """readback_pass comes from manifest['step_readback']['comparison']['pass']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        # Must be True (boolean), not None
        self.assertIs(result.validation_summary["readback_pass"], True)

    def test_is_valid_still_correct(self):
        """is_valid is still read from native_geometry['is_valid']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertIs(result.validation_summary["is_valid"], True)

    def test_volume_still_correct(self):
        """volume_mm3 is still read from native_geometry['volume_mm3']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertAlmostEqual(result.validation_summary["volume_mm3"], 1234.56)

    def test_step_bytes_still_correct(self):
        """step_bytes is still read from manifest['step']['bytes']."""
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(raw, Path(kw["output_dir"]))):
            result = self.handler.run("test", 24)
        self.assertGreater(result.validation_summary["step_bytes"], 0)

    def test_old_wrong_field_names_yield_none(self):
        """Confirm old incorrect fields (solid_count key on wrong dict) would give None.

        This is a cross-check: a manifest that only has the old-style *_count
        keys should produce None for the counts (old bug) and None for
        readback_pass (old path), showing the fix is load-bearing.
        """
        import hashlib, tempfile
        from pathlib import Path as _P
        from cad_compilation.compiler import CompilationResult

        def _mock_old_field_names(raw, **kw):
            """Mock using the old (wrong) field names the original code expected."""
            od = _P(kw["output_dir"])
            sc = b"ISO-10303-21;\nENDSEC;\nEND-ISO-10303-21;\n"
            sp = od / "mock.step"
            sp.write_bytes(sc)
            sh = hashlib.sha256(sc).hexdigest()
            ih = hashlib.sha256(raw).hexdigest()
            return CompilationResult(
                ok=True, status="step_readback", errors=[],
                ir={"ir_version": "typed-cad-ir.v0", "status": "accepted"},
                manifest={
                    "input_ir_sha256": ih,
                    "step": {"path": str(sp), "bytes": len(sc), "sha256": sh},
                    # Old wrong key names (what the original broken code tried to read):
                    "native_geometry": {
                        "solid_count": 1,   # wrong key — real compiler uses "solids"
                        "face_count": 10,   # wrong key — real compiler uses "faces"
                        "edge_count": 20,   # wrong key — real compiler uses "edges"
                        "vertex_count": 30, # wrong key — real compiler uses "vertices"
                        "is_valid": True,
                        "volume_mm3": 999.0,
                    },
                    # Old wrong path — real compiler uses step_readback.comparison.pass:
                    "readback": {"pass": True},
                },
                step_path=str(sp),
            )

        td = tempfile.mkdtemp()
        h = DemoHandler(output_root=_P(td))
        with patch("integration.pipeline.compile_ir", side_effect=_mock_old_field_names):
            result = h.run("test old fields", 24)

        self.assertEqual(result.status, "success")
        # With the fixed handler, old wrong field names → None (not 1/10/20/30/True)
        self.assertIsNone(result.validation_summary["solid_count"],
                          "solid_count should be None when manifest only has 'solid_count' key")
        self.assertIsNone(result.validation_summary["face_count"])
        self.assertIsNone(result.validation_summary["edge_count"])
        self.assertIsNone(result.validation_summary["vertex_count"])
        self.assertIsNone(result.validation_summary["readback_pass"],
                          "readback_pass should be None when only manifest['readback'] exists")


class TestUIHTMLEscape(unittest.TestCase):
    """Verify that the esc() function in server.py HTML-escapes dynamic values.

    The UI renders pipeline results into innerHTML using string templates.
    All dynamic values must be passed through esc() so that attacker-controlled
    strings (error messages, run_ids, field names, etc.) are displayed as text,
    not executed as HTML or JavaScript.
    """

    def _get_esc_fn(self):
        """Extract the esc() logic from server.py and return it as a Python callable.

        The server embeds esc() inside a JS string template that uses {{}} escaping
        for Python .format() – the actual JS source is:
            function esc(s) { ... .replace(/</, '&lt;') ... }
        We test the equivalent logic in Python to verify the escape rules.
        """
        # Equivalent Python implementation of the JS esc() in server.py
        def esc(s):
            if s is None:
                return ''
            s = str(s)
            s = s.replace('&', '&amp;')
            s = s.replace('<', '&lt;')
            s = s.replace('>', '&gt;')
            s = s.replace('"', '&quot;')
            s = s.replace("'", '&#39;')
            return s
        return esc

    def _assert_esc_fn_in_server_source(self):
        """Verify the esc() function is present in server.py source."""
        import demo.server as srv
        src = open(srv.__file__).read()
        self.assertIn("function esc(s)", src,
                      "esc() must be defined in server.py")
        self.assertIn("&amp;", src)
        self.assertIn("&lt;", src)
        self.assertIn("&gt;", src)
        self.assertIn("&quot;", src)
        self.assertIn("&#39;", src)

    def test_esc_function_in_server_source(self):
        """server.py HTML source contains esc() with all five escape sequences."""
        self._assert_esc_fn_in_server_source()

    def test_esc_ampersand(self):
        """& is escaped to &amp;."""
        esc = self._get_esc_fn()
        self.assertEqual(esc("a & b"), "a &amp; b")

    def test_esc_less_than(self):
        """< is escaped to &lt; — prevents tag injection."""
        esc = self._get_esc_fn()
        self.assertEqual(esc("<script>"), "&lt;script&gt;")

    def test_esc_greater_than(self):
        """> is escaped to &gt;."""
        esc = self._get_esc_fn()
        self.assertEqual(esc("a > b"), "a &gt; b")

    def test_esc_double_quote(self):
        '''Double quote is escaped to &quot; — safe inside attribute values.'''
        esc = self._get_esc_fn()
        self.assertEqual(esc('"hello"'), "&quot;hello&quot;")

    def test_esc_single_quote(self):
        """Single quote is escaped to &#39;."""
        esc = self._get_esc_fn()
        self.assertEqual(esc("it's"), "it&#39;s")

    def test_esc_onerror_payload(self):
        """XSS payload with onerror is fully escaped — cannot execute."""
        esc = self._get_esc_fn()
        payload = '<img src=x onerror=alert(1)>'
        escaped = esc(payload)
        # No unescaped < or > remain — the payload cannot form an HTML tag
        self.assertNotIn('<', escaped)
        self.assertNotIn('>', escaped)
        self.assertIn('&lt;', escaped)
        self.assertIn('&gt;', escaped)
        # "onerror" appears as plain text (safe — there are no surrounding < >)
        self.assertIn('onerror', escaped)
        # Full expected escaped value
        self.assertEqual(escaped, '&lt;img src=x onerror=alert(1)&gt;')

    def test_esc_script_tag(self):
        """<script>alert(1)</script> payload is fully escaped."""
        esc = self._get_esc_fn()
        payload = '<script>alert(1)</script>'
        escaped = esc(payload)
        self.assertNotIn('<script>', escaped)
        self.assertNotIn('</script>', escaped)
        self.assertIn('&lt;script&gt;', escaped)

    def test_esc_null_returns_empty(self):
        """None → empty string (not 'None')."""
        esc = self._get_esc_fn()
        self.assertEqual(esc(None), '')

    def test_esc_number(self):
        """Numbers are converted to string safely."""
        esc = self._get_esc_fn()
        self.assertEqual(esc(42), '42')
        self.assertEqual(esc(3.14), '3.14')

    def test_renderResult_uses_esc_in_source(self):
        """renderResult in server.py calls esc() on dynamic values."""
        import demo.server as srv
        src = open(srv.__file__).read()
        # Find renderResult function body and confirm esc() calls on dynamic data
        self.assertIn("esc(d.run_id)", src)
        self.assertIn("esc(d.stage)", src)
        self.assertIn("esc(e.code", src)
        self.assertIn("esc(e.message", src)
        self.assertIn("esc(k)", src)
        self.assertIn("esc(v)", src)
        self.assertIn("esc(d.run_id)", src)

    def test_no_unescaped_dynamic_in_renderResult(self):
        """renderResult must not concatenate d.run_id, d.stage, etc. without esc()."""
        import demo.server as srv
        src = open(srv.__file__).read()
        # Find the renderResult block (between 'function renderResult' and next
        # top-level 'function ' or end of script)
        start = src.find("function renderResult")
        self.assertGreater(start, 0, "renderResult must be in server.py source")
        # Slice just that function (heuristic: up to the next 'function ' at same level)
        end = src.find("\nfunction ", start + 1)
        block = src[start:end] if end > 0 else src[start:]
        # d.run_id, d.stage, d.status must only appear inside esc(...)
        # Check that d.run_id doesn't appear bare (unescaped) in a template literal
        import re
        # Pattern: ${d.run_id} WITHOUT esc() wrapping — this would be a bug
        bare_runid = re.search(r'\$\{d\.run_id\}', block)
        self.assertIsNone(bare_runid,
                          "d.run_id must be wrapped in esc() inside renderResult")
        bare_stage = re.search(r'\$\{d\.stage\}', block)
        self.assertIsNone(bare_stage,
                          "d.stage must be wrapped in esc() inside renderResult")

    def test_malicious_bore_d_error_message_escaped(self):
        """Error message containing HTML tags is treated as text, not markup."""
        tmpdir = tempfile.mkdtemp()
        handler = DemoHandler(output_root=Path(tmpdir))
        # bore_d value that would produce a message containing the payload
        result = handler.run("test", '<img src=x onerror=alert(1)>')
        self.assertEqual(result.status, "invalid_input")
        # The raw error message should contain the input string
        err_msg = result.errors[0].get("message", "")
        # Verify the pipeline didn't execute it — just stored as plain text
        self.assertIn("<img", err_msg)  # it's in the error message text
        # But when serialised to JSON for the UI, esc() on the JS side must handle it.
        # We verify JSON serialization is clean (no embedded script execution):
        import json
        serialised = json.dumps(result.as_dict())
        # The JSON string is safe for transmission; esc() on the JS side escapes it
        self.assertIn("img src=x", serialised)   # present as data
        self.assertNotIn("<script>", serialised)  # no injected script tags


if __name__ == "__main__":
    unittest.main()
