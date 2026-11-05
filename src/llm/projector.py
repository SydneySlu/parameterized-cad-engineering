"""Deterministic CAD-003 projection from explicit extracted parameters.

The projector takes the model's ``extracted_parameters`` (explicit user claims
only) and produces a strict CAD-003 envelope
``{schema_version, family_id, parameters}`` plus the raw extraction snapshot.

It is a pure function: it does not call the schema itself (the adapter does
that, so the schema result is recorded as a separate stage).  Unknown
parameter keys are rejected here so catalog/rule-derived values never enter the
model-extraction layer.

This module deliberately imports the schema module only for its constants when
needed; the actual ``validate_parameters`` call is performed by the adapter so
the run record can capture three distinct stages (raw extraction, projected
payload, schema result).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contract import (
    EXTRACTABLE_FIELDS,
    FAMILY_ID,
    SCHEMA_VERSION,
)


@dataclass(frozen=True)
class ProjectionResult:
    """Result of projecting explicit extracted parameters to CAD-003."""

    ok: bool
    projected_payload: dict[str, Any] | None
    raw_extraction: dict[str, Any]
    # Stable error code/fields for projection-layer rejections (unknown keys).
    errors: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "projected_payload": self.projected_payload,
            "raw_extraction": dict(self.raw_extraction),
            "errors": list(self.errors),
        }


def project_to_cad003(extracted_parameters: Mapping[str, Any] | None) -> ProjectionResult:
    """Project explicit extracted parameters into the strict CAD-003 envelope.

    The model's ``extracted_parameters`` may be empty (e.g. for ``ask`` /
    ``refuse`` decisions) or contain a subset of the six CAD-003 fields.  Each
    value is passed through verbatim -- including conflicting or out-of-range
    explicit claims -- because those are valid extraction claims scored at the
    extraction layer.  Catalog/rule-derived values are never injected here.

    Unknown keys are rejected at this layer (they should not have survived the
    parser's strict key check, but the projector is defensive).
    """
    raw: dict[str, Any] = {}
    if extracted_parameters is not None:
        if not isinstance(extracted_parameters, Mapping):
            return ProjectionResult(
                ok=False,
                projected_payload=None,
                raw_extraction={},
                errors=(
                    {
                        "code": "PROJECTION_INPUT_NOT_OBJECT",
                        "stage": "projection",
                        "fields": ("extracted_parameters",),
                        "message": "extracted_parameters must be an object",
                    },
                ),
            )
        raw = dict(extracted_parameters)

    unknown = sorted(set(raw) - set(EXTRACTABLE_FIELDS))
    if unknown:
        return ProjectionResult(
            ok=False,
            projected_payload=None,
            raw_extraction=raw,
            errors=(
                {
                    "code": "PROJECTION_UNKNOWN_FIELD",
                    "stage": "projection",
                    "fields": tuple(unknown),
                    "message": f"unknown parameter field(s) in extracted_parameters: {unknown}",
                },
            ),
        )

    # Build the strict CAD-003 envelope.  Omitted fields are omitted (the
    # schema layer derives catalog/rule values from bore_d); present fields are
    # passed through so the schema can report conflicts against the catalog.
    parameters: dict[str, Any] = {}
    for field_name in EXTRACTABLE_FIELDS:
        if field_name in raw and raw[field_name] is not None:
            parameters[field_name] = raw[field_name]

    payload = {
        "schema_version": SCHEMA_VERSION,
        "family_id": FAMILY_ID,
        "parameters": parameters,
    }
    return ProjectionResult(
        ok=True,
        projected_payload=payload,
        raw_extraction=raw,
        errors=(),
    )
