"""Scope-bound authorization for the APP-004 localhost live web demo.

This profile is intentionally isolated from the APP-003 product-live and
language-sample profiles. Constructing authorization or approval objects has
no filesystem, credential, CAD, or network side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .authorization import AuthorizationScopeError, FormalRunAuthorization
from .contract import CONTRACT_VERSION, DEEPSEEK_MODEL, DEEPSEEK_PROVIDER, PROMPT_VERSION

APP004_PROFILE_ID: Final[str] = "app004-live-web-demo.v1"
APP004_SAMPLE_SET: Final[str] = "app004-live-web-demo.v1"
APP004_BATCH_ID: Final[str] = "app004-live-web-demo-20261116-01"
APP004_INPUT_IDS: Final[tuple[str, ...]] = (
    "D01-collar-bore24",
    "D02-collar-anodizing",
)
APP004_INPUTS_SHA256: Final[str] = (
    "4c97a043e1547831fd92f3f7a95ba65b6ea6734b073f2ce9687454143ed65841"
)
APP004_LABELS_SHA256: Final[str] = (
    "4eff6146ee2b1809a9720407eceb605257340204fbca409a2c35e94295c5e091"
)
APP004_PROMPT_SHA256: Final[str] = (
    "18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9"
)
APP004_CONTRACT_SHA256: Final[str] = (
    "6e7c6022325273cedb5a0ba637c6165fd4237b16f63e362bb6844c5029a11d66"
)
APP004_PROVIDER: Final[str] = DEEPSEEK_PROVIDER
APP004_MODEL: Final[str] = DEEPSEEK_MODEL
APP004_CONDITION: Final[str] = "C0"
APP004_MAX_LOGICAL_RUNS: Final[int] = 2
APP004_MAX_ATTEMPTS_PER_RUN: Final[int] = 2
APP004_MAX_BATCH_HTTP: Final[int] = 4
@dataclass(frozen=True)
class App004LiveWebAuthorization(FormalRunAuthorization):
    """Authorization bound to the exact two-input APP-004 demo scope."""

    profile_id: str
    input_ids: tuple[str, ...]
    inputs_sha256: str
    evaluator_labels_sha256: str
    prompt_sha256: str
    contract_sha256: str
    enable_cad_pipeline: bool

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.protocol_versions != frozenset({CONTRACT_VERSION, PROMPT_VERSION}):
            errors.append("protocol_versions mismatch")
        if self.sample_set != APP004_SAMPLE_SET:
            errors.append("sample_set mismatch")
        if self.conditions != frozenset({APP004_CONDITION}):
            errors.append("conditions mismatch")
        if self.providers != frozenset({APP004_PROVIDER}):
            errors.append("providers mismatch")
        if self.models != frozenset({APP004_MODEL}):
            errors.append("models mismatch")
        if self.max_logical_runs != APP004_MAX_LOGICAL_RUNS:
            errors.append("max_logical_runs mismatch")
        if self.max_attempts_per_run != APP004_MAX_ATTEMPTS_PER_RUN:
            errors.append("max_attempts_per_run mismatch")
        if self.max_batch_attempts != APP004_MAX_BATCH_HTTP:
            errors.append("max_batch_attempts mismatch")
        if self.max_provider_attempts != APP004_MAX_BATCH_HTTP:
            errors.append("max_provider_attempts mismatch")
        if self.ir_cad_geometry_step_disabled is not True:
            errors.append("ir_cad_geometry_step_disabled must be True")
        if self.profile_id != APP004_PROFILE_ID:
            errors.append("profile_id mismatch")
        if self.input_ids != APP004_INPUT_IDS:
            errors.append("input_ids mismatch")
        if self.inputs_sha256 != APP004_INPUTS_SHA256:
            errors.append("inputs_sha256 mismatch")
        if self.evaluator_labels_sha256 != APP004_LABELS_SHA256:
            errors.append("evaluator_labels_sha256 mismatch")
        if self.prompt_sha256 != APP004_PROMPT_SHA256:
            errors.append("prompt_sha256 mismatch")
        if self.contract_sha256 != APP004_CONTRACT_SHA256:
            errors.append("contract_sha256 mismatch")
        if self.enable_cad_pipeline is not True:
            errors.append("enable_cad_pipeline must be True")
        if self.batch_id != APP004_BATCH_ID:
            errors.append("batch_id mismatch")
        if errors:
            raise AuthorizationScopeError("APP-004 authorization mismatch: " + "; ".join(errors))

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        return (provider, model) == (APP004_PROVIDER, APP004_MODEL)

    def max_provider_attempts_for(self, provider: str) -> int:
        if provider != APP004_PROVIDER:
            raise AuthorizationScopeError(f"provider {provider!r} is outside APP-004 scope")
        return APP004_MAX_BATCH_HTTP

    def max_chat_attempts_for(self, provider: str) -> int:
        return self.max_provider_attempts_for(provider)

    def allows_logical_run(self, logical_run_id: str, provider: str) -> bool:
        if provider != APP004_PROVIDER:
            return False
        return any(
            logical_run_id == self.expected_logical_run_id(input_id, APP004_CONDITION, provider)
            for input_id in self.input_ids
        )

    def expected_logical_run_id(self, input_id: str, condition: str, provider: str) -> str:
        if input_id not in self.input_ids or condition != APP004_CONDITION or provider != APP004_PROVIDER:
            raise AuthorizationScopeError("logical run is outside APP-004 scope")
        return f"{input_id}__{APP004_CONDITION}__{APP004_PROVIDER}__{APP004_MODEL}"

    def scope_summary(self) -> dict[str, object]:
        return {
            **super().scope_summary(),
            "profile_id": self.profile_id,
            "input_ids": list(self.input_ids),
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "prompt_sha256": self.prompt_sha256,
            "contract_sha256": self.contract_sha256,
            "enable_cad_pipeline": self.enable_cad_pipeline,
        }


class App004ApprovalValidationError(ValueError):
    """Raised when an APP-004 execution approval does not match the scope."""


@dataclass(frozen=True)
class App004LiveWebApproval:
    batch_id: str
    profile_id: str
    inputs_sha256: str
    evaluator_labels_sha256: str
    prompt_sha256: str
    contract_sha256: str
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
        expected = {
            "batch_id": APP004_BATCH_ID,
            "profile_id": APP004_PROFILE_ID,
            "inputs_sha256": APP004_INPUTS_SHA256,
            "evaluator_labels_sha256": APP004_LABELS_SHA256,
            "prompt_sha256": APP004_PROMPT_SHA256,
            "contract_sha256": APP004_CONTRACT_SHA256,
            "provider": APP004_PROVIDER,
            "model": APP004_MODEL,
            "condition": APP004_CONDITION,
            "max_batch_http": APP004_MAX_BATCH_HTTP,
            "enable_cad_pipeline": True,
        }
        mismatches = [
            key for key, value in expected.items()
            if type(getattr(self, key)) is not type(value) or getattr(self, key) != value
        ]
        for key in ("approver", "approved_at_utc", "approval_statement"):
            value = getattr(self, key)
            if type(value) is not str or not value.strip():
                mismatches.append(key)
        if self.approval_record_ref is not None and type(self.approval_record_ref) is not str:
            mismatches.append("approval_record_ref")
        if type(self.is_test_only) is not bool:
            mismatches.append("is_test_only")
        if mismatches:
            raise App004ApprovalValidationError(
                "APP-004 approval mismatch: " + ", ".join(mismatches)
            )

    def as_audit_dict(self) -> dict[str, object]:
        import hashlib

        return {
            "batch_id": self.batch_id,
            "profile_id": self.profile_id,
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "prompt_sha256": self.prompt_sha256,
            "contract_sha256": self.contract_sha256,
            "provider": self.provider,
            "model": self.model,
            "condition": self.condition,
            "max_batch_http": self.max_batch_http,
            "enable_cad_pipeline": self.enable_cad_pipeline,
            "approver": self.approver,
            "approved_at_utc": self.approved_at_utc,
            "approval_statement_sha256": hashlib.sha256(
                self.approval_statement.encode("utf-8")
            ).hexdigest(),
            "approval_record_ref_sha256": (
                hashlib.sha256(self.approval_record_ref.encode("utf-8")).hexdigest()
                if self.approval_record_ref else None
            ),
        }


def validate_app004_approval_binding(
    authorization: App004LiveWebAuthorization,
    approval: App004LiveWebApproval,
) -> None:
    if type(authorization) is not App004LiveWebAuthorization:
        raise App004ApprovalValidationError("expected App004LiveWebAuthorization")
    if type(approval) is not App004LiveWebApproval:
        raise App004ApprovalValidationError("expected App004LiveWebApproval")
    try:
        # Re-run the profile's immutable-scope checks at the execution gate;
        # frozen dataclasses can still be altered with low-level mutation.
        authorization.__post_init__()
    except AuthorizationScopeError as exc:
        raise App004ApprovalValidationError("APP-004 authorization binding invalid") from exc
    try:
        # Approval dataclasses are frozen for normal use, but object.__setattr__
        # can still mutate them. Re-run every constructor invariant before any
        # preflight, credential read, directory creation, or ledger setup.
        approval.__post_init__()
    except App004ApprovalValidationError as exc:
        raise App004ApprovalValidationError("APP-004 approval binding invalid") from exc
    if type(approval.is_test_only) is not bool or approval.is_test_only is not False:
        raise App004ApprovalValidationError("test-only approval cannot authorize live execution")
    expected = {
        "batch_id": authorization.batch_id,
        "profile_id": authorization.profile_id,
        "inputs_sha256": authorization.inputs_sha256,
        "evaluator_labels_sha256": authorization.evaluator_labels_sha256,
        "prompt_sha256": authorization.prompt_sha256,
        "contract_sha256": authorization.contract_sha256,
        "provider": APP004_PROVIDER,
        "model": APP004_MODEL,
        "condition": APP004_CONDITION,
        "max_batch_http": authorization.max_batch_attempts,
        "enable_cad_pipeline": authorization.enable_cad_pipeline,
    }
    mismatches = [
        key for key, value in expected.items()
        if type(getattr(approval, key)) is not type(value) or getattr(approval, key) != value
    ]
    for key in ("approver", "approved_at_utc", "approval_statement"):
        value = getattr(approval, key)
        if type(value) is not str or not value.strip():
            mismatches.append(key)
    if mismatches:
        raise App004ApprovalValidationError(
            "APP-004 approval binding mismatch: " + ", ".join(mismatches)
        )


def make_app004_test_approval() -> App004LiveWebApproval:
    """Create a structurally valid test-only approval for offline tests."""
    return App004LiveWebApproval(
        batch_id=APP004_BATCH_ID,
        profile_id=APP004_PROFILE_ID,
        inputs_sha256=APP004_INPUTS_SHA256,
        evaluator_labels_sha256=APP004_LABELS_SHA256,
        prompt_sha256=APP004_PROMPT_SHA256,
        contract_sha256=APP004_CONTRACT_SHA256,
        provider=APP004_PROVIDER,
        model=APP004_MODEL,
        condition=APP004_CONDITION,
        max_batch_http=APP004_MAX_BATCH_HTTP,
        enable_cad_pipeline=True,
        approver="test-only",
        approved_at_utc="2026-11-16T00:00:00Z",
        approval_statement="TEST ONLY; no live execution authorized",
        is_test_only=True,
    )


__all__ = [
    "APP004_PROFILE_ID", "APP004_SAMPLE_SET", "APP004_BATCH_ID",
    "APP004_INPUT_IDS", "APP004_INPUTS_SHA256", "APP004_LABELS_SHA256",
    "APP004_PROMPT_SHA256", "APP004_CONTRACT_SHA256",
    "APP004_PROVIDER", "APP004_MODEL", "APP004_CONDITION",
    "APP004_MAX_LOGICAL_RUNS", "APP004_MAX_ATTEMPTS_PER_RUN",
    "APP004_MAX_BATCH_HTTP",
    "App004LiveWebAuthorization", "App004LiveWebApproval",
    "App004ApprovalValidationError", "validate_app004_approval_binding",
    "make_app004_test_approval",
]
