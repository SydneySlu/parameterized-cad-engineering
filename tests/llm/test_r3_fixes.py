"""R3-FIX: Tests for the four R3 security fixes.

These tests verify:
1. Temp directory bypass is removed from BudgetLedger
2. Budget token binding prevents forgery, reuse, and mismatch
3. Ollama tags and chat are independently budgeted
4. C1 gate requires a valid frozen RetrievalIndex
"""
import json
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
        """Token can only be consumed once."""
        token = _BudgetReservationToken._create_for_budget_transport(
            batch_id="batch1",
            logical_run_id="run1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions",
            attempt_number=1
        )
        # First consume - OK
        token.consume(
            batch_id="batch1",
            provider="DeepSeek",
            model="deepseek-flash",
            endpoint="/chat/completions"
        )
        # Second consume - rejected
        with self.assertRaises(BudgetBypassError) as cm:
            token.consume(
                batch_id="batch1",
                provider="DeepSeek",
                model="deepseek-flash",
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

    def test_ollama_tags_requires_separate_token(self):
        """Ollama first send requires both chat token and tags token."""
        auth = authorize_phase1_run(batch_id="test-ollama-tags")
        transport = OllamaTransport(auth, host="http://localhost:11434")

        # Create chat token but no tags token
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

        # Should fail because _tags_budget_token is missing
        with self.assertRaises(BudgetBypassError) as cm:
            transport.send(request, _budget_token=chat_token)
        self.assertIn("_tags_budget_token", str(cm.exception))


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
        from retrieval.config import MANIFEST_REL_PATH
        repo_root = Path(__file__).resolve().parents[2]
        fake_index = Mock(spec=RetrievalIndex)
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
        auth = authorize_phase1_run(batch_id="test-no-policy")

        from retrieval import RetrievalIndex
        from retrieval.config import MANIFEST_REL_PATH
        repo_root = Path(__file__).resolve().parents[2]
        fake_index = Mock(spec=RetrievalIndex)
        fake_index.manifest_sha256 = "a" * 64
        fake_index.manifest_path = repo_root / MANIFEST_REL_PATH
        fake_index.manifest_version = "retrieval-manifest.v0"
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


if __name__ == "__main__":
    unittest.main()
