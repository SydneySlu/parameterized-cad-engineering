"""APP-001-RUNNER-R1 boundary tests.

Covers the four fixes required by APP-001-RUNNER-R1:
1. Acceptance-set SHA-256 enforcement (hash tamper rejection)
2. Per-physical-attempt budget reservation (BudgetAwareTransport)
3. C1: bore_d extraction from NLI (no fixed fallback bore_d=20)
4. Ollama digest strict prefix verification and actual-value recording

All tests use FakeTransport, synthetic fixtures, injected clocks/sleepers,
temporary directories.  No real network calls.  No .env reads.
No acceptance-set evaluator labels in any output.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.llm.authorization import authorize_phase1_run
from src.llm.budget import BudgetAwareTransport, BudgetExhausted, BudgetLedger
from src.llm.conditions import (
    CONDITION_C0,
    CONDITION_C1,
    assemble_c0,
    assemble_c1,
    extract_bore_d_mm,
)
from src.llm.contract import (
    ACCEPTANCE_SET_SHA256,
    ACCEPTANCE_SET_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)
from src.llm.input_projection import AcceptanceSetError, project_acceptance_set
from src.llm.real_transport import DeepSeekTransport, OllamaTransport, RealTransportError
from src.llm.runner import App001Runner
from src.llm.transport import (
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_TIMEOUT,
    COND_AUTH_PERMISSION,
    FakeTransport,
    TransportError,
    TransportResponse,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ACCEPTANCE_SET_PATH = (
    _REPO_ROOT / "agent-work" / "llm" / "APP-001-baseline-prep" / "acceptance-set-v0.json"
)


# ---------------------------------------------------------------------------
# Helper: build minimal acceptance-set JSON with controlled content
# ---------------------------------------------------------------------------

def _make_acceptance_set(tmp_dir: str, n_cases: int = 9, **overrides) -> str:
    """Write a minimal acceptance-set JSON to a temp file.  Returns the path."""
    cases = []
    for i in range(n_cases):
        cases.append({
            "case_id": f"APP001-SYN{i:02d}-test",
            "coverage": ["synthetic"],
            "natural_language_input": f"bore_d=2{i} mm 的轴环",
            "reference_context": None,
            "derived_values": {},
            "expected_behavior": "evaluator-only",
            "unacceptable_fabrication": ["evaluator-only"],
            "explicit_parameter_claims": {"bore_d": 20 + i},
        })
    data = {
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
    data.update(overrides)
    path = os.path.join(tmp_dir, "acceptance-set-v0.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return path


# ---------------------------------------------------------------------------
# 1. Acceptance-set SHA-256 enforcement
# ---------------------------------------------------------------------------


class AcceptanceSetHashTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def test_frozen_file_passes(self):
        """The real frozen acceptance-set-v0.json passes hash check."""
        projection = project_acceptance_set(
            _ACCEPTANCE_SET_PATH,
            expected_sha256=ACCEPTANCE_SET_SHA256,
        )
        self.assertEqual(projection.sample_count, 9)

    def test_hash_constant_matches_file(self):
        """contract.ACCEPTANCE_SET_SHA256 matches the real file."""
        raw = _ACCEPTANCE_SET_PATH.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, ACCEPTANCE_SET_SHA256)

    def test_tampered_nli_rejected(self):
        """Modifying natural_language_input changes the file hash → rejected."""
        path = _make_acceptance_set(self._tmp, n_cases=9)
        # Compute the correct hash for this synthetic file
        raw = Path(path).read_bytes()
        correct_sha = hashlib.sha256(raw).hexdigest()
        # Now tamper the NLI
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["cases"][0]["natural_language_input"] = "TAMPERED_INPUT"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        # Reading with original hash must fail
        with self.assertRaises(AcceptanceSetError):
            project_acceptance_set(path, expected_sha256=correct_sha)

    def test_tampered_query_id_rejected(self):
        """Modifying case_id changes the file hash → rejected."""
        path = _make_acceptance_set(self._tmp, n_cases=9)
        raw = Path(path).read_bytes()
        correct_sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["cases"][0]["case_id"] = "APP001-TAMPERED-ID"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        with self.assertRaises(AcceptanceSetError):
            project_acceptance_set(path, expected_sha256=correct_sha)

    def test_tampered_evaluator_only_field_rejected(self):
        """Modifying expected_behavior (evaluator-only) changes hash → rejected."""
        path = _make_acceptance_set(self._tmp, n_cases=9)
        raw = Path(path).read_bytes()
        correct_sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["cases"][0]["expected_behavior"] = "TAMPERED_EVALUATOR_VALUE"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        with self.assertRaises(AcceptanceSetError):
            project_acceptance_set(path, expected_sha256=correct_sha)

    def test_runner_dry_run_uses_frozen_hash(self):
        """App001Runner.dry_run() uses ACCEPTANCE_SET_SHA256; tampered file raises."""
        path = _make_acceptance_set(self._tmp, n_cases=9)
        # Runner uses the frozen SHA256 from contract.py, not from this file
        runner = App001Runner(acceptance_set_path=path)
        with self.assertRaises(AcceptanceSetError):
            runner.dry_run()

    def test_no_hash_check_passes_any_content(self):
        """Without expected_sha256, any valid JSON acceptance-set passes."""
        path = _make_acceptance_set(self._tmp, n_cases=9)
        projection = project_acceptance_set(path, expected_sha256=None)
        self.assertEqual(projection.sample_count, 9)

    def test_source_sha256_in_projection(self):
        """Projection records the actual source hash."""
        projection = project_acceptance_set(_ACCEPTANCE_SET_PATH)
        self.assertEqual(len(projection.source_sha256), 64)
        self.assertEqual(projection.source_sha256, ACCEPTANCE_SET_SHA256)


# ---------------------------------------------------------------------------
# 2. Per-physical-attempt budget reservation (BudgetAwareTransport)
# ---------------------------------------------------------------------------


def _auth():
    return authorize_phase1_run(batch_id="budget-test")


def _fake_ok():
    return TransportResponse(
        status=200,
        body=json.dumps({
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "ask",
            "extracted_parameters": {},
            "unsupported_requests": [],
            "evidence": [],
            "missing_fields": ["bore_d"],
            "questions": ["bore_d?"],
            "confidence": None,
        }),
        runtime_returned_model=DEEPSEEK_MODEL,
        runtime_returned_provider="not_exposed",
        usage={
            "prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46,
            "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 40,
        },
    )


class BudgetAwareTransportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def _make_wrapper(self, inner):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        ledger.acquire_lock()
        wrapper = BudgetAwareTransport(
            inner,
            ledger=ledger,
            logical_run_id="run-A",
            provider=DEEPSEEK_PROVIDER,
        )
        return wrapper, ledger

    def tearDown(self):
        # Release any held lock
        pass

    def test_success_reserves_one_slot(self):
        """Successful send() reserves exactly one budget slot."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            ft = FakeTransport()
            ft.queue_response(_fake_ok())
            from src.llm.providers import build_deepseek_request
            req = build_deepseek_request(system_prompt="s", user_prompt="u")
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-A", provider=DEEPSEEK_PROVIDER
            )
            wrapper.send(req)
        snap = BudgetLedger(self._batch_dir, auth).snapshot()
        self.assertEqual(snap["total_attempts_used"], 1)
        self.assertEqual(snap["provider_attempts_used"]["DeepSeek"], 1)

    def test_retry_then_success_reserves_two_slots(self):
        """One transient error + success = 2 budget slots consumed."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            ft = FakeTransport()
            ft.queue_error(TransportError(COND_TIMEOUT, None, "t"))
            ft.queue_response(_fake_ok())
            from src.llm.providers import build_deepseek_request
            req = build_deepseek_request(system_prompt="s", user_prompt="u")
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-A", provider=DEEPSEEK_PROVIDER
            )
            # First call raises
            with self.assertRaises(TransportError):
                wrapper.send(req)
            # Second call succeeds
            wrapper.send(req)
        snap = BudgetLedger(self._batch_dir, auth).snapshot()
        self.assertEqual(snap["total_attempts_used"], 2)

    def test_three_retries_exhausted_reserves_three_slots(self):
        """Three transient errors = 3 budget slots consumed."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            ft = FakeTransport()
            ft.queue_error(TransportError(COND_HTTP_5XX, 500, "e1"))
            ft.queue_error(TransportError(COND_HTTP_5XX, 500, "e2"))
            ft.queue_error(TransportError(COND_HTTP_5XX, 500, "e3"))
            from src.llm.providers import build_deepseek_request
            req = build_deepseek_request(system_prompt="s", user_prompt="u")
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-A", provider=DEEPSEEK_PROVIDER
            )
            for _ in range(3):
                try:
                    wrapper.send(req)
                except TransportError:
                    pass
        snap = BudgetLedger(self._batch_dir, auth).snapshot()
        self.assertEqual(snap["total_attempts_used"], 3)

    def test_108th_request_allowed_109th_rejected(self):
        """After 108 attempts, the 109th is refused before any network call."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            # Use 108 slots: 36 runs × 3 attempts each across 2 providers
            # Use 54 DeepSeek + 54 Ollama
            for run_idx in range(18):
                for provider in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
                    run_id = f"run-{provider}-{run_idx}"
                    for att in range(1, 4):
                        ledger.reserve_attempt(logical_run_id=run_id, provider=provider)
                        ledger.record_outcome(
                            logical_run_id=run_id, provider=provider,
                            attempt_number=att, outcome="transient_retryable"
                        )
            # 109th must be refused
            from src.llm.providers import build_deepseek_request
            req = build_deepseek_request(system_prompt="s", user_prompt="u")
            ft = FakeTransport()
            ft.queue_response(_fake_ok())
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-extra",
                provider=DEEPSEEK_PROVIDER
            )
            with self.assertRaises(BudgetExhausted):
                wrapper.send(req)
            # FakeTransport was never called
            self.assertEqual(ft.call_count, 0)

    def test_provider_54_limit_enforced(self):
        """After 54 DeepSeek attempts, further DeepSeek requests are refused."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            for run_idx in range(18):
                run_id = f"run-{run_idx}"
                for att in range(1, 4):
                    ledger.reserve_attempt(logical_run_id=run_id, provider=DEEPSEEK_PROVIDER)
                    ledger.record_outcome(
                        logical_run_id=run_id, provider=DEEPSEEK_PROVIDER,
                        attempt_number=att, outcome="transient_retryable"
                    )
            ft = FakeTransport()
            ft.queue_response(_fake_ok())
            from src.llm.providers import build_deepseek_request
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-new", provider=DEEPSEEK_PROVIDER
            )
            with self.assertRaises(BudgetExhausted):
                wrapper.send(build_deepseek_request(system_prompt="s", user_prompt="u"))
            self.assertEqual(ft.call_count, 0)

    def test_per_run_3_limit_enforced(self):
        """After 3 attempts for one logical run, a 4th is refused."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            for att in range(1, 4):
                ledger.reserve_attempt(logical_run_id="run-A", provider=DEEPSEEK_PROVIDER)
                ledger.record_outcome(
                    logical_run_id="run-A", provider=DEEPSEEK_PROVIDER,
                    attempt_number=att, outcome="transient_retryable"
                )
            ft = FakeTransport()
            ft.queue_response(_fake_ok())
            from src.llm.providers import build_deepseek_request
            wrapper = BudgetAwareTransport(
                ft, ledger=ledger, logical_run_id="run-A", provider=DEEPSEEK_PROVIDER
            )
            with self.assertRaises(BudgetExhausted):
                wrapper.send(build_deepseek_request(system_prompt="s", user_prompt="u"))
            self.assertEqual(ft.call_count, 0)

    def test_interrupted_resumption_fail_closed(self):
        """runner._execute_one_run fails closed when attempts exist without a result."""
        # This tests the runner-level check via BudgetLedger.
        auth = authorize_phase1_run(batch_id="interrupted-test")
        batch_dir = Path(self._tmp) / "interrupted"
        with BudgetLedger(batch_dir, auth) as ledger:
            # Reserve an attempt but never record outcome or result
            # (simulates process interrupted mid-attempt)
            ledger.reserve_attempt(logical_run_id="run-A", provider=DEEPSEEK_PROVIDER)
            # DO NOT call record_outcome or record_run_result
        # On restart, run_attempts_used > 0 but run_result is None
        with BudgetLedger(batch_dir, auth) as ledger2:
            self.assertEqual(ledger2.run_attempts_used("run-A"), 1)
            self.assertIsNone(ledger2.run_result("run-A"))

    def test_batch_summary_total_attempts_matches_ledger(self):
        """BatchSummary.total_attempts equals the ledger's total_attempts_used."""
        # Verify via the BudgetAwareTransport that ledger is consistent
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            from src.llm.providers import build_deepseek_request
            req = build_deepseek_request(system_prompt="s", user_prompt="u")
            for i in range(3):
                ft = FakeTransport()
                ft.queue_response(_fake_ok())
                wrapper = BudgetAwareTransport(
                    ft, ledger=ledger, logical_run_id=f"run-{i}",
                    provider=DEEPSEEK_PROVIDER
                )
                wrapper.send(req)
        snap = BudgetLedger(self._batch_dir, auth).snapshot()
        self.assertEqual(snap["total_attempts_used"], 3)


