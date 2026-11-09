"""Offline fixture tests for decision_policy_v5_candidate.py.

APP-001-V4-QUALITY-FIX-CANDIDATE-R1 — UNACTIVATED CANDIDATE ONLY.

All tests are offline: no model calls, no network access, no .env reads,
no API key reads or prints.  Fixtures are derived from the confirmed deviations
in batch app001-phase1-v4-20261109-01 (Codex review 2026-11-09).

R1 additions (Codex review 2026-11-09):
  - ImportSmokeTests: PYTHONPATH=src 'import llm.decision_policy_v5_candidate'
  - P2CatalogRuleConflictTests: P2-5 for A05 answer+outer_d and A09 answer+second_screw
  - NumericNormalizationTests: bore_d=24.0 and {"value":1.6,"unit":"cm"} recognized

Coverage:
  ImportSmokeTests
    - PYTHONPATH=src import llm.decision_policy_v5_candidate succeeds
    - src.llm namespace also works
  P1OverRefusalTests
    - A02 C0/C1 answer → passes
    - A02 C1 refuse → P1-1 detected
    - A03 C0 refuse bore_d=16 → P1-1 detected
    - A08 C1 refuse → P1-1 detected
    - A01/A06 answer → passes
    - A04 (missing bore_d), A07 (out of catalog+unsupported) → not over-refusal
    - A05 ask/refuse with catalog conflict → P1 suppressed (conflict is valid reason)
    - A09 ask/refuse with second_screw conflict → P1 suppressed
    - C0/C1 result is identical for same envelope
    - ask with valid bore, no missing, no conflict → P1-1 fires
  P2SelfConsistencyTests
    - A05 C0/C1 field overlap (outer_d in both extracted and missing) → P2-1
    - A05 corrected (outer_d only in extracted) → P2 passes
    - answer + non-empty missing_fields → P2-3
    - answer + non-empty unsupported_requests → P2-3
    - duplicate missing_fields → P2-4
    - non-Mapping input → structural violation
    - multiple P2-1 violations all reported
  P2CatalogRuleConflictTests
    - A05 answer + outer_d=40 conflict → P2-5 (catalog mismatch)
    - A09 answer + second_screw=0 at bore_d=80 → P2-5 (rule conflict)
    - A05 ask/refuse with conflict → P2 does NOT fire (only for answer)
    - A06 answer bore_d=70 second_screw=0 → passes (=70 is NOT >70)
    - Correct A05 answer (outer_d matches catalog) → no P2-5
    - Correct A09 answer (bore_d=80 second_screw=1) → passes
  NumericNormalizationTests
    - bore_d=24.0 recognized as catalog value 24
    - bore_d={"value":1.6,"unit":"cm"} recognized as catalog value 16
    - bore_d={"value":1.6,"unit":"inches"} → not recognized (unknown unit)
    - bore_d=inf → not recognized
    - bore_d=24.5 (non-integer mm) → not recognized as catalog
    - bore_d={"value":1.65,"unit":"cm"} (fractional mm) → not recognized
    - float bore_d refuse without conflict → P1-1 fires (24.0 is catalog)
    - measurement object refuse → P1-1 fires (16mm is catalog)
  VersionCompatibilityTests
    - CANDIDATE_VERSION is v5-candidate, not production v4
    - CONTRACT_VERSION is app001-io.v1 (unchanged)
    - condition_id kwarg accepted; defaults to None
    - result is V5CheckResult instance
    - violations are V5ViolationDetail instances
  ProductionIsolationTests
    - v5 not imported by adapter/parser/runner/contract/prompt_loader
    - v5 itself does not import forbidden modules
  EnvelopeImmutabilityTests
    - check_v5_envelope does not modify input envelope
  ConvenienceWrapperTests
    - is_over_refusal / is_self_consistent
  SyntaxTests
    - py_compile on checker and test file
"""

from __future__ import annotations

import importlib
import py_compile
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

# Import via src.llm namespace (test-environment path).
from src.llm.decision_policy_v5_candidate import (
    CANDIDATE_VERSION,
    CONTRACT_VERSION,
    V5CheckResult,
    V5ViolationDetail,
    _is_catalog_bore_d,
    _normalize_bore_d,
    check_v5_envelope,
    is_over_refusal,
    is_self_consistent,
)


# ── fixture builder ───────────────────────────────────────────────────────────

