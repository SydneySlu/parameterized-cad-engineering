"""Formal CAD-003 Schema → Typed CAD IR v0 adapter.

Implements the deterministic mapping defined in
agent-work/typed-cad-ir/IR-001-v0/mapping.md (frozen, R3).

Always re-runs validate_parameters on the raw payload.
Never trusts externally constructed ok=True.
Only generates status=accepted when ALL schema rules pass AND
the produced IR passes validate_ir.

Fixed source commit, IR version, and comparison policy are hardcoded per
the mapping spec; do not update them without a new ADR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Frozen constants (mapping.md § 5)
# ---------------------------------------------------------------------------

ADAPTER_VERSION: str = "integration.schema_to_ir.v0.1.0"
_SOURCE_COMMIT: str = "035f467142888edfd0bd7cd73906f9b155c8f43c"
_SNAPSHOT_STATUS: str = "reproducibility_partial"
_IR_VERSION: str = "typed-cad-ir.v0"
_IR_REVISION: str = "0.2.0"
_COMPARISON_POLICY: str = "CAD-006.geometry-comparison.v1"
_PARAMETER_ORDER: list[str] = [
    "bore_d", "outer_d", "screw_d", "screw_len", "second_screw", "width"
]


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class AdapterResult:
    """Result of the Schema→IR mapping step.

    status values:
      "accepted"      – IR produced and validates; ir_document/ir_json set.
      "rejected"      – Schema rules failed; ir_document is None.
      "ir_invalid"    – IR was produced but failed validate_ir (adapter bug).
    """

    status: str
    ir_document: dict[str, Any] | None
    ir_json: str | None
    schema_version: str
    errors: list[dict[str, Any]]
    stage: str
    provenance: dict[str, str]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_ir_from_schema_payload(
    raw_schema_payload: dict[str, Any],
    *,
    adapter_version: str = ADAPTER_VERSION,
) -> AdapterResult:
    """Build an accepted Typed CAD IR from a raw CAD-003 schema payload.

    Parameters
    ----------
    raw_schema_payload:
        The formal CAD-003 envelope produced by ``project_to_cad003``.
        May contain bare numbers or ``{value, unit}`` measurement objects.
        Must include ``schema_version``, ``family_id``, and ``parameters``.
    adapter_version:
        Recorded in ``source.adapter_version``; use the default for production.

    Notes
    -----
    - Always re-runs ``validate_parameters`` internally; never trusts an
      externally constructed ``ok=True``.
    - Preserves original ``{value, unit}`` for user-explicit length fields.
    - Bare numbers → ``input.unit = "mm"`` per the mapping spec.
    - ``second_screw`` iff ``bore_d > 70``; 70 → 0, 80 → 1.
    - ``screw_len`` is a catalog/task field, not a hole-depth input.
    """
    from schema.set_screw_shaft_collar import validate_parameters
    from cad_compilation import validate_ir

    # Always re-validate — never trust externally injected ok=True.
    validation = validate_parameters(raw_schema_payload)

    if not validation.ok:
        return AdapterResult(
            status="rejected",
            ir_document=None,
            ir_json=None,
            schema_version=validation.schema_version,
            errors=[e.as_dict() for e in validation.errors],
            stage="schema",
            provenance=dict(validation.provenance),
        )

    bore_d = int(validation.normalized["bore_d"])
    raw_params = _extract_params_dict(raw_schema_payload)

    ir_doc = _build_ir_document(
        raw_params=raw_params,
        normalized=validation.normalized,
        provenance=validation.provenance,
        bore_d=bore_d,
        schema_version=validation.schema_version,
        adapter_version=adapter_version,
    )

    ir_json = json.dumps(ir_doc, ensure_ascii=False, separators=(",", ":"))
    ir_errors = validate_ir(ir_json.encode("utf-8"))
    if ir_errors:
        return AdapterResult(
            status="ir_invalid",
            ir_document=ir_doc,
            ir_json=ir_json,
            schema_version=validation.schema_version,
            errors=[
                {
                    "code": e.code,
                    "stage": e.stage,
                    "message": e.message,
                    "field": e.field,
                }
                for e in ir_errors
            ],
            stage="ir_validation",
            provenance=dict(validation.provenance),
        )

    return AdapterResult(
        status="accepted",
        ir_document=ir_doc,
        ir_json=ir_json,
        schema_version=validation.schema_version,
        errors=[],
        stage="ir_validation",
        provenance=dict(validation.provenance),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_params_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the raw parameters sub-dict from a formal envelope or flat dict."""
    if "parameters" in payload:
        params = payload["parameters"]
        return params if isinstance(params, dict) else {}
    return {k: v for k, v in payload.items()
            if k not in {"schema_version", "family_id"}}


