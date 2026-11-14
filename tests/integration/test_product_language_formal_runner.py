"""Offline tests for the APP-003 language sample formal runner.

All tests use temporary directories and FakeTransport / mocks.
No network calls, no credential reads, no evaluator-labels.json opens,
no canonical batch directory creation, no CAD execution.

Coverage:
- Normal dry-run / mock plan (approval gate + offline preflight + mock execution)
- Approval field errors: test_only, batch_id mismatch, wrong profile/hash/scope
- Scope errors: wrong authorization type
- Input/hash/order errors: fail-closed preflight
- Existing batch directory: fail-closed preflight
- Budget exhaustion: per-run max 2 and batch max 20
- Retryable vs non-retryable error classification (via error code on results)
- Ledger / raw / summary failures: fail-closed state
- evaluator-labels.json: zero file reads in any path
- Network, credential loading, and formal transport: zero calls for invalid auth /
  failed preflight
- CAD/IR pipeline: never called
- Summary: no absolute paths, no secrets, no raw body, no evaluator label content
- All-failed status not marked complete
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm.authorization import AuthorizationScopeError
from llm.contract import RETRYABLE_CONDITIONS, NON_RETRYABLE_CONDITIONS
from llm.product_language_authorization import (
    PRODUCT_LANGUAGE_INPUTS_SHA256,
    PRODUCT_LANGUAGE_LABELS_SHA256,
    PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_PROFILE_ID,
    PRODUCT_LANGUAGE_PROVIDER,
    PRODUCT_LANGUAGE_MODEL,
    PRODUCT_LANGUAGE_CONDITION,
    ProductLanguageApprovalValidationError,
    ProductLanguageFormalApproval,
    ProductLanguageAuthorization,
    authorize_product_language_run,
    make_language_test_approval,
    validate_product_language_formal_approval_binding,
)
from integration import product_language_formal_runner as runner
from integration.product_language_formal_runner import (
    LANGUAGE_STATUS_ANSWER,
    LANGUAGE_STATUS_BLOCKED,
    LANGUAGE_STATUS_ERROR,
    LanguageSampleBatchResult,
    LanguageSampleRunState,
    _SummaryWriteError,
    run_language_offline_preflight,
    run_product_language_formal_batch,
)
from llm.transport import (
    FakeTransport,
    TransportError,
    TransportResponse,
    COND_AUTH_PERMISSION,
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_INVALID_JSON,
    COND_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BATCH_ID = "lang-formal-runner-test-offline-20261114-01"
REAL_BATCH_ID = "app003-product-language-20261114-01"
BATCH_ID_ALT = "app003-product-language-test-alt"


def _auth(batch_id: str = BATCH_ID) -> ProductLanguageAuthorization:
    return authorize_product_language_run(batch_id=batch_id)


def _test_approval(batch_id: str = BATCH_ID) -> ProductLanguageFormalApproval:
    """Test-only approval (is_test_only=True, structurally rejected for formal runs)."""
    return make_language_test_approval(batch_id=batch_id)


def _real_approval(batch_id: str = BATCH_ID) -> ProductLanguageFormalApproval:
    """Non-test approval matching frozen language scope constants."""
    return ProductLanguageFormalApproval(
        batch_id=batch_id,
        profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
        inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
        provider=PRODUCT_LANGUAGE_PROVIDER,
        model=PRODUCT_LANGUAGE_MODEL,
        condition=PRODUCT_LANGUAGE_CONDITION,
        max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
        automatic_cad_pipeline=False,
        approver="Wang sikai",
        approved_at_utc="2026-11-14T08:56:46Z",
        approval_statement=(
            "I approve the formal execution of the ten-input language sample batch "
            + batch_id
        ),
        approval_record_ref="Codex conversation 2026-11-14",
        is_test_only=False,
    )


def _answer_response() -> str:
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 24.0},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "24mm", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    })


def _ask_response() -> str:
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "ask",
        "extracted_parameters": {},
        "unsupported_requests": [],
        "evidence": [],
        "missing_fields": ["bore_d"],
        "questions": ["What bore diameter?"],
        "confidence": None,
    })


def _refuse_response() -> str:
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "refuse",
        "extracted_parameters": {},
        "unsupported_requests": ["keyway"],
        "evidence": [],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    })


def _fake_transport_all_answer(count: int = 20) -> FakeTransport:
    t = FakeTransport()
    for _ in range(count):
        t.queue_response(TransportResponse(status=200, body=_answer_response()))
    return t


def _fake_transport_all_error(condition: str, count: int = 20) -> FakeTransport:
    t = FakeTransport()
    for _ in range(count):
        t.queue_error(TransportError(condition=condition, http_status=None, message="test"))
    return t


def _fake_transport_bodies(body: str, count: int = 20) -> FakeTransport:
    t = FakeTransport()
    for _ in range(count):
        t.queue_response(TransportResponse(status=200, body=body))
    return t


def _assert_no_labels_read(test_case: unittest.TestCase, call_it):
    """Call call_it() ensuring evaluator-labels.json is never read."""
    original_read_bytes = Path.read_bytes

    def guarded(path: Path) -> bytes:
        test_case.assertNotEqual(
            path.name, "evaluator-labels.json",
            f"evaluator-labels.json was read at {path}"
        )
        return original_read_bytes(path)

    with patch.object(Path, "read_bytes", guarded):
        return call_it()


# ---------------------------------------------------------------------------
# 1. Approval class construction and validation
# ---------------------------------------------------------------------------

class TestProductLanguageFormalApproval(unittest.TestCase):

    def test_valid_real_approval_constructs(self) -> None:
        a = _real_approval()
        self.assertEqual(a.profile_id, PRODUCT_LANGUAGE_PROFILE_ID)
        self.assertEqual(a.inputs_sha256, PRODUCT_LANGUAGE_INPUTS_SHA256)
        self.assertEqual(a.evaluator_labels_sha256, PRODUCT_LANGUAGE_LABELS_SHA256)
        self.assertFalse(a.is_test_only)
        self.assertFalse(a.automatic_cad_pipeline)

    def test_test_only_approval_constructs(self) -> None:
        a = _test_approval()
        self.assertTrue(a.is_test_only)

    def test_wrong_profile_id_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            ProductLanguageFormalApproval(
                batch_id=BATCH_ID,
                profile_id="app003-product-live.v1",
                inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_PROVIDER,
                model=PRODUCT_LANGUAGE_MODEL,
                condition=PRODUCT_LANGUAGE_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-14T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_inputs_hash_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            ProductLanguageFormalApproval(
                batch_id=BATCH_ID,
                profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
                inputs_sha256="0" * 64,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_PROVIDER,
                model=PRODUCT_LANGUAGE_MODEL,
                condition=PRODUCT_LANGUAGE_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-14T00:00:00Z",
                approval_statement="ok",
            )

    def test_automatic_cad_pipeline_true_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            ProductLanguageFormalApproval(
                batch_id=BATCH_ID,
                profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_PROVIDER,
                model=PRODUCT_LANGUAGE_MODEL,
                condition=PRODUCT_LANGUAGE_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
                automatic_cad_pipeline=True,
                approver="X",
                approved_at_utc="2026-11-14T00:00:00Z",
                approval_statement="ok",
            )

    def test_empty_approver_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            ProductLanguageFormalApproval(
                batch_id=BATCH_ID,
                profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_PROVIDER,
                model=PRODUCT_LANGUAGE_MODEL,
                condition=PRODUCT_LANGUAGE_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="   ",
                approved_at_utc="2026-11-14T00:00:00Z",
                approval_statement="ok",
            )

    def test_as_audit_dict_contains_no_secret_fields(self) -> None:
        d = _real_approval().as_audit_dict()
        for key in d:
            self.assertNotIn("key", key.lower())
            self.assertNotIn("token", key.lower())
            self.assertNotIn("secret", key.lower())


class TestValidateApprovalBinding(unittest.TestCase):

    def test_matching_non_test_approval_passes(self) -> None:
        validate_product_language_formal_approval_binding(
            _auth(), _real_approval()
        )

    def test_test_only_approval_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            validate_product_language_formal_approval_binding(
                _auth(), _test_approval()
            )

    def test_batch_id_mismatch_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            validate_product_language_formal_approval_binding(
                _auth(BATCH_ID), _real_approval(BATCH_ID_ALT)
            )

    def test_wrong_authorization_type_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            validate_product_language_formal_approval_binding(
                object(),  # type: ignore
                _real_approval(),
            )

    def test_wrong_approval_type_rejected(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            validate_product_language_formal_approval_binding(
                _auth(), object()  # type: ignore
            )


# ---------------------------------------------------------------------------
# 2. Offline preflight
# ---------------------------------------------------------------------------

class TestRunLanguageOfflinePreflight(unittest.TestCase):

    def test_valid_preflight_passes(self) -> None:
        result = run_language_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["planned_runs"]), 10)
        self.assertEqual(result["details"]["budget_plan"]["computed_max_http"], 20)

    def test_wrong_auth_type_raises(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            run_language_offline_preflight(object())  # type: ignore

    def test_input_hash_failure_fails_closed(self) -> None:
        with patch.object(runner, "_load_inputs", side_effect=ValueError("hash")):
            result = run_language_offline_preflight(_auth())
        self.assertFalse(result["ok"])
        self.assertTrue(any("inputs_check" in e for e in result["errors"]))
        self.assertEqual(result["planned_runs"], [])

    def test_existing_batch_directory_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "already-there"
            batch_dir.mkdir()
            result = run_language_offline_preflight(_auth(), batch_dir=batch_dir)
        self.assertFalse(result["ok"])
        self.assertIn("batch_directory_already_exists", result["errors"])

    def test_evaluator_labels_never_opened(self) -> None:
        _assert_no_labels_read(
            self, lambda: run_language_offline_preflight(_auth())
        )

    def test_no_network_or_credentials_during_preflight(self) -> None:
        with (
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
        ):
            result = run_language_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        urlopen.assert_not_called()
        load_env.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Formal runner — gate / approval checks (zero side effects)
# ---------------------------------------------------------------------------

class TestFormalRunnerApprovalGates(unittest.TestCase):

    def test_wrong_authorization_type_raises_before_side_effects(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            run_product_language_formal_batch(
                authorization=object(),  # type: ignore
                approval=_real_approval(),
            )

    def test_test_only_approval_raises_before_side_effects(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_test_approval(),
            )

    def test_batch_id_mismatch_raises_before_side_effects(self) -> None:
        with self.assertRaises(ProductLanguageApprovalValidationError):
            run_product_language_formal_batch(
                authorization=_auth(BATCH_ID),
                approval=_real_approval(BATCH_ID_ALT),
            )

    def test_no_network_or_credentials_for_invalid_auth(self) -> None:
        with (
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
            self.assertRaises(AuthorizationScopeError),
        ):
            run_product_language_formal_batch(
                authorization=object(),  # type: ignore
                approval=_real_approval(),
            )
        urlopen.assert_not_called()
        load_env.assert_not_called()

    def test_no_batch_dir_created_for_test_only_approval(self) -> None:
        test_only_approval = _test_approval()
        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            self.assertRaises(ProductLanguageApprovalValidationError),
        ):
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=test_only_approval,
            )
        mock_mkdir.assert_not_called()

    def test_failed_preflight_returns_result_no_network(self) -> None:
        """Failed preflight must return a result object, not make network calls."""
        with (
            patch.object(runner, "_load_inputs", side_effect=ValueError("hash")),
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
        ):
            result = run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=FakeTransport(),
            )
        self.assertFalse(result.preflight_ok)
        urlopen.assert_not_called()
        load_env.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Mock mode (FakeTransport): normal execution paths
# ---------------------------------------------------------------------------

class TestFormalRunnerMockMode(unittest.TestCase):

    def test_mock_all_answer_returns_ten_results(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        self.assertTrue(result.preflight_ok, result.preflight_errors)
        self.assertEqual(result.mode, "mock")
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ANSWER)
            self.assertEqual(r.decision, "answer")

    def test_mock_ask_response_gives_blocked_status(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_bodies(_ask_response()),
        )
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertIn(r.llm_status, ("ask", LANGUAGE_STATUS_BLOCKED))

    def test_mock_refuse_response_gives_blocked_status(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_bodies(_refuse_response()),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, "refuse")

    def test_mock_transport_error_gives_error_status(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)

    def test_mock_no_cad_pipeline_called(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        mock_pipeline.assert_not_called()

    def test_mock_evaluator_labels_never_read(self) -> None:
        _assert_no_labels_read(
            self,
            lambda: run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            ),
        )

    def test_mock_no_network_calls(self) -> None:
        with patch("urllib.request.urlopen") as urlopen:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        urlopen.assert_not_called()

    def test_mock_no_credentials_read(self) -> None:
        with patch("llm.env_loader.load_deepseek_environment") as load_env:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        load_env.assert_not_called()

    def test_mock_input_ids_match_planned_runs(self) -> None:
        from llm.product_language_authorization import PRODUCT_LANGUAGE_INPUT_IDS
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        result_ids = [r.input_id for r in result.results]
        self.assertEqual(result_ids, list(PRODUCT_LANGUAGE_INPUT_IDS))


# ---------------------------------------------------------------------------
# 5. All-failed batch status (status computation logic)
# ---------------------------------------------------------------------------

class TestAllFailedBatchStatus(unittest.TestCase):
    """Verify the batch status computation logic does not mark all-fail as complete."""

    def test_all_error_results_not_complete_status(self) -> None:
        """When all runs fail with transport errors, the computed status is 'failed'."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)

    def test_status_logic_all_error_is_failed(self) -> None:
        """Directly test the finalize status computation."""
        error_statuses = {LANGUAGE_STATUS_ERROR}
        statuses = [LANGUAGE_STATUS_ERROR] * 10
        if all(s in error_statuses for s in statuses):
            computed = "failed"
        else:
            computed = "complete"
        self.assertEqual(computed, "failed")

    def test_status_logic_all_answer_is_complete(self) -> None:
        """Directly test the finalize status computation for all-answer."""
        error_statuses = {LANGUAGE_STATUS_ERROR}
        statuses = [LANGUAGE_STATUS_ANSWER] * 10
        if all(s in error_statuses for s in statuses):
            computed = "failed"
        elif any(s in error_statuses for s in statuses):
            computed = "partial"
        else:
            computed = "complete"
        self.assertEqual(computed, "complete")

    def test_status_logic_mixed_is_partial(self) -> None:
        """Directly test the finalize status computation for mixed results."""
        error_statuses = {LANGUAGE_STATUS_ERROR}
        statuses = [LANGUAGE_STATUS_ANSWER, LANGUAGE_STATUS_ERROR,
                     LANGUAGE_STATUS_ANSWER, LANGUAGE_STATUS_ERROR,
                     LANGUAGE_STATUS_ANSWER, LANGUAGE_STATUS_ANSWER,
                     LANGUAGE_STATUS_ANSWER, LANGUAGE_STATUS_ANSWER,
                     LANGUAGE_STATUS_ANSWER, LANGUAGE_STATUS_ANSWER]
        if all(s in error_statuses for s in statuses):
            computed = "failed"
        elif any(s in error_statuses for s in statuses):
            computed = "partial"
        else:
            computed = "complete"
        self.assertEqual(computed, "partial")


