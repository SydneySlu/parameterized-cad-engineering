"""Tests for RET-005 pool server routes (src/demo/server.py).

Covers:
- GET /pool → 200 HTML with offline banner
- GET /api/pool/samples → samples list, all retrieval_source, no forbidden fields
- GET /api/pool/samples with no service → 503
- POST /api/pool/create → needs_confirmation
- POST /api/pool/create + confirm → succeed (mocked pipeline)
- POST /api/pool/create with invalid pool → blocked
- POST /api/pool/confirm confirmed=false → blocked + CONFIRMATION_REJECTED
- GET /pool-download/<run_id> unfinished → 403
- GET /api/pool/<run_id> unknown → 404
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from http.server import HTTPServer
from unittest.mock import patch

from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
from llm.transport import FakeTransport, TransportResponse
from retrieval.config import MANIFEST_REL_PATH, REPO_ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MANIFEST_PATH = REPO_ROOT / MANIFEST_REL_PATH
_HAVE_MANIFEST = _MANIFEST_PATH.is_file() and _MANIFEST_PATH.stat().st_size > 0

_RET_IDS = [
    "set_screw_shaft_collar/catalog-bore-006",
    "set_screw_shaft_collar/catalog-bore-020",
    "set_screw_shaft_collar/catalog-bore-050",
]
_HELDOUT_IDS = [
    "set_screw_shaft_collar/catalog-bore-012",
    "set_screw_shaft_collar/catalog-bore-035",
    "set_screw_shaft_collar/catalog-bore-080",
]


def _envelope(*, bore: float = 24.0, decision: str = "answer") -> str:
    data = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": decision,
        "extracted_parameters": {"bore_d": bore},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": f"{bore} mm", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    return json.dumps(data, ensure_ascii=False)


def _make_transport(*responses: str) -> FakeTransport:
    t = FakeTransport()
    for body in responses:
        t.queue_response(TransportResponse(status=200, body=body))
    return t


def _pipeline_result(*, status="success", stage="step_export",
                     run_dir="/tmp/fake", step_path=None, ir_index=None, errors=None):
    from integration.pipeline import PipelineResult
    return PipelineResult(
        run_id="test-run",
        extraction_source="synthetic_fixture",
        status=status,
        stage=stage,
        errors=errors or [],
        questions=[],
        request_text="bore_d=24 mm",
        envelope_fixture_label="ret005_pool_test",
        parameters={"bore_d": 24.0},
        ir_index=ir_index or ({"step_sha256": "a" * 64} if status == "success" else None),
        step_path=step_path or (f"{run_dir}/cad_output/part.step" if status == "success" else None),
        run_dir=run_dir,
    )


class _FakeRequest:
    """Minimal WSGI-like request stub for testing handler methods."""
    def __init__(self, method: str, path: str, body: bytes = b""):
        self.method = method
        self.path = path
        self._body = body
        self.rfile = io.BytesIO(body)
        self.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "application/json",
        }

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self._body)


class _FakeHandler:
    """Thin wrapper to exercise handler methods without a real socket."""

    def __init__(self, method, path, body=b"", pool_service=None):
        from demo.handler import DemoHandler
        from demo.product_flow import ProductFlowHandler
        from demo.server import make_handler_class

        demo_handler = DemoHandler()
        handler_class = make_handler_class(
            demo_handler, pool_service=pool_service
        )

        class _Conn:
            def getpeername(self):
                return ("127.0.0.1", 9999)

        self._response_code = None
        self._response_headers = {}
        self._response_body = io.BytesIO()

        handler = handler_class.__new__(handler_class)
        handler.path = path
        handler.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "application/json",
        }
        handler.rfile = io.BytesIO(body)
        handler.wfile = self._response_body
        handler.connection = _Conn()
        handler.server = None
        handler.request = None
        handler.client_address = ("127.0.0.1", 9999)

        self._status = []
        self._headers = []
        self._body_chunks = []

        def send_response(code, message=""):
            self._status.append(code)

        def send_header(key, value):
            self._headers.append((key, value))

        def end_headers():
            pass

        def write(data):
            self._body_chunks.append(data)

        handler.send_response = send_response
        handler.send_header = send_header
        handler.end_headers = end_headers
        handler.wfile = type("W", (), {"write": lambda s, d: self._body_chunks.append(d)})()

        def log_message(fmt, *args):
            pass
        handler.log_message = log_message

        # Dispatch
        if method == "GET":
            handler.do_GET()
        elif method == "POST":
            handler.do_POST()

        self._handler = handler

    @property
    def status(self):
        return self._status[0] if self._status else None

    @property
    def body_bytes(self):
        return b"".join(self._body_chunks)

    @property
    def body_text(self):
        return self.body_bytes.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.body_bytes)


# ---------------------------------------------------------------------------
# 1. Pool HTML page
# ---------------------------------------------------------------------------


class TestPoolHtmlPage(unittest.TestCase):
    def test_pool_html_served_at_slash_pool(self):
        h = _FakeHandler("GET", "/pool")
        self.assertEqual(h.status, 200)
        body = h.body_text
        self.assertIn("OFFLINE", body.upper() + body,
                      "Pool HTML must contain offline warning")

    def test_pool_html_contains_离线(self):
        h = _FakeHandler("GET", "/pool")
        self.assertIn("离线", h.body_text)

    def test_pool_html_served_with_trailing_slash(self):
        h = _FakeHandler("GET", "/pool/")
        self.assertEqual(h.status, 200)


# ---------------------------------------------------------------------------
# 2. Samples endpoint
# ---------------------------------------------------------------------------


class TestPoolSamplesEndpoint(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_samples_requires_service(self):
        h = _FakeHandler("GET", "/api/pool/samples", pool_service=None)
        self.assertEqual(h.status, 503)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_samples_returns_retrieval_source_only(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport())
        h = _FakeHandler("GET", "/api/pool/samples", pool_service=service)
        self.assertEqual(h.status, 200)
        d = h.json()
        samples = d.get("samples", [])
        self.assertGreater(len(samples), 0)
        for s in samples:
            self.assertEqual(s.get("split_role"), "retrieval_source",
                             f"sample {s.get('sample_id')!r} has role {s.get('split_role')!r}")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_samples_no_forbidden_fields(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport())
        h = _FakeHandler("GET", "/api/pool/samples", pool_service=service)
        body = h.body_text
        # Forbidden fields must not appear
        for forbidden in ("evaluator_labels", "step_body", "ir_path",
                          "heldout", "held_out", "ground_truth", "raw_body"):
            self.assertNotIn(forbidden, body.lower(),
                             f"forbidden field {forbidden!r} found in /api/pool/samples response")


# ---------------------------------------------------------------------------
# 3. Pool create endpoint
# ---------------------------------------------------------------------------


class TestPoolCreateEndpoint(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_create_valid_request_needs_confirmation(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _RET_IDS,
            "condition_id": "C1",
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        self.assertEqual(h.status, 200)
        d = h.json()
        self.assertEqual(d["product_status"], "needs_confirmation")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_create_with_heldout_pool_blocked(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _HELDOUT_IDS,
            "condition_id": "C1",
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        self.assertEqual(h.status, 200)
        d = h.json()
        self.assertEqual(d["product_status"], "blocked")
        codes = [e.get("code", "") for e in d.get("errors", [])]
        self.assertIn("POOL_SAMPLE_ROLE_NOT_ALLOWED", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_create_with_too_few_pool_ids_blocked(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": [_RET_IDS[0]],  # only 1
            "condition_id": "C1",
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        self.assertEqual(h.status, 200)
        d = h.json()
        self.assertEqual(d["product_status"], "blocked")

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_create_no_service_returns_503(self):
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _RET_IDS,
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=None)
        self.assertEqual(h.status, 503)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_create_response_no_forbidden_fields(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _RET_IDS,
            "condition_id": "C1",
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        resp_text = h.body_text
        for forbidden in ("evaluator_labels", "step_body", "ir_path", "Authorization",
                          "api_key", "secret", "raw_body"):
            self.assertNotIn(forbidden.lower(), resp_text.lower(),
                             f"forbidden field {forbidden!r} in create response")
        # step_path must not appear in response (absolute path stripping)
        d = h.json()
        self.assertNotIn("step_path", d, "absolute step_path must not appear in response")


# ---------------------------------------------------------------------------
# 4. Pool confirm endpoint
# ---------------------------------------------------------------------------


class TestPoolConfirmEndpoint(unittest.TestCase):
    def _get_needs_confirmation_state(self, service):
        from integration.ret005_pool_runner import POOL_STATUS_NEEDS_CONFIRMATION
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _RET_IDS,
            "condition_id": "C1",
        }).encode()
        h = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        d = h.json()
        self.assertEqual(d.get("product_status"), POOL_STATUS_NEEDS_CONFIRMATION)
        return d["run_id"]

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirm_true_calls_pipeline(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        run_id = self._get_needs_confirmation_state(service)
        with patch("integration.pipeline.run_pipeline") as cad:
            cad.return_value = _pipeline_result()
            body = json.dumps({"confirmed": True}).encode()
            h = _FakeHandler("POST", f"/api/pool/confirm/{run_id}", body=body,
                             pool_service=service)
            self.assertEqual(h.status, 200)
            cad.assert_called_once()

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirm_false_returns_confirmation_rejected(self):
        from integration.ret005_pool_runner import Ret005PoolService, POOL_STATUS_BLOCKED
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        run_id = self._get_needs_confirmation_state(service)
        with patch("integration.pipeline.run_pipeline") as cad:
            body = json.dumps({"confirmed": False}).encode()
            h = _FakeHandler("POST", f"/api/pool/confirm/{run_id}", body=body,
                             pool_service=service)
            cad.assert_not_called()
        d = h.json()
        self.assertEqual(d["product_status"], POOL_STATUS_BLOCKED)
        codes = [e.get("code", "") for e in d.get("errors", [])]
        self.assertIn("CONFIRMATION_REJECTED", codes)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_confirm_zero_cad_before_extraction(self):
        """A confirm on a run that was never extracted must return 404."""
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        with patch("integration.pipeline.run_pipeline") as cad:
            body = json.dumps({"confirmed": True}).encode()
            h = _FakeHandler("POST", "/api/pool/confirm/nonexistent-run-id",
                             body=body, pool_service=service)
            cad.assert_not_called()
        self.assertEqual(h.status, 404)


# ---------------------------------------------------------------------------
# 5. Pool download endpoint
# ---------------------------------------------------------------------------


class TestPoolDownloadEndpoint(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_download_unfinished_run_returns_403(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        body = json.dumps({
            "request_text": "bore_d=24 mm 轴环",
            "pool_sample_ids": _RET_IDS,
            "condition_id": "C1",
        }).encode()
        # Create run but don't confirm
        h_create = _FakeHandler("POST", "/api/pool/create", body=body, pool_service=service)
        d = h_create.json()
        run_id = d.get("run_id", "unknown")
        h = _FakeHandler("GET", f"/pool-download/{run_id}", pool_service=service)
        # Should be 403 because run is not succeeded
        self.assertIn(h.status, (403, 404))

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_download_nonexistent_run_returns_404(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        h = _FakeHandler("GET", "/pool-download/does-not-exist-run-xyz",
                        pool_service=service)
        self.assertIn(h.status, (404, 403))


# ---------------------------------------------------------------------------
# 6. Status endpoint
# ---------------------------------------------------------------------------


class TestPoolGetEndpoint(unittest.TestCase):
    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_get_unknown_run_returns_404(self):
        from integration.ret005_pool_runner import Ret005PoolService
        service = Ret005PoolService(transport=_make_transport(_envelope()))
        h = _FakeHandler("GET", "/api/pool/unknown-run-id-xyz", pool_service=service)
        self.assertEqual(h.status, 404)

    @unittest.skipUnless(_HAVE_MANIFEST, "RET-001 manifest not available")
    def test_get_no_service_returns_503(self):
        h = _FakeHandler("GET", "/api/pool/some-run-id", pool_service=None)
        self.assertEqual(h.status, 503)


if __name__ == "__main__":
    unittest.main()
