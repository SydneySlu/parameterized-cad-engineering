"""Offline checks for the unactivated APP-001 decision policy v4 candidate.

These tests validate candidate wording and frozen-interface boundaries only;
they do not simulate or claim model compliance.
"""

import hashlib
import json
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
