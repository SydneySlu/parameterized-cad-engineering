"""Injectable transport abstraction for APP-001 model calls.

The adapter never performs real network calls in this task.  A transport is an
injectable object that takes a prepared request and returns a response or a
classified error.  Tests inject :class:`FakeTransport`; a real HTTP transport
can exist for future authorized runs but is not wired into any runnable entry
point here.

Security:
- :class:`FakeTransport` (a :class:`MockTransport`) may be used while the
  formal evaluation gate is closed.  Any transport that is NOT a subclass of
  :class:`MockTransport` requires the formal evaluation gate to be open; the
  adapter enforces this before calling ``send()``.
- :class:`FakeTransport` stores a sanitized copy of each request (with
  ``authorization`` cleared) so that ``calls`` / ``last_call()`` never contain
  credential values.  Tests must not assert on ``authorization`` values in
  stored calls.
- :class:`TransportError` carries only a stable ``condition``, an HTTP status,
  and a short redacted message; never the full response body, headers, or
  Authorization value.
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
    """A provider-specific, ready-to-send request.

    In the mock/test path, ``authorization`` is always ``None`` because
    :func:`build_deepseek_request` never reads credentials.  Credential
    injection is reserved for a future real-transport layer that must only be
    instantiated after the formal evaluation gate is open.
    """

    provider: str
    model: str
    base_url: str
    endpoint: str
    # The request body is the JSON-serializable payload (without secrets).
    body: dict[str, Any]
    # authorization is always None in the mock path.  A future real transport
    # may populate it when the gate is open, but only within the transport
    # itself -- never in the shared adapter code.
    authorization: str | None = None
    # Provider-specific headers that are not secret (e.g. Content-Type).
    headers: dict[str, str] = field(default_factory=dict)

    def body_json(self) -> str:
        import json

        return json.dumps(self.body, ensure_ascii=False, sort_keys=True)

    def sanitized(self) -> "PreparedRequest":
        """Return a copy with authorization cleared for safe storage in logs."""
        return PreparedRequest(
            provider=self.provider,
            model=self.model,
            base_url=self.base_url,
            endpoint=self.endpoint,
            body=self.body,
            authorization=None,
            headers=dict(self.headers),
        )


# ---------------------------------------------------------------------------
# Transport protocol
# ---------------------------------------------------------------------------


class Transport(Protocol):
    """A callable transport: send a prepared request, get a response or error."""

    def send(self, request: PreparedRequest) -> TransportResponse:
        """Send the request.  Raise :class:`TransportError` on failure."""
        ...


# ---------------------------------------------------------------------------
# MockTransport base class
# ---------------------------------------------------------------------------


class MockTransport:
    """Base class for transports that are safe to use while the formal
    evaluation gate is closed.

    Any transport that is a subclass of :class:`MockTransport` is allowed to
    run regardless of the gate state.  Any other transport -- including custom
    HTTP implementations -- requires the gate to be open.  The adapter enforces
    this check before calling ``send()``.

    Subclass this to create in-test transports.  Do NOT subclass this for real
    HTTP implementations.
    """


# ---------------------------------------------------------------------------
# Fake transport for tests
# ---------------------------------------------------------------------------


class FakeTransport(MockTransport):
    """An injectable transport that returns scripted responses or errors.

    Stores a *sanitized* copy of each request (``authorization`` cleared) so
    that ``calls`` / ``last_call()`` never contain credential values.  Never
    performs any network I/O.

    The ``calls`` list contains :class:`PreparedRequest` objects with
    ``authorization=None`` regardless of what was passed into ``send()``.
    """

    def __init__(self) -> None:
        # Stores sanitized (no authorization) copies of each request.
        self.calls: list[PreparedRequest] = []
        self._scripted: list[Any] = []
        self._index = 0

    def queue_response(self, response: TransportResponse) -> None:
        self._scripted.append(response)

    def queue_error(self, error: TransportError) -> None:
        self._scripted.append(error)

    def queue_sequence(self, items: list[Any]) -> None:
        for item in items:
            self._scripted.append(item)

    def send(self, request: PreparedRequest) -> TransportResponse:
        # Store a sanitized copy -- authorization is always cleared.
        self.calls.append(request.sanitized())
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
