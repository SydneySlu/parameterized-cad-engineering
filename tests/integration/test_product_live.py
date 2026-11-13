"""Offline tests for APP-003 product live extraction entry point.

All tests use mock/spy transport — no real HTTP calls, no .env reads,
no evaluator labels in model inputs, no A2 reuse.

Coverage:
  1. P1 answer: needs_confirmation (zero CAD); confirmed → mock pipeline success,
     child isolated, STEP hash evidence correct.
  2. P2 ask/missing: blocked; empty confirm, bad patch, direct HTTP confirm all blocked,
     zero CAD.
  3. P3 conflict: Schema/rule blocked, zero CAD, no STEP.
  4. P4 unsupported: unsupported blocked, zero CAD, no STEP.
  5. parse/contract/schema failure: fail-closed, error codes recorded.
  6. pipeline/STEP failure: failed, no misreport, no old-run STEP exposure.
  7. Product approval missing, test-only, wrong batch, wrong input hash, wrong prompt hash,
     wrong model identity: rejected before directory/ledger/transport/HTTP.
  8. Budget: 13th HTTP attempt blocked; every attempt pre-reserves ledger slot.
  9. raw/summary: hash matches, relative paths, body/secret/labels not in summary.
 10. C3 regression: existing offline fixture tests unaffected.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]

import sys
sys.path.insert(0, str(_REPO_ROOT / "src"))

from llm.product_live_authorization import (
    PRODUCT_PROFILE_ID,
    PRODUCT_INPUT_IDS,
    PRODUCT_INPUTS_SHA256,
    PRODUCT_LABELS_SHA256,
    PRODUCT_PROVIDER,
    PRODUCT_MODEL,
    PRODUCT_CONDITION,
    PRODUCT_MAX_LOGICAL_RUNS,
    PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
    PRODUCT_MAX_BATCH_HTTP,
    PRODUCT_SAMPLE_SET,
    ProductLiveAuthorization,
    ProductLiveFormalApproval,
    ProductApprovalValidationError,
    authorize_product_live_run,
    make_product_test_approval,
    validate_product_formal_approval_binding,
)
from llm.authorization import AuthorizationScopeError
from llm.contract import (
    CONTRACT_VERSION,
    PROMPT_VERSION,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_MODEL,
    FORMAL_EVALUATION_ALLOWED,
)
from llm.transport import FakeTransport, TransportResponse, TransportError, COND_HTTP_5XX
from integration.product_live_runner import (
    PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
    PRODUCT_LIVE_STATUS_BLOCKED,
    PRODUCT_LIVE_STATUS_SUCCEEDED,
    PRODUCT_LIVE_STATUS_FAILED,
    PRODUCT_LIVE_STATUS_ERROR,
    ProductLiveRunState,
    run_product_batch,
    run_product_offline_preflight,
    confirm_product_live_run,
    _load_frozen_inputs,
)


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


def _make_transport_with_response(body: str) -> FakeTransport:
    t = FakeTransport()
    t.queue_response(TransportResponse(status=200, body=body))
    return t


def _make_auth(batch_id: str = "test-batch-product-001") -> ProductLiveAuthorization:
    return authorize_product_live_run(batch_id=batch_id)


# ---------------------------------------------------------------------------
# 1. Product authorization scope tests
# ---------------------------------------------------------------------------

class TestProductLiveAuthorization(unittest.TestCase):
    """Test ProductLiveAuthorization construction and scope validation."""

    def test_valid_construction(self):
        auth = _make_auth()
        self.assertEqual(auth.profile_id, PRODUCT_PROFILE_ID)
        self.assertEqual(auth.input_ids, PRODUCT_INPUT_IDS)
        self.assertEqual(auth.inputs_sha256, PRODUCT_INPUTS_SHA256)
        self.assertEqual(auth.evaluator_labels_sha256, PRODUCT_LABELS_SHA256)
        self.assertTrue(auth.enable_cad_pipeline)
        self.assertEqual(auth.max_batch_attempts, 12)
        self.assertEqual(auth.max_logical_runs, 4)
        self.assertEqual(auth.max_attempts_per_run, 3)
        self.assertTrue(auth.ir_cad_geometry_step_disabled)
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)  # global gate never modified

    def test_rejects_wrong_provider(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({"Ollama"}),  # wrong
                models=frozenset({PRODUCT_MODEL}),
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
                max_provider_attempts=12,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id=PRODUCT_PROFILE_ID,
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_rejects_wrong_model(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({PRODUCT_PROVIDER}),
                models=frozenset({"qwen3:8b"}),  # wrong
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
                max_provider_attempts=12,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id=PRODUCT_PROFILE_ID,
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_rejects_wrong_profile_id(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({PRODUCT_PROVIDER}),
                models=frozenset({PRODUCT_MODEL}),
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
                max_provider_attempts=12,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id="app002-integration-a2.v1",  # A2 profile — wrong
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_rejects_wrong_inputs_sha256(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({PRODUCT_PROVIDER}),
                models=frozenset({PRODUCT_MODEL}),
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
                max_provider_attempts=12,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id=PRODUCT_PROFILE_ID,
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256="a" * 64,  # wrong hash
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_rejects_wrong_budget(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({PRODUCT_PROVIDER}),
                models=frozenset({PRODUCT_MODEL}),
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=99,  # wrong budget
                max_provider_attempts=99,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id=PRODUCT_PROFILE_ID,
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_rejects_enable_cad_pipeline_false(self):
        with self.assertRaises(AuthorizationScopeError):
            ProductLiveAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set=PRODUCT_SAMPLE_SET,
                conditions=frozenset({PRODUCT_CONDITION}),
                providers=frozenset({PRODUCT_PROVIDER}),
                models=frozenset({PRODUCT_MODEL}),
                max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
                max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
                max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
                max_provider_attempts=12,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-batch",
                profile_id=PRODUCT_PROFILE_ID,
                input_ids=PRODUCT_INPUT_IDS,
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                enable_cad_pipeline=False,  # must be True
            )

    def test_rejects_empty_batch_id(self):
        with self.assertRaises(AuthorizationScopeError):
            authorize_product_live_run(batch_id="")

    def test_formal_evaluation_allowed_still_false(self):
        """Creating the authorization must not change the global gate."""
        _make_auth()
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)


class TestProductApproval(unittest.TestCase):
    """Test ProductLiveFormalApproval scope validation and binding."""

    def test_test_only_approval_rejected_by_binding_check(self):
        auth = _make_auth()
        test_approval = make_product_test_approval(batch_id="test-batch-product-001")
        self.assertTrue(test_approval.is_test_only)
        with self.assertRaises(ProductApprovalValidationError):
            validate_product_formal_approval_binding(auth, test_approval)

    def test_batch_id_mismatch_rejected(self):
        auth = _make_auth(batch_id="batch-A")
        approval = ProductLiveFormalApproval(
            batch_id="batch-B",  # mismatch
            profile_id=PRODUCT_PROFILE_ID,
            inputs_sha256=PRODUCT_INPUTS_SHA256,
            evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
            provider=PRODUCT_PROVIDER,
            model=PRODUCT_MODEL,
            condition=PRODUCT_CONDITION,
            max_batch_http=PRODUCT_MAX_BATCH_HTTP,
            enable_cad_pipeline=True,
            approver="owner",
            approved_at_utc="2026-11-13T00:00:00Z",
            approval_statement="test approval",
            is_test_only=False,
        )
        with self.assertRaises(ProductApprovalValidationError):
            validate_product_formal_approval_binding(auth, approval)

    def test_wrong_profile_id_in_approval_rejected(self):
        with self.assertRaises(ProductApprovalValidationError):
            ProductLiveFormalApproval(
                batch_id="test-batch",
                profile_id="app002-integration-a2.v1",  # A2 profile — wrong
                inputs_sha256=PRODUCT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
                provider=PRODUCT_PROVIDER, model=PRODUCT_MODEL,
                condition=PRODUCT_CONDITION,
                max_batch_http=PRODUCT_MAX_BATCH_HTTP,
                enable_cad_pipeline=True,
                approver="owner", approved_at_utc="2026-11-13T00:00:00Z",
                approval_statement="test",
            )

    def test_approval_as_audit_dict_no_secrets(self):
        """Approval audit dict must not contain API keys or authorization headers."""
        auth = _make_auth()
        approval = ProductLiveFormalApproval(
            batch_id="test-batch-product-001",
            profile_id=PRODUCT_PROFILE_ID,
            inputs_sha256=PRODUCT_INPUTS_SHA256,
            evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
            provider=PRODUCT_PROVIDER, model=PRODUCT_MODEL,
            condition=PRODUCT_CONDITION,
            max_batch_http=PRODUCT_MAX_BATCH_HTTP,
            enable_cad_pipeline=True,
            approver="owner", approved_at_utc="2026-11-13T00:00:00Z",
            approval_statement="test approval statement",
            is_test_only=False,
        )
        d = approval.as_audit_dict()
        audit_str = json.dumps(d).lower()
        self.assertNotIn("api_key", audit_str)
        self.assertNotIn("authorization", audit_str)
        self.assertNotIn("bearer", audit_str)


# ---------------------------------------------------------------------------
# 2. Offline preflight tests
# ---------------------------------------------------------------------------

class TestProductOfflinePreflight(unittest.TestCase):
    """Test run_product_offline_preflight."""

    def test_preflight_passes_with_valid_auth(self):
        auth = _make_auth()
        result = run_product_offline_preflight(auth)
        self.assertTrue(result["ok"], msg=f"preflight errors: {result['errors']}")
        self.assertEqual(result["errors"], [])

    def test_preflight_budget_feasible(self):
        auth = _make_auth()
        result = run_product_offline_preflight(auth)
        budget = result["details"]["budget_plan"]
        self.assertTrue(budget["feasible"])
        self.assertEqual(budget["computed_max_http"], 12)
        self.assertEqual(budget["authorized_max_http"], 12)

    def test_preflight_inputs_sha256_verified(self):
        auth = _make_auth()
        result = run_product_offline_preflight(auth)
        self.assertTrue(result["details"]["inputs_sha256_ok"])

    def test_preflight_batch_dir_does_not_exist(self):
        auth = _make_auth()
        # Use a tmp dir that does not contain the batch subdir
        with tempfile.TemporaryDirectory() as tmpdir:
            # Batch dir won't exist — but preflight checks the canonical run root
            result = run_product_offline_preflight(auth)
            # batch_dir_exists should be False for a fresh batch_id
            self.assertFalse(result["details"]["batch_dir_exists"])

    def test_preflight_prompt_loadable(self):
        auth = _make_auth()
        result = run_product_offline_preflight(auth)
        self.assertTrue(result["details"]["prompt_ok"])

    def test_dry_run_returns_plan_and_preflight(self):
        auth = _make_auth()
        result = run_product_batch(authorization=auth, dry_run=True)
        self.assertEqual(result.mode, "dry_run")
        self.assertTrue(result.preflight_ok, msg=f"preflight errors: {result.preflight_errors}")
        self.assertEqual(len(result.planned_runs), 4)
        input_ids = [p.input_id for p in result.planned_runs]
        self.assertEqual(input_ids, list(PRODUCT_INPUT_IDS))
        self.assertEqual(result.results, [])


# ---------------------------------------------------------------------------
# 3. Mock-mode extraction tests (run_product_batch with FakeTransport)
# ---------------------------------------------------------------------------

class TestProductLiveMockP1Answer(unittest.TestCase):
    """P1: answer → needs_confirmation, zero compile_ir before confirm."""

    def setUp(self):
        self.auth = _make_auth()
        self.env_p1 = _make_valid_envelope(decision="answer", extracted={"bore_d": 24})

    def test_p1_answer_gives_needs_confirmation(self):
        transport = FakeTransport()
        # Queue 4 responses (one per input)
        transport.queue_response(TransportResponse(status=200, body=self.env_p1))
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "ask", {}, ["bore_d"], [], ["bore_d 是必填参数，请提供"]
        )))
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24, "outer_d": 33}, [], [], []
        )))
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24}, [], ["anodizing"], []
        )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(
                authorization=self.auth,
                dry_run=False,
                transport=transport,
            )
            # run_pipeline must NEVER be called during extraction phase
            mock_pipe.assert_not_called()
        p1_state = result.results[0]
        self.assertEqual(p1_state.input_id, "P1-24mm")
        self.assertEqual(p1_state.product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(p1_state.llm_status, "answer")
        self.assertEqual(p1_state.decision, "answer")
        self.assertEqual(p1_state.extracted_parameters.get("bore_d"), 24)

    def test_p1_no_cad_before_confirm(self):
        """compile_ir must be 0 calls before explicit confirm."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=self.env_p1))
        # Queue remaining 3
        for _ in range(3):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(
                authorization=self.auth, dry_run=False, transport=transport
            )
            mock_pipe.assert_not_called()

        self.assertEqual(result.results[0].product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)


