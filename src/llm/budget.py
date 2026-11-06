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

    R3-A: The ledger is bound to the unique canonical batch directory
    ``work/app001-runs/<authorization.batch_id>/``.  The same authorization
    cannot be used with multiple different directories to obtain independent
    budget quotas.  Path traversal, symlinks, and non-canonical paths are
    rejected at construction time (fail-closed).
    """

    def __init__(
        self,
        batch_dir: Path,
        authorization: FormalRunAuthorization,
    ) -> None:
        self._batch_dir = Path(batch_dir)
        self._auth = authorization
        # R3-A: Enforce that batch_dir is the unique canonical path for this authorization
        self._verify_canonical_batch_path()
        self._ledger_path = self._batch_dir / "budget_ledger.json"
        self._lock_path = self._batch_dir / "budget_ledger.lock"
        self._locked = False
        # R3-FIX-R6: In-process mutex for read-modify-write operations.
        # Prevents concurrent threads from racing through _claim_pending_reservation,
        # reserve_attempt, record_outcome, or record_run_result simultaneously.
        # The existing _locked / acquire_lock() mechanism guards against *cross-process*
        # concurrent runs; this RLock guards against *intra-process* (thread-level) races.
        import threading
        self._thread_lock = threading.RLock()

    def _verify_canonical_batch_path(self) -> None:
        """Verify batch_dir is the canonical path for authorization.batch_id.

        Rejects:
        - Path traversal (.. components)
        - Symlinks that escape the canonical directory
        - Absolute or relative paths that don't resolve to the expected location
        - Multiple ledgers for the same authorization batch_id
        - ANY directory outside work/app001-runs/<batch_id>/

        Fail-closed: any mismatch raises BudgetIntegrityError.
        No exemptions for temporary directories or testing.
        """
        # Canonical root: work/app001-runs
        from pathlib import Path as _Path
        repo_root = _Path(__file__).resolve().parents[2]
        canonical_root = repo_root / "work" / "app001-runs"

        # Expected canonical path for this batch_id
        safe_batch_id = _safe_filename(self._auth.batch_id)
        if not safe_batch_id:
            raise BudgetIntegrityError(
                f"authorization batch_id {self._auth.batch_id!r} is empty after sanitization"
            )
        expected_canonical = (canonical_root / safe_batch_id).resolve()

        # Resolve the provided batch_dir (follows symlinks)
        try:
            actual_resolved = self._batch_dir.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise BudgetIntegrityError(
                f"batch_dir {self._batch_dir} cannot be resolved: {exc}"
            ) from exc

        # Must match exactly - no exemptions
        if actual_resolved != expected_canonical:
            raise BudgetIntegrityError(
                f"batch_dir mismatch: authorization.batch_id={self._auth.batch_id!r} "
                f"expects {expected_canonical}, got {actual_resolved}; "
                "the same authorization cannot be used with multiple directories"
            )

        # Additional check: the resolved path must be inside canonical_root
        try:
            actual_resolved.relative_to(canonical_root.resolve())
        except ValueError:
            raise BudgetIntegrityError(
                f"batch_dir {actual_resolved} is outside the canonical run root {canonical_root}"
            )

    @property
    def authorization(self) -> FormalRunAuthorization:
        return self._auth

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
        - each run's MODEL-CALL attempt count <= max_attempts_per_run
          (HTTP-only attempts such as Ollama /api/tags are excluded from the
           per-run model-call limit but still counted in the provider/batch totals)
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
        # Only model-call attempts count toward the per-run limit.
        # Records without an explicit is_model_call field default to True for
        # backward compatibility with ledgers written before this field existed.
        run_model_counts: dict[str, int] = {}
        for rec in attempts:
            if rec.get("is_model_call", True):
                rid = rec.get("logical_run_id", "")
                run_model_counts[rid] = run_model_counts.get(rid, 0) + 1
        stored_run = data.get("run_attempts_used", {})
        for rid, count in run_model_counts.items():
            if count > self._auth.max_attempts_per_run:
                raise BudgetIntegrityError(
                    f"run {rid} has {count} model-call attempts "
                    f"> max {self._auth.max_attempts_per_run}"
                )
        for rid, count in run_model_counts.items():
            if stored_run.get(rid, -1) != count:
                raise BudgetIntegrityError(
                    f"run_attempts_used[{rid}] ({stored_run.get(rid)}) "
                    f"!= actual model-call count ({count})"
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
        self, *, logical_run_id: str, provider: str,
        is_model_call: bool = True, endpoint: str = "",
    ) -> AttemptReservation:
        """Atomically reserve one attempt before a network call.

        ``is_model_call`` distinguishes model-call HTTP requests (POST to
        /api/chat or /chat/completions) from auxiliary HTTP requests that are
        still subject to the batch/provider budget but do NOT consume the
        per-run model-call quota.  Currently the only non-model-call request
        is the Ollama ``GET /api/tags`` identity pre-check.

        - ``is_model_call=True``:  checks and updates all three limits
          (total, provider, per-run).
        - ``is_model_call=False``: checks and updates total + provider limits
          only; the per-run model-call limit is untouched.

        ``endpoint`` is stored in the attempt record for cross-validation by
        ``_verify_pending_reservation``.

        For HTTP-only (tags) reservations the ``attempt_number`` in the
        returned ``AttemptReservation`` is a negative serial:
        -1 for the first, -2 for the second, etc.  Model-call attempt numbers
        are positive (1, 2, 3).

        Raises:
            BudgetExhausted: if any applicable budget is exceeded.
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
        with self._thread_lock:
            data = self._read_ledger()

            if is_model_call:
                run_count = data["run_attempts_used"].get(logical_run_id, 0)
                if run_count == 0 and len(data["run_attempts_used"]) >= self._auth.max_logical_runs:
                    raise BudgetExhausted(
                        f"batch already used {len(data['run_attempts_used'])} logical runs "
                        f"(max {self._auth.max_logical_runs})"
                    )
                if run_count >= self._auth.max_attempts_per_run:
                    raise BudgetExhausted(
                        f"run {logical_run_id} already used {run_count} model-call attempts "
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

            # Compute attempt_number:
            # - Model calls: 1-based within the logical run
            # - HTTP-only:   negative serial (-1, -2, ...) to clearly separate from
            #                model-call attempts and enable per-record uniqueness
            if is_model_call:
                attempt_number = data["run_attempts_used"].get(logical_run_id, 0) + 1
            else:
                existing_http_only = sum(
                    1 for rec in data["attempts"]
                    if not rec.get("is_model_call", True)
                    and rec.get("logical_run_id") == logical_run_id
                    and rec.get("provider") == provider
                )
                attempt_number = -(existing_http_only + 1)

            record = {
                "logical_run_id": logical_run_id,
                "provider": provider,
                "attempt_number": attempt_number,
                "endpoint": endpoint,
                "is_model_call": is_model_call,
                "reserved_at_utc": _utc_now_iso(),
                "outcome": None,
            }
            data["attempts"].append(record)
            data["total_attempts_used"] = total + 1
            data["provider_attempts_used"][provider] = prov_count + 1
            if is_model_call:
                run_count = data["run_attempts_used"].get(logical_run_id, 0)
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
        with self._thread_lock:
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
        with self._thread_lock:
            data = self._read_ledger()
            data["run_results"][logical_run_id] = result
            self._write_ledger_atomic(data)

    def _claim_pending_reservation(
        self,
        *,
        logical_run_id: str,
        provider: str,
        attempt_number: int,
        endpoint: str,
    ) -> None:
        """Atomically claim a pending (outcome=None, claimed=False) attempt record.

        Called by ``_BudgetReservationToken.consume()`` before any urlopen.
        Finds the matching unclaimed record, sets ``claimed=True``, and writes
        the ledger atomically.  This prevents any second token from consuming
        the same reservation: a subsequent call for the same record will find
        ``claimed=True`` and raise :class:`~llm.real_transport.BudgetBypassError`.

        Requires the batch lock to be held (BudgetAwareTransport.send() already
        holds it via ``with ledger:`` for the duration of each send call).

        Raises :class:`~llm.real_transport.BudgetBypassError` if no matching
        unclaimed record is found.

        R3-FIX-R5 (Issue A): Replaces the former read-only
        ``_verify_pending_reservation`` which could not prevent two independent
        tokens from both passing the verification step.  The atomic write here
        ensures each reservation is consumed at most once.
        """
        if not self._locked:
            raise BudgetConcurrentRunError(
                "lock not acquired; _claim_pending_reservation requires the lock"
            )
        from .real_transport import BudgetBypassError
        with self._thread_lock:
            data = self._read_ledger()
            for rec in data.get("attempts", []):
                if (
                    rec.get("logical_run_id") == logical_run_id
                    and rec.get("provider") == provider
                    and rec.get("attempt_number") == attempt_number
                    and rec.get("endpoint") == endpoint
                    and rec.get("outcome") is None
                    and not rec.get("claimed", False)  # unclaimed
                ):
                    rec["claimed"] = True
                    self._write_ledger_atomic(data)
                    return  # claimed successfully
            raise BudgetBypassError(
                f"no pending reservation in ledger for "
                f"run={logical_run_id!r} provider={provider!r} "
                f"attempt={attempt_number} endpoint={endpoint!r}; "
                "reservation is missing, already claimed by another token, "
                "or outcome was already recorded"
            )

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


# ---------------------------------------------------------------------------
# Budget-aware transport wrapper
# ---------------------------------------------------------------------------


class BudgetAwareTransport:
    """Transport wrapper that atomically reserves one budget slot per send().

    Each call to ``send()`` performs, in order:
    1. ``ledger.reserve_attempt(logical_run_id, provider)`` — atomic, fail-closed
    2. ``inner.send(request)`` — the real or fake transport
    3. ``ledger.record_outcome(...)`` — records success or error classification

    This ensures every physical HTTP request consumes exactly one budget slot,
    including each internal retry made by ``send_with_retry()``.

    The wrapper is intentionally not a :class:`~src.llm.transport.MockTransport`
    subclass so that the adapter's gate check (``type(transport) is FakeTransport``)
    continues to function correctly: a real formal run uses a real transport wrapped
    in this class, and the adapter must have a valid ``FormalRunAuthorization``.
    """

    def __init__(
        self,
        inner,
        *,
        ledger: BudgetLedger,
        authorization: FormalRunAuthorization | None = None,
        logical_run_id: str,
        provider: str,
        model: str | None = None,
        adapter_run_id: str | None = None,
        query_id: str | None = None,
        condition_id: str | None = None,
    ) -> None:
        authorization = authorization or ledger.authorization
        if model is None:
            from .contract import DEEPSEEK_MODEL, OLLAMA_MODEL
            model = {
                "DeepSeek": DEEPSEEK_MODEL,
                "Ollama": OLLAMA_MODEL,
            }.get(provider)
        # Keep this wrapper tied to the exact authorization and provider/model
        # pair that created the ledger and real transport.
        if ledger.authorization is not authorization:
            raise BudgetIntegrityError("transport authorization does not match ledger")
        if not authorization.provider_model_is_allowed(provider, model):
            raise BudgetExhausted("provider/model pair is outside authorized scope")
        if condition_id is not None and not authorization.condition_is_allowed(condition_id):
            raise BudgetExhausted("condition is outside authorized scope")
        if query_id is not None and logical_run_id != (
            f"{query_id}__{condition_id}__{provider}__{model}"
        ):
            raise BudgetExhausted("logical run ID does not match its query/condition/provider/model binding")
        from .real_transport import DeepSeekTransport, OllamaTransport
        from .transport import FakeTransport

        expected_type = {
            "DeepSeek": DeepSeekTransport,
            "Ollama": OllamaTransport,
        }.get(provider)
        if expected_type is None or (
            type(inner) is not expected_type and type(inner) is not FakeTransport
        ):
            raise BudgetExhausted("inner transport type does not match provider")
        if type(inner) is not FakeTransport and inner.authorization is not authorization:
            raise BudgetIntegrityError("transport authorization does not match inner transport")
        self._inner = inner
        self._ledger = ledger
        self.authorization = authorization
        self._logical_run_id = logical_run_id
        self._provider = provider
        self._model = model
        self._adapter_run_id = adapter_run_id
        self._query_id = query_id
        self._condition_id = condition_id
        self._attempt_numbers: list[int] = []

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def logical_run_id(self) -> str:
        return self._logical_run_id

    @property
    def adapter_run_id(self) -> str | None:
        return self._adapter_run_id

    @property
    def query_id(self) -> str | None:
        return self._query_id

    @property
    def condition_id(self) -> str | None:
        return self._condition_id

    @property
    def uses_real_transport(self) -> bool:
        from .real_transport import DeepSeekTransport, OllamaTransport

        return type(self._inner) in (DeepSeekTransport, OllamaTransport)

    @property
    def attempt_numbers(self) -> list[int]:
        return list(self._attempt_numbers)

    def send(self, request) -> object:
        """Reserve a budget slot, call inner.send(), record outcome.

        For Ollama (first call, before digest is verified):
          1. Reserve tags slot (is_model_call=False, endpoint="/api/tags")
          2. Create tags token
          3. Call _inner._execute_tags_preflight(tags_token) — urlopen for /api/tags
          4. Record tags outcome
          If tags fails → record tags failure, do NOT create chat reservation, re-raise
          5. Reserve chat slot (is_model_call=True, endpoint=request.endpoint)
          6. Create chat token
          7. Call _inner.send(request, _budget_token=chat_token)
          8. Record chat outcome

        This guarantees that a failed /api/tags never produces a chat reservation,
        never increments run_attempts_used, and never inflates provider/batch HTTP counts
        beyond the single tags request that was actually sent.

        For DeepSeek and FakeTransport:
          Reserve slot → create token → send → record outcome (unchanged).

        R3-B-2: All tokens carry a weak reference to this ledger for cross-validation.
        """
        from .real_transport import (
            DeepSeekTransport, OllamaTransport,
            _BudgetReservationToken, OllamaTagsPreflightError,
        )
        from .transport import TransportError

        if type(self._inner) is OllamaTransport and not self._inner._verified_digest:
            return self._send_ollama_with_tags_preflight(request)

        # ----------------------------------------------------------------
        # DeepSeek path (or Ollama with digest already verified, or Fake)
        # ----------------------------------------------------------------
        reservation = self._ledger.reserve_attempt(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            is_model_call=True,
            endpoint=request.endpoint,
        )
        self._attempt_numbers.append(reservation.attempt_number)
        budget_token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=self._ledger._auth.batch_id,
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            model=self._model,
            endpoint=request.endpoint,
            attempt_number=reservation.attempt_number,
            ledger=self._ledger,
        )
        try:
            if type(self._inner) is DeepSeekTransport:
                response = self._inner.send(request, _budget_token=budget_token)
            elif type(self._inner) is OllamaTransport:
                # digest already verified — no tags needed
                response = self._inner.send(request, _budget_token=budget_token)
            else:
                # FakeTransport
                response = self._inner.send(request)
        except TransportError as exc:
            outcome = "transient_retryable" if exc.is_retryable() else "non_retryable"
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=reservation.attempt_number,
                outcome=outcome,
            )
            raise
        except Exception:
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=reservation.attempt_number,
                outcome="non_retryable",
            )
            raise
        self._ledger.record_outcome(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            attempt_number=reservation.attempt_number,
            outcome="success",
        )
        return response

    def _send_ollama_with_tags_preflight(self, request) -> object:
        """Ollama path when /api/tags digest is not yet verified.

        Sequence:
          1. Reserve tags slot → tags token
          2. Execute /api/tags via _inner._execute_tags_preflight()
          3. Record tags outcome
          If tags fails → record failure, raise — NO chat reservation created
          4. Reserve chat slot → chat token
          5. Execute /api/chat via _inner.send()
          6. Record chat outcome
        """
        from .real_transport import (
            OllamaTransport,
            _BudgetReservationToken, OllamaTagsPreflightError,
        )
        from .transport import TransportError

        # Step 1: Reserve tags slot (HTTP-only, not a model call)
        tags_reservation = self._ledger.reserve_attempt(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            is_model_call=False,
            endpoint="/api/tags",
        )
        tags_token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=self._ledger._auth.batch_id,
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            model=self._model,
            endpoint="/api/tags",
            attempt_number=tags_reservation.attempt_number,
            ledger=self._ledger,
        )

        # Step 2-3: Execute /api/tags preflight — sets _inner._verified_digest on success
        try:
            self._inner._execute_tags_preflight(tags_token, self._model)
        except OllamaTagsPreflightError as exc:
            # Record actual failure for the tags reservation
            tags_outcome = "transient_retryable" if exc.is_retryable() else "non_retryable"
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=tags_reservation.attempt_number,
                outcome=tags_outcome,
            )
            # Do NOT create a chat reservation — re-raise so caller sees the error.
            # run_attempts_used is NOT incremented (no is_model_call=True reservation).
            raise
        except Exception:
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=tags_reservation.attempt_number,
                outcome="non_retryable",
            )
            raise

        # Tags succeeded — record it
        self._ledger.record_outcome(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            attempt_number=tags_reservation.attempt_number,
            outcome="success",
        )
        # Tags attempt number is negative; prepend to attempt_numbers list
        self._attempt_numbers.insert(0, tags_reservation.attempt_number)

        # Step 4: Reserve chat slot — only reached if tags succeeded
        reservation = self._ledger.reserve_attempt(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            is_model_call=True,
            endpoint=request.endpoint,
        )
        self._attempt_numbers.append(reservation.attempt_number)
        budget_token = _BudgetReservationToken._create_for_budget_transport(
            batch_id=self._ledger._auth.batch_id,
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            model=self._model,
            endpoint=request.endpoint,
            attempt_number=reservation.attempt_number,
            ledger=self._ledger,
        )

        # Step 5-6: Execute /api/chat — _verified_digest is now True
        try:
            response = self._inner.send(request, _budget_token=budget_token)
        except TransportError as exc:
            outcome = "transient_retryable" if exc.is_retryable() else "non_retryable"
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=reservation.attempt_number,
                outcome=outcome,
            )
            raise
        except Exception:
            self._ledger.record_outcome(
                logical_run_id=self._logical_run_id,
                provider=self._provider,
                attempt_number=reservation.attempt_number,
                outcome="non_retryable",
            )
            raise
        self._ledger.record_outcome(
            logical_run_id=self._logical_run_id,
            provider=self._provider,
            attempt_number=reservation.attempt_number,
            outcome="success",
        )
        return response
