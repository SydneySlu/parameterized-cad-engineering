"""Retry and transient-fault classification tests with injectable clock/sleeper.

Covers: success on first attempt, transient retry then success, exhausted
retries, non-retryable error stops immediately, backoff order (1s then 2s),
no real sleep called.

3.4: total_elapsed_ms (including backoff) tests added.
"""

import unittest

from src.llm.contract import BACKOFF_SECONDS, MAX_ATTEMPTS_TOTAL
from src.llm.providers import build_deepseek_request, build_ollama_request
from src.llm.retry import send_with_retry
from src.llm.transport import (
    COND_AUTH_PERMISSION,
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_INTERRUPTION,
    COND_TIMEOUT,
    FakeTransport,
    TransportError,
    TransportResponse,
)


SYSTEM = "s"
USER = "u"


def _ok_response(status=200, body="{}", model="deepseek-flash", usage=None):
    return TransportResponse(status=status, body=body, runtime_returned_model=model, usage=usage or {})


class RetrySuccessTests(unittest.TestCase):
    def test_success_first_attempt_no_sleep(self):
        sleeps = []
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, total_ms = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
        self.assertIsNotNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "success")
        self.assertEqual(sleeps, [])
        self.assertGreaterEqual(total_ms, 0)

    def test_success_after_one_transient_retry(self):
        sleeps = []
        transport = FakeTransport()
        transport.queue_error(TransportError(COND_TIMEOUT, None, "timeout"))
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, total_ms = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
        self.assertIsNotNone(response)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes[0].outcome, "transient_retryable")
        self.assertEqual(outcomes[1].outcome, "success")
        self.assertEqual(sleeps, [1])  # backoff[0]

    def test_success_after_two_retries(self):
        sleeps = []
        transport = FakeTransport()
        transport.queue_error(TransportError(COND_HTTP_429, 429, "rate"))
        transport.queue_error(TransportError(COND_HTTP_5XX, 500, "server"))
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, total_ms = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
        self.assertIsNotNone(response)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual(sleeps, [1, 2])  # backoff order


class RetryExhaustionTests(unittest.TestCase):
    def test_exhausted_after_max_attempts(self):
        sleeps = []
        transport = FakeTransport()
        for _ in range(MAX_ATTEMPTS_TOTAL):
            transport.queue_error(TransportError(COND_HTTP_5XX, 500, "down"))
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, total_ms = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), MAX_ATTEMPTS_TOTAL)
        self.assertEqual(outcomes[-1].outcome, "exhausted")
        self.assertEqual(sleeps, [1, 2])

    def test_all_retryable_conditions_retried(self):
        for cond in (COND_TIMEOUT, COND_INTERRUPTION, COND_HTTP_429, COND_HTTP_5XX):
            with self.subTest(cond=cond):
                transport = FakeTransport()
                transport.queue_error(TransportError(cond, None, "x"))
                transport.queue_response(_ok_response())
                req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
                response, outcomes, _ = send_with_retry(transport, req, sleeper=lambda s: None)
                self.assertIsNotNone(response)
                self.assertEqual(outcomes[0].outcome, "transient_retryable")

    def test_backoff_order_is_fixed_1_then_2(self):
        self.assertEqual(BACKOFF_SECONDS, (1, 2))
        self.assertEqual(MAX_ATTEMPTS_TOTAL, 3)


class NonRetryableTests(unittest.TestCase):
    def test_auth_error_not_retried(self):
        transport = FakeTransport()
        transport.queue_error(TransportError(COND_AUTH_PERMISSION, 401, "auth"))
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, _ = send_with_retry(transport, req, sleeper=lambda s: self.fail("should not sleep"))
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "non_retryable")

    def test_malformed_request_not_retried(self):
        from src.llm.transport import COND_MALFORMED_REQUEST

        transport = FakeTransport()
        transport.queue_error(TransportError(COND_MALFORMED_REQUEST, 400, "bad"))
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, _ = send_with_retry(transport, req, sleeper=lambda s: self.fail())
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "non_retryable")

    def test_context_overflow_not_retried(self):
        from src.llm.transport import COND_CONTEXT_OVERFLOW

        transport = FakeTransport()
        transport.queue_error(TransportError(COND_CONTEXT_OVERFLOW, 400, "too long"))
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes, _ = send_with_retry(transport, req, sleeper=lambda s: self.fail())
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)


