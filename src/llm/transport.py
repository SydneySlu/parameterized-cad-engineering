"""Injectable transport abstraction for APP-001 model calls.

The adapter never performs real network calls in this task.  A transport is an
injectable object that takes a prepared request and returns a response or a
classified error.  Tests inject :class:`FakeTransport`; a real HTTP transport
can exist for future authorized runs but is not wired into any runnable entry
point here.

Security: transport implementations must never log Authorization headers, full
request headers, full provider error bodies, or response content beyond what
the run-record policy allows.  The :class:`TransportError` carries only a
stable ``condition``, an HTTP status (when applicable), and a short redacted
message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Classified transport errors
# ---------------------------------------------------------------------------

# Conditions
COND_TIMEOUT = "connection_or_read_timeout"
COND_INTERRUPTION = "connection_interruption"
COND_HTTP_429 = "http_429"
COND_HTTP_5XX = "http_5xx"
COND_AUTH_PERMISSION = "authentication_or_permission"
COND_MALFORMED_REQUEST = "malformed_request"
COND_CONTEXT_OVERFLOW = "context_overflow"
COND_INVALID_JSON = "invalid_json"
COND_OTHER_NON_RETRYABLE = "other_non_retryable"

RETRYABLE_CONDITIONS = frozenset({COND_TIMEOUT, COND_INTERRUPTION, COND_HTTP_429, COND_HTTP_5XX})


@dataclass(frozen=True)
class TransportError(Exception):
    """A classified, redacted transport error.

    ``message`` must be redacted -- never include the full response body,
    headers, Authorization, or any secret.  Use a short stable summary.
    """

    condition: str
    http_status: int | None
    message: str

    def is_retryable(self) -> bool:
        return self.condition in RETRYABLE_CONDITIONS


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransportResponse:
    """A successful transport response carrying only what the adapter needs."""

    status: int
    body: str
    # Runtime identity fields the API may expose (None if not exposed).
    runtime_returned_model: str | None = None
    runtime_returned_provider: str | None = None
    # Cloud usage fields (None when not applicable, e.g. local Ollama).
    usage: dict[str, Any] | None = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "runtime_returned_model": self.runtime_returned_model,
            "runtime_returned_provider": self.runtime_returned_provider,
            "usage": self.usage,
        }


# ---------------------------------------------------------------------------
# Prepared request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedRequest:
    """A provider-specific, ready-to-send request."""

    provider: str
    model: str
    base_url: str
    endpoint: str
    # The request body is the JSON-serializable payload (without secrets).
    body: dict[str, Any]
    # The Authorization header value is held separately and never serialized
    # into a run record; it is only used by a real transport.
    authorization: str | None = None
    # Provider-specific headers that are not secret (e.g. Content-Type).
    headers: dict[str, str] = field(default_factory=dict)

    def body_json(self) -> str:
        import json

        return json.dumps(self.body, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Transport protocol
# ---------------------------------------------------------------------------


class Transport(Protocol):
    """A callable transport: send a prepared request, get a response or error."""

    def send(self, request: PreparedRequest) -> TransportResponse:
        """Send the request.  Raise :class:`TransportError` on failure."""
        ...


# ---------------------------------------------------------------------------
# Fake transport for tests
# ---------------------------------------------------------------------------


class FakeTransport:
    """An injectable transport that returns scripted responses or errors.

    Records every request it receives (without the Authorization value) so
    tests can assert on the prepared payloads.  Never performs any network I/O.
    """

    def __init__(self) -> None:
        self.calls: list[PreparedRequest] = []
        self._scripted: list[Any] = []  # list of TransportResponse or TransportError
        self._index = 0

    def queue_response(self, response: TransportResponse) -> None:
        self._scripted.append(response)

    def queue_error(self, error: TransportError) -> None:
        self._scripted.append(error)

    def queue_sequence(self, items: list[Any]) -> None:
        for item in items:
            self._scripted.append(item)

    def send(self, request: PreparedRequest) -> TransportResponse:
        # Record the request without the Authorization value.
        self.calls.append(request)
        if self._index >= len(self._scripted):
            raise AssertionError("FakeTransport: no more scripted responses; calls exceeded script")
        item = self._scripted[self._index]
        self._index += 1
        if isinstance(item, TransportError):
            raise item
        return item

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def last_call(self) -> PreparedRequest | None:
        return self.calls[-1] if self.calls else None

    def reset(self) -> None:
        self.calls = []
        self._scripted = []
        self._index = 0
