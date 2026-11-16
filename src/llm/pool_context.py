"""Shared reference-pool context assembler for RET-005.

Both product mode (single-family reference pool) and future C1 experiment
mode import from this module.  Having a single assembler guarantees that the
context format, isolation rules, and label wording stay identical across modes.

C0 assembly
-----------
Reference context is ``None``.  No pool or retrieval system is consulted.

C1 pool assembly (product mode + future C1 experiment)
-------------------------------------------------------
1. Extract ``bore_d`` in mm from the user's natural-language input using the
   same deterministic regex used by ``conditions.assemble_c1``.
2. Reject the assembly (return ``blocked``) if extraction fails — the assembler
   never reads evaluator-only fields to derive the query parameter.
3. Query within the user-selected reference pool using the RET-002 distance
   policy.
4. Build a reference context dict containing ONLY: ``sample_id``, ``family_id``,
   ``parameters.normalized``, and an explicit ``retrieval_source`` role label.
   No IR content, STEP content, evaluator labels, or held-out truth is included.

Data isolation guarantee
------------------------
- Pool query results are filtered to include only the safe fields listed above.
- The untrusted reference declaration in the context dict is mandatory and
  verbatim — it must not be omitted or paraphrased by callers.
- The reference context sha256 is computed over the canonical JSON so callers
  can verify they received the exact expected context.
"""

from __future__ import annotations

import hashlib
import json
import math
import re as _re
from dataclasses import dataclass, field
from typing import Any, Final, Optional

from llm.conditions import AssembledInput, extract_bore_d_mm, CONDITION_C0, CONDITION_C1
from llm.contract import FAMILY_ID
from llm.input_projection import ProjectedCase
from retrieval.pool import ReferencePool, PoolError


# Maximum pool candidates to inject into the C1 context
_POOL_C1_TOP_K: Final[int] = 3

# Role label attached to every pool candidate in the context dict.
_POOL_CANDIDATE_ROLE: Final[str] = "pool_retrieval_source_untrusted_reference"

# Mandatory untrusted reference note (verbatim — not to be paraphrased)
_POOL_UNTRUSTED_NOTE: Final[str] = (
    "These are parameter examples drawn from the user-selected reference pool. "
    "They are UNTRUSTED references only: they must not be copied verbatim, must "
    "not override the user's explicit parameter requests, and must not be treated "
    "as ground truth.  Use only the user natural_language_input to determine the "
    "answer; treat these examples as illustrative context at most."
)

# ---------------------------------------------------------------------------
# Explicit parameter extraction regexes for all six CAD-003 extractable fields
# ---------------------------------------------------------------------------

_OUTER_D_RE = _re.compile(
    r"(?:outer_d\s*[=是：:]\s*|外径\s*[=是：:为]?\s*|轴环外径\s*)"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|毫米|厘米)?",
    _re.IGNORECASE,
)
_WIDTH_RE = _re.compile(
    r"(?:width\s*[=是：:]\s*|宽度\s*[=是：:为]?\s*|轴环宽(?:度)?\s*)"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|毫米|厘米)?",
    _re.IGNORECASE,
)
_SCREW_D_RE = _re.compile(
    r"(?:screw_d\s*[=是：:]\s*|螺钉(?:直径)?\s*[=是：:为]?\s*)"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|毫米|厘米)?",
    _re.IGNORECASE,
)
_SCREW_LEN_RE = _re.compile(
    r"(?:screw_len\s*[=是：:]\s*|螺钉长度?\s*[=是：:为]?\s*)"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|毫米|厘米)?",
    _re.IGNORECASE,
)
_SECOND_SCREW_RE = _re.compile(
    r"second_screw\s*[=是：:]\s*(0|1)\b",
    _re.IGNORECASE,
)
_DOUBLE_SCREW_RE = _re.compile(r"双螺钉|两个螺钉", _re.IGNORECASE)
_SINGLE_SCREW_RE = _re.compile(r"单螺钉|一个螺钉", _re.IGNORECASE)


