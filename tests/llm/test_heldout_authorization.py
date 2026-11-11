"""Offline scope and budget tests for the ADR-0019 held-out profile."""

from __future__ import annotations

import shutil
import json
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

from llm.authorization import AuthorizationScopeError
from llm.budget import BudgetExhausted, BudgetLedger
from llm.heldout_authorization import (
    HELDOUT_INPUTS_SHA256,
    HELDOUT_LABELS_SHA256,
    HELDOUT_MAX_BATCH_HTTP,
    HELDOUT_MAX_CHAT_ATTEMPTS,
    HELDOUT_MAX_IDENTITY_ATTEMPTS,
    HELDOUT_QUERY_IDS,
    HELDOUT_PROVIDER_HTTP_CAPS,
    HELDOUT_BATCH_PREFLIGHT_ID,
    authorize_heldout_v5_run,
)


class HeldoutAuthorizationTests(unittest.TestCase):
    def test_factory_returns_exact_hash_bound_scope(self):
        auth = authorize_heldout_v5_run(batch_id="heldout-profile-smoke")
        summary = auth.scope_summary()
        self.assertEqual(auth.query_ids, HELDOUT_QUERY_IDS)
        self.assertEqual(auth.inputs_sha256, HELDOUT_INPUTS_SHA256)
        self.assertEqual(auth.evaluator_labels_sha256, HELDOUT_LABELS_SHA256)
        self.assertEqual(summary["max_chat_attempts"], 36)
        self.assertEqual(summary["max_identity_attempts"], 20)
        self.assertEqual(summary["max_batch_attempts"], 44)
        self.assertEqual(summary["provider_http_caps"], {"DeepSeek": 18, "Ollama": 26})
        self.assertEqual(len(auth.scope_hash()), 64)

    def test_factory_rejects_empty_batch_id(self):
        with self.assertRaises(AuthorizationScopeError):
            authorize_heldout_v5_run(batch_id=" ")

    def test_scope_rejects_changed_input_hash(self):
        auth = authorize_heldout_v5_run(batch_id="heldout-replace-input")
        with self.assertRaises(AuthorizationScopeError):
            replace(auth, inputs_sha256="0" * 64)

    def test_scope_rejects_expanded_run_count(self):
        auth = authorize_heldout_v5_run(batch_id="heldout-replace-runs")
        with self.assertRaises(AuthorizationScopeError):
            replace(auth, max_logical_runs=36)


