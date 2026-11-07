"""Offline executable checker for the unactivated APP-001 v4 candidate.

This module is deliberately outside the production adapter/parser/runner path.
It turns the three v4 policy corrections into deterministic fixture checks:
exact unit normalization, user-claim precedence over retrieval references, and
stable unsupported-request labels.  It does not call a model and does not
authorize or perform a formal evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final, Mapping

from .decision_policy_v3_candidate import (
    ANSWER,
    CaseCharacteristics,
    allowed_decisions,
)
from ..schema.set_screw_shaft_collar import CATALOG_ROWS as FROZEN_CATALOG_ROWS


CANDIDATE_PROMPT_VERSION: Final[str] = "app001-extraction.v4"
CATALOG_BORE_D_VALUES: Final[frozenset[int]] = frozenset(
    int(row[0]) for row in FROZEN_CATALOG_ROWS
)
CATALOG_BORE_D_MIN: Final[int] = min(CATALOG_BORE_D_VALUES)
CATALOG_BORE_D_MAX: Final[int] = max(CATALOG_BORE_D_VALUES)

_UNIT_FACTORS: Final[Mapping[str, Decimal]] = {
    "mm": Decimal("1"),
    "millimeter": Decimal("1"),
    "millimeters": Decimal("1"),
    "毫米": Decimal("1"),
    "cm": Decimal("10"),
    "centimeter": Decimal("10"),
    "centimeters": Decimal("10"),
    "厘米": Decimal("10"),
    "m": Decimal("1000"),
    "meter": Decimal("1000"),
    "meters": Decimal("1000"),
    "米": Decimal("1000"),
}

_UNSUPPORTED_ALIASES: Final[Mapping[str, str]] = {
    "阳极氧化": "anodizing",
    "anodize": "anodizing",
    "anodized": "anodizing",
    "anodizing": "anodizing",
    "法兰": "flange",
    "flange": "flange",
    "键槽": "keyway",
    "keyway": "keyway",
}


class CandidateInputError(ValueError):
    """Raised when an offline fixture contains an invalid measurement."""


@dataclass(frozen=True)
class NormalizedLength:
    value_mm: int | Decimal
    original_value: object
    original_unit: str
    evidence_quote: str


@dataclass(frozen=True)
class UnsupportedEvidence:
    """Evidence entry for one unsupported feature request.

    Mirrors the ``evidence`` array entry shape from ``app001-io.v1``:
    each entry has a stable canonical field name, the user's original
    wording as the quote, and ``source="user_input"``.  Only the user's
    request can create an unsupported item — retrieval context cannot
    fabricate new items.
    """

    canonical_label: str
    original_quote: str
    source: str = "user_input"


@dataclass(frozen=True)
class V4FixtureCase:
    """Minimal evaluator fixture, containing no model output or secrets."""

    bore_value: object | None = None
    bore_unit: str = "mm"
    evidence_quote: str = ""
    retrieval_bore_value: object | None = None
    unsupported_terms: tuple[str, ...] = ()
    missing_required: bool = False
    catalog_conflict: bool = False
    rule_conflict: bool = False
    direct_contradiction: bool = False


@dataclass(frozen=True)
class V4FixtureResult:
    decision_options: frozenset[str]
    normalized_bore: NormalizedLength | None
    unsupported_labels: tuple[str, ...]
    retrieval_bore_raw: object | None = None
    retrieval_acknowledged: bool = False
    unsupported_evidence: tuple[UnsupportedEvidence, ...] = ()

    @property
    def answer_allowed(self) -> bool:
        return ANSWER in self.decision_options


def normalize_length_to_mm(value: object, unit: str, evidence_quote: str = "") -> NormalizedLength:
    """Normalize an explicitly supplied length while preserving its evidence."""

    unit_key = str(unit).strip().lower()
    if unit_key not in _UNIT_FACTORS:
        raise CandidateInputError(f"unsupported length unit: {unit!r}")
    try:
        normalized = Decimal(str(value)) * _UNIT_FACTORS[unit_key]
    except (InvalidOperation, ValueError):
        raise CandidateInputError(f"invalid numeric length: {value!r}") from None
    if not normalized.is_finite():
        raise CandidateInputError(f"non-finite length: {value!r}")
    if normalized != normalized.to_integral_value():
        result: int | Decimal = normalized
    else:
        result = int(normalized)
    return NormalizedLength(result, value, str(unit), evidence_quote)


def canonicalize_unsupported(label: str) -> str:
    """Return the stable v4 label for one explicitly requested feature."""

    key = str(label).strip().lower()
    return _UNSUPPORTED_ALIASES.get(key, key)


def resolve_bore_precedence(
    user_bore: NormalizedLength | None,
    retrieval_bore_value: object | None,
) -> NormalizedLength | None:
    """Return the bore to use, enforcing that the user claim controls.

    The retrieval value is untrusted reference context.  It is never
    promoted to a user claim, never treated as ``user_input`` evidence,
    and never fills in for a missing ``bore_d``.

    * When the user explicitly stated a ``bore_d``, the normalized user
      claim is returned regardless of what retrieval shows.
    * When the user bore is absent, ``None`` is returned — the retrieval
      value does **not** become the extracted claim.
    """

    # ``retrieval_bore_value`` is acknowledged as present but never
    # promoted: its presence does not change the return value.
    _ = retrieval_bore_value  # explicitly unused
    return user_bore


def evaluate_fixture(case: V4FixtureCase) -> V4FixtureResult:
    """Evaluate v4 decision options for a synthetic, offline fixture."""

    # Step 1: normalize the user's bore claim (None when absent).
    user_bore: NormalizedLength | None = None
    if case.bore_value is not None:
        user_bore = normalize_length_to_mm(
            case.bore_value, case.bore_unit, case.evidence_quote
        )

    # Step 2: resolve precedence — retrieval never promotes to user claim.
    normalized = resolve_bore_precedence(user_bore, case.retrieval_bore_value)
    retrieval_acknowledged = case.retrieval_bore_value is not None

    # Step 3: canonicalize unsupported labels and build evidence entries.
    # De-duplicate by canonical label while preserving each original quote.
    seen: dict[str, UnsupportedEvidence] = {}
    for term in case.unsupported_terms:
        label = canonicalize_unsupported(term)
        if label not in seen:
            seen[label] = UnsupportedEvidence(
                canonical_label=label,
                original_quote=term,
                source="user_input",
            )
    labels = tuple(seen.keys())
    evidence = tuple(seen.values())

    # Step 4: compute decision options via the v3 allowed_decisions gate.
    present = normalized is not None
    bore_number = normalized.value_mm if normalized is not None else None
    in_range = (
        isinstance(bore_number, (int, Decimal))
        and CATALOG_BORE_D_MIN <= bore_number <= CATALOG_BORE_D_MAX
    )
    in_catalog = isinstance(bore_number, int) and bore_number in CATALOG_BORE_D_VALUES
    options = allowed_decisions(
        CaseCharacteristics(
            bore_d_present=present,
            bore_d_value=bore_number,
            bore_d_in_catalog=in_catalog,
            bore_d_in_range=in_range,
            has_unsupported_requests=bool(labels),
            has_missing_required=case.missing_required or not present,
            has_catalog_conflict=case.catalog_conflict,
            has_rule_conflict=case.rule_conflict,
            has_direct_contradiction=case.direct_contradiction,
            unsupported_request_names=labels,
        )
    )
    return V4FixtureResult(
        decision_options=options,
        normalized_bore=normalized,
        unsupported_labels=labels,
        retrieval_bore_raw=case.retrieval_bore_value,
        retrieval_acknowledged=retrieval_acknowledged,
        unsupported_evidence=evidence,
    )
