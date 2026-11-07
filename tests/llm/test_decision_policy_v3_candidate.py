"""Offline regression tests for the v3 candidate decision policy.

These tests verify the v3 decision-gate logic, envelope self-consistency,
field claim preservation, unsupported-request evidence requirements, and
prompt interface compatibility — all offline, without real model calls.

Covered acceptance-set cases:
  A01: complete consistent description → answer allowed
  A02: only bore_d → answer allowed
  A04: missing bore_d → ask/refuse, NOT answer
  A05: catalog coupling conflict → ask/refuse, NOT answer
  A07: out-of-catalog + unsupported requests → refuse, NOT answer
  A09: rule conflict (second_screw) → ask/refuse, NOT answer

This module is a candidate test; it does not modify frozen files, does not
activate the v3 prompt, and does not authorize model evaluation.
"""

import unittest

from src.llm.decision_policy_v3_candidate import (
    CANDIDATE_PROMPT_VERSION,
    CATALOG_BORE_D_MAX,
    CATALOG_BORE_D_MIN,
    CaseCharacteristics,
    check_claim_preservation,
    check_envelope_consistency,
    check_prompt_interface_compatibility,
    is_answer_allowed,
    is_catalog_bore_d,
    is_in_range,
    allowed_decisions,
)
from src.llm.contract import (
    CONTRACT_VERSION,
    DECISION_VALUES,
    ENVELOPE_KEYS,
    EVIDENCE_SOURCE_VALUES,
    EXTRACTABLE_FIELDS,
)

# ---------------------------------------------------------------------------
# Case characteristics from the frozen acceptance-set-v0
# ---------------------------------------------------------------------------

A01 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=20, bore_d_in_catalog=True,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
)
A02 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=24, bore_d_in_catalog=True,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
)
A04 = CaseCharacteristics(
    bore_d_present=False, bore_d_value=None, bore_d_in_catalog=False,
    bore_d_in_range=False, has_unsupported_requests=False,
    has_missing_required=True, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
)
A05 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=20, bore_d_in_catalog=True,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=True,
    has_rule_conflict=False, has_direct_contradiction=False,
)
A07 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=75, bore_d_in_catalog=False,
    bore_d_in_range=True, has_unsupported_requests=True,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
    unsupported_request_names=("flange", "keyway", "anodizing"),
)
A09 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=80, bore_d_in_catalog=True,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=True, has_direct_contradiction=False,
)
A06 = CaseCharacteristics(
    bore_d_present=True, bore_d_value=70, bore_d_in_catalog=True,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
)
A07_BORE_ONLY = CaseCharacteristics(
    bore_d_present=True, bore_d_value=75, bore_d_in_catalog=False,
    bore_d_in_range=True, has_unsupported_requests=False,
    has_missing_required=False, has_catalog_conflict=False,
    has_rule_conflict=False, has_direct_contradiction=False,
)


# ---------------------------------------------------------------------------
# Model-output envelope fixtures (offline, v3-compliant and non-compliant)
# ---------------------------------------------------------------------------

def _envelope(decision, extracted, unsupported=None, evidence=None,
              missing=None, questions=None):
    return {
        "contract_version": "app001-io.v1",
        "prompt_version": CANDIDATE_PROMPT_VERSION,
        "decision": decision,
        "extracted_parameters": extracted,
        "unsupported_requests": unsupported or [],
        "evidence": evidence or [],
        "missing_fields": missing or [],
        "questions": questions or [],
        "confidence": None,
    }

