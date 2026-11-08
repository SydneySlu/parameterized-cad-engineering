"""R3-FIX: Tests for the four R3 security fixes.

These tests verify:
1. Temp directory bypass is removed from BudgetLedger
2. Budget token binding prevents forgery, reuse, and mismatch
3. Ollama tags and chat are independently budgeted
4. C1 gate requires a valid frozen RetrievalIndex
"""
import json
import uuid
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from llm.authorization import authorize_phase1_run
from llm.budget import BudgetLedger, BudgetIntegrityError, BudgetExhausted
from llm.real_transport import (
    DeepSeekTransport,
    OllamaTransport,
    BudgetBypassError,
    _BudgetReservationToken,
)
from llm.transport import PreparedRequest
from llm.runner import App001Runner
from llm.gate import FormalEvaluationBlockedError


class TestR3Fix1TempDirectoryBypassRemoved(unittest.TestCase):
    """R3-FIX-1: Temp directory bypass removed from canonical path check."""

    def test_temp_directory_rejected(self):
        """Temporary directory is rejected (no bypass)."""
        import tempfile
        auth = authorize_phase1_run(batch_id="test-temp-reject")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(BudgetIntegrityError) as cm:
                BudgetLedger(Path(td), auth)
            self.assertIn("batch_dir mismatch", str(cm.exception))

    def test_canonical_path_accepted(self):
        """Canonical path work/app001-runs/<batch_id>/ is accepted."""
        auth = authorize_phase1_run(batch_id="test-canonical-ok")
        repo_root = Path(__file__).resolve().parents[2]
        canonical = repo_root / "work" / "app001-runs" / "test-canonical-ok"
        ledger = BudgetLedger(canonical, auth)
        self.assertIsNotNone(ledger)

    def test_wrong_batch_dir_rejected(self):
        """Different batch directory is rejected."""
        auth = authorize_phase1_run(batch_id="test-batch-x")
        repo_root = Path(__file__).resolve().parents[2]
        wrong = repo_root / "work" / "app001-runs" / "wrong-batch-x"
        with self.assertRaises(BudgetIntegrityError) as cm:
            BudgetLedger(wrong, auth)
        self.assertIn("batch_dir mismatch", str(cm.exception))


class TestR3Fix2BudgetTokenBinding(unittest.TestCase):
    """R3-FIX-2: Budget token binding prevents forgery and mismatch."""

    def test_token_cannot_be_constructed_directly(self):
        """Token construction without private key is rejected."""
        with self.assertRaises(BudgetBypassError):
            _BudgetReservationToken(
                object(),  # wrong key
                batch_id="test",
                logical_run_id="run1",
                provider="DeepSeek",
                model="deepseek-flash",
                endpoint="/chat/completions",
                attempt_number=1
            )

    def test_token_reuse_rejected(self):
        """Token can only be consumed once — verified with a real ledger."""
        from llm.authorization import authorize_phase1_run
        from llm.budget import BudgetLedger
        from pathlib import Path as _Path
        import time

        batch_id = f"test-reuse-tkn-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = _Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id
        ledger = BudgetLedger(batch_dir, auth)
        with ledger:
            # Reserve a slot so the token has a real pending record
            reservation = ledger.reserve_attempt(
                logical_run_id="run-reuse",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )
            token = _BudgetReservationToken._create_for_budget_transport(
                batch_id=batch_id,
                logical_run_id="run-reuse",
                provider="DeepSeek",
                model="deepseek-reasoner",
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            # First consume — OK (matches pending record)
            token.consume(
                batch_id=batch_id,
                provider="DeepSeek",
                model="deepseek-reasoner",
                endpoint="/chat/completions"
            )
            # Second consume — rejected (already consumed)
            with self.assertRaises(BudgetBypassError) as cm:
                token.consume(
                    batch_id=batch_id,
                    provider="DeepSeek",
                    model="deepseek-reasoner",
                    endpoint="/chat/completions"
                )
            self.assertIn("already consumed", str(cm.exception))

    def test_token_batch_id_mismatch_rejected(self):
        """Token with wrong batch_id is rejected."""
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="batch1",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions",
            attempt_number=1
        )
        with self.assertRaises(BudgetBypassError) as cm:
            token.consume(
                batch_id="batch2",  # mismatch
                provider="DeepSeek",
                model="deepseek-flash",
                endpoint="/chat/completions"
            )
        self.assertIn("batch_id mismatch", str(cm.exception))

    def test_token_provider_mismatch_rejected(self):
        """Token with wrong provider is rejected."""
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="batch1",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions",
            attempt_number=1
        )
        with self.assertRaises(BudgetBypassError) as cm:
            token.consume(
                batch_id="batch1",
                provider="Ollama",  # mismatch
                model="deepseek-flash",
                endpoint="/chat/completions"
            )
        self.assertIn("provider mismatch", str(cm.exception))

    def test_token_model_mismatch_rejected(self):
        """Token with wrong model is rejected."""
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="batch1",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions",
            attempt_number=1
        )
        with self.assertRaises(BudgetBypassError) as cm:
            token.consume(
                batch_id="batch1",
                provider="DeepSeek",
                model="different-model",  # mismatch
                endpoint="/chat/completions"
            )
        self.assertIn("model mismatch", str(cm.exception))

    def test_token_endpoint_mismatch_rejected(self):
        """Token with wrong endpoint is rejected."""
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="batch1",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions",
            attempt_number=1
        )
        with self.assertRaises(BudgetBypassError) as cm:
            token.consume(
                batch_id="batch1",
                provider="DeepSeek",
                model="deepseek-flash",
                endpoint="/different/endpoint"  # mismatch
            )
        self.assertIn("endpoint mismatch", str(cm.exception))

    @patch('urllib.request.urlopen')
    def test_deepseek_without_token_no_urlopen(self, mock_urlopen):
        """DeepSeek direct call without token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="test-deepseek-no-token")
        transport = DeepSeekTransport(auth)
        request = PreparedRequest(
            provider="DeepSeek",
            model="deepseek-flash",
            base_url="https://api.deepseek.com",
            endpoint="/chat/completions",
            body={"model": "deepseek-flash", "messages": [{"role": "user", "content": "test"}]}
        )
        with self.assertRaises(BudgetBypassError):
            transport.send(request)
        # Verify urlopen was never called
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_ollama_without_token_no_urlopen(self, mock_urlopen):
        """Ollama direct call without token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="test-ollama-no-token")
        transport = OllamaTransport(auth, host="http://localhost:11434")
        request = PreparedRequest(
            provider="Ollama",
            model="qwen3:8b",
            base_url="http://localhost:11434",
            endpoint="/api/chat",
            body={"model": "qwen3:8b", "messages": [{"role": "user", "content": "test"}]}
        )
        with self.assertRaises(BudgetBypassError):
            transport.send(request)
        # Verify urlopen was never called
        self.assertEqual(mock_urlopen.call_count, 0)


class TestR3Fix3OllamaTagsAndChatSeparate(unittest.TestCase):
    """R3-FIX-3: Ollama /api/tags and /api/chat are independently budgeted."""

    @patch('urllib.request.urlopen')
    def test_ollama_send_without_tags_preflight_rejected(self, mock_urlopen):
        """OllamaTransport.send() called with _verified_digest=False is rejected before urlopen."""
        auth = authorize_phase1_run(batch_id="test-ollama-no-preflight")
        transport = OllamaTransport(auth, host="http://localhost:11434")
        # transport._verified_digest is False — send() must reject immediately
        chat_token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="Ollama",
            model="qwen3:8b",
            endpoint="/api/chat",
            attempt_number=1
        )
        request = PreparedRequest(
            provider="Ollama",
            model="qwen3:8b",
            base_url="http://localhost:11434",
            endpoint="/api/chat",
            body={"model": "qwen3:8b", "messages": [{"role": "user", "content": "test"}]}
        )
        # BudgetAwareTransport must call _execute_tags_preflight() first;
        # calling send() directly when digest not verified must be rejected.
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(request, _budget_token=chat_token)
        self.assertIn("preflight", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0, "urlopen must not be called")


