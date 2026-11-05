"""The orchestrating APP-001 adapter.

Ties together request building, injectable transport, retry, strict parsing,
CAD-003 projection, schema validation, the construction gate, and staged run
records.  CAD/IR/STEP hooks are explicit interfaces that stay ``not_run`` /
``blocked_no_approved_ir_mapping`` because no frozen src-level parameter-to-IR
mapping exists in this task.

This module never performs real network calls by itself.  Real transport
implementations are never imported here; the caller injects a transport
(which, in tests, is a :class:`FakeTransport`).  The formal evaluation gate is
checked at any runnable entry point.
"""

from __future__ import annotations

import hashlib
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
from .gate import require_formal_evaluation_allowed
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
from .transport import PreparedRequest, Transport, TransportResponse


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


class AdapterInput:
    """The frozen input for one query under one condition."""

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
        import json

        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def reference_context_sha256(self) -> str | None:
        if self.reference_context is None:
            return None
        return hashlib.sha256(self.reference_context.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Run-result dataclass (returned to the caller)
# ---------------------------------------------------------------------------


class AdapterRunResult:
    """The complete staged result of running one query."""

    def __init__(self, record: RunRecord, parse_result: ParseResult | None, projection: ProjectionResult | None, schema_result: Any | None) -> None:
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
        The injectable :class:`Transport`.  In tests this is a
        :class:`FakeTransport`; a real HTTP transport may be injected in a
        future authorized run, but is never created here.
    clock, sleeper:
        Injected monotonic clock and sleeper for retry/backoff.  Tests pass
        no-op fakes so ``time.sleep`` is never called.
    schema_validator:
        The CAD-003 validation callable.  Defaults to the real
        ``schema.set_screw_shaft_collar.validate_parameters`` (imported lazily so
        tests can import this module without the schema package on the path).
    """

    def __init__(
        self,
        *,
        provider: str,
        transport: Transport,
        clock=None,
        sleeper=None,
        schema_validator=None,
    ) -> None:
        if provider not in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
            raise ValueError(f"unknown provider: {provider!r}")
        self.provider = provider
        self.transport = transport
        self.clock = clock
        self.sleeper = sleeper
        self._schema_validator = schema_validator

    # ------------------------------------------------------------------
    # Public runnable entry point (still mock-only by default)
    # ------------------------------------------------------------------

    def run(self, adapter_input: AdapterInput, *, run_id: str, allow_real_network: bool = False) -> AdapterRunResult:
        """Run one query and return a staged :class:`AdapterRunResult`.

        ``allow_real_network`` must be True for any real-network transport to
        proceed; even then, :func:`require_formal_evaluation_allowed` is called
        first and fails closed.  With the default ``False`` and a fake
        transport, no guard trips because no real network is used.
        """
        if allow_real_network:
            require_formal_evaluation_allowed("run a real provider request")
        # If allow_real_network is False, we proceed only because tests inject
        # a FakeTransport.  A real transport with allow_real_network=False is
        # the caller's contract violation, not ours to enforce further.

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

        # --- Stage: model_call (transport + retry) ---
        request = self._build_request(adapter_input)
        response, attempts = send_with_retry(
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
        record.total_elapsed_ms = sum(o.elapsed_ms for o in attempts)

        if response is None:
            # Transport failed (exhausted retries or non-retryable).
            last = attempts[-1] if attempts else None
            record.add_stage(stage("model_call", "fail", error_code=(last.error_condition if last else "no_attempt"), error_fields=(last.error_fields if last else ())))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, None, None, None)

        record.add_stage(stage("model_call", "pass"))
        self._record_runtime_identity(record, response)

        # --- Stage: parse ---
        parse_result = parse_response(response.body)
        if not parse_result.ok:
            record.add_stage(stage("parse", "fail", error_code=parse_result.errors[0].code if parse_result.errors else "parse_error", error_fields=parse_result.errors[0].fields if parse_result.errors else (), detail={"errors": [e.as_dict() for e in parse_result.errors]}))
            self._finalize_no_construction(record)
            return AdapterRunResult(record, parse_result, None, None)
        record.add_stage(stage("parse", "pass"))

        # --- Stage: contract ---
        # The parser already validated the contract; record pass explicitly.
        record.add_stage(stage("contract", "pass"))

        envelope = parse_result.envelope

        # --- Cloud usage / cost (DeepSeek only) ---
        if self.provider == DEEPSEEK_PROVIDER:
            self._record_cloud_usage_and_cost(record, response)

        # --- Local timing (Ollama only) ---
        if self.provider == OLLAMA_PROVIDER:
            record.local_wall_time_ms = record.total_elapsed_ms

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
        # No frozen src-level parameter-to-IR mapping exists; record honestly.
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

    def _build_request(self, adapter_input: AdapterInput) -> PreparedRequest:
        system = adapter_input.system_prompt
        user = adapter_input.rendered_user_prompt()
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
            # Lazy import the real schema validator.
            from schema.set_screw_shaft_collar import validate_parameters

            validator = validate_parameters
        if projected_payload is None:
            return _empty_schema_result()
        return validator(projected_payload)

    def _finalize_no_construction(self, record: RunRecord) -> None:
        record.construction_ready = False
        # Explicitly record the construction gate as fail when not reached.
        if record.stage_status("construction_gate") is None:
            record.add_stage(stage("construction_gate", "fail", error_code="CONSTRUCTION_GATE_BLOCKED", error_fields=("decision", "unsupported_requests", "schema"), detail={"construction_ready": False}))
        # Any stage not yet recorded downstream of the failure is not_run.
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
    from schema.set_screw_shaft_collar import ValidationResult, RuleViolation

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
