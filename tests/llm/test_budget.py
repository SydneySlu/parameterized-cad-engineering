"""Tests for src/llm/budget.py — atomic budget ledger.

Tests 5 and 6:
5. Budget counted before call; max 3 per run, max 108 batch, max 54 per provider.
6. Exhausted after each limit; restart from ledger recovers counts; corrupted
   ledger, concurrent run, uncertain state all fail closed.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.llm.authorization import authorize_phase1_run
from src.llm.budget import (
    BudgetConcurrentRunError,
    BudgetExhausted,
    BudgetIntegrityError,
    BudgetLedger,
)


def _auth(batch_id="test-batch"):
    return authorize_phase1_run(batch_id=batch_id)


class BudgetBasicTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def test_fresh_reservation_returns_attempt_1(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        ledger.acquire_lock()
        try:
            res = ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            self.assertEqual(res.attempt_number, 1)
        finally:
            ledger.release_lock()

    def test_second_reservation_same_run_returns_attempt_2(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            ledger.record_outcome(
                logical_run_id="run-A", provider="DeepSeek",
                attempt_number=1, outcome="transient_retryable"
            )
            res2 = ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            self.assertEqual(res2.attempt_number, 2)

    def test_third_reservation_same_run_returns_attempt_3(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            for i in range(1, 3):
                ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
                ledger.record_outcome(
                    logical_run_id="run-A", provider="DeepSeek",
                    attempt_number=i, outcome="transient_retryable"
                )
            res = ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            self.assertEqual(res.attempt_number, 3)

    def test_fourth_reservation_same_run_raises_exhausted(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            for i in range(1, 4):
                ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
                ledger.record_outcome(
                    logical_run_id="run-A", provider="DeepSeek",
                    attempt_number=i, outcome="transient_retryable"
                )
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")

    def test_per_run_budget_independent_across_runs(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            res_a = ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            res_b = ledger.reserve_attempt(logical_run_id="run-B", provider="DeepSeek")
            self.assertEqual(res_a.attempt_number, 1)
            self.assertEqual(res_b.attempt_number, 1)

    def test_remaining_budget_decrements(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            res = ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            self.assertEqual(res.remaining_batch, 107)
            self.assertEqual(res.remaining_provider, 53)

    def test_unknown_provider_rejected(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(logical_run_id="run-A", provider="UNKNOWN")

    def test_record_run_result_stored(self):
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            ledger.record_run_result(logical_run_id="run-A", result="success")
        # Read back
        with BudgetLedger(self._batch_dir, auth) as ledger2:
            self.assertEqual(ledger2.run_result("run-A"), "success")


class BudgetExhaustionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def _exhaust_provider(self, ledger, provider, count):
        run_counter = 0
        for _ in range(count):
            run_id = f"run-{run_counter}-{provider}"
            run_counter += 1
            # Reserve up to 3 per run
            for att in range(1, 4):
                try:
                    ledger.reserve_attempt(
                        logical_run_id=run_id, provider=provider
                    )
                    ledger.record_outcome(
                        logical_run_id=run_id, provider=provider,
                        attempt_number=att, outcome="transient_retryable"
                    )
                except BudgetExhausted:
                    break

    def test_provider_budget_54_exhausted(self):
        """After 54 DeepSeek attempts across runs, further attempts fail closed."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            # Fill exactly 54 attempts across 18 runs × 3 attempts each
            for run_idx in range(18):
                run_id = f"run-ds-{run_idx}"
                for att in range(1, 4):
                    ledger.reserve_attempt(logical_run_id=run_id, provider="DeepSeek")
                    ledger.record_outcome(
                        logical_run_id=run_id, provider="DeepSeek",
                        attempt_number=att, outcome="transient_retryable"
                    )
            # 19th run must fail
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(
                    logical_run_id="run-ds-18", provider="DeepSeek"
                )

    def test_batch_total_not_exceeded(self):
        """Total batch limit of 108 is enforced."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        with ledger:
            # Use 54 DeepSeek + 54 Ollama = 108 total
            for run_idx in range(18):
                for provider in ("DeepSeek", "Ollama"):
                    run_id = f"run-{provider}-{run_idx}"
                    for att in range(1, 4):
                        ledger.reserve_attempt(
                            logical_run_id=run_id, provider=provider
                        )
                        ledger.record_outcome(
                            logical_run_id=run_id, provider=provider,
                            attempt_number=att, outcome="transient_retryable"
                        )
            # 109th must fail
            with self.assertRaises(BudgetExhausted):
                ledger.reserve_attempt(
                    logical_run_id="run-extra", provider="DeepSeek"
                )


class BudgetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def test_restart_recovers_counts(self):
        """Counts survive a process restart (new BudgetLedger on same dir)."""
        auth = _auth()
        with BudgetLedger(self._batch_dir, auth) as ledger:
            ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
            ledger.record_outcome(
                logical_run_id="run-A", provider="DeepSeek",
                attempt_number=1, outcome="transient_retryable"
            )
            ledger.reserve_attempt(logical_run_id="run-B", provider="Ollama")
        # Restart
        with BudgetLedger(self._batch_dir, auth) as ledger2:
            snap = ledger2.snapshot()
        self.assertEqual(snap["total_attempts_used"], 2)
        self.assertEqual(snap["provider_attempts_used"]["DeepSeek"], 1)
        self.assertEqual(snap["provider_attempts_used"]["Ollama"], 1)

    def test_restart_does_not_double_count(self):
        """Restarting from a ledger doesn't zero or duplicate counts."""
        auth = _auth()
        with BudgetLedger(self._batch_dir, auth) as ledger:
            for i in range(3):
                ledger.reserve_attempt(
                    logical_run_id=f"run-{i}", provider="DeepSeek"
                )
                ledger.record_outcome(
                    logical_run_id=f"run-{i}", provider="DeepSeek",
                    attempt_number=1, outcome="success"
                )
        with BudgetLedger(self._batch_dir, auth) as ledger2:
            snap = ledger2.snapshot()
        self.assertEqual(snap["total_attempts_used"], 3)


class BudgetIntegrityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def test_corrupted_ledger_fails_closed(self):
        """A corrupted ledger file fails closed on read."""
        auth = _auth()
        self._batch_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = self._batch_dir / "budget_ledger.json"
        ledger_path.write_text("NOT VALID JSON", encoding="utf-8")
        ledger = BudgetLedger(self._batch_dir, auth)
        ledger.acquire_lock()
        try:
            with self.assertRaises(BudgetIntegrityError):
                ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
        finally:
            ledger.release_lock()

    def test_wrong_scope_hash_fails_closed(self):
        """A ledger from a different batch is rejected."""
        auth1 = _auth("batch-1")
        auth2 = _auth("batch-2")
        # Create ledger for batch-1
        with BudgetLedger(self._batch_dir, auth1) as ledger1:
            ledger1.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
        # Try to read as batch-2
        ledger2 = BudgetLedger(self._batch_dir, auth2)
        ledger2.acquire_lock()
        try:
            with self.assertRaises(BudgetIntegrityError):
                ledger2.reserve_attempt(logical_run_id="run-B", provider="DeepSeek")
        finally:
            ledger2.release_lock()

    def test_counter_mismatch_fails_closed(self):
        """A ledger with a wrong total counter fails closed."""
        auth = _auth()
        with BudgetLedger(self._batch_dir, auth) as ledger:
            ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")
        # Tamper: inflate the counter
        ledger_path = self._batch_dir / "budget_ledger.json"
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
        data["total_attempts_used"] = 99  # mismatch with len(attempts)=1
        ledger_path.write_text(json.dumps(data), encoding="utf-8")
        ledger2 = BudgetLedger(self._batch_dir, auth)
        ledger2.acquire_lock()
        try:
            with self.assertRaises(BudgetIntegrityError):
                ledger2.reserve_attempt(logical_run_id="run-B", provider="DeepSeek")
        finally:
            ledger2.release_lock()


class BudgetConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._batch_dir = Path(self._tmp) / "batch"

    def test_concurrent_lock_rejected(self):
        """A second BudgetLedger.acquire_lock() while one is held must fail."""
        auth = _auth()
        ledger1 = BudgetLedger(self._batch_dir, auth)
        ledger1.acquire_lock()
        try:
            ledger2 = BudgetLedger(self._batch_dir, auth)
            with self.assertRaises(BudgetConcurrentRunError):
                ledger2.acquire_lock()
        finally:
            ledger1.release_lock()

    def test_reserve_without_lock_rejected(self):
        """reserve_attempt() without acquiring the lock fails."""
        auth = _auth()
        ledger = BudgetLedger(self._batch_dir, auth)
        # Do NOT call acquire_lock
        with self.assertRaises(BudgetConcurrentRunError):
            ledger.reserve_attempt(logical_run_id="run-A", provider="DeepSeek")

    def test_lock_released_allows_second_acquire(self):
        """After releasing, a second BudgetLedger can acquire the lock."""
        auth = _auth()
        ledger1 = BudgetLedger(self._batch_dir, auth)
        ledger1.acquire_lock()
        ledger1.release_lock()
        ledger2 = BudgetLedger(self._batch_dir, auth)
        ledger2.acquire_lock()  # must succeed
        ledger2.release_lock()


if __name__ == "__main__":
    unittest.main()
