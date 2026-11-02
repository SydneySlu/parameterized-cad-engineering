"""Transparent parameter distance for the RET-002 baseline.

The score is intentionally simple and auditable:

    d(field)      = abs(query - candidate) / (catalog_max - catalog_min)
    continuous    = mean(d(bore_d), d(outer_d), d(screw_d), d(screw_len), d(width))
    discrete      = 0.5 * (second_screw differs ? 1 : 0)
    total         = continuous + discrete

No field is learned or weighted from data.  Normalization uses the full 15-row
GN 705 catalog range, so scores stay comparable when only a subset of rows is
eligible as a candidate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from .config import (
    CONTINUOUS_FIELDS,
    CONTINUOUS_FIELD_WEIGHT,
    DISCRETE_WEIGHT,
    POLICY_ID,
)
from .errors import RetrievalError


@dataclass(frozen=True)
class DistancePolicy:
    """Fixed-weight distance policy with explicit per-field details."""

    ranges: Mapping[str, tuple[float, float]]
    continuous_field_weight: float = CONTINUOUS_FIELD_WEIGHT
    discrete_weight: float = DISCRETE_WEIGHT

    def validate(self) -> None:
        if set(self.ranges) != set(CONTINUOUS_FIELDS):
            raise RetrievalError(
                "RETRIEVAL_CONFIG_INVALID",
                "distance policy must define exactly the five continuous catalog fields",
                stage="config",
                fields=tuple(sorted(set(self.ranges) ^ set(CONTINUOUS_FIELDS))),
                details={"expected": list(CONTINUOUS_FIELDS), "observed": sorted(self.ranges)},
            )
        for field in CONTINUOUS_FIELDS:
            low, high = self.ranges[field]
            if (
                isinstance(low, bool)
                or isinstance(high, bool)
                or not isinstance(low, (int, float))
                or not isinstance(high, (int, float))
                or not math.isfinite(float(low))
                or not math.isfinite(float(high))
                or not float(high) > float(low)
            ):
                raise RetrievalError(
                    "RETRIEVAL_CONFIG_INVALID",
                    "distance normalization range must be finite with min < max",
                    stage="config",
                    fields=(field,),
                    details={"min": repr(low), "max": repr(high)},
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
