"""Strict parser tests for app001-io.v1 model responses.

Covers: valid response, extra prose, code fences, multiple objects, missing
keys, extra keys, wrong version, bad enum, non-null confidence, type errors.
"""

import json
import unittest

from src.llm.parser import parse_response, parse_response_for_version


def _valid_body(**overrides):
    # Default body uses the current production version (app001-extraction.v5).
    # Use prompt_version= to override for legacy audit tests.
    body = {
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v5",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "20 mm", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


class ParserValidTests(unittest.TestCase):
    def test_valid_minimal_envelope_parses(self):
        result = parse_response(_valid_body(extracted_parameters={"bore_d": 20}, evidence=[]))
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.decision, "answer")
        self.assertEqual(result.envelope.extracted_parameters, {"bore_d": 20})
        self.assertIsNone(result.envelope.confidence)

    def test_valid_ask_decision_with_partial_fields(self):
        result = parse_response(
            _valid_body(decision="ask", extracted_parameters={"outer_d": 32},
                        missing_fields=["bore_d"], questions=["What bore diameter?"])
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.envelope.decision, "ask")
        self.assertEqual(result.envelope.missing_fields, ["bore_d"])

    def test_valid_measurement_object_for_length(self):
        result = parse_response(
            _valid_body(extracted_parameters={"bore_d": {"value": 2, "unit": "cm"}})
        )
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])

    def test_valid_second_screw_integer(self):
        result = parse_response(
            _valid_body(extracted_parameters={"second_screw": 0})
        )
        self.assertTrue(result.ok)

    def test_retrieval_reference_source_accepted(self):
        result = parse_response(
            _valid_body(evidence=[{"field": "bore_d", "quote": "ref", "source": "retrieval_reference"}])
        )
        self.assertTrue(result.ok)


