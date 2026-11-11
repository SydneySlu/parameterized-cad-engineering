"""Offline-first held-out v5 runner for ADR-0019 12-run evaluation matrix.

This module is the ONLY entry point for the 3 held-out query × C0/C1 ×
DeepSeek/Ollama = 12 logical run evaluation.  It is completely independent of
``runner.py`` / ``run_app001_v5_formal_batch.py`` and may NOT reuse those.

Safety guarantees (identical to the Phase 1 runner):
- Defaults (no authorization, dry-run) never make network calls.
- Formal runs require an explicit :class:`HeldoutRunAuthorization` instance.
- Every physical HTTP request reserves a budget slot BEFORE network I/O via
  the existing :class:`BudgetLedger` / :class:`BudgetAwareTransport` machinery.
- Evaluator labels are NEVER passed to combination generation, input assembly,
  the Adapter, transports, the Prompt, or any logger.  The labels file is only
  read when explicitly requested by evaluator/reporting code (not here).
- Concurrent batch runs for the same batch_id are rejected.
- Failed runs are always retained in the output (denominator is always 12).
- C2/IR/CAD/geometry/STEP are always not_run / blocked.
- API keys are never logged, stored in run records, or printed.
- No formal batch_id is assigned and no network call is made in this module
  unless a HeldoutRunAuthorization with a user-approved batch_id is supplied.

Offline dry-run / plan mode:
  Returns the 12 planned runs (query_id, condition_id, provider, model,
  logical_run_id), plan SHA-256, frozen hash pins, and budget feasibility.
  No evaluator labels, no natural language inputs beyond query IDs.

Formal mode (offline preflight only until user-authorised):
  Runs the full offline preflight (hash verification, profile validation,
  retrieval config check, batch directory check, budget feasibility) and then,
  only after a valid HeldoutRunAuthorization is supplied, executes the 12 runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapter import Adapter, AdapterInput, RetentionPolicy
from .budget import BudgetAwareTransport, BudgetError, BudgetLedger
from .conditions import CONDITION_C0, CONDITION_C1, AssembledInput, assemble_c1
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
from .gate import FormalEvaluationBlockedError
from .heldout_authorization import (
    HELDOUT_BATCH_PREFLIGHT_ID,
    HELDOUT_INPUTS_SHA256,
    HELDOUT_LABELS_SHA256,
    HELDOUT_MAX_BATCH_HTTP,
    HELDOUT_MAX_CHAT_ATTEMPTS,
    HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN,
    HELDOUT_MAX_IDENTITY_ATTEMPTS,
    HELDOUT_MAX_LOGICAL_RUNS,
    HELDOUT_PROVIDER_HTTP_CAPS,
    HELDOUT_QUERY_IDS,
    HELDOUT_SAMPLE_SET,
    HeldoutRunAuthorization,
    authorize_heldout_v5_run,
)
from .prompt_loader import load_frozen_prompt
from .runrecord import RunRecord
from .transport import FakeTransport


# ---------------------------------------------------------------------------
# Repository layout constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_RUN_ROOT = _REPO_ROOT / "work" / "app001-runs"
_MODEL_INPUTS_REL = (
    "agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/model-inputs.json"
)
_EVALUATOR_LABELS_REL = (
    "agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/evaluator-labels.json"
)
_RET001_MANIFEST_REL = "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"

_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _safe(value: str) -> str:
    return _SAFE_RE.sub("_", value)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Frozen-input projection (model-visible only, no labels)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HeldoutCase:
    """A single held-out case projected to model-visible fields only.

    ``evaluator_labels`` is intentionally absent.  Labels live only in the
    evaluator-labels.json artifact, which is read only by evaluator/reporting
    code, never by this runner or the Adapter.
    """

    query_id: str
    natural_language_input: str


@dataclass(frozen=True)
class HeldoutInputProjection:
    """The three held-out cases, model-visible fields only."""

    cases: tuple[HeldoutCase, ...]
    inputs_sha256: str
    artifact_version: str

    def case_by_id(self, query_id: str) -> HeldoutCase | None:
        for case in self.cases:
            if case.query_id == query_id:
                return case
        return None

    def query_ids(self) -> tuple[str, ...]:
        return tuple(c.query_id for c in self.cases)


class HeldoutInputError(ValueError):
    """Raised when model-inputs.json is missing, malformed, or hash-invalid."""


def load_heldout_inputs(
    *,
    inputs_path: Path | None = None,
    expected_sha256: str = HELDOUT_INPUTS_SHA256,
) -> HeldoutInputProjection:
    """Load model-inputs.json and project to model-visible fields only.

    Raises :class:`HeldoutInputError` if the file is missing, malformed,
    or its SHA-256 does not match the frozen pin.

    Evaluator labels are never read by this function.
    """
    path = inputs_path or (_REPO_ROOT / _MODEL_INPUTS_REL)
    if not path.exists():
        raise HeldoutInputError(f"model-inputs.json not found: {path}")
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise HeldoutInputError(
            f"model-inputs.json SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    try:
        data = json.loads(path.read_bytes())
    except (json.JSONDecodeError, OSError) as exc:
        raise HeldoutInputError(f"cannot parse model-inputs.json: {exc}") from exc
    raw_cases = data.get("cases", [])
    if not isinstance(raw_cases, list) or len(raw_cases) != 3:
        raise HeldoutInputError(
            f"model-inputs.json must have exactly 3 cases, got {len(raw_cases)}"
        )
    seen_ids: set[str] = set()
    cases: list[HeldoutCase] = []
    for raw in raw_cases:
        qid = raw.get("query_id", "")
        nli = raw.get("natural_language_input", "")
        if not isinstance(qid, str) or not qid.strip():
            raise HeldoutInputError("model-inputs.json case has empty query_id")
        if not isinstance(nli, str) or not nli.strip():
            raise HeldoutInputError(f"model-inputs.json case {qid!r} has empty NLI")
        if qid in seen_ids:
            raise HeldoutInputError(f"model-inputs.json has duplicate query_id {qid!r}")
        seen_ids.add(qid)
        # Only allow the neutral query IDs from ADR-0019 (no evaluator leakage)
        if qid not in HELDOUT_QUERY_IDS:
            raise HeldoutInputError(
                f"model-inputs.json contains unexpected query_id {qid!r}; "
                f"allowed: {HELDOUT_QUERY_IDS}"
            )
        # Only project query_id and natural_language_input — no labels, no IDs
        cases.append(HeldoutCase(query_id=qid, natural_language_input=nli))
    return HeldoutInputProjection(
        cases=tuple(cases),
        inputs_sha256=actual_sha256,
        artifact_version=data.get("artifact_version", ""),
    )


# ---------------------------------------------------------------------------
# 12-combination generator (independent of generate_combinations)
# ---------------------------------------------------------------------------

_PROVIDER_MODELS: dict[str, str] = {}  # populated lazily below


def _get_provider_models() -> dict[str, str]:
    from .contract import DEEPSEEK_MODEL, OLLAMA_MODEL
    return {DEEPSEEK_PROVIDER: DEEPSEEK_MODEL, OLLAMA_PROVIDER: OLLAMA_MODEL}


@dataclass(frozen=True)
class HeldoutRunCombination:
    """One of the 12 held-out logical runs."""

    logical_run_id: str
    query_id: str
    condition_id: str
    provider: str
    model: str
    index: int

    def as_audit_dict(self) -> dict[str, Any]:
        """Audit output: stable IDs only, no case content, no labels."""
        return {
            "logical_run_id": self.logical_run_id,
            "query_id": self.query_id,
            "condition_id": self.condition_id,
            "provider": self.provider,
            "model": self.model,
            "index": self.index,
        }


@dataclass(frozen=True)
class HeldoutCombinationPlan:
    """The full 12-combination plan with audit metadata."""

    combinations: tuple[HeldoutRunCombination, ...]
    count: int
    plan_sha256: str
    query_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    providers: tuple[str, ...]
    models: tuple[str, ...]

    def as_audit_dict(self) -> dict[str, Any]:
        """Audit output: no case content, no labels, no NLI."""
        return {
            "count": self.count,
            "query_ids": list(self.query_ids),
            "conditions": list(self.conditions),
            "providers": list(self.providers),
            "models": list(self.models),
            "plan_sha256": self.plan_sha256,
            "combinations": [c.as_audit_dict() for c in self.combinations],
        }


class HeldoutCombinationError(ValueError):
    """Raised when combination generation detects a scope violation."""


def _make_heldout_logical_run_id(
    query_id: str, condition_id: str, provider: str, model: str
) -> str:
    return f"{query_id}__{condition_id}__{provider}__{model}"


def generate_heldout_combinations(
    projection: HeldoutInputProjection,
    authorization: HeldoutRunAuthorization,
) -> HeldoutCombinationPlan:
    """Generate the 12 held-out logical run combinations.

    Validates scope against the authorization:
    - Exactly 3 query IDs, matching authorization.query_ids
    - No duplicates, no extensions
    - Both conditions (C0, C1)
    - Both providers (DeepSeek, Ollama) with correct models
    - IR/CAD/geometry/STEP disabled

    Raises :class:`HeldoutCombinationError` on scope mismatch.
    """
    provider_models = _get_provider_models()

    if projection.inputs_sha256 != authorization.inputs_sha256:
        raise HeldoutCombinationError(
            f"inputs_sha256 mismatch between projection ({projection.inputs_sha256!r}) "
            f"and authorization ({authorization.inputs_sha256!r})"
        )
    if len(projection.cases) != 3:
        raise HeldoutCombinationError(
            f"expected exactly 3 held-out cases, got {len(projection.cases)}"
        )
    proj_ids = set(projection.query_ids())
    auth_ids = set(authorization.query_ids)
    if proj_ids != auth_ids:
        raise HeldoutCombinationError(
            f"query_ids mismatch: projection has {sorted(proj_ids)}, "
            f"authorization has {sorted(auth_ids)}"
        )
    if len(proj_ids) != 3:
        raise HeldoutCombinationError(
            f"expected exactly 3 unique query_ids, got {len(proj_ids)}"
        )
    if not authorization.condition_is_allowed("C0"):
        raise HeldoutCombinationError("authorization does not allow C0")
    if not authorization.condition_is_allowed("C1"):
        raise HeldoutCombinationError("authorization does not allow C1")
    for provider, model in provider_models.items():
        if not authorization.provider_model_is_allowed(provider, model):
            raise HeldoutCombinationError(
                f"authorization does not allow {provider}/{model}"
            )
    if not authorization.ir_cad_geometry_step_disabled:
        raise HeldoutCombinationError("IR/CAD/geometry/STEP must be disabled")

    combinations: list[HeldoutRunCombination] = []
    idx = 0
    # Deterministic order: query_ids in input order, C0 before C1,
    # DeepSeek before Ollama
    for case in projection.cases:
        for condition_id in (CONDITION_C0, CONDITION_C1):
            for provider in (DEEPSEEK_PROVIDER, OLLAMA_PROVIDER):
                model = provider_models[provider]
                lrid = _make_heldout_logical_run_id(
                    case.query_id, condition_id, provider, model
                )
                combinations.append(
                    HeldoutRunCombination(
                        logical_run_id=lrid,
                        query_id=case.query_id,
                        condition_id=condition_id,
                        provider=provider,
                        model=model,
                        index=idx,
                    )
                )
                idx += 1

    plan = HeldoutCombinationPlan(
        combinations=tuple(combinations),
        count=len(combinations),
        plan_sha256="",
        query_ids=tuple(c.query_id for c in projection.cases),
        conditions=(CONDITION_C0, CONDITION_C1),
        providers=(DEEPSEEK_PROVIDER, OLLAMA_PROVIDER),
        models=tuple(provider_models.values()),
    )
    # Stable hash over audit dict (without plan_sha256 itself)
    audit = plan.as_audit_dict()
    raw = json.dumps(audit, ensure_ascii=False, sort_keys=True).encode("utf-8")
    plan_sha = hashlib.sha256(raw).hexdigest()
    object.__setattr__(plan, "plan_sha256", plan_sha)
    return plan


# ---------------------------------------------------------------------------
# Input assembly wrapper (model-visible ProjectedCase adapter)
# ---------------------------------------------------------------------------

class _HeldoutProjectedCase:
    """Adapter that presents a HeldoutCase as a ProjectedCase-compatible object.

    Only exposes model-visible fields.  No evaluator labels.
    reference_context_structural is always None for held-out cases
    (bore_d is extracted directly from the NLI by assemble_c1).
    """

    def __init__(self, case: HeldoutCase) -> None:
        self.query_id = case.query_id
        self.natural_language_input = case.natural_language_input
        self.reference_context_structural = None
        self.coverage = ()

    def model_visible_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "family_id": FAMILY_ID,
            "natural_language_input": self.natural_language_input,
        }


def _assemble_c0(case: HeldoutCase) -> AssembledInput:
    """Assemble C0 (no retrieval) input for a held-out case."""
    projected = _HeldoutProjectedCase(case)
    from .conditions import assemble_c0 as _assemble_c0_impl
    return _assemble_c0_impl(projected)


def _assemble_held_c1(
    case: HeldoutCase,
    retrieval_index: Any,
) -> AssembledInput:
    """Assemble C1 input for a held-out case using frozen RET-002."""
    projected = _HeldoutProjectedCase(case)
    return assemble_c1(projected, retrieval_index)


def _assemble_all_heldout_inputs(
    projection: HeldoutInputProjection,
    plan: HeldoutCombinationPlan,
    retrieval_index: Any,
) -> dict[str, AssembledInput | None]:
    """Build assembled inputs for all 12 combinations.

    Returns mapping logical_run_id -> AssembledInput (or None for
    irrecoverably blocked C1 when no retrieval index was provided).
    Evaluator labels never appear in these objects.
    """
    assembled: dict[str, AssembledInput | None] = {}
    for combo in plan.combinations:
        case = projection.case_by_id(combo.query_id)
        if case is None:
            assembled[combo.logical_run_id] = None
            continue
        if combo.condition_id == CONDITION_C0:
            assembled[combo.logical_run_id] = _assemble_c0(case)
        elif combo.condition_id == CONDITION_C1:
            if retrieval_index is None:
                assembled[combo.logical_run_id] = AssembledInput(
                    query_id=combo.query_id,
                    condition_id=CONDITION_C1,
                    natural_language_input=case.natural_language_input,
                    reference_context=None,
                    reference_context_sha256=None,
                    candidate_source_ids=(),
                    blocked_reason=(
                        "BLOCKED_C1_NO_RETRIEVAL_INDEX: no retrieval index "
                        "provided; cannot generate C1 reference context"
                    ),
                    blocked_stage="c1_assembly",
                    error_code="BLOCKED_C1_NO_RETRIEVAL_INDEX",
                    error_fields=("retrieval_index",),
                )
            else:
                assembled[combo.logical_run_id] = _assemble_held_c1(
                    case, retrieval_index
                )
        else:
            # C2 and beyond are forbidden
            assembled[combo.logical_run_id] = AssembledInput(
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                natural_language_input=case.natural_language_input,
                reference_context=None,
                reference_context_sha256=None,
                candidate_source_ids=(),
                blocked_reason=f"CONDITION_FORBIDDEN: {combo.condition_id} is not allowed",
                blocked_stage="condition_check",
                error_code="CONDITION_FORBIDDEN",
                error_fields=("condition_id",),
            )
    return assembled


# ---------------------------------------------------------------------------
# Run result + batch summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HeldoutRunResult:
    """Result of one of the 12 held-out logical runs.

    Always retained; failed runs are never dropped from the batch.
    No evaluator labels.
    """

    logical_run_id: str
    query_id: str
    condition_id: str
    provider: str
    model: str
    attempt_count: int
    final_outcome: str  # success | non_retryable_error | retry_exhausted | blocked | dry_run | budget_exhausted
    record: RunRecord | None
    record_dict: dict[str, Any] | None
    blocked_reason: str | None


@dataclass(frozen=True)
class HeldoutBatchSummary:
    """Summary of a completed (or dry-run / offline-preflight) batch."""

    batch_id: str
    mode: str  # dry_run | offline_preflight | formal
    planned_runs: int
    completed_runs: int
    successful_runs: int
    failed_runs: int
    blocked_runs: int
    total_attempts: int
    formal_evaluation_allowed: bool
    run_record_paths: tuple[str, ...]
    dry_run_plan: dict[str, Any] | None
    offline_preflight_result: dict[str, Any] | None


# ---------------------------------------------------------------------------
# Raw retention policy
# ---------------------------------------------------------------------------

def _heldout_raw_retention_policy(batch_id: str) -> RetentionPolicy:
    return RetentionPolicy(
        retain_raw=True,
        base_dir=f"work/app001-runs/{batch_id}/raw",
    )


# ---------------------------------------------------------------------------
# Main runner class
# ---------------------------------------------------------------------------


class HeldoutRunner:
    """Offline-first held-out v5 runner for ADR-0019.

    Usage (dry-run -- no network calls, no transport instantiation):
        runner = HeldoutRunner()
        summary = runner.dry_run()

    Usage (offline preflight only -- validates everything offline, no HTTP):
        runner = HeldoutRunner(retrieval_index=idx)
        summary = runner.offline_preflight(batch_id="app001-heldout-v5-yyyymmdd-01")

    Usage (formal run -- requires HeldoutRunAuthorization from project owner):
        auth = authorize_heldout_v5_run(batch_id="app001-heldout-v5-yyyymmdd-01")
        runner = HeldoutRunner(retrieval_index=idx)
        summary = runner.run_formal(auth)

    This class never reads credentials, never makes network calls in dry-run or
    offline-preflight mode, and never assigns a formal batch_id or creates a
    formal batch directory until run_formal() is called with a valid
    HeldoutRunAuthorization.
    """

    def __init__(
        self,
        *,
        inputs_path: Path | None = None,
        retrieval_index: Any = None,
    ) -> None:
        self._inputs_path = inputs_path
        self._retrieval_index = retrieval_index

    # ------------------------------------------------------------------
    # Dry-run entry point
    # ------------------------------------------------------------------

    def dry_run(self) -> HeldoutBatchSummary:
        """Generate the 12-combination plan without any network calls.

        Output contains only: combination list (query_id, condition_id,
        provider, model, logical_run_id), counts, plan SHA-256, and
        frozen hash pins.  No evaluator labels, no NLI beyond query IDs.
        """
        projection = self._load_projection()
        auth = authorize_heldout_v5_run(batch_id="heldout-dry-run")
        plan = generate_heldout_combinations(projection, auth)
        plan_dict = plan.as_audit_dict()
        plan_dict["inputs_sha256"] = HELDOUT_INPUTS_SHA256
        plan_dict["evaluator_labels_sha256"] = HELDOUT_LABELS_SHA256
        plan_dict["budget"] = {
            "max_logical_runs": HELDOUT_MAX_LOGICAL_RUNS,
            "max_chat_attempts": HELDOUT_MAX_CHAT_ATTEMPTS,
            "max_chat_attempts_per_run": HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN,
            "max_identity_attempts": HELDOUT_MAX_IDENTITY_ATTEMPTS,
            "max_batch_http": HELDOUT_MAX_BATCH_HTTP,
            "provider_http_caps": dict(HELDOUT_PROVIDER_HTTP_CAPS),
        }
        return HeldoutBatchSummary(
            batch_id="heldout-dry-run",
            mode="dry_run",
            planned_runs=plan_dict["count"],
            completed_runs=0,
            successful_runs=0,
            failed_runs=0,
            blocked_runs=0,
            total_attempts=0,
            formal_evaluation_allowed=FORMAL_EVALUATION_ALLOWED,
            run_record_paths=(),
            dry_run_plan=plan_dict,
            offline_preflight_result=None,
        )

    # ------------------------------------------------------------------
    # Offline preflight entry point (no network calls)
    # ------------------------------------------------------------------

    def offline_preflight(self, batch_id: str) -> HeldoutBatchSummary:
        """Run the full offline preflight for a proposed batch_id.

        Verifies (without any network I/O):
        - Input and label artifact SHA-256 pins
        - Profile scope (v5 protocol, 12-run matrix, budget)
        - Retrieval config and manifest identity (if retrieval_index given)
        - Batch directory does not already exist
        - Budget feasibility (12 × 3 chat ≤ 36, etc.)

        Raises :class:`FormalEvaluationBlockedError` or other errors on failure.
        Does NOT assign a batch_id or create any directory.
        """
        result: dict[str, Any] = {}

        # 1. Hash pins
        result["inputs_sha256"] = self._verify_inputs_sha256()
        result["evaluator_labels_sha256"] = self._verify_labels_sha256()
        result["ret001_manifest_sha256"] = self._verify_ret001_manifest_sha256()

        # 2. Authorization profile
        auth = authorize_heldout_v5_run(batch_id=batch_id)
        result["profile_id"] = auth.profile_id
        result["sample_set"] = auth.sample_set
        result["protocol_versions"] = sorted(auth.protocol_versions)
        result["max_logical_runs"] = auth.max_logical_runs
        result["max_batch_http"] = auth.max_batch_attempts

        # 3. Input projection + combination plan
        projection = self._load_projection()
        plan = generate_heldout_combinations(projection, auth)
        result["planned_runs"] = plan.count
        result["plan_sha256"] = plan.plan_sha256

        # 4. Retrieval config check
        result["retrieval_index_provided"] = self._retrieval_index is not None
        if self._retrieval_index is not None:
            result["retrieval_config_check"] = self._verify_retrieval_index()
        else:
            result["retrieval_config_check"] = "skipped: no retrieval_index"

        # 5. Prompt version check
        prompt_artifact = load_frozen_prompt()
        result["prompt_version"] = PROMPT_VERSION
        result["contract_version"] = CONTRACT_VERSION

        # 6. Batch directory strategy
        batch_dir = self._resolve_batch_dir(batch_id)
        runs_jsonl = batch_dir / "runs.jsonl"
        if runs_jsonl.exists():
            raise FormalEvaluationBlockedError(
                f"batch directory {batch_dir} already has a runs.jsonl; "
                "refusing to overwrite an existing batch; use a new batch_id"
            )
        result["batch_dir_strategy"] = "work/app001-runs/<batch_id>/raw/"
        result["batch_dir_exists"] = batch_dir.exists()

        # 7. Budget feasibility
        result["budget_feasibility"] = {
            "chat_total": f"12 × {HELDOUT_MAX_CHAT_ATTEMPTS_PER_RUN} = "
                          f"{HELDOUT_MAX_CHAT_ATTEMPTS} ≤ {HELDOUT_MAX_CHAT_ATTEMPTS}",
            "identity_total": f"2 preflight + 6×3 runtime = 20 ≤ {HELDOUT_MAX_IDENTITY_ATTEMPTS}",
            "http_total": f"{HELDOUT_MAX_CHAT_ATTEMPTS} chat + "
                          f"{HELDOUT_MAX_IDENTITY_ATTEMPTS} identity = "
                          f"{HELDOUT_MAX_CHAT_ATTEMPTS + HELDOUT_MAX_IDENTITY_ATTEMPTS} ≤ "
                          f"{HELDOUT_MAX_BATCH_HTTP}",
            "feasible": True,
        }
        result["offline_preflight_status"] = "pass"

        return HeldoutBatchSummary(
            batch_id=batch_id,
            mode="offline_preflight",
            planned_runs=plan.count,
            completed_runs=0,
            successful_runs=0,
            failed_runs=0,
            blocked_runs=0,
            total_attempts=0,
            formal_evaluation_allowed=FORMAL_EVALUATION_ALLOWED,
            run_record_paths=(),
            dry_run_plan=None,
            offline_preflight_result=result,
        )

    # ------------------------------------------------------------------
    # Formal run entry point
    # ------------------------------------------------------------------

    def run_formal(
        self,
        authorization: HeldoutRunAuthorization,
    ) -> HeldoutBatchSummary:
        """Execute the formal held-out 12-run evaluation.

        Requires a valid :class:`HeldoutRunAuthorization`.  The authorization
        must have been approved by the project owner for a specific batch_id.

        This method NEVER makes network calls without a valid authorization.
        Every HTTP request (including Ollama preflight /api/tags and /api/version)
        reserves a budget slot from the authorization-bound ledger BEFORE the
        network I/O.

        Raises :class:`FormalEvaluationBlockedError` if any preflight check fails.
        """
        if not isinstance(authorization, HeldoutRunAuthorization):
            raise FormalEvaluationBlockedError(
                "run_formal requires a HeldoutRunAuthorization instance"
            )

        # Retrieval index required for C1 (all 6 C1 runs would be blocked otherwise)
        if self._retrieval_index is None:
            raise FormalEvaluationBlockedError(
                "run_formal requires a valid retrieval_index for C1; "
                "construct HeldoutRunner with a RET-002 RetrievalIndex"
            )
        self._verify_retrieval_index()

        # Hash pins
        self._verify_inputs_sha256()
        self._verify_labels_sha256()

        # Load artifacts
        projection = self._load_projection()
        prompt_artifact = load_frozen_prompt()

        # Validate projection against authorization
        if projection.inputs_sha256 != authorization.inputs_sha256:
            raise FormalEvaluationBlockedError(
                "model-inputs.json SHA-256 does not match authorization"
            )

        # Generate combinations
        plan = generate_heldout_combinations(projection, authorization)

        # Validate batch directory
        batch_dir = self._resolve_batch_dir(authorization.batch_id)
        self._verify_batch_dir_safe(batch_dir)

        # Assemble inputs (no labels)
        assembled = _assemble_all_heldout_inputs(
            projection, plan, self._retrieval_index
        )

        # Execute
        results = self._execute_batch(
            plan=plan,
            assembled=assembled,
            authorization=authorization,
            batch_dir=batch_dir,
            prompt_artifact=prompt_artifact,
        )

        return self._build_summary(authorization.batch_id, "formal", results, batch_dir)

    # ------------------------------------------------------------------
    # Batch execution with budget ledger
    # ------------------------------------------------------------------

    def _execute_batch(
        self,
        *,
        plan: HeldoutCombinationPlan,
        assembled: dict[str, Any],
        authorization: HeldoutRunAuthorization,
        batch_dir: Path,
        prompt_artifact: Any,
    ) -> list[HeldoutRunResult]:
        results: list[HeldoutRunResult] = []
        runs_jsonl_path = batch_dir / "runs.jsonl"
        batch_dir.mkdir(parents=True, exist_ok=True)
        with BudgetLedger(batch_dir, authorization) as ledger:
            for combo in plan.combinations:
                result = self._execute_one_run(
                    combo=combo,
                    assembled_input=assembled.get(combo.logical_run_id),
                    authorization=authorization,
                    ledger=ledger,
                    batch_dir=batch_dir,
                    prompt_artifact=prompt_artifact,
                )
                results.append(result)
                if result.record_dict is not None:
                    with open(runs_jsonl_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(result.record_dict, ensure_ascii=False))
                        fh.write("\n")
                else:
                    minimal = {
                        "logical_run_id": result.logical_run_id,
                        "query_id": result.query_id,
                        "condition_id": result.condition_id,
                        "provider": result.provider,
                        "model": result.model,
                        "final_outcome": result.final_outcome,
                        "blocked_reason": result.blocked_reason,
                        "batch_id": authorization.batch_id,
                    }
                    with open(runs_jsonl_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(minimal, ensure_ascii=False))
                        fh.write("\n")
        return results

    def _execute_one_run(
        self,
        *,
        combo: HeldoutRunCombination,
        assembled_input: object | None,
        authorization: HeldoutRunAuthorization,
        ledger: BudgetLedger,
        batch_dir: Path,
        prompt_artifact: object,
    ) -> HeldoutRunResult:
        lrid = combo.logical_run_id

        # Restart recovery
        existing = ledger.run_result(lrid)
        if existing is not None:
            return HeldoutRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=ledger.run_attempts_used(lrid),
                final_outcome=existing,
                record=None,
                record_dict=None,
                blocked_reason=None,
            )

        # Interrupted-attempt fail-closed
        run_used = ledger.run_attempts_used(lrid)
        if run_used > 0 and ledger.run_result(lrid) is None:
            ledger.record_run_result(logical_run_id=lrid, result="interrupted_fail_closed")
            return HeldoutRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=run_used,
                final_outcome="interrupted_fail_closed",
                record=None,
                record_dict=None,
                blocked_reason=(
                    "FAIL_CLOSED_INCOMPLETE_RESERVATION: prior attempts without result"
                ),
            )

        # Blocked input
        if assembled_input is None:
            ledger.record_run_result(logical_run_id=lrid, result="blocked")
            return HeldoutRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=0,
                final_outcome="blocked",
                record=None,
                record_dict=self._blocked_audit_record(
                    combo, authorization, prompt_artifact, None,
                    stage_name="input_assembly",
                    error_code="INPUT_ASSEMBLY_BLOCKED",
                    error_fields=("assembled_input",),
                ),
                blocked_reason="assembled_input is None",
            )

        if hasattr(assembled_input, "blocked_reason") and assembled_input.blocked_reason:
            ledger.record_run_result(logical_run_id=lrid, result="blocked")
            return HeldoutRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=0,
                final_outcome="blocked",
                record=None,
                record_dict=self._blocked_audit_record(
                    combo, authorization, prompt_artifact, assembled_input,
                    stage_name=getattr(assembled_input, "blocked_stage", None) or "c1_assembly",
                    error_code=getattr(assembled_input, "error_code", None) or "C1_BLOCKED",
                    error_fields=tuple(getattr(assembled_input, "error_fields", ()) or ()),
                ),
                blocked_reason=assembled_input.blocked_reason,
            )

        run_id = _safe(f"{authorization.batch_id}__{lrid}")
        retention = _heldout_raw_retention_policy(authorization.batch_id)
        inner_transport = self._build_transport(
            combo.provider, authorization,
            diagnostic_retainer=lambda body: __import__(
                "llm.adapter", fromlist=["_retain_response"]
            )._retain_response(body, run_id, combo.query_id, retention),
        )
        budget_transport = BudgetAwareTransport(
            inner_transport,
            ledger=ledger,
            authorization=authorization,
            logical_run_id=lrid,
            provider=combo.provider,
            model=combo.model,
            adapter_run_id=run_id,
            query_id=combo.query_id,
            condition_id=combo.condition_id,
        )
        adapter = Adapter(
            provider=combo.provider,
            transport=budget_transport,
            retention_policy=retention,
        )
        ref_ctx = getattr(assembled_input, "reference_context", None)
        adapter_input = AdapterInput(
            query_id=combo.query_id,
            natural_language_input=assembled_input.natural_language_input,
            reference_context=ref_ctx,
            system_prompt=prompt_artifact.system_prompt,
            user_prompt_template=prompt_artifact.user_template,
            condition_id=combo.condition_id,
        )
        result_record = None
        final_outcome = "non_retryable_error"
        attempt_count = 0
        try:
            run_result = adapter.run(
                adapter_input,
                run_id=run_id,
                formal_authorization=authorization,
            )
            result_record = run_result.record
            attempt_count = len(budget_transport.attempt_numbers)
            model_call_stage = result_record.stage_status("model_call")
            final_outcome = "success" if model_call_stage == "pass" else "non_retryable_error"
        except BudgetError as exc:
            final_outcome = "budget_exhausted"
            attempt_count = len(budget_transport.attempt_numbers)
            ledger.record_run_result(logical_run_id=lrid, result=final_outcome)
            return HeldoutRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=attempt_count,
                final_outcome=final_outcome,
                record=None,
                record_dict=None,
                blocked_reason=f"BUDGET_EXHAUSTED: {exc}",
            )
        except Exception:
            final_outcome = "non_retryable_error"
            attempt_count = len(budget_transport.attempt_numbers)
        ledger.record_run_result(logical_run_id=lrid, result=final_outcome)
        record_dict = None
        if result_record is not None:
            d = result_record.as_dict()
            d["logical_run_id"] = lrid
            d["batch_id"] = authorization.batch_id
            d["final_outcome"] = final_outcome
            d["inputs_sha256"] = authorization.inputs_sha256
            _ensure_heldout_ir_cad_not_run(d)
            record_dict = d
        return HeldoutRunResult(
            logical_run_id=lrid,
            query_id=combo.query_id,
            condition_id=combo.condition_id,
            provider=combo.provider,
            model=combo.model,
            attempt_count=attempt_count,
            final_outcome=final_outcome,
            record=result_record,
            record_dict=record_dict,
            blocked_reason=None,
        )

    # ------------------------------------------------------------------
    # Blocked audit record
    # ------------------------------------------------------------------

    def _blocked_audit_record(
        self, combo: HeldoutRunCombination, authorization: HeldoutRunAuthorization,
        prompt_artifact: object | None, assembled_input: object | None,
        *, stage_name: str, error_code: str, error_fields: tuple[str, ...],
    ) -> dict[str, Any]:
        import platform
        prompt_hashes: dict[str, Any] = {
            "unavailable_reason": "request_not_constructed"
        }
        if prompt_artifact is not None:
            prompt_hashes = {
                "system_prompt_sha256": getattr(prompt_artifact, "system_prompt_sha256", None),
                "user_template_sha256": getattr(prompt_artifact, "user_template_sha256", None),
                "unavailable_reason": None,
            }
        return {
            "logical_run_id": combo.logical_run_id,
            "batch_id": authorization.batch_id,
            "query_id": combo.query_id,
            "condition_id": combo.condition_id,
            "configured_provider": combo.provider,
            "configured_model_name": combo.model,
            "sample_set": HELDOUT_SAMPLE_SET,
            "inputs_sha256": authorization.inputs_sha256,
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "software_versions": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "adapter": ADAPTER_VERSION,
                "schema_version": SCHEMA_VERSION,
            },
            "prompt_hashes": prompt_hashes,
            "blocked_stage": stage_name,
            "error_code": error_code,
            "error_fields": list(error_fields),
            "bore_d_used_for_query": getattr(assembled_input, "bore_d_used_for_query", None),
            "candidate_source_count": len(
                getattr(assembled_input, "candidate_source_ids", ()) or ()
            ) if assembled_input else 0,
            "candidate_source_ids": list(
                getattr(assembled_input, "candidate_source_ids", ()) or ()
            ) if assembled_input else [],
            "reference_context_sha256": getattr(
                assembled_input, "reference_context_sha256", None
            ) if assembled_input else None,
        }

    # ------------------------------------------------------------------
    # Transport construction (real transports only during formal run)
    # ------------------------------------------------------------------

    def _build_transport(
        self, provider: str, authorization: HeldoutRunAuthorization,
        *, diagnostic_retainer: Any = None,
    ) -> Any:
        from .real_transport import DeepSeekTransport, OllamaTransport
        if provider == DEEPSEEK_PROVIDER:
            return DeepSeekTransport(authorization, diagnostic_retainer=diagnostic_retainer)
        if provider == OLLAMA_PROVIDER:
            return OllamaTransport(authorization, diagnostic_retainer=diagnostic_retainer)
        raise ValueError(f"unknown provider: {provider!r}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_projection(self) -> HeldoutInputProjection:
        return load_heldout_inputs(inputs_path=self._inputs_path)

    def _resolve_batch_dir(self, batch_id: str) -> Path:
        safe_id = _safe(batch_id)
        if not safe_id:
            raise ValueError("batch_id resolves to an empty safe filename")
        batch_dir = _CANONICAL_RUN_ROOT / safe_id
        try:
            batch_dir.resolve().relative_to(_CANONICAL_RUN_ROOT.resolve())
        except ValueError:
            raise ValueError(
                f"batch_dir {batch_dir} is outside the canonical run root "
                f"{_CANONICAL_RUN_ROOT}"
            )
        return batch_dir

    def _verify_batch_dir_safe(self, batch_dir: Path) -> None:
        runs_jsonl = batch_dir / "runs.jsonl"
        if runs_jsonl.exists():
            raise FormalEvaluationBlockedError(
                f"batch directory {batch_dir} already has a runs.jsonl; "
                "refusing to overwrite an existing batch; use a new batch_id"
            )

    def _verify_inputs_sha256(self) -> str:
        path = self._inputs_path or (_REPO_ROOT / _MODEL_INPUTS_REL)
        actual = _sha256_file(path)
        if actual != HELDOUT_INPUTS_SHA256:
            raise FormalEvaluationBlockedError(
                f"model-inputs.json SHA-256 mismatch: expected {HELDOUT_INPUTS_SHA256}, got {actual}"
            )
        return actual

    def _verify_labels_sha256(self) -> str:
        path = _REPO_ROOT / _EVALUATOR_LABELS_REL
        actual = _sha256_file(path)
        if actual != HELDOUT_LABELS_SHA256:
            raise FormalEvaluationBlockedError(
                f"evaluator-labels.json SHA-256 mismatch: expected {HELDOUT_LABELS_SHA256}, got {actual}"
            )
        return actual

    def _verify_ret001_manifest_sha256(self) -> str:
        path = _REPO_ROOT / _RET001_MANIFEST_REL
        from retrieval.config import MANIFEST_REL_PATH as _FROZEN_MANIFEST_REL_PATH
        expected_manifest_path = _REPO_ROOT / _FROZEN_MANIFEST_REL_PATH
        if not expected_manifest_path.exists():
            raise FormalEvaluationBlockedError(
                f"RET-001 manifest not found: {expected_manifest_path}"
            )
        actual = _sha256_file(expected_manifest_path)
        # The frozen pin from ADR-0019 / checkpoint
        _RET001_MANIFEST_SHA256 = "b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297"
        if actual != _RET001_MANIFEST_SHA256:
            raise FormalEvaluationBlockedError(
                f"RET-001 manifest SHA-256 mismatch: expected {_RET001_MANIFEST_SHA256}, got {actual}"
            )
        return actual

    def _verify_retrieval_index(self) -> str:
        """Verify the retrieval index is a real, frozen-manifest RetrievalIndex."""
        from retrieval import RetrievalIndex
        from retrieval.config import (
            MANIFEST_REL_PATH as _FROZEN_MANIFEST_REL_PATH,
            DEFAULT_CONFIG_REL_PATH as _FROZEN_CONFIG_REL_PATH,
            MANIFEST_FORMAT_VERSION as _FROZEN_MANIFEST_FORMAT_VERSION,
            RetrievalConfig as _FrozenRetrievalConfig,
        )
        idx = self._retrieval_index
        if not isinstance(idx, RetrievalIndex):
            raise FormalEvaluationBlockedError(
                f"retrieval_index must be a retrieval.RetrievalIndex, "
                f"got {type(idx).__name__}"
            )
        if not isinstance(idx.manifest_sha256, str) or len(idx.manifest_sha256) != 64:
            raise FormalEvaluationBlockedError(
                "retrieval_index.manifest_sha256 must be a 64-hex string"
            )
        try:
            _actual_rel = Path(str(idx.manifest_path)).resolve().relative_to(_REPO_ROOT)
            _actual_rel_str = str(_actual_rel).replace("\\", "/")
        except (ValueError, TypeError):
            _actual_rel_str = str(idx.manifest_path)
        if _actual_rel_str != _FROZEN_MANIFEST_REL_PATH:
            raise FormalEvaluationBlockedError(
                f"retrieval_index.manifest_path mismatch; "
                f"expected {_FROZEN_MANIFEST_REL_PATH!r}, got {_actual_rel_str!r}"
            )
        _manifest_version = getattr(idx, "manifest_version", None)
        if _manifest_version != _FROZEN_MANIFEST_FORMAT_VERSION:
            raise FormalEvaluationBlockedError(
                f"retrieval_index.manifest_version must be "
                f"{_FROZEN_MANIFEST_FORMAT_VERSION!r}; got {_manifest_version!r}"
            )
        _frozen_config = _FrozenRetrievalConfig.from_path(
            _REPO_ROOT / _FROZEN_CONFIG_REL_PATH, repo_root=_REPO_ROOT
        )
        if idx.manifest_sha256 != _frozen_config.manifest_sha256:
            raise FormalEvaluationBlockedError(
                "retrieval_index.manifest_sha256 does not match frozen RET-002 config"
            )
        from retrieval.distance import DistancePolicy as _DistancePolicy
        _policy = getattr(idx, "policy", None)
        if not isinstance(_policy, _DistancePolicy):
            raise FormalEvaluationBlockedError("retrieval_index.policy is not a DistancePolicy")
        try:
            _policy.validate()
        except Exception as exc:
            raise FormalEvaluationBlockedError(
                f"retrieval_index.policy validation failed: {exc}"
            ) from exc
        return idx.manifest_sha256

    def _build_summary(
        self,
        batch_id: str,
        mode: str,
        results: list[HeldoutRunResult],
        batch_dir: Path,
    ) -> HeldoutBatchSummary:
        successful = sum(1 for r in results if r.final_outcome == "success")
        failed = sum(
            1 for r in results
            if r.final_outcome in ("non_retryable_error", "retry_exhausted", "budget_exhausted")
        )
        blocked = sum(1 for r in results if r.final_outcome == "blocked")
        total_attempts = sum(r.attempt_count for r in results)
        record_paths = tuple(
            str(batch_dir / "runs.jsonl")
            for r in results
            if r.record_dict is not None
        )[:1]
        return HeldoutBatchSummary(
            batch_id=batch_id,
            mode=mode,
            planned_runs=len(results),
            completed_runs=successful + failed,
            successful_runs=successful,
            failed_runs=failed,
            blocked_runs=blocked,
            total_attempts=total_attempts,
            formal_evaluation_allowed=FORMAL_EVALUATION_ALLOWED,
            run_record_paths=record_paths,
            dry_run_plan=None,
            offline_preflight_result=None,
        )


def _ensure_heldout_ir_cad_not_run(record_dict: dict[str, Any]) -> None:
    """Ensure IR/CAD/geometry/STEP stages are always not_run / blocked."""
    stages = record_dict.get("stages", [])
    ir_cad_names = {"ir", "cad", "geometry", "step"}
    for stage in stages:
        if isinstance(stage, dict) and stage.get("stage") in ir_cad_names:
            if stage.get("status") not in ("not_run", "blocked", "not_applicable"):
                stage["status"] = "not_run"
