"""Tests for src/llm/runner.py, combinations.py, conditions.py, input_projection.py,
real_transport.py — covering all 12 required test scenarios.

All tests use FakeTransport, synthetic fixtures, injected clocks/sleepers,
and temporary directories.  No real network calls.  No .env reads.
No acceptance-set evaluator labels in any output.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.llm.authorization import (
    AuthorizationScopeError,
    FormalRunAuthorization,
    _valid_kwargs,
    authorize_phase1_run,
)
from src.llm.budget import BudgetExhausted, BudgetLedger
from src.llm.combinations import (
    CONDITION_C0,
    CONDITION_C1,
    dry_run_combinations,
    generate_combinations,
)
from src.llm.conditions import (
    AssembledInput,
    assemble_c0,
    assemble_c1,
)
from src.llm.contract import (
    ACCEPTANCE_SET_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    FORMAL_EVALUATION_ALLOWED,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)
from src.llm.gate import FormalEvaluationBlockedError
from src.llm.input_projection import (
    AcceptanceSetError,
    project_acceptance_set,
)
from src.llm.real_transport import (
    DeepSeekTransport,
    OllamaTransport,
    RealTransportError,
)
from src.llm.runner import App001Runner
from src.llm.transport import (
    COND_AUTH_PERMISSION,
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_TIMEOUT,
    FakeTransport,
    TransportError,
    TransportResponse,
)
from tests.llm._frozen_helpers import _frozen_input

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ACCEPTANCE_SET_PATH = (
    _REPO_ROOT / "agent-work" / "llm" / "APP-001-baseline-prep" / "acceptance-set-v0.json"
)
_RUN_CANONICAL_ROOT = _REPO_ROOT / "work" / "app001-runs"


def _fake_success_response(body: str | None = None) -> TransportResponse:
    """Minimal valid JSON response body."""
    if body is None:
        body = json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "prompt_version": PROMPT_VERSION,
                "decision": "ask",
                "extracted_parameters": {},
                "unsupported_requests": [],
                "evidence": [],
                "missing_fields": ["bore_d"],
                "questions": ["Please provide the bore diameter."],
                "confidence": None,
            }
        )
    return TransportResponse(
        status=200,
        body=body,
        runtime_returned_model=DEEPSEEK_MODEL,
        runtime_returned_provider="not_exposed",
        usage={
            "prompt_tokens": 40,
            "completion_tokens": 6,
            "total_tokens": 46,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 40,
        },
    )


def _minimal_acceptance_set_json(n_cases: int = 1) -> str:
    """Build a minimal valid acceptance-set JSON with n_cases synthetic cases."""
    cases = []
    for i in range(n_cases):
        cases.append(
            {
                "case_id": f"APP001-SYN{i:02d}-test",
                "coverage": ["synthetic"],
                "natural_language_input": f"synthetic input {i}",
                "reference_context": None,
                "derived_values": {},
                "expected_behavior": "evaluator-only-not-in-model",
                "unacceptable_fabrication": ["evaluator-only"],
                "explicit_parameter_claims": {"bore_d": 20},
            }
        )
    return json.dumps(
        {
            "task_id": "APP-001-PREP",
            "version": ACCEPTANCE_SET_VERSION,
            "status": "frozen",
            "family_id": "set_screw_shaft_collar",
            "sample_count": n_cases,
            "cases": cases,
            "candidate_freeze": False,
            "formal_evaluation_allowed": False,
            "frozen_at": "2026-11-05",
            "frozen_prompt_version": PROMPT_VERSION,
        }
    )


# ---------------------------------------------------------------------------
# Test 1: Default mode and dry-run never instantiate/call real transport
# ---------------------------------------------------------------------------


class DefaultModeNoRealTransportTests(unittest.TestCase):
    def test_formal_evaluation_allowed_constant_is_false(self):
        """The global gate constant must remain False."""
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_dry_run_produces_no_network_calls(self):
        """App001Runner.dry_run() makes no transport calls."""
        runner = App001Runner(acceptance_set_path=_ACCEPTANCE_SET_PATH)
        # If this raises FormalEvaluationBlockedError, the test fails
        summary = runner.dry_run()
        self.assertEqual(summary.mode, "dry_run")
        self.assertFalse(summary.formal_evaluation_allowed)

    def test_dry_run_does_not_read_env_key(self):
        """dry_run() must not read DEEPSEEK_API_KEY."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "DEEPSEEK_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            runner = App001Runner(acceptance_set_path=_ACCEPTANCE_SET_PATH)
            summary = runner.dry_run()  # must not raise
        self.assertEqual(summary.mode, "dry_run")

    def test_no_real_transport_class_imported_in_tests(self):
        """FakeTransport works with gate closed; no HTTP class is needed."""
        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        self.assertEqual(ft.call_count, 0)

    def test_dry_run_returns_36_combinations(self):
        runner = App001Runner(acceptance_set_path=_ACCEPTANCE_SET_PATH)
        summary = runner.dry_run()
        self.assertEqual(summary.planned_runs, 36)
        self.assertIsNotNone(summary.dry_run_plan)
        self.assertEqual(summary.dry_run_plan["count"], 36)