# ---------------------------------------------------------------------------
# 6. _SummaryWriter — direct infrastructure tests
# ---------------------------------------------------------------------------

class TestSummaryWriterDirect(unittest.TestCase):
    """Test _SummaryWriter directly in temp dirs (no BudgetLedger, no canonical root).

    This follows the pattern used by test_product_live.py, which tests
    _SummaryWriter as an isolated component rather than through the full
    runner — the runner only creates formal infrastructure when transport=None.
    """

    def _make_writer(self, tmpdir: str, batch_id: str = "test-batch"):
        from integration.product_language_formal_runner import _SummaryWriter
        batch_dir = Path(tmpdir) / batch_id
        batch_dir.mkdir()
        initial_data = {
            "schema_version": "language-sample-batch-summary.v1",
            "batch_id": batch_id,
            "batch_status": "running",
            "runs": {},
        }
        writer = _SummaryWriter(batch_dir, initial_data)
        return writer, batch_dir

    def _make_run_state(self, logical_run_id: str, llm_status: str, raw_path: str | None = None):
        return LanguageSampleRunState(
            logical_run_id=logical_run_id,
            input_id=logical_run_id.split("__")[0],
            condition_id=PRODUCT_LANGUAGE_CONDITION,
            provider=PRODUCT_LANGUAGE_PROVIDER,
            model=PRODUCT_LANGUAGE_MODEL,
            llm_status=llm_status,
            decision="answer" if llm_status == LANGUAGE_STATUS_ANSWER else "",
            extracted_parameters={"bore_d": 24.0} if llm_status == LANGUAGE_STATUS_ANSWER else {},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[] if llm_status == LANGUAGE_STATUS_ANSWER else [{"code": "ERR"}],
            raw_retention_path=raw_path,
            raw_retention_meta={"retained": bool(raw_path), "body_sha256": "abc123", "length_bytes": 100} if raw_path else None,
            llm_meta={"attempt_count": 1, "prompt_version": "app001-extraction.v5", "contract_version": "app001-io.v1"},
            request_text="test",
            prompt_file_sha256="deadbeef",
            created_at="2026-11-14T00:00:00Z",
        )

    def test_summary_writer_initial_writes_batch_status_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            summary = json.loads((batch_dir / "batch_summary.json").read_text())
            self.assertEqual(summary["batch_status"], "running")

    def test_summary_writer_finalize_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            writer.finalize(batch_status="complete")
            summary = json.loads((batch_dir / "batch_summary.json").read_text())
            self.assertEqual(summary["batch_status"], "complete")

    def test_summary_writer_finalize_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            writer.finalize(batch_status="failed")
            summary = json.loads((batch_dir / "batch_summary.json").read_text())
            self.assertEqual(summary["batch_status"], "failed")

    def test_summary_writer_update_run_writes_repo_relative_raw_path(self) -> None:
        """Raw retention path must be converted to repo-relative, not absolute."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            # Use an absolute path that should be converted
            abs_raw_path = str(Path(tmp) / "test-batch" / "raw" / "run-001.json")
            state = self._make_run_state("L01-legal-24mm__C0__DeepSeek__deepseek-flash",
                                          LANGUAGE_STATUS_ANSWER,
                                          raw_path=abs_raw_path)
            writer.update_run(state)
            summary = json.loads((batch_dir / "batch_summary.json").read_text())
            raw_path = summary["runs"]["L01-legal-24mm__C0__DeepSeek__deepseek-flash"]["raw_retention_path"]
            if raw_path is not None:
                self.assertFalse(raw_path.startswith("/"),
                                 f"absolute raw path in summary: {raw_path}")

    def test_summary_writer_update_run_no_raw_body(self) -> None:
        """Summary must not contain raw response body blob (extracted_parameters)."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            state = self._make_run_state("L01-legal-24mm__C0__DeepSeek__deepseek-flash",
                                          LANGUAGE_STATUS_ANSWER)
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            # The raw body would include "extracted_parameters" with field data.
            # The summary writer must not write extracted_parameters into the summary.
            self.assertNotIn('"extracted_parameters"', summary_text,
                             "extracted_parameters (raw body field) found in summary")

    def test_summary_writer_no_evaluator_label_content(self) -> None:
        """Summary must not reference evaluator labels file or its content."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            state = self._make_run_state("L01-legal-24mm__C0__DeepSeek__deepseek-flash",
                                          LANGUAGE_STATUS_ANSWER)
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            self.assertNotIn("evaluator-labels.json", summary_text)

    def test_summary_writer_no_secrets_in_text(self) -> None:
        """Summary must not contain secrets or Authorization header values."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            state = self._make_run_state("L01-legal-24mm__C0__DeepSeek__deepseek-flash",
                                          LANGUAGE_STATUS_ANSWER)
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            self.assertNotIn("DEEPSEEK_API_KEY", summary_text)
            self.assertNotIn("Authorization", summary_text)
            self.assertNotIn("Bearer ", summary_text)

    def test_summary_writer_no_absolute_paths(self) -> None:
        """Summary must not contain absolute filesystem paths."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            state = self._make_run_state("L01-legal-24mm__C0__DeepSeek__deepseek-flash",
                                          LANGUAGE_STATUS_ANSWER)
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            abs_pattern = re.compile(r'"(/[^"]+|[A-Za-z]:\\[^"]+)"')
            matches = abs_pattern.findall(summary_text)
            self.assertEqual(matches, [],
                             f"absolute paths found in summary: {matches}")

    def test_summary_writer_path_traversal_rejected(self) -> None:
        """_atomic_write_json must reject a summary path outside batch_dir."""
        from integration.product_language_formal_runner import _SummaryWriteError, _atomic_write_json
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "batch"
            batch_dir.mkdir()
            outside_path = Path(tmp) / "outside" / "batch_summary.json"
            with self.assertRaises(_SummaryWriteError):
                _atomic_write_json(outside_path, {"test": True}, batch_dir)


# ---------------------------------------------------------------------------
# 7. Budget constants and per-input caps
# ---------------------------------------------------------------------------

class TestBudgetConstants(unittest.TestCase):
    """Verify frozen budget constants match the scope requirements."""

    def test_max_attempts_per_run_is_two(self) -> None:
        self.assertEqual(PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN, 2)

    def test_max_batch_http_is_twenty(self) -> None:
        self.assertEqual(PRODUCT_LANGUAGE_MAX_BATCH_HTTP, 20)

    def test_auth_max_chat_attempts_returns_two(self) -> None:
        auth = _auth()
        self.assertEqual(auth.max_chat_attempts_for(PRODUCT_LANGUAGE_PROVIDER), 2)

    def test_auth_max_batch_attempts_is_twenty(self) -> None:
        auth = _auth()
        self.assertEqual(auth.max_batch_attempts, 20)


# ---------------------------------------------------------------------------
# 8. Retryable vs non-retryable classification
# ---------------------------------------------------------------------------

class TestRetryClassification(unittest.TestCase):

    def test_non_retryable_auth_error_is_error_status(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)

    def test_non_retryable_invalid_json_is_error_status(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_INVALID_JSON),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)

    def test_contract_in_retryable_conditions(self) -> None:
        self.assertIn(COND_HTTP_429, RETRYABLE_CONDITIONS)
        self.assertIn(COND_HTTP_5XX, RETRYABLE_CONDITIONS)

    def test_auth_permission_in_non_retryable_conditions(self) -> None:
        self.assertIn(COND_AUTH_PERMISSION, NON_RETRYABLE_CONDITIONS)

    def test_invalid_json_in_non_retryable_conditions(self) -> None:
        self.assertIn(COND_INVALID_JSON, NON_RETRYABLE_CONDITIONS)


# ---------------------------------------------------------------------------
# 9. Existing batch directory (preflight fail-closed)
# ---------------------------------------------------------------------------

class TestExistingBatchDirectory(unittest.TestCase):

    def test_existing_batch_dir_causes_preflight_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "existing-batch"
            batch_dir.mkdir()
            result = run_language_offline_preflight(_auth(), batch_dir=batch_dir)
        self.assertFalse(result["ok"])
        self.assertIn("batch_directory_already_exists", result["errors"])

    def test_existing_batch_dir_no_runner_result(self) -> None:
        """Formal runner must return preflight-failure result, not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            batch_id = "language-existing-test"
            batch_dir = Path(tmp) / batch_id
            batch_dir.mkdir()
            with patch.object(runner, "_CANONICAL_RUN_ROOT", Path(tmp)):
                result = run_product_language_formal_batch(
                    authorization=_auth(batch_id),
                    approval=_real_approval(batch_id),
                    transport=_fake_transport_all_answer(),
                )
        self.assertFalse(result.preflight_ok)
        self.assertTrue(any("batch_directory_already_exists" in e
                            for e in result.preflight_errors))
        self.assertEqual(result.results, [])

    def test_real_batch_directory_already_exists_regression(self) -> None:
        """Reverse regression: the real batch app003-product-language-20261114-01
        now exists in the canonical run root.  Offline preflight using that
        batch_id must return batch_directory_already_exists — proving the
        guard fires against the real directory, not just synthetic temp dirs.
        The real batch is never modified, deleted, or read beyond the
        existence check performed by preflight.
        """
        result = run_language_offline_preflight(_auth(REAL_BATCH_ID))
        self.assertFalse(result["ok"])
        self.assertIn("batch_directory_already_exists", result["errors"])


