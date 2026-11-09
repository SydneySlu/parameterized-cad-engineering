"""Offline fixture tests for decision_policy_v5_candidate.py.

APP-001-V4-QUALITY-FIX-CANDIDATE — UNACTIVATED CANDIDATE ONLY.

All tests are offline: no model calls, no network access, no .env reads,
no API key reads or prints.  Fixtures are derived from the confirmed deviations
in batch app001-phase1-v4-20261109-01 (Codex review 2026-11-09).

Passing these tests means the offline checker correctly identifies the
confirmed deviations and preserves existing correct decisions.  It does NOT
mean a model produces correct output — that requires a separate formal batch
with a new unique batch_id and Codex preflight authorization.

Coverage (all from task specification):
  P1 — Over-refusal detection
    - A02 C0/C1: bore_d=24, no missing/unsupported → answer allowed (not over-refusal)
    - A02 C1: refuse with valid bore_d → P1-1 violation detected
    - A03 C0: refuse with unit-converted bore_d=16 → P1-1 violation detected
    - A03 C0: answer with bore_d=16 → passes
    - A08 C0/C1: bore_d=24, retrieval context present → answer allowed regardless of condition
    - A08 C1: refuse with valid bore_d → P1-1 violation detected
    - A01: complete description, answer → passes P1
    - A06: boundary bore_d=70, second_screw=0, answer → passes P1
    - Reverse A02: remove bore_d → refuse is valid (P1 does NOT fire)
    - Reverse A03: missing bore_d → refuse is valid
    - A04: bore_d absent → refuse/ask valid, not over-refusal
    - A07: bore_d=75 (out of catalog) → refuse valid (not over-refusal)
    - A09: rule conflict + missing bore_d info → refuse/ask valid
    - C0/C1 consistency: same envelope, P1 result is condition-agnostic
    - ask with valid bore_d, empty missing/unsupported → P1-1 fires (ask also unjustified)

  P2 — Envelope self-consistency
    - A05 C0/C1 observed deviation: outer_d in both extracted and missing → P2-1 violation
    - A05 corrected: outer_d only in extracted → P2 passes
    - Clean envelope: no missing_fields → P2 passes
    - decision=answer + non-empty missing_fields → P2-3 violation
    - decision=answer + non-empty unsupported_requests → P2-3 violation
    - Duplicate missing_fields entry → P2-4 violation
    - Non-Mapping input → structural violation

  Version / interface compatibility
    - CANDIDATE_VERSION is v5-candidate, not production v4
    - CONTRACT_VERSION is app001-io.v1 (unchanged)
    - check_v5_envelope signature accepts condition_id kwarg
    - Production module isolation: v5 not imported by adapter/parser/runner/contract/prompt_loader

  Convenience wrappers
    - is_over_refusal / is_self_consistent
"""

from __future__ import annotations

import py_compile
import sys
import unittest
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from src.llm.decision_policy_v5_candidate import (
    CANDIDATE_VERSION,
    CONTRACT_VERSION,
    V5CheckResult,
    V5ViolationDetail,
    check_v5_envelope,
    is_over_refusal,
    is_self_consistent,
)


# ── fixture builders ──────────────────────────────────────────────────────────

def _env(
    *,
    decision: str = "answer",
    bore_d: int | float | None = None,
    extra_extracted: dict[str, Any] | None = None,
    missing_fields: list[str] | None = None,
    unsupported_requests: list[str] | None = None,
    evidence: list[dict] | None = None,
) -> dict[str, Any]:
    """Build a minimal app001-io.v1 envelope fixture."""
    extracted: dict[str, Any] = {}
    if bore_d is not None:
        extracted["bore_d"] = bore_d
    if extra_extracted:
        extracted.update(extra_extracted)
    return {
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v4",
        "decision": decision,
        "extracted_parameters": extracted,
        "missing_fields": missing_fields if missing_fields is not None else [],
        "unsupported_requests": unsupported_requests if unsupported_requests is not None else [],
        "evidence": evidence or [],
        "questions": [],
        "confidence": None,
    }


# ── P1: Over-refusal detection ─────────────────────────────────────────────────

