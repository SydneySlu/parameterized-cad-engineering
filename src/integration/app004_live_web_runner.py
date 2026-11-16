"""Approval-bound runner/service for the APP-004 localhost web demo.

The normal server does not construct this service. Formal activation is an
explicit caller action requiring the exact APP-004 authorization and a
non-test owner approval. Offline tests use an exact FakeTransport and never
read credentials or create a batch directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from llm.authorization import AuthorizationScopeError
from llm.budget import BudgetAwareTransport, BudgetLedger
from llm.contract import CONTRACT_VERSION, DEEPSEEK_MODEL, DEEPSEEK_PROVIDER, FORMAL_EVALUATION_ALLOWED, PROMPT_VERSION
from llm.env_loader import EnvironmentConfigurationError, load_deepseek_environment
from llm.prompt_loader import FROZEN_PROMPT_PATH, load_frozen_prompt
from llm.real_transport import DeepSeekTransport
from llm.transport import FakeTransport
from integration.product_live_runner import (
    ProductLiveRunState,
    ProductLiveLogicalRunPlan,
    PRODUCT_LIVE_STATUS_BLOCKED,
    PRODUCT_LIVE_STATUS_ERROR,
    PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
    PRODUCT_LIVE_STATUS_SUCCEEDED,
    _REPO_ROOT,
    _run_one_logical_mock,
    _utc_now_iso,
    confirm_product_live_run,
)
from llm.adapter import RetentionPolicy, _retain_response
from llm.app004_live_web_authorization import (
    APP004_BATCH_ID,
    APP004_CONTRACT_SHA256,
    APP004_CONDITION,
    APP004_INPUT_IDS,
    APP004_INPUTS_SHA256,
    APP004_LABELS_SHA256,
    APP004_MAX_ATTEMPTS_PER_RUN,
    APP004_MAX_BATCH_HTTP,
    APP004_MAX_LOGICAL_RUNS,
    APP004_MODEL,
    APP004_PROFILE_ID,
    APP004_PROVIDER,
    APP004_PROMPT_SHA256,
    APP004_SAMPLE_SET,
    App004ApprovalValidationError,
    App004LiveWebApproval,
    App004LiveWebAuthorization,
    validate_app004_approval_binding,
)

_INPUTS_PATH = _REPO_ROOT / "agent-work/integration/APP-004-LIVE-WEB-DEMO/model-inputs.json"
_RUN_ROOT = _REPO_ROOT / "work" / "app001-runs"
_BATCH_DIR = _RUN_ROOT / APP004_BATCH_ID
_D01 = APP004_INPUT_IDS[0]
_D02 = APP004_INPUT_IDS[1]


class App004LiveError(RuntimeError):
    """Stable APP-004 service error."""


def authorize_app004_live_web_run() -> App004LiveWebAuthorization:
    """Construct the exact frozen authorization; no side effects."""
    return App004LiveWebAuthorization(
        protocol_versions=frozenset({CONTRACT_VERSION, PROMPT_VERSION}),
        sample_set=APP004_SAMPLE_SET,
        conditions=frozenset({APP004_CONDITION}),
        providers=frozenset({APP004_PROVIDER}),
        models=frozenset({APP004_MODEL}),
        max_logical_runs=APP004_MAX_LOGICAL_RUNS,
        max_attempts_per_run=APP004_MAX_ATTEMPTS_PER_RUN,
        max_batch_attempts=APP004_MAX_BATCH_HTTP,
        max_provider_attempts=APP004_MAX_BATCH_HTTP,
        ir_cad_geometry_step_disabled=True,
        batch_id=APP004_BATCH_ID,
        profile_id=APP004_PROFILE_ID,
        input_ids=APP004_INPUT_IDS,
        inputs_sha256=APP004_INPUTS_SHA256,
        evaluator_labels_sha256=APP004_LABELS_SHA256,
        prompt_sha256=APP004_PROMPT_SHA256,
        contract_sha256=APP004_CONTRACT_SHA256,
        enable_cad_pipeline=True,
    )


def _load_frozen_inputs() -> dict[str, str]:
    raw = _INPUTS_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != APP004_INPUTS_SHA256:
        raise App004LiveError("APP004_INPUTS_HASH_MISMATCH")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("scope_id") != APP004_PROFILE_ID:
        raise App004LiveError("APP004_INPUTS_SCOPE_MISMATCH")
    rows = payload.get("inputs")
    if not isinstance(rows, list):
        raise App004LiveError("APP004_INPUTS_SCHEMA_MISMATCH")
    ids: list[str] = []
    result: dict[str, str] = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"input_id", "condition", "request_text"}
                or row.get("condition") != APP004_CONDITION
                or not isinstance(row.get("input_id"), str)
                or not isinstance(row.get("request_text"), str)
                or not row["request_text"].strip()):
            raise App004LiveError("APP004_INPUTS_SCHEMA_MISMATCH")
        ids.append(row["input_id"])
        result[row["input_id"]] = row["request_text"]
    if tuple(ids) != APP004_INPUT_IDS or len(result) != len(APP004_INPUT_IDS):
        raise App004LiveError("APP004_INPUT_IDS_MISMATCH")
    return result


def run_app004_offline_preflight(
    authorization: App004LiveWebAuthorization,
    *,
    require_cad_runtime: bool = True,
) -> dict[str, Any]:
    """Check frozen artifacts, prompt and exact batch availability without side effects."""
    errors: list[str] = []
    details: dict[str, Any] = {"batch_id": authorization.batch_id}
    try:
        _load_frozen_inputs()
        details["inputs_sha256_ok"] = True
    except (OSError, ValueError, App004LiveError, json.JSONDecodeError):
        details["inputs_sha256_ok"] = False
        errors.append("inputs_hash_or_schema_invalid")
    details["batch_dir_exists"] = _BATCH_DIR.exists()
    if _BATCH_DIR.exists():
        errors.append("batch_directory_already_exists")
    try:
        prompt = load_frozen_prompt()
        details["prompt_version"] = prompt.version
        prompt_digest = hashlib.sha256(FROZEN_PROMPT_PATH.read_bytes()).hexdigest()
        details["prompt_sha256"] = prompt_digest
        details["prompt_ok"] = prompt_digest == APP004_PROMPT_SHA256
        if not details["prompt_ok"]:
            errors.append("prompt_hash_mismatch")
    except Exception:
        details["prompt_ok"] = False
        errors.append("prompt_unavailable")
    contract_path = Path(__file__).resolve().parents[1] / "llm" / "contract.py"
    try:
        contract_digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        details["contract_sha256"] = contract_digest
        details["contract_ok"] = contract_digest == APP004_CONTRACT_SHA256
        if not details["contract_ok"]:
            errors.append("contract_hash_mismatch")
    except OSError:
        details["contract_ok"] = False
        errors.append("contract_unavailable")
    if require_cad_runtime:
        try:
            from integration.product_live_runner import _check_cad_runtime
            cad = _check_cad_runtime()
            details["cad_runtime"] = cad.get("details", {})
            if not cad.get("ok"):
                errors.append("cad_runtime_unavailable")
        except Exception:
            errors.append("cad_runtime_check_failed")
    details["max_batch_http"] = APP004_MAX_BATCH_HTTP
    details["max_runs_x_attempts"] = APP004_MAX_LOGICAL_RUNS * APP004_MAX_ATTEMPTS_PER_RUN
    return {"ok": not errors, "errors": errors, "details": details}


class _CaptureTransport:
    """Capture response bodies in memory so formal mode can retain raw evidence."""
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.last_body: str | None = None

    def send(self, request: Any) -> Any:
        response = self.inner.send(request)
        body = getattr(response, "body", None)
        if isinstance(body, str):
            self.last_body = body
        return response


class App004LiveWebService:
    """Allowlisted extraction and confirmation service for the APP-004 UI."""

    def __init__(
        self,
        *,
        authorization: App004LiveWebAuthorization,
        transport: Any,
        formal: bool,
        ledger: BudgetLedger | None = None,
        batch_dir: Path | None = None,
    ) -> None:
        if type(authorization) is not App004LiveWebAuthorization:
            raise App004LiveError("APP004_AUTHORIZATION_TYPE_INVALID")
        if formal:
            if type(transport) is not DeepSeekTransport or ledger is None:
                raise App004LiveError("APP004_FORMAL_SERVICE_NOT_BOUND_TO_LEDGER")
        elif type(transport) is not FakeTransport:
            raise App004LiveError("APP004_OFFLINE_SERVICE_REQUIRES_EXACT_FAKE_TRANSPORT")
        self.authorization = authorization
        self._transport = transport
        self._formal = formal
        self.mode = "formal" if formal else "offline_mock"
        self._ledger = ledger
        self._batch_dir = batch_dir
        self._pipeline_root = (batch_dir / "pipeline-runs") if batch_dir else (
            _REPO_ROOT / "work" / "app004-offline-runs"
        )
        self._inputs = _load_frozen_inputs()
        self._runs: dict[str, ProductLiveRunState] = {}
        self._used_inputs: set[str] = set()
        self._lock = threading.RLock()
        self._summary: dict[str, Any] | None = None
        self._closed = False
        self._summary_failed = False

    @classmethod
    def from_fake_transport(cls, transport: FakeTransport) -> "App004LiveWebService":
        """Explicit offline-only constructor for tests and browser smoke."""
        if type(transport) is not FakeTransport:
            raise App004LiveError("APP004_OFFLINE_SERVICE_REQUIRES_EXACT_FAKE_TRANSPORT")
        return cls(authorization=authorize_app004_live_web_run(), transport=transport, formal=False)

    @classmethod
    def prepare_formal(
        cls,
        *,
        authorization: App004LiveWebAuthorization,
        approval: App004LiveWebApproval,
    ) -> "App004LiveWebService":
        """Activate formal service only after owner approval and offline preflight.

        This method is deliberately not called by ``run_server``. Calling it
        creates the approved batch directory and reads credentials only after
        the exact approval and preflight gates succeed.
        """
        if type(authorization) is not App004LiveWebAuthorization:
            raise App004ApprovalValidationError("expected App004LiveWebAuthorization")
        validate_app004_approval_binding(authorization, approval)
        preflight = run_app004_offline_preflight(authorization, require_cad_runtime=True)
        if not preflight["ok"]:
            raise App004LiveError("APP004_PREFLIGHT_FAILED: " + ",".join(preflight["errors"]))
        inputs = _load_frozen_inputs()
        try:
            load_deepseek_environment(repo_root=_REPO_ROOT)
        except EnvironmentConfigurationError as exc:
            raise App004LiveError("APP004_CREDENTIAL_CONFIGURATION_INVALID") from exc
        try:
            _BATCH_DIR.mkdir(parents=False, exist_ok=False)
        except FileExistsError as exc:
            raise App004LiveError("APP004_BATCH_DIRECTORY_ALREADY_EXISTS") from exc
        try:
            ledger = BudgetLedger(_BATCH_DIR, authorization)
        except Exception as exc:
            try:
                _BATCH_DIR.rmdir()
            except OSError:
                pass
            raise App004LiveError("APP004_BUDGET_LEDGER_INIT_FAILED") from exc
        try:
            ledger.acquire_lock()
        except Exception as exc:
            ledger.release_lock()
            raise App004LiveError("APP004_BUDGET_LEDGER_LOCK_FAILED") from exc
        service = cls(
            authorization=authorization,
            transport=DeepSeekTransport(authorization=authorization),
            formal=True,
            ledger=ledger,
            batch_dir=_BATCH_DIR,
        )
        service._inputs = inputs
        service._summary = {
            "schema_version": "app004-live-web-summary.v1",
            "batch_id": APP004_BATCH_ID,
            "profile_id": APP004_PROFILE_ID,
            "batch_status": "running",
            "batch_started_utc": _utc_now_iso(),
            "approval": approval.as_audit_dict(),
            "scope": {
                "input_ids": list(APP004_INPUT_IDS), "provider": APP004_PROVIDER,
                "model": APP004_MODEL, "condition": APP004_CONDITION,
                "max_batch_http": APP004_MAX_BATCH_HTTP,
            },
            "artifact_hashes": {
                "inputs_sha256": APP004_INPUTS_SHA256,
                "evaluator_labels_sha256": APP004_LABELS_SHA256,
                "prompt_file_sha256": APP004_PROMPT_SHA256,
                "contract_file_sha256": APP004_CONTRACT_SHA256,
            },
            "runs": {},
        }
        try:
            service._write_summary()
        except Exception as exc:
            service._summary["batch_status"] = "aborted"
            if service._ledger is not None:
                service._ledger.release_lock()
            raise App004LiveError("APP004_SUMMARY_INITIALIZATION_FAILED") from exc
        return service

    def _write_summary(self) -> None:
        if not self._formal or self._summary is None or self._batch_dir is None:
            return
        target = self._batch_dir / "batch_summary.json"
        temp = target.with_suffix(".json.tmp")
        raw = json.dumps(self._summary, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        canonical_batch = self._batch_dir.resolve()
        if target.resolve(strict=False).parent != canonical_batch:
            raise App004LiveError("APP004_SUMMARY_PATH_INVALID")
        temp.write_bytes(raw)
        os.replace(temp, target)

    def _update_summary(self, state: ProductLiveRunState) -> None:
        if self._summary is None:
            return
        raw_meta = state.raw_retention_meta if isinstance(state.raw_retention_meta, dict) else {}
        raw_path = state.raw_retention_path
        try:
            rel_raw = Path(raw_path).resolve().relative_to(_REPO_ROOT.resolve()).as_posix() if raw_path else None
        except (ValueError, OSError):
            rel_raw = None
        self._summary["runs"][state.logical_run_id] = {
            "input_id": state.input_id,
            "product_status": state.product_status,
            "llm_status": state.llm_status,
            "decision": state.decision,
            "attempt_count": state.llm_meta.get("attempt_count"),
            "raw_retention_path": rel_raw,
            "raw_sha256": raw_meta.get("body_sha256"),
            "raw_retained": raw_meta.get("retained"),
            "pipeline_status": state.pipeline_status,
            "step_sha256": (state.ir_index or {}).get("step_sha256"),
            "errors": [{"code": e.get("code", "ERROR")} for e in state.errors],
        }
        self._write_summary()

    def extract(self, input_id: str) -> ProductLiveRunState:
        with self._lock:
            if self._closed or self._summary_failed:
                raise App004LiveError("APP004_SERVICE_CLOSED")
            if input_id not in APP004_INPUT_IDS:
                raise App004LiveError("APP004_INPUT_ID_NOT_ALLOWED")
            if input_id in self._used_inputs:
                raise App004LiveError("APP004_INPUT_ALREADY_USED")
            current_inputs = _load_frozen_inputs()
            if current_inputs != self._inputs:
                raise App004LiveError("APP004_INPUTS_CHANGED_AFTER_PREFLIGHT")
            self._used_inputs.add(input_id)
            request_text = self._inputs[input_id]
            logical_run_id = f"{input_id}__{APP004_CONDITION}__{APP004_PROVIDER}__{APP004_MODEL}"
            if not self.authorization.allows_logical_run(logical_run_id, APP004_PROVIDER):
                raise App004LiveError("APP004_LOGICAL_RUN_OUTSIDE_SCOPE")
            transport: Any = self._transport
            if self._formal:
                transport = BudgetAwareTransport(
                    self._transport, ledger=self._ledger, authorization=self.authorization,
                    logical_run_id=logical_run_id, provider=APP004_PROVIDER, model=APP004_MODEL,
                    adapter_run_id=logical_run_id, query_id=input_id, condition_id=APP004_CONDITION,
                )
            capture = _CaptureTransport(transport)
            plan = ProductLiveLogicalRunPlan(
                logical_run_id=logical_run_id, input_id=input_id,
                condition_id=APP004_CONDITION, provider=APP004_PROVIDER, model=APP004_MODEL,
            )
            try:
                state = _run_one_logical_mock(
                    plan=plan, natural_language=request_text, prompt=load_frozen_prompt(),
                    transport=capture, authorization=self.authorization,
                    pipeline_output_root=self._pipeline_root / input_id,
                )
            except Exception:
                state = ProductLiveRunState(
                    logical_run_id=logical_run_id, input_id=input_id,
                    condition_id=APP004_CONDITION, provider=APP004_PROVIDER, model=APP004_MODEL,
                    llm_status="error", product_status=PRODUCT_LIVE_STATUS_ERROR,
                    decision="", extracted_parameters={}, missing_fields=[],
                    unsupported_requests=[], questions=[], conflicts=[],
                    errors=[{"code": "APP004_EXTRACTION_FAILED", "message": "抽取失败，请查看稳定错误码。"}],
                    request_text=request_text,
                )
            # The boundary challenge can never become CAD eligible, even if the
            # model unexpectedly labels it answer with no unsupported fields.
            if input_id == _D02 and state.product_status == PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
                state.product_status = PRODUCT_LIVE_STATUS_BLOCKED
                state.errors = [{"code": "SCOPE_CAD_DENIED", "message": "此演示输入禁止进入 CAD 构造。"}]
            if capture.last_body is not None and self._formal and self._batch_dir is not None:
                policy = RetentionPolicy(retain_raw=True, base_dir=f"work/app001-runs/{APP004_BATCH_ID}/raw")
                meta = _retain_response(capture.last_body, logical_run_id, input_id, policy)
                state.raw_retention_meta = meta
                state.raw_retention_path = meta.get("path")
            # Provider-controlled diagnostics are never returned or summarized.
            for err in state.errors:
                code = str(err.get("code", "ERROR"))
                if code in {"TRANSPORT_EXCEPTION", "ADAPTER_EXCEPTION"}:
                    err["message"] = "请求失败；未能完成模型抽取。"
            self._runs[logical_run_id] = state
            try:
                self._update_summary(state)
            except Exception as exc:
                self._summary_failed = True
                if self._summary is not None:
                    self._summary["batch_status"] = "aborted"
                if self._ledger is not None:
                    self._ledger.release_lock()
                raise App004LiveError("APP004_SUMMARY_UPDATE_FAILED") from exc
            return state

    def confirm(self, logical_run_id: str, confirmed: bool) -> ProductLiveRunState | None:
        with self._lock:
            if self._closed or self._summary_failed:
                return None
            state = self._runs.get(logical_run_id)
            if state is None:
                return None
            if state.input_id != _D01 or state.product_status != PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION:
                return None
            result = confirm_product_live_run(
                state, confirmed=confirmed, patch=None, output_root=self._pipeline_root,
            )
            # Confirmation returns a new ProductLiveRunState. Preserve the
            # extraction audit metadata so the summary update cannot erase
            # the raw-response retention record for a successfully confirmed run.
            result.raw_retention_meta = state.raw_retention_meta
            result.raw_retention_path = state.raw_retention_path
            self._runs[logical_run_id] = result
            try:
                self._update_summary(result)
            except Exception as exc:
                self._summary_failed = True
                if self._summary is not None:
                    self._summary["batch_status"] = "aborted"
                if self._ledger is not None:
                    self._ledger.release_lock()
                raise App004LiveError("APP004_SUMMARY_UPDATE_FAILED") from exc
            return result

    def get(self, logical_run_id: str) -> ProductLiveRunState | None:
        return self._runs.get(logical_run_id)

    def get_step_bytes_secure(self, logical_run_id: str) -> bytes | None:
        state = self._runs.get(logical_run_id)
        if state is None or state.input_id != _D01 or state.product_status != PRODUCT_LIVE_STATUS_SUCCEEDED:
            return None
        if not state.step_path or not state.pipeline_run_dir or not isinstance(state.ir_index, dict):
            return None
        expected = state.ir_index.get("step_sha256")
        if not isinstance(expected, str):
            return None
        try:
            raw_run_dir = Path(state.pipeline_run_dir)
            raw_step = Path(state.step_path)
            # Reject a symlinked leaf before resolve() erases that fact.
            if raw_step.is_symlink():
                return None
            run_dir = raw_run_dir.resolve(strict=True)
            step = raw_step.resolve(strict=True)
            step.relative_to((run_dir / "cad_output").resolve())
            allowed_root = _BATCH_DIR if self._formal else self._pipeline_root
            step.relative_to(allowed_root.resolve(strict=True))
            if not step.is_file() or step.stat().st_size == 0:
                return None
            content = step.read_bytes()
        except (OSError, ValueError, RuntimeError):
            return None
        return content if hashlib.sha256(content).hexdigest() == expected else None

    def close(self, *, batch_status: str = "complete") -> None:
        with self._lock:
            if self._closed:
                return
            if self._summary is not None:
                if self._summary_failed:
                    final_status = "aborted"
                elif batch_status == "complete":
                    # An interrupted demo with unrun frozen inputs is partial,
                    # even when the server shuts down cleanly.
                    completed_ids = {
                        row.get("input_id")
                        for row in self._summary.get("runs", {}).values()
                        if isinstance(row, dict)
                    }
                    final_status = "complete" if completed_ids == set(APP004_INPUT_IDS) else "partial"
                else:
                    final_status = batch_status
                self._summary["batch_status"] = final_status
                self._summary["batch_finished_utc"] = _utc_now_iso()
                self._write_summary()
            if self._ledger is not None:
                self._ledger.release_lock()
            self._closed = True


__all__ = [
    "App004LiveError", "App004LiveWebService", "authorize_app004_live_web_run",
    "run_app004_offline_preflight",
]
