"""Offline executable checker for APP-001 v5 quality-fix candidate.

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

  P2 — Envelope self-consistency (2 cases):
    DeepSeek A05 C0 and C1: ``outer_d=40`` was present in both
    ``extracted_parameters`` and ``missing_fields``.  An extracted field cannot
    simultaneously be missing.

This checker works exclusively on model-output envelopes in app001-io.v1 format.
It does not re-implement the full production parse/project/schema pipeline.
Passing this checker does NOT mean a model response passes acceptance; it means
the envelope is self-consistent under the v5 rules.

Isolation guarantee
-------------------
This module imports only:
  - Python stdlib
  - ``schema.set_screw_shaft_collar.CATALOG_ROWS`` (read-only, no side effects)

It does NOT import from llm.contract, llm.parser, llm.adapter, llm.runner,
llm.prompt_loader, llm.budget, llm.gate, or any production path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Mapping, Sequence

# Read-only catalog import — same data as production, no production code path.
from ..schema.set_screw_shaft_collar import CATALOG_ROWS as _CATALOG_ROWS

# ---------------------------------------------------------------------------
# Candidate identity
# ---------------------------------------------------------------------------

CANDIDATE_VERSION: Final[str] = "app001-extraction.v5-candidate"
CONTRACT_VERSION: Final[str] = "app001-io.v1"  # unchanged I/O contract

# ---------------------------------------------------------------------------
# Catalog constants (derived from the same frozen CATALOG_ROWS as production)
# ---------------------------------------------------------------------------

_CATALOG_BORE_D: Final[frozenset[int]] = frozenset(row[0] for row in _CATALOG_ROWS)
_CATALOG_BORE_D_MIN: Final[int] = min(_CATALOG_BORE_D)
_CATALOG_BORE_D_MAX: Final[int] = max(_CATALOG_BORE_D)

# The complete set of extractable fields in app001-io.v1 (mirrors contract.py
# EXTRACTABLE_FIELDS without importing it).
_EXTRACTABLE_FIELDS: Final[frozenset[str]] = frozenset({
    "bore_d", "outer_d", "width", "screw_d", "screw_len", "second_screw",
})

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
# Helpers
# ---------------------------------------------------------------------------

def _bore_d_from_envelope(extracted: Mapping[str, Any]) -> float | int | None:
    """Extract a numeric bore_d from the extracted_parameters sub-object.

    Handles both bare-number and ``{"value": N, "unit": "mm"}`` object forms.
    Returns None if bore_d is absent or non-numeric.
    """
    if not isinstance(extracted, Mapping) or "bore_d" not in extracted:
        return None
    raw = extracted["bore_d"]
    if isinstance(raw, Mapping) and "value" in raw:
        raw = raw["value"]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return raw


def _is_catalog_bore_d(value: float | int) -> bool:
    """True when value is one of the 15 frozen GN 705 catalog bore_d values."""
    return isinstance(value, int) and value in _CATALOG_BORE_D


def _is_in_catalog_range(value: float | int) -> bool:
    """True when value is within the catalog range (inclusive)."""
    return _CATALOG_BORE_D_MIN <= value <= _CATALOG_BORE_D_MAX


# ---------------------------------------------------------------------------
# P1 — No over-refusal when user input is unambiguously complete
# ---------------------------------------------------------------------------

def _check_p1(
    envelope: Mapping[str, Any],
    condition_id: str | None,
) -> list[V5ViolationDetail]:
    """Apply P1 rules: a ``refuse`` is not justified when the envelope already
    shows a valid catalog bore_d, empty missing_fields, and empty
    unsupported_requests.

    Rules:
      P1-1  If bore_d is present in extracted_parameters (numeric, in catalog)
            AND missing_fields == []
            AND unsupported_requests == []
            THEN decision=refuse is an over-refusal.

      P1-2  C0 and C1 condition must not produce different answer/ask/refuse
            decisions when the envelope structure is otherwise identical
            (checked at the batch level; this per-envelope rule only flags
            refuse when the envelope itself already satisfies the answer
            preconditions, regardless of condition).

      P1-3  A unit-converted bore_d (e.g. 1.6 cm → 16 mm) that lands on a
            valid catalog value must not be refused solely because the original
            unit was non-mm.  This is captured by P1-1 using the normalized
            value already present in extracted_parameters.

      P1-4  Retrieval reference context (C1) must not fabricate
            missing_fields or unsupported_requests that are absent from the
            user's own input.  This rule is enforced transitively: when
            missing_fields and unsupported_requests are already empty and
            bore_d is valid, P1-1 fires regardless of condition_id.
    """
    violations: list[V5ViolationDetail] = []

    decision = envelope.get("decision")
    extracted = envelope.get("extracted_parameters", {})
    missing_fields: Any = envelope.get("missing_fields", [])
    unsupported: Any = envelope.get("unsupported_requests", [])

    # Normalise to lists defensively.
    if not isinstance(missing_fields, list):
        missing_fields = []
    if not isinstance(unsupported, list):
        unsupported = []

    bore_d = _bore_d_from_envelope(extracted if isinstance(extracted, Mapping) else {})
    bore_d_present = bore_d is not None
    bore_d_valid_catalog = bore_d_present and _is_catalog_bore_d(bore_d)

    # P1-1: refuse when bore_d valid, missing_fields empty, unsupported empty.
    if (
        decision == "refuse"
        and bore_d_valid_catalog
        and len(missing_fields) == 0
        and len(unsupported) == 0
    ):
        cond_note = f" (condition={condition_id})" if condition_id else ""
        violations.append(V5ViolationDetail(
            rule_id="P1-1",
            message=(
                f"decision=refuse is not justified when bore_d is a valid catalog "
                f"value, missing_fields=[], and unsupported_requests=[]"
                f"{cond_note}; the v5 candidate rule requires decision=answer "
                f"in this situation"
            ),
            evidence=f"bore_d={bore_d}  missing_fields={missing_fields}  "
                     f"unsupported_requests={unsupported}",
        ))

    # P1-1 also applies when decision=ask under the same conditions — asking
    # is also unjustified when all required info is present and valid.
    if (
        decision == "ask"
        and bore_d_valid_catalog
        and len(missing_fields) == 0
        and len(unsupported) == 0
    ):
        cond_note = f" (condition={condition_id})" if condition_id else ""
        violations.append(V5ViolationDetail(
            rule_id="P1-1",
            message=(
                f"decision=ask is not justified when bore_d is a valid catalog "
                f"value, missing_fields=[], and unsupported_requests=[]"
                f"{cond_note}; the v5 candidate rule requires decision=answer "
                f"in this situation"
            ),
            evidence=f"bore_d={bore_d}  missing_fields={missing_fields}  "
                     f"unsupported_requests={unsupported}",
        ))

    return violations


# ---------------------------------------------------------------------------
# P2 — Envelope self-consistency
# ---------------------------------------------------------------------------

def _check_p2(envelope: Mapping[str, Any]) -> list[V5ViolationDetail]:
    """Apply P2 rules: the envelope must not contradict itself.

    Rules:
      P2-1  No field that appears in extracted_parameters may also appear
            in missing_fields.  A field is either extracted (present) or
            missing — never both.

      P2-2  No field in missing_fields may appear as a key in
            extracted_parameters (same invariant, stated from the other side,
            to catch both directions in tests).

      P2-3  decision=answer must not coexist with non-empty missing_fields or
            non-empty unsupported_requests (pre-existing invariant, restated
            here for completeness; violations also appear in P1 context).

      P2-4  No duplicate entries within missing_fields (each field may appear
            at most once).

    Note: P2-1 and P2-2 are the same mathematical invariant.  Both are
    checked explicitly so tests can target either direction.
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

    # P2-1 / P2-2: intersection of extracted_keys and missing_set must be empty.
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

    # P2-3: decision=answer must not coexist with non-empty missing_fields.
    if decision == "answer" and len(missing_fields) > 0:
        violations.append(V5ViolationDetail(
            rule_id="P2-3",
            message=(
                "decision=answer but missing_fields is non-empty; "
                "a missing required field means construction cannot proceed"
            ),
            evidence=f"missing_fields={missing_fields}",
        ))

    # P2-3: decision=answer must not coexist with non-empty unsupported_requests.
    if decision == "answer" and len(unsupported) > 0:
        violations.append(V5ViolationDetail(
            rule_id="P2-3",
            message=(
                "decision=answer but unsupported_requests is non-empty; "
                "unsupported features block construction"
            ),
            evidence=f"unsupported_requests={unsupported}",
        ))

    # P2-4: no duplicate entries in missing_fields.
    seen_missing: set[str] = set()
    for f in missing_fields:
        if isinstance(f, str):
            if f in seen_missing:
                violations.append(V5ViolationDetail(
                    rule_id="P2-4",
                    message=f"field '{f}' appears more than once in missing_fields",
                    evidence=f"missing_fields={missing_fields}",
                ))
                break  # one violation per duplicate is enough
            seen_missing.add(f)

    return violations


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
            made; no API keys are read or examined.
        condition_id: Optional condition identifier (``"C0"`` or ``"C1"``)
            for auditability.  Does not change the P1/P2 rule logic — the
            rules are condition-agnostic by design (C0 and C1 must produce the
            same decision when the envelope structure is otherwise equivalent).

    Returns:
        A :class:`V5CheckResult` with:
          - ``ok=True`` when no violations are found.
          - Separate ``p1_violations`` and ``p2_violations`` tuples.
          - Combined ``violations`` tuple for convenience.

    This function never modifies the input envelope, never logs or prints
    API keys or secrets, and never makes network calls.
    """
    if not isinstance(envelope, Mapping):
        # Non-mapping input: cannot check; return a structural violation.
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
    """True when the envelope contains a P1 over-refusal violation.

    Convenience wrapper over :func:`check_v5_envelope`.
    """
    return len(check_v5_envelope(envelope, condition_id=condition_id).p1_violations) > 0


def is_self_consistent(envelope: Mapping[str, Any]) -> bool:
    """True when the envelope passes all P2 self-consistency checks.

    Convenience wrapper over :func:`check_v5_envelope`.
    """
    return len(check_v5_envelope(envelope).p2_violations) == 0