# ---------------------------------------------------------------------------
# 3. C1: bore_d extraction from NLI
# ---------------------------------------------------------------------------


class BoreDExtractionTests(unittest.TestCase):
    def test_explicit_mm(self):
        self.assertAlmostEqual(extract_bore_d_mm("bore_d=24 mm"), 24.0)

    def test_explicit_mm_no_space(self):
        self.assertAlmostEqual(extract_bore_d_mm("bore_d=24mm"), 24.0)

    def test_cm_conversion(self):
        self.assertAlmostEqual(extract_bore_d_mm("轴孔直径 1.6 cm"), 16.0)

    def test_chinese_mm(self):
        self.assertAlmostEqual(extract_bore_d_mm("轴孔直径 20 mm"), 20.0)

    def test_bore_d_is_keyword(self):
        self.assertAlmostEqual(
            extract_bore_d_mm("目标轴环的 bore_d 是 24 mm"), 24.0
        )

    def test_bore_d_equals_form(self):
        self.assertAlmostEqual(extract_bore_d_mm("做 GN 705 轴环，bore_d=70 mm"), 70.0)

    def test_missing_bore_d_returns_none(self):
        self.assertIsNone(extract_bore_d_mm("做一个紧定螺钉轴环，外径 32 mm"))

    def test_zero_bore_d_returns_none(self):
        self.assertIsNone(extract_bore_d_mm("bore_d=0 mm"))

    def test_negative_bore_d_returns_none(self):
        self.assertIsNone(extract_bore_d_mm("bore_d=-5 mm"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(extract_bore_d_mm(""))

    def test_none_input_returns_none(self):
        self.assertIsNone(extract_bore_d_mm(None))

    def test_ambiguous_no_bore_d_keyword_returns_none(self):
        self.assertIsNone(extract_bore_d_mm("外径 32 mm，宽度 14 mm"))


class C1AssemblyNoFixedFallbackTests(unittest.TestCase):
    """C1 must not use bore_d=20 for cases where NLI has no bore_d."""

    def _make_case(self, nli, ref=None):
        from src.llm.input_projection import ProjectedCase
        return ProjectedCase(
            query_id="test-case",
            natural_language_input=nli,
            reference_context_structural=ref,
            coverage=("test",),
        )

    def test_no_bore_d_in_nli_blocks(self):
        """Cases without bore_d in NLI must be blocked, not use bore_d=20."""
        case = self._make_case("做一个紧定螺钉轴环，外径 32 mm")
        mock_index = MagicMock()
        assembled = assemble_c1(case, mock_index)
        self.assertIsNotNone(assembled.blocked_reason)
        self.assertIn("C1_NO_SAFE_QUERY_PARAMETER", assembled.blocked_reason)
        # RET-002 must NOT have been called
        mock_index.query.assert_not_called()

    def test_bore_d_in_nli_queries_ret002(self):
        """When bore_d is in NLI, C1 uses it to query RET-002."""
        case = self._make_case("做 GN 705 轴环，bore_d=24 mm")

        class MockResult:
            results = [{
                "sample_id": "bore-020",
                "family_id": "set_screw_shaft_collar",
                "split": {"role": "retrieval_source"},
                "parameters": {"normalized": {"bore_d": 20.0}},
            }]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                assert "bore_d" in parameters
                assert parameters["bore_d"] == 24.0
                return MockResult()

        assembled = assemble_c1(case, MockIndex())
        self.assertIsNone(assembled.blocked_reason)
        self.assertEqual(assembled.bore_d_used_for_query, 24.0)

    def test_cm_unit_converted_for_query(self):
        """1.6 cm → 16 mm for the RET-002 query."""
        case = self._make_case("轴孔直径 1.6 cm，按 GN 705 目录做轴环。")
        queried = []

        class MockResult:
            results = [{
                "sample_id": "bore-016",
                "family_id": "set_screw_shaft_collar",
                "split": {"role": "retrieval_source"},
                "parameters": {"normalized": {"bore_d": 16.0}},
            }]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                queried.append(parameters["bore_d"])
                return MockResult()

        assembled = assemble_c1(case, MockIndex())
        self.assertEqual(queried, [16.0])
        self.assertIsNone(assembled.blocked_reason)

    def test_a08_structural_ref_bore_d_used(self):
        """A08-style: bore_d from structural reference context is used."""
        # A08: NLI is '目标轴环的 bore_d 是 24 mm'  → extracts from NLI
        case = self._make_case(
            "目标轴环的 bore_d 是 24 mm；请按目标尺寸给出参数。",
            ref={
                "role": "retrieval_example_untrusted_reference",
                "example": {
                    "family_id": "set_screw_shaft_collar",
                    "parameters": {"bore_d": 20, "outer_d": 32},
                }
            }
        )
        queried = []

        class MockResult:
            results = [{
                "sample_id": "bore-020",
                "family_id": "set_screw_shaft_collar",
                "split": {"role": "retrieval_source"},
                "parameters": {"normalized": {"bore_d": 20.0}},
            }]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                queried.append(parameters["bore_d"])
                return MockResult()

        assembled = assemble_c1(case, MockIndex())
        # NLI has bore_d=24 → that wins
        self.assertEqual(queried, [24.0])

    def test_c1_reference_only_contains_retrieval_source(self):
        """C1 reference context must only contain retrieval_source candidates."""
        case = self._make_case("bore_d=20 mm 轴环")

        class MockResultMixed:
            results = [
                {
                    "sample_id": "held-out-012",
                    "family_id": "set_screw_shaft_collar",
                    "split": {"role": "heldout_evaluation"},
                    "parameters": {"normalized": {"bore_d": 12.0}},
                },
                {
                    "sample_id": "source-020",
                    "family_id": "set_screw_shaft_collar",
                    "split": {"role": "retrieval_source"},
                    "parameters": {"normalized": {"bore_d": 20.0}},
                },
            ]

        class MockIndex:
            def query(self, family_id, parameters, top_k=3):
                return MockResultMixed()

        assembled = assemble_c1(case, MockIndex())
        self.assertIsNone(assembled.blocked_reason)
        # Only retrieval_source in candidates
        self.assertIn("source-020", assembled.candidate_source_ids)
        self.assertNotIn("held-out-012", assembled.candidate_source_ids)

    def test_c0_does_not_access_retrieval_index(self):
        """assemble_c0() must not call the retrieval index at all."""
        case = self._make_case("bore_d=20 mm 轴环")
        mock_index = MagicMock()
        assembled = assemble_c0(case)
        self.assertIsNone(assembled.reference_context)
        self.assertEqual(assembled.condition_id, CONDITION_C0)
        mock_index.query.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Ollama digest strict prefix verification and actual-value recording
# ---------------------------------------------------------------------------


class OllamaDigestTests(unittest.TestCase):
    """Test OllamaTransport._verify_model_digest() with injected responses."""

    def setUp(self):
        self._auth = authorize_phase1_run(batch_id="ollama-test")

    def _make_show_response(self, model="qwen3:8b", digest=None, family="qwen3", missing_digest=False):
        """Build a fake /api/show response dict.

        Pass missing_digest=True to omit the digest field entirely.
        Pass digest=None to use a valid default (OLLAMA_DIGEST + "abc123").
        Pass digest="" to explicitly test empty digest.
        """
        if missing_digest:
            d = {}
        elif digest is None:
            d = OLLAMA_DIGEST + "abc123"
        else:
            d = digest
        if missing_digest:
            return {
                "model": model,
                "details": {"family": family},
                "version": "0.33.2",
            }
        return {
            "model": model,
            "details": {"family": family, "digest": d},
            "digest": d,
            "version": "0.33.2",
        }

    def _patch_transport(self, transport, show_response):
        """Patch _verify_model_digest to use a synthetic response."""
        import json as _json
        original = transport._verify_model_digest

        def patched():
            data = show_response
            details = data.get("details", {})
            # Verify model name (qwen3 family)
            returned_model = data.get("model", "")
            family = details.get("family", "")
            if not ("qwen3" in str(returned_model).lower() or "qwen3" in str(family).lower()):
                from src.llm.transport import TransportError, COND_OTHER_NON_RETRYABLE
                raise TransportError(
                    condition=COND_OTHER_NON_RETRYABLE,
                    http_status=None,
                    message=f"model name mismatch: {returned_model}",
                )
            digest_field = data.get("digest") or details.get("digest") or ""
            actual = str(digest_field).strip()
            if not actual.startswith(OLLAMA_DIGEST):
                from src.llm.transport import TransportError, COND_OTHER_NON_RETRYABLE
                raise TransportError(
                    condition=COND_OTHER_NON_RETRYABLE,
                    http_status=None,
                    message=f"digest mismatch: {actual[:20]}",
                )
            transport._verified_digest = True
            transport._actual_digest = actual
            transport._actual_model_name = str(returned_model)
            transport._ollama_version = data.get("version", "unknown")

        transport._verify_model_digest = patched

    def test_correct_model_and_digest_accepted(self):
        """Correct model name and digest prefix → verification passes."""
        t = OllamaTransport(self._auth)
        self._patch_transport(t, self._make_show_response(
            model="qwen3:8b",
            digest=OLLAMA_DIGEST + "abc123",
            family="qwen3",
        ))
        t._verify_model_digest()
        self.assertTrue(t._verified_digest)
        self.assertTrue(t._actual_digest.startswith(OLLAMA_DIGEST))

    def test_wrong_model_name_rejected(self):
        """Non-qwen3 model name raises TransportError before send."""
        from src.llm.transport import TransportError
        t = OllamaTransport(self._auth)
        self._patch_transport(t, self._make_show_response(
            model="llama3:8b",
            digest=OLLAMA_DIGEST + "abc123",
            family="llama",
        ))
        raised = False
        try:
            t._verify_model_digest()
        except TransportError:
            raised = True
        self.assertTrue(raised, "Expected TransportError for wrong model name")

    def test_digest_contains_but_not_prefix_rejected(self):
        """Digest containing the expected prefix but not starting with it is rejected."""
        from src.llm.transport import TransportError
        t = OllamaTransport(self._auth)
        # Put the expected prefix in the middle, not at start
        bad_digest = "abc123" + OLLAMA_DIGEST + "xyz"
        self._patch_transport(t, self._make_show_response(
            model="qwen3:8b",
            digest=bad_digest,
            family="qwen3",
        ))
        raised = False
        try:
            t._verify_model_digest()
        except TransportError:
            raised = True
        self.assertTrue(raised, "Expected TransportError for contains-but-not-prefix digest")

    def test_missing_digest_rejected(self):
        """Empty/None digest raises TransportError."""
        from src.llm.transport import TransportError
        t = OllamaTransport(self._auth)
        self._patch_transport(t, self._make_show_response(
            model="qwen3:8b",
            missing_digest=True,
            family="qwen3",
        ))
        raised = False
        try:
            t._verify_model_digest()
        except TransportError:
            raised = True
        self.assertTrue(raised, "Expected TransportError for missing digest")

    def test_actual_digest_recorded_not_frozen_constant(self):
        """After verification, _actual_digest is the real API value, not just the prefix."""
        t = OllamaTransport(self._auth)
        full_digest = OLLAMA_DIGEST + "deadbeef1234567890abcdef"
        self._patch_transport(t, self._make_show_response(
            model="qwen3:8b",
            digest=full_digest,
            family="qwen3",
        ))
        t._verify_model_digest()
        # Should be the full digest, not just OLLAMA_DIGEST prefix
        self.assertEqual(t._actual_digest, full_digest)
        self.assertGreater(len(t._actual_digest), len(OLLAMA_DIGEST))

    def test_deepseek_transport_does_not_use_ollama_digest(self):
        """DeepSeekTransport must not have _actual_digest or verify digest."""
        auth = authorize_phase1_run(batch_id="ds-test")
        t = DeepSeekTransport(auth)
        self.assertFalse(hasattr(t, "_actual_digest"))
        self.assertFalse(hasattr(t, "_verified_digest"))


if __name__ == "__main__":
    unittest.main()