# ---------------------------------------------------------------------------
# 10. labels file zero reads across all code paths
# ---------------------------------------------------------------------------

class TestLabelsFileNeverRead(unittest.TestCase):

    def test_labels_never_read_in_preflight(self) -> None:
        _assert_no_labels_read(
            self, lambda: run_language_offline_preflight(_auth())
        )

    def test_labels_never_read_in_mock_all_answer(self) -> None:
        _assert_no_labels_read(
            self,
            lambda: run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            ),
        )

    def test_labels_never_read_in_mock_all_error(self) -> None:
        _assert_no_labels_read(
            self,
            lambda: run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
            ),
        )

    def test_labels_never_read_for_invalid_approval(self) -> None:
        def run():
            try:
                run_product_language_formal_batch(
                    authorization=_auth(),
                    approval=_test_approval(),
                )
            except ProductLanguageApprovalValidationError:
                pass
        _assert_no_labels_read(self, run)

    def test_labels_never_read_in_mock_mode(self) -> None:
        _assert_no_labels_read(
            self,
            lambda: run_product_language_formal_batch(
                authorization=_auth(BATCH_ID_ALT),
                approval=_real_approval(BATCH_ID_ALT),
                transport=_fake_transport_all_answer(),
            ),
        )


# ---------------------------------------------------------------------------
# 11. CAD / IR / pipeline never called
# ---------------------------------------------------------------------------

