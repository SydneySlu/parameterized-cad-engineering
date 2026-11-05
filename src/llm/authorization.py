"""Narrow-scope formal run authorization for APP-001 Phase 1.

This module provides the ONLY mechanism by which real (non-FakeTransport)
transports may be used.  The existing ``FORMAL_EVALUATION_ALLOWED = False``
constant in :mod:`src.llm.contract` is **unchanged** -- this authorization is
a separate, explicitly-constructed, scope-validated object that the runner
must obtain before any real network call.

The authorization is NOT a boolean flag, an environment variable, or a CLI
switch.  It is a frozen dataclass whose construction validates that the
requested scope exactly matches the frozen Phase 1 scope authorized by the
project owner on 2026-11-05.

Unauthorized construction or scope mismatch raises
:class:`AuthorizationScopeError`.  The global gate stays closed; this
authorization opens a narrow, auditable path for a specific batch only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Final

from .contract import (
    ACCEPTANCE_SET_VERSION,
    BACKOFF_SECONDS,
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    FAMILY_ID,
    MAX_ATTEMPTS_TOTAL,
    MAX_RETRIES_AFTER_INITIAL,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)


class AuthorizationScopeError(ValueError):
    """Raised when a formal run authorization scope does not match the frozen
    Phase 1 scope, or when the authorization is invalid."""


# ---------------------------------------------------------------------------
# Frozen Phase 1 scope (authorized by project owner 2026-11-05)
#
# These values are the single source of truth for what a formal Phase 1 run
# may do.  They are intentionally NOT configurable -- the project owner
# authorized exactly this scope, nothing more.
# ---------------------------------------------------------------------------

_FROZEN_PROTOCOL_VERSIONS: Final[frozenset[str]] = frozenset(
    {CONTRACT_VERSION, PROMPT_VERSION}
)
_FROZEN_SAMPLE_SET: Final[str] = ACCEPTANCE_SET_VERSION  # "acceptance-set-v0"
_FROZEN_CONDITIONS: Final[frozenset[str]] = frozenset({"C0", "C1"})
_FROZEN_PROVIDERS: Final[frozenset[str]] = frozenset(
    {DEEPSEEK_PROVIDER, OLLAMA_PROVIDER}
)
_FROZEN_MODELS: Final[frozenset[str]] = frozenset({DEEPSEEK_MODEL, OLLAMA_MODEL})
_FROZEN_MAX_LOGICAL_RUNS: Final[int] = 36
_FROZEN_MAX_ATTEMPTS_PER_RUN: Final[int] = MAX_ATTEMPTS_TOTAL  # 3
_FROZEN_MAX_BATCH_ATTEMPTS: Final[int] = 108
_FROZEN_MAX_PROVIDER_ATTEMPTS: Final[int] = 54


def _validate_scope(**kwargs: Any) -> list[str]:
    """Return a list of scope mismatch reasons (empty if scope matches)."""
    errors: list[str] = []
    if frozenset(kwargs["protocol_versions"]) != _FROZEN_PROTOCOL_VERSIONS:
        errors.append(
            f"protocol_versions mismatch: expected {sorted(_FROZEN_PROTOCOL_VERSIONS)}, "
            f"got {sorted(kwargs['protocol_versions'])}"
        )
    if kwargs["sample_set"] != _FROZEN_SAMPLE_SET:
        errors.append(
            f"sample_set mismatch: expected {_FROZEN_SAMPLE_SET!r}, "
            f"got {kwargs['sample_set']!r}"
        )
    if frozenset(kwargs["conditions"]) != _FROZEN_CONDITIONS:
        errors.append(
            f"conditions mismatch: expected {sorted(_FROZEN_CONDITIONS)}, "
            f"got {sorted(kwargs['conditions'])}"
        )
    if frozenset(kwargs["providers"]) != _FROZEN_PROVIDERS:
        errors.append(
            f"providers mismatch: expected {sorted(_FROZEN_PROVIDERS)}, "
            f"got {sorted(kwargs['providers'])}"
        )
    if frozenset(kwargs["models"]) != _FROZEN_MODELS:
        errors.append(
            f"models mismatch: expected {sorted(_FROZEN_MODELS)}, "
            f"got {sorted(kwargs['models'])}"
        )
    if kwargs["max_logical_runs"] != _FROZEN_MAX_LOGICAL_RUNS:
        errors.append(
            f"max_logical_runs mismatch: expected {_FROZEN_MAX_LOGICAL_RUNS}, "
            f"got {kwargs['max_logical_runs']}"
        )
    if kwargs["max_attempts_per_run"] != _FROZEN_MAX_ATTEMPTS_PER_RUN:
        errors.append(
            f"max_attempts_per_run mismatch: expected {_FROZEN_MAX_ATTEMPTS_PER_RUN}, "
            f"got {kwargs['max_attempts_per_run']}"
        )
    if kwargs["max_batch_attempts"] != _FROZEN_MAX_BATCH_ATTEMPTS:
        errors.append(
            f"max_batch_attempts mismatch: expected {_FROZEN_MAX_BATCH_ATTEMPTS}, "
            f"got {kwargs['max_batch_attempts']}"
        )
    if kwargs["max_provider_attempts"] != _FROZEN_MAX_PROVIDER_ATTEMPTS:
        errors.append(
            f"max_provider_attempts mismatch: expected {_FROZEN_MAX_PROVIDER_ATTEMPTS}, "
            f"got {kwargs['max_provider_attempts']}"
        )
    if kwargs["ir_cad_geometry_step_disabled"] is not True:
        errors.append("ir_cad_geometry_step_disabled must be True for Phase 1")
    if not kwargs.get("batch_id"):
        errors.append("batch_id must be a non-empty string")
    if not isinstance(kwargs.get("batch_id"), str):
        errors.append("batch_id must be a string")
    return errors


@dataclass(frozen=True)
class FormalRunAuthorization:
    """A scope-validated authorization for a formal APP-001 Phase 1 run.

    This object is the ONLY mechanism that allows real transports to run.
    It is not constructable from environment variables or boolean flags.
    The scope is validated at construction time and must exactly match the
    frozen Phase 1 scope.

    Construction is intentionally explicit -- every scope field must be
    provided and must match.  This prevents accidental activation through
    default parameters or partial configuration.

    The ``batch_id`` ties the authorization to a specific run batch
    directory under ``work/app001-runs/<batch-id>/``.  It is part of the
    scope -- a different batch_id requires a new authorization.
    """

    protocol_versions: frozenset[str]
    sample_set: str
    conditions: frozenset[str]
    providers: frozenset[str]
    models: frozenset[str]
    max_logical_runs: int
    max_attempts_per_run: int
    max_batch_attempts: int
    max_provider_attempts: int
    ir_cad_geometry_step_disabled: bool
    batch_id: str

    def __post_init__(self) -> None:
        errors = _validate_scope(
            protocol_versions=self.protocol_versions,
            sample_set=self.sample_set,
            conditions=self.conditions,
            providers=self.providers,
            models=self.models,
            max_logical_runs=self.max_logical_runs,
            max_attempts_per_run=self.max_attempts_per_run,
            max_batch_attempts=self.max_batch_attempts,
            max_provider_attempts=self.max_provider_attempts,
            ir_cad_geometry_step_disabled=self.ir_cad_geometry_step_disabled,
            batch_id=self.batch_id,
        )
        if errors:
            raise AuthorizationScopeError(
                "formal run authorization scope mismatch: " + "; ".join(errors)
            )

    # ------------------------------------------------------------------
    # Accessors used by the runner and adapter
    # ------------------------------------------------------------------

    @property
    def allowed_providers(self) -> frozenset[str]:
        return self.providers

    @property
    def allowed_models(self) -> frozenset[str]:
        return self.models

    @property
    def allowed_conditions(self) -> frozenset[str]:
        return self.conditions

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        """Check whether a (provider, model) pair is in the authorized scope."""
        return provider in self.providers and model in self.models

    def condition_is_allowed(self, condition: str) -> bool:
        return condition in self.conditions

    def scope_summary(self) -> dict[str, Any]:
        """Return a redacted, auditable summary of the authorization scope.

        Never includes API keys, Authorization values, or other secrets.
        """
        return {
            "protocol_versions": sorted(self.protocol_versions),
            "sample_set": self.sample_set,
            "conditions": sorted(self.conditions),
            "providers": sorted(self.providers),
            "models": sorted(self.models),
            "max_logical_runs": self.max_logical_runs,
            "max_attempts_per_run": self.max_attempts_per_run,
            "max_batch_attempts": self.max_batch_attempts,
            "max_provider_attempts": self.max_provider_attempts,
            "ir_cad_geometry_step_disabled": self.ir_cad_geometry_step_disabled,
            "batch_id": self.batch_id,
        }

    def scope_hash(self) -> str:
        """Stable SHA-256 of the authorization scope (for audit logs)."""
        raw = json.dumps(self.scope_summary(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _valid_kwargs(**overrides) -> dict:
    """Return a valid Phase 1 authorization kwargs dict, optionally overriding fields.

    Used in tests to construct authorizations with specific scope mismatches.
    """
    base = dict(
        protocol_versions=frozenset(_FROZEN_PROTOCOL_VERSIONS),
        sample_set=_FROZEN_SAMPLE_SET,
        conditions=frozenset(_FROZEN_CONDITIONS),
        providers=frozenset(_FROZEN_PROVIDERS),
        models=frozenset(_FROZEN_MODELS),
        max_logical_runs=_FROZEN_MAX_LOGICAL_RUNS,
        max_attempts_per_run=_FROZEN_MAX_ATTEMPTS_PER_RUN,
        max_batch_attempts=_FROZEN_MAX_BATCH_ATTEMPTS,
        max_provider_attempts=_FROZEN_MAX_PROVIDER_ATTEMPTS,
        ir_cad_geometry_step_disabled=True,
        batch_id="test-batch-001",
    )
    base.update(overrides)
    return base


def authorize_phase1_run(*, batch_id: str) -> FormalRunAuthorization:
    """Construct the canonical Phase 1 formal run authorization.

    This is the ONLY public factory for ``FormalRunAuthorization``.  It
    always uses the frozen Phase 1 scope; callers cannot customize it.
    The ``batch_id`` is the only variable part and ties the authorization
    to a specific batch directory.

    This function does NOT read environment variables, does NOT open the
    formal evaluation gate, and does NOT instantiate any transport.  It
    only constructs a scope-validated authorization object.
    """
    return FormalRunAuthorization(
        protocol_versions=_FROZEN_PROTOCOL_VERSIONS,
        sample_set=_FROZEN_SAMPLE_SET,
        conditions=_FROZEN_CONDITIONS,
        providers=_FROZEN_PROVIDERS,
        models=_FROZEN_MODELS,
        max_logical_runs=_FROZEN_MAX_LOGICAL_RUNS,
        max_attempts_per_run=_FROZEN_MAX_ATTEMPTS_PER_RUN,
        max_batch_attempts=_FROZEN_MAX_BATCH_ATTEMPTS,
        max_provider_attempts=_FROZEN_MAX_PROVIDER_ATTEMPTS,
        ir_cad_geometry_step_disabled=True,
        batch_id=batch_id,
    )