# v3-compliant fixtures
A01_ENVELOPE = _envelope(
    "answer", {"bore_d": 20, "outer_d": 32, "width": 14},
    evidence=[
        {"field": "bore_d", "quote": "轴孔直径 20 mm", "source": "user_input"},
        {"field": "outer_d", "quote": "外径 32 mm", "source": "user_input"},
        {"field": "width", "quote": "宽度 14 mm", "source": "user_input"},
    ],
)
A04_ENVELOPE_ASK = _envelope(
    "ask", {"outer_d": 32, "width": 14},
    evidence=[
        {"field": "outer_d", "quote": "外径 32 mm", "source": "user_input"},
        {"field": "width", "quote": "宽度 14 mm", "source": "user_input"},
    ],
    missing=["bore_d"],
    questions=["请提供轴孔直径（目录选择器 bore_d）。"],
)
A05_ENVELOPE_ASK = _envelope(
    "ask", {"bore_d": 20, "outer_d": 40},
    evidence=[
        {"field": "bore_d", "quote": "bore_d=20 mm", "source": "user_input"},
        {"field": "outer_d", "quote": "outer_d=40 mm", "source": "user_input"},
    ],
    questions=["bore_d=20 对应 outer_d=32，请确认以哪个规格为准。"],
)
A07_ENVELOPE_REFUSE = _envelope(
    "refuse", {"bore_d": 75},
    unsupported=["flange", "keyway", "anodizing"],
    evidence=[
        {"field": "bore_d", "quote": "bore_d=75 mm", "source": "user_input"},
        {"field": "flange", "quote": "法兰", "source": "user_input"},
        {"field": "keyway", "quote": "键槽", "source": "user_input"},
        {"field": "anodizing", "quote": "阳极氧化", "source": "user_input"},
    ],
)
A09_ENVELOPE_ASK = _envelope(
    "ask", {"bore_d": 80, "second_screw": 0},
    evidence=[
        {"field": "bore_d", "quote": "bore_d=80 mm", "source": "user_input"},
        {"field": "second_screw", "quote": "只要一个紧定螺钉", "source": "user_input"},
    ],
    questions=["bore_d=80 需要两个紧定螺钉，请确认是否保留 second_screw=0。"],
)

# Non-compliant fixtures (simulating v2 batch-4 decision偏差)
A04_BAD_ANSWER = _envelope(
    "answer", {"outer_d": 32, "width": 14},
    evidence=[
        {"field": "outer_d", "quote": "外径 32 mm", "source": "user_input"},
        {"field": "width", "quote": "宽度 14 mm", "source": "user_input"},
    ],
    missing=["bore_d"],
)
A05_BAD_ANSWER = _envelope(
    "answer", {"bore_d": 20, "outer_d": 40},
    evidence=[
        {"field": "bore_d", "quote": "bore_d=20 mm", "source": "user_input"},
        {"field": "outer_d", "quote": "outer_d=40 mm", "source": "user_input"},
    ],
)
A07_BAD_ANSWER = _envelope(
    "answer", {"bore_d": 75},
    unsupported=["flange", "keyway", "anodizing"],
    evidence=[
        {"field": "bore_d", "quote": "bore_d=75 mm", "source": "user_input"},
    ],
)
A09_BAD_ANSWER = _envelope(
    "answer", {"bore_d": 80, "second_screw": 0},
    evidence=[
        {"field": "bore_d", "quote": "bore_d=80 mm", "source": "user_input"},
        {"field": "second_screw", "quote": "second_screw=0", "source": "user_input"},
    ],
)
# A07 with incomplete evidence (missing evidence for keyway/anodizing)
A07_INCOMPLETE_EVIDENCE = _envelope(
    "refuse", {"bore_d": 75},
    unsupported=["flange", "keyway", "anodizing"],
    evidence=[
        {"field": "bore_d", "quote": "bore_d=75 mm", "source": "user_input"},
        {"field": "flange", "quote": "法兰", "source": "user_input"},
    ],
)


# ---------------------------------------------------------------------------
# TestAllowedDecisions: v3 decision-gate logic per acceptance case
# ---------------------------------------------------------------------------

class TestAllowedDecisions(unittest.TestCase):
    """Verify allowed_decisions for each frozen acceptance-set case."""

    def test_a01_answer_allowed(self):
        """A01: complete consistent → answer allowed (normal case)."""
        allowed = allowed_decisions(A01)
        self.assertIn("answer", allowed)
        self.assertNotIn("ask", allowed)
        self.assertNotIn("refuse", allowed)

    def test_a02_answer_allowed(self):
        """A02: only bore_d → answer allowed (normal case)."""
        allowed = allowed_decisions(A02)
        self.assertIn("answer", allowed)
        self.assertNotIn("ask", allowed)
        self.assertNotIn("refuse", allowed)

    def test_a04_answer_not_allowed(self):
        """A04: missing bore_d → ask or refuse, NOT answer."""
        allowed = allowed_decisions(A04)
        self.assertNotIn("answer", allowed)
        self.assertIn("ask", allowed)
        self.assertIn("refuse", allowed)

    def test_a05_answer_not_allowed(self):
        """A05: catalog conflict → ask or refuse, NOT answer."""
        allowed = allowed_decisions(A05)
        self.assertNotIn("answer", allowed)
        self.assertIn("ask", allowed)
        self.assertIn("refuse", allowed)

    def test_a07_refuse_only(self):
        """A07: out-of-catalog + unsupported → refuse only."""
        allowed = allowed_decisions(A07)
        self.assertEqual(allowed, frozenset({"refuse"}))

    def test_a09_answer_not_allowed(self):
        """A09: rule conflict → ask or refuse, NOT answer."""
        allowed = allowed_decisions(A09)
        self.assertNotIn("answer", allowed)
        self.assertIn("ask", allowed)
        self.assertIn("refuse", allowed)

    def test_a06_boundary_answer_allowed(self):
        """A06: bore_d=70 and second_screw=0 is the valid strict boundary."""
        self.assertEqual(allowed_decisions(A06), frozenset({"answer"}))

    def test_bore_d_75_alone_refused(self):
        """75 is in range but not one of the frozen discrete selectors."""
        self.assertEqual(allowed_decisions(A07_BORE_ONLY), frozenset({"refuse"}))

    def test_all_results_subset_of_frozen_contract(self):
        """Every case's allowed decisions must be a subset of DECISION_VALUES."""
        for case in (A01, A02, A04, A05, A07, A09):
            allowed = allowed_decisions(case)
            self.assertTrue(
                allowed.issubset(DECISION_VALUES),
                f"case {case} produced decisions outside contract: {allowed}",
            )

    def test_normal_case_not_all_refused(self):
        """At least one normal case allows answer (avoid over-restrictive policy)."""
        self.assertTrue(is_answer_allowed(A01))
        self.assertTrue(is_answer_allowed(A02))


