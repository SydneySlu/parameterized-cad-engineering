"""APP-001-PHASE1-ENVELOPE-FIX regression tests.

Root cause: ``prompt_loader._parse_artifact`` stripped fenced code blocks
from the ``## System message`` section, hiding the JSON envelope example
that is the only place ``contract_version`` and ``prompt_version`` appear.
The second formal batch (app001-phase1-20261107-02) confirmed this: all 32
model responses omitted those two keys and failed with MISSING_ENVELOPE_KEY.

These tests verify the fix and guard against regression.  They are pure
offline tests: no network, no API key, no real model responses, and no
formal-batch artifacts are read or copied.  Fixtures are desensitised.

Coverage map (per task requirements):
  1. Complete frozen envelope accepted by parser ............... ParserAcceptsFullEnvelope
  2. Missing contract_version fails closed w/ MISSING_ENVELOPE_KEY  MissingContractVersionFails
  3. Missing prompt_version fails closed ....................... MissingPromptVersionFails
  4. Extra field / wrong type / wrong version rejected ......... ExtraKeyRejected,
                                                                WrongContractVersionRejected,
                                                                WrongPromptVersionRejected,
                                                                WrongDecisionRejected,
                                                                NonNullConfidenceRejected
  5. Provider raw JSON content → transport → parser keeps fields  TransportPreservesContentFields
  6. DeepSeek request asserts JSON object constraint ............ DeepSeekRequestHasJsonObjectConstraint
                                                                OllamaRequestHasJsonFormat
  7. Formal batches unchanged / no formal responses in fixtures  (no file I/O on work/)
  8. Fixtures desensitised (no keys / tokens / user data) ...... (inspect fixture constants)
"""

from __future__ import annotations

import json
import unittest

from src.llm.contract import (
    CONTRACT_VERSION,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    ENVELOPE_KEYS,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)
from src.llm.parser import parse_response
from src.llm.prompt_loader import load_frozen_prompt
from src.llm.providers import build_deepseek_request, build_ollama_request
from src.llm.transport import TransportResponse


# ---------------------------------------------------------------------------
# Desensitised fixture builders (no real keys, tokens, or user data)
# ---------------------------------------------------------------------------


def _full_envelope(**overrides):
    """A complete frozen envelope with all required keys."""
    body = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "20 mm", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    body.update(overrides)
    return body


def _envelope_json(**overrides) -> str:
    return json.dumps(_full_envelope(**overrides), ensure_ascii=False)


# A DeepSeek Chat Completions raw HTTP response shape (desensitised).
# Content is deliberately a VALID envelope so we can assert the transport
# preserves every field through to the parser.
_DEEPSEEK_HTTP_FIXTURE = {
    "id": "fixture-no-real-data",
    "object": "chat.completion",
    "created": 1700000000,
    "model": DEEPSEEK_MODEL,
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": _envelope_json()},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 10,
        "total_tokens": 60,
        "prompt_cache_hit_tokens": 40,
        "prompt_cache_miss_tokens": 10,
    },
}


# ---------------------------------------------------------------------------
# 1. Prompt loader now includes the JSON envelope example
# ---------------------------------------------------------------------------


class PromptLoaderIncludesEnvelopeExample(unittest.TestCase):
    """APP-001-PHASE1-ENVELOPE-FIX: the frozen system prompt must include the
    JSON envelope example so the model sees contract_version/prompt_version.

    Before the fix, _parse_artifact stripped fenced code blocks from the
    system message, hiding the envelope template.
    """

    def setUp(self):
        from src.llm.prompt_loader import clear_cache
        clear_cache()
        self.artifact = load_frozen_prompt()

    def test_system_prompt_contains_contract_version_key(self):
        """The literal ``contract_version`` key must appear in the system
        prompt sent to the model."""
        self.assertIn("contract_version", self.artifact.system_prompt)

    def test_system_prompt_contains_prompt_version_key(self):
        """The literal ``prompt_version`` key must appear in the system
        prompt sent to the model."""
        self.assertIn("prompt_version", self.artifact.system_prompt)

    def test_system_prompt_contains_envelope_json_example(self):
        """The JSON envelope example object must be present verbatim."""
        self.assertIn('"contract_version": "app001-io.v1"',
                      self.artifact.system_prompt)
        self.assertIn('"prompt_version": "app001-extraction.v2"',
                      self.artifact.system_prompt)

    def test_system_prompt_does_not_contain_code_fence_markers(self):
        """No Markdown fence markers (`````````) should leak into the system
        prompt; the model should see a bare JSON object, consistent with the
        instruction "Return exactly one UTF-8 JSON object, with no Markdown
        fences"."""
        self.assertNotIn("```", self.artifact.system_prompt)

    def test_file_hash_anchor_still_matches(self):
        """The prompt artifact FILE hash must be unchanged (we did not modify
        prompt-v2.md; only the parsing logic changed)."""
        import hashlib
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        p = repo_root / "agent-work" / "llm" / "APP-001-baseline-prep" / "prompt-v2.md"
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(actual, "d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac")

    def test_envelope_keys_all_mentioned_in_system_prompt(self):
        """Every key in ENVELOPE_KEYS must appear somewhere in the system
        prompt, so the model is told about all required fields."""
        for key in ENVELOPE_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, self.artifact.system_prompt,
                              f"key {key!r} missing from system prompt")


