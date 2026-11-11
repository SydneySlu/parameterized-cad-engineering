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
import os
import re as _re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm.a2_authorization import (
    A2_BATCH_PREFLIGHT_ID,
    A2_CONDITION,
    A2_INPUT_IDS,
    A2_INPUTS_SHA256,
    A2_LABELS_SHA256,
    A2_MAX_BATCH_HTTP,
    A2_MAX_CHAT_ATTEMPTS_PER_RUN,
    A2_MAX_LOGICAL_RUNS,
    A2_MODEL,
    A2_PROFILE_ID,
    A2_PROVIDER,
    A2FormalApproval,
    A2IntegrationAuthorization,
    ApprovalValidationError,
    validate_formal_approval_binding,
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
from llm.prompt_loader import load_frozen_prompt, FROZEN_PROMPT_FILE_SHA256
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

_SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
_SUMMARY_SCHEMA_VERSION = "a2-batch-summary.v1"


class SummaryWriteError(RuntimeError):
    """Raised when the batch summary cannot be written atomically.

    The A2 formal run loop treats this as fail-closed: if the summary cannot
    be updated after a run, no further model requests are attempted.
    """


def _safe_filename_component(value: str) -> str:
    return _SAFE_RE.sub("_", value)


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
    # R1-CORRECTION: raw retention metadata from Adapter RunRecord
    # (retained, path, body_sha256, body_length, truncated, etc.)
    # This is the authoritative source for raw_sha256 in the summary.
    raw_retention_meta: dict[str, Any] | None = None

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
            "raw_retention_meta": self.raw_retention_meta,
        }


@dataclass
class A2BatchResult:
    """The result of a full A2 batch (3 logical runs)."""

    batch_id: str | None   # None in dry-run / preflight modes
    profile_id: str
    timestamp_utc: str
    mode: str              # "dry_run" / "offline_preflight" / "formal" / "mock"
    preflight_ok: bool
    preflight_errors: list[str]
    planned_runs: list[A2LogicalRunPlan]
    results: list[A2RunResult]
    # Budget summary
    budget_plan: dict[str, Any]
    # Path to batch_summary.json (formal runs only; None in dry-run/mock/preflight)
    summary_path: str | None = None
    # R1-CORRECTION: explicit error message when finalize() fails; None on success
    summary_finalize_error: str | None = None

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
            "summary_path": self.summary_path,
            "summary_finalize_error": self.summary_finalize_error,
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
# Batch summary writer (R1 — formal run evidence persistence)
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: dict[str, Any], batch_dir: Path) -> None:
    """Write ``data`` as JSON to ``path`` via a temp file + atomic os.replace.

    Path containment:  resolves both ``path`` and ``batch_dir`` and verifies
    that ``path`` stays inside ``batch_dir``.  Rejects path traversal and
    symlinks that escape the batch directory.

    Raises :class:`SummaryWriteError` on any failure.
    """
    try:
        canonical_batch = batch_dir.resolve()
    except OSError:
        canonical_batch = batch_dir.absolute()

    try:
        canonical_target = path.resolve()
    except OSError:
        canonical_target = path.absolute()

    try:
        canonical_target.relative_to(canonical_batch)
    except ValueError:
        raise SummaryWriteError(
            f"summary target {path} resolves outside batch_dir {batch_dir}; "
            "refusing to write evidence outside the canonical batch directory"
        )

    tmp_path = path.with_suffix(".json.tmp")
    try:
        canonical_tmp = tmp_path.resolve()
    except OSError:
        canonical_tmp = tmp_path.absolute()
    try:
        canonical_tmp.relative_to(canonical_batch)
    except ValueError:
        raise SummaryWriteError(
            f"tmp path {tmp_path} resolves outside batch_dir {batch_dir}"
        )

    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(str(tmp_path), str(path))
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise SummaryWriteError(
            f"failed to write summary to {path}: {exc}"
        ) from exc