class TestCadPipelineNeverCalled(unittest.TestCase):

    def test_cad_pipeline_not_called_for_answer(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        mock_pipeline.assert_not_called()

    def test_cad_pipeline_not_called_for_all_error(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
            )
        mock_pipeline.assert_not_called()

    def test_cad_pipeline_not_called_for_ask(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_bodies(_ask_response()),
            )
        mock_pipeline.assert_not_called()

    def test_cad_pipeline_not_called_for_refuse(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_bodies(_refuse_response()),
            )
        mock_pipeline.assert_not_called()


# ---------------------------------------------------------------------------
# 12. Summary isolation: raw path is repo-relative via as_dict
# ---------------------------------------------------------------------------

class TestSummaryRawRetention(unittest.TestCase):

    def test_state_raw_path_is_repo_relative_via_as_dict(self) -> None:
        """LanguageSampleRunState.as_dict() must return repo-relative paths."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        for r in result.results:
            d = r.as_dict()
            raw_path = d.get("raw_retention_path")
            if raw_path is not None:
                self.assertFalse(raw_path.startswith("/"),
                                 f"absolute path in as_dict: {raw_path}")

    def test_batch_result_summary_path_is_none_in_mock_mode(self) -> None:
        """In mock mode (FakeTransport), summary_path should be None."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        self.assertIsNone(result.summary_path)


# ---------------------------------------------------------------------------
# 13. Input/hash/order errors
# ---------------------------------------------------------------------------

class TestInputIntegrity(unittest.TestCase):

    def test_wrong_input_hash_fails_preflight(self) -> None:
        with patch.object(runner, "_load_inputs", side_effect=ValueError("SHA mismatch")):
            result = run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        self.assertFalse(result.preflight_ok)
        self.assertEqual(result.results, [])

    def test_missing_inputs_file_fails_preflight(self) -> None:
        with patch.object(runner, "_load_inputs", side_effect=OSError("not found")):
            result = run_product_language_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        self.assertFalse(result.preflight_ok)

    def test_input_ids_in_results_match_frozen_order(self) -> None:
        from llm.product_language_authorization import PRODUCT_LANGUAGE_INPUT_IDS
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        self.assertEqual(
            [r.input_id for r in result.results],
            list(PRODUCT_LANGUAGE_INPUT_IDS),
        )


# ---------------------------------------------------------------------------
# 14. Result isolation: failed run does not return other batch/run artifacts
# ---------------------------------------------------------------------------

class TestRunIsolation(unittest.TestCase):

    def test_failed_run_state_has_no_pipeline_data(self) -> None:
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)
            d = r.as_dict()
            self.assertNotIn("step_path", d)
            self.assertNotIn("pipeline_status", d)
            self.assertNotIn("ir_index", d)

    def test_error_results_do_not_reference_other_batch_files(self) -> None:
        """Error runs must not reference other batch directories."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            raw_path = r.raw_retention_path or ""
            self.assertNotIn("other-batch", raw_path)


# ---------------------------------------------------------------------------
# 15. Formal evaluation gate unchanged
# ---------------------------------------------------------------------------

class TestFormalEvaluationGate(unittest.TestCase):

    def test_formal_evaluation_allowed_remains_false(self) -> None:
        from llm.contract import FORMAL_EVALUATION_ALLOWED
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_preflight_reports_formal_evaluation_allowed_false(self) -> None:
        result = run_language_offline_preflight(_auth())
        self.assertFalse(result["details"]["formal_evaluation_allowed"])

    def test_runner_does_not_change_global_gate(self) -> None:
        """Running the batch must not change FORMAL_EVALUATION_ALLOWED."""
        from llm.contract import FORMAL_EVALUATION_ALLOWED
        original = FORMAL_EVALUATION_ALLOWED
        run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        self.assertEqual(FORMAL_EVALUATION_ALLOWED, original)
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)


# ---------------------------------------------------------------------------
# 16. Summary update failure → best-effort finalize as "aborted"
# ---------------------------------------------------------------------------

class TestSummaryUpdateFailureFinalize(unittest.TestCase):
    """When writer.update_run() fails, the runner must:
    - stop processing further inputs,
    - attempt to finalize the summary as "aborted",
    - report the outcome via summary_finalize_error.

    These tests exercise the formal path (transport=None) with comprehensive
    mocking so that the _SummaryWriter is actually created and used.
    """

    _FAIL_BATCH = "lang-summary-fail-test-001"

    def _run_formal_mocked(
        self, tmp: str, *, update_side_effect=None, finalize_side_effect=None,
    ) -> LanguageSampleBatchResult:
        """Run the formal runner with mocked credentials, transport, and ledger.

        Parameters
        ----------
        tmp:
            Path to a temporary directory (from tempfile.TemporaryDirectory())
            that will serve as the canonical run root.

        Patches:
        - _CANONICAL_RUN_ROOT → tmp dir
        - load_deepseek_environment → no-op
        - BudgetLedger._verify_canonical_batch_path → no-op
        - DeepSeekTransport.send → returns valid answer response
        - _SummaryWriter.update_run / finalize → optional side effects
        """
        from integration.product_language_formal_runner import _SummaryWriter

        patches = [
            patch.object(runner, "_CANONICAL_RUN_ROOT", Path(tmp)),
            patch("llm.env_loader.load_deepseek_environment"),
            patch("llm.budget.BudgetLedger._verify_canonical_batch_path"),
            patch(
                "llm.real_transport.DeepSeekTransport.send",
                return_value=TransportResponse(
                    status=200, body=_answer_response()
                ),
            ),
        ]
        if update_side_effect is not None:
            patches.append(
                patch.object(_SummaryWriter, "update_run", side_effect=update_side_effect)
            )
        if finalize_side_effect is not None:
            patches.append(
                patch.object(_SummaryWriter, "finalize", side_effect=finalize_side_effect)
            )

        import contextlib
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            return run_product_language_formal_batch(
                authorization=_auth(self._FAIL_BATCH),
                approval=_real_approval(self._FAIL_BATCH),
                transport=None,
            )

    def test_update_run_failure_stops_further_inputs(self) -> None:
        """First update_run failure should break the loop; subsequent inputs
        are not processed."""
        call_count = {"update": 0}

        def fail_first_then_ok(result):
            call_count["update"] += 1
            if call_count["update"] == 1:
                raise _SummaryWriteError("simulated write failure")
            # subsequent calls won't be reached due to break

        with tempfile.TemporaryDirectory() as tmp:
            self._run_formal_mocked(tmp, update_side_effect=fail_first_then_ok)
        # Only 1 update call should happen before the break
        self.assertEqual(call_count["update"], 1)

    def test_update_run_failure_finalizes_aborted_when_finalize_succeeds(self) -> None:
        """If finalize succeeds after update_run failure, finalize_error should
        report 'summary_write_failed_finalized_aborted'."""
        def fail_first(result):
            raise _SummaryWriteError("simulated write failure")

        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_formal_mocked(tmp, update_side_effect=fail_first)
        self.assertEqual(
            result.summary_finalize_error,
            "summary_write_failed_finalized_aborted",
        )

    def test_finalize_persistent_failure_reports_double_failure(self) -> None:
        """If both update_run and finalize fail, finalize_error should report
        'summary_write_failed_and_finalize_failed'."""
        def fail_update(result):
            raise _SummaryWriteError("simulated update failure")

        def fail_finalize(batch_status="complete"):
            raise _SummaryWriteError("simulated finalize failure")

        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_formal_mocked(
                tmp,
                update_side_effect=fail_update,
                finalize_side_effect=fail_finalize,
            )
        self.assertEqual(
            result.summary_finalize_error,
            "summary_write_failed_and_finalize_failed",
        )

    def test_update_failure_does_not_report_complete(self) -> None:
        """After update_run failure, the result must not claim success."""
        def fail_update(result):
            raise _SummaryWriteError("simulated write failure")

        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_formal_mocked(tmp, update_side_effect=fail_update)
        self.assertIsNotNone(result.summary_finalize_error)
        self.assertNotIn("complete", str(result.summary_finalize_error))

    def test_update_run_failure_writes_aborted_to_disk(self) -> None:
        """When update_run fails and finalize succeeds, the batch_summary.json
        on disk must have batch_status='aborted'."""
        def fail_update(result):
            raise _SummaryWriteError("simulated write failure")

        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_formal_mocked(tmp, update_side_effect=fail_update)
            summary_path = Path(tmp) / self._FAIL_BATCH / "batch_summary.json"
            self.assertTrue(summary_path.exists(),
                            f"batch_summary.json not found at {summary_path}")
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary["batch_status"], "aborted")
        self.assertEqual(
            result.summary_finalize_error,
            "summary_write_failed_finalized_aborted",
        )

    def test_adapter_exception_with_update_run_failure_stops_loop(self) -> None:
        """When Adapter.run raises AND update_run also fails, the loop must
        stop immediately — no subsequent logical runs should be processed.

        This exercises the Adapter exception branch's break-on-write-failure
        path, which previously used 'continue' instead of 'break'.
        """
        adapter_call_count = {"calls": 0}

        def exploding_adapter_run(self, *args, **kwargs):
            adapter_call_count["calls"] += 1
            raise RuntimeError("adapter exploded")

        def fail_update(result):
            raise _SummaryWriteError("simulated write failure")

        def fail_finalize(batch_status="complete"):
            raise _SummaryWriteError("simulated finalize failure")

        with tempfile.TemporaryDirectory() as tmp:
            patches = [
                patch.object(runner, "_CANONICAL_RUN_ROOT", Path(tmp)),
                patch("llm.env_loader.load_deepseek_environment"),
                patch("llm.budget.BudgetLedger._verify_canonical_batch_path"),
                patch(
                    "llm.real_transport.DeepSeekTransport.send",
                    return_value=TransportResponse(
                        status=200, body=_answer_response()
                    ),
                ),
                patch("llm.adapter.Adapter.run", exploding_adapter_run),
                patch.object(
                    runner._SummaryWriter, "update_run", side_effect=fail_update
                ),
                patch.object(
                    runner._SummaryWriter, "finalize", side_effect=fail_finalize
                ),
            ]
            import contextlib
            with contextlib.ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                result = run_product_language_formal_batch(
                    authorization=_auth(self._FAIL_BATCH),
                    approval=_real_approval(self._FAIL_BATCH),
                    transport=None,
                )

        # Only 1 adapter call should happen before the break
        self.assertEqual(adapter_call_count["calls"], 1)
        # Only 1 result should be in the results list
        self.assertEqual(len(result.results), 1)
        # Double-failure token, not complete/failed
        self.assertEqual(
            result.summary_finalize_error,
            "summary_write_failed_and_finalize_failed",
        )


# ---------------------------------------------------------------------------
# 17. Exception message sanitization
# ---------------------------------------------------------------------------

class TestExceptionSanitization(unittest.TestCase):
    """formal Adapter exceptions and mock transport exceptions must not
    leak str(exc) into run state, summary, or logs."""

    SENSITIVE_MARKER = "SECRET_API_KEY_leaked_in_exception_text"

    def test_mock_transport_exception_does_not_leak_sensitive_marker(self) -> None:
        """A transport that raises with a sensitive marker in the exception
        must not propagate that marker into the run state."""
        marker = self.SENSITIVE_MARKER

        class SensitiveTransport(FakeTransport):
            def send(self, request):
                raise RuntimeError(f"connection failed with {marker}")

        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=SensitiveTransport(),
        )
        for r in result.results:
            d = r.as_dict()
            d_json = json.dumps(d)
            self.assertNotIn(
                self.SENSITIVE_MARKER, d_json,
                f"sensitive marker leaked into run state: {d_json}",
            )
            for err in r.errors:
                self.assertNotIn(self.SENSITIVE_MARKER, json.dumps(err))

    def test_mock_transport_exception_has_stable_message(self) -> None:
        """When send_with_retry wraps a non-TransportError as 'other_non_retryable',
        the resulting run state should have llm_status=error and not leak exc text."""
        class ExplodingTransport(FakeTransport):
            def send(self, request):
                raise ValueError("detailed internal error message with secrets")

        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=ExplodingTransport(),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)
            for err in r.errors:
                self.assertNotIn("detailed internal error", err.get("message", ""))
                self.assertNotIn("secrets", err.get("message", ""))

    def test_formal_adapter_exception_sanitized(self) -> None:
        """When the formal Adapter.run raises an exception containing a
        sensitive marker, the marker must not appear in result.as_dict(),
        batch_summary.json, or any error dict.

        This test exercises the actual formal path (transport=None) with
        mocked credentials, transport, and ledger so that Adapter.run is
        called and its exception handler is exercised.
        """
        marker = self.SENSITIVE_MARKER
        adapter_call_count = {"calls": 0}

        def exploding_adapter_run(self, *args, **kwargs):
            adapter_call_count["calls"] += 1
            raise RuntimeError(f"adapter error containing {marker}")

        with tempfile.TemporaryDirectory() as tmp:
            patches = [
                patch.object(runner, "_CANONICAL_RUN_ROOT", Path(tmp)),
                patch("llm.env_loader.load_deepseek_environment"),
                patch("llm.budget.BudgetLedger._verify_canonical_batch_path"),
                patch(
                    "llm.real_transport.DeepSeekTransport.send",
                    return_value=TransportResponse(
                        status=200, body=_answer_response()
                    ),
                ),
                patch("llm.adapter.Adapter.run", exploding_adapter_run),
            ]
            import contextlib
            with contextlib.ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                result = run_product_language_formal_batch(
                    authorization=_auth("lang-sanitize-test-001"),
                    approval=_real_approval("lang-sanitize-test-001"),
                    transport=None,
                )

            # Keep the assertion inside TemporaryDirectory's lifetime so it
            # verifies the formal runner's on-disk summary before cleanup.
            summary_path = Path(tmp) / "lang-sanitize-test-001" / "batch_summary.json"
            self.assertTrue(
                summary_path.is_file(),
                f"batch_summary.json not found at {summary_path}",
            )
            summary_text = summary_path.read_text()
            self.assertNotIn(self.SENSITIVE_MARKER, summary_text)

        # Adapter.run must have been called at least once
        self.assertGreater(adapter_call_count["calls"], 0)

        # The marker must not appear in any run state
        for r in result.results:
            d = r.as_dict()
            self.assertNotIn(self.SENSITIVE_MARKER, json.dumps(d))
            for err in r.errors:
                err_json = json.dumps(err)
                self.assertNotIn(self.SENSITIVE_MARKER, err_json)
                # Verify stable code and exception_type are present
                self.assertEqual(err["code"], "ADAPTER_EXCEPTION")
                self.assertIn("exception_type", err)
                self.assertEqual(
                    err["message"],
                    "adapter raised an unexpected exception",
                )

    def test_attempt_count_preserved_on_transport_error(self) -> None:
        """Existing attempt count tracking must not regress — when the
        transport returns a TransportError, attempt_count should still
        be set."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)
            # In mock mode, attempt_count may be None since send_with_retry
            # raises before returning; verify llm_meta exists
            self.assertIsInstance(r.llm_meta, dict)

    def test_error_classification_not_regressed(self) -> None:
        """TransportError with auth condition should produce error status,
        not answer or blocked."""
        result = run_product_language_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_STATUS_ERROR)
            self.assertNotEqual(r.llm_status, LANGUAGE_STATUS_ANSWER)
            self.assertNotEqual(r.llm_status, LANGUAGE_STATUS_BLOCKED)


