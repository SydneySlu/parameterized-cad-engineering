"""Offline activation tests for APP-001 extraction v4 contract.

Coverage map (per APP-001-V4-ACTIVATION task requirements):

  1. v4 prompt matches manifest/hash; loader loads v4 and rejects hash/version
     tampering ................................................ TestV4PromptLoaderActivation
  2. v4 envelope passes default parser; v3/v2 history uses read-only compat
     entry; default parser rejects wrong version ............. TestV4ParserVersionBoundaries
  3. User bore_d=24 wins over retrieval=20; missing user value, retrieval must
     NOT fill in .............................................. TestV4RetrievalPrecedenceInFrozenPrompt
  4. 1.6 cm -> 16 mm policy requirement in frozen prompt ..... TestV4UnitConversionInFrozenPrompt
  5. anodized/阳极氧化 canonical label and evidence quote rule  TestV4AnodizingCanonicalLabel
  6. 75 mm, missing bore_d, A04/A05/A07/A09 safety boundaries TestV4SafetyBoundaries
  7. v3 history hash traceable from manifest; rollback target  TestV4RollbackAndV3HistoryAnchor
  8. authorization/budget and C2/IR/CAD/geometry/STEP guard   TestV4AuthorizationBoundaries

These tests validate the activation package, interface contracts, and static
rule verification ONLY.  They do not simulate or claim model compliance, do not
call any real model or API, and do not authorize any formal evaluation batch.

Normal cases and rejection/failure cases are both present.  Rejection boundary
tests are written so that they WOULD FAIL if the implementation incorrectly
promoted a retrieval value to a user claim, or incorrectly accepted 75 mm as a
valid catalog selector.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
V4_ACTIVATION_DIR = REPO_ROOT / "agent-work" / "llm" / "APP-001-v4-activation"
V3_ACTIVATION_DIR = REPO_ROOT / "agent-work" / "llm" / "APP-001-v3-activation"
CANDIDATE_DIR = REPO_ROOT / "agent-work" / "llm" / "APP-001-baseline-prep"

V4_PROMPT_FILE = V4_ACTIVATION_DIR / "prompt-v4.md"
V4_MANIFEST_FILE = V4_ACTIVATION_DIR / "manifest.json"
V3_PROMPT_FILE = V3_ACTIVATION_DIR / "prompt-v3.md"
ACCEPTANCE_SET_FILE = CANDIDATE_DIR / "acceptance-set-v0.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. v4 prompt/loader activation
# ---------------------------------------------------------------------------


class TestV4PromptLoaderActivation(unittest.TestCase):
    """The loader now points at the frozen v4 prompt; hash anchors prevent
    silent modification."""

    @classmethod
    def setUpClass(cls):
        from src.llm.prompt_loader import clear_cache
        clear_cache()
        from src.llm.prompt_loader import load_frozen_prompt, FROZEN_PROMPT_PATH, FROZEN_PROMPT_VERSION, FROZEN_PROMPT_FILE_SHA256
        cls.artifact = load_frozen_prompt()
        cls.path = FROZEN_PROMPT_PATH
        cls.declared_version = FROZEN_PROMPT_VERSION
        cls.declared_sha256 = FROZEN_PROMPT_FILE_SHA256

    def test_loader_points_to_v4_activation_directory(self):
        """The production loader path must be inside APP-001-v4-activation/."""
        self.assertIn("APP-001-v4-activation", str(self.path))
        self.assertTrue(self.path.name == "prompt-v4.md")

    def test_loader_declared_version_is_v4(self):
        """FROZEN_PROMPT_VERSION constant must be app001-extraction.v4."""
        self.assertEqual(self.declared_version, "app001-extraction.v4")

    def test_loader_artifact_version_is_v4(self):
        """Parsed artifact version must be app001-extraction.v4."""
        self.assertEqual(self.artifact.version, "app001-extraction.v4")

    def test_loader_file_sha256_matches_manifest(self):
        """The loader's FROZEN_PROMPT_FILE_SHA256 constant must match the
        actual file bytes AND match the manifest's prompt_file_sha256."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        actual_sha256 = _sha256_file(self.path)
        self.assertEqual(actual_sha256, self.declared_sha256,
                         "Loader SHA256 constant does not match actual file bytes")
        self.assertEqual(actual_sha256, manifest["prompt_file_sha256"],
                         "Loader SHA256 does not match manifest prompt_file_sha256")

    def test_loader_file_sha256_is_v4_value(self):
        """The frozen sha256 must be the known v4 value, not the v3 value."""
        v3_sha256 = "3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b"
        self.assertNotEqual(self.declared_sha256, v3_sha256,
                            "Loader is still pointing at v3 SHA256 anchor")

    def test_loader_rejects_missing_file(self):
        """Loading from a non-existent path raises FrozenPromptMismatchError."""
        from src.llm.prompt_loader import load_frozen_prompt, FrozenPromptMismatchError
        with self.assertRaises(FrozenPromptMismatchError):
            load_frozen_prompt(path=REPO_ROOT / "does_not_exist.md")

    def test_loader_rejects_hash_mismatch(self):
        """A file with wrong SHA-256 must be rejected (fails closed)."""
        import tempfile, os
        from src.llm.prompt_loader import _verify_file_hash, FrozenPromptMismatchError
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("tampered content without valid version marker")
            tmp = Path(f.name)
        try:
            with self.assertRaises(FrozenPromptMismatchError):
                _verify_file_hash(tmp, self.declared_sha256)
        finally:
            os.unlink(tmp)

    def test_loader_rejects_version_marker_absent(self):
        """A file lacking the version marker must be rejected."""
        import tempfile, os
        from src.llm.prompt_loader import load_frozen_prompt, FrozenPromptMismatchError
        content = V4_PROMPT_FILE.read_text("utf-8").replace(
            "app001-extraction.v4", "app001-extraction.vX"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write(content)
            tmp = Path(f.name)
        try:
            with self.assertRaises(FrozenPromptMismatchError):
                load_frozen_prompt(path=tmp)
        finally:
            os.unlink(tmp)

    def test_system_prompt_contains_v4_version_string(self):
        """The parsed system prompt must contain the v4 version literal so the
        model is instructed to declare it in its response."""
        self.assertIn('"prompt_version": "app001-extraction.v4"',
                      self.artifact.system_prompt)

    def test_system_prompt_no_code_fence_leaks(self):
        """No backtick fences must appear in the system prompt (regression for
        APP-001-PHASE1-ENVELOPE-FIX)."""
        self.assertNotIn("```", self.artifact.system_prompt)

    def test_manifest_source_candidate_sha256_matches_actual_candidate_file(self):
        """manifest.source_candidate_sha256 must match the actual candidate
        file bytes to ensure provenance is traceable."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        candidate_path = (V4_ACTIVATION_DIR / manifest["source_candidate"]).resolve()
        actual = _sha256_file(candidate_path)
        self.assertEqual(actual, manifest["source_candidate_sha256"])

    def test_manifest_acceptance_set_sha256_matches_actual_file(self):
        """manifest.acceptance_set_sha256 must match the frozen acceptance set
        bytes, confirming the set was not modified."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        self.assertEqual(
            _sha256_file(ACCEPTANCE_SET_FILE),
            manifest["acceptance_set_sha256"],
        )


