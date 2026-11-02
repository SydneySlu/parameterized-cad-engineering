"""CAD-005 whitelist compiler and CAD-006 geometry/STEP validation pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import CadError, PipelineError, fail
from .expressions import Quantity, evaluate
from .geometry import POLICY_ID, compare_native_repeat, compare_roundtrip, summarize
from .ir import IR_ROOT, SCHEMA_PATH, SOURCE_COMMIT, semantic_errors, validate_document, parse_json


@dataclass
class CompilationResult:
    ok: bool
    status: str
    errors: list[dict[str, str]]
    ir: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    step_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "status": self.status, "errors": self.errors, "ir": self.ir,
                "manifest": self.manifest, "step_path": self.step_path}


def validate_ir(raw: str | bytes) -> list[CadError]:
    document, errors = parse_json(raw)
    if errors or document is None:
        return errors
    return validate_document(document)


def _cq_runtime():
    try:
        import cadquery as cq
        import OCP
    except Exception as exc:
        fail("CAD_RUNTIME_UNAVAILABLE", "build", f"CadQuery/OCP runtime unavailable: {type(exc).__name__}: {str(exc)[:300]}", "runtime")
    # The pinned OCP 7.9 binding lacks legacy TopoDS.HashCode. The previous
    # global id(self)-based monkey patch was unnecessary for this pipeline's
    # direct build/export path and changed hash semantics for every TopoDS
    # object in-process, so leave the native binding untouched.
    return cq, OCP


def _shape(value: Any):
    return value.val() if hasattr(value, "val") else value


def _require_contract(document: dict[str, Any]) -> None:
    nodes = document["nodes"]
    ids = ["n0.catalog.resolve", "n1.collar.revolve", "n2.hole.primary", "n3.cut.primary",
           "n4.hole.secondary", "n5.cut.secondary", "n6.result"]
    output_ids = ["resolved_parameters", "collar_base", "hole_cutter_primary", "solid_after_primary",
                  "hole_cutter_secondary", "solid_after_secondary", "part"]
    expected_inputs = [
        {"bore_d"}, {"bore_d", "outer_d", "width", "chamfer"},
        {"thread_d", "pitch", "angle_deg", "over", "wall", "hole_len", "z_in", "z_out", "radial_offset", "axial"},
        {"base", "tool"},
        {"thread_d", "pitch", "angle_deg", "over", "wall", "hole_len", "z_in", "z_out", "radial_offset", "axial"},
        {"base", "tool"}, {"second_screw"},
    ]
    for index, node in enumerate(nodes):
        if node["node_id"] != ids[index] or set(node["inputs"]) != expected_inputs[index]:
            fail("IR_NODE_CONTRACT_UNSUPPORTED", "semantic", "Node ID or input names do not match the frozen v0 graph.", f"nodes[{index}]")
        if len(node["outputs"]) != 1 or node["outputs"][0]["output_id"] != output_ids[index]:
            fail("IR_NODE_OUTPUT_CONTRACT_MISMATCH", "semantic", "Node output does not match its frozen v0 contract.", f"nodes[{index}].outputs")
    for index in (2, 4):
        props = nodes[index]["properties"]
        expected = {
            "cutter_local_axis": "Z", "transform_order": "column_vector_left_multiply",
            "transforms": [
                {"operation": "rotate", "frame": "cutter_local", "pivot": [0, 0, 0], "axis": [0, 1, 0], "degrees": 90},
                {"operation": "translate", "frame": "world", "vector": ["radial_offset", 0, "axial"]},
                {"operation": "rotate", "frame": "world", "pivot": [0, 0, 0], "axis": [0, 0, 1], "angle_ref": "angle_deg"},
            ],
        }
        if props.get("placement_model") != "radial_bore_breakout" or props.get("placement") != expected:
            fail("IR_NODE_PROPERTIES_CONTRACT_MISMATCH", "semantic", "Cutter placement must exactly match the registered ordered transform signature.", f"nodes[{index}].properties.placement")
    if nodes[1]["properties"].get("profile_kind") != "chamfered_annulus" or nodes[1]["properties"].get("revolve_degrees") != 360:
        fail("IR_NODE_PROPERTIES_CONTRACT_MISMATCH", "semantic", "Revolve properties do not match the frozen profile contract.", "nodes[1].properties")


def _native_build(document: dict[str, Any], cq) -> tuple[Any, list[dict[str, Any]]]:
    params = {item["parameter_id"]: Quantity(float(item["value"]), item["unit"]) for item in document["parameters"]}
    raw_values = {key: value.value for key, value in params.items()}
    outputs: dict[str, Any] = {}
    node_log: list[dict[str, Any]] = []

    def value(node: dict[str, Any], name: str) -> Quantity:
        return evaluate(node["inputs"][name], params, outputs, f"nodes.{node['node_id']}.inputs.{name}")

    for node in document["nodes"]:
        enabled = node.get("enabled_if")
        if enabled and raw_values.get(enabled["parameter_id"]) != enabled["equals"]:
            node_log.append({"node_id": node["node_id"], "node_type": node["node_type"], "status": "skipped"})
            continue
        node_id, kind = node["node_id"], node["node_type"]
        try:
            if kind == "catalog.resolve":
                result = dict(raw_values)
            elif kind == "shape.revolve_profile":
                bore, outer, width, chamfer = (value(node, key).value for key in ("bore_d", "outer_d", "width", "chamfer"))
                points = [(bore / 2 + chamfer, 0), (outer / 2 - chamfer, 0), (outer / 2, chamfer),
                          (outer / 2, width - chamfer), (outer / 2 - chamfer, width),
                          (bore / 2 + chamfer, width), (bore / 2, width - chamfer), (bore / 2, chamfer)]
                result = _shape(cq.Workplane("XZ").polyline(points).close().revolve(360, (0, 0, 0), (0, 1, 0)))
            elif kind == "feature.tapped_hole_cutter":
                diameter = value(node, "thread_d").value
                pitch = value(node, "pitch").value
                angle = value(node, "angle_deg").value
                length = value(node, "hole_len").value
                z_in, z_out = value(node, "z_in").value, value(node, "z_out").value
                radial, axial = value(node, "radial_offset").value, value(node, "axial").value
                r_major = diameter / 2
                r_minor = r_major - 0.5413 * pitch
                r_cs = r_major + 0.1 * pitch
                d_cs = r_cs - r_minor
                z0, z1 = z_in + d_cs, z_out - d_cs
                if diameter <= 0 or pitch <= 0 or r_minor <= 0 or z1 < z0:
                    fail("IR_FORMULA_DOMAIN_ERROR", "build", "Tapped-hole dimensions are outside the registered geometry domain.", f"nodes.{node_id}.inputs")
                turns = max(1, int((z1 - z0) / pitch))
                if turns > 2**31 - 1:
                    fail("IR_FORMULA_DOMAIN_ERROR", "build", "Thread turn count exceeds signed 32-bit range.", f"nodes.{node_id}.inputs.pitch")
                pts = [(0.0, 0.0), (r_cs, 0.0), (r_cs, z_in), (r_minor, z0)]
                for index in range(turns):
                    zk = z0 + index * pitch
                    pts.extend([(r_minor, zk + pitch / 8), (r_major, zk + pitch / 2 - pitch / 16),
                                (r_major, zk + pitch / 2 + pitch / 16), (r_minor, zk + pitch - pitch / 8)])
                pts.extend([(r_minor, z1), (r_cs, z_out), (r_cs, length), (0.0, length)])
                result = _shape(cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)))
                result = result.rotate((0, 0, 0), (0, 1, 0), 90)
                result = result.translate((radial, 0, axial))
                result = result.rotate((0, 0, 0), (0, 0, 1), angle)
            elif kind == "boolean.cut":
                base_ref = node["properties"]["base_ref"]
                tool_ref = node["properties"]["tool_ref"]
                if base_ref not in outputs or tool_ref not in outputs:
                    fail("IR_REFERENCE_NOT_FOUND", "build", "Boolean inputs were not produced by earlier enabled nodes.", f"nodes.{node_id}.inputs")
                # BenchCAD uses Workplane.cut(), whose default clean=True is
                # part of the pinned native reference topology.
                result = _shape(cq.Workplane(obj=outputs[base_ref]).cut(outputs[tool_ref]))
            elif kind == "result.single_solid":
                key = "select_if_one" if raw_values["second_screw"] == 1 else "select_if_zero"
                ref = node["properties"][key]
                if ref not in outputs:
                    fail("IR_REFERENCE_NOT_FOUND", "build", "Selected result shape was not produced.", f"nodes.{node_id}.properties.{key}")
                result = outputs[ref]
            else:
                fail("IR_UNKNOWN_NODE_TYPE", "build", f"Node type {kind!r} is not permitted.", f"nodes.{node_id}.node_type")
        except PipelineError:
            raise
        except Exception as exc:
            fail("CAD_BUILD_NODE_ERROR", "build", f"Node {node_id} failed: {type(exc).__name__}: {str(exc)[:300]}", f"nodes.{node_id}")
        output_id = node["outputs"][0]["output_id"]
        outputs[output_id] = result
        node_log.append({"node_id": node_id, "node_type": kind, "status": "built", "output_id": output_id})
    return outputs["part"], node_log


def _runtime_manifest(OCP, cq, input_hash: str) -> dict[str, Any]:
    import numpy as np
    return {
        "policy_id": POLICY_ID,
        "python": sys.version,
        "cadquery": getattr(cq, "__version__", "unknown"),
        "ocp": getattr(OCP, "__version__", "unknown"),
        "numpy": np.__version__,
        "os": platform.platform(),
        "source_commit": SOURCE_COMMIT,
        "ir_revision": "0.2.0",
        "schema_version": "set_screw_shaft_collar.v0",
        "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        "snapshot_status": "reproducibility_partial",
        "license_scope": "license_scope_uncertain",
        "thread_model": "revolved_ring_approximation",
        "helical_thread_supported": False,
        "input_ir_sha256": input_hash,
        "step_hash_policy": "informational_only",
    }


def _error_node_ids(document: dict[str, Any], field: str | None) -> list[str]:
    if not field:
        return []
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("node_id")
        if isinstance(node_id, str) and f"nodes.{node_id}" in field:
            return [node_id]
    match = re.search(r"(?:^|\.)nodes(?:\[(\d+)\]|\.(\d+))(?:\.|$)", field)
    if match:
        index = int(match.group(1) or match.group(2))
        if 0 <= index < len(nodes) and isinstance(nodes[index], dict):
            node_id = nodes[index].get("node_id")
            if isinstance(node_id, str):
                return [node_id]
    return []


def _serialize_error(error: CadError, document: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: value for key, value in error.as_dict().items() if key != "field"}
    normalized.update({"severity": "error", "fields": [error.field] if error.field else [],
                       "node_ids": _error_node_ids(document, error.field), "retryable": False})
    return normalized


def _failed_result(document: dict[str, Any], error: CadError, manifest: dict[str, Any] | None = None,
                   completed: list[str] | None = None, log: list[dict[str, Any]] | None = None) -> CompilationResult:
    if error.stage == "build" and error.code not in {"CAD_BUILD_NODE_ERROR", "CAD_BUILD_BOOLEAN_ERROR", "CAD_BUILD_UNSUPPORTED_FEATURE"}:
        error = CadError("CAD_BUILD_NODE_ERROR", "build", error.message, error.field)
    # The IR schema intentionally has one stable error shape.  ``field`` is
    # an internal convenience on CadError; serialize its location only as
    # the schema's ``fields`` list.
    normalized = _serialize_error(error, document)
    validation = {"stage": error.stage, "ok": False, "completed_stages": completed or [], "errors": [normalized], "metrics": {}}
    error_metrics = dict(manifest.get("native_geometry", {})) if manifest else {}
    validation["metrics"] = error_metrics
    result_ir = dict(document)
    result_ir["validation_result"] = validation
    if manifest is not None:
        manifest["validation_result"] = validation
        if log is not None:
            manifest["execution_log"] = log
    return CompilationResult(False, error.stage, [normalized], result_ir, manifest)


def compile_ir(raw: str | bytes, *, output_dir: str | os.PathLike[str] | None = None) -> CompilationResult:
    """Validate serialized IR, execute its fixed graph, and validate STEP readback."""
    document, parse_errors = parse_json(raw)
    if parse_errors or document is None:
        return CompilationResult(False, "parse", [item.as_dict() for item in parse_errors])
    validation_errors = validate_document(document)
    if validation_errors:
        preflight_errors = [error for error in validation_errors if error.stage == "preflight"]
        if preflight_errors:
            return CompilationResult(False, "preflight", [_serialize_error(item, document) for item in preflight_errors[:50]], dict(document))
        return CompilationResult(False, validation_errors[0].stage,
                                 [_serialize_error(item, document) for item in validation_errors[:50]], dict(document))
    if document.get("status") != "accepted":
        errors = document.get("errors", []) or [{"code": "CAD_PREFLIGHT_REJECTED", "stage": "preflight", "message": "Rejected IR cannot be compiled."}]
        return CompilationResult(False, "preflight", errors, dict(document))
    try:
        _require_contract(document)
        cq, OCP = _cq_runtime()
    except PipelineError as exc:
        return _failed_result(document, exc.error)
    input_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    manifest = _runtime_manifest(OCP, cq, hashlib.sha256(input_bytes).hexdigest())
    log: list[dict[str, Any]] = []
    try:
        started = time.time()
        first_shape, node_log = _native_build(document, cq)
        log.append({"stage": "build", "status": "pass", "elapsed_seconds": time.time() - started, "nodes": node_log})
        first_summary = summarize(first_shape)
        second_shape, _ = _native_build(document, cq)
        second_summary = summarize(second_shape)
        repeat = compare_native_repeat(first_summary, second_summary)
        manifest["native_repeatability"] = {"first": first_summary, "second": second_summary, "comparison": repeat}
        if not repeat["pass"]:
            fail("GEOMETRY_REPEATABILITY_MISMATCH", "post_geometry", "Same-process native builds differ under the frozen exact-repeat policy.", "geometry.repeatability")
        log.append({"stage": "native_repeat", "status": "pass", "policy_id": POLICY_ID})
    except PipelineError as exc:
        completed = [] if exc.error.stage == "build" else ["build"]
        return _failed_result(document, exc.error, manifest, completed, log)
    except Exception as exc:
        return _failed_result(document, CadError("CAD_BUILD_NODE_ERROR", "build", f"Build failed: {type(exc).__name__}: {str(exc)[:300]}", "build"), manifest, [], log)
    try:
        # Geometry summary is mandatory after construction and before export.
        native_summary = first_summary
        log.append({"stage": "post_geometry", "status": "pass", "geometry": native_summary})
    except PipelineError as exc:
        return _failed_result(document, exc.error, manifest, ["build"], log)
    out = Path(output_dir) if output_dir is not None else Path(tempfile.gettempdir()) / "cad-compilation-output"
    try:
        out.mkdir(parents=True, exist_ok=True)
        step_path = out / f"{manifest['input_ir_sha256'][:16]}.step"
        first_shape.exportStep(str(step_path))
        if not step_path.is_file() or step_path.stat().st_size == 0:
            fail("CAD_STEP_EXPORT_FAILED", "step_export", "STEP export did not produce a non-empty file.", "step_path")
        step_hash = hashlib.sha256(step_path.read_bytes()).hexdigest()
        log.append({"stage": "step_export", "status": "pass", "bytes": step_path.stat().st_size, "sha256": step_hash})
    except PipelineError as exc:
        return _failed_result(document, exc.error, manifest, ["build", "post_geometry"], log)
    except Exception as exc:
        return _failed_result(document, CadError("CAD_STEP_EXPORT_FAILED", "step_export", f"STEP export failed: {type(exc).__name__}: {str(exc)[:300]}", "step_path"), manifest, ["build", "post_geometry"], log)
    try:
        imported = cq.importers.importStep(str(step_path))
        readback = _shape(imported)
        readback_summary = summarize(readback)
        comparison = compare_roundtrip(native_summary, readback_summary)
        manifest["step_readback"] = {"geometry": readback_summary, "comparison": comparison}
        if not comparison["pass"]:
            fail("GEOMETRY_STEP_MISMATCH", "step_readback", "STEP readback differs from native geometry under CAD-006.geometry-comparison.v1.", "step_readback")
        log.append({"stage": "step_readback", "status": "pass", "comparison": comparison})
    except PipelineError as exc:
        return _failed_result(document, exc.error, manifest, ["build", "post_geometry", "step_export"], log)
    except Exception as exc:
        return _failed_result(document, CadError("CAD_STEP_READBACK_FAILED", "step_readback", f"STEP readback failed: {type(exc).__name__}: {str(exc)[:300]}", "step_readback"), manifest, ["build", "post_geometry", "step_export"], log)
    validation = {"stage": "step_readback", "ok": True,
                  "completed_stages": ["build", "post_geometry", "step_export"], "errors": [],
                  "metrics": {"native_geometry": native_summary, "step_geometry": readback_summary,
                              "comparison": comparison}}
    result_ir = dict(document)
    result_ir["validation_result"] = validation
    manifest["validation_result"] = validation
    manifest["execution_log"] = log
    manifest["native_geometry"] = native_summary
    manifest["step"] = {"path": str(step_path), "bytes": step_path.stat().st_size, "sha256": step_hash}
    # Round-trip check the produced IR contract as well as the input document.
    from .ir import semantic_errors
    result_errors = semantic_errors(result_ir)
    if result_errors:
        error = result_errors[0]
        return _failed_result(document, error, manifest, ["build", "post_geometry", "step_export", "step_readback"], log)
    return CompilationResult(True, "step_readback", [], result_ir, manifest, str(step_path))
