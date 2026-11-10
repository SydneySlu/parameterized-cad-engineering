"""Frozen contract constants and envelope shapes for APP-001.

All values here are pinned by ADR-0013, ADR-0009/0010/0011/0012 and the
``APP-001-baseline-contract.md``.  Do not change them without a new ADR.
This module is intentionally dependency-free so it can be imported by both the
runtime adapter and by tests without touching the network or the CAD runtime.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Protocol versions (APP-001 v5 production prompt activated under ADR-0018)
# ---------------------------------------------------------------------------

CONTRACT_VERSION: Final[str] = "app001-io.v1"
PROMPT_VERSION: Final[str] = "app001-extraction.v5"
ACCEPTANCE_SET_VERSION: Final[str] = "acceptance-set-v0"
# SHA-256 of the frozen acceptance-set-v0.json file, verified 2026-11-06.
# Any content change — including NLI, query IDs, or evaluator-only fields —
# must be rejected before any run proceeds.
ACCEPTANCE_SET_SHA256: Final[str] = "ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf"
FORMAL_EVALUATION_ALLOWED: Final[bool] = False

# ---------------------------------------------------------------------------
# Family / schema
# ---------------------------------------------------------------------------

FAMILY_ID: Final[str] = "set_screw_shaft_collar"
SCHEMA_VERSION: Final[str] = "set_screw_shaft_collar.v0"

# The six CAD-003 parameter fields the model may populate.  ``second_screw``
# is an integer (0/1); the rest are lengths in mm.
EXTRACTABLE_FIELDS: Final[tuple[str, ...]] = (
    "bore_d",
    "outer_d",
    "width",
    "screw_d",
    "screw_len",
    "second_screw",
)

LENGTH_FIELDS: Final[frozenset[str]] = frozenset(
    {"bore_d", "outer_d", "width", "screw_d", "screw_len"}
)
INTEGER_FIELDS: Final[frozenset[str]] = frozenset({"second_screw"})

# ---------------------------------------------------------------------------
# Model output envelope (app001-io.v1)
# ---------------------------------------------------------------------------

ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "contract_version",
        "prompt_version",
        "decision",
        "extracted_parameters",
        "unsupported_requests",
        "evidence",
        "missing_fields",
        "questions",
        "confidence",
    }
)

DECISION_VALUES: Final[frozenset[str]] = frozenset({"answer", "ask", "refuse"})

# Evidence entry: each item must be an object with exactly these keys.
EVIDENCE_KEYS: Final[frozenset[str]] = frozenset({"field", "quote", "source"})

EVIDENCE_SOURCE_VALUES: Final[frozenset[str]] = frozenset(
    {"user_input", "retrieval_reference"}
)

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

# DeepSeek (cloud)
DEEPSEEK_PROVIDER: Final[str] = "DeepSeek"
DEEPSEEK_MODEL: Final[str] = "deepseek-flash"
DEEPSEEK_BASE_URL: Final[str] = "https://api.deepseek.com"
DEEPSEEK_THINKING_SETTING: Final[dict] = {"type": "disabled"}
DEEPSEEK_API_STYLE: Final[str] = "openai_compatible_chat_completions"

# Ollama (local)
OLLAMA_PROVIDER: Final[str] = "Ollama"
OLLAMA_MODEL: Final[str] = "qwen3:8b"
OLLAMA_DIGEST: Final[str] = "500a1f067a9f"
OLLAMA_DEFAULT_HOST: Final[str] = "http://127.0.0.1:11434"

# ---------------------------------------------------------------------------
# Shared decode settings
# ---------------------------------------------------------------------------

SHARED_DECODE: Final[dict] = {
    "temperature": 0,
    "top_p": 1,
    "max_output_tokens": 512,
    "seed": 271828,
}

# Retry policy
MAX_RETRIES_AFTER_INITIAL: Final[int] = 2
MAX_ATTEMPTS_TOTAL: Final[int] = 3
BACKOFF_SECONDS: Final[tuple[int, ...]] = (1, 2)
RETRYABLE_CONDITIONS: Final[tuple[str, ...]] = (
    "connection_or_read_timeout",
    "connection_interruption",
    "http_429",
    "http_5xx",
)
NON_RETRYABLE_CONDITIONS: Final[tuple[str, ...]] = (
    "authentication_or_permission",
    "malformed_request",
    "context_overflow",
    "invalid_json",
    "contract_error",
    "schema_or_rule_rejection",
    "cad_or_geometry_failure",
)

# ---------------------------------------------------------------------------
# Cost rate card snapshot (2026-11-05, CNY per 1M tokens)
# ---------------------------------------------------------------------------

RATE_CARD_OBSERVED_DATE: Final[str] = "2026-11-05"
RATE_CARD_CURRENCY: Final[str] = "CNY"
RATE_CARD_UNIT: Final[str] = "CNY_per_1M_tokens"
RATE_CARD_SOURCE: Final[str] = (
    "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
)

# Peak windows are Beijing time, Mon-Fri excluding China public holidays.
# Off-peak is everything else (weekends + public holidays + off-hours).
RATE_CARD_PEAK: Final[dict[str, float]] = {
    "input_cache_hit": 0.04,
    "input_cache_miss": 2.00,
    "output": 8.00,
}
RATE_CARD_OFF_PEAK: Final[dict[str, float]] = {
    "input_cache_hit": 0.02,
    "input_cache_miss": 1.00,
    "output": 4.00,
}

# ---------------------------------------------------------------------------
# Stage status vocabulary
# ---------------------------------------------------------------------------

STAGE_STATUSES: Final[frozenset[str]] = frozenset(
    {"not_run", "pass", "fail", "blocked", "not_applicable"}
)

# ---------------------------------------------------------------------------
# Software version (this adapter)
# ---------------------------------------------------------------------------

ADAPTER_VERSION: Final[str] = "app001-adapter.v0"
