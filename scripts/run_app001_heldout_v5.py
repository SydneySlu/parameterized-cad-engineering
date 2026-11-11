#!/usr/bin/env python3
"""Controlled entry point for ADR-0019 held-out v5 evaluation.

This script is the ONLY authorized entry point for the 12-run held-out
evaluation matrix (3 queries × C0/C1 × DeepSeek/Ollama).  It is completely
independent of ``run_app001_v5_formal_batch.py`` and must not be replaced by it.

Offline modes (always safe, no network calls):

    # Dry-run / plan mode — 12 planned runs, hash pins, budget summary
    PYTHONPATH=src:. python scripts/run_app001_heldout_v5.py --dry-run

    # Offline preflight — full preflight without any HTTP request
    PYTHONPATH=src:. python scripts/run_app001_heldout_v5.py \\
        --offline-preflight --batch-id app001-heldout-v5-20261112-01

Formal run (requires project-owner authorization for the specific batch_id):

    PYTHONPATH=src:. python scripts/run_app001_heldout_v5.py \\
        --run --batch-id app001-heldout-v5-20261112-01

Hard constraints enforced by this script:
- FORMAL_EVALUATION_ALLOWED=False → formal mode is fail-closed by default.
- --run is blocked unless a valid HeldoutRunAuthorization is constructed
  (which requires the caller to have project-owner approval and pass
  --allow-formal-run explicitly after final offline preflight passes).
- Evaluator labels are never read, logged, or included in any output.
- No network calls in --dry-run or --offline-preflight modes.
- No batch directory is created in --dry-run or --offline-preflight modes.
- No credentials are read in --dry-run or --offline-preflight modes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# PYTHONPATH guard
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ADR-0019 held-out v5 evaluation runner (offline-first)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --dry-run             Generate and print the 12-run plan. No network calls.
  --offline-preflight   Run full offline preflight for a batch_id. No network.
  --run                 Execute the 12 runs (requires --batch-id and
                        --allow-formal-run; blocked by default).

The --allow-formal-run flag is a belt-and-suspenders guard.
It does NOT substitute for project-owner authorization of the specific batch_id.
Only pass it after the offline preflight passes and the project owner has
reviewed and approved the complete authorization template.
""",
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Print 12-run plan (no network calls)")
    mode.add_argument("--offline-preflight", action="store_true",
                      help="Run offline preflight only (no network calls)")
    mode.add_argument("--run", action="store_true",
                      help="Execute formal 12-run batch (requires authorization)")
    p.add_argument("--batch-id", default=None,
                   help="Batch identifier (required for --offline-preflight and --run)")
    p.add_argument("--allow-formal-run", action="store_true",
                   help="Belt-and-suspenders guard for --run mode (see docs)")
    p.add_argument("--json", action="store_true",
                   help="Output result as JSON")
    return p.parse_args()


