"""Atomic, recoverable budget ledger for APP-001 Phase 1 formal runs.

Enforces hard attempt budgets:
- Per logical run: max 3 attempts (1 initial + 2 retries)
- Per provider: max 54 attempts
- Total batch: max 108 attempts

The ledger atomically reserves an attempt **before** any network call.
It persists state to a JSON file in the batch directory and can recover
from process restart by reading the ledger.  Concurrent runs of the same
batch are rejected via an exclusive lock file.

If ledger integrity cannot be confirmed (corrupted JSON, missing attempt
records, counter mismatch), the ledger fails closed and refuses all
further reservations.

This module performs NO network calls and reads NO secrets.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .authorization import FormalRunAuthorization


class BudgetError(RuntimeError):
    """Base error for budget violations."""


class BudgetExhausted(BudgetError):
    """Raised when a budget limit would be exceeded."""


class BudgetIntegrityError(BudgetError):
    """Raised when the ledger is corrupted or integrity cannot be confirmed."""


class BudgetConcurrentRunError(BudgetError):
    """Raised when another process holds the batch lock."""


# Safe filename component pattern
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _safe_filename(value: str) -> str:
    return _SAFE_ID_RE.sub("_", value)


@dataclass(frozen=True)
class AttemptReservation:
    """The result of a successful atomic reservation.

    ``attempt_number`` is 1-based (1 = first attempt, 2 = first retry, etc.).
    The reservation is recorded in the ledger; the caller must call
    :meth:`BudgetLedger.record_outcome` after the attempt completes.
    """

    logical_run_id: str
    provider: str
    attempt_number: int  # 1..max_attempts_per_run
    remaining_batch: int
    remaining_provider: int


class BudgetLedger:
    """File-based budget ledger with atomic reservation and restart recovery.

    The ledger file lives at ``<batch_dir>/budget_ledger.json`` and a lock
    file at ``<batch_dir>/budget_ledger.lock``.  All operations are atomic:

    1. Read the ledger JSON.
    2. Verify integrity (counter == len(attempts)).
    3. Check all budgets.
    4. If OK, append a new attempt record and update counters.
    5. Write atomically (temp file + os.replace).

    If the ledger does not exist, it is created fresh.  If it exists but
    is corrupted, :class:`BudgetIntegrityError` is raised and no further
    reservations are possible.
    """

    def __init__(
        self,
        batch_dir: Path,
        authorization: FormalRunAuthorization,
    ) -> None:
        self._batch_dir = Path(batch_dir)
        self._auth = authorization
        self._ledger_path = self._batch_dir / "budget_ledger.json"
        self._lock_path = self._batch_dir / "budget_ledger.lock"
        self._locked = False

    # ------------------------------------------------------------------
    # Lock management
    # ------------------------------------------------------------------

    def acquire_lock(self) -> None:
        """Acquire the exclusive batch lock.

        Raises :class:`BudgetConcurrentRunError` if another process holds it.
        Uses atomic file creation (O_EXCL) -- no platform-specific flock.
        """
        if self._locked:
            return
        self._batch_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(
                str(self._lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            self._locked = True
        except FileExistsError:
            raise BudgetConcurrentRunError(
                f"another process holds the batch lock: {self._lock_path}"
            )

    def release_lock(self) -> None:
        """Release the batch lock if held."""
        if not self._locked:
            return
        try:
            self._lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        self._locked = False

    # ------------------------------------------------------------------
    # Ledger read / write
    # ------------------------------------------------------------------

    def _read_ledger(self) -> dict[str, Any]:
        """Read the ledger, creating a fresh one if it does not exist."""
        if not self._ledger_path.exists():
            return self._fresh_ledger()
        try:
            with open(self._ledger_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            raise BudgetIntegrityError(
                f"ledger file is corrupted and cannot be parsed: {exc}"
            ) from exc
        self._verify_integrity(data)
        return data

    def _fresh_ledger(self) -> dict[str, Any]:
        return {
            "batch_id": self._auth.batch_id,
            "scope_hash": self._auth.scope_hash(),
            "max_batch_attempts": self._auth.max_batch_attempts,
            "max_provider_attempts": self._auth.max_provider_attempts,
            "max_attempts_per_run": self._auth.max_attempts_per_run,
            "providers": sorted(self._auth.providers),
            "total_attempts_used": 0,
            "provider_attempts_used": {p: 0 for p in sorted(self._auth.providers)},
            "run_attempts_used": {},
            "run_results": {},
            "attempts": [],
        }

    def _verify_integrity(self, data: dict[str, Any]) -> None:
        """Verify the ledger is internally consistent.

        Checks:
        - scope_hash matches the authorization
        - total_attempts_used == len(attempts)
        - sum of provider_attempts_used == len(attempts)
        - each run's attempt count <= max_attempts_per_run
        """
        if data.get("scope_hash") != self._auth.scope_hash():
            raise BudgetIntegrityError(
                "ledger scope_hash does not match authorization; "
                "the ledger may belong to a different batch or scope"
            )
        attempts = data.get("attempts", [])
        if not isinstance(attempts, list):
            raise BudgetIntegrityError("ledger 'attempts' is not a list")
        recorded_total = data.get("total_attempts_used", -1)
        if recorded_total != len(attempts):
            raise BudgetIntegrityError(
                f"total_attempts_used ({recorded_total}) != len(attempts) "
                f"({len(attempts)}); ledger is inconsistent"
            )
        provider_counts: dict[str, int] = {}
        for rec in attempts:
            prov = rec.get("provider", "")
            provider_counts[prov] = provider_counts.get(prov, 0) + 1
        stored_provider = data.get("provider_attempts_used", {})
        for prov, count in provider_counts.items():
            if stored_provider.get(prov, -1) != count:
                raise BudgetIntegrityError(
                    f"provider_attempts_used[{prov}] ({stored_provider.get(prov)}) "
                    f"!= actual count ({count})"
                )
        run_counts: dict[str, int] = {}
        for rec in attempts:
            rid = rec.get("logical_run_id", "")
            run_counts[rid] = run_counts.get(rid, 0) + 1
        stored_run = data.get("run_attempts_used", {})
        for rid, count in run_counts.items():
            if count > self._auth.max_attempts_per_run:
                raise BudgetIntegrityError(
                    f"run {rid} has {count} attempts > max {self._auth.max_attempts_per_run}"
                )
        for rid, count in run_counts.items():
            if stored_run.get(rid, -1) != count:
                raise BudgetIntegrityError(
                    f"run_attempts_used[{rid}] ({stored_run.get(rid)}) "
                    f"!= actual count ({count})"
                )

    def _write_ledger_atomic(self, data: dict[str, Any]) -> None:
        """Write the ledger atomically (temp file + os.replace)."""
        self._batch_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self._ledger_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, sort_keys=True, indent=2)
            fh.write("\n")
        os.replace(str(tmp_path), str(self._ledger_path))

    # ------------------------------------------------------------------
    # Atomic reservation
    # ------------------------------------------------------------------

    def reserve_attempt(
        self, *, logical_run_id: str, provider: str
    ) -> AttemptReservation:
        """Atomically reserve one attempt before a network call.

        Checks all budgets (per-run, per-provider, total).  If all pass,
        appends a new attempt record to the ledger and updates counters.

        Returns the :class:`AttemptReservation` with the attempt number.

        Raises:
            BudgetExhausted: if any budget is exceeded.
            BudgetIntegrityError: if the ledger is corrupted.
            BudgetConcurrentRunError: if the lock is not held.
        """
        if not self._locked:
            raise BudgetConcurrentRunError(
                "lock not acquired; call acquire_lock() before reserve_attempt()"
            )
        if provider not in self._auth.providers:
            raise BudgetExhausted(
                f"provider {provider!r} not in authorized scope"
            )
        data = self._read_ledger()
        run_count = data["run_attempts_used"].get(logical_run_id, 0)
        if run_count >= self._auth.max_attempts_per_run:
            raise BudgetExhausted(
                f"run {logical_run_id} already used {run_count} attempts "
                f"(max {self._auth.max_attempts_per_run})"
            )
        prov_count = data["provider_attempts_used"].get(provider, 0)
        if prov_count >= self._auth.max_provider_attempts:
            raise BudgetExhausted(
                f"provider {provider} already used {prov_count} attempts "
                f"(max {self._auth.max_provider_attempts})"
            )
        total = data["total_attempts_used"]
        if total >= self._auth.max_batch_attempts:
            raise BudgetExhausted(
                f"batch already used {total} attempts "
                f"(max {self._auth.max_batch_attempts})"
            )
        # Reserve
        attempt_number = run_count + 1
        record = {
            "logical_run_id": logical_run_id,
            "provider": provider,
            "attempt_number": attempt_number,
            "reserved_at_utc": _utc_now_iso(),
            "outcome": None,
        }
        data["attempts"].append(record)
        data["total_attempts_used"] = total + 1
        data["provider_attempts_used"][provider] = prov_count + 1
        data["run_attempts_used"][logical_run_id] = run_count + 1
        self._write_ledger_atomic(data)
        return AttemptReservation(
            logical_run_id=logical_run_id,
            provider=provider,
            attempt_number=attempt_number,
            remaining_batch=self._auth.max_batch_attempts - (total + 1),
            remaining_provider=self._auth.max_provider_attempts - (prov_count + 1),
        )

    def record_outcome(
        self,
        *,
        logical_run_id: str,
        provider: str,
        attempt_number: int,
        outcome: str,
    ) -> None:
        """Record the outcome of a completed attempt.

        ``outcome`` is a short stable string: ``success``, ``transient_retryable``,
        ``non_retryable``, ``exhausted``, or ``blocked``.
        """
        if not self._locked:
            raise BudgetConcurrentRunError("lock not acquired")
        data = self._read_ledger()
        for rec in reversed(data["attempts"]):
            if (
                rec.get("logical_run_id") == logical_run_id
                and rec.get("provider") == provider
                and rec.get("attempt_number") == attempt_number
                and rec.get("outcome") is None
            ):
                rec["outcome"] = outcome
                rec["completed_at_utc"] = _utc_now_iso()
                break
        else:
            raise BudgetIntegrityError(
                f"no pending attempt found for {logical_run_id}/{provider}/attempt {attempt_number}"
            )
        self._write_ledger_atomic(data)

    def record_run_result(
        self, *, logical_run_id: str, result: str
    ) -> None:
        """Record the final result of a logical run.

        ``result`` is one of ``success``, ``non_retryable_error``,
        ``retry_exhausted``, or ``blocked``.
        """
        if not self._locked:
            raise BudgetConcurrentRunError("lock not acquired")
        data = self._read_ledger()
        data["run_results"][logical_run_id] = result
        self._write_ledger_atomic(data)

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    def remaining_batch(self) -> int:
        data = self._read_ledger()
        return self._auth.max_batch_attempts - data["total_attempts_used"]

    def remaining_provider(self, provider: str) -> int:
        data = self._read_ledger()
        used = data["provider_attempts_used"].get(provider, 0)
        return self._auth.max_provider_attempts - used

    def run_attempts_used(self, logical_run_id: str) -> int:
        data = self._read_ledger()
        return data["run_attempts_used"].get(logical_run_id, 0)

    def run_result(self, logical_run_id: str) -> str | None:
        data = self._read_ledger()
        return data["run_results"].get(logical_run_id)

    def snapshot(self) -> dict[str, Any]:
        """Return a read-only snapshot of the ledger state."""
        data = self._read_ledger()
        return {
            "batch_id": data["batch_id"],
            "total_attempts_used": data["total_attempts_used"],
            "max_batch_attempts": self._auth.max_batch_attempts,
            "remaining_batch": (
                self._auth.max_batch_attempts - data["total_attempts_used"]
            ),
            "provider_attempts_used": dict(data["provider_attempts_used"]),
            "max_provider_attempts": self._auth.max_provider_attempts,
            "run_attempts_used": dict(data["run_attempts_used"]),
            "run_results": dict(data["run_results"]),
            "max_attempts_per_run": self._auth.max_attempts_per_run,
            "attempt_count": len(data["attempts"]),
        }

    def planned_runs(self) -> int:
        """Number of logical runs that have at least one attempt."""
        data = self._read_ledger()
        return len(data["run_attempts_used"])

    def completed_runs(self) -> int:
        """Number of logical runs with a recorded final result."""
        data = self._read_ledger()
        return len(data["run_results"])

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "BudgetLedger":
        self.acquire_lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release_lock()


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
