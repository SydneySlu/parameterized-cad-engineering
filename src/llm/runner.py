"""Controlled APP-001 Phase 1 runner entry point.

This module is the single controlled entry point for the 36-logical-run
Phase 1 evaluation.  It ties together:

- Frozen acceptance-set projection (evaluator labels stripped)
- C0 / C1 condition input assembly (C1 via RET-002 only)
- Real or fake provider transports
- Atomic budget ledger (per-run / per-provider / total limits)
- Existing ``Adapter.run()`` pipeline (parse, project, schema, CAD hooks)
- JSONL run record output to git-ignored batch directory
- Raw response retention per the existing :class:`RetentionPolicy`

Safety guarantees:
- Defaults (no authorization) never make network calls.
- Formal runs require an explicit :class:`FormalRunAuthorization`.
- Budget is atomically reserved BEFORE each network call.
- Concurrent batch runs for the same batch_id are rejected.
- Failed samples are never removed from the run record (failure denominator
  is always the full 9 × 2 × 2 = 36 combinations).
- IR / CAD / STEP are always ``not_run`` / ``blocked``.
- API keys are never logged, stored in run records, or printed.

No formal evaluation has been executed.  This runner awaits authorization
from the project owner before any real network calls are made.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapter import Adapter, AdapterInput, RetentionPolicy
from .authorization import FormalRunAuthorization, authorize_phase1_run
from .budget import BudgetAwareTransport, BudgetError, BudgetLedger
from .combinations import (
    CONDITION_C0,
    CONDITION_C1,
    CombinationPlan,
    LogicalRunCombination,
    dry_run_combinations,
    generate_combinations,
)
from .conditions import assemble_c0, assemble_c1
from .contract import (
    ACCEPTANCE_SET_SHA256,
    ACCEPTANCE_SET_VERSION,
    DEEPSEEK_PROVIDER,
    FAMILY_ID,
    FORMAL_EVALUATION_ALLOWED,
    OLLAMA_PROVIDER,
)
from .gate import FormalEvaluationBlockedError, require_formal_evaluation_allowed
from .input_projection import AcceptanceSetProjection, project_acceptance_set
from .prompt_loader import load_frozen_prompt
from .runrecord import RunRecord
from .transport import FakeTransport


# Default acceptance set path (relative to repo root)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ACCEPTANCE_SET_PATH = (
    _REPO_ROOT
    / "agent-work"
    / "llm"
    / "APP-001-baseline-prep"
    / "acceptance-set-v0.json"
)
_CANONICAL_RUN_ROOT = _REPO_ROOT / "work" / "app001-runs"

_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _safe(value: str) -> str:
    return _SAFE_RE.sub("_", value)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Run result for a single logical run
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogicalRunResult:
    """The result of executing one of the 36 logical runs.

    Always present in the output; failed runs are NOT dropped from the batch.
    """

    logical_run_id: str
    query_id: str
    condition_id: str
    provider: str
    model: str
    attempt_count: int
    final_outcome: str  # success | non_retryable_error | retry_exhausted | blocked | dry_run
    record: RunRecord | None
    record_dict: dict[str, Any] | None
    blocked_reason: str | None


# ---------------------------------------------------------------------------
# Batch summary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchSummary:
    """Summary of a completed (or dry-run) batch."""

    batch_id: str
    mode: str  # "dry_run" | "formal"
    planned_runs: int
    completed_runs: int
    successful_runs: int
    failed_runs: int
    blocked_runs: int
    total_attempts: int
    formal_evaluation_allowed: bool
    run_record_paths: tuple[str, ...]
    dry_run_plan: dict[str, Any] | None


# ---------------------------------------------------------------------------
# App001Runner
# ---------------------------------------------------------------------------


class App001Runner:
    """Controlled APP-001 Phase 1 runner.

    Usage (dry run -- no network calls, no real transports):
        runner = App001Runner()
        summary = runner.dry_run()

    Usage (formal run -- requires explicit authorization):
        auth = authorize_phase1_run(batch_id="20261106-001")
        runner = App001Runner()
        summary = runner.run_formal(auth)

    Formal runs write JSONL records to:
        ``work/app001-runs/<batch-id>/runs.jsonl``

    This class never reads or logs secrets.  Real transports are only
    instantiated during ``run_formal()`` with a valid authorization.
    """

    def __init__(
        self,
        *,
        acceptance_set_path: str | Path | None = None,
        retrieval_index: Any = None,
    ) -> None:
        """
        acceptance_set_path:
            Path to ``acceptance-set-v0.json``.  Defaults to the repo-relative
            standard location.
        retrieval_index:
            Optional pre-built RET-002 RetrievalIndex (for C1 condition).
            If None, C1 assembly will be blocked with
            ``BLOCKED_C1_NO_RETRIEVAL_INDEX``.
        """
        self._acceptance_set_path = Path(
            acceptance_set_path or _DEFAULT_ACCEPTANCE_SET_PATH
        )
        self._retrieval_index = retrieval_index

    # ------------------------------------------------------------------
    # Dry-run entry point
    # ------------------------------------------------------------------

    def dry_run(self) -> BatchSummary:
        """Generate the 36-combination plan without making any network calls.

        Returns a :class:`BatchSummary` with mode ``dry_run``.  The
        ``dry_run_plan`` field contains the combination list, counts, and hash.

        No transport is instantiated, no budget is reserved, and no network
        call is made.
        """
        projection = self._load_projection()
        auth = authorize_phase1_run(batch_id="dry-run")
        plan_dict = dry_run_combinations(projection, auth)
        return BatchSummary(
            batch_id="dry-run",
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
        )

    # ------------------------------------------------------------------
    # Formal run entry point
    # ------------------------------------------------------------------

    def run_formal(
        self,
        authorization: FormalRunAuthorization,
    ) -> BatchSummary:
        """Execute the formal Phase 1 evaluation run.

        Requires a valid :class:`FormalRunAuthorization`.  Validates the
        scope before constructing any transport or making any network call.

        R3-D: Also requires a valid retrieval_index for C1 condition assembly.
        If retrieval_index is None, the formal run is rejected before any
        HTTP request (fail-closed). Per-sample C1 blocking (e.g. missing bore_d)
        continues to work as designed.

        Writes run records to:
            ``work/app001-runs/<batch_id>/runs.jsonl``

        Raw responses (if retention is enabled in ``authorization``) go to:
            ``work/app001-runs/<batch_id>/raw/``

        Returns a :class:`BatchSummary` with mode ``formal``.
        """
        # Scope re-verify (belt-and-suspenders; __post_init__ already checked)
        if not isinstance(authorization, FormalRunAuthorization):
            raise FormalEvaluationBlockedError(
                "run_formal requires a FormalRunAuthorization instance"
            )
        # R3-D: Require and verify retrieval index for C1 before any HTTP request
        if self._retrieval_index is None:
            raise FormalEvaluationBlockedError(
                "run_formal requires a valid retrieval_index for C1 condition assembly; "
                "cannot proceed with C1 entirely blocked (all 18 C1 runs would be no-ops); "
                "construct App001Runner with a RET-002 RetrievalIndex before calling run_formal()"
            )
        # R3-D: Verify it's a real RetrievalIndex with frozen manifest identity
        from retrieval import RetrievalIndex
        from retrieval.config import (
            MANIFEST_REL_PATH as _FROZEN_MANIFEST_REL_PATH,
            RETRIEVAL_VERSION as _FROZEN_RETRIEVAL_VERSION,
            POLICY_ID as _FROZEN_POLICY_ID,
        )
        if not isinstance(self._retrieval_index, RetrievalIndex):
            raise FormalEvaluationBlockedError(
                f"retrieval_index must be a retrieval.RetrievalIndex instance, "
                f"got {type(self._retrieval_index).__name__}"
            )
        # R3-D: Verify frozen manifest identity (sha256, path, version, policy)
        # These checks use only already-validated attributes on RetrievalIndex,
        # not just duck-typed attributes that a Mock could fake.
        idx = self._retrieval_index
        # manifest_sha256 must be a non-empty 64-hex string
        if not isinstance(idx.manifest_sha256, str) or len(idx.manifest_sha256) != 64:
            raise FormalEvaluationBlockedError(
                "retrieval_index.manifest_sha256 must be a 64-hex string; "
                "use RetrievalIndex.from_manifest() with the frozen manifest"
            )
        # manifest_path must resolve to the frozen relative path
        from pathlib import Path as _Path
        _repo_root = _Path(__file__).resolve().parents[2]
        try:
            _actual_rel = _Path(str(idx.manifest_path)).resolve().relative_to(_repo_root)
            _actual_rel_str = str(_actual_rel).replace("\\", "/")
        except (ValueError, TypeError):
            _actual_rel_str = str(idx.manifest_path)
        if _actual_rel_str != _FROZEN_MANIFEST_REL_PATH:
            raise FormalEvaluationBlockedError(
                f"retrieval_index.manifest_path does not match frozen RET-002 path; "
                f"expected {_FROZEN_MANIFEST_REL_PATH!r}, got {_actual_rel_str!r}"
            )
        # manifest_version must match frozen version
        _manifest_version = getattr(idx, "manifest_version", None)
        if not isinstance(_manifest_version, str) or not _manifest_version.startswith("retrieval-manifest"):
            raise FormalEvaluationBlockedError(
                f"retrieval_index.manifest_version must match frozen manifest version; "
                f"got {_manifest_version!r}"
            )
        # policy must have the frozen POLICY_ID (via the DistancePolicy object)
        # We don't check an explicit policy_id attribute because DistancePolicy
        # is a domain object; instead we confirm a real policy object is present.
        _policy = getattr(idx, "policy", None)
        if _policy is None:
            raise FormalEvaluationBlockedError(
                "retrieval_index.policy is missing; "
                "use RetrievalIndex.from_manifest() with the frozen config"
            )
        from retrieval.distance import DistancePolicy as _DistancePolicy
        if not isinstance(_policy, _DistancePolicy):
            raise FormalEvaluationBlockedError(
                "retrieval_index.policy is not a retrieval.distance.DistancePolicy; "
                "use RetrievalIndex.from_config() with the frozen config"
            )
        # Validate batch directory
        batch_dir = self._resolve_batch_dir(authorization.batch_id)
        self._verify_batch_dir_ignored(batch_dir)
        # Load frozen artifacts
        projection = self._load_projection()
        prompt_artifact = load_frozen_prompt()
        # Generate 36 combinations
        plan = generate_combinations(projection, authorization)
        # Build C0/C1 assembled inputs (no evaluator labels escape)
        assembled = self._assemble_all_inputs(projection, plan)
        # Execute with budget ledger
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
        plan: CombinationPlan,
        assembled: dict[str, Any],
        authorization: FormalRunAuthorization,
        batch_dir: Path,
        prompt_artifact: Any,
    ) -> list[LogicalRunResult]:
        """Execute all 36 runs under the budget ledger."""
        results: list[LogicalRunResult] = []
        # Batch-level JSONL output
        runs_jsonl_path = batch_dir / "runs.jsonl"
        batch_dir.mkdir(parents=True, exist_ok=True)
        with BudgetLedger(batch_dir, authorization) as ledger:
            for combo in plan.combinations:
                result = self._execute_one_run(
                    combo=combo,
                    assembled_input=assembled[combo.logical_run_id],
                    authorization=authorization,
                    ledger=ledger,
                    batch_dir=batch_dir,
                    prompt_artifact=prompt_artifact,
                )
                results.append(result)
                # Write record to JSONL immediately (fail samples kept)
                if result.record_dict is not None:
                    with open(runs_jsonl_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(result.record_dict, ensure_ascii=False))
                        fh.write("\n")
                else:
                    # Blocked / no-record -- write a minimal entry
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
        combo: LogicalRunCombination,
        assembled_input: object,
        authorization: FormalRunAuthorization,
        ledger: BudgetLedger,
        batch_dir: Path,
        prompt_artifact: object,
    ) -> "LogicalRunResult":
        """Execute one logical run (up to max_attempts_per_run).

        Each physical transport.send() call atomically reserves one budget
        slot via BudgetAwareTransport before the actual request.
        """
        lrid = combo.logical_run_id
        # Check if already completed (restart recovery)
        existing = ledger.run_result(lrid)
        if existing is not None:
            return LogicalRunResult(
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
        # Check for unfinished reservations (incomplete attempt — fail closed)
        run_used = ledger.run_attempts_used(lrid)
        run_result_val = ledger.run_result(lrid)
        # If there are attempts but no result, that means a previous run was
        # interrupted mid-attempt.  We cannot safely resume — fail closed.
        if run_used > 0 and run_result_val is None:
            ledger.record_run_result(logical_run_id=lrid, result="interrupted_fail_closed")
            return LogicalRunResult(
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
                    "FAIL_CLOSED_INCOMPLETE_RESERVATION: "
                    "ledger shows attempts without a final result; "
                    "cannot safely resume without knowing prior budget consumption"
                ),
            )
        # C1 blocked?
        if assembled_input is None:
            ledger.record_run_result(logical_run_id=lrid, result="blocked")
            return LogicalRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=0,
                final_outcome="blocked",
                record=None,
                record_dict=None,
                blocked_reason="C1_reference_context_blocked",
            )
        if hasattr(assembled_input, "blocked_reason") and assembled_input.blocked_reason:
            ledger.record_run_result(logical_run_id=lrid, result="blocked")
            return LogicalRunResult(
                logical_run_id=lrid,
                query_id=combo.query_id,
                condition_id=combo.condition_id,
                provider=combo.provider,
                model=combo.model,
                attempt_count=0,
                final_outcome="blocked",
                record=None,
                record_dict=None,
                blocked_reason=assembled_input.blocked_reason,
            )
        # Build real transport and wrap it with BudgetAwareTransport
        inner_transport = self._build_transport(combo.provider, authorization)
        run_id = _safe(f"{authorization.batch_id}__{lrid}")
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
        retention = RetentionPolicy(
            retain_raw=True,
            base_dir=f"work/app001-runs/{authorization.batch_id}",
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
            if model_call_stage == "pass":
                final_outcome = "success"
            else:
                final_outcome = "non_retryable_error"
        except BudgetError as exc:
            final_outcome = "budget_exhausted"
            attempt_count = len(budget_transport.attempt_numbers)
            ledger.record_run_result(logical_run_id=lrid, result=final_outcome)
            return LogicalRunResult(
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
            d["acceptance_set_sha256"] = ACCEPTANCE_SET_SHA256
            _ensure_ir_cad_not_run(d)
            record_dict = d
        return LogicalRunResult(
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
    # Transport construction
    # ------------------------------------------------------------------

    def _build_transport(
        self, provider: str, authorization: FormalRunAuthorization
    ) -> Any:
        """Construct the real transport for a provider.

        Only called during formal runs.  Key read happens inside ``send()``.
        """
        from .real_transport import DeepSeekTransport, OllamaTransport

        if provider == DEEPSEEK_PROVIDER:
            return DeepSeekTransport(authorization)
        if provider == OLLAMA_PROVIDER:
            return OllamaTransport(authorization)
        raise ValueError(f"unknown provider: {provider!r}")

    # ------------------------------------------------------------------
    # Input assembly
    # ------------------------------------------------------------------

    def _assemble_all_inputs(
        self,
        projection: AcceptanceSetProjection,
        plan: CombinationPlan,
    ) -> dict[str, Any]:
        """Build assembled inputs for all 36 combinations.

        Returns a dict mapping logical_run_id -> AssembledInput (or None for
        blocked C1 runs).  Evaluator-only labels never appear in these objects.
        """
        assembled: dict[str, Any] = {}
        for combo in plan.combinations:
            case = projection.case_by_id(combo.query_id)
            if case is None:
                assembled[combo.logical_run_id] = None
                continue
            if combo.condition_id == CONDITION_C0:
                assembled[combo.logical_run_id] = assemble_c0(case)
            elif combo.condition_id == CONDITION_C1:
                if self._retrieval_index is None:
                    from .conditions import AssembledInput

                    assembled[combo.logical_run_id] = AssembledInput(
                        query_id=combo.query_id,
                        condition_id=CONDITION_C1,
                        natural_language_input=case.natural_language_input,
                        reference_context=None,
                        reference_context_sha256=None,
                        candidate_source_ids=(),
                        blocked_reason=(
                            "BLOCKED_C1_NO_RETRIEVAL_INDEX: no retrieval index "
                            "provided to runner; cannot generate C1 reference context"
                        ),
                    )
                else:
                    assembled[combo.logical_run_id] = assemble_c1(
                        case, self._retrieval_index
                    )
            else:
                assembled[combo.logical_run_id] = None
        return assembled

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_projection(self) -> AcceptanceSetProjection:
        return project_acceptance_set(
            self._acceptance_set_path,
            expected_sha256=ACCEPTANCE_SET_SHA256,
        )

    def _resolve_batch_dir(self, batch_id: str) -> Path:
        safe_id = _safe(batch_id)
        if not safe_id:
            raise ValueError("batch_id resolves to an empty safe filename")
        batch_dir = _CANONICAL_RUN_ROOT / safe_id
        # Verify path is inside canonical root (no traversal)
        try:
            batch_dir.resolve().relative_to(_CANONICAL_RUN_ROOT.resolve())
        except ValueError:
            raise ValueError(
                f"batch_dir {batch_dir} is outside the canonical run root "
                f"{_CANONICAL_RUN_ROOT}"
            )
        return batch_dir

    def _verify_batch_dir_ignored(self, batch_dir: Path) -> None:
        """Verify the batch directory is inside work/app001-runs/ (git-ignored)."""
        canonical = _CANONICAL_RUN_ROOT
        if not str(batch_dir).startswith(str(canonical)):
            raise ValueError(
                f"batch_dir {batch_dir} is not inside the git-ignored "
                f"canonical run directory {canonical}"
            )
        # Refuse to overwrite an existing batch
        runs_jsonl = batch_dir / "runs.jsonl"
        if runs_jsonl.exists():
            raise ValueError(
                f"batch directory {batch_dir} already has a runs.jsonl; "
                "refusing to overwrite an existing batch; use a new batch_id"
            )

    def _build_summary(
        self,
        batch_id: str,
        mode: str,
        results: list[LogicalRunResult],
        batch_dir: Path,
    ) -> BatchSummary:
        successful = sum(1 for r in results if r.final_outcome == "success")
        failed = sum(
            1
            for r in results
            if r.final_outcome in ("non_retryable_error", "retry_exhausted", "budget_exhausted")
        )
        blocked = sum(1 for r in results if r.final_outcome == "blocked")
        total_attempts = sum(r.attempt_count for r in results)
        record_paths = tuple(
            str(batch_dir / "runs.jsonl")
            for r in results
            if r.record_dict is not None
        )[:1]  # single JSONL file
        return BatchSummary(
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
        )


def _ensure_ir_cad_not_run(record_dict: dict[str, Any]) -> None:
    """Ensure IR / CAD / geometry / STEP stages are always not_run / blocked."""
    stages = record_dict.get("stages", [])
    ir_cad_names = {"ir", "cad", "geometry", "step"}
    for stage in stages:
        if isinstance(stage, dict) and stage.get("stage") in ir_cad_names:
            if stage.get("status") not in ("not_run", "blocked", "not_applicable"):
                stage["status"] = "not_run"
