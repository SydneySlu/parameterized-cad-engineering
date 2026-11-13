"""HTTP integration tests for APP-003-C3 product confirmation UI.

Run with:
    PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_ui -v

Tests verify:
- GET /product returns C3 HTML with offline disclaimer
- GET /api/product/fixtures returns JSON allowlist (no file paths)
- C1 / and /api/generate are still backward-compatible
- POST /api/product/create happy and error paths
- POST /api/product/confirm type validation (HTTP 400 for string types)
- GET /product-download/<run_id> rejects non-succeeded runs
- XSS: PRODUCT_HTML contains esc() with all five escape sequences
- Dynamic values in renderResult use esc()

CAD compile_ir is mocked; all tests run without CadQuery.
No network, no .env, no LLM calls.
"""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from demo.handler import DemoHandler
from demo.product_flow import ProductFlowHandler
from demo.server import make_handler_class, PRODUCT_HTML_CONTENT
from cad_compilation.compiler import CompilationResult


# ---------------------------------------------------------------------------
# HTTP simulation helpers
# ---------------------------------------------------------------------------

class _FakeServer:
    """Minimal server stub required by BaseHTTPRequestHandler.__init__."""
    timeout = None


def _make_request(handler_class, method: str, path: str,
                  body=None) -> tuple[int, bytes]:
    """Simulate one HTTP request and return (status_code, response_body_bytes)."""
    body_bytes = b""
    if body is not None:
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

    request_lines = (
        f"{method} {path} HTTP/1.1\r\n"
        f"Host: 127.0.0.1\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Content-Type: application/json\r\n"
        f"\r\n"
    ).encode("utf-8") + body_bytes

    response_io = io.BytesIO()

    class _TestSocket:
        def makefile(self, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "rb")
            if "r" in mode:
                return io.BufferedReader(io.BytesIO(request_lines))
            # Write path: wrap response_io in StreamWriter
            return _ResponseWriter(response_io)

        def getsockname(self):
            return ("127.0.0.1", 8080)

        def getpeername(self):
            return ("127.0.0.1", 1234)

        def sendall(self, data: bytes) -> None:
            response_io.write(data)

        def shutdown(self, *args):
            pass

        def close(self):
            pass

    class _ResponseWriter(io.RawIOBase):
        """Minimal writable stream that feeds into response_io."""
        def __init__(self, buf: io.BytesIO) -> None:
            self._buf = buf

        def write(self, b) -> int:
            self._buf.write(b)
            return len(b)

        def writelines(self, lines) -> None:
            for line in lines:
                self.write(line)

    try:
        handler_class(_TestSocket(), ("127.0.0.1", 1234), _FakeServer())
    except Exception:
        pass  # some paths raise after writing the response

    response_io.seek(0)
    raw = response_io.read()
    if not raw:
        return 0, b""

    sep = b"\r\n\r\n"
    idx = raw.find(sep)
    if idx < 0:
        return 0, raw

    header_part = raw[:idx].decode("utf-8", errors="replace")
    body_part = raw[idx + 4:]

    lines = header_part.split("\r\n")
    if not lines:
        return 0, body_part
    parts = lines[0].split(" ", 2)
    try:
        status = int(parts[1])
    except (IndexError, ValueError):
        status = 0
    return status, body_part


def _json_body(body_bytes: bytes) -> dict:
    return json.loads(body_bytes.decode("utf-8"))


# ---------------------------------------------------------------------------
# Mock CAD compile_ir (same structure as test_product_flow.py)
# ---------------------------------------------------------------------------

def _mock_compile_success(raw: bytes, output_dir: Path) -> CompilationResult:
    step_path = Path(output_dir) / "mock.step"
    step_content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Mock'));\nENDSEC;\nEND-ISO-10303-21;\n"
    step_path.write_bytes(step_content)
    step_hash = hashlib.sha256(step_content).hexdigest()
    ir_hash = hashlib.sha256(raw).hexdigest()
    return CompilationResult(
        ok=True, status="step_readback", errors=[],
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
                "geometry": {"solids": 1, "is_valid": True},
                "comparison": {"pass": True},
            },
        },
        step_path=str(step_path),
    )


def _mock_compile_fail(raw: bytes, *, output_dir=None) -> CompilationResult:
    return CompilationResult(
        ok=False, status="build",
        errors=[{"code": "CAD_BUILD_NODE_ERROR", "stage": "build",
                 "message": "mocked build failure"}],
        ir=None, manifest=None, step_path=None,
    )