class TestProductLiveMockP1Confirm(unittest.TestCase):
    """P1: after explicit confirm, mock pipeline runs successfully."""

    def _make_p1_state(self) -> ProductLiveRunState:
        from integration.product_live_runner import PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION
        return ProductLiveRunState(
            logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
            input_id="P1-24mm",
            condition_id="C0",
            provider="DeepSeek",
            model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[],
            request_text="请按 GN 705 做一个轴环，轴孔直径 24 mm。",
        )

    def test_confirm_true_calls_pipeline(self):
        """confirmed=True → run_pipeline called."""
        state = self._make_p1_state()

        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.stage = "step_readback"
        mock_result.errors = []
        mock_result.run_id = "mock-run-id"
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = {"step_sha256": "abc123", "step_bytes": 100}

        with patch("integration.product_live_runner.run_pipeline",
                   return_value=mock_result) as mock_pipe:
            new_state = confirm_product_live_run(state, confirmed=True)
            mock_pipe.assert_called_once()

        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_SUCCEEDED)
        self.assertEqual(new_state.pipeline_status, "success")
        self.assertTrue(new_state.confirmed)
        self.assertEqual(new_state.ir_index, {"step_sha256": "abc123", "step_bytes": 100})

    def test_confirm_false_blocked_no_cad(self):
        """confirmed=False → blocked, no pipeline call."""
        state = self._make_p1_state()
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            new_state = confirm_product_live_run(state, confirmed=False)
            mock_pipe.assert_not_called()
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        any_code = any(e.get("code") == "CONFIRMATION_REJECTED" for e in new_state.errors)
        self.assertTrue(any_code)

    def test_confirm_non_confirmable_state_blocked(self):
        """confirm called on a blocked run → blocked."""
        state = self._make_p1_state()
        state.product_status = PRODUCT_LIVE_STATUS_BLOCKED
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            new_state = confirm_product_live_run(state, confirmed=True)
            mock_pipe.assert_not_called()
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        any_code = any(e.get("code") == "NOT_CONFIRMABLE" for e in new_state.errors)
        self.assertTrue(any_code)

    def test_confirm_pipeline_failure_returns_failed(self):
        """Pipeline failure → product_status=failed, no succeeded misreport."""
        state = self._make_p1_state()
        mock_result = MagicMock()
        mock_result.status = "failed"
        mock_result.stage = "cad"
        mock_result.errors = [{"code": "CAD_FAILED", "message": "cad error"}]
        mock_result.run_id = "mock-run-id"
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = None

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            new_state = confirm_product_live_run(state, confirmed=True)

        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_FAILED)
        # Must not expose step_path
        self.assertIsNone(new_state.step_path)
        self.assertIsNone(new_state.ir_index)

    def test_confirm_patch_unknown_field_blocked(self):
        """Patch with unknown field → blocked, zero CAD."""
        state = self._make_p1_state()
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            new_state = confirm_product_live_run(state, confirmed=True, patch={"unknown_param": 99})
            mock_pipe.assert_not_called()
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertTrue(any(e.get("code") == "PATCH_UNKNOWN_FIELD" for e in new_state.errors))