class ElapsedTimeTests(unittest.TestCase):
    """3.4: total_elapsed_ms must include injected backoff waits."""

    def _make_clock(self, times):
        """Return a clock that steps through a list of times."""
        idx = [0]
        def clock():
            val = times[idx[0]] if idx[0] < len(times) else times[-1]
            idx[0] += 1
            return val
        return clock

    def test_success_first_attempt_elapsed_covers_request(self):
        # clock: overall_start=0.0, attempt_start=0.001, after_send=0.011, final=0.011
        times = [0.0, 0.001, 0.011, 0.011]
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        _, outcomes, total_ms = send_with_retry(
            transport, req,
            clock=self._make_clock(times),
            sleeper=lambda s: None,
        )
        # total = 0.011 - 0.0 = 0.011s = 11ms; attempt elapsed = 0.011 - 0.001 = 10ms
        self.assertAlmostEqual(total_ms, 11.0, places=3)
        self.assertAlmostEqual(outcomes[0].elapsed_ms, 10.0, places=3)
        # total >= per-attempt duration
        self.assertGreaterEqual(total_ms, outcomes[0].elapsed_ms)

    def test_retry_success_elapsed_includes_backoff(self):
        # Simulate: overall_start=0, attempt1_start=0, after_fail1=0.01,
        # (sleeper called with 1s, clock ticks to 1.01),
        # attempt2_start=1.01, after_success=1.02, final_read=1.02
        times = [0.0, 0.0, 0.01, 1.01, 1.01, 1.02, 1.02]
        sleeps = []
        transport = FakeTransport()
        transport.queue_error(TransportError(COND_HTTP_429, 429, "rate"))
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        _, outcomes, total_ms = send_with_retry(
            transport, req,
            clock=self._make_clock(times),
            sleeper=lambda s: sleeps.append(s),
        )
        self.assertEqual(sleeps, [1])
        # total elapsed ~= 1.02 - 0.0 = 1.02s = 1020ms; sum of attempts = 10+10 = 20ms
        self.assertGreater(total_ms, sum(o.elapsed_ms for o in outcomes))
        self.assertAlmostEqual(total_ms, 1020.0, delta=5.0)

    def test_exhausted_elapsed_includes_both_backoffs(self):
        # 3 attempts, each 10ms, backoffs 1s + 2s
        # overall_start=0, a1_start=0, a1_end=0.01, a2_start=1.01, a2_end=1.02,
        # a3_start=3.02, a3_end=3.03, final=3.03
        times = [0.0, 0.0, 0.01, 1.01, 1.02, 3.02, 3.03, 3.03]
        sleeps = []
        transport = FakeTransport()
        for _ in range(MAX_ATTEMPTS_TOTAL):
            transport.queue_error(TransportError(COND_HTTP_5XX, 500, "down"))
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        _, outcomes, total_ms = send_with_retry(
            transport, req,
            clock=self._make_clock(times),
            sleeper=lambda s: sleeps.append(s),
        )
        self.assertIsNone(_)
        self.assertEqual(sleeps, [1, 2])
        self.assertGreater(total_ms, sum(o.elapsed_ms for o in outcomes))
        self.assertAlmostEqual(total_ms, 3030.0, delta=5.0)


class FakeTransportTrackingTests(unittest.TestCase):
    def test_fake_transport_stores_sanitized_copy_no_authorization(self):
        """3.1: FakeTransport must not store authorization values."""
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        # Build a request and manually set authorization to simulate a future
        # real transport scenario (mock path requests are credential-free by
        # default, but we test the sanitization is enforced regardless).
        from src.llm.transport import PreparedRequest
        req = PreparedRequest(
            provider="DeepSeek",
            model="deepseek-flash",
            base_url="https://api.deepseek.com",
            endpoint="/chat/completions",
            body={"model": "deepseek-flash"},
            authorization="Bearer synthetic-test-secret",
        )
        transport.send(req)
        self.assertEqual(transport.call_count, 1)
        stored = transport.last_call()
        # Stored copy must have authorization cleared.
        self.assertIsNone(stored.authorization)

    def test_fake_transport_reset(self):
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        transport.send(req)
        transport.reset()
        self.assertEqual(transport.call_count, 0)

    def test_default_mock_request_has_no_authorization(self):
        """3.1: The default mock-path request builder produces no authorization."""
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        self.assertIsNone(req.authorization)
        transport.send(req)
        self.assertIsNone(transport.last_call().authorization)


if __name__ == "__main__":
    unittest.main()
