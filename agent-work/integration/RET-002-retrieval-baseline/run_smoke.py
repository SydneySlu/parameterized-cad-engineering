#!/usr/bin/env python3
"""RET-002 smoke runner: normal, boundary, invalid and determinism cases.

Writes `smoke-report.json` next to this file and exits non-zero if any check
fails.  The runner reads only the RET-001 manifest, the retrieval config and
the example query files.  It does not read STEP, render images, IR files or any
BenchCAD Public/Core asset.

Usage:
    PYTHONPATH=src python3 agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from retrieval import RetrievalError, RetrievalIndex  # noqa: E402
from retrieval.config import (  # noqa: E402
    CONTINUOUS_FIELDS,
    MANIFEST_REL_PATH,
    PARAMETER_ORDER,
    POLICY_ID,
    RETRIEVAL_VERSION,
    SPLIT_STATUS,
)
from schema.set_screw_shaft_collar import FAMILY_ID  # noqa: E402


MANIFEST = REPO_ROOT / MANIFEST_REL_PATH
CONFIG = HERE.parent / "retrieval-config.json"
EXAMPLES = HERE.parent / "examples"
REPORT = HERE.parent / "smoke-report.json"
REPLAY = HERE.parent / "replay_query.py"
WORK_DIR = REPO_ROOT / "work" / "ret-002-output"
TZ = timezone(timedelta(hours=8))

BOUNDARY_CASE: dict[str, Any] = {
    "case": "boundary_bore_080_second_screw",
    "notes": (
        "bore_d=80 is the unique second_screw=1 hard boundary row and is heldout_evaluation. "
        "It must not appear as a candidate under retrieval_source."
    ),
    "family_id": FAMILY_ID,
    "parameters": {
        "bore_d": 80,
        "outer_d": 110,
        "screw_d": 12,
        "screw_len": 20,
        "second_screw": 1,
        "width": 22,
    },
    "top_k": 3,
    "expected": {
        "input_form": "flat_parameters",
        "query_status": "catalog_validated",
        "top1_sample_id": f"{FAMILY_ID}/catalog-bore-050",
        "top1_same_catalog_row": False,
        "top1_total_is_zero": False,
        "forbidden_sample_ids": [
            f"{FAMILY_ID}/catalog-bore-080",
            f"{FAMILY_ID}/catalog-bore-012",
            f"{FAMILY_ID}/catalog-bore-035",
        ],
        "candidate_roles": ["retrieval_source"],
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def _load_case(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_source"] = str(path.relative_to(REPO_ROOT))
    return data


def _run_success(index: RetrievalIndex, case: Mapping[str, Any]) -> dict[str, Any]:
    result = index.query(
        family_id=case["family_id"],
        parameters=case["parameters"],
        top_k=case.get("top_k"),
    )
    payload = result.as_dict()
    entries = payload["results"]

    checks: dict[str, bool] = {}
    checks["split_status_top_level"] = payload["split_status"] == SPLIT_STATUS
    checks["manifest_hash_matches"] = payload["manifest"]["sha256"] == sha256_file(MANIFEST)
    checks["manifest_record_count"] = payload["manifest"]["records"] == 15
    checks["result_count"] = len(entries) == payload["top_k"]
    checks["ranks_contiguous"] = [entry["rank"] for entry in entries] == list(range(1, len(entries) + 1))
    sort_keys = [(entry["distance"]["total"], entry["sample_id"]) for entry in entries]
    checks["sorted_total_then_sample_id"] = sort_keys == sorted(sort_keys)
    checks["roles_within_selection"] = all(
        entry["split"]["role"] in payload["candidate_roles"] for entry in entries
    )
    checks["provisional_split_on_each"] = all(
        entry["split"]["split_status"] == SPLIT_STATUS for entry in entries
    )
    checks["ir_and_source_present"] = all(
        entry["ir"]["path"]
        and len(entry["ir"]["sha256"]) == 64
        and entry["source"]["source_commit"] == "035f467142888edfd0bd7cd73906f9b155c8f43c"
        for entry in entries
    )
    checks["distance_decomposition"] = all(
        _close(
            math.fsum(field["contribution"] for field in entry["distance"]["fields"].values()),
            entry["distance"]["continuous_mean"],
        )
        and _close(
            entry["distance"]["continuous_mean"] + entry["distance"]["discrete_term"],
            entry["distance"]["total"],
            1e-15,
        )
        for entry in entries
    )
    checks["data_boundary_no_step"] = (
        payload["data_boundary"]["reads_step"] is False
        and payload["data_boundary"]["reads_render"] is False
        and payload["data_boundary"]["reads_ir_files"] is False
    )
    checks["notes_keep_limits"] = (
        any("not CAD geometry equivalence" in note for note in payload["notes"])
        and any("provisional_small_n" in note for note in payload["notes"])
    )

    expected = case.get("expected", {})
    if "input_form" in expected:
        checks["expected_input_form"] = payload["query"]["input_form"] == expected["input_form"]
    if "query_status" in expected:
        checks["expected_query_status"] = payload["query"]["query_status"] == expected["query_status"]
    if "candidate_roles" in expected:
        checks["expected_candidate_roles"] = payload["candidate_roles"] == expected["candidate_roles"]
    if "top1_sample_id" in expected:
        checks["expected_top1"] = bool(entries) and entries[0]["sample_id"] == expected["top1_sample_id"]
    if "top1_same_catalog_row" in expected:
        checks["expected_top1_same_catalog_row"] = (
            bool(entries)
            and entries[0]["same_catalog_row_as_query"] is expected["top1_same_catalog_row"]
        )
    if "top1_total_is_zero" in expected:
        checks["expected_top1_total_is_zero"] = bool(entries) and (
            (entries[0]["distance"]["total"] == 0.0) is expected["top1_total_is_zero"]
        )
    if "schema_error_codes" in expected:
        observed_codes = [error["code"] for error in payload["query"]["schema_check"]["errors"]]
        checks["expected_schema_error_codes"] = observed_codes == expected["schema_error_codes"]
    if "forbidden_sample_ids" in expected:
        observed_ids = {entry["sample_id"] for entry in entries}
        checks["forbidden_candidates_absent"] = not (observed_ids & set(expected["forbidden_sample_ids"]))

    ranking = []
    for entry in entries:
        distance = entry["distance"]
        ranking.append(
            {
                "rank": entry["rank"],
                "sample_id": entry["sample_id"],
                "role": entry["split"]["role"],
                "group_id": entry["split"]["group_id"],
                "total": distance["total"],
                "continuous_mean": distance["continuous_mean"],
                "discrete_term": distance["discrete_term"],
                "same_catalog_row_as_query": entry["same_catalog_row_as_query"],
                "ir_path": entry["ir"]["path"],
                "ir_sha256": entry["ir"]["sha256"],
                "source_commit": entry["source"]["source_commit"],
                "license_scope": entry["source"]["license_scope"],
                "field_distances": {
                    field: {
                        "query": distance["fields"][field]["query"],
                        "candidate": distance["fields"][field]["candidate"],
                        "catalog_range_mm": distance["fields"][field]["catalog_range_mm"],
                        "normalized_abs_diff": distance["fields"][field]["normalized_abs_diff"],
                        "contribution": distance["fields"][field]["contribution"],
                    }
                    for field in CONTINUOUS_FIELDS
                },
                "second_screw": distance["second_screw"],
            }
        )

    return {
        "case": case["case"],
        "source": case.get("_source", "inline:run_smoke.py"),
        "notes": case.get("notes"),
        "input_form": payload["query"]["input_form"],
        "query_status": payload["query"]["query_status"],
        "query_parameters": payload["query"]["parameters"],
        "top_k": payload["top_k"],
        "candidates_considered": payload["candidates_considered"],
        "schema_error_codes": [error["code"] for error in payload["query"]["schema_check"]["errors"]],
        "ranking": ranking,
        "checks": checks,
        "pass": all(checks.values()),
    }


def _run_failure(
    name: str,
    expected_code: str,
    action: Callable[[], Any],
    *,
    expected_fields: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    try:
        action()
    except RetrievalError as exc:
        payload = exc.as_dict()["error"]
        passed = payload["code"] == expected_code
        if expected_fields is not None:
            passed = passed and payload["fields"] == expected_fields
        return {
            "case": name,
            "notes": notes,
            "expected_code": expected_code,
            "observed_code": payload["code"],
            "stage": payload["stage"],
            "fields": payload["fields"],
            "pass": passed,
        }
    except Exception as exc:  # noqa: BLE001 - smoke runner records unexpected failures
        return {
            "case": name,
            "notes": notes,
            "expected_code": expected_code,
            "observed_code": None,
            "stage": None,
            "fields": [],
            "unexpected_exception": f"{type(exc).__name__}: {exc}",
            "pass": False,
        }
    return {
        "case": name,
        "notes": notes,
        "expected_code": expected_code,
        "observed_code": None,
        "stage": None,
        "fields": [],
        "unexpected_exception": "query/index unexpectedly succeeded",
        "pass": False,
    }


def _determinism(index: RetrievalIndex, case_path: Path) -> dict[str, Any]:
    case = _load_case(case_path)

    def _query() -> Any:
        return index.query(
            family_id=case["family_id"],
            parameters=case["parameters"],
            top_k=case.get("top_k"),
        )

    first = _query()
    second = _query()
    in_process = first.to_canonical_json() == second.to_canonical_json()
    in_process_sha = first.sha256()

    runs = []
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, str(REPLAY), "--config", str(CONFIG), "--case", str(case_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        runs.append(
            {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr.strip(),
            }
        )
    cross_process = (
        runs[0]["returncode"] == 0
        and runs[1]["returncode"] == 0
        and runs[0]["stdout"] == runs[1]["stdout"]
    )
    parsed_sha = None
    for line in runs[0]["stdout"].splitlines():
        if line.startswith("sha256="):
            parsed_sha = line.split("=", 1)[1]
    matches = parsed_sha == in_process_sha
    return {
        "case": case["case"],
        "in_process_identical": in_process,
        "in_process_sha256": in_process_sha,
        "cross_process_identical": cross_process,
        "cross_process_sha256": parsed_sha,
        "cross_process_matches_in_process": matches,
        "runs": [
            {"returncode": run["returncode"], "stdout": run["stdout"], "stderr": run["stderr"]}
            for run in runs
        ],
        "pass": bool(in_process and cross_process and matches),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(REPORT))
    args = parser.parse_args()

    index = RetrievalIndex.from_config(CONFIG)
    config = index.config  # set by from_config

    cases = [
        _run_success(index, _load_case(EXAMPLES / "query-in-catalog.json")),
        _run_success(index, _load_case(EXAMPLES / "query-between-catalog-rows.json")),
        _run_success(index, dict(BOUNDARY_CASE)),
    ]

    full_020 = {
        "bore_d": 20,
        "outer_d": 32,
        "screw_d": 6,
        "screw_len": 8,
        "second_screw": 0,
        "width": 14,
    }
    example_invalid = _load_case(EXAMPLES / "query-invalid.json")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    manifest_lines = MANIFEST.read_text(encoding="utf-8").rstrip("\n").split("\n")
    duplicate_manifest = WORK_DIR / "duplicate-manifest.jsonl"
    duplicate_manifest.write_text(
        manifest_lines[0] + "\n" + manifest_lines[0] + "\n",
        encoding="utf-8",
    )

    failures = [
        _run_failure(
            "missing_field",
            "RETRIEVAL_MISSING_FIELD",
            lambda: index.query(
                family_id=FAMILY_ID,
                parameters=example_invalid["parameters"],
                top_k=example_invalid["top_k"],
            ),
            expected_fields=["outer_d"],
            notes="flat query omits outer_d; missing fields are rejected, not defaulted",
        ),
        _run_failure(
            "unknown_field",
            "RETRIEVAL_UNKNOWN_FIELD",
            lambda: index.query(
                family_id=FAMILY_ID,
                parameters={**full_020, "flange_d": 10},
                top_k=3,
            ),
            expected_fields=["flange_d"],
        ),
        _run_failure(
            "unknown_family",
            "RETRIEVAL_UNKNOWN_FAMILY",
            lambda: index.query(family_id="flange_bracket", parameters=full_020, top_k=3),
            expected_fields=["family_id"],
        ),
        _run_failure(
            "non_finite_parameter",
            "RETRIEVAL_INVALID_PARAMETER",
            lambda: index.query(
                family_id=FAMILY_ID,
                parameters={**full_020, "bore_d": float("nan")},
                top_k=3,
            ),
            expected_fields=["bore_d"],
        ),
        _run_failure(
            "invalid_second_screw",
            "RETRIEVAL_INVALID_PARAMETER",
            lambda: index.query(
                family_id=FAMILY_ID,
                parameters={**full_020, "second_screw": 2},
                top_k=3,
            ),
            expected_fields=["second_screw"],
        ),
        _run_failure(
            "top_k_zero",
            "RETRIEVAL_INVALID_TOP_K",
            lambda: index.query(family_id=FAMILY_ID, parameters=full_020, top_k=0),
            expected_fields=["top_k"],
        ),
        _run_failure(
            "top_k_boolean",
            "RETRIEVAL_INVALID_TOP_K",
            lambda: index.query(family_id=FAMILY_ID, parameters=full_020, top_k=True),
            expected_fields=["top_k"],
        ),
        _run_failure(
            "top_k_too_large",
            "RETRIEVAL_TOP_K_OUT_OF_RANGE",
            lambda: index.query(family_id=FAMILY_ID, parameters=full_020, top_k=4),
            expected_fields=["top_k"],
        ),
        _run_failure(
            "envelope_non_catalog_bore",
            "RETRIEVAL_SCHEMA_REJECTED",
            lambda: index.query(
                family_id=FAMILY_ID,
                parameters={
                    "schema_version": "set_screw_shaft_collar.v0",
                    "family_id": FAMILY_ID,
                    "parameters": {"bore_d": 18},
                },
                top_k=3,
            ),
            notes="the CAD-003 envelope path requires a Schema-valid catalog query",
        ),
        _run_failure(
            "empty_candidate_roles",
            "RETRIEVAL_EMPTY_CANDIDATE_ROLES",
            lambda: RetrievalIndex.from_manifest(MANIFEST, set()),
        ),
        _run_failure(
            "candidate_roles_omitted",
            "RETRIEVAL_CANDIDATE_ROLES_REQUIRED",
            lambda: RetrievalIndex.from_manifest(MANIFEST),
        ),
        _run_failure(
            "unknown_role",
            "RETRIEVAL_UNKNOWN_ROLE",
            lambda: RetrievalIndex.from_manifest(MANIFEST, {"typo_role"}),
        ),
        _run_failure(
            "duplicate_candidate",
            "RETRIEVAL_DUPLICATE_SAMPLE_ID",
            lambda: RetrievalIndex.from_manifest(duplicate_manifest, {"retrieval_source"}),
            notes="a manifest line duplicated twice must be rejected, not returned twice",
        ),
    ]

    determinism = _determinism(index, EXAMPLES / "query-in-catalog.json")

    failed_cases = [case["case"] for case in cases if not case["pass"]]
    failed_failures = [failure["case"] for failure in failures if not failure["pass"]]
    total_checks = sum(len(case["checks"]) for case in cases) + len(failures) + (1 if determinism["pass"] else 0)
    failed_checks = (
        sum(1 for case in cases for passed in case["checks"].values() if not passed)
        + len(failed_failures)
        + (0 if determinism["pass"] else 1)
    )

    report = {
        "task": "RET-002",
        "kind": "smoke-report",
        "status": "review",
        "retrieval_version": RETRIEVAL_VERSION,
        "policy_id": POLICY_ID,
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "environment": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "config": config.as_report_dict(),
        "manifest": index.describe()["manifest"],
        "index": {
            "family_id": index.family_id,
            "candidate_roles": list(index.candidate_roles),
            "candidate_count": index.candidate_count,
            "candidate_sample_ids": index.describe()["candidate_sample_ids"],
            "split_status": SPLIT_STATUS,
        },
        "data_boundary": {
            "reads_step": False,
            "reads_render": False,
            "reads_ir_files": False,
            "reads_external_drawings": False,
            "reads_benchcad_public_core": False,
        },
        "split": {
            "split_status": SPLIT_STATUS,
            "selection_rule": (
                "candidate roles are fixed explicitly in retrieval-config.json; only records whose "
                "split.role is listed are scored, and other roles are excluded rather than down-ranked"
            ),
            "group_rule": (
                "group_id = catalog-row-bore-0XX from RET-001; one role per group; the 9/3/3 grouping "
                "is provisional_small_n and is not a benchmark split"
            ),
            "role_counts": index.describe()["manifest"]["role_counts"],
        },
        "coverage": {
            "in_catalog_bore_020": "examples/query-in-catalog.json (CAD-003 envelope, Schema derives fields)",
            "between_catalog_rows": "examples/query-between-catalog-rows.json (bore_d=18, out_of_catalog_or_unvalidated)",
            "boundary_second_screw_bore_080": "inline case; held-out row must not be a candidate",
            "missing_field": "examples/query-invalid.json",
            "unknown_field": "inline failure case",
            "unknown_family": "inline failure case",
            "non_finite_and_invalid_second_screw": "inline failure cases",
            "empty_candidate_roles_top_k_out_of_range_duplicate_candidates": "inline failure cases",
        },
        "cases": cases,
        "failure_cases": failures,
        "determinism": determinism,
        "summary": {
            "success_cases": len(cases),
            "failure_cases": len(failures),
            "checks": total_checks,
            "failed": failed_checks,
            "failed_cases": failed_cases,
            "failed_failure_cases": failed_failures,
            "result": "pass" if failed_checks == 0 else "fail",
        },
        "limitations": [
            "single frozen family set_screw_shaft_collar with 15 catalog rows; candidates are only the 3 retrieval_source rows",
            "split_status=provisional_small_n is a provisional grouping, not a benchmark split; no accuracy or generalization claim is made",
            "distance is parameter proximity only, not CAD geometry equivalence, manufacturability, strength or generation quality",
            "only the pinned macOS arm64 / Python environment is verified; cross-platform and cross-process guarantee is limited to the recorded determinism check",
            "manifest snapshot is reproducibility_partial and the family is MERGED, not release-qualified",
            "generated STEP/render artifacts remain license_scope_uncertain and are not read by retrieval",
            "out-of-catalog queries are nearest-neighbour only and are not Schema-confirmed catalog truths",
            "no vector database, embedding model, LLM, training or synthetic sample expansion is used",
        ],
        "next_steps": [
            "Codex hub reviews the interface, stable ordering, failure paths and data boundary before RET-003.",
            "RET-003 decides whether to freeze a split or explicitly not split; the current 9/3/3 grouping must not be treated as a benchmark.",
            "RET-003 compares no-retrieval / retrieval / human-template conditions; candidates are references, not catalog or geometry truth.",
            "APP-001/RET-004 prompt injection must carry query_status, sample_id, ir.path, source_commit, split.role and limitations.",
            "Any larger candidate pool requires a hub decision on a new family or schema version; do not duplicate, expand randomly, or download Public/Core.",
        ],
    }

    report_path = Path(args.report)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"manifest records={index.describe()['manifest'].get('records')} candidates={index.candidate_count}")
    for case in cases:
        status = "PASS" if case["pass"] else "FAIL"
        top1 = case["ranking"][0]["sample_id"] if case["ranking"] else "-"
        print(f"case {case['case']}: {status} status={case['query_status']} top1={top1}")
    print(f"failure cases: {len(failures) - len(failed_failures)}/{len(failures)} rejected with the expected code")
    if failed_failures:
        print("failed failure cases: " + ", ".join(failed_failures))
    print(f"determinism: pass={determinism['pass']} in_process={determinism['in_process_identical']} "
          f"cross_process={determinism['cross_process_identical']} sha256={determinism['in_process_sha256']}")
    print(f"report={report_path.relative_to(REPO_ROOT).as_posix() if REPORT.parent in report_path.parents else report_path}")
    if failed_checks:
        for case in cases:
            for name, passed in case["checks"].items():
                if not passed:
                    print(f"FAIL: {case['case']} -> {name}")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