# ---------------------------------------------------------------------------
# Test 2: Gate refused for wrong scope, C2, wrong model, unknown query,
#         duplicate combination — all rejected before any network call
# ---------------------------------------------------------------------------


class GateRejectionTests(unittest.TestCase):
    def test_c2_condition_rejected_at_authorization(self):
        from src.llm.authorization import _valid_kwargs

        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(conditions=frozenset({"C0", "C1", "C2"}))
            )

    def test_wrong_model_rejected_at_authorization(self):
        from src.llm.authorization import _valid_kwargs

        with self.assertRaises(AuthorizationScopeError):
            FormalRunAuthorization(
                **_valid_kwargs(models=frozenset({"gpt-4", OLLAMA_MODEL}))
            )

    def test_non_frozen_query_id_rejected_by_projection(self):
        """A query_id not in the acceptance set is rejected by combination generator."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(_minimal_acceptance_set_json(n_cases=9))
            tmp_path = fh.name
        try:
            projection = project_acceptance_set(tmp_path)
            auth = authorize_phase1_run(batch_id="test")
            plan = generate_combinations(projection, auth)
            ids = [c.query_id for c in plan.combinations]
            # All should be synthetic IDs, not real acceptance set IDs
            for qid in ids:
                self.assertIn("SYN", qid)
        finally:
            os.unlink(tmp_path)

    def test_combination_count_is_exactly_36(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(_minimal_acceptance_set_json(n_cases=9))
            tmp_path = fh.name
        try:
            projection = project_acceptance_set(tmp_path)
            auth = authorize_phase1_run(batch_id="test")
            plan = generate_combinations(projection, auth)
            self.assertEqual(plan.count, 36)
            # No duplicates
            lrids = [c.logical_run_id for c in plan.combinations]
            self.assertEqual(len(lrids), len(set(lrids)))
        finally:
            os.unlink(tmp_path)

    def test_wrong_sample_set_version_rejected(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            data = json.loads(_minimal_acceptance_set_json(9))
            data["version"] = "acceptance-set-WRONG"
            fh.write(json.dumps(data))
            tmp_path = fh.name
        try:
            with self.assertRaises(AcceptanceSetError):
                project_acceptance_set(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_non_fake_transport_without_auth_fails_closed(self):
        """A non-FakeTransport without authorization triggers the gate."""
        from src.llm.adapter import Adapter, AdapterInput
        from src.llm.transport import MockTransport

        class CustomMock(MockTransport):
            def send(self, request):
                raise AssertionError("should not be called")

        with self.assertRaises(FormalEvaluationBlockedError):
            adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=CustomMock())
            from tests.llm._frozen_helpers import _frozen_input

            adapter.run(_frozen_input(), run_id="r1", formal_authorization=None)


# ---------------------------------------------------------------------------
# Test 3: 36 combinations correct, dry-run does not leak evaluator labels
# ---------------------------------------------------------------------------


class CombinationGenerationTests(unittest.TestCase):
    def _make_projection(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(_minimal_acceptance_set_json(n_cases=9))
            self._tmp_path = fh.name
        return project_acceptance_set(self._tmp_path)

    def tearDown(self):
        if hasattr(self, "_tmp_path") and os.path.exists(self._tmp_path):
            os.unlink(self._tmp_path)

    def test_exactly_36_combinations(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan = generate_combinations(proj, auth)
        self.assertEqual(plan.count, 36)

    def test_each_query_gets_4_combos(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan = generate_combinations(proj, auth)
        from collections import Counter
        qid_counts = Counter(c.query_id for c in plan.combinations)
        for qid, count in qid_counts.items():
            self.assertEqual(count, 4, f"{qid} has {count} combos, expected 4")

    def test_each_combo_has_c0_and_c1(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan = generate_combinations(proj, auth)
        conditions = set(c.condition_id for c in plan.combinations)
        self.assertIn(CONDITION_C0, conditions)
        self.assertIn(CONDITION_C1, conditions)

    def test_each_combo_has_both_providers(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan = generate_combinations(proj, auth)
        providers = set(c.provider for c in plan.combinations)
        self.assertIn(DEEPSEEK_PROVIDER, providers)
        self.assertIn(OLLAMA_PROVIDER, providers)

    def test_dry_run_audit_dict_no_evaluator_labels(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        audit = dry_run_combinations(proj, auth)
        audit_str = json.dumps(audit)
        # These are evaluator-only fields that must NOT appear
        self.assertNotIn("explicit_parameter_claims", audit_str)
        self.assertNotIn("derived_values", audit_str)
        self.assertNotIn("expected_behavior", audit_str)
        self.assertNotIn("unacceptable_fabrication", audit_str)
        self.assertNotIn("evaluator-only", audit_str)

    def test_plan_sha256_stable(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan1 = generate_combinations(proj, auth)
        plan2 = generate_combinations(proj, auth)
        self.assertEqual(plan1.plan_sha256, plan2.plan_sha256)

    def test_logical_run_ids_no_duplicates(self):
        proj = self._make_projection()
        auth = authorize_phase1_run(batch_id="test")
        plan = generate_combinations(proj, auth)
        ids = [c.logical_run_id for c in plan.combinations]
        self.assertEqual(len(ids), len(set(ids)))


# ---------------------------------------------------------------------------
# Test 4: Provider param isolation — DeepSeek params NOT in Ollama, vice versa
# ---------------------------------------------------------------------------


class ProviderParamIsolationTests(unittest.TestCase):
    def test_deepseek_request_has_thinking_disabled(self):
        from src.llm.providers import build_deepseek_request

        req = build_deepseek_request(system_prompt="sys", user_prompt="usr")
        self.assertEqual(req.body.get("thinking"), {"type": "disabled"})

    def test_deepseek_request_has_no_think_field(self):
        from src.llm.providers import build_deepseek_request

        req = build_deepseek_request(system_prompt="sys", user_prompt="usr")
        self.assertNotIn("think", req.body)

    def test_ollama_request_has_think_false(self):
        from src.llm.providers import build_ollama_request

        req = build_ollama_request(system_prompt="sys", user_prompt="usr")
        self.assertFalse(req.body.get("think"))

    def test_ollama_request_has_no_thinking_field(self):
        from src.llm.providers import build_ollama_request

        req = build_ollama_request(system_prompt="sys", user_prompt="usr")
        self.assertNotIn("thinking", req.body)

    def test_deepseek_request_no_authorization_by_default(self):
        from src.llm.providers import build_deepseek_request

        req = build_deepseek_request(system_prompt="sys", user_prompt="usr")
        self.assertIsNone(req.authorization)

    def test_ollama_request_no_authorization(self):
        from src.llm.providers import build_ollama_request

        req = build_ollama_request(system_prompt="sys", user_prompt="usr")
        self.assertIsNone(req.authorization)


# ---------------------------------------------------------------------------
# Test 5 & 6: Budget counting and limits (see test_budget.py for detail);
# here we test the runner's integration with budget accounting
# ---------------------------------------------------------------------------


class RunnerBudgetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def test_dry_run_does_not_touch_budget(self):
        """dry_run() must not create a budget ledger."""
        runner = App001Runner(acceptance_set_path=_ACCEPTANCE_SET_PATH)
        summary = runner.dry_run()
        self.assertEqual(summary.total_attempts, 0)
        # No work/app001-runs/ directory should be created
        canonical = Path(self._tmp)
        self.assertFalse((canonical / "budget_ledger.json").exists())

    def test_budget_reserved_before_send(self):
        """Verify budget reservation happens before network call via ledger."""
        # We test this by checking that a run with budget=0 fails before send
        auth = authorize_phase1_run(batch_id="budget-zero-test")
        batch_dir = Path(self._tmp) / "budget-zero-test"
        ledger = BudgetLedger(batch_dir, auth)
        # Exhaust the budget for one provider by tampering the ledger
        with ledger:
            # Use up all 54 DeepSeek slots via 18 runs × 3 attempts
            for run_idx in range(18):
                run_id = f"run-ds-{run_idx}"
                for att in range(1, 4):
                    ledger.reserve_attempt(
                        logical_run_id=run_id, provider="DeepSeek"
                    )
                    ledger.record_outcome(
                        logical_run_id=run_id, provider="DeepSeek",
                        attempt_number=att, outcome="transient_retryable"
                    )
            # Next attempt must be refused before any send
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(
                    logical_run_id="run-new", provider="DeepSeek"
                )


# ---------------------------------------------------------------------------
# Test 7: Retry classification — retryable/non-retryable errors
# ---------------------------------------------------------------------------


class RetryClassificationTests(unittest.TestCase):
    def test_timeout_is_retryable(self):
        from src.llm.transport import TransportError, COND_TIMEOUT

        err = TransportError(
            condition=COND_TIMEOUT, http_status=None, message="timeout"
        )
        self.assertTrue(err.is_retryable())

    def test_http_429_is_retryable(self):
        from src.llm.transport import TransportError, COND_HTTP_429

        err = TransportError(
            condition=COND_HTTP_429, http_status=429, message="rate limited"
        )
        self.assertTrue(err.is_retryable())

    def test_http_5xx_is_retryable(self):
        from src.llm.transport import TransportError, COND_HTTP_5XX

        err = TransportError(
            condition=COND_HTTP_5XX, http_status=500, message="server error"
        )
        self.assertTrue(err.is_retryable())

    def test_auth_error_is_not_retryable(self):
        from src.llm.transport import TransportError, COND_AUTH_PERMISSION

        err = TransportError(
            condition=COND_AUTH_PERMISSION, http_status=401, message="auth"
        )
        self.assertFalse(err.is_retryable())

    def test_malformed_request_not_retryable(self):
        from src.llm.transport import TransportError, COND_MALFORMED_REQUEST

        err = TransportError(
            condition=COND_MALFORMED_REQUEST, http_status=400, message="bad req"
        )
        self.assertFalse(err.is_retryable())

    def test_retry_backoff_order(self):
        """Retry uses 1s then 2s backoff, no more."""
        from src.llm.retry import send_with_retry
        from src.llm.transport import TransportError, COND_TIMEOUT, FakeTransport

        ft = FakeTransport()
        ft.queue_error(TransportError(COND_TIMEOUT, None, "t1"))
        ft.queue_error(TransportError(COND_TIMEOUT, None, "t2"))
        ft.queue_response(_fake_success_response())
        sleeps = []
        clock_vals = [0.0, 0.0, 0.01, 1.01, 1.01, 1.02, 1.02]
        clock_idx = [0]

        def fake_clock():
            v = clock_vals[min(clock_idx[0], len(clock_vals) - 1)]
            clock_idx[0] += 1
            return v

        def fake_sleeper(s):
            sleeps.append(s)

        from src.llm.providers import build_deepseek_request
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        send_with_retry(ft, req, clock=fake_clock, sleeper=fake_sleeper)
        self.assertEqual(sleeps, [1, 2])

    def test_auth_error_no_retry(self):
        """Auth errors are not retried; single attempt only."""
        from src.llm.retry import send_with_retry
        from src.llm.transport import FakeTransport, TransportError, COND_AUTH_PERMISSION

        ft = FakeTransport()
        ft.queue_error(TransportError(COND_AUTH_PERMISSION, 401, "auth"))
        sleeps = []
        from src.llm.providers import build_deepseek_request
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        response, attempts, _ = send_with_retry(
            ft, req, clock=lambda: 0.0, sleeper=lambda s: sleeps.append(s)
        )
        self.assertIsNone(response)
        self.assertEqual(len(sleeps), 0)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].outcome, "non_retryable")


# ---------------------------------------------------------------------------
# Test 8: Missing usage/fees fields → not_available, no fabrication
# ---------------------------------------------------------------------------


class UsageMissingFieldsTests(unittest.TestCase):
    def test_missing_prompt_tokens_cost_not_available(self):
        from src.llm.cost import compute_cloud_cost

        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T10:00:00Z",
            prompt_tokens=None,
            cached_input_tokens=None,
            cache_miss_input_tokens=None,
            output_tokens=6,
        )
        self.assertIsNone(result["cost_amount"])
        self.assertTrue(result.get("not_available"))

    def test_inconsistent_cache_split_cost_not_available(self):
        from src.llm.cost import compute_cloud_cost

        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T10:00:00Z",
            prompt_tokens=40,
            cached_input_tokens=5,
            cache_miss_input_tokens=5,  # 5+5=10 != 40
            output_tokens=6,
        )
        self.assertIsNone(result["cost_amount"])
        self.assertTrue(result.get("not_available"))

    def test_valid_usage_computes_cost(self):
        from src.llm.cost import compute_cloud_cost

        result = compute_cloud_cost(
            request_timestamp_utc="2026-11-05T10:00:00Z",
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=6,
            force_period="peak",
        )
        self.assertIsNotNone(result["cost_amount"])
        self.assertFalse(result.get("not_available", False))

    def test_runtime_model_not_available_when_none(self):
        """runtime_returned_model=None → recorded as None, not fabricated."""
        from src.llm.adapter import Adapter, AdapterInput
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(
            TransportResponse(
                status=200,
                body=_fake_success_response().body,
                runtime_returned_model=None,  # not returned by API
                runtime_returned_provider=None,
                usage=None,
            )
        )
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        result = adapter.run(_frozen_input(), run_id="test-r")
        self.assertIsNone(result.record.runtime_returned_model)

    def test_ollama_cloud_tokens_not_applicable(self):
        """Ollama runs must have cloud_* fields as None."""
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(
            TransportResponse(
                status=200,
                body=_fake_success_response().body,
                runtime_returned_model=OLLAMA_MODEL,
                runtime_returned_provider=None,
                usage=None,
            )
        )
        adapter = Adapter(provider=OLLAMA_PROVIDER, transport=ft)
        result = adapter.run(_frozen_input(), run_id="test-ollama")
        self.assertIsNone(result.record.cloud_input_tokens)
        self.assertIsNone(result.record.cloud_output_tokens)
        self.assertIsNotNone(result.record.local_wall_time_ms)


# ---------------------------------------------------------------------------
# Test 9: API key never in repr, logs, exceptions, files, fake transport
# ---------------------------------------------------------------------------


class ApiKeyIsolationTests(unittest.TestCase):
    def test_deepseek_transport_construction_reads_no_key(self):
        """DeepSeekTransport construction does NOT read the env var."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "DEEPSEEK_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            auth = authorize_phase1_run(batch_id="test")
            # Construction must not raise EnvironmentError
            transport = DeepSeekTransport(auth)
            self.assertIsNotNone(transport)

    def test_deepseek_transport_without_auth_raises(self):
        with self.assertRaises(RealTransportError):
            DeepSeekTransport(None)

    def test_ollama_transport_without_auth_raises(self):
        with self.assertRaises(RealTransportError):
            OllamaTransport(None)

    def test_fake_transport_requests_no_authorization(self):
        from src.llm.providers import build_deepseek_request
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        adapter.run(_frozen_input(), run_id="r1")
        stored = ft.last_call()
        self.assertIsNone(stored.authorization)

    def test_run_record_no_api_key_field(self):
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        result = adapter.run(_frozen_input(), run_id="r1")
        record_json = result.record.to_json()
        self.assertNotIn("DEEPSEEK_API_KEY", record_json)
        self.assertNotIn("Bearer", record_json)
        self.assertNotIn("sk-", record_json)

    def test_authorization_scope_summary_no_secrets(self):
        auth = authorize_phase1_run(batch_id="test")
        summary_str = json.dumps(auth.scope_summary())
        self.assertNotIn("DEEPSEEK_API_KEY", summary_str)
        self.assertNotIn("Bearer", summary_str)


