"""Controlled product live extraction entry point (APP-003-LIVE-PRODUCT).

This is the ONLY entry point for the product live smoke run:
  browser request → v5 DeepSeek (server-side) → product authorization gate
  → envelope parse + contract/schema preflight → C3 confirmation UI/API
  → explicit user confirmation → existing Schema→IR→CadQuery→geometry/STEP pipeline

Safety guarantees
-----------------
- Defaults (no authorization, dry-run) never make network calls.
- Formal runs require an explicit :class:`ProductLiveAuthorization` instance
  AND a matching non-test-only :class:`ProductLiveFormalApproval`.
- Evaluator labels are NEVER passed to combination generation, input assembly,
  the Adapter, transports, the prompt, or any logger.
- Inputs file SHA-256 is verified before any run proceeds.
- Every physical HTTP request reserves a budget slot BEFORE network I/O via
  :class:`BudgetAwareTransport` / :class:`BudgetLedger`.
- run_pipeline() is only called after:
    1. authorization.enable_cad_pipeline=True
    2. The model returns decision=answer with Schema passing
    3. The user provides explicit server-side confirmation
- P1 answer → needs_confirmation (waits for user confirm before CAD)
- P2/P3/P4 → blocked/ask (zero CAD calls, no STEP)
- Failed runs are always retained (denominator is always 4).
- Raw responses written to ``work/app001-runs/{batch_id}/raw/``.
- Pipeline runs isolated under ``work/app001-runs/{batch_id}/pipeline-runs/``.
- ``FORMAL_EVALUATION_ALLOWED`` remains False. Formal product execution is
  allowed only through its scope-validated authorization plus matching
  non-test-only approval and Adapter-bound BudgetAwareTransport.
- This does not authorize APP-001, A2, or held-out runners.

Offline dry-run / preflight mode
---------------------------------
``run_product_offline_preflight()`` checks: inputs-file SHA-256, authorization
scope, budget feasibility, batch directory not pre-existing.  Zero network
calls, zero key reads.

``run_product_batch(dry_run=True)`` returns the 4 planned logical run IDs,
budget plan, and preflight result WITHOUT any network I/O.

Offline mock testing
--------------------
Tests inject a :class:`~llm.transport.FakeTransport` via the ``transport``
parameter of :func:`run_product_batch`.  The mock path exercises the full
parse → gate → Schema → (confirmation gate) → pipeline path.

Confirmation gate
-----------------
Even when the model returns decision=answer (P1), the product runner does NOT
call run_pipeline() during the extraction phase.  The extraction result is
returned as ProductLiveRunState with status=needs_confirmation.  Only after
explicit user confirmation (via confirm_product_live_run()) does the runner
call run_pipeline() and produce a child run.
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

from llm.product_live_authorization import (
    PRODUCT_BATCH_PREFLIGHT_ID,
    PRODUCT_CONDITION,
    PRODUCT_INPUT_IDS,
    PRODUCT_INPUTS_SHA256,
    PRODUCT_LABELS_SHA256,
    PRODUCT_MAX_BATCH_HTTP,
    PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
    PRODUCT_MAX_LOGICAL_RUNS,
    PRODUCT_MODEL,
    PRODUCT_PROFILE_ID,
    PRODUCT_PROVIDER,
    PRODUCT_PROMPT_FILE_SHA256,
    ProductLiveFormalApproval,
    ProductLiveAuthorization,
    ProductApprovalValidationError,
    validate_product_formal_approval_binding,
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
    "agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json"
)

_SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
_SUMMARY_SCHEMA_VERSION = "product-live-batch-summary.v1"


def _safe_filename_component(value: str) -> str:
    return _SAFE_RE.sub("_", value)


def _to_repo_relative_path(path_str: str | None) -> str | None:
    """Convert an absolute or repo-rooted path to a repo-relative string.

    Fail-closed: returns ``None`` for *any* path that cannot be verified as
    residing inside ``_REPO_ROOT`` after canonical resolution.

    Rules:
    - ``None`` or empty string → ``None``.
    - Relative paths are resolved against ``_REPO_ROOT`` (never CWD).
    - Absolute paths are resolved canonically (symlinks followed).
    - The canonical result must be inside ``_REPO_ROOT``; otherwise ``None``.
    - ``..`` traversal that escapes the repo → ``None``.
    - Symlink that resolves outside the repo → ``None``.
    - No fallback to returning the original string unvalidated.
    - Never raises; all exceptions → ``None``.
    """
    if not path_str or not isinstance(path_str, str):
        return None
    try:
        root = _REPO_ROOT.resolve()
        # Resolve relative paths against _REPO_ROOT, NOT the CWD.
        raw = Path(path_str)
        if raw.is_absolute():
            candidate = raw.resolve()
        else:
            candidate = (root / raw).resolve()
        # Containment check: candidate must be inside root.
        candidate.relative_to(root)
        # Return POSIX-style repo-relative path (never starts with /).
        rel = candidate.relative_to(root)
        result = str(rel).replace("\\", "/")
        if result.startswith("/"):
            return None
        return result
    except (ValueError, OSError, RuntimeError, TypeError):
        return None


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_cad_runtime() -> dict[str, Any]:
    """Check that this interpreter can validate IR and run the CAD backend."""
    errors: list[str] = []
    details: dict[str, Any] = {}

    try:
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object"
        })
        from importlib.metadata import version
        details["jsonschema_version"] = version("jsonschema")
        details["draft_2020_12_supported"] = True
    except Exception as exc:
        details["draft_2020_12_supported"] = False
        errors.append(f"jsonschema_unavailable: {type(exc).__name__}: {exc}")

    try:
        import cadquery
        import OCP  # noqa: F401
        from importlib.metadata import version
        cadquery_version = getattr(cadquery, "__version__", None)
        details["cadquery_version"] = (
            cadquery_version if cadquery_version else version("cadquery")
        )
        details["ocp_version"] = version("cadquery-ocp")
    except Exception as exc:
        errors.append(f"cad_runtime_unavailable: {type(exc).__name__}: {exc}")

    return {"ok": not errors, "errors": errors, "details": details}


# ---------------------------------------------------------------------------
# Product run states (ADR-0023 state machine — product live variant)
# ---------------------------------------------------------------------------

PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION = "needs_confirmation"
PRODUCT_LIVE_STATUS_BLOCKED = "blocked"
PRODUCT_LIVE_STATUS_CONSTRUCTING = "constructing"
PRODUCT_LIVE_STATUS_SUCCEEDED = "succeeded"
PRODUCT_LIVE_STATUS_FAILED = "failed"
PRODUCT_LIVE_STATUS_ERROR = "error"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ProductLiveLogicalRunPlan:
    """One planned logical run (before execution)."""

    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str


@dataclass
class ProductLiveRunState:
    """The extraction result for one product live logical run.

    This is returned BEFORE any CAD pipeline call.  It represents the state
    after LLM extraction + schema preflight, waiting for user confirmation
    (or already blocked/failed).

    Status values:
    - needs_confirmation: decision=answer + schema preflight passed → awaits user confirm
    - blocked: ask/refuse/missing/unsupported/conflict/parse/schema error → no CAD
    - error: internal error (parse failure, transport error, etc.)
    """

    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str
    # Extraction result
    llm_status: str         # answer/ask/refuse/blocked/error
    product_status: str     # needs_confirmation/blocked/error
    decision: str
    extracted_parameters: dict[str, Any]
    missing_fields: list[str]
    unsupported_requests: list[str]
    questions: list[str]
    conflicts: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    # Confirmation state (set after user confirms)
    confirmed: bool = False
    confirmation_patch: dict[str, Any] = field(default_factory=dict)
    confirmed_at: str | None = None
    # Pipeline result (set after confirmed + pipeline runs)
    pipeline_status: str | None = None
    pipeline_stage: str | None = None
    pipeline_run_dir: str | None = None
    step_path: str | None = None
    ir_index: dict[str, Any] | None = None
    # Raw retention metadata (formal runs only)
    raw_retention_path: str | None = None
    raw_retention_meta: dict[str, Any] | None = None
    # LLM metadata (redacted — no secrets)
    llm_meta: dict[str, Any] = field(default_factory=dict)
    # Provenance / record fields
    request_text: str = ""
    prompt_version: str = PROMPT_VERSION
    contract_version: str = CONTRACT_VERSION
    prompt_file_sha256: str = PRODUCT_PROMPT_FILE_SHA256
    created_at: str = field(default_factory=_utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "logical_run_id": self.logical_run_id,
            "input_id": self.input_id,
            "condition_id": self.condition_id,
            "provider": self.provider,
            "model": self.model,
            "llm_status": self.llm_status,
            "product_status": self.product_status,
            "decision": self.decision,
            "extracted_parameters": self.extracted_parameters,
            "missing_fields": self.missing_fields,
            "unsupported_requests": self.unsupported_requests,
            "questions": self.questions,
            "conflicts": self.conflicts,
            "errors": self.errors,
            "confirmed": self.confirmed,
            "confirmation_patch": self.confirmation_patch,
            "confirmed_at": self.confirmed_at,
            "pipeline_status": self.pipeline_status,
            "pipeline_stage": self.pipeline_stage,
            "pipeline_run_dir": self.pipeline_run_dir,
            "step_path": self.step_path,
            "ir_index": self.ir_index,
            "raw_retention_path": self.raw_retention_path,
            "llm_meta": self.llm_meta,
            "request_text": self.request_text,
            "prompt_version": self.prompt_version,
            "contract_version": self.contract_version,
            "prompt_file_sha256": self.prompt_file_sha256,
            "created_at": self.created_at,
        }


@dataclass
class ProductLiveBatchResult:
    """The result of a full product live batch (4 logical runs)."""

    batch_id: str | None   # None in dry-run / preflight modes
    profile_id: str
    timestamp_utc: str
    mode: str              # "dry_run" / "offline_preflight" / "formal" / "mock"
    preflight_ok: bool
    preflight_errors: list[str]
    planned_runs: list[ProductLiveLogicalRunPlan]
    results: list[ProductLiveRunState]
    budget_plan: dict[str, Any]
    summary_path: str | None = None
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
                {
                    "logical_run_id": p.logical_run_id,
                    "input_id": p.input_id,
                    "condition_id": p.condition_id,
                    "provider": p.provider,
                    "model": p.model,
                }
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
    """Load and optionally verify the frozen product live model-inputs.json.

    Returns a list of input dicts with keys: input_id, condition, natural_language.
    Raises ValueError if SHA-256 does not match the frozen constant.
    Does NOT load evaluator labels.
    """
    inputs_path = _REPO_ROOT / _MODEL_INPUTS_REL
    if not inputs_path.is_file():
        raise FileNotFoundError(
            f"Product live inputs file not found: {inputs_path}\n"
            f"Expected at: {_MODEL_INPUTS_REL} relative to repo root."
        )
    raw_bytes = inputs_path.read_bytes()
    if verify_sha256:
        actual = hashlib.sha256(raw_bytes).hexdigest()
        if actual != PRODUCT_INPUTS_SHA256:
            raise ValueError(
                f"Product live inputs SHA-256 mismatch:\n"
                f"  expected: {PRODUCT_INPUTS_SHA256}\n"
                f"  actual:   {actual}\n"
                f"The inputs file has been modified; refusing to proceed."
            )
    data = json.loads(raw_bytes.decode("utf-8"))
    inputs = data.get("inputs", [])
    actual_ids = tuple(inp["input_id"] for inp in inputs)
    if actual_ids != PRODUCT_INPUT_IDS:
        raise ValueError(
            f"Product live input IDs in file do not match frozen constants:\n"
            f"  expected: {PRODUCT_INPUT_IDS}\n"
            f"  actual:   {actual_ids}"
        )
    return inputs


# ---------------------------------------------------------------------------
# Combination planning
# ---------------------------------------------------------------------------


def _plan_combinations(
    authorization: ProductLiveAuthorization | None = None,
) -> list[ProductLiveLogicalRunPlan]:
    """Return the 4 planned logical run combinations for product live."""
    plans: list[ProductLiveLogicalRunPlan] = []
    for input_id in PRODUCT_INPUT_IDS:
        if authorization is not None:
            lrid = authorization.expected_logical_run_id(
                input_id, PRODUCT_CONDITION, PRODUCT_PROVIDER
            )
        else:
            lrid = f"{input_id}__{PRODUCT_CONDITION}__{PRODUCT_PROVIDER}__{PRODUCT_MODEL}"
        plans.append(
            ProductLiveLogicalRunPlan(
                logical_run_id=lrid,
                input_id=input_id,
                condition_id=PRODUCT_CONDITION,
                provider=PRODUCT_PROVIDER,
                model=PRODUCT_MODEL,
            )
        )
    return plans


# ---------------------------------------------------------------------------
# Offline preflight
# ---------------------------------------------------------------------------


def run_product_offline_preflight(
    authorization: ProductLiveAuthorization,
    *,
    batch_dir: Path | None = None,
    require_cad_runtime: bool = False,
) -> dict[str, Any]:
    """Offline preflight checks for product live (no network calls, no key reads).

    Checks:
    1. Inputs file exists and SHA-256 matches frozen constant.
    2. Authorization scope is valid.
    3. Budget is feasible (4 runs × 3 attempts = 12 ≤ max_batch_attempts).
    4. Batch directory does not already exist.
    5. Frozen prompt artifact is loadable.
    6. When requested, this interpreter supports Draft 2020-12 and CAD runtime.

    Returns a dict with ``ok: bool``, ``errors: list[str]``, and check details.
    Zero network calls. Zero key reads.
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
    computed = PRODUCT_MAX_LOGICAL_RUNS * PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN
    budget_feasible = computed <= max_http
    details["budget_plan"] = {
        "max_logical_runs": PRODUCT_MAX_LOGICAL_RUNS,
        "max_chat_attempts_per_run": PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
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
        safe_batch_id = _SAFE_RE.sub("_", authorization.batch_id)
        batch_dir = _CANONICAL_RUN_ROOT / safe_batch_id
    details["batch_dir"] = str(batch_dir)
    details["batch_dir_exists"] = batch_dir.exists()
    if batch_dir.exists():
        errors.append(
            f"batch_dir_exists: {batch_dir} already exists; "
            "each batch must use a unique batch_id"
        )

    # --- 5. CAD runtime check (optional, for formal runs) ---
    if require_cad_runtime:
        runtime = _check_cad_runtime()
        details["cad_runtime"] = runtime["details"]
        if not runtime["ok"]:
            errors.extend(f"cad_runtime_check: {e}" for e in runtime["errors"])

    # --- 6. Frozen prompt loadable ---
    try:
        prompt = load_frozen_prompt()
        details["prompt_version"] = prompt.version
        details["prompt_sha256"] = (prompt.system_prompt_sha256 or "")[:16] + "..."
        details["prompt_ok"] = True
        # Verify prompt file hash matches the frozen constant in authorization
        if FROZEN_PROMPT_FILE_SHA256 != PRODUCT_PROMPT_FILE_SHA256:
            errors.append(
                f"prompt_file_sha256_mismatch: loader has "
                f"{FROZEN_PROMPT_FILE_SHA256!r}, authorization expects "
                f"{PRODUCT_PROMPT_FILE_SHA256!r}"
            )
    except Exception as exc:
        errors.append(f"prompt_load: {exc}")
        details["prompt_ok"] = False

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Atomic summary writer
# ---------------------------------------------------------------------------


class _SummaryWriteError(RuntimeError):
    """Raised when the batch summary cannot be written atomically."""


def _atomic_write_json(path: Path, data: dict[str, Any], batch_dir: Path) -> None:
    """Write ``data`` as JSON to ``path`` via a temp file + atomic os.replace."""
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
        raise _SummaryWriteError(
            f"summary target {path} resolves outside batch_dir {batch_dir}; "
            "refusing to write evidence outside the canonical batch directory"
        )

    tmp_path = path.with_suffix(".json.tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(str(tmp_path), str(path))
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise _SummaryWriteError(
            f"failed to write summary to {path}: {exc}"
        ) from exc


class _SummaryWriter:
    """Atomic batch summary writer for formal product live runs."""

    def __init__(self, batch_dir: Path, initial_data: dict[str, Any]) -> None:
        self._batch_dir = batch_dir
        self._summary_path = batch_dir / "batch_summary.json"
        self._data: dict[str, Any] = dict(initial_data)

    @property
    def summary_path(self) -> Path:
        return self._summary_path

    def write_initial(self) -> None:
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def update_run(self, result: "ProductLiveRunState") -> None:
        """Atomically update the summary with one run result (no raw body, no absolute paths)."""
        raw_sha256: str | None = None
        raw_retained: bool | None = None
        if isinstance(result.raw_retention_meta, dict):
            raw_sha256 = result.raw_retention_meta.get("body_sha256")
            raw_retained = result.raw_retention_meta.get("retained")

        # Normalise all file-system paths to repo-relative before writing to summary.
        # Absolute paths must never appear in batch_summary.json or HTTP responses.
        raw_path_rel = _to_repo_relative_path(result.raw_retention_path)
        pipeline_dir_rel = _to_repo_relative_path(result.pipeline_run_dir)
        step_path_rel = _to_repo_relative_path(result.step_path)

        # ir_index may carry an absolute step_path; normalise it too.
        ir_index_clean: dict[str, Any] | None = None
        if isinstance(result.ir_index, dict):
            ir_index_clean = dict(result.ir_index)
            if "step_path" in ir_index_clean:
                ir_index_clean["step_path"] = _to_repo_relative_path(ir_index_clean["step_path"])

        run_entry: dict[str, Any] = {
            "product_status": result.product_status,
            "llm_status": result.llm_status,
            "pipeline_status": result.pipeline_status,
            "attempt_count": result.llm_meta.get("attempt_count"),
            "prompt_version": result.prompt_version,
            "contract_version": result.contract_version,
            "prompt_file_sha256": result.prompt_file_sha256,
            "configured_provider": result.provider,
            "configured_model": result.model,
            # repo-relative paths only — raw body, secrets, labels excluded
            "raw_retention_path": raw_path_rel,
            "raw_retained": raw_retained,
            "raw_sha256": raw_sha256,
            "pipeline_run_dir": pipeline_dir_rel,
            "ir_index": ir_index_clean,
            "step_path": step_path_rel,
            "errors": result.errors,
            "questions": result.questions,
        }

        runs = self._data.setdefault("runs", {})
        runs[result.logical_run_id] = run_entry
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def finalize(self, batch_status: str = "complete") -> None:
        self._data["batch_status"] = batch_status
        self._data["batch_finished_utc"] = _utc_now_iso()
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)


def _build_initial_summary(
    authorization: ProductLiveAuthorization,
    approval: ProductLiveFormalApproval,
    planned: list[ProductLiveLogicalRunPlan],
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
        "profile_id": PRODUCT_PROFILE_ID,
        "batch_started_utc": started_utc,
        "batch_status": "running",
        "scope": {
            "protocol_versions": sorted(authorization.protocol_versions),
            "sample_set": authorization.sample_set,
            "condition": PRODUCT_CONDITION,
            "provider": PRODUCT_PROVIDER,
            "model": PRODUCT_MODEL,
            "max_batch_http": PRODUCT_MAX_BATCH_HTTP,
            "max_logical_runs": PRODUCT_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
            "enable_cad_pipeline": authorization.enable_cad_pipeline,
        },
        "artifact_hashes": {
            "inputs_sha256": PRODUCT_INPUTS_SHA256,
            "evaluator_labels_sha256": PRODUCT_LABELS_SHA256,
            "prompt_version": PROMPT_VERSION,
            "prompt_file_sha256": FROZEN_PROMPT_FILE_SHA256,
            "contract_version": CONTRACT_VERSION,
        },
        "approval": approval.as_audit_dict(),
        "planned_runs": [p.logical_run_id for p in planned],
        "runs": {
            p.logical_run_id: {"product_status": "pending"}
            for p in planned
        },
    }


# ---------------------------------------------------------------------------
# Single logical run — MOCK MODE
# ---------------------------------------------------------------------------


def _run_one_logical_mock(
    *,
    plan: ProductLiveLogicalRunPlan,
    natural_language: str,
    prompt: Any,
    transport: FakeTransport,
    authorization: ProductLiveAuthorization,
    pipeline_output_root: Path,
) -> ProductLiveRunState:
    """Mock-mode execution using FakeTransport directly.

    Exercises the full parse → gate → Schema preflight path.
    Does NOT call run_pipeline() — that only happens after user confirmation
    (via confirm_product_live_run()).

    Returns a ProductLiveRunState with product_status=needs_confirmation (for
    successful answer) or blocked/error (for all failure paths).
    """
    from llm.providers import build_deepseek_request
    from llm.retry import send_with_retry
    from llm.parser import parse_response
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    run_id = str(uuid.uuid4())
    now = _utc_now_iso()

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
        },
        "attempt_count": None,
        "total_elapsed_ms": None,
    }

    # --- Send via FakeTransport (with retry, no budget ledger in mock mode) ---
    try:
        response, attempts, elapsed_ms = send_with_retry(transport, request)
    except Exception as exc:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            product_status=PRODUCT_LIVE_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "TRANSPORT_EXCEPTION", "message": str(exc)}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    if response is None:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            product_status=PRODUCT_LIVE_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "NO_RESPONSE",
                     "message": "transport returned no response after retries"}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    llm_meta["attempt_count"] = len(attempts)
    llm_meta["total_elapsed_ms"] = elapsed_ms
    raw_body = response.body

    # --- Parse ---
    parse_result = parse_response(raw_body)
    if not parse_result.ok:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="error",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "PARSE_ERROR",
                     "message": str([e.as_dict() for e in parse_result.errors])}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    envelope = parse_result.envelope
    questions: list[str] = list(envelope.questions or [])
    missing_fields: list[str] = list(envelope.missing_fields or [])
    unsupported: list[str] = list(envelope.unsupported_requests or [])
    extracted = dict(envelope.extracted_parameters or {})
    decision = envelope.decision

    # --- Construction gate checks (fail-closed) ---
    if decision == "ask":
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="ask",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=[],
            errors=[{"code": "GATE_DECISION_ASK",
                     "message": "decision=ask; construction blocked until questions answered"}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    if decision == "refuse":
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="refuse",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=[],
            errors=[{"code": "GATE_DECISION_REFUSE",
                     "message": "decision=refuse; construction blocked"}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    if missing_fields:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=[],
            errors=[{"code": "GATE_MISSING_FIELDS",
                     "fields": missing_fields,
                     "message": f"missing_fields is not empty: {missing_fields}"}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    if unsupported:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=[],
            errors=[{"code": "GATE_UNSUPPORTED_REQUESTS",
                     "fields": unsupported,
                     "message": f"unsupported_requests is not empty: {unsupported}"}],
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    # --- Schema validation (preflight only, no CAD) ---
    projection = project_to_cad003(extracted)
    if not projection.ok:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=list(projection.errors),
            errors=list(projection.errors),
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        schema_errors = [e.as_dict() for e in schema_result.errors]
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status="blocked",
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision,
            extracted_parameters=extracted,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=schema_errors,
            errors=schema_errors,
            llm_meta=llm_meta,
            request_text=natural_language,
            created_at=now,
        )

    # --- decision=answer, all gates pass: needs_confirmation ---
    # NOTE: We do NOT call run_pipeline() here.
    # The caller (product runner / server) must present the extraction result
    # to the user and await explicit confirmation before calling
    # confirm_product_live_run().
    return ProductLiveRunState(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider,
        model=plan.model,
        llm_status="answer",
        product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
        decision=decision,
        extracted_parameters=extracted,
        missing_fields=[],
        unsupported_requests=[],
        questions=[],
        conflicts=[],
        errors=[],
        llm_meta=llm_meta,
        request_text=natural_language,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Confirm a product live run (after user confirmation)
# ---------------------------------------------------------------------------


def confirm_product_live_run(
    state: ProductLiveRunState,
    *,
    confirmed: bool,
    patch: dict[str, Any] | None = None,
    output_root: Path | None = None,
) -> ProductLiveRunState:
    """Execute the CAD pipeline after explicit user confirmation.

    This is the ONLY code path that calls run_pipeline() for product live runs.

    Parameters
    ----------
    state:
        The ProductLiveRunState returned by the extraction phase.  Must be
        in product_status=needs_confirmation.
    confirmed:
        Must be True to proceed.  False → returns blocked.
    patch:
        Optional parameter patch (e.g. user corrects bore_d).  Applied
        on top of extracted_parameters before Schema re-validation.
    output_root:
        Pipeline output root directory.  Defaults to work/product-live-runs/.

    Returns
    -------
    ProductLiveRunState
        A new state object with:
        - product_status=succeeded if pipeline succeeds
        - product_status=failed if pipeline fails
        - product_status=blocked if confirmation rejected or gate fails
        The original state is never mutated.
    """
    from llm.contract import EXTRACTABLE_FIELDS
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters
    import json as _json

    now = _utc_now_iso()
    out_root = Path(output_root) if output_root else (
        _REPO_ROOT / "work" / "product-live-runs"
    )

    # --- Gate 1: state must be needs_confirmation ---
    if state.product_status != PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=state.decision,
            extracted_parameters=state.extracted_parameters,
            missing_fields=state.missing_fields,
            unsupported_requests=state.unsupported_requests,
            questions=state.questions,
            conflicts=state.conflicts,
            errors=[{"code": "NOT_CONFIRMABLE",
                     "message": f"run is in status={state.product_status!r}; "
                                "only needs_confirmation runs can be confirmed"}],
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            created_at=now,
        )

    # --- Gate 2: confirmed must be True ---
    if not confirmed:
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=state.decision,
            extracted_parameters=state.extracted_parameters,
            missing_fields=state.missing_fields,
            unsupported_requests=state.unsupported_requests,
            questions=state.questions,
            conflicts=state.conflicts,
            errors=[{"code": "CONFIRMATION_REJECTED",
                     "message": "confirmed=False; construction blocked"}],
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            created_at=now,
        )

    # --- Merge patch into extracted parameters ---
    merged = dict(state.extracted_parameters)
    if patch:
        # Validate patch fields are known
        unknown = [k for k in patch if k not in EXTRACTABLE_FIELDS]
        if unknown:
            return ProductLiveRunState(
                logical_run_id=state.logical_run_id,
                input_id=state.input_id,
                condition_id=state.condition_id,
                provider=state.provider,
                model=state.model,
                llm_status=state.llm_status,
                product_status=PRODUCT_LIVE_STATUS_BLOCKED,
                decision=state.decision,
                extracted_parameters=state.extracted_parameters,
                missing_fields=state.missing_fields,
                unsupported_requests=state.unsupported_requests,
                questions=state.questions,
                conflicts=state.conflicts,
                errors=[{"code": "PATCH_UNKNOWN_FIELD",
                         "message": f"unknown fields in patch: {unknown}",
                         "fields": unknown}],
                llm_meta=state.llm_meta,
                request_text=state.request_text,
                created_at=now,
            )
        merged.update(patch)

    # --- Schema re-validation with merged params ---
    projection = project_to_cad003(merged)
    if not projection.ok:
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=state.decision,
            extracted_parameters=state.extracted_parameters,
            missing_fields=state.missing_fields,
            unsupported_requests=state.unsupported_requests,
            questions=state.questions,
            conflicts=list(projection.errors),
            errors=list(projection.errors),
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            confirmed=True,
            confirmation_patch=dict(patch or {}),
            confirmed_at=now,
            created_at=now,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        schema_errors = [e.as_dict() for e in schema_result.errors]
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=state.decision,
            extracted_parameters=state.extracted_parameters,
            missing_fields=state.missing_fields,
            unsupported_requests=state.unsupported_requests,
            questions=state.questions,
            conflicts=schema_errors,
            errors=schema_errors,
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            confirmed=True,
            confirmation_patch=dict(patch or {}),
            confirmed_at=now,
            created_at=now,
        )

    # --- Build envelope for pipeline ---
    from llm.contract import CONTRACT_VERSION as _CV, PROMPT_VERSION as _PV, EXTRACTABLE_FIELDS as _EF
    safe = {k: v for k, v in merged.items() if k in _EF and v is not None}
    evidence = [
        {"field": k, "quote": str(v), "source": "user_input"}
        for k, v in safe.items()
    ]
    envelope_obj = {
        "contract_version": _CV,
        "prompt_version": _PV,
        "decision": "answer",
        "extracted_parameters": safe,
        "unsupported_requests": [],
        "evidence": evidence,
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    envelope_json = _json.dumps(envelope_obj, ensure_ascii=False)

    # --- Call run_pipeline() ---
    try:
        pipeline_result = run_pipeline(
            request_text=state.request_text,
            raw_envelope=envelope_json,
            output_root=out_root,
            envelope_fixture_label=f"product_live_{state.input_id}",
        )
    except Exception as exc:
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_FAILED,
            decision=state.decision,
            extracted_parameters=state.extracted_parameters,
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "PIPELINE_EXCEPTION",
                     "message": f"{type(exc).__name__}: {str(exc)[:300]}"}],
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            confirmed=True,
            confirmation_patch=dict(patch or {}),
            confirmed_at=now,
            pipeline_status="error",
            pipeline_stage="pipeline_exception",
            created_at=now,
        )

    if pipeline_result.status == "success":
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_SUCCEEDED,
            decision=state.decision,
            extracted_parameters=merged,
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[],
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            confirmed=True,
            confirmation_patch=dict(patch or {}),
            confirmed_at=now,
            pipeline_status=pipeline_result.status,
            pipeline_stage=pipeline_result.stage,
            pipeline_run_dir=pipeline_result.run_dir,
            step_path=pipeline_result.step_path,
            ir_index=pipeline_result.ir_index,
            created_at=now,
        )
    else:
        return ProductLiveRunState(
            logical_run_id=state.logical_run_id,
            input_id=state.input_id,
            condition_id=state.condition_id,
            provider=state.provider,
            model=state.model,
            llm_status=state.llm_status,
            product_status=PRODUCT_LIVE_STATUS_FAILED,
            decision=state.decision,
            extracted_parameters=merged,
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=pipeline_result.errors,
            llm_meta=state.llm_meta,
            request_text=state.request_text,
            confirmed=True,
            confirmation_patch=dict(patch or {}),
            confirmed_at=now,
            pipeline_status=pipeline_result.status,
            pipeline_stage=pipeline_result.stage,
            pipeline_run_dir=pipeline_result.run_dir,
            step_path=None,  # never expose a failed step
            ir_index=None,
            created_at=now,
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_product_batch(
    *,
    authorization: ProductLiveAuthorization,
    dry_run: bool = True,
    transport=None,
    output_root: Path | None = None,
    approval: "ProductLiveFormalApproval | None" = None,
) -> ProductLiveBatchResult:
    """Run the product live extraction batch.

    Parameters
    ----------
    authorization:
        A validated :class:`ProductLiveAuthorization` instance.
    dry_run:
        If True (default): return the plan and preflight result only.
        No network calls, no Adapter runs, no pipeline calls.
        Does NOT require an ``approval`` credential.
    transport:
        Injectable transport for testing.  Use an exact FakeTransport for
        offline mock runs.  For formal product live execution, pass None and
        provide the exact authorization plus matching non-test-only approval.
    output_root:
        Override the pipeline-runs output root.
    approval:
        Required for formal live runs (``dry_run=False`` and ``transport is None``).
        Must be a :class:`ProductLiveFormalApproval` whose ``batch_id``
        matches ``authorization.batch_id``.  Validated BEFORE any directory
        creation, BudgetLedger initialization, Transport construction, or
        network I/O.  Not required for dry-run or mock modes.

    Notes
    -----
    This function NEVER calls run_pipeline() directly.  Extraction results with
    product_status=needs_confirmation must be confirmed via
    :func:`confirm_product_live_run` to trigger the CAD pipeline.
    """
    ts = _utc_now_iso()
    planned = _plan_combinations(authorization)
    budget_plan = {
        "max_logical_runs": PRODUCT_MAX_LOGICAL_RUNS,
        "max_chat_attempts_per_run": PRODUCT_MAX_CHAT_ATTEMPTS_PER_RUN,
        "max_batch_http": PRODUCT_MAX_BATCH_HTTP,
        "provider": PRODUCT_PROVIDER,
        "model": PRODUCT_MODEL,
        "condition": PRODUCT_CONDITION,
        "input_ids": list(PRODUCT_INPUT_IDS),
    }

    # --- dry_run: preflight only, no runs ---
    if dry_run:
        pf = run_product_offline_preflight(authorization)
        return ProductLiveBatchResult(
            batch_id=authorization.batch_id,
            profile_id=PRODUCT_PROFILE_ID,
            timestamp_utc=ts,
            mode="dry_run",
            preflight_ok=pf["ok"],
            preflight_errors=pf["errors"],
            planned_runs=planned,
            results=[],
            budget_plan=budget_plan,
        )

    is_formal = transport is None

    # --- Approval gate: required for formal runs ---
    if is_formal:
        if approval is None:
            raise ProductApprovalValidationError(
                "formal product live run requires a ProductLiveFormalApproval credential; "
                "received None.  Obtain owner approval and pass it as "
                "approval=<ProductLiveFormalApproval> before executing a live run."
            )
        # Raises ProductApprovalValidationError if batch_id mismatch or invalid
        validate_product_formal_approval_binding(authorization, approval)

    # --- Offline preflight must pass before any infra creation ---
    pf = run_product_offline_preflight(authorization, require_cad_runtime=is_formal)
    if not pf["ok"]:
        return ProductLiveBatchResult(
            batch_id=authorization.batch_id,
            profile_id=PRODUCT_PROFILE_ID,
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

    safe_batch_id = _safe_filename_component(authorization.batch_id)
    if output_root is None:
        pipeline_output_root = _CANONICAL_RUN_ROOT / safe_batch_id / "pipeline-runs"
    else:
        pipeline_output_root = Path(output_root)

    # --- Build formal batch infrastructure ---
    if is_formal:
        from llm.budget import BudgetAwareTransport, BudgetLedger
        from llm.real_transport import DeepSeekTransport

        batch_dir = _CANONICAL_RUN_ROOT / safe_batch_id
        try:
            batch_dir.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            raise _SummaryWriteError(
                f"batch directory already exists: {batch_dir}; "
                "each batch must use a unique batch_id"
            )

        initial_data = _build_initial_summary(
            authorization, approval, planned, prompt, ts
        )
        writer = _SummaryWriter(batch_dir, initial_data)
        try:
            writer.write_initial()
        except _SummaryWriteError:
            try:
                batch_dir.rmdir()
            except OSError:
                pass
            raise

        ledger = None
        try:
            ledger = BudgetLedger(batch_dir, authorization)
            ledger.acquire_lock()
        except Exception:
            try:
                writer.finalize(batch_status="aborted")
            except Exception:
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

    results: list[ProductLiveRunState] = []
    mode = "formal" if is_formal else "mock"
    summary_write_failed = False

    try:
        for plan in planned:
            natural_language = input_map[plan.input_id]

            if is_formal:
                # Formal path: construct BudgetAwareTransport + Adapter
                # NOTE: This task does NOT authorize actual live calls.
                # The formal wiring is here for completeness; real execution
                # requires Codex review + owner re-approval of a specific batch.
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

                # Build AdapterInput
                adapter_input = AdapterInput(
                    query_id=plan.input_id,
                    natural_language_input=natural_language,
                    reference_context=None,
                    system_prompt=prompt.system_prompt,
                    user_prompt_template=prompt.user_template,
                    condition_id=plan.condition_id,
                )

                try:
                    adapter_result = run_adapter.run(
                        adapter_input,
                        run_id=plan.logical_run_id,
                        formal_authorization=authorization,
                    )
                except Exception as exc:
                    result = ProductLiveRunState(
                        logical_run_id=plan.logical_run_id,
                        input_id=plan.input_id,
                        condition_id=plan.condition_id,
                        provider=plan.provider,
                        model=plan.model,
                        llm_status="error",
                        product_status=PRODUCT_LIVE_STATUS_ERROR,
                        decision="",
                        extracted_parameters={},
                        missing_fields=[],
                        unsupported_requests=[],
                        questions=[],
                        conflicts=[],
                        errors=[{"code": "ADAPTER_EXCEPTION", "message": str(exc)}],
                        llm_meta={"run_id": plan.logical_run_id},
                        request_text=natural_language,
                    )
                    results.append(result)
                    if writer is not None:
                        try:
                            writer.update_run(result)
                        except _SummaryWriteError as exc:
                            summary_write_failed = True
                            break
                    continue

                # Map adapter result to ProductLiveRunState
                record = adapter_result.record
                llm_meta = {
                    "run_id": plan.logical_run_id,
                    "configured_provider": record.configured_provider,
                    "configured_model_name": record.configured_model_name,
                    "prompt_version": record.prompt_version,
                    "contract_version": record.contract_version,
                    "attempt_count": record.attempt_count,
                    "total_elapsed_ms": record.total_elapsed_ms,
                    "construction_ready": record.construction_ready,
                }

                raw_retention_meta = dict(record.raw_response_retention or {})

                result = _build_state_from_adapter_result(
                    plan=plan,
                    adapter_result=adapter_result,
                    llm_meta=llm_meta,
                    natural_language=natural_language,
                )

                results.append(result)
                if writer is not None:
                    try:
                        writer.update_run(result)
                    except _SummaryWriteError:
                        summary_write_failed = True
                        break

            else:
                # Mock mode: use FakeTransport directly
                if not isinstance(transport, FakeTransport):
                    result = ProductLiveRunState(
                        logical_run_id=plan.logical_run_id,
                        input_id=plan.input_id,
                        condition_id=plan.condition_id,
                        provider=plan.provider,
                        model=plan.model,
                        llm_status="error",
                        product_status=PRODUCT_LIVE_STATUS_ERROR,
                        decision="",
                        extracted_parameters={},
                        missing_fields=[],
                        unsupported_requests=[],
                        questions=[],
                        conflicts=[],
                        errors=[{"code": "INVALID_MOCK_TRANSPORT",
                                 "message": "mock transport must be FakeTransport"}],
                        llm_meta={},
                        request_text=natural_language,
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
            except Exception:
                pass
        if is_formal and writer is not None and not summary_write_failed:
            statuses = [r.product_status for r in results]
            failed_statuses = {PRODUCT_LIVE_STATUS_ERROR, PRODUCT_LIVE_STATUS_FAILED}
            if len(results) < len(planned):
                final_batch_status = "aborted"
            elif statuses and all(s in failed_statuses for s in statuses):
                final_batch_status = "failed"
            elif any(s in failed_statuses for s in statuses):
                final_batch_status = "partial"
            else:
                final_batch_status = "complete"
            try:
                writer.finalize(batch_status=final_batch_status)
            except _SummaryWriteError as exc:
                finalize_error = str(exc)
            else:
                finalize_error = None
        else:
            finalize_error = None

    return ProductLiveBatchResult(
        batch_id=authorization.batch_id,
        profile_id=PRODUCT_PROFILE_ID,
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


def _build_state_from_envelope(
    *,
    plan: ProductLiveLogicalRunPlan,
    envelope: Any,
    llm_meta: dict[str, Any],
    natural_language: str,
    raw_retention_meta: dict[str, Any] | None = None,
    raw_retention_path: str | None = None,
) -> ProductLiveRunState:
    """Build a ProductLiveRunState from an already-parsed envelope object.

    Used by the formal path after the Adapter has parsed and validated the
    model response.  Applies the same gate logic as the mock path.
    """
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    now = _utc_now_iso()
    questions = list(envelope.questions or [])
    missing_fields = list(envelope.missing_fields or [])
    unsupported = list(envelope.unsupported_requests or [])
    extracted = dict(envelope.extracted_parameters or {})
    decision = envelope.decision

    if decision == "ask":
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="ask", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_DECISION_ASK",
                     "message": "decision=ask; construction blocked"}],
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    if decision == "refuse":
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="refuse", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_DECISION_REFUSE", "message": "decision=refuse"}],
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    if missing_fields:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_MISSING_FIELDS", "fields": missing_fields,
                     "message": f"missing_fields is not empty: {missing_fields}"}],
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    if unsupported:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_UNSUPPORTED_REQUESTS", "fields": unsupported,
                     "message": f"unsupported_requests is not empty: {unsupported}"}],
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    projection = project_to_cad003(extracted)
    if not projection.ok:
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=list(projection.errors),
            errors=list(projection.errors),
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        schema_errors = [e.as_dict() for e in schema_result.errors]
        return ProductLiveRunState(
            logical_run_id=plan.logical_run_id, input_id=plan.input_id,
            condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
            llm_status="blocked", product_status=PRODUCT_LIVE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=schema_errors, errors=schema_errors,
            llm_meta=llm_meta, request_text=natural_language,
            raw_retention_meta=raw_retention_meta,
            raw_retention_path=raw_retention_path, created_at=now,
        )

    # All gates pass: needs_confirmation
    return ProductLiveRunState(
        logical_run_id=plan.logical_run_id, input_id=plan.input_id,
        condition_id=plan.condition_id, provider=plan.provider, model=plan.model,
        llm_status="answer", product_status=PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
        decision=decision, extracted_parameters=extracted,
        missing_fields=[], unsupported_requests=[], questions=[], conflicts=[],
        errors=[],
        llm_meta=llm_meta, request_text=natural_language,
        raw_retention_meta=raw_retention_meta,
        raw_retention_path=raw_retention_path, created_at=now,
    )


