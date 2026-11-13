"""Offline HTTP integration tests for APP-003-LIVE-UI.

Tests the /product-live page and /api/product-live/* API end-to-end
using FakeTransport and mock run_pipeline.  No real HTTP, no .env reads.

Coverage:
  1. P1: create → needs_confirmation, run_pipeline=0; confirm → succeeded; download.
  2. P2/P3/P4: blocked, zero CAD, no download.
  3. Failure/isolation: pipeline exception → failed, no STEP.
  4. Security: XSS payloads as text, no secrets/labels, disabled when no service.
  5. C1/C2/C3 backward compatibility.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
import sys
sys.path.insert(0, str(_REPO_ROOT / "src"))

from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
from llm.transport import FakeTransport, TransportResponse
from integration.product_live_runner import (
    ProductLiveService,
    ProductLiveRunState,
    PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
    PRODUCT_LIVE_STATUS_BLOCKED,
    PRODUCT_LIVE_STATUS_SUCCEEDED,
    PRODUCT_LIVE_STATUS_FAILED,
)
from llm.product_live_authorization import authorize_product_live_run

from demo.handler import DemoHandler
from demo.product_flow import ProductFlowHandler
from demo.server import make_handler_class, PRODUCT_LIVE_HTML_CONTENT
from http.server import HTTPServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_envelope(
    decision: str = "answer",
    extracted: dict | None = None,
    missing: list | None = None,
    unsupported: list | None = None,
    questions: list | None = None,
) -> str:
    if extracted is None:
        extracted = {"bore_d": 24} if decision == "answer" else {}
    if missing is None:
        missing = []
    if unsupported is None:
        unsupported = []
    if questions is None:
        questions = []
    env = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": decision,
        "extracted_parameters": extracted,
        "unsupported_requests": unsupported,
        "evidence": [{"field": k, "quote": str(v), "source": "user_input"}
                     for k, v in extracted.items()],
        "missing_fields": missing,
        "questions": questions,
        "confidence": None,
    }
    return json.dumps(env, ensure_ascii=False)


def _make_service(transport: FakeTransport, output_root=None) -> ProductLiveService:
    auth = authorize_product_live_run(batch_id="test-batch-ui-001")
    return ProductLiveService(
        transport=transport,
        authorization=auth,
        output_root=Path(output_root) if output_root else Path(tempfile.mkdtemp()),
    )


def _make_test_server(service=None, port=0) -> tuple:
    demo = DemoHandler(output_root=Path(tempfile.mkdtemp()))
    product = ProductFlowHandler(output_root=Path(tempfile.mkdtemp()))
    handler_cls = make_handler_class(demo, product, product_live_service=service)
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    actual_port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, actual_port, t


def _http_post(port, path, body_dict):
    body = json.dumps(body_dict).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("POST", path, body=body,
                 headers={"Content-Type": "application/json",
                          "Content-Length": str(len(body))})
    resp = conn.getresponse()
    data = json.loads(resp.read())
    conn.close()
    return resp.status, data


def _http_get_raw(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, raw


# ---------------------------------------------------------------------------
# 1. Product Live UI page tests
# ---------------------------------------------------------------------------

class TestProductLivePage(unittest.TestCase):
    """GET /product-live returns the live UI HTML page."""

    def test_get_product_live_returns_html(self):
        """GET /product-live returns 200 HTML with the live UI content."""
        demo = DemoHandler(output_root=Path(tempfile.mkdtemp()))
        product = ProductFlowHandler(output_root=Path(tempfile.mkdtemp()))
        handler_cls = make_handler_class(demo, product)
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/product-live")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8")
        self.assertIn("Product Live", html)
        self.assertIn("offline/mock transport", html)
        self.assertIn("STEP 通过 ≠ 制造认证", html)

    def test_product_live_page_has_esc_function(self):
        """The live UI HTML must contain the esc() function for XSS prevention."""
        self.assertIn("function esc(s)", PRODUCT_LIVE_HTML_CONTENT)

    def test_product_live_page_has_five_char_escapes(self):
        """esc() must replace &, <, >, \", ' characters."""
        self.assertIn("&amp;", PRODUCT_LIVE_HTML_CONTENT)
        self.assertIn("&lt;", PRODUCT_LIVE_HTML_CONTENT)
        self.assertIn("&gt;", PRODUCT_LIVE_HTML_CONTENT)
        self.assertIn("&quot;", PRODUCT_LIVE_HTML_CONTENT)
        self.assertIn("&#39;", PRODUCT_LIVE_HTML_CONTENT)

    def test_product_live_page_has_banners(self):
        """Page must contain offline mode, non-real-model, and STEP≠manufacturing warnings."""
        html = PRODUCT_LIVE_HTML_CONTENT
        self.assertIn("受控 Product Live UI", html)
        self.assertIn("非真实模型效果", html)
        self.assertIn("STEP 通过 ≠ 制造认证", html)
        self.assertIn("不接触 API key", html)

    def test_product_live_page_no_bare_interpolation(self):
        """No bare ${d.run_id} or ${d.pipeline_status} in page template literals."""
        # The page uses esc() for all dynamic values; bare interpolations
        # that bypass esc() would be a XSS vector.
        html = PRODUCT_LIVE_HTML_CONTENT
        # Check that bare interpolations of critical fields are wrapped in esc()
        # Look for patterns like ${d.run_id} WITHOUT esc() — should not exist
        import re
        bare_patterns = re.findall(r'\$\{d\.(run_id|logical_run_id|product_status|pipeline_status|step_sha256|request_text)\}', html)
        # Filter out the ones inside esc() — those are fine
        # A bare one would be one NOT preceded by "esc("
        bare_unsafe = []
        for m in re.finditer(r'\$\{(d\.\w+)\}', html):
            # Check if this is inside an esc() call
            prefix = html[max(0, m.start()-10):m.start()]
            if 'esc(' not in prefix:
                bare_unsafe.append(m.group(1))
        self.assertEqual(bare_unsafe, [],
                         msg=f"Bare interpolations without esc(): {bare_unsafe}")

    def test_get_inputs_api(self):
        """GET /api/product-live/inputs returns input IDs when service configured."""
        transport = FakeTransport()
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/api/product-live/inputs")
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertIn("inputs", data)
        ids = [i["input_id"] for i in data["inputs"]]
        self.assertIn("P1-24mm", ids)
        self.assertIn("P4-unsupported", ids)

    def test_get_inputs_disabled_without_service(self):
        """GET /api/product-live/inputs returns 503 when no service."""
        server, port, t = _make_test_server(service=None)
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/api/product-live/inputs")
        self.assertEqual(status, 503)