class TestR3Fix4C1IndexVerification(unittest.TestCase):
    """R3-FIX-4: C1 gate requires valid frozen RetrievalIndex with correct manifest identity."""

    def test_run_formal_without_index_rejected(self):
        """run_formal with retrieval_index=None is rejected before HTTP."""
        auth = authorize_phase1_run(batch_id="test-no-index")
        runner = App001Runner(retrieval_index=None)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("retrieval_index", str(cm.exception).lower())

    def test_run_formal_with_magic_mock_rejected(self):
        """run_formal with MagicMock index is rejected."""
        auth = authorize_phase1_run(batch_id="test-mock-index")
        fake_index = MagicMock()
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("RetrievalIndex instance", str(cm.exception))

    def test_run_formal_with_wrong_manifest_sha256_rejected(self):
        """run_formal with index with wrong-length sha256 is rejected."""
        auth = authorize_phase1_run(batch_id="test-wrong-sha256")

        from retrieval import RetrievalIndex
        from retrieval.distance import DistancePolicy
        from retrieval.config import DEFAULT_CONFIG_REL_PATH, MANIFEST_REL_PATH
        fake_index = Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = "too-short"  # not 64-hex
        fake_index.manifest_path = Path(MANIFEST_REL_PATH)
        fake_index.manifest_version = "retrieval-manifest.v0"
        fake_index.policy = MagicMock(spec=DistancePolicy)

        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("manifest_sha256", str(cm.exception))

    def test_run_formal_with_wrong_manifest_path_rejected(self):
        """run_formal with index with wrong manifest path is rejected."""
        import hashlib
        auth = authorize_phase1_run(batch_id="test-wrong-path")

        from retrieval import RetrievalIndex
        from retrieval.distance import DistancePolicy
        from retrieval.config import MANIFEST_REL_PATH
        fake_index = Mock(spec=RetrievalIndex)
        # 64-hex sha256 but wrong path
        fake_index.manifest_sha256 = "a" * 64
        fake_index.manifest_path = Path("/wrong/path/to/manifest.jsonl")
        fake_index.manifest_version = "retrieval-manifest.v0"
        fake_index.policy = MagicMock(spec=DistancePolicy)

        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("manifest_path", str(cm.exception))

    def test_run_formal_with_wrong_manifest_version_rejected(self):
        """run_formal with index with wrong manifest version is rejected."""
        auth = authorize_phase1_run(batch_id="test-wrong-version")

        from retrieval import RetrievalIndex
        from retrieval.distance import DistancePolicy
        from retrieval.config import MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION
        repo_root = Path(__file__).resolve().parents[2]
        fake_index = Mock(spec=RetrievalIndex)
        # Use valid-format sha256 — version check fires before sha256 file check
        fake_index.manifest_sha256 = "a" * 64
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = "wrong-version"  # not a valid version
        fake_index.policy = MagicMock(spec=DistancePolicy)

        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("manifest_version", str(cm.exception))

    def test_run_formal_with_non_distance_policy_rejected(self):
        """run_formal with index without real DistancePolicy is rejected."""
        import hashlib
        auth = authorize_phase1_run(batch_id="test-no-policy")

        from retrieval import RetrievalIndex
        from retrieval.config import MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION
        from retrieval.config import sha256_file as _sha256_file
        repo_root = Path(__file__).resolve().parents[2]
        # Use the real sha256 so the sha256 check passes and policy check fires
        real_sha256 = _sha256_file(repo_root / MANIFEST_REL_PATH)
        fake_index = Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = real_sha256
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        fake_index.policy = None  # no policy

        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("policy", str(cm.exception))

    def test_run_formal_with_real_frozen_index_passes_gate(self):
        """Real frozen RetrievalIndex from config passes the identity gate."""
        auth = authorize_phase1_run(batch_id="test-real-index")

        from retrieval import RetrievalIndex
        from retrieval.config import DEFAULT_CONFIG_REL_PATH
        real_index = RetrievalIndex.from_config(DEFAULT_CONFIG_REL_PATH)
        runner = App001Runner(retrieval_index=real_index)

        # Gate should pass; run should fail later (missing acceptance set etc.)
        # but NOT with FormalEvaluationBlockedError about retrieval_index
        try:
            runner.run_formal(auth)
        except FormalEvaluationBlockedError as e:
            # Should NOT be about retrieval_index
            self.assertNotIn("retrieval_index", str(e).lower(),
                             f"Unexpected gate failure: {e}")
        except Exception:
            # Any other failure is acceptable (we're not running for real)
            pass

    def test_run_formal_with_valid_length_wrong_sha256_rejected(self):
        """run_formal with index with correct-length but wrong sha256 value is rejected."""
        auth = authorize_phase1_run(batch_id="test-wrong-sha-value")

        from retrieval import RetrievalIndex
        from retrieval.config import MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION
        repo_root = Path(__file__).resolve().parents[2]
        fake_index = Mock(spec=RetrievalIndex)
        # 64-hex but NOT the actual file hash
        fake_index.manifest_sha256 = "b" * 64
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        from retrieval.distance import DistancePolicy
        fake_index.policy = MagicMock(spec=DistancePolicy)

        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("sha256", str(cm.exception).lower())


class TestR3ForgedTokenLedgerCheck(unittest.TestCase):
    """R3-FIX-1 additional: Forged tokens (no real ledger) must produce 0 urlopen calls."""

    @patch('urllib.request.urlopen')
    def test_forged_token_deepseek_no_urlopen(self, mock_urlopen):
        """A token created with valid fields but no ledger ref is rejected; 0 urlopen."""
        auth = authorize_phase1_run(batch_id="test-forged-deepseek")
        transport = DeepSeekTransport(auth)

        # Create a token with valid fields but NO ledger reference
        forged_token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-reasoner",
            endpoint="/chat/completions",
            attempt_number=1,
            ledger=None,  # No real ledger — forged
        )

        from llm.transport import PreparedRequest
        request = PreparedRequest(
            provider="DeepSeek",
            model="deepseek-reasoner",
            base_url="https://api.deepseek.com",
            endpoint="/chat/completions",
            body={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "x"}]}
        )
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(request, _budget_token=forged_token)
        self.assertIn("no live ledger reference", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0, "urlopen must never be called with forged token")

    @patch('urllib.request.urlopen')
    def test_token_with_no_matching_ledger_record_rejected(self, mock_urlopen):
        """A token that references a ledger but has no matching pending record is rejected."""
        import time
        from pathlib import Path as _Path
        batch_id = f"test-no-rec-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = _Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id
        ledger = __import__('llm.budget', fromlist=['BudgetLedger']).BudgetLedger(batch_dir, auth)
        with ledger:
            # Reserve slot for run-A
            ledger.reserve_attempt(
                logical_run_id="run-A", provider="DeepSeek",
                is_model_call=True, endpoint="/chat/completions"
            )
            # Create token that claims it's for run-B (no such record in ledger)
            bad_token = _BudgetReservationToken._create_for_budget_transport(
                batch_id=batch_id,
                logical_run_id="run-B",  # no reservation for this run
                provider="DeepSeek",
                model="deepseek-reasoner",
                endpoint="/chat/completions",
                attempt_number=1,
                ledger=ledger,
            )
            transport = DeepSeekTransport(auth)
            from llm.transport import PreparedRequest
            request = PreparedRequest(
                provider="DeepSeek",
                model="deepseek-reasoner",
                base_url="https://api.deepseek.com",
                endpoint="/chat/completions",
                body={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "x"}]}
            )
            with self.assertRaises(BudgetBypassError) as cm:
                transport.send(request, _budget_token=bad_token)
            self.assertIn("no pending reservation", str(cm.exception))
            self.assertEqual(mock_urlopen.call_count, 0)