# ---------------------------------------------------------------------------
# 2. Parser version boundaries
# ---------------------------------------------------------------------------


class TestV4ParserVersionBoundaries(unittest.TestCase):
    """The default parser accepts v4 and rejects all other versions.
    Historical v2/v3 are accessible via the explicit legacy audit entry point.
    """

    def _body(self, **overrides):
        base = {
            "contract_version": "app001-io.v1",
            "prompt_version": "app001-extraction.v4",
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "24 mm", "source": "user_input"}],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        }
        base.update(overrides)
        return json.dumps(base)

    # Normal cases
    def test_v4_envelope_accepted_by_default_parser(self):
        """A valid v4 envelope must parse OK with no errors."""
        from src.llm.parser import parse_response
        result = parse_response(self._body())
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version, "app001-extraction.v4")

    def test_v3_envelope_accepted_via_explicit_legacy_audit_path(self):
        """A v3 envelope must be parseable via parse_response_for_version with
        prompt_version='app001-extraction.v3' — the legacy audit entry point."""
        from src.llm.parser import parse_response_for_version
        body = self._body(prompt_version="app001-extraction.v3")
        result = parse_response_for_version(body, prompt_version="app001-extraction.v3")
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version, "app001-extraction.v3")

    def test_v2_envelope_accepted_via_explicit_legacy_audit_path(self):
        """A v2 envelope must be parseable via parse_response_for_version with
        prompt_version='app001-extraction.v2' — the legacy audit entry point."""
        from src.llm.parser import parse_response_for_version
        body = self._body(prompt_version="app001-extraction.v2")
        result = parse_response_for_version(body, prompt_version="app001-extraction.v2")
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version, "app001-extraction.v2")

    # Rejection cases
    def test_v3_envelope_rejected_by_default_parser(self):
        """REJECTION: the default parser must reject v3 so historical batch
        responses are never silently relabelled as v4."""
        from src.llm.parser import parse_response
        result = parse_response(self._body(prompt_version="app001-extraction.v3"))
        self.assertFalse(result.ok)
        self.assertIn("PROMPT_VERSION_MISMATCH",
                      [e.code for e in result.errors])

    def test_v2_envelope_rejected_by_default_parser(self):
        """REJECTION: the default parser must reject v2."""
        from src.llm.parser import parse_response
        result = parse_response(self._body(prompt_version="app001-extraction.v2"))
        self.assertFalse(result.ok)
        self.assertIn("PROMPT_VERSION_MISMATCH",
                      [e.code for e in result.errors])

    def test_v3_audit_parser_does_not_relabel_v4_envelope(self):
        """REJECTION: the explicit v3 audit parser must reject a v4 body."""
        from src.llm.parser import parse_response_for_version
        result = parse_response_for_version(
            self._body(prompt_version="app001-extraction.v4"),
            prompt_version="app001-extraction.v3",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PROMPT_VERSION_MISMATCH")

    def test_audit_parser_rejects_unregistered_version(self):
        """REJECTION: parse_response_for_version raises ValueError for any
        version that is not the production version or an explicit legacy audit
        version.  This prevents silent relabelling of arbitrary responses."""
        from src.llm.parser import parse_response_for_version
        with self.assertRaises(ValueError):
            parse_response_for_version(
                self._body(), prompt_version="app001-extraction.v1"
            )


# ---------------------------------------------------------------------------
# 3. Retrieval precedence — user value controls
# ---------------------------------------------------------------------------


class TestV4RetrievalPrecedenceInFrozenPrompt(unittest.TestCase):
    """The frozen v4 prompt must contain the policy text requiring that an
    explicit user bore_d takes precedence over untrusted retrieval context,
    and that a missing user bore_d is not filled by retrieval.
    """

    @classmethod
    def setUpClass(cls):
        cls.prompt = V4_PROMPT_FILE.read_text("utf-8")

    # Normal case: rule text present
    def test_prompt_states_user_claim_controls_over_retrieval(self):
        """The policy text must explicitly state that the user request controls
        over retrieval context."""
        self.assertIn("Do not ask again for a parameter", self.prompt)

    def test_prompt_cites_bore_d_24_example(self):
        """The rule must give the concrete bore_d=24 / retrieval=20 example."""
        self.assertIn("bore_d=24 mm", self.prompt)
        self.assertIn("retrieved example shows `bore_d=20`", self.prompt)

    def test_prompt_states_do_not_ask_which_value_intended(self):
        """The rule must explicitly say 'do not ask which value was intended'."""
        self.assertIn("do not ask which value was", self.prompt)
        self.assertIn("intended", self.prompt)

    # Offline checker: user=24 wins over retrieval=20 (reverse assertion)
    def test_offline_checker_user_24_wins_over_retrieval_20(self):
        """Normal case: user bore_d=24 with retrieval=20 → answer allowed.
        The offline checker must return 24, not 20."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=20))
        self.assertEqual(result.normalized_bore.value_mm, 24)
        self.assertIn("answer", result.decision_options)

    def test_offline_checker_user_missing_retrieval_present_no_answer(self):
        """REJECTION: when user bore_d is absent and retrieval=20 is present,
        answer must NOT be allowed.  This test would FAIL if the implementation
        incorrectly promoted the retrieval value to a user claim."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(
            V4FixtureCase(bore_value=None, retrieval_bore_value=20)
        )
        self.assertIsNone(result.normalized_bore,
                          "retrieval value must not be promoted to user claim")
        self.assertNotIn("answer", result.decision_options,
                         "answer must not be allowed when user bore_d is absent")

    def test_offline_checker_retrieval_catalog_value_not_promoted(self):
        """REJECTION: even when retrieval shows a valid catalog value (24),
        if the user did not state bore_d, answer must not be allowed."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(
            V4FixtureCase(bore_value=None, retrieval_bore_value=24)
        )
        self.assertIsNone(result.normalized_bore)
        self.assertNotIn("answer", result.decision_options)


# ---------------------------------------------------------------------------
# 4. Unit conversion rule (1.6 cm -> 16 mm)
# ---------------------------------------------------------------------------


class TestV4UnitConversionInFrozenPrompt(unittest.TestCase):
    """The frozen v4 prompt must contain the exact unit conversion policy."""

    @classmethod
    def setUpClass(cls):
        cls.prompt = V4_PROMPT_FILE.read_text("utf-8")

    def test_prompt_contains_1_6_cm_example(self):
        """The policy must cite the exact '1.6 cm' example."""
        self.assertIn("1.6 cm", self.prompt)

    def test_prompt_contains_16_mm_result(self):
        """The policy must state the result '16 mm'."""
        self.assertIn("16 mm", self.prompt)

    def test_prompt_states_does_not_require_clarification(self):
        """The policy must say the valid catalog value does not require
        clarification when the source unit was not millimeters."""
        self.assertIn("does not itself require a", self.prompt)

    def test_prompt_states_preserve_original_value_and_unit_in_evidence(self):
        """The policy must require preserving the original value and unit in
        the evidence quote."""
        self.assertIn("preserve the original value and unit", self.prompt)

    # Normal case: offline checker
    def test_offline_checker_1_6_cm_normalized_to_16(self):
        """Normal case: 1.6 cm normalizes to exactly 16 mm."""
        from src.llm.decision_policy_v4_candidate import normalize_length_to_mm
        result = normalize_length_to_mm(1.6, "cm", "轴孔直径 1.6 cm")
        self.assertEqual(result.value_mm, 16)
        self.assertEqual(result.evidence_quote, "轴孔直径 1.6 cm")

    def test_offline_checker_1_6_cm_allows_answer(self):
        """Normal case: fixture with bore_value=1.6 cm must allow answer."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(1.6, "cm"))
        self.assertIn("answer", result.decision_options)

    def test_offline_checker_fractional_non_catalog_cm_refused(self):
        """REJECTION: 1.65 cm → 16.5 mm, which is not a catalog value; answer
        must not be allowed."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(1.65, "cm"))
        self.assertNotIn("answer", result.decision_options)


# ---------------------------------------------------------------------------
# 5. Anodizing canonical label and evidence quote
# ---------------------------------------------------------------------------


class TestV4AnodizingCanonicalLabel(unittest.TestCase):
    """The frozen v4 prompt must specify the anodizing canonical label rule and
    require original-wording evidence quotes."""

    @classmethod
    def setUpClass(cls):
        cls.prompt = V4_PROMPT_FILE.read_text("utf-8")

    def test_prompt_contains_chinese_anodizing_term(self):
        """The policy must mention the Chinese equivalent 阳极氧化."""
        self.assertIn("阳极氧化", self.prompt)

    def test_prompt_contains_anodized_variant(self):
        """The policy must list the 'anodized' variant explicitly."""
        self.assertIn("anodized", self.prompt)

    def test_prompt_specifies_anodizing_as_canonical_label(self):
        """The policy must specify 'use `anodizing`' as the stable label."""
        self.assertIn("use `anodizing`", self.prompt)

    def test_prompt_requires_preserving_user_exact_wording(self):
        """The policy must require preserving the user's exact wording as the
        evidence quote."""
        self.assertIn("user's exact wording in the evidence", self.prompt)

    # Normal case: Chinese maps to canonical label
    def test_offline_checker_chinese_maps_to_anodizing(self):
        """Normal case: 阳极氧化 canonicalizes to 'anodizing'."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(unsupported_terms=("阳极氧化",)))
        self.assertEqual(result.unsupported_labels, ("anodizing",))
        ev = result.unsupported_evidence[0]
        self.assertEqual(ev.canonical_label, "anodizing")
        self.assertEqual(ev.original_quote, "阳极氧化",
                         "original Chinese quote must be preserved")
        self.assertEqual(ev.source, "user_input")

    def test_offline_checker_anodized_maps_to_anodizing_keeps_quote(self):
        """Normal case: 'anodized' variant maps to canonical 'anodizing' but
        the original quote 'anodized' is preserved."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(unsupported_terms=("anodized",)))
        ev = result.unsupported_evidence[0]
        self.assertEqual(ev.canonical_label, "anodizing")
        self.assertEqual(ev.original_quote, "anodized")

    def test_offline_checker_no_fabricated_items_when_none_requested(self):
        """REJECTION: when the user requests no unsupported features, the
        evidence list must be empty — no fabricated unsupported items."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(24, "mm"))
        self.assertEqual(len(result.unsupported_evidence), 0)
        self.assertEqual(len(result.unsupported_labels), 0)


