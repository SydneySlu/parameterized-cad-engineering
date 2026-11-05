"""Real HTTP transports for APP-001 Phase 1 formal runs.

These transports make actual network calls.  They may ONLY be instantiated
after the formal run authorization is validated.  In tests, :class:`FakeTransport`
is used instead -- these classes are never imported or instantiated in test code.

Security rules:
- ``DeepSeekTransport`` reads ``DEEPSEEK_API_KEY`` from ``os.environ`` only
  inside ``send()``, only after confirming a valid ``FormalRunAuthorization``
  is bound to the transport.  The key value is injected into the Authorization
  header and is NOT stored on the object, NOT logged, NOT included in any
  exception message, and NOT written to any output file.
- ``OllamaTransport`` requires no credentials.  It connects only to the
  local Ollama host.  It does NOT read or require any API key.  DeepSeek-specific
  parameters (``thinking``, ``response_format``, ``max_tokens``) are not sent.

Both transports record runtime version/identity metadata without storing secrets.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .authorization import FormalRunAuthorization
from .contract import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_PROVIDER,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
)
from .transport import (
    COND_AUTH_PERMISSION,
    COND_HTTP_429,
    COND_HTTP_5XX,
    COND_INTERRUPTION,
    COND_INVALID_JSON,
    COND_MALFORMED_REQUEST,
    COND_OTHER_NON_RETRYABLE,
    COND_TIMEOUT,
    PreparedRequest,
    TransportError,
    TransportResponse,
)


class RealTransportError(RuntimeError):
    """Raised when real transport construction is attempted without valid
    authorization."""


def _require_authorization(auth: FormalRunAuthorization | None, label: str) -> None:
    """Raise if authorization is None (fail-closed)."""
    if auth is None:
        raise RealTransportError(
            f"cannot construct {label} without a FormalRunAuthorization; "
            "formal runs require explicit authorization"
        )


# ---------------------------------------------------------------------------
# DeepSeek real transport
# ---------------------------------------------------------------------------

class DeepSeekTransport:
    """Real HTTP transport for DeepSeek Chat Completions API.

    Construction requires a valid :class:`FormalRunAuthorization`.
    The API key is read from ``os.environ["DEEPSEEK_API_KEY"]`` only inside
    ``send()`` and is never stored, logged, or written to files.

    This transport may NOT be used while ``FORMAL_EVALUATION_ALLOWED = False``
    in :mod:`src.llm.contract`.  The adapter's gate check prevents this:
    when a non-FakeTransport is passed to ``Adapter``, the adapter verifies
    the ``FormalRunAuthorization``.
    """

    def __init__(
        self,
        authorization: FormalRunAuthorization | None,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        _require_authorization(authorization, "DeepSeekTransport")
        if DEEPSEEK_PROVIDER not in authorization.providers:
            raise RealTransportError(
                "authorization does not permit DeepSeek provider"
            )
        self._auth = authorization
        self._timeout = timeout_seconds
        self._runtime_version: str | None = None

    def send(self, request: PreparedRequest) -> TransportResponse:
        """Send the request to the DeepSeek API.

        Reads ``DEEPSEEK_API_KEY`` from ``os.environ`` at call time.
        The key is used only to set the Authorization header and is
        immediately discarded from the local scope.  It is not stored,
        logged, or included in any exception.
        """
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise TransportError(
                condition=COND_AUTH_PERMISSION,
                http_status=None,
                message="DEEPSEEK_API_KEY env var is empty or not set",
            )
        url = f"{request.base_url}{request.endpoint}"
        body_bytes = request.body_json().encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        # Immediately discard the key from local scope
        api_key = None  # noqa: F841
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return self._handle_http_error(exc)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._handle_connection_error(exc)
        return self._parse_response(status, raw)

    def _handle_http_error(self, exc: urllib.error.HTTPError) -> TransportResponse:
        status = exc.code
        # Don't read or log the body -- it may contain sensitive details
        if status == 401 or status == 403:
            raise TransportError(
                condition=COND_AUTH_PERMISSION,
                http_status=status,
                message=f"HTTP {status} authentication/permission error",
            )
        if status == 429:
            raise TransportError(
                condition=COND_HTTP_429,
                http_status=status,
                message="HTTP 429 rate limit",
            )
        if 400 <= status < 500:
            raise TransportError(
                condition=COND_MALFORMED_REQUEST,
                http_status=status,
                message=f"HTTP {status} client error",
            )
        if 500 <= status < 600:
            raise TransportError(
                condition=COND_HTTP_5XX,
                http_status=status,
                message=f"HTTP {status} server error",
            )
        raise TransportError(
            condition=COND_OTHER_NON_RETRYABLE,
            http_status=status,
            message=f"HTTP {status} unexpected error",
        )

    def _handle_connection_error(self, exc: Exception) -> TransportResponse:
        msg = type(exc).__name__
        if "timeout" in str(exc).lower() or isinstance(exc, TimeoutError):
            raise TransportError(
                condition=COND_TIMEOUT,
                http_status=None,
                message=f"connection/read timeout: {msg}",
            )
        raise TransportError(
            condition=COND_INTERRUPTION,
            http_status=None,
            message=f"connection interrupted: {msg}",
        )

    def _parse_response(self, status: int, raw: str) -> TransportResponse:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TransportError(
                condition=COND_INVALID_JSON,
                http_status=status,
                message=f"response JSON parse error: {type(exc).__name__}",
            )
        if not isinstance(data, dict):
            raise TransportError(
                condition=COND_INVALID_JSON,
                http_status=status,
                message="response is not a JSON object",
            )
        # Extract content from the first choice
        choices = data.get("choices", [])
        if not choices or not isinstance(choices, list):
            raise TransportError(
                condition=COND_INVALID_JSON,
                http_status=status,
                message="response has no 'choices' array",
            )
        choice = choices[0]
        message = choice.get("message", {})
        body = message.get("content", "") if isinstance(message, dict) else ""
        # Runtime identity (safe fields only -- no key, no Authorization)
        runtime_model = data.get("model")
        runtime_provider = data.get("provider")  # may be None per baseline-contract
        # Usage (cloud token fields)
        usage_raw = data.get("usage", {}) or {}
        usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens"),
            "completion_tokens": usage_raw.get("completion_tokens"),
            "total_tokens": usage_raw.get("total_tokens"),
            "prompt_cache_hit_tokens": usage_raw.get(
                "prompt_cache_hit_tokens",
                usage_raw.get("prompt_tokens_details", {}).get("cached_tokens"),
            ),
            "prompt_cache_miss_tokens": usage_raw.get("prompt_cache_miss_tokens"),
        }
        return TransportResponse(
            status=status,
            body=body if isinstance(body, str) else "",
            runtime_returned_model=str(runtime_model) if runtime_model else None,
            runtime_returned_provider=(
                str(runtime_provider) if runtime_provider else "not_exposed"
            ),
            usage=usage,
        )


# ---------------------------------------------------------------------------
# Ollama real transport
# ---------------------------------------------------------------------------

class OllamaTransport:
    """Real HTTP transport for the local Ollama ``/api/chat`` endpoint.

    Construction requires a valid :class:`FormalRunAuthorization`.
    No API key is required or read.  DeepSeek-specific parameters
    (``thinking``, ``response_format``, ``max_tokens``) are NEVER sent.

    The transport verifies that the local Ollama model ID starts with the
    frozen digest prefix.  If the model is not running or the digest does
    not match, a :class:`TransportError` with a non-retryable condition is
    raised without pulling models automatically.
    """

    def __init__(
        self,
        authorization: FormalRunAuthorization | None,
        *,
        host: str = OLLAMA_DEFAULT_HOST,
        timeout_seconds: float = 180.0,
    ) -> None:
        _require_authorization(authorization, "OllamaTransport")
        if OLLAMA_PROVIDER not in authorization.providers:
            raise RealTransportError(
                "authorization does not permit Ollama provider"
            )
        self._auth = authorization
        self._host = host.rstrip("/")
        self._timeout = timeout_seconds
        self._ollama_version: str | None = None
        self._verified_digest: bool = False

    def send(self, request: PreparedRequest) -> TransportResponse:
        """Send the request to the local Ollama /api/chat endpoint."""
        if not self._verified_digest:
            self._verify_model_digest()
        url = f"{self._host}{request.endpoint}"
        body_bytes = request.body_json().encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        t_start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            status = exc.code
            if 500 <= status < 600:
                raise TransportError(
                    condition=COND_HTTP_5XX,
                    http_status=status,
                    message=f"Ollama HTTP {status} server error",
                )
            raise TransportError(
                condition=COND_MALFORMED_REQUEST,
                http_status=status,
                message=f"Ollama HTTP {status} client error",
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            msg = type(exc).__name__
            if "timeout" in str(exc).lower() or isinstance(exc, TimeoutError):
                raise TransportError(
                    condition=COND_TIMEOUT,
                    http_status=None,
                    message=f"Ollama connection/read timeout: {msg}",
                )
            raise TransportError(
                condition=COND_INTERRUPTION,
                http_status=None,
                message=f"Ollama connection interrupted: {msg}",
            )
        t_elapsed = time.monotonic() - t_start
        return self._parse_response(status, raw, t_elapsed)

    def _verify_model_digest(self) -> None:
        """Check that the expected model is running locally.

        Does NOT pull the model or change anything.  Raises a non-retryable
        :class:`TransportError` if the model is absent or digest mismatches.
        """
        url = f"{self._host}/api/show"
        body_bytes = json.dumps({"name": OLLAMA_MODEL}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
        except Exception:
            raise TransportError(
                condition=COND_OTHER_NON_RETRYABLE,
                http_status=None,
                message=(
                    "Ollama is not running or /api/show failed; "
                    "ensure Ollama is running with qwen3:8b loaded"
                ),
            )
        # Check digest prefix matches the frozen value
        details = data.get("details", {}) if isinstance(data, dict) else {}
        model_id = data.get("modelfile", "") or ""
        digest_field = data.get("digest", "") or details.get("digest", "") or ""
        if not (
            str(digest_field).startswith(OLLAMA_DIGEST)
            or OLLAMA_DIGEST in str(digest_field)
        ):
            raise TransportError(
                condition=COND_OTHER_NON_RETRYABLE,
                http_status=None,
                message=(
                    f"Ollama model digest mismatch: expected prefix {OLLAMA_DIGEST!r}, "
                    f"got {str(digest_field)[:20]!r}; "
                    "do not auto-pull; verify the model manually"
                ),
            )
        self._verified_digest = True
        # Record Ollama runtime version (non-sensitive)
        self._ollama_version = data.get("version", "unknown")

    def _parse_response(
        self, status: int, raw: str, wall_time_s: float
    ) -> TransportResponse:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TransportError(
                condition=COND_INVALID_JSON,
                http_status=status,
                message=f"Ollama response JSON parse error: {type(exc).__name__}",
            )
        if not isinstance(data, dict):
            raise TransportError(
                condition=COND_INVALID_JSON,
                http_status=status,
                message="Ollama response is not a JSON object",
            )
        message = data.get("message", {})
        body = message.get("content", "") if isinstance(message, dict) else ""
        # Runtime metadata (no secrets)
        runtime_model = data.get("model", OLLAMA_MODEL)
        usage: dict[str, Any] = {
            "local_wall_time_seconds": wall_time_s,
            "ollama_runtime": self._ollama_version,
            "cloud_tokens": "not_applicable",
            "cloud_cost": "not_applicable",
        }
        return TransportResponse(
            status=status,
            body=body if isinstance(body, str) else "",
            runtime_returned_model=str(runtime_model) if runtime_model else None,
            runtime_returned_provider="not_exposed",
            usage=usage,
        )
