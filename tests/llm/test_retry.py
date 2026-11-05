"""Retry and transient-fault classification tests with injectable clock/sleeper.

Covers: success on first attempt, transient retry then success, exhausted
retries, non-retryable error stops immediately, backoff order (1s then 2s),
no real sleep called.
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
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
        self.assertIsNotNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "success")
        self.assertEqual(sleeps, [])

    def test_success_after_one_transient_retry(self):
        sleeps = []
        transport = FakeTransport()
        transport.queue_error(TransportError(COND_TIMEOUT, None, "timeout"))
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
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
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
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
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: sleeps.append(s))
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
                response, outcomes = send_with_retry(transport, req, sleeper=lambda s: None)
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
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: self.fail("should not sleep"))
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "non_retryable")

    def test_malformed_request_not_retried(self):
        from src.llm.transport import COND_MALFORMED_REQUEST

        transport = FakeTransport()
        transport.queue_error(TransportError(COND_MALFORMED_REQUEST, 400, "bad"))
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: self.fail())
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].outcome, "non_retryable")

    def test_context_overflow_not_retried(self):
        from src.llm.transport import COND_CONTEXT_OVERFLOW

        transport = FakeTransport()
        transport.queue_error(TransportError(COND_CONTEXT_OVERFLOW, 400, "too long"))
        req = build_ollama_request(system_prompt=SYSTEM, user_prompt=USER)
        response, outcomes = send_with_retry(transport, req, sleeper=lambda s: self.fail())
        self.assertIsNone(response)
        self.assertEqual(len(outcomes), 1)


class FakeTransportTrackingTests(unittest.TestCase):
    def test_fake_transport_records_calls_without_authorization(self):
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER, api_key="secret")
        transport.send(req)
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(transport.last_call().authorization, "Bearer secret")

    def test_fake_transport_reset(self):
        transport = FakeTransport()
        transport.queue_response(_ok_response())
        req = build_deepseek_request(system_prompt=SYSTEM, user_prompt=USER)
        transport.send(req)
        transport.reset()
        self.assertEqual(transport.call_count, 0)


if __name__ == "__main__":
    unittest.main()