class TestR3BudgetSeparateHTTPModelCounts(unittest.TestCase):
    """R3 Issue 2: HTTP budget and model-call budget are counted separately."""

    def setUp(self):
        from pathlib import Path as _Path
        import time
        self._batch_id = f"test-sep-budget-{uuid.uuid4().hex[:8]}"
        repo_root = _Path(__file__).resolve().parents[2]
        self._batch_dir = repo_root / "work" / "app001-runs" / self._batch_id
        from llm.authorization import authorize_phase1_run
        from llm.budget import BudgetLedger
        self._auth = authorize_phase1_run(batch_id=self._batch_id)
        self._BudgetLedger = BudgetLedger

    def test_tags_reservation_does_not_consume_model_call_quota(self):
        """HTTP-only (tags) reservation does not count toward per-run model-call limit."""
        from llm.budget import BudgetExhausted
        ledger = self._BudgetLedger(self._batch_dir, self._auth)
        with ledger:
            # Reserve 1 tags call (HTTP-only) — should NOT count toward the 3-call quota
            ledger.reserve_attempt(
                logical_run_id="run1", provider="Ollama",
                is_model_call=False, endpoint="/api/tags"
            )
            ledger.record_outcome(
                logical_run_id="run1", provider="Ollama",
                attempt_number=-1, outcome="success"
            )
            # Now reserve 3 model calls — all should succeed (quota not consumed by tags)
            for i in range(1, 4):
                ledger.reserve_attempt(
                    logical_run_id="run1", provider="Ollama",
                    is_model_call=True, endpoint="/api/chat"
                )
                ledger.record_outcome(
                    logical_run_id="run1", provider="Ollama",
                    attempt_number=i, outcome="success"
                )
            # 4th model call must fail (quota = 3)
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(
                    logical_run_id="run1", provider="Ollama",
                    is_model_call=True, endpoint="/api/chat"
                )

    def test_tags_reservation_counts_toward_provider_total(self):
        """HTTP-only (tags) reservation counts toward the provider HTTP total (54)."""
        from llm.budget import BudgetExhausted
        ledger = self._BudgetLedger(self._batch_dir, self._auth)
        with ledger:
            # Use 53 model calls across runs (18×3=54 max, so use 53 first)
            for run_idx in range(17):
                for att in range(1, 4):
                    ledger.reserve_attempt(
                        logical_run_id=f"run-ollama-{run_idx}",
                        provider="Ollama", is_model_call=True, endpoint="/api/chat"
                    )
                    ledger.record_outcome(
                        logical_run_id=f"run-ollama-{run_idx}",
                        provider="Ollama", attempt_number=att, outcome="success"
                    )
            # 2 more model calls = total 53 for Ollama
            for att in range(1, 3):
                ledger.reserve_attempt(
                    logical_run_id="run-ollama-17",
                    provider="Ollama", is_model_call=True, endpoint="/api/chat"
                )
                ledger.record_outcome(
                    logical_run_id="run-ollama-17",
                    provider="Ollama", attempt_number=att, outcome="success"
                )
            # 54th slot: tags call (HTTP-only)
            ledger.reserve_attempt(
                logical_run_id="run-ollama-17",
                provider="Ollama", is_model_call=False, endpoint="/api/tags"
            )
            # 55th slot must fail — provider budget (54) exhausted
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(
                    logical_run_id="run-ollama-17",
                    provider="Ollama", is_model_call=True, endpoint="/api/chat"
                )

    def test_tags_and_chat_outcomes_recorded_separately(self):
        """Tags and chat reservations each have their own outcome record."""
        from llm.budget import BudgetExhausted
        ledger = self._BudgetLedger(self._batch_dir, self._auth)
        with ledger:
            # Tags reservation
            tags_res = ledger.reserve_attempt(
                logical_run_id="run1", provider="Ollama",
                is_model_call=False, endpoint="/api/tags"
            )
            # Chat reservation
            chat_res = ledger.reserve_attempt(
                logical_run_id="run1", provider="Ollama",
                is_model_call=True, endpoint="/api/chat"
            )
            self.assertNotEqual(tags_res.attempt_number, chat_res.attempt_number,
                                "tags and chat must have distinct attempt numbers")
            self.assertTrue(tags_res.attempt_number < 0, "tags attempt number must be negative")
            self.assertTrue(chat_res.attempt_number > 0, "chat attempt number must be positive")
            # Record each outcome separately
            ledger.record_outcome(
                logical_run_id="run1", provider="Ollama",
                attempt_number=tags_res.attempt_number, outcome="success"
            )
            ledger.record_outcome(
                logical_run_id="run1", provider="Ollama",
                attempt_number=chat_res.attempt_number, outcome="success"
            )
            snap = ledger.snapshot()
            self.assertEqual(snap["total_attempts_used"], 2)
            self.assertEqual(snap["run_attempts_used"].get("run1"), 1,
                             "only 1 model call counted in run quota")


class TestR3Fix1TransportLevelMismatch(unittest.TestCase):
    """R3-FIX-1: Transport-level mismatch tests prove urlopen=0 via mock.

    The consume()-level tests in TestR3Fix2BudgetTokenBinding verify the
    BudgetBypassError is raised; these tests additionally verify that when the
    real transport's send() is called with a mismatched token, the mocked
    urllib.request.urlopen is never invoked.
    """

    def _make_deepseek_request(self):
        return PreparedRequest(
            provider="DeepSeek",
            model="deepseek-reasoner",
            base_url="https://api.deepseek.com",
            endpoint="/chat/completions",
            body={"model": "deepseek-reasoner",
                  "messages": [{"role": "user", "content": "x"}]},
        )

    @patch('urllib.request.urlopen')
    def test_transport_batch_mismatch_no_urlopen(self, mock_urlopen):
        """DeepSeek send() with batch-mismatched token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="real-batch")
        transport = DeepSeekTransport(auth)
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="wrong-batch",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-reasoner",
            endpoint="/chat/completions",
            attempt_number=1,
        )
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(self._make_deepseek_request(), _budget_token=token)
        self.assertIn("batch_id mismatch", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_transport_provider_mismatch_no_urlopen(self, mock_urlopen):
        """DeepSeek send() with provider-mismatched token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="batch-mismatch-prov")
        transport = DeepSeekTransport(auth)
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="Ollama",
            model="deepseek-reasoner",
            endpoint="/chat/completions",
            attempt_number=1,
        )
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(self._make_deepseek_request(), _budget_token=token)
        self.assertIn("provider mismatch", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_transport_model_mismatch_no_urlopen(self, mock_urlopen):
        """DeepSeek send() with model-mismatched token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="batch-mismatch-model")
        transport = DeepSeekTransport(auth)
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="DeepSeek",
            model="wrong-model",
            endpoint="/chat/completions",
            attempt_number=1,
        )
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(self._make_deepseek_request(), _budget_token=token)
        self.assertIn("model mismatch", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_transport_endpoint_mismatch_no_urlopen(self, mock_urlopen):
        """DeepSeek send() with endpoint-mismatched token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="batch-mismatch-endpoint")
        transport = DeepSeekTransport(auth)
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-reasoner",
            endpoint="/wrong/endpoint",
            attempt_number=1,
        )
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(self._make_deepseek_request(), _budget_token=token)
        self.assertIn("endpoint mismatch", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    def test_transport_token_reuse_no_urlopen(self, mock_urlopen):
        """DeepSeek send() with already-consumed token: 0 urlopen calls."""
        auth = authorize_phase1_run(batch_id="batch-reuse")
        transport = DeepSeekTransport(auth)
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=auth.batch_id,
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-reasoner",
            endpoint="/chat/completions",
            attempt_number=1,
        )
        token._consumed = True
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(self._make_deepseek_request(), _budget_token=token)
        self.assertIn("already consumed", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 0)