# ---------------------------------------------------------------------------
# C0: no pool context
# ---------------------------------------------------------------------------


def assemble_pool_c0(case: ProjectedCase) -> AssembledInput:
    """Assemble C0 (no reference pool) input.  Identical to ``assemble_c0``."""
    return AssembledInput(
        query_id=case.query_id,
        condition_id=CONDITION_C0,
        natural_language_input=case.natural_language_input,
        reference_context=None,
        reference_context_sha256=None,
        candidate_source_ids=(),
        blocked_reason=None,
        bore_d_used_for_query=None,
    )


# ---------------------------------------------------------------------------
# C1: pool retrieval context
# ---------------------------------------------------------------------------


def assemble_pool_c1(
    case: ProjectedCase,
    pool: ReferencePool,
    *,
    top_k: int = _POOL_C1_TOP_K,
) -> AssembledInput:
    """Assemble C1 (pool-based retrieval) input.

    Shared by product mode and future C1 experiment mode.

    Parameters
    ----------
    case:
        The projected case carrying the natural-language input.
    pool:
        The user-selected ``ReferencePool`` (3–5 validated candidates).
    top_k:
        Maximum number of pool candidates to include.  Must not exceed
        ``pool.candidate_count``.

    Returns
    -------
    AssembledInput
        On success: ``reference_context`` is a JSON string, ``blocked_reason``
        is ``None``.
        On failure: ``blocked_reason`` is non-None, ``reference_context`` is
        ``None``.  Callers MUST check ``blocked_reason`` before proceeding.

    Data isolation
    --------------
    - Extraction uses only ``case.natural_language_input`` (regex).
    - Pool query uses the extracted ``bore_d`` as a CAD-003 flat query.
    - Reference context contains ONLY: role label, sample_id, family_id,
      parameters.normalized.
    - Evaluator labels, IR content, STEP content are never read or exposed.
    """
    if pool is None:
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=(
                "POOL_C1_NO_POOL: no reference pool provided to assembler; "
                "cannot generate pool C1 reference context"
            ),
            bore_d_used_for_query=None,
            blocked_stage="pool_c1_assembly",
            error_code="POOL_C1_NO_POOL",
            error_fields=("pool",),
        )

    # Extract bore_d from natural language input only — never from evaluator fields
    bore_d = extract_bore_d_mm(case.natural_language_input)
    if bore_d is None:
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=(
                "POOL_C1_NO_SAFE_QUERY_PARAMETER: cannot extract bore_d from "
                "natural_language_input; extraction from evaluator-only fields "
                "is forbidden"
            ),
            bore_d_used_for_query=None,
            blocked_stage="pool_c1_query_extraction",
            error_code="POOL_C1_NO_SAFE_QUERY_PARAMETER",
            error_fields=("bore_d",),
        )

    # Build a 6-field flat query from bore_d only via Schema derivation.
    # We pass a CAD-003 envelope query to the pool so the Schema can fill the
    # catalog-derived fields; the pool's internal DistancePolicy then scores
    # all pool candidates.
    from llm.contract import SCHEMA_VERSION
    from schema.set_screw_shaft_collar import validate_parameters

    envelope_params = {
        "schema_version": SCHEMA_VERSION,
        "family_id": FAMILY_ID,
        "parameters": {"bore_d": bore_d},
    }
    result = validate_parameters(envelope_params)
    if not result.ok or result.normalized is None:
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=(
                f"POOL_C1_SCHEMA_REJECTED: bore_d={bore_d} rejected by Schema; "
                "cannot build pool query"
            ),
            bore_d_used_for_query=bore_d,
            blocked_stage="pool_c1_schema_validation",
            error_code="POOL_C1_SCHEMA_REJECTED",
            error_fields=("bore_d",),
        )

    query_normalized = result.normalized
    effective_top_k = min(top_k, pool.candidate_count)

    # Query within the pool
    try:
        pool_result = pool.query(parameters=query_normalized, top_k=effective_top_k)
    except PoolError as exc:
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=f"POOL_C1_QUERY_ERROR: {exc.code}: {exc.message}",
            bore_d_used_for_query=bore_d,
            blocked_stage="pool_c1_retrieval_query",
            error_code=exc.code,
            error_fields=("pool_query",),
        )
    except Exception as exc:  # noqa: BLE001
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=f"POOL_C1_QUERY_ERROR: {type(exc).__name__}: {exc}",
            bore_d_used_for_query=bore_d,
            blocked_stage="pool_c1_retrieval_query",
            error_code="POOL_C1_QUERY_ERROR",
            error_fields=("pool_query",),
        )

    candidates = pool_result.get("results", [])
    if not candidates:
        return AssembledInput(
            query_id=case.query_id,
            condition_id=CONDITION_C1,
            natural_language_input=case.natural_language_input,
            reference_context=None,
            reference_context_sha256=None,
            candidate_source_ids=(),
            blocked_reason=(
                "POOL_C1_NO_RESULTS: pool query returned no candidates"
            ),
            bore_d_used_for_query=bore_d,
            blocked_stage="pool_c1_result_filter",
            error_code="POOL_C1_NO_RESULTS",
            error_fields=("candidate_source_ids",),
        )

    # Build the reference context — only safe fields, mandatory role label
    ref_dict = _build_pool_reference_context_dict(candidates)
    ref_str = json.dumps(ref_dict, ensure_ascii=False, sort_keys=True)
    ref_sha = hashlib.sha256(ref_str.encode("utf-8")).hexdigest()
    cand_ids = tuple(c.get("sample_id", "") for c in candidates)

    return AssembledInput(
        query_id=case.query_id,
        condition_id=CONDITION_C1,
        natural_language_input=case.natural_language_input,
        reference_context=ref_str,
        reference_context_sha256=ref_sha,
        candidate_source_ids=cand_ids,
        blocked_reason=None,
        bore_d_used_for_query=bore_d,
    )