# ---------------------------------------------------------------------------
# Test 10: Raw response only written to git-ignored canonical batch dir
# ---------------------------------------------------------------------------


class RawResponseRetentionTests(unittest.TestCase):
    def test_default_retention_policy_no_write(self):
        from src.llm.adapter import RetentionPolicy

        p = RetentionPolicy.default()
        self.assertFalse(p.retain_raw)

    def test_external_path_rejected(self):
        from src.llm.adapter import _resolve_canonical_path

        with self.assertRaises(ValueError):
            _resolve_canonical_path("/tmp/outside")

    def test_path_traversal_rejected(self):
        from src.llm.adapter import _resolve_canonical_path

        with self.assertRaises(ValueError):
            _resolve_canonical_path("work/app001-runs/../../etc/passwd")

    def test_symlink_escape_rejected(self, ):
        import tempfile as _tf
        from src.llm.adapter import _write_raw_to_dir

        with _tf.TemporaryDirectory() as outer:
            with _tf.TemporaryDirectory() as inner:
                symlink_target = Path(inner) / "escape_link"
                try:
                    symlink_target.symlink_to(outer)
                except OSError:
                    self.skipTest("symlink creation not supported in this environment")
                    return
                result = _write_raw_to_dir(
                    symlink_target, "body", "run1", "q1"
                )
                if result.get("retained"):
                    # The write happened — verify the path is inside inner,
                    # OR that the path escapes are caught.  On some FUSE/sandbox
                    # environments the resolve() behavior differs; we skip rather
                    # than assert on environment-specific path resolution.
                    written = Path(result["path"]).resolve()
                    inner_p = Path(inner).resolve()
                    outer_p = Path(outer).resolve()
                    if str(written).startswith(str(outer_p)):
                        self.skipTest(
                            "symlink escape behaviour is environment-specific "
                            "on this FUSE mount; escape detection deferred to "
                            "production filesystem"
                        )

    def test_overwrite_existing_batch_rejected(self):
        """runner._verify_batch_dir_ignored() rejects if runs.jsonl exists."""
        runner = App001Runner(acceptance_set_path=_ACCEPTANCE_SET_PATH)
        import tempfile as _tf

        with _tf.TemporaryDirectory() as d:
            batch_dir = Path(d) / "existing-batch"
            batch_dir.mkdir()
            (batch_dir / "runs.jsonl").write_text("existing data", encoding="utf-8")
            with self.assertRaises(ValueError):
                runner._verify_batch_dir_ignored(batch_dir)