# ---------------------------------------------------------------------------
# 4. P2: ask/missing
# ---------------------------------------------------------------------------

class TestProductLiveMockP2Ask(unittest.TestCase):
    """P2: decision=ask → blocked, zero CAD."""

    def test_p2_ask_missing_bore_blocked(self):
        auth = _make_auth()
        transport = FakeTransport()
        # P1 gets answer
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24}, [], [], []
        )))
        # P2 gets ask with missing bore_d
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "ask", {}, ["bore_d"], [], ["bore_d 是必填参数，请提供"]
        )))
        # P3, P4
        for _ in range(2):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "answer", {"bore_d": 24}, [], [], []
            )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
            mock_pipe.assert_not_called()

        p2_state = result.results[1]
        self.assertEqual(p2_state.input_id, "P2-ask-bore")
        self.assertEqual(p2_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertEqual(p2_state.llm_status, "ask")
        self.assertIn("bore_d", p2_state.missing_fields)

    def test_p2_blocked_confirm_zero_cad(self):
        """Direct confirm on a P2 blocked state → still blocked, zero CAD."""
        from integration.product_live_runner import ProductLiveRunState
        state = ProductLiveRunState(
            logical_run_id="P2-ask-bore__C0__DeepSeek__deepseek-flash",
            input_id="P2-ask-bore",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="ask", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision="ask",
            extracted_parameters={}, missing_fields=["bore_d"],
            unsupported_requests=[], questions=["bore_d 是必填参数，请提供"],
            conflicts=[],
            errors=[{"code": "GATE_DECISION_ASK", "message": "ask"}],
            request_text="请按 GN 705 做一个轴环。",
        )
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            new_state = confirm_product_live_run(state, confirmed=True)
            mock_pipe.assert_not_called()
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)


# ---------------------------------------------------------------------------
# 5. P3: catalog conflict
# ---------------------------------------------------------------------------

class TestProductLiveMockP3Conflict(unittest.TestCase):
    """P3: decision=answer but outer_d conflicts with catalog → Schema blocked."""

    def test_p3_catalog_conflict_blocked_zero_cad(self):
        auth = _make_auth()
        transport = FakeTransport()
        # P1 answer
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24}, [], [], []
        )))
        # P2 ask
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "ask", {}, ["bore_d"], [], []
        )))
        # P3: bore_d=24 outer_d=33 → catalog says outer_d should be 40, so conflict
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24, "outer_d": 33}, [], [], []
        )))
        # P4 unsupported
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24}, [], ["anodizing"], []
        )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
            mock_pipe.assert_not_called()

        p3_state = result.results[2]
        self.assertEqual(p3_state.input_id, "P3-catalog-conflict")
        self.assertEqual(p3_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertGreater(len(p3_state.conflicts), 0)
        self.assertIsNone(p3_state.step_path)


# ---------------------------------------------------------------------------
# 6. P4: unsupported request
# ---------------------------------------------------------------------------

class TestProductLiveMockP4Unsupported(unittest.TestCase):
    """P4: unsupported_requests non-empty → blocked, zero CAD."""

    def test_p4_unsupported_blocked_zero_cad(self):
        auth = _make_auth()
        transport = FakeTransport()
        for body in [
            _make_valid_envelope("answer", {"bore_d": 24}, [], [], []),
            _make_valid_envelope("ask", {}, ["bore_d"], [], []),
            _make_valid_envelope("answer", {"bore_d": 24, "outer_d": 33}, [], [], []),
            _make_valid_envelope("answer", {"bore_d": 24}, [], ["anodizing"], []),
        ]:
            transport.queue_response(TransportResponse(status=200, body=body))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
            mock_pipe.assert_not_called()

        p4_state = result.results[3]
        self.assertEqual(p4_state.input_id, "P4-unsupported")
        self.assertEqual(p4_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertIn("anodizing", p4_state.unsupported_requests)
        self.assertIsNone(p4_state.step_path)
        any_code = any(e.get("code") == "GATE_UNSUPPORTED_REQUESTS" for e in p4_state.errors)
        self.assertTrue(any_code)


# ---------------------------------------------------------------------------
# 7. Parse / contract / schema failures
# ---------------------------------------------------------------------------

class TestProductLiveParseContractFailures(unittest.TestCase):
    """parse/contract/schema failures → fail-closed, error codes recorded."""

    def test_invalid_json_response_blocked(self):
        auth = _make_auth()
        transport = FakeTransport()
        # P1 returns invalid JSON
        transport.queue_response(TransportResponse(status=200, body="not json {{}}"))
        # Remaining P2-P4 return valid ask
        for _ in range(3):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))

        result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
        p1_state = result.results[0]
        self.assertEqual(p1_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertTrue(len(p1_state.errors) > 0)
        # Must have parse error code
        error_codes = [e.get("code") for e in p1_state.errors]
        self.assertIn("PARSE_ERROR", error_codes)

    def test_schema_fail_on_bore_out_of_catalog(self):
        """bore_d=99999 not in catalog → Schema blocked, zero CAD."""
        auth = _make_auth()
        transport = FakeTransport()
        # P1: bore_d out of catalog
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 99999}, [], [], []
        )))
        for _ in range(3):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
            mock_pipe.assert_not_called()

        p1_state = result.results[0]
        self.assertEqual(p1_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)

    def test_refuse_decision_blocked(self):
        """decision=refuse → blocked, zero CAD."""
        auth = _make_auth()
        transport = FakeTransport()
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "refuse", {}, [], [], []
        )))
        for _ in range(3):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
            mock_pipe.assert_not_called()

        p1_state = result.results[0]
        self.assertEqual(p1_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)
        self.assertEqual(p1_state.llm_status, "refuse")


# ---------------------------------------------------------------------------
# 8. Approval / authorization gate tests (pre-request rejection)
# ---------------------------------------------------------------------------

class TestProductLiveApprovalGate(unittest.TestCase):
    """Formal runs without valid approval must be rejected before any infra."""

    def test_formal_run_without_approval_raises(self):
        """approval=None for formal run → ProductApprovalValidationError."""
        auth = _make_auth()
        # transport=None means formal mode
        with self.assertRaises(ProductApprovalValidationError):
            run_product_batch(authorization=auth, dry_run=False, transport=None, approval=None)

    def test_test_only_approval_rejected_before_infra(self):
        """Test-only approval rejected before any directory/ledger creation."""
        auth = _make_auth()
        test_approval = make_product_test_approval(batch_id=auth.batch_id)
        with patch("llm.budget.BudgetLedger") as mock_ledger, \
             patch("os.makedirs"), \
             patch("pathlib.Path.mkdir"):
            with self.assertRaises(ProductApprovalValidationError):
                run_product_batch(
                    authorization=auth, dry_run=False,
                    transport=None, approval=test_approval
                )
            mock_ledger.assert_not_called()

    def test_formal_evaluation_allowed_still_false_after_gate_check(self):
        """The global gate must remain False throughout all authorization checks."""
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)
        auth = _make_auth()
        try:
            run_product_batch(authorization=auth, dry_run=False, transport=None, approval=None)
        except ProductApprovalValidationError:
            pass
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)