def _build_parameters(
    raw_params: dict[str, Any],
    normalized: dict[str, int | float],
    provenance: dict[str, str],
    bore_d: int,
) -> list[dict[str, Any]]:
    """Build the IR parameters list (fixed order per mapping.md § 2)."""
    catalog_ref = f"GN705.catalog_row:bore_d={bore_d}"
    result: list[dict[str, Any]] = []

    for param_id in _PARAMETER_ORDER:
        norm_value = normalized[param_id]
        source = provenance[param_id]

        if param_id == "second_screw":
            type_ = "integer"
            unit = "1"
        else:
            type_ = "number"
            unit = "mm"

        item: dict[str, Any] = {
            "parameter_id": param_id,
            "type": type_,
            "unit": unit,
            "value": norm_value,
        }

        # Preserve original input for user_explicit parameters.
        if source == "user_explicit":
            raw_val = raw_params.get(param_id)
            if param_id == "second_screw":
                item["input"] = {"value": int(norm_value), "unit": "1"}
            elif isinstance(raw_val, dict) and "value" in raw_val and "unit" in raw_val:
                # Measurement object — preserve original value and unit.
                item["input"] = {"value": raw_val["value"], "unit": raw_val["unit"]}
            else:
                # Bare number — input.unit is mm per the mapping spec.
                item["input"] = {"value": norm_value, "unit": "mm"}

        # Source and source_ref.
        item["source"] = source
        if source == "user_explicit":
            item["source_ref"] = f"CAD-003.field:{param_id}"
        elif source == "catalog_derived":
            item["source_ref"] = catalog_ref
            item["catalog_row_key"] = f"bore_d={bore_d}"
        else:  # rule_derived (second_screw only)
            item["source_ref"] = "CAD-003.rule:second_screw_threshold"

        # bore_d always carries catalog_row_key (it IS the catalog selector).
        if param_id == "bore_d":
            item["catalog_row_key"] = f"bore_d={bore_d}"

        result.append(item)

    return result


# ---------------------------------------------------------------------------
# Canonical fixed graph (mapping.md §§ 3–4, frozen for set_screw_shaft_collar v0)
# ---------------------------------------------------------------------------
# These structures never change between bore_d values; only the parameters
# list above carries actual numeric values.