def _env(
    *,
    decision: str = "answer",
    bore_d: Any = None,
    extra_extracted: dict[str, Any] | None = None,
    missing_fields: list[str] | None = None,
    unsupported_requests: list[str] | None = None,
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
        "evidence": [],
        "questions": [],
        "confidence": None,
    }


# ── R1-1: Import smoke tests ───────────────────────────────────────────────────

class ImportSmokeTests(unittest.TestCase):

    def test_import_via_llm_package_pythonpath_src(self):
        """PYTHONPATH=src import llm.decision_policy_v5_candidate must succeed.

        This is the project-standard entry point.  It fails if the module uses
        a relative import that goes beyond the top-level package.
        We test by running a subprocess with PYTHONPATH=src only.
        """
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import llm.decision_policy_v5_candidate as m; "
                "assert m.CANDIDATE_VERSION.startswith('app001-extraction.v5'), "
                "f'unexpected version: {m.CANDIDATE_VERSION}'; "
                "print('ok:', m.CANDIDATE_VERSION)"
            ],
            capture_output=True, text=True,
            env={**__import__("os").environ, "PYTHONPATH": str(_REPO_ROOT / "src")},
        )
        self.assertEqual(result.returncode, 0,
                         f"PYTHONPATH=src import failed:\n{result.stderr}")
        self.assertIn("ok:", result.stdout)

    def test_import_via_src_llm_namespace(self):
        """src.llm namespace must also import the module (test-environment path)."""
        mod = importlib.import_module("src.llm.decision_policy_v5_candidate")
        self.assertEqual(mod.CANDIDATE_VERSION, CANDIDATE_VERSION)

    def test_candidate_version_accessible_after_import(self):
        """CANDIDATE_VERSION must be a non-empty string after import."""
        self.assertTrue(CANDIDATE_VERSION)
        self.assertIsInstance(CANDIDATE_VERSION, str)


# ── P1: Over-refusal detection ────────────────────────────────────────────────

