"""Candidate decision policy v3 for APP-001 (offline checker, UNACTIVATED).

This module is an **unactivated candidate**.  It is NOT imported by the
adapter, parser, runner, or any production code path.  It exists solely to
make the v3 decision-gate logic testable offline against the frozen
acceptance set without calling a real model.

It imports read-only constants from the frozen ``contract`` module to verify
interface compatibility, but does not modify any frozen module.

See ``agent-work/llm/APP-001-baseline-prep/decision-policy-v3-candidate.md``
for the strategy spec and
``agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate.md`` for the
candidate prompt text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Mapping

# Read-only imports from the frozen contract (interface compatibility only).
from .contract import (
    CONTRACT_VERSION,
    DECISION_VALUES,
    ENVELOPE_KEYS,
    EVIDENCE_KEYS,
    EVIDENCE_SOURCE_VALUES,
    EXTRACTABLE_FIELDS,
)

# ---------------------------------------------------------------------------
# Candidate constants (NOT in contract.py; not activated)
# ---------------------------------------------------------------------------

CANDIDATE_PROMPT_VERSION: Final[str] = "app001-extraction.v3"

# The 15 frozen GN 705 catalog bore_d values, used for range and catalog
# membership checks.  Sourced from src/schema/set_screw_shaft_collar.py
# CATALOG_ROWS column 0 (read-only reference, not a modification).
_CATALOG_BORE_D_VALUES: Final[frozenset[int]] = frozenset(
    {5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80}
)
CATALOG_BORE_D_MIN: Final[int] = 5
CATALOG_BORE_D_MAX: Final[int] = 80

# Decision constants (mirrors of DECISION_VALUES for readability).
ANSWER: Final[str] = "answer"
ASK: Final[str] = "ask"
REFUSE: Final[str] = "refuse"

# Path to the candidate prompt file (for interface compatibility checks).
_REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_PROMPT_PATH: Final[Path] = (
    _REPO_ROOT
    / "agent-work"
    / "llm"
    / "APP-001-baseline-prep"
    / "prompt-v3-candidate.md"
)


# ---------------------------------------------------------------------------
# Case characteristics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseCharacteristics:
    """Characteristics of a user request case, as seen by the v3 policy.

    Some fields represent what the model CAN detect from user input alone
    (bore_d_present, bore_d_in_range, has_unsupported_requests,
    has_direct_contradiction).  Others represent what the deterministic
    CAD-003 layer WOULD detect (bore_d_in_catalog, has_catalog_conflict,
    has_rule_conflict).  The offline checker uses both to test the ideal
    behavior expected by the frozen acceptance set.
    """

    bore_d_present: bool
    bore_d_value: float | int | None
    bore_d_in_catalog: bool
    bore_d_in_range: bool
    has_unsupported_requests: bool
    has_missing_required: bool
    has_catalog_conflict: bool
    has_rule_conflict: bool
    has_direct_contradiction: bool
    unsupported_request_names: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Decision-gate logic
# ---------------------------------------------------------------------------


def allowed_decisions(case: CaseCharacteristics) -> frozenset[str]:
    """Return the set of decision values allowed by the v3 policy.

    The returned set is a subset of ``DECISION_VALUES`` from the frozen
    contract.  An empty set means the case characteristics are contradictory
    (a bug in the test fixture, not a model behavior).
    """

    allowed: set[str] = set()

    # --- answer: all preconditions met ---
    answer_allowed = (
        case.bore_d_present
        and case.bore_d_in_range
        and not case.has_unsupported_requests
        and not case.has_missing_required
        and not case.has_direct_contradiction
        and not case.has_catalog_conflict
        and not case.has_rule_conflict
    )
    if answer_allowed:
        allowed.add(ANSWER)

    # --- ask: resolvable issue, no hard refuse trigger ---
    needs_clarification = (
        case.has_missing_required
        or case.has_direct_contradiction
        or case.has_catalog_conflict
        or case.has_rule_conflict
    )
    hard_refuse = case.has_unsupported_requests or (
        case.bore_d_present and not case.bore_d_in_range
    )
    if needs_clarification and not hard_refuse:
        allowed.add(ASK)

    # --- refuse: hard construction blocker or unresolvable ---
    refuse_allowed = (
        case.has_unsupported_requests
        or (case.bore_d_present and not case.bore_d_in_range)
        or case.has_catalog_conflict
        or case.has_rule_conflict
        or case.has_missing_required
    )
    if refuse_allowed:
        allowed.add(REFUSE)

    # Sanity: result must be a subset of the frozen contract's decision values.
    if not allowed.issubset(DECISION_VALUES):
        raise AssertionError(
            f"v3 checker produced decisions outside frozen contract: {allowed - DECISION_VALUES}"
        )
    return frozenset(allowed)


def is_answer_allowed(case: CaseCharacteristics) -> bool:
    """True when the v3 policy permits ``decision=answer`` for this case."""
    return ANSWER in allowed_decisions(case)


# ---------------------------------------------------------------------------
# Envelope self-consistency check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyResult:
    """Result of checking a model output envelope against v3 self-consistency rules."""

    ok: bool
    violations: tuple[str, ...]


def check_envelope_consistency(envelope: Mapping[str, Any]) -> ConsistencyResult:
    """Check that a model output envelope is self-consistent under v3 rules.

    This verifies the self-consistency invariants from the v3 prompt's
    "Self-consistency check before finalizing" section.  It does NOT verify
    CAD-003 constraints (those are checked by the deterministic layer).

    The input ``envelope`` is a parsed JSON object with the same shape as the
    ``app001-io.v1`` envelope.  The ``prompt_version`` may be ``v2`` or ``v3``;
    this checker only looks at decision/fields/unsupported consistency.
    """

    violations: list[str] = []

    decision = envelope.get("decision")
    missing_fields = envelope.get("missing_fields", [])
    unsupported = envelope.get("unsupported_requests", [])
    extracted = envelope.get("extracted_parameters", {})
    evidence = envelope.get("evidence", [])

    # Invariant 1: missing_fields non-empty => decision != answer
    if isinstance(missing_fields, list) and len(missing_fields) > 0:
        if decision == ANSWER:
            violations.append(
                "decision=answer but missing_fields is non-empty; "
                "a missing required field means construction cannot proceed"
            )

    # Invariant 2: unsupported_requests non-empty => decision != answer
    if isinstance(unsupported, list) and len(unsupported) > 0:
        if decision == ANSWER:
            violations.append(
                "decision=answer but unsupported_requests is non-empty; "
                "unsupported features block construction"
            )

    # Invariant 3: decision=answer => bore_d present and in range 5-80
    if decision == ANSWER:
        if not isinstance(extracted, Mapping) or "bore_d" not in extracted:
            violations.append(
                "decision=answer but bore_d is absent from extracted_parameters; "
                "bore_d is required for construction"
            )
        else:
            bore_val = extracted.get("bore_d")
            if isinstance(bore_val, Mapping) and "value" in bore_val:
                bore_num = bore_val["value"]
            else:
                bore_num = bore_val
            if not isinstance(bore_num, (int, float)) or isinstance(bore_num, bool):
                violations.append(
                    "decision=answer but bore_d is not a valid number"
                )
            elif not (CATALOG_BORE_D_MIN <= bore_num <= CATALOG_BORE_D_MAX):
                violations.append(
                    f"decision=answer but bore_d={bore_num} is outside "
                    f"catalog range {CATALOG_BORE_D_MIN}-{CATALOG_BORE_D_MAX}"
                )

    # Invariant 4: each unsupported request has corresponding evidence
    if isinstance(unsupported, list) and isinstance(evidence, list):
        evidence_fields = {
            entry.get("field")
            for entry in evidence
            if isinstance(entry, Mapping)
        }
        for item in unsupported:
            if isinstance(item, str) and item not in evidence_fields:
                violations.append(
                    f"unsupported_requests contains '{item}' but no evidence "
                    f"entry has field='{item}'; each unsupported request needs "
                    f"corresponding evidence"
                )

    return ConsistencyResult(ok=len(violations) == 0, violations=tuple(violations))


# ---------------------------------------------------------------------------
# Field claim preservation check
# ---------------------------------------------------------------------------


def check_claim_preservation(
    extracted_parameters: Mapping[str, Any],
    explicit_claims: Mapping[str, Any],
) -> ConsistencyResult:
    """Check that explicit user claims are preserved without silent changes.

    The v3 policy (and v2 before it) requires that explicit user claims be
    preserved even when they conflict with catalog or family rules.  This
    function verifies that each explicit claim value appears unchanged in
    the extracted parameters, after unit normalization for length fields.

    ``explicit_claims`` are the evaluator-only labels from the acceptance set
    (already normalized to mm).  ``extracted_parameters`` is the model's
    output.  Length fields may be bare numbers or ``{value, unit}`` objects.
    """

    violations: list[str] = []

    for field_name, expected_value in explicit_claims.items():
        if field_name not in extracted_parameters:
            violations.append(
                f"explicit claim '{field_name}' is missing from extracted_parameters; "
                f"expected {expected_value}"
            )
            continue

        actual_raw = extracted_parameters[field_name]
        # Normalize measurement objects to bare mm values.
        if isinstance(actual_raw, Mapping) and "value" in actual_raw:
            actual_value = actual_raw["value"]
        else:
            actual_value = actual_raw

        if isinstance(actual_value, bool) or not isinstance(actual_value, (int, float)):
            violations.append(
                f"explicit claim '{field_name}' has non-numeric value {actual_value!r}; "
                f"expected {expected_value}"
            )
            continue

        if actual_value != expected_value:
            violations.append(
                f"explicit claim '{field_name}' was silently changed: "
                f"expected {expected_value}, got {actual_value}"
            )

    return ConsistencyResult(ok=len(violations) == 0, violations=tuple(violations))


# ---------------------------------------------------------------------------
# Prompt interface compatibility check (static)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterfaceCompatResult:
    """Result of checking the v3 prompt file against the frozen I/O contract."""

    ok: bool
    contract_version: str
    prompt_version: str
    envelope_keys: tuple[str, ...]
    decision_values_found: tuple[str, ...]
    violations: tuple[str, ...]


def check_prompt_interface_compatibility(
    prompt_path: Path = CANDIDATE_PROMPT_PATH,
) -> InterfaceCompatResult:
    """Statically check the v3 candidate prompt file against the frozen contract.

    This parses the prompt markdown text (no model calls) and verifies:

    1. The JSON envelope example has the same key set as ``ENVELOPE_KEYS``.
    2. ``contract_version`` is ``app001-io.v1`` (same I/O contract).
    3. ``prompt_version`` is ``app001-extraction.v3`` (candidate, not v2).
    4. The decision value in the example is in ``DECISION_VALUES``.
    5. The ``EXTRACTABLE_FIELDS`` mentioned match the frozen set.
    6. Evidence source values match ``EVIDENCE_SOURCE_VALUES``.
    """

    violations: list[str] = []
    contract_version = ""
    prompt_version = ""
    envelope_keys: tuple[str, ...] = ()
    decision_values_found: list[str] = []

    try:
        text = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return InterfaceCompatResult(
            ok=False,
            contract_version="",
            prompt_version="",
            envelope_keys=(),
            decision_values_found=(),
            violations=(f"candidate prompt file not found at {prompt_path}",),
        )

    # Extract the first JSON envelope example from the prompt.
    json_blocks = re.findall(r"```json\s*\n(.*?)```", text, re.DOTALL)
    if not json_blocks:
        return InterfaceCompatResult(
            ok=False,
            contract_version="",
            prompt_version="",
            envelope_keys=(),
            decision_values_found=(),
            violations=("no JSON code block found in candidate prompt",),
        )

    try:
        envelope = json.loads(json_blocks[0].strip())
    except json.JSONDecodeError as exc:
        return InterfaceCompatResult(
            ok=False,
            contract_version="",
            prompt_version="",
            envelope_keys=(),
            decision_values_found=(),
            violations=(f"JSON envelope example is invalid: {exc}",),
        )

    if not isinstance(envelope, Mapping):
        violations.append("JSON envelope example is not a JSON object")
    else:
        actual_keys = set(envelope.keys())
        envelope_keys = tuple(sorted(actual_keys))

        # Check 1: envelope key set matches frozen contract.
        missing_keys = ENVELOPE_KEYS - actual_keys
        extra_keys = actual_keys - ENVELOPE_KEYS
        if missing_keys:
            violations.append(
                f"envelope missing key(s): {sorted(missing_keys)}"
            )
        if extra_keys:
            violations.append(
                f"envelope has unexpected key(s): {sorted(extra_keys)}"
            )

        # Check 2: contract_version.
        contract_version = str(envelope.get("contract_version", ""))
        if contract_version != CONTRACT_VERSION:
            violations.append(
                f"contract_version is {contract_version!r}, expected {CONTRACT_VERSION!r}"
            )

        # Check 3: prompt_version.
        prompt_version = str(envelope.get("prompt_version", ""))
        if prompt_version != CANDIDATE_PROMPT_VERSION:
            violations.append(
                f"prompt_version is {prompt_version!r}, expected {CANDIDATE_PROMPT_VERSION!r}"
            )

        # Check 4: decision value in example.
        decision = envelope.get("decision")
        decision_values_found = [str(decision)] if decision is not None else []
        if decision not in DECISION_VALUES:
            violations.append(
                f"decision in example is {decision!r}, not in {sorted(DECISION_VALUES)}"
            )

    # Check 5: extractable fields mentioned in prompt match frozen set.
    for field_name in EXTRACTABLE_FIELDS:
        if field_name not in text:
            violations.append(
                f"extractable field '{field_name}' not mentioned in prompt text"
            )

    # Check 6: evidence source values.
    for source_val in EVIDENCE_SOURCE_VALUES:
        if f'"{source_val}"' not in text and f"'{source_val}'" not in text:
            violations.append(
                f"evidence source value '{source_val}' not found in prompt text"
            )

    return InterfaceCompatResult(
        ok=len(violations) == 0,
        contract_version=contract_version,
        prompt_version=prompt_version,
        envelope_keys=envelope_keys,
        decision_values_found=tuple(decision_values_found),
        violations=tuple(violations),
    )


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------


def is_catalog_bore_d(value: float | int) -> bool:
    """True when ``value`` is one of the 15 frozen GN 705 catalog bore_d values."""
    return value in _CATALOG_BORE_D_VALUES


def is_in_range(value: float | int) -> bool:
    """True when ``value`` is within the catalog range 5-80 mm (inclusive)."""
    return CATALOG_BORE_D_MIN <= value <= CATALOG_BORE_D_MAX