class TestR3Fix2OllamaTagsFailChatBlocked(unittest.TestCase):
    """R3-FIX-2: When /api/tags fails, /api/chat is not sent; outcomes are independent."""

    def _make_ollama_request(self):
        return PreparedRequest(
            provider="Ollama",
            model="qwen3:8b",
            base_url="http://localhost:11434",
            endpoint="/api/chat",
            body={"model": "qwen3:8b",
                  "messages": [{"role": "user", "content": "test"}]},
        )

    @patch('urllib.request.urlopen')
    def test_ollama_tags_fail_urlopen_called_once(self, mock_urlopen):
        """When /api/tags fails, urlopen is called exactly once (tags, not chat)."""
        import urllib.error as _ue
        import time
        mock_urlopen.side_effect = _ue.URLError("Ollama not running")

        batch_id = f"test-tags-fail-urlopen-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetAwareTransport
        from llm.transport import TransportError

        with BudgetLedger(batch_dir, auth) as ledger:
            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner,
                ledger=ledger,
                authorization=auth,
                logical_run_id="run1",
                provider="Ollama",
                model="qwen3:8b",
            )
            with self.assertRaises(TransportError):
                bt.send(self._make_ollama_request())
            # urlopen called exactly once: for /api/tags only, never for /api/chat
            self.assertEqual(mock_urlopen.call_count, 1,
                             "urlopen must be called once (tags only) when tags fail")

    @patch('urllib.request.urlopen')
    def test_ollama_tags_fail_outcomes_recorded_independently(self, mock_urlopen):
        """When /api/tags fails, ledger has exactly 1 attempt (tags only, no chat)."""
        import urllib.error as _ue
        import time
        mock_urlopen.side_effect = _ue.URLError("Ollama not running")

        batch_id = f"test-tags-fail-outcomes-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetAwareTransport
        from llm.transport import TransportError

        with BudgetLedger(batch_dir, auth) as ledger:
            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner,
                ledger=ledger,
                authorization=auth,
                logical_run_id="run1",
                provider="Ollama",
                model="qwen3:8b",
            )
            try:
                bt.send(self._make_ollama_request())
            except Exception:
                pass

            # Read ledger to verify outcomes
            data = ledger._read_ledger()
            attempts = data["attempts"]
            # Exactly 1 attempt: tags only. No chat reservation created.
            self.assertEqual(len(attempts), 1,
                             "Exactly one attempt expected: tags only, no chat reservation")
            tags_rec = attempts[0]
            self.assertEqual(tags_rec["endpoint"], "/api/tags",
                             "The single attempt must be for /api/tags")
            self.assertEqual(tags_rec["outcome"], "non_retryable",
                             "Tags outcome must be non_retryable when /api/tags fails")
            self.assertFalse(tags_rec.get("is_model_call", True),
                             "Tags attempt must NOT be a model call")
            self.assertLess(tags_rec["attempt_number"], 0,
                            "Tags attempt_number must be negative")
            # run_attempts_used must be 0 — no model-call reservation was created
            self.assertEqual(data["run_attempts_used"].get("run1", 0), 0,
                             "run_attempts_used must be 0 when tags fail (no chat reservation)")
            # provider budget must be 1 (only tags)
            self.assertEqual(data["provider_attempts_used"].get("Ollama", 0), 1,
                             "Provider budget must be incremented by 1 (tags only)")


class _FakeHttpResp:
    """Minimal fake HTTP response for urlopen mocks.

    Using unittest.Mock() as a context-manager return value can crash Python
    3.10's unittest error reporter when exceptions propagate through frozen
    dataclass instances (FrozenInstanceError on __traceback__ assignment).
    This plain class avoids that by being a real class, not a Mock.
    """

    def __init__(self, data: bytes, status: int = 200):
        self._data = data
        self.status = status

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# Frozen digest prefix from contract.py — used by all Ollama mock responses.
_FAKE_DIGEST = "sha256:500a1f067a9fabcdef1234567890abcdef1234567890abcdef1234567890abcd"