class P1OverRefusalTests(unittest.TestCase):

    # ── A02: only bore_d=24 ──

    def test_a02_c0_answer_passes_p1(self):
        """A02 C0: decision=answer with bore_d=24 must not be flagged as over-refusal."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env, condition_id="C0")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    def test_a02_c1_answer_passes_p1(self):
        """A02 C1: decision=answer with bore_d=24 must not be flagged as over-refusal."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env, condition_id="C1")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    def test_a02_c1_refuse_triggers_p1_violation(self):
        """A02 C1 observed deviation: refuse with valid bore_d=24 → P1-1 violation."""
        env = _env(decision="refuse", bore_d=24)
        result = check_v5_envelope(env, condition_id="C1")
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p1_violations), 0)
        self.assertEqual(result.p1_violations[0].rule_id, "P1-1")
        self.assertIn("bore_d", result.p1_violations[0].evidence)

    def test_a02_c0_refuse_triggers_p1_violation(self):
        """A02 C0: refuse with valid bore_d=24 also triggers P1-1."""
        env = _env(decision="refuse", bore_d=24)
        result = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p1_violations), 0)

    # ── A03: unit conversion 1.6cm → 16mm ──

    def test_a03_c0_answer_with_normalized_bore_passes_p1(self):
        """A03 C0: answer with bore_d=16 (normalized from 1.6 cm) must pass."""
        env = _env(decision="answer", bore_d=16)
        result = check_v5_envelope(env, condition_id="C0")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    def test_a03_c0_refuse_with_normalized_bore_triggers_p1_violation(self):
        """A03 C0 observed deviation: refuse with bore_d=16 → P1-1 violation."""
        env = _env(decision="refuse", bore_d=16)
        result = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p1_violations), 0)
        self.assertEqual(result.p1_violations[0].rule_id, "P1-1")

    # ── A08: retrieval context present, bore_d=24 ──

    def test_a08_c0_answer_passes_p1(self):
        """A08 C0: answer with bore_d=24 (retrieval context present) must pass."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env, condition_id="C0")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    def test_a08_c1_answer_passes_p1(self):
        """A08 C1: answer with bore_d=24, retrieval context → must pass (C1 same as C0)."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env, condition_id="C1")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    def test_a08_c1_refuse_triggers_p1_violation(self):
        """A08 C1 observed deviation: refuse with valid bore_d=24 → P1-1 violation."""
        env = _env(decision="refuse", bore_d=24)
        result = check_v5_envelope(env, condition_id="C1")
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p1_violations), 0)
        self.assertEqual(result.p1_violations[0].rule_id, "P1-1")

    # ── A01: complete description ──

    def test_a01_answer_passes_p1(self):
        """A01: complete description, answer, bore_d=20 → must pass P1."""
        env = _env(
            decision="answer",
            bore_d=20,
            extra_extracted={"outer_d": 32, "width": 14},
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    # ── A06: boundary bore_d=70, second_screw=0 ──

    def test_a06_answer_passes_p1(self):
        """A06: bore_d=70, second_screw=0, answer → must pass P1."""
        env = _env(
            decision="answer",
            bore_d=70,
            extra_extracted={"second_screw": 0},
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.p1_violations), 0)

    # ── Condition-agnostic: same envelope, same result regardless of C0/C1 ──

    def test_p1_result_is_same_for_c0_and_c1_on_refusal(self):
        """P1 violation detection must be identical for C0 and C1 — no condition-based loophole."""
        env = _env(decision="refuse", bore_d=24)
        result_c0 = check_v5_envelope(env, condition_id="C0")
        result_c1 = check_v5_envelope(env, condition_id="C1")
        self.assertEqual(result_c0.ok, result_c1.ok)
        self.assertEqual(len(result_c0.p1_violations), len(result_c1.p1_violations))
        # condition_id is recorded separately
        self.assertEqual(result_c0.condition_id, "C0")
        self.assertEqual(result_c1.condition_id, "C1")

    def test_p1_result_is_same_for_c0_and_c1_on_valid_answer(self):
        """A valid answer must pass P1 identically under C0 and C1."""
        env = _env(decision="answer", bore_d=24)
        self.assertTrue(check_v5_envelope(env, condition_id="C0").ok)
        self.assertTrue(check_v5_envelope(env, condition_id="C1").ok)

    # ── ask with complete valid envelope also triggers P1 ──

    def test_ask_with_valid_bore_no_missing_triggers_p1(self):
        """ask is also unjustified when bore_d valid, missing_fields=[], unsupported=[]."""
        env = _env(decision="ask", bore_d=24)
        result = check_v5_envelope(env)
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p1_violations), 0)
        self.assertEqual(result.p1_violations[0].rule_id, "P1-1")

    # ── Reverse tests: P1 must NOT fire when refusal is justified ──

    def test_a04_refuse_without_bore_d_does_not_trigger_p1(self):
        """A04: refuse when bore_d absent → NOT an over-refusal (P1 does not fire)."""
        env = _env(
            decision="refuse",
            bore_d=None,
            missing_fields=["bore_d"],
            extra_extracted={"outer_d": 32, "width": 14},
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(result.p1_violations), 0)

    def test_a04_ask_with_missing_bore_d_does_not_trigger_p1(self):
        """A04: ask when bore_d absent → NOT an over-refusal."""
        env = _env(
            decision="ask",
            bore_d=None,
            missing_fields=["bore_d"],
            extra_extracted={"outer_d": 32, "width": 14},
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(result.p1_violations), 0)

    def test_a07_refuse_out_of_catalog_bore_not_over_refusal(self):
        """A07: refuse with bore_d=75 (out of catalog) → not over-refusal."""
        env = _env(
            decision="refuse",
            bore_d=75,
            unsupported_requests=["flange", "keyway", "anodizing"],
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(result.p1_violations), 0,
                         f"P1 must not fire for out-of-catalog bore: {result.p1_violations}")

    def test_a05_ask_with_catalog_conflict_not_over_refusal(self):
        """A05: ask when catalog conflict present (missing_fields non-empty) → not over-refusal."""
        env = _env(
            decision="ask",
            bore_d=20,
            extra_extracted={"outer_d": 40},
            missing_fields=["outer_d"],  # conflict detected
        )
        result = check_v5_envelope(env, condition_id="C0")
        # P1 does not fire because missing_fields is non-empty
        self.assertEqual(len(result.p1_violations), 0)

    def test_a09_rule_conflict_refuse_not_over_refusal(self):
        """A09: rule conflict (second_screw=0 at bore_d=80 forced) → refuse valid."""
        env = _env(
            decision="refuse",
            bore_d=80,
            extra_extracted={"second_screw": 0},
            missing_fields=["second_screw"],
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(result.p1_violations), 0)

    def test_refuse_with_non_catalog_bore_not_over_refusal(self):
        """bore_d=75 is not in catalog; refuse is valid → P1 does not fire."""
        env = _env(decision="refuse", bore_d=75)
        result = check_v5_envelope(env)
        self.assertEqual(len(result.p1_violations), 0)

    def test_refuse_with_unsupported_requests_not_over_refusal(self):
        """Unsupported features block construction; refuse valid → P1 does not fire."""
        env = _env(decision="refuse", bore_d=24, unsupported_requests=["flange"])
        result = check_v5_envelope(env)
        self.assertEqual(len(result.p1_violations), 0)


