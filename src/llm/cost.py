"""Cloud cost calculation from actual usage and the dated DeepSeek rate card.

Cost is computed only from the response's actual usage fields and the rate-card
period applicable to the request timestamp.  When any required input is
missing, the result is ``not_available`` -- we never estimate.

Local Ollama runs never carry cloud token/cost fields; the adapter marks those
``not_applicable``.
"""

from __future__ import annotations

from typing import Any

from .contract import (
    RATE_CARD_CURRENCY,
    RATE_CARD_OFF_PEAK,
    RATE_CARD_OBSERVED_DATE,
    RATE_CARD_PEAK,
    RATE_CARD_SOURCE,
    RATE_CARD_UNIT,
)


# Beijing time peak windows (Monday-Friday, excluding China public holidays):
#   09:00-12:00, 14:00-18:00.
# This helper uses the request timestamp's offset to determine the period.
# We do not maintain a public-holiday calendar here; if a request falls on a
# public holiday it is treated as off-peak.  Callers may override the period
# decision by passing ``force_period``.
_PEAK_HOUR_RANGES = ((9, 12), (14, 18))


def classify_rate_period(request_timestamp_utc: str, *, force_period: str | None = None) -> str:
    """Return ``"peak"`` or ``"off_peak"`` for the given request time.

    The timestamp is interpreted in Beijing time (UTC+8).  Weekends (Saturday,
    Sunday in Beijing time) are always off-peak.  ``force_period`` overrides
    the calculation for tests.
    """
    if force_period is not None:
        if force_period not in ("peak", "off_peak"):
            raise ValueError(f"force_period must be 'peak' or 'off_peak', got {force_period!r}")
        return force_period
    # Parse the ISO-8601 UTC timestamp and convert to Beijing time components.
    from datetime import datetime, timedelta, timezone

    dt = datetime.fromisoformat(request_timestamp_utc.replace("Z", "+00:00"))
    beijing = dt.astimezone(timezone(timedelta(hours=8)))
    if beijing.weekday() >= 5:  # Saturday/Sunday
        return "off_peak"
    hour = beijing.hour
    for start, end in _PEAK_HOUR_RANGES:
        if start <= hour < end:
            return "peak"
    return "off_peak"


def compute_cloud_cost(
    *,
    request_timestamp_utc: str,
    prompt_tokens: int | None,
    cached_input_tokens: int | None,
    cache_miss_input_tokens: int | None,
    output_tokens: int | None,
    force_period: str | None = None,
) -> dict[str, Any]:
    """Compute the DeepSeek cloud cost from actual usage and the rate card.

    Returns a dict with ``cost_amount``, ``cost_currency``, ``cost_source``,
    ``rate_card_observed_date``, and ``rate_period``.  When any required usage
    field is missing, ``cost_amount`` is ``None`` and a ``not_available`` flag is
    set; we never estimate.

    The cost formula uses cache-hit/cache-miss split for input tokens:
    ``cost = (cache_hit * hit_rate + cache_miss * miss_rate + output * out_rate) / 1e6``.
    """
    period = classify_rate_period(request_timestamp_utc, force_period=force_period)
    rate = RATE_CARD_PEAK if period == "peak" else RATE_CARD_OFF_PEAK

    missing = []
    if prompt_tokens is None:
        missing.append("prompt_tokens")
    if output_tokens is None:
        missing.append("output_tokens")

    # We need either the cache split or a single prompt_tokens figure to split.
    # DeepSeek responses provide both cache_hit and cache_miss; use those.
    cache_hit = cached_input_tokens
    cache_miss = cache_miss_input_tokens
    if cache_hit is None and cache_miss is None and prompt_tokens is not None:
        # Fall back: treat all prompt_tokens as cache miss (conservative).
        cache_hit = 0
        cache_miss = prompt_tokens
    elif cache_hit is None or cache_miss is None:
        missing.append("cache_hit/miss")

    if missing or cache_hit is None or cache_miss is None or output_tokens is None:
        return {
            "cost_amount": None,
            "not_available": True,
            "not_available_reason": f"missing usage field(s): {missing}",
            "cost_currency": RATE_CARD_CURRENCY,
            "cost_source": RATE_CARD_SOURCE,
            "rate_card_observed_date": RATE_CARD_OBSERVED_DATE,
            "rate_card_unit": RATE_CARD_UNIT,
            "rate_period": period,
        }

    cost_cny = (
        cache_hit * rate["input_cache_hit"]
        + cache_miss * rate["input_cache_miss"]
        + output_tokens * rate["output"]
    ) / 1_000_000.0

    return {
        "cost_amount": round(cost_cny, 8),
        "not_available": False,
        "cost_currency": RATE_CARD_CURRENCY,
        "cost_source": RATE_CARD_SOURCE,
        "rate_card_observed_date": RATE_CARD_OBSERVED_DATE,
        "rate_card_unit": RATE_CARD_UNIT,
        "rate_period": period,
        "rate_used": dict(rate),
    }
