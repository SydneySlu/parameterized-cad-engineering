"""Small typed interpreter for the registered IR expressions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import fail

PITCH_MM = {3: 0.5, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25, 10: 1.5, 12: 1.75}


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Expression value must be a finite number.", field)
    return float(value)


def evaluate(expr: dict[str, Any], parameters: dict[str, Quantity], outputs: dict[str, Any] | None = None, field: str = "expression") -> Quantity:
    kind = expr.get("kind")
    if kind == "parameter_ref":
        key = expr["parameter_id"]
        if key not in parameters:
            fail("IR_REFERENCE_NOT_FOUND", "semantic", "Parameter reference was not found.", field)
        return parameters[key]
    if kind == "node_output_ref":
        key = expr["output_id"]
        if outputs is None or key not in outputs:
            fail("IR_REFERENCE_NOT_FOUND", "semantic", "Node output reference was not produced.", field)
        return Quantity(float(len(outputs[key]) if isinstance(outputs[key], (list, tuple)) else 1), "1")
    if kind == "literal":
        unit = expr.get("unit")
        if unit not in {"mm", "deg", "1"}:
            fail("IR_UNIT_MISMATCH", "semantic", "Literal unit must be mm, deg, or 1.", field)
        return Quantity(_finite(expr.get("value"), field), unit)
    if kind == "lookup":
        if expr.get("table_id") != "iso261.coarse_pitch_mm":
            fail("IR_UNREGISTERED_LOOKUP", "semantic", "Lookup table is not registered.", field)
        key = evaluate(expr["key"], parameters, outputs, f"{field}.key")
        if key.unit != "mm" or int(key.value) != key.value or int(key.value) not in PITCH_MM:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Thread diameter has no registered ISO 261 coarse pitch.", field)
        return Quantity(PITCH_MM[int(key.value)], "mm")
    if kind != "formula":
        fail("IR_EXECUTION_STRING_FORBIDDEN", "semantic", "Unrecognized expression kind.", field)
    formula = expr.get("formula_id")
    args = expr.get("args")
    if not isinstance(args, dict):
        fail("IR_FORMULA_ARGUMENT_ERROR", "semantic", "Formula args must be an object.", field)
    signatures = {
        "half_difference": {"outer_d", "bore_d"}, "half": {"value"},
        "multiply": {"value", "factor"}, "add": {"left", "right"},
        "subtract": {"left", "right"}, "min": {"values"}, "max": {"values"},
        "collar_chamfer": {"bore_d", "wall", "width"},
        "thread_minor_radius": {"thread_d", "pitch"},
        "thread_countersink_radius": {"thread_d", "pitch"},
        "thread_turn_count": {"z1", "z0", "pitch"},
    }
    expected = signatures.get(formula)
    if expected is None:
        fail("IR_UNREGISTERED_FORMULA", "semantic", f"Formula {formula!r} is not registered.", field)
    if formula == "multiply" and set(args) == {"width", "factor"}:
        # Frozen examples use the named axial parameter; evaluate it as the
        # same registered length-times-scalar operation.
        args = {"value": args["width"], "factor": args["factor"]}
    if set(args) != expected:
        fail("IR_FORMULA_ARGUMENT_ERROR", "semantic", f"Formula {formula} requires exactly {sorted(expected)}.", field)
    if formula in {"min", "max"}:
        raw = args["values"]
        if not isinstance(raw, list) or len(raw) < 2:
            fail("IR_FORMULA_ARGUMENT_ERROR", "semantic", f"Formula {formula} needs at least two values.", field)
        values = [evaluate(item, parameters, outputs, field) for item in raw]
        if len({item.unit for item in values}) != 1:
            fail("IR_UNIT_MISMATCH", "semantic", "min/max values must have matching units.", field)
        return Quantity((min if formula == "min" else max)(item.value for item in values), values[0].unit)
    values = {name: evaluate(item, parameters, outputs, f"{field}.{name}") for name, item in args.items()}
    units = {name: item.unit for name, item in values.items()}
    if formula == "half_difference":
        if units["outer_d"] != "mm" or units["bore_d"] != "mm":
            fail("IR_UNIT_MISMATCH", "semantic", "half_difference requires lengths.", field)
        value, unit = (values["outer_d"].value - values["bore_d"].value) / 2, "mm"
    elif formula == "half":
        if units["value"] not in {"mm", "1"}:
            fail("IR_UNIT_MISMATCH", "semantic", "half accepts a length or scalar.", field)
        value, unit = values["value"].value / 2, units["value"]
    elif formula == "multiply":
        a, b = units["value"], units["factor"]
        if a == b == "mm":
            fail("IR_UNIT_MISMATCH", "semantic", "Length times length is unsupported.", field)
        if a not in {"mm", "1"} or b not in {"mm", "1"}:
            fail("IR_UNIT_MISMATCH", "semantic", "Unsupported multiply units.", field)
        value = values["value"].value * values["factor"].value
        unit = "mm" if "mm" in (a, b) else "1"
    elif formula in {"add", "subtract"}:
        a, b = units["left"], units["right"]
        if a != b:
            fail("IR_UNIT_MISMATCH", "semantic", "Addition/subtraction requires matching units.", field)
        value = values["left"].value + values["right"].value if formula == "add" else values["left"].value - values["right"].value
        unit = a
    elif formula == "collar_chamfer":
        if set(units.values()) != {"mm"}:
            fail("IR_UNIT_MISMATCH", "semantic", "collar_chamfer requires lengths.", field)
        value = min(max(0.25, 0.012 * values["bore_d"].value), 0.18 * values["wall"].value, 0.08 * values["width"].value)
        unit = "mm"
        if values["wall"].value <= 0 or values["width"].value <= 0 or value <= 0:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Chamfer dimensions must be positive.", field)
    elif formula == "thread_minor_radius":
        d, pitch = values["thread_d"], values["pitch"]
        if d.unit != "mm" or pitch.unit != "mm":
            fail("IR_UNIT_MISMATCH", "semantic", "Thread dimensions must use mm.", field)
        value, unit = d.value / 2 - 0.5413 * pitch.value, "mm"
        if d.value <= 0 or pitch.value <= 0 or value <= 0:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Thread minor radius must be positive.", field)
    elif formula == "thread_countersink_radius":
        d, pitch = values["thread_d"], values["pitch"]
        if d.unit != "mm" or pitch.unit != "mm" or d.value <= 0 or pitch.value <= 0:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Thread countersink inputs must be positive lengths.", field)
        value, unit = d.value / 2 + 0.1 * pitch.value, "mm"
    else:  # thread_turn_count
        z1, z0, pitch = values["z1"], values["z0"], values["pitch"]
        if any(q.unit != "mm" for q in (z1, z0, pitch)) or pitch.value <= 0 or z1.value < z0.value:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Thread turn count requires z1 >= z0 and positive pitch in mm.", field)
        value, unit = max(1, int((z1.value - z0.value) / pitch.value)), "1"
        if value > 2**31 - 1:
            fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Thread turn count exceeds signed 32-bit range.", field)
    if not math.isfinite(value):
        fail("IR_FORMULA_DOMAIN_ERROR", "semantic", "Formula result must be finite.", field)
    return Quantity(float(value), unit)