def _build_initial_summary(
    authorization: A2IntegrationAuthorization,
    approval: A2FormalApproval,
    planned: list[A2LogicalRunPlan],
    prompt: Any,
    started_utc: str,
) -> dict[str, Any]:
    """Build the initial batch_summary.json content (before any HTTP requests).

    Does NOT include raw response bodies, API keys, Authorization headers,
    or evaluator labels.
    """
    return {
        "schema_version": _SUMMARY_SCHEMA_VERSION,
        "batch_id": authorization.batch_id,
        "profile_id": A2_PROFILE_ID,
        "batch_started_utc": started_utc,
        "batch_status": "running",
        "scope": {
            "protocol_versions": sorted(authorization.protocol_versions),
            "sample_set": authorization.sample_set,
            "condition": A2_CONDITION,
            "provider": A2_PROVIDER,
            "model": A2_MODEL,
            "max_batch_http": A2_MAX_BATCH_HTTP,
            "max_logical_runs": A2_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": A2_MAX_CHAT_ATTEMPTS_PER_RUN,
            "enable_cad_pipeline": authorization.enable_cad_pipeline,
        },
        "artifact_hashes": {
            "inputs_sha256": A2_INPUTS_SHA256,
            "evaluator_labels_sha256": A2_LABELS_SHA256,
            "prompt_version": PROMPT_VERSION,
            "prompt_file_sha256": FROZEN_PROMPT_FILE_SHA256,
            "contract_version": CONTRACT_VERSION,
        },
        "approval": approval.as_audit_dict(),
        "planned_runs": [p.logical_run_id for p in planned],
        "runs": {
            p.logical_run_id: {"status": "pending"}
            for p in planned
        },
    }