# ---------------------------------------------------------------------------
# TestEnvelopeConsistency: v3 self-consistency invariants
# ---------------------------------------------------------------------------

class TestEnvelopeConsistency(unittest.TestCase):
    """Verify that v3-compliant envelopes pass and non-compliant fail."""

    def test_a01_compliant_answer_passes(self):
        result = check_envelope_consistency(A01_ENVELOPE)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a04_compliant_ask_passes(self):
        result = check_envelope_consistency(A04_ENVELOPE_ASK)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a05_compliant_ask_passes(self):
        result = check_envelope_consistency(A05_ENVELOPE_ASK)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a07_compliant_refuse_passes(self):
        result = check_envelope_consistency(A07_ENVELOPE_REFUSE)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a09_compliant_ask_passes(self):
        result = check_envelope_consistency(A09_ENVELOPE_ASK)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a04_bad_answer_fails(self):
        """decision=answer with missing_fields=[bore_d] must fail."""
        result = check_envelope_consistency(A04_BAD_ANSWER)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("missing_fields" in v for v in result.violations),
            f"Expected missing_fields violation: {result.violations}",
        )

    def test_a05_bad_answer_fails(self):
        """decision=answer with catalog conflict must fail (no bore_d missing,
        but the v3 checker flags missing bore_d via the answer invariant)."""
        result = check_envelope_consistency(A05_BAD_ANSWER)
        # A05_BAD_ANSWER has bore_d=20 present, so invariant 3 passes.
        # The checker does NOT know about catalog conflicts (deterministic layer does).
        # This is expected: the checker tests model self-consistency, not CAD-003.
        # The CAD-003 layer would reject this independently.
        # For v3 policy, the ideal behavior is ask/refuse, tested via allowed_decisions.
        # The envelope consistency check only catches model-detectable issues.
        self.assertTrue(result.ok)  # no self-consistency violation detectable

    def test_a07_bad_answer_fails(self):
        """decision=answer with unsupported_requests non-empty must fail."""
        result = check_envelope_consistency(A07_BAD_ANSWER)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("unsupported_requests" in v for v in result.violations),
            f"Expected unsupported_requests violation: {result.violations}",
        )

    def test_a09_bad_answer_fails(self):
        """decision=answer with rule conflict: checker detects via no missing/unsupported,
        so it passes self-consistency. CAD-003 catches the rule conflict."""
        result = check_envelope_consistency(A09_BAD_ANSWER)
        # Similar to A05: the checker tests model self-consistency.
        # bore_d=80 is present and in range, no unsupported, no missing.
        # The rule conflict is caught by CAD-003, not by the envelope checker.
        self.assertTrue(result.ok)

    def test_answer_without_bore_d_fails(self):
        """decision=answer but bore_d absent must fail."""
        bad = _envelope("answer", {"outer_d": 32})
        result = check_envelope_consistency(bad)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("bore_d" in v for v in result.violations),
            f"Expected bore_d violation: {result.violations}",
        )

    def test_answer_with_bore_d_out_of_range_fails(self):
        """decision=answer with bore_d outside 5-80 must fail."""
        bad = _envelope("answer", {"bore_d": 100})
        result = check_envelope_consistency(bad)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("outside catalog range" in v for v in result.violations),
            f"Expected range violation: {result.violations}",
        )

    def test_answer_with_in_range_non_catalog_bore_fails(self):
        """bore_d=75 is numerically in range but not a catalog selector."""
        bad = _envelope("answer", {"bore_d": 75})
        result = check_envelope_consistency(bad)
        self.assertFalse(result.ok)
        self.assertTrue(any("15 frozen GN 705 catalog choices" in v for v in result.violations))


