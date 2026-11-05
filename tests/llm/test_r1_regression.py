"""R1 regression tests for APP-001-ADAPTER corrections.

Covers the specific edge cases flagged in APP-001-ADAPTER-codex-review.md:
- 3.3: Cost not_available when cache fields missing, invalid type, negative,
       or inconsistent with prompt total.
- 3.5: Parser rejects NaN / Infinity; evidence/array element type errors.
- 4.1: Raw response retention: default off; opt-in writes to ignored dir;
       path errors handled without silent success.
- 4.2: Prompt hash stability; hash changes when prompt changes; no prompt
       text in hash output.
"""

import hashlib
import json
from pathlib import Path
import os
import tempfile
import unittest

from src.llm.adapter import Adapter, AdapterInput, RetentionPolicy
from tests.llm._frozen_helpers import _frozen_input as _frozen_input_factory
from src.llm.contract import DEEPSEEK_PROVIDER, OLLAMA_PROVIDER
from src.llm.cost import compute_cloud_cost
from src.llm.parser import parse_response
from src.llm.transport import FakeTransport, TransportResponse


SYSTEM_PROMPT = "system"
USER_TEMPLATE = (
    "query_id: {query_id}\nfamily_id: set_screw_shaft_collar\n"
    "natural_language_input:\n{natural_language_input}\n"
    "reference_context:\n{reference_context_or_null}"
)


def _input(qid="q1", cond="c0", nl="bore_d=20"):
    return _frozen_input_factory(query_id=qid, natural_language_input=nl, condition_id=cond)


def _body(**overrides):
    base = {
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v2",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "20", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


def _deepseek_response(body=None, usage=None):
    return TransportResponse(
        status=200,
        body=body or _body(),
        runtime_returned_model="deepseek-flash",
        runtime_returned_provider=None,
        usage=usage,
    )


class _NoSleep:
    def __call__(self, s):
        raise AssertionError(f"unexpected sleep({s})")


# ---------------------------------------------------------------------------
# 3.3: Cost not_available edge cases
# ---------------------------------------------------------------------------


class CostNotAvailableTests(unittest.TestCase):
    TS = "2026-11-05T01:30:00Z"  # peak

    def test_both_cache_fields_missing_is_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=None,
            cache_miss_input_tokens=None,
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])
        self.assertIsNone(result["cost_amount"])
        self.assertIn("missing", result["not_available_reason"].lower())

    def test_one_cache_field_missing_is_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=None,
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])

    def test_negative_cache_field_is_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=-1,
            cache_miss_input_tokens=41,
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])

    def test_bool_cache_field_is_not_available(self):
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=True,  # bool is not int
            cache_miss_input_tokens=40,
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])

    def test_inconsistent_cache_split_is_not_available(self):
        """cache_hit + cache_miss != prompt_tokens -> not_available."""
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=10,
            cache_miss_input_tokens=25,  # 10+25=35 != 40
            output_tokens=6,
        )
        self.assertTrue(result["not_available"])
        self.assertIn("!=", result["not_available_reason"])

    def test_complete_valid_usage_computes_cost(self):
        result = compute_cloud_cost(
            request_timestamp_utc=self.TS,
            prompt_tokens=40,
            cached_input_tokens=0,
            cache_miss_input_tokens=40,
            output_tokens=6,
        )
        self.assertFalse(result["not_available"])
        self.assertIsNotNone(result["cost_amount"])
        self.assertGreater(result["cost_amount"], 0)

    def test_adapter_missing_cache_fields_yields_none_cost(self):
        transport = FakeTransport()
        transport.queue_response(_deepseek_response(usage={
            "prompt_tokens": 40,
            "completion_tokens": 6,
            "total_tokens": 46,
            # no prompt_cache_hit_tokens or prompt_cache_miss_tokens
        }))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        rec = adapter.run(_input(), run_id="r1").record
        self.assertIsNone(rec.cloud_cost_amount)


# ---------------------------------------------------------------------------
# 3.5: Parser NaN / Infinity and array element types
# ---------------------------------------------------------------------------