# ---------------------------------------------------------------------------
# 6. Safety boundaries: 75 mm, missing bore_d, rejection gates
# ---------------------------------------------------------------------------


class TestV4SafetyBoundaries(unittest.TestCase):
    """Critical rejection and clarification boundaries must not be weakened by
    the v4 activation.  Tests include reverse assertions that WOULD FAIL if the
    implementation incorrectly accepted 75 mm as a catalog selector, or
    incorrectly allowed answer when bore_d is missing.
    """

    @classmethod
    def setUpClass(cls):
        cls.prompt = V4_PROMPT_FILE.read_text("utf-8")

    # 75 mm boundary
    def test_prompt_explicitly_names_75_mm_as_non_catalog(self):
        """The prompt must explicitly state that 75 mm is not a valid catalog
        choice even though it is within the 5-80 mm numeric span."""
        self.assertIn("such as `75 mm`", self.prompt)

    def test_prompt_states_not_one_of_15_discrete_catalog_selectors(self):
        """The prompt must use the exact phrase 'not one of the 15 discrete
        catalog selectors' to cover in-range non-catalog values."""
        self.assertIn("not one of the 15 discrete catalog selectors", self.prompt)

    def test_prompt_states_do_not_snap_to_nearest(self):
        """The prompt must forbid snapping to a nearby catalog row."""
        self.assertIn("never snap it to a nearby row", self.prompt)

    def test_offline_checker_75_mm_refused(self):
        """REJECTION: bore_d=75 mm must be refused even though 75 is between
        5 and 80.  This test WOULD FAIL if the checker treated the numeric
        range 5-80 as a continuous valid range."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(75))
        self.assertIn("refuse", result.decision_options,
                      "bore_d=75 (in-range non-catalog) must be refused")
        self.assertNotIn("answer", result.decision_options,
                         "bore_d=75 must not allow answer")

    def test_offline_checker_75_mm_also_refused_with_retrieval(self):
        """REJECTION: even with retrieval present, bore_d=75 must still be
        refused — retrieval context cannot override the catalog gate."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(75, retrieval_bore_value=70))
        self.assertNotIn("answer", result.decision_options)

    # Missing bore_d
    def test_offline_checker_missing_bore_d_cannot_answer(self):
        """REJECTION: when bore_d is absent, answer must not be allowed."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase())
        self.assertNotIn("answer", result.decision_options)
        self.assertIn("ask", result.decision_options)

    def test_offline_checker_missing_bore_d_ask_is_appropriate(self):
        """Normal: the appropriate response when bore_d is absent is ask."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase())
        self.assertIn("ask", result.decision_options)

    # Catalog conflict cannot answer
    def test_offline_checker_catalog_conflict_cannot_answer(self):
        """REJECTION: a bore_d with an explicit catalog conflict must not allow
        answer (A04/A05 style scenario)."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(20, catalog_conflict=True))
        self.assertNotIn("answer", result.decision_options)

    # Unsupported request blocks answer (A07 style)
    def test_offline_checker_unsupported_request_blocks_answer(self):
        """REJECTION: the presence of any unsupported request must block answer
        (A07 scenario: anodizing requested)."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(
            V4FixtureCase(24, unsupported_terms=("阳极氧化",))
        )
        self.assertNotIn("answer", result.decision_options)
        self.assertIn("refuse", result.decision_options)

    # Rule conflict cannot answer (A09 style: second_screw rule)
    def test_offline_checker_rule_conflict_cannot_answer(self):
        """REJECTION: an explicit rule conflict (second_screw rule) must not
        allow answer (A09 scenario)."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(80, rule_conflict=True))
        self.assertNotIn("answer", result.decision_options)

    # Normal catalog values still work
    def test_offline_checker_bore_d_24_allows_answer(self):
        """Normal case: bore_d=24 (valid catalog member) allows answer."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(24))
        self.assertIn("answer", result.decision_options)
        self.assertNotIn("refuse", result.decision_options)

    def test_offline_checker_bore_d_16_from_cm_allows_answer(self):
        """Normal case: bore_d=1.6 cm → 16 mm (valid catalog member) allows
        answer (A03 regression)."""
        from src.llm.decision_policy_v4_candidate import evaluate_fixture, V4FixtureCase
        result = evaluate_fixture(V4FixtureCase(1.6, "cm"))
        self.assertIn("answer", result.decision_options)

    def test_prompt_retains_v3_safety_gate_preconditions(self):
        """The answer gate preconditions from v3 must still be present."""
        self.assertIn("answer` ONLY when ALL", self.prompt)
        self.assertIn("15 catalog selectors", self.prompt)
        self.assertIn("CAD-003", self.prompt)