# ── P2: Envelope self-consistency ─────────────────────────────────────────────

class P2SelfConsistencyTests(unittest.TestCase):

    # ── A05 observed deviation ──

    def test_a05_c0_outer_d_in_both_extracted_and_missing_triggers_p2(self):
        """A05 C0 observed deviation: outer_d in extracted_parameters AND missing_fields → P2-1."""
        env = _env(
            decision="ask",
            bore_d=20,
            extra_extracted={"outer_d": 40},
            missing_fields=["outer_d"],
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(result.ok)
        self.assertGreater(len(result.p2_violations), 0)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertIn("P2-1", rule_ids)
        # evidence must mention the field name
        p2_1 = next(v for v in result.p2_violations if v.rule_id == "P2-1")
        self.assertIn("outer_d", p2_1.message)

    def test_a05_c1_outer_d_in_both_extracted_and_missing_triggers_p2(self):
        """A05 C1 observed deviation: same violation under C1."""
        env = _env(
            decision="ask",
            bore_d=20,
            extra_extracted={"outer_d": 40},
            missing_fields=["outer_d"],
        )
        result = check_v5_envelope(env, condition_id="C1")
        self.assertFalse(result.ok)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertIn("P2-1", rule_ids)

    def test_a05_corrected_outer_d_only_in_extracted_passes_p2(self):
        """A05 corrected: outer_d only in extracted_parameters, NOT in missing_fields → P2 passes."""
        env = _env(
            decision="ask",
            bore_d=20,
            extra_extracted={"outer_d": 40},
            missing_fields=[],
        )
        result = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(result.p2_violations), 0,
                         f"P2 must not fire when fields are only in extracted: {result.p2_violations}")

    # ── Clean envelope ──

    def test_clean_answer_envelope_passes_p2(self):
        """Clean answer envelope with no conflicts must pass all P2 checks."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env)
        self.assertEqual(len(result.p2_violations), 0)

    def test_clean_ask_envelope_with_missing_passes_p2(self):
        """ask with bore_d missing and listed in missing_fields (not in extracted) passes P2."""
        env = _env(decision="ask", bore_d=None, missing_fields=["bore_d"],
                   extra_extracted={"outer_d": 32})
        result = check_v5_envelope(env)
        self.assertEqual(len(result.p2_violations), 0)

    # ── P2-3: answer + non-empty missing_fields ──

    def test_answer_with_nonempty_missing_fields_triggers_p2_3(self):
        """decision=answer + non-empty missing_fields → P2-3 violation."""
        env = _env(decision="answer", bore_d=24, missing_fields=["outer_d"])
        result = check_v5_envelope(env)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertIn("P2-3", rule_ids)

    def test_answer_with_nonempty_unsupported_requests_triggers_p2_3(self):
        """decision=answer + non-empty unsupported_requests → P2-3 violation."""
        env = _env(decision="answer", bore_d=24, unsupported_requests=["flange"])
        result = check_v5_envelope(env)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertIn("P2-3", rule_ids)

    # ── P2-4: duplicate missing_fields ──

    def test_duplicate_in_missing_fields_triggers_p2_4(self):
        """Duplicate entry in missing_fields → P2-4 violation."""
        env = _env(decision="ask", bore_d=None, missing_fields=["bore_d", "bore_d"])
        result = check_v5_envelope(env)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertIn("P2-4", rule_ids)

    def test_no_duplicate_missing_fields_passes_p2(self):
        """No duplicates in missing_fields → P2-4 does not fire."""
        env = _env(decision="ask", bore_d=None, missing_fields=["bore_d"])
        result = check_v5_envelope(env)
        rule_ids = [v.rule_id for v in result.p2_violations]
        self.assertNotIn("P2-4", rule_ids)

    # ── Structural: non-Mapping input ──

    def test_non_mapping_input_returns_structural_violation(self):
        """Non-dict input must return a structural violation (ok=False)."""
        result = check_v5_envelope("not a dict")  # type: ignore[arg-type]
        self.assertFalse(result.ok)
        self.assertGreater(len(result.violations), 0)

    # ── Multiple P2 violations can coexist ──

    def test_multiple_fields_in_both_extracted_and_missing_all_reported(self):
        """Two fields in both extracted and missing → two separate P2-1 violations."""
        env = _env(
            decision="ask",
            bore_d=20,
            extra_extracted={"outer_d": 40, "width": 14},
            missing_fields=["outer_d", "width"],
        )
        result = check_v5_envelope(env)
        p2_1_violations = [v for v in result.p2_violations if v.rule_id == "P2-1"]
        offending_fields = {v.message.split("'")[1] for v in p2_1_violations}
        self.assertIn("outer_d", offending_fields)
        self.assertIn("width", offending_fields)


# ── Version and interface compatibility ────────────────────────────────────────

class VersionCompatibilityTests(unittest.TestCase):

    def test_candidate_version_is_v5_candidate_not_v4(self):
        """CANDIDATE_VERSION must be the v5 candidate string, not production v4."""
        self.assertIn("v5", CANDIDATE_VERSION)
        self.assertIn("candidate", CANDIDATE_VERSION)
        self.assertNotEqual(CANDIDATE_VERSION, "app001-extraction.v4")

    def test_contract_version_is_unchanged_io_v1(self):
        """CONTRACT_VERSION must remain app001-io.v1 (I/O contract is unchanged)."""
        self.assertEqual(CONTRACT_VERSION, "app001-io.v1")

    def test_check_v5_envelope_accepts_condition_id_kwarg(self):
        """check_v5_envelope must accept condition_id as a keyword argument."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env, condition_id="C1")
        self.assertEqual(result.condition_id, "C1")

    def test_check_v5_envelope_condition_id_defaults_to_none(self):
        """condition_id defaults to None when not supplied."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env)
        self.assertIsNone(result.condition_id)

    def test_result_is_v5_check_result_instance(self):
        """Return value must be a V5CheckResult instance."""
        env = _env(decision="answer", bore_d=24)
        result = check_v5_envelope(env)
        self.assertIsInstance(result, V5CheckResult)

    def test_violations_are_v5_violation_detail_instances(self):
        """Each violation must be a V5ViolationDetail with rule_id and message."""
        env = _env(decision="refuse", bore_d=24)
        result = check_v5_envelope(env)
        for v in result.violations:
            self.assertIsInstance(v, V5ViolationDetail)
            self.assertTrue(v.rule_id)
            self.assertTrue(v.message)


# ── Production isolation ───────────────────────────────────────────────────────

class ProductionIsolationTests(unittest.TestCase):

    def test_v5_not_imported_by_adapter(self):
        """adapter.py must not import decision_policy_v5_candidate."""
        text = (_REPO_ROOT / "src/llm/adapter.py").read_text()
        self.assertNotIn("decision_policy_v5", text)

    def test_v5_not_imported_by_parser(self):
        """parser.py must not import decision_policy_v5_candidate."""
        text = (_REPO_ROOT / "src/llm/parser.py").read_text()
        self.assertNotIn("decision_policy_v5", text)

    def test_v5_not_imported_by_runner(self):
        """runner.py must not import decision_policy_v5_candidate."""
        text = (_REPO_ROOT / "src/llm/runner.py").read_text()
        self.assertNotIn("decision_policy_v5", text)

    def test_v5_not_imported_by_contract(self):
        """contract.py must not import decision_policy_v5_candidate."""
        text = (_REPO_ROOT / "src/llm/contract.py").read_text()
        self.assertNotIn("decision_policy_v5", text)

    def test_v5_not_imported_by_prompt_loader(self):
        """prompt_loader.py must not import decision_policy_v5_candidate."""
        text = (_REPO_ROOT / "src/llm/prompt_loader.py").read_text()
        self.assertNotIn("decision_policy_v5", text)

    def test_v5_does_not_import_forbidden_modules(self):
        """v5 candidate must not import from adapter/parser/runner/contract/prompt_loader."""
        import ast
        src = (_REPO_ROOT / "src/llm/decision_policy_v5_candidate.py").read_text()
        tree = ast.parse(src)
        forbidden = {"adapter", "parser", "runner", "contract", "prompt_loader"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                for p in parts:
                    self.assertNotIn(p, forbidden,
                                     f"v5 candidate imports from forbidden module: {node.module}")


# ── Convenience wrappers ───────────────────────────────────────────────────────

class ConvenienceWrapperTests(unittest.TestCase):

    def test_is_over_refusal_true_for_a02_c1_refuse(self):
        """is_over_refusal must return True for A02 C1 refuse pattern."""
        env = _env(decision="refuse", bore_d=24)
        self.assertTrue(is_over_refusal(env, condition_id="C1"))

    def test_is_over_refusal_false_for_valid_answer(self):
        """is_over_refusal must return False for a valid answer envelope."""
        env = _env(decision="answer", bore_d=24)
        self.assertFalse(is_over_refusal(env))

    def test_is_over_refusal_false_when_bore_d_absent(self):
        """is_over_refusal must return False when bore_d is absent (refuse is valid)."""
        env = _env(decision="refuse", bore_d=None, missing_fields=["bore_d"])
        self.assertFalse(is_over_refusal(env))

    def test_is_self_consistent_true_for_clean_answer(self):
        """is_self_consistent must return True for a self-consistent answer."""
        env = _env(decision="answer", bore_d=24)
        self.assertTrue(is_self_consistent(env))

    def test_is_self_consistent_false_for_a05_deviation(self):
        """is_self_consistent must return False for the A05 observed deviation."""
        env = _env(
            decision="ask", bore_d=20,
            extra_extracted={"outer_d": 40},
            missing_fields=["outer_d"],
        )
        self.assertFalse(is_self_consistent(env))


# ── py_compile ─────────────────────────────────────────────────────────────────

class SyntaxTests(unittest.TestCase):

    def test_py_compile_checker(self):
        """decision_policy_v5_candidate.py must compile without syntax errors."""
        py_compile.compile(
            str(_REPO_ROOT / "src/llm/decision_policy_v5_candidate.py"),
            doraise=True,
        )

    def test_py_compile_tests(self):
        """This test file must compile without syntax errors."""
        py_compile.compile(str(_REPO_ROOT / "tests/llm/test_decision_policy_v5_candidate.py"),
                           doraise=True)


if __name__ == "__main__":
    unittest.main()