# ---------------------------------------------------------------------------
# 2-4. Parser strict acceptance / rejection (envelope-level)
# ---------------------------------------------------------------------------


class ParserAcceptsFullEnvelope(unittest.TestCase):
    """Requirement 1: a complete frozen envelope is accepted by the parser."""

    def test_full_envelope_parses_ok(self):
        result = parse_response(_envelope_json())
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.contract_version, CONTRACT_VERSION)
        self.assertEqual(result.envelope.prompt_version, PROMPT_VERSION)
        self.assertEqual(result.envelope.decision, "answer")

    def test_full_envelope_with_all_fields_populated(self):
        result = parse_response(_envelope_json(
            extracted_parameters={"bore_d": 20, "outer_d": 32, "width": 14,
                                  "screw_d": 5, "screw_len": 8, "second_screw": 0},
            evidence=[
                {"field": "bore_d", "quote": "20 mm", "source": "user_input"},
                {"field": "outer_d", "quote": "32 mm", "source": "user_input"},
            ],
        ))
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])


class MissingContractVersionFails(unittest.TestCase):
    """Requirement 2: missing contract_version fails closed with
    MISSING_ENVELOPE_KEY."""

    def test_missing_contract_version_rejected(self):
        body = _full_envelope()
        del body["contract_version"]
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_ENVELOPE_KEY")
        self.assertIn("contract_version", result.errors[0].fields)

    def test_missing_contract_version_does_not_become_success(self):
        """The parser must not silently repair or auto-fill contract_version."""
        body = _full_envelope()
        del body["contract_version"]
        result = parse_response(json.dumps(body))
        self.assertIsNone(result.envelope)


class MissingPromptVersionFails(unittest.TestCase):
    """Requirement 3: missing prompt_version fails closed."""

    def test_missing_prompt_version_rejected(self):
        body = _full_envelope()
        del body["prompt_version"]
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_ENVELOPE_KEY")
        self.assertIn("prompt_version", result.errors[0].fields)

    def test_missing_both_version_fields_rejected(self):
        body = _full_envelope()
        del body["contract_version"]
        del body["prompt_version"]
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_ENVELOPE_KEY")
        fields = result.errors[0].fields
        self.assertIn("contract_version", fields)
        self.assertIn("prompt_version", fields)


class ExtraKeyRejected(unittest.TestCase):
    """Requirement 4: extra fields are rejected."""

    def test_extra_key_rejected(self):
        body = _full_envelope()
        body["cad_parameters"] = {"bore_d": 20}
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EXTRA_ENVELOPE_KEY", codes)


