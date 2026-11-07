"""Provider request builder tests: frozen fields, model identity, and
provider-specific parameter isolation (DeepSeek thinking vs Ollama think).
"""

import json
import unittest

from src.llm.contract import (
    CONTRACT_VERSION,
    DECISION_VALUES,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_THINKING_SETTING,
    ENVELOPE_KEYS,
    EVIDENCE_KEYS,
    EVIDENCE_SOURCE_VALUES,
    EXTRACTABLE_FIELDS,
    INTEGER_FIELDS,
    LENGTH_FIELDS,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)
from src.llm.providers import (
    OLLAMA_FORMAT_SCHEMA,
    OLLAMA_FORMAT_SCHEMA_SHA256,
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
        # format is now a structured JSON Schema object, not the plain string "json"
        self.assertIsInstance(req.body["format"], dict)
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
        # format is now recorded as a schema hash + version, not the plain string "json"
        self.assertNotIn("format", snap)
        self.assertIn("format_schema_sha256", snap)
        self.assertIn("format_schema_version", snap)
        self.assertEqual(snap["format_schema_sha256"], OLLAMA_FORMAT_SCHEMA_SHA256)
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


# ---------------------------------------------------------------------------
# APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX: Ollama JSON Schema format tests
# ---------------------------------------------------------------------------


class OllamaFormatSchemaStructureTests(unittest.TestCase):
    """OLLAMA_FORMAT_SCHEMA must align with the app001-io.v1 contract enforced
    by parse_response().  All assertions are offline — no network, no model."""

    def test_format_field_is_dict_not_string(self):
        """format must be a dict (schema object), not the plain string 'json'."""
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertIsInstance(req.body["format"], dict)
        self.assertNotEqual(req.body["format"], "json")

    def test_format_schema_is_module_constant(self):
        """The format field must be the frozen OLLAMA_FORMAT_SCHEMA constant."""
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertEqual(req.body["format"], OLLAMA_FORMAT_SCHEMA)

    def test_schema_top_level_type_is_object(self):
        self.assertEqual(OLLAMA_FORMAT_SCHEMA["type"], "object")

    def test_schema_has_no_additional_properties(self):
        self.assertFalse(OLLAMA_FORMAT_SCHEMA["additionalProperties"])

    def test_schema_required_matches_envelope_keys(self):
        """required list must contain exactly the frozen ENVELOPE_KEYS."""
        self.assertEqual(
            set(OLLAMA_FORMAT_SCHEMA["required"]),
            ENVELOPE_KEYS,
        )

    def test_schema_properties_keys_match_envelope_keys(self):
        """properties must cover exactly the frozen ENVELOPE_KEYS."""
        self.assertEqual(
            set(OLLAMA_FORMAT_SCHEMA["properties"].keys()),
            ENVELOPE_KEYS,
        )

    def test_contract_version_is_const(self):
        cv = OLLAMA_FORMAT_SCHEMA["properties"]["contract_version"]
        self.assertEqual(cv, {"const": CONTRACT_VERSION})

    def test_prompt_version_is_const(self):
        pv = OLLAMA_FORMAT_SCHEMA["properties"]["prompt_version"]
        self.assertEqual(pv, {"const": PROMPT_VERSION})

    def test_decision_is_enum_of_frozen_values(self):
        dec = OLLAMA_FORMAT_SCHEMA["properties"]["decision"]
        self.assertIn("enum", dec)
        self.assertEqual(set(dec["enum"]), DECISION_VALUES)

    def test_confidence_is_null_type(self):
        conf = OLLAMA_FORMAT_SCHEMA["properties"]["confidence"]
        self.assertEqual(conf, {"type": "null"})

    def test_extracted_parameters_no_additional_properties(self):
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        self.assertFalse(ep["additionalProperties"])

    def test_extracted_parameters_covers_all_extractable_fields(self):
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        self.assertEqual(
            set(ep["properties"].keys()),
            set(EXTRACTABLE_FIELDS),
        )

    def test_extracted_parameters_no_required_fields(self):
        """No fields in extracted_parameters must be required — they are all
        optional (the model may extract any subset of explicit claims)."""
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        self.assertNotIn("required", ep)

    def test_length_fields_allow_number(self):
        """Each length field schema must accept a plain JSON number."""
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        for fname in LENGTH_FIELDS:
            with self.subTest(field=fname):
                schema = ep["properties"][fname]
                self.assertIn("oneOf", schema)
                one_of_types = [s.get("type") for s in schema["oneOf"]]
                self.assertIn("number", one_of_types)

    def test_length_fields_allow_measurement_object(self):
        """Each length field must also accept {value: number, unit: string}."""
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        for fname in LENGTH_FIELDS:
            with self.subTest(field=fname):
                schema = ep["properties"][fname]
                object_schemas = [s for s in schema["oneOf"]
                                  if s.get("type") == "object"]
                self.assertEqual(len(object_schemas), 1)
                obj = object_schemas[0]
                self.assertIn("value", obj["properties"])
                self.assertIn("unit", obj["properties"])
                self.assertEqual(obj["properties"]["value"], {"type": "number"})
                self.assertEqual(obj["properties"]["unit"], {"type": "string"})

    def test_length_fields_do_not_allow_string(self):
        """Length fields must NOT include a string variant — prevents '24 mm'."""
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        for fname in LENGTH_FIELDS:
            with self.subTest(field=fname):
                schema = ep["properties"][fname]
                one_of_types = [s.get("type") for s in schema["oneOf"]]
                self.assertNotIn("string", one_of_types)

    def test_second_screw_is_integer_type(self):
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        ss = ep["properties"]["second_screw"]
        self.assertEqual(ss, {"type": "integer"})

    def test_second_screw_is_not_number_or_string(self):
        """second_screw must only be 'integer', not generic number or string."""
        ep = OLLAMA_FORMAT_SCHEMA["properties"]["extracted_parameters"]
        ss = ep["properties"]["second_screw"]
        self.assertNotEqual(ss.get("type"), "number")
        self.assertNotEqual(ss.get("type"), "string")

    def test_array_fields_have_string_items(self):
        """unsupported_requests, missing_fields, questions are string arrays."""
        props = OLLAMA_FORMAT_SCHEMA["properties"]
        for field_name in ("unsupported_requests", "missing_fields", "questions"):
            with self.subTest(field=field_name):
                self.assertEqual(props[field_name]["type"], "array")
                self.assertEqual(props[field_name]["items"], {"type": "string"})

    def test_evidence_items_shape(self):
        """evidence items must have field, quote, source as required strings."""
        ev_schema = OLLAMA_FORMAT_SCHEMA["properties"]["evidence"]
        self.assertEqual(ev_schema["type"], "array")
        item = ev_schema["items"]
        self.assertEqual(item["type"], "object")
        self.assertFalse(item["additionalProperties"])
        for key in ("field", "quote", "source"):
            with self.subTest(key=key):
                self.assertIn(key, item["required"])
                if key != "source":
                    self.assertEqual(item["properties"][key], {"type": "string"})

    def test_evidence_source_enum(self):
        """Evidence source must be constrained to the frozen source values."""
        ev_schema = OLLAMA_FORMAT_SCHEMA["properties"]["evidence"]
        item = ev_schema["items"]
        source_schema = item["properties"]["source"]
        self.assertIn("enum", source_schema)
        self.assertEqual(set(source_schema["enum"]), EVIDENCE_SOURCE_VALUES)

    def test_schema_is_valid_json_serialisable(self):
        """The schema must survive a JSON round-trip without change."""
        round_tripped = json.loads(json.dumps(OLLAMA_FORMAT_SCHEMA, ensure_ascii=False))
        self.assertEqual(round_tripped, OLLAMA_FORMAT_SCHEMA)

    def test_schema_sha256_is_stable(self):
        """OLLAMA_FORMAT_SCHEMA_SHA256 must match a fresh re-computation."""
        import hashlib
        computed = hashlib.sha256(
            json.dumps(OLLAMA_FORMAT_SCHEMA, sort_keys=True, ensure_ascii=False
                       ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(computed, OLLAMA_FORMAT_SCHEMA_SHA256)


class OllamaSchemaVsParserAlignmentTests(unittest.TestCase):
    """The JSON Schema constraint and the strict parser must be consistent:
    numbers accepted by the schema must pass the parser; strings must fail."""

    def _full_envelope(self, **overrides):
        body = {
            "contract_version": CONTRACT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "decision": "answer",
            "extracted_parameters": {"bore_d": 20},
            "unsupported_requests": [],
            "evidence": [{"field": "bore_d", "quote": "20 mm",
                          "source": "user_input"}],
            "missing_fields": [],
            "questions": [],
            "confidence": None,
        }
        body.update(overrides)
        return json.dumps(body, ensure_ascii=False)

    def test_numeric_bore_d_parses_ok(self):
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"bore_d": 24}))
        self.assertTrue(r.ok, [e.as_dict() for e in r.errors])

    def test_string_bore_d_rejected_by_parser(self):
        """'24 mm' must still be rejected — schema constraint is a hint only."""
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"bore_d": "24 mm"}))
        self.assertFalse(r.ok)
        self.assertEqual(r.errors[0].code, "EXTRACTED_TYPE_ERROR")

    def test_string_zero_rejected_by_parser(self):
        """The string '0' must still be rejected for second_screw."""
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"second_screw": "0"}))
        self.assertFalse(r.ok)
        self.assertEqual(r.errors[0].code, "EXTRACTED_TYPE_ERROR")

    def test_integer_second_screw_parses_ok(self):
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"bore_d": 20, "second_screw": 0}))
        self.assertTrue(r.ok)

    def test_float_second_screw_rejected_by_parser(self):
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"second_screw": 0.5}))
        self.assertFalse(r.ok)

    def test_measurement_object_bore_d_parses_ok(self):
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"bore_d": {"value": 20, "unit": "mm"}}))
        self.assertTrue(r.ok)

    def test_cm_string_rejected_by_parser(self):
        """The string '1.6 cm' must be rejected — not a number."""
        from src.llm.parser import parse_response
        r = parse_response(self._full_envelope(
            extracted_parameters={"bore_d": "1.6 cm"}))
        self.assertFalse(r.ok)
        self.assertEqual(r.errors[0].code, "EXTRACTED_TYPE_ERROR")


