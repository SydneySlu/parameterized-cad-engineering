"""RET-004 paired C0/C1 runner and per-run confirmation gate.

Offline FakeTransport runs validate wiring only. Formal calls require an exact
RET004Approval and successful side-effect-free preflight; this module never
changes FORMAL_EVALUATION_ALLOWED.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from llm.adapter import Adapter, AdapterInput, RetentionPolicy
from llm.budget import BudgetAwareTransport, BudgetLedger
from llm.conditions import assemble_c0, assemble_c1, extract_bore_d_mm
from llm.contract import CONTRACT_VERSION, DEEPSEEK_MODEL, DEEPSEEK_PROVIDER, FORMAL_EVALUATION_ALLOWED, PROMPT_VERSION
from llm.env_loader import EnvironmentConfigurationError, load_deepseek_environment
from llm.prompt_loader import FROZEN_PROMPT_PATH, load_frozen_prompt
from llm.real_transport import DeepSeekTransport
from llm.transport import FakeTransport
from llm.input_projection import ProjectedCase
from llm.ret004_authorization import (
    RET004Authorization, RET004Approval, RET004_BATCH_ID, RET004_CONFIG_SHA256,
    RET004_CONDITIONS, RET004_INPUTS_SHA256, RET004_INPUT_IDS, RET004_LABELS_SHA256,
    RET004_MANIFEST_SHA256, RET004_MAX_ATTEMPTS_PER_RUN, RET004_MAX_HTTP,
    RET004_MAX_RUNS, RET004_MODEL, RET004_PROFILE_ID, RET004_PROVIDER, RET004_PROMPT_SHA256,
    RET004_CONTRACT_SHA256, authorize_ret004, validate_ret004_approval,
)

from integration.product_live_runner import (
    ProductLiveLogicalRunPlan, ProductLiveRunState, PRODUCT_LIVE_STATUS_BLOCKED,
    PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION, _build_state_from_adapter_result,
    confirm_product_live_run, _REPO_ROOT, _to_repo_relative_path, _utc_now_iso,
)

_SCOPE_DIR = _REPO_ROOT / "agent-work/integration/RET-004-PAIRED-LIVE-20261116-01"
_INPUTS = _SCOPE_DIR / "model-inputs.json"
_CONFIG = _REPO_ROOT / "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json"
_MANIFEST = _REPO_ROOT / "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"
_RUN_ROOT = _REPO_ROOT / "work/app001-runs"


class RET004PreflightError(RuntimeError): pass


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_ret004_offline_preflight(auth: RET004Authorization | None = None) -> dict[str, Any]:
    """Check model-visible artifacts and batch availability without credentials or writes.

    Evaluator-label bytes are deliberately never opened by this runner. Their
    digest is bound as a frozen authorization constant and independently
    checked by the review/preflight operator outside the execution process.
    """
    auth = auth or authorize_ret004()
    if type(auth) is not RET004Authorization:
        raise RET004PreflightError("RET004_AUTHORIZATION_TYPE_INVALID")
    try: auth.__post_init__()
    except Exception as exc: raise RET004PreflightError("RET004_AUTHORIZATION_INVALID") from exc
    expected = {
        _INPUTS: RET004_INPUTS_SHA256,
        _CONFIG: RET004_CONFIG_SHA256, _MANIFEST: RET004_MANIFEST_SHA256,
        FROZEN_PROMPT_PATH: RET004_PROMPT_SHA256,
        _REPO_ROOT / "src/llm/contract.py": RET004_CONTRACT_SHA256,
    }
    errors = []
    hashes = {}
    for path, digest in expected.items():
        try: actual = _digest(path)
        except OSError: actual = None
        hashes[path.relative_to(_REPO_ROOT).as_posix()] = actual
        if actual != digest: errors.append("artifact_hash_mismatch")
    batch_dir = _RUN_ROOT / RET004_BATCH_ID
    if batch_dir.exists(): errors.append("batch_directory_already_exists")
    if RET004_MAX_RUNS * RET004_MAX_ATTEMPTS_PER_RUN != RET004_MAX_HTTP:
        errors.append("budget_infeasible")
    try:
        prompt = load_frozen_prompt()
        if prompt.version != PROMPT_VERSION: errors.append("prompt_version_mismatch")
    except Exception: errors.append("prompt_unavailable")
    try:
        _load_index()
    except Exception:
        errors.append("retrieval_index_invalid")
    try:
        from integration.product_live_runner import _check_cad_runtime
        cad_check = _check_cad_runtime()
        if not cad_check.get("ok"):
            errors.append("cad_runtime_unavailable")
    except Exception:
        cad_check = {"ok": False}
        errors.append("cad_runtime_check_failed")
    return {"ok": not errors, "errors": errors, "artifact_hashes": hashes,
            "evaluator_labels_sha256_bound": auth.labels_sha256 == RET004_LABELS_SHA256,
            "evaluator_labels_read": False,
            "batch_id": RET004_BATCH_ID, "batch_dir_exists": batch_dir.exists(),
            "planned_runs": 4, "max_attempts_per_run": 2, "max_batch_http": 8,
            "cad_runtime": cad_check, "formal_evaluation_allowed": FORMAL_EVALUATION_ALLOWED}


def _load_inputs() -> dict[str, str]:
    raw = _INPUTS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RET004_INPUTS_SHA256:
        raise RET004PreflightError("RET004_INPUT_HASH_MISMATCH")
    data = json.loads(raw)
    rows = data.get("inputs") if isinstance(data, dict) and data.get("scope_id") == RET004_PROFILE_ID else None
    if not isinstance(rows, list): raise RET004PreflightError("RET004_INPUT_SCHEMA_INVALID")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"input_id", "request_text"}:
            raise RET004PreflightError("RET004_INPUT_SCHEMA_INVALID")
        if row["input_id"] in result or not isinstance(row["request_text"], str):
            raise RET004PreflightError("RET004_INPUT_SCHEMA_INVALID")
        result[row["input_id"]] = row["request_text"]
    if tuple(result) != RET004_INPUT_IDS: raise RET004PreflightError("RET004_INPUT_IDS_INVALID")
    return result


def _load_index():
    from retrieval import RetrievalIndex
    from retrieval.config import DEFAULT_CONFIG_REL_PATH
    index = RetrievalIndex.from_config(DEFAULT_CONFIG_REL_PATH, repo_root=_REPO_ROOT)
    if type(index) is not RetrievalIndex or index.manifest_sha256 != RET004_MANIFEST_SHA256:
        raise RET004PreflightError("RET004_RETRIEVAL_INDEX_IDENTITY_INVALID")
    if tuple(index.candidate_roles) != ("retrieval_source",) or index.default_top_k != 3:
        raise RET004PreflightError("RET004_RETRIEVAL_POLICY_INVALID")
    return index


def _plan(input_id: str, condition: str, auth: RET004Authorization) -> ProductLiveLogicalRunPlan:
    return ProductLiveLogicalRunPlan(
        logical_run_id=auth.expected_logical_run_id(input_id, condition), input_id=input_id,
        condition_id=condition, provider=RET004_PROVIDER, model=RET004_MODEL,
    )


def _planned_run_records(auth: RET004Authorization) -> dict[str, dict[str, Any]]:
    return {
        auth.expected_logical_run_id(input_id, condition): {
            "input_id": input_id, "condition_id": condition,
            "run_status": "not_started", "attempted": False,
        }
        for input_id in RET004_INPUT_IDS for condition in RET004_CONDITIONS
    }


def _assemble_c1_from_user_text(case: ProjectedCase, retrieval_index: Any):
    """RET-004 permits only request-text query extraction, never structural fallback."""
    if case.reference_context_structural is not None:
        raise RET004PreflightError("RET004_STRUCTURED_QUERY_SOURCE_FORBIDDEN")
    return assemble_c1(case, retrieval_index)


class RET004PairedService:
    """In-memory run registry with formal ledger and explicit R01 confirmations."""
    def __init__(self, *, auth: RET004Authorization, approval: RET004Approval,
                 transport: Any, formal: bool, ledger: BudgetLedger | None = None,
                 batch_dir: Path | None = None):
        if type(auth) is not RET004Authorization: raise ValueError("RET004_AUTHORIZATION_TYPE_INVALID")
        validate_ret004_approval(auth, approval)
        if formal and approval.is_test_only:
            raise ValueError("RET004_TEST_ONLY_APPROVAL_CANNOT_CONFIRM_CAD")
        if formal and (type(transport) is not DeepSeekTransport or ledger is None):
            raise ValueError("RET004_FORMAL_TRANSPORT_NOT_LEDGER_BOUND")
        if not formal and type(transport) is not FakeTransport:
            raise ValueError("RET004_OFFLINE_REQUIRES_EXACT_FAKE_TRANSPORT")
        self.auth, self.approval, self.transport, self.formal = auth, approval, transport, formal
        self.ledger, self.batch_dir = ledger, batch_dir
        self.inputs = _load_inputs()
        self.index = _load_index()
        self.prompt = load_frozen_prompt()
        self.runs: dict[str, ProductLiveRunState] = {}
        self._confirmed: set[str] = set()
        self._confirmable_state_hashes: dict[str, str] = {}
        self._summary_path = (batch_dir / "batch_summary.json") if batch_dir else None
        self._summary: dict[str, Any] = {
            "schema_version": "ret004-paired-summary.v1", "batch_id": RET004_BATCH_ID,
            "profile_id": RET004_PROFILE_ID, "batch_status": "running",
            "planned_runs": 4, "max_batch_http": RET004_MAX_HTTP,
            "approval": {"is_test_only": approval.is_test_only,
                         "approver": approval.approver,
                         "approved_at_utc": approval.approved_at_utc,
                         "approval_statement_sha256": hashlib.sha256(approval.approval_statement.encode("utf-8")).hexdigest()},
            "runs": _planned_run_records(auth),
        }
        self._flush_summary()

    def _flush_summary(self) -> None:
        if self._summary_path is None:
            return
        self._summary_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._summary_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self._summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self._summary_path)

    def _record_state(self, state: ProductLiveRunState) -> None:
        raw = state.raw_retention_meta or {}
        raw_claimed_retained = raw.get("retained") is True
        raw_path_candidate = raw.get("path") if raw_claimed_retained else None
        raw_path = _to_repo_relative_path(raw_path_candidate)
        raw_path_invalid = raw_claimed_retained and raw_path is None
        errors = [{"code": e.get("code", "ERROR")} for e in state.errors]
        if raw_path_invalid:
            errors.append({"code": "RAW_RETENTION_PATH_INVALID"})
        self._summary["runs"][state.logical_run_id] = {
            "input_id": state.input_id, "condition_id": state.condition_id,
            "run_status": state.product_status, "attempted": True,
            "product_status": state.product_status, "decision": state.decision,
            "extracted_parameters": state.extracted_parameters,
            "unsupported_requests": state.unsupported_requests,
            "llm_meta": state.llm_meta,
            "schema_status": "pass" if state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION else "blocked_or_not_applicable",
            "confirmation_status": "pending" if state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION and state.input_id == RET004_INPUT_IDS[0] else ("denied_by_scope" if state.input_id == RET004_INPUT_IDS[1] else "not_required"),
            "raw_retained": raw_claimed_retained and raw_path is not None,
            "raw_path": raw_path, "raw_path_invalid": raw_path_invalid,
            "raw_sha256": raw.get("body_sha256"),
            "errors": errors,
            "pipeline_status": state.pipeline_status,
            "step_sha256": (state.ir_index or {}).get("step_sha256"),
        }
        self._flush_summary()

    def _refresh_batch_status(self) -> str:
        expected_ids = {
            self.auth.expected_logical_run_id(input_id, condition)
            for input_id in RET004_INPUT_IDS for condition in RET004_CONDITIONS
        }
        if set(self.runs) != expected_ids:
            status = "incomplete"
        else:
            failed = False
            for input_id in RET004_INPUT_IDS:
                for condition in RET004_CONDITIONS:
                    state = self.runs[self.auth.expected_logical_run_id(input_id, condition)]
                    error_codes = {e.get("code") for e in state.errors}
                    expected_codes = {"SCOPE_CAD_DENIED"}
                    if input_id == RET004_INPUT_IDS[1] and state.decision == "refuse" and state.unsupported_requests:
                        expected_codes.add("GATE_DECISION_REFUSE")
                    if input_id == RET004_INPUT_IDS[0] and "CONFIRMATION_REJECTED" in error_codes:
                        expected_codes.add("CONFIRMATION_REJECTED")
                    if error_codes - expected_codes or state.product_status in {"error", "failed"}:
                        failed = True
                    if state.raw_retention_meta and state.raw_retention_meta.get("retained") is True:
                        if _to_repo_relative_path(state.raw_retention_meta.get("path")) is None:
                            failed = True
                    if input_id == RET004_INPUT_IDS[0]:
                        if state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
                            continue
                        if any(e.get("code") == "CONFIRMATION_REJECTED" for e in state.errors):
                            continue
                        if state.product_status == "succeeded":
                            continue
                        failed = True
                    else:
                        if state.decision != "refuse" or not state.unsupported_requests:
                            failed = True
            if failed:
                status = "failed"
            elif any(
                self.runs[self.auth.expected_logical_run_id(RET004_INPUT_IDS[0], c)].product_status
                == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION
                for c in RET004_CONDITIONS
            ):
                status = "awaiting_confirmation"
            else:
                status = "complete"
        self._summary["batch_status"] = status
        self._flush_summary()
        return status

    @staticmethod
    def _state_fingerprint(state: ProductLiveRunState) -> str:
        payload = json.dumps(state.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def extract_all(self) -> list[ProductLiveRunState]:
        for input_id in RET004_INPUT_IDS:
            text = self.inputs[input_id]
            for condition in RET004_CONDITIONS:
                plan = _plan(input_id, condition, self.auth)
                if not self.auth.allows_logical_run(plan.logical_run_id, plan.provider):
                    raise ValueError("RET004_LOGICAL_RUN_OUTSIDE_SCOPE")
                if condition == "C0":
                    assembled = assemble_c0(ProjectedCase(input_id, text, None, ("bore_d",)))
                else:
                    assembled = _assemble_c1_from_user_text(
                        ProjectedCase(input_id, text, None, ("bore_d",)), self.index
                    )
                if assembled.blocked_reason:
                    state = ProductLiveRunState(
                        logical_run_id=plan.logical_run_id, input_id=input_id, condition_id=condition,
                        provider=RET004_PROVIDER, model=RET004_MODEL, llm_status="blocked",
                        product_status=PRODUCT_LIVE_STATUS_BLOCKED, decision="", extracted_parameters={},
                        missing_fields=[], unsupported_requests=[], questions=[], conflicts=[],
                        errors=[{"code": assembled.error_code or "C1_ASSEMBLY_BLOCKED"}],
                        request_text=text,
                    )
                    self.runs[plan.logical_run_id] = state
                    self._record_state(state)
                    continue
                run_transport: Any = self.transport
                if self.formal:
                    run_transport = BudgetAwareTransport(
                        self.transport, ledger=self.ledger, authorization=self.auth,
                        logical_run_id=plan.logical_run_id, provider=plan.provider, model=plan.model,
                        adapter_run_id=plan.logical_run_id, query_id=input_id, condition_id=condition,
                    )
                policy = RetentionPolicy(retain_raw=True, base_dir=f"work/app001-runs/{RET004_BATCH_ID}/raw") if self.formal else RetentionPolicy.default()
                adapter = Adapter(provider=plan.provider, transport=run_transport, retention_policy=policy)
                adapter_input = AdapterInput(
                    query_id=input_id, natural_language_input=text,
                    reference_context=assembled.reference_context,
                    system_prompt=self.prompt.system_prompt,
                    user_prompt_template=self.prompt.user_template, condition_id=condition,
                )
                try:
                    adapter_result = adapter.run(adapter_input, run_id=plan.logical_run_id,
                                                 formal_authorization=self.auth,
                                                 max_attempts=RET004_MAX_ATTEMPTS_PER_RUN)
                    record = adapter_result.record
                    meta = {"run_id": plan.logical_run_id, "attempt_count": record.attempt_count,
                            "total_elapsed_ms": record.total_elapsed_ms,
                            "cloud_input_tokens": record.cloud_input_tokens,
                            "cloud_output_tokens": record.cloud_output_tokens,
                            "cloud_total_tokens": record.cloud_total_tokens,
                            "cloud_cost_amount": record.cloud_cost_amount,
                            "cloud_cost_currency": record.cloud_cost_currency,
                            "configured_provider": record.configured_provider,
                            "configured_model_name": record.configured_model_name,
                            "prompt_version": record.prompt_version, "contract_version": record.contract_version,
                            "reference_context_sha256": assembled.reference_context_sha256,
                            "candidate_source_ids": list(assembled.candidate_source_ids),
                            "bore_d_used_for_query": assembled.bore_d_used_for_query,
                            "prompt_hashes": dict(record.prompt_hashes or {})}
                    state = _build_state_from_adapter_result(plan=plan, adapter_result=adapter_result,
                                                             llm_meta=meta, natural_language=text)
                except Exception as exc:
                    state = ProductLiveRunState(
                        logical_run_id=plan.logical_run_id, input_id=input_id, condition_id=condition,
                        provider=RET004_PROVIDER, model=RET004_MODEL, llm_status="error",
                        product_status="error", decision="", extracted_parameters={}, missing_fields=[],
                        unsupported_requests=[], questions=[], conflicts=[],
                        errors=[{"code": "ADAPTER_EXCEPTION", "exception_type": type(exc).__name__,
                                 "message": "抽取失败；不会进入 CAD。"}], request_text=text,
                    )
                if input_id == RET004_INPUT_IDS[0] and state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
                    explicit_bore = extract_bore_d_mm(text)
                    extracted_bore = state.extracted_parameters.get("bore_d")
                    valid_extracted_bore = (
                        type(extracted_bore) in (int, float)
                        and math.isfinite(float(extracted_bore))
                    )
                    if explicit_bore is None:
                        state.product_status = PRODUCT_LIVE_STATUS_BLOCKED
                        state.errors.append({"code": "EXPLICIT_BORE_NOT_PARSEABLE"})
                    elif not valid_extracted_bore or not math.isclose(
                        float(extracted_bore), explicit_bore, rel_tol=0.0, abs_tol=1e-9
                    ):
                        state.product_status = PRODUCT_LIVE_STATUS_BLOCKED
                        state.errors.append({"code": "EXPLICIT_BORE_MISMATCH"})
                # R02 is an unconditional CAD deny, independent of model output.
                if input_id == RET004_INPUT_IDS[1]:
                    state.product_status = PRODUCT_LIVE_STATUS_BLOCKED
                    if state.decision != "refuse" or not state.unsupported_requests:
                        state.errors.append({"code": "UNSUPPORTED_REQUEST_NOT_REFUSED_OR_REPRESENTED"})
                    if not any(e.get("code") == "SCOPE_CAD_DENIED" for e in state.errors):
                        state.errors.append({"code": "SCOPE_CAD_DENIED"})
                self.runs[plan.logical_run_id] = state
                if input_id == RET004_INPUT_IDS[0] and state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
                    self._confirmable_state_hashes[plan.logical_run_id] = self._state_fingerprint(state)
                self._record_state(state)
                if self.ledger is not None:
                    outcome = "success" if state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION else (
                        "blocked" if state.product_status == PRODUCT_LIVE_STATUS_BLOCKED else "non_retryable_error"
                    )
                    self.ledger.record_run_result(logical_run_id=plan.logical_run_id, result=outcome)
        self._refresh_batch_status()
        return [self.runs[self.auth.expected_logical_run_id(i, c)] for i in RET004_INPUT_IDS for c in RET004_CONDITIONS]

    def confirm_r01(self, condition: str, confirmed: bool) -> ProductLiveRunState:
        if condition not in RET004_CONDITIONS: raise ValueError("RET004_CONDITION_OUTSIDE_SCOPE")
        logical_id = self.auth.expected_logical_run_id(RET004_INPUT_IDS[0], condition)
        return self.confirm_run(logical_id, confirmed)

    def confirm_run(self, logical_id: str, confirmed: bool) -> ProductLiveRunState:
        if type(confirmed) is not bool:
            raise ValueError("RET004_CONFIRMATION_MUST_BE_BOOLEAN")
        if logical_id not in {self.auth.expected_logical_run_id(RET004_INPUT_IDS[0], c) for c in RET004_CONDITIONS}:
            raise ValueError("RET004_CAD_DENIED_FOR_INPUT")
        if not self.formal:
            raise ValueError("RET004_OFFLINE_CAD_DISABLED")
        if logical_id in self._confirmed: raise ValueError("RET004_CONFIRMATION_ALREADY_USED")
        state = self.runs.get(logical_id)
        if state is None or state.input_id != RET004_INPUT_IDS[0] or state.product_status != PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
            raise ValueError("RET004_RUN_NOT_CONFIRMABLE")
        expected_fingerprint = self._confirmable_state_hashes.get(logical_id)
        if expected_fingerprint is None or self._state_fingerprint(state) != expected_fingerprint:
            raise ValueError("RET004_CONFIRMATION_STATE_CHANGED")
        self._confirmed.add(logical_id)
        result = confirm_product_live_run(state, confirmed=confirmed,
                                          output_root=(self.batch_dir / "pipeline-runs") if self.batch_dir else None)
        result.raw_retention_meta = state.raw_retention_meta
        result.raw_retention_path = state.raw_retention_path
        self.runs[logical_id] = result
        self._record_state(result)
        self._refresh_batch_status()
        return result


def run_ret004_paired_batch(*, authorization: RET004Authorization | None = None,
                            approval: RET004Approval, transport: Any = None) -> tuple[RET004PairedService | None, dict[str, Any]]:
    """Execute after explicit approval; formal mode is transport=None.

    This function is deliberately not called by app startup or a CLI default.
    """
    auth = authorization or authorize_ret004()
    if type(auth) is not RET004Authorization: raise ValueError("RET004_AUTHORIZATION_TYPE_INVALID")
    validate_ret004_approval(auth, approval)
    formal = transport is None
    if not formal and type(transport) is not FakeTransport:
        raise ValueError("RET004_OFFLINE_REQUIRES_EXACT_FAKE_TRANSPORT")
    if formal and approval.is_test_only:
        raise ValueError("test-only approval cannot authorize RET-004 live execution")
    preflight = run_ret004_offline_preflight(auth)
    if not preflight["ok"]: return None, {"preflight": preflight, "runs": []}
    if formal:
        try: load_deepseek_environment(repo_root=_REPO_ROOT)
        except EnvironmentConfigurationError as exc: raise RET004PreflightError("RET004_CREDENTIALS_UNAVAILABLE") from exc
        batch_dir = _RUN_ROOT / RET004_BATCH_ID
        batch_dir.mkdir(parents=False, exist_ok=False)
        initial_summary = {
            "schema_version": "ret004-paired-summary.v1", "batch_id": RET004_BATCH_ID,
            "profile_id": RET004_PROFILE_ID, "batch_status": "initializing",
            "planned_runs": 4, "max_batch_http": RET004_MAX_HTTP,
            "approval": {"approver": approval.approver, "approved_at_utc": approval.approved_at_utc,
                         "approval_statement_sha256": hashlib.sha256(approval.approval_statement.encode("utf-8")).hexdigest(),
                         "is_test_only": approval.is_test_only},
            "runs": _planned_run_records(auth),
        }
        summary_path = batch_dir / "batch_summary.json"
        summary_path.write_text(json.dumps(initial_summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        ledger = None
        try:
            ledger = BudgetLedger(batch_dir, auth)
            ledger.acquire_lock()
            real_transport = DeepSeekTransport(authorization=auth)
            service = RET004PairedService(auth=auth, approval=approval, transport=real_transport,
                                          formal=True, ledger=ledger, batch_dir=batch_dir)
        except Exception:
            initial_summary["batch_status"] = "aborted"
            try: summary_path.write_text(json.dumps(initial_summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            except OSError: pass
            if ledger is not None: ledger.release_lock()
            raise
    else:
        if type(transport) is not FakeTransport: raise ValueError("RET004_OFFLINE_REQUIRES_EXACT_FAKE_TRANSPORT")
        ledger, batch_dir = None, None
        service = RET004PairedService(auth=auth, approval=approval, transport=transport,
                                      formal=False)
    try:
        runs = service.extract_all()
    except Exception:
        service._summary["batch_status"] = "aborted"
        try: service._flush_summary()
        except OSError: pass
        raise
    finally:
        if ledger is not None: ledger.release_lock()
    return service, {"preflight": preflight, "planned_runs": 4, "runs": [
        {"logical_run_id": r.logical_run_id, "input_id": r.input_id, "condition_id": r.condition_id,
         "product_status": r.product_status, "decision": r.decision,
         "extracted_parameters": r.extracted_parameters, "errors": [e.get("code") for e in r.errors],
         "llm_meta": r.llm_meta}
        for r in runs
    ], "interpretation": "offline harness evidence only; live results remain to_be_measured" if transport is not None else "live extraction results"}
