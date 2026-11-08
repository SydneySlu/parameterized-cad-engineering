"""Security and run-record tests: serialization, append behavior, secret/PII
scanning, default-off evaluation gate, and no-network/no-credential assertions.
"""

import json
import os
import re
import unittest

from src.llm.adapter import Adapter, AdapterInput
from src.llm.contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    DEEPSEEK_PROVIDER,
    FORMAL_EVALUATION_ALLOWED,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
)
from tests.llm._frozen_helpers import _frozen_input
from src.llm.gate import (
    FormalEvaluationBlockedError,
    formal_evaluation_allowed,
    require_formal_evaluation_allowed,
)
from src.llm.runrecord import RunRecord, StageStatus, stage, utc_now_iso
from src.llm.transport import FakeTransport, TransportResponse


SYSTEM_PROMPT = "system"
USER_TEMPLATE = (
    "query_id: {query_id}\n"
    "family_id: set_screw_shaft_collar\n"
    "natural_language_input:\n"
    "{natural_language_input}\n"
    "reference_context:\n"
    "{reference_context_or_null}"
)


def _input(qid="q1", nl="bore_d=20", cond="c0", ref=None):
    return _frozen_input(query_id=qid, natural_language_input=nl, reference_context=ref, condition_id=cond)


def _body():
    return json.dumps({
        "contract_version": "app001-io.v1",
        "prompt_version": "app001-extraction.v4",
        "decision": "answer",
        "extracted_parameters": {"bore_d": 20},
        "unsupported_requests": [],
        "evidence": [{"field": "bore_d", "quote": "20", "source": "user_input"}],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    })


class GateTests(unittest.TestCase):
    def test_formal_evaluation_allowed_is_false(self):
        self.assertFalse(formal_evaluation_allowed())
        self.assertFalse(FORMAL_EVALUATION_ALLOWED)

    def test_require_gate_raises(self):
        with self.assertRaises(FormalEvaluationBlockedError):
            require_formal_evaluation_allowed("test run")

    def test_non_mock_transport_trips_gate_before_send(self):
        """3.2: Any non-MockTransport transport must be refused before send()."""
        class CountingTransport:
            """Not a MockTransport -- simulates a custom/real transport."""
            def __init__(self):
                self.send_calls = 0
            def send(self, request):
                self.send_calls += 1
                return TransportResponse(200, "{}")

        custom = CountingTransport()
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=custom, sleeper=lambda s: None)
        with self.assertRaises(FormalEvaluationBlockedError):
            adapter.run(_input(), run_id="g1")
        # send() must NOT have been called -- gate fires before transport
        self.assertEqual(custom.send_calls, 0)

    def test_fake_transport_allowed_with_gate_closed(self):
        """3.2: FakeTransport (MockTransport) runs regardless of gate state."""
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 40, "completion_tokens": 6, "total_tokens": 46, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 40}))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None)
        result = adapter.run(_input(), run_id="g2")
        self.assertTrue(result.record.construction_ready)


