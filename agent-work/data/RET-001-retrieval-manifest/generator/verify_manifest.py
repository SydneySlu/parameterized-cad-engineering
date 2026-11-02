#!/usr/bin/env python3
"""RET-001 independent manifest verification (no CAD runtime required for --tracked-only).

Checks, per record and across records:

  * JSONL parses line by line and matches manifest.schema.json (Draft 2020-12)
  * sample_id / group_id / catalog row / split role are mutually consistent
  * normalized parameters equal the frozen catalog row in src/schema
  * provenance sources and source_refs match the CAD-003 contract
  * input payload exists, parses, and its sha256 matches
  * IR file exists, sha256 matches, validates against ir-v0.schema.json and
    the IR semantic contract, is accepted, and carries the manifest parameters
  * IR schema sha256 matches the on-disk schema
  * STEP and validation artifacts exist and hash-match (unless --tracked-only)
  * one role per group; no duplicated sample/group/payload/geometry fingerprint
  * generation-report.json manifest sha256 equals the actual manifest sha256

This is a data-integrity and traceability check. It does not re-run CAD
geometry, and passing it is not evidence that the geometry is correct.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
MANIFEST_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from schema.set_screw_shaft_collar import CATALOG_ROWS, FAMILY_ID, validate_parameters  # noqa: E402
from cad_compilation.ir import SCHEMA_PATH as IR_SCHEMA_PATH  # noqa: E402
from cad_compilation.ir import validate_document  # noqa: E402

PARAMETER_ORDER = ["bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"]
ROW_BY_BORE = {row[0]: row for row in CATALOG_ROWS}
POLICY_ID = "CAD-006.geometry-comparison.v1"
TZ = timezone(timedelta(hours=8))


class Checks:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes = 0

    def check(self, condition: bool, message: str) -> None:
        if condition:
            self.passes += 1
        else:
            self.failures.append(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def split_for(index: int) -> str:
    if index % 5 == 1:
        return "retrieval_source"
    if index % 5 == 4:
        return "heldout_evaluation"
    return "development"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked-only", action="store_true", help="skip ignored STEP/validation artifacts")
    args = parser.parse_args()

    checks = Checks()
    from jsonschema import Draft202012Validator

    manifest_path = MANIFEST_DIR / "manifest-v0.jsonl"
    schema_path = MANIFEST_DIR / "manifest.schema.json"
    report_path = MANIFEST_DIR / "generation-report.json"

    checks.check(manifest_path.is_file(), f"missing {manifest_path}")
    checks.check(schema_path.is_file(), f"missing {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    text = manifest_path.read_text(encoding="utf-8")
    checks.check(text.endswith("\n") and not text.endswith("\n\n"), "manifest must end with exactly one newline")
    lines = text.rstrip("\n").split("\n")
    checks.check(all(line.strip() for line in lines), "manifest contains blank lines")
    records = []
    for number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            checks.check(False, f"line {number}: invalid JSON: {exc}")
            continue
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "record"
            checks.check(False, f"line {number} {record.get('sample_id')}: schema {path}: {error.message}")
        checks.check(not errors, f"line {number}: schema errors")
        records.append(record)

    checks.check(len(records) == len(CATALOG_ROWS), f"expected {len(CATALOG_ROWS)} records, found {len(records)}")
    checks.check(len(records) == 15, "frozen catalog coverage must be exactly 15 rows")

    ir_schema_sha = sha256_file(IR_SCHEMA_PATH)
    ir_schema = json.loads(IR_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(ir_schema)
    ir_validator = Draft202012Validator(ir_schema)

    seen_sample: set[str] = set()
    seen_group: set[str] = set()
    seen_payload: dict[str, str] = {}
    seen_fingerprint: dict[str, str] = {}
    role_by_group: dict[str, str] = {}
    role_counts: dict[str, int] = {"development": 0, "retrieval_source": 0, "heldout_evaluation": 0}
    covered_bore: set[int] = set()

    for record in records:
        sample_id = record["sample_id"]
        index = record["source"]["catalog_row"]["index"]
        bore = record["source"]["catalog_row"]["value"]
        row = ROW_BY_BORE[bore]
        short = f"catalog-bore-{bore:03d}"

        checks.check(sample_id == f"{FAMILY_ID}/{short}", f"{sample_id}: sample_id does not match catalog row {bore}")
        checks.check(record["split"]["group_id"] == f"catalog-row-bore-{bore:03d}", f"{sample_id}: group_id mismatch")
        checks.check(sample_id not in seen_sample, f"{sample_id}: duplicated sample_id")
        seen_sample.add(sample_id)
        checks.check(record["split"]["group_id"] not in seen_group, f"{sample_id}: duplicated group_id across records")
        seen_group.add(record["split"]["group_id"])
        covered_bore.add(bore)

        checks.check(list(record["source"]["catalog_row"]["row"]) == list(row), f"{sample_id}: catalog row != src/schema CATALOG_ROWS")
        checks.check(record["source"]["catalog_row"]["index"] == CATALOG_ROWS.index(row), f"{sample_id}: catalog index mismatch")

        normalized = record["parameters"]["normalized"]
        checks.check(list(normalized) == PARAMETER_ORDER, f"{sample_id}: normalized parameter order mismatch")
        checks.check(tuple(normalized[pid] for pid in ("bore_d", "outer_d", "screw_d", "screw_len", "width")) == row, f"{sample_id}: normalized values != catalog row")
        checks.check(normalized["second_screw"] == (1 if bore > 70 else 0), f"{sample_id}: second_screw rule violated")

        payload_path = REPO_ROOT / record["parameters"]["input_payload"]["path"]
        checks.check(payload_path.is_file(), f"{sample_id}: missing input payload {payload_path}")
        if payload_path.is_file():
            checks.check(sha256_file(payload_path) == record["parameters"]["input_payload"]["sha256"], f"{sample_id}: payload sha256 mismatch")
            result = validate_parameters(json.loads(payload_path.read_text(encoding="utf-8")))
            checks.check(result.ok, f"{sample_id}: payload rejected by family rules")
            checks.check(result.normalized == normalized, f"{sample_id}: payload normalization differs from manifest")
            for pid in PARAMETER_ORDER:
                checks.check(
                    record["parameters"]["provenance"][pid]["source"] == result.provenance[pid],
                    f"{sample_id}: provenance source mismatch for {pid}",
                )

        payload_fingerprint = record["parameters"]["input_payload"]["sha256"]
        checks.check(payload_fingerprint not in seen_payload, f"{sample_id}: parameter payload duplicated with {seen_payload.get(payload_fingerprint)}")
        seen_payload[payload_fingerprint] = sample_id

        geometry = record["validation"]["native_geometry"]
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "volume_mm3": round(geometry["volume_mm3"], 6),
                    "bbox_mm": {key: round(value, 6) for key, value in geometry["bbox_mm"].items()},
                    "counts": [geometry["solids"], geometry["shells"], geometry["faces"], geometry["edges"], geometry["vertices"]],
                },
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        checks.check(fingerprint not in seen_fingerprint, f"{sample_id}: geometry fingerprint duplicated with {seen_fingerprint.get(fingerprint)}")
        seen_fingerprint[fingerprint] = sample_id

        role = record["split"]["role"]
        role_counts[role] += 1
        checks.check(role == split_for(index), f"{sample_id}: split role {role} does not follow the documented rule")
        checks.check(record["split"]["split_status"] == "provisional_small_n", f"{sample_id}: split_status must stay provisional_small_n")
        checks.check(role_by_group.setdefault(record["split"]["group_id"], role) == role, f"{sample_id}: group assigned to multiple roles")
        checks.check(record["split"]["role"] != "heldout_evaluation" or record["validation"]["step_readback"]["pass"], f"{sample_id}: held-out sample failed geometry")

        checks.check(record["ir"]["schema_sha256"] == ir_schema_sha, f"{sample_id}: IR schema sha256 mismatch")
        ir_path = REPO_ROOT / record["ir"]["path"]
        checks.check(ir_path.is_file(), f"{sample_id}: missing IR {ir_path}")
        if ir_path.is_file():
            checks.check(sha256_file(ir_path) == record["ir"]["sha256"], f"{sample_id}: IR sha256 mismatch")
            document = json.loads(ir_path.read_text(encoding="utf-8"))
            ir_errors = sorted(ir_validator.iter_errors(document), key=lambda error: list(error.absolute_path))
            for error in ir_errors:
                path = ".".join(str(part) for part in error.absolute_path) or "ir"
                checks.check(False, f"{sample_id}: IR schema {path}: {error.message}")
            checks.check(not ir_errors, f"{sample_id}: IR schema errors")
            semantic = validate_document(document)
            for error in semantic:
                checks.check(False, f"{sample_id}: IR semantic {error.code} at {error.field}: {error.message}")
            checks.check(not semantic, f"{sample_id}: IR semantic errors")
            checks.check(document.get("ir_version") == record["ir"]["ir_version"], f"{sample_id}: IR version mismatch")
            checks.check(document.get("ir_revision") == record["ir"]["ir_revision"], f"{sample_id}: IR revision mismatch")
            checks.check(document.get("status") == record["ir"]["status"] == "accepted", f"{sample_id}: IR status mismatch")
            ir_params = {item["parameter_id"]: item["value"] for item in document["parameters"]}
            checks.check(ir_params == normalized, f"{sample_id}: IR parameters differ from manifest normalized parameters")
            checks.check(document["execution"].get("tolerance_profile") == POLICY_ID, f"{sample_id}: IR tolerance_profile is not the frozen policy")

        validation = record["validation"]
        checks.check(validation["policy_id"] == POLICY_ID, f"{sample_id}: policy id mismatch")
        checks.check(validation["native_repeatability"]["policy_id"] == POLICY_ID, f"{sample_id}: repeat policy id mismatch")
        checks.check(validation["step_readback"]["policy_id"] == POLICY_ID, f"{sample_id}: readback policy id mismatch")
        checks.check(validation["native_geometry"]["solids"] == 1 and validation["native_geometry"]["shells"] == 1, f"{sample_id}: native geometry is not a single solid/shell")
        checks.check(validation["step_readback"]["readback_geometry"]["solids"] == 1, f"{sample_id}: readback is not a single solid")
        checks.check(record["artifacts"]["render"] is None, f"{sample_id}: render must stay null in manifest v0")

        step = record["artifacts"]["step"]
        checks.check(step["path"].startswith("work/ret-001-output/"), f"{sample_id}: STEP path must stay in the ignored output tree")

        if not args.tracked_only:
            step_path = REPO_ROOT / step["path"]
            checks.check(step_path.is_file(), f"{sample_id}: missing STEP artifact {step_path} (run the generator)")
            if step_path.is_file():
                checks.check(step_path.stat().st_size == step["bytes"], f"{sample_id}: STEP byte size mismatch")
                checks.check(sha256_file(step_path) == step["sha256"], f"{sample_id}: STEP sha256 mismatch")
            validation_path = REPO_ROOT / record["artifacts"]["validation_result"]["path"]
            checks.check(validation_path.is_file(), f"{sample_id}: missing validation artifact {validation_path}")
            if validation_path.is_file():
                checks.check(sha256_file(validation_path) == record["artifacts"]["validation_result"]["sha256"], f"{sample_id}: validation artifact sha256 mismatch")
                payload = json.loads(validation_path.read_text(encoding="utf-8"))
                checks.check(payload["compile"]["ok"] is True, f"{sample_id}: validation artifact records a failed compile")
                checks.check(payload["ir_sha256"] == record["ir"]["sha256"], f"{sample_id}: validation artifact IR sha256 mismatch")
                artifact_geometry = payload["manifest"]["native_geometry"]
                checks.check(artifact_geometry["volume_mm3"] == geometry["volume_mm3"], f"{sample_id}: validation artifact volume differs from manifest")
                checks.check(artifact_geometry["face_areas_mm2"] and validation["native_geometry"]["face_areas_count"] == len(artifact_geometry["face_areas_mm2"]), f"{sample_id}: face area count differs")
                checks.check(
                    hashlib.sha256(json.dumps(artifact_geometry["face_areas_mm2"], separators=(",", ":")).encode("utf-8")).hexdigest()
                    == validation["native_geometry"]["face_areas_sha256"],
                    f"{sample_id}: face area array sha256 differs",
                )
                checks.check(
                    hashlib.sha256(json.dumps(artifact_geometry["edge_lengths_mm"], separators=(",", ":")).encode("utf-8")).hexdigest()
                    == validation["native_geometry"]["edge_lengths_sha256"],
                    f"{sample_id}: edge length array sha256 differs",
                )

    checks.check(covered_bore == set(ROW_BY_BORE), "catalog coverage is not exactly the 15 frozen rows")
    checks.check(len(seen_group) == len(records), "group_id is not one-to-one with records")
    checks.check(role_counts["heldout_evaluation"] >= 1, "no held-out evaluation groups")
    checks.check(role_counts["retrieval_source"] >= 1, "no retrieval source groups")
    checks.check(role_counts["development"] >= 1, "no development groups")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    checks.check(report["manifest"]["sha256"] == manifest_sha, "generation-report manifest sha256 does not match manifest-v0.jsonl")
    checks.check(report["leakage_checks"]["cross_split_group_overlap"] == 0, "generation report records cross-split group overlap")
    checks.check(report["summary"]["failed"] == 0, "generation report records failures")

    ignore = subprocess.run(["git", "check-ignore", "-q", "work/ret-001-output/probe.step"], cwd=REPO_ROOT)
    checks.check(ignore.returncode == 0, "work/ret-001-output is not git-ignored")

    verification = {
        "manifest_version": "retrieval-manifest.v0",
        "task": "RET-001",
        "kind": "verification-report",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "verifier": {
            "path": rel(HERE),
            "sha256": sha256_file(HERE),
            "python": platform.python_version(),
            "jsonschema": importlib.metadata.version("jsonschema"),
        },
        "manifest": {"path": rel(manifest_path), "sha256": manifest_sha, "records": len(records)},
        "manifest_schema": {"path": rel(schema_path), "sha256": sha256_file(schema_path)},
        "ir_schema": {"path": rel(IR_SCHEMA_PATH), "sha256": ir_schema_sha},
        "split_counts": role_counts,
        "checks": {"passed": checks.passes, "failed": len(checks.failures), "failures": checks.failures},
        "artifacts_checked": "tracked-only" if args.tracked_only else "tracked + ignored local artifacts",
        "scope": "JSONL/schema integrity, provenance, hash, IR re-validation and split isolation. Not a geometry-correctness check.",
        "result": "pass" if not checks.failures else "fail",
    }
    (MANIFEST_DIR / "verification-report.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"records={len(records)} lines={len(lines)} checks_passed={checks.passes} failures={len(checks.failures)}")
    print("split=" + json.dumps(role_counts))
    print("manifest_sha256=" + manifest_sha)
    if checks.failures:
        for failure in checks.failures[:40]:
            print("FAIL: " + failure)
        if len(checks.failures) > 40:
            print(f"FAIL: ... {len(checks.failures) - 40} more")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