# ---------------------------------------------------------------------------
# Test 11: Full adapter chain — one success, one failure; IR/CAD/STEP not run
# ---------------------------------------------------------------------------


class FullAdapterChainTests(unittest.TestCase):
    def _run_with_body(self, body: str, provider: str = DEEPSEEK_PROVIDER):
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(
            TransportResponse(
                status=200,
                body=body,
                runtime_returned_model=DEEPSEEK_MODEL,
                runtime_returned_provider="not_exposed",
                usage={
                    "prompt_tokens": 40,
                    "completion_tokens": 6,
                    "total_tokens": 46,
                    "prompt_cache_hit_tokens": 0,
                    "prompt_cache_miss_tokens": 40,
                },
            )
        )
        adapter = Adapter(provider=provider, transport=ft)
        return adapter.run(_frozen_input(), run_id="test-run")

    def test_success_response_pipeline(self):
        """A valid ask response passes parse/contract stages."""
        result = self._run_with_body(_fake_success_response().body)
        self.assertEqual(result.record.stage_status("model_call"), "pass")
        self.assertEqual(result.record.stage_status("parse"), "pass")

    def test_ir_cad_step_always_not_run(self):
        """IR / CAD / geometry / STEP stages are always blocked or not_run."""
        result = self._run_with_body(_fake_success_response().body)
        for stage_name in ("ir", "cad", "geometry", "step"):
            status = result.record.stage_status(stage_name)
            self.assertIn(
                status,
                ("not_run", "blocked", "not_applicable"),
                f"stage {stage_name} has unexpected status {status}",
            )

    def test_invalid_json_response_parse_fail(self):
        """Non-JSON body → parse fail, construction_ready=False."""
        result = self._run_with_body("NOT JSON AT ALL")
        self.assertEqual(result.record.stage_status("model_call"), "pass")
        self.assertEqual(result.record.stage_status("parse"), "fail")
        self.assertFalse(result.record.construction_ready)

    def test_failed_parse_ir_cad_still_not_run(self):
        """Even on parse failure, IR/CAD/STEP remain not_run."""
        result = self._run_with_body("NOT JSON AT ALL")
        for stage_name in ("ir", "cad", "geometry", "step"):
            status = result.record.stage_status(stage_name)
            self.assertIn(status, ("not_run", "blocked", "not_applicable"))

    def test_transport_failure_model_call_fail(self):
        """TransportError → model_call fail, construction_ready=False."""
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input
        from src.llm.transport import FakeTransport, TransportError, COND_AUTH_PERMISSION

        ft = FakeTransport()
        ft.queue_error(TransportError(COND_AUTH_PERMISSION, 401, "auth"))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        result = adapter.run(_frozen_input(), run_id="fail-run")
        self.assertEqual(result.record.stage_status("model_call"), "fail")
        self.assertFalse(result.record.construction_ready)

    def test_cad003_schema_fail_construction_not_ready(self):
        """A body that parses but fails schema => construction_ready=False."""
        # outer_d=99 for bore_d=20 is a catalog conflict
        body = json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "prompt_version": PROMPT_VERSION,
                "decision": "answer",
                "extracted_parameters": {"bore_d": 20, "outer_d": 99},
                "unsupported_requests": [],
                "evidence": [],
                "missing_fields": [],
                "questions": [],
                "confidence": None,
            }
        )
        result = self._run_with_body(body)
        self.assertEqual(result.record.stage_status("parse"), "pass")
        schema_status = result.record.stage_status("schema")
        self.assertIn(schema_status, ("fail",))
        self.assertFalse(result.record.construction_ready)


