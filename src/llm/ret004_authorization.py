"""Frozen authorization contract for the RET-004 paired C0/C1 experiment.

Constructing these objects is side-effect free. This module binds one exact
candidate scope; it does not itself authorize execution or open the global
formal-evaluation gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .authorization import AuthorizationScopeError, FormalRunAuthorization
from .contract import CONTRACT_VERSION, DEEPSEEK_MODEL, DEEPSEEK_PROVIDER, PROMPT_VERSION

RET004_PROFILE_ID: Final[str] = "ret004-paired-live.v1"
RET004_BATCH_ID: Final[str] = "ret004-paired-live-20261116-01"
RET004_INPUT_IDS: Final[tuple[str, ...]] = (
    "R01-collar-bore24", "R02-collar-bore24-anodizing",
)
RET004_INPUTS_SHA256: Final[str] = "6f2faf8d83aa013c860db4e17593788bc906757660ed8c985f374b6bbe21a457"
RET004_LABELS_SHA256: Final[str] = "fc1691317dfc6452a956bad36fff8e5e6cd3a4d4dbf459d096632e6e4850091e"
RET004_PROMPT_SHA256: Final[str] = "18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9"
RET004_CONTRACT_SHA256: Final[str] = "6e7c6022325273cedb5a0ba637c6165fd4237b16f63e362bb6844c5029a11d66"
RET004_MANIFEST_SHA256: Final[str] = "b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297"
RET004_CONFIG_SHA256: Final[str] = "424322f51da78df2a154043d284d307ae285c7d2a2cb659f5517a6ecb847cfc5"
RET004_PROVIDER: Final[str] = DEEPSEEK_PROVIDER
RET004_MODEL: Final[str] = DEEPSEEK_MODEL
RET004_CONDITIONS: Final[tuple[str, ...]] = ("C0", "C1")
RET004_MAX_RUNS: Final[int] = 4
RET004_MAX_ATTEMPTS_PER_RUN: Final[int] = 2
RET004_MAX_HTTP: Final[int] = 8


@dataclass(frozen=True)
class RET004Authorization(FormalRunAuthorization):
    profile_id: str
    input_ids: tuple[str, ...]
    inputs_sha256: str
    labels_sha256: str
    prompt_sha256: str
    contract_sha256: str
    manifest_sha256: str
    retrieval_config_sha256: str
    enable_cad_pipeline: bool

    def __post_init__(self) -> None:
        expected = {
            "protocol_versions": frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
            "sample_set": RET004_PROFILE_ID,
            "conditions": frozenset(RET004_CONDITIONS),
            "providers": frozenset({RET004_PROVIDER}),
            "models": frozenset({RET004_MODEL}),
            "max_logical_runs": RET004_MAX_RUNS,
            "max_attempts_per_run": RET004_MAX_ATTEMPTS_PER_RUN,
            "max_batch_attempts": RET004_MAX_HTTP,
            "max_provider_attempts": RET004_MAX_HTTP,
            "ir_cad_geometry_step_disabled": False,
            "profile_id": RET004_PROFILE_ID,
            "input_ids": RET004_INPUT_IDS,
            "inputs_sha256": RET004_INPUTS_SHA256,
            "labels_sha256": RET004_LABELS_SHA256,
            "prompt_sha256": RET004_PROMPT_SHA256,
            "contract_sha256": RET004_CONTRACT_SHA256,
            "manifest_sha256": RET004_MANIFEST_SHA256,
            "retrieval_config_sha256": RET004_CONFIG_SHA256,
            "enable_cad_pipeline": True,
            "batch_id": RET004_BATCH_ID,
        }
        wrong = [k for k, v in expected.items() if type(getattr(self, k)) is not type(v) or getattr(self, k) != v]
        if wrong:
            raise AuthorizationScopeError("RET-004 scope mismatch: " + ", ".join(wrong))

    def provider_model_is_allowed(self, provider: str, model: str) -> bool:
        return (provider, model) == (RET004_PROVIDER, RET004_MODEL)

    def max_provider_attempts_for(self, provider: str) -> int:
        if provider != RET004_PROVIDER:
            raise AuthorizationScopeError("provider outside RET-004 scope")
        return RET004_MAX_HTTP

    def max_chat_attempts_for(self, provider: str) -> int:
        return self.max_provider_attempts_for(provider)

    def expected_logical_run_id(self, input_id: str, condition: str, provider: str = RET004_PROVIDER) -> str:
        if input_id not in RET004_INPUT_IDS or condition not in RET004_CONDITIONS or provider != RET004_PROVIDER:
            raise AuthorizationScopeError("logical run outside RET-004 scope")
        return f"{input_id}__{condition}__{provider}__{RET004_MODEL}"

    def allows_logical_run(self, logical_run_id: str, provider: str) -> bool:
        if provider != RET004_PROVIDER:
            return False
        return any(
            logical_run_id == self.expected_logical_run_id(input_id, condition, provider)
            for input_id in RET004_INPUT_IDS for condition in RET004_CONDITIONS
        )

    def scope_summary(self) -> dict:
        return {
            **super().scope_summary(), "profile_id": self.profile_id,
            "input_ids": list(self.input_ids), "inputs_sha256": self.inputs_sha256,
            "labels_sha256": self.labels_sha256, "prompt_sha256": self.prompt_sha256,
            "contract_sha256": self.contract_sha256, "manifest_sha256": self.manifest_sha256,
            "retrieval_config_sha256": self.retrieval_config_sha256,
            "enable_cad_pipeline": self.enable_cad_pipeline,
        }


def authorize_ret004() -> RET004Authorization:
    return RET004Authorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=RET004_PROFILE_ID, conditions=frozenset(RET004_CONDITIONS),
        providers=frozenset({RET004_PROVIDER}), models=frozenset({RET004_MODEL}),
        max_logical_runs=RET004_MAX_RUNS, max_attempts_per_run=RET004_MAX_ATTEMPTS_PER_RUN,
        max_batch_attempts=RET004_MAX_HTTP, max_provider_attempts=RET004_MAX_HTTP,
        ir_cad_geometry_step_disabled=False, batch_id=RET004_BATCH_ID,
        profile_id=RET004_PROFILE_ID, input_ids=RET004_INPUT_IDS,
        inputs_sha256=RET004_INPUTS_SHA256, labels_sha256=RET004_LABELS_SHA256,
        prompt_sha256=RET004_PROMPT_SHA256, contract_sha256=RET004_CONTRACT_SHA256,
        manifest_sha256=RET004_MANIFEST_SHA256,
        retrieval_config_sha256=RET004_CONFIG_SHA256, enable_cad_pipeline=True,
    )


@dataclass(frozen=True)
class RET004Approval:
    batch_id: str
    profile_id: str
    inputs_sha256: str
    labels_sha256: str
    prompt_sha256: str
    contract_sha256: str
    manifest_sha256: str
    retrieval_config_sha256: str
    provider: str
    model: str
    conditions: tuple[str, ...]
    max_batch_http: int
    enable_cad_pipeline: bool
    approver: str
    approved_at_utc: str
    approval_statement: str
    is_test_only: bool = False

    def __post_init__(self) -> None:
        expected = {
            "batch_id": RET004_BATCH_ID, "profile_id": RET004_PROFILE_ID,
            "inputs_sha256": RET004_INPUTS_SHA256, "labels_sha256": RET004_LABELS_SHA256,
            "prompt_sha256": RET004_PROMPT_SHA256, "contract_sha256": RET004_CONTRACT_SHA256,
            "manifest_sha256": RET004_MANIFEST_SHA256,
            "retrieval_config_sha256": RET004_CONFIG_SHA256,
            "provider": RET004_PROVIDER, "model": RET004_MODEL,
            "conditions": RET004_CONDITIONS, "max_batch_http": RET004_MAX_HTTP,
            "enable_cad_pipeline": True,
        }
        bad = [k for k, v in expected.items() if type(getattr(self, k)) is not type(v) or getattr(self, k) != v]
        for k in ("approver", "approved_at_utc", "approval_statement"):
            if type(getattr(self, k)) is not str or not getattr(self, k).strip(): bad.append(k)
        if type(self.is_test_only) is not bool: bad.append("is_test_only")
        if bad: raise ValueError("RET-004 approval mismatch: " + ", ".join(bad))


def validate_ret004_approval(auth: RET004Authorization, approval: RET004Approval) -> None:
    if type(auth) is not RET004Authorization or type(approval) is not RET004Approval:
        raise ValueError("RET-004 exact authorization and approval types are required")
    try: auth.__post_init__(); approval.__post_init__()
    except (AuthorizationScopeError, ValueError) as exc: raise ValueError("RET-004 binding invalid") from exc
    # Test-only approvals are valid for FakeTransport harness runs. The formal
    # entry point separately rejects them before preflight or credential I/O.
