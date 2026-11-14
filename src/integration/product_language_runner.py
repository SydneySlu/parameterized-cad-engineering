"""Offline-only preflight for the APP-003 language sample matrix.

This module deliberately has no request execution path.  It validates the
frozen stimulus file and budget plan while keeping evaluator labels unopened.
Formal execution requires a future independently reviewed runner.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from llm.authorization import AuthorizationScopeError
from llm.contract import FORMAL_EVALUATION_ALLOWED
from llm.product_language_authorization import (
    PRODUCT_LANGUAGE_CONDITION,
    PRODUCT_LANGUAGE_INPUT_IDS,
    PRODUCT_LANGUAGE_INPUTS_SHA256,
    PRODUCT_LANGUAGE_LABELS_SHA256,
    PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
    PRODUCT_LANGUAGE_MAX_BATCH_HTTP,
    PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
    PRODUCT_LANGUAGE_MODEL,
    PRODUCT_LANGUAGE_PROFILE_ID,
    PRODUCT_LANGUAGE_PROVIDER,
    ProductLanguageAuthorization,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUTS_RELATIVE_PATH = Path(
    "agent-work/integration/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01/model-inputs.json"
)


def _load_inputs(*, verify_sha256: bool = True) -> list[dict[str, str]]:
    path = REPO_ROOT / INPUTS_RELATIVE_PATH
    payload = path.read_bytes()
    if verify_sha256 and hashlib.sha256(payload).hexdigest() != PRODUCT_LANGUAGE_INPUTS_SHA256:
        raise ValueError("language model-inputs SHA-256 mismatch")
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("language model-inputs must be a JSON array")
    if any(
        not isinstance(row, dict)
        or set(row) != {"input_id", "request_text"}
        or not isinstance(row.get("input_id"), str)
        or not isinstance(row.get("request_text"), str)
        or not row["request_text"].strip()
        for row in data
    ):
        raise ValueError("language model-inputs row schema mismatch")
    ids = tuple(row["input_id"] for row in data)
    if ids != PRODUCT_LANGUAGE_INPUT_IDS:
        raise ValueError("language model-input IDs/order mismatch")
    return data


def run_product_language_offline_preflight(
    authorization: ProductLanguageAuthorization,
    *,
    batch_dir: Path | None = None,
) -> dict[str, Any]:
    """Check frozen input, authorization and budget without labels/network/keys."""
    if not isinstance(authorization, ProductLanguageAuthorization):
        raise AuthorizationScopeError("expected ProductLanguageAuthorization")
    errors: list[str] = []
    inputs_valid = False
    details: dict[str, Any] = {
        "profile_id": authorization.profile_id,
        "batch_id": authorization.batch_id,
        "input_ids": list(authorization.input_ids),
        "provider": PRODUCT_LANGUAGE_PROVIDER,
        "model": PRODUCT_LANGUAGE_MODEL,
        "condition": PRODUCT_LANGUAGE_CONDITION,
        "evaluator_labels_sha256_bound": (
            authorization.evaluator_labels_sha256 == PRODUCT_LANGUAGE_LABELS_SHA256
        ),
        "formal_evaluation_allowed": FORMAL_EVALUATION_ALLOWED,
        "execution_enabled": False,
    }
    try:
        inputs = _load_inputs(verify_sha256=True)
        inputs_valid = True
        details["inputs_sha256_ok"] = True
        details["input_count"] = len(inputs)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        details["inputs_sha256_ok"] = False
        errors.append(f"inputs_check:{type(exc).__name__}")

    computed_budget = PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS * PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN
    details["budget_plan"] = {
        "logical_runs": PRODUCT_LANGUAGE_MAX_LOGICAL_RUNS,
        "max_attempts_per_run": PRODUCT_LANGUAGE_MAX_ATTEMPTS_PER_RUN,
        "computed_max_http": computed_budget,
        "authorized_max_http": authorization.max_batch_attempts,
        "feasible": computed_budget <= authorization.max_batch_attempts,
    }
    if computed_budget > authorization.max_batch_attempts:
        errors.append("budget_infeasible")
    if authorization.max_batch_attempts != PRODUCT_LANGUAGE_MAX_BATCH_HTTP:
        errors.append("authorized_budget_mismatch")

    if batch_dir is not None:
        details["batch_dir_exists"] = batch_dir.exists()
        if batch_dir.exists():
            errors.append("batch_directory_already_exists")

    return {
        "ok": not errors,
        "errors": errors,
        "details": details,
        "planned_runs": [
            {
                "logical_run_id": authorization.expected_logical_run_id(input_id),
                "input_id": input_id,
                "condition": PRODUCT_LANGUAGE_CONDITION,
                "provider": PRODUCT_LANGUAGE_PROVIDER,
                "model": PRODUCT_LANGUAGE_MODEL,
            }
            for input_id in PRODUCT_LANGUAGE_INPUT_IDS
        ] if inputs_valid else [],
    }


def run_product_language_batch(*, authorization: ProductLanguageAuthorization, **_: Any) -> None:
    """Reject execution until a separately reviewed formal runner exists."""
    raise RuntimeError(
        f"{PRODUCT_LANGUAGE_PROFILE_ID} is offline-preflight-only; "
        "no model request path is implemented"
    )


__all__ = ["run_product_language_offline_preflight", "run_product_language_batch"]