class P1OverRefusalTests(unittest.TestCase):

    # A02: only bore_d=24

    def test_a02_c0_answer_passes(self):
        self.assertTrue(check_v5_envelope(_env(decision="answer", bore_d=24), condition_id="C0").ok)

    def test_a02_c1_answer_passes(self):
        self.assertTrue(check_v5_envelope(_env(decision="answer", bore_d=24), condition_id="C1").ok)

    def test_a02_c1_refuse_triggers_p1_1(self):
        r = check_v5_envelope(_env(decision="refuse", bore_d=24), condition_id="C1")
        self.assertFalse(r.ok)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")
        self.assertIn("bore_d", r.p1_violations[0].evidence)

    def test_a02_c0_refuse_triggers_p1_1(self):
        r = check_v5_envelope(_env(decision="refuse", bore_d=24), condition_id="C0")
        self.assertFalse(r.ok)
        self.assertEqual(len(r.p1_violations), 1)

    # A03: unit conversion 1.6 cm → 16 mm

    def test_a03_c0_answer_bore_d_16_passes(self):
        self.assertTrue(check_v5_envelope(_env(decision="answer", bore_d=16), condition_id="C0").ok)

    def test_a03_c0_refuse_bore_d_16_triggers_p1_1(self):
        r = check_v5_envelope(_env(decision="refuse", bore_d=16), condition_id="C0")
        self.assertFalse(r.ok)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")

    # A08: retrieval context present, bore_d=24

    def test_a08_c0_answer_passes(self):
        self.assertTrue(check_v5_envelope(_env(decision="answer", bore_d=24), condition_id="C0").ok)

    def test_a08_c1_answer_passes(self):
        self.assertTrue(check_v5_envelope(_env(decision="answer", bore_d=24), condition_id="C1").ok)

    def test_a08_c1_refuse_triggers_p1_1(self):
        r = check_v5_envelope(_env(decision="refuse", bore_d=24), condition_id="C1")
        self.assertFalse(r.ok)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")

    # A01 / A06 normal paths

    def test_a01_answer_passes(self):
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 32, "width": 14})
        self.assertTrue(check_v5_envelope(env, condition_id="C0").ok)

    def test_a06_answer_bore_d_70_ss_0_passes(self):
        """bore_d=70 is the boundary: second_screw rule requires >70, so =70 → second_screw=0 is valid."""
        env = _env(decision="answer", bore_d=70, extra_extracted={"second_screw": 0})
        self.assertTrue(check_v5_envelope(env, condition_id="C0").ok)

    # Reverse: P1 must NOT fire when refuse/ask is legitimate

    def test_a04_refuse_no_bore_d_not_over_refusal(self):
        """bore_d absent → refuse is valid."""
        env = _env(decision="refuse", extra_extracted={"outer_d": 32, "width": 14},
                   missing_fields=["bore_d"])
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_a04_ask_no_bore_d_not_over_refusal(self):
        env = _env(decision="ask", extra_extracted={"outer_d": 32, "width": 14},
                   missing_fields=["bore_d"])
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_a07_refuse_out_of_catalog_not_over_refusal(self):
        """bore_d=75 not in catalog → refuse valid."""
        env = _env(decision="refuse", bore_d=75, unsupported_requests=["flange", "keyway"])
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_a05_ask_with_catalog_conflict_p1_suppressed(self):
        """A05 ask with outer_d conflict and no missing_fields: P1 suppressed because
        the catalog conflict (outer_d=40 ≠ expected 32) is a legitimate reason to ask."""
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40})
        r = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(r.p1_violations), 0,
                         f"P1 must be suppressed for catalog conflict: {r.p1_violations}")

    def test_a05_refuse_with_catalog_conflict_p1_suppressed(self):
        env = _env(decision="refuse", bore_d=20, extra_extracted={"outer_d": 40})
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_a09_ask_with_second_screw_conflict_p1_suppressed(self):
        """A09 ask: bore_d=80, second_screw=0 conflict. P1 suppressed."""
        env = _env(decision="ask", bore_d=80, extra_extracted={"second_screw": 0})
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_a09_refuse_with_second_screw_conflict_p1_suppressed(self):
        env = _env(decision="refuse", bore_d=80, extra_extracted={"second_screw": 0})
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_refuse_with_unsupported_not_over_refusal(self):
        env = _env(decision="refuse", bore_d=24, unsupported_requests=["flange"])
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_refuse_with_noncatalog_bore_not_over_refusal(self):
        env = _env(decision="refuse", bore_d=75)
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    # C0/C1 condition-agnostic

    def test_p1_result_is_same_for_c0_and_c1_on_refusal(self):
        env = _env(decision="refuse", bore_d=24)
        r0 = check_v5_envelope(env, condition_id="C0")
        r1 = check_v5_envelope(env, condition_id="C1")
        self.assertEqual(r0.ok, r1.ok)
        self.assertEqual(len(r0.p1_violations), len(r1.p1_violations))
        self.assertEqual(r0.condition_id, "C0")
        self.assertEqual(r1.condition_id, "C1")

    def test_ask_valid_bore_no_missing_no_conflict_triggers_p1(self):
        """ask with no conflict, no missing_fields → P1-1 fires (ask unjustified)."""
        env = _env(decision="ask", bore_d=24)
        r = check_v5_envelope(env)
        self.assertGreater(len(r.p1_violations), 0)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")


# ── P2: Envelope self-consistency ─────────────────────────────────────────────

