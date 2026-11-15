"""Offline-only mock runner for the APP-003 *next* ten-input language sample
scope (``app003-product-language-next.v1``).

ADR-0025 PHASE BOUNDARY
-----------------------
This runner is **offline-mock-only** under ADR-0025.  The public entry point
:func:`run_product_language_next_formal_batch` accepts ONLY a
:class:`~llm.transport.FakeTransport` as ``transport``.

``transport=None`` and any non-FakeTransport are rejected at Gate 3 by
raising :class:`LanguageNextOfflineOnlyError` BEFORE any credential read,
directory creation, BudgetLedger initialisation, transport construction, or
network I/O.  No live DeepSeek execution path exists in this module.

Real execution (live DeepSeek requests) is not implemented in this phase.
It requires a new independent scope, batch, preflight, and owner approval
under a future ADR.

SAFETY GUARANTEES
-----------------
- ``FORMAL_EVALUATION_ALLOWED`` remains ``False`` and is never changed here.
- Evaluator labels (``evaluator-labels.json``) are NEVER loaded, read, opened,
  or referenced in any code path: preflight, execution, raw retention, summary,
  or logs.
- Authorization type, test-only flag, batch ID, profile, frozen inputs + hash,
  provider/model/condition, and approval binding are ALL validated BEFORE
  the transport gate.  The transport gate (Gate 3) rejects non-FakeTransport
  before any credential read, directory creation, ledger initialisation,
  transport construction, or network I/O.
- No credentials are loaded, no batch directory is created, no BudgetLedger
  is initialised, and no real transport is constructed in any path.
- Only transient transport failures are retried (connection/read timeout,
  connection interruption, HTTP 429, HTTP 5xx).  Authentication/permission
  errors, malformed requests, invalid JSON, and contract failures are not
  retried.
- No IR / CAD / geometry / STEP pipeline is ever called.  ``answer`` results
  are recorded for language extraction and evaluation only; they never trigger
  product confirmation or the CAD pipeline.
- No new generic live switch or global gate is opened.  The caller cannot
  override inputs, provider, model, condition, budget, or batch scope.
- N08 (bore-shaft-fit-conflict) and N09 (approximate-fit-clearance) are
  treated as ordinary extraction inputs.  The runner does not label them as
  covered by any existing v5 policy, nor does it inject policy-score fields
  or capability claims.  Their downstream CAD-blocking requirement is enforced
  by the existing gate (unsupported/conflict detection), not by this runner.

Offline mock testing
--------------------
Tests inject a :class:`~llm.transport.FakeTransport` via the ``transport``
parameter of :func:`run_product_language_next_formal_batch`.  The mock path
exercises the full preflight → send → parse → gate path without network I/O,
credential reads, or batch directory creation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re as _re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm.authorization import AuthorizationScopeError
from llm.contract import (
    CONTRACT_VERSION,
    FORMAL_EVALUATION_ALLOWED,
    PROMPT_VERSION,
)
from llm.product_language_next_authorization import (
    PRODUCT_LANGUAGE_NEXT_CONDITION,
    PRODUCT_LANGUAGE_NEXT_INPUT_IDS,
    PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256,
    PRODUCT_LANGUAGE_NEXT_LABELS_SHA256,
    PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS,
    PRODUCT_LANGUAGE_NEXT_MODEL,
    PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
    PRODUCT_LANGUAGE_NEXT_PROMPT_SHA256,
    PRODUCT_LANGUAGE_NEXT_PROVIDER,
    ProductLanguageNextApprovalValidationError,
    ProductLanguageNextAuthorization,
    ProductLanguageNextFormalApproval,
    validate_product_language_next_formal_approval_binding,
)
from llm.prompt_loader import FROZEN_PROMPT_FILE_SHA256, load_frozen_prompt
from llm.transport import FakeTransport

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_RUN_ROOT = _REPO_ROOT / "work" / "app003-language-next-runs"
_INPUTS_REL = Path(
    "agent-work/integration/APP-003-LANGUAGE-MATRIX-20261115-01/model-inputs.json"
)
_SAFE_RE = _re.compile(r"[^a-zA-Z0-9._-]")
_SUMMARY_SCHEMA_VERSION = "language-next-batch-summary.v1"

# Scope ID as encoded in the inputs file
_INPUTS_SCOPE_ID = PRODUCT_LANGUAGE_NEXT_PROFILE_ID


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

def _load_next_inputs(*, verify_sha256: bool = True) -> list[dict[str, str]]:
    """Load and verify frozen next language-sample inputs.

    The inputs file uses the structured format::

        {
          "scope_id": "app003-product-language-next.v1",
          "inputs": [
            {"input_id": "N01-...", "condition": "C0", "request_text": "..."},
            ...
          ]
        }

    Never reads, opens, or references ``evaluator-labels.json``.
    Raises ``ValueError`` on SHA-256 mismatch or schema error.

    Returns a list of ``{"input_id": str, "request_text": str}`` dicts in the
    same fixed order as :data:`~llm.product_language_next_authorization.PRODUCT_LANGUAGE_NEXT_INPUT_IDS`.
    """
    path = _REPO_ROOT / _INPUTS_REL
    payload = path.read_bytes()
    if verify_sha256:
        actual = _sha256_bytes(payload)
        if actual != PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256:
            raise ValueError(
                f"next language model-inputs SHA-256 mismatch: "
                f"expected {PRODUCT_LANGUAGE_NEXT_INPUTS_SHA256!r}, got {actual!r}"
            )
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("next language model-inputs must be a JSON object")
    if "scope_id" not in data or "inputs" not in data:
        raise ValueError(
            "next language model-inputs must have 'scope_id' and 'inputs' keys"
        )
    if data["scope_id"] != _INPUTS_SCOPE_ID:
        raise ValueError(
            f"next language model-inputs scope_id mismatch: "
            f"expected {_INPUTS_SCOPE_ID!r}, got {data['scope_id']!r}"
        )
    inputs = data["inputs"]
    if not isinstance(inputs, list):
        raise ValueError("next language model-inputs 'inputs' must be a JSON array")
    for row in inputs:
        if (
            not isinstance(row, dict)
            or set(row) != {"input_id", "condition", "request_text"}
            or not isinstance(row.get("input_id"), str)
            or not isinstance(row.get("condition"), str)
            or not isinstance(row.get("request_text"), str)
            or not row["request_text"].strip()
        ):
            raise ValueError(
                f"next language model-inputs row schema mismatch: {row!r}"
            )
        if row["condition"] != PRODUCT_LANGUAGE_NEXT_CONDITION:
            raise ValueError(
                f"next language model-inputs row condition mismatch: "
                f"expected {PRODUCT_LANGUAGE_NEXT_CONDITION!r}, "
                f"got {row['condition']!r}"
            )
    ids = tuple(row["input_id"] for row in inputs)
    if ids != PRODUCT_LANGUAGE_NEXT_INPUT_IDS:
        raise ValueError(
            f"next language model-input IDs/order mismatch: "
            f"expected {PRODUCT_LANGUAGE_NEXT_INPUT_IDS!r}, got {ids!r}"
        )
    # Return stripped view: input_id + request_text only (condition is validated above)
    return [{"input_id": row["input_id"], "request_text": row["request_text"]}
            for row in inputs]


# ---------------------------------------------------------------------------
# Run state data model
# ---------------------------------------------------------------------------

LANGUAGE_NEXT_STATUS_ANSWER = "answer"
LANGUAGE_NEXT_STATUS_BLOCKED = "blocked"   # ask/refuse/missing/unsupported
LANGUAGE_NEXT_STATUS_ERROR = "error"       # transport/parse/adapter failure


@dataclass
class LanguageNextLogicalRunPlan:
    """One planned logical run (before execution)."""
    logical_run_id: str
    input_id: str
    condition_id: str
    provider: str
    model: str


@dataclass
class LanguageNextRunState:
    """Extraction result for one next language sample logical run.

    Never triggers CAD pipeline.  Records extraction state for downstream
    evaluation only.

    N08/N09 notes
    -------------
    These inputs involve physical-fit conflicts and approximate-fit requests.
    The runner records whatever the model returns without asserting that
    any existing v5 policy covers them.  Policy coverage for N08/N09 is
    undefined at the current v5 policy version; they do not receive a
    policy-score field or capability annotation from this runner.
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
class LanguageNextBatchResult:
    """Result of a full next language sample batch (10 logical runs)."""
    batch_id: str | None   # None in preflight-only modes
    profile_id: str
    timestamp_utc: str
    mode: str              # "formal" / "mock" / "dry_run"
    preflight_ok: bool
    preflight_errors: list[str]
    planned_runs: list[LanguageNextLogicalRunPlan]
    results: list[LanguageNextRunState]
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


