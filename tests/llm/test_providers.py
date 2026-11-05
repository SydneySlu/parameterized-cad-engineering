"""Provider request builder tests: frozen fields, model identity, and
provider-specific parameter isolation (DeepSeek thinking vs Ollama think).
"""

import unittest

from src.llm.contract import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_THINKING_SETTING,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
)
from src.llm.providers import (
    build_deepseek_request,
    build_ollama_request,
    decoding_parameters_snapshot,
    deepseek_configured_identity,
    ollama_configured_identity,
)


SYSTEM = "system prompt"
USER = "user prompt"


class DeepSeekRequestTests(unittest.TestCase):
    def test_configured_identity(self):
        ident = deepseek_configured_identity()
        self.assertEqual(ident["configured_provider"], DEEPSEEK_PROVIDER)
        self.assertEqual(ident["configured_model_name"], DEEPSEEK_MODEL)
        self.assertEqual(ident["base_url"], DEEPSEEK_BASE_URL)
        self.assertEqual(ident["thinking_setting"], {"type": "disabled"})

    def test_request_uses_frozen_fields(self):
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertEqual(req.provider, DEEPSEEK_PROVIDER)
        self.assertEqual(req.model, DEEPSEEK_MODEL)
        self.assertEqual(req.base_url, DEEPSEEK_BASE_URL)
        self.assertEqual(req.endpoint, "/chat/completions")
        self.assertEqual(req.body["model"], DEEPSEEK_MODEL)
        self.assertEqual(req.body["temperature"], 0)
        self.assertEqual(req.body["top_p"], 1)
        self.assertEqual(req.body["max_tokens"], 512)
        self.assertEqual(req.body["seed"], 271828)
        self.assertEqual(req.body["thinking"], {"type": "disabled"})
        self.assertEqual(req.body["response_format"], {"type": "json_object"})
        self.assertFalse(req.body["stream"])

    def test_messages_built_with_system_and_user(self):
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        msgs = req.body["messages"]
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], SYSTEM)
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[1]["content"], USER)

    def test_thinking_setting_is_frozen_disabled(self):
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertEqual(req.body["thinking"], DEEPSEEK_THINKING_SETTING)

    def test_no_ollama_fields_in_deepseek_request(self):
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertNotIn("think", req.body)
        self.assertNotIn("num_predict", req.body)
        self.assertNotIn("options", req.body)

    def test_no_explicit_key_uses_env_or_none(self):
        """3.1: build_deepseek_request never reads env vars; authorization is always None."""
        import os
        saved = os.environ.pop("DEEPSEEK_API_KEY", None)
        try:
            req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
            self.assertIsNone(req.authorization)
        finally:
            if saved is not None:
                os.environ["DEEPSEEK_API_KEY"] = saved

    def test_explicit_key_not_accepted_by_mock_builder(self):
        """3.1: build_deepseek_request does not accept an api_key parameter."""
        import inspect
        sig = inspect.signature(build_deepseek_request)
        self.assertNotIn("api_key", sig.parameters)

    def test_decode_snapshot_deepseek(self):
        snap = decoding_parameters_snapshot(DEEPSEEK_PROVIDER)
        self.assertEqual(snap["temperature"], 0)
        self.assertEqual(snap["max_tokens_field"], "max_tokens")
        self.assertEqual(snap["thinking"], {"type": "disabled"})
        self.assertNotIn("think", snap)
        self.assertNotIn("num_predict_field", snap)


class OllamaRequestTests(unittest.TestCase):
    def test_configured_identity(self):
        ident = ollama_configured_identity()
        self.assertEqual(ident["configured_provider"], OLLAMA_PROVIDER)
        self.assertEqual(ident["configured_model_name"], OLLAMA_MODEL)
        self.assertEqual(ident["local_digest"], OLLAMA_DIGEST)
        self.assertEqual(ident["base_url"], OLLAMA_DEFAULT_HOST)
        self.assertFalse(ident["think_setting"])

    def test_request_uses_frozen_fields(self):
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertEqual(req.provider, OLLAMA_PROVIDER)
        self.assertEqual(req.model, OLLAMA_MODEL)
        self.assertEqual(req.base_url, OLLAMA_DEFAULT_HOST)
        self.assertEqual(req.endpoint, "/api/chat")
        self.assertEqual(req.body["model"], OLLAMA_MODEL)
        self.assertEqual(req.body["think"], False)
        self.assertEqual(req.body["format"], "json")
        self.assertFalse(req.body["stream"])
        opts = req.body["options"]
        self.assertEqual(opts["temperature"], 0)
        self.assertEqual(opts["top_p"], 1)
        self.assertEqual(opts["num_predict"], 512)
        self.assertEqual(opts["seed"], 271828)

    def test_no_deepseek_fields_in_ollama_request(self):
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertNotIn("thinking", req.body)
        self.assertNotIn("response_format", req.body)
        self.assertNotIn("max_tokens", req.body)

    def test_no_authorization_for_ollama(self):
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertIsNone(req.authorization)

    def test_decode_snapshot_ollama(self):
        snap = decoding_parameters_snapshot(OLLAMA_PROVIDER)
        self.assertEqual(snap["temperature"], 0)
        self.assertEqual(snap["num_predict_field"], "num_predict")
        self.assertFalse(snap["think"])
        self.assertEqual(snap["format"], "json")
        self.assertNotIn("thinking", snap)
        self.assertNotIn("max_tokens_field", snap)


class ParameterIsolationTests(unittest.TestCase):
    """The two providers must never cross-contaminate parameters."""

    def test_deepseek_and_ollama_bodies_are_disjoint_on_provider_specifics(self):
        dreq = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        oreq = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        # DeepSeek-specific
        self.assertIn("thinking", dreq.body)
        self.assertNotIn("thinking", oreq.body)
        self.assertIn("response_format", dreq.body)
        self.assertNotIn("response_format", oreq.body)
        # Ollama-specific
        self.assertIn("think", oreq.body)
        self.assertNotIn("think", dreq.body)
        self.assertIn("options", oreq.body)
        self.assertNotIn("options", dreq.body)
        # Shared messages shape is the same
        self.assertEqual(len(dreq.body["messages"]), len(oreq.body["messages"]))


if __name__ == "__main__":
    unittest.main()
