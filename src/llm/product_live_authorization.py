"""Fail-closed authorization profile for APP-003 product live extraction.

This profile is completely separate from:
- APP-001 Phase 1 authorization (authorize_phase1_run)
- ADR-0019 held-out authorization (authorize_heldout_v5_run)
- A2 integration authorization (authorize_a2_run)

It binds a unique batch to:
- Frozen v5 prompt / contract (app001-io.v1 / app001-extraction.v5)
- 4 natural-language input requests: P1-24mm, P2-ask-bore, P3-catalog-conflict, P4-unsupported
- DeepSeek deepseek-flash only, C0 only (no retrieval context)
- Max 12 HTTP requests (4 runs × 3 chat attempts max)
- Explicit ``enable_cad_pipeline=True`` authorising the product runner to
  call ``run_pipeline()`` after a successful LLM response + user confirmation

Constructing this object does NOT perform network I/O, read secrets, open
the formal evaluation gate, or create a batch directory.

The formal gate (``FORMAL_EVALUATION_ALLOWED=False``) is unchanged.
A batch_id is not assigned here; the project owner must supply it when
approving the execution authorisation template.

Relationship to existing authorization classes
----------------------------------------------
- ``FormalRunAuthorization`` (Phase 1, ADR-0014): 36-run Schema-only scope.
- ``HeldoutRunAuthorization`` (ADR-0019): 12-run held-out retrieval study.
- ``A2IntegrationAuthorization`` (ADR-0021): 3-run CAD integration smoke.
- ``ProductLiveAuthorization`` (this module): 4-run product live extraction
  smoke, DeepSeek only, ``enable_cad_pipeline=True``, with user confirmation
  gate before CAD.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from .authorization import AuthorizationScopeError, FormalRunAuthorization
from .contract import (
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    PROMPT_VERSION,
)
from .prompt_loader import FROZEN_PROMPT_FILE_SHA256

# ---------------------------------------------------------------------------
# Frozen product live scope constants
# ---------------------------------------------------------------------------

PRODUCT_PROFILE_ID: Final[str] = "app003-product-live.v1"
PRODUCT_SAMPLE_SET: Final[str] = "app003-product-live-smoke.v1"

# Four representative inputs: legal bore, missing bore (ask), catalog conflict,
# and unsupported request. These IDs must match model-inputs.json.
PRODUCT_INPUT_IDS: Final[tuple[str, ...]] = (
    "P1-24mm",
    "P2-ask-bore",
    "P3-catalog-conflict",
    "P4-unsupported",
)

# SHA-256 of agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json
# (computed 2026-11-13, frozen at creation).
PRODUCT_INPUTS_SHA256: Final[str] = (
    "666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a"
)

# SHA-256 of evaluator-labels.json (not passed to model).
PRODUCT_LABELS_SHA256: Final[str] = (
    "73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795"
)

# Only DeepSeek deepseek-flash; no Ollama.
PRODUCT_PROVIDER: Final[str] = DEEPSEEK_PROVIDER
PRODUCT_MODEL: Final[str] = DEEPSEEK_MODEL

# Only C0 (no retrieval context).
PRODUCT_CONDITION: Final[str] = "C0"

# Budget: 4 inputs × 1 provider × 1 condition × max 3 attempts = 12 HTTP max.
PRODUCT_MAX_LOGICAL_RUNS: Final[int] = 4
PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN: Final[int] = 3
PRODUCT_MAX_BATCH_HTTP: Final[int] = 12  # = 4 × 3

# Provider HTTP cap (DeepSeek only; equals global cap for single-provider scope).
PRODUCT_PROVIDER_HTTP_CAPS: Final[dict[str, int]] = {DEEPSEEK_PROVIDER: 12}

# Batch preflight ID used in the budget ledger for pre-run identity checks.
PRODUCT_BATCH_PREFLIGHT_ID: Final[str] = "__product_live_batch_preflight__"

# Frozen prompt file SHA-256 (from prompt_loader.py, v5 activation).
PRODUCT_PROMPT_FILE_SHA256: Final[str] = FROZEN_PROMPT_FILE_SHA256


# ---------------------------------------------------------------------------
# Authorization class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductLiveAuthorization(FormalRunAuthorization):
    """Fail-closed authorization for the product live extraction smoke.

    Extends ``FormalRunAuthorization`` so that the existing ``Adapter.run()``
    gate check (``isinstance(formal_authorization, FormalRunAuthorization)``)
    passes without modification.

    Additional fields beyond the base class:
    - ``profile_id``: must equal ``PRODUCT_PROFILE_ID``
    - ``input_ids``: must equal ``PRODUCT_INPUT_IDS``
    - ``inputs_sha256``: must equal ``PRODUCT_INPUTS_SHA256``
    - ``evaluator_labels_sha256``: must equal ``PRODUCT_LABELS_SHA256``
    - ``enable_cad_pipeline``: must be True — explicit authorisation for the
      product runner to call ``run_pipeline()`` after a successful LLM
      response AND explicit user confirmation.

    ``ir_cad_geometry_step_disabled`` is set to True (as required by the base
    class field default).  The Adapter's own staged record still marks IR/CAD
    as "blocked"; the pipeline call is a *separate* step authorised exclusively
    by ``enable_cad_pipeline=True`` in this object, gated by user confirmation.
    """

    profile_id: str
    input_ids: tuple[str, ...]
    inputs_sha256: str
    evaluator_labels_sha256: str
    enable_cad_pipeline: bool

    def __post_init__(self) -> None:  # type: ignore[override]
        """Full product live scope validation; replaces base class scope check."""
        mismatches: list[str] = []

        # Protocol versions
        expected_protos = frozenset({CONTRACT_VERSION, PROMPT_VERSION})
        if self.protocol_versions != expected_protos:
            mismatches.append(
                f"protocol_versions mismatch: expected {sorted(expected_protos)}, "
                f"got {sorted(self.protocol_versions)}"
            )

        # Sample set
        if self.sample_set != PRODUCT_SAMPLE_SET:
            mismatches.append(
                f"sample_set mismatch: expected {PRODUCT_SAMPLE_SET!r}, "
                f"got {self.sample_set!r}"
            )

        # Conditions
        if self.conditions != frozenset({PRODUCT_CONDITION}):
            mismatches.append(
                f"conditions mismatch: expected {{{PRODUCT_CONDITION!r}}}, "
                f"got {sorted(self.conditions)}"
            )

        # Provider / model: DeepSeek only
        if self.providers != frozenset({PRODUCT_PROVIDER}):
            mismatches.append(
                f"providers mismatch: expected {{{PRODUCT_PROVIDER!r}}}, "
                f"got {sorted(self.providers)}"
            )
        if self.models != frozenset({PRODUCT_MODEL}):
            mismatches.append(
                f"models mismatch: expected {{{PRODUCT_MODEL!r}}}, "
                f"got {sorted(self.models)}"
            )

        # Budget
        if self.max_logical_runs != PRODUCT_MAX_LOGICAL_RUNS:
            mismatches.append(
                f"max_logical_runs mismatch: expected {PRODUCT_MAX_LOGICAL_RUNS}, "
                f"got {self.max_logical_runs}"
            )
        if self.max_attempts_per_run != PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN:
            mismatches.append(
                f"max_attempts_per_run mismatch: expected "
                f"{PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN}, got {self.max_attempts_per_run}"
            )
        if self.max_batch_attempts != PRODUCT_MAX_BATCH_HTTP:
            mismatches.append(
                f"max_batch_attempts mismatch: expected {PRODUCT_MAX_BATCH_HTTP}, "
                f"got {self.max_batch_attempts}"
            )
        if self.max_provider_attempts != PRODUCT_PROVIDER_HTTP_CAPS[PRODUCT_PROVIDER]:
            mismatches.append(
                f"max_provider_attempts mismatch: expected "
                f"{PRODUCT_PROVIDER_HTTP_CAPS[PRODUCT_PROVIDER]}, "
                f"got {self.max_provider_attempts}"
            )

        # ir_cad_geometry_step_disabled must be True (Adapter stages stay blocked)
        if self.ir_cad_geometry_step_disabled is not True:
            mismatches.append("ir_cad_geometry_step_disabled must be True for product live")

        # Profile identity
        if self.profile_id != PRODUCT_PROFILE_ID:
            mismatches.append(
                f"profile_id mismatch: expected {PRODUCT_PROFILE_ID!r}, "
                f"got {self.profile_id!r}"
            )
        if self.input_ids != PRODUCT_INPUT_IDS:
            mismatches.append(
                f"input_ids mismatch: expected {PRODUCT_INPUT_IDS!r}, "
                f"got {self.input_ids!r}"
            )
        if self.inputs_sha256 != PRODUCT_INPUTS_SHA256:
            mismatches.append(
                f"inputs_sha256 mismatch: expected {PRODUCT_INPUTS_SHA256!r}, "
                f"got {self.inputs_sha256!r}"
            )
        if self.evaluator_labels_sha256 != PRODUCT_LABELS_SHA256:
            mismatches.append(
                f"evaluator_labels_sha256 mismatch: expected {PRODUCT_LABELS_SHA256!r}, "
                f"got {self.evaluator_labels_sha256!r}"
            )

        # Pipeline flag: must be explicitly True
        if self.enable_cad_pipeline is not True:
            mismatches.append(
                "enable_cad_pipeline must be True; "
                "product live runner requires explicit CAD pipeline authorisation"
            )

        # batch_id must be non-empty
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")

        if mismatches:
            raise AuthorizationScopeError(
                "Product live authorization scope mismatch: "
                + "; ".join(mismatches)
            )

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        """Product live authorises exactly one (provider, model) pair."""
        return (provider, model) == (PRODUCT_PROVIDER, PRODUCT_MODEL)

    def max_provider_attempts_for(self, provider: str) -> int:
        """Return the per-provider HTTP cap; raises for unauthorised providers."""
        try:
            return PRODUCT_PROVIDER_HTTP_CAPS[provider]
        except KeyError as exc:
            raise AuthorizationScopeError(
                f"provider {provider!r} is not authorised for product live scope"
            ) from exc

    def max_chat_attempts_for(self, provider: str) -> int:
        """Chat cap equals the provider HTTP cap (no identity requests)."""
        return self.max_provider_attempts_for(provider)

    def allows_logical_run(self, logical_run_id: str, provider: str) -> bool:
        """Check whether a logical_run_id belongs to the authorised scope."""
        return any(
            logical_run_id == self.expected_logical_run_id(input_id, PRODUCT_CONDITION, provider)
            for input_id in self.input_ids
        )

    def expected_logical_run_id(
        self, input_id: str, condition: str, provider: str
    ) -> str:
        """Canonical deterministic logical run ID for one (input, condition, provider)."""
        if input_id not in self.input_ids:
            raise AuthorizationScopeError(
                f"input_id {input_id!r} is outside product live scope"
            )
        if condition != PRODUCT_CONDITION:
            raise AuthorizationScopeError(
                f"condition {condition!r} is outside product live scope "
                f"(only {PRODUCT_CONDITION!r})"
            )
        if provider != PRODUCT_PROVIDER:
            raise AuthorizationScopeError(
                f"provider {provider!r} is outside product live scope "
                f"(only {PRODUCT_PROVIDER!r})"
            )
        return f"{input_id}__{condition}__{provider}__{PRODUCT_MODEL}"

    def scope_summary(self) -> dict:
        return {
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
            "provider_http_caps": dict(sorted(PRODUCT_PROVIDER_HTTP_CAPS.items())),
            "prompt_file_sha256": PRODUCT_PROMPT_FILE_SHA256,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def authorize_product_live_run(*, batch_id: str) -> ProductLiveAuthorization:
    """Construct the fixed product live authorization for a caller-supplied batch ID.

    ``batch_id`` is the only variable part.  It ties the authorization to a
    specific batch directory under ``work/app001-runs/<batch_id>/`` and must be
    unique across all batches.

    This function does NOT read environment variables, does NOT open the
    formal evaluation gate, does NOT instantiate any transport, and does NOT
    create any directory or file.
    """
    return ProductLiveAuthorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=PRODUCT_SAMPLE_SET,
        conditions=frozenset({PRODUCT_CONDITION}),
        providers=frozenset({PRODUCT_PROVIDER}),
        models=frozenset({PRODUCT_MODEL}),
        max_logical_runs=PRODUCT_MAX_LOGICAL_RUNS,
        max_attempts_per_run=PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
        max_batch_attempts=PRODUCT_MAX_BATCH_HTTP,
        max_provider_attempts=PRODUCT_PROVIDER_HTTP_CAPS[PRODUCT_PROVIDER],
        ir_cad_geometry_step_disabled=True,
        batch_id=batch_id,
        profile_id=PRODUCT_PROFILE_ID,
        input_ids=PRODUCT_INPUT_IDS,
        inputs_sha256=PRODUCT_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
        enable_cad_pipeline=True,
    )


# ---------------------------------------------------------------------------
# Owner approval credential for formal execution
# ---------------------------------------------------------------------------

_APPROVAL_STATEMENT_PREFIX: Final[str] = (
    "I approve product live formal execution of batch"
)


class ProductApprovalValidationError(ValueError):
    """Raised when a product live formal approval credential is invalid."""


@dataclass(frozen=True)
class ProductLiveFormalApproval:
    """Explicit, fail-closed owner approval credential for one product live batch.

    Formal execution requires BOTH:
    - :class:`ProductLiveAuthorization` (fixed scope check), AND
    - this :class:`ProductLiveFormalApproval` (owner approval for same batch_id).

    The approval binds to the exact same scope fields as the authorization:
    profile_id, inputs_sha256, evaluator_labels_sha256, provider, model,
    condition, max_batch_http, and enable_cad_pipeline.  The ``batch_id`` must
    match the authorization's ``batch_id`` exactly.

    Security
    --------
    - Construction validates all scope fields against frozen product constants.
    - Any mismatch raises :class:`ProductApprovalValidationError` at construction.
    - This object does NOT perform cryptographic signature verification.
    - No secrets (API keys, Authorization headers) are stored on this object.
    """

    batch_id: str
    profile_id: str
    inputs_sha256: str
    evaluator_labels_sha256: str
    provider: str
    model: str
    condition: str
    max_batch_http: int
    enable_cad_pipeline: bool
    approver: str
    approved_at_utc: str
    approval_statement: str
    approval_record_ref: str | None = None
    is_test_only: bool = False

    def __post_init__(self) -> None:
        mismatches: list[str] = []

        if self.profile_id != PRODUCT_PROFILE_ID:
            mismatches.append(
                f"profile_id mismatch: expected {PRODUCT_PROFILE_ID!r}, "
                f"got {self.profile_id!r}"
            )
        if self.inputs_sha256 != PRODUCT_INPUTS_SHA256:
            mismatches.append(
                f"inputs_sha256 mismatch: expected {PRODUCT_INPUTS_SHA256!r}, "
                f"got {self.inputs_sha256!r}"
            )
        if self.evaluator_labels_sha256 != PRODUCT_LABELS_SHA256:
            mismatches.append(
                f"evaluator_labels_sha256 mismatch: expected {PRODUCT_LABELS_SHA256!r}, "
                f"got {self.evaluator_labels_sha256!r}"
            )
        if self.provider != PRODUCT_PROVIDER:
            mismatches.append(
                f"provider mismatch: expected {PRODUCT_PROVIDER!r}, "
                f"got {self.provider!r}"
            )
        if self.model != PRODUCT_MODEL:
            mismatches.append(
                f"model mismatch: expected {PRODUCT_MODEL!r}, got {self.model!r}"
            )
        if self.condition != PRODUCT_CONDITION:
            mismatches.append(
                f"condition mismatch: expected {PRODUCT_CONDITION!r}, "
                f"got {self.condition!r}"
            )
        if self.max_batch_http != PRODUCT_MAX_BATCH_HTTP:
            mismatches.append(
                f"max_batch_http mismatch: expected {PRODUCT_MAX_BATCH_HTTP}, "
                f"got {self.max_batch_http}"
            )
        if self.enable_cad_pipeline is not True:
            mismatches.append("enable_cad_pipeline must be True")

        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")
        if not isinstance(self.approver, str) or not self.approver.strip():
            mismatches.append("approver must be a non-empty string")
        if not isinstance(self.approved_at_utc, str) or not self.approved_at_utc.strip():
            mismatches.append("approved_at_utc must be a non-empty string")
        if not isinstance(self.approval_statement, str) or not self.approval_statement.strip():
            mismatches.append("approval_statement must be a non-empty string")

        if mismatches:
            raise ProductApprovalValidationError(
                "Product live formal approval scope validation failed: "
                + "; ".join(mismatches)
            )

    def matches_authorization(
        self, authorization: ProductLiveAuthorization
    ) -> bool:
        """Return True iff this approval's batch_id matches the authorization's."""
        return self.batch_id == authorization.batch_id

    def as_audit_dict(self) -> dict[str, Any]:
        """Return a redacted audit record of this approval (no secrets)."""
        return {
            "approver": self.approver,
            "approved_at_utc": self.approved_at_utc,
            "approval_statement": self.approval_statement,
            "approval_record_ref": self.approval_record_ref,
            "batch_id": self.batch_id,
            "profile_id": self.profile_id,
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "provider": self.provider,
            "model": self.model,
            "condition": self.condition,
            "max_batch_http": self.max_batch_http,
            "enable_cad_pipeline": self.enable_cad_pipeline,
        }


def validate_product_formal_approval_binding(
    authorization: ProductLiveAuthorization,
    approval: ProductLiveFormalApproval,
) -> None:
    """Validate that an approval credential is bound to the same batch.

    Raises :class:`ProductApprovalValidationError` if the batch_ids do not
    match or if the approval is marked as test-only.

    This check MUST be performed BEFORE any directory creation, BudgetLedger
    initialization, Transport construction, or network I/O.
    """
    if not isinstance(approval, ProductLiveFormalApproval):
        raise ProductApprovalValidationError(
            f"approval must be a ProductLiveFormalApproval instance, "
            f"got {type(approval).__name__}"
        )
    if not isinstance(authorization, ProductLiveAuthorization):
        raise ProductApprovalValidationError(
            f"authorization must be a ProductLiveAuthorization instance, "
            f"got {type(authorization).__name__}"
        )
    if getattr(approval, "is_test_only", False):
        raise ProductApprovalValidationError(
            "test-only approval credential cannot be used for a formal product "
            "live run; a real owner-approved ProductLiveFormalApproval with "
            "is_test_only=False (the default) is required for live execution"
        )
    if approval.batch_id != authorization.batch_id:
        raise ProductApprovalValidationError(
            f"approval batch_id {approval.batch_id!r} does not match "
            f"authorization batch_id {authorization.batch_id!r}"
        )


def make_product_test_approval(
    *,
    batch_id: str,
    approver: str = "test-owner",
    approved_at_utc: str = "2026-11-13T00:00:00Z",
    approval_statement: str | None = None,
    approval_record_ref: str | None = None,
) -> ProductLiveFormalApproval:
    """Construct a test-only ProductLiveFormalApproval for unit tests.

    This produces a structurally valid approval credential bound to the given
    batch_id.  It is for MOCK TESTS ONLY.  The credential has ``is_test_only=True``
    which is structurally rejected by
    :func:`validate_product_formal_approval_binding`.
    """
    if approval_statement is None:
        approval_statement = (
            f"{_APPROVAL_STATEMENT_PREFIX} {batch_id} "
            f"for product live smoke test (TEST ONLY, not a real approval)"
        )
    return ProductLiveFormalApproval(
        batch_id=batch_id,
        profile_id=PRODUCT_PROFILE_ID,
        inputs_sha256=PRODUCT_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LABELS_SHA256,
        provider=PRODUCT_PROVIDER,
        model=PRODUCT_MODEL,
        condition=PRODUCT_CONDITION,
        max_batch_http=PRODUCT_MAX_BATCH_HTTP,
        enable_cad_pipeline=True,
        approver=approver,
        approved_at_utc=approved_at_utc,
        approval_statement=approval_statement,
        approval_record_ref=approval_record_ref,
        is_test_only=True,
    )
