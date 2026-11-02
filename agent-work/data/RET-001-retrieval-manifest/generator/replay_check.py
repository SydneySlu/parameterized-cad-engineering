#!/usr/bin/env python3
"""RET-001 replay check: re-run frozen CAD compilation and compare with the manifest.

In a fresh process, for one normal catalog row and the second-screw hard
boundary row:

  * re-validate the tracked input payload with the family schema
  * recompile the tracked accepted IR with compile_ir()
  * compare native geometry, repeatability, STEP readback and array hashes
    against the committed manifest record
  * record STEP byte hash equality as informational only

Then run two negative controls twice each:

  * tampered accepted IR (radial_offset as a 100 mm literal) must be rejected
    before the CAD runtime, with the frozen node_ids, and must produce no STEP
  * CAD-003 catalog mismatch must be rejected at schema stage

Writes replay-report.json next to the manifest. Geometry is compared with
exact equality for native summaries (CAD-006.geometry-comparison.v1 only
guarantees same-process repeatability); STEP bytes are not required to match.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
MANIFEST_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from schema.set_screw_shaft_collar import (  # noqa: E402
    FAMILY_ID,
    SCHEMA_VERSION,
    validate_parameters,
)
from cad_compilation.compiler import compile_ir, validate_ir  # noqa: E402
from cad_compilation.geometry import POLICY_ID  # noqa: E402

OUT_ROOT = REPO_ROOT / "work/ret-001-output"
REPLAY_DIR = OUT_ROOT / "replay"
REPORT_PATH = MANIFEST_DIR / "replay-report.json"
TZ = timezone(timedelta(hours=8))
NORMAL_SAMPLES = ("catalog-bore-020", "catalog-bore-080")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value) -> str:
    return sha256_bytes(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def load_manifest() -> dict[str, dict]:
    text = (MANIFEST_DIR / "manifest-v0.jsonl").read_text(encoding="utf-8")
    return {record["sample_id"]: record for record in map(json.loads, text.rstrip("\n").split("\n"))}


def summarize(native: dict) -> dict:
    return {
        "solids": native["solids"],
        "shells": native["shells"],
        "faces": native["faces"],
        "edges": native["edges"],
        "vertices": native["vertices"],
        "is_valid": native["is_valid"],
        "volume_mm3": native["volume_mm3"],
        "bbox_mm": native["bbox_mm"],
        "face_areas_sha256": sha256_json(native["face_areas_mm2"]),
        "edge_lengths_sha256": sha256_json(native["edge_lengths_mm"]),
    }


def replay_sample(record: dict) -> dict:
    sample_id = record["sample_id"]
    short = sample_id.split("/")[1]
    payload_path = REPO_ROOT / record["parameters"]["input_payload"]["path"]
    ir_path = REPO_ROOT / record["ir"]["path"]

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    family = validate_parameters(payload)
    ir_bytes = ir_path.read_bytes()

    started = time.time()
    compiled = compile_ir(ir_bytes, output_dir=REPLAY_DIR / short)
    elapsed = time.time() - started

    result = {
        "sample_id": sample_id,
        "ir_sha256_match": sha256_bytes(ir_bytes) == record["ir"]["sha256"],
        "payload_sha256_match": sha256_bytes(payload_path.read_bytes()) == record["parameters"]["input_payload"]["sha256"],
        "family_rules_ok": family.ok,
        "family_normalized_match": family.normalized == record["parameters"]["normalized"],
        "validate_ir_errors": [error.as_dict() for error in validate_ir(ir_bytes)],
        "compile_ok": compiled.ok,
        "status": compiled.status,
        "elapsed_seconds": round(elapsed, 3),
        "policy_id": POLICY_ID,
    }
    if not compiled.ok or compiled.manifest is None:
        result["pass"] = False
        result["errors"] = compiled.errors
        return result

    native = compiled.manifest["native_geometry"]
    repeat = compiled.manifest["native_repeatability"]["comparison"]
    comparison = compiled.manifest["step_readback"]["comparison"]
    step = compiled.manifest["step"]
    step_path = Path(step["path"])
    expected = record["validation"]["native_geometry"]

    native_match = summarize(native) == {
        "solids": expected["solids"],
        "shells": expected["shells"],
        "faces": expected["faces"],
        "edges": expected["edges"],
        "vertices": expected["vertices"],
        "is_valid": expected["is_valid"],
        "volume_mm3": expected["volume_mm3"],
        "bbox_mm": expected["bbox_mm"],
        "face_areas_sha256": expected["face_areas_sha256"],
        "edge_lengths_sha256": expected["edge_lengths_sha256"],
    }
    step_sha = sha256_bytes(step_path.read_bytes())
    result.update(
        {
            "native_geometry": summarize(native),
            "native_geometry_match": native_match,
            "native_repeat_pass": repeat["pass"],
            "step_readback_pass": comparison["pass"],
            "step_readback_policy": comparison["policy_id"],
            "step_bytes": step["bytes"],
            "step_sha256": step_sha,
            "step_sha_matches_manifest": step_sha == record["artifacts"]["step"]["sha256"],
            "step_sha_note": "informational only; equality is not required",
        }
    )
    result["pass"] = bool(
        result["ir_sha256_match"]
        and result["payload_sha256_match"]
        and family.ok
        and result["family_normalized_match"]
        and not result["validate_ir_errors"]
        and result["compile_ok"]
        and result["status"] == "step_readback"
        and native_match
        and repeat["pass"]
        and comparison["pass"]
    )
    return result


def failure_controls() -> dict:
    record = load_manifest()["set_screw_shaft_collar/catalog-bore-020"]
    ir_path = REPO_ROOT / record["ir"]["path"]
    tampered = json.loads(ir_path.read_text(encoding="utf-8"))
    tampered["nodes"][2]["inputs"]["radial_offset"] = {"kind": "literal", "value": 100, "unit": "mm"}
    tampered_bytes = json.dumps(tampered, ensure_ascii=False, indent=2).encode("utf-8")

    runs = []
    for run in (1, 2):
        output_dir = REPLAY_DIR / "controls" / f"tampered-run{run}"
        output_dir.mkdir(parents=True, exist_ok=True)
        for stale in output_dir.glob("*.step"):
            stale.unlink()
        compiled = compile_ir(tampered_bytes, output_dir=output_dir)
        step_files = sorted(path.name for path in output_dir.glob("*.step"))
        runs.append(
            {
                "run": run,
                "ok": compiled.ok,
                "status": compiled.status,
                "errors": [
                    {
                        "code": error.get("code"),
                        "stage": error.get("stage"),
                        "fields": error.get("fields"),
                        "node_ids": error.get("node_ids"),
                    }
                    for error in compiled.errors
                ],
                "validate_ir_errors": [
                    {"code": error.code, "field": error.field} for error in validate_ir(tampered_bytes)
                ],
                "step_files_written": step_files,
            }
        )

    expected_codes = {"IR_NODE_INPUT_KIND_MISMATCH"}
    expected_nodes = {"n2.hole.primary"}
    tampered_pass = all(
        run["ok"] is False
        and run["status"] == "semantic"
        and {error["code"] for error in run["errors"]} == expected_codes
        and any(set(error["node_ids"]) == expected_nodes for error in run["errors"])
        and not run["step_files_written"]
        for run in runs
    )

    rule_runs = []
    for run in (1, 2):
        family = validate_parameters(
            {
                "schema_version": SCHEMA_VERSION,
                "family_id": FAMILY_ID,
                "parameters": {"bore_d": 20, "outer_d": 33},
            }
        )
        rule_runs.append(
            {
                "run": run,
                "ok": family.ok,
                "errors": [{"code": error.code, "stage": error.stage, "fields": list(error.fields)} for error in family.errors],
            }
        )
    rule_pass = all(
        run["ok"] is False and {error["code"] for error in run["errors"]} == {"CATALOG_MISMATCH"} for run in rule_runs
    )

    return {
        "tampered_radial_offset": {
            "case": "nodes[2].inputs.radial_offset := literal 100 mm on the tracked bore_d=20 accepted IR",
            "expected": "IR_NODE_INPUT_KIND_MISMATCH at semantic stage, node_ids=[n2.hole.primary], no STEP",
            "runs": runs,
            "identical_across_runs": runs[0]["errors"] == runs[1]["errors"],
            "pass": tampered_pass,
        },
        "catalog_mismatch": {
            "case": "CAD-003 envelope bore_d=20 with explicit outer_d=33",
            "expected": "CATALOG_MISMATCH at schema stage",
            "runs": rule_runs,
            "identical_across_runs": rule_runs[0]["errors"] == rule_runs[1]["errors"],
            "pass": rule_pass,
        },
        "ir_unchanged": {"sha256": record["ir"]["sha256"], "nodes_tampered_only_in_memory": True},
    }


def main() -> int:
    records = load_manifest()
    replay_results = []
    for short in NORMAL_SAMPLES:
        sample_id = f"{FAMILY_ID}/{short}"
        replay_results.append(replay_sample(records[sample_id]))

    controls = failure_controls()

    report = {
        "manifest_version": "retrieval-manifest.v0",
        "task": "RET-001",
        "kind": "replay-check",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "environment": {
            "python": platform.python_version(),
            "cadquery": __import__("cadquery").__version__,
            "ocp": __import__("OCP").__version__,
            "numpy": __import__("numpy").__version__,
            "platform": platform.platform(),
        },
        "policy_id": POLICY_ID,
        "normal_cases": replay_results,
        "negative_controls": controls,
        "notes": [
            "replay runs in a fresh process and compares against the committed manifest record",
            "STEP byte sha256 is informational; a difference is not a geometry failure",
            "only one pinned environment is exercised; cross-platform/cross-process claims are out of scope",
        ],
        "pass": all(item.get("pass") for item in replay_results) and controls["tampered_radial_offset"]["pass"] and controls["catalog_mismatch"]["pass"],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for item in replay_results:
        print(
            f"{item['sample_id']}: pass={item.get('pass')} status={item.get('status')} "
            f"native_match={item.get('native_geometry_match')} readback={item.get('step_readback_pass')} "
            f"step_sha_same={item.get('step_sha_matches_manifest')} elapsed={item.get('elapsed_seconds')}s"
        )
    print(
        "control tampered_radial_offset: pass="
        f"{controls['tampered_radial_offset']['pass']} runs_identical={controls['tampered_radial_offset']['identical_across_runs']}"
    )
    print(
        "control catalog_mismatch: pass="
        f"{controls['catalog_mismatch']['pass']} runs_identical={controls['catalog_mismatch']['identical_across_runs']}"
    )
    print(f"report={REPORT_PATH.relative_to(REPO_ROOT).as_posix()}")
    print("RESULT: " + ("PASS" if report["pass"] else "FAIL"))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