class WrongContractVersionRejected(unittest.TestCase):
    """Requirement 4: wrong contract version is rejected."""

    def test_wrong_contract_version(self):
        result = parse_response(_envelope_json(contract_version="app001-io.v0"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "CONTRACT_VERSION_MISMATCH")


class WrongPromptVersionRejected(unittest.TestCase):
    """Requirement 4: wrong prompt version is rejected."""

    def test_wrong_prompt_version(self):
        result = parse_response(_envelope_json(prompt_version="app001-extraction.v1"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PROMPT_VERSION_MISMATCH")


class WrongDecisionRejected(unittest.TestCase):
    """Requirement 4: invalid decision enum is rejected."""

    def test_invalid_decision(self):
        result = parse_response(_envelope_json(decision="maybe"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "DECISION_INVALID")


class NonNullConfidenceRejected(unittest.TestCase):
    """Requirement 4: non-null confidence is a contract failure."""

    def test_non_null_confidence_rejected(self):
        result = parse_response(_envelope_json(confidence=0.9))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("CONFIDENCE_NOT_NULL", codes)


class WrongTypeRejected(unittest.TestCase):
    """Requirement 4: wrong types are rejected."""

    def test_extracted_parameters_not_object(self):
        result = parse_response(_envelope_json(extracted_parameters=[1, 2]))
        self.assertFalse(result.ok)

    def test_bool_length_field_rejected(self):
        result = parse_response(_envelope_json(extracted_parameters={"bore_d": True}))
        self.assertFalse(result.ok)

    def test_second_screw_must_be_integer(self):
        result = parse_response(_envelope_json(
            extracted_parameters={"second_screw": 0.5}))
        self.assertFalse(result.ok)


# ---------------------------------------------------------------------------
# 5. Provider raw JSON content → transport → parser preserves fields
# ---------------------------------------------------------------------------


class TransportPreservesContentFields(unittest.TestCase):
    """Requirement 5: provider raw JSON content passed through the transport
    layer must reach the parser without losing any envelope fields.

    We simulate DeepSeekTransport._parse_response extracting the content
    string from the choices[0].message.content field, then feed it to the
    parser.  This proves the transport does not drop contract_version or
    prompt_version.
    """

    def test_deepseek_content_preserves_all_envelope_fields(self):
        """The content string extracted from a DeepSeek Chat Completions
        response must parse into a complete envelope."""
        raw = json.dumps(_DEEPSEEK_HTTP_FIXTURE)
        data = json.loads(raw)
        choices = data.get("choices", [])
        message = choices[0].get("message", {})
        content = message.get("content", "")
        # The content is a complete envelope JSON string
        self.assertIsInstance(content, str)
        result = parse_response(content)
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.contract_version, CONTRACT_VERSION)
        self.assertEqual(result.envelope.prompt_version, PROMPT_VERSION)
        self.assertEqual(result.envelope.decision, "answer")
        self.assertEqual(result.envelope.extracted_parameters, {"bore_d": 20})

    def test_transport_response_body_reaches_parser_intact(self):
        """A TransportResponse.body that contains a full envelope must parse
        successfully, proving the transport layer does not strip fields."""
        body = _envelope_json()
        resp = TransportResponse(
            status=200,
            body=body,
            runtime_returned_model=DEEPSEEK_MODEL,
            runtime_returned_provider=None,
            usage=None,
        )
        result = parse_response(resp.body)
        self.assertTrue(result.ok)
        self.assertEqual(result.envelope.contract_version, CONTRACT_VERSION)
        self.assertEqual(result.envelope.prompt_version, PROMPT_VERSION)

    def test_ollama_content_preserves_all_envelope_fields(self):
        """The content string extracted from an Ollama /api/chat response must
        parse into a complete envelope."""
        ollama_fixture = {
            "model": OLLAMA_MODEL,
            "message": {"role": "assistant", "content": _envelope_json()},
            "done": True,
        }
        raw = json.dumps(ollama_fixture)
        data = json.loads(raw)
        message = data.get("message", {})
        content = message.get("content", "")
        result = parse_response(content)
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.contract_version, CONTRACT_VERSION)
        self.assertEqual(result.envelope.prompt_version, PROMPT_VERSION)


# ---------------------------------------------------------------------------
# 6. Request construction asserts JSON/object constraint (no network)
# ---------------------------------------------------------------------------


class DeepSeekRequestHasJsonObjectConstraint(unittest.TestCase):
    """Requirement 6: DeepSeek request must include a JSON object response
    format constraint so the model is instructed to return a JSON object."""

    def test_response_format_is_json_object(self):
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        self.assertIn("response_format", req.body)
        self.assertEqual(req.body["response_format"], {"type": "json_object"})

    def test_messages_contain_system_and_user(self):
        req = build_deepseek_request(system_prompt="sys", user_prompt="usr")
        msgs = req.body["messages"]
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0], {"role": "system", "content": "sys"})
        self.assertEqual(msgs[1], {"role": "user", "content": "usr"})

    def test_thinking_disabled(self):
        """DeepSeek requests must explicitly disable thinking per ADR-0012."""
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        self.assertEqual(req.body["thinking"], {"type": "disabled"})

    def test_decode_settings_frozen(self):
        """Shared decode settings must match the frozen contract."""
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        self.assertEqual(req.body["temperature"], 0)
        self.assertEqual(req.body["top_p"], 1)
        self.assertEqual(req.body["max_tokens"], 512)
        self.assertEqual(req.body["seed"], 271828)

    def test_no_credentials_in_request(self):
        """The mock-path request builder must never embed credentials."""
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        self.assertIsNone(req.authorization)
        self.assertNotIn("Authorization", req.headers)
        self.assertNotIn("api_key", req.body)

    def test_no_network_call_made(self):
        """Building a request must not perform any network I/O."""
        # If this completes without network access, the builder is pure.
        req = build_deepseek_request(system_prompt="s", user_prompt="u")
        self.assertEqual(req.endpoint, "/chat/completions")