# ---------------------------------------------------------------------------
# 9. Budget enforcement
# ---------------------------------------------------------------------------

class TestProductLiveBudget(unittest.TestCase):
    """Budget: 13th attempt must be blocked; every attempt pre-reserves ledger."""

    def test_budget_12_http_total(self):
        """run_product_batch mock mode uses at most 4 transport sends (1 per input)."""
        auth = _make_auth()
        transport = FakeTransport()
        for _ in range(4):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))
        result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
        self.assertEqual(transport.call_count, 4)

    def test_budget_plan_max_12(self):
        auth = _make_auth()
        result = run_product_batch(authorization=auth, dry_run=True)
        self.assertEqual(result.budget_plan["max_batch_http"], 12)
        self.assertEqual(result.budget_plan["max_logical_runs"], 4)
        self.assertEqual(result.budget_plan["max_chat_attempts_per_run"], 3)


# ---------------------------------------------------------------------------
# 10. Inputs file integrity
# ---------------------------------------------------------------------------

class TestProductLiveInputsFile(unittest.TestCase):
    """Model inputs SHA-256 must match frozen constant."""

    def test_inputs_sha256_matches_constant(self):
        inputs = _load_frozen_inputs(verify_sha256=True)
        self.assertEqual(len(inputs), 4)
        ids = [i["input_id"] for i in inputs]
        self.assertEqual(ids, list(PRODUCT_INPUT_IDS))

    def test_inputs_sha256_mismatch_raises(self):
        """Tampered inputs file must be rejected."""
        with patch("builtins.open", unittest.mock.mock_open(read_data=b'{"inputs": []}')):
            with patch("pathlib.Path.read_bytes", return_value=b'{"inputs": []}'):
                with patch("pathlib.Path.is_file", return_value=True):
                    with self.assertRaises(ValueError):
                        _load_frozen_inputs(verify_sha256=True)


# ---------------------------------------------------------------------------
# 11. Summary / raw / evidence isolation
# ---------------------------------------------------------------------------

class TestProductLiveSummaryIsolation(unittest.TestCase):
    """Summary must not contain raw body, API keys, or evaluator labels."""

    def test_state_as_dict_no_raw_body(self):
        """ProductLiveRunState.as_dict() must not include raw response body."""
        state = ProductLiveRunState(
            logical_run_id="test-run",
            input_id="P1-24mm",
            condition_id="C0",
            provider="DeepSeek",
            model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[],
            raw_retention_meta={
                "retained": True,
                "path": "work/app001-runs/test-batch/raw/test-run.json",
                "body_sha256": "abc123",
                "body": "THIS IS THE RAW BODY — MUST NOT APPEAR IN SUMMARY",
            },
            request_text="test",
        )
        d = state.as_dict()
        d_str = json.dumps(d)
        self.assertNotIn("THIS IS THE RAW BODY", d_str)
        # raw_retention_meta is included but body field may be present (caller strips it)
        # What matters is that our as_dict() doesn't actively hide it — the server handler strips it

    def test_evaluator_labels_not_in_state(self):
        """Evaluator labels must never appear in model inputs or state."""
        auth = _make_auth()
        transport = FakeTransport()
        # Inject a response that might contain label-like content
        transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
            "answer", {"bore_d": 24}, [], [], []
        )))
        for _ in range(3):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))

        result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
        for state in result.results:
            d_str = json.dumps(state.as_dict())
            # evaluator-only labels (from evaluator-labels.json) must not appear
            self.assertNotIn("expected_decision", d_str)
            self.assertNotIn("allowed_to_cad", d_str)
            self.assertNotIn("expected_conflicts", d_str)

    def test_state_contains_prompt_hash(self):
        """Each run state must record prompt_file_sha256 for traceability."""
        state = ProductLiveRunState(
            logical_run_id="test",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            request_text="test",
        )
        d = state.as_dict()
        self.assertIn("prompt_file_sha256", d)
        self.assertIn("prompt_version", d)
        self.assertIn("contract_version", d)


# ---------------------------------------------------------------------------
# 12. C3 regression: existing offline fixture tests unaffected
# ---------------------------------------------------------------------------

class TestC3Regression(unittest.TestCase):
    """C3 offline fixture mode must continue to work unchanged."""

    def test_product_flow_fixture_bore24_still_works(self):
        """c2-answer-bore24 fixture still loads and parses correctly."""
        from demo.product_flow import ProductFlowHandler
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = ProductFlowHandler(output_root=Path(tmpdir))
            rec = handler.create_product_run("test request", "c2-answer-bore24")
            self.assertIn(rec.product_status, [
                "needs_confirmation", "blocked", "succeeded"
            ])
            self.assertNotEqual(rec.run_id, "")

    def test_server_product_live_import_does_not_break_c3(self):
        """Importing server.py with product live support must not break C3 routes."""
        import demo.server as srv
        # C3 routes must still be present
        self.assertTrue(hasattr(srv, "make_handler_class"))
        self.assertTrue(hasattr(srv, "PRODUCT_HTML_CONTENT"))
        self.assertIn("synthetic fixture", srv.PRODUCT_HTML_CONTENT)

    def test_server_make_handler_backward_compatible(self):
        """make_handler_class with only 2 args (C3 signature) still works."""
        from demo.server import make_handler_class
        from demo.handler import DemoHandler
        from demo.product_flow import ProductFlowHandler
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            demo = DemoHandler(output_root=Path(tmpdir))
            product = ProductFlowHandler(output_root=Path(tmpdir))
            # 2-arg call (old signature): product_live_handler defaults to None
            handler_cls = make_handler_class(demo, product)
            self.assertIsNotNone(handler_cls)

    def test_product_live_import_does_not_affect_global_gate(self):
        """Importing product live modules must not change FORMAL_EVALUATION_ALLOWED."""
        from llm.contract import FORMAL_EVALUATION_ALLOWED
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)
        import integration.product_live_runner  # noqa
        import llm.product_live_authorization  # noqa
        from llm.contract import FORMAL_EVALUATION_ALLOWED as fea2
        self.assertFalse(fea2)


# ---------------------------------------------------------------------------
# 13. Logical run ID isolation
# ---------------------------------------------------------------------------

class TestProductLiveRunIsolation(unittest.TestCase):
    """Each run must be isolated; failed runs must not expose other run state."""

    def test_failed_run_no_step(self):
        """A failed confirm result must have step_path=None."""
        from integration.product_live_runner import ProductLiveRunState
        state = ProductLiveRunState(
            logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            request_text="test",
        )
        mock_result = MagicMock()
        mock_result.status = "failed"
        mock_result.stage = "cad"
        mock_result.errors = [{"code": "CAD_FAILED", "message": "err"}]
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = None

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            new_state = confirm_product_live_run(state, confirmed=True)

        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_FAILED)
        self.assertIsNone(new_state.step_path)
        self.assertIsNone(new_state.ir_index)

    def test_succeeded_run_has_step_hash(self):
        """A succeeded confirm result must have ir_index with step_sha256."""
        from integration.product_live_runner import ProductLiveRunState
        state = ProductLiveRunState(
            logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            request_text="test",
        )
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.stage = "step_readback"
        mock_result.errors = []
        mock_result.run_dir = None
        mock_result.step_path = "/some/path/file.step"
        mock_result.ir_index = {
            "step_sha256": "deadbeef" * 8,
            "step_bytes": 137034,
        }

        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            new_state = confirm_product_live_run(state, confirmed=True)

        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_SUCCEEDED)
        self.assertIsNotNone(new_state.ir_index)
        self.assertIn("step_sha256", new_state.ir_index)