def _canonical_nodes() -> list[dict[str, Any]]:
    """Return the seven-node fixed graph for set_screw_shaft_collar v0.

    Matches _canonical_node_contracts() in src/cad_compilation/ir.py exactly,
    extended with node_type, ordinal, outputs, refs and enabled_if null
    markers required by the IR JSON schema.
    """
    _r = lambda pid: {"kind": "parameter_ref", "parameter_id": pid}
    _lit = lambda v, u: {"kind": "literal", "value": v, "unit": u}
    _formula = lambda fid, **args: {"kind": "formula", "formula_id": fid, "args": args}
    _half_diff = lambda: _formula("half_difference",
                                  outer_d=_r("outer_d"), bore_d=_r("bore_d"))
    _over = _lit(0.5, "mm")
    _wall = _half_diff()
    _collar_chamfer = _formula("collar_chamfer",
                               bore_d=_r("bore_d"), wall=_half_diff(), width=_r("width"))

    def _hole_inputs(angle_deg: int) -> dict[str, Any]:
        return {
            "thread_d": _r("screw_d"),
            "pitch": {"kind": "lookup", "table_id": "iso261.coarse_pitch_mm",
                      "key": _r("screw_d")},
            "angle_deg": _lit(angle_deg, "deg"),
            "over": _lit(0.5, "mm"),
            "wall": _half_diff(),
            "hole_len": _formula("add",
                                 left=_half_diff(),
                                 right=_formula("multiply",
                                               value=_lit(0.5, "mm"),
                                               factor=_lit(2, "1"))),
            "z_in": _lit(0.5, "mm"),
            "z_out": _formula("add",
                              left=_lit(0.5, "mm"),
                              right=_half_diff()),
            "radial_offset": _formula("subtract",
                                      left=_formula("half", value=_r("bore_d")),
                                      right=_lit(0.5, "mm")),
            "axial": _formula("multiply", width=_r("width"), factor=_lit(0.5, "1")),
        }

    _placement = {
        "cutter_local_axis": "Z",
        "transform_order": "column_vector_left_multiply",
        "transforms": [
            {"operation": "rotate", "frame": "cutter_local",
             "pivot": [0, 0, 0], "axis": [0, 1, 0], "degrees": 90},
            {"operation": "translate", "frame": "world",
             "vector": ["radial_offset", 0, "axial"]},
            {"operation": "rotate", "frame": "world",
             "pivot": [0, 0, 0], "axis": [0, 0, 1], "angle_ref": "angle_deg"},
        ],
    }
    _hole_props = {
        "thread_model": "revolved_ring_approximation",
        "helical_thread_supported": False,
        "placement_model": "radial_bore_breakout",
        "placement": _placement,
    }
    _secondary_cond = {"kind": "parameter_equals",
                       "parameter_id": "second_screw", "equals": 1}

    return [
        {
            "node_id": "n0.catalog.resolve",
            "node_type": "catalog.resolve",
            "ordinal": 0,
            "enabled_if": None,
            "depends_on": [],
            "inputs": {"bore_d": _r("bore_d")},
            "outputs": [{"output_id": "resolved_parameters",
                         "kind": "resolved_parameters"}],
            "refs": [{"kind": "parameter", "id": "bore_d"},
                     {"kind": "catalog", "id": "gn705.gn705_metric_v0"}],
            "properties": {
                "catalog_key": "bore_d",
                "resolved_fields": ["outer_d", "width", "screw_d",
                                    "screw_len", "second_screw"],
            },
        },
        {
            "node_id": "n1.collar.revolve",
            "node_type": "shape.revolve_profile",
            "ordinal": 1,
            "depends_on": ["n0.catalog.resolve"],
            "inputs": {
                "bore_d": _r("bore_d"),
                "outer_d": _r("outer_d"),
                "width": _r("width"),
                "chamfer": _collar_chamfer,
            },
            "outputs": [{"output_id": "collar_base", "kind": "shape"}],
            "refs": [
                {"kind": "parameter", "id": "bore_d"},
                {"kind": "parameter", "id": "outer_d"},
                {"kind": "parameter", "id": "width"},
                {"kind": "formula", "id": "collar_chamfer"},
            ],
            "properties": {
                "profile_kind": "chamfered_annulus",
                "axis": "Z",
                "revolve_degrees": 360,
                "workplane": "XZ",
                "axis_local": [0, 1, 0],
            },
        },
        {
            "node_id": "n2.hole.primary",
            "node_type": "feature.tapped_hole_cutter",
            "ordinal": 2,
            "depends_on": ["n1.collar.revolve"],
            "inputs": _hole_inputs(0),
            "outputs": [{"output_id": "hole_cutter_primary", "kind": "cutter"}],
            "refs": [
                {"kind": "parameter", "id": "screw_d"},
                {"kind": "catalog", "id": "iso261.coarse_pitch_mm"},
            ],
            "properties": _hole_props,
        },
        {
            "node_id": "n3.cut.primary",
            "node_type": "boolean.cut",
            "ordinal": 3,
            "depends_on": ["n1.collar.revolve", "n2.hole.primary"],
            "inputs": {
                "base": {"kind": "node_output_ref", "output_id": "collar_base"},
                "tool": {"kind": "node_output_ref",
                         "output_id": "hole_cutter_primary"},
            },
            "outputs": [{"output_id": "solid_after_primary",
                         "kind": "solid_candidate"}],
            "refs": [
                {"kind": "node_output", "id": "collar_base"},
                {"kind": "node_output", "id": "hole_cutter_primary"},
            ],
            "properties": {
                "base_ref": "collar_base",
                "tool_ref": "hole_cutter_primary",
                "operation": "difference",
            },
        },
        {
            "node_id": "n4.hole.secondary",
            "node_type": "feature.tapped_hole_cutter",
            "ordinal": 4,
            "enabled_if": _secondary_cond,
            "depends_on": ["n3.cut.primary"],
            "inputs": _hole_inputs(135),
            "outputs": [{"output_id": "hole_cutter_secondary", "kind": "cutter"}],
            "refs": [
                {"kind": "parameter", "id": "screw_d"},
                {"kind": "parameter", "id": "second_screw"},
                {"kind": "catalog", "id": "iso261.coarse_pitch_mm"},
            ],
            "properties": _hole_props,
        },
        {
            "node_id": "n5.cut.secondary",
            "node_type": "boolean.cut",
            "ordinal": 5,
            "enabled_if": _secondary_cond,
            "depends_on": ["n3.cut.primary", "n4.hole.secondary"],
            "inputs": {
                "base": {"kind": "node_output_ref",
                         "output_id": "solid_after_primary"},
                "tool": {"kind": "node_output_ref",
                         "output_id": "hole_cutter_secondary"},
            },
            "outputs": [{"output_id": "solid_after_secondary",
                         "kind": "solid_candidate"}],
            "refs": [
                {"kind": "node_output", "id": "solid_after_primary"},
                {"kind": "node_output", "id": "hole_cutter_secondary"},
            ],
            "properties": {
                "base_ref": "solid_after_primary",
                "tool_ref": "hole_cutter_secondary",
                "operation": "difference",
            },
        },
        {
            "node_id": "n6.result",
            "node_type": "result.single_solid",
            "ordinal": 6,
            "depends_on": ["n3.cut.primary", "n5.cut.secondary"],
            "inputs": {"second_screw": _r("second_screw")},
            "outputs": [{"output_id": "part", "kind": "part"}],
            "refs": [
                {"kind": "node_output", "id": "solid_after_primary"},
                {"kind": "node_output", "id": "solid_after_secondary"},
            ],
            "properties": {
                "select_if_zero": "solid_after_primary",
                "select_if_one": "solid_after_secondary",
            },
        },
    ]