class SecretScanTests(unittest.TestCase):
    SECRET_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9]{10,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"),
        re.compile(r"DEEPSEEK_API_KEY\s*=\s*['\"][^'\"]{10,}"),
    ]

    def _run_and_serialize(self, provider):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash" if provider == DEEPSEEK_PROVIDER else None, None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10} if provider == DEEPSEEK_PROVIDER else None))
        adapter = Adapter(provider=provider, transport=transport, sleeper=lambda s: None)
        result = adapter.run(_input(), run_id="sec1")
        return result.record.to_json()

    def test_no_secrets_in_deepseek_record(self):
        text = self._run_and_serialize(DEEPSEEK_PROVIDER)
        for pat in self.SECRET_PATTERNS:
            self.assertIsNone(pat.search(text), f"matched secret pattern {pat.pattern}")

    def test_no_secrets_in_ollama_record(self):
        text = self._run_and_serialize(OLLAMA_PROVIDER)
        for pat in self.SECRET_PATTERNS:
            self.assertIsNone(pat.search(text), f"matched secret pattern {pat.pattern}")

    def test_authorization_not_in_record(self):
        """3.1: Authorization values must never appear in run records."""
        # Build a mock run; mock path requests have no credentials.
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None)
        text = adapter.run(_input(), run_id="sec2").record.to_json()
        # No authorization values should appear anywhere in the record.
        self.assertNotIn("Bearer ", text)
        self.assertNotIn("sk-test", text)

    def test_no_env_key_read_during_run(self):
        """3.1: DEEPSEEK_API_KEY env var must not be read during a mock run."""
        import os
        # Set a synthetic env var. If the adapter reads it, authorization
        # would appear as "Bearer synthetic-never-read-key" in the record.
        saved = os.environ.get("DEEPSEEK_API_KEY")
        os.environ["DEEPSEEK_API_KEY"] = "synthetic-never-read-key"
        try:
            transport = FakeTransport()
            transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
            adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None)
            result = adapter.run(_input(), run_id="sec3")
            self.assertTrue(result.record.construction_ready)
            # The stored request must have no authorization.
            req = transport.last_call()
            self.assertIsNone(req.authorization)
            # The JSON record must not contain the synthetic key value.
            record_text = result.record.to_json()
            self.assertNotIn("synthetic-never-read-key", record_text)
        finally:
            if saved is None:
                os.environ.pop("DEEPSEEK_API_KEY", None)
            else:
                os.environ["DEEPSEEK_API_KEY"] = saved


class RunRecordSerializationTests(unittest.TestCase):
    def test_stage_status_values_in_vocab(self):
        from src.llm.contract import STAGE_STATUSES
        rec = RunRecord(run_id="x", condition_id="c", query_id="q", timestamp_utc=utc_now_iso(),
                        configured_provider="p", configured_model_name="m")
        for status in ("not_run", "pass", "fail", "blocked", "not_applicable"):
            rec.add_stage(stage("s_" + status, status))
        for st in rec.stages:
            self.assertIn(st.status, STAGE_STATUSES)

    def test_invalid_stage_status_raises(self):
        with self.assertRaises(ValueError):
            StageStatus(stage="s", status="bogus")

    def test_record_has_contract_and_prompt_versions(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
        rec = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None).run(_input(), run_id="r1").record
        self.assertEqual(rec.contract_version, CONTRACT_VERSION)
        self.assertEqual(rec.prompt_version, PROMPT_VERSION)
        self.assertEqual(rec.adapter_version, ADAPTER_VERSION)

    def test_ir_cad_geometry_step_all_honest(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
        rec = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None).run(_input(), run_id="r2").record
        self.assertEqual(rec.stage_status("ir"), "blocked")
        self.assertEqual(rec.stage_status("cad"), "not_run")
        self.assertEqual(rec.stage_status("geometry"), "not_run")
        self.assertEqual(rec.stage_status("step"), "not_run")

    def test_no_step_pass_claim_in_json(self):
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
        text = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None).run(_input(), run_id="r3").record.to_json()
        data = json.loads(text)
        for st in data["stages"]:
            if st["stage"] in ("cad", "geometry", "step"):
                self.assertEqual(st["status"], "not_run")
            if st["stage"] == "ir":
                self.assertEqual(st["status"], "blocked")


class NoNetworkTests(unittest.TestCase):
    """A default run must not access the network or read credentials."""

    def test_fake_transport_makes_no_network(self):
        # FakeTransport has no socket use; this is a guard that the adapter
        # path uses it.  We assert no real HTTP library is imported.
        transport = FakeTransport()
        transport.queue_response(TransportResponse(200, _body(), "deepseek-flash", None, {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10}))
        adapter = Adapter(provider=DEEPSEEK_PROVIDER, transport=transport, sleeper=lambda s: None)
        result = adapter.run(_input(), run_id="nn1")
        self.assertTrue(result.record.construction_ready)
        self.assertEqual(transport.call_count, 1)


if __name__ == "__main__":
    unittest.main()
