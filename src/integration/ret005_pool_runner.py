"""RET-005 single-family reference pool product runner.

Product-mode controlled entry point for the RET-005 reference pool.
Accepts a user request text plus a user-selected reference pool (3–5 sample_ids),
assembles C0 and C1 contexts via the shared pool_context assembler, runs LLM
extraction via FakeTransport (offline) or a real transport (formal mode), enforces
user parameter priority before CAD, and isolates every confirmed run to its own
output directory.

Safety guarantees
-----------------
- Evaluator labels are NEVER passed to context assembly, the Adapter, transports,
  the prompt, or any logger.
- Pool allowlist is verified before any context assembly.
- User explicit parameters extracted from text take priority over model results;
  any conflict is returned as a stable error before CAD.
- CAD (run_pipeline) is only called after:
    1. The model returns decision=answer with Schema passing.
    2. User provides explicit confirmation (confirmed=True).
- Each confirmed run writes its STEP to an isolated per-run directory.
- No other run's STEP files are ever returned.
- FORMAL_EVALUATION_ALLOWED remains False; this runner does not change it.

Offline / mock mode
-------------------
Inject a ``FakeTransport`` via the ``transport`` parameter.  The offline path
exercises the full: pool validation → context assembly → extraction gate →
user-param priority check → confirmation gate → pipeline path.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm.conditions import extract_bore_d_mm, CONDITION_C0, CONDITION_C1
from llm.contract import (
    CONTRACT_VERSION,
    ENVELOPE_KEYS,
    EXTRACTABLE_FIELDS,
    FORMAL_EVALUATION_ALLOWED,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)
from llm.input_projection import ProjectedCase
from llm.pool_context import (
    assemble_pool_c0,
    assemble_pool_c1,
    check_user_param_priority,
    extract_explicit_parameters,
    _POOL_CANDIDATE_ROLE,
)
from llm.prompt_loader import load_frozen_prompt
from llm.transport import FakeTransport, TransportResponse
from retrieval.config import REPO_ROOT
from retrieval.pool import ReferencePool, PoolError, MANIFEST_REL_PATH, ALLOWED_POOL_ROLE


# ---------------------------------------------------------------------------
# Status constants (mirror product_live_runner vocabulary)
# ---------------------------------------------------------------------------

POOL_STATUS_NEEDS_CONFIRMATION = "needs_confirmation"
POOL_STATUS_BLOCKED = "blocked"
POOL_STATUS_SUCCEEDED = "succeeded"
POOL_STATUS_FAILED = "failed"
POOL_STATUS_ERROR = "error"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PoolRunState:
    """The state of one RET-005 pool logical run.

    Returned BEFORE any CAD call.  status=needs_confirmation means the LLM
    extraction passed all gates and the run is waiting for user confirmation.
    """

    run_id: str
    condition_id: str
    # Extraction result
    llm_status: str
    product_status: str
    decision: str
    extracted_parameters: dict[str, Any]
    explicit_parameters: dict[str, Any]       # from user text, not model
    missing_fields: list[str]
    unsupported_requests: list[str]
    questions: list[str]
    conflicts: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    # Context provenance
    pool_sample_ids: list[str]
    reference_context_sha256: str | None = None
    candidate_source_ids: list[str] = field(default_factory=list)
    bore_d_used_for_query: float | None = None
    # Confirmation state
    confirmed: bool = False
    confirmed_at: str | None = None
    # Pipeline result
    pipeline_status: str | None = None
    pipeline_stage: str | None = None
    pipeline_run_dir: str | None = None
    step_path: str | None = None
    ir_index: dict[str, Any] | None = None
    # LLM metadata
    llm_meta: dict[str, Any] = field(default_factory=dict)
    request_text: str = ""
    prompt_version: str = PROMPT_VERSION
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "condition_id": self.condition_id,
            "llm_status": self.llm_status,
            "product_status": self.product_status,
            "decision": self.decision,
            "extracted_parameters": self.extracted_parameters,
            "explicit_parameters": self.explicit_parameters,
            "missing_fields": self.missing_fields,
            "unsupported_requests": self.unsupported_requests,
            "questions": self.questions,
            "conflicts": self.conflicts,
            "errors": self.errors,
            "pool_sample_ids": self.pool_sample_ids,
            "reference_context_sha256": self.reference_context_sha256,
            "candidate_source_ids": self.candidate_source_ids,
            "bore_d_used_for_query": self.bore_d_used_for_query,
            "confirmed": self.confirmed,
            "confirmed_at": self.confirmed_at,
            "pipeline_status": self.pipeline_status,
            "pipeline_stage": self.pipeline_stage,
            "pipeline_run_dir": self.pipeline_run_dir,
            "step_path": self.step_path,
            "ir_index": self.ir_index,
            "llm_meta": self.llm_meta,
            "request_text": self.request_text,
            "prompt_version": self.prompt_version,
            "contract_version": self.contract_version,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pool(sample_ids: list[str], *, repo_root: Path | None = None) -> ReferencePool:
    """Load the RET-001 manifest and build a ReferencePool from sample_ids."""
    root = repo_root or _REPO_ROOT
    manifest_path = root / MANIFEST_REL_PATH
    return ReferencePool.from_manifest(
        sample_ids,
        manifest_path=manifest_path,
        repo_root=root,
    )


def _run_extraction(
    *,
    run_id: str,
    condition_id: str,
    request_text: str,
    pool_sample_ids: list[str],
    transport: Any,
    prompt: Any,
    repo_root: Path | None = None,
) -> PoolRunState:
    """Run extraction for one (request, condition) pair using the provided transport.

    Does NOT call run_pipeline — that only happens after explicit confirmation.

    Parameters
    ----------
    run_id:
        Unique identifier for this run.
    condition_id:
        ``"C0"`` or ``"C1"``.
    request_text:
        User's natural-language request.
    pool_sample_ids:
        3–5 user-selected sample_ids for the reference pool (required for C1).
    transport:
        A ``FakeTransport`` for offline/test runs.
    prompt:
        Loaded frozen prompt object.
    repo_root:
        Repository root override.
    """
    from llm.providers import build_deepseek_request
    from llm.retry import send_with_retry
    from llm.parser import parse_response
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    now = _utc_now_iso()

    # --- Build pool and assemble context ---
    pool: ReferencePool | None = None
    assembled_error: str | None = None
    assembled_error_code: str | None = None
    reference_context: str | None = None
    reference_context_sha256: str | None = None
    candidate_source_ids: tuple = ()
    bore_d_used: float | None = None

    if condition_id == CONDITION_C1:
        try:
            pool = _load_pool(pool_sample_ids, repo_root=repo_root)
        except PoolError as exc:
            assembled_error = f"POOL_LOAD_ERROR: {exc.code}: {exc.message}"
            assembled_error_code = exc.code
        if pool is not None:
            case = ProjectedCase(run_id, request_text, None, ("bore_d",))
            assembled = assemble_pool_c1(case, pool)
            if assembled.blocked_reason:
                assembled_error = assembled.blocked_reason
                assembled_error_code = assembled.error_code or "POOL_C1_BLOCKED"
            else:
                reference_context = assembled.reference_context
                reference_context_sha256 = assembled.reference_context_sha256
                candidate_source_ids = assembled.candidate_source_ids or ()
                bore_d_used = assembled.bore_d_used_for_query
    else:
        # C0: no pool context
        case = ProjectedCase(run_id, request_text, None, ("bore_d",))
        assembled = assemble_pool_c0(case)
        # C0 is always unblocked

    if assembled_error is not None:
        return PoolRunState(
            run_id=run_id,
            condition_id=condition_id,
            llm_status="blocked",
            product_status=POOL_STATUS_BLOCKED,
            decision="",
            extracted_parameters={},
            explicit_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": assembled_error_code or "CONTEXT_ASSEMBLY_BLOCKED",
                     "message": assembled_error}],
            pool_sample_ids=list(pool_sample_ids),
            request_text=request_text,
        )

    # --- Render prompt ---
    rendered_user = prompt.user_template.format(
        query_id=run_id,
        natural_language_input=request_text,
        reference_context_or_null=reference_context if reference_context else "null",
    )
    request = build_deepseek_request(
        system_prompt=prompt.system_prompt,
        user_prompt=rendered_user,
    )

    llm_meta: dict[str, Any] = {
        "run_id": run_id,
        "condition_id": condition_id,
        "prompt_version": PROMPT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "reference_context_sha256": reference_context_sha256,
        "candidate_source_ids": list(candidate_source_ids),
        "bore_d_used_for_query": bore_d_used,
    }

    # --- Send via transport (with retry) ---
    try:
        response, attempts, elapsed_ms = send_with_retry(transport, request)
    except Exception as exc:
        return PoolRunState(
            run_id=run_id,
            condition_id=condition_id,
            llm_status="error",
            product_status=POOL_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            explicit_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "TRANSPORT_EXCEPTION", "message": str(exc)}],
            pool_sample_ids=list(pool_sample_ids),
            llm_meta=llm_meta,
            request_text=request_text,
        )

    if response is None:
        return PoolRunState(
            run_id=run_id,
            condition_id=condition_id,
            llm_status="error",
            product_status=POOL_STATUS_ERROR,
            decision="",
            extracted_parameters={},
            explicit_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "NO_RESPONSE",
                     "message": "transport returned no response after retries"}],
            pool_sample_ids=list(pool_sample_ids),
            llm_meta=llm_meta,
            request_text=request_text,
        )

    llm_meta["attempt_count"] = len(attempts)
    llm_meta["total_elapsed_ms"] = elapsed_ms

    # --- Parse response ---
    parse_result = parse_response(response.body)
    if not parse_result.ok:
        return PoolRunState(
            run_id=run_id,
            condition_id=condition_id,
            llm_status="error",
            product_status=POOL_STATUS_BLOCKED,
            decision="",
            extracted_parameters={},
            explicit_parameters={},
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            errors=[{"code": "PARSE_ERROR",
                     "message": "response failed strict parsing or envelope validation"}],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta,
            request_text=request_text,
        )

    envelope = parse_result.envelope
    questions: list[str] = list(envelope.questions or [])
    missing_fields: list[str] = list(envelope.missing_fields or [])
    unsupported: list[str] = list(envelope.unsupported_requests or [])
    extracted = dict(envelope.extracted_parameters or {})
    decision = envelope.decision

    # --- Fail-closed gate checks ---
    if decision == "ask":
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="ask", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters={},
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_DECISION_ASK",
                     "message": "decision=ask; construction blocked until questions answered"}],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    if decision == "refuse":
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="refuse", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters={},
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_DECISION_REFUSE",
                     "message": "decision=refuse; construction blocked"}],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    if missing_fields:
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="blocked", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters={},
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_MISSING_FIELDS", "fields": missing_fields,
                     "message": f"missing_fields is not empty: {missing_fields}"}],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    if unsupported:
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="blocked", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters={},
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=[],
            errors=[{"code": "GATE_UNSUPPORTED_REQUESTS", "fields": unsupported,
                     "message": f"unsupported_requests is not empty: {unsupported}"}],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    # --- User parameter priority check (before Schema/CAD) ---
    explicit_params = extract_explicit_parameters(request_text)
    param_conflicts = check_user_param_priority(explicit_params, extracted)
    if param_conflicts:
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="blocked", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters=explicit_params,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=param_conflicts,
            errors=[{
                "code": "USER_PARAM_CONFLICT",
                "conflicts": param_conflicts,
                "message": (
                    "model extracted parameters conflict with user explicit text; "
                    "user parameter takes priority; construction blocked"
                ),
            }],
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    # --- Schema preflight (no CAD) ---
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    projection = project_to_cad003(extracted)
    if not projection.ok:
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="blocked", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters=explicit_params,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=list(projection.errors),
            errors=list(projection.errors),
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        schema_errors = [e.as_dict() for e in schema_result.errors]
        return PoolRunState(
            run_id=run_id, condition_id=condition_id,
            llm_status="blocked", product_status=POOL_STATUS_BLOCKED,
            decision=decision, extracted_parameters=extracted,
            explicit_parameters=explicit_params,
            missing_fields=missing_fields, unsupported_requests=unsupported,
            questions=questions, conflicts=schema_errors,
            errors=schema_errors,
            pool_sample_ids=list(pool_sample_ids),
            reference_context_sha256=reference_context_sha256,
            candidate_source_ids=list(candidate_source_ids),
            bore_d_used_for_query=bore_d_used,
            llm_meta=llm_meta, request_text=request_text,
        )

    # All gates pass: needs_confirmation.  CAD is NOT called here.
    return PoolRunState(
        run_id=run_id, condition_id=condition_id,
        llm_status="answer", product_status=POOL_STATUS_NEEDS_CONFIRMATION,
        decision=decision, extracted_parameters=extracted,
        explicit_parameters=explicit_params,
        missing_fields=[], unsupported_requests=[],
        questions=[], conflicts=[],
        errors=[],
        pool_sample_ids=list(pool_sample_ids),
        reference_context_sha256=reference_context_sha256,
        candidate_source_ids=list(candidate_source_ids),
        bore_d_used_for_query=bore_d_used,
        llm_meta=llm_meta, request_text=request_text,
    )


# ---------------------------------------------------------------------------
# Confirm a run → CAD
# ---------------------------------------------------------------------------


def confirm_pool_run(
    state: PoolRunState,
    *,
    confirmed: bool,
    output_root: Path | None = None,
) -> PoolRunState:
    """Execute the CAD pipeline after explicit user confirmation.

    This is the ONLY code path that calls run_pipeline() for pool runs.

    Parameters
    ----------
    state:
        A ``PoolRunState`` with product_status=needs_confirmation.
    confirmed:
        Must be ``True`` to proceed.  ``False`` returns a blocked state with
        code ``CONFIRMATION_REJECTED``.
    output_root:
        Pipeline output root.  Each run writes to its own isolated subdirectory
        ``<output_root>/<run_id>/`` so no two runs can overwrite each other.

    Returns
    -------
    PoolRunState
        New state with product_status=succeeded, failed, or blocked.
        Original state is never mutated.
    """
    from llm.contract import CONTRACT_VERSION as _CV, PROMPT_VERSION as _PV, EXTRACTABLE_FIELDS as _EF
    from integration.pipeline import run_pipeline
    import json as _json

    now = _utc_now_iso()
    root = Path(output_root) if output_root else (_REPO_ROOT / "work" / "ret005-pool-runs")

    # Gate 1: must be needs_confirmation
    if state.product_status != POOL_STATUS_NEEDS_CONFIRMATION:
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_BLOCKED,
            decision=state.decision, extracted_parameters=state.extracted_parameters,
            explicit_parameters=state.explicit_parameters,
            missing_fields=state.missing_fields, unsupported_requests=state.unsupported_requests,
            questions=state.questions, conflicts=state.conflicts,
            errors=[{"code": "NOT_CONFIRMABLE",
                     "message": f"run is in status={state.product_status!r}; "
                                "only needs_confirmation runs can be confirmed"}],
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )

    # Gate 2: confirmed must be True
    if not confirmed:
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_BLOCKED,
            decision=state.decision, extracted_parameters=state.extracted_parameters,
            explicit_parameters=state.explicit_parameters,
            missing_fields=state.missing_fields, unsupported_requests=state.unsupported_requests,
            questions=state.questions, conflicts=state.conflicts,
            errors=[{"code": "CONFIRMATION_REJECTED",
                     "message": "confirmed=False; construction blocked"}],
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True,
            confirmed_at=now,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )

    # Schema re-validation with merged params
    from llm.projector import project_to_cad003
    from schema.set_screw_shaft_collar import validate_parameters

    merged = dict(state.extracted_parameters)
    projection = project_to_cad003(merged)
    if not projection.ok:
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_BLOCKED,
            decision=state.decision, extracted_parameters=state.extracted_parameters,
            explicit_parameters=state.explicit_parameters,
            missing_fields=state.missing_fields, unsupported_requests=state.unsupported_requests,
            questions=state.questions, conflicts=list(projection.errors),
            errors=list(projection.errors),
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True, confirmed_at=now,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )

    schema_result = validate_parameters(projection.projected_payload)
    if not schema_result.ok:
        schema_errors = [e.as_dict() for e in schema_result.errors]
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_BLOCKED,
            decision=state.decision, extracted_parameters=state.extracted_parameters,
            explicit_parameters=state.explicit_parameters,
            missing_fields=state.missing_fields, unsupported_requests=state.unsupported_requests,
            questions=state.questions, conflicts=schema_errors, errors=schema_errors,
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True, confirmed_at=now,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )

    # Build envelope for pipeline
    safe = {k: v for k, v in merged.items() if k in _EF and v is not None}
    evidence = [
        {"field": k, "quote": str(v), "source": "user_input"}
        for k, v in safe.items()
    ]
    envelope_obj = {
        "contract_version": _CV, "prompt_version": _PV,
        "decision": "answer", "extracted_parameters": safe,
        "unsupported_requests": [], "evidence": evidence,
        "missing_fields": [], "questions": [], "confidence": None,
    }
    envelope_json = _json.dumps(envelope_obj, ensure_ascii=False)

    # Isolated per-run output directory
    run_output_root = root / state.run_id

    # Call run_pipeline()
    try:
        pipeline_result = run_pipeline(
            request_text=state.request_text,
            raw_envelope=envelope_json,
            output_root=run_output_root,
            envelope_fixture_label=f"ret005_pool_{state.run_id}",
        )
    except Exception as exc:
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_FAILED,
            decision=state.decision, extracted_parameters=state.extracted_parameters,
            explicit_parameters=state.explicit_parameters,
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[],
            errors=[{"code": "PIPELINE_EXCEPTION",
                     "message": f"{type(exc).__name__}: {str(exc)[:300]}"}],
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True, confirmed_at=now,
            pipeline_status="error", pipeline_stage="pipeline_exception",
            llm_meta=state.llm_meta, request_text=state.request_text,
        )

    if pipeline_result.status == "success":
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_SUCCEEDED,
            decision=state.decision, extracted_parameters=merged,
            explicit_parameters=state.explicit_parameters,
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[],
            errors=[],
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True, confirmed_at=now,
            pipeline_status=pipeline_result.status,
            pipeline_stage=pipeline_result.stage,
            pipeline_run_dir=pipeline_result.run_dir,
            step_path=pipeline_result.step_path,
            ir_index=pipeline_result.ir_index,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )
    else:
        return PoolRunState(
            run_id=state.run_id, condition_id=state.condition_id,
            llm_status=state.llm_status, product_status=POOL_STATUS_FAILED,
            decision=state.decision, extracted_parameters=merged,
            explicit_parameters=state.explicit_parameters,
            missing_fields=[], unsupported_requests=[], questions=[], conflicts=[],
            errors=pipeline_result.errors,
            pool_sample_ids=state.pool_sample_ids,
            reference_context_sha256=state.reference_context_sha256,
            candidate_source_ids=state.candidate_source_ids,
            confirmed=True, confirmed_at=now,
            pipeline_status=pipeline_result.status,
            pipeline_stage=pipeline_result.stage,
            pipeline_run_dir=pipeline_result.run_dir,
            step_path=None,  # never expose a failed step
            ir_index=None,
            llm_meta=state.llm_meta, request_text=state.request_text,
        )


# ---------------------------------------------------------------------------
# Pool service (injectable, offline-safe)
# ---------------------------------------------------------------------------


class Ret005PoolService:
    """Injectable pool service for offline and product-mode pool runs.

    Usage:
        transport = FakeTransport()
        transport.queue_response(TransportResponse(...))
        service = Ret005PoolService(transport=transport)
        state = service.extract("bore_d=24 mm 轴环", ["sample1", "sample2", "sample3"])
        if state.product_status == "needs_confirmation":
            final = service.confirm(state.run_id, confirmed=True)

    Security guarantees:
    - Evaluator labels never enter the context, transport, or prompt.
    - Pool allowlist is checked before any context assembly.
    - User explicit parameters take priority; conflicts block before CAD.
    - CAD only runs after explicit confirmation (confirmed=True).
    - Each confirmed run writes to its own isolated directory.
    - No other run's STEP file is returned.
    - FORMAL_EVALUATION_ALLOWED is never changed.
    - extract() returns a frozen copy; callers cannot mutate the internal state.
    - confirm() re-validates the state fingerprint before calling run_pipeline.
    - Duplicate confirmations are rejected.
    - Only exact FakeTransport (not subclasses) is accepted.
    """

    def __init__(
        self,
        transport: FakeTransport,
        *,
        output_root: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        # P1c: exact type check — subclasses that override send() must not bypass
        if type(transport) is not FakeTransport:
            raise TypeError(
                "Ret005PoolService requires an exact FakeTransport instance; "
                "subclasses that override send() are not permitted.  "
                "Formal live transport is not yet authorized for RET-005."
            )
        self._transport = transport
        self._output_root = Path(output_root) if output_root else (
            _REPO_ROOT / "work" / "ret005-pool-runs"
        )
        self._repo_root: Path | None = Path(repo_root) if repo_root else None
        self._runs: dict[str, PoolRunState] = {}
        self._confirmable_fingerprints: dict[str, str] = {}
        self._confirmed: set[str] = set()

    @staticmethod
    def _state_fingerprint(state: PoolRunState) -> str:
        """Compute a stable fingerprint over the extraction state.

        This is used to detect any mutation between extract() and confirm().
        The fingerprint covers all fields that affect the confirmation decision:
        product_status, extracted_parameters, explicit_parameters, decision,
        missing_fields, unsupported_requests, conflicts, errors,
        reference_context_sha256, and the run_id.
        """
        payload = json.dumps({
            "run_id": state.run_id,
            "product_status": state.product_status,
            "decision": state.decision,
            "extracted_parameters": state.extracted_parameters,
            "explicit_parameters": state.explicit_parameters,
            "missing_fields": state.missing_fields,
            "unsupported_requests": state.unsupported_requests,
            "conflicts": state.conflicts,
            "reference_context_sha256": state.reference_context_sha256,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _frozen_copy(state: PoolRunState) -> PoolRunState:
        """Return a copy of the state that callers cannot mutate to affect
        the internal service state.

        The returned object is a new PoolRunState with deep-copied dict/list
        fields.  Even if the caller mutates the returned copy, the service's
        internal state (stored separately) is unaffected.
        """
        import copy as _copy
        return _copy.deepcopy(state)

    def extract(
        self,
        request_text: str,
        pool_sample_ids: list[str],
        condition_id: str = CONDITION_C1,
    ) -> PoolRunState:
        """Run extraction for one (request, pool, condition) combination.

        Never calls run_pipeline — only confirm() does that.
        Returns a frozen copy of the state; the internal copy is stored
        separately so callers cannot tamper with it.
        """
        run_id = uuid.uuid4().hex
        prompt = load_frozen_prompt()
        state = _run_extraction(
            run_id=run_id,
            condition_id=condition_id,
            request_text=request_text,
            pool_sample_ids=list(pool_sample_ids),
            transport=self._transport,
            prompt=prompt,
            repo_root=self._repo_root,
        )
        # Store internal state — callers never get a reference to this object
        self._runs[run_id] = state
        # Record the fingerprint for confirmation validation
        if state.product_status == POOL_STATUS_NEEDS_CONFIRMATION:
            self._confirmable_fingerprints[run_id] = self._state_fingerprint(state)
        # Return a deep copy so callers cannot mutate the internal state
        return self._frozen_copy(state)

    def confirm(self, run_id: str, confirmed: bool) -> PoolRunState | None:
        """Confirm a pending extraction result and optionally run the CAD pipeline.

        Returns None if run_id is unknown.  Calls confirm_pool_run() — the only
        path to run_pipeline() for pool runs.

        Security checks:
        - run_id must exist in the internal registry.
        - The run must not have already been confirmed (duplicate rejection).
        - The internal state fingerprint must match the one recorded at
          extraction time.  Any mutation (e.g. caller changes bore_d) is
          detected and the confirmation is rejected.
        - The state must still be needs_confirmation.
        - User explicit parameters are re-checked against extracted parameters.
        """
        if not isinstance(confirmed, bool):
            raise TypeError("confirmed must be a bool")
        state = self._runs.get(run_id)
        if state is None:
            return None

        # Reject duplicate confirmations
        if run_id in self._confirmed:
            return PoolRunState(
                run_id=run_id,
                condition_id=state.condition_id,
                llm_status=state.llm_status,
                product_status=POOL_STATUS_BLOCKED,
                decision=state.decision,
                extracted_parameters=dict(state.extracted_parameters),
                explicit_parameters=dict(state.explicit_parameters),
                missing_fields=list(state.missing_fields),
                unsupported_requests=list(state.unsupported_requests),
                questions=list(state.questions),
                conflicts=list(state.conflicts),
                errors=[{"code": "CONFIRMATION_ALREADY_USED",
                         "message": "this run has already been confirmed; "
                                    "duplicate confirmation is rejected"}],
                pool_sample_ids=list(state.pool_sample_ids),
                reference_context_sha256=state.reference_context_sha256,
                candidate_source_ids=list(state.candidate_source_ids),
                llm_meta=dict(state.llm_meta),
                request_text=state.request_text,
            )

        # Validate state fingerprint — detect any mutation between extract and confirm
        expected_fingerprint = self._confirmable_fingerprints.get(run_id)
        if expected_fingerprint is None:
            # Not a confirmable run (was never needs_confirmation)
            return PoolRunState(
                run_id=run_id,
                condition_id=state.condition_id,
                llm_status=state.llm_status,
                product_status=POOL_STATUS_BLOCKED,
                decision=state.decision,
                extracted_parameters=dict(state.extracted_parameters),
                explicit_parameters=dict(state.explicit_parameters),
                missing_fields=list(state.missing_fields),
                unsupported_requests=list(state.unsupported_requests),
                questions=list(state.questions),
                conflicts=list(state.conflicts),
                errors=[{"code": "NOT_CONFIRMABLE",
                         "message": f"run is in status={state.product_status!r}; "
                                    "only needs_confirmation runs can be confirmed"}],
                pool_sample_ids=list(state.pool_sample_ids),
                reference_context_sha256=state.reference_context_sha256,
                candidate_source_ids=list(state.candidate_source_ids),
                llm_meta=dict(state.llm_meta),
                request_text=state.request_text,
            )

        actual_fingerprint = self._state_fingerprint(state)
        if actual_fingerprint != expected_fingerprint:
            # State was mutated between extract() and confirm() — reject
            return PoolRunState(
                run_id=run_id,
                condition_id=state.condition_id,
                llm_status=state.llm_status,
                product_status=POOL_STATUS_BLOCKED,
                decision=state.decision,
                extracted_parameters=dict(state.extracted_parameters),
                explicit_parameters=dict(state.explicit_parameters),
                missing_fields=list(state.missing_fields),
                unsupported_requests=list(state.unsupported_requests),
                questions=list(state.questions),
                conflicts=list(state.conflicts),
                errors=[{"code": "CONFIRMATION_STATE_CHANGED",
                         "message": "extraction state was mutated between extract "
                                    "and confirm; confirmation rejected to prevent "
                                    "tampering with user explicit parameters"}],
                pool_sample_ids=list(state.pool_sample_ids),
                reference_context_sha256=state.reference_context_sha256,
                candidate_source_ids=list(state.candidate_source_ids),
                llm_meta=dict(state.llm_meta),
                request_text=state.request_text,
            )

        # Re-validate user explicit parameters vs model extracted parameters
        param_conflicts = check_user_param_priority(
            state.explicit_parameters, state.extracted_parameters,
        )
        if param_conflicts:
            return PoolRunState(
                run_id=run_id,
                condition_id=state.condition_id,
                llm_status=state.llm_status,
                product_status=POOL_STATUS_BLOCKED,
                decision=state.decision,
                extracted_parameters=dict(state.extracted_parameters),
                explicit_parameters=dict(state.explicit_parameters),
                missing_fields=list(state.missing_fields),
                unsupported_requests=list(state.unsupported_requests),
                questions=list(state.questions),
                conflicts=param_conflicts,
                errors=[{"code": "USER_PARAM_CONFLICT",
                         "conflicts": param_conflicts,
                         "message": "model extracted parameters conflict with user "
                                    "explicit text at confirmation time"}],
                pool_sample_ids=list(state.pool_sample_ids),
                reference_context_sha256=state.reference_context_sha256,
                candidate_source_ids=list(state.candidate_source_ids),
                llm_meta=dict(state.llm_meta),
                request_text=state.request_text,
            )

        # All checks passed — mark as confirmed and call pipeline
        self._confirmed.add(run_id)
        new_state = confirm_pool_run(
            state,
            confirmed=confirmed,
            output_root=self._output_root,
        )
        # Store confirmed result under a separate key (run isolation)
        self._runs[run_id + "__confirmed"] = new_state
        return self._frozen_copy(new_state)

    def get(self, run_id: str) -> PoolRunState | None:
        """Return the latest state for a run_id (frozen copy)."""
        state = (
            self._runs.get(run_id + "__confirmed")
            or self._runs.get(run_id)
        )
        if state is None:
            return None
        return self._frozen_copy(state)

    def get_step_bytes_secure(self, run_id: str) -> bytes | None:
        """Return STEP bytes for a succeeded confirmed run with 5-layer security.

        Never exposes absolute paths or other run STEP files.  Returns None if
        run is not confirmed+succeeded, or if path/sha256 security checks fail.
        """
        state = self._runs.get(run_id + "__confirmed")
        if state is None:
            return None
        if state.product_status != POOL_STATUS_SUCCEEDED:
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
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            return None
        return content


def list_eligible_pool_samples() -> list[dict[str, Any]]:
    """List all manifest samples eligible for the reference pool (retrieval_source only).

    Returns a list of safe display dicts with sample_id, family_id,
    parameters_normalized, validation status, and source summary.
    Never includes evaluator labels, IR content, STEP content, or held-out truth.
    """
    manifest_path = _REPO_ROOT / MANIFEST_REL_PATH
    if not manifest_path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in manifest_path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        split = record.get("split", {})
        if not isinstance(split, dict):
            continue
        role = split.get("role")
        if role != ALLOWED_POOL_ROLE:
            continue
        entry = _safe_pool_entry_for_api(record)
        records.append(entry)
    return records


def _safe_pool_entry_for_api(record: dict[str, Any]) -> dict[str, Any]:
    """Build a safe API-facing dict from a manifest record.

    Only contains: sample_id, family_id, sample_kind, parameters_normalized,
    validation_status, validation_is_valid, source_repository, source_family_path,
    source_release_qualified, split_role.
    """
    from retrieval.pool import _safe_pool_entry
    entry = _safe_pool_entry(record)
    return {
        "sample_id": entry.sample_id,
        "family_id": entry.family_id,
        "sample_kind": entry.sample_kind,
        "parameters_normalized": dict(entry.parameters_normalized),
        "validation_status": entry.validation_status,
        "validation_is_valid": entry.validation_is_valid,
        "source_repository": entry.source_repository,
        "source_family_path": entry.source_family_path,
        "source_release_qualified": entry.source_release_qualified,
        "split_role": entry.split_role,
    }
