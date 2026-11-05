"""The orchestrating APP-001 adapter.

Ties together request building, injectable transport, retry, strict parsing,
CAD-003 projection, schema validation, the construction gate, and staged run
records.  CAD/IR/STEP hooks are explicit interfaces that stay ``not_run`` /
``blocked_no_approved_ir_mapping`` because no frozen src-level parameter-to-IR
mapping exists in this task.

Gate enforcement (ADR-0013 / task section 3.2):
Any transport that is NOT a :class:`~src.llm.transport.MockTransport`
(e.g. a real HTTP transport) is refused before ``send()`` is called unless the
formal evaluation gate is open.  :class:`~src.llm.transport.FakeTransport` is
a :class:`~src.llm.transport.MockTransport` and may be used while the gate is
closed.  This check is unconditional and cannot be bypassed by the caller.

Credential handling (task section 3.1):
The mock-path request builders never read environment variables or credentials.
Credential injection is reserved for a future real-transport layer.

Raw response retention (task section 4.1):
Raw model responses are not stored by default (``RetentionPolicy.retain_raw=False``).
When a future authorized run enables retention, responses are written only to
the git-ignored ``work/app001-runs/`` directory, never to tracked files or
run records.  The run record always contains only sanitized metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from .contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_PROVIDER,
    FAMILY_ID,
    FORMAL_EVALUATION_ALLOWED,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)
from .cost import compute_cloud_cost
from .gate import FormalEvaluationBlockedError, require_formal_evaluation_allowed
from .parser import ParseResult, parse_response
from .projector import ProjectionResult, project_to_cad003
from .providers import (
    build_deepseek_request,
    build_ollama_request,
    decoding_parameters_snapshot,
)
from .retry import send_with_retry
from .runrecord import (
    AttemptRecord,
    RunRecord,
    StageStatus,
    stage,
    utc_now_iso,
)
from .transport import MockTransport, PreparedRequest, Transport, TransportResponse


# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionPolicy:
    """Controls whether raw model responses are persisted to disk.

    Default: ``retain_raw=False`` -- no raw content is written anywhere.
    When ``retain_raw=True`` (future authorized runs only), raw responses are
    written to ``base_dir`` (must be a git-ignored path).  The run record
    always records only the retention status and a body-length/hash, never
    the raw content itself.
    """

    retain_raw: bool = False
    base_dir: str = "work/app001-runs"

    # Returns False (disabled) by default; enabled only when
    # formal evaluation is authorized and this policy is explicitly set.
    @classmethod
    def default(cls) -> "RetentionPolicy":
        return cls(retain_raw=False)


def _retain_response(
    body: str,
    run_id: str,
    query_id: str,
    policy: RetentionPolicy,
) -> dict[str, Any]:
    """Attempt to retain a raw response body per the policy.

    Returns a metadata dict with ``retained``, ``path`` (if retained),
    ``body_length``, and ``body_sha256``.  Never writes content to tracked
    paths, RunRecord fields, stdout, or exceptions.
    """
    body_len = len(body.encode("utf-8"))
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    if not policy.retain_raw:
        return {"retained": False, "body_length": body_len, "body_sha256": body_hash}

    # Only allow writing to the ignored work/app001-runs/ directory.
    import re

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{run_id}_{query_id}")
    rel_path = os.path.join(policy.base_dir, f"{safe_id}_raw_response.txt")
    try:
        os.makedirs(policy.base_dir, exist_ok=True)
        with open(rel_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return {"retained": True, "path": rel_path, "body_length": body_len, "body_sha256": body_hash}
    except OSError as exc:
        return {
            "retained": False,
            "retention_failed": True,
            "error": type(exc).__name__,
            "body_length": body_len,
            "body_sha256": body_hash,
        }


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


class AdapterInput:
    """The frozen input for one query under one condition.

    In addition to the query content, records SHA-256 hashes of the system
    prompt and user-message template so that the run record can identify which
    prompt was actually used, independent of the version label.
    """

    def __init__(
        self,
        *,
        query_id: str,
        natural_language_input: str,
        reference_context: str | None,
        system_prompt: str,
        user_prompt_template: str,
        condition_id: str,
    ) -> None:
        self.query_id = query_id
        self.natural_language_input = natural_language_input
        self.reference_context = reference_context
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.condition_id = condition_id

    def rendered_user_prompt(self) -> str:
        """Render the user message using the frozen template.

        The template has exactly three placeholders: ``query_id``,
        ``natural_language_input``, and ``reference_context_or_null``.
        """
        ref = self.reference_context if self.reference_context is not None else "null"
        return self.user_prompt_template.format(
            query_id=self.query_id,
            natural_language_input=self.natural_language_input,
            reference_context_or_null=ref,
        )

    def input_payload_sha256(self) -> str:
        payload = {
            "query_id": self.query_id,
            "family_id": FAMILY_ID,
            "natural_language_input": self.natural_language_input,
            "reference_context": self.reference_context,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def reference_context_sha256(self) -> str | None:
        if self.reference_context is None:
            return None
        return hashlib.sha256(self.reference_context.encode("utf-8")).hexdigest()

    def system_prompt_sha256(self) -> str:
        """SHA-256 of the system prompt (UTF-8 encoded).  Not the prompt text."""
        return hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest()

    def user_template_sha256(self) -> str:
        """SHA-256 of the user prompt template (UTF-8 encoded)."""
        return hashlib.sha256(self.user_prompt_template.encode("utf-8")).hexdigest()

    def rendered_payload_sha256(self, rendered_user: str) -> str:
        """SHA-256 of the actual rendered request payload (system + user)."""
        payload = {"system_prompt": self.system_prompt, "user_message": rendered_user}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Run-result dataclass (returned to the caller)
# ---------------------------------------------------------------------------


class AdapterRunResult:
    """The complete staged result of running one query."""

    def __init__(
        self,
        record: RunRecord,
        parse_result: ParseResult | None,
        projection: ProjectionResult | None,
        schema_result: Any | None,
    ) -> None:
        self.record = record
        self.parse_result = parse_result
        self.projection = projection
        self.schema_result = schema_result

    @property
    def ok(self) -> bool:
        return self.record.construction_ready


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class Adapter:
    """Run a query through a provider with an injected transport.

    Parameters
    ----------
    provider:
        One of ``"DeepSeek"`` or ``"Ollama"``.
    transport:
        The injectable transport.  In tests this is a :class:`FakeTransport`
        (a :class:`MockTransport`).  A real HTTP transport may only be injected
        after the formal evaluation gate is open; the adapter enforces this.
    clock, sleeper:
        Injected monotonic clock and sleeper for retry/backoff.  Tests pass
        no-op fakes so ``time.sleep`` is never called.
    schema_validator:
        The CAD-003 validation callable (lazy import by default).
    retention_policy:
        Controls raw-response persistence.  Default: disabled.
    """

    def __init__(
        self,
        *,
        provider: str,
        transport,
        clock=None,
        sleeper=None,
        schema_validator=None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        if provider not in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
            raise ValueError(f"unknown provider: {provider!r}")
        self.provider = provider
        self.transport = transport
        self.clock = clock
        self.sleeper = sleeper
        self._schema_validator = schema_validator
        self._retention_policy = retention_policy or RetentionPolicy.default()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, adapter_input: AdapterInput, *, run_id: str) -> AdapterRunResult:
        """Run one query and return a staged :class:`AdapterRunResult`.

        Gate enforcement (3.2): if the injected transport is not a
        :class:`MockTransport`, the formal evaluation gate is checked
        **before** calling ``send()``.  This is unconditional and cannot be
        bypassed by the caller.  :class:`FakeTransport` (a
        :class:`MockTransport`) is always allowed.
        """
        # --- 3.2: Gate enforcement before any transport use ---
        if not isinstance(self.transport, MockTransport):
            require_formal_evaluation_allowed("run a non-mock transport request")

        record = RunRecord(
            run_id=run_id,
            condition_id=adapter_input.condition_id,
            query_id=adapter_input.query_id,
            timestamp_utc=utc_now_iso(),
            configured_provider=self.provider,
            configured_model_name=self._configured_model_name(),
            contract_version=CONTRACT_VERSION,
            prompt_version=PROMPT_VERSION,
            adapter_version=ADAPTER_VERSION,
            input_payload_sha256=adapter_input.input_payload_sha256(),
            reference_context_sha256=adapter_input.reference_context_sha256(),
            decoding_parameters=decoding_parameters_snapshot(self.provider),
            software_versions=self._software_versions(),
            formal_evaluation_allowed=FORMAL_EVALUATION_ALLOWED,
        )

        # --- 4.2: Prompt hashes ---
        rendered_user = adapter_input.rendered_user_prompt()
        record.prompt_hashes = {
            "system_prompt_sha256": adapter_input.system_prompt_sha256(),
            "user_template_sha256": adapter_input.user_template_sha256(),
            "rendered_payload_sha256": adapter_input.rendered_payload_sha256(rendered_user),
        }

        # --- Stage: model_call (transport + retry) ---
        request = self._build_request(adapter_input, rendered_user)
        response, attempts, total_elapsed_ms = send_with_retry(
            self.transport,
            request,
            clock=self.clock or _default_clock,
            sleeper=self.sleeper or _default_sleeper,
        )
        record.attempts = [
            AttemptRecord(
                attempt_number=o.attempt_number,
                timestamp_utc=utc_now_iso(),
                latency_ms=o.elapsed_ms,
                outcome=o.outcome,
                http_status=o.http_status,
                error_code=o.error_condition,
                error_stage=o.error_stage,
                error_fields=o.error_fields,
            )
            for o in attempts
        ]
        record.attempt_count = len(attempts)
        # 3.4: total_elapsed_ms is wall-clock from before first attempt to
        # after final outcome, including all backoff waits.
        record.total_elapsed_ms = total_elapsed_ms

        if response is None:
            last = attempts[-1] if attempts else None
            record.add_stage(stage("model_call", "fail", error_code=(last.error_condition if last else "no_attempt"), error_fields=(last.error_fields if last else ())))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, None, None, None)

        record.add_stage(stage("model_call", "pass"))
        self._record_runtime_identity(record, response)

        # --- 4.1: Raw response retention (default: not retained) ---
        retention_meta = _retain_response(
            response.body, run_id, adapter_input.query_id, self._retention_policy
        )
        record.raw_response_retention = retention_meta

        # --- Stage: parse ---
        parse_result = parse_response(response.body)
        if not parse_result.ok:
            record.add_stage(stage("parse", "fail", error_code=parse_result.errors[0].code if parse_result.errors else "parse_error", error_fields=parse_result.errors[0].fields if parse_result.errors else (), detail={"errors": [e.as_dict() for e in parse_result.errors]}))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, parse_result, None, None)
        record.add_stage(stage("parse", "pass"))

        # --- Stage: contract ---
        record.add_stage(stage("contract", "pass"))

        envelope = parse_result.envelope

        # --- Cloud usage / cost (DeepSeek only) ---
        if self.provider == DEEPSEEK_PROVIDER:
            self._record_cloud_usage_and_cost(record, response)

        # --- Local timing (Ollama only) ---
        if self.provider == OLLAMA_PROVIDER:
            record.local_wall_time_ms = total_elapsed_ms

        # --- Stage: projection ---
        projection = project_to_cad003(envelope.extracted_parameters)
        if not projection.ok:
            record.add_stage(stage("projection", "fail", error_code=projection.errors[0]["code"] if projection.errors else "projection_error", error_fields=projection.errors[0]["fields"] if projection.errors else (), detail={"raw_extraction": projection.raw_extraction}))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, parse_result, projection, None)
        record.add_stage(stage("projection", "pass", detail={"projected_payload": projection.projected_payload}))

        # --- Stage: schema (CAD-003 validation) ---
        schema_result = self._validate_schema(projection.projected_payload)
        schema_errors = getattr(schema_result, "errors", None) or []
        if not getattr(schema_result, "ok", False):
            error_codes = [e.code for e in schema_errors]
            error_fields = tuple(sorted({f for e in schema_errors for f in e.fields}))
            record.add_stage(stage("schema", "fail", error_code=error_codes[0] if error_codes else "schema_error", error_fields=error_fields, detail={"schema_errors": [e.as_dict() for e in schema_errors], "projected_payload": projection.projected_payload}))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, parse_result, projection, schema_result)

        record.add_stage(stage("schema", "pass", detail={"normalized": getattr(schema_result, "normalized", None), "provenance": dict(getattr(schema_result, "provenance", {}))}))

        # --- Construction gate ---
        decision_ok = envelope.decision == "answer"
        unsupported_empty = len(envelope.unsupported_requests) == 0
        schema_ok = getattr(schema_result, "ok", False)
        construction_ready = decision_ok and unsupported_empty and schema_ok
        record.construction_ready = construction_ready

        gate_errors: list[str] = []
        if not decision_ok:
            gate_errors.append(f"decision={envelope.decision!r} (expected 'answer')")
        if not unsupported_empty:
            gate_errors.append("unsupported_requests not empty")
        if not schema_ok:
            gate_errors.append("schema validation failed")
        record.add_stage(stage("construction_gate", "pass" if construction_ready else "fail", error_code=None if construction_ready else "CONSTRUCTION_GATE_BLOCKED", error_fields=() if construction_ready else ("decision", "unsupported_requests", "schema"), detail={"construction_ready": construction_ready, "gate_errors": gate_errors}))

        # --- IR / CAD / STEP hooks (not_run / blocked) ---
        record.add_stage(stage("ir", "blocked", error_code="blocked_no_approved_ir_mapping", detail={"reason": "no frozen src-level parameter->IR adapter; requires Codex hub to freeze mapping contract"}))
        record.add_stage(stage("cad", "not_run"))
        record.add_stage(stage("geometry", "not_run"))
        record.add_stage(stage("step", "not_run"))

        return AdapterRunResult(record, parse_result, projection, schema_result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _configured_model_name(self) -> str:
        if self.provider == DEEPSEEK_PROVIDER:
            from .contract import DEEPSEEK_MODEL

            return DEEPSEEK_MODEL
        from .contract import OLLAMA_MODEL

        return OLLAMA_MODEL

    def _build_request(self, adapter_input: AdapterInput, rendered_user: str | None = None) -> PreparedRequest:
        system = adapter_input.system_prompt
        user = rendered_user if rendered_user is not None else adapter_input.rendered_user_prompt()
        if self.provider == DEEPSEEK_PROVIDER:
            return build_deepseek_request(system_prompt=system, user_prompt=user)
        return build_ollama_request(system_prompt=system, user_prompt=user)

    def _record_runtime_identity(self, record: RunRecord, response: TransportResponse) -> None:
        record.runtime_returned_model = response.runtime_returned_model
        record.runtime_returned_provider = response.runtime_returned_provider
        if self.provider == OLLAMA_PROVIDER:
            from .contract import OLLAMA_DIGEST

            record.local_digest = OLLAMA_DIGEST

    def _record_cloud_usage_and_cost(self, record: RunRecord, response: TransportResponse) -> None:
        usage = response.usage or {}
        record.cloud_input_tokens = usage.get("prompt_tokens")
        record.cloud_output_tokens = usage.get("completion_tokens")
        record.cloud_total_tokens = usage.get("total_tokens")
        record.cloud_cached_input_tokens = usage.get("prompt_cache_hit_tokens")
        record.cloud_cache_miss_input_tokens = usage.get("prompt_cache_miss_tokens")
        cost = compute_cloud_cost(
            request_timestamp_utc=record.timestamp_utc,
            prompt_tokens=record.cloud_input_tokens,
            cached_input_tokens=record.cloud_cached_input_tokens,
            cache_miss_input_tokens=record.cloud_cache_miss_input_tokens,
            output_tokens=record.cloud_output_tokens,
        )
        record.cloud_cost_amount = cost.get("cost_amount")
        record.cloud_cost_currency = cost.get("cost_currency")
        record.cloud_cost_source = cost.get("cost_source")

    def _validate_schema(self, projected_payload: dict[str, Any] | None):
        validator = self._schema_validator
        if validator is None:
            from schema.set_screw_shaft_collar import validate_parameters

            validator = validate_parameters
        if projected_payload is None:
            return _empty_schema_result()
        return validator(projected_payload)

    def _finalize_no_construction(self, record: RunRecord) -> None:
        record.construction_ready = False
        if record.stage_status("construction_gate") is None:
            record.add_stage(stage("construction_gate", "fail", error_code="CONSTRUCTION_GATE_BLOCKED", error_fields=("decision", "unsupported_requests", "schema"), detail={"construction_ready": False}))
        for stage_name in ("projection", "schema", "ir", "cad", "geometry", "step"):
            if record.stage_status(stage_name) is None:
                record.add_stage(stage(stage_name, "not_run"))

    def _software_versions(self) -> dict[str, Any]:
        import platform
        import sys

        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "adapter": ADAPTER_VERSION,
            "schema_version": SCHEMA_VERSION,
        }


def _empty_schema_result():
    from schema.set_screw_shaft_collar import RuleViolation, ValidationResult

    return ValidationResult(
        ok=False,
        schema_version=SCHEMA_VERSION,
        family_id=FAMILY_ID,
        normalized=None,
        provenance={},
        errors=(RuleViolation(code="PROJECTION_EMPTY", fields=("parameters",), message="no projected payload", stage="schema"),),
    )


def _default_clock() -> float:
    import time

    return time.monotonic()


def _default_sleeper(seconds: float) -> None:
    import time

    time.sleep(seconds)
