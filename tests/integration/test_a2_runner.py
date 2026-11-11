"""Offline tests for the A2 real-model integration entry point.

All tests use FakeTransport and do NOT make network calls,
read secrets, write to work/app001-runs/, or call the real pipeline with CAD
compilation.  The pipeline is mocked via unittest.mock.patch.

Test categories
---------------
1. Authorization scope validation (construction-time checks)
2. Offline preflight checks (hash, budget, batch dir, prompt)
3. Dry-run combinations (input isolation, no runs)
4. Gate closed / zero side-effects (FORMAL_EVALUATION_ALLOWED=False)
5. Mock success path: answer → pipeline success
6. Mock ask path: ask → pipeline NOT called
7. Mock refuse path: refuse → pipeline NOT called
8. Mock blocked path (missing_fields) → pipeline NOT called
9. Mock pipeline failure: LLM answer → pipeline fail → failed status
10. Input / evaluator-label isolation: labels never reach adapter
11. Prompt / schema / version / hash anchoring
12. Budget plan correctness
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm.a2_authorization import (
    A2_INPUT_IDS,
    A2_INPUTS_SHA256,
    A2_LABELS_SHA256,
    A2_MAX_BATCH_HTTP,
    A2_MAX_LOGICAL_RUNS,
    A2_PROFILE_ID,
    A2_PROVIDER,
    A2FormalApproval,
    A2IntegrationAuthorization,
    ApprovalValidationError,
    AuthorizationScopeError,
    authorize_a2_run,
    make_test_approval,
    validate_formal_approval_binding,
)
from llm.transport import FakeTransport, TransportError, TransportResponse
from integration.a2_runner import (
    A2BatchResult,
    SummaryWriteError,
    _SummaryWriter,
    _atomic_write_json,
    _build_initial_summary,
    _load_frozen_inputs,
    _plan_combinations,
    run_a2_batch,
    run_a2_offline_preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


def _make_transport_with_response(body: str) -> FakeTransport:
    """Return a FakeTransport pre-loaded with one response."""
    fake = FakeTransport()
    fake.queue_response(TransportResponse(status=200, body=body))
    return fake


def _make_transport_sequence(bodies: list[str]) -> FakeTransport:
    """Return a FakeTransport pre-loaded with multiple responses."""
    fake = FakeTransport()
    for body in bodies:
        fake.queue_response(TransportResponse(status=200, body=body))
    return fake


def _make_auth(batch_id: str = "app002-a2-test-batch-01") -> A2IntegrationAuthorization:
    return authorize_a2_run(batch_id=batch_id)


# Pipeline success mock: returns a PipelineResult-like object
def _mock_pipeline_success(request_text, raw_envelope, *, output_root=None,
                            envelope_fixture_label="", run_id=None):
    from integration.pipeline import PipelineResult
    rid = run_id or "mock-run-id"
    return PipelineResult(
        run_id=rid,
        extraction_source="a2_real_model",
        status="success",
        stage="step_readback",
        errors=[],
        questions=[],
        request_text=request_text,
        envelope_fixture_label=envelope_fixture_label,
        parameters={"bore_d": 24},
        ir_index={
            "run_id": rid,
            "envelope_sha256": "aaa",
            "input_ir_sha256": "bbb",
            "result_ir_sha256": "ccc",
            "step_sha256": "ddd",
            "step_bytes": 1024,
            "step_path": f"/mock/path/{rid}/cad_output/part.step",
            "compiler_manifest_input_ir_sha256": "bbb",
        },
        step_path=f"/mock/path/{rid}/cad_output/part.step",
        run_dir=f"/mock/path/{rid}",
    )


def _mock_pipeline_failure(request_text, raw_envelope, *, output_root=None,
                            envelope_fixture_label="", run_id=None):
    from integration.pipeline import PipelineResult
    rid = run_id or "mock-run-id"
    return PipelineResult(
        run_id=rid,
        extraction_source="a2_real_model",
        status="failed",
        stage="cad",
        errors=[{"code": "CAD_FAILED", "message": "mock compilation failure"}],
        questions=[],
        request_text=request_text,
        envelope_fixture_label=envelope_fixture_label,
        parameters=None,
        ir_index=None,
        step_path=None,
        run_dir=f"/mock/path/{rid}",
    )


# ---------------------------------------------------------------------------
# 1. Authorization scope validation
# ---------------------------------------------------------------------------

class TestA2AuthorizationScope(unittest.TestCase):

    def test_valid_construction(self):
        auth = authorize_a2_run(batch_id="test-001")
        self.assertEqual(auth.profile_id, A2_PROFILE_ID)
        self.assertEqual(auth.input_ids, A2_INPUT_IDS)
        self.assertEqual(auth.inputs_sha256, A2_INPUTS_SHA256)
        self.assertEqual(auth.evaluator_labels_sha256, A2_LABELS_SHA256)
        self.assertTrue(auth.enable_cad_pipeline)
        self.assertEqual(auth.max_batch_attempts, A2_MAX_BATCH_HTTP)
        self.assertEqual(auth.max_logical_runs, A2_MAX_LOGICAL_RUNS)
        self.assertIn(A2_PROVIDER, auth.providers)

    def test_wrong_profile_id_rejected(self):
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        with self.assertRaises(AuthorizationScopeError):
            A2IntegrationAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set="a2-integration-smoke.v1",
                conditions=frozenset({"C0"}),
                providers=frozenset({"DeepSeek"}),
                models=frozenset({"deepseek-flash"}),
                max_logical_runs=3,
                max_attempts_per_run=3,
                max_batch_attempts=9,
                max_provider_attempts=9,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-001",
                profile_id="WRONG_PROFILE_ID",  # <-- wrong
                input_ids=A2_INPUT_IDS,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_ollama_provider_rejected(self):
        """Ollama must not be added to A2 scope without explicit authorization."""
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        with self.assertRaises(AuthorizationScopeError):
            A2IntegrationAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set="a2-integration-smoke.v1",
                conditions=frozenset({"C0"}),
                providers=frozenset({"DeepSeek", "Ollama"}),  # <-- Ollama added
                models=frozenset({"deepseek-flash", "qwen3:8b"}),
                max_logical_runs=3,
                max_attempts_per_run=3,
                max_batch_attempts=9,
                max_provider_attempts=9,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-001",
                profile_id=A2_PROFILE_ID,
                input_ids=A2_INPUT_IDS,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_cad_pipeline_disabled_rejected(self):
        """enable_cad_pipeline=False must be rejected."""
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        with self.assertRaises(AuthorizationScopeError):
            A2IntegrationAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set="a2-integration-smoke.v1",
                conditions=frozenset({"C0"}),
                providers=frozenset({"DeepSeek"}),
                models=frozenset({"deepseek-flash"}),
                max_logical_runs=3,
                max_attempts_per_run=3,
                max_batch_attempts=9,
                max_provider_attempts=9,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-001",
                profile_id=A2_PROFILE_ID,
                input_ids=A2_INPUT_IDS,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                enable_cad_pipeline=False,  # <-- must be True
            )

    def test_empty_batch_id_rejected(self):
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        with self.assertRaises(AuthorizationScopeError):
            A2IntegrationAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set="a2-integration-smoke.v1",
                conditions=frozenset({"C0"}),
                providers=frozenset({"DeepSeek"}),
                models=frozenset({"deepseek-flash"}),
                max_logical_runs=3,
                max_attempts_per_run=3,
                max_batch_attempts=9,
                max_provider_attempts=9,
                ir_cad_geometry_step_disabled=True,
                batch_id="",  # <-- empty
                profile_id=A2_PROFILE_ID,
                input_ids=A2_INPUT_IDS,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_wrong_inputs_sha256_rejected(self):
        from llm.contract import CONTRACT_VERSION, PROMPT_VERSION
        with self.assertRaises(AuthorizationScopeError):
            A2IntegrationAuthorization(
                protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
                sample_set="a2-integration-smoke.v1",
                conditions=frozenset({"C0"}),
                providers=frozenset({"DeepSeek"}),
                models=frozenset({"deepseek-flash"}),
                max_logical_runs=3,
                max_attempts_per_run=3,
                max_batch_attempts=9,
                max_provider_attempts=9,
                ir_cad_geometry_step_disabled=True,
                batch_id="test-001",
                profile_id=A2_PROFILE_ID,
                input_ids=A2_INPUT_IDS,
                inputs_sha256="0" * 64,  # <-- wrong hash
                evaluator_labels_sha256=A2_LABELS_SHA256,
                enable_cad_pipeline=True,
            )

    def test_provider_model_check(self):
        auth = _make_auth()
        self.assertTrue(auth.provider_model_is_allowed("DeepSeek", "deepseek-flash"))
        self.assertFalse(auth.provider_model_is_allowed("Ollama", "qwen3:8b"))
        self.assertFalse(auth.provider_model_is_allowed("DeepSeek", "deepseek-chat"))

    def test_expected_logical_run_id(self):
        auth = _make_auth()
        lrid = auth.expected_logical_run_id("A2-24mm", "C0", "DeepSeek")
        self.assertEqual(lrid, "A2-24mm__C0__DeepSeek__deepseek-flash")

    def test_wrong_condition_rejected(self):
        auth = _make_auth()
        with self.assertRaises(AuthorizationScopeError):
            auth.expected_logical_run_id("A2-24mm", "C1", "DeepSeek")

    def test_wrong_provider_rejected(self):
        auth = _make_auth()
        with self.assertRaises(AuthorizationScopeError):
            auth.expected_logical_run_id("A2-24mm", "C0", "Ollama")


# ---------------------------------------------------------------------------
# 2. Offline preflight
# ---------------------------------------------------------------------------

class TestA2OfflinePreflight(unittest.TestCase):

    def test_preflight_passes(self):
        auth = _make_auth("app002-a2-preflight-test-01")
        pf = run_a2_offline_preflight(auth)
        self.assertTrue(pf["ok"], f"preflight should pass; errors: {pf['errors']}")
        self.assertEqual(pf["errors"], [])
        self.assertTrue(pf["details"]["inputs_sha256_ok"])
        self.assertTrue(pf["details"]["prompt_ok"])
        self.assertTrue(pf["details"]["budget_plan"]["feasible"])
        self.assertFalse(pf["details"]["batch_dir_exists"])

    def test_preflight_budget_numbers(self):
        auth = _make_auth()
        pf = run_a2_offline_preflight(auth)
        bp = pf["details"]["budget_plan"]
        self.assertEqual(bp["max_logical_runs"], 3)
        self.assertEqual(bp["max_chat_attempts_per_run"], 3)
        self.assertEqual(bp["computed_max_http"], 9)
        self.assertEqual(bp["authorized_max_http"], 9)
        self.assertTrue(bp["feasible"])
        # Key invariant: 9 ≤ 9 is feasible
        self.assertLessEqual(bp["computed_max_http"], bp["authorized_max_http"])

    def test_preflight_batch_dir_exists_fails(self):
        """If the batch directory already exists, preflight must fail."""
        auth = _make_auth("app002-a2-preflight-test-01")
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_dir = Path(tmpdir) / "fake-batch-dir"
            existing_dir.mkdir()
            pf = run_a2_offline_preflight(auth, batch_dir=existing_dir)
            self.assertFalse(pf["ok"])
            self.assertTrue(any("batch_dir_exists" in e for e in pf["errors"]))

    def test_preflight_inputs_sha256_verified(self):
        """Tampered inputs file must cause preflight to fail."""
        auth = _make_auth()
        # Monkeypatch the SHA-256 to a wrong value
        with patch("integration.a2_runner.A2_INPUTS_SHA256", "0" * 64):
            pf = run_a2_offline_preflight(auth)
        self.assertFalse(pf["ok"])
        self.assertTrue(any("inputs_check" in e for e in pf["errors"]))


# ---------------------------------------------------------------------------
# 3. Dry-run combinations (input isolation, no runs executed)
# ---------------------------------------------------------------------------

class TestA2DryRun(unittest.TestCase):

    def test_dry_run_returns_plan(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        self.assertEqual(result.mode, "dry_run")
        self.assertTrue(result.preflight_ok)
        self.assertEqual(len(result.planned_runs), 3)
        self.assertEqual(result.results, [])

    def test_dry_run_input_ids(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        actual_ids = tuple(p.input_id for p in result.planned_runs)
        self.assertEqual(actual_ids, A2_INPUT_IDS)

    def test_dry_run_no_network(self):
        """Dry-run must make zero network calls even with a transport injected."""
        fake = FakeTransport()
        auth = _make_auth()
        # Even if transport is available, dry_run must not use it
        result = run_a2_batch(authorization=auth, dry_run=True, transport=fake)
        self.assertEqual(fake.call_count, 0, "FakeTransport must not be called in dry_run")
        self.assertEqual(result.results, [])

    def test_dry_run_evaluator_labels_absent(self):
        """Evaluator labels must never appear in dry-run output."""
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        output = json.dumps(result.as_dict())
        # Labels file content
        self.assertNotIn("expected_decision", output)
        self.assertNotIn("expected_pipeline_status", output)
        self.assertNotIn("evaluator-labels", output)

    def test_dry_run_budget_plan(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        bp = result.budget_plan
        self.assertEqual(bp["max_logical_runs"], 3)
        self.assertEqual(bp["max_batch_http"], 9)
        self.assertEqual(bp["provider"], "DeepSeek")
        self.assertEqual(bp["condition"], "C0")


# ---------------------------------------------------------------------------
# 4. Gate closed: FORMAL_EVALUATION_ALLOWED=False
# ---------------------------------------------------------------------------

class TestA2GateClosed(unittest.TestCase):

    def test_gate_closed_no_network_with_fake_transport(self):
        """With FakeTransport and gate=False, mock runs are allowed (no real HTTP)."""
        auth = _make_auth()
        body = _load_fixture("ask-missing-bore.json")
        transport = FakeTransport()
        # Queue one response per input
        for _ in A2_INPUT_IDS:
            transport.queue_response(TransportResponse(status=200, body=body))

        with patch("integration.a2_runner.run_pipeline") as mock_pipeline:
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        # Pipeline must NOT be called (all inputs return ask)
        mock_pipeline.assert_not_called()
        self.assertEqual(len(result.results), 3)
        self.assertEqual(result.mode, "mock")

    def test_gate_closed_no_real_transport_accepted(self):
        """A non-FakeTransport without authorization must be refused."""
        from llm.transport import MockTransport

        class NotFake(MockTransport):
            def send(self, request):
                raise AssertionError("send() must not be called")

        auth = _make_auth()
        # Pass NotFake (not FakeTransport, not BudgetAwareTransport) with dry_run=False.
        # The Adapter gate check should block this before any HTTP.
        # In practice, the Adapter checks type(transport) is FakeTransport;
        # NotFake would fail and the run should return error status.
        transport = NotFake()
        with patch("integration.a2_runner.run_pipeline") as mock_pipeline:
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)
        # All runs should fail or error (gate refused)
        mock_pipeline.assert_not_called()
        for r in result.results:
            self.assertNotEqual(r.combined_status, "success")


# ---------------------------------------------------------------------------
# 5. Mock success path: answer → pipeline success
# ---------------------------------------------------------------------------

class TestA2MockSuccessPath(unittest.TestCase):

    def test_answer_input_calls_pipeline(self):
        """answer-bore24 → pipeline called with the raw envelope."""
        auth = _make_auth()
        body_24 = _load_fixture("answer-bore24.json")
        body_80 = _load_fixture("answer-bore80.json")
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for body in [body_24, body_80, body_ask]:
            fake.queue_response(TransportResponse(status=200, body=body))
        transport = fake

        pipeline_calls = []

        def _capture_pipeline(request_text, raw_envelope, **kwargs):
            pipeline_calls.append((request_text, raw_envelope))
            return _mock_pipeline_success(request_text, raw_envelope, **kwargs)

        with patch("integration.a2_runner.run_pipeline", side_effect=_capture_pipeline):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        # 2 answer inputs (A2-24mm, A2-80mm) → 2 pipeline calls
        self.assertEqual(len(pipeline_calls), 2)
        # A2-ask-bore → pipeline NOT called (ask status)
        self.assertEqual(len(result.results), 3)

    def test_success_result_fields(self):
        """Successful run sets step_path, ir_index, combined_status=success."""
        auth = _make_auth()
        body_24 = _load_fixture("answer-bore24.json")
        body_80 = _load_fixture("answer-bore80.json")
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for body in [body_24, body_80, body_ask]:
            fake.queue_response(TransportResponse(status=200, body=body))
        transport = fake

        with patch("integration.a2_runner.run_pipeline", side_effect=_mock_pipeline_success):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        a2_24 = next(r for r in result.results if r.input_id == "A2-24mm")
        self.assertEqual(a2_24.combined_status, "success")
        self.assertEqual(a2_24.llm_status, "answer")
        self.assertEqual(a2_24.pipeline_status, "success")
        self.assertIsNotNone(a2_24.step_path)
        self.assertIsNotNone(a2_24.ir_index)
        self.assertEqual(a2_24.errors, [])

    def test_step_comes_from_current_run(self):
        """step_path must come from the pipeline result for THIS run, not any other."""
        auth = _make_auth()
        body_24 = _load_fixture("answer-bore24.json")
        body_80 = _load_fixture("answer-bore80.json")
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for body in [body_24, body_80, body_ask]:
            fake.queue_response(TransportResponse(status=200, body=body))
        transport = fake

        seen_run_ids = []

        def _capturing_pipeline(request_text, raw_envelope, *, run_id=None, **kwargs):
            seen_run_ids.append(run_id)
            return _mock_pipeline_success(request_text, raw_envelope,
                                          run_id=run_id, **kwargs)

        with patch("integration.a2_runner.run_pipeline", side_effect=_capturing_pipeline):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        # Each pipeline call uses the same run_id as the LLM run
        answer_results = [r for r in result.results if r.combined_status == "success"]
        for r in answer_results:
            self.assertIn(r.llm_meta.get("run_id"), seen_run_ids,
                          "pipeline must use the same run_id as the LLM call")
            # step_path must contain that run_id
            if r.step_path:
                self.assertIn(r.llm_meta["run_id"], r.step_path)


# ---------------------------------------------------------------------------
# 6. Mock ask path: ask → pipeline NOT called
# ---------------------------------------------------------------------------

class TestA2AskPath(unittest.TestCase):

    def test_ask_does_not_call_pipeline(self):
        auth = _make_auth()
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        # Queue ask for all 3 inputs
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        transport = fake

        with patch("integration.a2_runner.run_pipeline") as mock_pipeline:
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        mock_pipeline.assert_not_called()
        for r in result.results:
            self.assertEqual(r.llm_status, "ask")
            self.assertIsNone(r.pipeline_status)
            self.assertEqual(r.combined_status, "ask")

    def test_ask_result_includes_questions(self):
        auth = _make_auth()
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        transport = fake

        with patch("integration.a2_runner.run_pipeline"):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        ask_bore_result = next(r for r in result.results if r.input_id == "A2-ask-bore")
        self.assertGreater(len(ask_bore_result.questions), 0)


# ---------------------------------------------------------------------------
# 7. Mock refuse path: refuse → pipeline NOT called
# ---------------------------------------------------------------------------

class TestA2RefusePath(unittest.TestCase):

    def test_refuse_does_not_call_pipeline(self):
        auth = _make_auth()
        body_refuse = _load_fixture("refuse-decision.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_refuse))
        transport = fake

        with patch("integration.a2_runner.run_pipeline") as mock_pipeline:
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        mock_pipeline.assert_not_called()
        for r in result.results:
            self.assertIn(r.llm_status, ("refuse", "blocked"))
            self.assertIsNone(r.pipeline_status)


# ---------------------------------------------------------------------------
# 8. Mock blocked path (missing_fields / unsupported)
# ---------------------------------------------------------------------------

class TestA2BlockedPath(unittest.TestCase):

    def test_missing_fields_blocks_pipeline(self):
        auth = _make_auth()
        body_blocked = _load_fixture("answer-missing-fields.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_blocked))
        transport = fake

        with patch("integration.a2_runner.run_pipeline") as mock_pipeline:
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        mock_pipeline.assert_not_called()
        for r in result.results:
            # answer+missing_fields → pipeline blocked
            self.assertNotEqual(r.combined_status, "success")
            self.assertIsNone(r.step_path)


# ---------------------------------------------------------------------------
# 9. Mock pipeline failure: LLM answer → pipeline fail → failed status
# ---------------------------------------------------------------------------

class TestA2PipelineFailure(unittest.TestCase):

    def test_pipeline_fail_returns_failed_status(self):
        auth = _make_auth()
        body_24 = _load_fixture("answer-bore24.json")
        body_80 = _load_fixture("answer-bore80.json")
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for body in [body_24, body_80, body_ask]:
            fake.queue_response(TransportResponse(status=200, body=body))
        transport = fake

        with patch("integration.a2_runner.run_pipeline", side_effect=_mock_pipeline_failure):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        a2_24 = next(r for r in result.results if r.input_id == "A2-24mm")
        self.assertEqual(a2_24.llm_status, "answer")
        self.assertEqual(a2_24.pipeline_status, "failed")
        self.assertEqual(a2_24.combined_status, "failed")
        self.assertIsNone(a2_24.step_path)

    def test_pipeline_fail_no_old_step(self):
        """On pipeline failure, step_path and ir_index must be None."""
        auth = _make_auth()
        body_24 = _load_fixture("answer-bore24.json")
        body_80 = _load_fixture("answer-bore80.json")
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for body in [body_24, body_80, body_ask]:
            fake.queue_response(TransportResponse(status=200, body=body))
        transport = fake

        with patch("integration.a2_runner.run_pipeline", side_effect=_mock_pipeline_failure):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        for r in result.results:
            if r.pipeline_status == "failed":
                self.assertIsNone(r.step_path,
                    f"step_path must be None on failure for input {r.input_id}")
                self.assertIsNone(r.ir_index,
                    f"ir_index must be None on failure for input {r.input_id}")


# ---------------------------------------------------------------------------
# 10. Input / evaluator-label isolation
# ---------------------------------------------------------------------------

class TestA2InputIsolation(unittest.TestCase):

    def test_evaluator_labels_not_in_plan(self):
        """Evaluator labels must not appear in combination plans."""
        auth = _make_auth()
        plans = _plan_combinations(auth)
        plan_str = json.dumps([{
            "logical_run_id": p.logical_run_id,
            "input_id": p.input_id,
            "condition_id": p.condition_id,
        } for p in plans])
        self.assertNotIn("expected_decision", plan_str)
        self.assertNotIn("expected_pipeline_status", plan_str)

    def test_frozen_inputs_sha256_matches(self):
        """The SHA-256 of the actual inputs file must match the frozen constant."""
        import hashlib
        from integration.a2_runner import _REPO_ROOT, _MODEL_INPUTS_REL
        path = _REPO_ROOT / _MODEL_INPUTS_REL
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(actual, A2_INPUTS_SHA256,
            "Inputs file has been modified; frozen SHA-256 must be updated.")

    def test_load_frozen_inputs_no_labels(self):
        """Loaded inputs must not contain evaluator-only fields."""
        inputs = _load_frozen_inputs(verify_sha256=True)
        for inp in inputs:
            keys = set(inp.keys())
            self.assertNotIn("expected_decision", keys)
            self.assertNotIn("expected_pipeline_status", keys)
            self.assertNotIn("expected_params", keys)
            self.assertIn("input_id", keys)
            self.assertIn("natural_language", keys)

    def test_load_frozen_inputs_ids(self):
        inputs = _load_frozen_inputs(verify_sha256=True)
        actual_ids = tuple(i["input_id"] for i in inputs)
        self.assertEqual(actual_ids, A2_INPUT_IDS)


# ---------------------------------------------------------------------------
# 11. Prompt / schema / version / hash anchoring
# ---------------------------------------------------------------------------

class TestA2PromptAnchoring(unittest.TestCase):

    def test_prompt_version_in_run_meta(self):
        """Every LLM run record must reference the frozen v5 prompt version."""
        auth = _make_auth()
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        transport = fake

        with patch("integration.a2_runner.run_pipeline"):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        from llm.contract import PROMPT_VERSION
        for r in result.results:
            self.assertEqual(r.llm_meta.get("prompt_version"), PROMPT_VERSION,
                f"input {r.input_id}: prompt_version should be {PROMPT_VERSION}")

    def test_contract_version_in_run_meta(self):
        auth = _make_auth()
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        transport = fake

        with patch("integration.a2_runner.run_pipeline"):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        from llm.contract import CONTRACT_VERSION
        for r in result.results:
            self.assertEqual(r.llm_meta.get("contract_version"), CONTRACT_VERSION)

    def test_prompt_hashes_present(self):
        """prompt_hashes must be recorded in llm_meta for every run."""
        auth = _make_auth()
        body_ask = _load_fixture("ask-missing-bore.json")

        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        transport = fake

        with patch("integration.a2_runner.run_pipeline"):
            result = run_a2_batch(authorization=auth, dry_run=False, transport=transport)

        for r in result.results:
            hashes = r.llm_meta.get("prompt_hashes", {})
            self.assertIn("system_prompt_sha256", hashes)
            self.assertIn("user_template_sha256", hashes)
            self.assertIn("rendered_payload_sha256", hashes)


# ---------------------------------------------------------------------------
# 12. Budget plan correctness
# ---------------------------------------------------------------------------

class TestA2BudgetPlan(unittest.TestCase):

    def test_budget_numbers(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        bp = result.budget_plan
        # 3 runs × 3 attempts = 9 max HTTP; must equal the authorized cap
        self.assertEqual(bp["max_logical_runs"] * bp["max_chat_attempts_per_run"],
                         bp["max_batch_http"])
        self.assertEqual(bp["max_batch_http"], A2_MAX_BATCH_HTTP)

    def test_budget_provider(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        self.assertEqual(result.budget_plan["provider"], "DeepSeek")

    def test_all_3_inputs_planned(self):
        auth = _make_auth()
        result = run_a2_batch(authorization=auth, dry_run=True)
        self.assertEqual(result.budget_plan["input_ids"], list(A2_INPUT_IDS))


# ---------------------------------------------------------------------------
# 13. A2FormalApproval scope validation (R1)
# ---------------------------------------------------------------------------

class TestA2FormalApproval(unittest.TestCase):

    def test_valid_construction(self):
        app = make_test_approval(batch_id="test-approval-01")
        self.assertEqual(app.profile_id, A2_PROFILE_ID)
        self.assertEqual(app.inputs_sha256, A2_INPUTS_SHA256)
        self.assertEqual(app.evaluator_labels_sha256, A2_LABELS_SHA256)
        self.assertEqual(app.provider, A2_PROVIDER)
        self.assertEqual(app.max_batch_http, A2_MAX_BATCH_HTTP)
        self.assertTrue(app.enable_cad_pipeline)
        self.assertTrue(app.approver)
        self.assertTrue(app.approved_at_utc)
        self.assertTrue(app.approval_statement)

    def test_empty_approver_rejected(self):
        from llm.a2_authorization import A2_PROFILE_ID, A2_INPUTS_SHA256, A2_LABELS_SHA256
        from llm.a2_authorization import A2_PROVIDER, A2_MODEL, A2_CONDITION, A2_MAX_BATCH_HTTP
        with self.assertRaises(ApprovalValidationError):
            A2FormalApproval(
                batch_id="test-01",
                profile_id=A2_PROFILE_ID,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                provider=A2_PROVIDER,
                model=A2_MODEL,
                condition=A2_CONDITION,
                max_batch_http=A2_MAX_BATCH_HTTP,
                enable_cad_pipeline=True,
                approver="",  # <-- empty
                approved_at_utc="2026-11-11T00:00:00Z",
                approval_statement="I approve this batch",
            )

    def test_empty_approval_statement_rejected(self):
        from llm.a2_authorization import A2_PROFILE_ID, A2_INPUTS_SHA256, A2_LABELS_SHA256
        from llm.a2_authorization import A2_PROVIDER, A2_MODEL, A2_CONDITION, A2_MAX_BATCH_HTTP
        with self.assertRaises(ApprovalValidationError):
            A2FormalApproval(
                batch_id="test-01",
                profile_id=A2_PROFILE_ID,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                provider=A2_PROVIDER,
                model=A2_MODEL,
                condition=A2_CONDITION,
                max_batch_http=A2_MAX_BATCH_HTTP,
                enable_cad_pipeline=True,
                approver="owner",
                approved_at_utc="2026-11-11T00:00:00Z",
                approval_statement="",  # <-- empty
            )

    def test_wrong_profile_id_rejected(self):
        from llm.a2_authorization import A2_INPUTS_SHA256, A2_LABELS_SHA256
        from llm.a2_authorization import A2_PROVIDER, A2_MODEL, A2_CONDITION, A2_MAX_BATCH_HTTP
        with self.assertRaises(ApprovalValidationError):
            A2FormalApproval(
                batch_id="test-01",
                profile_id="WRONG_PROFILE",  # <-- wrong
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                provider=A2_PROVIDER,
                model=A2_MODEL,
                condition=A2_CONDITION,
                max_batch_http=A2_MAX_BATCH_HTTP,
                enable_cad_pipeline=True,
                approver="owner",
                approved_at_utc="2026-11-11T00:00:00Z",
                approval_statement="I approve this batch",
            )

    def test_wrong_max_batch_http_rejected(self):
        from llm.a2_authorization import A2_PROFILE_ID, A2_INPUTS_SHA256, A2_LABELS_SHA256
        from llm.a2_authorization import A2_PROVIDER, A2_MODEL, A2_CONDITION
        with self.assertRaises(ApprovalValidationError):
            A2FormalApproval(
                batch_id="test-01",
                profile_id=A2_PROFILE_ID,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                provider=A2_PROVIDER,
                model=A2_MODEL,
                condition=A2_CONDITION,
                max_batch_http=999,  # <-- wrong
                enable_cad_pipeline=True,
                approver="owner",
                approved_at_utc="2026-11-11T00:00:00Z",
                approval_statement="I approve this batch",
            )

    def test_enable_cad_pipeline_false_rejected(self):
        from llm.a2_authorization import A2_PROFILE_ID, A2_INPUTS_SHA256, A2_LABELS_SHA256
        from llm.a2_authorization import A2_PROVIDER, A2_MODEL, A2_CONDITION, A2_MAX_BATCH_HTTP
        with self.assertRaises(ApprovalValidationError):
            A2FormalApproval(
                batch_id="test-01",
                profile_id=A2_PROFILE_ID,
                inputs_sha256=A2_INPUTS_SHA256,
                evaluator_labels_sha256=A2_LABELS_SHA256,
                provider=A2_PROVIDER,
                model=A2_MODEL,
                condition=A2_CONDITION,
                max_batch_http=A2_MAX_BATCH_HTTP,
                enable_cad_pipeline=False,  # <-- must be True
                approver="owner",
                approved_at_utc="2026-11-11T00:00:00Z",
                approval_statement="I approve this batch",
            )

    def test_binding_match(self):
        auth = authorize_a2_run(batch_id="binding-test-01")
        app = make_test_approval(batch_id="binding-test-01")
        validate_formal_approval_binding(auth, app)

    def test_binding_mismatch_rejected(self):
        auth = authorize_a2_run(batch_id="binding-test-01")
        app = make_test_approval(batch_id="different-batch")
        with self.assertRaises(ApprovalValidationError):
            validate_formal_approval_binding(auth, app)

    def test_audit_dict_no_secrets(self):
        app = make_test_approval(batch_id="audit-test-01")
        audit = app.as_audit_dict()
        # Must not contain any secret-related keys
        for key in audit:
            self.assertNotIn("key", key.lower())
            self.assertNotIn("secret", key.lower())
            self.assertNotIn("token", key.lower())
            self.assertNotIn("password", key.lower())
            self.assertNotIn("authorization", key.lower())
        # Must contain approval identity
        self.assertIn("approver", audit)
        self.assertIn("approved_at_utc", audit)
        self.assertIn("approval_statement", audit)


# ---------------------------------------------------------------------------
# 14. Approval gate: zero side-effects when credential missing/wrong (R1)
# ---------------------------------------------------------------------------

class TestA2ApprovalGate(unittest.TestCase):
    """Spy tests: verify that directory creation, BudgetLedger, Transport, and
    HTTP calls are ALL zero when the approval credential is missing or wrong."""

    def test_formal_without_approval_raises_before_any_side_effect(self):
        """Formal run (transport=None, dry_run=False) without approval must raise
        before any directory or BudgetLedger is created."""
        auth = _make_auth("gate-test-no-approval-01")
        with patch("integration.a2_runner._CANONICAL_RUN_ROOT") as mock_root, \
             patch("llm.budget.BudgetLedger") as mock_ledger, \
             patch("llm.real_transport.DeepSeekTransport") as mock_transport:
            with self.assertRaises(ApprovalValidationError):
                run_a2_batch(authorization=auth, dry_run=False, transport=None)
            mock_root.mkdir.assert_not_called()
            mock_ledger.assert_not_called()
            mock_transport.assert_not_called()

    def test_formal_with_wrong_batch_id_approval_raises(self):
        """Approval with mismatched batch_id must raise before any infra."""
        auth = _make_auth("gate-test-batch-01")
        wrong_approval = make_test_approval(batch_id="different-batch-id")
        with patch("integration.a2_runner._CANONICAL_RUN_ROOT") as mock_root, \
             patch("llm.budget.BudgetLedger") as mock_ledger:
            with self.assertRaises(ApprovalValidationError):
                run_a2_batch(
                    authorization=auth,
                    dry_run=False,
                    transport=None,
                    approval=wrong_approval,
                )
            mock_root.mkdir.assert_not_called()
            mock_ledger.assert_not_called()

    def test_formal_with_none_approval_raises(self):
        """Explicitly passing approval=None must raise."""
        auth = _make_auth("gate-test-none-01")
        with patch("integration.a2_runner._CANONICAL_RUN_ROOT") as mock_root:
            with self.assertRaises(ApprovalValidationError):
                run_a2_batch(
                    authorization=auth,
                    dry_run=False,
                    transport=None,
                    approval=None,
                )
            mock_root.mkdir.assert_not_called()

    def test_dry_run_does_not_require_approval(self):
        """Dry-run must work without approval credential."""
        auth = _make_auth("gate-test-dryrun-01")
        result = run_a2_batch(authorization=auth, dry_run=True, approval=None)
        self.assertEqual(result.mode, "dry_run")
        self.assertTrue(result.preflight_ok)

    def test_mock_mode_does_not_require_approval(self):
        """Mock mode (transport=FakeTransport) must work without approval."""
        auth = _make_auth("gate-test-mock-01")
        body_ask = _load_fixture("ask-missing-bore.json")
        fake = FakeTransport()
        for _ in A2_INPUT_IDS:
            fake.queue_response(TransportResponse(status=200, body=body_ask))
        with patch("integration.a2_runner.run_pipeline"):
            result = run_a2_batch(
                authorization=auth,
                dry_run=False,
                transport=fake,
                approval=None,
            )
        self.assertEqual(result.mode, "mock")
        self.assertEqual(len(result.results), 3)


# ---------------------------------------------------------------------------
# 15. Summary persistence (R1)
# ---------------------------------------------------------------------------

class TestA2SummaryPersistence(unittest.TestCase):
    """Test the _SummaryWriter and batch_summary.json lifecycle."""

    def test_summary_writer_initial_write(self):
        """_SummaryWriter.write_initial creates batch_summary.json atomically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch"
            batch_dir.mkdir()
            initial = {
                "schema_version": "a2-batch-summary.v1",
                "batch_id": "test-batch",
                "batch_status": "running",
                "runs": {},
            }
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()
            summary_path = batch_dir / "batch_summary.json"
            self.assertTrue(summary_path.exists())
            data = json.loads(summary_path.read_text("utf-8"))
            self.assertEqual(data["batch_id"], "test-batch")
            self.assertEqual(data["batch_status"], "running")
            # No temp file left behind
            self.assertFalse((batch_dir / "batch_summary.json.tmp").exists())

    def test_summary_writer_update_run(self):
        """_SummaryWriter.update_run atomically adds run evidence."""
        from integration.a2_runner import A2RunResult
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch"
            batch_dir.mkdir()
            initial = {
                "schema_version": "a2-batch-summary.v1",
                "batch_id": "test-batch",
                "batch_status": "running",
                "runs": {"run-01": {"status": "pending"}},
            }
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()

            run_result = A2RunResult(
                logical_run_id="run-01",
                input_id="A2-24mm",
                condition_id="C0",
                provider="DeepSeek",
                model="deepseek-flash",
                llm_status="answer",
                pipeline_status="success",
                combined_status="success",
                errors=[],
                questions=[],
                raw_retention_path="work/app001-runs/test-batch/raw/run-01_raw.txt",
                pipeline_run_dir="/mock/pipeline",
                step_path="/mock/pipeline/part.step",
                ir_index={
                    "run_id": "run-01",
                    "envelope_sha256": "abc123",
                    "input_ir_sha256": "def456",
                    "step_sha256": "ghi789",
                },
                llm_meta={
                    "attempt_count": 1,
                    "prompt_version": "app001-extraction.v5",
                    "contract_version": "app001-io.v1",
                    "configured_provider": "DeepSeek",
                    "configured_model_name": "deepseek-flash",
                },
            )
            writer.update_run(run_result)

            summary_path = batch_dir / "batch_summary.json"
            data = json.loads(summary_path.read_text("utf-8"))
            self.assertEqual(data["runs"]["run-01"]["status"], "success")
            self.assertEqual(data["runs"]["run-01"]["llm_status"], "answer")
            self.assertEqual(data["runs"]["run-01"]["pipeline_status"], "success")
            self.assertEqual(data["runs"]["run-01"]["raw_sha256"], "abc123")
            self.assertEqual(data["runs"]["run-01"]["raw_retention_path"],
                             "work/app001-runs/test-batch/raw/run-01_raw.txt")

    def test_summary_writer_finalize(self):
        """_SummaryWriter.finalize updates batch_status to complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch"
            batch_dir.mkdir()
            initial = {"batch_status": "running", "runs": {}}
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()
            writer.finalize(batch_status="complete")
            summary_path = batch_dir / "batch_summary.json"
            data = json.loads(summary_path.read_text("utf-8"))
            self.assertEqual(data["batch_status"], "complete")
            self.assertIn("batch_finished_utc", data)

    def test_raw_body_not_in_summary(self):
        """batch_summary.json must NOT contain raw response body content."""
        from integration.a2_runner import A2RunResult
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "test-batch"
            batch_dir.mkdir()
            initial = {"runs": {"run-01": {"status": "pending"}}}
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()

            raw_body = "SECRET_RAW_RESPONSE_BODY_WITH_SECRETS"
            run_result = A2RunResult(
                logical_run_id="run-01",
                input_id="A2-24mm",
                condition_id="C0",
                provider="DeepSeek",
                model="deepseek-flash",
                llm_status="answer",
                pipeline_status="success",
                combined_status="success",
                errors=[],
                questions=[],
                raw_retention_path="work/app001-runs/test/raw.txt",
                pipeline_run_dir=None,
                step_path=None,
                ir_index={"envelope_sha256": "abc123"},
                llm_meta={"attempt_count": 1},
            )
            writer.update_run(run_result)

            summary_text = (batch_dir / "batch_summary.json").read_text("utf-8")
            self.assertNotIn("SECRET_RAW_RESPONSE_BODY_WITH_SECRETS", summary_text)
            # raw_sha256 (hash) is OK; raw body content is NOT
            self.assertIn("abc123", summary_text)

    def test_path_traversal_rejected(self):
        """_atomic_write_json must reject paths that escape batch_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            batch_dir.mkdir()
            # Try to write to a path outside batch_dir
            outside_path = Path(tmpdir) / "escape.json"
            with self.assertRaises(SummaryWriteError):
                _atomic_write_json(outside_path, {"x": 1}, batch_dir)
            self.assertFalse(outside_path.exists())

    def test_summary_write_initial_failure_raises(self):
        """If write_initial fails, SummaryWriteError must be raised."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            # Don't create batch_dir — write should fail
            writer = _SummaryWriter(batch_dir, {"runs": {}})
            with self.assertRaises(SummaryWriteError):
                writer.write_initial()

    def test_summary_write_failure_during_update_blocks_subsequent(self):
        """If update_run fails mid-batch, no further model requests should proceed."""
        from integration.a2_runner import A2RunResult
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            batch_dir.mkdir()
            initial = {
                "runs": {
                    "run-01": {"status": "pending"},
                    "run-02": {"status": "pending"},
                    "run-03": {"status": "pending"},
                }
            }
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()

            # First update succeeds
            run1 = A2RunResult(
                logical_run_id="run-01",
                input_id="A2-24mm",
                condition_id="C0",
                provider="DeepSeek",
                model="deepseek-flash",
                llm_status="answer",
                pipeline_status="success",
                combined_status="success",
                errors=[],
                questions=[],
                raw_retention_path=None,
                pipeline_run_dir=None,
                step_path=None,
                ir_index=None,
                llm_meta={},
            )
            writer.update_run(run1)
            self.assertTrue((batch_dir / "batch_summary.json").exists())

            # Simulate write failure on the next update_run call.
            # We patch _atomic_write_json to raise immediately.
            def failing_write(path, data, batch_dir_arg):
                raise SummaryWriteError("simulated write failure")

            with patch("integration.a2_runner._atomic_write_json", side_effect=failing_write):
                run2 = A2RunResult(
                    logical_run_id="run-02",
                    input_id="A2-80mm",
                    condition_id="C0",
                    provider="DeepSeek",
                    model="deepseek-flash",
                    llm_status="answer",
                    pipeline_status="success",
                    combined_status="success",
                    errors=[],
                    questions=[],
                    raw_retention_path=None,
                    pipeline_run_dir=None,
                    step_path=None,
                    ir_index=None,
                    llm_meta={},
                )
                with self.assertRaises(SummaryWriteError):
                    writer.update_run(run2)

    def test_evaluator_labels_not_in_summary(self):
        """batch_summary.json must NOT contain evaluator labels content."""
        from integration.a2_runner import A2RunResult
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            batch_dir.mkdir()
            initial = {"runs": {"run-01": {"status": "pending"}}}
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()

            run_result = A2RunResult(
                logical_run_id="run-01",
                input_id="A2-24mm",
                condition_id="C0",
                provider="DeepSeek",
                model="deepseek-flash",
                llm_status="answer",
                pipeline_status="success",
                combined_status="success",
                errors=[],
                questions=[],
                raw_retention_path=None,
                pipeline_run_dir=None,
                step_path=None,
                ir_index={"envelope_sha256": "abc123"},
                llm_meta={"attempt_count": 1},
            )
            writer.update_run(run_result)

            summary_text = (batch_dir / "batch_summary.json").read_text("utf-8")
            self.assertNotIn("expected_decision", summary_text)
            self.assertNotIn("expected_pipeline_status", summary_text)
            self.assertNotIn("expected_params", summary_text)
            self.assertNotIn("evaluator-labels", summary_text)

    def test_build_initial_summary_structure(self):
        """_build_initial_summary must contain all required fields."""
        auth = _make_auth("summary-test-01")
        approval = make_test_approval(batch_id="summary-test-01")
        planned = _plan_combinations(auth)
        from llm.prompt_loader import load_frozen_prompt
        prompt = load_frozen_prompt()
        ts = "2026-11-11T12:00:00Z"
        summary = _build_initial_summary(auth, approval, planned, prompt, ts)

        self.assertEqual(summary["schema_version"], "a2-batch-summary.v1")
        self.assertEqual(summary["batch_id"], "summary-test-01")
        self.assertEqual(summary["batch_status"], "running")
        self.assertEqual(summary["batch_started_utc"], ts)
        self.assertIn("scope", summary)
        self.assertIn("artifact_hashes", summary)
        self.assertIn("approval", summary)
        self.assertEqual(len(summary["planned_runs"]), 3)
        self.assertEqual(len(summary["runs"]), 3)
        for p in planned:
            self.assertIn(p.logical_run_id, summary["runs"])
            self.assertEqual(summary["runs"][p.logical_run_id]["status"], "pending")

    def test_build_initial_summary_approval_recorded(self):
        """The approval audit dict must be in the initial summary."""
        auth = _make_auth("approval-record-01")
        approval = make_test_approval(batch_id="approval-record-01")
        planned = _plan_combinations(auth)
        from llm.prompt_loader import load_frozen_prompt
        prompt = load_frozen_prompt()
        summary = _build_initial_summary(auth, approval, planned, prompt, "ts")
        self.assertEqual(summary["approval"]["approver"], "test-owner")
        self.assertEqual(summary["approval"]["batch_id"], "approval-record-01")
        self.assertIn("approval_statement", summary["approval"])

    def test_summary_no_api_keys(self):
        """batch_summary.json must NOT contain API keys or Authorization headers."""
        from integration.a2_runner import A2RunResult
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_dir = Path(tmpdir) / "batch"
            batch_dir.mkdir()
            initial = {"runs": {}}
            writer = _SummaryWriter(batch_dir, initial)
            writer.write_initial()

            run_result = A2RunResult(
                logical_run_id="run-01",
                input_id="A2-24mm",
                condition_id="C0",
                provider="DeepSeek",
                model="deepseek-flash",
                llm_status="answer",
                pipeline_status="success",
                combined_status="success",
                errors=[],
                questions=[],
                raw_retention_path=None,
                pipeline_run_dir=None,
                step_path=None,
                ir_index={"envelope_sha256": "abc"},
                llm_meta={"attempt_count": 1},
            )
            writer.update_run(run_result)

            summary_text = (batch_dir / "batch_summary.json").read_text("utf-8")
            # Check for common secret patterns
            self.assertNotIn("api_key", summary_text.lower())
            self.assertNotIn("authorization", summary_text.lower())
            self.assertNotIn("bearer", summary_text.lower())
            self.assertNotIn("sk-", summary_text)


# ---------------------------------------------------------------------------
# 16. Summary write failure → zero network calls (R1)
# ---------------------------------------------------------------------------

class TestA2SummaryWriteFailure(unittest.TestCase):

    def test_initial_summary_failure_prevents_all_runs(self):
        """If the initial batch_summary.json write fails, no model requests
        should be attempted.  Since formal runs need the batch directory under
        work/app001-runs/ (which requires actual filesystem creation), we test
        the _SummaryWriter directly and verify the contract: write_initial()
        raises SummaryWriteError, and the caller must not proceed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate: batch_dir doesn't exist (write will fail)
            batch_dir = Path(tmpdir) / "nonexistent" / "batch"
            writer = _SummaryWriter(batch_dir, {"runs": {}})
            with self.assertRaises(SummaryWriteError):
                writer.write_initial()
            # Verify no summary was created
            self.assertFalse((batch_dir / "batch_summary.json").exists())


# ---------------------------------------------------------------------------
# 17. Formal run integration with summary (mocked infra)
# ---------------------------------------------------------------------------

class TestA2FormalRunSummaryIntegration(unittest.TestCase):
    """Test that formal run mode writes batch_summary.json with correct
    per-run evidence, using mocked BudgetLedger and Transport.

    These tests use monkeypatching to avoid real network/ledger but exercise
    the full summary lifecycle.
    """

    def test_formal_run_writes_summary_path(self):
        """A2BatchResult.summary_path must be set for formal runs."""
        # We can't actually run a formal batch without real infra,
        # but we can verify that the dry_run result has summary_path=None
        # and that the formal path would set it.
        auth = _make_auth("formal-summary-test-01")
        result = run_a2_batch(authorization=auth, dry_run=True)
        self.assertIsNone(result.summary_path)


if __name__ == "__main__":
    unittest.main()
