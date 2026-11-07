"""Offline checks for the unactivated APP-001 decision policy v4 candidate.

These tests validate candidate wording and frozen-interface boundaries only;
they do not simulate or claim model compliance.
"""

import hashlib
import json
import unittest
from pathlib import Path

from src.llm.decision_policy_v4_candidate import (
    CandidateInputError,
    V4FixtureCase,
    canonicalize_unsupported,
    evaluate_fixture,
    normalize_length_to_mm,
)


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "agent-work/llm/APP-001-baseline-prep"
ACTIVE = ROOT / "agent-work/llm/APP-001-v3-activation/prompt-v3.md"
ACCEPTANCE = BASELINE / "acceptance-set-v0.json"
PROMPT_V4 = BASELINE / "prompt-v4-candidate.md"
POLICY_V4 = BASELINE / "decision-policy-v4-candidate.md"


class TestV4CandidateBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prompt = PROMPT_V4.read_text(encoding="utf-8")
        cls.policy = POLICY_V4.read_text(encoding="utf-8")
        cls.acceptance_bytes = ACCEPTANCE.read_bytes()
        cls.acceptance = json.loads(cls.acceptance_bytes)

    def test_candidate_has_new_version_without_changing_active_v3(self):
        self.assertIn('"prompt_version": "app001-extraction.v4"', self.prompt)
        self.assertIn('"prompt_version": "app001-extraction.v3"', ACTIVE.read_text())

    def test_unit_conversion_rule_is_explicit_and_evidence_preserving(self):
        self.assertIn("1.6 cm", self.prompt)
        self.assertIn("16 mm", self.prompt)
        self.assertIn("does not itself require a", self.prompt)
        self.assertIn("preserve the original value and unit", self.prompt)

    def test_untrusted_retrieval_cannot_create_ambiguity(self):
        self.assertIn("Do not ask again for a parameter", self.prompt)
        self.assertIn("bore_d=24 mm", self.prompt)
        self.assertIn("retrieved example shows `bore_d=20`", self.prompt)
        self.assertIn("do not ask which value was", self.prompt)
        self.assertIn("intended", self.prompt)

    def test_unsupported_aliases_use_stable_canonical_names(self):
        self.assertIn("阳极氧化", self.prompt)
        self.assertIn("anodized", self.prompt)
        self.assertIn("use `anodizing`", self.prompt)
        self.assertIn("user's exact wording in the evidence", self.prompt)

    def test_v3_safety_gate_and_directory_reference_are_retained(self):
        self.assertIn("answer` ONLY when ALL", self.prompt)
        self.assertIn("15 catalog selectors", self.prompt)
        self.assertIn("never snap it to a nearby row", self.prompt)
        self.assertIn("CAD-003", self.prompt)

    def test_candidate_policy_maps_observed_errors_to_expected_cases(self):
        for text in (
            "A03 C0/C1", "A08 C1", "A07 C0", "bore_d=75",
            "A01/A02/A06", "A04/A05/A09",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.policy)

    def test_frozen_acceptance_set_is_unchanged_and_v3_versioned(self):
        self.assertEqual(self.acceptance["frozen_prompt_version"], "app001-extraction.v2")
        self.assertEqual(self.acceptance["sample_count"], 9)
        self.assertEqual(
            hashlib.sha256(self.acceptance_bytes).hexdigest(),
            "ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf",
        )

    def test_candidate_does_not_claim_model_effect_or_authorize_a_run(self):
        self.assertIn("不能证明模型会遵循指令", self.policy)
        self.assertIn("单独授权", self.policy)

    def test_non_catalog_wording_covers_in_range_75(self):
        self.assertIn("not one of the 15 discrete catalog selectors", self.prompt)
        self.assertIn("such as `75 mm`", self.prompt)