# ---------------------------------------------------------------------------
# Adapter result mapping
# ---------------------------------------------------------------------------


def _build_state_from_adapter_result(
    *,
    plan: ProductLiveLogicalRunPlan,
    adapter_result: Any,
    llm_meta: dict[str, Any],
    natural_language: str,
) -> ProductLiveRunState:
    """Map Adapter outcomes without conflating transport and parse failures.

    Only stable codes, fields, status codes, and attempt outcomes are copied
    into product evidence. Provider error bodies and parser diagnostic text can
    contain untrusted response content, so they are deliberately omitted.
    Raw response retention metadata is carried for every received response,
    including parse and envelope validation failures.
    """
    record = adapter_result.record
    parse_result = adapter_result.parse_result
    raw_meta = dict(record.raw_response_retention or {})
    raw_path = raw_meta.get("path") if raw_meta.get("retained") else None

    if parse_result is not None and parse_result.envelope is not None:
        return _build_state_from_envelope(
            plan=plan,
            envelope=parse_result.envelope,
            llm_meta=llm_meta,
            natural_language=natural_language,
            raw_retention_meta=raw_meta,
            raw_retention_path=raw_path,
        )

    if parse_result is None:
        attempts = list(getattr(record, "attempts", ()) or ())
        last_attempt = attempts[-1] if attempts else None
        model_call_stage = next(
            (item for item in getattr(record, "stages", ())
             if getattr(item, "stage", None) == "model_call"),
            None,
        )
        cause_code = (
            getattr(last_attempt, "error_code", None)
            or getattr(model_call_stage, "error_code", None)
            or "NO_RESPONSE"
        )
        error = {
            "code": "TRANSPORT_ERROR",
            "cause_code": str(cause_code),
            "message": "model call did not produce a response",
            "attempt_count": len(attempts),
        }
        http_status = getattr(last_attempt, "http_status", None)
        outcome = getattr(last_attempt, "outcome", None)
        if http_status is not None:
            error["http_status"] = http_status
        if outcome:
            error["attempt_outcome"] = str(outcome)
        fields = list(getattr(last_attempt, "error_fields", ()) or ())
        if fields:
            error["fields"] = [str(field) for field in fields]
    else:
        parse_errors = list(getattr(parse_result, "errors", ()) or ())
        causes = []
        for item in parse_errors:
            cause = {"code": str(getattr(item, "code", "PARSE_ERROR"))}
            error_stage = getattr(item, "stage", None)
            if error_stage:
                cause["stage"] = str(error_stage)
            fields = list(getattr(item, "fields", ()) or ())
            if fields:
                cause["fields"] = [str(field) for field in fields]
            causes.append(cause)
        parse_stage = getattr(parse_result, "stage", None)
        error = {
            "code": "RESPONSE_PARSE_ERROR" if parse_stage == "parse" else "ENVELOPE_VALIDATION_ERROR",
            "message": "response failed strict parsing or envelope validation",
            "causes": causes,
        }

    return ProductLiveRunState(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider,
        model=plan.model,
        llm_status="error",
        product_status=PRODUCT_LIVE_STATUS_ERROR,
        decision="",
        extracted_parameters={},
        missing_fields=[],
        unsupported_requests=[],
        questions=[],
        conflicts=[],
        errors=[error],
        llm_meta=llm_meta,
        raw_retention_meta=raw_meta or None,
        raw_retention_path=raw_path,
        request_text=natural_language,
    )


