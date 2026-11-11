"""Integration tests for the unified offline pipeline (APP-002-INTEGRATION-A1).

Run with:
    PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline -v

CAD calls are mocked with unittest.mock so all tests run with Python 3.10
(no cadquery required).  The tests verify gate logic, run isolation, and
failure semantics.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from integration.pipeline import run_pipeline, PipelineResult
from cad_compilation.compiler import CompilationResult

_FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _mock_compile_success(raw: bytes, output_dir: Path) -> CompilationResult:
    """Build a real temporary STEP file and return a success CompilationResult.

    Uses the actual ``raw`` IR bytes to compute ``input_ir_sha256`` so that
    the pipeline's new hash-verification gate is satisfied.
    """
    step_path = output_dir / "mock.step"
    step_content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Mock STEP'),'2;1');\nENDSEC;\nEND-ISO-10303-21;\n"
    step_path.write_bytes(step_content)
    step_hash = hashlib.sha256(step_content).hexdigest()
    ir_hash = hashlib.sha256(raw).hexdigest()   # must match the bytes sent in
    return CompilationResult(
        ok=True,
        status="step_readback",
        errors=[],
        ir={"ir_version": "typed-cad-ir.v0", "status": "accepted"},
        manifest={
            "input_ir_sha256": ir_hash,
            "step": {"path": str(step_path), "bytes": len(step_content), "sha256": step_hash},
            "native_geometry": {"solid_count": 1, "is_valid": True},
        },
        step_path=str(step_path),
    )


def _mock_compile_fail(output_dir: Path) -> CompilationResult:
    return CompilationResult(
        ok=False,
        status="build",
        errors=[{"code": "CAD_BUILD_NODE_ERROR", "stage": "build",
                 "message": "mocked build failure", "fields": ["runtime"]}],
        ir=None,
        manifest=None,
        step_path=None,
    )


class TestPipelineBore24Success(unittest.TestCase):
    """bore_d=24 with mocked CAD → success."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.envelope = _load_fixture("answer-bore24.json")

    def test_success_status(self):
        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("孔径 24 mm", self.envelope, output_root=self.tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.stage, "step_readback")
        self.assertIsNotNone(result.step_path)
        self.assertTrue(Path(result.step_path).is_file())
        self.assertGreater(Path(result.step_path).stat().st_size, 0)

    def test_extraction_source(self):
        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", self.envelope, output_root=self.tmpdir)

        self.assertEqual(result.extraction_source, "synthetic_fixture")

    def test_parameters_correct(self):
        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", self.envelope, output_root=self.tmpdir)

        self.assertEqual(result.parameters["bore_d"], 24)
        self.assertEqual(result.parameters["outer_d"], 40)
        self.assertEqual(result.parameters["second_screw"], 0)

    def test_ir_index_hashes(self):
        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", self.envelope, output_root=self.tmpdir)

        idx = result.ir_index
        self.assertIsNotNone(idx)
        self.assertIn("input_ir_sha256", idx)
        self.assertIn("step_sha256", idx)
        self.assertIn("envelope_sha256", idx)

    def test_run_dir_has_evidence_files(self):
        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", self.envelope, output_root=self.tmpdir)

        run_dir = Path(result.run_dir)
        for f in ("input.json", "envelope.json", "input_ir.json",
                  "schema_result.json", "compilation_result.json",
                  "index.json", "summary.json"):
            self.assertTrue((run_dir / f).is_file(), f"Missing: {f}")