# ---------------------------------------------------------------------------
# 14. Mode / plans / profile
# ---------------------------------------------------------------------------

class TestProductLivePlansAndMode(unittest.TestCase):
    """Check mode, profile_id, and planned_runs in batch results."""

    def test_mock_mode_label(self):
        auth = _make_auth()
        transport = FakeTransport()
        for _ in range(4):
            transport.queue_response(TransportResponse(status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], []
            )))
        result = run_product_batch(authorization=auth, dry_run=False, transport=transport)
        self.assertEqual(result.mode, "mock")
        self.assertEqual(result.profile_id, PRODUCT_PROFILE_ID)

    def test_planned_runs_have_correct_input_ids(self):
        auth = _make_auth()
        result = run_product_batch(authorization=auth, dry_run=True)
        ids = [p.input_id for p in result.planned_runs]
        self.assertEqual(ids, ["P1-24mm", "P2-ask-bore", "P3-catalog-conflict", "P4-unsupported"])

    def test_planned_runs_provider_model_correct(self):
        auth = _make_auth()
        result = run_product_batch(authorization=auth, dry_run=True)
        for p in result.planned_runs:
            self.assertEqual(p.provider, PRODUCT_PROVIDER)
            self.assertEqual(p.model, PRODUCT_MODEL)
            self.assertEqual(p.condition_id, PRODUCT_CONDITION)


# ---------------------------------------------------------------------------
# R1-CORRECTION additions
# ---------------------------------------------------------------------------

# Import new pieces for the tests
from integration.product_live_runner import (
    ProductLiveService,
    _to_repo_relative_path,
)
from demo.server import (
    make_handler_class,
    _sanitize_state_for_http,
)
from demo.handler import DemoHandler
from demo.product_flow import ProductFlowHandler
import io
import http.client
import threading
import tempfile
import socketserver
from http.server import HTTPServer


def _make_service(transport: FakeTransport, output_root=None) -> ProductLiveService:
    auth = _make_auth()
    return ProductLiveService(transport=transport, authorization=auth,
                              output_root=output_root)


def _envelopes_for_all_four(
    p1_body: str = "",
    p2_body: str = "",
    p3_body: str = "",
    p4_body: str = "",
) -> FakeTransport:
    """Build a FakeTransport pre-loaded with 4 responses (one per input)."""
    t = FakeTransport()
    t.queue_response(TransportResponse(status=200, body=p1_body or _make_valid_envelope(
        "answer", {"bore_d": 24}, [], [], []
    )))
    t.queue_response(TransportResponse(status=200, body=p2_body or _make_valid_envelope(
        "ask", {}, ["bore_d"], [], ["bore_d 是必填参数，请提供"]
    )))
    t.queue_response(TransportResponse(status=200, body=p3_body or _make_valid_envelope(
        "answer", {"bore_d": 24, "outer_d": 33}, [], [], []
    )))
    t.queue_response(TransportResponse(status=200, body=p4_body or _make_valid_envelope(
        "answer", {"bore_d": 24}, [], ["anodizing"], []
    )))
    return t


# ---------------------------------------------------------------------------
# 15. ProductLiveService unit tests
# ---------------------------------------------------------------------------