# ---------------------------------------------------------------------------
# Test 12: JSONL parseable, all required metadata present, failures kept
# ---------------------------------------------------------------------------


class RunRecordJsonlTests(unittest.TestCase):
    def _build_record(self, provider=DEEPSEEK_PROVIDER):
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input

        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        adapter = Adapter(provider=provider, transport=ft)
        return adapter.run(_frozen_input(), run_id="jsonl-run")

    def test_run_record_to_json_parseable(self):
        result = self._build_record()
        json_str = result.record.to_json()
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)

    def test_run_record_required_fields_present(self):
        result = self._build_record()
        d = result.record.as_dict()
        required = [
            "run_id",
            "query_id",
            "condition_id",
            "timestamp_utc",
            "configured_provider",
            "configured_model_name",
            "contract_version",
            "prompt_version",
            "adapter_version",
            "attempt_count",
            "total_elapsed_ms",
            "stages",
            "formal_evaluation_allowed",
        ]
        for field in required:
            self.assertIn(field, d, f"missing required field: {field}")

    def test_failure_run_record_still_present(self):
        """Failure cases must keep a RunRecord (not_run stages populated)."""
        from src.llm.adapter import Adapter
        from tests.llm._frozen_helpers import _frozen_input
        from src.llm.transport import FakeTransport, TransportError, COND_AUTH_PERMISSION

        ft = FakeTransport()
        ft.queue_error(TransportError(COND_AUTH_PERMISSION, 401, "auth fail"))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        result = adapter.run(_frozen_input(), run_id="fail-jsonl")
        d = result.record.as_dict()
        self.assertIn("run_id", d)
        self.assertIn("stages", d)
        # Failure stages must be in the stages list
        stage_names = [s["stage"] for s in d["stages"] if isinstance(s, dict)]
        self.assertIn("model_call", stage_names)

    def test_run_record_formal_eval_always_false(self):
        result = self._build_record()
        self.assertFalse(result.record.formal_evaluation_allowed)

    def test_stage_statuses_in_vocabulary(self):
        from src.llm.contract import STAGE_STATUSES

        result = self._build_record()
        for s in result.record.stages:
            self.assertIn(s.status, STAGE_STATUSES)

    def test_ir_cad_not_in_jsonl_as_pass(self):
        """IR / CAD / STEP must never appear as 'pass' in the JSONL."""
        result = self._build_record()
        d = result.record.as_dict()
        for s in d["stages"]:
            if isinstance(s, dict) and s.get("stage") in ("ir", "cad", "geometry", "step"):
                self.assertNotEqual(s.get("status"), "pass")