class TestR4OllamaTagsChatIntegration(unittest.TestCase):
    """R4: Ollama tags/chat integration tests with BudgetAwareTransport.send()."""

    def setUp(self):
        # R3-FIX-R5: _consumed_tokens class variable has been removed (id() reuse bug).
        # No setUp cleanup needed — per-token replay is now handled by self._consumed
        # (instance flag) and cross-token duplicate consumption by ledger _claim_pending_reservation.
        pass

    def _make_ollama_request(self):
        from llm.transport import PreparedRequest
        return PreparedRequest(
            provider="Ollama",
            model="qwen3:8b",
            base_url="http://localhost:11434",
            endpoint="/api/chat",
            body={"model": "qwen3:8b",
                  "messages": [{"role": "user", "content": "test"}]},
        )

    def _tags_ok_response(self):
        """Return a _FakeHttpResp simulating a successful /api/tags reply."""
        import json
        return _FakeHttpResp(
            json.dumps({"models": [{"name": "qwen3:8b", "digest": _FAKE_DIGEST}]}).encode()
        )

    def _chat_ok_response(self):
        """Return a _FakeHttpResp simulating a successful /api/chat reply."""
        import json
        return _FakeHttpResp(
            json.dumps({"model": "qwen3:8b", "message": {"content": "ok"}}).encode()
        )

    @patch('urllib.request.urlopen')
    def test_tags_success_chat_success_full_flow(self, mock_urlopen):
        """Tags success + chat success: 2 HTTP calls, 2 ledger records, run_attempts_used=1."""
        import time

        def side_effect(req_or_url, timeout=None):
            url = req_or_url if isinstance(req_or_url, str) else req_or_url.get_full_url()
            if "/api/tags" in url:
                return self._tags_ok_response()
            elif "/api/chat" in url:
                return self._chat_ok_response()
            raise ValueError(f"Unexpected URL: {url}")

        mock_urlopen.side_effect = side_effect

        batch_id = f"test-r4-chat-ok-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport

        with BudgetLedger(batch_dir, auth) as ledger:
            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=auth,
                logical_run_id="run1", provider="Ollama", model="qwen3:8b",
            )
            response = bt.send(self._make_ollama_request())
            self.assertIsNotNone(response)

            # Verify HTTP calls: tags + chat = 2
            self.assertEqual(mock_urlopen.call_count, 2,
                             "Must call urlopen twice: tags + chat")

            data = ledger._read_ledger()
            attempts = data["attempts"]
            self.assertEqual(len(attempts), 2, "Must have 2 attempt records")

            tags_rec = attempts[0]
            self.assertEqual(tags_rec["endpoint"], "/api/tags")
            self.assertFalse(tags_rec.get("is_model_call", True))
            self.assertLess(tags_rec["attempt_number"], 0)
            self.assertEqual(tags_rec["outcome"], "success")

            chat_rec = attempts[1]
            self.assertEqual(chat_rec["endpoint"], "/api/chat")
            self.assertTrue(chat_rec.get("is_model_call", True))
            self.assertEqual(chat_rec["attempt_number"], 1)
            self.assertEqual(chat_rec["outcome"], "success")

            self.assertEqual(data["run_attempts_used"].get("run1"), 1)
            self.assertEqual(data["provider_attempts_used"].get("Ollama"), 2)
            self.assertEqual(data["total_attempts_used"], 2)

    @patch('urllib.request.urlopen')
    def test_tags_success_chat_fail_outcomes_independent(self, mock_urlopen):
        """Tags success + chat fail: tags=success, chat=non_retryable, counts correct."""
        import time
        import urllib.error

        def side_effect(req_or_url, timeout=None):
            url = req_or_url if isinstance(req_or_url, str) else req_or_url.get_full_url()
            if "/api/tags" in url:
                return self._tags_ok_response()
            elif "/api/chat" in url:
                raise urllib.error.HTTPError(url, 500, "Internal Error", {}, None)
            raise ValueError(f"Unexpected URL: {url}")

        mock_urlopen.side_effect = side_effect

        batch_id = f"test-r4-chat-fail-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport
        from llm.transport import TransportError

        with BudgetLedger(batch_dir, auth) as ledger:
            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=auth,
                logical_run_id="run1", provider="Ollama", model="qwen3:8b",
            )
            with self.assertRaises(TransportError):
                bt.send(self._make_ollama_request())

            # 2 HTTP calls: tags succeeded + chat failed
            self.assertEqual(mock_urlopen.call_count, 2)

            data = ledger._read_ledger()
            attempts = data["attempts"]
            self.assertEqual(len(attempts), 2, "Must have 2 records: tags + chat")

            tags_rec = attempts[0]
            self.assertEqual(tags_rec["endpoint"], "/api/tags")
            self.assertEqual(tags_rec["outcome"], "success",
                             "tags must be success even when chat fails")
            self.assertFalse(tags_rec.get("is_model_call", True))

            chat_rec = attempts[1]
            self.assertEqual(chat_rec["endpoint"], "/api/chat")
            self.assertEqual(chat_rec["outcome"], "transient_retryable",
                             "chat HTTP 500 is transient_retryable per RETRYABLE_CONDITIONS")
            self.assertTrue(chat_rec.get("is_model_call", True))

            # run_attempts_used=1 (chat was attempted as model call)
            self.assertEqual(data["run_attempts_used"].get("run1"), 1)
            self.assertEqual(data["provider_attempts_used"].get("Ollama"), 2)
            self.assertEqual(data["total_attempts_used"], 2)

    @patch('urllib.request.urlopen')
    def test_tags_retry_each_creates_new_reservation(self, mock_urlopen):
        """Tags retry: each tags HTTP request creates separate reservation; tags not in run_attempts_used."""
        import time
        import urllib.error

        call_count = [0]

        def side_effect(req_or_url, timeout=None):
            url = req_or_url if isinstance(req_or_url, str) else req_or_url.get_full_url()
            if "/api/tags" in url:
                call_count[0] += 1
                if call_count[0] == 1:
                    raise urllib.error.URLError("Connection refused")
                return self._tags_ok_response()
            elif "/api/chat" in url:
                return self._chat_ok_response()
            raise ValueError(f"Unexpected URL: {url}")

        mock_urlopen.side_effect = side_effect

        batch_id = f"test-r4-tags-retry-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport
        from llm.transport import TransportError

        with BudgetLedger(batch_dir, auth) as ledger:
            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=auth,
                logical_run_id="run1", provider="Ollama", model="qwen3:8b",
            )
            # First send: tags fail
            with self.assertRaises(TransportError):
                bt.send(self._make_ollama_request())

            # Second send: tags succeed, chat succeed
            response = bt.send(self._make_ollama_request())
            self.assertIsNotNone(response)

            # Total urlopen calls: tags-fail + tags-ok + chat = 3
            self.assertEqual(mock_urlopen.call_count, 3)

            data = ledger._read_ledger()
            attempts = data["attempts"]
            self.assertEqual(len(attempts), 3, "3 attempts: tags-fail, tags-ok, chat")

            tags1 = attempts[0]
            self.assertEqual(tags1["endpoint"], "/api/tags")
            self.assertFalse(tags1.get("is_model_call", True))
            self.assertEqual(tags1["outcome"], "non_retryable")
            self.assertLess(tags1["attempt_number"], 0)

            tags2 = attempts[1]
            self.assertEqual(tags2["endpoint"], "/api/tags")
            self.assertFalse(tags2.get("is_model_call", True))
            self.assertEqual(tags2["outcome"], "success")
            self.assertLess(tags2["attempt_number"], 0)
            self.assertNotEqual(tags1["attempt_number"], tags2["attempt_number"],
                                "Each tags retry must have a distinct negative attempt_number")

            chat_rec = attempts[2]
            self.assertEqual(chat_rec["endpoint"], "/api/chat")
            self.assertTrue(chat_rec.get("is_model_call", True))
            self.assertEqual(chat_rec["attempt_number"], 1)
            self.assertEqual(chat_rec["outcome"], "success")

            # run_attempts_used=1 (only chat counted as model call)
            self.assertEqual(data["run_attempts_used"].get("run1"), 1,
                             "run_attempts_used must count only model calls, not tags retries")
            self.assertEqual(data["provider_attempts_used"].get("Ollama"), 3)
            self.assertEqual(data["total_attempts_used"], 3)

    def test_tags_budget_exhausted_before_urlopen(self):
        """When tags budget is exhausted, reservation fails before urlopen."""
        import time
        from llm.budget import BudgetExhausted

        batch_id = f"test-r4-tags-exhaust-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport

        with BudgetLedger(batch_dir, auth) as ledger:
            # Exhaust Ollama provider budget (54 slots) with model calls
            for i in range(18):
                for attempt in range(1, 4):
                    ledger.reserve_attempt(
                        logical_run_id=f"run-{i}",
                        provider="Ollama",
                        is_model_call=True,
                        endpoint="/api/chat",
                    )
                    ledger.record_outcome(
                        logical_run_id=f"run-{i}",
                        provider="Ollama",
                        attempt_number=attempt,
                        outcome="success",
                    )
            # Provider budget fully exhausted (54/54)

            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=auth,
                logical_run_id="run-new", provider="Ollama", model="qwen3:8b",
            )
            # Must fail at reserve_attempt(tags) — before any urlopen
            try:
                bt.send(self._make_ollama_request())
                self.fail("Expected BudgetExhausted")
            except BudgetExhausted:
                pass

            data = ledger._read_ledger()
            self.assertEqual(data["total_attempts_used"], 54,
                             "No new attempt must be recorded when budget exhausted")

    @patch('urllib.request.urlopen')
    def test_tags_ok_chat_budget_exhausted_no_chat_attempt(self, mock_urlopen):
        """Tags succeed but chat budget exhausted: tags recorded, no chat attempt."""
        import time

        def side_effect(req_or_url, timeout=None):
            url = req_or_url if isinstance(req_or_url, str) else req_or_url.get_full_url()
            if "/api/tags" in url:
                return self._tags_ok_response()
            raise ValueError(f"Should not reach chat: {url}")

        mock_urlopen.side_effect = side_effect

        batch_id = f"test-r4-chat-exhaust-{uuid.uuid4().hex[:8]}"
        auth = authorize_phase1_run(batch_id=batch_id)
        repo_root = Path(__file__).resolve().parents[2]
        batch_dir = repo_root / "work" / "app001-runs" / batch_id

        from llm.real_transport import OllamaTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport, BudgetExhausted

        with BudgetLedger(batch_dir, auth) as ledger:
            # Use 53 model-call slots: 17 runs × 3 attempts + 2 more
            for i in range(17):
                for attempt in range(1, 4):
                    ledger.reserve_attempt(
                        logical_run_id=f"run-{i}",
                        provider="Ollama",
                        is_model_call=True,
                        endpoint="/api/chat",
                    )
                    ledger.record_outcome(
                        logical_run_id=f"run-{i}",
                        provider="Ollama",
                        attempt_number=attempt,
                        outcome="success",
                    )
            for attempt in range(1, 3):
                ledger.reserve_attempt(
                    logical_run_id="run-17",
                    provider="Ollama",
                    is_model_call=True,
                    endpoint="/api/chat",
                )
                ledger.record_outcome(
                    logical_run_id="run-17",
                    provider="Ollama",
                    attempt_number=attempt,
                    outcome="success",
                )
            # 53/54 slots used. tags reservation (54th) will succeed; chat reservation fails.

            inner = OllamaTransport(auth, host="http://localhost:11434")
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=auth,
                logical_run_id="run-new", provider="Ollama", model="qwen3:8b",
            )
            try:
                bt.send(self._make_ollama_request())
                self.fail("Expected BudgetExhausted")
            except BudgetExhausted:
                pass

            # urlopen called exactly once (tags only)
            self.assertEqual(mock_urlopen.call_count, 1, "Only tags HTTP executed")

            data = ledger._read_ledger()
            self.assertEqual(data["total_attempts_used"], 54)
            self.assertEqual(data["provider_attempts_used"].get("Ollama"), 54)

            last = data["attempts"][-1]
            self.assertEqual(last["endpoint"], "/api/tags")
            self.assertEqual(last["outcome"], "success")
            # No chat reservation created
            self.assertEqual(data["run_attempts_used"].get("run-new", 0), 0,
                             "No chat reservation when budget exhausted after tags")