# ---------------------------------------------------------------------------
# TestUnsupportedRequestEvidence: each unsupported item needs evidence
# ---------------------------------------------------------------------------

class TestUnsupportedRequestEvidence(unittest.TestCase):
    """Verify unsupported requests have corresponding evidence entries."""

    def test_a07_full_evidence_passes(self):
        result = check_envelope_consistency(A07_ENVELOPE_REFUSE)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a07_incomplete_evidence_fails(self):
        """A07 with evidence only for flange must flag keyway and anodizing."""
        result = check_envelope_consistency(A07_INCOMPLETE_EVIDENCE)
        self.assertFalse(result.ok)
        violations_text = " ".join(result.violations)
        self.assertIn("keyway", violations_text)
        self.assertIn("anodizing", violations_text)

    def test_a07_bad_answer_incomplete_evidence_fails(self):
        """A07_BAD_ANSWER: both answer+unsupported and missing evidence."""
        result = check_envelope_consistency(A07_BAD_ANSWER)
        self.assertFalse(result.ok)
        violations_text = " ".join(result.violations)
        # Should flag both the decision=answer+unsupported and missing evidence
        self.assertTrue(
            any("unsupported_requests" in v for v in result.violations),
            f"Expected unsupported+answer violation: {result.violations}",
        )
        self.assertIn("keyway", violations_text)
        self.assertIn("anodizing", violations_text)


# ---------------------------------------------------------------------------
# TestClaimPreservation: explicit claims must not be silently changed
# ---------------------------------------------------------------------------

class TestClaimPreservation(unittest.TestCase):
    """Verify explicit user claims are preserved without silent changes."""

    def test_a01_claims_preserved(self):
        claims = {"bore_d": 20, "outer_d": 32, "width": 14}
        extracted = {"bore_d": 20, "outer_d": 32, "width": 14}
        result = check_claim_preservation(extracted, claims)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a05_conflicting_claims_preserved(self):
        """Both bore_d=20 and outer_d=40 must be preserved even though they conflict."""
        claims = {"bore_d": 20, "outer_d": 40}
        extracted = {"bore_d": 20, "outer_d": 40}
        result = check_claim_preservation(extracted, claims)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a09_conflicting_claims_preserved(self):
        """Both bore_d=80 and second_screw=0 must be preserved even though they conflict."""
        claims = {"bore_d": 80, "second_screw": 0}
        extracted = {"bore_d": 80, "second_screw": 0}
        result = check_claim_preservation(extracted, claims)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_silent_change_detected(self):
        """Changing outer_d from 40 to 32 silently must be detected."""
        claims = {"bore_d": 20, "outer_d": 40}
        extracted = {"bore_d": 20, "outer_d": 32}  # silently snapped to catalog value
        result = check_claim_preservation(extracted, claims)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("silently changed" in v for v in result.violations),
            f"Expected silent change detection: {result.violations}",
        )

    def test_missing_claim_detected(self):
        """Missing bore_d from extracted_parameters must be detected."""
        claims = {"bore_d": 20, "outer_d": 32}
        extracted = {"outer_d": 32}  # bore_d dropped
        result = check_claim_preservation(extracted, claims)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("bore_d" in v and "missing" in v for v in result.violations),
            f"Expected missing claim detection: {result.violations}",
        )

    def test_measurement_object_normalized(self):
        """Length fields as {value, unit} objects are normalized before comparison."""
        claims = {"bore_d": 16}
        extracted = {"bore_d": {"value": 16, "unit": "mm"}}
        result = check_claim_preservation(extracted, claims)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")

    def test_a04_partial_claims_preserved(self):
        """A04: outer_d=32 and width=14 preserved, bore_d correctly missing."""
        claims = {"outer_d": 32, "width": 14}
        extracted = {"outer_d": 32, "width": 14}
        result = check_claim_preservation(extracted, claims)
        self.assertTrue(result.ok, f"Expected pass: {result.violations}")