class TestPipelineBore20Success(unittest.TestCase):
    """bore_d=20 with mocked CAD → success."""

    def test_success(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore20.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("孔径 20 mm", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.parameters["bore_d"], 20)
        self.assertEqual(result.parameters["outer_d"], 32)
        self.assertEqual(result.parameters["second_screw"], 0)


class TestPipelineBore16cm(unittest.TestCase):
    """bore_d={value:1.6,unit:cm} → 16 mm in IR."""

    def test_unit_conversion(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore16cm.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("孔径 1.6 cm", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.parameters["bore_d"], 16)

        # Verify the IR preserves original input.
        ir_doc = json.loads(
            (Path(result.run_dir) / "input_ir.json").read_text()
        )
        params = {p["parameter_id"]: p for p in ir_doc["parameters"]}
        self.assertEqual(params["bore_d"]["value"], 16)
        self.assertEqual(params["bore_d"]["input"]["value"], 1.6)
        self.assertEqual(params["bore_d"]["input"]["unit"], "cm")


class TestPipelineBore70SecondScrew(unittest.TestCase):
    """bore_d=70 → second_screw=0 (threshold is >70, not >=70)."""

    def test_second_screw_zero(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore70.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("孔径 70 mm", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.parameters["second_screw"], 0)


class TestPipelineBore80SecondScrew(unittest.TestCase):
    """bore_d=80 → second_screw=1."""

    def test_second_screw_one(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore80.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("孔径 80 mm", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.parameters["second_screw"], 1)


class TestPipelineAsk(unittest.TestCase):
    """ask decision → status=ask, questions returned, no STEP."""

    def test_ask_status(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("ask-missing-bore.json")

        result = run_pipeline("孔径?", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "ask")
        self.assertTrue(len(result.questions) > 0)
        self.assertIsNone(result.step_path)
        self.assertIsNone(result.ir_index)

    def test_compiler_not_called(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("ask-missing-bore.json")

        with patch("integration.pipeline.compile_ir") as mock_cad:
            result = run_pipeline("test", envelope, output_root=tmpdir)
            mock_cad.assert_not_called()

        self.assertEqual(result.status, "ask")


class TestPipelineRefuse(unittest.TestCase):
    """refuse decision → status=refuse, no STEP."""

    def test_refuse_status(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("refuse-decision.json")

        result = run_pipeline("孔径 24 mm", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "refuse")
        self.assertIsNone(result.step_path)

    def test_compiler_not_called(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("refuse-decision.json")

        with patch("integration.pipeline.compile_ir") as mock_cad:
            result = run_pipeline("test", envelope, output_root=tmpdir)
            mock_cad.assert_not_called()

        self.assertEqual(result.status, "refuse")


class TestPipelineMissingFields(unittest.TestCase):
    """answer with non-empty missing_fields → blocked, no STEP.

    This is the reverse test: Schema may pass (bore_d=24 is valid) but the
    construction gate blocks because missing_fields is non-empty.
    """

    def test_blocked_status(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-missing-fields.json")

        result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.step_path)
        self.assertIsNone(result.ir_index)

    def test_gate_error_code(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-missing-fields.json")

        result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertTrue(len(result.errors) > 0)
        self.assertEqual(result.errors[0]["code"], "GATE_MISSING_FIELDS")

    def test_compiler_not_called(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-missing-fields.json")

        with patch("integration.pipeline.compile_ir") as mock_cad:
            result = run_pipeline("test", envelope, output_root=tmpdir)
            mock_cad.assert_not_called()

        self.assertEqual(result.status, "blocked")


class TestPipelineUnsupportedRequests(unittest.TestCase):
    """answer with non-empty unsupported_requests → blocked."""

    def test_blocked_status(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("refuse-unsupported.json")

        result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.step_path)

    def test_gate_error_code(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("refuse-unsupported.json")

        result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.errors[0]["code"], "GATE_UNSUPPORTED_REQUESTS")

    def test_compiler_not_called(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("refuse-unsupported.json")

        with patch("integration.pipeline.compile_ir") as mock_cad:
            result = run_pipeline("test", envelope, output_root=tmpdir)
            mock_cad.assert_not_called()

        self.assertEqual(result.status, "blocked")


class TestPipelineCADFailure(unittest.TestCase):
    """Mocked CAD build failure → status=failed, no STEP."""

    def test_failed_status(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_fail(Path(output_dir) if output_dir else Path(tmpdir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.stage, "build")
        self.assertIsNone(result.step_path)
        self.assertIsNone(result.ir_index)

    def test_failed_has_error(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_fail(Path(output_dir) if output_dir else Path(tmpdir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertTrue(len(result.errors) > 0)
        self.assertEqual(result.errors[0]["code"], "CAD_BUILD_NODE_ERROR")


class TestPipelineRunIsolation(unittest.TestCase):
    """Two runs must not interfere; a failed run must not return a previous STEP."""

    def test_success_then_fail_no_step_leak(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        # First run: success.
        def mock_success(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_success):
            r1 = run_pipeline("first", envelope, output_root=tmpdir,
                              run_id="run-success-001")

        self.assertEqual(r1.status, "success")
        self.assertIsNotNone(r1.step_path)

        # Second run: failure.
        def mock_fail(raw, *, output_dir=None):
            return _mock_compile_fail(Path(output_dir) if output_dir else Path(tmpdir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_fail):
            r2 = run_pipeline("second", envelope, output_root=tmpdir,
                              run_id="run-fail-002")

        self.assertEqual(r2.status, "failed")
        self.assertIsNone(r2.step_path, "Failed run must not publish any STEP")

    def test_same_request_different_runs_no_overwrite(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            r1 = run_pipeline("same request", envelope, output_root=tmpdir,
                              run_id="dup-001")
            r2 = run_pipeline("same request", envelope, output_root=tmpdir,
                              run_id="dup-002")

        self.assertEqual(r1.status, "success")
        self.assertEqual(r2.status, "success")
        self.assertNotEqual(r1.run_id, r2.run_id)
        self.assertNotEqual(r1.run_dir, r2.run_dir)

    def test_duplicate_run_id_rejected(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            r1 = run_pipeline("test", envelope, output_root=tmpdir, run_id="dup-id")
            with self.assertRaises(ValueError):
                run_pipeline("test", envelope, output_root=tmpdir, run_id="dup-id")

    def test_invalid_run_id_path_separator(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        with self.assertRaises(ValueError):
            run_pipeline("test", envelope, output_root=tmpdir, run_id="../escape")

    def test_invalid_run_id_slash(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        with self.assertRaises(ValueError):
            run_pipeline("test", envelope, output_root=tmpdir, run_id="a/b")

    def test_invalid_run_id_empty(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        with self.assertRaises(ValueError):
            run_pipeline("test", envelope, output_root=tmpdir, run_id="")


class TestPipelineEvidenceIntegrity(unittest.TestCase):
    """Verify evidence files and hash consistency on success."""

    def test_step_hash_matches_manifest(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", envelope, output_root=tmpdir)

        idx = result.ir_index
        step_path = Path(result.step_path)
        actual_step_hash = hashlib.sha256(step_path.read_bytes()).hexdigest()
        self.assertEqual(idx["step_sha256"], actual_step_hash)

    def test_envelope_hash_matches_input(self):
        tmpdir = tempfile.mkdtemp()
        envelope = _load_fixture("answer-bore24.json")

        def mock_compile(raw, *, output_dir=None):
            return _mock_compile_success(raw, Path(output_dir))

        with patch("integration.pipeline.compile_ir", side_effect=mock_compile):
            result = run_pipeline("test", envelope, output_root=tmpdir)

        expected_hash = hashlib.sha256(envelope).hexdigest()
        self.assertEqual(result.ir_index["envelope_sha256"], expected_hash)


# ---------------------------------------------------------------------------
# P1-FIX: Fail-closed success gate tests
# These tests verify the six-condition success gate added in the P1 narrow fix.
# Every condition that is violated must produce status=failed and no step_path.
# ---------------------------------------------------------------------------


class TestPipelineExternalStepRejected(unittest.TestCase):
    """STEP path outside the current run's cad_output/ must be rejected.

    Reproduces the bug where the compiler returns ok=True, status=step_readback,
    and a step_path pointing outside the run directory, and the pipeline
    previously returned success.
    """

    def _make_external_step(self, external_dir: str) -> tuple[str, str, str]:
        """Create a STEP file in an external directory, return (path, hash, ir_hash)."""
        step_path = Path(external_dir) / "external_old.step"
        step_content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('old STEP'),'2;1');\nENDSEC;\nEND-ISO-10303-21;\n"
        step_path.write_bytes(step_content)
        step_hash = hashlib.sha256(step_content).hexdigest()
        ir_bytes = b'{"ir_version":"typed-cad-ir.v0"}'
        ir_hash = hashlib.sha256(ir_bytes).hexdigest()
        return str(step_path), step_hash, ir_hash

    def test_external_step_path_rejected(self):
        """Compiler returning step_path outside run dir must fail, not succeed."""
        with tempfile.TemporaryDirectory() as external_dir:
            ext_step_path, step_hash, ir_hash = self._make_external_step(external_dir)
            envelope = _load_fixture("answer-bore24.json")

            with tempfile.TemporaryDirectory() as tmpdir:
                def mock_compile_external(raw, *, output_dir=None):
                    # Returns ok=True but step_path points OUTSIDE the run dir.
                    return CompilationResult(
                        ok=True,
                        status="step_readback",
                        errors=[],
                        ir={"ir_version": "typed-cad-ir.v0", "status": "accepted"},
                        manifest={
                            "input_ir_sha256": hashlib.sha256(raw).hexdigest(),
                            "step": {"path": ext_step_path, "bytes": 80, "sha256": step_hash},
                            "native_geometry": {"solid_count": 1},
                        },
                        step_path=ext_step_path,
                    )

                with patch("integration.pipeline.compile_ir",
                           side_effect=mock_compile_external):
                    result = run_pipeline("孔径 24 mm", envelope, output_root=tmpdir)

            self.assertEqual(result.status, "failed",
                             "External STEP path must not be published as success")
            self.assertIsNone(result.step_path,
                              "step_path must be None when STEP is outside run dir")
            self.assertIsNone(result.ir_index,
                              "ir_index must be None on failure")
            codes = [e.get("code") for e in result.errors]
            self.assertIn("STEP_PATH_OUTSIDE_RUN_DIR", codes,
                          f"Expected STEP_PATH_OUTSIDE_RUN_DIR error, got: {codes}")

    def test_external_step_path_does_not_copy_or_delete(self):
        """The external STEP file must still exist after the rejection."""
        with tempfile.TemporaryDirectory() as external_dir:
            ext_step_path, step_hash, ir_hash = self._make_external_step(external_dir)
            envelope = _load_fixture("answer-bore24.json")

            with tempfile.TemporaryDirectory() as tmpdir:
                def mock_compile_external(raw, *, output_dir=None):
                    return CompilationResult(
                        ok=True,
                        status="step_readback",
                        errors=[],
                        ir={"ir_version": "typed-cad-ir.v0"},
                        manifest={
                            "input_ir_sha256": hashlib.sha256(raw).hexdigest(),
                            "step": {"path": ext_step_path, "bytes": 80,
                                     "sha256": step_hash},
                        },
                        step_path=ext_step_path,
                    )

                with patch("integration.pipeline.compile_ir",
                           side_effect=mock_compile_external):
                    run_pipeline("test", envelope, output_root=tmpdir)

            # External file must be untouched.
            self.assertTrue(Path(ext_step_path).is_file(),
                            "External STEP must not be deleted by the pipeline")


class TestPipelineManifestMissing(unittest.TestCase):
    """Compiler returning None manifest must be rejected."""

    def test_no_manifest_fails(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile_no_manifest(raw, *, output_dir=None):
                # ok=True, step_readback, but manifest=None.
                step_path = Path(output_dir) / "mock.step"
                step_content = b"STEP content"
                step_path.write_bytes(step_content)
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest=None,
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile_no_manifest):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("MANIFEST_MISSING", codes,
                      f"Expected MANIFEST_MISSING, got: {codes}")

    def test_empty_dict_manifest_fails(self):
        """manifest={} (no input_ir_sha256 key) must also fail."""
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile_empty_manifest(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_path.write_bytes(b"STEP content")
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={},  # empty — missing both required keys
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile_empty_manifest):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)


class TestPipelineManifestInputIRHashMissing(unittest.TestCase):
    """manifest missing input_ir_sha256 must fail."""

    def test_missing_input_ir_sha256(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_content = b"STEP content"
                step_path.write_bytes(step_content)
                step_hash = hashlib.sha256(step_content).hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={
                        # input_ir_sha256 intentionally absent
                        "step": {"path": str(step_path), "bytes": 12,
                                 "sha256": step_hash},
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("MANIFEST_INPUT_IR_SHA256_MISSING", codes,
                      f"Expected MANIFEST_INPUT_IR_SHA256_MISSING, got: {codes}")


class TestPipelineManifestStepHashMissing(unittest.TestCase):
    """manifest missing step.sha256 must fail."""

    def test_missing_step_sha256(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_path.write_bytes(b"STEP content")
                ir_hash = hashlib.sha256(raw).hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={
                        "input_ir_sha256": ir_hash,
                        # "step" key absent
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("MANIFEST_STEP_MISSING", codes,
                      f"Expected MANIFEST_STEP_MISSING, got: {codes}")

    def test_step_dict_missing_sha256_key(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_path.write_bytes(b"STEP content")
                ir_hash = hashlib.sha256(raw).hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={
                        "input_ir_sha256": ir_hash,
                        "step": {"path": str(step_path), "bytes": 12},
                        # sha256 key absent in step dict
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("MANIFEST_STEP_SHA256_MISSING", codes,
                      f"Expected MANIFEST_STEP_SHA256_MISSING, got: {codes}")


class TestPipelineInputIRHashMismatch(unittest.TestCase):
    """manifest.input_ir_sha256 must match the IR sent to compile_ir."""

    def test_wrong_input_ir_hash_fails(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_content = b"STEP content"
                step_path.write_bytes(step_content)
                step_hash = hashlib.sha256(step_content).hexdigest()
                # Provide a WRONG input_ir_sha256 (hash of empty bytes).
                wrong_ir_hash = hashlib.sha256(b"wrong-ir-bytes").hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={
                        "input_ir_sha256": wrong_ir_hash,  # intentionally wrong
                        "step": {"path": str(step_path), "bytes": 12,
                                 "sha256": step_hash},
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("INPUT_IR_HASH_MISMATCH", codes,
                      f"Expected INPUT_IR_HASH_MISMATCH, got: {codes}")


class TestPipelineStepHashMismatch(unittest.TestCase):
    """manifest.step.sha256 must match actual STEP file content."""

    def test_wrong_step_hash_fails(self):
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                step_path = Path(output_dir) / "mock.step"
                step_path.write_bytes(b"real STEP content")
                ir_hash = hashlib.sha256(raw).hexdigest()
                # Provide a WRONG step hash.
                wrong_step_hash = hashlib.sha256(b"wrong step bytes").hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0"},
                    manifest={
                        "input_ir_sha256": ir_hash,
                        "step": {"path": str(step_path), "bytes": 17,
                                 "sha256": wrong_step_hash},  # intentionally wrong
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("test", envelope, output_root=tmpdir)

        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.step_path)
        codes = [e.get("code") for e in result.errors]
        self.assertIn("STEP_HASH_MISMATCH", codes,
                      f"Expected STEP_HASH_MISMATCH, got: {codes}")


class TestPipelineSuccessGateAllConditions(unittest.TestCase):
    """Verify that the correct mock produces success (gate is not over-rejecting)."""

    def test_well_formed_manifest_succeeds(self):
        """The correct mock (all six conditions met) must still succeed."""
        envelope = _load_fixture("answer-bore24.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_compile(raw, *, output_dir=None):
                # Build a fully correct CompilationResult with matched hashes.
                step_path = Path(output_dir) / "valid.step"
                step_content = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"
                step_path.write_bytes(step_content)
                step_hash = hashlib.sha256(step_content).hexdigest()
                # input_ir_sha256 must match the ACTUAL IR bytes sent in.
                ir_hash = hashlib.sha256(raw).hexdigest()
                return CompilationResult(
                    ok=True,
                    status="step_readback",
                    errors=[],
                    ir={"ir_version": "typed-cad-ir.v0", "status": "accepted"},
                    manifest={
                        "input_ir_sha256": ir_hash,
                        "step": {"path": str(step_path), "bytes": len(step_content),
                                 "sha256": step_hash},
                        "native_geometry": {"solid_count": 1, "is_valid": True},
                    },
                    step_path=str(step_path),
                )

            with patch("integration.pipeline.compile_ir",
                       side_effect=mock_compile):
                result = run_pipeline("孔径 24 mm", envelope, output_root=tmpdir)

            self.assertEqual(result.status, "success")
            self.assertIsNotNone(result.step_path)
            self.assertIsNotNone(result.ir_index)
            self.assertEqual(result.ir_index["step_sha256"],
                             hashlib.sha256(Path(result.step_path).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
