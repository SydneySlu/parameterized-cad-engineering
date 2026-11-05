"""Deterministic 36-combination generator for APP-001 Phase 1.

Generates the 36 logical run combinations: 9 frozen acceptance samples ×
2 conditions (C0, C1) × 2 models (DeepSeek, Ollama).

Each combination gets a stable logical run ID of the form::

    <query_id>__<condition>__<provider>__<model>

For example::

    APP001-A01-complete-description__C0__DeepSeek__deepseek-flash

The generator is deterministic: the same acceptance set always produces the
same 36 combinations in the same order.  The combination list has a stable
SHA-256 hash that the dry-run can output for audit.

In dry-run mode, the generator outputs ONLY the combination list, counts,
and hash.  It does NOT output evaluator labels, expected values, natural
language inputs (beyond the query IDs), or any other case content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final

from .authorization import FormalRunAuthorization
from .contract import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
)
from .input_projection import AcceptanceSetProjection
from .input_projection import AcceptanceSetProjection

# Phase 1 conditions
CONDITION_C0: Final[str] = "C0"  # no retrieval
CONDITION_C1: Final[str] = "C1"  # RET-002 parametric retrieval

PHASE1_CONDITIONS: Final[tuple[str, ...]] = (CONDITION_C0, CONDITION_C1)

# Provider → model mapping (frozen)
_PROVIDER_MODELS: Final[dict[str, str]] = {
    DEEPSEEK_PROVIDER: DEEPSEEK_MODEL,
    OLLAMA_PROVIDER: OLLAMA_MODEL,
}


class CombinationError(ValueError):
    """Raised when the combination generator detects a scope violation."""


@dataclass(frozen=True)
class LogicalRunCombination:
    """One of the 36 Phase 1 logical run combinations.

    Contains only the stable identifiers needed to plan and audit a run.
    No evaluator labels, natural language inputs, or expected values.
    """

    logical_run_id: str
    query_id: str
    condition_id: str
    provider: str
    model: str
    # Index within the 36-combination list (0-based)
    index: int

    def as_audit_dict(self) -> dict[str, Any]:
        """Return a dict suitable for dry-run audit output (no case content)."""
        return {
            "logical_run_id": self.logical_run_id,
            "query_id": self.query_id,
            "condition_id": self.condition_id,
            "provider": self.provider,
            "model": self.model,
            "index": self.index,
        }


@dataclass(frozen=True)
class CombinationPlan:
    """The full 36-combination plan with audit metadata."""

    combinations: tuple[LogicalRunCombination, ...]
    count: int
    plan_sha256: str
    query_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    providers: tuple[str, ...]
    models: tuple[str, ...]

    def as_audit_dict(self) -> dict[str, Any]:
        """Return a dict for dry-run output.  Contains no case content,
        no evaluator labels, no natural language inputs."""
        return {
            "count": self.count,
            "query_ids": list(self.query_ids),
            "conditions": list(self.conditions),
            "providers": list(self.providers),
            "models": list(self.models),
            "plan_sha256": self.plan_sha256,
            "combinations": [c.as_audit_dict() for c in self.combinations],
        }


def _make_logical_run_id(
    query_id: str, condition_id: str, provider: str, model: str
) -> str:
    """Build a stable, filesystem-safe logical run ID."""
    return f"{query_id}__{condition_id}__{provider}__{model}"


def generate_combinations(
    projection: AcceptanceSetProjection,
    authorization: FormalRunAuthorization,
) -> CombinationPlan:
    """Generate the 36 Phase 1 logical run combinations.

    Validates that the projection and authorization are consistent:
    - The projection has exactly 9 cases.
    - The authorization allows C0 and C1.
    - The authorization allows both providers and models.

    The order is deterministic: for each of the 9 query IDs (in acceptance
    set order), for each of the 2 conditions (C0, C1), for each of the 2
    providers (DeepSeek, Ollama).

    Raises :class:`CombinationError` on scope mismatch.
    """
    if projection.sample_count != 9:
        raise CombinationError(
            f"expected 9 acceptance cases, got {projection.sample_count}"
        )
    if not authorization.condition_is_allowed(CONDITION_C0):
        raise CombinationError("authorization does not allow C0")
    if not authorization.condition_is_allowed(CONDITION_C1):
        raise CombinationError("authorization does not allow C1")
    for provider, model in _PROVIDER_MODELS.items():
        if not authorization.provider_model_is_allowed(provider, model):
            raise CombinationError(
                f"authorization does not allow {provider}/{model}"
            )
    query_ids = projection.case_ids()
    if len(query_ids) != len(set(query_ids)):
        raise CombinationError("duplicate query IDs in acceptance set")
    combinations: list[LogicalRunCombination] = []
    idx = 0
    for query_id in query_ids:
        for condition_id in PHASE1_CONDITIONS:
            for provider in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
                model = _PROVIDER_MODELS[provider]
                lrid = _make_logical_run_id(query_id, condition_id, provider, model)
                combinations.append(
                    LogicalRunCombination(
                        logical_run_id=lrid,
                        query_id=query_id,
                        condition_id=condition_id,
                        provider=provider,
                        model=model,
                        index=idx,
                    )
                )
                idx += 1
    plan = CombinationPlan(
        combinations=tuple(combinations),
        count=len(combinations),
        plan_sha256="",
        query_ids=query_ids,
        conditions=PHASE1_CONDITIONS,
        providers=(DEEPSEEK_PROVIDER, OLLAMA_PROVIDER),
        models=(DEEPSEEK_MODEL, OLLAMA_MODEL),
    )
    # Compute stable hash of the plan
    audit = plan.as_audit_dict()
    raw = json.dumps(audit, ensure_ascii=False, sort_keys=True).encode("utf-8")
    plan_sha = hashlib.sha256(raw).hexdigest()
    # Reconstruct with hash (dataclass is frozen, use object.__setattr__)
    object.__setattr__(plan, "plan_sha256", plan_sha)
    return plan


def dry_run_combinations(
    projection: AcceptanceSetProjection,
    authorization: FormalRunAuthorization,
) -> dict[str, Any]:
    """Generate the 36-combination plan and return ONLY the audit dict.

    This is the dry-run entry point.  It outputs the combination list,
    counts, and plan hash.  It does NOT output natural language inputs,
    evaluator labels, expected values, or any other case content.

    No network calls are made; no transports are instantiated.
    """
    plan = generate_combinations(projection, authorization)
    return plan.as_audit_dict()