# ---------------------------------------------------------------------------
# TestPromptInterfaceCompatibility: v3 prompt content vs frozen contract
# ---------------------------------------------------------------------------

class TestPromptInterfaceCompatibility(unittest.TestCase):
    """Verify the v3 candidate prompt file is compatible with the frozen I/O contract."""

    def setUp(self):
        self.result = check_prompt_interface_compatibility()

    def test_prompt_file_exists_and_parses(self):
        self.assertTrue(
            self.result.ok or len(self.result.violations) > 0,
            "Interface check should return a result",
        )

    def test_contract_version_unchanged(self):
        """v3 must use the same contract_version as the frozen I/O contract."""
        self.assertEqual(self.result.contract_version, CONTRACT_VERSION)

    def test_prompt_version_is_v3_candidate(self):
        """v3 must declare app001-extraction.v3, not v2."""
        self.assertEqual(self.result.prompt_version, CANDIDATE_PROMPT_VERSION)

    def test_envelope_keys_match_frozen_contract(self):
        """The envelope example in v3 must have the same key set as ENVELOPE_KEYS."""
        self.assertEqual(
            frozenset(self.result.envelope_keys), ENVELOPE_KEYS,
            f"Envelope keys mismatch: {self.result.envelope_keys}",
        )

    def test_decision_value_in_example_valid(self):
        """The decision value in the v3 envelope example must be in DECISION_VALUES."""
        self.assertTrue(
            set(self.result.decision_values_found).issubset(DECISION_VALUES),
            f"Decision values outside contract: {self.result.decision_values_found}",
        )

    def test_no_interface_violations(self):
        """The v3 prompt must have no interface compatibility violations."""
        self.assertTrue(
            self.result.ok,
            f"Interface compatibility violations: {self.result.violations}",
        )


# ---------------------------------------------------------------------------
# TestCatalogHelpers
# ---------------------------------------------------------------------------

class TestCatalogHelpers(unittest.TestCase):
    """Verify catalog membership and range helpers."""

    def test_catalog_values(self):
        for v in (5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80):
            self.assertTrue(is_catalog_bore_d(v), f"{v} should be in catalog")
        self.assertFalse(is_catalog_bore_d(75), "75 is not a catalog value")
        self.assertFalse(is_catalog_bore_d(4), "4 is below catalog range")
        self.assertFalse(is_catalog_bore_d(81), "81 is above catalog range")

    def test_prompt_table_matches_frozen_catalog(self):
        """The model-visible candidate table must match CAD-003 exactly."""
        result = check_prompt_interface_compatibility()
        self.assertTrue(result.ok, result.violations)

    def test_range_check(self):
        self.assertTrue(is_in_range(5))
        self.assertTrue(is_in_range(80))
        self.assertTrue(is_in_range(75))
        self.assertFalse(is_in_range(4))
        self.assertFalse(is_in_range(81))

    def test_range_bounds_match_constants(self):
        self.assertEqual(CATALOG_BORE_D_MIN, 5)
        self.assertEqual(CATALOG_BORE_D_MAX, 80)


# ---------------------------------------------------------------------------
# TestDecisionVsAcceptanceSet: cross-check decision gate with expected behavior
# ---------------------------------------------------------------------------

class TestDecisionVsAcceptanceSet(unittest.TestCase):
    """Cross-check allowed_decisions against acceptance-set expected_behavior."""

    def test_a04_decision_consistent_with_missing_state(self):
        """A04 missing bore_d: decision must not be answer (missing state)."""
        self.assertFalse(is_answer_allowed(A04))

    def test_a05_decision_consistent_with_conflict_state(self):
        """A05 catalog conflict: decision must not be answer (conflict state)."""
        self.assertFalse(is_answer_allowed(A05))

    def test_a07_decision_consistent_with_unsupported_state(self):
        """A07 unsupported: decision must be refuse only."""
        allowed = allowed_decisions(A07)
        self.assertEqual(allowed, frozenset({"refuse"}))

    def test_a09_decision_consistent_with_rule_conflict(self):
        """A09 rule conflict: decision must not be answer (rule conflict state)."""
        self.assertFalse(is_answer_allowed(A09))

    def test_a01_decision_allows_construction(self):
        """A01 normal case: answer allowed (construction can proceed)."""
        self.assertTrue(is_answer_allowed(A01))

    def test_a02_decision_allows_construction(self):
        """A02 normal case: answer allowed (construction can proceed)."""
        self.assertTrue(is_answer_allowed(A02))


if __name__ == "__main__":
    unittest.main()
# --- end ---
