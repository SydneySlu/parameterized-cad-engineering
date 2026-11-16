"""Offline APP-004 authorization/service/HTTP tests; never call CAD or network."""

from __future__ import annotations

import http.client
import hashlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from demo.handler import DemoHandler
from demo.product_flow import ProductFlowHandler
from demo.server import APP004_LIVE_HTML_CONTENT, make_handler_class
from integration.app004_live_web_runner import (
    App004LiveWebService, authorize_app004_live_web_run, run_app004_offline_preflight,
)
from integration.product_live_runner import ProductLiveRunState, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION
from llm.app004_live_web_authorization import (
    APP004_BATCH_ID, APP004_CONDITION, APP004_CONTRACT_SHA256, APP004_INPUT_IDS, APP004_LABELS_SHA256,
    APP004_MAX_BATCH_HTTP, APP004_MODEL, APP004_PROFILE_ID, APP004_PROVIDER,
    APP004_INPUTS_SHA256, APP004_PROMPT_SHA256, APP004_SAMPLE_SET, App004ApprovalValidationError,
    App004LiveWebApproval, make_app004_test_approval, validate_app004_approval_binding,
)
from llm.contract import CONTRACT_VERSION, FORMAL_EVALUATION_ALLOWED, PROMPT_VERSION
from llm.transport import FakeTransport, TransportResponse


def _envelope(decision="answer", extracted=None, unsupported=None):
    extracted = extracted if extracted is not None else {"bore_d": 24}
    unsupported = unsupported or []
    data = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": decision,
        "extracted_parameters": extracted,
        "unsupported_requests": unsupported,
        "evidence": [{"field": k, "quote": str(v), "source": "user_input"} for k, v in extracted.items()],
        "missing_fields": [], "questions": [], "confidence": None,
    }
    return json.dumps(data, ensure_ascii=False)


def _http_server(service=None):
    demo = DemoHandler(output_root=Path(tempfile.mkdtemp()))
    product = ProductFlowHandler(output_root=Path(tempfile.mkdtemp()))
    handler = make_handler_class(demo, product, app004_live_service=service)
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1], thread


