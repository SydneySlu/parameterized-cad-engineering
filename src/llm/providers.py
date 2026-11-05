"""DeepSeek and Ollama request builders with provider-specific isolation.

Each builder produces a :class:`PreparedRequest` for its provider using the
frozen shared decode settings and the provider-specific controls required by
ADR-0011/0012.  The two builders are deliberately separate so a DeepSeek-only
parameter (``thinking``) is never sent to Ollama and vice-versa.

No real network call is made here.  The authorization token, when provided, is
held only on the :class:`PreparedRequest` and is never serialized into a run
record.
"""

from __future__ import annotations

import os
from typing import Any

from .contract import (
    DEEPSEEK_API_STYLE,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_THINKING_SETTING,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    SHARED_DECODE,
)
from .transport import PreparedRequest


# ---------------------------------------------------------------------------
# Shared input message builder (provider-agnostic)
# ---------------------------------------------------------------------------


def build_model_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    """Build the OpenAI-style messages array used by both providers."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# DeepSeek request builder
# ---------------------------------------------------------------------------


def build_deepseek_request(
    *,
    system_prompt: str,
    user_prompt: str,
    api_key: str | None = None,
    base_url: str = DEEPSEEK_BASE_URL,
) -> PreparedRequest:
    """Build a DeepSeek Chat Completions request.

    Sends the frozen shared decode settings plus the explicit
    ``thinking: {"type":"disabled"}`` control required by ADR-0012.  JSON mode
    is requested via ``response_format``.

    The API key is read only from the argument or the environment; it is never
    printed or logged.  When ``api_key`` is ``None`` and the environment
    variable is unset, the authorization is left ``None`` -- a real transport
    would then fail with an auth error, which is the correct fail-closed
    behavior for any accidentally-enabled real run.
    """
    body: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": build_model_messages(system_prompt, user_prompt),
        "temperature": SHARED_DECODE["temperature"],
        "top_p": SHARED_DECODE["top_p"],
        "max_tokens": SHARED_DECODE["max_output_tokens"],
        "seed": SHARED_DECODE["seed"],
        "response_format": {"type": "json_object"},
        "thinking": dict(DEEPSEEK_THINKING_SETTING),
        "stream": False,
    }

    auth = _resolve_deepseek_auth(api_key)
    return PreparedRequest(
        provider=DEEPSEEK_PROVIDER,
        model=DEEPSEEK_MODEL,
        base_url=base_url,
        endpoint="/chat/completions",
        body=body,
        authorization=auth,
        headers={"Content-Type": "application/json"},
    )


def _resolve_deepseek_auth(explicit_key: str | None) -> str | None:
    """Resolve the DeepSeek API key without ever printing it."""
    if explicit_key is not None:
        return f"Bearer {explicit_key}"
    env_value = os.environ.get("DEEPSEEK_API_KEY")
    if env_value:
        return f"Bearer {env_value}"
    return None


def deepseek_configured_identity() -> dict[str, Any]:
    """Return the configured (not runtime) identity for DeepSeek."""
    return {
        "configured_provider": DEEPSEEK_PROVIDER,
        "configured_model_name": DEEPSEEK_MODEL,
        "base_url": DEEPSEEK_BASE_URL,
        "api_style": DEEPSEEK_API_STYLE,
        "thinking_setting": dict(DEEPSEEK_THINKING_SETTING),
    }


# ---------------------------------------------------------------------------
# Ollama request builder
# ---------------------------------------------------------------------------


def build_ollama_request(
    *,
    system_prompt: str,
    user_prompt: str,
    base_url: str = OLLAMA_DEFAULT_HOST,
    endpoint: str = "/api/chat",
) -> PreparedRequest:
    """Build an Ollama request.

    Uses the Ollama-native controls: ``think=False``, ``format=json``,
    ``num_predict`` (Ollama's max-output token field), and the shared seed.
    No DeepSeek-specific ``thinking`` parameter is sent.
    """
    body: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": build_model_messages(system_prompt, user_prompt),
        "think": False,
        "format": "json",
        "options": {
            "temperature": SHARED_DECODE["temperature"],
            "top_p": SHARED_DECODE["top_p"],
            "num_predict": SHARED_DECODE["max_output_tokens"],
            "seed": SHARED_DECODE["seed"],
        },
        "stream": False,
    }
    return PreparedRequest(
        provider=OLLAMA_PROVIDER,
        model=OLLAMA_MODEL,
        base_url=base_url,
        endpoint=endpoint,
        body=body,
        authorization=None,
        headers={"Content-Type": "application/json"},
    )


def ollama_configured_identity() -> dict[str, Any]:
    """Return the configured (not runtime) identity for Ollama."""
    return {
        "configured_provider": OLLAMA_PROVIDER,
        "configured_model_name": OLLAMA_MODEL,
        "local_digest": OLLAMA_DIGEST,
        "base_url": OLLAMA_DEFAULT_HOST,
        "think_setting": False,
    }


# ---------------------------------------------------------------------------
# Decoding parameters snapshot (for run records)
# ---------------------------------------------------------------------------


def decoding_parameters_snapshot(provider: str) -> dict[str, Any]:
    """Return the actual decoding parameters sent for a provider."""
    base = {
        "temperature": SHARED_DECODE["temperature"],
        "top_p": SHARED_DECODE["top_p"],
        "max_output_tokens": SHARED_DECODE["max_output_tokens"],
        "seed": SHARED_DECODE["seed"],
        "stream": False,
    }
    if provider == DEEPSEEK_PROVIDER:
        base["response_format"] = {"type": "json_object"}
        base["thinking"] = dict(DEEPSEEK_THINKING_SETTING)
        base["max_tokens_field"] = "max_tokens"
    elif provider == OLLAMA_PROVIDER:
        base["think"] = False
        base["format"] = "json"
        base["num_predict_field"] = "num_predict"
    return base