# ---------------------------------------------------------------------------
# Test fixture setup helper
# ---------------------------------------------------------------------------

def _make_handler(tmpdir):
    demo = DemoHandler(output_root=Path(tmpdir))
    product = ProductFlowHandler(output_root=Path(tmpdir))
    return make_handler_class(demo, product)


# ===========================================================================
# TestC3ProductPage
# ===========================================================================

class TestC3ProductPage(unittest.TestCase):
    """GET /product and GET /api/product/fixtures."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_product_page_returns_200(self):
        """GET /product → 200 HTML."""
        status, body = _make_request(self.hcls, "GET", "/product")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body[:200])

    def test_product_page_contains_offline_disclaimer(self):
        """GET /product page warns about offline synthetic fixture mode."""
        status, body = _make_request(self.hcls, "GET", "/product")
        self.assertEqual(status, 200)
        # Must contain the offline mode warning (in Chinese or English)
        text = body.decode("utf-8", errors="replace")
        self.assertTrue(
            "synthetic" in text.lower() or "离线" in text or "fixture" in text.lower(),
            "Product page must mention offline/synthetic/fixture mode"
        )

    def test_product_page_contains_esc_function(self):
        """GET /product page has esc() HTML-escape function."""
        status, body = _make_request(self.hcls, "GET", "/product")
        text = body.decode("utf-8", errors="replace")
        self.assertIn("function esc(", text)
        self.assertIn("&amp;", text)
        self.assertIn("&lt;", text)
        self.assertIn("&gt;", text)

    def test_product_page_no_bare_dynamic_interpolation(self):
        """Dynamic values in renderResultSection call esc()."""
        # The PRODUCT_HTML should not have bare ${d.run_id} etc.
        import re
        bare = re.search(r'\$\{d\.run_id\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.run_id must be wrapped in esc()")

    def test_product_page_mentions_step_not_certification(self):
        """Product page mentions STEP ≠ manufacturing certification."""
        _, body = _make_request(self.hcls, "GET", "/product")
        text = body.decode("utf-8", errors="replace")
        self.assertTrue("制造认证" in text or "manufacturing" in text.lower())

    def test_fixture_list_endpoint_returns_json(self):
        """GET /api/product/fixtures → 200 JSON with fixtures array."""
        status, body = _make_request(self.hcls, "GET", "/api/product/fixtures")
        self.assertEqual(status, 200)
        d = _json_body(body)
        self.assertIn("fixtures", d)
        self.assertIsInstance(d["fixtures"], list)
        self.assertGreater(len(d["fixtures"]), 0)

    def test_fixture_list_no_file_paths(self):
        """GET /api/product/fixtures never exposes file paths."""
        status, body = _make_request(self.hcls, "GET", "/api/product/fixtures")
        text = body.decode("utf-8", errors="replace")
        # Must not contain OS path separators in the response body
        self.assertNotIn("/sessions/", text)
        self.assertNotIn("tests/demo/fixtures/", text)

    def test_fixture_list_contains_known_fixture_ids(self):
        """Fixture list includes the expected C2 fixture IDs."""
        status, body = _make_request(self.hcls, "GET", "/api/product/fixtures")
        d = _json_body(body)
        ids = {f["fixture_id"] for f in d["fixtures"]}
        self.assertIn("c2-answer-bore24", ids)
        self.assertIn("c2-ask-missing-bore", ids)
        self.assertIn("c2-refuse", ids)


# ===========================================================================
# TestC1BackwardCompat
# ===========================================================================

class TestC1BackwardCompat(unittest.TestCase):
    """C1 routes must remain unchanged."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_c1_root_still_200(self):
        """GET / → 200 C1 HTML (backward compat)."""
        status, body = _make_request(self.hcls, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body[:200])

    def test_c1_root_not_product_page(self):
        """GET / returns C1 page (not C3 product page)."""
        _, root_body = _make_request(self.hcls, "GET", "/")
        _, prod_body = _make_request(self.hcls, "GET", "/product")
        root_text = root_body.decode("utf-8", errors="replace")
        prod_text = prod_body.decode("utf-8", errors="replace")
        # C3 page must contain fixture-related elements; C1 page must not
        self.assertIn("fixture-sel", prod_text)
        self.assertNotIn("fixture-sel", root_text)
        # C1 page has bore-d dropdown; C3 has fixture-sel instead
        self.assertIn("bore-d", root_text)

    def test_c1_api_generate_missing_bore_returns_400(self):
        """POST /api/generate with missing bore_d → 400 (C1 backward compat)."""
        status, body = _make_request(
            self.hcls, "POST", "/api/generate",
            body={"request_text": "test request"}
        )
        self.assertEqual(status, 400)

    def test_unknown_path_returns_404(self):
        """Unknown path → 404."""
        status, _ = _make_request(self.hcls, "GET", "/this-does-not-exist")
        self.assertEqual(status, 404)