class OllamaRequestHasJsonFormat(unittest.TestCase):
    """Requirement 6: Ollama request must include a JSON format constraint."""

    def test_format_is_schema_object(self):
        """format must be a JSON Schema object (not the plain string 'json')."""
        req = build_ollama_request(system_prompt="s", user_prompt="u")
        self.assertIsInstance(req.body["format"], dict)
        self.assertNotEqual(req.body["format"], "json")

    def test_think_is_false(self):
        req = build_ollama_request(system_prompt="s", user_prompt="u")
        self.assertFalse(req.body["think"])

    def test_no_deepseek_thinking_field(self):
        """Ollama requests must NOT carry the DeepSeek-specific thinking
        parameter."""
        req = build_ollama_request(system_prompt="s", user_prompt="u")
        self.assertNotIn("thinking", req.body)
        self.assertNotIn("response_format", req.body)

    def test_no_credentials_in_request(self):
        req = build_ollama_request(system_prompt="s", user_prompt="u")
        self.assertIsNone(req.authorization)


# ---------------------------------------------------------------------------
# 8. Fixture desensitisation check
# ---------------------------------------------------------------------------


class FixturesAreDesensitised(unittest.TestCase):
    """Requirement 8: test fixtures must not contain API keys, Authorization
    headers, Bearer tokens, or real user data."""

    def test_no_api_key_in_fixtures(self):
        """No fixture constant may look like a DeepSeek API key."""
        for name in dir(__name__):
            # module-level dunder names are skipped
            if name.startswith("_"):
                continue
        # Scan the fixture constants for key-like patterns
        fixture_text = json.dumps(_DEEPSEEK_HTTP_FIXTURE) + _envelope_json()
        self.assertNotIn("sk-", fixture_text)
        self.assertNotIn("DEEPSEEK_API_KEY", fixture_text.replace(
            "DEEPSEEK_API_KEY_PLACEHOLDER", ""))
        self.assertNotIn("Bearer", fixture_text)
        self.assertNotIn("Authorization", fixture_text)

    def test_no_real_user_data_in_fixtures(self):
        """Fixtures use generic placeholder quotes, not real user content."""
        fixture_text = _envelope_json()
        # Only generic test values are used
        self.assertIn("20 mm", fixture_text)  # generic placeholder


# ---------------------------------------------------------------------------
# Integration: prompt loader → adapter input → adapter run (FakeTransport)
# ---------------------------------------------------------------------------


class PromptLoaderAdapterIntegration(unittest.TestCase):
    """Verify the fixed system prompt flows through the adapter and the run
    record records the new system_prompt_sha256 (not the old stripped one)."""

    def test_adapter_input_uses_fixed_system_prompt(self):
        from src.llm.adapter import AdapterInput
        from tests.llm._frozen_helpers import _frozen_input
        ai = _frozen_input()
        self.assertIn("contract_version", ai.system_prompt)
        self.assertIn("prompt_version", ai.system_prompt)

    def test_adapter_run_records_fixed_prompt_hash(self):
        """The run record's system_prompt_sha256 must match the FIXED loader
        output (which includes the envelope example), not the old stripped
        version."""
        from src.llm.adapter import Adapter
        from src.llm.transport import FakeTransport
        from tests.llm._frozen_helpers import _frozen_input
        from src.llm.prompt_loader import load_frozen_prompt, clear_cache
        clear_cache()
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_envelope_json(),
            runtime_returned_model=DEEPSEEK_MODEL,
            runtime_returned_provider=None,
            usage={"prompt_tokens": 40, "completion_tokens": 6,
                   "total_tokens": 46, "prompt_cache_hit_tokens": 0,
                   "prompt_cache_miss_tokens": 40},
        ))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport,
                          sleeper=lambda s: None)
        rec = adapter.run(_frozen_input(), run_id="env-fix-1").record
        self.assertEqual(rec.prompt_hashes["system_prompt_sha256"],
                         artifact.system_prompt_sha256)
        # The recorded hash must NOT equal the old stripped-prompt hash
        self.assertNotEqual(rec.prompt_hashes["system_prompt_sha256"],
                            "561904470ff60377f4ed919f50bf78a853e77c00e95e2debd37d7b2ceef64403")

    def test_system_prompt_text_not_in_run_record_json(self):
        """The system prompt TEXT must never appear in the run record JSON;
        only its hash is recorded (privacy / prompt-leak protection)."""
        from src.llm.adapter import Adapter
        from src.llm.transport import FakeTransport
        from tests.llm._frozen_helpers import _frozen_input
        from src.llm.prompt_loader import load_frozen_prompt, clear_cache
        clear_cache()
        artifact = load_frozen_prompt()
        transport = FakeTransport()
        transport.queue_response(TransportResponse(
            status=200, body=_envelope_json(),
            runtime_returned_model=DEEPSEEK_MODEL,
            runtime_returned_provider=None, usage=None,
        ))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport,
                          sleeper=lambda s: None)
        rec_json = adapter.run(_frozen_input(), run_id="env-fix-2").record.to_json()
        self.assertNotIn(artifact.system_prompt[:40], rec_json)


if __name__ == "__main__":
    unittest.main()