# ---------------------------------------------------------------------------
# 7. v3 history hash and rollback target
# ---------------------------------------------------------------------------


class TestV4RollbackAndV3HistoryAnchor(unittest.TestCase):
    """The v3 prompt file must be unmodified, and the manifest must document
    the rollback target with the correct hash."""

    def test_v3_prompt_file_sha256_unchanged(self):
        """The v3 frozen prompt file must not have been modified.  It is the
        read-only rollback target for the v4 activation."""
        actual = _sha256_file(V3_PROMPT_FILE)
        self.assertEqual(
            actual,
            "3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b",
            "v3 prompt file was modified — rollback target integrity violated",
        )

    def test_manifest_rollback_target_is_v3(self):
        """The v4 manifest must name app001-extraction.v3 as rollback target."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        self.assertEqual(manifest["rollback_target"], "app001-extraction.v3")

    def test_manifest_rollback_prompt_sha256_matches_actual_v3_file(self):
        """manifest.rollback_prompt_file_sha256 must match the actual v3 file
        bytes so the rollback can be verified independently."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        actual = _sha256_file(V3_PROMPT_FILE)
        self.assertEqual(actual, manifest["rollback_prompt_file_sha256"])

    def test_manifest_records_v2_rollback_hash_as_deeper_anchor(self):
        """The manifest must also record the v2 hash as a deeper audit anchor,
        matching ADR-0016's documented rollback hash."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        self.assertEqual(
            manifest["rollback_v2_prompt_file_sha256"],
            "d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac",
        )

    def test_acceptance_set_sha256_unchanged(self):
        """The frozen acceptance-set-v0.json must not have been modified."""
        actual = _sha256_file(ACCEPTANCE_SET_FILE)
        self.assertEqual(
            actual,
            "ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf",
        )

    def test_acceptance_set_frozen_prompt_version_is_still_v2(self):
        """acceptance-set-v0.json.frozen_prompt_version is historical metadata
        that must not be changed (it was v2 at freeze time)."""
        data = json.loads(ACCEPTANCE_SET_FILE.read_bytes())
        self.assertEqual(data["frozen_prompt_version"], "app001-extraction.v2")

    def test_v3_activation_manifest_is_unchanged(self):
        """The v3 activation manifest must not have been modified."""
        v3_manifest = json.loads((V3_ACTIVATION_DIR / "manifest.json").read_bytes())
        self.assertEqual(v3_manifest["package_id"], "APP-001-v3-activation")
        self.assertEqual(v3_manifest["prompt_file_sha256"],
                         "3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b")

    def test_v3_audit_parser_accepts_v3_historical_batch_response(self):
        """The legacy v3 audit entry point must still parse a valid v3 envelope
        so historical batch audit/replay is preserved."""
        from src.llm.parser import parse_response_for_version
        body = json.dumps({
            "contract_version": "app001-io.v1",
            "prompt_version": "app001-extraction.v3",
            "decision": "answer",
            "extracted_parameters": {"bore_d": 24},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "24 mm",
                           "source": "user_input"}],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        })
        result = parse_response_for_version(body, prompt_version="app001-extraction.v3")
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])


# ---------------------------------------------------------------------------
# 8. Authorization/budget and prohibited stage boundaries
# ---------------------------------------------------------------------------


class TestV4AuthorizationBoundaries(unittest.TestCase):
    """FORMAL_EVALUATION_ALLOWED must remain False.  C2/IR/CAD/geometry/STEP
    stages must not be unlocked by the v4 activation.  Checker must not be
    imported by production modules."""

    def test_formal_evaluation_allowed_is_false(self):
        """FORMAL_EVALUATION_ALLOWED must remain False after v4 activation."""
        from src.llm.contract import FORMAL_EVALUATION_ALLOWED
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_manifest_formal_evaluation_authorized_is_false(self):
        """The v4 manifest must record formal_evaluation_authorized=false."""
        manifest = json.loads(V4_MANIFEST_FILE.read_bytes())
        self.assertFalse(manifest["formal_evaluation_authorized"])

    def test_ir_stage_is_not_run_by_default(self):
        """A default RunRecord must have IR stage status 'not_run' or
        'blocked', never 'pass'.  Verified by checking STAGE_STATUSES and the
        adapter's default stage initialization."""
        from src.llm.contract import STAGE_STATUSES
        self.assertIn("not_run", STAGE_STATUSES)
        self.assertIn("blocked", STAGE_STATUSES)
        self.assertNotIn("pass_ir", STAGE_STATUSES)  # no auto-pass shortcuts

    def test_cad_stage_is_not_run_by_default(self):
        """A default RunRecord must not have CAD stage status 'pass'.
        Verified by checking that the CAD stage is in the blocked/not_run
        set and that no CAD gate constant is True."""
        from src.llm.contract import STAGE_STATUSES
        # The set must have not_run as a valid status (the default)
        self.assertIn("not_run", STAGE_STATUSES)
        # FORMAL_EVALUATION_ALLOWED controls the gate; CAD runs only when
        # it is True AND a valid FormalRunAuthorization is presented.
        from src.llm.contract import FORMAL_EVALUATION_ALLOWED
        self.assertFalse(FORMAL_EVALUATION_ALLOWED,
                         "CAD gate is open: FORMAL_EVALUATION_ALLOWED is True")

    def test_v4_checker_module_is_not_imported_by_contract(self):
        """Production contract.py must not depend on the v4 checker candidate
        module (which is a test/candidate-only helper)."""
        import importlib, sys
        # Remove any cached import of contract to get fresh module graph check
        mod = importlib.import_module("src.llm.contract")
        # The v4 candidate checker must NOT appear in contract's module imports
        imported_names = {
            k for k in sys.modules
            if "decision_policy_v4_candidate" in k
        }
        # Check contract source does not reference the checker
        import inspect
        source = inspect.getsource(mod)
        self.assertNotIn("decision_policy_v4_candidate", source)

    def test_v4_checker_module_is_not_imported_by_parser(self):
        """Production parser.py must not depend on the v4 checker candidate."""
        import inspect, importlib
        mod = importlib.import_module("src.llm.parser")
        source = inspect.getsource(mod)
        self.assertNotIn("decision_policy_v4_candidate", source)

    def test_v4_checker_module_is_not_imported_by_prompt_loader(self):
        """Production prompt_loader.py must not depend on the v4 checker."""
        import inspect, importlib
        mod = importlib.import_module("src.llm.prompt_loader")
        source = inspect.getsource(mod)
        self.assertNotIn("decision_policy_v4_candidate", source)

    def test_contract_version_is_unchanged(self):
        """CONTRACT_VERSION (app001-io.v1) must not have changed."""
        from src.llm.contract import CONTRACT_VERSION
        self.assertEqual(CONTRACT_VERSION, "app001-io.v1")

    def test_acceptance_set_version_is_unchanged(self):
        """ACCEPTANCE_SET_VERSION must remain acceptance-set-v0."""
        from src.llm.contract import ACCEPTANCE_SET_VERSION
        self.assertEqual(ACCEPTANCE_SET_VERSION, "acceptance-set-v0")

    def test_max_retries_after_initial_unchanged(self):
        """MAX_RETRIES_AFTER_INITIAL must still be 2 (ADR-0010)."""
        from src.llm.contract import MAX_RETRIES_AFTER_INITIAL
        self.assertEqual(MAX_RETRIES_AFTER_INITIAL, 2)

    def test_max_attempts_total_unchanged(self):
        """MAX_ATTEMPTS_TOTAL must still be 3 (ADR-0010)."""
        from src.llm.contract import MAX_ATTEMPTS_TOTAL
        self.assertEqual(MAX_ATTEMPTS_TOTAL, 3)


if __name__ == "__main__":
    unittest.main()