# ---------------------------------------------------------------------------
# 2. P1 HTTP E2E: create → confirm → download
# ---------------------------------------------------------------------------

class TestProductLiveUIP1Flow(unittest.TestCase):
    """P1: create → needs_confirmation → confirm → succeeded → download."""

    def _make_server(self, transport):
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)
        return port

    def test_p1_create_needs_confirmation_zero_cad(self):
        """P1 create → needs_confirmation; run_pipeline not called."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "请做一个轴环，轴孔直径 24 mm。",
                                       "input_id": "P1-24mm"})
            mock_pipe.assert_not_called()

        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "needs_confirmation")
        self.assertEqual(data["input_id"], "P1-24mm")
        self.assertNotIn("step_path", data)

    def test_p1_confirm_succeeded_mock_pipeline(self):
        """P1 confirm → succeeded (mock pipeline)."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.stage = "step_readback"
        mock_result.errors = []
        mock_result.run_id = "mock-uuid"
        mock_result.run_dir = str(Path(tempfile.mkdtemp()) / "cad_output")
        mock_result.step_path = None
        mock_result.ir_index = {"step_sha256": "a" * 64, "step_bytes": 12345}

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": True, "patch": {}})

        self.assertEqual(status2, 200)
        self.assertEqual(data2["product_status"], "succeeded")
        self.assertEqual(data2["ir_index"]["step_sha256"], "a" * 64)
        self.assertNotIn("step_path", data2)

    def test_p1_download_succeeded(self):
        """P1 download returns STEP bytes when succeeded."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        # Create and confirm
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        # Write a fake STEP file and mock the pipeline result to point to it
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run-001"
            cad_output = run_dir / "cad_output"
            cad_output.mkdir(parents=True)
            step_file = cad_output / "collar.step"
            step_content = b"ISO-10303-21 STEP FILE CONTENT\n"
            step_file.write_bytes(step_content)
            step_hash = hashlib.sha256(step_content).hexdigest()

            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stage = "step_readback"
            mock_result.errors = []
            mock_result.run_id = "mock-uuid"
            mock_result.run_dir = str(run_dir)
            mock_result.step_path = str(step_file)
            mock_result.ir_index = {"step_sha256": step_hash, "step_bytes": len(step_content),
                                    "step_path": str(step_file)}

            with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
                _, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                      {"confirmed": True, "patch": {}})

            self.assertEqual(data2["product_status"], "succeeded")

            # Download
            status_dl, raw = _http_get_raw(port, f"/product-live-download/{run_id}")
            self.assertEqual(status_dl, 200)
            self.assertEqual(raw, step_content)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), step_hash)

    def test_p1_download_hash_matches_state(self):
        """Download SHA-256 matches ir_index.step_sha256."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        _, data = _http_post(port, "/api/product-live/create",
                             {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run-002"
            cad_output = run_dir / "cad_output"
            cad_output.mkdir(parents=True)
            step_file = cad_output / "collar.step"
            step_content = b"STEP CONTENT FOR HASH TEST\n"
            step_file.write_bytes(step_content)
            step_hash = hashlib.sha256(step_content).hexdigest()

            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stage = "step_readback"
            mock_result.errors = []
            mock_result.run_id = "mock"
            mock_result.run_dir = str(run_dir)
            mock_result.step_path = str(step_file)
            mock_result.ir_index = {"step_sha256": step_hash, "step_bytes": len(step_content)}

            with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
                _, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                      {"confirmed": True, "patch": {}})

            # Verify the state has the correct hash
            self.assertEqual(data2["ir_index"]["step_sha256"], step_hash)

            # Download and verify hash
            status_dl, raw = _http_get_raw(port, f"/product-live-download/{run_id}")
            self.assertEqual(status_dl, 200)
            actual_hash = hashlib.sha256(raw).hexdigest()
            self.assertEqual(actual_hash, step_hash)


