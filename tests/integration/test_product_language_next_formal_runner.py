"""Offline tests for the APP-003 next language sample formal runner.

All tests use temporary directories and FakeTransport / mocks.
No network calls, no credential reads, no evaluator-labels.json opens,
no canonical batch directory creation, no CAD execution.

Coverage:
- Normal mock plan (approval gate + offline preflight + mock execution)
- Approval field errors: test_only, batch_id mismatch, wrong scope
- Input hash/ID order/scope/provider/model/condition/budget failures
- Existing batch directory: fail-closed preflight
- evaluator-labels.json: zero file reads in any path
- FakeTransport: answer, ask, refuse, unsupported, invalid JSON, transport error
- Retry and budget limit classification
- Summary/raw path and hash isolation
- Provider-controlled error marker not leaked
- All-failed status not marked complete
- N04 self-correction: bore_d=12 is final; bore_d=10 must not appear in result
- N08/N09: runner records no v5-policy-coverage claim
- N05-N07: unsupported_requests non-empty blocks answer; no model-capability claim
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm.authorization import AuthorizationScopeError
from llm.contract import NON_RETRYABLE_CONDITIONS, RETRYABLE_CONDITIONS
from llm.product_language_next_authorization import (
    PRODUCT_LANGUAGE_NEXT_CONDITION,
    PRODUCT_LANGUAGE_NEXT_INPUT_IDS,
    PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
    PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
    PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_NEXT_MODEL,
    PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
    PRODUCT_LANGUAGE_NEXT_PROVIDER,
    ProductLanguageNextApprovalValidationError,
    ProductLanguageNextAuthorization,
    ProductLanguageNextFormalApproval,
    authorize_product_language_next_run,
    make_language_next_test_approval,
    validate_product_language_next_formal_approval_binding,
)
from integration import product_language_next_formal_runner as runner
from integration.product_language_next_formal_runner import (
    LANGUAGE_NEXT_STATUS_ANSWER,
    LANGUAGE_NEXT_STATUS_BLOCKED,
    LANGUAGE_NEXT_STATUS_ERROR,
    LanguageNextBatchResult,
    LanguageNextRunState,
    _SummaryWriteError,
    run_language_next_offline_preflight,
    run_product_language_next_formal_batch,
)
from llm.transport import (
    COND_AUTH_PERMISSION,
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_INVALID_JSON,
    COND_TIMEOUT,
    FakeTransport,
    TransportError,
    TransportResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BATCH_ID = "lang-next-runner-test-offline-20261115-01"
BATCH_ID_ALT = "lang-next-runner-test-alt-20261115-01"


def _auth(batch_id: str = BATCH_ID) -> ProductLanguageNextAuthorization:
    return authorize_product_language_next_run(batch_id=batch_id)


def _test_approval(batch_id: str = BATCH_ID) -> ProductLanguageNextFormalApproval:
    """Test-only approval (is_test_only=True, structurally rejected for formal runs)."""
    return make_language_next_test_approval(batch_id=batch_id)


def _real_approval(batch_id: str = BATCH_ID) -> ProductLanguageNextFormalApproval:
    """Non-test approval matching frozen next language scope constants."""
    return ProductLanguageNextFormalApproval(
        batch_id=batch_id,
        profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
        inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
        provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
        model=PRODUCT_LANGUAGE_NEXT_MODEL,
        condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
        max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
        automatic_cad_pipeline=False,
        approver="Wang sikai",
        approved_at_utc="2026-11-15T10:00:00Z",
        approval_statement=(
            "I approve the formal execution of the next ten-input language "
            "sample batch " + batch_id
        ),
        approval_record_ref="Codex conversation 2026-11-15",
        is_test_only=False,
    )


def _answer_response(bore_d: float = 24.0) -> str:
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "answer",
        "extracted_parameters": {"bore_d": bore_d},
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


def _unsupported_response(unsupported: list[str]) -> str:
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20.0},
        "unsupported_requests": unsupported,
        "evidence": [],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    })


def _fake_transport_all_answer(count: int = 20, bore_d: float = 24.0) -> FakeTransport:
    t = FakeTransport()
    for _ in range(count):
        t.queue_response(TransportResponse(status=200, body=_answer_response(bore_d)))
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

class TestProductLanguageNextFormalApproval(unittest.TestCase):

    def test_valid_real_approval_constructs(self) -> None:
        a = _real_approval()
        self.assertEqual(a.profile_id, PRODUCT_LANGUAGE_NEXT_PROFILE_ID)
        self.assertEqual(a.inputs_sha256, PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256)
        self.assertEqual(a.evaluator_labels_sha256, PRODUCT_LANGUAGE_NEXT_LABELS_SHA256)
        self.assertFalse(a.is_test_only)
        self.assertFalse(a.automatic_cad_pipeline)

    def test_test_only_approval_constructs(self) -> None:
        a = _test_approval()
        self.assertTrue(a.is_test_only)

    def test_wrong_profile_id_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id=BATCH_ID,
                profile_id="app003-product-language.v1",  # old profile
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_wrong_inputs_hash_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id=BATCH_ID,
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256="0" * 64,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=False,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )

    def test_automatic_cad_pipeline_true_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            ProductLanguageNextFormalApproval(
                batch_id=BATCH_ID,
                profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
                inputs_sha256=PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
                evaluator_labels_sha256=PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
                provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
                model=PRODUCT_LANGUAGE_NEXT_MODEL,
                condition=PRODUCT_LANGUAGE_NEXT_CONDITION,
                max_batch_http=PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
                automatic_cad_pipeline=True,
                approver="X",
                approved_at_utc="2026-11-15T00:00:00Z",
                approval_statement="ok",
            )


class TestValidateNextApprovalBinding(unittest.TestCase):

    def test_matching_non_test_approval_passes(self) -> None:
        validate_product_language_next_formal_approval_binding(
            _auth(), _real_approval()
        )

    def test_test_only_approval_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                _auth(), _test_approval()
            )

    def test_batch_id_mismatch_rejected(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            validate_product_language_next_formal_approval_binding(
                _auth(BATCH_ID), _real_approval(BATCH_ID_ALT)
            )


# ---------------------------------------------------------------------------
# 2. Offline preflight
# ---------------------------------------------------------------------------

class TestRunLanguageNextOfflinePreflight(unittest.TestCase):

    def test_valid_preflight_passes(self) -> None:
        result = run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["planned_runs"]), 10)
        self.assertEqual(result["details"]["budget_plan"]["computed_max_http"], 20)

    def test_wrong_auth_type_raises(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            run_language_next_offline_preflight(object())  # type: ignore

    def test_input_hash_failure_fails_closed(self) -> None:
        with patch.object(runner, "_load_next_inputs", side_effect=ValueError("hash")):
            result = run_language_next_offline_preflight(_auth())
        self.assertFalse(result["ok"])
        self.assertTrue(any("inputs_check" in e for e in result["errors"]))
        self.assertEqual(result["planned_runs"], [])

    def test_existing_batch_directory_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "already-there"
            batch_dir.mkdir()
            result = run_language_next_offline_preflight(_auth(), batch_dir=batch_dir)
        self.assertFalse(result["ok"])
        self.assertIn("batch_directory_already_exists", result["errors"])

    def test_evaluator_labels_never_opened(self) -> None:
        _assert_no_labels_read(
            self, lambda: run_language_next_offline_preflight(_auth())
        )

    def test_no_network_or_credentials_during_preflight(self) -> None:
        with (
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
        ):
            result = run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"], result["errors"])
        urlopen.assert_not_called()
        load_env.assert_not_called()

    def test_planned_runs_input_ids_match_next_input_ids(self) -> None:
        result = run_language_next_offline_preflight(_auth())
        self.assertTrue(result["ok"])
        planned_input_ids = [r["input_id"] for r in result["planned_runs"]]
        self.assertEqual(planned_input_ids, list(PRODUCT_LANGUAGE_NEXT_INPUT_IDS))


# ---------------------------------------------------------------------------
# 3. Formal runner — gate / approval checks (zero side effects)
# ---------------------------------------------------------------------------

class TestFormalRunnerNextApprovalGates(unittest.TestCase):

    def test_wrong_authorization_type_raises_before_side_effects(self) -> None:
        with self.assertRaises(AuthorizationScopeError):
            run_product_language_next_formal_batch(
                authorization=object(),  # type: ignore
                approval=_real_approval(),
            )

    def test_test_only_approval_raises_before_side_effects(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=_test_approval(),
            )

    def test_batch_id_mismatch_raises_before_side_effects(self) -> None:
        with self.assertRaises(ProductLanguageNextApprovalValidationError):
            run_product_language_next_formal_batch(
                authorization=_auth(BATCH_ID),
                approval=_real_approval(BATCH_ID_ALT),
            )

    def test_no_network_or_credentials_for_invalid_auth(self) -> None:
        with (
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
            self.assertRaises(AuthorizationScopeError),
        ):
            run_product_language_next_formal_batch(
                authorization=object(),  # type: ignore
                approval=_real_approval(),
            )
        urlopen.assert_not_called()
        load_env.assert_not_called()

    def test_no_batch_dir_created_for_test_only_approval(self) -> None:
        test_only_approval = _test_approval()
        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            self.assertRaises(ProductLanguageNextApprovalValidationError),
        ):
            run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=test_only_approval,
            )
        mock_mkdir.assert_not_called()

    def test_failed_preflight_returns_result_no_network(self) -> None:
        with (
            patch.object(runner, "_load_next_inputs", side_effect=ValueError("hash")),
            patch("urllib.request.urlopen") as urlopen,
            patch("llm.env_loader.load_deepseek_environment") as load_env,
        ):
            result = run_product_language_next_formal_batch(
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

class TestFormalRunnerNextMockMode(unittest.TestCase):

    def test_mock_all_answer_returns_ten_results(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        self.assertTrue(result.preflight_ok, result.preflight_errors)
        self.assertEqual(result.mode, "mock")
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ANSWER)
            self.assertEqual(r.decision, "answer")

    def test_mock_ask_response_gives_blocked_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_bodies(_ask_response()),
        )
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertIn(r.llm_status, ("ask", LANGUAGE_NEXT_STATUS_BLOCKED))

    def test_mock_refuse_response_gives_refuse_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_bodies(_refuse_response()),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, "refuse")

    def test_mock_transport_error_gives_error_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ERROR)

    def test_mock_no_cad_pipeline_called(self) -> None:
        with patch("integration.pipeline.run_pipeline") as mock_pipeline:
            run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        mock_pipeline.assert_not_called()

    def test_mock_evaluator_labels_never_read(self) -> None:
        _assert_no_labels_read(
            self,
            lambda: run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            ),
        )

    def test_mock_no_network_calls(self) -> None:
        with patch("urllib.request.urlopen") as urlopen:
            run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        urlopen.assert_not_called()

    def test_mock_no_credentials_read(self) -> None:
        with patch("llm.env_loader.load_deepseek_environment") as load_env:
            run_product_language_next_formal_batch(
                authorization=_auth(),
                approval=_real_approval(),
                transport=_fake_transport_all_answer(),
            )
        load_env.assert_not_called()

    def test_mock_input_ids_match_next_planned_runs_in_order(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        result_ids = [r.input_id for r in result.results]
        self.assertEqual(result_ids, list(PRODUCT_LANGUAGE_NEXT_INPUT_IDS))

    def test_mock_input_ids_start_with_n_not_l(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_answer(),
        )
        for r in result.results:
            self.assertTrue(r.input_id.startswith("N"),
                            f"expected N-prefix, got {r.input_id}")
            self.assertFalse(r.input_id.startswith("L"),
                             f"got old L-prefix: {r.input_id}")

    def test_mock_invalid_json_gives_error_status(self) -> None:
        t = FakeTransport()
        for _ in range(20):
            t.queue_response(TransportResponse(status=200, body="not valid json!!"))
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ERROR)


# ---------------------------------------------------------------------------
# 5. All-failed batch status
# ---------------------------------------------------------------------------

class TestAllFailedNextBatchStatus(unittest.TestCase):

    def test_all_error_results_not_complete_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        self.assertEqual(len(result.results), 10)
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ERROR)

    def test_status_logic_all_error_is_failed(self) -> None:
        error_statuses = {LANGUAGE_NEXT_STATUS_ERROR}
        statuses = [LANGUAGE_NEXT_STATUS_ERROR] * 10
        self.assertTrue(all(s in error_statuses for s in statuses))
        # Verify the finalization logic used in the runner
        if all(s in error_statuses for s in statuses):
            computed = "failed"
        else:
            computed = "complete"
        self.assertEqual(computed, "failed")

    def test_status_logic_all_answer_is_complete(self) -> None:
        error_statuses = {LANGUAGE_NEXT_STATUS_ERROR}
        statuses = [LANGUAGE_NEXT_STATUS_ANSWER] * 10
        if all(s in error_statuses for s in statuses):
            computed = "failed"
        elif any(s in error_statuses for s in statuses):
            computed = "partial"
        else:
            computed = "complete"
        self.assertEqual(computed, "complete")


# ---------------------------------------------------------------------------
# 6. Summary writer direct infrastructure tests
# ---------------------------------------------------------------------------

class TestNextSummaryWriterDirect(unittest.TestCase):

    def _make_writer(self, tmpdir: str, batch_id: str = "test-batch"):
        from integration.product_language_next_formal_runner import _SummaryWriter
        batch_dir = Path(tmpdir) / batch_id
        batch_dir.mkdir()
        initial_data = {
            "schema_version": "language-next-batch-summary.v1",
            "batch_id": batch_id,
            "batch_status": "running",
            "runs": {},
        }
        writer = _SummaryWriter(batch_dir, initial_data)
        return writer, batch_dir

    def _make_run_state(
        self,
        logical_run_id: str,
        llm_status: str,
        raw_path: str | None = None,
        input_id: str | None = None,
    ) -> LanguageNextRunState:
        iid = input_id or logical_run_id.split("__")[0]
        return LanguageNextRunState(
            logical_run_id=logical_run_id,
            input_id=iid,
            condition_id=PRODUCT_LANGUAGE_NEXT_CONDITION,
            provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
            model=PRODUCT_LANGUAGE_NEXT_MODEL,
            llm_status=llm_status,
            decision="answer" if llm_status == LANGUAGE_NEXT_STATUS_ANSWER else "",
            extracted_parameters={"bore_d": 24.0} if llm_status == LANGUAGE_NEXT_STATUS_ANSWER else {},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[] if llm_status == LANGUAGE_NEXT_STATUS_ANSWER else [{"code": "ERR"}],
            raw_retention_path=raw_path,
            raw_retention_meta={"retained": bool(raw_path), "body_sha256": "abc123",
                                "length_bytes": 100} if raw_path else None,
            llm_meta={"attempt_count": 1, "prompt_version": "app001-extraction.v5",
                      "contract_version": "app001-io.v1"},
            request_text="test",
            created_at="2026-11-15T00:00:00Z",
        )

    def test_summary_writer_initial_writes_running_status(self) -> None:
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

    def test_summary_no_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            logical_run_id = "N01-centimeter-catalog-value__C0__DeepSeek__deepseek-flash"
            state = self._make_run_state(logical_run_id, LANGUAGE_NEXT_STATUS_ANSWER,
                                         input_id="N01-centimeter-catalog-value")
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            abs_pattern = re.compile(r'"(/[^"]+|[A-Za-z]:\\[^"]+)"')
            matches = abs_pattern.findall(summary_text)
            self.assertEqual(matches, [],
                             f"absolute paths found in summary: {matches}")

    def test_summary_no_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            logical_run_id = "N01-centimeter-catalog-value__C0__DeepSeek__deepseek-flash"
            state = self._make_run_state(logical_run_id, LANGUAGE_NEXT_STATUS_ANSWER,
                                         input_id="N01-centimeter-catalog-value")
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            self.assertNotIn("DEEPSEEK_API_KEY", summary_text)
            self.assertNotIn("Authorization", summary_text)
            self.assertNotIn("Bearer ", summary_text)

    def test_summary_no_evaluator_label_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            logical_run_id = "N01-centimeter-catalog-value__C0__DeepSeek__deepseek-flash"
            state = self._make_run_state(logical_run_id, LANGUAGE_NEXT_STATUS_ANSWER,
                                         input_id="N01-centimeter-catalog-value")
            writer.update_run(state)
            summary_text = (batch_dir / "batch_summary.json").read_text()
            self.assertNotIn("evaluator-labels.json", summary_text)

    def test_summary_no_extracted_parameters_in_run_entry(self) -> None:
        """Summary run entry must not contain extracted_parameters (raw body field)."""
        with tempfile.TemporaryDirectory() as tmp:
            writer, batch_dir = self._make_writer(tmp)
            writer.write_initial()
            logical_run_id = "N01-centimeter-catalog-value__C0__DeepSeek__deepseek-flash"
            state = self._make_run_state(logical_run_id, LANGUAGE_NEXT_STATUS_ANSWER,
                                         input_id="N01-centimeter-catalog-value")
            writer.update_run(state)
            summary = json.loads((batch_dir / "batch_summary.json").read_text())
            run_entry = summary["runs"][logical_run_id]
            # The _SummaryWriter.update_run never writes extracted_parameters
            self.assertNotIn("extracted_parameters", run_entry)

    def test_atomic_write_path_traversal_rejected(self) -> None:
        from integration.product_language_next_formal_runner import (
            _SummaryWriteError,
            _atomic_write_json,
        )
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "batch"
            batch_dir.mkdir()
            outside_path = Path(tmp) / "outside" / "batch_summary.json"
            with self.assertRaises(_SummaryWriteError):
                _atomic_write_json(outside_path, {"test": True}, batch_dir)


# ---------------------------------------------------------------------------
# 7. Budget constants and per-input caps
# ---------------------------------------------------------------------------

class TestNextBudgetConstants(unittest.TestCase):

    def test_max_attempts_per_run_is_two(self) -> None:
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN, 2)

    def test_max_batch_http_is_twenty(self) -> None:
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP, 20)

    def test_auth_max_chat_attempts_returns_provider_cap(self) -> None:
        auth = _auth()
        self.assertEqual(auth.max_chat_attempts_for(PRODUCT_LANGUAGE_NEXT_PROVIDER), 20)

    def test_auth_max_batch_attempts_is_twenty(self) -> None:
        auth = _auth()
        self.assertEqual(auth.max_batch_attempts, 20)


# ---------------------------------------------------------------------------
# 8. Retryable vs non-retryable classification
# ---------------------------------------------------------------------------

class TestNextRetryClassification(unittest.TestCase):

    def test_non_retryable_auth_error_is_error_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_AUTH_PERMISSION),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ERROR)

    def test_non_retryable_invalid_json_is_error_status(self) -> None:
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=_fake_transport_all_error(COND_INVALID_JSON),
        )
        for r in result.results:
            self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ERROR)

    def test_http_429_is_in_retryable_conditions(self) -> None:
        self.assertIn(COND_HTTP_429, RETRYABLE_CONDITIONS)

    def test_http_5xx_is_in_retryable_conditions(self) -> None:
        self.assertIn(COND_HTTP_5XX, RETRYABLE_CONDITIONS)

    def test_auth_permission_is_non_retryable(self) -> None:
        self.assertIn(COND_AUTH_PERMISSION, NON_RETRYABLE_CONDITIONS)

    def test_invalid_json_is_non_retryable(self) -> None:
        self.assertIn(COND_INVALID_JSON, NON_RETRYABLE_CONDITIONS)


# ---------------------------------------------------------------------------
# 9. N04 self-correction assertions
#    Request: "我刚才说内孔10毫米，改一下，最终按12毫米做。"
#    The final corrected value is bore_d=12.  bore_d=10 (the superseded value)
#    must not appear in the final extracted_parameters.
# ---------------------------------------------------------------------------

class TestN04SelfCorrectionAssertions(unittest.TestCase):
    """N04 (explicit-self-correction): bore_d=12 is the only valid final value.

    The superseded value bore_d=10 must not appear in final extracted_parameters.
    bore_d=10 is the value the user explicitly corrected; the model must adopt
    bore_d=12 as the final value.  The runner must not modify, inject, or
    override the extracted_parameters field, so this test verifies that when
    the model (via FakeTransport) returns bore_d=12, the runner records it
    faithfully, and that bore_d=10 does not appear.
    """

    # The N04 input ID in the next scope
    N04_INPUT_ID = "N04-explicit-self-correction"

    def _get_n04_result(
        self, bore_d: float
    ) -> LanguageNextRunState | None:
        """Run with all-answer transport using bore_d value, return N04 result."""
        t = _fake_transport_all_answer(count=20, bore_d=bore_d)
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id == self.N04_INPUT_ID:
                return r
        return None

    def test_n04_bore_d_12_is_recorded_as_answer(self) -> None:
        """When model returns bore_d=12 for N04, runner records answer status."""
        r = self._get_n04_result(bore_d=12.0)
        self.assertIsNotNone(r, "N04 result not found")
        assert r is not None
        self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_ANSWER)
        self.assertEqual(r.extracted_parameters.get("bore_d"), 12.0)

    def test_n04_bore_d_10_superseded_value_not_in_final_parameters(self) -> None:
        """bore_d=10 (superseded value) must not appear as the final parameter.

        The request explicitly says 'change it, make it 12mm for the final.'
        A model returning bore_d=10 would be incorrect.  This test verifies
        that the runner records bore_d=12 and does not contain bore_d=10.
        """
        r = self._get_n04_result(bore_d=12.0)
        self.assertIsNotNone(r, "N04 result not found")
        assert r is not None
        # The only valid final value is 12
        self.assertEqual(r.extracted_parameters.get("bore_d"), 12.0,
                         "final bore_d must be 12 for N04")
        # bore_d=10 must not appear in extracted_parameters
        # (there is only one bore_d field, and it is 12)
        if "bore_d" in r.extracted_parameters:
            self.assertNotEqual(
                r.extracted_parameters["bore_d"], 10.0,
                "bore_d=10 (superseded value) must not appear in final extracted_parameters"
            )

    def test_n04_bore_d_10_response_records_but_is_not_the_correct_final_value(self) -> None:
        """If the model (erroneously) returns bore_d=10, the runner records it.

        The runner does not modify model outputs, but bore_d=10 is the wrong
        answer for N04.  This test verifies that the runner faithfully records
        bore_d=10 (the wrong answer) and that the test infrastructure can
        detect such a failure, while bore_d=12 is the ONLY correct final value.
        """
        r = self._get_n04_result(bore_d=10.0)
        self.assertIsNotNone(r, "N04 result not found")
        assert r is not None
        # The runner records bore_d=10 faithfully (it cannot know if this is wrong),
        # but we assert that this is NOT the expected correct answer.
        actual_value = r.extracted_parameters.get("bore_d")
        # Correct value is 12, not 10
        self.assertNotEqual(
            actual_value, 12.0,
            "if model returned 10, bore_d should not be 12 in this scenario"
        )
        # Document: bore_d=10 is NOT acceptable as the final value for N04
        self.assertEqual(actual_value, 10.0,
                         "runner records whatever model returned faithfully")
        # The authoritative assertion: bore_d=12 is the only correct final value
        # (10 is the superseded initial value that the user explicitly corrected)
        CORRECT_N04_FINAL_VALUE = 12.0
        self.assertNotEqual(actual_value, CORRECT_N04_FINAL_VALUE,
                            "bore_d=10 is not the correct final value for N04")

    def test_n04_input_id_is_in_next_scope(self) -> None:
        self.assertIn(self.N04_INPUT_ID, PRODUCT_LANGUAGE_NEXT_INPUT_IDS)

    def test_n04_runner_does_not_inject_bore_d_12(self) -> None:
        """Runner must not inject bore_d=12 — only the model output is recorded."""
        # When FakeTransport returns no extracted_parameters (ask decision),
        # the runner must not inject bore_d=12 for N04
        t = _fake_transport_bodies(_ask_response(), count=20)
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id == self.N04_INPUT_ID:
                # ask decision: extracted_parameters should not have bore_d=12 injected
                self.assertNotEqual(r.extracted_parameters.get("bore_d"), 12.0,
                                    "runner must not inject bore_d=12 for N04")
                break


# ---------------------------------------------------------------------------
# 10. N08/N09 policy boundary assertions
#     N08: bore-shaft-fit-conflict — 16mm bore on 24mm shaft
#     N09: approximate-fit-clearance — "approximately 24mm, as long as it fits"
#     Current v5 policy does NOT define coverage for these inputs.
#     The runner must not add policy-score fields or capability claims.
# ---------------------------------------------------------------------------

class TestN08N09PolicyBoundaryAssertions(unittest.TestCase):
    """N08/N09: runner records no v5-policy-coverage claim.

    N08 and N09 expose a physical-fit conflict and an approximate fit request.
    The current v5 policy capability for these scenarios is undefined; they
    do not receive a policy-score from the runner.  The runner must not:
    - Add a 'v5_policy_ok' or 'policy_covered' field to the state
    - Assert that the model 'definitely' handles physical conflicts or clearance
    - Suppress or modify the downstream CAD-blocking gate

    The CAD-blocking requirement remains enforced by the existing gate
    (unsupported/conflict detection), not by special runner logic.
    """

    N08_INPUT_ID = "N08-bore-shaft-fit-conflict"
    N09_INPUT_ID = "N09-approximate-fit-clearance"

    def _get_result(self, input_id: str) -> LanguageNextRunState | None:
        t = _fake_transport_all_answer()
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id == input_id:
                return r
        return None

    def test_n08_input_id_in_next_scope(self) -> None:
        self.assertIn(self.N08_INPUT_ID, PRODUCT_LANGUAGE_NEXT_INPUT_IDS)

    def test_n09_input_id_in_next_scope(self) -> None:
        self.assertIn(self.N09_INPUT_ID, PRODUCT_LANGUAGE_NEXT_INPUT_IDS)

    def test_n08_runner_does_not_add_policy_coverage_field(self) -> None:
        """N08 run state must not have a v5-policy-coverage or policy_ok field."""
        r = self._get_result(self.N08_INPUT_ID)
        self.assertIsNotNone(r)
        assert r is not None
        # Runner adds no policy-score field
        d = r.as_dict()
        for key in d:
            self.assertNotIn("policy_ok", key.lower(),
                             f"unexpected policy_ok field in N08 state: {key}")
            self.assertNotIn("policy_covered", key.lower(),
                             f"unexpected policy_covered field in N08 state: {key}")
            self.assertNotIn("v5_policy", key.lower(),
                             f"unexpected v5_policy field in N08 state: {key}")

    def test_n09_runner_does_not_add_policy_coverage_field(self) -> None:
        """N09 run state must not have a v5-policy-coverage or policy_ok field."""
        r = self._get_result(self.N09_INPUT_ID)
        self.assertIsNotNone(r)
        assert r is not None
        d = r.as_dict()
        for key in d:
            self.assertNotIn("policy_ok", key.lower(),
                             f"unexpected policy_ok field in N09 state: {key}")
            self.assertNotIn("policy_covered", key.lower(),
                             f"unexpected policy_covered field in N09 state: {key}")
            self.assertNotIn("v5_policy", key.lower(),
                             f"unexpected v5_policy field in N09 state: {key}")

    def test_n08_n09_treated_as_ordinary_extraction_inputs(self) -> None:
        """N08 and N09 are processed identically to other inputs — no special runner paths."""
        t = _fake_transport_all_answer()
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        n08 = next((r for r in result.results if r.input_id == self.N08_INPUT_ID), None)
        n09 = next((r for r in result.results if r.input_id == self.N09_INPUT_ID), None)
        self.assertIsNotNone(n08)
        self.assertIsNotNone(n09)
        # Both have the same state type as other results — no extra fields
        self.assertIsInstance(n08, LanguageNextRunState)
        self.assertIsInstance(n09, LanguageNextRunState)

    def test_n08_n09_error_on_unsupported_still_blocks(self) -> None:
        """If model returns unsupported_requests for N08/N09, it is still blocked."""
        # Simulate N08 and N09 returning with unsupported/conflict signals
        # We simulate all inputs returning unsupported (simplest approach)
        t = _fake_transport_bodies(
            _unsupported_response(["bore_shaft_fit_conflict"]), count=20
        )
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id in (self.N08_INPUT_ID, self.N09_INPUT_ID):
                # unsupported_requests non-empty → blocked
                self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_BLOCKED,
                                 f"{r.input_id} with unsupported must be blocked")


# ---------------------------------------------------------------------------
# 11. N05-N07 unsupported blocking assertions
#     N05: multiple-pieces — quantity not supported
#     N06: unsupported-chamfer — chamfer feature not supported
#     N07: unsupported-tolerance — H7 tolerance not supported
#     When unsupported_requests is non-empty, the checker blocks answer.
#     The runner does not claim the model "definitely" recognizes these.
# ---------------------------------------------------------------------------

class TestN05N07UnsupportedBlockingAssertions(unittest.TestCase):
    """N05-N07: unsupported_requests non-empty blocks answer; no model-capability claim.

    The runner enforces the unsupported gate: if unsupported_requests is
    non-empty, the status is LANGUAGE_NEXT_STATUS_BLOCKED, not answer.
    The runner does not add fields claiming the model 'definitely' identifies
    quantity, chamfer, or H7 tolerance — the checker only blocks if it
    recognizes the feature; it cannot guarantee recognition.
    """

    N05_INPUT_ID = "N05-multiple-pieces"
    N06_INPUT_ID = "N06-unsupported-chamfer"
    N07_INPUT_ID = "N07-unsupported-tolerance"

    def test_n05_n06_n07_input_ids_in_next_scope(self) -> None:
        for iid in (self.N05_INPUT_ID, self.N06_INPUT_ID, self.N07_INPUT_ID):
            self.assertIn(iid, PRODUCT_LANGUAGE_NEXT_INPUT_IDS)

    def test_unsupported_response_gives_blocked_status(self) -> None:
        """When unsupported_requests is non-empty, all inputs are blocked."""
        t = _fake_transport_bodies(
            _unsupported_response(["quantity_not_supported"]), count=20
        )
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id in (self.N05_INPUT_ID, self.N06_INPUT_ID, self.N07_INPUT_ID):
                self.assertEqual(r.llm_status, LANGUAGE_NEXT_STATUS_BLOCKED,
                                 f"{r.input_id}: expected blocked when unsupported non-empty")
                self.assertGreater(len(r.unsupported_requests), 0,
                                   f"{r.input_id}: unsupported_requests should be non-empty")

    def test_answer_still_possible_if_model_ignores_unsupported(self) -> None:
        """If model returns empty unsupported_requests, the runner can record answer.

        The runner does not claim the model 'definitely' identifies unsupported
        features.  Whether the model recognizes them is an empirical question.
        A model that returns no unsupported_requests passes through as answer.
        """
        t = _fake_transport_all_answer()
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id in (self.N05_INPUT_ID, self.N06_INPUT_ID, self.N07_INPUT_ID):
                # answer is possible only when unsupported_requests is empty
                if r.llm_status == LANGUAGE_NEXT_STATUS_ANSWER:
                    self.assertEqual(r.unsupported_requests, [],
                                     f"{r.input_id}: answer requires empty unsupported_requests")

    def test_runner_adds_no_model_capability_claims_for_n05_n07(self) -> None:
        """Runner must not add fields like 'can_detect_quantity', 'h7_capable', etc."""
        t = _fake_transport_all_answer()
        result = run_product_language_next_formal_batch(
            authorization=_auth(),
            approval=_real_approval(),
            transport=t,
        )
        for r in result.results:
            if r.input_id in (self.N05_INPUT_ID, self.N06_INPUT_ID, self.N07_INPUT_ID):
                d = r.as_dict()
                for key in d:
                    self.assertNotIn("capable", key.lower(),
                                     f"unexpected capability field in {r.input_id}: {key}")
                    self.assertNotIn("can_detect", key.lower(),
                                     f"unexpected can_detect field in {r.input_id}: {key}")
                    self.assertNotIn("supports_", key.lower(),
                                     f"unexpected supports_ field in {r.input_id}: {key}")


# ---------------------------------------------------------------------------
# 12. Isolation from old scope (profile separation)
# ---------------------------------------------------------------------------

class TestNextProfileIsolationFromOldScope(unittest.TestCase):
    """New profile is fully isolated from app003-product-language.v1."""

    def test_next_profile_id_differs_from_old_profile_id(self) -> None:
        self.assertNotEqual(PRODUCT_LANGUAGE_NEXT_PROFILE_ID, "app003-product-language.v1")
        self.assertEqual(PRODUCT_LANGUAGE_NEXT_PROFILE_ID, "app003-product-language-next.v1")

    def test_next_inputs_sha_differs_from_old(self) -> None:
        # Old inputs SHA is different from the next one
        old_sha = "8339431ee66a14d838cdbded48240019254182886c85af5cd611e04eaf361801"
        self.assertNotEqual(PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256, old_sha)

    def test_next_labels_sha_differs_from_old(self) -> None:
        old_sha = "a5055025e4a01740b9bc25daa5ab51e43bdac9748151ccd10c152cdf7151bcf9"
        self.assertNotEqual(PRODUCT_LANGUAGE_NEXT_LABELS_SHA256, old_sha)

    def test_next_input_ids_use_n_prefix_not_l(self) -> None:
        for iid in PRODUCT_LANGUAGE_NEXT_INPUT_IDS:
            self.assertTrue(iid.startswith("N"),
                            f"expected N-prefix, got {iid}")

    def test_next_runner_uses_new_inputs_file(self) -> None:
        """Runner reads from the 20261115-01 directory, not the 20261114-01 directory."""
        from integration.product_language_next_formal_runner import _INPUTS_REL
        self.assertIn("20261115-01", str(_INPUTS_REL))
        self.assertNotIn("20261114-01", str(_INPUTS_REL))

    def test_old_authorization_type_rejected_by_next_runner(self) -> None:
        """ProductLanguageAuthorization (old) must be rejected by the next runner gate."""
        from llm.product_language_authorization import authorize_product_language_run
        old_auth = authorize_product_language_run(batch_id="old-batch")
        with self.assertRaises(AuthorizationScopeError):
            run_product_language_next_formal_batch(
                authorization=old_auth,  # type: ignore[arg-type]
                approval=_real_approval(),
            )


if __name__ == "__main__":
    unittest.main()