class TestR3Fix3C1PolicyDetails(unittest.TestCase):
    """R3-FIX-3: Policy ranges, weights, and identity must pass frozen validation."""

    def _make_mock_index_with_valid_sha(self, policy):
        """Helper: Mock RetrievalIndex with the real manifest sha256 but custom policy."""
        from retrieval import RetrievalIndex
        from retrieval.config import MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION
        from retrieval.config import sha256_file as _sha256_file
        repo_root = Path(__file__).resolve().parents[2]
        real_sha256 = _sha256_file(repo_root / MANIFEST_REL_PATH)
        fake_index = __import__('unittest.mock', fromlist=['Mock']).Mock(
            spec=RetrievalIndex
        )
        fake_index.manifest_sha256 = real_sha256
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        fake_index.policy = policy
        return fake_index

    def test_run_formal_with_wrong_policy_ranges_rejected(self):
        """run_formal with DistancePolicy having wrong ranges: rejected before HTTP."""
        from retrieval.config import catalog_ranges, CONTINUOUS_FIELDS
        from retrieval.distance import DistancePolicy
        auth = authorize_phase1_run(batch_id="test-wrong-ranges")

        # Build a policy with all ranges shifted by +1
        real_ranges = catalog_ranges()
        bad_ranges = {
            field: (low + 1.0, high + 1.0)
            for field, (low, high) in real_ranges.items()
        }
        bad_policy = DistancePolicy(bad_ranges)
        fake_index = self._make_mock_index_with_valid_sha(bad_policy)
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        msg = str(cm.exception).lower()
        self.assertIn("policy", msg, f"Expected policy mention: {cm.exception}")

    def test_run_formal_with_wrong_policy_weights_rejected(self):
        """run_formal with DistancePolicy having wrong continuous_field_weight: rejected."""
        from retrieval.config import catalog_ranges
        from retrieval.distance import DistancePolicy
        auth = authorize_phase1_run(batch_id="test-wrong-weights")

        bad_policy = DistancePolicy(catalog_ranges(), continuous_field_weight=0.3)
        fake_index = self._make_mock_index_with_valid_sha(bad_policy)
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        msg = str(cm.exception).lower()
        self.assertIn("policy", msg, f"Expected policy mention: {cm.exception}")

    def test_run_formal_with_wrong_policy_identity_rejected(self):
        """run_formal with DistancePolicy whose validate() raises (identity mismatch)."""
        from retrieval.errors import RetrievalError
        from retrieval.distance import DistancePolicy as _DP
        from unittest.mock import Mock
        auth = authorize_phase1_run(batch_id="test-wrong-identity")

        # A mock DistancePolicy whose validate() always raises — simulates
        # any combination of wrong ranges + weights that yields identity mismatch.
        policy_mock = Mock(spec=_DP)
        policy_mock.validate.side_effect = RetrievalError(
            "RETRIEVAL_CONFIG_INVALID",
            "normalization range differs from the frozen 15-row catalog range; "
            "changing ranges or weights requires a new policy id and Codex review",
            stage="config",
        )
        fake_index = self._make_mock_index_with_valid_sha(policy_mock)
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        msg = str(cm.exception).lower()
        self.assertIn("policy", msg, f"Expected policy mention: {cm.exception}")


