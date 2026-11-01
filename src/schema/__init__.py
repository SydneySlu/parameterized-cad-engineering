"""Versioned parameter schemas for the parameterized CAD project.

The package intentionally contains parameter-boundary code only.  It does not
import CadQuery/OCP or construct geometry.
"""

from .set_screw_shaft_collar import (
    FAMILY_ID,
    SCHEMA_VERSION,
    CATALOG_ROWS,
    FieldSpec,
    RuleViolation,
    ValidationResult,
    validate_parameters,
    validate_json,
    resolve_parameters,
    schema_descriptor,
)

__all__ = [
    "FAMILY_ID",
    "SCHEMA_VERSION",
    "CATALOG_ROWS",
    "FieldSpec",
    "RuleViolation",
    "ValidationResult",
    "validate_parameters",
    "validate_json",
    "resolve_parameters",
    "schema_descriptor",
]
