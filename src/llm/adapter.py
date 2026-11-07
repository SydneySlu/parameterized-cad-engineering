"""The orchestrating APP-001 adapter.

Ties together request building, injectable transport, retry, strict parsing,
CAD-003 projection, schema validation, the construction gate, and staged run
records.  CAD/IR/STEP hooks are explicit interfaces that stay ``not_run`` /
``blocked_no_approved_ir_mapping`` because no frozen src-level parameter-to-IR
mapping exists in this task.

Gate enforcement (R2):
Only the exact :class:`~src.llm.transport.FakeTransport` type is allowed while
the formal evaluation gate is closed.  Any other transport -- including subclasses
of MockTransport -- is refused before ``send()`` is called.  This uses an exact
type check (``type(transport) is FakeTransport``) that cannot be bypassed by
inheritance.

Retention (R2):
Retention root is fixed to ``work/app001-runs/`` (git-ignored).  Path validation
rejects paths outside that canonical root.  Tests use an explicit test-only
dependency-injection mechanism; production callers cannot specify arbitrary paths.

Prompt artifact verification (R2 / 4.3):
:func:`verify_adapter_input` checks the actual system prompt and user template
against the frozen ``prompt-v2.md`` before any transport ``send()`` call.

Credential handling:
The mock-path request builders never read environment variables or credentials.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
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
from .prompt_loader import FrozenPromptMismatchError, verify_adapter_input
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

# The canonical git-ignored run directory (relative to repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_RUN_DIR_NAME = "work/app001-runs"
_CANONICAL_RUN_DIR = _REPO_ROOT / "work" / "app001-runs"
_MAX_RETAINED_RESPONSE_BYTES = 64 * 1024


def _resolve_canonical_path(base_dir: str | Path) -> Path:
    """Resolve ``base_dir`` to an absolute path and verify it is inside the
    canonical ``work/app001-runs/`` directory.

    Raises :class:`ValueError` with a stable error code on:
    - Absolute paths or relative paths that escape ``work/app001-runs/``
    - Path traversal (``..``)
    - Symbolic links that resolve outside the canonical root
    """
    resolved = Path(base_dir) if Path(base_dir).is_absolute() else (_REPO_ROOT / base_dir)
    try:
        resolved = resolved.resolve()
    except OSError:
        pass  # allow non-existent paths; existence is checked on write

    canonical = _CANONICAL_RUN_DIR.resolve() if _CANONICAL_RUN_DIR.exists() else _CANONICAL_RUN_DIR.absolute()
    try:
        resolved.relative_to(canonical)
    except ValueError:
        raise ValueError(
            f"RETENTION_PATH_OUTSIDE_IGNORED_DIR: base_dir {base_dir!r} resolves to "
            f"{resolved} which is outside the canonical ignored run directory "
            f"{canonical}; refusing to write raw response"
        )
    return resolved


@dataclass(frozen=True)
class RetentionPolicy:
    """Controls whether raw model responses are persisted to disk.

    Default: ``retain_raw=False`` -- no raw content is written anywhere.

    When ``retain_raw=True`` (future authorized runs only), raw responses are
    written inside ``work/app001-runs/`` (git-ignored).  The ``base_dir``
    must be a path within ``work/app001-runs/`` or it is rejected before any
    write.  There is no public parameter to specify an arbitrary directory
    outside the canonical root.

    R3-B: There is no ``_test_only`` field.  Tests that need to exercise the
    writer use the private :func:`_write_raw_to_dir` function directly with a
    test-controlled temporary directory; the production :class:`Adapter` always
    uses the fixed canonical root.
    """

    retain_raw: bool = False
    base_dir: str = _CANONICAL_RUN_DIR_NAME

    @classmethod
    def default(cls) -> "RetentionPolicy":
        return cls(retain_raw=False)

    def resolved_dir(self) -> Path:
        """Return the resolved canonical directory, raising on out-of-bounds."""
        return _resolve_canonical_path(self.base_dir)


def _write_raw_to_dir(
    write_dir: Path,
    body: str,
    run_id: str,
    query_id: str,
) -> dict[str, Any]:
    """Write a raw response body to ``write_dir``.  Private; for tests and
    the production writer.

    Returns metadata dict.  Caller is responsible for ensuring ``write_dir``
    is a safe location (canonical root or a test tempdir).
    """
    body_len = len(body.encode("utf-8"))
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{run_id}_{query_id}")
    rel_path = write_dir / f"{safe_id}_raw_response.txt"
    try:
        write_dir.mkdir(parents=True, exist_ok=True)
        # Re-check that the actual write path (after mkdir) is still inside
        # the intended directory.  This catches TOCTOU symlink replacement
        # between resolve() and the actual write, though it cannot prevent
        # all concurrent races.
        resolved_path = rel_path.resolve()
        resolved_dir = write_dir.resolve()
        try:
            resolved_path.relative_to(resolved_dir)
        except ValueError:
            return {
                "retained": False,
                "retention_failed": True,
                "error": "RETENTION_PATH_ESCAPED_AFTER_RESOLVE",
                "body_length": body_len,
                "body_sha256": body_hash,
            }
        with open(rel_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return {"retained": True, "path": str(rel_path), "body_length": body_len, "body_sha256": body_hash}
    except OSError as exc:
        return {
            "retained": False,
            "retention_failed": True,
            "error": type(exc).__name__,
            "body_length": body_len,
            "body_sha256": body_hash,
        }


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

    R3-B: The production path always uses the canonical root.  There is no
    test-only bypass flag.  Tests that need a tempdir call ``_write_raw_to_dir``
    directly.
    """
    body_bytes = body.encode("utf-8")
    body_len = len(body_bytes)
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    truncated = body_len > _MAX_RETAINED_RESPONSE_BYTES
    saved_body = body_bytes[:_MAX_RETAINED_RESPONSE_BYTES].decode("utf-8", errors="ignore") if truncated else body
    saved_len = len(saved_body.encode("utf-8"))

    if not policy.retain_raw:
        return {"retained": False, "body_length": body_len, "saved_length": 0, "body_sha256": body_hash, "truncated": truncated}

    # Resolve and validate the canonical path before writing.
    try:
        write_dir = policy.resolved_dir()
    except ValueError as exc:
        return {
            "retained": False,
            "retention_failed": True,
            "error": "RETENTION_PATH_OUTSIDE_IGNORED_DIR",
            "body_length": body_len,
            "saved_length": 0,
            "body_sha256": body_hash,
            "truncated": truncated,
        }

    meta = _write_raw_to_dir(write_dir, saved_body, run_id, query_id)
    if meta.get("retained") and meta.get("path"):
        try:
            meta["path"] = Path(meta["path"]).resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
        except (OSError, ValueError):
            # A retained file without a safe repository-relative identity is
            # treated as failed evidence; never expose an absolute path.
            meta.pop("path", None)
            meta["retained"] = False
            meta["retention_failed"] = True
            meta["error"] = "RETENTION_PATH_NOT_REPO_RELATIVE"
    meta.update({"body_length": body_len, "saved_length": saved_len, "body_sha256": body_hash, "truncated": truncated})
    return meta


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

    def run(
        self,
        adapter_input: AdapterInput,
        *,
        run_id: str,
        formal_authorization: "Any | None" = None,
    ) -> AdapterRunResult:
        """Run one query and return a staged :class:`AdapterRunResult`.

        Gate enforcement (4.1 R2 / runner extension):
        Only the exact :class:`FakeTransport` type is allowed while the
        formal evaluation gate is closed AND no narrow-scope
        :class:`FormalRunAuthorization` is provided.

        - If transport is FakeTransport: always allowed (tests, dry-run).
        - If transport is NOT FakeTransport AND a valid
          :class:`~src.llm.authorization.FormalRunAuthorization` is provided:
          allowed for the authorized scope only (ADR-0014).
        - If transport is NOT FakeTransport AND no authorization is provided:
          the gate check raises :class:`FormalEvaluationBlockedError`.

        This means the global ``FORMAL_EVALUATION_ALLOWED = False`` constant
        is NOT changed.  The authorization object is a separate, explicit,
        scope-validated path that the runner must obtain and pass in.

        Prompt verification (R3-A): the frozen prompt artifact is always loaded
        and verified against the ``adapter_input``'s system prompt and user
        template before ``send()``.  There is no parameter to skip, replace, or
        bypass this check.  Tests that need synthetic prompts must test the
        loader/verifier directly, not via ``Adapter.run()``.
        """
        # --- Gate check: FakeTransport, authorized formal run, or fail-closed ---
        from .transport import FakeTransport as _FakeTransport

        if type(self.transport) is not _FakeTransport:
            if formal_authorization is not None:
                # Formal execution must use the exact budget-aware wrapper
                # built for this authorization, provider/model, logical input,
                # and adapter run ID. A generic authorized transport is not
                # sufficient because it could bypass the durable attempt ledger.
                from .authorization import FormalRunAuthorization as _FRA
                from .budget import BudgetAwareTransport as _BAT

                expected_model = self._configured_model_name()
                if (
                    not isinstance(formal_authorization, _FRA)
                    or type(self.transport) is not _BAT
                    or not self.transport.uses_real_transport
                    or self.transport.authorization is not formal_authorization
                    or self.transport.provider != self.provider
                    or self.transport.model != expected_model
                    or not formal_authorization.provider_model_is_allowed(
                        self.provider, expected_model
                    )
                    or self.transport.adapter_run_id != run_id
                    or self.transport.query_id != adapter_input.query_id
                    or self.transport.condition_id != adapter_input.condition_id
                ):
                    require_formal_evaluation_allowed(
                        "formal run must use a runner-bound, budget-aware real transport"
                    )
            else:
                # No authorization and not FakeTransport: fail-closed.
                require_formal_evaluation_allowed("run a non-FakeTransport request")

        # --- R3-A: Verify frozen prompt artifact unconditionally before send() ---
        try:
            verify_adapter_input(adapter_input)
        except FrozenPromptMismatchError as exc:
            raise FrozenPromptMismatchError(
                f"frozen prompt verification failed; "
                "cannot proceed with mislabeled run: " + str(exc)
            ) from exc

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
                diagnostic_retention=o.diagnostic_retention or {},
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
        # R3-B: production path always uses canonical root; no test-only bypass.
        retention_meta = _retain_response(
            response.body, run_id, adapter_input.query_id, self._retention_policy,
        )
        record.raw_response_retention = retention_meta

        # --- Cloud usage / cost (DeepSeek only) ---
        # Recorded immediately after model_call succeeds, before parse, so that
        # token counts and cost are captured even when the response body fails
        # to parse (e.g. MISSING_ENVELOPE_KEY).  Without this, an early return
        # in the parse stage would leave all usage fields as None.
        if self.provider == DEEPSEEK_PROVIDER:
            self._record_cloud_usage_and_cost(record, response)

        # --- Local timing (Ollama only) ---
        # Likewise recorded before parse so wall-time is always present.
        if self.provider == OLLAMA_PROVIDER:
            record.local_wall_time_ms = total_elapsed_ms

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
            # Use actual digest from the transport's /api/show verification result,
            # not the frozen expected constant.  If not available (e.g. FakeTransport),
            # fall back to the usage field set by OllamaTransport.
            usage = response.usage or {}
            actual_digest = usage.get("local_actual_digest")
            if actual_digest:
                record.local_digest = str(actual_digest)
            else:
                # FakeTransport / tests: record the expected constant but note it's
                # not confirmed by a real /api/show call
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
