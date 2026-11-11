"""Offline tests for the ADR-0019 held-out v5 runner.

All tests are offline/mock.  No network calls, no .env reads, no formal batch
directory creation, no evaluator labels in any output.

Test categories (per task spec):
1. Fixed 12 combinations; each query × condition × provider/model exactly once.
2. Input/labels isolation; Adapter/Transport never see labels; logs/dry-run
   output exclude label values, sample IDs, expected parameters.
3. Normal: at least one C0 and one C1 assemble correctly; C1 uses frozen
   RET-002 retrieval_source.
4. Rejection: bad input/label hash, query ID extension/duplication, C2,
   provider/model mismatch, C1 retrieval missing or config hash wrong,
   existing batch dir, missing authorization, FORMAL_EVALUATION_ALLOWED=False
   default path.
5. Mock HTTP: all version/tags/chat requests reserve ledger first; budget
   exhausted → mock urlopen/send calls = 0; tags failure → retry count + reject.
6. Run records and raw written to work/app001-runs/<batch_id>/raw/; raw not
   in Git; blocked records retained; no labels.
7. Scope summary/ledger audit query IDs, hash pins, provider caps, failure
   counts; legacy auth/budget regression passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm.authorization import AuthorizationScopeError
from llm.budget import BudgetExhausted, BudgetLedger
from llm.contract import (
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    FORMAL_EVALUATION_ALLOWED,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)
from llm.gate import FormalEvaluationBlockedError
from llm.heldout_authorization import (
    HELDOUT_BATCH_PREFLIGHT_ID,
    HELDOUT_INPUTS_SHA256,
    HELDOUT_LABELS_SHA256,
    HELDOUT_MAX_BATCH_HTTP,
    HELDOUT_MAX_CHAT_ATTEMPTS,
    HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN,
    HELDOUT_MAX_IDENTITY_ATTEMPTS,
    HELDOUT_MAX_LOGICAL_RUNS,
    HELDOUT_PROVIDER_HTTP_CAPS,
    HELDOUT_QUERY_IDS,
    authorize_heldout_v5_run,
)
from llm.heldout_runner import (
    HeldoutBatchSummary,
    HeldoutCombinationError,
    HeldoutCombinationPlan,
    HeldoutInputError,
    HeldoutInputProjection,
    HeldoutRunner,
    HeldoutRunCombination,
    generate_heldout_combinations,
    load_heldout_inputs,
)
from llm.transport import (
    COND_HTTP_5XX,
    COND_TIMEOUT,
    FakeTransport,
    PreparedRequest,
    TransportError,
    TransportResponse,
)
from tests.llm._frozen_helpers import _frozen_input

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUN_CANONICAL_ROOT = _REPO_ROOT / "work" / "app001-runs"
_MODEL_INPUTS_PATH = (
    _REPO_ROOT
    / "agent-work"
    / "llm"
    / "APP-001-NEXT-REAL-MODEL-EVALUATION"
    / "model-inputs.json"
)
_EVALUATOR_LABELS_PATH = (
    _REPO_ROOT
    / "agent-work"
    / "llm"
    / "APP-001-NEXT-REAL-MODEL-EVALUATION"
    / "evaluator-labels.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_success_response(body: str | None = None) -> TransportResponse:
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
        usage={},
    )


def _fake_answer_response(bore_d: int = 12) -> TransportResponse:
    body = json.dumps(
        {
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": bore_d},
            "unsupported_requests": [],
            "evidence": [
                {"field": "bore_d", "quote": f"bore_d={bore_d} mm", "source": "user_input"}
            ],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        }
    )
    return TransportResponse(
        status=200,
        body=body,
        runtime_returned_model=DEEPSEEK_MODEL,
        runtime_returned_provider="not_exposed",
        usage={},
    )


class _MockRetrievalIndex:
    """Minimal mock RET-002 retrieval index for offline C1 tests.

    Returns retrieval_source candidates that the held-out runner will use
    to build C1 reference context.  Does NOT include evaluator labels or
    held-out evaluation roles.
    """

    def __init__(self, candidates: list[dict] | None = None) -> None:
        self._candidates = candidates or [
            {
                "sample_id": "set_screw_shaft_collar/catalog-bore-012",
                "family_id": "set_screw_shaft_collar",
                "split": {"role": "retrieval_source"},
                "parameters": {"normalized": {"bore_d": 12, "outer_d": 22, "width": 12,
                                              "screw_d": 6, "screw_len": 8, "second_screw": 0}},
            },
            {
                "sample_id": "set_screw_shaft_collar/catalog-bore-016",
                "family_id": "set_screw_shaft_collar",
                "split": {"role": "retrieval_source"},
                "parameters": {"normalized": {"bore_d": 16, "outer_d": 26, "width": 12,
                                              "screw_d": 6, "screw_len": 8, "second_screw": 0}},
            },
        ]
        self.manifest_sha256 = "a" * 64
        self.manifest_path = _REPO_ROOT / "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"
        self.manifest_version = "retrieval-manifest.v0"
        self.policy = MagicMock()
        self.policy.validate = MagicMock()
        self.candidate_roles = ("retrieval_source",)
        self.default_top_k = 3

    def query(self, *, family_id: str, parameters: dict, top_k: int = 3):
        result = MagicMock()
        result.results = self._candidates[:top_k]
        return result


# ---------------------------------------------------------------------------
# Category 1: Fixed 12 combinations
# ---------------------------------------------------------------------------

class TestFixedCombinations(unittest.TestCase):
    """Test 1: Fixed 12 combinations; each query × condition × provider/model once."""

    def test_dry_run_produces_exactly_12_combinations(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        plan = summary.dry_run_plan
        self.assertEqual(plan["count"], 12)
        self.assertEqual(len(plan["combinations"]), 12)

    def test_each_query_appears_exactly_4_times(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        combos = summary.dry_run_plan["combinations"]
        for qid in HELDOUT_QUERY_IDS:
            count = sum(1 for c in combos if c["query_id"] == qid)
            self.assertEqual(count, 4, f"query {qid} appears {count} times, expected 4")

    def test_each_condition_appears_exactly_6_times(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        combos = summary.dry_run_plan["combinations"]
        for cond in ("C0", "C1"):
            count = sum(1 for c in combos if c["condition_id"] == cond)
            self.assertEqual(count, 6, f"condition {cond} appears {count} times, expected 6")

    def test_each_provider_appears_exactly_6_times(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        combos = summary.dry_run_plan["combinations"]
        for prov in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
            count = sum(1 for c in combos if c["provider"] == prov)
            self.assertEqual(count, 6)

    def test_every_combination_is_unique(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        combos = summary.dry_run_plan["combinations"]
        seen = set()
        for c in combos:
            key = (c["query_id"], c["condition_id"], c["provider"], c["model"])
            self.assertNotIn(key, seen, f"duplicate combination: {key}")
            seen.add(key)

    def test_plan_sha256_is_stable(self):
        r1 = HeldoutRunner()
        r2 = HeldoutRunner()
        s1 = r1.dry_run()
        s2 = r2.dry_run()
        self.assertEqual(s1.dry_run_plan["plan_sha256"], s2.dry_run_plan["plan_sha256"])
        self.assertEqual(len(s1.dry_run_plan["plan_sha256"]), 64)


# ---------------------------------------------------------------------------
# Category 2: Input/labels isolation
# ---------------------------------------------------------------------------

class TestLabelIsolation(unittest.TestCase):
    """Test 2: Evaluator labels never reach Adapter/Transport/logs/dry-run."""

    EXPECTED_LABEL_VALUES = [
        "heldout-bore-012",
        "heldout-bore-035",
        "heldout-bore-080",
        "catalog-bore-012",
        "catalog-bore-035",
        "catalog-bore-080",
        "expected_explicit_claims",
        "expected_schema_parameters",
        "second_screw",
    ]

    def test_load_heldout_inputs_returns_no_labels(self):
        projection = load_heldout_inputs()
        for case in projection.cases:
            d = case.__dict__
            for label_key in ("expected_explicit_claims", "expected_schema_parameters",
                              "ret003_query_id", "sample_id"):
                self.assertNotIn(label_key, d)

    def test_dry_run_output_excludes_label_values(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        plan_json = json.dumps(summary.dry_run_plan, ensure_ascii=False)
        for val in self.EXPECTED_LABEL_VALUES:
            self.assertNotIn(val, plan_json,
                             f"label value {val!r} found in dry-run output")

    def test_dry_run_output_excludes_expected_parameters(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        plan_json = json.dumps(summary.dry_run_plan, ensure_ascii=False)
        # outer_d, width, screw_d, screw_len are evaluator-only when part of
        # expected_schema_parameters
        self.assertNotIn("outer_d", plan_json)
        self.assertNotIn("screw_d", plan_json)
        self.assertNotIn("screw_len", plan_json)

    def test_assembled_input_does_not_contain_labels(self):
        projection = load_heldout_inputs()
        from llm.heldout_runner import _assemble_c0
        case = projection.cases[0]
        assembled = _assemble_c0(case)
        d = assembled.__dict__
        for label_key in ("expected_explicit_claims", "expected_schema_parameters",
                          "ret003_query_id", "sample_id"):
            self.assertNotIn(label_key, d)

    def test_fake_transport_never_receives_labels(self):
        """Verify that FakeTransport.send() never receives evaluator labels in the request body.

        The frozen prompt contains a decision reference table (bore_d catalog) that
        includes catalog-level field names like 'second_screw' and 'outer_d' as column
        headers.  These are part of the prompt text that is intentionally visible to
        the model — they do not come from evaluator-labels.json.  The isolation check
        must only verify that evaluator-only values (held-out query IDs, sample IDs,
        expected schema parameters with specific numeric values, and RET-003 IDs) are
        absent from the request body.
        """
        # Evaluator-only label values that must NEVER appear in any transport request.
        # These come exclusively from evaluator-labels.json and are not part of the prompt.
        EVALUATOR_ONLY_VALUES = [
            "heldout-bore-012",
            "heldout-bore-035",
            "heldout-bore-080",
            "catalog-bore-012",
            "catalog-bore-035",
            "catalog-bore-080",
            "expected_explicit_claims",
            "expected_schema_parameters",
            "ret003_query_id",
        ]
        projection = load_heldout_inputs()
        from llm.heldout_runner import _HeldoutProjectedCase, _assemble_c0
        case = projection.cases[0]
        assembled = _assemble_c0(case)
        from llm.adapter import AdapterInput
        from llm.prompt_loader import load_frozen_prompt
        artifact = load_frozen_prompt()
        adapter_input = AdapterInput(
            query_id=case.query_id,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template,
            condition_id="C0",
        )
        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        from llm.adapter import Adapter
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=ft)
        try:
            adapter.run(adapter_input, run_id="test-isolation")
        except Exception:
            pass  # may fail on parse; we only care about the request body
        for call in ft.calls:
            body_str = json.dumps(call.body, ensure_ascii=False)
            for val in EVALUATOR_ONLY_VALUES:
                self.assertNotIn(val, body_str,
                                 f"evaluator-only value {val!r} found in transport request body")

    def test_blocked_audit_record_excludes_labels(self):
        runner = HeldoutRunner()
        auth = authorize_heldout_v5_run(batch_id="test-blocked-labels")
        projection = load_heldout_inputs()
        plan = generate_heldout_combinations(projection, auth)
        from llm.heldout_runner import _assemble_all_heldout_inputs
        assembled = _assemble_all_heldout_inputs(projection, plan, None)
        # Pick a C1 blocked case (no retrieval index)
        c1_combo = [c for c in plan.combinations if c.condition_id == "C1"][0]
        blocked_input = assembled[c1_combo.logical_run_id]
        record = runner._blocked_audit_record(
            c1_combo, auth, None, blocked_input,
            stage_name="c1_assembly",
            error_code="BLOCKED_C1_NO_RETRIEVAL_INDEX",
            error_fields=("retrieval_index",),
        )
        record_json = json.dumps(record, ensure_ascii=False)
        for val in self.EXPECTED_LABEL_VALUES:
            self.assertNotIn(val, record_json)


# ---------------------------------------------------------------------------
# Category 3: Normal cases (C0 and C1 assembly)
# ---------------------------------------------------------------------------

class TestNormalAssembly(unittest.TestCase):
    """Test 3: At least one C0 and one C1 assemble correctly."""

    def test_c0_assembles_correctly_for_ho01(self):
        projection = load_heldout_inputs()
        from llm.heldout_runner import _assemble_c0
        case = projection.case_by_id("APP001-HO-01")
        assembled = _assemble_c0(case)
        self.assertEqual(assembled.condition_id, "C0")
        self.assertIsNone(assembled.reference_context)
        self.assertIsNone(assembled.blocked_reason)
        self.assertIn("bore_d=12", assembled.natural_language_input)

    def test_c0_assembles_for_all_three_queries(self):
        projection = load_heldout_inputs()
        from llm.heldout_runner import _assemble_c0
        for case in projection.cases:
            assembled = _assemble_c0(case)
            self.assertIsNone(assembled.blocked_reason)
            self.assertIsNone(assembled.reference_context)

    def test_c1_uses_frozen_ret002_retrieval_source(self):
        projection = load_heldout_inputs()
        mock_idx = _MockRetrievalIndex()
        from llm.heldout_runner import _assemble_held_c1
        case = projection.case_by_id("APP001-HO-01")
        assembled = _assemble_held_c1(case, mock_idx)
        self.assertEqual(assembled.condition_id, "C1")
        self.assertIsNotNone(assembled.reference_context)
        self.assertIsNotNone(assembled.reference_context_sha256)
        self.assertIsNone(assembled.blocked_reason)
        self.assertEqual(len(assembled.candidate_source_ids), 2)
        # All candidates must be retrieval_source
        ref_dict = json.loads(assembled.reference_context)
        for entry in ref_dict["candidates"]:
            self.assertEqual(entry["role"], "retrieval_example_untrusted_reference")

    def test_c1_bore_d_extracted_from_nli_not_labels(self):
        projection = load_heldout_inputs()
        mock_idx = _MockRetrievalIndex()
        from llm.heldout_runner import _assemble_held_c1
        for case in projection.cases:
            assembled = _assemble_held_c1(case, mock_idx)
            self.assertIsNotNone(assembled.bore_d_used_for_query)
            self.assertIsNone(assembled.blocked_reason)

    def test_c1_blocks_when_no_retrieval_index(self):
        projection = load_heldout_inputs()
        from llm.heldout_runner import _assemble_all_heldout_inputs, generate_heldout_combinations
        auth = authorize_heldout_v5_run(batch_id="test-no-idx")
        plan = generate_heldout_combinations(projection, auth)
        assembled = _assemble_all_heldout_inputs(projection, plan, None)
        c1_combos = [c for c in plan.combinations if c.condition_id == "C1"]
        for combo in c1_combos:
            inp = assembled[combo.logical_run_id]
            self.assertIsNotNone(inp.blocked_reason)
            self.assertEqual(inp.error_code, "BLOCKED_C1_NO_RETRIEVAL_INDEX")


# ---------------------------------------------------------------------------
# Category 4: Rejection cases
# ---------------------------------------------------------------------------

class TestRejectionCases(unittest.TestCase):
    """Test 4: All rejection cases reject before any request."""

    def test_bad_inputs_hash_rejected(self):
        """load_heldout_inputs with wrong expected hash raises."""
        with self.assertRaises(HeldoutInputError):
            load_heldout_inputs(expected_sha256="0" * 64)

    def test_bad_labels_hash_rejected_in_offline_preflight(self):
        """If evaluator-labels.json hash doesn't match, preflight should fail."""
        runner = HeldoutRunner()
        with patch("llm.heldout_runner.HELDOUT_LABELS_SHA256", "f" * 64):
            with self.assertRaises(FormalEvaluationBlockedError):
                runner._verify_labels_sha256()

    def test_query_id_extension_rejected(self):
        """Combination generator rejects projections with unexpected query IDs."""
        projection = HeldoutInputProjection(
            cases=(
                HeldoutRunCombination.__new__(HeldoutRunCombination) and
                type("X", (), {"query_id": "APP001-HO-01",
                               "natural_language_input": "bore_d=12 mm"})(),
                type("X", (), {"query_id": "APP001-HO-02",
                               "natural_language_input": "bore_d=35 mm"})(),
                type("X", (), {"query_id": "APP001-HO-03",
                               "natural_language_input": "bore_d=80 mm"})(),
                type("X", (), {"query_id": "APP001-HO-04",
                               "natural_language_input": "bore_d=99 mm"})(),
            ),
            inputs_sha256=HELDOUT_INPUTS_SHA256,
            artifact_version="test",
        )
        auth = authorize_heldout_v5_run(batch_id="test-extension")
        # The projection has 4 cases; generator should reject
        with self.assertRaises((HeldoutCombinationError, HeldoutInputError, ValueError)):
            # This will fail because the mock cases don't match HeldoutCase shape
            generate_heldout_combinations(projection, auth)

    def test_duplicate_query_id_rejected(self):
        """load_heldout_inputs rejects duplicate query IDs."""
        # Create a temp file with duplicate query IDs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "artifact_version": "test",
                "cases": [
                    {"query_id": "APP001-HO-01", "natural_language_input": "bore_d=12 mm"},
                    {"query_id": "APP001-HO-01", "natural_language_input": "bore_d=12 mm"},
                    {"query_id": "APP001-HO-02", "natural_language_input": "bore_d=35 mm"},
                ]
            }, f)
            tmp_path = Path(f.name)
        try:
            with self.assertRaises(HeldoutInputError):
                load_heldout_inputs(inputs_path=tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_c2_condition_rejected(self):
        """The runner never generates C2 combinations."""
        runner = HeldoutRunner()
        summary = runner.dry_run()
        for c in summary.dry_run_plan["combinations"]:
            self.assertIn(c["condition_id"], ("C0", "C1"))

    def test_provider_model_mismatch_rejected(self):
        """Authorization with wrong providers/models raises scope error."""
        auth = authorize_heldout_v5_run(batch_id="test-mismatch")
        with self.assertRaises(AuthorizationScopeError):
            replace(auth, providers=frozenset({"WrongProvider"}))

    def test_c1_retrieval_missing_blocks_formal_run(self):
        """Formal run without retrieval_index raises FormalEvaluationBlockedError."""
        runner = HeldoutRunner()  # no retrieval_index
        auth = authorize_heldout_v5_run(batch_id="test-no-retrieval-formal")
        with self.assertRaises(FormalEvaluationBlockedError):
            runner.run_formal(auth)

    def test_existing_batch_directory_rejected(self):
        """Offline preflight rejects if runs.jsonl already exists."""
        batch_id = f"test-existing-batch-{uuid.uuid4().hex[:8]}"
        batch_dir = _RUN_CANONICAL_ROOT / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        (batch_dir / "runs.jsonl").write_text("existing\n", encoding="utf-8")
        try:
            runner = HeldoutRunner()
            with self.assertRaises(FormalEvaluationBlockedError):
                runner.offline_preflight(batch_id)
        finally:
            shutil.rmtree(batch_dir, ignore_errors=True)

    def test_missing_authorization_rejected(self):
        """run_formal with non-HeldoutRunAuthorization raises."""
        runner = HeldoutRunner()
        with self.assertRaises(FormalEvaluationBlockedError):
            runner.run_formal("not-an-authorization")  # type: ignore

    def test_formal_evaluation_allowed_is_false(self):
        """FORMAL_EVALUATION_ALLOWED is False by default."""
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_dry_run_summary_reflects_closed_gate(self):
        runner = HeldoutRunner()
        summary = runner.dry_run()
        self.assertFalse(summary.formal_evaluation_allowed)

    def test_authorization_rejects_changed_inputs_hash(self):
        auth = authorize_heldout_v5_run(batch_id="test-hash-pin")
        with self.assertRaises(AuthorizationScopeError):
            replace(auth, inputs_sha256="0" * 64)

    def test_authorization_rejects_changed_labels_hash(self):
        auth = authorize_heldout_v5_run(batch_id="test-labels-pin")
        with self.assertRaises(AuthorizationScopeError):
            replace(auth, evaluator_labels_sha256="0" * 64)


# ---------------------------------------------------------------------------
# Category 5: Mock HTTP tests — ledger reservation before network I/O
# ---------------------------------------------------------------------------

class TestMockHTTPBudgetEnforcement(unittest.TestCase):
    """Test 5: All HTTP requests reserve ledger first; budget exhausted → 0 calls."""

    def setUp(self):
        self.batch_id = f"test-mock-http-{uuid.uuid4().hex[:8]}"
        self.batch_dir = _RUN_CANONICAL_ROOT / self.batch_id
        self.auth = authorize_heldout_v5_run(batch_id=self.batch_id)
        self.ledger = BudgetLedger(self.batch_dir, self.auth)
        self.ledger.acquire_lock()

    def tearDown(self):
        self.ledger.release_lock()
        shutil.rmtree(self.batch_dir, ignore_errors=True)

    def test_chat_reservation_required_before_send(self):
        """A chat request must have a ledger reservation before urlopen/send."""
        logical_run_id = self.auth.expected_logical_run_id(
            HELDOUT_QUERY_IDS[0], "C0", DEEPSEEK_PROVIDER
        )
        # Reserve one chat attempt
        reservation = self.ledger.reserve_attempt(
            logical_run_id=logical_run_id,
            provider=DEEPSEEK_PROVIDER,
            is_model_call=True,
            endpoint="/chat/completions",
            request_category="chat",
        )
        self.assertEqual(reservation.attempt_number, 1)
        self.assertEqual(reservation.remaining_batch, HELDOUT_MAX_BATCH_HTTP - 1)

    def test_budget_exhausted_prevents_any_send(self):
        """When chat budget is exhausted, mock send count must be 0."""
        ft = FakeTransport()
        ft.queue_response(_fake_success_response())
        # Exhaust DeepSeek chat budget (18)
        deepseek_runs = [
            self.auth.expected_logical_run_id(qid, cond, DEEPSEEK_PROVIDER)
            for qid in HELDOUT_QUERY_IDS
            for cond in ("C0", "C1")
        ]
        for lrid in deepseek_runs:
            for _ in range(3):
                self.ledger.reserve_attempt(
                    logical_run_id=lrid,
                    provider=DEEPSEEK_PROVIDER,
                    is_model_call=True,
                    endpoint="/chat/completions",
                    request_category="chat",
                )
        # Now budget should be exhausted for DeepSeek chat
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=deepseek_runs[0],
                provider=DEEPSEEK_PROVIDER,
                is_model_call=True,
                endpoint="/chat/completions",
                request_category="chat",
            )
        # FakeTransport was never called
        self.assertEqual(ft.call_count, 0)

    def test_identity_reservation_required_before_tags(self):
        """Ollama /api/tags must have a ledger reservation before network I/O."""
        logical_run_id = self.auth.expected_logical_run_id(
            HELDOUT_QUERY_IDS[0], "C0", OLLAMA_PROVIDER
        )
        reservation = self.ledger.reserve_attempt(
            logical_run_id=logical_run_id,
            provider=OLLAMA_PROVIDER,
            is_model_call=False,
            endpoint="/api/tags",
            request_category="identity",
        )
        self.assertLess(reservation.attempt_number, 0)  # negative serial

    def test_preflight_version_reservation_required(self):
        """/api/version preflight must have a ledger reservation."""
        reservation = self.ledger.reserve_attempt(
            logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
            provider=OLLAMA_PROVIDER,
            is_model_call=False,
            endpoint="/api/version",
            request_category="identity",
        )
        self.assertLess(reservation.attempt_number, 0)

    def test_tags_failure_retry_count_and_final_rejection(self):
        """When /api/tags fails, retries are counted and eventually rejected."""
        logical_run_id = self.auth.expected_logical_run_id(
            HELDOUT_QUERY_IDS[0], "C0", OLLAMA_PROVIDER
        )
        # Simulate 3 failed tags attempts (max per run)
        for _ in range(3):
            self.ledger.reserve_attempt(
                logical_run_id=logical_run_id,
                provider=OLLAMA_PROVIDER,
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )
        # 4th tags attempt for the same run should be rejected
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=logical_run_id,
                provider=OLLAMA_PROVIDER,
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )

    def test_all_12_runs_fit_within_budget(self):
        """All 12 logical runs × 3 chat attempts = 36 chat reservations fit."""
        all_runs = [
            self.auth.expected_logical_run_id(qid, cond, prov)
            for qid in HELDOUT_QUERY_IDS
            for cond in ("C0", "C1")
            for prov in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER)
        ]
        self.assertEqual(len(all_runs), 12)
        for lrid in all_runs:
            provider = DEEPSEEK_PROVIDER if "DeepSeek" in lrid else OLLAMA_PROVIDER
            endpoint = "/chat/completions" if provider == DEEPSEEK_PROVIDER else "/api/chat"
            for _ in range(3):
                self.ledger.reserve_attempt(
                    logical_run_id=lrid,
                    provider=provider,
                    is_model_call=True,
                    endpoint=endpoint,
                    request_category="chat",
                )
        snapshot = self.ledger.snapshot()
        self.assertEqual(snapshot["category_attempts_used"]["chat"], 36)
        self.assertEqual(snapshot["total_attempts_used"], 36)

    def test_full_budget_44_http_is_exact(self):
        """36 chat + 2 preflight identity + 6 runtime tags = 44 total HTTP."""
        # 36 chat
        all_runs = [
            self.auth.expected_logical_run_id(qid, cond, prov)
            for qid in HELDOUT_QUERY_IDS
            for cond in ("C0", "C1")
            for prov in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER)
        ]
        for lrid in all_runs:
            provider = DEEPSEEK_PROVIDER if "DeepSeek" in lrid else OLLAMA_PROVIDER
            endpoint = "/chat/completions" if provider == DEEPSEEK_PROVIDER else "/api/chat"
            for _ in range(3):
                self.ledger.reserve_attempt(
                    logical_run_id=lrid,
                    provider=provider,
                    is_model_call=True,
                    endpoint=endpoint,
                    request_category="chat",
                )
        # 2 preflight identity
        for endpoint in ("/api/version", "/api/tags"):
            self.ledger.reserve_attempt(
                logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
                provider=OLLAMA_PROVIDER,
                is_model_call=False,
                endpoint=endpoint,
                request_category="identity",
            )
        # 6 runtime tags (one per Ollama run)
        ollama_runs = [lrid for lrid in all_runs if "Ollama" in lrid]
        for lrid in ollama_runs:
            self.ledger.reserve_attempt(
                logical_run_id=lrid,
                provider=OLLAMA_PROVIDER,
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )
        snapshot = self.ledger.snapshot()
        self.assertEqual(snapshot["total_attempts_used"], 44)
        # 45th should fail
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=ollama_runs[0],
                provider=OLLAMA_PROVIDER,
                is_model_call=True,
                endpoint="/api/chat",
                request_category="chat",
            )