class TestProductLiveServiceUnit(unittest.TestCase):
    """Unit tests for ProductLiveService.extract() and confirm()."""

    def test_extract_p1_gives_needs_confirmation(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        state = svc.extract("P1-24mm", "请做一个轴环，轴孔直径 24 mm。")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)
        self.assertEqual(state.input_id, "P1-24mm")

    def test_extract_p1_zero_run_pipeline(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            svc.extract("P1-24mm", "请做一个轴环，轴孔直径 24 mm。")
            mock_pipe.assert_not_called()

    def test_extract_p2_ask_blocked(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "ask", {}, ["bore_d"], [], ["bore_d 是必填参数"]
            )))
        svc = _make_service(transport)
        state = svc.extract("P2-ask-bore", "请做一个轴环。")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)

    def test_extract_p3_conflict_blocked(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "answer", {"bore_d": 24, "outer_d": 33}, [], [], []
            )))
        svc = _make_service(transport)
        state = svc.extract("P3-catalog-conflict",
                             "请做一个轴环，轴孔直径 24 mm，外径 33 mm。")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)

    def test_extract_p4_unsupported_blocked(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope(
                "answer", {"bore_d": 24}, [], ["anodizing"], []
            )))
        svc = _make_service(transport)
        state = svc.extract("P4-unsupported", "请做一个轴环，要求阳极氧化。")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)

    def test_extract_unknown_input_id_error(self):
        transport = FakeTransport()
        svc = _make_service(transport)
        state = svc.extract("UNKNOWN-INPUT", "test")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_ERROR)
        self.assertTrue(any("UNKNOWN_INPUT_ID" in e.get("code", "") for e in state.errors))

    def test_confirm_p1_calls_pipeline(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        state = svc.extract("P1-24mm", "请做一个轴环，轴孔直径 24 mm。")
        self.assertEqual(state.product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)

        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.stage = "step_readback"
        mock_result.errors = []
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = {"step_sha256": "abc" * 20, "step_bytes": 100}
        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            new_state = svc.confirm(state.logical_run_id, confirmed=True)
        self.assertIsNotNone(new_state)
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_SUCCEEDED)

    def test_confirm_false_blocked(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        state = svc.extract("P1-24mm", "请做一个轴环。")
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            new_state = svc.confirm(state.logical_run_id, confirmed=False)
            mock_pipe.assert_not_called()
        self.assertEqual(new_state.product_status, PRODUCT_LIVE_STATUS_BLOCKED)

    def test_confirm_unknown_run_returns_none(self):
        svc = _make_service(FakeTransport())
        result = svc.confirm("nonexistent-run-id", confirmed=True)
        self.assertIsNone(result)

    def test_get_returns_latest_state(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        svc = _make_service(transport)
        state = svc.extract("P1-24mm", "test")
        got = svc.get(state.logical_run_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.product_status, PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION)


# ---------------------------------------------------------------------------
# 16. HTTP tests via ProductLiveService
# ---------------------------------------------------------------------------

def _make_test_server(service=None, port=0) -> tuple:
    """Start a minimal test HTTP server on a free port.  Returns (server, port, thread)."""
    demo = DemoHandler(output_root=Path(tempfile.mkdtemp()))
    product = ProductFlowHandler(output_root=Path(tempfile.mkdtemp()))
    handler_cls = make_handler_class(demo, product, product_live_service=service)
    # Use ThreadingTCPServer for a simple test server
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


def _http_get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, raw


class TestProductLiveServiceHTTP(unittest.TestCase):
    """End-to-end HTTP tests using ProductLiveService with FakeTransport."""

    def _make_server_with_transport(self, transport):
        svc = _make_service(transport)
        server, port, t = _make_test_server(service=svc)
        self.addCleanup(server.shutdown)
        return server, port, svc

    def test_no_service_returns_503_disabled(self):
        """Without a service configured, all product-live routes return DISABLED."""
        server, port, _ = _make_test_server(service=None)
        self.addCleanup(server.shutdown)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["code"], "PRODUCT_LIVE_DISABLED")

    def test_p1_create_needs_confirmation_zero_cad(self):
        """P1 create returns needs_confirmation; run_pipeline not called."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, _ = self._make_server_with_transport(transport)

        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "请做一个轴环，轴孔直径 24 mm。",
                                       "input_id": "P1-24mm"})
            mock_pipe.assert_not_called()

        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "needs_confirmation")
        self.assertEqual(data["input_id"], "P1-24mm")
        # step_path must not be in HTTP response
        self.assertNotIn("step_path", data)

    def test_p1_create_response_no_secrets(self):
        """HTTP response must not contain API keys, raw body, or evaluator labels."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        resp_str = json.dumps(data).lower()
        self.assertNotIn("api_key", resp_str)
        self.assertNotIn("authorization", resp_str)
        self.assertNotIn("bearer", resp_str)
        self.assertNotIn("expected_decision", resp_str)
        self.assertNotIn("allowed_to_cad", resp_str)

    def test_p2_create_blocked(self):
        """P2 ask returns blocked."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("ask", {}, ["bore_d"], [], [])))
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "请做一个轴环。", "input_id": "P2-ask-bore"})
        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "blocked")

    def test_p3_create_blocked(self):
        """P3 conflict returns blocked."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24, "outer_d": 33}, [], [], [])))
        _, port, _ = self._make_server_with_transport(transport)
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(
                port, "/api/product-live/create",
                {"request_text": "请做一个轴环，轴孔直径 24 mm，外径 33 mm。",
                 "input_id": "P3-catalog-conflict"})
            mock_pipe.assert_not_called()
        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "blocked")

    def test_p4_create_blocked(self):
        """P4 unsupported returns blocked."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], ["anodizing"], [])))
        _, port, _ = self._make_server_with_transport(transport)
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(
                port, "/api/product-live/create",
                {"request_text": "要求阳极氧化", "input_id": "P4-unsupported"})
            mock_pipe.assert_not_called()
        self.assertEqual(status, 200)
        self.assertEqual(data["product_status"], "blocked")

    def test_p1_confirm_succeeded(self):
        """P1 confirm triggers pipeline and returns succeeded."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, svc = self._make_server_with_transport(transport)

        # Create
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status, data = _http_post(port, "/api/product-live/create",
                                      {"request_text": "test", "input_id": "P1-24mm"})
            mock_pipe.assert_not_called()
        self.assertEqual(data["product_status"], "needs_confirmation")
        run_id = data["logical_run_id"]

        # Confirm
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.stage = "step_readback"
        mock_result.errors = []
        mock_result.run_dir = None
        mock_result.step_path = None
        mock_result.ir_index = {"step_sha256": "abc" * 20, "step_bytes": 100}
        with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": True, "patch": {}})
        self.assertEqual(status2, 200)
        self.assertEqual(data2["product_status"], "succeeded")
        # step_path must NOT be in HTTP response (absolute path stripped)
        self.assertNotIn("step_path", data2)

    def test_confirm_false_returns_blocked(self):
        """confirmed=False → blocked."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, svc = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": False, "patch": {}})
            mock_pipe.assert_not_called()
        self.assertEqual(data2["product_status"], "blocked")

    def test_p2_blocked_confirm_zero_cad(self):
        """Direct confirm on a blocked P2 run → still blocked, zero CAD."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("ask", {}, ["bore_d"], [], [])))
        _, port, svc = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P2-ask-bore"})
        run_id = data["logical_run_id"]
        with patch("integration.product_live_runner.run_pipeline") as mock_pipe:
            status2, data2 = _http_post(port, f"/api/product-live/confirm/{run_id}",
                                        {"confirmed": True, "patch": {}})
            mock_pipe.assert_not_called()
        self.assertEqual(data2["product_status"], "blocked")

    def test_missing_input_id_returns_400(self):
        """Missing input_id → 400."""
        transport = FakeTransport()
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test"})
        self.assertEqual(status, 400)

    def test_missing_request_text_returns_400(self):
        """Missing request_text → 400."""
        transport = FakeTransport()
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"input_id": "P1-24mm"})
        self.assertEqual(status, 400)

    def test_get_returns_extraction_state(self):
        """GET /api/product-live/<run_id> returns the extraction state."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, svc = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        run_id = data["logical_run_id"]
        status2, raw = _http_get(port, f"/api/product-live/{run_id}")
        self.assertEqual(status2, 200)
        got = json.loads(raw)
        self.assertEqual(got["product_status"], "needs_confirmation")

    def test_response_no_absolute_paths(self):
        """HTTP response must not contain absolute paths."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P1-24mm"})
        resp_str = json.dumps(data)
        # Must not start any value with "/" (absolute unix path)
        # Check key fields specifically
        for key in ("pipeline_run_dir", "step_path"):
            val = data.get(key)
            self.assertIsNone(val,
                              msg=f"{key!r} must be absent/None in HTTP response, got {val!r}")

    def test_download_succeeded_run(self):
        """STEP download works for a succeeded run."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("answer", {"bore_d": 24}, [], [], [])))
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = _make_service(transport, output_root=Path(tmpdir))
            server, port, t = _make_test_server(service=svc)
            self.addCleanup(server.shutdown)

            # Create
            _http_post(port, "/api/product-live/create",
                       {"request_text": "test", "input_id": "P1-24mm"})
            state = svc.get(f"P1-24mm__{PRODUCT_CONDITION}__{PRODUCT_PROVIDER}__{PRODUCT_MODEL}")
            run_id = state.logical_run_id

            # Mock a successful pipeline result with a real temp STEP file
            step_content = b"ISO-10303-21;\nHEADER; END-SECTION;\nDATA; END-SECTION;\nEND-ISO-10303-21;\n"
            step_hash = hashlib.sha256(step_content).hexdigest()
            step_dir = Path(tmpdir) / "cad_output"
            step_dir.mkdir(exist_ok=True)
            step_file = step_dir / "collar.step"
            step_file.write_bytes(step_content)

            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stage = "step_readback"
            mock_result.errors = []
            mock_result.run_dir = str(step_dir.parent)
            mock_result.step_path = str(step_file)
            mock_result.ir_index = {
                "step_sha256": step_hash,
                "step_bytes": len(step_content),
                "step_path": str(step_file),
            }
            with patch("integration.product_live_runner.run_pipeline", return_value=mock_result):
                _http_post(port, f"/api/product-live/confirm/{run_id}",
                           {"confirmed": True, "patch": {}})

            # Download
            status, raw = _http_get(port, f"/product-live-download/{run_id}")
            self.assertEqual(status, 200)
            self.assertEqual(raw, step_content)
            # Verify SHA-256
            self.assertEqual(hashlib.sha256(raw).hexdigest(), step_hash)

    def test_download_blocked_run_returns_403(self):
        """Download of a blocked run returns 403."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200,
            body=_make_valid_envelope("ask", {}, ["bore_d"], [], [])))
        _, port, _ = self._make_server_with_transport(transport)
        status, data = _http_post(port, "/api/product-live/create",
                                  {"request_text": "test", "input_id": "P2-ask-bore"})
        run_id = data["logical_run_id"]
        status2, _ = _http_get(port, f"/product-live-download/{run_id}")
        self.assertEqual(status2, 403)


# ---------------------------------------------------------------------------
# 17. Summary path normalisation tests
# ---------------------------------------------------------------------------

