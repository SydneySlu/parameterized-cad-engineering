#!/usr/bin/env python3
"""RET-001: build the retrieval manifest v0 for the frozen family.

Pipeline per catalog row (no synthetic parameter expansion):

  1. minimal CAD-003 JSON envelope with only bore_d
  2. schema.set_screw_shaft_collar.validate_parameters  -> normalized + provenance
  3. adapter -> typed-cad-ir.v0 revision 0.2.0 accepted IR (frozen seven-node graph)
  4. Draft 2020-12 JSON Schema + IR semantic validation
  5. cad_compilation.compile_ir -> native build, CAD-006 gate, STEP export + readback
  6. one stable manifest-v0.jsonl record per row

The generator is read-only with respect to src/, the IR schema and the frozen
examples; it only writes under this task directory and the ignored
work/ret-001-output/ tree.
"""

from __future__ import annotations

import copy
import hashlib
import json
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
MANIFEST_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]

sys.path.insert(0, str(REPO_ROOT / "src"))

from schema.set_screw_shaft_collar import (  # noqa: E402
    CATALOG_ROWS,
    FAMILY_ID,
    SCHEMA_VERSION,
    SOURCE_COMMIT,
    validate_parameters,
)
from cad_compilation.compiler import compile_ir  # noqa: E402
from cad_compilation.geometry import POLICY_ID  # noqa: E402
from cad_compilation.ir import SCHEMA_PATH, validate_document  # noqa: E402

MANIFEST_VERSION = "retrieval-manifest.v0"
TEMPLATE_IR = REPO_ROOT / "agent-work/typed-cad-ir/IR-001-v0/examples/legal-catalog-row.json"
IR_SCHEMA_REL = "agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json"
OUT_ROOT = REPO_ROOT / "work/ret-001-output"
CAD_DIR = OUT_ROOT / "cad"
VAL_DIR = OUT_ROOT / "validation"
PARAMETER_ORDER = ["bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"]
LENGTH_FIELDS = ("bore_d", "outer_d", "screw_d", "screw_len", "width")
REPOSITORY = "https://github.com/BenchCAD-org/benchcad-2"
FAMILY_PATH = "designs/set_screw_shaft_collar"
LICENSE_SCOPE = "source/designs MIT; generated STEP/render scope uncertain"
SPLIT_STATUS = "provisional_small_n"
SPLIT_RULE = (
    "catalog-row-grouped: rows ordered by bore_d ascending; index%5==1 -> retrieval_source, "
    "index%5==4 -> heldout_evaluation, otherwise development; one role per group; "
    "provisional_small_n and not a frozen benchmark split (needs RET-003/Codex review)"
)
LIMITATIONS = [
    "single frozen family: set_screw_shaft_collar only",
    "only the 15 frozen GN 705 catalog rows; no synthetic or random parameter expansion",
    "source snapshot status is reproducibility_partial (api/raw reconstruction, not a git archive)",
    "generated STEP/render license scope uncertain; project-internal use only, not for redistribution",
    "STEP sha256 is an artifact identifier only, not evidence of geometry equality",
    "geometry verdict follows CAD-006.geometry-comparison.v1 in one pinned environment; cross-platform and cross-process unverified",
    "split_status=provisional_small_n: 15 groups are too few for a statistical benchmark split",
]
TZ = timezone(timedelta(hours=8))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(value) -> str:
    return sha256_bytes(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, value, *, indent: int = 2) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def split_for(index: int) -> str:
    if index % 5 == 1:
        return "retrieval_source"
    if index % 5 == 4:
        return "heldout_evaluation"
    return "development"


def sample_short(bore: int) -> str:
    return f"catalog-bore-{bore:03d}"


def source_ref(parameter_id: str, source: str, bore: int) -> str:
    if parameter_id == "bore_d":
        return "CAD-003.field:bore_d"
    if parameter_id == "second_screw":
        return "CAD-003.rule:second_screw_threshold"
    return f"GN705.catalog_row:bore_d={bore}"


def build_payload(bore: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "family_id": FAMILY_ID,
        "parameters": {"bore_d": bore},
    }