class P2SelfConsistencyTests(unittest.TestCase):

    def test_a05_c0_outer_d_in_both_triggers_p2_1(self):
        """A05 C0 observed deviation: outer_d in extracted AND missing → P2-1."""
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40},
                   missing_fields=["outer_d"])
        r = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(r.ok)
        self.assertIn("P2-1", [v.rule_id for v in r.p2_violations])
        p2_1 = next(v for v in r.p2_violations if v.rule_id == "P2-1")
        self.assertIn("outer_d", p2_1.message)

    def test_a05_c1_outer_d_in_both_triggers_p2_1(self):
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40},
                   missing_fields=["outer_d"])
        r = check_v5_envelope(env, condition_id="C1")
        self.assertIn("P2-1", [v.rule_id for v in r.p2_violations])

    def test_a05_corrected_outer_d_only_in_extracted_passes(self):
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40})
        r = check_v5_envelope(env, condition_id="C0")
        self.assertEqual(len(r.p2_violations), 0,
                         f"P2 must not fire when outer_d is only in extracted: {r.p2_violations}")

    def test_clean_answer_passes_p2(self):
        self.assertEqual(len(check_v5_envelope(_env(decision="answer", bore_d=24)).p2_violations), 0)

    def test_answer_with_nonempty_missing_fields_triggers_p2_3(self):
        env = _env(decision="answer", bore_d=24, missing_fields=["outer_d"])
        self.assertIn("P2-3", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_answer_with_nonempty_unsupported_triggers_p2_3(self):
        env = _env(decision="answer", bore_d=24, unsupported_requests=["flange"])
        self.assertIn("P2-3", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_duplicate_missing_fields_triggers_p2_4(self):
        env = _env(decision="ask", missing_fields=["bore_d", "bore_d"])
        self.assertIn("P2-4", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_non_mapping_input_returns_structural_violation(self):
        r = check_v5_envelope("not a dict")  # type: ignore[arg-type]
        self.assertFalse(r.ok)
        self.assertGreater(len(r.violations), 0)

    def test_multiple_fields_in_both_all_reported(self):
        env = _env(decision="ask", bore_d=20,
                   extra_extracted={"outer_d": 40, "width": 14},
                   missing_fields=["outer_d", "width"])
        r = check_v5_envelope(env)
        p2_1 = [v for v in r.p2_violations if v.rule_id == "P2-1"]
        offending = {v.message.split("'")[1] for v in p2_1}
        self.assertIn("outer_d", offending)
        self.assertIn("width", offending)


# ── P2-5: Deterministic catalog/rule conflict ─────────────────────────────────

class P2CatalogRuleConflictTests(unittest.TestCase):

    def test_a05_answer_outer_d_conflict_triggers_p2_5(self):
        """A05: decision=answer with bore_d=20, outer_d=40 → P2-5 (catalog row expects outer_d=32)."""
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 40})
        r = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(r.ok)
        self.assertIn("P2-5", [v.rule_id for v in r.p2_violations])
        v = next(v for v in r.p2_violations if v.rule_id == "P2-5")
        self.assertIn("outer_d", v.message)
        self.assertIn("32", v.message)  # expected outer_d from catalog

    def test_a09_answer_second_screw_conflict_triggers_p2_5(self):
        """A09: decision=answer with bore_d=80, second_screw=0 → P2-5 (rule: bore_d>70 → ss=1)."""
        env = _env(decision="answer", bore_d=80, extra_extracted={"second_screw": 0})
        r = check_v5_envelope(env, condition_id="C0")
        self.assertFalse(r.ok)
        self.assertIn("P2-5", [v.rule_id for v in r.p2_violations])
        v = next(v for v in r.p2_violations if v.rule_id == "P2-5")
        self.assertIn("second_screw", v.message)
        self.assertIn("80", v.message)

    def test_a05_ask_conflict_no_p2_5(self):
        """P2-5 only applies to decision=answer; ask is not flagged."""
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40})
        r = check_v5_envelope(env, condition_id="C0")
        self.assertNotIn("P2-5", [v.rule_id for v in r.p2_violations])

    def test_a05_refuse_conflict_no_p2_5(self):
        """P2-5 only for answer; refuse is not flagged."""
        env = _env(decision="refuse", bore_d=20, extra_extracted={"outer_d": 40})
        self.assertNotIn("P2-5", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_a09_ask_conflict_no_p2_5(self):
        env = _env(decision="ask", bore_d=80, extra_extracted={"second_screw": 0})
        self.assertNotIn("P2-5", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_a06_answer_bore_d_70_ss_0_no_p2_5(self):
        """bore_d=70: rule is bore_d > 70 (strict), so second_screw=0 is correct at =70."""
        env = _env(decision="answer", bore_d=70, extra_extracted={"second_screw": 0})
        self.assertNotIn("P2-5", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_correct_a05_outer_d_matches_catalog_no_p2_5(self):
        """bore_d=20, outer_d=32 matches catalog row → no P2-5."""
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 32})
        self.assertNotIn("P2-5", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_correct_a09_second_screw_1_at_bore_d_80_no_p2_5(self):
        """bore_d=80, second_screw=1 satisfies the rule → no P2-5."""
        env = _env(decision="answer", bore_d=80, extra_extracted={"second_screw": 1})
        self.assertNotIn("P2-5", [v.rule_id for v in check_v5_envelope(env).p2_violations])

    def test_a05_c1_answer_outer_d_conflict_also_triggers_p2_5(self):
        """P2-5 fires under C1 just as under C0."""
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 40})
        r = check_v5_envelope(env, condition_id="C1")
        self.assertIn("P2-5", [v.rule_id for v in r.p2_violations])