def _build_pool_reference_context_dict(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the model-visible reference context from pool query results.

    Contains ONLY: role label, sample_id, family_id, parameters.normalized.
    No IR, CAD, STEP, evaluator labels, source metadata, or distance details.
    The mandatory untrusted-reference note is always included verbatim.
    """
    entries = []
    for candidate in candidates:
        entry = {
            "role": _POOL_CANDIDATE_ROLE,
            "sample_id": candidate.get("sample_id", ""),
            "family_id": candidate.get("family_id", FAMILY_ID),
            "parameters": dict(candidate.get("parameters_normalized", {})),
        }
        entries.append(entry)
    return {
        "retrieval_condition": "pool_C1_ret005_v1",
        "note": _POOL_UNTRUSTED_NOTE,
        "candidates": entries,
    }


# ---------------------------------------------------------------------------
# Explicit parameter extraction (user param priority)
# ---------------------------------------------------------------------------


def _extract_mm_field(text: str, pattern: "_re.Pattern[str]") -> float | None:
    """Extract a mm value from text using the given pattern.

    Returns None on no match or on value that cannot be safely parsed.
    Fail-closed: ambiguous or non-positive values are omitted.
    """
    match = pattern.search(text)
    if match is None:
        return None
    value_str = match.group(1)
    unit = (match.group(2) or "mm").lower()
    try:
        value = float(value_str)
    except (ValueError, TypeError):
        return None
    if not (value > 0):
        return None
    if unit in ("cm", "厘米"):
        value = value * 10.0
    if not (0 < value < 1e6) or not math.isfinite(value):
        return None
    return value


def _extract_second_screw(text: str) -> int | None:
    """Extract second_screw from text; only 0 or 1 allowed, fail-closed."""
    m = _SECOND_SCREW_RE.search(text)
    if m:
        try:
            val = int(m.group(1))
            if val in (0, 1):
                return val
        except ValueError:
            pass
    if _DOUBLE_SCREW_RE.search(text):
        return 1
    if _SINGLE_SCREW_RE.search(text):
        return 0
    return None


def extract_explicit_parameters(natural_language_input: str) -> dict[str, Any]:
    """Extract explicitly stated parameters from user natural-language input.

    Covers all six CAD-003 extractable fields: bore_d, outer_d, width,
    screw_d, screw_len, second_screw.  Values are normalised to mm.
    second_screw is accepted only as integer 0 or 1.

    Fail-closed: if a field keyword is recognised but the value cannot be
    safely parsed, the field is omitted — the model's extracted value then
    passes unchallenged for that field.  This avoids false positives for
    format-ambiguous text while still catching unambiguous conflicts.

    Does NOT read any evaluator-only fields.
    """
    result: dict[str, Any] = {}
    if not natural_language_input:
        return result

    # bore_d — reuse existing regex from conditions.extract_bore_d_mm
    bore_d = extract_bore_d_mm(natural_language_input)
    if bore_d is not None:
        result["bore_d"] = bore_d

    # outer_d
    outer_d_val = _extract_mm_field(natural_language_input, _OUTER_D_RE)
    if outer_d_val is not None:
        result["outer_d"] = outer_d_val

    # width
    width_val = _extract_mm_field(natural_language_input, _WIDTH_RE)
    if width_val is not None:
        result["width"] = width_val

    # screw_d
    screw_d_val = _extract_mm_field(natural_language_input, _SCREW_D_RE)
    if screw_d_val is not None:
        result["screw_d"] = screw_d_val

    # screw_len
    screw_len_val = _extract_mm_field(natural_language_input, _SCREW_LEN_RE)
    if screw_len_val is not None:
        result["screw_len"] = screw_len_val

    # second_screw — only 0 or 1; non-matching text is omitted (fail-closed)
    second_screw_val = _extract_second_screw(natural_language_input)
    if second_screw_val is not None:
        result["second_screw"] = second_screw_val

    return result


def check_user_param_priority(
    explicit_params: dict[str, Any],
    model_params: dict[str, Any],
    *,
    abs_tol: float = 1e-9,
) -> list[dict[str, Any]]:
    """Return conflict errors when model params disagree with explicit user params.

    Parameters
    ----------
    explicit_params:
        Parameters explicitly stated in the user's natural-language input
        (output of ``extract_explicit_parameters``).
    model_params:
        Parameters extracted by the LLM from the prompt response.
    abs_tol:
        Absolute tolerance for numeric comparison.

    Returns
    -------
    list of dicts
        Each dict has ``code``, ``field``, ``explicit_value``, and
        ``model_value``.  An empty list means no conflicts.
    """
    import math as _math

    conflicts: list[dict[str, Any]] = []
    for field_name, explicit_val in explicit_params.items():
        model_val = model_params.get(field_name)
        if model_val is None:
            # Model didn't extract this field; not a conflict (model just missed it)
            continue
        # Numeric comparison with tolerance
        try:
            explicit_num = float(explicit_val)
            model_num = float(model_val)
            if not _math.isclose(explicit_num, model_num, rel_tol=0.0, abs_tol=abs_tol):
                conflicts.append({
                    "code": f"USER_PARAM_CONFLICT_{field_name.upper()}",
                    "field": field_name,
                    "explicit_value": explicit_val,
                    "model_value": model_val,
                    "message": (
                        f"model extracted {field_name}={model_val!r} but user text "
                        f"explicitly states {field_name}={explicit_val!r}; "
                        "user parameter takes priority"
                    ),
                })
        except (TypeError, ValueError):
            # Non-numeric; use equality
            if explicit_val != model_val:
                conflicts.append({
                    "code": f"USER_PARAM_CONFLICT_{field_name.upper()}",
                    "field": field_name,
                    "explicit_value": explicit_val,
                    "model_value": model_val,
                    "message": (
                        f"model extracted {field_name}={model_val!r} but user text "
                        f"explicitly states {field_name}={explicit_val!r}; "
                        "user parameter takes priority"
                    ),
                })
    return conflicts