class HeldoutBudgetLedgerTests(unittest.TestCase):
    def setUp(self):
        self.batch_id = f"heldout-budget-test-{uuid.uuid4().hex}"
        self.batch_dir = Path("work/app001-runs") / self.batch_id
        self.auth = authorize_heldout_v5_run(batch_id=self.batch_id)
        self.ledger = BudgetLedger(self.batch_dir, self.auth)
        self.ledger.acquire_lock()

    def tearDown(self):
        self.ledger.release_lock()
        shutil.rmtree(self.batch_dir, ignore_errors=True)

    def _reserve_chat(self, index: int):
        provider = "DeepSeek" if index < 18 else "Ollama"
        provider_model = "deepseek-flash" if provider == "DeepSeek" else "qwen3:8b"
        provider_index = index % 18
        query_id = HELDOUT_QUERY_IDS[provider_index // 6]
        condition = ("C0", "C1")[(provider_index % 6) // 3]
        logical_run_id = self.auth.expected_logical_run_id(query_id, condition, provider)
        return self.ledger.reserve_attempt(
            logical_run_id=logical_run_id,
            provider=provider,
            is_model_call=True,
            endpoint="/api/chat" if provider == "Ollama" else "/chat/completions",
            request_category="chat",
        )

    def test_category_provider_and_batch_chat_caps_are_enforced(self):
        # Each provider receives 18 chat reservations; total is 36.
        for i in range(36):
            self._reserve_chat(i)
        snapshot = self.ledger.snapshot()
        self.assertEqual(snapshot["category_attempts_used"]["chat"], 36)
        self.assertEqual(snapshot["provider_attempts_used"], {"DeepSeek": 18, "Ollama": 18})
        self.assertEqual(snapshot["total_attempts_used"], 36)
        with self.assertRaises(BudgetExhausted):
            self._reserve_chat(36)

    def test_each_provider_chat_cap_is_enforced_independently(self):
        deepseek_runs = [
            self.auth.expected_logical_run_id(query_id, condition, "DeepSeek")
            for query_id in HELDOUT_QUERY_IDS
            for condition in ("C0", "C1")
        ]
        for logical_run_id in deepseek_runs:
            for _ in range(3):
                self.ledger.reserve_attempt(
                    logical_run_id=logical_run_id,
                    provider="DeepSeek",
                    is_model_call=True,
                    endpoint="/chat/completions",
                    request_category="chat",
                )
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=deepseek_runs[0],
                provider="DeepSeek",
                is_model_call=True,
                endpoint="/chat/completions",
                request_category="chat",
            )
        self.assertEqual(self.ledger.snapshot()["total_attempts_used"], 18)

    def test_identity_category_cap_is_enforced_and_not_a_model_attempt(self):
        for endpoint in ("/api/version", "/api/tags"):
            self.ledger.reserve_attempt(
                logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
                provider="Ollama",
                is_model_call=False,
                endpoint=endpoint,
                request_category="identity",
            )
        ollama_runs = [
            self.auth.expected_logical_run_id(query_id, condition, "Ollama")
            for query_id in HELDOUT_QUERY_IDS
            for condition in ("C0", "C1")
        ]
        for logical_run_id in ollama_runs:
            for _ in range(3):
                self.ledger.reserve_attempt(
                    logical_run_id=logical_run_id,
                    provider="Ollama",
                    is_model_call=False,
                    endpoint="/api/tags",
                    request_category="identity",
                )
        snapshot = self.ledger.snapshot()
        self.assertEqual(snapshot["category_attempts_used"]["identity"], 20)
        self.assertEqual(snapshot["run_attempts_used"], {})
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=ollama_runs[0],
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )

    def test_identity_category_rejects_wrong_provider_or_endpoint(self):
        for provider, endpoint in (("DeepSeek", "/api/tags"), ("Ollama", "/api/chat")):
            with self.subTest(provider=provider, endpoint=endpoint):
                with self.assertRaises(BudgetExhausted):
                    self.ledger.reserve_attempt(
                        logical_run_id="bad-identity",
                        provider=provider,
                        is_model_call=False,
                        endpoint=endpoint,
                        request_category="identity",
                    )

    def test_each_preflight_identity_endpoint_is_reserved_at_most_once(self):
        for endpoint in ("/api/version", "/api/tags"):
            self.ledger.reserve_attempt(
                logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
                provider="Ollama",
                is_model_call=False,
                endpoint=endpoint,
                request_category="identity",
            )
            with self.subTest(endpoint=endpoint), self.assertRaises(BudgetExhausted):
                self.ledger.reserve_attempt(
                    logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
                    provider="Ollama",
                    is_model_call=False,
                    endpoint=endpoint,
                    request_category="identity",
                )

    def test_runtime_tags_are_capped_at_three_per_logical_run(self):
        logical_run_id = self.auth.expected_logical_run_id(HELDOUT_QUERY_IDS[0], "C0", "Ollama")
        for _ in range(3):
            self.ledger.reserve_attempt(
                logical_run_id=logical_run_id,
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )

    def test_ledger_upgrade_reconstructs_counters_from_existing_attempt_rows(self):
        logical_run_id = self.auth.expected_logical_run_id(HELDOUT_QUERY_IDS[0], "C0", "DeepSeek")
        self.ledger.reserve_attempt(
            logical_run_id=logical_run_id,
            provider="DeepSeek",
            is_model_call=True,
            endpoint="/chat/completions",
        )
        path = self.batch_dir / "budget_ledger.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "category_attempts_used",
            "chat_attempts_by_provider",
            "identity_attempts_by_bucket",
            "identity_attempts_by_run",
        ):
            data.pop(key, None)
        path.write_text(json.dumps(data), encoding="utf-8")

        snapshot = self.ledger.snapshot()
        self.assertEqual(snapshot["total_attempts_used"], 1)
        self.assertEqual(snapshot["chat_attempts_by_provider"]["DeepSeek"], 1)
        self.ledger.reserve_attempt(
            logical_run_id=logical_run_id,
            provider="DeepSeek",
            is_model_call=True,
            endpoint="/chat/completions",
        )
        self.assertEqual(self.ledger.snapshot()["total_attempts_used"], 2)
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id=logical_run_id,
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )

    def test_heldout_profile_rejects_unclassified_auxiliary_http(self):
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id="unclassified",
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/unknown",
                request_category="auxiliary",
            )

    def test_per_provider_http_cap_is_exact(self):
        # 18 chat plus 8 identity reservations consume the provider cap.
        ollama_runs = [
            self.auth.expected_logical_run_id(query_id, condition, "Ollama")
            for query_id in HELDOUT_QUERY_IDS
            for condition in ("C0", "C1")
        ]
        for i in range(18):
            self.ledger.reserve_attempt(
                logical_run_id=ollama_runs[i // 3],
                provider="Ollama",
                is_model_call=True,
                endpoint="/api/chat",
                request_category="chat",
            )
        self.ledger.reserve_attempt(
            logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
            provider="Ollama",
            is_model_call=False,
            endpoint="/api/version",
            request_category="identity",
        )
        self.ledger.reserve_attempt(
            logical_run_id=HELDOUT_BATCH_PREFLIGHT_ID,
            provider="Ollama",
            is_model_call=False,
            endpoint="/api/tags",
            request_category="identity",
        )
        for logical_run_id in ollama_runs:
            self.ledger.reserve_attempt(
                logical_run_id=logical_run_id,
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )
        self.assertEqual(self.ledger.remaining_provider("Ollama"), 0)
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_attempt(
                logical_run_id="ollama-over-cap",
                provider="Ollama",
                is_model_call=False,
                endpoint="/api/tags",
                request_category="identity",
            )


if __name__ == "__main__":
    unittest.main()
