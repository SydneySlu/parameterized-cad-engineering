#!/usr/bin/env python3
"""Validate the repository's lightweight project-management contract."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md",
    "README.md",
    "docs/PROJECT_STATUS.md",
    "docs/PROJECT_PLAN.md",
    "docs/TASKS.md",
    "docs/WORKLOG.md",
    "docs/DECISIONS.md",
    "docs/coordination/agent-bootstrap.md",
    "docs/coordination/orchestrator.md",
    "docs/coordination/progress-sync.md",
]
VALID_STATUS = {"planned", "in_progress", "blocked", "review", "done", "deferred"}


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    for path in REQUIRED:
        if not (ROOT / path).is_file():
            errors.append(f"missing required file: {path}")

    tasks_text = (ROOT / "docs/TASKS.md").read_text(encoding="utf-8") if (ROOT / "docs/TASKS.md").exists() else ""
    status_text = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8") if (ROOT / "docs/PROJECT_STATUS.md").exists() else ""
    task_ids = set(re.findall(r"\|\s*([A-Z]+-\d+)\s*\|", tasks_text))
    if not task_ids:
        errors.append("no task IDs found in docs/TASKS.md")
    for state in re.findall(r"\|\s*([A-Z]+-\d+)\s*\|[^\n]*?\|\s*(planned|in_progress|blocked|review|done|deferred)\s*\|", tasks_text):
        if state[1] not in VALID_STATUS:
            errors.append(f"invalid task status: {state[0]}={state[1]}")
    for status_id in re.findall(r"\|\s*([A-Z]+-\d+)\s*\|", status_text):
        if status_id not in task_ids:
            warnings.append(f"status page references task absent from TASKS.md: {status_id}")

    git_status = run("git", "status", "--porcelain")
    if git_status:
        warnings.append("working tree has uncommitted changes")
    if not run("git", "remote"):
        warnings.append("no Git remote configured; cross-device sync is not active")
    diff_check = subprocess.run(["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True, check=False)
    if diff_check.returncode:
        errors.append("git diff --check failed:\n" + diff_check.stdout + diff_check.stderr)

    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: project state valid ({len(task_ids)} task IDs checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