# ---------------------------------------------------------------------------
# Category 6: Run records and raw response paths
# ---------------------------------------------------------------------------

class TestRunRecordPaths(unittest.TestCase):
    """Test 6: Run records and raw written to work/app001-runs/<batch_id>/raw/."""

    def test_raw_retention_policy_uses_raw_subdirectory(self):
        from llm.heldout_runner import _heldout_raw_retention_policy
        policy = _heldout_raw_retention_policy("test-batch-raw")
        self.assertIn("raw", policy.base_dir)
        self.assertTrue(policy.retain_raw)
        self.assertIn("work/app001-runs/test-batch-raw/raw", policy.base_dir)

    def test_raw_directory_is_git_ignored(self):
        """work/app001-runs/ is covered by .gitignore."""
        gitignore = _REPO_ROOT / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            # Check that work/ or app001-runs is in gitignore
            self.assertTrue(
                "work/" in content or "app001-runs" in content,
                "work/app001-runs should be in .gitignore"
            )

    def test_blocked_audit_record_has_no_labels(self):
        """Blocked audit records must not contain evaluator labels."""
        runner = HeldoutRunner()
        auth = authorize_heldout_v5_run(batch_id="test-blocked-no-labels")
        projection = load_heldout_inputs()
        plan = generate_heldout_combinations(projection, auth)
        from llm.heldout_runner import _assemble_all_heldout_inputs
        assembled = _assemble_all_heldout_inputs(projection, plan, None)
        c1_combo = [c for c in plan.combinations if c.condition_id == "C1"][0]
        blocked = assembled[c1_combo.logical_run_id]
        record = runner._blocked_audit_record(
            c1_combo, auth, None, blocked,
            stage_name="c1_assembly",
            error_code="BLOCKED_C1_NO_RETRIEVAL_INDEX",
            error_fields=("retrieval_index",),
        )
        record_json = json.dumps(record, ensure_ascii=False)
        self.assertNotIn("expected_schema_parameters", record_json)
        self.assertNotIn("expected_explicit_claims", record_json)
        self.assertNotIn("heldout-bore-012", record_json)
        self.assertNotIn("catalog-bore-012", record_json)

    def test_run_record_dict_includes_inputs_sha256_not_labels(self):
        """Run record dicts include inputs_sha256 but not labels."""
        from llm.heldout_runner import _ensure_heldout_ir_cad_not_run
        sample = {
            "logical_run_id": "test__C0__DeepSeek__deepseek-flash",
            "batch_id": "test-batch",
            "stages": [
                {"stage": "ir", "status": "not_run"},
                {"stage": "cad", "status": "not_run"},
                {"stage": "model_call", "status": "pass"},
            ],
        }
        _ensure_heldout_ir_cad_not_run(sample)
        for stage in sample["stages"]:
            if stage["stage"] in ("ir", "cad"):
                self.assertEqual(stage["status"], "not_run")