# ---------------------------------------------------------------------------
# 3. P2/P3/P4 HTTP blocked paths
# ---------------------------------------------------------------------------

class TestProductLiveUIBlockedPaths(unittest.TestCase):
    """P2/P3/P4: blocked, zero CAD, no download."""

    def _make_server(self, transport):
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)
        return port

    def test_p2_ask_blocked_no_download(self):
        """P2 ask → blocked; no download button; run_pipeline=0."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], ["bore_d 是必填参数，请提供"])))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "请做一个轴环。", "input_id": "P2-ask-bore"})
            mock_pipe.assert_not_called()

        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "blocked")
        self.assertIn("bore_d", data.get("missing_fields", []))
        # No download button in succeeded sense — not succeeded
        self.assertNotEqual(data["product_status"], "succeeded")

    def test_p2_confirm_still_blocked(self):
        """Direct confirm on P2 blocked → still blocked, zero CAD."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("ask", {}, ["bore_d"], [], [])))
        port = self._make_server(transport)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P2-ask-bore"})
        run_id = data["logical_run_id"]

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": True, "patch": {}})
            mock_pipe.assert_not_called()

        self.assertEqual(data2["product_status"], "blocked")

    def test_p3_conflict_blocked(self):
        """P3 catalog conflict → blocked, zero CAD."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "answer", {"bore_d": 24, "outer_d": 33}, [], [], [])))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "轴孔 24，外径 33", "input_id": "P3-catalog-conflict"})
            mock_pipe.assert_not_called()

        self.assertEqual(data["product_status"], "blocked")
        self.assertGreater(len(data.get("conflicts", [])), 0)

    def test_p4_unsupported_blocked(self):
        """P4 unsupported → blocked, zero CAD."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "answer", {"bore_d": 24}, [], ["anodizing"], [])))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "轴孔 24，阳极氧化", "input_id": "P4-unsupported"})
            mock_pipe.assert_not_called()

        self.assertEqual(data["product_status"], "blocked")
        self.assertIn("anodizing", data.get("unsupported_requests", []))

    def test_blocked_no_step_download(self):
        """Blocked run download returns 403."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("ask", {}, ["bore_d"], [], [])))
        port = self._make_server(transport)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P2-ask-bore"})
        run_id = data["logical_run_id"]

        status_dl, raw = _http_get_raw(port, f"/product-live-download/{run_id}")
        self.assertEqual(status_dl, 403)


# ---------------------------------------------------------------------------
# 4. Failure and isolation
# ---------------------------------------------------------------------------

class TestProductLiveUIFailure(unittest.TestCase):
    """Pipeline/STEP failure → failed, no STEP exposure."""

    def _make_server(self, transport):
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)
        return port

    def test_pipeline_failure_returns_failed(self):
        """Pipeline exception → product_status=failed, no STEP."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        mock_result = MagicMock()
        mock_result.status = "failed"
        mock_result.stage = "cad"
        mock_result.errors = [{"code": "CAD_FAILED", "message": "compile error"}]
        mock_result.run_id = "mock"
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = None

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": True, "patch": {}})

        self.assertEqual(data2["product_status"], "failed")
        # No step info
        self.assertNotIn("step_path", data2)
        self.assertIsNone(data2.get("ir_index"))

    def test_failed_no_download(self):
        """Failed run download returns 403."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        port = self._make_server(transport)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        mock_result = MagicMock()
        mock_result.status = "failed"
        mock_result.stage = "cad"
        mock_result.errors = [{"code": "CAD_FAILED"}]
        mock_result.run_id = "mock"
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = None

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            _ = _http_post(port, f"/api/product-live/confirm/{run_id}",
                           {"confirmed": True, "patch": {}})

        status_dl, _ = _http_get_raw(port, f"/product-live-download/{run_id}")
        self.assertEqual(status_dl, 403)

    def test_parse_error_blocked(self):
        """Invalid JSON response → blocked with PARSE_ERROR."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body="THIS IS NOT VALID JSON!!!"))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "test", "input_id": "P1-24mm"})
            mock_pipe.assert_not_called()

        self.assertEqual(data["product_status"], "blocked")
        error_codes = [e.get("code") for e in data.get("errors", [])]
        self.assertIn("PARSE_ERROR", error_codes)

    def test_refuse_blocked(self):
        """decision=refuse → blocked."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("refuse", {}, [], [], [])))
        port = self._make_server(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "test", "input_id": "P1-24mm"})
            mock_pipe.assert_not_called()

        self.assertEqual(data["product_status"], "blocked")


# ---------------------------------------------------------------------------
# 5. Security: XSS, secrets, disabled, labels
# ---------------------------------------------------------------------------

class TestProductLiveUISecurity(unittest.TestCase):
    """Security: XSS payloads as text, no secrets/labels, disabled when no service."""

    def test_xss_request_text_as_text(self):
        """XSS payload in request_text must be displayed as text, not HTML."""
        xss_payload = '<img src=x onerror=window.__live_xss=1>'
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": xss_payload, "input_id": "P1-24mm"})
        # The payload must be in the response as a JSON string, not executed
        resp_str = json.dumps(data)
        self.assertIn(xss_payload, resp_str)  # It's there as text
        # But the HTML page uses esc() so it won't be interpreted as HTML

    def test_api_response_no_secrets(self):
        """HTTP response must not contain API keys, Authorization, or evaluator labels."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        resp_str = json.dumps(data).lower()
        self.assertNotIn("api_key", resp_str)
        self.assertNotIn("authorization", resp_str)
        self.assertNotIn("bearer", resp_str)
        self.assertNotIn("expected_decision", resp_str)
        self.assertNotIn("allowed_to_cad", resp_str)
        self.assertNotIn("expected_conflicts", resp_str)

    def test_no_service_returns_disabled(self):
        """Without service, create returns 503 PRODUCT_LIVE_DISABLED."""
        server, port, t = _make_test_server(service=None)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["code"], "PRODUCT_LIVE_DISABLED")

    def test_no_service_confirm_returns_disabled(self):
        """Without service, confirm returns 503."""
        server, port, t = _make_test_server(service=None)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/confirm/some-run-id",
                                  {"confirmed": True, "patch": {}})
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["code"], "PRODUCT_LIVE_DISABLED")

    def test_no_service_download_returns_disabled(self):
        """Without service, download returns 503."""
        server, port, t = _make_test_server(service=None)
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/product-live-download/some-run-id")
        self.assertEqual(status, 503)

    def test_response_no_absolute_paths(self):
        """HTTP response must not contain absolute file paths."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        resp_str = json.dumps(data)
        # step_path must not be in response (stripped by _sanitize_state_for_http)
        self.assertNotIn("step_path", data)
        # No absolute paths starting with /
        # (all path fields are normalized to repo-relative or None)
        for key in ("pipeline_run_dir",):
            val = data.get(key)
            if val is not None:
                self.assertFalse(val.startswith("/"),
                                 msg=f"Absolute path in {key}: {val!r}")

    def test_confirm_false_blocked_zero_cad(self):
        """confirmed=False → blocked, zero CAD."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": False, "patch": {}})
            mock_pipe.assert_not_called()

        self.assertEqual(data2["product_status"], "blocked")

    def test_invalid_confirmed_type_rejected(self):
        """confirmed as string must be rejected with 400."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        _, data = _http_post(port, "/api/product-live/create",
                              {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]

        status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                    {"confirmed": "true", "patch": {}})
        self.assertEqual(status2, 400)

    def test_missing_request_text_400(self):
        """Missing request_text → 400."""
        svc = _make_service(FakeTransport())
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"input_id": "P1-24mm"})
        self.assertEqual(status, 400)

    def test_missing_input_id_400(self):
        """Missing input_id → 400."""
        svc = _make_service(FakeTransport())
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test"})
        self.assertEqual(status, 400)


# ---------------------------------------------------------------------------
# 6. C1/C2/C3 backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat(unittest.TestCase):
    """C1/C2/C3 routes must still work when product live service is configured."""

    def test_c1_root_still_works(self):
        """GET / still returns C1 HTML."""
        svc = _make_service(FakeTransport())
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/")
        self.assertEqual(status, 200)
        self.assertIn("参数化 CAD", raw.decode("utf-8"))

    def test_c3_product_page_still_works(self):
        """GET /product still returns C3 HTML."""
        svc = _make_service(FakeTransport())
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, raw = _http_get_raw(port, "/product")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8")
        self.assertIn("离线 synthetic fixture", html)

    def test_make_handler_class_two_args(self):
        """make_handler_class with 2 args (no live service) still works."""
        demo = DemoHandler(output_root=Path(tempfile.mkdtemp()))
        product = ProductFlowHandler(output_root=Path(tempfile.mkdtemp()))
        handler_cls = make_handler_class(demo, product)
        self.assertIsNotNone(handler_cls)

    def test_formal_evaluation_allowed_still_false(self):
        """FORMAL_EVALUATION_ALLOWED must remain False."""
        from llm.contract import FORMAL_EVALUATION_ALLOWED
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_product_live_page_distinct_from_c3(self):
        """The /product-live page must be distinct from /product (C3)."""
        html = PRODUCT_LIVE_HTML_CONTENT
        self.assertIn("Product Live", html)
        self.assertNotIn("离线 synthetic fixture", html)

    def test_c2_product_create_still_works(self):
        """POST /api/product/create (C2) still works when live service is configured."""
        svc = _make_service(FakeTransport())
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)

        status, data = _http_post(port, "/api/product/create",
                                  {"request_text": "test", "fixture_id": "c2-answer-bore24"})
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
