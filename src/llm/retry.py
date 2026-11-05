"""Transient-fault retry loop with an injectable clock and sleeper.

Retries only for connection/read timeout, connection interruption, HTTP 429
and HTTP 5xx, with fixed 1s/2s backoff (max 2 retries after the initial
attempt).  Authentication/permission, malformed request, context overflow,
invalid JSON, contract/schema/rule and CAD failures are never retried.

The clock and sleeper are injected so tests never call ``time.sleep``.

3.4 fix: ``send_with_retry`` returns a third value, ``total_elapsed_ms``, which
is measured from before the first attempt to after the final outcome,
*including* all backoff waits.  This is distinct from the sum of per-attempt
request durations and gives the correct per-sample wall-clock time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .contract import BACKOFF_SECONDS, MAX_ATTEMPTS_TOTAL
from .transport import PreparedRequest, Transport, TransportError, TransportResponse


# Clock and sleeper type aliases.
Clock = Callable[[], float]
Sleeper = Callable[[float], None]


def _real_clock() -> float:
    return time.monotonic()


def _real_sleeper(seconds: float) -> None:
    time.sleep(seconds)


@dataclass(frozen=True)
class AttemptOutcome:
    """The outcome of one attempt, recorded for the run record."""

    attempt_number: int
    started_at: float
    elapsed_ms: float  # duration of this transport.send() call only
    outcome: str  # "success" | "transient_retryable" | "non_retryable" | "exhausted"
    http_status: int | None
    error_condition: str | None
    error_stage: str | None
    error_fields: tuple[str, ...]


def send_with_retry(
    transport: Transport,
    request: PreparedRequest,
    *,
    clock: Clock = _real_clock,
    sleeper: Sleeper = _real_sleeper,
) -> tuple[TransportResponse | None, list[AttemptOutcome], float]:
    """Send ``request`` via ``transport`` with the frozen retry policy.

    Returns a 3-tuple:
    - ``response``: the final :class:`TransportResponse`, or ``None`` on failure.
    - ``outcomes``: per-attempt outcome records (request durations only).
    - ``total_elapsed_ms``: wall-clock time from before the first attempt to
      after the final outcome, **including all backoff waits**.  This is what
      ``RunRecord.total_elapsed_ms`` and ``local_wall_time_ms`` must use.
    """
    outcomes: list[AttemptOutcome] = []
    backoff = list(BACKOFF_SECONDS)

    # Start the overall wall-clock before the first attempt.
    overall_start = clock()

    for attempt in range(1, MAX_ATTEMPTS_TOTAL + 1):
        started = clock()
        http_status: int | None = None
        error_condition: str | None = None
        try:
            response = transport.send(request)
            elapsed_ms = (clock() - started) * 1000.0
            outcomes.append(
                AttemptOutcome(
                    attempt_number=attempt,
                    started_at=started,
                    elapsed_ms=elapsed_ms,
                    outcome="success",
                    http_status=response.status,
                    error_condition=None,
                    error_stage=None,
                    error_fields=(),
                )
            )
            total_elapsed_ms = (clock() - overall_start) * 1000.0
            return response, outcomes, total_elapsed_ms
        except TransportError as exc:
            elapsed_ms = (clock() - started) * 1000.0
            http_status = exc.http_status
            error_condition = exc.condition
            retryable = exc.is_retryable()
            if not retryable:
                outcomes.append(
                    AttemptOutcome(
                        attempt_number=attempt,
                        started_at=started,
                        elapsed_ms=elapsed_ms,
                        outcome="non_retryable",
                        http_status=http_status,
                        error_condition=error_condition,
                        error_stage="transport",
                        error_fields=(error_condition or "unknown",),
                    )
                )
                total_elapsed_ms = (clock() - overall_start) * 1000.0
                return None, outcomes, total_elapsed_ms
            # Retryable: record and maybe back off.
            if attempt < MAX_ATTEMPTS_TOTAL:
                outcomes.append(
                    AttemptOutcome(
                        attempt_number=attempt,
                        started_at=started,
                        elapsed_ms=elapsed_ms,
                        outcome="transient_retryable",
                        http_status=http_status,
                        error_condition=error_condition,
                        error_stage="transport",
                        error_fields=(error_condition,),
                    )
                )
                sleep_for = backoff[attempt - 1] if attempt - 1 < len(backoff) else backoff[-1]
                sleeper(sleep_for)
                # (wall clock continues ticking during sleep via the injected clock)
            else:
                outcomes.append(
                    AttemptOutcome(
                        attempt_number=attempt,
                        started_at=started,
                        elapsed_ms=elapsed_ms,
                        outcome="exhausted",
                        http_status=http_status,
                        error_condition=error_condition,
                        error_stage="transport",
                        error_fields=(error_condition,),
                    )
                )
                total_elapsed_ms = (clock() - overall_start) * 1000.0
                return None, outcomes, total_elapsed_ms
        except Exception as exc:  # pragma: no cover - defensive
            elapsed_ms = (clock() - started) * 1000.0
            outcomes.append(
                AttemptOutcome(
                    attempt_number=attempt,
                    started_at=started,
                    elapsed_ms=elapsed_ms,
                    outcome="non_retryable",
                    http_status=None,
                    error_condition="other_non_retryable",
                    error_stage="transport",
                    error_fields=("other_non_retryable",),
                )
            )
            total_elapsed_ms = (clock() - overall_start) * 1000.0
            return None, outcomes, total_elapsed_ms

    total_elapsed_ms = (clock() - overall_start) * 1000.0
    return None, outcomes, total_elapsed_ms