# ── R1-3: Numeric and unit normalization ──────────────────────────────────────

class NumericNormalizationTests(unittest.TestCase):

    def test_normalize_24_int(self):
        self.assertEqual(_normalize_bore_d(24), 24)
        self.assertTrue(_is_catalog_bore_d(24))

    def test_normalize_24_0_float(self):
        """bore_d=24.0 must be treated as catalog value 24."""
        self.assertEqual(_normalize_bore_d(24.0), 24)
        self.assertTrue(_is_catalog_bore_d(_normalize_bore_d(24.0)))

    def test_normalize_measurement_object_cm(self):
        """{"value":1.6,"unit":"cm"} must normalize to 16 mm (a catalog value)."""
        result = _normalize_bore_d({"value": 1.6, "unit": "cm"})
        self.assertEqual(result, 16)
        self.assertTrue(_is_catalog_bore_d(result))

    def test_normalize_measurement_object_unknown_unit(self):
        """Unknown unit must return None (not a catalog value)."""
        self.assertIsNone(_normalize_bore_d({"value": 1.6, "unit": "inches"}))

    def test_normalize_infinite_float(self):
        """Infinity must return None."""
        self.assertIsNone(_normalize_bore_d(float("inf")))
        self.assertIsNone(_normalize_bore_d(float("-inf")))

    def test_normalize_nan(self):
        """NaN must return None."""
        self.assertIsNone(_normalize_bore_d(float("nan")))

    def test_normalize_fractional_mm(self):
        """bore_d=24.5 (not a whole number) must return None."""
        self.assertIsNone(_normalize_bore_d(24.5))

    def test_normalize_fractional_after_unit_conversion(self):
        """1.65 cm = 16.5 mm is not a whole mm → None."""
        self.assertIsNone(_normalize_bore_d({"value": 1.65, "unit": "cm"}))

    def test_float_bore_d_triggers_p1_1_on_refuse(self):
        """bore_d=24.0 is catalog value 24: refuse with no conflict/missing → P1-1."""
        env = _env(decision="refuse", bore_d=24.0)
        r = check_v5_envelope(env)
        self.assertGreater(len(r.p1_violations), 0)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")

    def test_measurement_object_bore_d_triggers_p1_1_on_refuse(self):
        """bore_d={"value":1.6,"unit":"cm"} → 16 mm is catalog: refuse → P1-1."""
        env = _env(decision="refuse", bore_d={"value": 1.6, "unit": "cm"})
        r = check_v5_envelope(env)
        self.assertGreater(len(r.p1_violations), 0)
        self.assertEqual(r.p1_violations[0].rule_id, "P1-1")

    def test_unknown_unit_bore_d_not_over_refusal(self):
        """bore_d with unknown unit is not recognized as catalog → P1 does not fire."""
        env = _env(decision="refuse", bore_d={"value": 1.6, "unit": "inches"})
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_infinite_bore_d_not_over_refusal(self):
        """bore_d=inf is not a catalog value → P1 does not fire."""
        env = _env(decision="refuse", bore_d=float("inf"))
        self.assertEqual(len(check_v5_envelope(env).p1_violations), 0)

    def test_float_bore_d_answer_passes(self):
        """bore_d=24.0 with decision=answer must pass (no false positive)."""
        env = _env(decision="answer", bore_d=24.0)
        self.assertTrue(check_v5_envelope(env).ok)


# ── Version and interface compatibility ────────────────────────────────────────

class VersionCompatibilityTests(unittest.TestCase):

    def test_candidate_version_is_v5_candidate_not_v4(self):
        self.assertIn("v5", CANDIDATE_VERSION)
        self.assertIn("candidate", CANDIDATE_VERSION)
        self.assertNotEqual(CANDIDATE_VERSION, "app001-extraction.v4")

    def test_contract_version_is_io_v1(self):
        self.assertEqual(CONTRACT_VERSION, "app001-io.v1")

    def test_condition_id_kwarg_accepted(self):
        env = _env(decision="answer", bore_d=24)
        r = check_v5_envelope(env, condition_id="C1")
        self.assertEqual(r.condition_id, "C1")

    def test_condition_id_defaults_to_none(self):
        env = _env(decision="answer", bore_d=24)
        self.assertIsNone(check_v5_envelope(env).condition_id)

    def test_result_is_v5_check_result_instance(self):
        self.assertIsInstance(check_v5_envelope(_env(decision="answer", bore_d=24)), V5CheckResult)

    def test_violations_are_v5_violation_detail_instances(self):
        env = _env(decision="refuse", bore_d=24)
        for v in check_v5_envelope(env).violations:
            self.assertIsInstance(v, V5ViolationDetail)
            self.assertTrue(v.rule_id)
            self.assertTrue(v.message)