# ===========================================================================
# TestProductCreateHTTP
# ===========================================================================

class TestProductCreateHTTP(unittest.TestCase):
    """POST /api/product/create via HTTP."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_create_valid_fixture_returns_200(self):
        """POST /api/product/create with known fixture → 200 JSON."""
        with patch("integration.pipeline.compile_ir"):
            status, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test 24mm", "fixture_id": "c2-answer-bore24"}
            )
        self.assertEqual(status, 200)
        d = _json_body(body)
        self.assertIn("run_id", d)
        self.assertIn("product_status", d)

    def test_create_bore24_needs_confirmation(self):
        """POST create bore24 → needs_confirmation status."""
        with patch("integration.pipeline.compile_ir"):
            status, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "needs_confirmation")

    def test_create_refuse_returns_blocked(self):
        """POST create refuse fixture → blocked status."""
        with patch("integration.pipeline.compile_ir"):
            status, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-refuse"}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "blocked")

    def test_create_unsupported_returns_blocked(self):
        """POST create unsupported fixture → blocked."""
        with patch("integration.pipeline.compile_ir"):
            status, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-unsupported"}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "blocked")

    def test_create_conflict_fixture_blocked(self):
        """POST create catalog-conflict fixture → blocked."""
        with patch("integration.pipeline.compile_ir"):
            status, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-catalog-conflict"}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "blocked")

    def test_create_unknown_fixture_id_returns_blocked(self):
        """Unknown fixture_id → product response with blocked status."""
        status, body = _make_request(
            self.hcls, "POST", "/api/product/create",
            body={"request_text": "test", "fixture_id": "nonexistent-fixture-xyz"}
        )
        # Should be 200 with blocked status (C2 returns a blocked run record)
        self.assertEqual(status, 200)
        d = _json_body(body)
        self.assertEqual(d["product_status"], "blocked")

    def test_create_missing_request_text_returns_400(self):
        """POST create missing request_text → 400."""
        status, body = _make_request(
            self.hcls, "POST", "/api/product/create",
            body={"fixture_id": "c2-answer-bore24"}
        )
        self.assertEqual(status, 400)

    def test_create_missing_fixture_id_returns_400(self):
        """POST create missing fixture_id → 400."""
        status, body = _make_request(
            self.hcls, "POST", "/api/product/create",
            body={"request_text": "test request"}
        )
        self.assertEqual(status, 400)

    def test_create_no_cad_calls(self):
        """POST create does not call compile_ir for any fixture."""
        with patch("integration.pipeline.compile_ir") as mock_cad:
            for fid in ["c2-answer-bore24", "c2-refuse", "c2-ask-missing-bore",
                        "c2-answer-unsupported", "c2-answer-catalog-conflict"]:
                _make_request(self.hcls, "POST", "/api/product/create",
                              body={"request_text": "t", "fixture_id": fid})
        mock_cad.assert_not_called()


# ===========================================================================
# TestProductConfirmHTTP
# ===========================================================================

class TestProductConfirmHTTP(unittest.TestCase):
    """POST /api/product/confirm/<run_id> via HTTP — type validation and flow."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def _create_run(self, fixture_id="c2-answer-bore24"):
        """Helper: create a run and return run_id."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": fixture_id}
            )
        d = _json_body(body)
        return d["run_id"]

    def test_confirm_string_confirmed_false_returns_400(self):
        """confirmed='false' (string) → HTTP 400."""
        run_id = self._create_run()
        status, body = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": 0, "confirmed": "false", "patch": {}}
        )
        self.assertEqual(status, 400)
        d = _json_body(body)
        self.assertIn("INVALID_CONFIRMED_TYPE", str(d))

    def test_confirm_string_confirmed_true_returns_400(self):
        """confirmed='true' (string) → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": 0, "confirmed": "true", "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_int_confirmed_zero_returns_400(self):
        """confirmed=0 (integer) → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": 0, "confirmed": 0, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_int_confirmed_one_returns_400(self):
        """confirmed=1 (integer) → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": 0, "confirmed": 1, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_string_revision_zero_returns_400(self):
        """confirmation_revision='0' (string) → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": "0", "confirmed": True, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_string_revision_abc_returns_400(self):
        """confirmation_revision='abc' → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": "abc", "confirmed": True, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_bool_revision_returns_400(self):
        """confirmation_revision=True (bool) → HTTP 400."""
        run_id = self._create_run()
        status, _ = _make_request(
            self.hcls, "POST", f"/api/product/confirm/{run_id}",
            body={"confirmation_revision": True, "confirmed": True, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_valid_types_accepted(self):
        """confirmation_revision=0 (int), confirmed=True (bool) → not 400."""
        run_id = self._create_run()
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            status, body = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{run_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        # Should be 200 with a child run
        self.assertEqual(status, 200)
        d = _json_body(body)
        self.assertIn("product_status", d)
        self.assertNotEqual(d["run_id"], run_id)  # child run has new ID

    def test_confirm_bore24_full_flow_succeeded(self):
        """Full flow: create bore24 → confirm → child succeeded."""
        run_id = self._create_run("c2-answer-bore24")
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            status, body = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{run_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "succeeded")
        self.assertIsNotNone(d.get("step_sha256"))
        self.assertGreater(d.get("step_bytes", 0), 0)

    def test_confirm_missing_bore_with_patch_bore16(self):
        """ask-missing-bore + patch bore_d=16 → succeeded."""
        run_id = self._create_run("c2-ask-missing-bore")
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            status, body = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{run_id}",
                body={"confirmation_revision": 0, "confirmed": True,
                      "patch": {"bore_d": 16}}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "succeeded")

    def test_confirm_non_uuid_run_id_returns_400(self):
        """confirm with non-UUID run_id → 400."""
        status, _ = _make_request(
            self.hcls, "POST", "/api/product/confirm/not-a-uuid",
            body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
        )
        self.assertEqual(status, 400)

    def test_confirm_type_errors_no_cad_called(self):
        """Type validation errors (400) must not call compile_ir."""
        run_id = self._create_run()
        with patch("integration.pipeline.compile_ir") as mock_cad:
            _make_request(
                self.hcls, "POST", f"/api/product/confirm/{run_id}",
                body={"confirmation_revision": "0", "confirmed": True, "patch": {}}
            )
        mock_cad.assert_not_called()


# ===========================================================================
# TestProductDownloadHTTP
# ===========================================================================

class TestProductDownloadHTTP(unittest.TestCase):
    """GET /product-download/<run_id> via HTTP."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_download_needs_confirmation_run_returns_403(self):
        """GET /product-download for needs_confirmation run → 403."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        status, _ = _make_request(
            self.hcls, "GET", f"/product-download/{parent_id}"
        )
        self.assertEqual(status, 403)

    def test_download_succeeded_run_returns_200(self):
        """Full flow create→confirm→download: succeeded run → 200 STEP."""
        # Create
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        # Confirm
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            _, body2 = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{parent_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d2 = _json_body(body2)
        self.assertEqual(d2["product_status"], "succeeded")
        child_id = d2["run_id"]
        # Download
        status, step_bytes = _make_request(
            self.hcls, "GET", f"/product-download/{child_id}"
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(step_bytes), 0)
        # Hash must match what was reported
        actual_hash = hashlib.sha256(step_bytes).hexdigest()
        self.assertEqual(actual_hash, d2["step_sha256"])

    def test_download_failed_run_returns_403(self):
        """Failed compile → child product_status=failed → download 403."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(
                       raw, output_dir=kw["output_dir"])):
            _, body2 = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{parent_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d2 = _json_body(body2)
        self.assertEqual(d2["product_status"], "failed")
        child_id = d2["run_id"]
        status, _ = _make_request(
            self.hcls, "GET", f"/product-download/{child_id}"
        )
        self.assertEqual(status, 403)

    def test_download_non_uuid_returns_400(self):
        """Non-UUID run_id → 400."""
        status, _ = _make_request(
            self.hcls, "GET", "/product-download/../etc/passwd"
        )
        self.assertEqual(status, 400)


# ===========================================================================
# TestProductUIXSSDefense
# ===========================================================================

class TestProductUIXSSDefense(unittest.TestCase):
    """PRODUCT_HTML esc() defense checks."""

    def test_product_html_has_esc_function(self):
        """PRODUCT_HTML contains esc() with all five escape sequences."""
        self.assertIn("function esc(", PRODUCT_HTML_CONTENT)
        self.assertIn("&amp;", PRODUCT_HTML_CONTENT)
        self.assertIn("&lt;", PRODUCT_HTML_CONTENT)
        self.assertIn("&gt;", PRODUCT_HTML_CONTENT)
        self.assertIn("&quot;", PRODUCT_HTML_CONTENT)
        self.assertIn("&#39;", PRODUCT_HTML_CONTENT)

    def test_product_html_no_bare_runid_in_templates(self):
        """${d.run_id} must not appear bare (must be wrapped in esc())."""
        import re
        bare = re.search(r'\$\{d\.run_id\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.run_id used bare (unescaped) in product HTML")

    def test_product_html_no_bare_pipeline_status(self):
        """pipeline_status appears only inside esc() calls."""
        import re
        bare = re.search(r'\$\{d\.pipeline_status\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.pipeline_status used bare in product HTML")

    def test_product_html_has_online_disclaimer(self):
        """PRODUCT_HTML contains fixture/offline disclaimer text."""
        lower = PRODUCT_HTML_CONTENT.lower()
        self.assertTrue(
            "synthetic" in lower or "fixture" in lower or "离线" in PRODUCT_HTML_CONTENT,
            "Must mention offline/synthetic/fixture mode"
        )

    def test_product_html_step_not_certification_disclaimer(self):
        """PRODUCT_HTML includes STEP ≠ certification disclaimer."""
        self.assertTrue(
            "制造认证" in PRODUCT_HTML_CONTENT
            or "manufacturing" in PRODUCT_HTML_CONTENT.lower()
        )


# ===========================================================================
# TestProductGetHTTP
# ===========================================================================

class TestProductGetHTTP(unittest.TestCase):
    """GET /api/product/<run_id> via HTTP."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_get_known_run_returns_200(self):
        """GET /api/product/<run_id> for known run → 200."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        run_id = _json_body(body)["run_id"]
        status, body2 = _make_request(
            self.hcls, "GET", f"/api/product/{run_id}"
        )
        self.assertEqual(status, 200)
        d = _json_body(body2)
        self.assertEqual(d["run_id"], run_id)

    def test_get_unknown_run_returns_404(self):
        """GET /api/product/<unknown_uuid> → 404."""
        status, _ = _make_request(
            self.hcls, "GET", "/api/product/00000000-0000-4000-8000-000000000000"
        )
        self.assertEqual(status, 404)

    def test_get_non_uuid_returns_400(self):
        """GET /api/product/not-a-uuid → 400."""
        status, _ = _make_request(
            self.hcls, "GET", "/api/product/not-a-uuid"
        )
        self.assertEqual(status, 400)


# ===========================================================================
# TestRequestTextDisplay (narrow fix: request_text in confirm section)
# ===========================================================================

class TestRequestTextDisplay(unittest.TestCase):
    """renderConfirmSection must display request_text safely."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_product_html_renders_request_text(self):
        """PRODUCT_HTML renderConfirmSection references d.request_text via esc()."""
        self.assertIn("d.request_text", PRODUCT_HTML_CONTENT)
        # Must be wrapped in esc(), not bare
        import re
        bare = re.search(r'\$\{d\.request_text\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.request_text must be wrapped in esc()")

    def test_create_response_includes_request_text(self):
        """POST /api/product/create response includes request_text field."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "需要孔径 24 mm 的轴环", "fixture_id": "c2-answer-bore24"}
            )
        d = _json_body(body)
        self.assertIn("request_text", d)
        self.assertEqual(d["request_text"], "需要孔径 24 mm 的轴环")

    def test_create_response_request_text_is_the_input(self):
        """request_text in response matches what was sent in the request."""
        req_text = "GN705轴环 24mm轴孔"
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": req_text, "fixture_id": "c2-answer-bore24"}
            )
        d = _json_body(body)
        self.assertEqual(d["request_text"], req_text)

    def test_malicious_request_text_in_api_response_is_plain_data(self):
        """Malicious request_text is returned as JSON string (not executed)."""
        malicious = '<img src=x onerror=alert(1)>'
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": malicious, "fixture_id": "c2-answer-bore24"}
            )
        d = _json_body(body)
        # The JSON must contain it as a plain string
        self.assertEqual(d["request_text"], malicious)
        # JSON encoding itself is safe — the browser's esc() must handle it
        body_text = body.decode("utf-8")
        self.assertIn("img src=x", body_text)  # present as data
        # JSON encodes it safely: < should be escaped as < or literal
        # Either way, it's JSON string — the esc() in HTML rendering is what matters
        self.assertNotIn("<script>", body_text)  # no injected script tags


# ===========================================================================
# TestStepHashDisplay (narrow fix: STEP SHA-256 in result section)
# ===========================================================================

class TestStepHashDisplay(unittest.TestCase):
    """renderResultSection must show step_sha256 on success, nothing on failure."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.hcls = _make_handler(self.tmpdir)

    def test_product_html_renders_step_sha256_on_succeeded(self):
        """PRODUCT_HTML references d.step_sha256 inside the succeeded branch."""
        # Find the succeeded block in renderResultSection
        self.assertIn("d.step_sha256", PRODUCT_HTML_CONTENT)
        # Must be wrapped in esc(), not bare
        import re
        bare = re.search(r'\$\{d\.step_sha256\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.step_sha256 must be wrapped in esc()")

    def test_product_html_step_sha256_inside_succeeded_block(self):
        """d.step_sha256 appears only inside the succeeded conditional block."""
        # Find the section between "if (d.product_status === 'succeeded')" and
        # the matching closing block
        idx_succeeded = PRODUCT_HTML_CONTENT.find("if (d.product_status === 'succeeded')")
        self.assertGreater(idx_succeeded, 0, "Must have succeeded conditional")
        idx_sha = PRODUCT_HTML_CONTENT.find("d.step_sha256", idx_succeeded)
        self.assertGreater(idx_sha, idx_succeeded,
                           "d.step_sha256 must appear after succeeded check")

    def test_full_flow_confirm_response_has_step_sha256(self):
        """confirm → succeeded response includes step_sha256 field."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            _, body2 = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{parent_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d2 = _json_body(body2)
        self.assertEqual(d2["product_status"], "succeeded")
        self.assertIn("step_sha256", d2)
        self.assertIsNotNone(d2["step_sha256"])
        # Must be a 64-char hex string
        self.assertEqual(len(d2["step_sha256"]), 64)
        int(d2["step_sha256"], 16)  # valid hex

    def test_failed_run_response_has_no_step_sha256(self):
        """confirm → failed response has step_sha256=None."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_fail(
                       raw, output_dir=kw["output_dir"])):
            _, body2 = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{parent_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d2 = _json_body(body2)
        self.assertEqual(d2["product_status"], "failed")
        # step_sha256 should be None or absent for failed runs
        self.assertIsNone(d2.get("step_sha256"))

    def test_blocked_run_has_no_step_sha256(self):
        """blocked run (refuse fixture) has step_sha256=None."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-refuse"}
            )
        d = _json_body(body)
        self.assertEqual(d["product_status"], "blocked")
        self.assertIsNone(d.get("step_sha256"))

    def test_step_sha256_matches_downloadable_file(self):
        """Downloaded STEP file hash matches step_sha256 in confirm response."""
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                self.hcls, "POST", "/api/product/create",
                body={"request_text": "test", "fixture_id": "c2-answer-bore24"}
            )
        parent_id = _json_body(body)["run_id"]
        with patch("integration.pipeline.compile_ir",
                   side_effect=lambda raw, **kw: _mock_compile_success(
                       raw, Path(kw["output_dir"]))):
            _, body2 = _make_request(
                self.hcls, "POST", f"/api/product/confirm/{parent_id}",
                body={"confirmation_revision": 0, "confirmed": True, "patch": {}}
            )
        d2 = _json_body(body2)
        child_id = d2["run_id"]
        _, step_bytes = _make_request(self.hcls, "GET", f"/product-download/{child_id}")
        actual_hash = hashlib.sha256(step_bytes).hexdigest()
        self.assertEqual(actual_hash, d2["step_sha256"])


# ===========================================================================
# TestXSSNarrowFix (narrow fix: request_text + step_sha256 XSS regression)
# ===========================================================================

class TestXSSNarrowFix(unittest.TestCase):
    """XSS regression for new dynamic fields: request_text and step_sha256."""

    def test_product_html_no_bare_request_text(self):
        """d.request_text must not appear bare in template literals."""
        import re
        bare = re.search(r'\$\{d\.request_text\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.request_text must be in esc()")

    def test_product_html_no_bare_step_sha256(self):
        """d.step_sha256 must not appear bare in template literals."""
        import re
        bare = re.search(r'\$\{d\.step_sha256\}', PRODUCT_HTML_CONTENT)
        self.assertIsNone(bare, "d.step_sha256 must be in esc()")

    def test_product_html_step_sha256_uses_esc(self):
        """PRODUCT_HTML uses esc(d.step_sha256) in template."""
        self.assertIn("esc(d.step_sha256)", PRODUCT_HTML_CONTENT)

    def test_product_html_request_text_uses_esc(self):
        """PRODUCT_HTML uses esc(d.request_text) in template."""
        self.assertIn("esc(d.request_text)", PRODUCT_HTML_CONTENT)

    def test_malicious_request_text_in_json_response_safe(self):
        """XSS payload in request_text is a JSON string; esc() handles it.

        The API correctly returns request_text as a JSON string value.
        The safety invariant is:
        1. The payload is inside a JSON string (not bare HTML in the response)
        2. The browser-side esc() renders it as text, not as HTML
        This test verifies (1): the payload appears as a JSON-encoded string,
        not as an executable HTML element outside JSON.
        """
        import tempfile
        tmpdir = tempfile.mkdtemp()
        hcls = _make_handler(tmpdir)
        payload = '<img src=x onerror=alert(1)>'
        with patch("integration.pipeline.compile_ir"):
            _, body = _make_request(
                hcls, "POST", "/api/product/create",
                body={"request_text": payload, "fixture_id": "c2-answer-bore24"}
            )
        d = _json_body(body)
        # API returns it as a plain string; esc() in JS handles rendering
        self.assertEqual(d["request_text"], payload)
        # The payload must be inside a JSON string value, not injected as
        # bare HTML outside the JSON body. We check that it appears as a
        # JSON-encoded string (with surrounding quotes), not as a raw tag.
        raw_json = body.decode("utf-8")
        # Must be inside a JSON string (quoted), not a bare HTML element
        self.assertIn('"request_text": "<img src=x onerror=alert(1)>"', raw_json,
                      "Payload must be inside JSON string quotes")
        # The response Content-Type is application/json (checked elsewhere),
        # so the browser will parse it as JSON, not as HTML. The esc() in
        # renderConfirmSection prevents it from being interpreted as HTML.

    def test_switch_run_no_stale_step_sha256(self):
        """After resetAll (new run), old step_sha256 must not persist.

        This is a source-code check: resetAll() clears result-area innerHTML,
        so any displayed hash from a prior run is wiped before the new run shows.
        """
        # Verify resetAll() clears result-area and step3
        self.assertIn("result-area", PRODUCT_HTML_CONTENT)
        self.assertIn("resetAll", PRODUCT_HTML_CONTENT)
        # resetAll sets innerHTML = '' for result-area
        idx_reset = PRODUCT_HTML_CONTENT.find("function resetAll")
        self.assertGreater(idx_reset, 0)
        reset_block_end = PRODUCT_HTML_CONTENT.find("}", idx_reset + 1)
        reset_block = PRODUCT_HTML_CONTENT[idx_reset:reset_block_end + 1]
        self.assertIn("result-area", reset_block)

    def test_step_sha256_inside_succeeded_block_not_in_failed_path(self):
        """step_sha256 is shown only in succeeded block, not globally."""
        idx_succeeded = PRODUCT_HTML_CONTENT.find("if (d.product_status === 'succeeded')")
        self.assertGreater(idx_succeeded, 0)
        # sha256 must appear after the succeeded check in the same function
        idx_sha = PRODUCT_HTML_CONTENT.find("step_sha256", idx_succeeded)
        self.assertGreater(idx_sha, idx_succeeded)
        # sha256 must NOT appear before the succeeded check in renderResultSection
        idx_render_result = PRODUCT_HTML_CONTENT.find("function renderResultSection")
        self.assertGreater(idx_render_result, 0)
        idx_sha_before = PRODUCT_HTML_CONTENT.find("step_sha256", idx_render_result)
        # It should not appear before the succeeded block within renderResultSection
        self.assertGreaterEqual(idx_sha_before, idx_succeeded,
                                "step_sha256 must only appear inside succeeded block")


if __name__ == "__main__":
    unittest.main()