class LanguageNextOfflineOnlyError(RuntimeError):
    """Raised when a non-FakeTransport (including transport=None) is passed to
    :func:`run_product_language_next_formal_batch`.

    Under ADR-0025, this runner is offline-mock-only.  ``transport=None``
    (which would enter live formal mode) and any non-FakeTransport are rejected
    at Gate 3 BEFORE any credential read, directory creation, BudgetLedger
    initialisation, or network I/O.  Real execution requires a new independent
    scope, batch, preflight, and owner approval under a future ADR.
    """


# ---------------------------------------------------------------------------
# Offline preflight
# ---------------------------------------------------------------------------

def run_language_next_offline_preflight(
    authorization: ProductLanguageNextAuthorization,
    *,
    batch_dir: Path | None = None,
) -> dict[str, Any]:
    """Check frozen inputs, auth scope, and budget without labels/network/keys.

    Zero network calls. Zero credential reads. Never opens evaluator-labels.json.
    """
    if not isinstance(authorization, ProductLanguageNextAuthorization):
        raise AuthorizationScopeError("expected ProductLanguageNextAuthorization")

    errors: list[str] = []
    details: dict[str, Any] = {
        "profile_id": authorization.profile_id,
        "batch_id": authorization.batch_id,
        "input_ids": list(authorization.input_ids),
        "provider": PRODUCT_LANGUAGE_NEXT_PROVIDER,
        "model": PRODUCT_LANGUAGE_NEXT_MODEL,
        "condition": PRODUCT_LANGUAGE_NEXT_CONDITION,
        "formal_evaluation_allowed": FORMAL_EVALUATION_ALLOWED,
        "evaluator_labels_sha256_bound": (
            authorization.evaluator_labels_sha256 == PRODUCT_LANGUAGE_NEXT_LABELS_SHA256
        ),
        "evaluator_labels_opened": False,
    }

    # --- Inputs file ---
    inputs_valid = False
    try:
        _load_next_inputs(verify_sha256=True)
        inputs_valid = True
        details["inputs_sha256_ok"] = True
        details["input_count"] = PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        details["inputs_sha256_ok"] = False
        errors.append(f"inputs_check:{type(exc).__name__}")

    # --- Budget ---
    computed = (
        PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS
        * PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN
    )
    details["budget_plan"] = {
        "logical_runs": PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS,
        "max_attempts_per_run": PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
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
        if FROZEN_PROMPT_FILE_SHA256 != PRODUCT_LANGUAGE_NEXT_PROMPT_SHA256:
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
                "condition": PRODUCT_LANGUAGE_NEXT_CONDITION,
                "provider": PRODUCT_LANGUAGE_NEXT_PROVIDER,
                "model": PRODUCT_LANGUAGE_NEXT_MODEL,
            }
            for input_id in PRODUCT_LANGUAGE_NEXT_INPUT_IDS
        ] if inputs_valid else [],
    }


