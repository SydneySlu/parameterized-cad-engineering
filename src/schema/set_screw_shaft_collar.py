"""Schema v0 and pure parameter rules for ``set_screw_shaft_collar``.

This module is deliberately independent of BenchCAD and of any CAD kernel.
It defines the JSON boundary that must be checked before a future builder is
called.  The catalog values are copied from DATA-003's fixed source commit;
they are not a claim that the schema is valid for another family.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import json
import math
from typing import Any, Mapping, Sequence


FAMILY_ID = "set_screw_shaft_collar"
SCHEMA_VERSION = "set_screw_shaft_collar.v0"
SOURCE_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"
CANONICAL_LENGTH_UNIT = "mm"

# d1, d2, screw major diameter, screw length, b.  This is the complete table
# observed in designs/set_screw_shaft_collar/spec.py at SOURCE_COMMIT.
CATALOG_ROWS: tuple[tuple[int, int, int, int, int], ...] = (
    (5, 10, 3, 4, 6),
    (6, 12, 4, 5, 8),
    (8, 16, 4, 6, 8),
    (10, 20, 5, 8, 10),
    (12, 22, 6, 8, 12),
    (16, 28, 6, 8, 12),
    (20, 32, 6, 8, 14),
    (24, 40, 8, 12, 16),
    (30, 45, 8, 10, 16),
    (35, 56, 8, 12, 16),
    (40, 63, 10, 16, 18),
    (50, 80, 10, 16, 18),
    (60, 90, 10, 16, 20),
    (70, 100, 10, 20, 20),
    (80, 110, 12, 20, 22),
)

_ROW_BY_BORE = {row[0]: row for row in CATALOG_ROWS}
_LENGTH_FIELDS = ("bore_d", "outer_d", "width", "screw_d", "screw_len")
_KNOWN_FIELDS = frozenset(
    {"bore_d", "outer_d", "width", "screw_d", "screw_len", "second_screw"}
)
_UNIT_FACTORS = {
    "mm": Decimal("1"),
    "millimeter": Decimal("1"),
    "millimeters": Decimal("1"),
    "cm": Decimal("10"),
    "centimeter": Decimal("10"),
    "centimeters": Decimal("10"),
    "m": Decimal("1000"),
    "meter": Decimal("1000"),
    "meters": Decimal("1000"),
    "in": Decimal("25.4"),
    "inch": Decimal("25.4"),
    "inches": Decimal("25.4"),
}


@dataclass(frozen=True)
class FieldSpec:
    """Human- and machine-readable contract for one input/resolved field."""

    name: str
    type: str
    unit: str
    source: str
    required: bool
    missing_behavior: str
    allowed_range: tuple[float | int, float | int] | None = None
    allowed_values: tuple[float | int, ...] | None = None
    derived_from: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.allowed_range is not None:
            value["allowed_range"] = list(self.allowed_range)
        if self.allowed_values is not None:
            value["allowed_values"] = list(self.allowed_values)
        value["derived_from"] = list(self.derived_from)
        return value


@dataclass(frozen=True)
class RuleViolation:
    """Stable, serializable validation error."""

    code: str
    fields: tuple[str, ...]
    message: str
    stage: str = "schema"

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["fields"] = list(self.fields)
        return value


@dataclass(frozen=True)
class ValidationResult:
    """Result of resolving and checking a parameter JSON payload."""

    ok: bool
    schema_version: str
    family_id: str
    normalized: dict[str, int | float] | None
    provenance: dict[str, str]
    errors: tuple[RuleViolation, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "schema_version": self.schema_version,
            "family_id": self.family_id,
            "normalized": self.normalized,
            "provenance": self.provenance,
            "errors": [error.as_dict() for error in self.errors],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, indent=indent)

    @classmethod
    def from_json(cls, document: str | bytes) -> "ValidationResult":
        """Deserialize a previously serialized result without re-running rules."""

        value = json.loads(document)
        if not isinstance(value, Mapping):
            raise ValueError("serialized validation result must be a JSON object")
        errors = tuple(
            RuleViolation(
                code=item["code"],
                fields=tuple(item["fields"]),
                message=item["message"],
                stage=item.get("stage", "schema"),
            )
            for item in value.get("errors", [])
        )
        return cls(
            ok=bool(value["ok"]),
            schema_version=value["schema_version"],
            family_id=value["family_id"],
            normalized=value.get("normalized"),
            provenance=dict(value.get("provenance", {})),
            errors=errors,
        )


def _unique_values(index: int) -> tuple[int, ...]:
    return tuple(sorted({row[index] for row in CATALOG_ROWS}))


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="bore_d",
        type="number",
        unit="mm",
        source="JW Winco GN 705 metric table, column d1 H8; DATA-003 source commit",
        required=True,
        missing_behavior="reject: critical catalog selector is absent",
        allowed_range=(5, 80),
        allowed_values=tuple(row[0] for row in CATALOG_ROWS),
    ),
    FieldSpec(
        name="outer_d",
        type="number",
        unit="mm",
        source="JW Winco GN 705 metric table, column d2",
        required=False,
        missing_behavior="derive exact value from the selected bore_d catalog row",
        allowed_range=(10, 110),
        allowed_values=_unique_values(1),
        derived_from=("bore_d",),
    ),
    FieldSpec(
        name="width",
        type="number",
        unit="mm",
        source="JW Winco GN 705 metric table, column b js14",
        required=False,
        missing_behavior="derive exact value from the selected bore_d catalog row",
        allowed_range=(6, 22),
        allowed_values=_unique_values(4),
        derived_from=("bore_d",),
    ),
    FieldSpec(
        name="screw_d",
        type="number",
        unit="mm",
        source="JW Winco GN 705 metric table, column d3 major diameter",
        required=False,
        missing_behavior="derive exact value from the selected bore_d catalog row",
        allowed_range=(3, 12),
        allowed_values=_unique_values(2),
        derived_from=("bore_d",),
    ),
    FieldSpec(
        name="screw_len",
        type="number",
        unit="mm",
        source="JW Winco GN 705 metric table, column d3 length after x",
        required=False,
        missing_behavior="derive exact value from the selected bore_d catalog row",
        allowed_range=(4, 20),
        allowed_values=_unique_values(3),
        derived_from=("bore_d",),
    ),
    FieldSpec(
        name="second_screw",
        type="integer",
        unit="",
        source="JW Winco GN 705 note: second grub screw for d1 > 70 mm",
        required=False,
        missing_behavior="derive 1 iff bore_d > 70; otherwise derive 0",
        allowed_range=(0, 1),
        allowed_values=(0, 1),
        derived_from=("bore_d",),
    ),
)


def schema_descriptor() -> dict[str, Any]:
    """Return the versioned, JSON-serializable field contract.

    This is a project-level descriptor rather than a claim of cross-family
    standardization.  ``json_schema`` is included for consumers that want a
    conventional JSON Schema shape, while coupling and wall rules remain in
    :func:`validate_parameters`.
    """

    return {
        "schema_version": SCHEMA_VERSION,
        "family_id": FAMILY_ID,
        "source_commit": SOURCE_COMMIT,
        "canonical_length_unit": CANONICAL_LENGTH_UNIT,
        "input_contract": {
            "formal_envelope_required": ["schema_version", "family_id", "parameters"],
            "parameter_required": ["bore_d"],
            "parameter_optional": ["outer_d", "width", "screw_d", "screw_len", "second_screw"],
            "unknown_fields": "reject",
            "measurement_encoding": "bare numbers use canonical mm; {value, unit} is normalized to mm",
            "python_compatibility": "validate_parameters accepts a flat parameter object and an envelope with omitted metadata; these are not the formal external JSON protocol",
        },
        "fields": [field.as_dict() for field in FIELD_SPECS],
        "relations": [
            {
                "id": "catalog_row_coupling",
                "expression": "(outer_d, screw_d, screw_len, width) = catalog_row[bore_d]",
                "source": "DATA-003 audit of spec.py::CATALOG_ROWS/refine",
            },
            {
                "id": "second_screw_threshold",
                "expression": "second_screw == 1 iff bore_d > 70",
                "source": "DATA-003 audit of spec.py::check and GN 705 note",
            },
            {
                "id": "wall_thickness",
                "expression": "(outer_d - bore_d) / 2 > 0.65 * screw_d",
                "source": "DATA-003 audit of spec.py::check",
            },
            {
                "id": "axial_support",
                "expression": "width >= 1.45 * screw_d",
                "source": "DATA-003 audit of spec.py::check",
            },
        ],
        "json_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://parameterized-cad-engineering.invalid/schema/set_screw_shaft_collar.v0.json",
            "title": "set_screw_shaft_collar parameter envelope",
            "type": "object",
            "additionalProperties": False,
            "required": ["schema_version", "family_id", "parameters"],
            "properties": {
                "schema_version": {"const": SCHEMA_VERSION},
                "family_id": {"const": FAMILY_ID},
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["bore_d"],
                    "properties": {
                        field.name: _json_schema_property(field)
                        for field in FIELD_SPECS
                    },
                },
            },
        },
        "normalized_json_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://parameterized-cad-engineering.invalid/schema/set_screw_shaft_collar.v0.normalized.json",
            "title": "set_screw_shaft_collar normalized parameter object (internal compatibility)",
            "type": "object",
            "additionalProperties": False,
            "required": ["bore_d"],
            "properties": {
                field.name: _json_schema_property(field, allow_measurement=False)
                for field in FIELD_SPECS
            },
        },
    }


def _error(code: str, fields: Sequence[str], message: str) -> RuleViolation:
    return RuleViolation(code=code, fields=tuple(fields), message=message)


def _json_schema_property(field: FieldSpec, *, allow_measurement: bool = True) -> dict[str, Any]:
    value: dict[str, Any] = {
        "type": "integer" if field.type == "integer" else "number",
    }
    if field.allowed_range is not None:
        value["minimum"], value["maximum"] = field.allowed_range
    if field.allowed_values is not None:
        value["enum"] = list(field.allowed_values)
    if field.unit:
        value["unit"] = field.unit
    if not allow_measurement or not field.unit:
        return value

    # The object form deliberately checks only the measurement shape.  Unit
    # conversion and catalog choices occur in Python, because JSON Schema
    # cannot express that e.g. 2 cm must become the catalog value 20 mm.
    measurement = {
        "type": "object",
        "additionalProperties": False,
        "required": ["value", "unit"],
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": sorted(_UNIT_FACTORS)},
        },
    }
    return {"oneOf": [value, measurement]}


def _as_decimal(value: Any, field: str, errors: list[RuleViolation]) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        errors.append(_error("TYPE_ERROR", [field], f"{field} must be a finite number"))
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(_error("TYPE_ERROR", [field], f"{field} must be a finite number"))
        return None
    if not parsed.is_finite() or (isinstance(value, float) and not math.isfinite(value)):
        errors.append(_error("TYPE_ERROR", [field], f"{field} must be a finite number"))
        return None
    return parsed


def _normalize_length(value: Any, field: str, errors: list[RuleViolation]) -> Decimal | None:
    unit = CANONICAL_LENGTH_UNIT
    raw = value
    if isinstance(value, Mapping):
        if "value" not in value:
            errors.append(_error("UNIT_VALUE_MISSING", [field], f"{field} measurement needs a value"))
            return None
        raw = value["value"]
        unit = value.get("unit")
        if not isinstance(unit, str) or unit.lower() not in _UNIT_FACTORS:
            errors.append(_error("UNSUPPORTED_UNIT", [field], f"{field} unit must be a supported length unit"))
            return None
        unit = unit.lower()
    parsed = _as_decimal(raw, field, errors)
    return parsed * _UNIT_FACTORS[unit] if parsed is not None else None


def _canonical_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _payload_fields(payload: Mapping[str, Any], errors: list[RuleViolation]) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        errors.append(_error("PAYLOAD_TYPE_ERROR", ["parameters"], "payload must be a JSON object"))
        return None
    envelope_markers = {"schema_version", "family_id", "parameters"}
    if envelope_markers.intersection(payload):
        envelope_allowed = {"schema_version", "family_id", "parameters"}
        unknown_envelope = sorted(set(payload) - envelope_allowed)
        if unknown_envelope:
            errors.append(_error("UNKNOWN_FIELD", unknown_envelope, "unknown envelope field(s)"))
        if "parameters" not in payload:
            errors.append(_error("MISSING_PARAMETERS", ["parameters"], "formal envelope requires parameters"))
            return None
        version = payload.get("schema_version")
        if version is not None and version != SCHEMA_VERSION:
            errors.append(_error("SCHEMA_VERSION_MISMATCH", ["schema_version"], f"expected {SCHEMA_VERSION}"))
        family = payload.get("family_id")
        if family is not None and family != FAMILY_ID:
            errors.append(_error("FAMILY_ID_MISMATCH", ["family_id"], f"expected {FAMILY_ID}"))
        fields = payload["parameters"]
        if not isinstance(fields, Mapping):
            errors.append(_error("PAYLOAD_TYPE_ERROR", ["parameters"], "parameters must be a JSON object"))
            return None
        return fields
    return payload


def resolve_parameters(payload: Mapping[str, Any]) -> ValidationResult:
    """Normalize, derive, and validate a parameter payload.

    The returned ``normalized`` values are safe to pass to a future builder
    only after checking ``ok``.  No builder is called here.
    """

    errors: list[RuleViolation] = []
    fields = _payload_fields(payload, errors)
    if fields is None:
        return ValidationResult(False, SCHEMA_VERSION, FAMILY_ID, None, {}, tuple(errors))

    unknown = sorted(set(fields) - _KNOWN_FIELDS)
    if unknown:
        errors.append(_error("UNKNOWN_FIELD", unknown, "unknown parameter field(s)"))
    if "bore_d" not in fields or fields.get("bore_d") is None:
        errors.append(_error("MISSING_REQUIRED", ["bore_d"], "bore_d is the required catalog selector"))
        return ValidationResult(False, SCHEMA_VERSION, FAMILY_ID, None, {}, tuple(errors))

    normalized: dict[str, int | float] = {}
    provenance: dict[str, str] = {}
    parsed: dict[str, Decimal] = {}
    for field in _LENGTH_FIELDS:
        if field not in fields or fields[field] is None:
            continue
        value = _normalize_length(fields[field], field, errors)
        if value is not None:
            parsed[field] = value
            normalized[field] = _canonical_number(value)
            provenance[field] = "user_explicit"

    bore = parsed.get("bore_d")
    if bore is None:
        return ValidationResult(False, SCHEMA_VERSION, FAMILY_ID, None, provenance, tuple(errors))
    if bore != bore.to_integral_value() or int(bore) not in _ROW_BY_BORE:
        errors.append(_error("CATALOG_CHOICE", ["bore_d"], "bore_d must be one of the 15 GN 705 catalog choices"))
        return ValidationResult(False, SCHEMA_VERSION, FAMILY_ID, None, provenance, tuple(errors))

    bore_i = int(bore)
    row = _ROW_BY_BORE[bore_i]
    expected = {"outer_d": row[1], "screw_d": row[2], "screw_len": row[3], "width": row[4]}
    for field, expected_value in expected.items():
        expected_decimal = Decimal(expected_value)
        if field not in parsed:
            parsed[field] = expected_decimal
            normalized[field] = expected_value
            provenance[field] = "catalog_derived"
        elif parsed[field] != expected_decimal:
            errors.append(
                _error(
                    "CATALOG_MISMATCH",
                    [field, "bore_d"],
                    f"{field}={normalized[field]} does not match the catalog row selected by bore_d={bore_i} (expected {expected_value})",
                )
            )

    expected_second = 1 if bore_i > 70 else 0
    if "second_screw" not in fields or fields.get("second_screw") is None:
        second = expected_second
        provenance["second_screw"] = "rule_derived"
    else:
        raw_second = fields["second_screw"]
        if isinstance(raw_second, bool) or not isinstance(raw_second, int):
            errors.append(_error("TYPE_ERROR", ["second_screw"], "second_screw must be integer 0 or 1"))
            second = None
        else:
            second = raw_second
            if second not in (0, 1):
                errors.append(_error("OPTION_ERROR", ["second_screw"], "second_screw must be 0 or 1"))
                second = None
            else:
                provenance["second_screw"] = "user_explicit"
    if second is not None:
        normalized["second_screw"] = second
        if second != expected_second:
            errors.append(
                _error(
                    "SECOND_SCREW_CONSTRAINT",
                    ["second_screw", "bore_d"],
                    f"second_screw must be {expected_second} when bore_d={bore_i}; the GN 705 note applies iff bore_d > 70",
                )
            )

    # These are the DATA-003 spec.check rules, evaluated before a future build.
    if all(name in parsed for name in ("outer_d", "bore_d", "screw_d")):
        wall = (parsed["outer_d"] - parsed["bore_d"]) / Decimal(2)
        if wall <= 0:
            errors.append(_error("OUTER_DIAMETER_NOT_GREATER", ["outer_d", "bore_d"], "outer_d must be greater than bore_d"))
        if wall <= parsed["screw_d"] * Decimal("0.65"):
            errors.append(
                _error(
                    "WALL_THICKNESS_TOO_SMALL",
                    ["outer_d", "bore_d", "screw_d"],
                    "wall thickness must be strictly greater than 0.65 * screw_d",
                )
            )
    if all(name in parsed for name in ("width", "screw_d")) and parsed["width"] < parsed["screw_d"] * Decimal("1.45"):
        errors.append(
            _error(
                "WIDTH_SUPPORT_TOO_SMALL",
                ["width", "screw_d"],
                "width must be at least 1.45 * screw_d",
            )
        )

    return ValidationResult(
        ok=not errors,
        schema_version=SCHEMA_VERSION,
        family_id=FAMILY_ID,
        normalized=normalized if not errors else normalized,
        provenance=provenance,
        errors=tuple(errors),
    )


def validate_parameters(payload: Mapping[str, Any]) -> ValidationResult:
    """Alias emphasizing that callers should check the result before build."""

    return resolve_parameters(payload)


def validate_json(document: str | bytes) -> ValidationResult:
    """Deserialize a parameter JSON document and validate it.

    JSON parsing errors use the same structured result shape as schema rule
    errors, so callers do not need a second exception channel for bad input.
    """

    try:
        payload = json.loads(document)
    except (TypeError, json.JSONDecodeError) as exc:
        return ValidationResult(
            ok=False,
            schema_version=SCHEMA_VERSION,
            family_id=FAMILY_ID,
            normalized=None,
            provenance={},
            errors=(_error("INVALID_JSON", ["parameters"], f"invalid JSON: {exc}"),),
        )
    return validate_parameters(payload)
