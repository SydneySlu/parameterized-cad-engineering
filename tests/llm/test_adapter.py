"""Adapter integration tests with fake transport, staged records, and the
construction gate. Covers normal/missing/conflict/unsupported/ask/refuse paths,
usage/cost, local timing, construction gate, and IR/CAD/STEP staying not_run.

R3: tests use the real frozen prompt artifact via _frozen_input(); no
verify_frozen_prompt bypass.
"""

import json
import unittest

from src.llm.adapter import Adapter, AdapterInput
from src.llm.contract import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
)
from src.llm.transport import (
    COND_HTTP_429,
    COND_HTTP_5XX,
    FakeTransport,
    TransportError,
    TransportResponse,
)
from tests.llm._frozen_helpers import _frozen_input


def _input(nl="轴孔直径 20 mm 的紧定螺钉轴环", ref=None, qid="q1", cond="c0"):
    return _frozen_input(natural_language_input=nl, reference_context=ref, query_id=qid, condition_id=cond)


def _envelope_body(**overrides):
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


def _deepseek_response(body=None, model=DEEPSEEK_MODEL, usage=None):
    return TransportResponse(
        status=200,
        body=body or _envelope_body(),
        runtime_returned_model=model,
        runtime_returned_provider=None,
        usage=usage or {"prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 40},
    )


def _ollama_response(body=None):
    return TransportResponse(
        status=200,
        body=body or _envelope_body(),
        runtime_returned_model=None,
        runtime_returned_provider=None,
        usage=None,
    )


class _NoSleep:
    def __call__(self, seconds):
        raise AssertionError(f"unexpected sleep({seconds})")


class DeepSeekAdapterTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()

    def _adapter(self):
        return Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=_NoSleep())

    def test_normal_answer_passes_to_construction_gate(self):
        self.transport.queue_response(_deepseek_response())
        result = self._adapter().run(_input(), run_id="r1")
        rec = result.record
        self.assertTrue(rec.construction_ready)
        self.assertEqual(rec.stage_status("model_call"), "pass")
        self.assertEqual(rec.stage_status("parse"), "pass")
        self.assertEqual(rec.stage_status("schema"), "pass")
        self.assertEqual(rec.stage_status("construction_gate"), "pass")
        self.assertEqual(rec.stage_status("ir"), "blocked")
        self.assertEqual(rec.stage_status("cad"), "not_run")
        self.assertEqual(rec.stage_status("step"), "not_run")
        self.assertEqual(rec.configured_provider, DEEPSEEK_PROVIDER)
        self.assertEqual(rec.runtime_returned_model, DEEPSEEK_MODEL)
        self.assertIsNone(rec.runtime_returned_provider)
        self.assertEqual(rec.cloud_input_tokens, 40)
        self.assertEqual(rec.cloud_output_tokens, 6)
        self.assertIsNotNone(rec.cloud_cost_amount)
        self.assertEqual(rec.cloud_cost_currency, "CNY")

    def test_missing_bore_d_ask_decision_not_construction_ready(self):
        self.transport.queue_response(
            _deepseek_response(
                body=_envelope_body(decision="ask", extracted_parameters={"outer_d": 32},
                                     missing_fields=["bore_d"], questions=["bore?"])
            )
        )
        result = self._adapter().run(_input(), run_id="r2")
        rec = result.record
        self.assertFalse(rec.construction_ready)
        self.assertEqual(rec.stage_status("schema"), "fail")
        self.assertEqual(rec.stage_status("construction_gate"), "fail")
        self.assertEqual(rec.stage_status("ir"), "not_run")

    def test_catalog_conflict_explicit_outer_d_kept(self):
        # bore_d=20 implies outer_d=32; explicit outer_d=99 is a conflict.
        self.transport.queue_response(
            _deepseek_response(
                body=_envelope_body(extracted_parameters={"bore_d": 20, "outer_d": 99})
            )
        )
        result = self._adapter().run(_input(), run_id="r3")
        rec = result.record
        self.assertFalse(rec.construction_ready)
        self.assertEqual(rec.stage_status("schema"), "fail")
        # The explicit claim is preserved in the projection raw_extraction.
        self.assertEqual(result.projection.raw_extraction["outer_d"], 99)
        self.assertEqual(rec.stage_status("construction_gate"), "fail")
        self.assertEqual(rec.stage_status("cad"), "not_run")

    def test_unknown_field_in_extracted_parameters_fails_projection(self):
        self.transport.queue_response(
            _deepseek_response(
                body=_envelope_body(extracted_parameters={"bore_d": 20, "color": "red"})
            )
        )
        result = self._adapter().run(_input(), run_id="r4")
        rec = result.record
        # Parser rejects unknown field already; projection never reached.
        self.assertEqual(rec.stage_status("parse"), "fail")

    def test_unsupported_requests_block_construction(self):
        self.transport.queue_response(
            _deepseek_response(
                body=_envelope_body(
                    decision="answer",
                    extracted_parameters={"bore_d": 20},
                    unsupported_requests=["flange"],
                )
            )
        )
        result = self._adapter().run(_input(), run_id="r5")
        rec = result.record
        # Schema passes but construction gate fails due to unsupported_requests.
        self.assertEqual(rec.stage_status("schema"), "pass")
        self.assertFalse(rec.construction_ready)
        self.assertEqual(rec.stage_status("construction_gate"), "fail")
        self.assertEqual(rec.stage_status("cad"), "not_run")

    def test_refuse_decision_not_construction_ready(self):
        self.transport.queue_response(
            _deepseek_response(
                body=_envelope_body(decision="refuse", extracted_parameters={},
                                     questions=["out of scope"])
            )
        )
        result = self._adapter().run(_input(), run_id="r6")
        rec = result.record
        self.assertFalse(rec.construction_ready)
        self.assertEqual(rec.stage_status("construction_gate"), "fail")

    def test_parse_failure_recorded_and_no_construction(self):
        self.transport.queue_response(
            TransportResponse(status=200, body="```json\n" + _envelope_body() + "\n```")
        )
        result = self._adapter().run(_input(), run_id="r7")
        rec = result.record
        self.assertEqual(rec.stage_status("parse"), "fail")
        self.assertFalse(rec.construction_ready)
        self.assertEqual(rec.stage_status("schema"), "not_run")

    def test_transient_retry_then_success(self):
        sleeps = []
        self.transport.queue_error(TransportError(COND_HTTP_429, 429, "rate"))
        self.transport.queue_response(_deepseek_response())
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=lambda s: sleeps.append(s))
        result = adapter.run(_input(), run_id="r8")
        rec = result.record
        self.assertTrue(rec.construction_ready)
        self.assertEqual(rec.attempt_count, 2)
        self.assertEqual(sleeps, [1])

    def test_non_retryable_auth_error_no_retry(self):
        from src.llm.transport import COND_AUTH_PERMISSION

        self.transport.queue_error(TransportError(COND_AUTH_PERMISSION, 401, "auth"))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=_NoSleep())
        result = adapter.run(_input(), run_id="r9")
        rec = result.record
        self.assertEqual(rec.stage_status("model_call"), "fail")
        self.assertEqual(rec.attempt_count, 1)
        self.assertFalse(rec.construction_ready)

    def test_usage_with_missing_cache_fields_yields_not_available_cost(self):
        """3.3: cache hit/miss missing -> cost must be not_available, never estimated."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body=_envelope_body(),
                runtime_returned_model=DEEPSEEK_MODEL,
                usage={"prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46},
                # prompt_cache_hit_tokens and prompt_cache_miss_tokens are absent
            )
        )
        result = self._adapter().run(_input(), run_id="r10")
        rec = result.record
        # Cost must be None (not_available) because cache fields are missing.
        self.assertIsNone(rec.cloud_cost_amount)


class OllamaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()

    def _adapter(self):
        return Adapter(provider=OLLAMA_PROVIDER, transport=self.transport, sleeper=_NoSleep())

    def test_local_run_records_wall_time_no_cloud_tokens(self):
        self.transport.queue_response(_ollama_response())
        result = self._adapter().run(_input(), run_id="o1")
        rec = result.record
        self.assertTrue(rec.construction_ready)
        self.assertEqual(rec.configured_provider, OLLAMA_PROVIDER)
        self.assertEqual(rec.local_digest, OLLAMA_DIGEST)
        self.assertIsNotNone(rec.local_wall_time_ms)
        self.assertIsNone(rec.cloud_input_tokens)
        self.assertIsNone(rec.cloud_cost_amount)

    def test_ollama_no_think_field_in_request(self):
        self.transport.queue_response(_ollama_response())
        adapter = self._adapter()
        adapter.run(_input(), run_id="o2")
        req = self.transport.last_call()
        self.assertEqual(req.provider, OLLAMA_PROVIDER)
        self.assertFalse(req.body["think"])
        # format is now a structured JSON Schema object (not the plain string "json")
        self.assertIsInstance(req.body["format"], dict)
        self.assertNotIn("thinking", req.body)


class RunRecordTests(unittest.TestCase):
    def test_record_serializes_to_json(self):
        self.transport = FakeTransport()
        self.transport.queue_response(_deepseek_response())
        result = Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=_NoSleep()).run(_input(), run_id="s1")
        text = result.record.to_json()
        data = json.loads(text)
        self.assertEqual(data["run_id"], "s1")
        self.assertIn("stages", data)
        self.assertTrue(data["construction_ready"])
        self.assertFalse(data["formal_evaluation_allowed"])

    def test_stage_status_lookup(self):
        self.transport = FakeTransport()
        self.transport.queue_response(_deepseek_response())
        rec = Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=_NoSleep()).run(_input(), run_id="s2").record
        self.assertEqual(rec.stage_status("model_call"), "pass")
        self.assertIsNone(rec.stage_status("nonexistent_stage"))


class DeepSeekUsagePropagationTests(unittest.TestCase):
    """APP-001-PHASE1-FIX Part 2: usage/token/cost fields recorded before parse gate."""

    def setUp(self):
        self.transport = FakeTransport()

    def _adapter(self):
        return Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport, sleeper=_NoSleep())

    def test_usage_captured_when_parse_fails(self):
        """cloud_input_tokens populated even when parse stage fails."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="not a valid json envelope",  # parse will fail
                runtime_returned_model=DEEPSEEK_MODEL,
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "total_tokens": 125,
                    "prompt_cache_hit_tokens": 80,
                    "prompt_cache_miss_tokens": 20,
                },
            )
        )
        result = self._adapter().run(_input(), run_id="u1")
        rec = result.record
        self.assertEqual(rec.stage_status("model_call"), "pass")
        self.assertEqual(rec.stage_status("parse"), "fail")
        self.assertEqual(rec.cloud_input_tokens, 100)
        self.assertEqual(rec.cloud_output_tokens, 25)
        self.assertEqual(rec.cloud_total_tokens, 125)
        self.assertEqual(rec.cloud_cached_input_tokens, 80)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 20)

    def test_usage_complete_with_full_cache_fields(self):
        """Full usage + cache fields → cost is computed (not not_available)."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body=_envelope_body(),
                runtime_returned_model=DEEPSEEK_MODEL,
                usage={
                    "prompt_tokens": 200,
                    "completion_tokens": 50,
                    "total_tokens": 250,
                    "prompt_cache_hit_tokens": 150,
                    "prompt_cache_miss_tokens": 50,
                },
            )
        )
        result = self._adapter().run(_input(), run_id="u2")
        rec = result.record
        self.assertEqual(rec.cloud_input_tokens, 200)
        self.assertEqual(rec.cloud_output_tokens, 50)
        self.assertEqual(rec.cloud_cached_input_tokens, 150)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 50)
        self.assertIsNotNone(rec.cloud_cost_amount)

    def test_missing_cache_fields_yields_none_cost_not_guessed(self):
        """Missing cache fields → cost is None (not_available), not guessed."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body=_envelope_body(),
                runtime_returned_model=DEEPSEEK_MODEL,
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 30,
                    "total_tokens": 130,
                },
            )
        )
        result = self._adapter().run(_input(), run_id="u3")
        rec = result.record
        self.assertEqual(rec.cloud_input_tokens, 100)
        self.assertIsNone(rec.cloud_cached_input_tokens)
        self.assertIsNone(rec.cloud_cache_miss_input_tokens)
        self.assertIsNone(rec.cloud_cost_amount)

    def test_inconsistent_cache_counts_yield_none_cost(self):
        """cache_hit + cache_miss != prompt_tokens → cost is None, not guessed."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body=_envelope_body(),
                runtime_returned_model=DEEPSEEK_MODEL,
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 30,
                    "total_tokens": 130,
                    "prompt_cache_hit_tokens": 60,
                    "prompt_cache_miss_tokens": 60,  # 60+60=120 != 100
                },
            )
        )
        result = self._adapter().run(_input(), run_id="u4")
        rec = result.record
        self.assertEqual(rec.cloud_cached_input_tokens, 60)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 60)
        self.assertIsNone(rec.cloud_cost_amount)

    def test_no_usage_in_response_yields_none_fields(self):
        """When usage is absent from response, all cloud fields must stay None."""
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body=_envelope_body(),
                runtime_returned_model=DEEPSEEK_MODEL,
                usage=None,
            )
        )
        result = self._adapter().run(_input(), run_id="u5")
        rec = result.record
        self.assertIsNone(rec.cloud_input_tokens)
        self.assertIsNone(rec.cloud_output_tokens)
        self.assertIsNone(rec.cloud_cost_amount)


class OllamaUsageUnavailableTests(unittest.TestCase):
    """Ollama usage is not_applicable; cloud fields stay None."""

    def setUp(self):
        self.transport = FakeTransport()

    def _adapter(self):
        return Adapter(provider=OLLAMA_PROVIDER, transport=self.transport, sleeper=_NoSleep())

    def test_ollama_cloud_fields_always_none(self):
        """Ollama runs never have cloud token/cost fields."""
        self.transport.queue_response(
            TransportResponse(status=200, body=_envelope_body(),
                              runtime_returned_model=None, usage=None)
        )
        result = self._adapter().run(_input(), run_id="o10")
        rec = result.record
        self.assertIsNone(rec.cloud_input_tokens)
        self.assertIsNone(rec.cloud_output_tokens)
        self.assertIsNone(rec.cloud_total_tokens)
        self.assertIsNone(rec.cloud_cached_input_tokens)
        self.assertIsNone(rec.cloud_cache_miss_input_tokens)
        self.assertIsNone(rec.cloud_cost_amount)

    def test_ollama_local_wall_time_captured_even_on_parse_fail(self):
        """local_wall_time_ms recorded before parse; captured on parse fail too."""
        self.transport.queue_response(
            TransportResponse(status=200, body="not a valid json envelope",
                              runtime_returned_model=None, usage=None)
        )
        result = self._adapter().run(_input(), run_id="o11")
        rec = result.record
        self.assertEqual(rec.stage_status("parse"), "fail")
        self.assertIsNotNone(rec.local_wall_time_ms)


if __name__ == "__main__":
    unittest.main()