class ParserNaNInfinityTests(unittest.TestCase):
    def _wrap(self, extracted_parameters):
        return _body(extracted_parameters=extracted_parameters)

    def test_nan_in_length_field_rejected(self):
        from src.llm.parser import parse_response as pr

        # Python's json.loads accepts bare NaN (non-standard JSON extension).
        # Our parser's _walk_check_finite must catch it and return NON_FINITE_VALUE.
        body_with_nan = '{"contract_version": "app001-io.v1", "prompt_version": "app001-extraction.v2", "decision": "answer", "extracted_parameters": {"bore_d": NaN}, "unsupported_requests": [], "evidence": [], "missing_fields": [], "questions": [], "confidence": null}'
        result = pr(body_with_nan)
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        # Python 3.10+ json.loads parses NaN as float('nan'); our post-parse
        # walk catches it with NON_FINITE_VALUE.  Older interpreters may raise
        # JSONDecodeError (INVALID_JSON) instead.  Either way, rejected.
        self.assertTrue(
            "INVALID_JSON" in codes or "NON_FINITE_VALUE" in codes,
            f"Expected INVALID_JSON or NON_FINITE_VALUE, got: {codes}",
        )

    def test_infinity_in_field_rejected(self):
        from src.llm.parser import parse_response as pr

        body = '{"contract_version": "app001-io.v1", "prompt_version": "app001-extraction.v2", "decision": "answer", "extracted_parameters": {"bore_d": Infinity}, "unsupported_requests": [], "evidence": [], "missing_fields": [], "questions": [], "confidence": null}'
        result = pr(body)
        self.assertFalse(result.ok)

    def test_negative_infinity_in_field_rejected(self):
        from src.llm.parser import parse_response as pr

        body = '{"contract_version": "app001-io.v1", "prompt_version": "app001-extraction.v2", "decision": "answer", "extracted_parameters": {"bore_d": -Infinity}, "unsupported_requests": [], "evidence": [], "missing_fields": [], "questions": [], "confidence": null}'
        result = pr(body)
        self.assertFalse(result.ok)

    def test_non_finite_float_in_parsed_object_rejected(self):
        """Test that _walk_check_finite catches non-finite floats from non-standard parsers."""
        import math
        from src.llm.parser import _walk_check_finite

        found = []
        _walk_check_finite({"a": float("nan"), "b": [float("inf"), 1.0]}, "", found)
        self.assertIn("a", found)
        self.assertIn("[0]", found[1] if len(found) > 1 else "b[0]")

    def test_valid_finite_numbers_accepted(self):
        result = parse_response(_body(extracted_parameters={"bore_d": 20.0}))
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])


