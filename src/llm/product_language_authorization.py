"""Versioned authorization profile for the APP-003 language matrix.

This module only defines immutable scope identity.  It does not authorize a
live request by itself, read credentials, create a batch, or open the global
formal-evaluation gate.  The profile is intentionally separate from the
four-input ``app003-product-live.v1`` profile.
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


__all__ = [
    "PRODUCT_LANGUAGE_PROFILE_ID", "PRODUCT_LANGUAGE_INPUT_IDS",
    "PRODUCT_LANGUAGE_INPUTS_SHA256", "PRODUCT_LANGUAGE_LABELS_SHA256",
    "PRODUCT_LANGUAGE_PROVIDER", "PRODUCT_LANGUAGE_MODEL",
    "PRODUCT_LANGUAGE_CONDITION", "PRODUCT_LANGUAGE_MAX_BATCH_HTTP",
    "ProductLanguageAuthorization", "authorize_product_language_run",
]
