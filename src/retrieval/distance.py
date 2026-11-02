"""Transparent parameter distance for the RET-002 baseline.

The score is intentionally simple and auditable:

    d(field)      = abs(query - candidate) / (catalog_max - catalog_min)
    continuous    = mean(d(bore_d), d(outer_d), d(screw_d), d(screw_len), d(width))
    discrete      = 0.5 * (second_screw differs ? 1 : 0)
    total         = continuous + discrete

No field is learned or weighted from data.  Normalization uses the full 15-row
GN 705 catalog range, so scores stay comparable when only a subset of rows is
eligible as a candidate.

The ranges and weights are part of the frozen `RET-002.parametric_distance.v1`
contract.  `validate()` requires every continuous field to match
`catalog_ranges()` exactly and refuses any custom range; changing the policy
requires a new policy id reviewed by the Codex hub, not a local override.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .config import (
    CONTINUOUS_FIELDS,
    CONTINUOUS_FIELD_WEIGHT,
    DISCRETE_WEIGHT,
    POLICY_ID,
    catalog_ranges,
)
from .errors import RetrievalError


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError):
        return False
    return math.isfinite(numeric)


@dataclass(frozen=True)
class DistancePolicy:
    """Fixed-weight distance policy with explicit per-field details."""

    ranges: Mapping[str, tuple[float, float]]
    continuous_field_weight: float = CONTINUOUS_FIELD_WEIGHT
    discrete_weight: float = DISCRETE_WEIGHT

    def __post_init__(self) -> None:
        # Freeze a copy so mutating the caller's mapping (or a mutable list used
        # as a range pair) after validation cannot change the distance semantics
        # while the policy id stays v1.
        try:
            raw = dict(self.ranges)
        except (TypeError, ValueError):
            frozen: Any = self.ranges
        else:
            normalized: dict[Any, Any] = {}
            for key, value in raw.items():
                try:
                    low, high = value
                except (TypeError, ValueError):
                    normalized[key] = value
                else:
                    normalized[key] = (low, high)
            frozen = MappingProxyType(normalized)
        object.__setattr__(self, "ranges", frozen)

    def validate(self) -> None:
        try:
            observed_fields = set(self.ranges)
        except TypeError as exc:
            raise RetrievalError(
                "RETRIEVAL_CONFIG_INVALID",
                "distance policy ranges must be a mapping of field -> (min, max)",
                stage="config",
                details={"type": type(self.ranges).__name__},
            ) from exc
        if observed_fields != set(CONTINUOUS_FIELDS):
            raise RetrievalError(
                "RETRIEVAL_CONFIG_INVALID",
                "distance policy must define exactly the five continuous catalog fields",
                stage="config",
                fields=tuple(sorted(observed_fields ^ set(CONTINUOUS_FIELDS))),
                details={"expected": list(CONTINUOUS_FIELDS), "observed": sorted(observed_fields)},
            )
        expected_ranges = catalog_ranges()
        for field in CONTINUOUS_FIELDS:
            try:
                low, high = self.ranges[field]
            except (KeyError, TypeError, ValueError) as exc:
                raise RetrievalError(
                    "RETRIEVAL_CONFIG_INVALID",
                    "distance normalization range must be a (min, max) pair",
                    stage="config",
                    fields=(field,),
                    details={"field": field, "reason": type(exc).__name__},
                ) from exc
            if (
                not _is_finite_number(low)
                or not _is_finite_number(high)
                or not float(high) > float(low)
            ):
                raise RetrievalError(
                    "RETRIEVAL_CONFIG_INVALID",
                    "distance normalization range must be finite numbers with min < max",
                    stage="config",
                    fields=(field,),
                    details={"field": field, "min": repr(low), "max": repr(high)},
                )
            expected_low, expected_high = expected_ranges[field]
            if float(low) != expected_low or float(high) != expected_high:
                raise RetrievalError(
                    "RETRIEVAL_CONFIG_INVALID",
                    "normalization range differs from the frozen 15-row catalog range; "
                    "changing ranges or weights requires a new policy id and Codex review",
                    stage="config",
                    fields=(field,),
                    details={
                        "field": field,
                        "policy_id": POLICY_ID,
                        "expected": [expected_low, expected_high],
                        "observed": [low, high],
                    },
                )
        if self.continuous_field_weight != CONTINUOUS_FIELD_WEIGHT:
            raise RetrievalError(
                "RETRIEVAL_CONFIG_INVALID",
                "continuous field weight differs from the frozen policy",
                stage="config",
                details={"expected": CONTINUOUS_FIELD_WEIGHT, "observed": self.continuous_field_weight},
            )
        if self.discrete_weight != DISCRETE_WEIGHT:
            raise RetrievalError(
                "RETRIEVAL_CONFIG_INVALID",
                "second_screw discrete weight differs from the frozen policy",
                stage="config",
                details={"expected": DISCRETE_WEIGHT, "observed": self.discrete_weight},
            )

    def score(self, query: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Score one candidate and return the full field-level breakdown."""

        fields: dict[str, dict[str, Any]] = {}
        diffs: list[float] = []
        for field in CONTINUOUS_FIELDS:
            low, high = self.ranges[field]
            query_value = query[field]
            candidate_value = candidate[field]
            diff = abs(float(query_value) - float(candidate_value)) / (float(high) - float(low))
            diffs.append(diff)
            fields[field] = {
                "query": query_value,
                "candidate": candidate_value,
                "catalog_range_mm": [float(low), float(high)],
                "normalized_abs_diff": diff,
                "weight": self.continuous_field_weight,
                "contribution": diff * self.continuous_field_weight,
            }
        continuous_mean = math.fsum(diffs) / len(CONTINUOUS_FIELDS)
        mismatch = 1.0 if int(query["second_screw"]) != int(candidate["second_screw"]) else 0.0
        discrete_term = mismatch * self.discrete_weight
        return {
            "policy_id": POLICY_ID,
            "total": continuous_mean + discrete_term,
            "continuous_mean": continuous_mean,
            "discrete_term": discrete_term,
            "second_screw": {
                "query": query["second_screw"],
                "candidate": candidate["second_screw"],
                "match": mismatch == 0.0,
                "weight": self.discrete_weight,
                "contribution": discrete_term,
            },
            "fields": fields,
        }
