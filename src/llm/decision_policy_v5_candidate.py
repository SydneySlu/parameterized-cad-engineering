"""Offline executable checker for APP-001 v5 quality-fix candidate (R1).

CANDIDATE VERSION — NOT ACTIVATED.

This module is deliberately outside the production adapter/parser/runner path.
It must NOT be imported by adapter.py, parser.py, runner.py, contract.py, or
prompt_loader.py.  Its purpose is to make the two confirmed quality deviations
from batch app001-phase1-v4-20261109-01 (Codex review 2026-11-09) testable
offline without any model call, network access, or API-key read.

Confirmed deviations this candidate addresses:

  P1 — Ollama over-refusal (3 cases):
    A02 C1, A03 C0, A08 C1: model returned ``refuse`` where ``answer`` was
    expected.  In all three cases the extracted envelope already contained a
    valid catalog bore_d, ``missing_fields=[]``, and ``unsupported_requests=[]``.
    The over-refusal violates the prompt instruction: "Do not ask again for a
    parameter that is explicit and unambiguous in the user request merely
    because untrusted retrieval context contains a different value."

  P2 — Envelope self-consistency (5 rules):
    P2-1/P2-2  Field overlap: extracted field also in missing_fields.
               DeepSeek A05 C0/C1: outer_d=40 in both extracted_parameters
               and missing_fields.
    P2-3       decision=answer + non-empty missing_fields or unsupported.
    P2-4       Duplicate entries in missing_fields.
    P2-5       decision=answer + deterministic CAD-003 catalog/rule conflict:
               (a) bore_d value maps to a catalog row but another explicit
                   extracted field disagrees with that row (catalog conflict);
               (b) second_screw value contradicts the bore_d > 70 rule.

R1 additions (Codex review 2026-11-09, issue #2 and #3):
  - P2-5: catalog/rule conflict check (A05 answer, A09 answer).
  - Numeric normalization: bore_d=24.0 treated as catalog value 24;
    measurement-object bore_d {"value":1.6,"unit":"cm"} normalised to 16 mm.

Isolation guarantee
-------------------
This module imports only:
  - Python stdlib (decimal, dataclasses, typing)
  - ``schema.set_screw_shaft_collar.CATALOG_ROWS`` (read-only, no side effects)

It does NOT import from llm.contract, llm.parser, llm.adapter, llm.runner,
llm.prompt_loader, llm.budget, llm.gate, or any production path.

Import path
-----------
The module uses an absolute import ``schema.set_screw_shaft_collar`` so it
works under the project-standard ``PYTHONPATH=src`` entry point:

    PYTHONPATH=src python3 -c 'import llm.decision_policy_v5_candidate as m'

It also works as ``src.llm.decision_policy_v5_candidate`` when tests add the
repo root to ``PYTHONPATH``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Final, Mapping

# ---------------------------------------------------------------------------
# Catalog import — absolute path for PYTHONPATH=src compatibility (R1-1).
# The module lives in src/llm/ and schema/ is a sibling package under src/.
# Using an absolute import instead of ``from ..schema...`` avoids the
# "attempted relative import beyond top-level package" error when the module
# is imported via the plain ``llm`` package (PYTHONPATH=src).
# ---------------------------------------------------------------------------
from schema.set_screw_shaft_collar import CATALOG_ROWS as _CATALOG_ROWS  # type: ignore[import]

# ---------------------------------------------------------------------------
# Candidate identity
# ---------------------------------------------------------------------------

CANDIDATE_VERSION: Final[str] = "app001-extraction.v5-candidate"
CONTRACT_VERSION: Final[str] = "app001-io.v1"  # unchanged I/O contract

# ---------------------------------------------------------------------------
# Catalog constants (derived from the same frozen CATALOG_ROWS as production)
# CATALOG_ROWS columns: (bore_d, outer_d, screw_d, screw_len, width)
# ---------------------------------------------------------------------------

# Set of the 15 valid bore_d values.
_CATALOG_BORE_D: Final[frozenset[int]] = frozenset(row[0] for row in _CATALOG_ROWS)
_CATALOG_BORE_D_MIN: Final[int] = min(_CATALOG_BORE_D)
_CATALOG_BORE_D_MAX: Final[int] = max(_CATALOG_BORE_D)

# Map bore_d → expected outer_d (from the catalog row).
# Used for P2-5 catalog-conflict detection.
_CATALOG_BORE_TO_OUTER: Final[dict[int, int]] = {row[0]: row[1] for row in _CATALOG_ROWS}

# second_screw rule: second_screw == 1 iff bore_d > 70 (GN 705 note).
# bore_d = 70 → expected second_screw = 0 (strict threshold, not >=).
_SECOND_SCREW_THRESHOLD: Final[int] = 70

# Unit conversion factors to mm.
_MM_PER_UNIT: Final[dict[str, Decimal]] = {
    "mm": Decimal("1"),
    "millimeter": Decimal("1"),
    "millimeters": Decimal("1"),
    "cm": Decimal("10"),
    "centimeter": Decimal("10"),
    "centimeters": Decimal("10"),
    "m": Decimal("1000"),
    "meter": Decimal("1000"),
    "meters": Decimal("1000"),
}

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class V5ViolationDetail:
    """A single auditable violation record."""

    rule_id: str        # e.g. "P1-1", "P2-1"
    message: str
    evidence: str = ""  # non-sensitive context (field names, values — no keys)


@dataclass(frozen=True)
class V5CheckResult:
    """Result of running the v5 offline consistency check on one envelope.

    Attributes:
        ok: True when no P1 or P2 violations are found.
        p1_violations: Over-refusal violations (P1 rules).
        p2_violations: Envelope self-consistency violations (P2 rules).
        violations: Combined tuple of all violations, in rule order.
        condition_id: The condition under which the response was produced
            (``"C0"`` or ``"C1"``), if supplied.  Provided for auditability
            only; the rules themselves are condition-agnostic.
    """

    ok: bool
    p1_violations: tuple[V5ViolationDetail, ...]
    p2_violations: tuple[V5ViolationDetail, ...]
    violations: tuple[V5ViolationDetail, ...]
    condition_id: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_bore_d(raw: Any) -> int | None:
    """Return the numeric bore_d as an integer mm value, or None.

    Handles three forms:
      1. Bare integer or float: bore_d=24 or bore_d=24.0 → 24
      2. Measurement object: {"value": 1.6, "unit": "cm"} → 16
      3. Anything else (bool, string, None, unknown unit) → None

    Only returns a value when the result is a whole-number mm value that
    could potentially be a catalog entry.  Non-finite values, non-integer
    results after unit conversion, and unknown units all return None.
    """
    if isinstance(raw, Mapping) and "value" in raw:
        unit = str(raw.get("unit", "mm")).strip().lower()
        factor = _MM_PER_UNIT.get(unit)
        if factor is None:
            return None  # unknown unit — not a valid catalog bore
        try:
            converted = Decimal(str(raw["value"])) * factor
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not converted.is_finite():
            return None
        if converted != converted.to_integral_value():
            return None  # fractional mm — no catalog entry is fractional
        return int(converted)

    if isinstance(raw, bool):
        return None
    if isinstance(raw, float):
        # Only accept finite whole-number floats (e.g. 24.0 → 24).
        import math
        if not math.isfinite(raw) or raw != int(raw):
            return None
        return int(raw)
    if isinstance(raw, int):
        return raw
    return None


def _bore_d_from_envelope(extracted: Mapping[str, Any]) -> int | None:
    """Extract a normalized integer bore_d (mm) from extracted_parameters.

    Returns None if bore_d is absent, non-numeric, uses an unknown unit,
    or produces a non-integer mm value after conversion.
    """
    if not isinstance(extracted, Mapping) or "bore_d" not in extracted:
        return None
    return _normalize_bore_d(extracted["bore_d"])


def _is_catalog_bore_d(value: int) -> bool:
    """True when value is one of the 15 frozen GN 705 catalog bore_d values."""
    return value in _CATALOG_BORE_D


# ---------------------------------------------------------------------------
# P1 — No over-refusal when user input is unambiguously complete
# ---------------------------------------------------------------------------


def _has_deterministic_conflict(extracted: Mapping[str, Any], bore_d: int) -> bool:
    """True when extracted_parameters contain a deterministic CAD-003 conflict.

    Used by P1-1 to distinguish legitimate ask/refuse (conflict exists) from
    over-refusal (no conflict exists).  Checks the same conditions as P2-5
    but as a boolean gate, without recording violation details.

    A conflict exists when:
    (a) explicit outer_d disagrees with the catalog row for bore_d; OR
    (b) explicit second_screw violates the bore_d > 70 rule.
    """
    expected_outer = _CATALOG_BORE_TO_OUTER.get(bore_d)
    if "outer_d" in extracted and expected_outer is not None:
        outer_mm = _normalize_bore_d(extracted["outer_d"])
        if outer_mm is not None and outer_mm != expected_outer:
            return True

    if "second_screw" in extracted:
        raw_ss = extracted["second_screw"]
        if isinstance(raw_ss, bool) or not isinstance(raw_ss, (int, float)):
            pass
        else:
            ss_val = int(raw_ss) if isinstance(raw_ss, float) and raw_ss == int(raw_ss) else raw_ss
            if isinstance(ss_val, int) and ss_val in (0, 1):
                expected_ss = 1 if bore_d > _SECOND_SCREW_THRESHOLD else 0
                if ss_val != expected_ss:
                    return True

    return False


def _check_p1(
    envelope: Mapping[str, Any],
    condition_id: str | None,
) -> list[V5ViolationDetail]:
    """Apply P1 rules.

    P1-1  If bore_d is present and is a valid catalog value AND
          missing_fields == [] AND unsupported_requests == [] THEN
          decision=refuse or decision=ask is an over-refusal; decision=answer
          is required.

    P1-2/P1-3/P1-4 are captured by P1-1 (condition-agnostic; unit-converted
    and retrieval-context cases all reduce to the same envelope check).
    """
    violations: list[V5ViolationDetail] = []

    decision = envelope.get("decision")
    extracted = envelope.get("extracted_parameters", {})
    missing_fields: Any = envelope.get("missing_fields", [])
    unsupported: Any = envelope.get("unsupported_requests", [])

    if not isinstance(missing_fields, list):
        missing_fields = []
    if not isinstance(unsupported, list):
        unsupported = []

    bore_d = _bore_d_from_envelope(extracted if isinstance(extracted, Mapping) else {})
    bore_d_valid_catalog = bore_d is not None and _is_catalog_bore_d(bore_d)

    # Suppress P1-1 when there is a deterministic catalog/rule conflict in the
    # extracted fields.  A catalog conflict is a legitimate reason for ask/refuse
    # (e.g. A05: bore_d=20 but outer_d=40 conflicts with the catalog row).
    has_conflict = (
        bore_d_valid_catalog
        and isinstance(extracted, Mapping)
        and _has_deterministic_conflict(extracted, bore_d)
    )

    if (
        decision in ("refuse", "ask")
        and bore_d_valid_catalog
        and not has_conflict
        and len(missing_fields) == 0
        and len(unsupported) == 0
    ):
        cond_note = f" (condition={condition_id})" if condition_id else ""
        violations.append(V5ViolationDetail(
            rule_id="P1-1",
            message=(
                f"decision={decision} is not justified when bore_d is a valid "
                f"catalog value, missing_fields=[], and unsupported_requests=[]"
                f"{cond_note}; the v5 candidate rule requires decision=answer "
                f"in this situation"
            ),
            evidence=(
                f"bore_d={bore_d}  missing_fields={missing_fields}  "
                f"unsupported_requests={unsupported}"
            ),
        ))

    return violations


# ---------------------------------------------------------------------------
# P2 — Envelope self-consistency (including catalog/rule conflict)
# ---------------------------------------------------------------------------


def _check_p2(envelope: Mapping[str, Any]) -> list[V5ViolationDetail]:
    """Apply P2 rules.

    P2-1/P2-2  Field in extracted_parameters also appears in missing_fields.
    P2-3       decision=answer + non-empty missing_fields or unsupported.
    P2-4       Duplicate entries in missing_fields.
    P2-5       decision=answer + deterministic catalog/rule conflict:
               (a) explicit outer_d disagrees with the catalog row for bore_d;
               (b) explicit second_screw violates the bore_d > 70 rule.
               The checker records the conflict without modifying or removing
               any explicit claim.
    """
    violations: list[V5ViolationDetail] = []

    decision = envelope.get("decision")
    extracted = envelope.get("extracted_parameters", {})
    missing_fields: Any = envelope.get("missing_fields", [])
    unsupported: Any = envelope.get("unsupported_requests", [])

    if not isinstance(missing_fields, list):
        missing_fields = []
    if not isinstance(unsupported, list):
        unsupported = []
    if not isinstance(extracted, Mapping):
        extracted = {}

    extracted_keys = set(extracted.keys())
    missing_set = {f for f in missing_fields if isinstance(f, str)}

    # P2-1/P2-2: overlap between extracted_parameters and missing_fields.
    overlap = extracted_keys & missing_set
    for field_name in sorted(overlap):
        violations.append(V5ViolationDetail(
            rule_id="P2-1",
            message=(
                f"field '{field_name}' appears in both extracted_parameters "
                f"and missing_fields; a field is either extracted or missing, "
                f"never both"
            ),
            evidence=(
                f"extracted_parameters keys={sorted(extracted_keys)}  "
                f"missing_fields={sorted(missing_set)}"
            ),
        ))

    # P2-3: answer + non-empty missing_fields.
    if decision == "answer" and len(missing_fields) > 0:
        violations.append(V5ViolationDetail(
            rule_id="P2-3",
            message=(
                "decision=answer but missing_fields is non-empty; "
                "a missing required field means construction cannot proceed"
            ),
            evidence=f"missing_fields={missing_fields}",
        ))

    # P2-3: answer + non-empty unsupported_requests.
    if decision == "answer" and len(unsupported) > 0:
        violations.append(V5ViolationDetail(
            rule_id="P2-3",
            message=(
                "decision=answer but unsupported_requests is non-empty; "
                "unsupported features block construction"
            ),
            evidence=f"unsupported_requests={unsupported}",
        ))

    # P2-4: duplicate entries in missing_fields.
    seen_missing: set[str] = set()
    for f in missing_fields:
        if isinstance(f, str):
            if f in seen_missing:
                violations.append(V5ViolationDetail(
                    rule_id="P2-4",
                    message=f"field '{f}' appears more than once in missing_fields",
                    evidence=f"missing_fields={missing_fields}",
                ))
                break
            seen_missing.add(f)

    # P2-5: decision=answer + deterministic catalog/rule conflict.
    # Only checked when decision=answer (other decisions are expected to
    # reflect a conflict by using ask/refuse; flagging them here would
    # produce false positives for correct ask/refuse envelopes).
    if decision == "answer":
        bore_d = _bore_d_from_envelope(extracted)
        if bore_d is not None and _is_catalog_bore_d(bore_d):
            _check_p2_5_catalog(bore_d, extracted, violations)

    return violations


def _check_p2_5_catalog(
    bore_d: int,
    extracted: Mapping[str, Any],
    violations: list[V5ViolationDetail],
) -> None:
    """Check P2-5 catalog/rule conflicts for a decision=answer envelope.

    (a) outer_d conflict: the explicit outer_d disagrees with the catalog row.
    (b) second_screw rule conflict: the explicit second_screw violates the
        bore_d > 70 threshold.

    Violations are appended to ``violations`` in-place.
    The checker never modifies, removes, or rewrites any explicit claim.
    """
    expected_outer_d = _CATALOG_BORE_TO_OUTER.get(bore_d)

    # (a) outer_d catalog conflict.
    if "outer_d" in extracted and expected_outer_d is not None:
        raw_outer = extracted["outer_d"]
        outer_mm = _normalize_bore_d(raw_outer)  # reuse normalization
        if outer_mm is not None and outer_mm != expected_outer_d:
            violations.append(V5ViolationDetail(
                rule_id="P2-5",
                message=(
                    f"decision=answer but explicit outer_d conflicts with the "
                    f"catalog row for bore_d={bore_d}: "
                    f"catalog expects outer_d={expected_outer_d}, "
                    f"envelope has outer_d={outer_mm}; "
                    f"construction cannot proceed with conflicting dimensions"
                ),
                evidence=(
                    f"bore_d={bore_d}  explicit_outer_d={outer_mm}  "
                    f"catalog_outer_d={expected_outer_d}"
                ),
            ))

    # (b) second_screw rule conflict.
    if "second_screw" in extracted:
        raw_ss = extracted["second_screw"]
        if isinstance(raw_ss, bool) or not isinstance(raw_ss, (int, float)):
            pass  # non-numeric second_screw: let schema handle it
        else:
            ss_val = int(raw_ss) if isinstance(raw_ss, float) and raw_ss == int(raw_ss) else raw_ss
            if isinstance(ss_val, int) and ss_val in (0, 1):
                expected_ss = 1 if bore_d > _SECOND_SCREW_THRESHOLD else 0
                if ss_val != expected_ss:
                    violations.append(V5ViolationDetail(
                        rule_id="P2-5",
                        message=(
                            f"decision=answer but explicit second_screw={ss_val} "
                            f"violates the GN 705 rule: "
                            f"bore_d={bore_d} {'>' if bore_d > _SECOND_SCREW_THRESHOLD else '<='} "
                            f"{_SECOND_SCREW_THRESHOLD}, so second_screw must be "
                            f"{expected_ss}"
                        ),
                        evidence=(
                            f"bore_d={bore_d}  explicit_second_screw={ss_val}  "
                            f"required_second_screw={expected_ss}"
                        ),
                    ))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_v5_envelope(
    envelope: Mapping[str, Any],
    *,
    condition_id: str | None = None,
) -> V5CheckResult:
    """Run the v5 P1 and P2 offline consistency checks on one model-output
    envelope.

    Args:
        envelope: A parsed app001-io.v1 envelope (dict-like).  This is the
            model's JSON response object, already parsed.  No network call is
            made; no API keys are read or examined.  The input is never
            modified.
        condition_id: Optional condition identifier (``"C0"`` or ``"C1"``)
            for auditability.  Does not change the P1/P2 rule logic.

    Returns:
        A :class:`V5CheckResult` with ``ok=True`` when no violations are found.
    """
    if not isinstance(envelope, Mapping):
        v = V5ViolationDetail(
            rule_id="P2-0",
            message="envelope is not a JSON object (Mapping); cannot check",
            evidence=f"type={type(envelope).__name__}",
        )
        return V5CheckResult(
            ok=False,
            p1_violations=(),
            p2_violations=(v,),
            violations=(v,),
            condition_id=condition_id,
        )

    p1 = _check_p1(envelope, condition_id)
    p2 = _check_p2(envelope)
    all_violations = tuple(p1) + tuple(p2)
    return V5CheckResult(
        ok=len(all_violations) == 0,
        p1_violations=tuple(p1),
        p2_violations=tuple(p2),
        violations=all_violations,
        condition_id=condition_id,
    )


def is_over_refusal(
    envelope: Mapping[str, Any],
    condition_id: str | None = None,
) -> bool:
    """True when the envelope contains a P1 over-refusal violation."""
    return len(check_v5_envelope(envelope, condition_id=condition_id).p1_violations) > 0


def is_self_consistent(envelope: Mapping[str, Any]) -> bool:
    """True when the envelope passes all P2 self-consistency checks."""
    return len(check_v5_envelope(envelope).p2_violations) == 0