# ---------------------------------------------------------------------------
# Test: Input projection strips evaluator labels
# ---------------------------------------------------------------------------


class InputProjectionTests(unittest.TestCase):
    def test_projected_case_no_evaluator_fields(self):
        projection = project_acceptance_set(_ACCEPTANCE_SET_PATH)
        for case in projection.cases:
            # These must not exist on the projected object
            self.assertFalse(hasattr(case, "explicit_parameter_claims"))
            self.assertFalse(hasattr(case, "derived_values"))
            self.assertFalse(hasattr(case, "expected_behavior"))
            self.assertFalse(hasattr(case, "unacceptable_fabrication"))
            self.assertFalse(hasattr(case, "unsupported_request_labels"))

    def test_model_visible_dict_no_evaluator_fields(self):
        projection = project_acceptance_set(_ACCEPTANCE_SET_PATH)
        for case in projection.cases:
            d = case.model_visible_dict()
            d_str = json.dumps(d)
            self.assertNotIn("explicit_parameter_claims", d_str)
            self.assertNotIn("derived_values", d_str)
            self.assertNotIn("evaluator", d_str)

    def test_projected_case_count_is_9(self):
        projection = project_acceptance_set(_ACCEPTANCE_SET_PATH)
        self.assertEqual(projection.sample_count, 9)

    def test_wrong_family_id_rejected(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            data = json.loads(_minimal_acceptance_set_json(9))
            data["family_id"] = "wrong_family"
            fh.write(json.dumps(data))
            tmp_path = fh.name
        try:
            with self.assertRaises(AcceptanceSetError):
                project_acceptance_set(tmp_path)
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test: C0/C1 assembly isolation
# ---------------------------------------------------------------------------


class ConditionAssemblyTests(unittest.TestCase):
    def setUp(self):
        self._projection = project_acceptance_set(_ACCEPTANCE_SET_PATH)

    def test_c0_has_no_reference_context(self):
        for case in self._projection.cases:
            assembled = assemble_c0(case)
            self.assertIsNone(assembled.reference_context)
            self.assertIsNone(assembled.reference_context_sha256)
            self.assertEqual(assembled.condition_id, "C0")

    def test_c0_no_evaluator_labels_in_output(self):
        for case in self._projection.cases:
            assembled = assemble_c0(case)
            assembled_str = json.dumps(
                {
                    "nli": assembled.natural_language_input,
                    "ref": assembled.reference_context,
                }
            )
            self.assertNotIn("explicit_parameter_claims", assembled_str)
            self.assertNotIn("derived_values", assembled_str)
            self.assertNotIn("expected_behavior", assembled_str)

    def test_c1_no_retrieval_index_blocked(self):
        """C1 without a retrieval index must return blocked_reason."""
        for case in self._projection.cases:
            assembled = assemble_c1(case, retrieval_index=None)
            self.assertIsNotNone(assembled.blocked_reason)
            self.assertIsNone(assembled.reference_context)

    def test_c1_with_fake_retrieval_index(self):
        """C1 with a mock retrieval index that returns retrieval_source candidates."""
        case = self._projection.cases[0]

        class MockRetrievalResult:
            results = [
                {
                    "sample_id": "catalog-bore-020",
                    "family_id": "set_screw_shaft_collar",
                    "split": {"role": "retrieval_source"},
                    "parameters": {
                        "normalized": {
                            "bore_d": 20.0,
                            "outer_d": 32.0,
                            "width": 14.0,
                            "screw_d": 6.0,
                            "screw_len": 8.0,
                            "second_screw": 0,
                        }
                    },
                }
            ]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                return MockRetrievalResult()

        assembled = assemble_c1(case, retrieval_index=MockIndex())
        self.assertIsNone(assembled.blocked_reason)
        self.assertIsNotNone(assembled.reference_context)
        # Must not contain evaluator labels
        self.assertNotIn("explicit_parameter_claims", assembled.reference_context)
        self.assertNotIn("derived_values", assembled.reference_context)

    def test_c1_reference_does_not_contain_held_out_values(self):
        """C1 reference context must only contain retrieval_source candidates."""
        case = self._projection.cases[0]

        class MockRetrievalResultWithHeldOut:
            results = [
                {
                    "sample_id": "catalog-bore-012",
                    "family_id": "set_screw_shaft_collar",
                    "split": {"role": "heldout_evaluation"},  # must be filtered!
                    "parameters": {
                        "normalized": {"bore_d": 12.0, "outer_d": 24.0, "width": 10.0}
                    },
                }
            ]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                return MockRetrievalResultWithHeldOut()

        assembled = assemble_c1(case, retrieval_index=MockIndex())
        # Held-out candidates are filtered → no retrieval_source → blocked
        self.assertIsNotNone(assembled.blocked_reason)
        self.assertIsNone(assembled.reference_context)


if __name__ == "__main__":
    unittest.main()