class TestR5IssueAReservationAtomicity(unittest.TestCase):
    """R5-A: Each pending reservation can be claimed at most once; second token rejected before urlopen."""

    def setUp(self):
        import time
        from pathlib import Path as _Path
        self._batch_id = f"test-r5a-{uuid.uuid4().hex[:8]}"
        from llm.authorization import authorize_phase1_run
        from llm.budget import BudgetLedger
        self._auth = authorize_phase1_run(batch_id=self._batch_id)
        self._repo_root = _Path(__file__).resolve().parents[2]
        self._batch_dir = self._repo_root / "work" / "app001-runs" / self._batch_id
        self._BudgetLedger = BudgetLedger

    def _make_deepseek_request(self):
        from llm.transport import PreparedRequest
        from llm.contract import DEEPSEEK_MODEL
        return PreparedRequest(
            provider="DeepSeek",
            model=DEEPSEEK_MODEL,
            base_url="https://api.deepseek.com",
            endpoint="/chat/completions",
            body={"model": DEEPSEEK_MODEL,
                  "messages": [{"role": "user", "content": "x"}]},
        )

    @patch('urllib.request.urlopen')
    def test_second_token_same_reservation_rejected_before_urlopen(self, mock_urlopen):
        """Two tokens for the same reservation: first succeeds (1 urlopen), second rejected (still 1)."""
        import json
        from llm.real_transport import DeepSeekTransport, _BudgetReservationToken, BudgetBypassError
        from llm.budget import BudgetAwareTransport

        ok_resp = _FakeHttpResp(
            json.dumps({"choices": [{"message": {"content": "ok"}}],
                        "model": "deepseek-flash", "usage": {}}).encode()
        )
        mock_urlopen.return_value = ok_resp

        with self._BudgetLedger(self._batch_dir, self._auth) as ledger:
            # Reserve one slot
            reservation = ledger.reserve_attempt(
                logical_run_id="run1",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )
            # Create two tokens for the same reservation
            from llm.contract import DEEPSEEK_MODEL as _DM
            token1 = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            token2 = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            import os; os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-r5a")
            transport = DeepSeekTransport(self._auth)

            # First token: succeeds, 1 urlopen call
            transport.send(self._make_deepseek_request(), _budget_token=token1)
            ledger.record_outcome(
                logical_run_id="run1", provider="DeepSeek",
                attempt_number=reservation.attempt_number, outcome="success",
            )
            self.assertEqual(mock_urlopen.call_count, 1)

            # Second token for the same reservation: must be rejected before urlopen
            with self.assertRaises(BudgetBypassError) as cm:
                transport.send(self._make_deepseek_request(), _budget_token=token2)
            self.assertIn("no pending reservation", str(cm.exception),
                          "Second token must be rejected by ledger claim check")
            self.assertEqual(mock_urlopen.call_count, 1,
                             "No additional HTTP call when second token is rejected")

    def test_same_token_replay_rejected_by_instance_flag(self):
        """Same token object consumed twice: second consume raises 'already consumed'."""
        from llm.real_transport import _BudgetReservationToken, BudgetBypassError

        with self._BudgetLedger(self._batch_dir, self._auth) as ledger:
            reservation = ledger.reserve_attempt(
                logical_run_id="run1",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )
            from llm.contract import DEEPSEEK_MODEL as _DM
            token = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            # First consume: succeeds
            token.consume(
                batch_id=self._batch_id,
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
            )
            # Second consume of same object: rejected by instance flag
            with self.assertRaises(BudgetBypassError) as cm:
                token.consume(
                    batch_id=self._batch_id,
                    provider="DeepSeek",
                    model=_DM,
                    endpoint="/chat/completions",
                )
            self.assertIn("already consumed", str(cm.exception))

    @patch('urllib.request.urlopen')
    def test_concurrent_claim_at_most_one_network_call(self, mock_urlopen):
        """Simulated concurrent claims: at most one succeeds and at most one network call."""
        import json
        from llm.real_transport import DeepSeekTransport, _BudgetReservationToken, BudgetBypassError
        from llm.budget import BudgetAwareTransport

        ok_resp = _FakeHttpResp(
            json.dumps({"choices": [{"message": {"content": "ok"}}],
                        "model": "deepseek-flash", "usage": {}}).encode()
        )
        mock_urlopen.return_value = ok_resp

        with self._BudgetLedger(self._batch_dir, self._auth) as ledger:
            reservation = ledger.reserve_attempt(
                logical_run_id="run1",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )
            # Two tokens for the same slot (simulating a race)
            from llm.contract import DEEPSEEK_MODEL as _DM
            token_a = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            token_b = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=_DM,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            import os; os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-r5a-concurrent")
            transport = DeepSeekTransport(self._auth)

            successes = 0
            failures = 0
            for tok in (token_a, token_b):
                try:
                    transport.send(self._make_deepseek_request(), _budget_token=tok)
                    if tok is token_a:
                        ledger.record_outcome(
                            logical_run_id="run1", provider="DeepSeek",
                            attempt_number=reservation.attempt_number, outcome="success",
                        )
                    successes += 1
                except BudgetBypassError:
                    failures += 1

            self.assertEqual(successes, 1, "Exactly one token must succeed")
            self.assertEqual(failures, 1, "Exactly one token must be rejected")
            self.assertLessEqual(mock_urlopen.call_count, 1,
                                  "At most one network call for one reservation")

    @patch('urllib.request.urlopen')
    def test_normal_deepseek_flow_still_works(self, mock_urlopen):
        """Normal DeepSeek send via BudgetAwareTransport succeeds end-to-end."""
        import json
        from llm.real_transport import DeepSeekTransport
        from llm.budget import BudgetLedger, BudgetAwareTransport

        ok_resp = _FakeHttpResp(
            json.dumps({"choices": [{"message": {"content": "ok"}}],
                        "model": "deepseek-flash", "usage": {}}).encode()
        )
        mock_urlopen.return_value = ok_resp
        import os; os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-r5a-ds")

        from llm.contract import DEEPSEEK_MODEL as _DM
        with BudgetLedger(self._batch_dir, self._auth) as ledger:
            inner = DeepSeekTransport(self._auth)
            bt = BudgetAwareTransport(
                inner, ledger=ledger, authorization=self._auth,
                logical_run_id="run1", provider="DeepSeek", model=_DM,
            )
            response = bt.send(self._make_deepseek_request())
            self.assertIsNotNone(response)
            self.assertEqual(mock_urlopen.call_count, 1)

            data = ledger._read_ledger()
            self.assertEqual(len(data["attempts"]), 1)
            self.assertEqual(data["attempts"][0]["outcome"], "success")
            self.assertEqual(data["attempts"][0].get("claimed"), True,
                             "Claimed record should have claimed=True after successful send")


class TestR6TrueConcurrentClaimAtomicity(unittest.TestCase):
    """R6: True concurrent threads racing to claim the same reservation.

    Uses two real threads with a synchronization barrier to maximise the
    chance they hit _claim_pending_reservation simultaneously.  Verifies:
      - Exactly one thread succeeds (claimed=True in ledger).
      - The losing thread raises BudgetBypassError before any urlopen.
      - The ledger has exactly one claimed=True record.
      - No FileNotFoundError, JSON corruption or double-success.
    """

    def setUp(self):
        import time
        from pathlib import Path as _Path
        self._batch_id = f"test-r6-conc-{uuid.uuid4().hex[:8]}"
        from llm.authorization import authorize_phase1_run
        from llm.budget import BudgetLedger
        self._auth = authorize_phase1_run(batch_id=self._batch_id)
        self._repo_root = _Path(__file__).resolve().parents[2]
        self._batch_dir = self._repo_root / "work" / "app001-runs" / self._batch_id
        self._BudgetLedger = BudgetLedger

    @patch('urllib.request.urlopen')
    def test_true_concurrent_claim_only_one_succeeds(self, mock_urlopen):
        """Two threads racing to claim the same reservation: exactly one wins, zero or one HTTP call."""
        import json
        import threading
        from llm.real_transport import DeepSeekTransport, _BudgetReservationToken, BudgetBypassError
        from llm.budget import BudgetLedger, BudgetAwareTransport
        from llm.contract import DEEPSEEK_MODEL

        ok_resp = _FakeHttpResp(
            json.dumps({"choices": [{"message": {"content": "ok"}}],
                        "model": "deepseek-flash", "usage": {}}).encode()
        )
        mock_urlopen.return_value = ok_resp

        import os; os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-r6-concurrent")

        with BudgetLedger(self._batch_dir, self._auth) as ledger:
            # Reserve exactly one slot
            reservation = ledger.reserve_attempt(
                logical_run_id="run1",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )

            # Create two independent tokens for the same reservation
            token_a = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=DEEPSEEK_MODEL,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            token_b = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run1",
                provider="DeepSeek",
                model=DEEPSEEK_MODEL,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )

            transport = DeepSeekTransport(self._auth)
            results = {}
            barrier = threading.Barrier(2)

            # Use consume() directly — transport.send() calls consume() before urlopen,
            # so testing consume() directly proves the pre-HTTP rejection.
            def consume_in_thread(name, tok):
                barrier.wait()
                try:
                    tok.consume(
                        batch_id=self._batch_id,
                        provider="DeepSeek",
                        model=DEEPSEEK_MODEL,
                        endpoint="/chat/completions",
                    )
                    results[name] = "success"
                except BudgetBypassError as exc:
                    results[name] = f"rejected: {exc}"
                except Exception as exc:
                    results[name] = f"error: {type(exc).__name__}: {exc}"

            t1 = threading.Thread(target=consume_in_thread, args=("thread_a", token_a))
            t2 = threading.Thread(target=consume_in_thread, args=("thread_b", token_b))
            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)

            # Exactly one thread must succeed, one must be rejected
            successes = [k for k, v in results.items() if v == "success"]
            rejections = [k for k, v in results.items() if v.startswith("rejected")]
            errors = [k for k, v in results.items() if v.startswith("error")]

            self.assertEqual(errors, [],
                             f"No unexpected errors in threads: {results}")
            self.assertEqual(len(successes), 1,
                             f"Exactly one thread must succeed: {results}")
            self.assertEqual(len(rejections), 1,
                             f"Exactly one thread must be rejected: {results}")

            # Ledger must have exactly one claimed=True record
            data = ledger._read_ledger()
            claimed_records = [r for r in data["attempts"] if r.get("claimed")]
            self.assertEqual(len(claimed_records), 1,
                             "Ledger must have exactly one claimed record")

            # urlopen must NOT have been called (consume() raises before send reaches urlopen)
            self.assertEqual(mock_urlopen.call_count, 0,
                             "consume() is called before urlopen; failing thread must not reach HTTP")

    def test_true_concurrent_claim_no_json_corruption(self):
        """Two threads racing: ledger remains valid JSON with correct structure after race."""
        import threading
        from llm.real_transport import _BudgetReservationToken, BudgetBypassError
        from llm.budget import BudgetLedger
        from llm.contract import DEEPSEEK_MODEL

        with BudgetLedger(self._batch_dir, self._auth) as ledger:
            reservation = ledger.reserve_attempt(
                logical_run_id="run2",
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
            )

            token_x = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run2",
                provider="DeepSeek",
                model=DEEPSEEK_MODEL,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )
            token_y = _BudgetReservationToken._create_for_budget_transport(
                batch_id=self._batch_id,
                logical_run_id="run2",
                provider="DeepSeek",
                model=DEEPSEEK_MODEL,
                endpoint="/chat/completions",
                attempt_number=reservation.attempt_number,
                ledger=ledger,
            )

            results = {}
            barrier = threading.Barrier(2)

            def consume_in_thread(name, tok):
                barrier.wait()
                try:
                    tok.consume(
                        batch_id=self._batch_id,
                        provider="DeepSeek",
                        model=DEEPSEEK_MODEL,
                        endpoint="/chat/completions",
                    )
                    results[name] = "success"
                except BudgetBypassError:
                    results[name] = "rejected"
                except Exception as exc:
                    results[name] = f"error:{type(exc).__name__}:{exc}"

            t1 = threading.Thread(target=consume_in_thread, args=("x", token_x))
            t2 = threading.Thread(target=consume_in_thread, args=("y", token_y))
            t1.start(); t2.start()
            t1.join(timeout=10); t2.join(timeout=10)

            # No errors (especially no FileNotFoundError or JSON corruption)
            for name, val in results.items():
                self.assertFalse(val.startswith("error"),
                                 f"Thread {name} had unexpected error: {val}")

            # Ledger is still valid JSON with correct structure
            data = ledger._read_ledger()  # raises if JSON corrupted
            self.assertIn("attempts", data)
            self.assertIn("total_attempts_used", data)
            claimed = [r for r in data["attempts"] if r.get("claimed")]
            self.assertLessEqual(len(claimed), 1,
                                  "At most one record may be claimed after concurrent race")
            successes = [k for k, v in results.items() if v == "success"]
            self.assertEqual(len(successes), 1,
                             f"Exactly one thread must succeed: {results}")


