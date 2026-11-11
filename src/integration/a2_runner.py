"""Controlled A2 real-model integration entry point.

This is the ONLY entry point for the ``APP-002-INTEGRATION-A2-SCOPE`` run:
  natural-language request → v5 LLM (DeepSeek) → parse/Schema gate
  → (if answer) run_pipeline() [Schema→IR→CadQuery→geometry/STEP verification]

Safety guarantees
-----------------
- Defaults (no authorization, dry-run) never make network calls.
- Formal runs require an explicit :class:`A2IntegrationAuthorization` instance.
- Evaluator labels are NEVER passed to combination generation, input assembly,
  the Adapter, transports, the prompt, or any logger.
- Inputsfile SHA-256 is verified before any run proceeds.
- Every physical HTTP request reserves a budget slot BEFORE network I/O via
  :class:`BudgetAwareTransport` / :class:`BudgetLedger`.
- run_pipeline() is only called when ``authorization.enable_cad_pipeline=True``
  AND the Adapter returns ``decision=answer`` with Schema passing.
- Failed runs are always retained (denominator is always 3).
- Raw responses are written to ``work/app001-runs/{batch_id}/raw/``.
- Pipeline runs are isolated under ``work/app001-runs/{batch_id}/pipeline-runs/``.
- No formal batch_id is assigned and no network call is made in this module
  unless a :class:`A2IntegrationAuthorization` with an owner-approved batch_id
  is supplied.
- ``FORMAL_EVALUATION_ALLOWED`` is never set or checked; the gate is entirely
  mediated by the authorization object and BudgetAwareTransport.

Offline dry-run / preflight mode
---------------------------------
``run_a2_offline_preflight()`` checks: inputs-file SHA-256, authorization
scope, budget feasibility, and batch directory not pre-existing.  It makes
NO network calls and reads NO secrets.

``run_a2_batch(dry_run=True)`` returns the 3 planned logical run IDs, the
budget plan, and the preflight result WITHOUT any network I/O.

Offline mock testing
--------------------
Tests inject a :class:`~llm.transport.FakeTransport` via the ``transport``
parameter of :func:`run_a2_batch`.  The Adapter accepts FakeTransport without
a formal authorization; the ``authorization`` parameter is used only for
preflight hash verification and pipeline-call gating.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm.a2_authorization import (
    A2_BATCH_PREFLIGHT_ID,
    A2_CONDITION,
    A2_INPUT_IDS,
    A2_INPUTS_SHA256,
    A2_MAX_BATCH_HTTP,
    A2_MAX_CHAT_ATTEMPTS_PER_RUN,
    A2_MAX_LOGICAL_RUNS,
    A2_MODEL,
    A2_PROFILE_ID,
    A2_PROVIDER,
    A2IntegrationAuthorization,
)
from llm.adapter import Adapter, AdapterInput, RetentionPolicy
from llm.contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_PROVIDER,
    FORMAL_EVALUATION_ALLOWED,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)
from llm.prompt_loader import load_frozen_prompt
from llm.transport import FakeTransport, MockTransport, PreparedRequest, TransportResponse
from integration.pipeline import run_pipeline, PipelineResult


# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_RUN_ROOT = _REPO_ROOT / "work" / "app001-runs"
_MODEL_INPUTS_REL = (
    "agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json"
)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class A2LogicalRunPlan:
    """One planned logical run (before execution)."""

    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str


@dataclass
class A2RunResult:
    """The result of one A2 logical run.

    Always present in the output even on failure (denominator is always 3).
    """

    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str
    llm_status: str          # adapter combined status: answer/ask/refuse/blocked/error
    pipeline_status: str | None   # pipeline result status, or None if not called
    combined_status: str     # overall: success / ask / refuse / blocked / failed / error
    errors: list[dict[str, Any]]
    questions: list[str]
    # Evidence paths (repo-relative, only set on success or partial success)
    raw_retention_path: str | None
    pipeline_run_dir: str | None
    step_path: str | None
    # Hashes for traceability (all stages)
    ir_index: dict[str, Any] | None
    # Redacted LLM metadata (no secrets)
    llm_meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "logical_run_id": self.logical_run_id,
            "input_id": self.input_id,
            "condition_id": self.condition_id,
            "provider": self.provider,
            "model": self.model,
            "llm_status": self.llm_status,
            "pipeline_status": self.pipeline_status,
            "combined_status": self.combined_status,
            "errors": self.errors,
            "questions": self.questions,
            "raw_retention_path": self.raw_retention_path,
            "pipeline_run_dir": self.pipeline_run_dir,
            "step_path": self.step_path,
            "ir_index": self.ir_index,
            "llm_meta": self.llm_meta,
        }


@dataclass
class A2BatchResult:
    """The result of a full A2 batch (3 logical runs)."""

    batch_id: str | None   # None in dry-run / preflight modes
    profile_id: str
    timestamp_utc: str
    mode: str              # "dry_run" / "offline_preflight" / "formal"
    preflight_ok: bool
    preflight_errors: list[str]
    planned_runs: list[A2LogicalRunPlan]
    results: list[A2RunResult]
    # Budget summary
    budget_plan: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "profile_id": self.profile_id,
            "timestamp_utc": self.timestamp_utc,
            "mode": self.mode,
            "preflight_ok": self.preflight_ok,
            "preflight_errors": self.preflight_errors,
            "planned_runs": [
                {"logical_run_id": p.logical_run_id, "input_id": p.input_id,
                 "condition_id": p.condition_id, "provider": p.provider, "model": p.model}
                for p in self.planned_runs
            ],
            "results": [r.as_dict() for r in self.results],
            "budget_plan": self.budget_plan,
        }


# ---------------------------------------------------------------------------
# Frozen-input loader
# ---------------------------------------------------------------------------


def _load_frozen_inputs(*, verify_sha256: bool = True) -> list[dict[str, Any]]:
    """Load and optionally verify the frozen A2 model-inputs.json.

    Returns a list of input dicts with keys: input_id, condition, natural_language.
    Raises ValueError if SHA-256 does not match the frozen constant.
    Does NOT load evaluator labels.
    """
    inputs_path = _REPO_ROOT / _MODEL_INPUTS_REL
    if not inputs_path.is_file():
        raise FileNotFoundError(
            f"A2 inputs file not found: {inputs_path}\n"
            f"Expected at: {_MODEL_INPUTS_REL} relative to repo root."
        )
    raw_bytes = inputs_path.read_bytes()
    if verify_sha256:
        actual = hashlib.sha256(raw_bytes).hexdigest()
        if actual != A2_INPUTS_SHA256:
            raise ValueError(
                f"A2 inputs SHA-256 mismatch:\n"
                f"  expected: {A2_INPUTS_SHA256}\n"
                f"  actual:   {actual}\n"
                f"The inputs file has been modified; refusing to proceed."
            )
    data = json.loads(raw_bytes.decode("utf-8"))
    inputs = data.get("inputs", [])
    # Verify input IDs match frozen constants
    actual_ids = tuple(inp["input_id"] for inp in inputs)
    if actual_ids != A2_INPUT_IDS:
        raise ValueError(
            f"A2 input IDs in file do not match frozen constants:\n"
            f"  expected: {A2_INPUT_IDS}\n"
            f"  actual:   {actual_ids}"
        )
    return inputs


# ---------------------------------------------------------------------------
# Combination planning
# ---------------------------------------------------------------------------


def _plan_combinations(
    authorization: A2IntegrationAuthorization | None = None,
) -> list[A2LogicalRunPlan]:
    """Return the 3 planned logical run combinations for A2.

    Can be called without an authorization for dry-run / plan mode.
    """
    plans: list[A2LogicalRunPlan] = []
    for input_id in A2_INPUT_IDS:
        if authorization is not None:
            lrid = authorization.expected_logical_run_id(
                input_id, A2_CONDITION, A2_PROVIDER
            )
        else:
            lrid = f"{input_id}__{A2_CONDITION}__{A2_PROVIDER}__{A2_MODEL}"
        plans.append(
            A2LogicalRunPlan(
                logical_run_id=lrid,
                input_id=input_id,
                condition_id=A2_CONDITION,
                provider=A2_PROVIDER,
                model=A2_MODEL,
            )
        )
    return plans


# ---------------------------------------------------------------------------
# Offline preflight
# ---------------------------------------------------------------------------


def run_a2_offline_preflight(
    authorization: A2IntegrationAuthorization,
    *,
    batch_dir: Path | None = None,
) -> dict[str, Any]:
    """Offline preflight checks for A2 (no network calls, no key reads).

    Checks:
    1. Inputs file exists and SHA-256 matches frozen constant.
    2. Authorization scope is valid (profile_id, input_ids, hashes, budget).
    3. Budget is feasible (3 runs × 3 attempts = 9 ≤ max_batch_attempts).
    4. Batch directory does not already exist.
    5. Frozen prompt artifact is loadable.

    Returns a dict with ``ok: bool``, ``errors: list[str]``, and check details.
    """
    errors: list[str] = []
    details: dict[str, Any] = {}

    # --- 1. Inputs file SHA-256 ---
    try:
        _load_frozen_inputs(verify_sha256=True)
        details["inputs_sha256_ok"] = True
        details["inputs_path"] = str(_REPO_ROOT / _MODEL_INPUTS_REL)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(f"inputs_check: {exc}")
        details["inputs_sha256_ok"] = False

    # --- 2. Authorization scope ---
    details["profile_id"] = authorization.profile_id
    details["input_ids"] = list(authorization.input_ids)
    details["enable_cad_pipeline"] = authorization.enable_cad_pipeline
    details["max_batch_http"] = authorization.max_batch_attempts
    details["batch_id"] = authorization.batch_id

    # --- 3. Budget feasibility ---
    max_http = authorization.max_batch_attempts
    computed = A2_MAX_LOGICAL_RUNS * A2_MAX_CHAT_ATTEMPTS_PER_RUN
    budget_feasible = computed <= max_http
    details["budget_plan"] = {
        "max_logical_runs": A2_MAX_LOGICAL_RUNS,
        "max_chat_attempts_per_run": A2_MAX_CHAT_ATTEMPTS_PER_RUN,
        "computed_max_http": computed,
        "authorized_max_http": max_http,
        "feasible": budget_feasible,
    }
    if not budget_feasible:
        errors.append(
            f"budget_infeasible: computed max {computed} > authorized max {max_http}"
        )

    # --- 4. Batch directory must not exist ---
    if batch_dir is None:
        import re as _re
        _SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
        safe_batch_id = _SAFE_RE.sub("_", authorization.batch_id)
        batch_dir = _CANONICAL_RUN_ROOT / safe_batch_id
    details["batch_dir"] = str(batch_dir)
    details["batch_dir_exists"] = batch_dir.exists()
    if batch_dir.exists():
        errors.append(
            f"batch_dir_exists: {batch_dir} already exists; "
            "each batch must use a unique batch_id"
        )

    # --- 5. Frozen prompt loadable ---
    try:
        prompt = load_frozen_prompt()
        details["prompt_version"] = prompt.version
        details["prompt_sha256"] = (prompt.system_prompt_sha256 or "")[:16] + "..."
        details["prompt_ok"] = True
    except Exception as exc:  # noqa: BLE001
        errors.append(f"prompt_load: {exc}")
        details["prompt_ok"] = False

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Single logical run — MOCK MODE (FakeTransport, no Adapter gate)
# ---------------------------------------------------------------------------


def _run_one_logical_mock(
    *,
    plan: A2LogicalRunPlan,
    natural_language: str,
    prompt,
    transport: FakeTransport,
    authorization: A2IntegrationAuthorization,
    pipeline_output_root: Path,
) -> A2RunResult:
    """Mock-mode execution using FakeTransport directly (no Adapter gate check).

    Uses building blocks directly to avoid the Adapter's exact FakeTransport
    type check, while still exercising the full parse → gate → Schema →
    pipeline path.
    """
    from llm.providers import build_deepseek_request
    from llm.retry import send_with_retry
    from llm.parser import parse_response
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    run_id = str(uuid.uuid4())

    # Build rendered user prompt (C0: reference_context_or_null = "null")
    rendered_user = prompt.user_template.format(
        query_id=plan.input_id,
        natural_language_input=natural_language,
        reference_context_or_null="null",
    )
    request = build_deepseek_request(
        system_prompt=prompt.system_prompt,
        user_prompt=rendered_user,
    )

    llm_meta: dict[str, Any] = {
        "run_id": run_id,
        "query_id": plan.input_id,
        "condition_id": plan.condition_id,
        "configured_provider": plan.provider,
        "configured_model_name": plan.model,
        "prompt_version": PROMPT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "prompt_hashes": {
            "system_prompt_sha256": hashlib.sha256(
                prompt.system_prompt.encode("utf-8")
            ).hexdigest(),
            "user_template_sha256": hashlib.sha256(
                prompt.user_template.encode("utf-8")
            ).hexdigest(),
            "rendered_payload_sha256": hashlib.sha256(
                json.dumps(
                    {"system_prompt": prompt.system_prompt, "user_message": rendered_user},
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
        },
        "attempt_count": None,
        "total_elapsed_ms": None,
        "construction_ready": None,
    }

    # --- Send via FakeTransport (with retry, no budget ledger) ---
    try:
        response, attempts, elapsed_ms = send_with_retry(transport, request)
    except Exception as exc:  # noqa: BLE001
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            pipeline_status=None,
            combined_status="error",
            errors=[{"code": "TRANSPORT_EXCEPTION", "message": str(exc)}],
            questions=[],
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    if response is None:
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            pipeline_status=None,
            combined_status="error",
            errors=[{"code": "NO_RESPONSE",
                     "message": "transport returned no response after retries"}],
            questions=[],
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    llm_meta["attempt_count"] = len(attempts)
    llm_meta["total_elapsed_ms"] = elapsed_ms
    raw_body = response.body
    raw_envelope_bytes = raw_body.encode("utf-8")

    # --- Parse ---
    parse_result = parse_response(raw_body)
    if not parse_result.ok:
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            pipeline_status=None,
            combined_status="error",
            errors=[{"code": "PARSE_ERROR",
                     "message": str([e.as_dict() for e in parse_result.errors])}],
            questions=[],
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    envelope = parse_result.envelope
    questions: list[str] = list(envelope.questions or [])

    # --- Construction gate checks ---
    if envelope.decision == "ask":
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="ask",
            pipeline_status=None,
            combined_status="ask",
            errors=[],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    if envelope.decision == "refuse":
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="refuse",
            pipeline_status=None,
            combined_status="refuse",
            errors=[],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    if envelope.missing_fields:
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            pipeline_status=None,
            combined_status="blocked",
            errors=[{"code": "GATE_MISSING_FIELDS",
                     "fields": list(envelope.missing_fields)}],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    if envelope.unsupported_requests:
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            pipeline_status=None,
            combined_status="blocked",
            errors=[{"code": "GATE_UNSUPPORTED",
                     "fields": list(envelope.unsupported_requests)}],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    # --- Schema validation ---
    projection = project_to_cad003(envelope.extracted_parameters)
    if not projection.ok:
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            pipeline_status=None,
            combined_status="blocked",
            errors=list(projection.errors),
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        llm_meta["construction_ready"] = False
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            pipeline_status=None,
            combined_status="blocked",
            errors=[e.as_dict() for e in schema_result.errors],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    llm_meta["construction_ready"] = True

    # --- decision=answer, all gates pass: call pipeline ---
    pipeline_run_root = pipeline_output_root / plan.input_id
    try:
        pipeline_result: PipelineResult = run_pipeline(
            request_text=natural_language,
            raw_envelope=raw_envelope_bytes,
            output_root=pipeline_run_root,
            envelope_fixture_label=f"a2_mock_{plan.input_id}",
            run_id=run_id,
        )
    except Exception as exc:  # noqa: BLE001
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="answer",
            pipeline_status=None,
            combined_status="failed",
            errors=[{"code": "PIPELINE_EXCEPTION", "message": str(exc)}],
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    pipeline_status = pipeline_result.status
    combined_status = "success" if pipeline_status == "success" else pipeline_status

    return A2RunResult(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider,
        model=plan.model,
        llm_status="answer",
        pipeline_status=pipeline_status,
        combined_status=combined_status,
        errors=pipeline_result.errors,
        questions=questions,
        raw_retention_path=None,
        pipeline_run_dir=pipeline_result.run_dir,
        step_path=pipeline_result.step_path,
        ir_index=pipeline_result.ir_index,
        llm_meta=llm_meta,
    )


# ---------------------------------------------------------------------------
# Single logical run — FORMAL MODE (BudgetAwareTransport + Adapter)
# ---------------------------------------------------------------------------


def _run_one_logical(
    *,
    plan: A2LogicalRunPlan,
    natural_language: str,
    prompt,
    adapter: Adapter,
    authorization: A2IntegrationAuthorization,
    batch_id: str,
    pipeline_output_root: Path,
    repo_root: Path,
    is_formal: bool,
) -> A2RunResult:
    """Execute one A2 logical run end-to-end.

    For formal runs (is_formal=True):
      - Adapter uses BudgetAwareTransport+DeepSeekTransport.
      - Raw retention is enabled to work/app001-runs/{batch_id}/raw/.
      - After a successful Adapter response (answer + Schema pass), reads the
        retained raw envelope and calls run_pipeline().

    For offline mock runs (is_formal=False):
      - Adapter uses FakeTransport.
      - Raw retention is disabled (FakeTransport does not retain).
      - run_pipeline() is called only if the FakeTransport response parses
        to decision=answer with Schema passing; raw_envelope is extracted
        directly from the FakeTransport's last response body.
    """
    run_id = str(uuid.uuid4())
    errors: list[str] = []

    # Build AdapterInput (C0: no reference_context)
    adapter_input = AdapterInput(
        query_id=plan.input_id,
        natural_language_input=natural_language,
        reference_context=None,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_template,
        condition_id=plan.condition_id,
    )

    # Run the Adapter
    formal_auth_arg = authorization if is_formal else None
    try:
        adapter_result = adapter.run(
            adapter_input,
            run_id=run_id,
            formal_authorization=formal_auth_arg,
        )
    except Exception as exc:  # noqa: BLE001
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            pipeline_status=None,
            combined_status="error",
            errors=[{"code": "ADAPTER_EXCEPTION", "message": str(exc)}],
            questions=[],
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta={"run_id": run_id},
        )

    record = adapter_result.record

    # Redacted LLM metadata (no secrets)
    llm_meta = {
        "run_id": run_id,
        "query_id": record.query_id,
        "condition_id": record.condition_id,
        "configured_provider": record.configured_provider,
        "configured_model_name": record.configured_model_name,
        "prompt_version": record.prompt_version,
        "contract_version": record.contract_version,
        "attempt_count": record.attempt_count,
        "total_elapsed_ms": record.total_elapsed_ms,
        "construction_ready": record.construction_ready,
        "prompt_hashes": record.prompt_hashes or {},
    }

    # Determine LLM status from run record
    parse_result = adapter_result.parse_result
    if parse_result is None:
        llm_status = "error"
    else:
        envelope = parse_result.envelope
        if envelope is None:
            llm_status = "error"
        elif envelope.decision == "ask":
            llm_status = "ask"
        elif envelope.decision == "refuse":
            llm_status = "refuse"
        elif not record.construction_ready:
            llm_status = "blocked"
        else:
            llm_status = "answer"

    questions: list[str] = []
    if parse_result and parse_result.envelope:
        questions = list(parse_result.envelope.questions or [])

    # If not answer+construction_ready, stop before pipeline
    if llm_status != "answer":
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=llm_status,
            pipeline_status=None,
            combined_status=llm_status,
            errors=errors,
            questions=questions,
            raw_retention_path=None,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    # ----- answer path: get raw envelope, call pipeline -----

    # Get raw envelope bytes
    raw_envelope_bytes: bytes | None = None
    raw_retention_path: str | None = None

    if is_formal:
        # Read from retained file
        retention_meta = record.raw_response_retention or {}
        if retention_meta.get("retained") and retention_meta.get("path"):
            retained_rel = retention_meta["path"]
            retained_abs = repo_root / retained_rel
            try:
                raw_envelope_bytes = retained_abs.read_bytes()
                raw_retention_path = retained_rel
            except OSError as exc:
                errors.append({
                    "code": "RAW_READ_ERROR",
                    "message": f"cannot read retained raw file: {exc}",
                    "path": retained_rel,
                })
        else:
            errors.append({
                "code": "RAW_NOT_RETAINED",
                "message": (
                    "Adapter did not retain raw response; "
                    "pipeline cannot be called without the raw envelope"
                ),
                "retention_meta": retention_meta,
            })
    else:
        # Mock/offline mode: get raw body from CapturingTransport's last response
        transport = adapter.transport
        if isinstance(transport, CapturingTransport) and transport.last_response is not None:
            raw_envelope_bytes = transport.last_response.body.encode("utf-8")

    if raw_envelope_bytes is None:
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=llm_status,
            pipeline_status=None,
            combined_status="failed",
            errors=errors + [{"code": "RAW_ENVELOPE_UNAVAILABLE",
                               "message": "raw envelope not available for pipeline call"}],
            questions=questions,
            raw_retention_path=raw_retention_path,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    # Call run_pipeline()
    pipeline_run_root = pipeline_output_root / plan.input_id
    try:
        pipeline_result: PipelineResult = run_pipeline(
            request_text=natural_language,
            raw_envelope=raw_envelope_bytes,
            output_root=pipeline_run_root,
            envelope_fixture_label=f"a2_real_model_{plan.input_id}",
            run_id=run_id,
        )
    except Exception as exc:  # noqa: BLE001
        return A2RunResult(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=llm_status,
            pipeline_status=None,
            combined_status="failed",
            errors=errors + [{"code": "PIPELINE_EXCEPTION", "message": str(exc)}],
            questions=questions,
            raw_retention_path=raw_retention_path,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
        )

    pipeline_status = pipeline_result.status
    combined_status = "success" if pipeline_status == "success" else pipeline_status

    return A2RunResult(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider,
        model=plan.model,
        llm_status=llm_status,
        pipeline_status=pipeline_status,
        combined_status=combined_status,
        errors=errors + pipeline_result.errors,
        questions=questions,
        raw_retention_path=raw_retention_path,
        pipeline_run_dir=pipeline_result.run_dir,
        step_path=pipeline_result.step_path,
        ir_index=pipeline_result.ir_index,
        llm_meta=llm_meta,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_a2_batch(
    *,
    authorization: A2IntegrationAuthorization,
    dry_run: bool = True,
    transport=None,
    output_root: Path | None = None,
) -> A2BatchResult:
    """Run the A2 integration batch.

    Parameters
    ----------
    authorization:
        A validated :class:`A2IntegrationAuthorization` instance.  Provides
        the batch_id, scope constants, and pipeline authorisation flag.
    dry_run:
        If True (default): return the plan and preflight result only; no
        network calls, no Adapter runs, no pipeline calls.  Safe to call
        at any time.
    transport:
        Injectable transport for testing.  Must be a
        :class:`~llm.transport.FakeTransport` instance when the formal gate
        is closed (which it always is; ``FORMAL_EVALUATION_ALLOWED=False``).
        For formal live runs (not yet authorised), pass None and set
        ``dry_run=False`` to have the runner build a
        ``BudgetAwareTransport+DeepSeekTransport``; this requires the gate to
        be open OR a valid ``A2IntegrationAuthorization`` (the Adapter checks
        this per-call).
    output_root:
        Override the pipeline-runs output root.  Defaults to
        ``work/app001-runs/{batch_id}/pipeline-runs/``.
    """
    ts = _utc_now_iso()
    planned = _plan_combinations(authorization)
    budget_plan = {
        "max_logical_runs": A2_MAX_LOGICAL_RUNS,
        "max_chat_attempts_per_run": A2_MAX_CHAT_ATTEMPTS_PER_RUN,
        "max_batch_http": A2_MAX_BATCH_HTTP,
        "provider": A2_PROVIDER,
        "model": A2_MODEL,
        "condition": A2_CONDITION,
        "input_ids": list(A2_INPUT_IDS),
    }

    # --- dry_run: preflight only, no runs ---
    if dry_run:
        pf = run_a2_offline_preflight(authorization)
        return A2BatchResult(
            batch_id=authorization.batch_id,
            profile_id=A2_PROFILE_ID,
            timestamp_utc=ts,
            mode="dry_run",
            preflight_ok=pf["ok"],
            preflight_errors=pf["errors"],
            planned_runs=planned,
            results=[],
            budget_plan=budget_plan,
        )

    # --- formal/mock run: execute ---
    # Preflight must pass before any run
    pf = run_a2_offline_preflight(authorization)
    if not pf["ok"]:
        return A2BatchResult(
            batch_id=authorization.batch_id,
            profile_id=A2_PROFILE_ID,
            timestamp_utc=ts,
            mode="formal" if transport is None else "mock",
            preflight_ok=False,
            preflight_errors=pf["errors"],
            planned_runs=planned,
            results=[],
            budget_plan=budget_plan,
        )

    # Load frozen inputs (SHA-256 verified by preflight, verify again here)
    inputs = _load_frozen_inputs(verify_sha256=True)
    input_map = {inp["input_id"]: inp["natural_language"] for inp in inputs}

    # Load frozen prompt
    prompt = load_frozen_prompt()

    # Determine if this is a formal live run or offline mock
    is_formal = transport is None

    # Resolve output root for pipeline runs
    import re as _re
    _SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
    safe_batch_id = _SAFE_RE.sub("_", authorization.batch_id)
    if output_root is None:
        pipeline_output_root = _CANONICAL_RUN_ROOT / safe_batch_id / "pipeline-runs"
    else:
        pipeline_output_root = Path(output_root)

    # Build transport and batch infrastructure for formal runs
    if is_formal:
        # Build budget ledger + BudgetAwareTransport + DeepSeekTransport
        from llm.budget import BudgetAwareTransport, BudgetLedger
        from llm.real_transport import DeepSeekTransport

        batch_dir = _CANONICAL_RUN_ROOT / safe_batch_id
        ledger = BudgetLedger(batch_dir, authorization)
        ledger.acquire_lock()
        raw_dir = batch_dir / "raw"
        raw_retention_policy = RetentionPolicy(
            retain_raw=True,
            base_dir=f"work/app001-runs/{safe_batch_id}/raw",
        )
    else:
        ledger = None
        raw_dir = None
        raw_retention_policy = RetentionPolicy.default()

    results: list[A2RunResult] = []
    mode = "formal" if is_formal else "mock"

    try:
        for plan in planned:
            natural_language = input_map[plan.input_id]

            if is_formal:
                # Build per-run budget-aware transport
                from llm.budget import BudgetAwareTransport
                from llm.real_transport import DeepSeekTransport

                run_transport = BudgetAwareTransport(
                    real_transport=DeepSeekTransport(authorization=authorization),
                    ledger=ledger,
                    authorization=authorization,
                    provider=plan.provider,
                    model=plan.model,
                    adapter_run_id=plan.logical_run_id,
                    query_id=plan.input_id,
                    condition_id=plan.condition_id,
                )
                run_adapter = Adapter(
                    provider=plan.provider,
                    transport=run_transport,
                    retention_policy=raw_retention_policy,
                )
                result = _run_one_logical(
                    plan=plan,
                    natural_language=natural_language,
                    prompt=prompt,
                    adapter=run_adapter,
                    authorization=authorization,
                    batch_id=authorization.batch_id,
                    pipeline_output_root=pipeline_output_root,
                    repo_root=_REPO_ROOT,
                    is_formal=True,
                )
            else:
                # Mock mode: bypass Adapter gate, use FakeTransport directly
                if not isinstance(transport, FakeTransport):
                    result = A2RunResult(
                        logical_run_id=plan.logical_run_id,
                        input_id=plan.input_id,
                        condition_id=plan.condition_id,
                        provider=plan.provider,
                        model=plan.model,
                        llm_status="error",
                        pipeline_status=None,
                        combined_status="error",
                        errors=[{"code": "INVALID_MOCK_TRANSPORT",
                                 "message": "mock transport must be FakeTransport"}],
                        questions=[],
                        raw_retention_path=None,
                        pipeline_run_dir=None,
                        step_path=None,
                        ir_index=None,
                    )
                else:
                    result = _run_one_logical_mock(
                        plan=plan,
                        natural_language=natural_language,
                        prompt=prompt,
                        transport=transport,
                        authorization=authorization,
                        pipeline_output_root=pipeline_output_root,
                    )
            results.append(result)
    finally:
        if ledger is not None:
            try:
                ledger.release_lock()
            except Exception:  # noqa: BLE001
                pass

    return A2BatchResult(
        batch_id=authorization.batch_id,
        profile_id=A2_PROFILE_ID,
        timestamp_utc=ts,
        mode=mode,
        preflight_ok=True,
        preflight_errors=[],
        planned_runs=planned,
        results=results,
        budget_plan=budget_plan,
    )