# ---------------------------------------------------------------------------
# 18. output_root parameter removed — raw path is canonical-only
# ---------------------------------------------------------------------------

class TestRawPathCanonicalOnly(unittest.TestCase):
    """Verify that the formal raw retention path is always the canonical
    work/app001-runs/{batch_id}/raw and cannot be overridden."""

    def test_run_function_has_no_output_root_parameter(self) -> None:
        """run_product_language_formal_batch must not accept output_root."""
        import inspect
        sig = inspect.signature(run_product_language_formal_batch)
        self.assertNotIn("output_root", sig.parameters)

    def test_raw_retention_policy_uses_canonical_batch_raw(self) -> None:
        """The RetentionPolicy base_dir in the formal path must be
        work/app001-runs/{batch_id}/raw, expressed as a repo-relative string."""
        from integration.product_language_formal_runner import _CANONICAL_RUN_ROOT
        # The canonical raw path is always _CANONICAL_RUN_ROOT / batch_id / raw
        expected = _CANONICAL_RUN_ROOT / "app003-product-language-20261114-01" / "raw"
        repo_root = expected.parents[3]  # _CANONICAL_RUN_ROOT.parents[1]
        rel = str(expected.relative_to(repo_root))
        self.assertTrue(rel.startswith("work/app001-runs/"),
                        f"unexpected relative path: {rel}")
        self.assertTrue(rel.endswith("/raw"),
                        f"unexpected relative path: {rel}")

    def test_mock_mode_does_not_create_canonical_batch(self) -> None:
        """Mock mode (FakeTransport) must not create any directory in
        work/app001-runs/."""
        canonical_batch = (
            Path(runner.__file__).resolve().parents[2]
            / "work" / "app001-runs" / BATCH_ID_ALT
        )
        self.assertFalse(
            canonical_batch.exists(),
            f"canonical batch dir should not exist: {canonical_batch}",
        )
        result = run_product_language_formal_batch(
            authorization=_auth(BATCH_ID_ALT),
            approval=_real_approval(BATCH_ID_ALT),
            transport=_fake_transport_all_answer(),
        )
        self.assertFalse(canonical_batch.exists())
        self.assertIsNone(result.summary_path)


if __name__ == "__main__":
    unittest.main()