class TestR5IssueBCandidateRolesTopK(unittest.TestCase):
    """R5-B: run_formal() must validate candidate_roles and default_top_k against frozen config."""

    def _make_mock_index_with_all_valid(self, candidate_roles=None, default_top_k=None):
        """Helper: Mock RetrievalIndex with valid frozen identity plus configurable roles/top_k."""
        from retrieval import RetrievalIndex
        from retrieval.config import (
            MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION,
            sha256_file as _sha256_file,
        )
        from retrieval.config import catalog_ranges
        from retrieval.distance import DistancePolicy
        repo_root = Path(__file__).resolve().parents[2]
        real_sha256 = _sha256_file(repo_root / MANIFEST_REL_PATH)
        fake_index = __import__('unittest.mock', fromlist=['Mock']).Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = real_sha256
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        fake_index.policy = DistancePolicy(catalog_ranges())
        fake_index.candidate_roles = (
            candidate_roles if candidate_roles is not None else ("retrieval_source",)
        )
        fake_index.default_top_k = default_top_k if default_top_k is not None else 3
        return fake_index

    def test_frozen_index_candidate_roles_and_top_k_pass(self):
        """RetrievalIndex with correct candidate_roles and default_top_k passes step (f) and (g)."""
        auth = authorize_phase1_run(batch_id="test-r5b-ok")
        fake_index = self._make_mock_index_with_all_valid()
        runner = App001Runner(retrieval_index=fake_index)
        # Should not raise at step (f) or (g); will fail later at batch_dir or batch-level
        try:
            runner.run_formal(auth)
        except FormalEvaluationBlockedError as exc:
            msg = str(exc).lower()
            # Steps (f) and (g) must not be the cause
            self.assertNotIn("candidate_roles", msg,
                             f"candidate_roles check must not block: {exc}")
            self.assertNotIn("default_top_k", msg,
                             f"default_top_k check must not block: {exc}")
        except Exception:
            pass  # any other exception is OK for this test

    def test_wrong_candidate_roles_rejected(self):
        """Wrong candidate_roles is rejected before HTTP."""
        auth = authorize_phase1_run(batch_id="test-r5b-bad-roles")
        fake_index = self._make_mock_index_with_all_valid(
            candidate_roles=("wrong_role",)
        )
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("candidate_roles", str(cm.exception).lower(),
                      f"Expected candidate_roles mention: {cm.exception}")

    def test_missing_candidate_roles_rejected(self):
        """Missing candidate_roles attribute is rejected before HTTP."""
        from unittest.mock import Mock
        from retrieval import RetrievalIndex
        from retrieval.config import (
            MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION,
            sha256_file as _sha256_file,
        )
        from retrieval.config import catalog_ranges
        from retrieval.distance import DistancePolicy

        repo_root = Path(__file__).resolve().parents[2]
        real_sha256 = _sha256_file(repo_root / MANIFEST_REL_PATH)
        fake_index = Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = real_sha256
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        fake_index.policy = DistancePolicy(catalog_ranges())
        # candidate_roles is deliberately not set — will return Mock attribute
        # We override with None via spec behavior
        del fake_index.candidate_roles  # Remove the Mock auto-attribute
        fake_index.default_top_k = 3

        auth = authorize_phase1_run(batch_id="test-r5b-no-roles")
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        # Should mention candidate_roles (missing or type check fails)
        self.assertIn("candidate_roles", str(cm.exception).lower(),
                      f"Expected candidate_roles mention: {cm.exception}")

    def test_wrong_default_top_k_rejected(self):
        """Wrong default_top_k is rejected before HTTP."""
        auth = authorize_phase1_run(batch_id="test-r5b-bad-topk")
        fake_index = self._make_mock_index_with_all_valid(default_top_k=5)
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("default_top_k", str(cm.exception).lower(),
                      f"Expected default_top_k mention: {cm.exception}")

    def test_missing_default_top_k_rejected(self):
        """Missing default_top_k attribute is rejected before HTTP."""
        from unittest.mock import Mock
        from retrieval import RetrievalIndex
        from retrieval.config import (
            MANIFEST_REL_PATH, MANIFEST_FORMAT_VERSION,
            sha256_file as _sha256_file,
        )
        from retrieval.config import catalog_ranges
        from retrieval.distance import DistancePolicy

        repo_root = Path(__file__).resolve().parents[2]
        real_sha256 = _sha256_file(repo_root / MANIFEST_REL_PATH)
        fake_index = Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = real_sha256
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = MANIFEST_FORMAT_VERSION
        fake_index.policy = DistancePolicy(catalog_ranges())
        fake_index.candidate_roles = ("retrieval_source",)
        del fake_index.default_top_k  # Remove the Mock auto-attribute

        auth = authorize_phase1_run(batch_id="test-r5b-no-topk")
        runner = App001Runner(retrieval_index=fake_index)
        with self.assertRaises(FormalEvaluationBlockedError) as cm:
            runner.run_formal(auth)
        self.assertIn("default_top_k", str(cm.exception).lower(),
                      f"Expected default_top_k mention: {cm.exception}")


if __name__ == "__main__":
    unittest.main()