class ParserFailureTests(unittest.TestCase):
    def test_previous_prompt_version_is_rejected(self):
        # v2 is a registered legacy version but not the active production version;
        # the default parse_response() still rejects it.
        result = parse_response(
            _valid_body(prompt_version="app001-extraction.v2")
        )
        self.assertFalse(result.ok)
        self.assertIn("PROMPT_VERSION_MISMATCH", [e.code for e in result.errors])

    def test_v3_prompt_version_rejected_by_default_parser(self):
        # After the v4 activation, v3 is a legacy history version.  The default
        # production parse_response() must reject it so historical v3 batch
        # responses are never silently relabelled as v4.
        result = parse_response(
            _valid_body(prompt_version="app001-extraction.v3")
        )
        self.assertFalse(result.ok)
        self.assertIn("PROMPT_VERSION_MISMATCH", [e.code for e in result.errors])

    def test_explicit_v2_audit_parser_accepts_legacy_envelope(self):
        result = parse_response_for_version(
            _valid_body(prompt_version="app001-extraction.v2"),
            prompt_version="app001-extraction.v2",
        )
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version, "app001-extraction.v2")

    def test_explicit_v3_audit_parser_accepts_legacy_v3_envelope(self):
        # v3 is now a registered legacy audit version; historical batch responses
        # should be re-parseable via the explicit audit entry point.
        result = parse_response_for_version(
            _valid_body(prompt_version="app001-extraction.v3"),
            prompt_version="app001-extraction.v3",
        )
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])
        self.assertEqual(result.envelope.prompt_version, "app001-extraction.v3")

    def test_explicit_v2_audit_parser_keeps_contract_failures(self):
        body = json.loads(_valid_body(prompt_version="app001-extraction.v2"))
        del body["decision"]
        result = parse_response_for_version(
            json.dumps(body), prompt_version="app001-extraction.v2"
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_ENVELOPE_KEY")

    def test_explicit_v2_audit_parser_does_not_relabel_v3_payload(self):
        result = parse_response_for_version(
            _valid_body(prompt_version="app001-extraction.v3"),
            prompt_version="app001-extraction.v2",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PROMPT_VERSION_MISMATCH")

    def test_explicit_v3_audit_parser_does_not_relabel_v4_payload(self):
        # Even though v3 is now a registered legacy version, requesting the v3
        # audit parser with a v4 response body must reject the mismatch.
        result = parse_response_for_version(
            _valid_body(prompt_version="app001-extraction.v5"),
            prompt_version="app001-extraction.v3",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PROMPT_VERSION_MISMATCH")

    def test_audit_parser_rejects_unregistered_version(self):
        with self.assertRaises(ValueError):
            parse_response_for_version(
                _valid_body(), prompt_version="app001-extraction.v1"
            )

    def test_extra_prose_before_json_rejected(self):
        result = parse_response("here is the answer: " + _valid_body())
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "INVALID_JSON")

    def test_code_fence_rejected(self):
        result = parse_response("```json\n" + _valid_body() + "\n```")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "RESPONSE_HAS_CODE_FENCE")

    def test_multiple_json_objects_rejected(self):
        result = parse_response(_valid_body() + "\n" + _valid_body())
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "INVALID_JSON")

    def test_missing_key_rejected(self):
        body = json.loads(_valid_body())
        del body["decision"]
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "MISSING_ENVELOPE_KEY")
        self.assertIn("decision", result.errors[0].fields)

    def test_extra_key_rejected(self):
        body = json.loads(_valid_body())
        body["cad_parameters"] = {"bore_d": 20}
        result = parse_response(json.dumps(body))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EXTRA_ENVELOPE_KEY", codes)

    def test_wrong_contract_version_rejected(self):
        result = parse_response(_valid_body(contract_version="app001-io.v0"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "CONTRACT_VERSION_MISMATCH")

    def test_wrong_prompt_version_rejected(self):
        result = parse_response(_valid_body(prompt_version="app001-extraction.v1"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "PROMPT_VERSION_MISMATCH")

    def test_invalid_decision_enum_rejected(self):
        result = parse_response(_valid_body(decision="maybe"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "DECISION_INVALID")

    def test_non_null_confidence_is_contract_failure(self):
        result = parse_response(_valid_body(confidence=0.9))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("CONFIDENCE_NOT_NULL", codes)

    def test_extracted_parameters_not_object_rejected(self):
        result = parse_response(_valid_body(extracted_parameters=[1, 2]))
        self.assertFalse(result.ok)

    def test_unknown_extracted_parameter_key_rejected(self):
        result = parse_response(_valid_body(extracted_parameters={"bore_d": 20, "color": "red"}))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EXTRACTED_PARAMETERS_UNKNOWN_FIELD", codes)

    def test_bool_length_field_rejected(self):
        result = parse_response(_valid_body(extracted_parameters={"bore_d": True}))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EXTRACTED_TYPE_ERROR", codes)

    def test_second_screw_must_be_integer(self):
        result = parse_response(_valid_body(extracted_parameters={"second_screw": 0.5}))
        self.assertFalse(result.ok)

    def test_evidence_entry_missing_key_rejected(self):
        result = parse_response(_valid_body(evidence=[{"field": "bore_d", "quote": "20"}]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_ENTRY_MISSING_KEY", codes)

    def test_evidence_bad_source_rejected(self):
        result = parse_response(
            _valid_body(evidence=[{"field": "bore_d", "quote": "20", "source": "guess"}])
        )
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_SOURCE_INVALID", codes)

    def test_field_not_array_rejected(self):
        result = parse_response(_valid_body(questions="what?"))
        self.assertFalse(result.ok)

    def test_empty_body_rejected(self):
        result = parse_response("")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "RESPONSE_EMPTY")

    def test_bytes_input_accepted(self):
        result = parse_response(_valid_body().encode("utf-8"))
        self.assertTrue(result.ok)

    def test_non_utf8_bytes_rejected(self):
        result = parse_response(b"\xff\xfe\x00")
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, "RESPONSE_NOT_UTF8")


class EvidenceNullFieldTests(unittest.TestCase):
    """APP-001-EVIDENCE-CONTRACT-FIX: evidence field/quote/source must be str.

    Previously the parser used ``if val is not None and not isinstance(val, str)``
    which silently allowed explicit ``null`` values.  The fix removes the
    ``is not None`` guard so that ``null`` (Python ``None``) is rejected with
    ``EVIDENCE_FIELD_TYPE_ERROR``, aligning the parser with the Ollama JSON
    Schema which declares these fields as ``{type: string}``.
    """

    def _ev(self, **kw):
        """Build a valid body with one evidence entry overriding given keys."""
        entry = {"field": "bore_d", "quote": "20 mm", "source": "user_input"}
        entry.update(kw)
        return _valid_body(evidence=[entry])

    # ------------------------------------------------------------------ normal

    def test_valid_string_evidence_passes(self):
        """A well-formed evidence entry with all-string values must pass."""
        result = parse_response(_valid_body(
            evidence=[{"field": "bore_d", "quote": "20 mm", "source": "user_input"}]
        ))
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])

    def test_empty_evidence_array_passes(self):
        """An empty evidence array is valid."""
        result = parse_response(_valid_body(evidence=[]))
        self.assertTrue(result.ok)

    # ------------------------------------------------------------------ null cases

    def test_field_null_rejected(self):
        """evidence[*].field = null must fail with EVIDENCE_FIELD_TYPE_ERROR."""
        result = parse_response(self._ev(field=None))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_field_null_has_correct_path(self):
        """Error fields must pinpoint evidence[0].field."""
        result = parse_response(self._ev(field=None))
        err = next(e for e in result.errors if e.code == "EVIDENCE_FIELD_TYPE_ERROR")
        self.assertIn("evidence[0].field", err.fields)

    def test_quote_null_rejected(self):
        """evidence[*].quote = null must fail with EVIDENCE_FIELD_TYPE_ERROR."""
        result = parse_response(self._ev(quote=None))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_quote_null_has_correct_path(self):
        """Error fields must pinpoint evidence[0].quote."""
        result = parse_response(self._ev(quote=None))
        err = next(e for e in result.errors if e.code == "EVIDENCE_FIELD_TYPE_ERROR")
        self.assertIn("evidence[0].quote", err.fields)

    def test_source_null_rejected(self):
        """evidence[*].source = null must fail with EVIDENCE_FIELD_TYPE_ERROR."""
        result = parse_response(self._ev(source=None))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_source_null_has_correct_path(self):
        """Error fields must pinpoint evidence[0].source."""
        result = parse_response(self._ev(source=None))
        err = next(e for e in result.errors if e.code == "EVIDENCE_FIELD_TYPE_ERROR")
        self.assertIn("evidence[0].source", err.fields)

    def test_all_three_null_produces_three_errors(self):
        """Three null values must produce three EVIDENCE_FIELD_TYPE_ERROR entries."""
        result = parse_response(self._ev(field=None, quote=None, source=None))
        self.assertFalse(result.ok)
        type_errors = [e for e in result.errors if e.code == "EVIDENCE_FIELD_TYPE_ERROR"]
        self.assertEqual(len(type_errors), 3)
        paths = {f for e in type_errors for f in e.fields}
        self.assertIn("evidence[0].field", paths)
        self.assertIn("evidence[0].quote", paths)
        self.assertIn("evidence[0].source", paths)

    # ------------------------------------------------------------------ non-string (pre-existing behaviour preserved)

    def test_field_integer_still_rejected(self):
        """Non-string non-null values still produce EVIDENCE_FIELD_TYPE_ERROR."""
        result = parse_response(self._ev(field=42))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_field_bool_still_rejected(self):
        result = parse_response(self._ev(field=True))
        self.assertFalse(result.ok)
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", [e.code for e in result.errors])

    # ------------------------------------------------------------------ source enum check still applies

    def test_source_wrong_string_still_evidence_source_invalid(self):
        """A non-null string source that is not in the enum still produces
        EVIDENCE_SOURCE_INVALID (not a type error)."""
        result = parse_response(self._ev(source="guess"))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_SOURCE_INVALID", codes)
        self.assertNotIn("EVIDENCE_FIELD_TYPE_ERROR", codes)


if __name__ == "__main__":
    unittest.main()
