"""JSON Schema and semantic validation for the reviewed Typed CAD IR v0.2."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .errors import CadError

REPO_ROOT = Path(__file__).resolve().parents[2]
IR_ROOT = REPO_ROOT / "agent-work" / "typed-cad-ir" / "IR-001-v0"
SCHEMA_PATH = IR_ROOT / "ir-v0.schema.json"
SOURCE_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"
SCHEMA_VERSION = "set_screw_shaft_collar.v0"
POLICY_ID = "CAD-006.geometry-comparison.v1"
PARAMETER_ORDER = ["bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"]
CATALOG = {
    5: (10, 3, 4, 6), 6: (12, 4, 5, 8), 8: (16, 4, 6, 8),
    10: (20, 5, 8, 10), 12: (22, 6, 8, 12), 16: (28, 6, 8, 12),
    20: (32, 6, 8, 14), 24: (40, 8, 12, 16), 30: (45, 8, 10, 16),
    35: (56, 8, 12, 16), 40: (63, 10, 16, 18), 50: (80, 10, 16, 18),
    60: (90, 10, 16, 20), 70: (100, 10, 20, 20), 80: (110, 12, 20, 22),
}


def parse_json(raw: str | bytes) -> tuple[dict[str, Any] | None, list[CadError]]:
    if not isinstance(raw, (str, bytes)):
        return None, [CadError("IR_SERIALIZED_JSON_REQUIRED", "parse", "IR entry point accepts JSON text or bytes, not Python objects.", "ir")]
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, [CadError("IR_INVALID_JSON", "parse", f"Invalid JSON: {str(exc)[:300]}", "ir")]
    if not isinstance(value, dict):
        return None, [CadError("IR_ROOT_TYPE_INVALID", "parse", "IR JSON root must be an object.", "ir")]
    return value, []


def _schema_errors(document: dict[str, Any]) -> list[CadError]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return [CadError("CAD_SCHEMA_VALIDATOR_UNAVAILABLE", "schema", "The jsonschema package is required to validate IR against Draft 2020-12.", "schema")]
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(document), key=lambda error: (list(error.absolute_path), error.message))
    except Exception as exc:
        return [CadError("CAD_SCHEMA_LOAD_ERROR", "schema", f"Unable to load IR schema: {type(exc).__name__}: {str(exc)[:300]}", "schema")]
    result = []
    for error in errors[:50]:
        path = ".".join(str(part) for part in error.absolute_path) or "ir"
        result.append(CadError("IR_SCHEMA_VALIDATION_ERROR", "schema", error.message[:300], path))
    if len(errors) > 50:
        result.append(CadError("IR_SCHEMA_ERROR_LIMIT", "schema", "Schema validation returned more than 50 errors; remaining errors omitted.", "ir"))
    return result


def _unique(items: list[dict[str, Any]], key: str, code: str, field: str, errors: list[CadError]) -> None:
    seen: set[Any] = set()
    for index, item in enumerate(items):
        value = item.get(key)
        if value in seen:
            errors.append(CadError(code, "semantic", f"Duplicate {key}: {value!r}.", f"{field}[{index}].{key}"))
        seen.add(value)


def _walk_expr(expr: Any, params: set[str], outputs: set[str], errors: list[CadError], field: str) -> None:
    if not isinstance(expr, dict):
        errors.append(CadError("IR_EXECUTION_STRING_FORBIDDEN", "semantic", "Node expressions must be structured objects.", field))
        return
    kind = expr.get("kind")
    if kind == "parameter_ref" and expr.get("parameter_id") not in params:
        errors.append(CadError("IR_REFERENCE_NOT_FOUND", "semantic", "Unknown parameter reference.", field))
    elif kind == "node_output_ref" and expr.get("output_id") not in outputs:
        errors.append(CadError("IR_REFERENCE_NOT_FOUND", "semantic", "Unknown node output reference.", field))
    elif kind == "formula":
        registered = {"half_difference", "half", "multiply", "add", "subtract", "min", "max", "collar_chamfer",
                      "thread_minor_radius", "thread_countersink_radius", "thread_turn_count"}
        formula_id = expr.get("formula_id")
        if formula_id not in registered:
            errors.append(CadError("IR_UNREGISTERED_FORMULA", "semantic", f"Formula {formula_id!r} is not registered for this v0 IR.", field))
        args = expr.get("args")
        if isinstance(args, dict):
            for name, value in args.items():
                _walk_expr(value, params, outputs, errors, f"{field}.args.{name}")
        elif isinstance(args, list):
            for index, value in enumerate(args):
                _walk_expr(value, params, outputs, errors, f"{field}.args[{index}]")
    elif kind == "lookup":
        if expr.get("table_id") != "iso261.coarse_pitch_mm":
            errors.append(CadError("IR_UNREGISTERED_LOOKUP", "semantic", "Lookup table is not registered.", field))
        _walk_expr(expr.get("key"), params, outputs, errors, f"{field}.key")
    elif kind == "literal":
        value = expr.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(CadError("IR_NONFINITE_LITERAL", "semantic", "Literal must be a finite number.", field))
    elif kind not in {"parameter_ref", "node_output_ref", "literal"}:
        errors.append(CadError("IR_EXECUTION_STRING_FORBIDDEN", "semantic", f"Expression kind {kind!r} is not allowed.", field))


def semantic_errors(document: dict[str, Any]) -> list[CadError]:
    errors: list[CadError] = []
    if document.get("ir_version") != "typed-cad-ir.v0" or document.get("ir_revision") != "0.2.0":
        errors.append(CadError("IR_VERSION_UNSUPPORTED", "semantic", "Only typed-cad-ir.v0 revision 0.2.0 is supported.", "ir_version"))
    family = document.get("family", {})
    source = document.get("source", {})
    if family.get("family_id") != "set_screw_shaft_collar" or (document.get("status") == "accepted" and family.get("directory_id") != "set_screw_shaft_collar"):
        errors.append(CadError("IR_FAMILY_MISMATCH", "semantic", "Only the frozen set_screw_shaft_collar family is supported.", "family"))
    if family.get("extension_namespace") != "family.set_screw_shaft_collar.v0":
        errors.append(CadError("IR_FAMILY_MISMATCH", "semantic", "Unsupported family extension namespace.", "family.extension_namespace"))
    if source.get("schema_version") != SCHEMA_VERSION:
        errors.append(CadError("IR_SCHEMA_VERSION_MISMATCH", "semantic", "Unsupported family schema version.", "source.schema_version"))
    if source.get("source_commit") != SOURCE_COMMIT:
        errors.append(CadError("IR_SOURCE_COMMIT_MISMATCH", "semantic", "IR source commit differs from the frozen BenchCAD commit.", "source.source_commit"))
    if source.get("snapshot_status") != "reproducibility_partial":
        errors.append(CadError("IR_SNAPSHOT_STATUS_UNSUPPORTED", "semantic", "Snapshot status must remain reproducibility_partial.", "source.snapshot_status"))
    parameters = document.get("parameters", [])
    nodes = document.get("nodes", [])
    constraints = document.get("constraints", [])
    _unique(parameters, "parameter_id", "IR_DUPLICATE_PARAMETER_ID", "parameters", errors)
    _unique(nodes, "node_id", "IR_DUPLICATE_NODE_ID", "nodes", errors)
    _unique(constraints, "constraint_id", "IR_DUPLICATE_CONSTRAINT_ID", "constraints", errors)
    outputs: list[dict[str, Any]] = [output for node in nodes for output in node.get("outputs", [])]
    _unique(outputs, "output_id", "IR_DUPLICATE_OUTPUT_ID", "nodes.outputs", errors)
    if document.get("status") == "accepted":
        names = [parameter.get("parameter_id") for parameter in parameters]
        if names != PARAMETER_ORDER:
            errors.append(CadError("IR_PARAMETER_ORDER_MISMATCH", "semantic", "Accepted parameters must follow the frozen six-field order.", "parameters"))
        values = {parameter.get("parameter_id"): parameter.get("value") for parameter in parameters}
        if set(values) == set(PARAMETER_ORDER):
            bore = values["bore_d"]
            if isinstance(bore, bool) or not isinstance(bore, (int, float)) or int(bore) != bore or int(bore) not in CATALOG:
                errors.append(CadError("CAD_PREFLIGHT_CATALOG_ROW_INVALID", "preflight", "bore_d must select one of the 15 frozen catalog rows.", "parameters.bore_d"))
            else:
                expected = CATALOG[int(bore)]
                actual = (values["outer_d"], values["screw_d"], values["screw_len"], values["width"])
                if tuple(actual) != expected:
                    errors.append(CadError("CAD_PREFLIGHT_CATALOG_MISMATCH", "preflight", "Derived dimensions do not match the selected catalog row.", "parameters"))
                if values["second_screw"] != int(bore > 70):
                    errors.append(CadError("CAD_PREFLIGHT_SECOND_SCREW_RULE", "preflight", "second_screw must equal 1 exactly when bore_d > 70.", "parameters.second_screw"))
                wall = (values["outer_d"] - bore) / 2
                if values["outer_d"] <= bore:
                    errors.append(CadError("CAD_PREFLIGHT_OUTER_DIAMETER", "preflight", "outer_d must be greater than bore_d.", "parameters.outer_d"))
                if wall <= 0.65 * values["screw_d"]:
                    errors.append(CadError("CAD_PREFLIGHT_WALL_THICKNESS", "preflight", "Wall thickness must exceed 0.65 times screw_d.", "parameters.outer_d"))
                if values["width"] < 1.45 * values["screw_d"]:
                    errors.append(CadError("CAD_PREFLIGHT_AXIAL_SUPPORT", "preflight", "width must be at least 1.45 times screw_d.", "parameters.width"))
    node_ordinals = [node.get("ordinal") for node in nodes]
    if node_ordinals != list(range(len(nodes))):
        errors.append(CadError("IR_ORDINAL_NOT_CONTIGUOUS", "semantic", "Node ordinals must be contiguous and match array order.", "nodes"))
    node_by_id = {node.get("node_id"): node for node in nodes}
    for i, node in enumerate(nodes):
        for dependency in node.get("depends_on", []):
            previous = node_by_id.get(dependency)
            if previous is None or previous.get("ordinal", i) >= i:
                errors.append(CadError("IR_DEPENDENCY_NOT_PREVIOUS", "semantic", "Dependencies must point to existing earlier nodes.", f"nodes[{i}].depends_on"))
        for key, expr in node.get("inputs", {}).items():
            _walk_expr(expr, {p.get("parameter_id") for p in parameters}, {o.get("output_id") for o in outputs}, errors, f"nodes[{i}].inputs.{key}")
    expected_types = ["catalog.resolve", "shape.revolve_profile", "feature.tapped_hole_cutter", "boolean.cut", "feature.tapped_hole_cutter", "boolean.cut", "result.single_solid"]
    if document.get("status") == "accepted" and [n.get("node_type") for n in nodes] != expected_types:
        errors.append(CadError("IR_NODE_CONTRACT_UNSUPPORTED", "semantic", "Accepted v0 must use the seven-node frozen single-family graph.", "nodes"))
    if document.get("status") == "accepted" and len(nodes) == 7:
        revolve = nodes[1]
        props = revolve.get("properties", {})
        if (props.get("workplane"), props.get("axis_local"), props.get("axis"), props.get("revolve_degrees")) != ("XZ", [0, 1, 0], "Z", 360):
            errors.append(CadError("IR_REVOLVE_AXIS_CONTRACT_MISMATCH", "semantic", "Revolve must preserve XZ / local +Y / world Z / 360 degree semantics.", "nodes[1].properties"))
        for index in (2, 4):
            prop = nodes[index].get("properties", {})
            if prop.get("thread_model") != "revolved_ring_approximation" or prop.get("helical_thread_supported") is not False:
                errors.append(CadError("IR_NODE_PROPERTIES_CONTRACT_MISMATCH", "semantic", "Thread model must remain a revolved ring approximation; helical support is false.", f"nodes[{index}].properties"))
    validation = document.get("validation_result")
    if validation is not None:
        errs = validation.get("errors", [])
        if bool(validation.get("ok")) != (len(errs) == 0):
            errors.append(CadError("IR_VALIDATION_RESULT_ERRORS_INCONSISTENT", "semantic", "validation_result.ok must agree with its errors array.", "validation_result"))
        if any(err.get("stage") != validation.get("stage") for err in errs):
            errors.append(CadError("IR_VALIDATION_STAGE_MISMATCH", "semantic", "Every validation error stage must match validation_result.stage.", "validation_result.errors"))
        completed = {
            "build": [], "post_geometry": ["build"],
            "step_export": ["build", "post_geometry"],
            "step_readback": ["build", "post_geometry", "step_export"],
        }
        if validation.get("completed_stages") != completed.get(validation.get("stage")):
            errors.append(CadError("IR_VALIDATION_STAGE_ORDER_INVALID", "semantic", "completed_stages must exactly match successful prerequisite stages.", "validation_result.completed_stages"))
    return errors


def validate_document(document: dict[str, Any]) -> list[CadError]:
    errors = _schema_errors(document)
    if errors:
        return errors
    return semantic_errors(document)
