"""Exact, fail-closed authorization profile for ADR-0019 held-out evaluation.

This profile is separate from ``authorize_phase1_run``. Its factory binds a
single batch to the frozen three-query inputs, evaluator-label artifact,
production v5 protocol, and the 12-run request budget. Constructing this
object does not grant user approval or perform network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .authorization import FormalRunAuthorization, AuthorizationScopeError
from .contract import (
    CONTRACT_VERSION, DEEPSEEK_MODEL, DEEPSEEK_PROVIDER, OLLAMA_MODEL,
    OLLAMA_PROVIDER, PROMPT_VERSION,
)

HELDOUT_PROFILE_ID: Final = "app001-heldout-v5-retrieval.v1"
HELDOUT_SAMPLE_SET: Final = "app001-heldout-v5-v1"
HELDOUT_QUERY_IDS: Final = ("APP001-HO-01", "APP001-HO-02", "APP001-HO-03")
HELDOUT_INPUTS_SHA256: Final = "c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6"
HELDOUT_LABELS_SHA256: Final = "bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a"
HELDOUT_MAX_LOGICAL_RUNS: Final = 12
HELDOUT_MAX_CHAT_ATTEMPTS: Final = 36
HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN: Final = 3
HELDOUT_MAX_IDENTITY_ATTEMPTS: Final = 20
HELDOUT_MAX_BATCH_HTTP: Final = 44
HELDOUT_PROVIDER_HTTP_CAPS: Final = {
    DEEPSEEK_PROVIDER: 18,
    OLLAMA_PROVIDER: 26,
}
HELDOUT_CHAT_PROVIDER_CAPS: Final = {
    DEEPSEEK_PROVIDER: 18,
    OLLAMA_PROVIDER: 18,
}
HELDOUT_IDENTITY_BUCKET_CAPS: Final = {
    "preflight:/api/version": 1,
    "preflight:/api/tags": 1,
    "runtime:/api/tags": 18,
}
HELDOUT_MAX_RUNTIME_IDENTITY_PER_RUN: Final = 3
HELDOUT_BATCH_PREFLIGHT_ID: Final = "__heldout_batch_preflight__"


@dataclass(frozen=True)
class HeldoutRunAuthorization(FormalRunAuthorization):
    """ADR-0019 authorization-compatible object with immutable artifact pins."""

    profile_id: str
    query_ids: tuple[str, ...]
    inputs_sha256: str
    evaluator_labels_sha256: str
    max_chat_attempts: int
    max_identity_attempts: int

    def __post_init__(self) -> None:
        expected = {
            "profile_id": HELDOUT_PROFILE_ID,
            "sample_set": HELDOUT_SAMPLE_SET,
            "conditions": frozenset({"C0", "C1"}),
            "providers": frozenset({DEEPSEEK_PROVIDER, OLLAMA_PROVIDER}),
            "models": frozenset({DEEPSEEK_MODEL, OLLAMA_MODEL}),
            "max_logical_runs": HELDOUT_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN,
            "max_batch_attempts": HELDOUT_MAX_BATCH_HTTP,
            "max_provider_attempts": HELDOUT_PROVIDER_HTTP_CAPS[OLLAMA_PROVIDER],
            "ir_cad_geometry_step_disabled": True,
            "query_ids": HELDOUT_QUERY_IDS,
            "inputs_sha256": HELDOUT_INPUTS_SHA256,
            "evaluator_labels_sha256": HELDOUT_LABELS_SHA256,
            "max_chat_attempts": HELDOUT_MAX_CHAT_ATTEMPTS,
            "max_identity_attempts": HELDOUT_MAX_IDENTITY_ATTEMPTS,
        }
        mismatches = [
            f"{name} mismatch: expected {value!r}, got {getattr(self, name)!r}"
            for name, value in expected.items()
            if getattr(self, name) != value
        ]
        if self.protocol_versions != frozenset({CONTRACT_VERSION, PROMPT_VERSION}):
            mismatches.append("protocol_versions do not match frozen v5/IO contract")
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            mismatches.append("batch_id must be a non-empty string")
        if mismatches:
            raise AuthorizationScopeError(
                "held-out authorization scope mismatch: " + "; ".join(mismatches)
            )

    @property
    def identity_bucket_caps(self) -> dict[str, int]:
        return dict(HELDOUT_IDENTITY_BUCKET_CAPS)

    @property
    def max_runtime_identity_per_run(self) -> int:
        return HELDOUT_MAX_RUNTIME_IDENTITY_PER_RUN

    def max_provider_attempts_for(self, provider: str) -> int:
        try:
            return HELDOUT_PROVIDER_HTTP_CAPS[provider]
        except KeyError as exc:
            raise AuthorizationScopeError(f"provider {provider!r} is not authorized") from exc

    def max_chat_attempts_for(self, provider: str) -> int:
        try:
            return HELDOUT_CHAT_PROVIDER_CAPS[provider]
        except KeyError as exc:
            raise AuthorizationScopeError(f"provider {provider!r} is not authorized") from exc

    def identity_bucket(self, logical_run_id: str, endpoint: str) -> str:
        """Validate and name an allowed batch-preflight or runtime identity call."""
        if logical_run_id == HELDOUT_BATCH_PREFLIGHT_ID:
            if endpoint not in {"/api/version", "/api/tags"}:
                raise AuthorizationScopeError("preflight identity endpoint is outside scope")
            return f"preflight:{endpoint}"
        if endpoint != "/api/tags" or not self.allows_logical_run(logical_run_id, OLLAMA_PROVIDER):
            raise AuthorizationScopeError("runtime identity request is outside held-out scope")
        return "runtime:/api/tags"

    def expected_logical_run_id(self, query_id: str, condition: str, provider: str) -> str:
        model = {
            DEEPSEEK_PROVIDER: DEEPSEEK_MODEL,
            OLLAMA_PROVIDER: OLLAMA_MODEL,
        }.get(provider)
        if query_id not in self.query_ids or condition not in self.conditions or model is None:
            raise AuthorizationScopeError("query/condition/provider is outside held-out scope")
        return f"{query_id}__{condition}__{provider}__{model}"

    def allows_logical_run(self, logical_run_id: str, provider: str) -> bool:
        return any(
            logical_run_id == self.expected_logical_run_id(query, condition, provider)
            for query in self.query_ids
            for condition in sorted(self.conditions)
        )

    def scope_summary(self) -> dict:
        summary = super().scope_summary()
        summary.update({
            "profile_id": self.profile_id,
            "query_ids": list(self.query_ids),
            "inputs_sha256": self.inputs_sha256,
            "evaluator_labels_sha256": self.evaluator_labels_sha256,
            "max_chat_attempts": HELDOUT_MAX_CHAT_ATTEMPTS,
            "max_identity_attempts": self.max_identity_attempts,
            "provider_http_caps": dict(sorted(HELDOUT_PROVIDER_HTTP_CAPS.items())),
            "chat_provider_caps": dict(sorted(HELDOUT_CHAT_PROVIDER_CAPS.items())),
            "identity_bucket_caps": dict(sorted(HELDOUT_IDENTITY_BUCKET_CAPS.items())),
            "max_runtime_identity_per_run": HELDOUT_MAX_RUNTIME_IDENTITY_PER_RUN,
        })
        return summary


def authorize_heldout_v5_run(*, batch_id: str) -> HeldoutRunAuthorization:
    """Construct the fixed ADR-0019 profile for a caller-supplied batch ID."""
    return HeldoutRunAuthorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=HELDOUT_SAMPLE_SET,
        conditions=frozenset({"C0", "C1"}),
        providers=frozenset({DEEPSEEK_PROVIDER, OLLAMA_PROVIDER}),
        models=frozenset({DEEPSEEK_MODEL, OLLAMA_MODEL}),
        max_logical_runs=HELDOUT_MAX_LOGICAL_RUNS,
        max_attempts_per_run=HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN,
        max_batch_attempts=HELDOUT_MAX_BATCH_HTTP,
        max_provider_attempts=HELDOUT_PROVIDER_HTTP_CAPS[OLLAMA_PROVIDER],
        ir_cad_geometry_step_disabled=True,
        batch_id=batch_id,
        profile_id=HELDOUT_PROFILE_ID,
        query_ids=HELDOUT_QUERY_IDS,
        inputs_sha256=HELDOUT_INPUTS_SHA256,
        evaluator_labels_sha256=HELDOUT_LABELS_SHA256,
        max_chat_attempts=HELDOUT_MAX_CHAT_ATTEMPTS,
        max_identity_attempts=HELDOUT_MAX_IDENTITY_ATTEMPTS,
    )
