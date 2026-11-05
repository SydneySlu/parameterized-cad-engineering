"""Strict-allowlist projection of the frozen acceptance set for APP-001.

Reads ``acceptance-set-v0.json`` and projects each case to only the
model-visible fields: ``query_id``, ``natural_language_input``, and the
case's ``reference_context`` (used only as a structural template, not
directly injected -- the runner's condition assembler decides what reference
context to use).

Evaluator-only labels -- ``explicit_parameter_claims``, ``derived_values``,
``expected_behavior``, ``unsupported_request_labels``,
``unacceptable_fabrication`` -- are NEVER included in the projection.  They
do not enter the provider transport, the prompt, the run record's model
input, or any C1 reference context.

This module is pure-function; it performs no network calls and reads no
secrets.  It validates the acceptance set structure and the frozen hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from .contract import ACCEPTANCE_SET_VERSION, FAMILY_ID


# Fields that ARE visible to the model (via the prompt template).
_MODEL_VISIBLE_KEYS: Final[frozenset[str]] = frozenset(
    {"case_id", "natural_language_input", "reference_context"}
)

# Fields that are evaluator-only and must NEVER enter the model input.
_EVALUATOR_ONLY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "explicit_parameter_claims",
        "derived_values",
        "expected_behavior",
        "unsupported_request_labels",
        "unacceptable_fabrication",
    }
)


class AcceptanceSetError(ValueError):
    """Raised when the acceptance set is malformed, wrong version, or
    contains evaluator-only fields in a model-visible position."""


@dataclass(frozen=True)
class ProjectedCase:
    """A single acceptance case projected to model-visible fields only.

    ``query_id`` is the ``case_id`` from the acceptance set (e.g.
    ``APP001-A01-complete-description``).
    ``reference_context_structural`` is the case's ``reference_context``
    field, kept for structural reference by the condition assembler.  It is
    NOT directly injected into the model input -- the condition assembler
    decides whether to use it (C0 ignores it; C1 generates via RET-002).

    No evaluator-only fields are present on this object.
    """

    query_id: str
    natural_language_input: str
    reference_context_structural: dict[str, Any] | None
    coverage: tuple[str, ...]

    def model_visible_dict(self) -> dict[str, Any]:
        """Return the dict of fields that may appear in the model prompt."""
        return {
            "query_id": self.query_id,
            "family_id": FAMILY_ID,
            "natural_language_input": self.natural_language_input,
        }


@dataclass(frozen=True)
class AcceptanceSetProjection:
    """The projected acceptance set: 9 cases with only model-visible fields."""

    version: str
    family_id: str
    sample_count: int
    cases: tuple[ProjectedCase, ...]
    source_path: str
    source_sha256: str

    def case_ids(self) -> tuple[str, ...]:
        return tuple(c.query_id for c in self.cases)

    def case_by_id(self, query_id: str) -> ProjectedCase | None:
        for c in self.cases:
            if c.query_id == query_id:
                return c
        return None


def project_acceptance_set(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> AcceptanceSetProjection:
    """Read and project the frozen acceptance set.

    Validates:
    - The JSON is well-formed.
    - ``version`` equals ``ACCEPTANCE_SET_VERSION``.
    - ``family_id`` equals ``FAMILY_ID``.
    - ``sample_count`` equals the number of cases.
    - Each case has the required model-visible fields.
    - If ``expected_sha256`` is provided, the file hash must match.

    Returns an :class:`AcceptanceSetProjection` with only model-visible
    fields per case.  Evaluator-only labels are stripped and not accessible
    through the returned object.
    """
    file_path = Path(path)
    raw_bytes = file_path.read_bytes()
    source_sha = hashlib.sha256(raw_bytes).hexdigest()
    if expected_sha256 is not None and source_sha != expected_sha256:
        raise AcceptanceSetError(
            f"acceptance set hash mismatch: expected {expected_sha256}, "
            f"got {source_sha}"
        )
    try:
        data = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise AcceptanceSetError(f"acceptance set is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AcceptanceSetError("acceptance set root is not a JSON object")
    if data.get("version") != ACCEPTANCE_SET_VERSION:
        raise AcceptanceSetError(
            f"acceptance set version mismatch: expected {ACCEPTANCE_SET_VERSION!r}, "
            f"got {data.get('version')!r}"
        )
    if data.get("family_id") != FAMILY_ID:
        raise AcceptanceSetError(
            f"family_id mismatch: expected {FAMILY_ID!r}, "
            f"got {data.get('family_id')!r}"
        )
    raw_cases = data.get("cases", [])
    if not isinstance(raw_cases, list):
        raise AcceptanceSetError("'cases' is not a list")
    sample_count = data.get("sample_count")
    if sample_count != len(raw_cases):
        raise AcceptanceSetError(
            f"sample_count ({sample_count}) != len(cases) ({len(raw_cases)})"
        )
    projected: list[ProjectedCase] = []
    for idx, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise AcceptanceSetError(f"case {idx} is not a JSON object")
        case_id = raw_case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise AcceptanceSetError(f"case {idx} missing 'case_id'")
        nli = raw_case.get("natural_language_input")
        if not isinstance(nli, str) or not nli:
            raise AcceptanceSetError(f"case {case_id} missing 'natural_language_input'")
        ref = raw_case.get("reference_context")
        if ref is not None and not isinstance(ref, dict):
            raise AcceptanceSetError(
                f"case {case_id} 'reference_context' is not a dict or null"
            )
        coverage = raw_case.get("coverage", [])
        if not isinstance(coverage, list):
            raise AcceptanceSetError(f"case {case_id} 'coverage' is not a list")
        coverage_t = tuple(str(c) for c in coverage)
        projected.append(
            ProjectedCase(
                query_id=case_id,
                natural_language_input=nli,
                reference_context_structural=ref,
                coverage=coverage_t,
            )
        )
    return AcceptanceSetProjection(
        version=ACCEPTANCE_SET_VERSION,
        family_id=FAMILY_ID,
        sample_count=len(projected),
        cases=tuple(projected),
        source_path=str(file_path),
        source_sha256=source_sha,
    )
