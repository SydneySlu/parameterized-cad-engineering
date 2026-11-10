"""Offline checks for APP-001 v5 activation-preparation artifacts.

These tests assert provenance and that v5 is NOT active. They make no network
or model calls and do not read credentials or create a batch.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "agent-work/llm/APP-001-v5-activation-prep"
MANIFEST = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V5ActivationPreparationTests(unittest.TestCase):
    def test_package_is_proposed_and_non_active(self):
        self.assertEqual(MANIFEST["status"], "proposed")
        self.assertEqual(MANIFEST["candidate_prompt_version"], "app001-extraction.v5")
        self.assertEqual(MANIFEST["production_prompt_version"], "app001-extraction.v4")
        self.assertFalse(MANIFEST["production_files_changed"])
        self.assertFalse(MANIFEST["formal_evaluation_authorized"])

    def test_activation_copy_hash_matches_manifest(self):
        path = PKG / MANIFEST["prompt_file"]
        self.assertEqual(_sha(path), MANIFEST["prompt_file_sha256"])
        prompt = path.read_text(encoding="utf-8")
        self.assertIn('"prompt_version": "app001-extraction.v5"', prompt)
        self.assertIn("activation-preparation copy; not active", prompt)

    def test_source_candidate_hash_matches_manifest(self):
        source = (PKG / MANIFEST["source_candidate"]).resolve()
        self.assertEqual(_sha(source), MANIFEST["source_candidate_sha256"])

    def test_activation_copy_only_normalizes_version_and_candidate_headings(self):
        source = (PKG / MANIFEST["source_candidate"]).resolve().read_text(encoding="utf-8")
        expected = source.replace(
            "# APP-001 extraction prompt v5 (offline candidate; not activated)",
            "# APP-001 extraction prompt v5 (activation-preparation copy; not active)",
        ).replace(
            '"prompt_version": "app001-extraction.v5-candidate"',
            '"prompt_version": "app001-extraction.v5"',
        ).replace("(v5 candidate)", "(v5 policy)")
        actual = (PKG / MANIFEST["prompt_file"]).read_text(encoding="utf-8")
        self.assertEqual(actual, expected)

    def test_acceptance_set_hash_and_count_match_manifest(self):
        acceptance = (PKG / MANIFEST["acceptance_set"]).resolve()
        self.assertEqual(_sha(acceptance), MANIFEST["acceptance_set_sha256"])
        data = json.loads(acceptance.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], MANIFEST["acceptance_set_version"])
        self.assertEqual(data["sample_count"], MANIFEST["acceptance_case_count"])

    def test_v4_rollback_target_hash_matches_manifest(self):
        rollback = (PKG / MANIFEST["rollback_prompt_file"]).resolve()
        self.assertEqual(_sha(rollback), MANIFEST["rollback_prompt_file_sha256"])
        self.assertEqual(MANIFEST["rollback_target"], "app001-extraction.v4")

    def test_production_constants_remain_v4_and_gate_closed(self):
        from src.llm.contract import FORMAL_EVALUATION_ALLOWED, PROMPT_VERSION
        from src.llm.prompt_loader import FROZEN_PROMPT_VERSION, FROZEN_PROMPT_FILE_SHA256
        self.assertEqual(PROMPT_VERSION, "app001-extraction.v4")
        self.assertEqual(FROZEN_PROMPT_VERSION, "app001-extraction.v4")
        self.assertEqual(FROZEN_PROMPT_FILE_SHA256, MANIFEST["rollback_prompt_file_sha256"])
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_candidate_checker_not_in_production_imports(self):
        for name in ("adapter.py", "parser.py", "runner.py", "contract.py", "prompt_loader.py"):
            text = (ROOT / "src/llm" / name).read_text(encoding="utf-8")
            self.assertNotIn("decision_policy_v5_candidate", text, name)

    def test_all_prerequisites_are_explicit(self):
        requirements = "\n".join(MANIFEST["activation_requires"])
        self.assertIn("ADR-0018", requirements)
        self.assertIn("independent review", requirements)
        self.assertIn("unique batch_id", requirements)

    def test_adr_0018_is_proposed_and_separates_decision_gates(self):
        decisions = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
        adr = decisions.split("## ADR-0018：", 1)[1]
        self.assertIn("状态：proposed", adr)
        self.assertIn("本 ADR 不授权任何模型请求", adr)
        self.assertIn("不等于激活实现完成", adr)


if __name__ == "__main__":
    unittest.main()