_CANONICAL_CONSTRAINTS: list[dict[str, Any]] = [
    {
        "constraint_id": "catalog_row_coupling",
        "kind": "equality",
        "fields": ["bore_d", "outer_d", "screw_d", "screw_len", "width"],
        "expression": "(outer_d, screw_d, screw_len, width) = catalog[bore_d]",
        "enforced_at": "preflight",
        "source_ref": "CAD-003.rule:catalog_row_coupling",
    },
    {
        "constraint_id": "second_screw_threshold",
        "kind": "iff",
        "fields": ["bore_d", "second_screw"],
        "expression": "second_screw == 1 iff bore_d > 70",
        "enforced_at": "preflight",
        "source_ref": "CAD-003.rule:second_screw_threshold",
    },
    {
        "constraint_id": "outer_d_gt_bore_d",
        "kind": "inequality",
        "fields": ["outer_d", "bore_d"],
        "expression": "outer_d > bore_d",
        "enforced_at": "preflight",
        "source_ref": "CAD-003.rule:outer_d_gt_bore_d",
    },
    {
        "constraint_id": "wall_thickness",
        "kind": "inequality",
        "fields": ["outer_d", "bore_d", "screw_d"],
        "expression": "(outer_d - bore_d) / 2 > 0.65 * screw_d",
        "enforced_at": "preflight",
        "source_ref": "CAD-003.rule:wall_thickness",
    },
    {
        "constraint_id": "axial_support",
        "kind": "inequality",
        "fields": ["width", "screw_d"],
        "expression": "width >= 1.45 * screw_d",
        "enforced_at": "preflight",
        "source_ref": "CAD-003.rule:axial_support",
    },
    {
        "constraint_id": "single_solid_target",
        "kind": "postcondition",
        "fields": [],
        "expression": "solid_count == 1 and is_valid == true",
        "enforced_at": "post_geometry",
        "source_ref": "IR-001.validation_contract",
    },
    {
        "constraint_id": "step_roundtrip",
        "kind": "roundtrip",
        "fields": [],
        "expression": "STEP export and readback succeed with matching normalized metrics",
        "enforced_at": "step_readback",
        "source_ref": "IR-001.validation_contract",
    },
]

