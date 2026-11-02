#!/usr/bin/env python3
"""Measure CAD-006 geometry repeatability before freezing tolerances.

This is a measurement artifact, not a production validator.  It reads the
fixed BenchCAD API snapshot under ``work/`` and writes temporary STEP files
under ignored ``work/benchcad-output/tolerance-measurement``.  No threshold
from this script is consumed by ``src/cad_compilation``.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO_ROOT / "work" / "benchcad-source" / "api-snapshot-035f467"
FAMILY = SNAPSHOT / "designs" / "set_screw_shaft_collar"
OUT_DIR = REPO_ROOT / "work" / "benchcad-output" / "tolerance-measurement"
RESULT_PATH = Path(__file__).with_name("tolerance-results.json")
SOURCE_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"
IR_VERSION = "typed-cad-ir.v0"
IR_REVISION = "0.2.0"
SCHEMA_VERSION = "set_screw_shaft_collar.v0"
SCHEMA_PATH = REPO_ROOT / "agent-work" / "typed-cad-ir" / "IR-001-v0" / "ir-v0.schema.json"


def install_compatibility_shim() -> None:
    """Apply the explicit CQ 2.3/OCP 7.9 HashCode compatibility shim."""

    from OCP.TopoDS import (
        TopoDS_Compound,
        TopoDS_CompSolid,
        TopoDS_Edge,
        TopoDS_Face,
        TopoDS_Shape,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Vertex,
        TopoDS_Wire,
    )

    for cls in (
        TopoDS_Shape,
        TopoDS_Face,
        TopoDS_Edge,
        TopoDS_Vertex,
        TopoDS_Wire,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Compound,
        TopoDS_CompSolid,
    ):
        if not hasattr(cls, "HashCode"):
            cls.HashCode = lambda self, ub=2147483647: id(self) % ub


def shape_from_result(result):
    import cadquery as cq

    if isinstance(result, cq.Assembly):
        return result.toCompound()
    return result.val() if hasattr(result, "val") else result


def metric_values(shape):
    import cadquery as cq

    wp = cq.Workplane(obj=shape)
    bb = shape.BoundingBox()
    bbox = {
        name: float(getattr(bb, name))
        for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")
    }
    return {
        "solids": int(wp.solids().size()),
        "shells": int(wp.shells().size()),
        "faces": int(wp.faces().size()),
        "edges": int(wp.edges().size()),
        "vertices": int(wp.vertices().size()),
        "is_valid": bool(shape.isValid()),
        "volume_mm3": float(shape.Volume()),
        "bbox_mm": bbox,
        "face_areas_mm2": sorted(float(face.Area()) for face in wp.faces().vals()),
        "edge_lengths_mm": sorted(float(edge.Length()) for edge in wp.edges().vals()),
    }


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def relative_error(a, b, floor=1e-300):
    scale = max(abs(float(a)), abs(float(b)), floor)
    return abs(float(a) - float(b)) / scale


def sequence_error(left, right):
    if len(left) != len(right):
        return {
            "count_left": len(left),
            "count_right": len(right),
            "max_abs": None,
            "max_rel": None,
        }
    abs_values = [abs(float(a) - float(b)) for a, b in zip(left, right)]
    rel_values = [relative_error(a, b) for a, b in zip(left, right)]
    return {
        "count_left": len(left),
        "count_right": len(right),
        "max_abs": max(abs_values, default=0.0),
        "max_rel": max(rel_values, default=0.0),
    }


def metric_error(left, right):
    bbox_abs = {
        key: abs(float(left["bbox_mm"][key]) - float(right["bbox_mm"][key]))
        for key in left["bbox_mm"]
    }
    # Bounding-box coordinates can legitimately be zero.  Use a 1 mm scale
    # floor for their relative display so a signed-zero roundoff is not
    # reported as a meaningless 100% error; absolute coordinate error remains
    # the primary measure.
    bbox_rel = {
        key: relative_error(left["bbox_mm"][key], right["bbox_mm"][key], floor=1.0)
        for key in left["bbox_mm"]
    }
    return {
        "volume_mm3": {
            "abs": abs(left["volume_mm3"] - right["volume_mm3"]),
            "rel": relative_error(left["volume_mm3"], right["volume_mm3"]),
        },
        "bbox_mm": {
            "abs_by_coordinate": bbox_abs,
            "rel_by_coordinate": bbox_rel,
            "max_abs": max(bbox_abs.values(), default=0.0),
            "max_rel": max(bbox_rel.values(), default=0.0),
        },
        "face_areas_mm2": sequence_error(
            left["face_areas_mm2"], right["face_areas_mm2"]
        ),
        "edge_lengths_mm": sequence_error(
            left["edge_lengths_mm"], right["edge_lengths_mm"]
        ),
    }


def collect_max(errors):
    fields = {
        "volume_mm3": ("abs", "rel"),
        "bbox_mm": ("max_abs", "max_rel"),
        "face_areas_mm2": ("max_abs", "max_rel"),
        "edge_lengths_mm": ("max_abs", "max_rel"),
    }
    out = {}
    for field, keys in fields.items():
        for key in keys:
            values = [
                error[field][key]
                for error in errors
                if error[field].get(key) is not None
            ]
            out[f"{field}.{key}"] = max(values, default=0.0)
    return out


def candidate_thresholds(maxima):
    """Return review-only candidates using 2x the observed maximum."""

    return {
        key: {
            "value": value * 2.0,
            "basis": "2x observed maximum; candidate only, not production policy",
        }
        for key, value in maxima.items()
    }


def main() -> int:
    if not SNAPSHOT.is_dir() or not FAMILY.joinpath("part.py").is_file():
        print(f"blocked: fixed snapshot/family missing under {SNAPSHOT}")
        return 2

    sys.path.insert(0, str(SNAPSHOT / "framework"))
    sys.path.insert(0, str(SNAPSHOT))

    import cadquery as cq
    import numpy as np
    from bench2.loader import load_family

    install_compatibility_shim()
    part, spec = load_family(FAMILY)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    catalog_rows = list(spec.CATALOG_ROWS)
    if len(catalog_rows) != 15:
        print(f"blocked: expected 15 catalog rows, found {len(catalog_rows)}")
        return 2

    cases = []
    for row in catalog_rows:
        bore_d, outer_d, screw_d, screw_len, width = row
        cases.append(
            {
                "case_id": f"catalog_bore_{bore_d:g}",
                "params": {
                    "bore_d": bore_d,
                    "outer_d": outer_d,
                    "width": width,
                    "screw_d": screw_d,
                    "screw_len": screw_len,
                    "second_screw": 1 if bore_d > 70 else 0,
                },
            }
        )

    records = []
    repeat_errors = []
    roundtrip_errors = []
    for case in cases:
        case_id = case["case_id"]
        params = case["params"]
        check_errors = list(spec.check(dict(params)))
        for run in range(1, 4):
            record = {
                "case_id": case_id,
                "run": run,
                "params": params,
                "check_errors": check_errors,
            }
            step_path = OUT_DIR / f"{case_id}-run{run}.step"
            try:
                native = shape_from_result(part.build(**params))
                native_metrics = metric_values(native)
                native_metrics["all_finite"] = all(
                    finite(x)
                    for x in [
                        native_metrics["volume_mm3"],
                        *native_metrics["bbox_mm"].values(),
                        *native_metrics["face_areas_mm2"],
                        *native_metrics["edge_lengths_mm"],
                    ]
                )
                native.exportStep(str(step_path))
                readback = shape_from_result(cq.importers.importStep(str(step_path)))
                readback_metrics = metric_values(readback)
                rt_error = metric_error(native_metrics, readback_metrics)
                roundtrip_errors.append(rt_error)
                record.update(
                    {
                        "native": native_metrics,
                        "step": {
                            "path": str(step_path.relative_to(REPO_ROOT)),
                            "bytes": step_path.stat().st_size,
                            "sha256": hashlib.sha256(step_path.read_bytes()).hexdigest(),
                        },
                        "step_readback": readback_metrics,
                        "native_to_step_readback_error": rt_error,
                    }
                )
            except Exception as exc:  # pragma: no cover - environment dependent
                record["error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc)[:1000],
                }
            records.append(record)

        successful = [r for r in records if r["case_id"] == case_id and "native" in r]
        for left, right in zip(successful, successful[1:]):
            error = metric_error(left["native"], right["native"])
            error["case_id"] = case_id
            error["runs"] = [left["run"], right["run"]]
            repeat_errors.append(error)

    native_max = collect_max(repeat_errors)
    roundtrip_max = collect_max(roundtrip_errors)
    result = {
        "measurement": {
            "task": "CAD-005/006-tolerance",
            "status": "review",
            "repeat_count": 3,
            "catalog_row_count": len(cases),
            "catalog_bore_values": [case["params"]["bore_d"] for case in cases],
            "source_commit": SOURCE_COMMIT,
            "snapshot_status": "reproducibility_partial",
            "ir_version": IR_VERSION,
            "ir_revision": IR_REVISION,
            "schema_version": SCHEMA_VERSION,
            "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "cadquery": getattr(cq, "__version__", "unknown"),
                "ocp": __import__("OCP").__version__ if hasattr(__import__("OCP"), "__version__") else "7.9.3.0",
                "numpy": np.__version__,
                "compatibility_shim": "OCP.TopoDS.HashCode fallback for CQ 2.3/OCP 7.9",
            },
        },
        "records": records,
        "native_repeatability": {
            "comparison_count": len(repeat_errors),
            "max_errors": native_max,
            "candidate_thresholds": candidate_thresholds(native_max),
            "note": "Candidate thresholds are 2x observed maxima for review only; no production validator consumes them.",
        },
        "step_roundtrip": {
            "comparison_count": len(roundtrip_errors),
            "max_errors": roundtrip_max,
            "candidate_thresholds": candidate_thresholds(roundtrip_max),
            "note": "STEP byte hashes are retained as auxiliary data; geometry comparisons use raw metrics and sorted arrays.",
        },
        "structure_summary": {
            "native_unique_counts": {
                key: sorted({r["native"][key] for r in records if "native" in r})
                for key in ("solids", "shells", "faces", "edges", "vertices")
            },
            "readback_unique_counts": {
                key: sorted({r["step_readback"][key] for r in records if "step_readback" in r})
                for key in ("solids", "shells", "faces", "edges", "vertices")
            },
        },
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["measurement"]["status"],
        "records": len(records),
        "successful_records": sum("native" in r for r in records),
        "native_repeat_comparisons": len(repeat_errors),
        "roundtrip_comparisons": len(roundtrip_errors),
        "result_path": str(RESULT_PATH),
    }, indent=2))
    return 0 if all("native" in r for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