# ---------------------------------------------------------------------------
# ProductLiveService — injectable offline service for server.py
# ---------------------------------------------------------------------------


class ProductLiveService:
    """Injectable service that wires the HTTP layer to the product live runner.

    Encapsulates a FakeTransport (for offline/mock mode) and an in-memory
    registry.  The server never touches transport details; it only calls
    ``extract()`` and ``confirm()``.

    Default (no transport): all create calls return PRODUCT_LIVE_DISABLED.

    Security guarantees:
    - The browser submits only ``request_text`` and ``input_id``.
    - ``extract()`` calls ``_run_one_logical_mock()`` internally and stores the
      result in a private registry.  Evaluator labels never enter this path.
    - ``confirm()`` calls ``confirm_product_live_run()`` — the only path to
      ``run_pipeline()``.
    - No network I/O, no .env reads, no FORMAL_EVALUATION_ALLOWED change.
    """

    def __init__(
        self,
        transport: FakeTransport,
        authorization: "ProductLiveAuthorization | None" = None,
        output_root: "Path | None" = None,
    ) -> None:
        self._transport = transport
        self._authorization = authorization or _make_offline_auth()
        self._output_root = Path(output_root) if output_root else (
            _REPO_ROOT / "work" / "product-live-runs"
        )
        self._runs: dict[str, ProductLiveRunState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, input_id: str, request_text: str) -> ProductLiveRunState:
        """Run extraction for one input, store state, return result.

        Calls ``_run_one_logical_mock()`` with the injected FakeTransport.
        Never calls run_pipeline() — that only happens after confirm().
        """
        if input_id not in PRODUCT_INPUT_IDS:
            now = _utc_now_iso()
            lrid = f"{input_id}__{PRODUCT_CONDITION}__{PRODUCT_PROVIDER}__{PRODUCT_MODEL}"
            state = ProductLiveRunState(
                logical_run_id=lrid, input_id=input_id,
                condition_id=PRODUCT_CONDITION, provider=PRODUCT_PROVIDER, model=PRODUCT_MODEL,
                llm_status="error", product_status=PRODUCT_LIVE_STATUS_ERROR,
                decision="", extracted_parameters={}, missing_fields=[],
                unsupported_requests=[], questions=[], conflicts=[],
                errors=[{"code": "UNKNOWN_INPUT_ID",
                         "message": f"input_id {input_id!r} not in authorized scope: {PRODUCT_INPUT_IDS}"}],
                request_text=request_text, created_at=now,
            )
            self._runs[lrid] = state
            return state

        prompt = load_frozen_prompt()
        plan = ProductLiveLogicalRunPlan(
            logical_run_id=f"{input_id}__{PRODUCT_CONDITION}__{PRODUCT_PROVIDER}__{PRODUCT_MODEL}",
            input_id=input_id,
            condition_id=PRODUCT_CONDITION,
            provider=PRODUCT_PROVIDER,
            model=PRODUCT_MODEL,
        )
        state = _run_one_logical_mock(
            plan=plan,
            natural_language=request_text,
            prompt=prompt,
            transport=self._transport,
            authorization=self._authorization,
            pipeline_output_root=self._output_root / input_id,
        )
        self._runs[plan.logical_run_id] = state
        return state

    def confirm(
        self,
        logical_run_id: str,
        confirmed: bool,
        patch: "dict[str, Any] | None" = None,
    ) -> "ProductLiveRunState | None":
        """Confirm a pending extraction result and optionally run the CAD pipeline.

        Returns None if the run_id is unknown.  Calls
        ``confirm_product_live_run()`` — the only path to ``run_pipeline()``.
        """
        state = self._runs.get(logical_run_id)
        if state is None:
            return None
        new_state = confirm_product_live_run(
            state,
            confirmed=confirmed,
            patch=patch,
            output_root=self._output_root,
        )
        self._runs[logical_run_id + "__confirmed"] = new_state
        return new_state

    def get(self, logical_run_id: str) -> "ProductLiveRunState | None":
        """Return the latest state for a logical run id."""
        return (
            self._runs.get(logical_run_id + "__confirmed")
            or self._runs.get(logical_run_id)
        )

    def get_step_bytes_secure(self, logical_run_id: str) -> bytes | None:
        """Return STEP bytes for a succeeded confirmed run with 6-layer security.

        Never exposes absolute paths or other run STEP files.
        """
        import hashlib as _hashlib
        state = self._runs.get(logical_run_id + "__confirmed")
        if state is None:
            return None
        if state.product_status != PRODUCT_LIVE_STATUS_SUCCEEDED:
            return None
        step_path_str = state.step_path
        run_dir_str = state.pipeline_run_dir
        expected_sha256 = (
            state.ir_index.get("step_sha256")
            if isinstance(state.ir_index, dict) else None
        )
        if not step_path_str or not run_dir_str or not expected_sha256:
            return None
        step_path = Path(step_path_str)
        expected_prefix = Path(run_dir_str) / "cad_output"
        try:
            canonical_step = step_path.resolve()
            canonical_prefix = expected_prefix.resolve()
            canonical_step.relative_to(canonical_prefix)
        except (ValueError, OSError):
            return None
        if canonical_step.is_symlink():
            return None
        if not canonical_step.is_file() or canonical_step.stat().st_size == 0:
            return None
        content = canonical_step.read_bytes()
        if _hashlib.sha256(content).hexdigest() != expected_sha256:
            return None
        return content


def _make_offline_auth() -> "ProductLiveAuthorization":
    """Return a minimal offline-mode authorization for the service (no batch)."""
    from llm.product_live_authorization import authorize_product_live_run
    return authorize_product_live_run(batch_id="product-live-offline-service")
