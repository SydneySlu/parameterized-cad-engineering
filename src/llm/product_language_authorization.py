"""Versioned authorization profile and formal approval for the APP-003 language matrix.

This module defines immutable scope identity and the formal approval credential
required for the ten-input language sample formal runner.

It does NOT read credentials, create a batch, make network calls, or open the
global formal-evaluation gate.  The profile is intentionally separate from the
four-input ``app003-product-live.v1`` profile.
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

PRODUCT_LANGUAGE_PROFILE_ID: Final[str] = "app003-product-language.v1"
PRODUCT_LANGUAGE_SAMPLE_SET: Final[str] = "app003-language-sample-20261114-01.v1"
PRODUCT_LANGUAGE_INPUT_IDS: Final[tuple[str, ...]] = (
    "L01-legal-24mm",
    "L02-inch-noncatalog",
    "L03-catalog-conflict",
    "L04-missing-bore",
    "L05-unsupported-finish",
    "L06-near-boundary-25mm",
    "L07-meter-24mm",
    "L08-unsupported-keyway",
    "L09-ambiguous-fallback",
    "L10-vague-size",
)
PRODUCT_LANGUAGE_INPUTS_SHA256: Final[str] = (
    "8339431ee66a14d838cdbded48240019254182886c85af5cd611e04eaf361801"
)
PRODUCT_LANGUAGE_LABELS_SHA256: Final[str] = (
    "a5055025e4a01740b9bc25daa5ab51e43bdac9748151ccd10c152cdf7151bcf9"
)
PRODUCT_LANGUAGE_PROVIDER: Final[str] = DEEPSEEK_PROVIDER
PRODUCT_LANGUAGE_MODEL: Final[str] = DEEPSEEK_MODEL
PRODUCT_LANGUAGE_CONDITION: Final[str] = "C0"
PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS: Final[int] = 10
PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN: Final[int] = 2
PRODUCT_LANGUAGE_MAX_BATCH_HTTP: Final[int] = 20
PRODUCT_LANGUAGE_PROMPT_SHA256: Final[str] = FROZEN_PROMPT_FILE_SHA256


@dataclass(frozen=True)
class ProductLanguageAuthorization(FormalRunAuthorization):
    """Scope-bound base authorization for the ten-input language matrix.

    This is not an execution approval.  Live use must be added through a
    separately reviewed runner and a matching, non-test-only owner approval.
    """

    profile_id: str
    input_ids: tuple[str, ...]
    inputs_sha256: str
    evaluator_labels_sha256: str

    def __post_init__(self) -> None:  # type: ignore[override]
        mismatches: list[str] = []
        expected = {
            "protocol_versions": frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
            "sample_set": PRODUCT_LANGUAGE_SAMPLE_SET,
            "conditions": frozenset({PRODUCT_LANGUAGE_CONDITION}),
            "providers": frozenset({PRODUCT_LANGUAGE_PROVIDER}),
            "models": frozenset({PRODUCT_LANGUAGE_MODEL}),
            "max_logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
            "max_batch_attempts": PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
            "max_provider_attempts": PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
            "ir_cad_geometry_step_disabled": True,
            "profile_id": PRODUCT_LANGUAGE_PROFILE_ID,
            "input_ids": PRODUCT_LANGUAGE_INPUT_IDS,
            "inputs_sha256": PRODUCT_LANGUAGE_INPUTS_SHA256,
            "evaluator_labels_sha256": PRODUCT_LANGUAGE_LABELS_SHA256,
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                mismatches.append(f"{name} mismatch")
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")
        if mismatches:
            raise AuthorizationScopeError(
                "Product language authorization scope mismatch: "
                + "; ".join(mismatches)
            )

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        return (provider, model) == (
            PRODUCT_LANGUAGE_PROVIDER,
            PRODUCT_LANGUAGE_MODEL,
        )

    def max_provider_attempts_for(self, provider: str) -> int:
        if provider != PRODUCT_LANGUAGE_PROVIDER:
            raise AuthorizationScopeError(f"provider {provider!r} is outside scope")
        return PRODUCT_LANGUAGE_MAX_BATCH_HTTP

    def max_chat_attempts_for(self, provider: str) -> int:
        if provider != PRODUCT_LANGUAGE_PROVIDER:
            raise AuthorizationScopeError(f"provider {provider!r} is outside scope")
        return PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN

    def expected_logical_run_id(
        self, input_id: str, condition: str = PRODUCT_LANGUAGE_CONDITION,
        provider: str = PRODUCT_LANGUAGE_PROVIDER,
    ) -> str:
        if input_id not in self.input_ids:
            raise AuthorizationScopeError(f"input_id {input_id!r} is outside scope")
        if condition != PRODUCT_LANGUAGE_CONDITION:
            raise AuthorizationScopeError(f"condition {condition!r} is outside scope")
        if provider != PRODUCT_LANGUAGE_PROVIDER:
            raise AuthorizationScopeError(f"provider {provider!r} is outside scope")
        return f"{input_id}__{condition}__{provider}__{PRODUCT_LANGUAGE_MODEL}"

    def scope_summary(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "batch_id": self.batch_id,
            "input_ids": list(self.input_ids),
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "provider": PRODUCT_LANGUAGE_PROVIDER,
            "model": PRODUCT_LANGUAGE_MODEL,
            "condition": PRODUCT_LANGUAGE_CONDITION,
            "max_logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
            "max_batch_http": PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
            "ir_cad_geometry_step_disabled": True,
            "prompt_file_sha256": PRODUCT_LANGUAGE_PROMPT_SHA256,
        }


def authorize_product_language_run(*, batch_id: str) -> ProductLanguageAuthorization:
    """Construct the versioned scope identity without side effects."""
    return ProductLanguageAuthorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=PRODUCT_LANGUAGE_SAMPLE_SET,
        conditions=frozenset({PRODUCT_LANGUAGE_CONDITION}),
        providers=frozenset({PRODUCT_LANGUAGE_PROVIDER}),
        models=frozenset({PRODUCT_LANGUAGE_MODEL}),
        max_logical_runs=PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
        max_attempts_per_run=PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
        max_batch_attempts=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
        max_provider_attempts=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
        ir_cad_geometry_step_disabled=True,
        batch_id=batch_id,
        profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
        input_ids=PRODUCT_LANGUAGE_INPUT_IDS,
        inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
    )


# ---------------------------------------------------------------------------
# Formal approval credential for the language sample runner
# ---------------------------------------------------------------------------

_LANGUAGE_APPROVAL_STATEMENT_PREFIX: Final[str] = (
    "I approve the formal execution of the ten-input language sample batch"
)


class ProductLanguageApprovalValidationError(ValueError):
    """Raised when a language sample formal approval credential is invalid."""


@dataclass(frozen=True)
class ProductLanguageFormalApproval:
    """Explicit, fail-closed owner approval credential for one language sample batch.

    Formal execution requires BOTH:
    - :class:`ProductLanguageAuthorization` (fixed scope check), AND
    - this :class:`ProductLanguageFormalApproval` (owner approval for same batch_id).

    Security
    --------
    - Construction validates all scope fields against frozen language constants.
    - Any mismatch raises :class:`ProductLanguageApprovalValidationError` at construction.
    - ``is_test_only=True`` credentials are structurally rejected by
      :func:`validate_product_language_formal_approval_binding`.
    - No secrets (API keys, Authorization headers) are stored on this object.
    - Automatic CAD pipeline is never authorised by this profile.
    """

    batch_id: str
    profile_id: str
    inputs_sha256: str
    evaluator_labels_sha256: str
    provider: str
    model: str
    condition: str
    max_batch_http: int
    automatic_cad_pipeline: bool
    approver: str
    approved_at_utc: str
    approval_statement: str
    approval_record_ref: str | None = None
    is_test_only: bool = False

    def __post_init__(self) -> None:
        mismatches: list[str] = []
        if self.profile_id != PRODUCT_LANGUAGE_PROFILE_ID:
            mismatches.append(
                f"profile_id mismatch: expected {PRODUCT_LANGUAGE_PROFILE_ID!r}, "
                f"got {self.profile_id!r}"
            )
        if self.inputs_sha256 != PRODUCT_LANGUAGE_INPUTS_SHA256:
            mismatches.append(
                f"inputs_sha256 mismatch: expected {PRODUCT_LANGUAGE_INPUTS_SHA256!r}, "
                f"got {self.inputs_sha256!r}"
            )
        if self.evaluator_labels_sha256 != PRODUCT_LANGUAGE_LABELS_SHA256:
            mismatches.append(
                f"evaluator_labels_sha256 mismatch: "
                f"expected {PRODUCT_LANGUAGE_LABELS_SHA256!r}, "
                f"got {self.evaluator_labels_sha256!r}"
            )
        if self.provider != PRODUCT_LANGUAGE_PROVIDER:
            mismatches.append(
                f"provider mismatch: expected {PRODUCT_LANGUAGE_PROVIDER!r}, "
                f"got {self.provider!r}"
            )
        if self.model != PRODUCT_LANGUAGE_MODEL:
            mismatches.append(
                f"model mismatch: expected {PRODUCT_LANGUAGE_MODEL!r}, "
                f"got {self.model!r}"
            )
        if self.condition != PRODUCT_LANGUAGE_CONDITION:
            mismatches.append(
                f"condition mismatch: expected {PRODUCT_LANGUAGE_CONDITION!r}, "
                f"got {self.condition!r}"
            )
        if self.max_batch_http != PRODUCT_LANGUAGE_MAX_BATCH_HTTP:
            mismatches.append(
                f"max_batch_http mismatch: expected {PRODUCT_LANGUAGE_MAX_BATCH_HTTP}, "
                f"got {self.max_batch_http}"
            )
        if self.automatic_cad_pipeline is not False:
            mismatches.append(
                "automatic_cad_pipeline must be False; "
                "language sample scope never authorises automatic CAD execution"
            )
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")
        if not isinstance(self.approver, str) or not self.approver.strip():
            mismatches.append("approver must be a non-empty string")
        if not isinstance(self.approved_at_utc, str) or not self.approved_at_utc.strip():
            mismatches.append("approved_at_utc must be a non-empty string")
        if not isinstance(self.approval_statement, str) or not self.approval_statement.strip():
            mismatches.append("approval_statement must be a non-empty string")
        if mismatches:
            raise ProductLanguageApprovalValidationError(
                "Language sample formal approval scope validation failed: "
                + "; ".join(mismatches)
            )

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
            "automatic_cad_pipeline": self.automatic_cad_pipeline,
        }


def validate_product_language_formal_approval_binding(
    authorization: ProductLanguageAuthorization,
    approval: ProductLanguageFormalApproval,
) -> None:
    """Validate that an approval credential is bound to the same batch scope.

    Raises :class:`ProductLanguageApprovalValidationError` if:
    - Either argument is the wrong type
    - ``approval.is_test_only`` is True
    - ``approval.batch_id`` does not match ``authorization.batch_id``

    This check MUST be performed BEFORE any directory creation, BudgetLedger
    initialisation, Transport construction, or network I/O.
    """
    if not isinstance(approval, ProductLanguageFormalApproval):
        raise ProductLanguageApprovalValidationError(
            f"approval must be a ProductLanguageFormalApproval instance, "
            f"got {type(approval).__name__}"
        )
    if not isinstance(authorization, ProductLanguageAuthorization):
        raise ProductLanguageApprovalValidationError(
            f"authorization must be a ProductLanguageAuthorization instance, "
            f"got {type(authorization).__name__}"
        )
    if approval.is_test_only:
        raise ProductLanguageApprovalValidationError(
            "test-only approval credential cannot be used for a formal language "
            "sample run; a real owner-approved ProductLanguageFormalApproval with "
            "is_test_only=False (the default) is required for live execution"
        )
    if approval.batch_id != authorization.batch_id:
        raise ProductLanguageApprovalValidationError(
            f"approval batch_id {approval.batch_id!r} does not match "
            f"authorization batch_id {authorization.batch_id!r}"
        )


def make_language_test_approval(
    *,
    batch_id: str,
    approver: str = "test-owner",
    approved_at_utc: str = "2026-11-14T00:00:00Z",
    approval_statement: str | None = None,
    approval_record_ref: str | None = None,
) -> ProductLanguageFormalApproval:
    """Construct a test-only approval credential for unit tests.

    The resulting object has ``is_test_only=True``, which is structurally
    rejected by :func:`validate_product_language_formal_approval_binding`.
    It exercises the approval dataclass path without authorising real execution.
    """
    if approval_statement is None:
        approval_statement = (
            f"{_LANGUAGE_APPROVAL_STATEMENT_PREFIX} {batch_id} (TEST ONLY)"
        )
    return ProductLanguageFormalApproval(
        batch_id=batch_id,
        profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
        inputs_sha256=PRODUCT_LANGUAGE_INPUTS_SHA256,
        evaluator_labels_sha256=PRODUCT_LANGUAGE_LABELS_SHA256,
        provider=PRODUCT_LANGUAGE_PROVIDER,
        model=PRODUCT_LANGUAGE_MODEL,
        condition=PRODUCT_LANGUAGE_CONDITION,
        max_batch_http=PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
        automatic_cad_pipeline=False,
        approver=approver,
        approved_at_utc=approved_at_utc,
        approval_statement=approval_statement,
        approval_record_ref=approval_record_ref,
        is_test_only=True,
    )


__all__ = [
    "PRODUCT_LANGUAGE_PROFILE_ID", "PRODUCT_LANGUAGE_INPUT_IDS",
    "PRODUCT_LANGUAGE_INPUTS_SHA256", "PRODUCT_LANGUAGE_LABELS_SHA256",
    "PRODUCT_LANGUAGE_PROVIDER", "PRODUCT_LANGUAGE_MODEL",
    "PRODUCT_LANGUAGE_CONDITION", "PRODUCT_LANGUAGE_MAX_BATCH_HTTP",
    "ProductLanguageAuthorization", "authorize_product_language_run",
    "ProductLanguageApprovalValidationError",
    "ProductLanguageFormalApproval",
    "validate_product_language_formal_approval_binding",
    "make_language_test_approval",
]
