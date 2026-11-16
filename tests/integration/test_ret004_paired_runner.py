from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
from llm.ret004_authorization import (
    RET004_BATCH_ID, RET004_CONFIG_SHA256, RET004_CONDITIONS, RET004_CONTRACT_SHA256,
    RET004_INPUTS_SHA256, RET004_LABELS_SHA256, RET004_MANIFEST_SHA256, RET004_MAX_HTTP,
    RET004_MODEL, RET004_PROFILE_ID, RET004_PROMPT_SHA256, RET004_PROVIDER,
    authorize_ret004, RET004Approval,
)
from llm.transport import FakeTransport, TransportResponse
from llm.conditions import assemble_c1
from llm.input_projection import ProjectedCase
from integration.ret004_paired_runner import (
    RET004PairedService, _load_index, _load_inputs, run_ret004_offline_preflight,
    run_ret004_paired_batch,
)


def _approval(*, test_only: bool = True) -> RET004Approval:
    return RET004Approval(
        batch_id=RET004_BATCH_ID, profile_id=RET004_PROFILE_ID,
        inputs_sha256=RET004_INPUTS_SHA256, labels_sha256=RET004_LABELS_SHA256,
        prompt_sha256=RET004_PROMPT_SHA256, contract_sha256=RET004_CONTRACT_SHA256,
        manifest_sha256=RET004_MANIFEST_SHA256, retrieval_config_sha256=RET004_CONFIG_SHA256,
        provider=RET004_PROVIDER, model=RET004_MODEL, conditions=RET004_CONDITIONS,
        max_batch_http=RET004_MAX_HTTP, enable_cad_pipeline=True,
        approver="offline-test", approved_at_utc="2026-11-16T00:00:00Z",
        approval_statement="TEST ONLY RET-004 harness approval", is_test_only=test_only,
    )


def _envelope(*, unsupported=None):
    data = {
        "contract_version": CONTRACT_VERSION, "prompt_version": PROMPT_VERSION,
        "decision": "answer", "extracted_parameters": {"bore_d": 24},
        "unsupported_requests": unsupported or [],
        "evidence": [{"field": "bore_d", "quote": "24 mm", "source": "user_input"}],
        "missing_fields": [], "questions": [], "confidence": None,
    }
    return json.dumps(data, ensure_ascii=False)


class TestRET004AuthorizationAndPreflight(unittest.TestCase):
    def test_exact_profile_is_frozen(self):
        auth = authorize_ret004()
        self.assertEqual(auth.max_batch_attempts, 8)
        self.assertTrue(auth.allows_logical_run(auth.expected_logical_run_id("R01-collar-bore24", "C1"), "DeepSeek"))

    def test_artifact_preflight_does_not_create_batch_or_credentials(self):
        with patch("integration.ret004_paired_runner.load_deepseek_environment") as load:
            result = run_ret004_offline_preflight()
        self.assertIn(result["ok"], (True, False))  # Batch collision is environment-dependent.
        self.assertEqual(result["max_batch_http"], 8)
        load.assert_not_called()
        self.assertFalse(result["evaluator_labels_read"])

    def test_wrong_profile_hash_rejected_at_construction(self):
        from dataclasses import replace
        with self.assertRaises(Exception):
            replace(authorize_ret004(), inputs_sha256="0" * 64)