class OllamaDecodingSnapshotConsistencyTests(unittest.TestCase):
    """decoding_parameters_snapshot(OLLAMA_PROVIDER) must reflect the actual
    request body configuration and not drift from it."""

    def test_snapshot_schema_hash_matches_request_format(self):
        """The snapshot's format_schema_sha256 must match the schema in the
        actual Ollama request body."""
        import hashlib
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        snap = decoding_parameters_snapshot(OLLAMA_PROVIDER)
        actual_hash = hashlib.sha256(
            json.dumps(req.body["format"], sort_keys=True, ensure_ascii=False
                       ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(actual_hash, snap["format_schema_sha256"])

    def test_snapshot_has_format_schema_version(self):
        snap = decoding_parameters_snapshot(OLLAMA_PROVIDER)
        self.assertIn("format_schema_version", snap)
        self.assertIsInstance(snap["format_schema_version"], str)

    def test_snapshot_does_not_have_plain_format_string(self):
        """Snapshot must not still record the old 'format': 'json' entry."""
        snap = decoding_parameters_snapshot(OLLAMA_PROVIDER)
        self.assertNotIn("format", snap)

    def test_deepseek_snapshot_unaffected(self):
        """DeepSeek snapshot must be unchanged by this fix."""
        snap = decoding_parameters_snapshot(DEEPSEEK_PROVIDER)
        self.assertNotIn("format_schema_sha256", snap)
        self.assertNotIn("format_schema_version", snap)
        self.assertEqual(snap["response_format"], {"type": "json_object"})
        self.assertEqual(snap["thinking"], {"type": "disabled"})


if __name__ == "__main__":
    unittest.main()