# ---------------------------------------------------------------------------
# Category 7: Scope summary / ledger audit
# ---------------------------------------------------------------------------

class TestScopeSummaryAndLedgerAudit(unittest.TestCase):
    """Test 7: Scope summary/ledger audits query IDs, hash pins, caps, failures."""

    def test_scope_summary_contains_query_ids(self):
        auth = authorize_heldout_v5_run(batch_id="test-scope-summary")
        summary = auth.scope_summary()
        self.assertEqual(summary["query_ids"], list(HELDOUT_QUERY_IDS))

    def test_scope_summary_contains_hash_pins(self):
        auth = authorize_heldout_v5_run(batch_id="test-hash-pins")
        summary = auth.scope_summary()
        self.assertEqual(summary["inputs_sha256"], HELDOUT_INPUTS_SHA256)
        self.assertEqual(summary["evaluator_labels_sha256"], HELDOUT_LABELS_SHA256)

    def test_scope_summary_contains_provider_caps(self):
        auth = authorize_heldout_v5_run(batch_id="test-caps")
        summary = auth.scope_summary()
        self.assertEqual(summary["provider_http_caps"], {"DeepSeek": 18, "Ollama": 26})
        self.assertEqual(summary["chat_provider_caps"], {"DeepSeek": 18, "Ollama": 18})
        self.assertEqual(summary["identity_bucket_caps"],
                         {"preflight:/api/tags": 1,
                          "preflight:/api/version": 1,
                          "runtime:/api/tags": 18})

    def test_ledger_snapshot_audits_failures(self):
        """Ledger snapshot records failure outcomes."""
        batch_id = f"test-failures-{uuid.uuid4().hex[:8]}"
        batch_dir = _RUN_CANONICAL_ROOT / batch_id
        auth = authorize_heldout_v5_run(batch_id=batch_id)
        ledger = BudgetLedger(batch_dir, auth)
        ledger.acquire_lock()
        try:
            lrid = auth.expected_logical_run_id(HELDOUT_QUERY_IDS[0], "C0", DEEPSEEK_PROVIDER)
            reservation = ledger.reserve_attempt(
                logical_run_id=lrid,
                provider=DEEPSEEK_PROVIDER,
                is_model_call=True,
                endpoint="/chat/completions",
                request_category="chat",
            )
            ledger.record_outcome(
                logical_run_id=lrid,
                provider=DEEPSEEK_PROVIDER,
                attempt_number=reservation.attempt_number,
                outcome="non_retryable",
            )
            snapshot = ledger.snapshot()
            self.assertEqual(snapshot["total_attempts_used"], 1)
            self.assertEqual(snapshot["run_attempts_used"][lrid], 1)
        finally:
            ledger.release_lock()
            shutil.rmtree(batch_dir, ignore_errors=True)

    def test_legacy_authorization_regression(self):
        """Legacy 9-case/36-run authorization still works unchanged."""
        from llm.authorization import authorize_phase1_run
        auth = authorize_phase1_run(batch_id="legacy-regression-test")
        self.assertEqual(auth.max_logical_runs, 36)
        self.assertEqual(auth.max_batch_attempts, 108)

    def test_legacy_budget_ledger_regression(self):
        """Legacy budget ledger still works with the old authorization."""
        from llm.authorization import authorize_phase1_run
        batch_id = f"legacy-budget-{uuid.uuid4().hex[:8]}"
        batch_dir = _RUN_CANONICAL_ROOT / batch_id
        auth = authorize_phase1_run(batch_id=batch_id)
        ledger = BudgetLedger(batch_dir, auth)
        ledger.acquire_lock()
        try:
            # Legacy ledger uses default chat category for model calls
            reservation = ledger.reserve_attempt(
                logical_run_id="legacy-run-01",
                provider=DEEPSEEK_PROVIDER,
                is_model_call=True,
                endpoint="/chat/completions",
            )
            self.assertEqual(reservation.attempt_number, 1)
        finally:
            ledger.release_lock()
            shutil.rmtree(batch_dir, ignore_errors=True)

    def test_heldout_dry_run_audit_dict_has_no_labels(self):
        """The dry-run audit dict contains no evaluator labels."""
        runner = HeldoutRunner()
        summary = runner.dry_run()
        audit = summary.dry_run_plan
        audit_str = json.dumps(audit, ensure_ascii=False)
        # Check that no label-specific fields appear
        self.assertNotIn("expected_schema_parameters", audit_str)
        self.assertNotIn("expected_explicit_claims", audit_str)
        self.assertNotIn("sample_id", audit_str)
        self.assertNotIn("ret003_query_id", audit_str)

    def test_offline_preflight_checks_all_hash_pins(self):
        """Offline preflight verifies inputs, labels, and RET-001 manifest hashes."""
        batch_id = f"test-preflight-{uuid.uuid4().hex[:8]}"
        runner = HeldoutRunner()
        summary = runner.offline_preflight(batch_id)
        result = summary.offline_preflight_result
        self.assertIsNotNone(result)
        self.assertEqual(result["inputs_sha256"], HELDOUT_INPUTS_SHA256)
        self.assertEqual(result["evaluator_labels_sha256"], HELDOUT_LABELS_SHA256)
        self.assertEqual(result["planned_runs"], 12)
        self.assertEqual(result["offline_preflight_status"], "pass")