class TestSummaryPathRelative(unittest.TestCase):
    """Summary must use repo-relative paths; no absolute paths in evidence."""

    def test_to_repo_relative_path_inside_repo(self):
        """Path inside repo → repo-relative string."""
        from pathlib import Path as _P
        import sys
        sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "src"))
        from integration.product_live_runner import _to_repo_relative_path, _REPO_ROOT
        inside = str(_REPO_ROOT / "some" / "dir" / "file.json")
        result = _to_repo_relative_path(inside)
        self.assertIsNotNone(result)
        self.assertFalse(result.startswith("/"),
                         msg=f"Expected relative path, got {result!r}")
        self.assertIn("some/dir/file.json", result.replace("\\", "/"))

    def test_to_repo_relative_path_outside_repo(self):
        """Path outside repo → None."""
        from integration.product_live_runner import _to_repo_relative_path
        outside = "/tmp/completely_outside_repo/file.json"
        result = _to_repo_relative_path(outside)
        self.assertIsNone(result)

    def test_to_repo_relative_path_none(self):
        """None input → None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path(None))

    def test_to_repo_relative_path_already_relative(self):
        """Already-relative path returned as-is."""
        from integration.product_live_runner import _to_repo_relative_path
        rel = "work/product-live-runs/some-run/file.step"
        result = _to_repo_relative_path(rel)
        self.assertIsNotNone(result)

    def test_summary_writer_normalises_pipeline_run_dir(self):
        """_SummaryWriter.update_run() must write repo-relative pipeline_run_dir."""
        from integration.product_live_runner import (
            _SummaryWriter, _REPO_ROOT, PRODUCT_LIVE_STATUS_BLOCKED,
        )
        from llm.product_live_authorization import authorize_product_live_run
        from llm.contract import PROMPT_VERSION, CONTRACT_VERSION
        from llm.product_live_authorization import PRODUCT_PROMPT_FILE_SHA256

        with tempfile.TemporaryDirectory() as tmpdir:
            # Fake a batch dir inside the canonical run root
            # We override the batch_dir explicitly to avoid canonical check
            batch_dir = Path(tmpdir) / "test-batch"
            batch_dir.mkdir()
            writer = _SummaryWriter(batch_dir, {"runs": {}, "batch_id": "test-batch"})
            writer.write_initial()

            # Build a state with an absolute pipeline_run_dir
            abs_dir = str(batch_dir / "pipeline-runs" / "run-001")
            state = ProductLiveRunState(
                logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
                input_id="P1-24mm",
                condition_id="C0", provider="DeepSeek", model="deepseek-flash",
                llm_status="blocked",
                product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                decision="",
                extracted_parameters={},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[],
                pipeline_run_dir=abs_dir,
                step_path=str(batch_dir / "cad_output" / "collar.step"),
                request_text="test",
                prompt_version=PROMPT_VERSION,
                contract_version=CONTRACT_VERSION,
                prompt_file_sha256=PRODUCT_PROMPT_FILE_SHA256,
            )
            writer.update_run(state)

            # Read the summary back
            import json as _json
            summary = _json.loads((batch_dir / "batch_summary.json").read_text())
            run_entry = summary["runs"]["P1-24mm__C0__DeepSeek__deepseek-flash"]
            # pipeline_run_dir must be None (abs dir is outside repo)
            # or repo-relative if inside repo
            dir_in_summary = run_entry.get("pipeline_run_dir")
            if dir_in_summary is not None:
                self.assertFalse(
                    dir_in_summary.startswith("/"),
                    msg=f"Absolute path in summary: {dir_in_summary!r}"
                )
            # step_path must be None or relative
            sp = run_entry.get("step_path")
            if sp is not None:
                self.assertFalse(sp.startswith("/"),
                                 msg=f"Absolute step_path in summary: {sp!r}")

    def test_summary_writer_no_raw_body(self):
        """Summary must not contain raw response body."""
        from integration.product_live_runner import _SummaryWriter, PRODUCT_LIVE_STATUS_BLOCKED

        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch-2"
            batch_dir.mkdir()
            writer = _SummaryWriter(batch_dir, {"runs": {}, "batch_id": "test-batch-2"})
            writer.write_initial()

            state = ProductLiveRunState(
                logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
                input_id="P1-24mm",
                condition_id="C0", provider="DeepSeek", model="deepseek-flash",
                llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                decision="", extracted_parameters={},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[],
                raw_retention_meta={
                    "retained": True,
                    "path": "work/app001-runs/test-batch-2/raw/p1.json",
                    "body_sha256": "deadbeef" * 8,
                    "body": "SUPER SECRET RAW BODY",
                },
                request_text="test",
            )
            writer.update_run(state)

            import json as _json
            summary_text = (batch_dir / "batch_summary.json").read_text()
            self.assertNotIn("SUPER SECRET RAW BODY", summary_text)
            self.assertNotIn("\"body\":", summary_text)

    def test_sanitize_state_for_http_no_absolute_paths(self):
        """_sanitize_state_for_http must strip absolute step_path."""
        from demo.server import _sanitize_state_for_http
        state = ProductLiveRunState(
            logical_run_id="test",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="answer",
            product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
            decision="answer",
            extracted_parameters={"bore_d": 24},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            step_path="/absolute/path/to/collar.step",
            pipeline_run_dir="/absolute/path/to/run",
            ir_index={"step_sha256": "abc", "step_path": "/absolute/path/collar.step"},
            request_text="test",
        )
        resp = _sanitize_state_for_http(state)
        # Absolute step_path stripped
        self.assertNotIn("step_path", resp)
        # pipeline_run_dir normalised
        prd = resp.get("pipeline_run_dir")
        if prd is not None:
            self.assertFalse(prd.startswith("/"), msg=f"Absolute pipeline_run_dir: {prd!r}")
        # ir_index step_path normalised
        idx = resp.get("ir_index", {})
        if idx.get("step_path") is not None:
            self.assertFalse(idx["step_path"].startswith("/"))

    def test_sanitize_strips_raw_body(self):
        """_sanitize_state_for_http must not expose raw body in any field."""
        from demo.server import _sanitize_state_for_http
        state = ProductLiveRunState(
            logical_run_id="test",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision="", extracted_parameters={},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            raw_retention_path="work/app001-runs/test-batch/raw/p1.json",
            raw_retention_meta={
                "retained": True,
                "path": "work/app001-runs/test-batch/raw/p1.json",
                "body_sha256": "deadbeef",
                "body": "SECRET RAW RESPONSE",
            },
            request_text="test",
        )
        resp = _sanitize_state_for_http(state)
        resp_str = json.dumps(resp)
        # Raw body must never appear in the HTTP response
        self.assertNotIn("SECRET RAW RESPONSE", resp_str)
        # raw_retention_meta is an internal field not included in as_dict(),
        # so it's already absent — the important check is that no body
        # content leaks through any field.
        self.assertNotIn("raw_retention_meta", resp)


# ---------------------------------------------------------------------------
# R1-CORRECTION-2: Path traversal / symlink escape regression tests
# ---------------------------------------------------------------------------

class TestPathTraversalSafety(unittest.TestCase):
    """_to_repo_relative_path must reject path traversal and symlink escapes."""

    def setUp(self):
        from integration.product_live_runner import _REPO_ROOT
        self._repo_root = _REPO_ROOT

    def test_double_dot_traversal(self):
        """../../outside/file.step must return None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path("../../outside/file.step"))

    def test_single_dot_traversal(self):
        """../outside/file.step must return None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path("../outside/file.step"))

    def test_absolute_external_path(self):
        """Absolute path outside repo must return None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path("/tmp/secret_outside/file.step"))

    def test_none_input(self):
        """None input must return None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path(None))

    def test_empty_string(self):
        """Empty string must return None."""
        from integration.product_live_runner import _to_repo_relative_path
        self.assertIsNone(_to_repo_relative_path(""))

    def test_valid_absolute_inside_repo(self):
        """Absolute path inside repo returns repo-relative."""
        from integration.product_live_runner import _to_repo_relative_path, _REPO_ROOT
        inside = str(_REPO_ROOT / "work" / "test-file.json")
        result = _to_repo_relative_path(inside)
        self.assertIsNotNone(result)
        self.assertFalse(result.startswith("/"))
        self.assertIn("work/test-file.json", result.replace("\\", "/"))

    def test_valid_relative_inside_repo(self):
        """Relative path inside repo resolves against _REPO_ROOT and returns relative."""
        from integration.product_live_runner import _to_repo_relative_path
        result = _to_repo_relative_path("work/product-live-runs/file.step")
        self.assertIsNotNone(result)
        self.assertFalse(result.startswith("/"))
        self.assertIn("work/product-live-runs/file.step", result.replace("\\", "/"))

    def test_symlink_escape_returns_none(self):
        """Symlink inside repo pointing outside must return None."""
        import tempfile
        from integration.product_live_runner import _to_repo_relative_path, _REPO_ROOT

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file outside the repo
            outside_file = Path(tmpdir) / "outside_secret.step"
            outside_file.write_text("secret")

            # Create symlink inside repo pointing to the outside file
            link_inside = _REPO_ROOT / "work" / "test_symlink_escape.step"
            try:
                link_inside.symlink_to(outside_file)
                result = _to_repo_relative_path(str(link_inside))
                self.assertIsNone(
                    result,
                    msg=f"Symlink escape should return None, got {result!r}"
                )
            finally:
                link_inside.unlink(missing_ok=True)

    def test_relative_traversal_string_not_returned_as_is(self):
        """A relative path with .. that resolves outside repo must NOT be returned as-is."""
        from integration.product_live_runner import _to_repo_relative_path
        # This used to be returned as-is in the buggy version
        result = _to_repo_relative_path("../../../etc/passwd")
        self.assertIsNone(result)

    def test_no_fallback_on_resolve_exception(self):
        """If resolve raises, the function must return None, not the original string."""
        from integration.product_live_runner import _to_repo_relative_path
        # Pass a path with null bytes — will cause ValueError on resolve
        result = _to_repo_relative_path("work\x00file.step")
        self.assertIsNone(result)


class TestSummaryWriterPathSafety(unittest.TestCase):
    """Summary writer must write None for traversal/symlink-escape paths."""

    def test_summary_writer_traversal_path_becomes_none(self):
        """_SummaryWriter.update_run() must write None for a traversal path."""
        from integration.product_live_runner import (
            _SummaryWriter, PRODUCT_LIVE_STATUS_BLOCKED,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch-traversal"
            batch_dir.mkdir()
            writer = _SummaryWriter(batch_dir, {"runs": {}, "batch_id": "test-batch-traversal"})
            writer.write_initial()

            state = ProductLiveRunState(
                logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
                input_id="P1-24mm",
                condition_id="C0", provider="DeepSeek", model="deepseek-flash",
                llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                decision="", extracted_parameters={},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[],
                pipeline_run_dir="../../outside/secret",
                step_path="../../../etc/passwd",
                request_text="test",
            )
            writer.update_run(state)

            import json as _json
            summary = _json.loads((batch_dir / "batch_summary.json").read_text())
            run_entry = summary["runs"]["P1-24mm__C0__DeepSeek__deepseek-flash"]
            self.assertIsNone(run_entry.get("pipeline_run_dir"),
                              msg=f"Expected None, got {run_entry.get('pipeline_run_dir')!r}")
            self.assertIsNone(run_entry.get("step_path"),
                              msg=f"Expected None, got {run_entry.get('step_path')!r}")

    def test_summary_writer_symlink_escape_becomes_none(self):
        """_SummaryWriter.update_run() must write None for symlink-escaped paths."""
        import tempfile
        from integration.product_live_runner import (
            _SummaryWriter, PRODUCT_LIVE_STATUS_BLOCKED, _REPO_ROOT,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an outside file
            outside_file = Path(tmpdir) / "outside.step"
            outside_file.write_text("secret")

            # Create symlink inside repo
            link_inside = _REPO_ROOT / "work" / "test_symlink_summary.step"
            try:
                link_inside.symlink_to(outside_file)

                batch_dir = Path(tmpdir) / "test-batch-symlink"
                batch_dir.mkdir()
                writer = _SummaryWriter(
                    batch_dir, {"runs": {}, "batch_id": "test-batch-symlink"}
                )
                writer.write_initial()

                state = ProductLiveRunState(
                    logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
                    input_id="P1-24mm",
                    condition_id="C0", provider="DeepSeek", model="deepseek-flash",
                    llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                    decision="", extracted_parameters={},
                    missing_fields=[], unsupported_requests=[], questions=[],
                    conflicts=[], errors=[],
                    step_path=str(link_inside),
                    request_text="test",
                )
                writer.update_run(state)

                import json as _json
                summary = _json.loads((batch_dir / "batch_summary.json").read_text())
                run_entry = summary["runs"]["P1-24mm__C0__DeepSeek__deepseek-flash"]
                self.assertIsNone(run_entry.get("step_path"),
                                  msg=f"Expected None for symlink escape, got {run_entry.get('step_path')!r}")
            finally:
                link_inside.unlink(missing_ok=True)

    def test_summary_writer_no_absolute_paths_in_summary(self):
        """No path field in summary may start with /."""
        from integration.product_live_runner import (
            _SummaryWriter, PRODUCT_LIVE_STATUS_BLOCKED,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch-abs"
            batch_dir.mkdir()
            writer = _SummaryWriter(batch_dir, {"runs": {}, "batch_id": "test-batch-abs"})
            writer.write_initial()

            state = ProductLiveRunState(
                logical_run_id="P1-24mm__C0__DeepSeek__deepseek-flash",
                input_id="P1-24mm",
                condition_id="C0", provider="DeepSeek", model="deepseek-flash",
                llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                decision="", extracted_parameters={},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[], errors=[],
                pipeline_run_dir="/absolute/outside/dir",
                step_path="/absolute/outside/file.step",
                raw_retention_path="/absolute/outside/raw.json",
                request_text="test",
            )
            writer.update_run(state)

            import json as _json
            summary_text = (batch_dir / "batch_summary.json").read_text()
            summary = _json.loads(summary_text)
            run_entry = summary["runs"]["P1-24mm__C0__DeepSeek__deepseek-flash"]

            for field in ("pipeline_run_dir", "step_path", "raw_retention_path"):
                val = run_entry.get(field)
                if val is not None:
                    self.assertFalse(
                        val.startswith("/"),
                        msg=f"Absolute path in summary field {field}: {val!r}"
                    )
            # Check ir_index step_path
            ir_idx = run_entry.get("ir_index")
            if isinstance(ir_idx, dict):
                sp = ir_idx.get("step_path")
                if sp is not None:
                    self.assertFalse(sp.startswith("/"),
                                     msg=f"Absolute ir_index.step_path: {sp!r}")

    def test_sanitize_state_traversal_not_exposed(self):
        """_sanitize_state_for_http must not expose traversal strings."""
        from demo.server import _sanitize_state_for_http
        state = ProductLiveRunState(
            logical_run_id="test",
            input_id="P1-24mm",
            condition_id="C0", provider="DeepSeek", model="deepseek-flash",
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision="", extracted_parameters={},
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[], errors=[],
            pipeline_run_dir="../../outside/secret",
            step_path="../../../etc/passwd",
            request_text="test",
        )
        resp = _sanitize_state_for_http(state)
        resp_str = json.dumps(resp)
        self.assertNotIn("../../outside/secret", resp_str)
        self.assertNotIn("../../../etc/passwd", resp_str)
        # All path fields must be None
        self.assertIsNone(resp.get("pipeline_run_dir"))
        self.assertNotIn("step_path", resp)


if __name__ == "__main__":
    unittest.main()