# ── Production isolation ───────────────────────────────────────────────────────

class ProductionIsolationTests(unittest.TestCase):

    def test_v5_not_imported_by_adapter(self):
        self.assertNotIn("decision_policy_v5", (_REPO_ROOT / "src/llm/adapter.py").read_text())

    def test_v5_not_imported_by_parser(self):
        self.assertNotIn("decision_policy_v5", (_REPO_ROOT / "src/llm/parser.py").read_text())

    def test_v5_not_imported_by_runner(self):
        self.assertNotIn("decision_policy_v5", (_REPO_ROOT / "src/llm/runner.py").read_text())

    def test_v5_not_imported_by_contract(self):
        self.assertNotIn("decision_policy_v5", (_REPO_ROOT / "src/llm/contract.py").read_text())

    def test_v5_not_imported_by_prompt_loader(self):
        self.assertNotIn("decision_policy_v5", (_REPO_ROOT / "src/llm/prompt_loader.py").read_text())

    def test_v5_does_not_import_forbidden_modules(self):
        import ast
        src_text = (_REPO_ROOT / "src/llm/decision_policy_v5_candidate.py").read_text()
        tree = ast.parse(src_text)
        forbidden = {"adapter", "parser", "runner", "contract", "prompt_loader"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for part in node.module.split("."):
                    self.assertNotIn(part, forbidden,
                                     f"v5 imports from forbidden module: {node.module}")


# ── Envelope immutability ─────────────────────────────────────────────────────

class EnvelopeImmutabilityTests(unittest.TestCase):

    def test_check_v5_envelope_does_not_modify_input(self):
        """check_v5_envelope must never modify the input envelope."""
        import copy
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 40})
        env_before = copy.deepcopy(env)
        check_v5_envelope(env, condition_id="C0")
        self.assertEqual(env, env_before, "envelope was modified by check_v5_envelope")

    def test_check_v5_envelope_on_violation_does_not_modify_input(self):
        """Even on P2-1 violation, the input must not be modified."""
        import copy
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40},
                   missing_fields=["outer_d"])
        env_before = copy.deepcopy(env)
        check_v5_envelope(env)
        self.assertEqual(env, env_before)


# ── Convenience wrappers ──────────────────────────────────────────────────────

class ConvenienceWrapperTests(unittest.TestCase):

    def test_is_over_refusal_true_for_a02_c1_refuse(self):
        self.assertTrue(is_over_refusal(_env(decision="refuse", bore_d=24), condition_id="C1"))

    def test_is_over_refusal_false_for_valid_answer(self):
        self.assertFalse(is_over_refusal(_env(decision="answer", bore_d=24)))

    def test_is_over_refusal_false_when_bore_d_absent(self):
        env = _env(decision="refuse", missing_fields=["bore_d"])
        self.assertFalse(is_over_refusal(env))

    def test_is_self_consistent_true_for_clean_answer(self):
        self.assertTrue(is_self_consistent(_env(decision="answer", bore_d=24)))

    def test_is_self_consistent_false_for_a05_deviation(self):
        env = _env(decision="ask", bore_d=20, extra_extracted={"outer_d": 40},
                   missing_fields=["outer_d"])
        self.assertFalse(is_self_consistent(env))

    def test_is_self_consistent_false_for_p2_5_catalog_conflict(self):
        env = _env(decision="answer", bore_d=20, extra_extracted={"outer_d": 40})
        self.assertFalse(is_self_consistent(env))


# ── Syntax ────────────────────────────────────────────────────────────────────

class SyntaxTests(unittest.TestCase):

    def test_py_compile_checker(self):
        py_compile.compile(
            str(_REPO_ROOT / "src/llm/decision_policy_v5_candidate.py"),
            doraise=True,
        )

    def test_py_compile_tests(self):
        py_compile.compile(
            str(_REPO_ROOT / "tests/llm/test_decision_policy_v5_candidate.py"),
            doraise=True,
        )


if __name__ == "__main__":
    unittest.main()