class TestV4ExecutableOfflineChecker(unittest.TestCase):
    def test_exact_cm_conversion_preserves_evidence(self):
        result = normalize_length_to_mm(1.6, "cm", "轴孔直径 1.6 cm")
        self.assertEqual(result.value_mm, 16)
        self.assertEqual(result.evidence_quote, "轴孔直径 1.6 cm")
        self.assertEqual(evaluate_fixture(V4FixtureCase(1.6, "cm")).decision_options, {"answer"})

    def test_fractional_conversion_does_not_fake_catalog_membership(self):
        result = evaluate_fixture(V4FixtureCase(1.65, "cm"))
        self.assertNotIn("answer", result.decision_options)

    def test_user_bore_wins_over_untrusted_retrieval_reference(self):
        result = evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=20))
        self.assertEqual(result.normalized_bore.value_mm, 24)
        self.assertEqual(result.decision_options, {"answer"})

    def test_unsupported_aliases_are_stable(self):
        self.assertEqual(canonicalize_unsupported("阳极氧化"), "anodizing")
        self.assertEqual(canonicalize_unsupported("anodized"), "anodizing")
        result = evaluate_fixture(V4FixtureCase(75, unsupported_terms=("阳极氧化",)))
        self.assertEqual(result.unsupported_labels, ("anodizing",))
        self.assertEqual(result.decision_options, {"refuse"})

    def test_in_range_non_catalog_75_is_refused(self):
        result = evaluate_fixture(V4FixtureCase(75))
        self.assertEqual(result.decision_options, {"refuse"})
        self.assertFalse(result.answer_allowed)

    def test_missing_bore_cannot_answer(self):
        result = evaluate_fixture(V4FixtureCase())
        self.assertNotIn("answer", result.decision_options)
        self.assertIn("ask", result.decision_options)

    def test_catalog_conflict_cannot_answer(self):
        result = evaluate_fixture(V4FixtureCase(20, catalog_conflict=True))
        self.assertNotIn("answer", result.decision_options)

    def test_rule_conflict_cannot_answer(self):
        result = evaluate_fixture(V4FixtureCase(80, rule_conflict=True))
        self.assertNotIn("answer", result.decision_options)

    def test_unknown_unit_fails_closed(self):
        with self.assertRaises(CandidateInputError):
            normalize_length_to_mm(16, "inch")


class TestV4RetrievalIsolation(unittest.TestCase):
    """Tests that the user's explicit bore_d controls and retrieval context
    is never promoted to a user claim.

    These tests include reverse assertions that would fail if the
    implementation erroneously selected the retrieval value.
    """

    def test_user_bore_24_wins_over_retrieval_20(self):
        """User bore_d=24 controls even when retrieval shows 20."""
        result = evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=20))
        self.assertEqual(result.normalized_bore.value_mm, 24)
        self.assertIn("answer", result.decision_options)

    def test_retrieval_noncatalog_does_not_override_user_catalog(self):
        """Reverse test: retrieval=75 (non-catalog) would give ``refuse`` if
        promoted; user=24 (catalog) gives ``answer``.  Asserting ``answer``
        catches an implementation that erroneously selects retrieval."""
        result = evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=75))
        self.assertIn("answer", result.decision_options)
        self.assertNotIn("refuse", result.decision_options)
        self.assertEqual(result.normalized_bore.value_mm, 24)

    def test_user_missing_retrieval_present_no_answer(self):
        """Reverse test: user bore missing, retrieval=20 is catalog.  If
        retrieval were promoted, ``answer`` would be allowed.  Correct
        behavior: bore_d missing → answer is NOT allowed."""
        result = evaluate_fixture(
            V4FixtureCase(bore_value=None, retrieval_bore_value=20)
        )
        self.assertIsNone(result.normalized_bore)
        self.assertNotIn("answer", result.decision_options)

    def test_user_missing_retrieval_present_ask_allowed(self):
        """When user bore is missing and retrieval is present, ``ask`` is
        appropriate because the user can still supply bore_d."""
        result = evaluate_fixture(
            V4FixtureCase(bore_value=None, retrieval_bore_value=20)
        )
        self.assertIn("ask", result.decision_options)

    def test_retrieval_catalog_value_not_promoted_to_user_claim(self):
        """Strong reverse test: retrieval=24 is a valid catalog value, but
        the user did not state bore_d.  If retrieval were promoted,
        ``normalized_bore`` would be 24 and ``answer`` would be allowed.
        Correct behavior: ``normalized_bore`` is None."""
        result = evaluate_fixture(
            V4FixtureCase(bore_value=None, retrieval_bore_value=24)
        )
        self.assertIsNone(result.normalized_bore)
        self.assertNotIn("answer", result.decision_options)

    def test_retrieval_acknowledged_when_present(self):
        """When a retrieval value is provided, it is tracked for audit but
        not promoted."""
        result = evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=20))
        self.assertTrue(result.retrieval_acknowledged)
        self.assertEqual(result.retrieval_bore_raw, 20)

    def test_retrieval_not_acknowledged_when_absent(self):
        """When no retrieval value is provided, ``retrieval_acknowledged``
        is False and ``retrieval_bore_raw`` is None."""
        result = evaluate_fixture(V4FixtureCase(24, "mm"))
        self.assertFalse(result.retrieval_acknowledged)
        self.assertIsNone(result.retrieval_bore_raw)

    def test_resolve_bore_precedence_returns_user_when_present(self):
        """The pure function returns the user bore when present, ignoring
        retrieval entirely."""
        from src.llm.decision_policy_v4_candidate import resolve_bore_precedence

        user_bore = normalize_length_to_mm(24, "mm", "bore_d=24 mm")
        result = resolve_bore_precedence(user_bore, retrieval_bore_value=20)
        self.assertIs(result, user_bore)
        self.assertEqual(result.value_mm, 24)

    def test_resolve_bore_precedence_returns_none_when_user_absent(self):
        """The pure function returns None when user bore is absent, even if
        retrieval has a value."""
        from src.llm.decision_policy_v4_candidate import resolve_bore_precedence

        result = resolve_bore_precedence(None, retrieval_bore_value=20)
        self.assertIsNone(result)


