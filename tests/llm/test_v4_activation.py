"""Read-only compatibility checks for the archived APP-001 v4 activation."""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V4_DIR = ROOT / "agent-work/llm/APP-001-v4-activation"
V4_PATH = V4_DIR / "prompt-v4.md"
V4 = "app001-extraction.v4"

def _body(version=V4):
    return json.dumps({"contract_version":"app001-io.v1", "prompt_version":version, "decision":"answer", "extracted_parameters":{"bore_d":24}, "unsupported_requests":[], "evidence":[{"field":"bore_d","quote":"24 mm","source":"user_input"}], "missing_fields":[], "questions":[], "confidence":None})

class V4HistoricalActivationTests(unittest.TestCase):
    def test_archived_v4_file_hash_and_manifest_are_unchanged(self):
        manifest=json.loads((V4_DIR/"manifest.json").read_text())
        digest=hashlib.sha256(V4_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, "73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc")
        self.assertEqual(digest, manifest["prompt_file_sha256"])

    def test_v4_identity_remains_in_archived_prompt(self):
        self.assertIn('"prompt_version": "app001-extraction.v4"', V4_PATH.read_text())

    def test_default_parser_rejects_archived_v4(self):
        from src.llm.parser import parse_response
        result=parse_response(_body())
        self.assertFalse(result.ok)
        self.assertIn("PROMPT_VERSION_MISMATCH", [e.code for e in result.errors])

    def test_explicit_legacy_audit_parser_accepts_v4(self):
        from src.llm.parser import parse_response_for_version
        result=parse_response_for_version(_body(), prompt_version=V4)
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version,V4)

if __name__ == "__main__": unittest.main()