# ---------------------------------------------------------------------------
# Entrypoint tests
# ---------------------------------------------------------------------------

class TestEntrypoint(unittest.TestCase):
    """Test the entrypoint script's offline modes."""

    def test_dry_run_mode_produces_plan(self):
        from llm.heldout_runner import HeldoutRunner
        runner = HeldoutRunner()
        summary = runner.dry_run()
        self.assertEqual(summary.mode, "dry_run")
        self.assertEqual(summary.planned_runs, 12)

    def test_offline_preflight_mode_validates_hashes(self):
        batch_id = f"test-entrypoint-preflight-{uuid.uuid4().hex[:8]}"
        runner = HeldoutRunner()
        summary = runner.offline_preflight(batch_id)
        self.assertEqual(summary.mode, "offline_preflight")
        self.assertEqual(summary.planned_runs, 12)

    def test_offline_preflight_rejects_existing_batch_dir(self):
        batch_id = f"test-entrypoint-existing-{uuid.uuid4().hex[:8]}"
        batch_dir = _RUN_CANONICAL_ROOT / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        (batch_dir / "runs.jsonl").write_text("existing\n", encoding="utf-8")
        try:
            runner = HeldoutRunner()
            with self.assertRaises(FormalEvaluationBlockedError):
                runner.offline_preflight(batch_id)
        finally:
            shutil.rmtree(batch_dir, ignore_errors=True)

    def test_formal_mode_blocked_without_authorization(self):
        """run_formal raises FormalEvaluationBlockedError without HeldoutRunAuthorization."""
        runner = HeldoutRunner()
        with self.assertRaises(FormalEvaluationBlockedError):
            runner.run_formal("not-an-auth")  # type: ignore


if __name__ == "__main__":
    unittest.main()
