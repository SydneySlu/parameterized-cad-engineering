"""Geometry summaries and the frozen CAD-006.geometry-comparison.v1 policy."""

from __future__ import annotations

import math
from typing import Any

from .errors import fail

POLICY_ID = "CAD-006.geometry-comparison.v1"
COUNTS = ("solids", "shells", "faces", "edges", "vertices")
COORDS = ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")


def _finite(values: list[float], code: str, field: str, *, positive: bool = False) -> None:
    if any(not math.isfinite(value) or (positive and value <= 0) for value in values):
        fail(code, "post_geometry", "Geometry summary contains a missing, non-finite, or non-positive value.", field)


def summarize(shape: Any) -> dict[str, Any]:
    try:
        bbox = shape.BoundingBox()
        faces = [float(face.Area()) for face in shape.Faces()]
        edges = [float(edge.Length()) for edge in shape.Edges()]
        result = {
            "solids": len(shape.Solids()),
            "shells": len(shape.Shells()),
            "faces": len(faces),
            "edges": len(edges),
            "vertices": len(shape.Vertices()),
            "is_valid": bool(shape.isValid()),
            "volume_mm3": float(shape.Volume()),
            "bbox_mm": {key: float(getattr(bbox, key)) for key in COORDS},
            "face_areas_mm2": sorted(faces),
            "edge_lengths_mm": sorted(edges),
        }
    except Exception as exc:
        fail("GEOMETRY_SUMMARY_FAILED", "post_geometry", f"Could not summarize built shape: {type(exc).__name__}: {str(exc)[:300]}", "geometry")
    _validate_summary(result, "GEOMETRY_INVALID_SUMMARY")
    return result


def _validate_summary(summary: dict[str, Any], code: str) -> None:
    if not summary.get("is_valid"):
        fail("GEOMETRY_INVALID_BREP", "post_geometry", "B-Rep is not valid.", "geometry.is_valid")
    if any(not isinstance(summary.get(key), int) or summary[key] < 0 for key in COUNTS):
        fail(code, "post_geometry", "Topology counts are missing or invalid.", "geometry.counts")
    if summary["solids"] != 1 or summary["shells"] != 1:
        fail("GEOMETRY_MULTI_SOLID" if summary["solids"] != 1 else "GEOMETRY_SHELL_COUNT", "post_geometry", "Geometry must contain exactly one solid and one shell.", "geometry.solids")
    if summary["faces"] == 0 or summary["edges"] == 0 or summary["vertices"] == 0:
        fail("GEOMETRY_EMPTY", "post_geometry", "Geometry must have non-empty faces, edges, and vertices.", "geometry")
    if not math.isfinite(summary.get("volume_mm3", float("nan"))) or summary["volume_mm3"] <= 0:
        fail(code, "post_geometry", "Volume must be finite and positive.", "geometry.volume_mm3")
    if set(summary.get("bbox_mm", {})) != set(COORDS):
        fail(code, "post_geometry", "All six bounding box coordinates are required.", "geometry.bbox_mm")
    _finite(list(summary["bbox_mm"].values()), code, "geometry.bbox_mm")
    for field in ("face_areas_mm2", "edge_lengths_mm"):
        values = summary.get(field)
        if not isinstance(values, list) or not values:
            fail(code, "post_geometry", "Sorted geometric metric array must be present and non-empty.", f"geometry.{field}")
        _finite(values, code, f"geometry.{field}", positive=True)


def validate_summary(summary: dict[str, Any]) -> None:
    _validate_summary(summary, "GEOMETRY_INVALID_SUMMARY")


def _near(a: float, b: float, abs_tol: float, rel_tol: float) -> dict[str, float | bool]:
    absolute = abs(a - b)
    relative = absolute / max(abs(a), abs(b))
    return {"abs": absolute, "rel": relative, "pass": absolute <= abs_tol and relative <= rel_tol}


def compare_native_repeat(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    validate_summary(first)
    validate_summary(second)
    fields = (*COUNTS, "is_valid", "volume_mm3", "bbox_mm", "face_areas_mm2", "edge_lengths_mm")
    differences = [field for field in fields if first[field] != second[field]]
    return {"policy_id": POLICY_ID, "comparison": "same_process_native_repeat", "pass": not differences, "exact_equal": not differences, "different_fields": differences}


def compare_roundtrip(native: dict[str, Any], readback: dict[str, Any]) -> dict[str, Any]:
    validate_summary(native)
    validate_summary(readback)
    hard_mismatches = [key for key in COUNTS if native[key] != readback[key]]
    if native["is_valid"] is not True or readback["is_valid"] is not True:
        hard_mismatches.append("is_valid")
    if len(native["face_areas_mm2"]) != len(readback["face_areas_mm2"]):
        hard_mismatches.append("face_areas_mm2.length")
    if len(native["edge_lengths_mm"]) != len(readback["edge_lengths_mm"]):
        hard_mismatches.append("edge_lengths_mm.length")
    bbox = {key: abs(native["bbox_mm"][key] - readback["bbox_mm"][key]) for key in COORDS}
    volume = _near(native["volume_mm3"], readback["volume_mm3"], 0.0682, 3.941e-6)
    face_pairs = [_near(a, b, 0.00794, 1.440e-5) for a, b in zip(native["face_areas_mm2"], readback["face_areas_mm2"])]
    edge_pairs = [_near(a, b, 1e-5, 2.956e-8) for a, b in zip(native["edge_lengths_mm"], readback["edge_lengths_mm"])]
    bbox_ok = all(value <= 1e-5 for value in bbox.values())
    passed = (not hard_mismatches and bbox_ok and volume["pass"] and
              all(item["pass"] for item in face_pairs) and all(item["pass"] for item in edge_pairs))
    return {
        "policy_id": POLICY_ID,
        "comparison": "native_to_step_readback",
        "pass": passed,
        "hard_mismatches": hard_mismatches,
        "bbox_abs_diffs_mm": bbox,
        "bbox_pass": bbox_ok,
        "volume": volume,
        "face_areas": {"count": len(face_pairs), "pass": all(item["pass"] for item in face_pairs), "max_abs": max((float(i["abs"]) for i in face_pairs), default=0.0), "max_rel": max((float(i["rel"]) for i in face_pairs), default=0.0)},
        "edge_lengths": {"count": len(edge_pairs), "pass": all(item["pass"] for item in edge_pairs), "max_abs": max((float(i["abs"]) for i in edge_pairs), default=0.0), "max_rel": max((float(i["rel"]) for i in edge_pairs), default=0.0)},
    }