class TestV4UnsupportedEvidenceQuote(unittest.TestCase):
    """Tests that unsupported spec labels are canonicalized while preserving
    the user's original wording as an evidence quote with source=user_input.
    """

    def test_chinese_anodizing_maps_to_canonical_label(self):
        """阳极氧化 canonicalizes to ``anodizing``."""
        result = evaluate_fixture(V4FixtureCase(unsupported_terms=("阳极氧化",)))
        self.assertEqual(len(result.unsupported_evidence), 1)
        ev = result.unsupported_evidence[0]
        self.assertEqual(ev.canonical_label, "anodizing")

    def test_original_quote_preserves_chinese_not_canonical(self):
        """The evidence quote preserves ``阳极氧化``, not the canonical
        ``anodizing``."""
        result = evaluate_fixture(V4FixtureCase(unsupported_terms=("阳极氧化",)))
        ev = result.unsupported_evidence[0]
        self.assertEqual(ev.original_quote, "阳极氧化")
        self.assertNotEqual(ev.original_quote, ev.canonical_label)

    def test_evidence_source_is_user_input(self):
        """source must be ``user_input`` — retrieval cannot create
        unsupported items."""
        result = evaluate_fixture(
            V4FixtureCase(unsupported_terms=("阳极氧化", "法兰"))
        )
        for ev in result.unsupported_evidence:
            self.assertEqual(ev.source, "user_input")

    def test_anodized_variant_preserves_original_quote(self):
        """``anodized`` maps to ``anodizing`` but the quote stays
        ``anodized``."""
        result = evaluate_fixture(V4FixtureCase(unsupported_terms=("anodized",)))
        ev = result.unsupported_evidence[0]
        self.assertEqual(ev.canonical_label, "anodizing")
        self.assertEqual(ev.original_quote, "anodized")

    def test_no_fabricated_unsupported_items_when_none_requested(self):
        """When the user does not request any unsupported feature, the
        evidence list is empty."""
        result = evaluate_fixture(V4FixtureCase(24, "mm"))
        self.assertEqual(len(result.unsupported_evidence), 0)
        self.assertEqual(len(result.unsupported_labels), 0)

    def test_canonical_labels_match_evidence_labels(self):
        """``unsupported_labels`` and the canonical labels from
        ``unsupported_evidence`` are consistent."""
        result = evaluate_fixture(
            V4FixtureCase(unsupported_terms=("阳极氧化", "法兰"))
        )
        evidence_labels = tuple(ev.canonical_label for ev in result.unsupported_evidence)
        self.assertEqual(evidence_labels, result.unsupported_labels)

    def test_multiple_unsupported_items_each_have_evidence(self):
        """Each unsupported item gets its own evidence entry with the
        original quote."""
        result = evaluate_fixture(
            V4FixtureCase(unsupported_terms=("阳极氧化", "法兰", "键槽"))
        )
        self.assertEqual(len(result.unsupported_evidence), 3)
        quotes = {ev.original_quote for ev in result.unsupported_evidence}
        self.assertEqual(quotes, {"阳极氧化", "法兰", "键槽"})
        labels = {ev.canonical_label for ev in result.unsupported_evidence}
        self.assertEqual(labels, {"anodizing", "flange", "keyway"})


if __name__ == "__main__":
    unittest.main()