class _SummaryWriter:
    """Atomic batch summary writer for formal A2 runs.

    Usage::

        writer = _SummaryWriter(batch_dir, initial_data)
        writer.write_initial()         # fail-closed; call before BudgetLedger
        for run in runs:
            result = execute_run(run)
            writer.update_run(result)  # fail-closed; blocks further runs on failure

    The summary is written to ``batch_dir/batch_summary.json`` via a temp-file
    + ``os.replace`` for atomicity.  All writes are path-safe: the target path
    is verified to stay inside ``batch_dir``.

    Raises :class:`SummaryWriteError` on any write failure.
    Does NOT store or write raw response bodies, API keys, or evaluator labels.
    """

    def __init__(self, batch_dir: Path, initial_data: dict[str, Any]) -> None:
        self._batch_dir = batch_dir
        self._summary_path = batch_dir / "batch_summary.json"
        self._data: dict[str, Any] = dict(initial_data)

    @property
    def summary_path(self) -> Path:
        return self._summary_path

    def write_initial(self) -> None:
        """Write the initial summary before any model requests.

        Raises :class:`SummaryWriteError` if the write fails.  The caller
        MUST NOT proceed with model requests if this raises.
        """
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def update_run(self, result: "A2RunResult") -> None:
        """Atomically update the summary with one run result.

        Raises :class:`SummaryWriteError` if the write fails.  The runner
        loop MUST stop further model requests if this raises.
        """
        # Build the run evidence record (no raw body content, no secrets).
        # R1-CORRECTION: raw_sha256 comes from raw_retention_meta["body_sha256"],
        # which is the SHA-256 of the actual raw response body as recorded by
        # the Adapter's RetentionPolicy.  This is distinct from
        # ir_index["envelope_sha256"] (which is recomputed inside run_pipeline()).
        raw_sha256: str | None = None
        raw_retained: bool | None = None
        if isinstance(result.raw_retention_meta, dict):
            raw_sha256 = result.raw_retention_meta.get("body_sha256")
            raw_retained = result.raw_retention_meta.get("retained")
        elif result.raw_retention_path is not None:
            # Fallback for mock mode where retention meta is not populated
            # but a path exists (should not normally happen)
            pass

        run_entry: dict[str, Any] = {
            "status": result.combined_status,
            "llm_status": result.llm_status,
            "pipeline_status": result.pipeline_status,
            "attempt_count": result.llm_meta.get("attempt_count"),
            "prompt_version": result.llm_meta.get("prompt_version"),
            "contract_version": result.llm_meta.get("contract_version"),
            "configured_provider": result.llm_meta.get("configured_provider"),
            "configured_model_name": result.llm_meta.get("configured_model_name"),
            # raw_retention_path is a repo-relative path; raw body is NOT included
            "raw_retention_path": result.raw_retention_path,
            "raw_retained": raw_retained,
            "raw_sha256": raw_sha256,
            "pipeline_run_dir": result.pipeline_run_dir,
            "ir_index": result.ir_index,
            "step_path": result.step_path,
            "errors": result.errors,
            "questions": result.questions,
        }

        # Merge into the in-memory data
        runs = self._data.setdefault("runs", {})
        runs[result.logical_run_id] = run_entry

        # Write atomically
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def finalize(self, batch_status: str = "complete") -> None:
        """Update batch_status and write the final summary.

        Raises :class:`SummaryWriteError` if the write fails.
        """
        self._data["batch_status"] = batch_status
        self._data["batch_finished_utc"] = _utc_now_iso()
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)


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
        # R1-CORRECTION: populate raw_retention_meta even for non-answer paths
        # (ask, refuse, blocked, parse error) so the summary records evidence
        # for all runs that received a model response.
        non_answer_retention_meta = None
        non_answer_retention_path = None
        if is_formal:
            rm = record.raw_response_retention or {}
            if rm:
                non_answer_retention_meta = dict(rm)
                if rm.get("retained") and rm.get("path"):
                    non_answer_retention_path = rm["path"]
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
            raw_retention_path=non_answer_retention_path,
            pipeline_run_dir=None,
            step_path=None,
            ir_index=None,
            llm_meta=llm_meta,
            raw_retention_meta=non_answer_retention_meta,
        )

    # ----- answer path: get raw envelope, call pipeline -----

    # Get raw envelope bytes
    raw_envelope_bytes: bytes | None = None
    raw_retention_path: str | None = None

    # R1-CORRECTION-2: capture retention meta once for all answer-path returns
    answer_retention_meta: dict[str, Any] | None = None
    if is_formal:
        rm = record.raw_response_retention or {}
        if rm:
            answer_retention_meta = dict(rm)

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
            raw_retention_meta=answer_retention_meta,
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
            raw_retention_meta=answer_retention_meta,
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
        raw_retention_meta=answer_retention_meta,
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
    approval: "A2FormalApproval | None" = None,
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
        at any time.  Does NOT require an ``approval`` credential.
    transport:
        Injectable transport for testing.  Must be a
        :class:`~llm.transport.FakeTransport` instance when the formal gate
        is closed (which it always is; ``FORMAL_EVALUATION_ALLOWED=False``).
        For formal live runs (not yet authorised), pass None and set
        ``dry_run=False``.  Mock mode (non-None transport) does NOT require
        an ``approval`` credential.
    output_root:
        Override the pipeline-runs output root.  Defaults to
        ``work/app001-runs/{batch_id}/pipeline-runs/``.
    approval:
        Required for formal live runs (``dry_run=False`` and ``transport is None``).
        Must be an :class:`A2FormalApproval` instance whose ``batch_id``
        matches ``authorization.batch_id``.  Validated BEFORE any directory
        creation, BudgetLedger initialization, Transport construction, or
        network I/O.  Not required for dry-run or mock modes.
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

    is_formal = transport is None

    # --- Approval gate: required for formal runs; must happen before any infra ---
    if is_formal:
        if approval is None:
            raise ApprovalValidationError(
                "formal A2 run requires an A2FormalApproval credential; "
                "received None.  Obtain owner approval and pass it as "
                "approval=<A2FormalApproval> before executing a live run."
            )
        # Raises ApprovalValidationError if batch_id mismatch or invalid type
        validate_formal_approval_binding(authorization, approval)

    # --- Offline preflight must pass before any infra creation ---
    pf = run_a2_offline_preflight(authorization)
    if not pf["ok"]:
        return A2BatchResult(
            batch_id=authorization.batch_id,
            profile_id=A2_PROFILE_ID,
            timestamp_utc=ts,
            mode="formal" if is_formal else "mock",
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

    # Resolve safe batch ID and output root
    safe_batch_id = _safe_filename_component(authorization.batch_id)
    if output_root is None:
        pipeline_output_root = _CANONICAL_RUN_ROOT / safe_batch_id / "pipeline-runs"
    else:
        pipeline_output_root = Path(output_root)

    # --- Build formal batch infrastructure (after approval validated) ---
    if is_formal:
        from llm.budget import BudgetAwareTransport, BudgetLedger
        from llm.real_transport import DeepSeekTransport

        batch_dir = _CANONICAL_RUN_ROOT / safe_batch_id
        # Create batch directory (fail if already exists)
        try:
            batch_dir.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            raise SummaryWriteError(
                f"batch directory already exists: {batch_dir}; "
                "each batch must use a unique batch_id"
            )

        # Write initial batch summary BEFORE BudgetLedger / Transport
        initial_data = _build_initial_summary(
            authorization, approval, planned, prompt, ts
        )
        writer = _SummaryWriter(batch_dir, initial_data)
        try:
            writer.write_initial()
        except SummaryWriteError:
            # Clean up the directory if summary write fails
            try:
                batch_dir.rmdir()
            except OSError:
                pass
            raise

        # Now safe to create BudgetLedger and Transport.
        # R1-LIVE-FIX: If BudgetLedger or acquire_lock fails after write_initial,
        # the batch_summary.json is left with batch_status="running".
        # Wrap in try/except to finalize as "aborted" and re-raise.
        ledger = None
        try:
            ledger = BudgetLedger(batch_dir, authorization)
            ledger.acquire_lock()
        except Exception:
            # Attempt to mark the summary as aborted before re-raising
            try:
                writer.finalize(batch_status="aborted")
            except Exception:  # noqa: BLE001
                pass
            raise

        raw_retention_policy = RetentionPolicy(
            retain_raw=True,
            base_dir=f"work/app001-runs/{safe_batch_id}/raw",
        )
        summary_path: str | None = str(writer.summary_path)
    else:
        ledger = None
        raw_retention_policy = RetentionPolicy.default()
        writer = None
        summary_path = None

    results: list[A2RunResult] = []
    mode = "formal" if is_formal else "mock"
    summary_write_failed = False

    try:
        for plan in planned:
            natural_language = input_map[plan.input_id]

            if is_formal:
                from llm.budget import BudgetAwareTransport
                from llm.real_transport import DeepSeekTransport

                run_transport = BudgetAwareTransport(
                    DeepSeekTransport(authorization=authorization),
                    ledger=ledger,
                    authorization=authorization,
                    logical_run_id=plan.logical_run_id,
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

            # Persist run evidence atomically (formal runs only)
            if is_formal and writer is not None:
                try:
                    writer.update_run(result)
                except SummaryWriteError as exc:
                    summary_write_failed = True
                    # Mark the run with the write error and stop further runs
                    result.errors = list(result.errors) + [
                        {"code": "SUMMARY_WRITE_FAILED", "message": str(exc)}
                    ]
                    break

    finally:
        if ledger is not None:
            try:
                ledger.release_lock()
            except Exception:  # noqa: BLE001
                pass
        # Finalize summary
        if is_formal and writer is not None and not summary_write_failed:
            try:
                writer.finalize(batch_status="complete")
            except SummaryWriteError as exc:
                # R1-CORRECTION: finalize failure must be explicit, not swallowed.
                # The caller must not receive a result that looks like the batch
                # completed normally.  We record the error in the result so it
                # is visible, while still returning the per-run results that
                # were collected before the failure.
                finalize_error = str(exc)
            else:
                finalize_error = None
        else:
            finalize_error = None

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
        summary_path=summary_path,
        summary_finalize_error=finalize_error,
    )
