"""Versioned, staged run-record data model for APP-001.

A run record captures every stage of a single query: model call attempts,
parsing, contract validation, CAD-003 projection, schema validation, the
construction gate, and the (default-off) IR/CAD/STEP hooks.  Each stage carries
an explicit status from :data:`STAGE_STATUSES` so a single boolean can never
hide a stage failure.

Records are plain dataclasses with JSON serialization.  No secrets, full
provider error bodies, request headers, Authorization values, or hidden
reasoning content are ever stored -- only stable error codes/stages/fields and
necessary redacted summaries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    PROMPT_VERSION,
    STAGE_STATUSES,
)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_stage_status(status: str) -> str:
    if status not in STAGE_STATUSES:
        raise ValueError(f"stage status must be one of {sorted(STAGE_STATUSES)}, got {status!r}")
    return status


@dataclass(frozen=True)
class AttemptRecord:
    """One model-call attempt within a run."""

    attempt_number: int
    timestamp_utc: str
    latency_ms: float
    outcome: str  # "success" | "transient_retryable" | "non_retryable" | "exhausted"
    http_status: int | None
    error_code: str | None
    error_stage: str | None
    error_fields: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "timestamp_utc": self.timestamp_utc,
            "latency_ms": self.latency_ms,
            "outcome": self.outcome,
            "http_status": self.http_status,
            "error_code": self.error_code,
            "error_stage": self.error_stage,
            "error_fields": list(self.error_fields),
        }


@dataclass(frozen=True)
class StageStatus:
    """The status of one named pipeline stage."""

    stage: str
    status: str  # one of STAGE_STATUSES
    error_code: str | None = None
    error_fields: tuple[str, ...] = ()
    detail: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        _validate_stage_status(self.status)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "error_code": self.error_code,
            "error_fields": list(self.error_fields),
            "detail": self.detail,
        }


@dataclass
class RunRecord:
    """The full staged record for one query under one condition."""

    # --- Identity ---
    run_id: str
    condition_id: str
    query_id: str
    timestamp_utc: str

    # --- Configured identities (what we asked for) ---
    configured_provider: str
    configured_model_name: str

    # --- Runtime identities (what the API returned) ---
    runtime_returned_provider: str | None = None
    runtime_returned_model: str | None = None
    local_digest: str | None = None

    # --- Contract / prompt versions ---
    contract_version: str = CONTRACT_VERSION
    prompt_version: str = PROMPT_VERSION
    adapter_version: str = ADAPTER_VERSION

    # --- Input hashes ---
    input_payload_sha256: str | None = None
    reference_context_sha256: str | None = None

    # --- Actual decode / runtime settings ---
    decoding_parameters: dict[str, Any] = field(default_factory=dict)
    software_versions: dict[str, Any] = field(default_factory=dict)

    # --- Attempts ---
    attempts: list[AttemptRecord] = field(default_factory=list)
    attempt_count: int = 0
    total_elapsed_ms: float = 0.0

    # --- Staged outcomes ---
    stages: list[StageStatus] = field(default_factory=list)

    # --- Cloud usage / cost (not_applicable for local) ---
    cloud_input_tokens: int | None = None
    cloud_cached_input_tokens: int | None = None
    cloud_cache_miss_input_tokens: int | None = None
    cloud_output_tokens: int | None = None
    cloud_total_tokens: int | None = None
    cloud_cost_amount: float | None = None
    cloud_cost_currency: str | None = None
    cloud_cost_source: str | None = None

    # --- Local timing (not_applicable for cloud) ---
    local_wall_time_ms: float | None = None

    # --- Overall construction gate ---
    construction_ready: bool = False

    # --- Formal evaluation gate (always false in this task) ---
    formal_evaluation_allowed: bool = False

    # --- Prompt hashes (4.2: identifies actual prompt used, not just version label) ---
    prompt_hashes: dict[str, Any] = field(default_factory=dict)

    # --- Raw response retention metadata (4.1: body never stored in record) ---
    raw_response_retention: dict[str, Any] = field(default_factory=dict)

    def add_stage(self, stage: StageStatus) -> None:
        self.stages.append(stage)

    def stage_status(self, stage_name: str) -> str | None:
        for stage in self.stages:
            if stage.stage == stage_name:
                return stage.status
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "condition_id": self.condition_id,
            "query_id": self.query_id,
            "timestamp_utc": self.timestamp_utc,
            "configured_provider": self.configured_provider,
            "configured_model_name": self.configured_model_name,
            "runtime_returned_provider": self.runtime_returned_provider,
            "runtime_returned_model": self.runtime_returned_model,
            "local_digest": self.local_digest,
            "contract_version": self.contract_version,
            "prompt_version": self.prompt_version,
            "adapter_version": self.adapter_version,
            "input_payload_sha256": self.input_payload_sha256,
            "reference_context_sha256": self.reference_context_sha256,
            "decoding_parameters": dict(self.decoding_parameters),
            "software_versions": dict(self.software_versions),
            "attempts": [attempt.as_dict() for attempt in self.attempts],
            "attempt_count": self.attempt_count,
            "total_elapsed_ms": self.total_elapsed_ms,
            "stages": [stage.as_dict() for stage in self.stages],
            "cloud_input_tokens": self.cloud_input_tokens,
            "cloud_cached_input_tokens": self.cloud_cached_input_tokens,
            "cloud_cache_miss_input_tokens": self.cloud_cache_miss_input_tokens,
            "cloud_output_tokens": self.cloud_output_tokens,
            "cloud_total_tokens": self.cloud_total_tokens,
            "cloud_cost_amount": self.cloud_cost_amount,
            "cloud_cost_currency": self.cloud_cost_currency,
            "cloud_cost_source": self.cloud_cost_source,
            "local_wall_time_ms": self.local_wall_time_ms,
            "construction_ready": self.construction_ready,
            "formal_evaluation_allowed": self.formal_evaluation_allowed,
            "prompt_hashes": dict(self.prompt_hashes),
            "raw_response_retention": dict(self.raw_response_retention),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, indent=indent)


def stage(stage_name: str, status: str, *, error_code: str | None = None, error_fields: tuple[str, ...] = (), detail: dict[str, Any] | None = None) -> StageStatus:
    """Convenience constructor for :class:`StageStatus`."""
    return StageStatus(stage=stage_name, status=status, error_code=error_code, error_fields=error_fields, detail=detail)