_CANONICAL_EXECUTION: dict[str, Any] = {
    "preflight_required_before_build": True,
    "node_order": "ordinal_topological",
    "unknown_operation_policy": "reject",
    "tolerance_profile": _COMPARISON_POLICY,
}

_CANONICAL_VALIDATION_CONTRACT: dict[str, Any] = {
    "expected_solids": 1,
    "require_valid": True,
    "step_roundtrip_required": True,
    "byte_hash_policy": "informational_only",
    "metrics": [
        "solid_count", "shell_count", "face_count", "edge_count",
        "vertex_count", "is_valid", "volume_mm3", "bbox_mm",
        "face_area_signature", "edge_length_signature",
    ],
}


def _build_ir_document(
    raw_params: dict[str, Any],
    normalized: dict[str, int | float],
    provenance: dict[str, str],
    bore_d: int,
    schema_version: str,
    adapter_version: str,
) -> dict[str, Any]:
    return {
        "ir_version": _IR_VERSION,
        "ir_revision": _IR_REVISION,
        "status": "accepted",
        "family": {
            "family_id": "set_screw_shaft_collar",
            "directory_id": "set_screw_shaft_collar",
            "extension_namespace": "family.set_screw_shaft_collar.v0",
            "family_data": {
                "catalog_table_id": "gn705.gn705_metric_v0",
                "profile_kind": "chamfered_annulus",
                "thread_model": "revolved_ring_approximation",
                "helical_thread_supported": False,
                "hole_angles_deg": [0, 135],
                "second_hole_condition": "second_screw == 1",
            },
        },
        "source": {
            "schema_version": schema_version,
            "source_system": "BenchCAD",
            "source_commit": _SOURCE_COMMIT,
            # JSON schema requires these two const values verbatim.
            # adapter_version is tracked in ADAPTER_VERSION module constant
            # for external callers; the schema const pins it at 0.1.0.
            "adapter_id": "benchcad.set_screw_shaft_collar",
            "adapter_version": "0.1.0",
            "snapshot_status": _SNAPSHOT_STATUS,
        },
        "parameters": _build_parameters(raw_params, normalized, provenance, bore_d),
        "nodes": _canonical_nodes(),
        "constraints": _CANONICAL_CONSTRAINTS,
        "execution": _CANONICAL_EXECUTION,
        "validation_contract": _CANONICAL_VALIDATION_CONTRACT,
    }