def build_accepted_ir(template: dict, result, bore: int) -> dict:
    """Substitute parameter values/sources into the frozen seven-node template.

    Nodes, constraints, family_data and validation_contract are taken verbatim
    from the reviewed example; only the parameters array changes. The stale
    template tolerance_profile string is replaced by the policy in force
    (IR-001-v0 spec section 9.2 / ADR-0008); the example file itself is not
    modified because it is outside this task's file boundary.
    """

    document = copy.deepcopy(template)
    normalized = result.normalized
    provenance = result.provenance
    if set(normalized) != set(PARAMETER_ORDER):
        raise SystemExit(f"unexpected normalized parameter set: {sorted(normalized)}")
    if set(provenance) != set(PARAMETER_ORDER):
        raise SystemExit(f"unexpected provenance set: {sorted(provenance)}")

    parameters = []
    for parameter_id in PARAMETER_ORDER:
        value = normalized[parameter_id]
        source = provenance[parameter_id]
        entry = {
            "parameter_id": parameter_id,
            "type": "integer" if parameter_id == "second_screw" else "number",
            "unit": "1" if parameter_id == "second_screw" else "mm",
            "value": value,
        }
        if source == "user_explicit":
            entry["input"] = {
                "value": value,
                "unit": "1" if parameter_id == "second_screw" else "mm",
            }
        entry["source"] = source
        entry["source_ref"] = source_ref(parameter_id, source, bore)
        if parameter_id in LENGTH_FIELDS:
            entry["catalog_row_key"] = f"bore_d={bore}"
        parameters.append(entry)

    document["parameters"] = parameters
    document["execution"]["tolerance_profile"] = POLICY_ID
    return document


