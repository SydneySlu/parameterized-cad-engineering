"""DeepSeek and Ollama request builders with provider-specific isolation.

Each builder produces a :class:`PreparedRequest` for its provider using the
frozen shared decode settings and the provider-specific controls required by
ADR-0011/0012.  The two builders are deliberately separate so a DeepSeek-only
parameter (``thinking``) is never sent to Ollama and vice-versa.

No real network call is made here.  In the mock/test path, requests are
always credential-free -- ``build_deepseek_request()`` never reads environment
variables or the ``.env`` file.  Credential injection is the responsibility of
a real transport implementation that must only be used after the formal
evaluation gate is open and explicitly authorized.

APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX:
``build_ollama_request()`` now passes a JSON Schema object as the Ollama
``format`` field instead of the plain string ``"json"``.  This instructs the
Ollama runtime to constrain its sampling to JSON output that matches the
``app001-io.v1`` envelope shape, reducing the incidence of numeric values
serialised as strings (e.g. ``"24 mm"`` instead of ``24``).  The schema is
a generation hint only; the strict ``parse_response()`` gate is unchanged and
remains the authoritative contract enforcer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .contract import (
    CONTRACT_VERSION,
    DECISION_VALUES,
    DEEPSEEK_API_STYLE,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_THINKING_SETTING,
    ENVELOPE_KEYS,
    EVIDENCE_KEYS,
    EVIDENCE_SOURCE_VALUES,
    EXTRACTABLE_FIELDS,
    INTEGER_FIELDS,
    LENGTH_FIELDS,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DIGEST,
    OLLAMA_MODEL,
    OLLAMA_PROVIDER,
    PROMPT_VERSION,
    SHARED_DECODE,
)
from .transport import PreparedRequest


# ---------------------------------------------------------------------------
# Ollama structured-output JSON Schema (app001-io.v1 aligned)
#
# APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX:
# Ollama ≥0.4 accepts a JSON Schema object as the ``format`` field, constraining
# the sampler to produce output that conforms to the schema.  This schema mirrors
# the ``app001-io.v1`` envelope contract enforced by ``parse_response()``, with
# the following alignment notes:
#
#   - All nine ENVELOPE_KEYS are listed under ``properties``; all are required at
#     the top level because the parser enforces exact key presence (MISSING_ENVELOPE_KEY
#     and EXTRA_ENVELOPE_KEY).
#   - ``additionalProperties: false`` prevents the model from emitting extra keys
#     that the parser would reject.
#   - ``contract_version`` and ``prompt_version`` are ``const`` strings so the
#     model does not guess version values.
#   - ``decision`` is an ``enum`` of the three frozen DECISION_VALUES.
#   - Length fields (bore_d, outer_d, width, screw_d, screw_len) accept either a
#     JSON ``number`` or a ``{value: number, unit: string}`` measurement object;
#     the ``oneOf`` deliberately excludes ``string`` to prevent "24 mm" mistakes.
#   - ``second_screw`` is constrained to JSON ``integer`` only.
#   - ``extracted_parameters`` uses ``additionalProperties: false`` over the six
#     EXTRACTABLE_FIELDS; none is ``required`` because the model may omit any.
#   - Evidence entries use ``additionalProperties: false`` with ``field``,
#     ``quote``, and ``source`` all required and typed as ``string``.
#   - ``confidence`` is ``null`` only (the contract forbids non-null values).
#
# SCHEMA DOES NOT ENCODE:
#   - Numeric ranges, catalog values, or CAD-003 validation rules (those remain
#     in the deterministic Schema/adapter layer).
#   - Evaluator-only labels, expected outputs, or derived-value annotations.
#
# This schema is a generation constraint, not a guarantee: ``parse_response()``
# remains the authoritative gating layer.
# ---------------------------------------------------------------------------

def _build_ollama_format_schema() -> dict[str, Any]:
    """Build the frozen Ollama structured-output JSON Schema for app001-io.v1.

    Returns a new dict each call; callers that need a stable reference should
    use the module-level ``OLLAMA_FORMAT_SCHEMA`` constant (which is a deep copy
    frozen at import time via ``json.loads(json.dumps(...))``).
    """
    # Measurement object: {value: number, unit: string}
    measurement_obj = {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string"},
        },
        "required": ["value", "unit"],
        "additionalProperties": False,
    }
    # Length field: number or measurement object (string excluded)
    length_field = {
        "oneOf": [
            {"type": "number"},
            measurement_obj,
        ]
    }

    # extracted_parameters: all six fields optional, no extras, types enforced
    extracted_parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {f: length_field for f in sorted(LENGTH_FIELDS)},
        "additionalProperties": False,
    }
    # second_screw is integer, not a length field
    extracted_parameters_schema["properties"]["second_screw"] = {"type": "integer"}

    # Evidence entry shape
    evidence_entry = {
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "quote": {"type": "string"},
            "source": {"enum": sorted(EVIDENCE_SOURCE_VALUES)},
        },
        "required": ["field", "quote", "source"],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            "contract_version": {"const": CONTRACT_VERSION},
            "prompt_version": {"const": PROMPT_VERSION},
            "decision": {"enum": sorted(DECISION_VALUES)},
            "extracted_parameters": extracted_parameters_schema,
            "unsupported_requests": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": evidence_entry},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
            "questions": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "null"},
        },
        "required": sorted(ENVELOPE_KEYS),
        "additionalProperties": False,
    }


# Module-level constant: deep-copy via JSON round-trip ensures it is independent
# of any future mutation to the contract constants used to build it, and provides
# a stable snapshot for hash computation and request body construction.
OLLAMA_FORMAT_SCHEMA: dict[str, Any] = json.loads(json.dumps(_build_ollama_format_schema()))

# Stable SHA-256 of the serialised schema (sorted keys) for run-record snapshots.
# Used by decoding_parameters_snapshot() so the snapshot records a compact,
# auditable fingerprint rather than the full schema object.
OLLAMA_FORMAT_SCHEMA_SHA256: str = hashlib.sha256(
    json.dumps(OLLAMA_FORMAT_SCHEMA, sort_keys=True, ensure_ascii=False).encode("utf-8")
).hexdigest()


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
    base_url: str = DEEPSEEK_BASE_URL,
) -> PreparedRequest:
    """Build a credential-free DeepSeek Chat Completions request body.

    This function never reads environment variables, the ``.env`` file, or any
    credential store.  The returned ``PreparedRequest.authorization`` is always
    ``None``.  Credential injection is deliberately deferred to a future real
    transport layer that is only instantiated after the formal evaluation gate
    is open and explicitly authorized.

    Sends the frozen shared decode settings plus the explicit
    ``thinking: {"type":"disabled"}`` control required by ADR-0012.  JSON mode
    is requested via ``response_format``.
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

    return PreparedRequest(
        provider=DEEPSEEK_PROVIDER,
        model=DEEPSEEK_MODEL,
        base_url=base_url,
        endpoint="/chat/completions",
        body=body,
        authorization=None,  # credential-free; real transport injects auth
        headers={"Content-Type": "application/json"},
    )


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
    """Build an Ollama request with structured JSON Schema output constraint.

    Uses the Ollama-native controls: ``think=False``,
    ``format=<JSON Schema object>`` (structured output, not plain ``"json"``),
    ``num_predict`` (Ollama's max-output token field), and the shared seed.
    No DeepSeek-specific ``thinking`` parameter is sent.
    No credentials are required for local Ollama.

    The ``format`` value is :data:`OLLAMA_FORMAT_SCHEMA`, a JSON Schema object
    aligned with the ``app001-io.v1`` envelope contract.  This constrains the
    Ollama sampler to produce numeric types for length fields (preventing
    ``"24 mm"`` strings) and fixes the envelope key set.  The strict
    ``parse_response()`` gate remains the authoritative enforcer.
    """
    body: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": build_model_messages(system_prompt, user_prompt),
        "think": False,
        "format": OLLAMA_FORMAT_SCHEMA,
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
        # Record the schema hash rather than the full object to keep the
        # snapshot compact and auditable.  The full schema is available as
        # providers.OLLAMA_FORMAT_SCHEMA; its SHA-256 is OLLAMA_FORMAT_SCHEMA_SHA256.
        base["format_schema_sha256"] = OLLAMA_FORMAT_SCHEMA_SHA256
        base["format_schema_version"] = "ollama-app001-io-v1.0"
        base["num_predict_field"] = "num_predict"
    return base
