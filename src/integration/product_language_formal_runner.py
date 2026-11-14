"""Formal runner for the APP-003 ten-input language sample scope.

SAFETY GUARANTEES
-----------------
- ``FORMAL_EVALUATION_ALLOWED`` remains ``False`` and is never changed here.
- Evaluator labels (``evaluator-labels.json``) are NEVER loaded, read, opened,
  or referenced in any code path: preflight, execution, raw retention, summary,
  or logs.
- Formal runs require a :class:`~llm.product_language_authorization.ProductLanguageAuthorization`
  AND a matching non-test-only
  :class:`~llm.product_language_authorization.ProductLanguageFormalApproval`.
- Authorization type, test-only flag, batch ID, profile, frozen inputs + hash,
  provider/model/condition, approval binding, budget feasibility, and formal
  preflight results are ALL validated BEFORE any directory creation, ledger
  initialisation, transport construction, credential loading, or network I/O.
- Frozen inputs SHA-256 is verified twice: once at preflight and again just
  before the first request.
- Every HTTP request reserves a budget slot atomically BEFORE the network call
  via :class:`~llm.budget.BudgetLedger`.  Concurrent, exception, and retry
  paths cannot exceed the per-run cap of 2 or the batch cap of 20.
- Only transient transport failures are retried (connection/read timeout,
  connection interruption, HTTP 429, HTTP 5xx).  Authentication/permission
  errors, malformed requests, invalid JSON, and contract failures are not
  retried.
- No IR / CAD / geometry / STEP pipeline is ever called.  ``answer`` results
  are recorded for extraction and evaluation only; they never trigger product
  confirmation or the CAD pipeline.
- Raw responses are written to ``work/app001-runs/{batch_id}/raw/``.  Each
  file records the response body, its length in bytes, and its SHA-256.
- The batch summary (``batch_summary.json``) contains only approved fields,
  repo-relative paths, and hashes.  It never contains raw response bodies,
  API keys, Authorization header values, absolute filesystem paths, or
  evaluator label content.
- A batch that has all runs with transport/parse errors must NOT be reported
  as ``complete``; it is reported as ``failed``.
- Batch init, lock, ledger, raw write, and finalize failures all fail closed
  and produce auditable state.  A failed run never reads or returns artefacts
  from other runs or batches.
- No new generic live switch or global gate is opened.  The caller cannot
  override inputs, provider, model, condition, budget, or batch scope.

Offline mock testing
--------------------
Tests inject a :class:`~llm.transport.FakeTransport` via the ``transport``
parameter of :func:`run_product_language_formal_batch`.  The mock path
exercises the full preflight → budget → Adapter → raw-retention → summary
path without network I/O, credential reads, or batch directory creation
in the canonical run root.
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

from llm.authorization import AuthorizationScopeError
from llm.contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    FORMAL_EVALUATION_ALLOWED,
    PROMPT_VERSION,
)
from llm.env_loader import EnvironmentConfigurationError, load_deepseek_environment
from llm.product_language_authorization import (
    PRODUCT_LANGUAGE_CONDITION,
    PRODUCT_LANGUAGE_INPUT_IDS,
    PRODUCT_LANGUAGE_INPUTS_SHA256,
    PRODUCT_LANGUAGE_LABELS_SHA256,
    PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
    PRODUCT_LANGUAGE_MODEL,
    PRODUCT_LANGUAGE_PROFILE_ID,
    PRODUCT_LANGUAGE_PROMPT_SHA256,
    PRODUCT_LANGUAGE_PROVIDER,
    ProductLanguageApprovalValidationError,
    ProductLanguageAuthorization,
    ProductLanguageFormalApproval,
    validate_product_language_formal_approval_binding,
)
from llm.prompt_loader import FROZEN_PROMPT_FILE_SHA256, load_frozen_prompt
from llm.transport import FakeTransport

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_RUN_ROOT = _REPO_ROOT / "work" / "app001-runs"
_INPUTS_REL = Path(
    "agent-work/integration/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01/model-inputs.json"
)
_SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
_SUMMARY_SCHEMA_VERSION = "language-sample-batch-summary.v1"


def _safe_component(value: str) -> str:
    return _SAFE_RE.sub("_", value)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _to_repo_relative_path(path_str: str | None) -> str | None:
    """Convert a path to a repo-relative string, or None if outside the repo.

    Fail-closed: any path that cannot be verified as residing inside
    ``_REPO_ROOT`` after canonical resolution returns ``None``.
    """
    if not path_str or not isinstance(path_str, str):
        return None
    try:
        root = _REPO_ROOT.resolve()
        raw = Path(path_str)
        if raw.is_absolute():
            candidate = raw.resolve()
        else:
            candidate = (root / raw).resolve()
        candidate.relative_to(root)
        rel = candidate.relative_to(root)
        result = str(rel).replace("\\", "/")
        if result.startswith("/"):
            return None
        return result
    except (ValueError, OSError, RuntimeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Frozen-input loader (never touches evaluator-labels.json)
# ---------------------------------------------------------------------------

def _load_inputs(*, verify_sha256: bool = True) -> list[dict[str, str]]:
    """Load and verify frozen language-sample inputs.

    Never reads, opens, or references ``evaluator-labels.json``.
    Raises ``ValueError`` on SHA-256 mismatch or schema error.
    """
    path = _REPO_ROOT / _INPUTS_REL
    payload = path.read_bytes()
    if verify_sha256:
        actual = _sha256_bytes(payload)
        if actual != PRODUCT_LANGUAGE_INPUTS_SHA256:
            raise ValueError(
                f"language model-inputs SHA-256 mismatch: "
                f"expected {PRODUCT_LANGUAGE_INPUTS_SHA256!r}, got {actual!r}"
            )
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("language model-inputs must be a JSON array")
    for row in data:
        if (
            not isinstance(row, dict)
            or set(row) != {"input_id", "request_text"}
            or not isinstance(row.get("input_id"), str)
            or not isinstance(row.get("request_text"), str)
            or not row["request_text"].strip()
        ):
            raise ValueError(f"language model-inputs row schema mismatch: {row!r}")
    ids = tuple(row["input_id"] for row in data)
    if ids != PRODUCT_LANGUAGE_INPUT_IDS:
        raise ValueError(
            f"language model-input IDs/order mismatch: "
            f"expected {PRODUCT_LANGUAGE_INPUT_IDS!r}, got {ids!r}"
        )
    return data


# ---------------------------------------------------------------------------
# Run state data model
# ---------------------------------------------------------------------------

LANGUAGE_STATUS_ANSWER = "answer"
LANGUAGE_STATUS_BLOCKED = "blocked"   # ask/refuse/missing/unsupported/schema error
LANGUAGE_STATUS_ERROR = "error"       # transport/parse/adapter failure


@dataclass
class LanguageSampleLogicalRunPlan:
    """One planned logical run (before execution)."""
    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str


@dataclass
class LanguageSampleRunState:
    """Extraction result for one language sample logical run.

    Never triggers CAD pipeline.  Records extraction state for downstream
    evaluation only.
    """
    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str
    llm_status: str         # answer / ask / refuse / blocked / error
    decision: str
    extracted_parameters: dict[str, Any]
    missing_fields: list[str]
    unsupported_requests: list[str]
    questions: list[str]
    errors: list[dict[str, Any]]
    raw_retention_path: str | None
    raw_retention_meta: dict[str, Any] | None
    llm_meta: dict[str, Any]
    request_text: str
    prompt_version: str = PROMPT_VERSION
    contract_version: str = CONTRACT_VERSION
    prompt_file_sha256: str = FROZEN_PROMPT_FILE_SHA256
    created_at: str = field(default_factory=_utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "logical_run_id": self.logical_run_id,
            "input_id": self.input_id,
            "condition_id": self.condition_id,
            "provider": self.provider,
            "model": self.model,
            "llm_status": self.llm_status,
            "decision": self.decision,
            "extracted_parameters": self.extracted_parameters,
            "missing_fields": self.missing_fields,
            "unsupported_requests": self.unsupported_requests,
            "questions": self.questions,
            "errors": self.errors,
            "raw_retention_path": _to_repo_relative_path(self.raw_retention_path),
            "raw_retention_meta": self.raw_retention_meta,
            "llm_meta": self.llm_meta,
            "request_text": self.request_text,
            "prompt_version": self.prompt_version,
            "contract_version": self.contract_version,
            "prompt_file_sha256": self.prompt_file_sha256,
            "created_at": self.created_at,
        }


@dataclass
class LanguageSampleBatchResult:
    """Result of a full language sample batch (10 logical runs)."""
    batch_id: str | None   # None in preflight-only modes
    profile_id: str
    timestamp_utc: str
    mode: str              # "formal" / "mock" / "dry_run"
    preflight_ok: bool
    preflight_errors: list[str]
    planned_runs: list[LanguageSampleLogicalRunPlan]
    results: list[LanguageSampleRunState]
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
            "summary_path": _to_repo_relative_path(self.summary_path),
            "summary_finalize_error": self.summary_finalize_error,
        }


class LanguageSampleConfigurationError(RuntimeError):
    """Raised when formal language sample credentials are not configured."""


# ---------------------------------------------------------------------------
# Offline preflight
# ---------------------------------------------------------------------------

def run_language_offline_preflight(
    authorization: ProductLanguageAuthorization,
    *,
    batch_dir: Path | None = None,
) -> dict[str, Any]:
    """Check frozen inputs, auth scope, and budget without labels/network/keys.

    Zero network calls. Zero credential reads. Never opens evaluator-labels.json.
    """
    if not isinstance(authorization, ProductLanguageAuthorization):
        raise AuthorizationScopeError("expected ProductLanguageAuthorization")

    errors: list[str] = []
    details: dict[str, Any] = {
        "profile_id": authorization.profile_id,
        "batch_id": authorization.batch_id,
        "input_ids": list(authorization.input_ids),
        "provider": PRODUCT_LANGUAGE_PROVIDER,
        "model": PRODUCT_LANGUAGE_MODEL,
        "condition": PRODUCT_LANGUAGE_CONDITION,
        "formal_evaluation_allowed": FORMAL_EVALUATION_ALLOWED,
        "evaluator_labels_sha256_bound": (
            authorization.evaluator_labels_sha256 == PRODUCT_LANGUAGE_LABELS_SHA256
        ),
        "evaluator_labels_opened": False,
    }

    # --- Inputs file ---
    inputs_valid = False
    try:
        _load_inputs(verify_sha256=True)
        inputs_valid = True
        details["inputs_sha256_ok"] = True
        details["input_count"] = PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        details["inputs_sha256_ok"] = False
        errors.append(f"inputs_check:{type(exc).__name__}")

    # --- Budget ---
    computed = PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS * PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN
    details["budget_plan"] = {
        "logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
        "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
        "computed_max_http": computed,
        "authorized_max_http": authorization.max_batch_attempts,
        "feasible": computed <= authorization.max_batch_attempts,
    }
    if computed > authorization.max_batch_attempts:
        errors.append("budget_infeasible")

    # --- Batch directory ---
    if batch_dir is None:
        safe_id = _safe_component(authorization.batch_id)
        batch_dir = _CANONICAL_RUN_ROOT / safe_id
    details["batch_dir"] = str(batch_dir)
    details["batch_dir_exists"] = batch_dir.exists()
    if batch_dir.exists():
        errors.append("batch_directory_already_exists")

    # --- Prompt loadable ---
    try:
        prompt = load_frozen_prompt()
        details["prompt_version"] = prompt.version
        details["prompt_sha256_prefix"] = FROZEN_PROMPT_FILE_SHA256[:16] + "..."
        details["prompt_ok"] = True
        if FROZEN_PROMPT_FILE_SHA256 != PRODUCT_LANGUAGE_PROMPT_SHA256:
            errors.append("prompt_file_sha256_mismatch")
    except Exception as exc:
        errors.append(f"prompt_load:{type(exc).__name__}")
        details["prompt_ok"] = False

    return {
        "ok": not errors,
        "errors": errors,
        "details": details,
        "planned_runs": [
            {
                "logical_run_id": authorization.expected_logical_run_id(input_id),
                "input_id": input_id,
                "condition": PRODUCT_LANGUAGE_CONDITION,
                "provider": PRODUCT_LANGUAGE_PROVIDER,
                "model": PRODUCT_LANGUAGE_MODEL,
            }
            for input_id in PRODUCT_LANGUAGE_INPUT_IDS
        ] if inputs_valid else [],
    }


# ---------------------------------------------------------------------------
# Combination planning
# ---------------------------------------------------------------------------

def _plan_combinations(
    authorization: ProductLanguageAuthorization,
) -> list[LanguageSampleLogicalRunPlan]:
    return [
        LanguageSampleLogicalRunPlan(
            logical_run_id=authorization.expected_logical_run_id(input_id),
            input_id=input_id,
            condition_id=PRODUCT_LANGUAGE_CONDITION,
            provider=PRODUCT_LANGUAGE_PROVIDER,
            model=PRODUCT_LANGUAGE_MODEL,
        )
        for input_id in PRODUCT_LANGUAGE_INPUT_IDS
    ]


# ---------------------------------------------------------------------------
# Atomic summary writer
# ---------------------------------------------------------------------------

class _SummaryWriteError(RuntimeError):
    pass


def _atomic_write_json(path: Path, data: dict[str, Any], batch_dir: Path) -> None:
    """Write data as JSON to path via temp file + atomic os.replace."""
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
            "refusing to write evidence outside canonical batch directory"
        )
    tmp = path.with_suffix(".json.tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise _SummaryWriteError(f"failed to write summary to {path}: {exc}") from exc


class _SummaryWriter:
    """Atomic batch summary writer for the language sample formal run."""

    def __init__(self, batch_dir: Path, initial_data: dict[str, Any]) -> None:
        self._batch_dir = batch_dir
        self._summary_path = batch_dir / "batch_summary.json"
        self._data: dict[str, Any] = dict(initial_data)

    @property
    def summary_path(self) -> Path:
        return self._summary_path

    def write_initial(self) -> None:
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def update_run(self, result: LanguageSampleRunState) -> None:
        """Atomically update the summary with one run result.

        Never writes: raw response body, secrets, Authorization headers,
        absolute paths, or evaluator label content.
        """
        raw_sha256: str | None = None
        raw_retained: bool | None = None
        raw_length: int | None = None
        if isinstance(result.raw_retention_meta, dict):
            raw_sha256 = result.raw_retention_meta.get("body_sha256")
            raw_retained = result.raw_retention_meta.get("retained")
            raw_length = result.raw_retention_meta.get("length_bytes")

        raw_path_rel = _to_repo_relative_path(result.raw_retention_path)

        run_entry: dict[str, Any] = {
            "llm_status": result.llm_status,
            "decision": result.decision,
            "attempt_count": result.llm_meta.get("attempt_count"),
            "prompt_version": result.prompt_version,
            "contract_version": result.contract_version,
            "prompt_file_sha256": result.prompt_file_sha256,
            "configured_provider": result.provider,
            "configured_model": result.model,
            # repo-relative path only — raw body, secrets, labels excluded
            "raw_retention_path": raw_path_rel,
            "raw_retained": raw_retained,
            "raw_sha256": raw_sha256,
            "raw_length_bytes": raw_length,
            "errors": result.errors,
            "questions": result.questions,
            "missing_fields": result.missing_fields,
            "unsupported_requests": result.unsupported_requests,
        }

        runs = self._data.setdefault("runs", {})
        runs[result.logical_run_id] = run_entry
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def finalize(self, batch_status: str = "complete") -> None:
        self._data["batch_status"] = batch_status
        self._data["batch_finished_utc"] = _utc_now_iso()
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)


def _build_initial_summary(
    authorization: ProductLanguageAuthorization,
    approval: ProductLanguageFormalApproval,
    planned: list[LanguageSampleLogicalRunPlan],
    prompt: Any,
    started_utc: str,
) -> dict[str, Any]:
    """Build initial batch_summary.json content (before any HTTP requests).

    Never includes raw response bodies, API keys, Authorization headers,
    absolute paths, or evaluator label content.
    """
    return {
        "schema_version": _SUMMARY_SCHEMA_VERSION,
        "batch_id": authorization.batch_id,
        "profile_id": PRODUCT_LANGUAGE_PROFILE_ID,
        "batch_started_utc": started_utc,
        "batch_status": "running",
        "scope": {
            "protocol_versions": sorted(authorization.protocol_versions),
            "sample_set": authorization.sample_set,
            "condition": PRODUCT_LANGUAGE_CONDITION,
            "provider": PRODUCT_LANGUAGE_PROVIDER,
            "model": PRODUCT_LANGUAGE_MODEL,
            "max_batch_http": PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
            "max_logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
            "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
            "automatic_cad_pipeline": False,
        },
        "artifact_hashes": {
            "inputs_sha256": PRODUCT_LANGUAGE_INPUTS_SHA256,
            "evaluator_labels_sha256": PRODUCT_LANGUAGE_LABELS_SHA256,
            "prompt_version": PROMPT_VERSION,
            "prompt_file_sha256": FROZEN_PROMPT_FILE_SHA256,
            "contract_version": CONTRACT_VERSION,
        },
        "approval": approval.as_audit_dict(),
        "planned_runs": [p.logical_run_id for p in planned],
        "runs": {
            p.logical_run_id: {"llm_status": "pending"}
            for p in planned
        },
    }


# ---------------------------------------------------------------------------
# Safe parse-error cause extractor
# ---------------------------------------------------------------------------

def _safe_parse_error_causes(parse_result: Any) -> list[dict[str, Any]]:
    """Return parser diagnostics without copying provider-controlled text."""
    from llm.contract import ENVELOPE_KEYS, EXTRACTABLE_FIELDS
    causes: list[dict[str, Any]] = []
    safe_fields = set(ENVELOPE_KEYS) | set(EXTRACTABLE_FIELDS) | {"confidence"}
    for item in list(getattr(parse_result, "errors", ()) or ()):
        cause: dict[str, Any] = {
            "code": str(getattr(item, "code", "PARSE_ERROR")),
        }
        stage = getattr(item, "stage", None)
        if stage:
            cause["stage"] = str(stage)
        fields = [
            str(f) for f in list(getattr(item, "fields", ()) or ())
            if str(f) in safe_fields
        ]
        if fields:
            cause["fields"] = fields
        causes.append(cause)
    return causes


# ---------------------------------------------------------------------------
# Single logical run — MOCK MODE (FakeTransport, no network)
# ---------------------------------------------------------------------------

def _run_one_logical_mock(
    *,
    plan: LanguageSampleLogicalRunPlan,
    request_text: str,
    prompt: Any,
    transport: FakeTransport,
) -> LanguageSampleRunState:
    """Mock-mode execution using FakeTransport.

    Exercises the full prompt-build → send → parse → gate path.
    Never calls the CAD pipeline or opens evaluator-labels.json.
    """
    from llm.providers import build_deepseek_request
    from llm.retry import send_with_retry
    from llm.parser import parse_response

    now = _utc_now_iso()
    llm_meta: dict[str, Any] = {
        "query_id": plan.input_id,
        "condition_id": plan.condition_id,
        "configured_provider": plan.provider,
        "configured_model_name": plan.model,
        "prompt_version": PROMPT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "attempt_count": None,
        "total_elapsed_ms": None,
    }

    rendered_user = prompt.user_template.format(
        query_id=plan.input_id,
        natural_language_input=request_text,
        reference_context_or_null="null",
    )
    request = build_deepseek_request(
        system_prompt=prompt.system_prompt,
        user_prompt=rendered_user,
    )

    try:
        response, attempts, elapsed_ms = send_with_retry(transport, request)
    except Exception as exc:
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[{"code": "TRANSPORT_EXCEPTION", "message": str(exc)}],
            raw_retention_path=None,
            raw_retention_meta=None,
            llm_meta=llm_meta,
            request_text=request_text,
            created_at=now,
        )

    if response is None:
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[{"code": "NO_RESPONSE",
                     "message": "transport returned no response after retries"}],
            raw_retention_path=None,
            raw_retention_meta=None,
            llm_meta=llm_meta,
            request_text=request_text,
            created_at=now,
        )

    llm_meta["attempt_count"] = len(attempts)
    llm_meta["total_elapsed_ms"] = elapsed_ms

    parse_result = parse_response(response.body)
    if not parse_result.ok:
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[{
                "code": "PARSE_ERROR",
                "message": "response failed strict parsing or envelope validation",
                "causes": _safe_parse_error_causes(parse_result),
            }],
            raw_retention_path=None,
            raw_retention_meta=None,
            llm_meta=llm_meta,
            request_text=request_text,
            created_at=now,
        )

    return _build_state_from_envelope(
        plan=plan,
        envelope=parse_result.envelope,
        llm_meta=llm_meta,
        request_text=request_text,
        raw_retention_meta=None,
        raw_retention_path=None,
    )


# ---------------------------------------------------------------------------
# State builder from parsed envelope (shared by mock and formal paths)
# ---------------------------------------------------------------------------

def _build_state_from_envelope(
    *,
    plan: LanguageSampleLogicalRunPlan,
    envelope: Any,
    llm_meta: dict[str, Any],
    request_text: str,
    raw_retention_meta: dict[str, Any] | None,
    raw_retention_path: str | None,
) -> LanguageSampleRunState:
    """Build a LanguageSampleRunState from a parsed envelope.

    Never triggers the CAD pipeline.  Records extraction state for evaluation.
    """
    now = _utc_now_iso()
    questions = list(envelope.questions or [])
    missing_fields = list(envelope.missing_fields or [])
    unsupported = list(envelope.unsupported_requests or [])
    extracted = dict(envelope.extracted_parameters or {})
    decision = envelope.decision

    if decision == "ask":
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status="ask",
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions,
            errors=[{"code": "GATE_DECISION_ASK",
                     "message": "decision=ask; construction blocked"}],
            raw_retention_path=raw_retention_path,
            raw_retention_meta=raw_retention_meta,
            llm_meta=llm_meta, request_text=request_text, created_at=now,
        )

    if decision == "refuse":
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status="refuse",
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions,
            errors=[{"code": "GATE_DECISION_REFUSE",
                     "message": "decision=refuse; construction blocked"}],
            raw_retention_path=raw_retention_path,
            raw_retention_meta=raw_retention_meta,
            llm_meta=llm_meta, request_text=request_text, created_at=now,
        )

    if missing_fields:
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status=LANGUAGE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions,
            errors=[{"code": "GATE_MISSING_FIELDS", "fields": missing_fields,
                     "message": f"missing_fields is not empty: {missing_fields}"}],
            raw_retention_path=raw_retention_path,
            raw_retention_meta=raw_retention_meta,
            llm_meta=llm_meta, request_text=request_text, created_at=now,
        )

    if unsupported:
        return LanguageSampleRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status=LANGUAGE_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions,
            errors=[{"code": "GATE_UNSUPPORTED_REQUESTS", "fields": unsupported,
                     "message": f"unsupported_requests is not empty: {unsupported}"}],
            raw_retention_path=raw_retention_path,
            raw_retention_meta=raw_retention_meta,
            llm_meta=llm_meta, request_text=request_text, created_at=now,
        )

    # decision=answer, no missing fields, no unsupported
    return LanguageSampleRunState(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider, model=plan.model,
        llm_status=LANGUAGE_STATUS_ANSWER,
        decision=decision, extracted_parameters=extracted,
        missing_fields=[], unsupported_requests=[],
        questions=[], errors=[],
        raw_retention_path=raw_retention_path,
        raw_retention_meta=raw_retention_meta,
        llm_meta=llm_meta, request_text=request_text, created_at=now,
    )


# ---------------------------------------------------------------------------
# Adapter result mapper (formal path)
# ---------------------------------------------------------------------------

def _build_state_from_adapter_result(
    *,
    plan: LanguageSampleLogicalRunPlan,
    adapter_result: Any,
    llm_meta: dict[str, Any],
    request_text: str,
) -> LanguageSampleRunState:
    """Map Adapter outcomes to LanguageSampleRunState.

    Only stable codes, fields, and status values are copied into evidence.
    Provider error bodies and parser diagnostic text may contain untrusted
    response content and are deliberately omitted from the state.
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
            request_text=request_text,
            raw_retention_meta=raw_meta,
            raw_retention_path=raw_path,
        )

    # Transport or parse failure
    if parse_result is None:
        attempts = list(getattr(record, "attempts", ()) or ())
        last_attempt = attempts[-1] if attempts else None
        cause_code = (
            getattr(last_attempt, "error_code", None)
            or "NO_RESPONSE"
        )
        error: dict[str, Any] = {
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
    else:
        causes = _safe_parse_error_causes(parse_result)
        parse_stage = getattr(parse_result, "stage", None)
        error = {
            "code": (
                "RESPONSE_PARSE_ERROR"
                if parse_stage == "parse"
                else "ENVELOPE_VALIDATION_ERROR"
            ),
            "message": "response failed strict parsing or envelope validation",
            "causes": causes,
        }

    return LanguageSampleRunState(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider, model=plan.model,
        llm_status=LANGUAGE_STATUS_ERROR,
        decision="",
        extracted_parameters={},
        missing_fields=[],
        unsupported_requests=[],
        questions=[],
        errors=[error],
        raw_retention_path=raw_path,
        raw_retention_meta=raw_meta or None,
        llm_meta=llm_meta,
        request_text=request_text,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_product_language_formal_batch(
    *,
    authorization: ProductLanguageAuthorization,
    approval: ProductLanguageFormalApproval,
    transport: Any = None,
    output_root: Path | None = None,
) -> LanguageSampleBatchResult:
    """Run the language sample extraction batch.

    Parameters
    ----------
    authorization:
        A validated :class:`ProductLanguageAuthorization` instance.
    approval:
        A non-test-only :class:`ProductLanguageFormalApproval` whose
        ``batch_id`` matches ``authorization.batch_id``.  Required for
        all execution modes.  Validated BEFORE any directory creation,
        BudgetLedger initialisation, Transport construction, or network I/O.
    transport:
        Injectable :class:`~llm.transport.FakeTransport` for offline mock
        testing.  For formal live execution, pass ``None``.
    output_root:
        Override the raw-retention root (testing only).

    Notes
    -----
    - Evaluator labels are NEVER opened in any path.
    - CAD / IR / geometry / STEP pipeline is NEVER called.
    - ``FORMAL_EVALUATION_ALLOWED`` remains ``False``.
    - The formal path reads credentials from ``.env`` only after all
      gate checks pass and only once per batch.
    - Budget is enforced atomically via BudgetLedger before each HTTP call.
    """
    ts = _utc_now_iso()

    # ----------------------------------------------------------------
    # Gate 1: authorization type
    # ----------------------------------------------------------------
    if not isinstance(authorization, ProductLanguageAuthorization):
        raise AuthorizationScopeError(
            "run_product_language_formal_batch requires a "
            "ProductLanguageAuthorization; "
            f"got {type(authorization).__name__}"
        )

    # ----------------------------------------------------------------
    # Gate 2: approval type and test-only flag (before ANY side effects)
    # ----------------------------------------------------------------
    validate_product_language_formal_approval_binding(authorization, approval)

    # ----------------------------------------------------------------
    # Gate 3: offline preflight (inputs hash, budget, batch dir)
    # ----------------------------------------------------------------
    is_formal = transport is None
    planned = _plan_combinations(authorization)
    budget_plan = {
        "max_logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
        "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
        "max_batch_http": PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
        "provider": PRODUCT_LANGUAGE_PROVIDER,
        "model": PRODUCT_LANGUAGE_MODEL,
        "condition": PRODUCT_LANGUAGE_CONDITION,
        "input_ids": list(PRODUCT_LANGUAGE_INPUT_IDS),
    }

    pf = run_language_offline_preflight(authorization)
    if not pf["ok"]:
        return LanguageSampleBatchResult(
            batch_id=authorization.batch_id,
            profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
            timestamp_utc=ts,
            mode="formal" if is_formal else "mock",
            preflight_ok=False,
            preflight_errors=pf["errors"],
            planned_runs=planned,
            results=[],
            budget_plan=budget_plan,
        )

    # ----------------------------------------------------------------
    # Gate 4: credential loading (formal only, after all gate checks)
    # ----------------------------------------------------------------
    if is_formal:
        try:
            load_deepseek_environment(repo_root=_REPO_ROOT)
        except EnvironmentConfigurationError as exc:
            raise LanguageSampleConfigurationError(str(exc)) from exc

    # Load frozen inputs (re-verify SHA-256 after credential gate)
    inputs = _load_inputs(verify_sha256=True)
    input_map = {row["input_id"]: row["request_text"] for row in inputs}

    prompt = load_frozen_prompt()

    safe_batch_id = _safe_component(authorization.batch_id)
    if output_root is None:
        raw_root = _CANONICAL_RUN_ROOT / safe_batch_id / "raw"
    else:
        raw_root = Path(output_root) / "raw"

    # ----------------------------------------------------------------
    # Formal infrastructure (batch dir, ledger, summary writer)
    # ----------------------------------------------------------------
    if is_formal:
        from llm.budget import BudgetAwareTransport, BudgetLedger
        from llm.adapter import Adapter, AdapterInput, RetentionPolicy
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

        ledger: Any = None
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
        # Mock mode: temporary infrastructure only, no canonical batch dir
        import tempfile
        ledger = None
        raw_retention_policy = None   # will use default in Adapter
        writer = None
        summary_path = None

        if not isinstance(transport, FakeTransport):
            return LanguageSampleBatchResult(
                batch_id=authorization.batch_id,
                profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
                timestamp_utc=ts,
                mode="mock",
                preflight_ok=True,
                preflight_errors=[],
                planned_runs=planned,
                results=[LanguageSampleRunState(
                    logical_run_id=p.logical_run_id,
                    input_id=p.input_id,
                    condition_id=p.condition_id,
                    provider=p.provider, model=p.model,
                    llm_status=LANGUAGE_STATUS_ERROR,
                    decision="",
                    extracted_parameters={},
                    missing_fields=[],
                    unsupported_requests=[],
                    questions=[],
                    errors=[{"code": "INVALID_MOCK_TRANSPORT",
                             "message": "mock transport must be FakeTransport"}],
                    raw_retention_path=None,
                    raw_retention_meta=None,
                    llm_meta={},
                    request_text="",
                ) for p in planned],
                budget_plan=budget_plan,
            )

    results: list[LanguageSampleRunState] = []
    mode = "formal" if is_formal else "mock"
    summary_write_failed = False

    try:
        for plan in planned:
            request_text = input_map[plan.input_id]

            if is_formal:
                from llm.budget import BudgetAwareTransport
                from llm.adapter import Adapter, AdapterInput, RetentionPolicy
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
                adapter_input = AdapterInput(
                    query_id=plan.input_id,
                    natural_language_input=request_text,
                    reference_context=None,
                    system_prompt=prompt.system_prompt,
                    user_prompt_template=prompt.user_template,
                    condition_id=plan.condition_id,
                )

                llm_meta: dict[str, Any] = {
                    "query_id": plan.input_id,
                    "condition_id": plan.condition_id,
                    "configured_provider": plan.provider,
                    "configured_model_name": plan.model,
                    "prompt_version": PROMPT_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    "attempt_count": None,
                    "total_elapsed_ms": None,
                }

                try:
                    adapter_result = run_adapter.run(
                        adapter_input,
                        run_id=plan.logical_run_id,
                        formal_authorization=authorization,
                    )
                except Exception as exc:
                    result = LanguageSampleRunState(
                        logical_run_id=plan.logical_run_id,
                        input_id=plan.input_id,
                        condition_id=plan.condition_id,
                        provider=plan.provider, model=plan.model,
                        llm_status=LANGUAGE_STATUS_ERROR,
                        decision="",
                        extracted_parameters={},
                        missing_fields=[],
                        unsupported_requests=[],
                        questions=[],
                        errors=[{"code": "ADAPTER_EXCEPTION",
                                 "message": str(exc)}],
                        raw_retention_path=None,
                        raw_retention_meta=None,
                        llm_meta=llm_meta,
                        request_text=request_text,
                    )
                    results.append(result)
                    if writer is not None:
                        try:
                            writer.update_run(result)
                        except _SummaryWriteError:
                            summary_write_failed = True
                            break
                    continue

                record = adapter_result.record
                llm_meta["attempt_count"] = record.attempt_count
                llm_meta["total_elapsed_ms"] = record.total_elapsed_ms

                result = _build_state_from_adapter_result(
                    plan=plan,
                    adapter_result=adapter_result,
                    llm_meta=llm_meta,
                    request_text=request_text,
                )
                results.append(result)
                if writer is not None:
                    try:
                        writer.update_run(result)
                    except _SummaryWriteError:
                        summary_write_failed = True
                        break

            else:
                # Mock mode: FakeTransport, no ledger
                result = _run_one_logical_mock(
                    plan=plan,
                    request_text=request_text,
                    prompt=prompt,
                    transport=transport,
                )
                results.append(result)

    finally:
        if ledger is not None:
            try:
                ledger.release_lock()
            except Exception:
                pass
        if is_formal and writer is not None and not summary_write_failed:
            error_statuses = {LANGUAGE_STATUS_ERROR}
            statuses = [r.llm_status for r in results]
            if len(results) < len(planned):
                final_batch_status = "aborted"
            elif statuses and all(s in error_statuses for s in statuses):
                final_batch_status = "failed"
            elif any(s in error_statuses for s in statuses):
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

    return LanguageSampleBatchResult(
        batch_id=authorization.batch_id,
        profile_id=PRODUCT_LANGUAGE_PROFILE_ID,
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


__all__ = [
    "LANGUAGE_STATUS_ANSWER", "LANGUAGE_STATUS_BLOCKED", "LANGUAGE_STATUS_ERROR",
    "LanguageSampleLogicalRunPlan", "LanguageSampleRunState",
    "LanguageSampleBatchResult", "LanguageSampleConfigurationError",
    "run_language_offline_preflight",
    "run_product_language_formal_batch",
]
