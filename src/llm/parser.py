"""Strict parser for the frozen ``app001-io.v1`` model response envelope.

This module is pure: it takes a raw response body (str or bytes) and returns a
``ParseResult``.  It never repairs, cleans, or auto-fills invalid output, and
it never imports the schema or CAD runtime.  Protocol failures are reported as
structured errors with stable codes so the adapter can classify them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from .contract import (
    CONTRACT_VERSION,
    DECISION_VALUES,
    ENVELOPE_KEYS,
    EVIDENCE_KEYS,
    EVIDENCE_SOURCE_VALUES,
    EXTRACTABLE_FIELDS,
    INTEGER_FIELDS,
    LENGTH_FIELDS,
    PROMPT_VERSION,
)


# ---------------------------------------------------------------------------
# Error model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParseError:
    """A stable, serializable parser/contract error."""

    code: str
    stage: str
    fields: tuple[str, ...]
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "stage": self.stage,
            "fields": list(self.fields),
            "message": self.message,
        }


# Stage names recorded in parse results.
STAGE_PARSE = "parse"
STAGE_CONTRACT = "contract"


# ---------------------------------------------------------------------------
# Parse result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedEnvelope:
    """The strictly-validated model envelope, or ``None`` on protocol failure."""

    contract_version: str
    prompt_version: str
    decision: str
    extracted_parameters: dict[str, Any]
    unsupported_requests: list[Any]
    evidence: list[Any]
    missing_fields: list[Any]
    questions: list[Any]
    confidence: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "prompt_version": self.prompt_version,
            "decision": self.decision,
            "extracted_parameters": dict(self.extracted_parameters),
            "unsupported_requests": list(self.unsupported_requests),
            "evidence": list(self.evidence),
            "missing_fields": list(self.missing_fields),
            "questions": list(self.questions),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing one raw model response.

    ``ok`` is True only when the body parsed to exactly one JSON object that
    satisfies the frozen envelope.  ``envelope`` is ``None`` on any failure.
    """

    ok: bool
    stage: str
    envelope: ParsedEnvelope | None
    errors: tuple[ParseError, ...]
    # The raw body is intentionally NOT stored here; the adapter decides
    # retention via the run-record policy.  We keep only a short, redacted
    # diagnostic length for logging.

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "stage": self.stage,
            "envelope": self.envelope.as_dict() if self.envelope is not None else None,
            "errors": [error.as_dict() for error in self.errors],
        }


