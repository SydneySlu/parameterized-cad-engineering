"""Fail-closed authorization profile for APP-002-INTEGRATION-A2 real-model integration.

This profile is completely separate from APP-001 Phase 1 authorization
(authorize_phase1_run) and ADR-0019 held-out authorization
(authorize_heldout_v5_run).  It binds a unique batch to:

- Frozen v5 prompt / contract (app001-io.v1 / app001-extraction.v5)
- 3 natural-language input requests: A2-24mm, A2-80mm, A2-ask-bore
- DeepSeek deepseek-flash only, C0 only (Ollama excluded from minimal scope)
- Max 9 HTTP requests (3 runs × 3 chat attempts max)
- Explicit field (``enable_cad_pipeline=True``) authorising the A2 runner to
  call ``run_pipeline()`` after a successful LLM response

Constructing this object does NOT perform network I/O, read secrets, open
the formal evaluation gate, or create a batch directory.

The formal gate (``FORMAL_EVALUATION_ALLOWED=False``) is unchanged.
A batch_id is not assigned here; the project owner must supply it when
approving the execution authorisation template.

Relationship to existing authorization classes
----------------------------------------------
- ``FormalRunAuthorization`` (Phase 1, ADR-0014): 36-run Schema-only scope,
  both providers, ``ir_cad_geometry_step_disabled=True``.  A2 is independent.
- ``HeldoutRunAuthorization`` (ADR-0019): 12-run held-out retrieval study,
  both providers, IR/CAD/STEP disabled.  A2 is independent.
- ``A2IntegrationAuthorization`` (this module): 3-run CAD integration smoke,
  DeepSeek only, ``enable_cad_pipeline=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .authorization import AuthorizationScopeError, FormalRunAuthorization
from .contract import (
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    PROMPT_VERSION,
)

# ---------------------------------------------------------------------------
# Frozen A2 scope constants
# ---------------------------------------------------------------------------

A2_PROFILE_ID: Final[str] = "app002-integration-a2.v1"
A2_SAMPLE_SET: Final[str] = "a2-integration-smoke.v1"

# Three representative inputs: standard legal bore, second-screw boundary,
# and missing bore_d (ask path).  These IDs must match model-inputs.json.
A2_INPUT_IDS: Final[tuple[str, ...]] = ("A2-24mm", "A2-80mm", "A2-ask-bore")

# SHA-256 of agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json
# (computed 2026-11-11, frozen at creation).
A2_INPUTS_SHA256: Final[str] = (
    "d290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b"
)

# SHA-256 of evaluator-labels.json (not passed to model).
A2_LABELS_SHA256: Final[str] = (
    "67fe1e68ed27fbaef420846ac2f7eb92abb402b49134a058f676a4bdb965d6e7"
)

# Only DeepSeek deepseek-flash; Ollama excluded from minimal A2 scope.
A2_PROVIDER: Final[str] = DEEPSEEK_PROVIDER
A2_MODEL: Final[str] = DEEPSEEK_MODEL

# Only C0 (no retrieval context) for the minimal smoke test.
A2_CONDITION: Final[str] = "C0"

# Budget: 3 inputs × 1 provider × 1 condition × max 3 attempts = 9 HTTP max.
A2_MAX_LOGICAL_RUNS: Final[int] = 3
A2_MAX_CHAT_ATTEMPTS_PER_RUN: Final[int] = 3
A2_MAX_BATCH_HTTP: Final[int] = 9  # = A2_MAX_LOGICAL_RUNS × A2_MAX_CHAT_ATTEMPTS_PER_RUN

# Provider HTTP cap (DeepSeek only; equals global cap for single-provider scope).
A2_PROVIDER_HTTP_CAPS: Final[dict[str, int]] = {DEEPSEEK_PROVIDER: 9}

# Batch preflight ID used in the budget ledger for pre-run identity checks.
A2_BATCH_PREFLIGHT_ID: Final[str] = "__a2_batch_preflight__"


# ---------------------------------------------------------------------------
# Authorization class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2IntegrationAuthorization(FormalRunAuthorization):
    """Fail-closed authorization for the A2 real-model CAD integration smoke.

    Extends ``FormalRunAuthorization`` so that the existing ``Adapter.run()``
    gate check (``isinstance(formal_authorization, FormalRunAuthorization)``)
    passes without modification.

    Additional fields beyond the base class:
    - ``profile_id``: must equal ``A2_PROFILE_ID``
    - ``input_ids``: must equal ``A2_INPUT_IDS``
    - ``inputs_sha256``: must equal ``A2_INPUTS_SHA256``
    - ``evaluator_labels_sha256``: must equal ``A2_LABELS_SHA256``
    - ``enable_cad_pipeline``: must be True — explicit authorisation for the
      A2 runner to call ``run_pipeline()`` after a successful LLM response.

    ``ir_cad_geometry_step_disabled`` is set to True (as required by the base
    class field default).  The Adapter's own staged record still marks IR/CAD
    as "blocked"; the pipeline call is a *separate* step authorised exclusively
    by ``enable_cad_pipeline=True`` in this object.
    """

    profile_id: str
    input_ids: tuple[str, ...]
    inputs_sha256: str
    evaluator_labels_sha256: str
    enable_cad_pipeline: bool

    def __post_init__(self) -> None:  # type: ignore[override]
        """Full A2 scope validation; replaces base class ``_validate_scope``."""
        mismatches: list[str] = []

        # Protocol versions
        expected_protos = frozenset({CONTRACT_VERSION, PROMPT_VERSION})
        if self.protocol_versions != expected_protos:
            mismatches.append(
                f"protocol_versions mismatch: expected {sorted(expected_protos)}, "
                f"got {sorted(self.protocol_versions)}"
            )

        # Sample set
        if self.sample_set != A2_SAMPLE_SET:
            mismatches.append(
                f"sample_set mismatch: expected {A2_SAMPLE_SET!r}, "
                f"got {self.sample_set!r}"
            )

        # Conditions
        if self.conditions != frozenset({A2_CONDITION}):
            mismatches.append(
                f"conditions mismatch: expected {{'{A2_CONDITION}'}}, "
                f"got {sorted(self.conditions)}"
            )

        # Provider / model: DeepSeek only
        if self.providers != frozenset({A2_PROVIDER}):
            mismatches.append(
                f"providers mismatch: expected {{'{A2_PROVIDER}'}}, "
                f"got {sorted(self.providers)}"
            )
        if self.models != frozenset({A2_MODEL}):
            mismatches.append(
                f"models mismatch: expected {{'{A2_MODEL}'}}, "
                f"got {sorted(self.models)}"
            )

        # Budget
        if self.max_logical_runs != A2_MAX_LOGICAL_RUNS:
            mismatches.append(
                f"max_logical_runs mismatch: expected {A2_MAX_LOGICAL_RUNS}, "
                f"got {self.max_logical_runs}"
            )
        if self.max_attempts_per_run != A2_MAX_CHAT_ATTEMPTS_PER_RUN:
            mismatches.append(
                f"max_attempts_per_run mismatch: expected "
                f"{A2_MAX_CHAT_ATTEMPTS_PER_RUN}, got {self.max_attempts_per_run}"
            )
        if self.max_batch_attempts != A2_MAX_BATCH_HTTP:
            mismatches.append(
                f"max_batch_attempts mismatch: expected {A2_MAX_BATCH_HTTP}, "
                f"got {self.max_batch_attempts}"
            )
        if self.max_provider_attempts != A2_PROVIDER_HTTP_CAPS[A2_PROVIDER]:
            mismatches.append(
                f"max_provider_attempts mismatch: expected "
                f"{A2_PROVIDER_HTTP_CAPS[A2_PROVIDER]}, got {self.max_provider_attempts}"
            )

        # ir_cad_geometry_step_disabled must be True (Adapter stages stay blocked)
        if self.ir_cad_geometry_step_disabled is not True:
            mismatches.append("ir_cad_geometry_step_disabled must be True for A2")

        # Profile identity
        if self.profile_id != A2_PROFILE_ID:
            mismatches.append(
                f"profile_id mismatch: expected {A2_PROFILE_ID!r}, "
                f"got {self.profile_id!r}"
            )
        if self.input_ids != A2_INPUT_IDS:
            mismatches.append(
                f"input_ids mismatch: expected {A2_INPUT_IDS!r}, "
                f"got {self.input_ids!r}"
            )
        if self.inputs_sha256 != A2_INPUTS_SHA256:
            mismatches.append(
                f"inputs_sha256 mismatch: expected {A2_INPUTS_SHA256!r}, "
                f"got {self.inputs_sha256!r}"
            )
        if self.evaluator_labels_sha256 != A2_LABELS_SHA256:
            mismatches.append(
                f"evaluator_labels_sha256 mismatch: expected {A2_LABELS_SHA256!r}, "
                f"got {self.evaluator_labels_sha256!r}"
            )

        # Pipeline flag: must be explicitly True
        if self.enable_cad_pipeline is not True:
            mismatches.append(
                "enable_cad_pipeline must be True; "
                "A2 runner requires explicit CAD pipeline authorisation"
            )

        # batch_id must be non-empty
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")

        if mismatches:
            raise AuthorizationScopeError(
                "A2 integration authorization scope mismatch: "
                + "; ".join(mismatches)
            )

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        """A2 authorises exactly one (provider, model) pair."""
        return (provider, model) == (A2_PROVIDER, A2_MODEL)

    def max_provider_attempts_for(self, provider: str) -> int:
        """Return the per-provider HTTP cap; raises for unauthorised providers."""
        try:
            return A2_PROVIDER_HTTP_CAPS[provider]
        except KeyError as exc:
            raise AuthorizationScopeError(
                f"provider {provider!r} is not authorised for A2 scope"
            ) from exc

    def max_chat_attempts_for(self, provider: str) -> int:
        """Chat cap equals the provider HTTP cap (no identity requests in A2)."""
        return self.max_provider_attempts_for(provider)

    def allows_logical_run(self, logical_run_id: str, provider: str) -> bool:
        """Check whether a logical_run_id belongs to the authorised A2 scope."""
        return any(
            logical_run_id == self.expected_logical_run_id(input_id, A2_CONDITION, provider)
            for input_id in self.input_ids
        )

    def expected_logical_run_id(
        self, input_id: str, condition: str, provider: str
    ) -> str:
        """Canonical deterministic logical run ID for one (input, condition, provider)."""
        if input_id not in self.input_ids:
            raise AuthorizationScopeError(
                f"input_id {input_id!r} is outside A2 scope"
            )
        if condition != A2_CONDITION:
            raise AuthorizationScopeError(
                f"condition {condition!r} is outside A2 scope (only {A2_CONDITION!r})"
            )
        if provider != A2_PROVIDER:
            raise AuthorizationScopeError(
                f"provider {provider!r} is outside A2 scope (only {A2_PROVIDER!r})"
            )
        return f"{input_id}__{condition}__{provider}__{A2_MODEL}"

    def scope_summary(self) -> dict:
        summary = {
            "profile_id": self.profile_id,
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
            "input_ids": list(self.input_ids),
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "enable_cad_pipeline": self.enable_cad_pipeline,
            "provider_http_caps": dict(sorted(A2_PROVIDER_HTTP_CAPS.items())),
        }
        return summary


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def authorize_a2_run(*, batch_id: str) -> A2IntegrationAuthorization:
    """Construct the fixed A2 integration authorization for a caller-supplied batch ID.

    ``batch_id`` is the only variable part.  It ties the authorization to a
    specific batch directory under ``work/app001-runs/<batch_id>/`` and must be
    unique across all batches (use a date-stamped name such as
    ``app002-a2-smoke-20261111-01``).

    This function does NOT read environment variables, does NOT open the
    formal evaluation gate, does NOT instantiate any transport, and does NOT
    create any directory or file.
    """
    return A2IntegrationAuthorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=A2_SAMPLE_SET,
        conditions=frozenset({A2_CONDITION}),
        providers=frozenset({A2_PROVIDER}),
        models=frozenset({A2_MODEL}),
        max_logical_runs=A2_MAX_LOGICAL_RUNS,
        max_attempts_per_run=A2_MAX_CHAT_ATTEMPTS_PER_RUN,
        max_batch_attempts=A2_MAX_BATCH_HTTP,
        max_provider_attempts=A2_PROVIDER_HTTP_CAPS[A2_PROVIDER],
        ir_cad_geometry_step_disabled=True,
        batch_id=batch_id,
        profile_id=A2_PROFILE_ID,
        input_ids=A2_INPUT_IDS,
        inputs_sha256=A2_INPUTS_SHA256,
        evaluator_labels_sha256=A2_LABELS_SHA256,
        enable_cad_pipeline=True,
    )