# ---------------------------------------------------------------------------
# Combination planning
# ---------------------------------------------------------------------------

def _plan_combinations(
    authorization: ProductLanguageNextAuthorization,
) -> list[LanguageNextLogicalRunPlan]:
    return [
        LanguageNextLogicalRunPlan(
            logical_run_id=authorization.expected_logical_run_id(input_id),
            input_id=input_id,
            condition_id=PRODUCT_LANGUAGE_NEXT_CONDITION,
            provider=PRODUCT_LANGUAGE_NEXT_PROVIDER,
            model=PRODUCT_LANGUAGE_NEXT_MODEL,
        )
        for input_id in PRODUCT_LANGUAGE_NEXT_INPUT_IDS
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
        raise _SummaryWriteError(
            f"failed to write summary to {path}: {exc}"
        ) from exc


class _SummaryWriter:
    """Atomic batch summary writer for the next language sample formal run."""

    def __init__(self, batch_dir: Path, initial_data: dict[str, Any]) -> None:
        self._batch_dir = batch_dir
        self._summary_path = batch_dir / "batch_summary.json"
        self._data: dict[str, Any] = dict(initial_data)

    @property
    def summary_path(self) -> Path:
        return self._summary_path

    def write_initial(self) -> None:
        _atomic_write_json(self._summary_path, self._data, self._batch_dir)

    def update_run(self, result: LanguageNextRunState) -> None:
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
    plan: LanguageNextLogicalRunPlan,
    request_text: str,
    prompt: Any,
    transport: FakeTransport,
) -> LanguageNextRunState:
    """Mock-mode execution using FakeTransport.

    Exercises the full prompt-build → send → parse → gate path.
    Never calls the CAD pipeline or opens evaluator-labels.json.

    ``answer`` results are recorded for language extraction only; they do not
    trigger the CAD pipeline or product confirmation flow.
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
        # Do not copy str(exc) — it may contain provider-controlled content.
        exc_type = type(exc).__name__
        return LanguageNextRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_NEXT_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            errors=[{"code": "TRANSPORT_EXCEPTION",
                     "exception_type": exc_type,
                     "message": "transport raised an unexpected exception"}],
            raw_retention_path=None,
            raw_retention_meta=None,
            llm_meta=llm_meta,
            request_text=request_text,
            created_at=now,
        )

    if response is None:
        return LanguageNextRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_NEXT_STATUS_ERROR,
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
        return LanguageNextRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider,
            model=plan.model,
            llm_status=LANGUAGE_NEXT_STATUS_ERROR,
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
    plan: LanguageNextLogicalRunPlan,
    envelope: Any,
    llm_meta: dict[str, Any],
    request_text: str,
    raw_retention_meta: dict[str, Any] | None,
    raw_retention_path: str | None,
) -> LanguageNextRunState:
    """Build a LanguageNextRunState from a parsed envelope.

    Never triggers the CAD pipeline.  Records extraction state for evaluation.

    ``answer`` is recorded as-is; the ``extracted_parameters`` value is the
    language extraction result only and does not automatically enter any
    construction flow.
    """
    now = _utc_now_iso()
    questions = list(envelope.questions or [])
    missing_fields = list(envelope.missing_fields or [])
    unsupported = list(envelope.unsupported_requests or [])
    extracted = dict(envelope.extracted_parameters or {})
    decision = envelope.decision

    if decision == "ask":
        return LanguageNextRunState(
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
        return LanguageNextRunState(
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
        return LanguageNextRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status=LANGUAGE_NEXT_STATUS_BLOCKED,
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
        return LanguageNextRunState(
            logical_run_id=plan.logical_run_id,
            input_id=plan.input_id,
            condition_id=plan.condition_id,
            provider=plan.provider, model=plan.model,
            llm_status=LANGUAGE_NEXT_STATUS_BLOCKED,
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
    return LanguageNextRunState(
        logical_run_id=plan.logical_run_id,
        input_id=plan.input_id,
        condition_id=plan.condition_id,
        provider=plan.provider, model=plan.model,
        llm_status=LANGUAGE_NEXT_STATUS_ANSWER,
        decision=decision, extracted_parameters=extracted,
        missing_fields=[], unsupported_requests=[],
        questions=[], errors=[],
        raw_retention_path=raw_retention_path,
        raw_retention_meta=raw_retention_meta,
        llm_meta=llm_meta, request_text=request_text, created_at=now,
    )



# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_product_language_next_formal_batch(
    *,
    authorization: ProductLanguageNextAuthorization,
    approval: ProductLanguageNextFormalApproval,
    transport: Any = None,
) -> LanguageNextBatchResult:
    """Run the next language sample extraction batch (offline mock only).

    This runner is **offline-mock-only** under ADR-0025.  ``transport`` MUST
    be a :class:`~llm.transport.FakeTransport` instance.

    ``transport=None`` and any non-:class:`~llm.transport.FakeTransport` are
    rejected at Gate 3 by raising :class:`LanguageNextOfflineOnlyError` BEFORE
    any credential read, directory creation, BudgetLedger initialisation,
    transport construction, or network I/O.

    Parameters
    ----------
    authorization:
        A validated :class:`ProductLanguageNextAuthorization` instance.
    approval:
        A non-test-only :class:`ProductLanguageNextFormalApproval` whose
        ``batch_id`` matches ``authorization.batch_id``.  Validated BEFORE
        the transport gate and before any side effects.
    transport:
        MUST be a :class:`~llm.transport.FakeTransport` instance.  Passing
        ``None`` or any other value raises :class:`LanguageNextOfflineOnlyError`
        at Gate 3, before any credential read, directory creation, ledger
        initialisation, or network I/O.

    Notes
    -----
    - Evaluator labels are NEVER opened in any path.
    - CAD / IR / geometry / STEP pipeline is NEVER called.
    - ``FORMAL_EVALUATION_ALLOWED`` remains ``False``.
    - No credentials are loaded, no batch directory is created, no BudgetLedger
      is initialised, and no real transport is constructed.
    """
    ts = _utc_now_iso()

    # ----------------------------------------------------------------
    # Gate 1: authorization type
    # ----------------------------------------------------------------
    if not isinstance(authorization, ProductLanguageNextAuthorization):
        raise AuthorizationScopeError(
            "run_product_language_next_formal_batch requires a "
            "ProductLanguageNextAuthorization; "
            f"got {type(authorization).__name__}"
        )

    # ----------------------------------------------------------------
    # Gate 2: approval type and test-only flag (before ANY side effects)
    # ----------------------------------------------------------------
    validate_product_language_next_formal_approval_binding(authorization, approval)

    # ----------------------------------------------------------------
    # Gate 3: ADR-0025 phase boundary — offline-mock-only.
    # Must be a FakeTransport.  transport=None (which would enter live
    # formal mode) is not permitted in this phase.  Raised BEFORE any
    # credential read, directory creation, BudgetLedger init, or network I/O.
    # ----------------------------------------------------------------
    if not isinstance(transport, FakeTransport):
        raise LanguageNextOfflineOnlyError(
            "run_product_language_next_formal_batch is offline-mock-only under "
            "ADR-0025: a FakeTransport instance is required as 'transport'.  "
            "transport=None (live formal mode) is not permitted in this phase.  "
            "No credentials have been read, no directories created, and no "
            "network calls have been made.  Real execution requires a new "
            "independent scope, batch, preflight, and owner approval."
        )

    # ----------------------------------------------------------------
    # Gate 4: offline preflight (inputs hash, budget, batch dir check)
    # ----------------------------------------------------------------
    planned = _plan_combinations(authorization)
    budget_plan = {
        "max_logical_runs": PRODUCT_LANGUAGE_NEXT_MAX_LOGICAL_RUNS,
        "max_attempts_per_run": PRODUCT_LANGUAGE_NEXT_MAX_ATTEMPTS_PER_RUN,
        "max_batch_http": PRODUCT_LANGUAGE_NEXT_MAX_BATCH_HTTP,
        "provider": PRODUCT_LANGUAGE_NEXT_PROVIDER,
        "model": PRODUCT_LANGUAGE_NEXT_MODEL,
        "condition": PRODUCT_LANGUAGE_NEXT_CONDITION,
        "input_ids": list(PRODUCT_LANGUAGE_NEXT_INPUT_IDS),
    }

    pf = run_language_next_offline_preflight(authorization)
    if not pf["ok"]:
        return LanguageNextBatchResult(
            batch_id=authorization.batch_id,
            profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
            timestamp_utc=ts,
            mode="mock",
            preflight_ok=False,
            preflight_errors=pf["errors"],
            planned_runs=planned,
            results=[],
            budget_plan=budget_plan,
        )

    # Load frozen inputs (verify SHA-256)
    inputs = _load_next_inputs(verify_sha256=True)
    input_map = {row["input_id"]: row["request_text"] for row in inputs}

    prompt = load_frozen_prompt()

    results: list[LanguageNextRunState] = []
    for plan in planned:
        result = _run_one_logical_mock(
            plan=plan,
            request_text=input_map[plan.input_id],
            prompt=prompt,
            transport=transport,
        )
        results.append(result)

    return LanguageNextBatchResult(
        batch_id=authorization.batch_id,
        profile_id=PRODUCT_LANGUAGE_NEXT_PROFILE_ID,
        timestamp_utc=ts,
        mode="mock",
        preflight_ok=True,
        preflight_errors=[],
        planned_runs=planned,
        results=results,
        budget_plan=budget_plan,
        summary_path=None,
        summary_finalize_error=None,
    )


__all__ = [
    "LANGUAGE_NEXT_STATUS_ANSWER", "LANGUAGE_NEXT_STATUS_BLOCKED",
    "LANGUAGE_NEXT_STATUS_ERROR",
    "LanguageNextLogicalRunPlan", "LanguageNextRunState",
    "LanguageNextBatchResult", "LanguageNextOfflineOnlyError",
    "run_language_next_offline_preflight",
    "run_product_language_next_formal_batch",
]