def _err(code: str, stage: str, fields: tuple[str, ...], message: str) -> ParseError:
    return ParseError(code=code, stage=stage, fields=fields, message=message)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_response(raw: str | bytes) -> ParseResult:
    """Parse and strictly validate one model response body.

    Steps (each recorded as a distinct stage):

    1. Decode UTF-8 and parse exactly one JSON object.
    2. Verify the exact key set matches ``ENVELOPE_KEYS``.
    3. Verify ``contract_version`` and ``prompt_version`` literals.
    4. Verify ``decision`` is one of ``DECISION_VALUES``.
    5. Verify ``extracted_parameters`` is an object whose keys are a subset of
       ``EXTRACTABLE_FIELDS``; reject unknown keys (protocol failure, not a
       schema/rule failure).
    6. Verify array-typed fields are arrays and evidence entries are shaped
       correctly.
    7. Verify ``confidence`` is ``null`` (the contract requires it); a non-null
       value is a contract failure, recorded as a diagnostic only.
    """
    errors: list[ParseError] = []

    # --- Step 1: decode + JSON parse ---
    body = _decode_and_parse_json(raw, errors)
    if body is None:
        return ParseResult(ok=False, stage=STAGE_PARSE, envelope=None, errors=tuple(errors))

    if not isinstance(body, Mapping):
        errors.append(_err("PROTOCOL_NOT_OBJECT", STAGE_PARSE, (), "response is not a JSON object"))
        return ParseResult(ok=False, stage=STAGE_PARSE, envelope=None, errors=tuple(errors))

    # --- Step 2: exact key set ---
    actual_keys = set(body.keys())
    missing = sorted(ENVELOPE_KEYS - actual_keys)
    extra = sorted(actual_keys - ENVELOPE_KEYS)
    if missing:
        errors.append(_err("MISSING_ENVELOPE_KEY", STAGE_CONTRACT, tuple(missing), f"missing required key(s): {missing}"))
    if extra:
        errors.append(_err("EXTRA_ENVELOPE_KEY", STAGE_CONTRACT, tuple(extra), f"unexpected key(s): {extra}"))
    if errors:
        return ParseResult(ok=False, stage=STAGE_CONTRACT, envelope=None, errors=tuple(errors))

    # --- Step 3: version literals ---
    cv = body.get("contract_version")
    if cv != CONTRACT_VERSION:
        errors.append(_err("CONTRACT_VERSION_MISMATCH", STAGE_CONTRACT, ("contract_version",), f"expected {CONTRACT_VERSION!r}, got {cv!r}"))
    pv = body.get("prompt_version")
    if pv != PROMPT_VERSION:
        errors.append(_err("PROMPT_VERSION_MISMATCH", STAGE_CONTRACT, ("prompt_version",), f"expected {PROMPT_VERSION!r}, got {pv!r}"))

    # --- Step 4: decision enum ---
    decision = body.get("decision")
    if not isinstance(decision, str) or decision not in DECISION_VALUES:
        errors.append(_err("DECISION_INVALID", STAGE_CONTRACT, ("decision",), f"decision must be one of {sorted(DECISION_VALUES)}, got {decision!r}"))

    # --- Step 5: extracted_parameters ---
    extracted = body.get("extracted_parameters")
    if not isinstance(extracted, Mapping):
        errors.append(_err("EXTRACTED_PARAMETERS_NOT_OBJECT", STAGE_CONTRACT, ("extracted_parameters",), "extracted_parameters must be a JSON object"))
        extracted = {}
    else:
        unknown_params = sorted(set(extracted) - set(EXTRACTABLE_FIELDS))
        if unknown_params:
            errors.append(_err("EXTRACTED_PARAMETERS_UNKNOWN_FIELD", STAGE_CONTRACT, tuple(unknown_params), f"extracted_parameters has unknown field(s): {unknown_params}"))
        # Type-check length fields: must be number or measurement object; bool is rejected.
        for field_name, value in extracted.items():
            if field_name in LENGTH_FIELDS:
                if not _is_number_or_measurement(value):
                    errors.append(_err("EXTRACTED_TYPE_ERROR", STAGE_CONTRACT, (field_name,), f"{field_name} must be a finite number or {{value, unit}} object"))
            elif field_name in INTEGER_FIELDS:
                if isinstance(value, bool) or not isinstance(value, int):
                    errors.append(_err("EXTRACTED_TYPE_ERROR", STAGE_CONTRACT, (field_name,), f"{field_name} must be an integer"))

    # --- Step 6: array fields + evidence shape ---
    for array_field in ("unsupported_requests", "evidence", "missing_fields", "questions"):
        value = body.get(array_field)
        if not isinstance(value, list):
            errors.append(_err("FIELD_NOT_ARRAY", STAGE_CONTRACT, (array_field,), f"{array_field} must be an array"))
    evidence = body.get("evidence")
    if isinstance(evidence, list):
        for index, entry in enumerate(evidence):
            if not isinstance(entry, Mapping):
                errors.append(_err("EVIDENCE_ENTRY_NOT_OBJECT", STAGE_CONTRACT, (f"evidence[{index}]",), f"evidence[{index}] must be an object"))
                continue
            ev_keys = set(entry.keys())
            ev_missing = sorted(EVIDENCE_KEYS - ev_keys)
            ev_extra = sorted(ev_keys - EVIDENCE_KEYS)
            if ev_missing:
                errors.append(_err("EVIDENCE_ENTRY_MISSING_KEY", STAGE_CONTRACT, (f"evidence[{index}]",), f"evidence[{index}] missing key(s): {ev_missing}"))
            if ev_extra:
                errors.append(_err("EVIDENCE_ENTRY_EXTRA_KEY", STAGE_CONTRACT, (f"evidence[{index}]",), f"evidence[{index}] unexpected key(s): {ev_extra}"))
            # 3.5: field, quote, source must be strings.
            for str_field in ("field", "quote", "source"):
                val = entry.get(str_field)
                if val is not None and not isinstance(val, str):
                    errors.append(_err("EVIDENCE_FIELD_TYPE_ERROR", STAGE_CONTRACT, (f"evidence[{index}].{str_field}",), f"evidence[{index}].{str_field} must be a string, got {type(val).__name__}"))
            source = entry.get("source")
            if isinstance(source, str) and source not in EVIDENCE_SOURCE_VALUES:
                errors.append(_err("EVIDENCE_SOURCE_INVALID", STAGE_CONTRACT, (f"evidence[{index}].source",), f"evidence source must be one of {sorted(EVIDENCE_SOURCE_VALUES)}, got {source!r}"))

    # 3.5: Array element type checks for unsupported_requests, missing_fields, questions.
    for str_array_field in ("unsupported_requests", "missing_fields", "questions"):
        arr = body.get(str_array_field)
        if not isinstance(arr, list):
            continue  # already reported as FIELD_NOT_ARRAY above
        for idx, elem in enumerate(arr):
            if not isinstance(elem, str):
                errors.append(_err("ARRAY_ELEMENT_TYPE_ERROR", STAGE_CONTRACT, (f"{str_array_field}[{idx}]",), f"{str_array_field}[{idx}] must be a string, got {type(elem).__name__}"))

    # --- Step 7: confidence must be null (diagnostic only) ---
    confidence = body.get("confidence")
    if confidence is not None:
        # Contract requires null; a non-null value is a contract failure.  It is
        # recorded but never used for routing/gating/scoring.
        errors.append(_err("CONFIDENCE_NOT_NULL", STAGE_CONTRACT, ("confidence",), "confidence must be null; non-null values are diagnostic only and never used for routing"))

    if errors:
        return ParseResult(ok=False, stage=STAGE_CONTRACT, envelope=None, errors=tuple(errors))

    envelope = ParsedEnvelope(
        contract_version=cv,
        prompt_version=pv,
        decision=decision,
        extracted_parameters=dict(extracted),
        unsupported_requests=list(body.get("unsupported_requests", [])),
        evidence=list(body.get("evidence", [])),
        missing_fields=list(body.get("missing_fields", [])),
        questions=list(body.get("questions", [])),
        confidence=confidence,
    )
    return ParseResult(ok=True, stage=STAGE_CONTRACT, envelope=envelope, errors=())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decode_and_parse_json(raw: str | bytes, errors: list[ParseError]) -> Any | None:
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(_err("RESPONSE_NOT_UTF8", STAGE_PARSE, (), f"response is not valid UTF-8: {str(exc)[:120]}"))
            return None
    elif isinstance(raw, str):
        text = raw
    else:
        errors.append(_err("RESPONSE_TYPE_ERROR", STAGE_PARSE, (), "response must be str or bytes"))
        return None

    text_stripped = text.strip()
    if not text_stripped:
        errors.append(_err("RESPONSE_EMPTY", STAGE_PARSE, (), "response body is empty"))
        return None

    # Reject leading/trailing prose or code fences: the entire body must be one
    # JSON object.  We do not strip Markdown fences or extract a JSON block.
    if text_stripped.startswith("```") or text_stripped.endswith("```"):
        errors.append(_err("RESPONSE_HAS_CODE_FENCE", STAGE_PARSE, (), "response must be a single JSON object, not a code-fenced block"))
        return None

    # 3.5: Reject non-finite literals (NaN, Infinity, -Infinity) which Python's
    # json.loads accepts when they appear as bare identifiers, but which are not
    # valid JSON per RFC 8259 / ECMA-404.  Python's default json module does NOT
    # parse bare NaN/Infinity, but model outputs may contain them as strings or
    # as float values in JSON (e.g. via non-compliant serializers).  We
    # additionally reject them after parsing.
    try:
        # Use parse_constant=None (disables NaN/Infinity if present in source)
        # Python's json.loads already rejects bare NaN/Infinity by default,
        # but we add a post-parse walk to catch them as float values.
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(_err("INVALID_JSON", STAGE_PARSE, (), f"invalid JSON: {str(exc)[:200]}"))
        return None

    # Walk the parsed value to detect non-finite floats (NaN / ±Infinity).
    # json.loads in Python won't produce these from well-formed JSON, but
    # some JSON variants (JavaScript, non-standard serializers) may; adding
    # the check makes the parser robust to those inputs.
    _nan_inf_errors: list[str] = []
    _walk_check_finite(parsed, "", _nan_inf_errors)
    if _nan_inf_errors:
        errors.append(_err("NON_FINITE_VALUE", STAGE_PARSE, tuple(_nan_inf_errors[:5]), "response contains non-finite numeric values (NaN or Infinity), which are not valid JSON"))
        return None

    return parsed


def _walk_check_finite(obj: Any, path: str, found: list[str]) -> None:
    """Walk a parsed JSON value and record paths of any non-finite floats."""
    import math

    if isinstance(obj, float):
        if not math.isfinite(obj):
            found.append(path or "<root>")
    elif isinstance(obj, Mapping):
        for key, value in obj.items():
            _walk_check_finite(value, f"{path}.{key}" if path else key, found)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_check_finite(item, f"{path}[{i}]", found)


def _is_number_or_measurement(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, Mapping):
        if set(value.keys()) == {"value", "unit"}:
            raw = value.get("value")
            return isinstance(raw, (int, float)) and not isinstance(raw, bool)
    return False
