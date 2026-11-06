"""Tests for C0/C1 condition assembly (APP-001-PHASE1-FIX).

Verifies:
  - Valid C1 input (explicit bore_d in NLI) produces a non-blocked AssembledInput
    with correct candidate_source_ids and a non-null reference_context.
  - Missing bore_d in NLI → blocked with C1_NO_SAFE_QUERY_PARAMETER.
  - Evaluator-only label fields are never forwarded to the query.
  - assemble_c0 always returns reference_context=None regardless of input.
  - The cad003_envelope query form is used (not flat_parameters) so that
    the Schema can derive the five non-bore-d fields from bore_d.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


def _projected_case(query_id: str, nli: str, ref_struct=None):
    """Return a ProjectedCase from the real input_projection module."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from llm.input_projection import ProjectedCase

    return ProjectedCase(
        query_id=query_id,
        natural_language_input=nli,
        reference_context_structural=ref_struct,
        coverage=("bore_d",) if "bore_d" in nli.lower() or "轴孔" in nli else (),
    )


def _real_index():
    """Load the frozen RET-002 RetrievalIndex."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from retrieval import RetrievalIndex
    from retrieval.config import DEFAULT_CONFIG_REL_PATH

    return RetrievalIndex.from_config(DEFAULT_CONFIG_REL_PATH, repo_root=REPO_ROOT)


# ---------------------------------------------------------------------------
# C0 tests
# ---------------------------------------------------------------------------


class TestAssembleC0(unittest.TestCase):
    """assemble_c0 always produces a null reference context."""

    def test_c0_has_no_reference_context(self):
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c0, CONDITION_C0

        case = _projected_case("q0", "bore_d=20 mm collar")
        result = assemble_c0(case)
        self.assertEqual(result.condition_id, CONDITION_C0)
        self.assertIsNone(result.reference_context)
        self.assertIsNone(result.blocked_reason)
        self.assertEqual(result.candidate_source_ids, ())

    def test_c0_no_reference_even_when_bore_d_present(self):
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c0

        case = _projected_case("q0b", "bore_d=50 mm")
        result = assemble_c0(case)
        self.assertIsNone(result.reference_context)
        self.assertIsNone(result.bore_d_used_for_query)


# ---------------------------------------------------------------------------
# C1 success tests
# ---------------------------------------------------------------------------


class TestAssembleC1Success(unittest.TestCase):
    """Valid C1 inputs produce a non-blocked AssembledInput with candidates."""

    @classmethod
    def setUpClass(cls):
        cls.idx = _real_index()

    def test_valid_bore_d_20mm_produces_candidates(self):
        """C1 with bore_d=20 mm returns 3 retrieval_source candidates."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1, CONDITION_C1

        case = _projected_case("q1", "I need a set screw shaft collar with bore_d=20 mm")
        result = assemble_c1(case, self.idx)
        self.assertEqual(result.condition_id, CONDITION_C1)
        self.assertIsNone(result.blocked_reason,
                          f"Unexpected block: {result.blocked_reason}")
        self.assertIsNotNone(result.reference_context)
        self.assertIsNotNone(result.reference_context_sha256)
        self.assertEqual(result.bore_d_used_for_query, 20.0)
        self.assertGreater(len(result.candidate_source_ids), 0,
                           "At least one candidate_source_id expected")

    def test_reference_context_contains_only_allowed_fields(self):
        """reference_context must not contain evaluator labels."""
        import sys, json; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1

        case = _projected_case("q2", "bore_d=30 mm set screw collar")
        result = assemble_c1(case, self.idx)
        self.assertIsNone(result.blocked_reason)
        self.assertIsNotNone(result.reference_context)
        ctx = json.loads(result.reference_context)
        # Must not contain evaluator-only labels
        for entry in ctx.get("candidates", []):
            for forbidden in ("expected_parameters", "ground_truth", "evaluator",
                              "split_role", "development", "heldout_evaluation"):
                self.assertNotIn(forbidden, entry,
                                 f"Evaluator label {forbidden!r} found in reference context")
            # Must carry only the model-visible subset
            self.assertIn("role", entry)
            self.assertEqual(entry["role"], "retrieval_example_untrusted_reference")

    def test_c1_bore_d_in_chinese_nli(self):
        """C1 extraction from Chinese natural language input."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1

        case = _projected_case("q3", "需要一个轴孔直径20mm的轴环")
        result = assemble_c1(case, self.idx)
        self.assertIsNone(result.blocked_reason,
                          f"Expected success, got: {result.blocked_reason}")
        self.assertEqual(result.bore_d_used_for_query, 20.0)


# ---------------------------------------------------------------------------
# C1 blocking tests
# ---------------------------------------------------------------------------


class TestAssembleC1Blocked(unittest.TestCase):
    """C1 blocks safely when bore_d cannot be extracted from allowed inputs."""

    @classmethod
    def setUpClass(cls):
        cls.idx = _real_index()

    def test_missing_bore_d_is_blocked(self):
        """NLI with no bore_d → C1_NO_SAFE_QUERY_PARAMETER block."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1

        case = _projected_case("q4", "I need a collar but I don't specify the bore size")
        result = assemble_c1(case, self.idx)
        self.assertIsNotNone(result.blocked_reason)
        self.assertIn("C1_NO_SAFE_QUERY_PARAMETER", result.blocked_reason)
        self.assertIsNone(result.reference_context)
        self.assertEqual(result.candidate_source_ids, ())
        self.assertIsNone(result.bore_d_used_for_query)

    def test_no_retrieval_index_is_blocked(self):
        """retrieval_index=None → blocked with informative message."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1

        case = _projected_case("q5", "bore_d=20 mm collar")
        result = assemble_c1(case, retrieval_index=None)
        self.assertIsNotNone(result.blocked_reason)
        self.assertIn("NO_RETRIEVAL_INDEX", result.blocked_reason)
        self.assertIsNone(result.reference_context)


class TestEvaluatorLabelsNotForwardedToQuery(unittest.TestCase):
    """Evaluator-only fields must not reach the retrieval query."""

    @classmethod
    def setUpClass(cls):
        cls.idx = _real_index()

    def test_evaluator_label_in_ref_struct_does_not_contaminate_query(self):
        """reference_context_structural with evaluator-only keys is never forwarded."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1
        from llm.input_projection import ProjectedCase

        # Provide a ref_struct that contains evaluator-only keys
        ref_struct_with_eval_labels = {
            "example": {
                "parameters": {"bore_d": 999.0},  # Would give wrong bore_d
                "evaluator_answer": "secret",
                "ground_truth": {"bore_d": 999.0},
            }
        }
        case = ProjectedCase(
            query_id="q6",
            # NLI says bore_d=20; ref_struct has bore_d=999 in evaluator-only zone
            natural_language_input="bore_d=20 mm",
            reference_context_structural=ref_struct_with_eval_labels,
            coverage=("bore_d",),
        )
        result = assemble_c1(case, self.idx)
        # bore_d must come from NLI (20), not from the ref_struct evaluator zone
        self.assertEqual(result.bore_d_used_for_query, 20.0,
                         "bore_d must be taken from NLI, not from ref_struct evaluator fields")
        self.assertIsNone(result.blocked_reason)

    def test_query_constructed_from_nli_not_evaluator_labels(self):
        """Verify the query is driven by the extracted bore_d, not any evaluator label."""
        import sys, json; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1
        from llm.input_projection import ProjectedCase

        # NLI with explicit bore_d, no evaluator fields anywhere
        case = ProjectedCase(
            query_id="q7",
            natural_language_input="Set screw collar, bore_d=50 mm, no other constraints",
            reference_context_structural=None,
            coverage=("bore_d",),
        )
        result = assemble_c1(case, self.idx)
        self.assertIsNone(result.blocked_reason)
        # bore_d=50 must be the query parameter
        self.assertEqual(result.bore_d_used_for_query, 50.0)
        # reference_context must not contain any of these evaluator-only strings
        if result.reference_context:
            ctx_str = result.reference_context
            for forbidden_substr in ("ground_truth", "evaluator", "expected_answer",
                                     "heldout", "private"):
                self.assertNotIn(forbidden_substr, ctx_str,
                                 f"Evaluator label {forbidden_substr!r} leaked into reference context")


# ---------------------------------------------------------------------------
# C1 envelope form test
# ---------------------------------------------------------------------------


class TestC1UsesEnvelopeForm(unittest.TestCase):
    """assemble_c1 must use the cad003_envelope query form, not flat_parameters."""

    @classmethod
    def setUpClass(cls):
        cls.idx = _real_index()

    def test_envelope_form_used_not_flat_parameters(self):
        """The query must use the envelope form so Schema derives the 5 non-bore_d fields.

        If flat_parameters were used, only bore_d would be provided and
        RetrievalError RETRIEVAL_MISSING_FIELD would be raised (the 5 other
        fields are missing), causing a blocked result.
        With the envelope form the Schema derives them, so the result is unblocked.
        """
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.conditions import assemble_c1

        case = _projected_case("q_env", "bore_d=20 mm collar required")
        result = assemble_c1(case, self.idx)
        # If flat_parameters were used this would be blocked with BLOCKED_C1_RETRIEVAL_ERROR
        self.assertIsNone(result.blocked_reason,
                          "assemble_c1 must use cad003_envelope, not flat_parameters; "
                          f"got blocked_reason={result.blocked_reason!r}")


if __name__ == "__main__":
    unittest.main()