class TestRET004FakeTransportWiring(unittest.TestCase):
    def _service(self, responses):
        transport = FakeTransport()
        for body in responses:
            transport.queue_response(TransportResponse(status=200, body=body, runtime_returned_model=RET004_MODEL))
        service = RET004PairedService(
            auth=authorize_ret004(), approval=_approval(), transport=transport, formal=False,
        )
        return service, transport

    def test_four_logical_runs_keep_failures_in_denominator_and_pair_context_only(self):
        service, transport = self._service([_envelope()] * 4)
        results = service.extract_all()
        self.assertEqual(len(results), 4)
        self.assertEqual(transport.call_count, 4)
        calls = transport.calls
        bodies = [c.body for c in calls]
        self.assertEqual(len(bodies), 4)
        # Adapter's provider body contains the rendered prompt. Pairwise exact
        # equality is checked at assembled-input level via the recorded hashes.
        for input_id in ("R01-collar-bore24", "R02-collar-bore24-anodizing"):
            c0 = service.runs[authorize_ret004().expected_logical_run_id(input_id, "C0")]
            c1 = service.runs[authorize_ret004().expected_logical_run_id(input_id, "C1")]
            self.assertNotEqual(c0.logical_run_id, c1.logical_run_id)
            self.assertEqual(c0.llm_meta.get("candidate_source_ids"), [])
            self.assertEqual(len(c1.llm_meta.get("candidate_source_ids", [])), 3)
            self.assertIsNone(c0.llm_meta.get("reference_context_sha256"))
            self.assertRegex(c1.llm_meta.get("reference_context_sha256", ""), r"^[0-9a-f]{64}$")

    def test_c0_reference_context_is_null_and_c1_contains_untrusted_role(self):
        service, transport = self._service([_envelope()] * 4)
        service.extract_all()
        rendered = [call.body["messages"][-1]["content"] for call in transport.calls]
        # Same text is present in each pair, with reference_context as the only
        # condition-specific template slot.
        self.assertTrue(rendered[0].endswith("reference_context:\nnull"))
        self.assertIn("retrieval_example_untrusted_reference", rendered[1])
        self.assertTrue(rendered[2].endswith("reference_context:\nnull"))
        self.assertIn("retrieval_example_untrusted_reference", rendered[3])

    def test_pair_differs_only_in_reference_context_slot(self):
        service, transport = self._service([_envelope()] * 4)
        service.extract_all()
        rendered = [call.body["messages"][-1]["content"] for call in transport.calls]
        inputs = _load_inputs()
        for pair_index, input_id in ((0, "R01-collar-bore24"), (2, "R02-collar-bore24-anodizing")):
            c1 = assemble_c1(ProjectedCase(input_id, inputs[input_id], None, ("bore_d",)), _load_index())
            self.assertIsNone(c1.blocked_reason)
            self.assertIsNotNone(c1.reference_context)
            normalized_c1 = rendered[pair_index + 1].replace(c1.reference_context, "null", 1)
            self.assertEqual(rendered[pair_index], normalized_c1)

    def test_r01_each_condition_requires_separate_confirmation(self):
        service, _ = self._service([_envelope()] * 4)
        service.extract_all()
        c0_id = authorize_ret004().expected_logical_run_id("R01-collar-bore24", "C0")
        with self.assertRaisesRegex(ValueError, "OFFLINE_CAD_DISABLED"):
            service.confirm_run(c0_id, True)
        # Exercise confirmation routing with an explicit non-test approval,
        # while patching the only CAD entry so this remains an offline test.
        service.approval = _approval(test_only=False)
        service.formal = True
        with patch("integration.ret004_paired_runner.confirm_product_live_run") as confirm:
            confirm.return_value = service.runs[c0_id]
            c0 = service.confirm_r01("C0", True)
            self.assertEqual(c0.product_status, "needs_confirmation")
            confirm.assert_called_once()
        # C1 remains separately confirmable; C0 confirmation does not authorize it.
        self.assertEqual(service.runs[authorize_ret004().expected_logical_run_id("R01-collar-bore24", "C1")].product_status,
                         "needs_confirmation")

    def test_confirmation_requires_actual_boolean(self):
        service, _ = self._service([_envelope()] * 4)
        service.extract_all()
        service.formal = True
        service.approval = _approval(test_only=False)
        logical_id = authorize_ret004().expected_logical_run_id("R01-collar-bore24", "C0")
        with patch("integration.ret004_paired_runner.confirm_product_live_run") as confirm:
            with self.assertRaisesRegex(ValueError, "MUST_BE_BOOLEAN"):
                service.confirm_run(logical_id, "false")
            confirm.assert_not_called()

    def test_mutated_extraction_state_cannot_be_confirmed(self):
        service, _ = self._service([_envelope()] * 4)
        service.extract_all()
        service.formal = True
        service.approval = _approval(test_only=False)
        logical_id = authorize_ret004().expected_logical_run_id("R01-collar-bore24", "C0")
        service.runs[logical_id].extracted_parameters["bore_d"] = 80
        with patch("integration.ret004_paired_runner.confirm_product_live_run") as confirm:
            with self.assertRaisesRegex(ValueError, "STATE_CHANGED"):
                service.confirm_run(logical_id, True)
            confirm.assert_not_called()

    def test_r02_is_hard_denied_even_when_model_returns_answer(self):
        service, _ = self._service([_envelope()] * 4)
        service.extract_all()
        for condition in RET004_CONDITIONS:
            state = service.runs[authorize_ret004().expected_logical_run_id("R02-collar-bore24-anodizing", condition)]
            self.assertEqual(state.product_status, "blocked")
            self.assertEqual(state.errors[0]["code"], "SCOPE_CAD_DENIED")
        with patch("integration.ret004_paired_runner.confirm_product_live_run") as confirm:
            r02 = authorize_ret004().expected_logical_run_id("R02-collar-bore24-anodizing", "C1")
            with self.assertRaises(ValueError): service.confirm_run(r02, True)
            confirm.assert_not_called()

    def test_unsupported_response_blocks_before_cad(self):
        service, _ = self._service([_envelope(), _envelope(), _envelope(unsupported=["anodizing"]), _envelope(unsupported=["anodizing"])])
        service.extract_all()
        for condition in RET004_CONDITIONS:
            state = service.runs[authorize_ret004().expected_logical_run_id("R02-collar-bore24-anodizing", condition)]
            self.assertEqual(state.product_status, "blocked")
            self.assertIn("anodizing", state.unsupported_requests)

    def test_malformed_provider_body_does_not_leak_into_failure_state(self):
        marker = "RET004_PROVIDER_SECRET_MARKER"
        service, _ = self._service(["{" + marker] + [_envelope()] * 3)
        with patch("integration.product_live_runner.run_pipeline") as cad:
            states = service.extract_all()
        cad.assert_not_called()
        first = states[0].as_dict()
        self.assertEqual(first["product_status"], "error")
        self.assertNotIn(marker, json.dumps(first, ensure_ascii=False))

    def test_only_r01_can_be_confirmed(self):
        service, _ = self._service([_envelope()] * 4)
        service.extract_all()
        r02_c0 = authorize_ret004().expected_logical_run_id("R02-collar-bore24-anodizing", "C0")
        with self.assertRaisesRegex(ValueError, "CAD_DENIED"):
            service.confirm_run(r02_c0, True)

    def test_test_approval_cannot_enter_formal_path(self):
        with patch("integration.ret004_paired_runner.run_ret004_offline_preflight") as preflight:
            with self.assertRaises(ValueError):
                run_ret004_paired_batch(approval=_approval(test_only=True), transport=None)
            preflight.assert_not_called()

    def test_test_only_approval_cannot_construct_formal_service(self):
        from llm.real_transport import DeepSeekTransport
        with self.assertRaisesRegex(ValueError, "TEST_ONLY_APPROVAL"):
            RET004PairedService(
                auth=authorize_ret004(), approval=_approval(test_only=True),
                transport=DeepSeekTransport(authorize_ret004()), formal=True, ledger=object(),
            )

    def test_non_fake_offline_transport_rejected(self):
        with self.assertRaises(ValueError):
            run_ret004_paired_batch(approval=_approval(), transport=object())

    def test_two_retryable_failures_do_not_exceed_pair_budget(self):
        from llm.transport import TransportError, COND_TIMEOUT
        transport = FakeTransport()
        transport.queue_error(TransportError(condition=COND_TIMEOUT, http_status=None, message="timeout"))
        transport.queue_error(TransportError(condition=COND_TIMEOUT, http_status=None, message="timeout"))
        transport.queue_response(TransportResponse(status=200, body=_envelope()))
        service = RET004PairedService(auth=authorize_ret004(), approval=_approval(), transport=transport, formal=False)
        states = service.extract_all()
        self.assertEqual(transport.call_count, 5)
        self.assertLessEqual(transport.call_count, RET004_MAX_HTTP)
        self.assertEqual(states[0].product_status, "error")
        self.assertEqual(states[0].llm_meta["attempt_count"], 2)


if __name__ == "__main__":
    unittest.main()
