"""Integration test: DeepSeek HTTP JSON fixture → transport → Adapter → RunRecord/cost.

Tests usage propagation through the real DeepSeekTransport parse path, using a
desensitised fixture that matches the DeepSeek Chat Completions API response shape
(constructed from the DeepSeek documentation and saved probe responses; the actual
formal batch app001-phase1-20261107-01 raw responses do not include the full HTTP
usage/model envelope because they are stored as parsed bodies only).

Strategy: we test the transport → RunRecord path in three tiers.

Tier 1 (transport-layer): calls DeepSeekTransport._parse_response() directly to
verify the usage dict it builds from the JSON fixture.  No BudgetAwareTransport or
Adapter gate needed.

Tier 2 (adapter-layer): uses the existing FakeTransport-based Adapter pattern
from test_adapter.py to verify usage propagation through Adapter._record_cloud_
usage_and_cost() and into RunRecord.  The transport-layer fixture values are
injected as the usage dict in a TransportResponse, then the Adapter processes it.

Tier 3 (end-to-end): patches urllib.request.urlopen with the full JSON fixture so
the real DeepSeekTransport._parse_response() is invoked.  Wraps it in a
BudgetAwareTransport with the exact query/condition/run-id binding that the Adapter
gate requires, then calls Adapter.run() with a FormalRunAuthorization.  Asserts
that urlopen is called exactly once, all five usage fields match the fixture, the
parse stage fails (fixture content is not a valid APP-001 envelope), usage is still
present after the parse failure, cost is computed when cache fields are consistent,
and runtime_returned_model matches the fixture.

No network calls are made.  DEEPSEEK_API_KEY is set via patch.dict to a dummy test
value (never logged, printed, or written to any file) and restored after each test.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Desensitised fixture: matches the real Chat Completions API shape.
# No real keys, no real user data, no real model responses.
# ---------------------------------------------------------------------------

_DEEPSEEK_FIXTURE_FULL_CACHE = {
    "id": "test-fixture-001",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "deepseek-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                # Intentionally not a valid APP-001 envelope so we can verify
                # that usage is captured even when parse fails.
                "content": "This is a test response that does not parse as a CAD-003 envelope.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 240,
        "completion_tokens": 18,
        "total_tokens": 258,
        "prompt_cache_hit_tokens": 192,
        "prompt_cache_miss_tokens": 48,
    },
}

_DEEPSEEK_FIXTURE_NO_CACHE = {
    "id": "test-fixture-002",
    "object": "chat.completion",
    "created": 1700000001,
    "model": "deepseek-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Another non-envelope response.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110,
        # cache fields absent — should yield cost = None
    },
}

_DEEPSEEK_FIXTURE_INCONSISTENT_CACHE = {
    "id": "test-fixture-003",
    "object": "chat.completion",
    "created": 1700000002,
    "model": "deepseek-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Inconsistent cache counts.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110,
        "prompt_cache_hit_tokens": 70,
        "prompt_cache_miss_tokens": 70,  # 70+70=140 != 100
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeResp:
    """Minimal HTTP response wrapper for urlopen mock."""

    def __init__(self, data: bytes, status: int = 200):
        self._data = data
        self.status = status

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_deepseek_fixture_resp(fixture: dict) -> _FakeResp:
    return _FakeResp(json.dumps(fixture).encode("utf-8"))


# ---------------------------------------------------------------------------
# Tier 1: Transport-layer parse tests (no Adapter, no gate, no network)
# ---------------------------------------------------------------------------


class TestDeepSeekTransportParsesUsageFixture(unittest.TestCase):
    """Verify DeepSeekTransport._parse_response() correctly extracts usage fields
    from the desensitised JSON fixture.

    No urlopen, no API key, no Adapter gate.
    """

    def _parse(self, fixture: dict):
        """Call _parse_response on the fixture JSON."""
        import sys; sys.path.insert(0, str(REPO_ROOT / "src"))
        from llm.real_transport import DeepSeekTransport
        from llm.authorization import authorize_phase1_run

        auth = authorize_phase1_run(batch_id="test-transport-parse")
        t = DeepSeekTransport(auth)
        raw = json.dumps(fixture)
        return t._parse_response(status=200, raw=raw)

    def test_full_cache_usage_parsed(self):
        """Full cache fixture: all five usage keys extracted correctly."""
        resp = self._parse(_DEEPSEEK_FIXTURE_FULL_CACHE)
        u = resp.usage
        self.assertEqual(u.get("prompt_tokens"), 240)
        self.assertEqual(u.get("completion_tokens"), 18)
        self.assertEqual(u.get("total_tokens"), 258)
        self.assertEqual(u.get("prompt_cache_hit_tokens"), 192)
        self.assertEqual(u.get("prompt_cache_miss_tokens"), 48)
        self.assertEqual(resp.runtime_returned_model, "deepseek-flash")

    def test_no_cache_fields_none(self):
        """Fixture without cache fields: prompt_cache_* are None."""
        resp = self._parse(_DEEPSEEK_FIXTURE_NO_CACHE)
        u = resp.usage
        self.assertEqual(u.get("prompt_tokens"), 100)
        self.assertEqual(u.get("completion_tokens"), 10)
        self.assertIsNone(u.get("prompt_cache_hit_tokens"),
                           "cache hit must be None when absent")
        self.assertIsNone(u.get("prompt_cache_miss_tokens"),
                           "cache miss must be None when absent")

    def test_inconsistent_cache_fields_propagated(self):
        """Inconsistent cache fixture: values propagated as-is (cost layer rejects them)."""
        resp = self._parse(_DEEPSEEK_FIXTURE_INCONSISTENT_CACHE)
        u = resp.usage
        self.assertEqual(u.get("prompt_tokens"), 100)
        self.assertEqual(u.get("prompt_cache_hit_tokens"), 70)
        self.assertEqual(u.get("prompt_cache_miss_tokens"), 70)
        # Transport does not check consistency — that is the cost layer's job.


# ---------------------------------------------------------------------------
# Tier 2: Adapter-layer propagation tests
#
# Uses the FakeTransport pattern (same as test_adapter.py), injecting the
# usage dict built in Tier 1 into TransportResponse.  Exercises
# Adapter._record_cloud_usage_and_cost() → RunRecord → cost.compute_cloud_cost().
# ---------------------------------------------------------------------------


class TestDeepSeekUsagePropagationViaAdapter(unittest.TestCase):
    """Verify usage → RunRecord → cost propagation through the Adapter.

    Uses FakeTransport with TransportResponse carrying the fixture usage dict,
    matching the exact format that DeepSeekTransport._parse_response() returns.
    No urlopen, no real API calls.
    """

    def setUp(self):
        import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
        from llm.transport import FakeTransport
        self.transport = FakeTransport()

    def _adapter(self):
        from llm.adapter import Adapter
        from llm.contract import DEEPSEEK_PROVIDER
        return Adapter(provider=DEEPSEEK_PROVIDER, transport=self.transport,
                       sleeper=lambda s: None)

    def _input(self):
        from tests.llm._frozen_helpers import _frozen_input
        return _frozen_input(query_id="fq1", condition_id="c0")

    def test_full_cache_usage_propagates_to_runrecord(self):
        """Full cache fixture usage → all RunRecord cloud token fields set, cost computed."""
        from llm.transport import TransportResponse

        # Use the same usage dict that DeepSeekTransport._parse_response would build
        usage = {
            "prompt_tokens": 240,
            "completion_tokens": 18,
            "total_tokens": 258,
            "prompt_cache_hit_tokens": 192,
            "prompt_cache_miss_tokens": 48,
        }
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="not a valid envelope",  # parse fails; usage still captured
                runtime_returned_model="deepseek-flash",
                usage=usage,
            )
        )
        result = self._adapter().run(self._input(), run_id="r1")
        rec = result.record

        self.assertEqual(rec.stage_status("model_call"), "pass")
        self.assertEqual(rec.stage_status("parse"), "fail",
                         "parse fails for non-envelope content")

        # Token fields populated even with parse failure
        self.assertEqual(rec.cloud_input_tokens, 240)
        self.assertEqual(rec.cloud_output_tokens, 18)
        self.assertEqual(rec.cloud_total_tokens, 258)
        self.assertEqual(rec.cloud_cached_input_tokens, 192)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 48)

        # Cost: cache_hit(192) + cache_miss(48) = 240 = prompt_tokens → consistent
        self.assertIsNotNone(rec.cloud_cost_amount,
                              "cost must be computed when cache is consistent")
        self.assertIsInstance(rec.cloud_cost_amount, float)
        self.assertGreater(rec.cloud_cost_amount, 0.0)
        self.assertIsNotNone(rec.cloud_cost_source,
                              "cost_source must be set")
        self.assertEqual(rec.runtime_returned_model, "deepseek-flash")

    def test_no_cache_fields_cost_is_none(self):
        """No cache fields in usage → tokens present, cost is None."""
        from llm.transport import TransportResponse

        usage = {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
        }
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="not a valid envelope",
                runtime_returned_model="deepseek-flash",
                usage=usage,
            )
        )
        result = self._adapter().run(self._input(), run_id="r2")
        rec = result.record

        self.assertEqual(rec.cloud_input_tokens, 100)
        self.assertEqual(rec.cloud_output_tokens, 10)
        self.assertEqual(rec.cloud_total_tokens, 110)
        self.assertIsNone(rec.cloud_cached_input_tokens)
        self.assertIsNone(rec.cloud_cache_miss_input_tokens)
        self.assertIsNone(rec.cloud_cost_amount,
                           "cost must be None when cache fields absent")

    def test_inconsistent_cache_fields_cost_is_none(self):
        """Inconsistent cache counts → cost is None, tokens propagated."""
        from llm.transport import TransportResponse

        usage = {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
            "prompt_cache_hit_tokens": 70,
            "prompt_cache_miss_tokens": 70,  # 70+70=140 != 100
        }
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="not a valid envelope",
                runtime_returned_model="deepseek-flash",
                usage=usage,
            )
        )
        result = self._adapter().run(self._input(), run_id="r3")
        rec = result.record

        self.assertEqual(rec.cloud_input_tokens, 100)
        self.assertEqual(rec.cloud_cached_input_tokens, 70)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 70)
        self.assertIsNone(rec.cloud_cost_amount,
                           "cost must be None when cache counts are inconsistent")

    def test_usage_captured_even_when_parse_fails(self):
        """Usage is captured before parse; RunRecord has token data regardless of parse outcome."""
        from llm.transport import TransportResponse

        usage = {
            "prompt_tokens": 500,
            "completion_tokens": 42,
            "total_tokens": 542,
            "prompt_cache_hit_tokens": 400,
            "prompt_cache_miss_tokens": 100,
        }
        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="completely unparseable",
                runtime_returned_model="deepseek-flash",
                usage=usage,
            )
        )
        result = self._adapter().run(self._input(), run_id="r4")
        rec = result.record

        self.assertEqual(rec.stage_status("parse"), "fail")
        # Usage must still be present
        self.assertEqual(rec.cloud_input_tokens, 500,
                          "usage must be captured even when parse fails")
        self.assertEqual(rec.cloud_output_tokens, 42)
        self.assertIsNotNone(rec.cloud_cost_amount)

    def test_no_usage_in_response_all_cloud_fields_none(self):
        """No usage in response → all cloud fields remain None."""
        from llm.transport import TransportResponse

        self.transport.queue_response(
            TransportResponse(
                status=200,
                body="not a valid envelope",
                runtime_returned_model="deepseek-flash",
                usage=None,
            )
        )
        result = self._adapter().run(self._input(), run_id="r5")
        rec = result.record

        self.assertIsNone(rec.cloud_input_tokens)
        self.assertIsNone(rec.cloud_output_tokens)
        self.assertIsNone(rec.cloud_total_tokens)
        self.assertIsNone(rec.cloud_cached_input_tokens)
        self.assertIsNone(rec.cloud_cache_miss_input_tokens)
        self.assertIsNone(rec.cloud_cost_amount)


# ---------------------------------------------------------------------------
# Tier 3: End-to-end integration test
#
# Patches urllib.request.urlopen so the REAL DeepSeekTransport._parse_response()
# is exercised.  Wraps DeepSeekTransport in BudgetAwareTransport with the exact
# query/condition/run-id binding required by Adapter.run()'s gate check, then
# calls Adapter.run() with a FormalRunAuthorization.
# ---------------------------------------------------------------------------


class TestDeepSeekEndToEndFixtureFlow(unittest.TestCase):
    """End-to-end: urlopen mock → real DeepSeekTransport → BudgetAwareTransport
    → Adapter → RunRecord/cost.

    The full chain from HTTP response bytes to RunRecord fields is exercised.
    No real network calls.  DEEPSEEK_API_KEY patched to a dummy value.
    """

    # Desensitised fixture with consistent cache counts (192+48=240=prompt_tokens)
    _E2E_FIXTURE = {
        "id": "e2e-test-fixture-001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "deepseek-flash",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    # Deliberately not a valid APP-001 envelope: verifies that
                    # usage is captured even when the parse stage fails.
                    "content": "E2E test: not a valid CAD-003 envelope.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 240,
            "completion_tokens": 18,
            "total_tokens": 258,
            "prompt_cache_hit_tokens": 192,
            "prompt_cache_miss_tokens": 48,
        },
    }

    @patch("urllib.request.urlopen")
    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-only-not-a-secret"})
    def test_full_e2e_transport_adapter_usage_flow(self, mock_urlopen):
        """Full end-to-end: fixture bytes → DeepSeekTransport parse → RunRecord.

        Asserts:
        - urlopen called exactly once
        - all five usage fields match the fixture
        - parse fails (non-envelope content) but usage is still present
        - cost is computed (cache counts consistent: 192+48=240)
        - runtime_returned_model matches fixture
        - cost_source and cost_currency match the project rate card contract
        """
        import time
        import sys
        sys.path.insert(0, str(REPO_ROOT / "src"))

        from llm.authorization import authorize_phase1_run
        from llm.budget import BudgetAwareTransport, BudgetLedger
        from llm.real_transport import DeepSeekTransport
        from llm.adapter import Adapter, AdapterInput
        from llm.contract import DEEPSEEK_PROVIDER, RATE_CARD_CURRENCY, RATE_CARD_SOURCE
        from llm.prompt_loader import load_frozen_prompt

        # --- Setup ---
        batch_id = f"test-e2e-fixture-{int(time.time() * 1000) % 999999}"
        query_id = "A01-test"
        condition_id = "C0"
        provider = DEEPSEEK_PROVIDER
        model = "deepseek-flash"
        # logical_run_id must match {query_id}__{condition_id}__{provider}__{model}
        lrid = f"{query_id}__{condition_id}__{provider}__{model}"
        run_id = f"{batch_id}__{lrid}"

        auth = authorize_phase1_run(batch_id=batch_id)
        batch_dir = REPO_ROOT / "work" / "app001-runs" / batch_id

        # Configure mock: return fixture bytes as HTTP response
        fixture_bytes = json.dumps(self._E2E_FIXTURE).encode("utf-8")
        mock_urlopen.return_value = _FakeResp(fixture_bytes)

        # Build the exact stack that runner.py uses
        with BudgetLedger(batch_dir, auth) as ledger:
            inner = DeepSeekTransport(auth)
            budget_transport = BudgetAwareTransport(
                inner,
                ledger=ledger,
                authorization=auth,
                logical_run_id=lrid,
                provider=provider,
                model=model,
                adapter_run_id=run_id,
                query_id=query_id,
                condition_id=condition_id,
            )

            prompt_artifact = load_frozen_prompt()
            adapter_input = AdapterInput(
                query_id=query_id,
                natural_language_input="bore_d=20 mm set screw collar",
                reference_context=None,
                system_prompt=prompt_artifact.system_prompt,
                user_prompt_template=prompt_artifact.user_template,
                condition_id=condition_id,
            )

            adapter = Adapter(
                provider=DEEPSEEK_PROVIDER,
                transport=budget_transport,
                sleeper=lambda s: None,
            )

            result = adapter.run(
                adapter_input,
                run_id=run_id,
                formal_authorization=auth,
            )

        rec = result.record

        # --- Assertions ---

        # 1. urlopen called exactly once (one DeepSeek HTTP POST)
        self.assertEqual(mock_urlopen.call_count, 1,
                         "urlopen must be called exactly once")

        # 2. model_call must succeed (HTTP 200 received)
        self.assertEqual(rec.stage_status("model_call"), "pass",
                         "model_call must pass when transport returns 200")

        # 3. Five usage fields from fixture
        self.assertEqual(rec.cloud_input_tokens, 240)
        self.assertEqual(rec.cloud_output_tokens, 18)
        self.assertEqual(rec.cloud_total_tokens, 258)
        self.assertEqual(rec.cloud_cached_input_tokens, 192)
        self.assertEqual(rec.cloud_cache_miss_input_tokens, 48)

        # 4. parse fails (non-envelope content), but usage is still captured
        self.assertEqual(rec.stage_status("parse"), "fail",
                         "parse must fail for non-CAD-003-envelope content")
        self.assertIsNotNone(rec.cloud_input_tokens,
                              "usage must be captured even when parse fails")

        # 5. Cost computed: cache_hit(192) + cache_miss(48) = 240 = prompt_tokens
        self.assertIsNotNone(rec.cloud_cost_amount,
                              "cost must be computed when cache counts are consistent")
        self.assertIsInstance(rec.cloud_cost_amount, float)
        self.assertGreater(rec.cloud_cost_amount, 0.0)

        # 6. cost_source and cost_currency match project contract
        self.assertEqual(rec.cloud_cost_currency, RATE_CARD_CURRENCY)
        self.assertEqual(rec.cloud_cost_source, RATE_CARD_SOURCE)

        # 7. runtime_returned_model from fixture
        self.assertEqual(rec.runtime_returned_model, "deepseek-flash",
                         "runtime_returned_model must come from fixture model field")


if __name__ == "__main__":
    unittest.main()