def _print_result(obj: object, as_json: bool) -> None:
    if as_json:
        if hasattr(obj, "__dict__"):
            print(json.dumps(obj.__dict__, default=str, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(str(obj), ensure_ascii=False, indent=2))
    else:
        print(obj)


def main() -> int:
    args = _parse_args()

    from llm.gate import FormalEvaluationBlockedError
    from llm.heldout_runner import HeldoutRunner, HeldoutBatchSummary

    # ------------------------------------------------------------------
    # Dry-run mode
    # ------------------------------------------------------------------
    if args.dry_run:
        runner = HeldoutRunner()
        summary = runner.dry_run()
        if args.json:
            out = {
                "mode": summary.mode,
                "planned_runs": summary.planned_runs,
                "formal_evaluation_allowed": summary.formal_evaluation_allowed,
                "dry_run_plan": summary.dry_run_plan,
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            plan = summary.dry_run_plan or {}
            print(f"=== Held-out v5 dry-run plan ({plan.get('count', '?')} runs) ===")
            print(f"inputs_sha256:          {plan.get('inputs_sha256', '?')}")
            print(f"evaluator_labels_sha256:{plan.get('evaluator_labels_sha256', '?')}")
            print(f"plan_sha256:            {plan.get('plan_sha256', '?')}")
            budget = plan.get("budget", {})
            print(f"budget.max_chat:        {budget.get('max_chat_attempts', '?')}")
            print(f"budget.max_http:        {budget.get('max_batch_http', '?')}")
            print()
            for c in plan.get("combinations", []):
                print(
                    f"  [{c.get('index', '?'):2d}] {c.get('logical_run_id', '?')}"
                )
        return 0

    # ------------------------------------------------------------------
    # Offline preflight mode
    # ------------------------------------------------------------------
    if args.offline_preflight:
        if not args.batch_id:
            print("ERROR: --offline-preflight requires --batch-id", file=sys.stderr)
            return 2
        # Optionally load RET-002 retrieval index for C1 config check
        retrieval_index = _try_load_retrieval_index()
        runner = HeldoutRunner(retrieval_index=retrieval_index)
        try:
            summary = runner.offline_preflight(args.batch_id)
        except (FormalEvaluationBlockedError, Exception) as exc:
            print(f"PREFLIGHT FAILED: {exc}", file=sys.stderr)
            return 1
        result = summary.offline_preflight_result or {}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("=== Held-out v5 offline preflight ===")
            for k, v in result.items():
                print(f"  {k}: {v}")
        return 0

    # ------------------------------------------------------------------
    # Formal run mode
    # ------------------------------------------------------------------
    if args.run:
        if not args.batch_id:
            print("ERROR: --run requires --batch-id", file=sys.stderr)
            return 2
        if not args.allow_formal_run:
            print(
                "ERROR: --run requires --allow-formal-run. "
                "Only pass this flag after the offline preflight passes and "
                "the project owner has approved the complete authorization template.",
                file=sys.stderr,
            )
            return 2
        from llm.contract import FORMAL_EVALUATION_ALLOWED
        if not FORMAL_EVALUATION_ALLOWED:
            print(
                "ERROR: FORMAL_EVALUATION_ALLOWED=False. "
                "The global evaluation gate is closed. "
                "A new ADR and project-owner authorization are required.",
                file=sys.stderr,
            )
            return 2
        from llm.heldout_authorization import authorize_heldout_v5_run
        auth = authorize_heldout_v5_run(batch_id=args.batch_id)
        retrieval_index = _load_retrieval_index_or_fail()
        runner = HeldoutRunner(retrieval_index=retrieval_index)
        try:
            summary = runner.run_formal(auth)
        except (FormalEvaluationBlockedError, Exception) as exc:
            print(f"RUN FAILED: {exc}", file=sys.stderr)
            return 1
        if args.json:
            out = {
                "mode": summary.mode,
                "batch_id": summary.batch_id,
                "planned_runs": summary.planned_runs,
                "completed_runs": summary.completed_runs,
                "successful_runs": summary.successful_runs,
                "failed_runs": summary.failed_runs,
                "blocked_runs": summary.blocked_runs,
                "total_attempts": summary.total_attempts,
                "run_record_paths": list(summary.run_record_paths),
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"=== Held-out v5 formal run complete ===")
            print(f"  batch_id:         {summary.batch_id}")
            print(f"  planned_runs:     {summary.planned_runs}")
            print(f"  successful_runs:  {summary.successful_runs}")
            print(f"  failed_runs:      {summary.failed_runs}")
            print(f"  blocked_runs:     {summary.blocked_runs}")
            print(f"  total_attempts:   {summary.total_attempts}")
        return 0

    return 0


def _try_load_retrieval_index() -> object | None:
    """Attempt to load the RET-002 retrieval index; return None on failure."""
    try:
        from retrieval import RetrievalIndex
        from retrieval.config import DEFAULT_CONFIG_REL_PATH, REPO_ROOT
        config_path = REPO_ROOT / DEFAULT_CONFIG_REL_PATH
        if not config_path.exists():
            return None
        return RetrievalIndex.from_config(config_path, repo_root=REPO_ROOT)
    except Exception:
        return None


def _load_retrieval_index_or_fail() -> object:
    """Load the RET-002 retrieval index; raise on failure."""
    from retrieval import RetrievalIndex
    from retrieval.config import DEFAULT_CONFIG_REL_PATH, REPO_ROOT
    config_path = REPO_ROOT / DEFAULT_CONFIG_REL_PATH
    return RetrievalIndex.from_config(config_path, repo_root=REPO_ROOT)


if __name__ == "__main__":
    sys.exit(main())