def _post(port, path, data):
    raw = json.dumps(data).encode()
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("POST", path, body=raw, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response.status, json.loads(body.decode())


def _owner_approval():
    return App004LiveWebApproval(
        batch_id=APP004_BATCH_ID,
        profile_id=APP004_PROFILE_ID,
        inputs_sha256=APP004_INPUTS_SHA256,
        evaluator_labels_sha256=APP004_LABELS_SHA256,
        prompt_sha256=APP004_PROMPT_SHA256,
        contract_sha256=APP004_CONTRACT_SHA256,
        provider=APP004_PROVIDER,
        model=APP004_MODEL,
        condition=APP004_CONDITION,
        max_batch_http=APP004_MAX_BATCH_HTTP,
        enable_cad_pipeline=True,
        approver="Wang sikai",
        approved_at_utc="2026-11-16T00:00:00Z",
        approval_statement="APP-004 test approval object",
    )


class _MaliciousString(str):
    def strip(self, *args, **kwargs):
        return "non-empty"

    def encode(self, *args, **kwargs):
        raise RuntimeError("string subclass encode must not run")


class TestApp004Authorization(unittest.TestCase):
    def test_profile_is_exact_and_global_gate_stays_closed(self):
        auth = authorize_app004_live_web_run()
        self.assertEqual(auth.profile_id, APP004_PROFILE_ID)
        self.assertEqual(auth.input_ids, APP004_INPUT_IDS)
        self.assertEqual(auth.max_batch_attempts, 4)
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_test_only_approval_rejected_before_preflight(self):
        auth = authorize_app004_live_web_run()
        with self.assertRaises(App004ApprovalValidationError):
            validate_app004_approval_binding(auth, make_app004_test_approval())

    def test_wrong_batch_approval_rejected(self):
        auth = authorize_app004_live_web_run()
        approval = make_app004_test_approval()
        object.__setattr__(approval, "batch_id", "wrong-batch")
        with self.assertRaises(App004ApprovalValidationError):
            validate_app004_approval_binding(auth, approval)

    def test_mutated_approval_scope_fields_rejected_before_preflight(self):
        auth = authorize_app004_live_web_run()
        fields = {
            "profile_id": "wrong-profile",
            "inputs_sha256": "0" * 64,
            "evaluator_labels_sha256": "1" * 64,
            "prompt_sha256": "2" * 64,
            "contract_sha256": "3" * 64,
            "provider": "wrong-provider",
            "model": "wrong-model",
            "condition": "C1",
            "max_batch_http": 5,
            "enable_cad_pipeline": False,
        }
        for field, value in fields.items():
            with self.subTest(field=field):
                approval = App004LiveWebApproval(
                    batch_id=APP004_BATCH_ID,
                    profile_id=APP004_PROFILE_ID,
                    inputs_sha256=APP004_INPUTS_SHA256,
                    evaluator_labels_sha256=APP004_LABELS_SHA256,
                    prompt_sha256=APP004_PROMPT_SHA256,
                    contract_sha256=APP004_CONTRACT_SHA256,
                    provider=APP004_PROVIDER,
                    model=APP004_MODEL,
                    condition=APP004_CONDITION,
                    max_batch_http=APP004_MAX_BATCH_HTTP,
                    enable_cad_pipeline=True,
                    approver="Wang sikai",
                    approved_at_utc="2026-11-16T00:00:00Z",
                    approval_statement="APP-004 test approval object",
                )
                object.__setattr__(approval, field, value)
                with patch("integration.app004_live_web_runner.run_app004_offline_preflight") as preflight, \
                     patch("integration.app004_live_web_runner.load_deepseek_environment") as load_env:
                    with self.assertRaises(App004ApprovalValidationError):
                        App004LiveWebService.prepare_formal(
                            authorization=auth, approval=approval
                        )
                preflight.assert_not_called()
                load_env.assert_not_called()

    def test_mutated_authorization_rejected_before_preflight(self):
        auth = authorize_app004_live_web_run()
        object.__setattr__(auth, "inputs_sha256", "0" * 64)
        approval = App004LiveWebApproval(
            batch_id=APP004_BATCH_ID,
            profile_id=APP004_PROFILE_ID,
            inputs_sha256=APP004_INPUTS_SHA256,
            evaluator_labels_sha256=APP004_LABELS_SHA256,
            prompt_sha256=APP004_PROMPT_SHA256,
            contract_sha256=APP004_CONTRACT_SHA256,
            provider=APP004_PROVIDER,
            model=APP004_MODEL,
            condition=APP004_CONDITION,
            max_batch_http=APP004_MAX_BATCH_HTTP,
            enable_cad_pipeline=True,
            approver="Wang sikai",
            approved_at_utc="2026-11-16T00:00:00Z",
            approval_statement="APP-004 test approval object",
        )
        with patch("integration.app004_live_web_runner.run_app004_offline_preflight") as preflight, \
             patch("integration.app004_live_web_runner.load_deepseek_environment") as load_env:
            with self.assertRaises(App004ApprovalValidationError):
                App004LiveWebService.prepare_formal(authorization=auth, approval=approval)
        preflight.assert_not_called()
        load_env.assert_not_called()

    def test_missing_approval_does_not_run_preflight_or_load_credentials(self):
        with patch("integration.app004_live_web_runner.run_app004_offline_preflight") as preflight, \
             patch("integration.app004_live_web_runner.load_deepseek_environment") as load_env:
            with self.assertRaises(App004ApprovalValidationError):
                App004LiveWebService.prepare_formal(
                    authorization=authorize_app004_live_web_run(), approval=None
                )
        preflight.assert_not_called()
        load_env.assert_not_called()

    def test_mutated_approval_free_fields_rejected_before_formal_side_effects(self):
        auth = authorize_app004_live_web_run()
        mutations = {
            "approval_record_ref": object(),
            "approver": object(),
            "approved_at_utc": object(),
            "approval_statement": object(),
            "approval_statement_subclass": _MaliciousString("approved"),
            "is_test_only": 0,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                approval = _owner_approval()
                target_field = (
                    "approval_statement"
                    if field == "approval_statement_subclass"
                    else field
                )
                object.__setattr__(approval, target_field, value)
                with patch(
                    "integration.app004_live_web_runner.run_app004_offline_preflight"
                ) as preflight, patch(
                    "integration.app004_live_web_runner.load_deepseek_environment"
                ) as load_env, patch.object(Path, "mkdir") as mkdir, patch(
                    "integration.app004_live_web_runner.BudgetLedger"
                ) as ledger:
                    with self.assertRaises(App004ApprovalValidationError):
                        App004LiveWebService.prepare_formal(
                            authorization=auth, approval=approval
                        )
                preflight.assert_not_called()
                load_env.assert_not_called()
                mkdir.assert_not_called()
                ledger.assert_not_called()


class TestApp004OfflineService(unittest.TestCase):
    def test_approval_audit_redacts_free_text_and_reference(self):
        from dataclasses import replace

        approval = replace(
            make_app004_test_approval(),
            is_test_only=False,
            approval_statement="SECRET_MARKER /Users/private/key.txt",
            approval_record_ref="/Users/private/approval-record.json",
        )
        audit = json.dumps(approval.as_audit_dict())
        self.assertNotIn("SECRET_MARKER", audit)
        self.assertNotIn("/Users/private", audit)
        self.assertIn("approval_statement_sha256", audit)
        self.assertIn("approval_record_ref_sha256", audit)

    def test_prompt_and_contract_hash_are_bound_in_authorization_and_approval(self):
        auth = authorize_app004_live_web_run()
        approval = make_app004_test_approval()
        self.assertEqual(auth.prompt_sha256, APP004_PROMPT_SHA256)
        self.assertEqual(auth.contract_sha256, APP004_CONTRACT_SHA256)
        self.assertEqual(approval.prompt_sha256, APP004_PROMPT_SHA256)
        self.assertEqual(approval.contract_sha256, APP004_CONTRACT_SHA256)
        self.assertIn("prompt_sha256", auth.scope_summary())
        self.assertIn("contract_sha256", auth.scope_summary())

    def test_offline_preflight_rejects_prompt_or_contract_hash_mismatch(self):
        auth = authorize_app004_live_web_run()
        for field in ("APP004_PROMPT_SHA256", "APP004_CONTRACT_SHA256"):
            with self.subTest(field=field), patch(
                f"integration.app004_live_web_runner.{field}", "0" * 64
            ):
                result = run_app004_offline_preflight(auth, require_cad_runtime=False)
                self.assertFalse(result["ok"])
                expected_error = "prompt_hash_mismatch" if "PROMPT" in field else "contract_hash_mismatch"
                self.assertIn(expected_error, result["errors"])

    def test_d01_answer_waits_for_confirmation(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        state = service.extract("D01-collar-bore24")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(state.extracted_parameters["bore_d"], 24)
        self.assertEqual(transport.call_count, 1)

    def test_d02_answer_is_hard_blocked_and_unconfirmable(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        state = service.extract("D02-collar-anodizing")
        self.assertEqual(state.product_status, "blocked")
        self.assertEqual(state.errors[0]["code"], "SCOPE_CAD_DENIED")
        self.assertIsNone(service.confirm(state.logical_run_id, True))
        self.assertEqual(transport.call_count, 1)

    def test_d02_ask_and_refuse_remain_blocked(self):
        for decision in ("ask", "refuse"):
            transport = FakeTransport()
            transport.queue_response(TransportResponse(status=200, body=_envelope(decision, {})))
            service = App004LiveWebService.from_fake_transport(transport)
            state = service.extract("D02-collar-anodizing")
            self.assertEqual(state.product_status, "blocked")
            self.assertIsNone(service.confirm(state.logical_run_id, True))

    def test_invalid_json_diagnostic_does_not_echo_provider_body(self):
        marker = "PRIVATE_PROVIDER_MARKER"
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body="{" + marker))
        state = App004LiveWebService.from_fake_transport(transport).extract("D01-collar-bore24")
        serialized = json.dumps(state.as_dict(), ensure_ascii=False)
        self.assertNotIn(marker, serialized)
        self.assertEqual(state.product_status, "blocked")

    def test_only_d01_confirmation_reaches_cad_confirmation_gate(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        state = service.extract("D01-collar-bore24")
        with patch("integration.app004_live_web_runner.confirm_product_live_run", return_value=state) as confirm:
            self.assertIs(service.confirm(state.logical_run_id, True), state)
        confirm.assert_called_once()
        self.assertEqual(confirm.call_args.kwargs["confirmed"], True)

    def test_arbitrary_input_rejected_without_transport_send(self):
        transport = FakeTransport()
        service = App004LiveWebService.from_fake_transport(transport)
        with self.assertRaisesRegex(RuntimeError, "APP004_INPUT_ID_NOT_ALLOWED"):
            service.extract("user-controlled-text")
        self.assertEqual(transport.call_count, 0)

    def test_duplicate_input_cannot_exceed_logical_budget(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        service.extract("D01-collar-bore24")
        with self.assertRaisesRegex(RuntimeError, "APP004_INPUT_ALREADY_USED"):
            service.extract("D01-collar-bore24")
        self.assertEqual(transport.call_count, 1)

    def test_offline_step_download_accepts_only_current_service_root(self):
        service = App004LiveWebService.from_fake_transport(FakeTransport())
        with tempfile.TemporaryDirectory() as tmp:
            service._pipeline_root = Path(tmp)
            run_dir = service._pipeline_root / APP004_INPUT_IDS[0] / "run-1"
            cad_dir = run_dir / "cad_output"
            cad_dir.mkdir(parents=True)
            step_path = cad_dir / "output.step"
            content = b"ISO-10303-21; APP004 OFFLINE TEST\n"
            step_path.write_bytes(content)
            state = ProductLiveRunState(
                logical_run_id="offline-run",
                input_id=APP004_INPUT_IDS[0],
                condition_id=APP004_CONDITION,
                provider=APP004_PROVIDER,
                model=APP004_MODEL,
                llm_status="answer",
                product_status="succeeded",
                decision="answer",
                extracted_parameters={"bore_d": 24},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[], pipeline_status="success",
                pipeline_run_dir=str(run_dir), step_path=str(step_path),
                ir_index={"step_sha256": hashlib.sha256(content).hexdigest()},
            )
            service._runs[state.logical_run_id] = state
            self.assertEqual(service.get_step_bytes_secure(state.logical_run_id), content)

            outside = Path(tmp).parent / (Path(tmp).name + "-outside.step")
            outside.write_bytes(content)
            try:
                escaped = ProductLiveRunState(
                    **{**state.__dict__, "step_path": str(outside)}
                )
                service._runs["outside"] = escaped
                self.assertIsNone(service.get_step_bytes_secure("outside"))
            finally:
                outside.unlink(missing_ok=True)

    def test_offline_step_download_rejects_symlink_leaf(self):
        service = App004LiveWebService.from_fake_transport(FakeTransport())
        with tempfile.TemporaryDirectory() as tmp:
            service._pipeline_root = Path(tmp)
            run_dir = service._pipeline_root / APP004_INPUT_IDS[0] / "run-1"
            cad_dir = run_dir / "cad_output"
            cad_dir.mkdir(parents=True)
            actual = cad_dir / "actual.step"
            actual.write_bytes(b"safe step")
            link = cad_dir / "output.step"
            try:
                link.symlink_to(actual)
            except OSError:
                self.skipTest("symlinks unavailable")
            state = ProductLiveRunState(
                logical_run_id="symlink-run",
                input_id=APP004_INPUT_IDS[0],
                condition_id=APP004_CONDITION,
                provider=APP004_PROVIDER,
                model=APP004_MODEL,
                llm_status="answer",
                product_status="succeeded",
                decision="answer",
                extracted_parameters={"bore_d": 24},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[], pipeline_status="success",
                pipeline_run_dir=str(run_dir), step_path=str(link),
                ir_index={"step_sha256": hashlib.sha256(b"safe step").hexdigest()},
            )
            service._runs[state.logical_run_id] = state
            self.assertIsNone(service.get_step_bytes_secure(state.logical_run_id))

    def test_clean_shutdown_marks_unrun_frozen_input_partial(self):
        service = App004LiveWebService.from_fake_transport(FakeTransport())
        service._summary = {
            "batch_status": "running",
            "runs": {"run-1": {"input_id": APP004_INPUT_IDS[0]}},
        }
        with patch.object(service, "_write_summary"):
            service.close()
        self.assertEqual(service._summary["batch_status"], "partial")

    def test_clean_shutdown_marks_both_frozen_inputs_complete(self):
        service = App004LiveWebService.from_fake_transport(FakeTransport())
        service._summary = {
            "batch_status": "running",
            "runs": {
                "run-1": {"input_id": APP004_INPUT_IDS[0]},
                "run-2": {"input_id": APP004_INPUT_IDS[1]},
            },
        }
        with patch.object(service, "_write_summary"):
            service.close()
        self.assertEqual(service._summary["batch_status"], "complete")


class TestApp004HTTP(unittest.TestCase):
    def test_disabled_by_default(self):
        server, port, thread = _http_server()
        try:
            status, data = _post(port, "/api/app004-live/create", {"input_id": APP004_INPUT_IDS[0]})
            self.assertEqual(status, 503)
            self.assertEqual(data["error"]["code"], "APP004_LIVE_DISABLED")
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_only_input_id_accepted_and_frozen_text_displayed(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        server, port, thread = _http_server(service)
        try:
            status, data = _post(port, "/api/app004-live/create", {
                "input_id": APP004_INPUT_IDS[0], "request_text": "replace the frozen prompt"
            })
            self.assertEqual(status, 400)
            status, data = _post(port, "/api/app004-live/create", {"input_id": APP004_INPUT_IDS[0]})
            self.assertEqual(status, 200)
            self.assertEqual(data["request_text"], "请按 GN 705 设计一个带轴孔轴环，轴孔孔径为 24 mm。")
            self.assertEqual(data["product_status"], "needs_confirmation")
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_d02_confirmation_route_is_denied(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        server, port, thread = _http_server(service)
        try:
            _, data = _post(port, "/api/app004-live/create", {"input_id": APP004_INPUT_IDS[1]})
            status, result = _post(port, f"/api/app004-live/confirm/{data['logical_run_id']}", {"confirmed": True})
            self.assertEqual(status, 403)
            self.assertEqual(result["error"]["code"], "APP004_CAD_CONFIRM_DENIED")
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_d01_confirmation_http_route_invokes_only_confirmation_gate(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = App004LiveWebService.from_fake_transport(transport)
        server, port, thread = _http_server(service)
        try:
            _, data = _post(port, "/api/app004-live/create", {"input_id": APP004_INPUT_IDS[0]})
            with patch("integration.app004_live_web_runner.confirm_product_live_run", return_value=service.get(data["logical_run_id"])) as confirm:
                status, result = _post(port, f"/api/app004-live/confirm/{data['logical_run_id']}", {"confirmed": True})
            self.assertEqual(status, 200)
            confirm.assert_called_once()
            self.assertIs(confirm.call_args.args[0], service.get(data["logical_run_id"]))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_confirmation_body_is_strict_and_html_escapes_model_fields(self):
        self.assertIn("function esc(s)", APP004_LIVE_HTML_CONTENT)
        self.assertIn("esc(d.request_text)", APP004_LIVE_HTML_CONTENT)
        transport = FakeTransport()
        service = App004LiveWebService.from_fake_transport(transport)
        server, port, thread = _http_server(service)
        try:
            status, data = _post(port, "/api/app004-live/confirm/some-id", {"confirmed": True, "patch": {}})
            self.assertEqual(status, 400)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