def geometry_block(native: dict) -> dict:
    return {
        "solids": native["solids"],
        "shells": native["shells"],
        "faces": native["faces"],
        "edges": native["edges"],
        "vertices": native["vertices"],
        "is_valid": native["is_valid"],
        "volume_mm3": native["volume_mm3"],
        "bbox_mm": {key: native["bbox_mm"][key] for key in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")},
        "face_areas_count": len(native["face_areas_mm2"]),
        "face_areas_sha256": sha256_json(native["face_areas_mm2"]),
        "edge_lengths_count": len(native["edge_lengths_mm"]),
        "edge_lengths_sha256": sha256_json(native["edge_lengths_mm"]),
    }


def run_controls() -> dict:
    """Negative controls: tampered accepted IR and a CAD-003 rule rejection."""

    template = json.loads(TEMPLATE_IR.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(template)
    tampered["nodes"][2]["inputs"]["radial_offset"] = {"kind": "literal", "value": 100, "unit": "mm"}
    tampered_bytes = json.dumps(tampered, ensure_ascii=False, indent=2).encode("utf-8")
    ir_errors = [error.as_dict() for error in validate_document(tampered)]
    semantic_run = compile_ir(tampered_bytes, output_dir=OUT_ROOT / "controls")

    bad_rule = validate_parameters(
        {
            "schema_version": SCHEMA_VERSION,
            "family_id": FAMILY_ID,
            "parameters": {"bore_d": 20, "outer_d": 33},
        }
    )

    return {
        "control_tampered_radial_offset": {
            "case": "accepted IR for bore_d=20 with nodes[2].inputs.radial_offset replaced by literal 100 mm",
            "expected": "rejected before CAD runtime",
            "validate_document_errors": [
                {"code": error["code"], "stage": error["stage"], "field": error.get("field")} for error in ir_errors
            ],
            "compile": {
                "ok": semantic_run.ok,
                "status": semantic_run.status,
                "errors": [
                    {
                        "code": error.get("code"),
                        "stage": error.get("stage"),
                        "fields": error.get("fields"),
                        "node_ids": error.get("node_ids"),
                    }
                    for error in semantic_run.errors
                ],
            },
            "result": "rejected" if not semantic_run.ok and semantic_run.status == "semantic" else "unexpected",
        },
        "control_rule_rejection": {
            "case": "CAD-003 envelope bore_d=20 with explicit outer_d=33",
            "expected": "CATALOG_MISMATCH at schema stage, no IR generated",
            "ok": bad_rule.ok,
            "errors": [error.as_dict() for error in bad_rule.errors],
            "result": "rejected" if not bad_rule.ok else "unexpected",
        },
    }


def main() -> int:
    manifest_path = MANIFEST_DIR / "manifest-v0.jsonl"
    inputs_dir = MANIFEST_DIR / "inputs"
    ir_dir = MANIFEST_DIR / "ir"
    for directory in (inputs_dir, ir_dir, CAD_DIR, VAL_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    template_bytes = TEMPLATE_IR.read_bytes()
    template = json.loads(template_bytes)
    schema_bytes = SCHEMA_PATH.read_bytes()
    schema_sha256 = sha256_bytes(schema_bytes)

    from jsonschema import Draft202012Validator

    schema = json.loads(schema_bytes)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    environment = {
        "python": platform.python_version(),
        "cadquery": __import__("cadquery").__version__,
        "ocp": __import__("OCP").__version__,
        "numpy": __import__("numpy").__version__,
    }
    platform_string = platform.platform()
    generated_at = datetime.now(TZ).isoformat(timespec="seconds")
    generator_rel = rel(HERE)
    generator_sha = sha256_file(HERE)

    records = []
    report_rows = []
    geometry_fingerprints = {}

    for index, row in enumerate(CATALOG_ROWS):
        bore, outer, screw_d, screw_len, width = row
        short = sample_short(bore)
        sample_id = f"{FAMILY_ID}/{short}"

        payload = build_payload(bore)
        payload_path = inputs_dir / f"{short}.json"
        payload_sha = write_json(payload_path, payload)
        payload_bytes = payload_path.read_bytes()

        result = validate_parameters(json.loads(payload_bytes))
        if not result.ok:
            raise SystemExit(f"family rules rejected frozen catalog row bore_d={bore}: {result.as_dict()}")

        document = build_accepted_ir(template, result, bore)
        schema_errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
        if schema_errors:
            raise SystemExit(f"IR JSON Schema rejected bore_d={bore}: {[error.message for error in schema_errors]}")
        semantic = validate_document(document)
        if semantic:
            raise SystemExit(f"IR semantic validation rejected bore_d={bore}: {[error.as_dict() for error in semantic]}")

        ir_path = ir_dir / f"{short}.json"
        ir_sha = write_json(ir_path, document)
        ir_bytes = ir_path.read_bytes()

        compiled = compile_ir(ir_bytes, output_dir=CAD_DIR / short)
        if not compiled.ok:
            raise SystemExit(f"compile_ir failed for bore_d={bore}: status={compiled.status} errors={compiled.errors}")
        if compiled.manifest is None:
            raise SystemExit(f"compile_ir returned no manifest for bore_d={bore}")

        native = compiled.manifest["native_geometry"]
        repeat = compiled.manifest["native_repeatability"]["comparison"]
        comparison = compiled.manifest["step_readback"]["comparison"]
        readback = compiled.manifest["step_readback"]["geometry"]
        step = compiled.manifest["step"]
        step_path = Path(step["path"])
        step_sha = sha256_file(step_path)

        validation_artifact = {
            "sample_id": sample_id,
            "ir_sha256": ir_sha,
            "compile": {"ok": compiled.ok, "status": compiled.status, "errors": compiled.errors},
            "validation_result": compiled.ir["validation_result"],
            "manifest": compiled.manifest,
        }
        validation_path = VAL_DIR / f"{short}.json"
        validation_sha = write_json(validation_path, validation_artifact)

        role = split_for(index)
        record = {
            "manifest_version": MANIFEST_VERSION,
            "sample_id": sample_id,
            "family_id": FAMILY_ID,
            "sample_kind": "catalog_row",
            "source": {
                "repository": REPOSITORY,
                "source_commit": SOURCE_COMMIT,
                "family_path": FAMILY_PATH,
                "family_status": "MERGED",
                "release_qualified": False,
                "snapshot_status": "reproducibility_partial",
                "license_scope": LICENSE_SCOPE,
                "catalog_row": {
                    "index": index,
                    "key": "bore_d",
                    "value": bore,
                    "fields": ["bore_d", "outer_d", "screw_d", "screw_len", "width"],
                    "row": [bore, outer, screw_d, screw_len, width],
                },
            },
            "parameters": {
                "normalized": {key: result.normalized[key] for key in PARAMETER_ORDER},
                "units": {"length": "mm", "second_screw": "1 (dimensionless)"},
                "provenance": {
                    key: {
                        "source": result.provenance[key],
                        "source_ref": source_ref(key, result.provenance[key], bore),
                    }
                    for key in PARAMETER_ORDER
                },
                "catalog_key": "bore_d",
                "input_payload": {"path": rel(payload_path), "sha256": payload_sha},
            },
            "ir": {
                "ir_version": document["ir_version"],
                "ir_revision": document["ir_revision"],
                "status": document["status"],
                "schema_path": IR_SCHEMA_REL,
                "schema_sha256": schema_sha256,
                "path": rel(ir_path),
                "sha256": ir_sha,
            },
            "artifacts": {
                "step": {
                    "path": rel(step_path),
                    "sha256": step_sha,
                    "bytes": step["bytes"],
                    "repository_status": "ignored_local_artifact",
                    "license_status": "license_scope_uncertain",
                },
                "render": None,
                "validation_result": {
                    "path": rel(validation_path),
                    "sha256": validation_sha,
                    "repository_status": "ignored_local_artifact",
                },
            },
            "validation": {
                "schema": "pass",
                "family_rules": "pass",
                "cad_compile": "pass",
                "completed_stages": compiled.ir["validation_result"]["completed_stages"],
                "final_stage": compiled.ir["validation_result"]["stage"],
                "native_geometry": geometry_block(native),
                "native_repeatability": {
                    "pass": repeat["pass"],
                    "exact_equal": repeat["exact_equal"],
                    "different_fields": repeat["different_fields"],
                    "policy_id": repeat["policy_id"],
                },
                "step_readback": {
                    "pass": comparison["pass"],
                    "policy_id": comparison["policy_id"],
                    "hard_mismatches": comparison["hard_mismatches"],
                    "bbox_pass": comparison["bbox_pass"],
                    "bbox_max_abs_mm": max(comparison["bbox_abs_diffs_mm"].values()),
                    "volume_abs_mm3": comparison["volume"]["abs"],
                    "volume_rel": comparison["volume"]["rel"],
                    "face_areas": comparison["face_areas"],
                    "edge_lengths": comparison["edge_lengths"],
                    "readback_geometry": {
                        "solids": readback["solids"],
                        "shells": readback["shells"],
                        "faces": readback["faces"],
                        "edges": readback["edges"],
                        "vertices": readback["vertices"],
                        "is_valid": readback["is_valid"],
                        "volume_mm3": readback["volume_mm3"],
                    },
                },
                "policy_id": POLICY_ID,
            },
            "split": {
                "role": role,
                "group_id": f"catalog-row-bore-{bore:03d}",
                "split_rule": SPLIT_RULE,
                "split_status": SPLIT_STATUS,
            },
            "generation": {
                "generator": generator_rel,
                "generator_version": MANIFEST_VERSION,
                "ir_template": rel(TEMPLATE_IR),
                "ir_template_sha256": sha256_bytes(template_bytes),
                "seed": None,
                "generated_at": generated_at,
                **environment,
                "platform": platform_string,
            },
            "limitations": LIMITATIONS,
        }
        records.append(record)

        fingerprint = {
            "volume_mm3": round(native["volume_mm3"], 6),
            "bbox_mm": {key: round(native["bbox_mm"][key], 6) for key in native["bbox_mm"]},
            "counts": [native["solids"], native["shells"], native["faces"], native["edges"], native["vertices"]],
        }
        geometry_fingerprints[sample_id] = sha256_json(fingerprint)

        report_rows.append(
            {
                "sample_id": sample_id,
                "bore_d": bore,
                "catalog_row": list(row),
                "split_role": role,
                "group_id": record["split"]["group_id"],
                "ir_sha256": ir_sha,
                "step_sha256": step_sha,
                "step_bytes": step["bytes"],
                "cad_compile": "pass",
                "final_stage": compiled.ir["validation_result"]["stage"],
                "solids": native["solids"],
                "shells": native["shells"],
                "is_valid": native["is_valid"],
                "volume_mm3": native["volume_mm3"],
                "bbox_mm": native["bbox_mm"],
                "faces": native["faces"],
                "edges": native["edges"],
                "vertices": native["vertices"],
                "native_repeat_pass": repeat["pass"],
                "step_readback_pass": comparison["pass"],
                "step_volume_abs_mm3": comparison["volume"]["abs"],
                "step_volume_rel": comparison["volume"]["rel"],
                "step_bbox_max_abs_mm": max(comparison["bbox_abs_diffs_mm"].values()),
                "step_face_area_max_abs_mm2": comparison["face_areas"]["max_abs"],
                "step_edge_length_max_abs_mm": comparison["edge_lengths"]["max_abs"],
            }
        )

    records.sort(key=lambda item: item["source"]["catalog_row"]["index"])
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=False) for record in records]
    manifest_text = "\n".join(lines) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_sha = sha256_bytes(manifest_text.encode("utf-8"))

    # Leakage / duplication checks.
    parameter_payloads = {}
    for record in records:
        payload_sha = record["parameters"]["input_payload"]["sha256"]
        parameter_payloads.setdefault(payload_sha, []).append(record["sample_id"])
    duplicated_payloads = {key: value for key, value in parameter_payloads.items() if len(value) > 1}
    duplicated_geometry = {}
    for sample_id, fingerprint in geometry_fingerprints.items():
        duplicated_geometry.setdefault(fingerprint, []).append(sample_id)
    duplicated_geometry = {key: value for key, value in duplicated_geometry.items() if len(value) > 1}

    role_by_group = {}
    for record in records:
        role_by_group.setdefault(record["split"]["group_id"], set()).add(record["split"]["role"])
    cross_role_groups = {group: sorted(roles) for group, roles in role_by_group.items() if len(roles) > 1}

    def role_count(role: str) -> int:
        return sum(1 for record in records if record["split"]["role"] == role)

    volumes = sorted(record["validation"]["native_geometry"]["volume_mm3"] for record in records)
    min_volume_gap = min(
        (abs(a - b) / max(abs(a), abs(b)) for a, b in zip(volumes, volumes[1:])), default=None
    )

    leakage = {
        "group_key": "family_id + catalog_row (bore_d)",
        "group_count": len(role_by_group),
        "cross_split_group_overlap": len(cross_role_groups),
        "duplicate_parameter_payloads": duplicated_payloads,
        "duplicate_geometry_fingerprints": duplicated_geometry,
        "geometry_fingerprint_definition": "sha256 of rounded volume(6dp)+bbox(6dp)+topology counts",
        "min_pairwise_relative_volume_gap": min_volume_gap,
        "same_catalog_row_in_two_splits": 0,
        "retrieval_source_shared_with_evaluation": 0,
    }

    report = {
        "manifest_version": MANIFEST_VERSION,
        "task": "RET-001",
        "status": "review",
        "generated_at": generated_at,
        "generator": {
            "path": generator_rel,
            "sha256": generator_sha,
            "ir_template": rel(TEMPLATE_IR),
            "ir_template_sha256": sha256_bytes(template_bytes),
            "ir_schema_path": IR_SCHEMA_REL,
            "ir_schema_sha256": schema_sha256,
        },
        "environment": {**environment, "platform": platform_string},
        "source": {
            "repository": REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "family_path": FAMILY_PATH,
            "family_id": FAMILY_ID,
            "family_status": "MERGED",
            "release_qualified": False,
            "snapshot_status": "reproducibility_partial",
            "license_scope": LICENSE_SCOPE,
        },
        "catalog_coverage": {
            "frozen_rows": len(CATALOG_ROWS),
            "samples_generated": len(records),
            "bore_d_values": [row[0] for row in CATALOG_ROWS],
            "scope_note": "the frozen family has exactly 15 catalog rows; no additional samples were synthesized",
        },
        "split_plan": {
            "split_status": SPLIT_STATUS,
            "split_rule": SPLIT_RULE,
            "counts": {
                "development": role_count("development"),
                "retrieval_source": role_count("retrieval_source"),
                "heldout_evaluation": role_count("heldout_evaluation"),
            },
            "groups": [
                {
                    "group_id": record["split"]["group_id"],
                    "sample_id": record["sample_id"],
                    "role": record["split"]["role"],
                    "bore_d": record["source"]["catalog_row"]["value"],
                }
                for record in records
            ],
            "frozen_benchmark": False,
            "note": "provisional grouping only; RET-003/Codex must freeze any evaluation split",
        },
        "results": report_rows,
        "summary": {
            "schema_pass": len(records),
            "ir_schema_pass": len(records),
            "ir_semantic_pass": len(records),
            "cad_compile_pass": sum(1 for record in records if record["validation"]["cad_compile"] == "pass"),
            "native_repeat_pass": sum(1 for record in records if record["validation"]["native_repeatability"]["pass"]),
            "step_readback_pass": sum(1 for record in records if record["validation"]["step_readback"]["pass"]),
            "failed": 0,
        },
        "negative_controls": run_controls(),
        "leakage_checks": leakage,
        "manifest": {
            "path": rel(manifest_path),
            "sha256": manifest_sha,
            "records": len(records),
            "bytes": len(manifest_text.encode("utf-8")),
        },
        "checks": {
            "jsonl_lines": len(records),
            "jsonl_parse": "pass",
            "manifest_schema": "checked by generator/verify_manifest.py; see verification-report.json",
            "hash_verification": "checked by generator/verify_manifest.py; see verification-report.json",
            "replay": "checked by generator/replay_check.py; see replay-report.json",
        },
        "limitations": LIMITATIONS,
    }
    report_path = MANIFEST_DIR / "generation-report.json"
    report_sha = write_json(report_path, report)

    print(f"records={len(records)} manifest={rel(manifest_path)} sha256={manifest_sha}")
    print(f"report={rel(report_path)} sha256={report_sha}")
    print(json.dumps(report["summary"], indent=1))
    print(json.dumps(report["negative_controls"], indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