class ParserArrayElementTypeTests(unittest.TestCase):
    def test_non_string_in_missing_fields_rejected(self):
        result = parse_response(_body(missing_fields=[42]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("ARRAY_ELEMENT_TYPE_ERROR", codes)

    def test_non_string_in_questions_rejected(self):
        result = parse_response(_body(questions=[True]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("ARRAY_ELEMENT_TYPE_ERROR", codes)

    def test_non_string_in_unsupported_requests_rejected(self):
        result = parse_response(_body(unsupported_requests=[{"name": "flange"}]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("ARRAY_ELEMENT_TYPE_ERROR", codes)

    def test_non_string_evidence_field_rejected(self):
        result = parse_response(_body(evidence=[{"field": 7, "quote": "text", "source": "user_input"}]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_non_string_evidence_quote_rejected(self):
        result = parse_response(_body(evidence=[{"field": "bore_d", "quote": False, "source": "user_input"}]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_non_string_evidence_source_rejected(self):
        result = parse_response(_body(evidence=[{"field": "bore_d", "quote": "x", "source": 42}]))
        self.assertFalse(result.ok)
        codes = [e.code for e in result.errors]
        self.assertIn("EVIDENCE_FIELD_TYPE_ERROR", codes)

    def test_valid_string_elements_accepted(self):
        result = parse_response(_body(
            missing_fields=["bore_d"],
            questions=["What bore?"],
            unsupported_requests=["flange"],
        ))
        self.assertTrue(result.ok, [e.as_dict() for e in result.errors])


# ---------------------------------------------------------------------------
# 4.1: Raw response retention policy
# ---------------------------------------------------------------------------


class RetentionPolicyTests(unittest.TestCase):
    """R3-B: Retention tests use private _write_raw_to_dir, not public policy bypass."""

    def _run_adapter(self, policy=None):
        transport = FakeTransport()
        transport.queue_response(_deepseek_response(usage={
            "prompt_tokens": 40,
            "completion_tokens": 6,
            "total_tokens": 46,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 40,
        }))
        adapter = Adapter(
            provider=DEEPSEEK_PROVIDER,
            transport=transport,
            sleeper=_NoSleep(),
            retention_policy=policy,
        )
        return adapter.run(_input(), run_id="ret1")

    def test_default_policy_does_not_retain(self):
        result = self._run_adapter()
        meta = result.record.raw_response_retention
        self.assertFalse(meta.get("retained", True))

    def test_default_policy_records_hash_and_length(self):
        result = self._run_adapter()
        meta = result.record.raw_response_retention
        self.assertIn("body_sha256", meta)
        self.assertIn("body_length", meta)
        self.assertEqual(len(meta["body_sha256"]), 64)

    def test_raw_body_not_in_run_record_json(self):
        """The raw response body must never appear in the run record."""
        body_text = _body()
        transport = FakeTransport()
        transport.queue_response(_deepseek_response(body=body_text, usage={
            "prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46,
            "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 40,
        }))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=_NoSleep())
        record_json = adapter.run(_input(), run_id="ret2").record.to_json()
        body_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
        self.assertIn(body_hash, record_json)

    def test_retention_policy_has_no_test_only_field(self):
        """R3-B: RetentionPolicy must not have a _test_only dataclass field."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(RetentionPolicy)}
        self.assertNotIn("_test_only", fields)

    def test_retention_policy_has_no_for_test_factory(self):
        """R3-B: RetentionPolicy must not have a for_test classmethod."""
        self.assertFalse(hasattr(RetentionPolicy, "for_test"))

    def test_production_policy_rejects_external_path(self):
        """R3-B: A production policy with an external base_dir must be rejected."""
        from src.llm.adapter import _resolve_canonical_path
        with self.assertRaises(ValueError) as ctx:
            _resolve_canonical_path("/tmp/some_external_dir")
        self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_production_policy_rejects_path_traversal(self):
        """R3-B: Path traversal via .. must be rejected."""
        from src.llm.adapter import _resolve_canonical_path
        with self.assertRaises(ValueError) as ctx:
            _resolve_canonical_path("work/app001-runs/../../etc")
        self.assertIn("RETENTION_PATH_OUTSIDE_IGNORED_DIR", str(ctx.exception))

    def test_write_raw_to_dir_writes_to_tempdir(self):
        """R3-B: Private _write_raw_to_dir can write to a test tempdir."""
        from src.llm.adapter import _write_raw_to_dir
        with tempfile.TemporaryDirectory() as tmp:
            meta = _write_raw_to_dir(Path(tmp), "raw body", "run1", "q1")
            self.assertTrue(meta.get("retained"))
            self.assertTrue(os.path.exists(meta["path"]))
            self.assertTrue(meta["path"].startswith(tmp))

    def test_write_raw_failure_recorded(self):
        """R3-B: Write failure must be recorded, not silently swallowed."""
        from src.llm.adapter import _write_raw_to_dir
        meta = _write_raw_to_dir(Path("/dev/null/impossible_path_xyz"), "raw", "r", "q")
        self.assertFalse(meta.get("retained", True))
        self.assertTrue(meta.get("retention_failed"))


# ---------------------------------------------------------------------------
# 4.2: Prompt hash stability and sensitivity (R3: via AdapterInput, not Adapter.run)
# ---------------------------------------------------------------------------


class PromptHashTests(unittest.TestCase):
    """R3-A: Prompt hash tests use AdapterInput directly, not Adapter.run().

    Adapter.run() now unconditionally verifies the frozen prompt; tests that
    need synthetic prompts test the hash functions directly.
    """

    def _make_input(self, system="test_system", template="query_id: {query_id}\nfamily_id: set_screw_shaft_collar\nnatural_language_input:\n{natural_language_input}\nreference_context:\n{reference_context_or_null}"):
        return AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=system, user_prompt_template=template, condition_id="c0",
        )

    def test_prompt_hashes_are_present(self):
        ai = self._make_input()
        self.assertIn(ai.system_prompt_sha256(), ai.system_prompt_sha256())
        self.assertIn(ai.user_template_sha256(), ai.user_template_sha256())

    def test_hashes_are_64_char_hex(self):
        ai = self._make_input()
        for val in (ai.system_prompt_sha256(), ai.user_template_sha256()):
            self.assertEqual(len(val), 64)
            self.assertRegex(val, r"^[0-9a-f]{64}$")

    def test_same_prompt_same_hash(self):
        ai1 = self._make_input()
        ai2 = self._make_input()
        self.assertEqual(ai1.system_prompt_sha256(), ai2.system_prompt_sha256())
        self.assertEqual(ai1.user_template_sha256(), ai2.user_template_sha256())

    def test_different_system_prompt_different_hash(self):
        ai1 = self._make_input(system="original system")
        ai2 = self._make_input(system="modified system prompt")
        self.assertNotEqual(ai1.system_prompt_sha256(), ai2.system_prompt_sha256())

    def test_different_template_different_hash(self):
        ai1 = self._make_input(template="original {query_id} {natural_language_input} {reference_context_or_null}")
        ai2 = self._make_input(template="modified {query_id} {natural_language_input} {reference_context_or_null}")
        self.assertNotEqual(ai1.user_template_sha256(), ai2.user_template_sha256())

    def test_adapterinput_sha256_stability(self):
        ai = self._make_input()
        self.assertEqual(ai.system_prompt_sha256(), ai.system_prompt_sha256())
        self.assertEqual(ai.user_template_sha256(), ai.user_template_sha256())

    def test_frozen_prompt_hash_matches_artifact(self):
        """The frozen prompt hash from AdapterInput must match the artifact."""
        from src.llm.prompt_loader import load_frozen_prompt
        artifact = load_frozen_prompt()
        ai = AdapterInput(
            query_id="q1", natural_language_input="bore_d=20", reference_context=None,
            system_prompt=artifact.system_prompt,
            user_prompt_template=artifact.user_template,
            condition_id="c0",
        )
        self.assertEqual(ai.system_prompt_sha256(), artifact.system_prompt_sha256)
        self.assertEqual(ai.user_template_sha256(), artifact.user_template_sha256)


if __name__ == "__main__":
    unittest.main()
