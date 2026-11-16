"""Single-family reference pool for RET-005.

The reference pool is a user-selected 3–5 sample subset of the RET-001 manifest.
Pool construction validates every sample_id against the manifest allowlist.
Retrieval within the pool reuses the RET-002 distance policy so that both
product mode and future C1 experiment mode share the same scoring logic.

Allowlist
---------
The allowlist contains every sample_id present in the manifest v0 JSONL.  User
selection is validated against this allowlist at construction time.  Pool size
must be between 3 and 5 (inclusive); any other size is a hard error.

Forbidden fields
----------------
Pool construction and display never read or expose:
- Evaluator labels or held-out truth (held in a separate evaluator-labels.json)
- IR file contents (the ir.path and ir.sha256 digest are carried but the file
  is never opened)
- STEP file contents
- Source CAD files
- Any field under ``artifacts.raw``, ``artifacts.step_body``, or similar

Allowed display fields
----------------------
- sample_id, family_id, sample_kind
- parameters.normalized (all six frozen fields)
- validation.schema, validation.final_stage, validation.native_geometry.is_valid
- source.repository, source.family_path, source.release_qualified,
  source.license_scope
- split.role, split.group_id, split.split_status
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from retrieval.config import (
    CONTINUOUS_FIELDS,
    DEFAULT_TOP_K,
    PARAMETER_ORDER,
    REPO_ROOT,
    SPLIT_STATUS,
    catalog_ranges,
)
from retrieval.distance import DistancePolicy
from retrieval.errors import RetrievalError


# ---------------------------------------------------------------------------
# Pool-specific constants
# ---------------------------------------------------------------------------

POOL_MIN_SIZE: int = 3
POOL_MAX_SIZE: int = 5
POOL_VERSION: str = "ret-005.pool.v1"
MANIFEST_REL_PATH = "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"


# ---------------------------------------------------------------------------
# Pool error codes (extend RetrievalError with pool-specific codes)
# ---------------------------------------------------------------------------


class PoolError(Exception):
    """A deterministic pool construction or query failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = dict(details or {})
        super().__init__(f"{code}: {message}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


# ---------------------------------------------------------------------------
# Safe display model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolEntry:
    """Read-only display entry for one reference pool sample.

    Contains ONLY the fields permitted for display.  Forbidden fields
    (evaluator labels, held-out truth, IR/STEP/source-CAD content) are never
    populated.
    """

    sample_id: str
    family_id: str
    sample_kind: str
    parameters_normalized: dict[str, Any]
    validation_status: str          # validation.final_stage
    validation_is_valid: bool       # validation.native_geometry.is_valid
    validation_schema: str          # validation.schema
    source_repository: str
    source_family_path: str
    source_release_qualified: bool
    source_license_scope: str
    split_role: str
    split_group_id: str
    split_status: str


def _safe_pool_entry(record: dict[str, Any]) -> PoolEntry:
    """Extract only the allowed display fields from a manifest record.

    Never accesses: ir content, STEP content, artifacts, evaluator labels,
    or any field not explicitly listed here.
    """
    params = record["parameters"]["normalized"]
    validation = record["validation"]
    native = validation.get("native_geometry", {})
    source = record["source"]
    split = record["split"]
    return PoolEntry(
        sample_id=record["sample_id"],
        family_id=record["family_id"],
        sample_kind=record["sample_kind"],
        parameters_normalized={field: params[field] for field in PARAMETER_ORDER},
        validation_status=validation["final_stage"],
        validation_is_valid=bool(native.get("is_valid", False)),
        validation_schema=validation["schema"],
        source_repository=source["repository"],
        source_family_path=source["family_path"],
        source_release_qualified=bool(source.get("release_qualified", False)),
        source_license_scope=source["license_scope"],
        split_role=split["role"],
        split_group_id=split["group_id"],
        split_status=split["split_status"],
    )


# ---------------------------------------------------------------------------
# Reference pool
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PoolCandidate:
    sample_id: str
    family_id: str
    normalized: dict[str, Any]
    record: dict[str, Any]


class ReferencePool:
    """User-selected 3–5 sample reference pool backed by the RET-001 manifest.

    Construction validates:
    - Every requested sample_id is present in the manifest (allowlist check).
    - Pool size is between ``POOL_MIN_SIZE`` and ``POOL_MAX_SIZE`` inclusive.
    - All samples belong to the same family.

    Retrieval uses the RET-002 ``DistancePolicy`` applied to the pool candidates
    only, not the full manifest.  This ensures pool-internal ordering is
    consistent with the global distance metric.
    """

    def __init__(
        self,
        *,
        family_id: str,
        candidates: tuple[_PoolCandidate, ...],
        policy: DistancePolicy,
        manifest_path: Path,
        manifest_sha256: str,
        manifest_version: str,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.family_id = family_id
        self._candidates = candidates
        self.policy = policy
        self.manifest_path = manifest_path
        self.manifest_sha256 = manifest_sha256
        self.manifest_version = manifest_version
        self.default_top_k = min(default_top_k, len(candidates))

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(c.sample_id for c in self._candidates)

    @classmethod
    def from_manifest(
        cls,
        sample_ids: Sequence[str],
        manifest_path: str | Path | None = None,
        *,
        policy: DistancePolicy | None = None,
        repo_root: str | Path | None = None,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> "ReferencePool":
        """Build a reference pool from a user-supplied list of sample_ids.

        Parameters
        ----------
        sample_ids:
            3–5 sample_id strings requested by the user.  Each must be present
            in the manifest; duplicates are rejected.
        manifest_path:
            Path to the JSONL manifest.  Defaults to the frozen RET-001 path.
        policy:
            Distance policy to use.  Defaults to the catalog-range RET-002 policy.
        repo_root:
            Repository root override.  Defaults to the package-inferred root.
        default_top_k:
            Default number of results returned by ``query()``.

        Raises
        ------
        PoolError
            If pool size is out of range, any sample_id is not in the allowlist,
            there are duplicates, or the manifest cannot be read.
        """
        root = Path(repo_root) if repo_root is not None else REPO_ROOT
        manifest_file = Path(manifest_path) if manifest_path is not None else (
            root / MANIFEST_REL_PATH
        )
        if not manifest_file.is_absolute():
            manifest_file = root / manifest_file

        # --- Validate count before any I/O ---
        ids = list(sample_ids)
        if len(ids) < POOL_MIN_SIZE:
            raise PoolError(
                "POOL_TOO_SMALL",
                f"pool requires at least {POOL_MIN_SIZE} sample_ids; "
                f"got {len(ids)}",
                details={"requested": ids, "min": POOL_MIN_SIZE},
            )
        if len(ids) > POOL_MAX_SIZE:
            raise PoolError(
                "POOL_TOO_LARGE",
                f"pool allows at most {POOL_MAX_SIZE} sample_ids; "
                f"got {len(ids)}",
                details={"requested": ids, "max": POOL_MAX_SIZE},
            )
        seen: set[str] = set()
        for sid in ids:
            if not isinstance(sid, str) or not sid:
                raise PoolError(
                    "POOL_INVALID_SAMPLE_ID",
                    "each sample_id must be a non-empty string",
                    details={"value": repr(sid)},
                )
            if sid in seen:
                raise PoolError(
                    "POOL_DUPLICATE_SAMPLE_ID",
                    "duplicate sample_id in pool request",
                    details={"sample_id": sid},
                )
            seen.add(sid)

        # --- Load manifest ---
        try:
            raw = manifest_file.read_bytes()
        except OSError as exc:
            raise PoolError(
                "POOL_MANIFEST_NOT_FOUND",
                "manifest file could not be read",
                details={"path": str(manifest_file), "error": str(exc)},
            ) from exc

        manifest_sha256 = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PoolError(
                "POOL_MANIFEST_PARSE_ERROR",
                "manifest is not valid UTF-8",
                details={"error": str(exc)},
            ) from exc

        lines = text.rstrip("\n").split("\n")
        all_records: dict[str, dict[str, Any]] = {}
        manifest_version: str | None = None

        for lineno, line in enumerate(lines, start=1):
            if not line.strip():
                raise PoolError(
                    "POOL_MANIFEST_PARSE_ERROR",
                    "manifest contains a blank line",
                    details={"line": lineno},
                )
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PoolError(
                    "POOL_MANIFEST_PARSE_ERROR",
                    "manifest line is not valid JSON",
                    details={"line": lineno, "error": str(exc)},
                ) from exc
            if not isinstance(record, dict):
                raise PoolError(
                    "POOL_MANIFEST_PARSE_ERROR",
                    "manifest record must be a JSON object",
                    details={"line": lineno},
                )
            sid = record.get("sample_id")
            if not isinstance(sid, str) or not sid:
                raise PoolError(
                    "POOL_MANIFEST_PARSE_ERROR",
                    "manifest record missing sample_id",
                    details={"line": lineno},
                )
            if manifest_version is None:
                manifest_version = record.get("manifest_version")
            all_records[sid] = record

        if manifest_version is None or not isinstance(manifest_version, str):
            raise PoolError(
                "POOL_MANIFEST_PARSE_ERROR",
                "manifest_version missing from first record",
            )

        # --- Allowlist check: every requested sample_id must be in manifest ---
        missing_ids = [sid for sid in ids if sid not in all_records]
        if missing_ids:
            raise PoolError(
                "POOL_SAMPLE_NOT_IN_ALLOWLIST",
                "one or more requested sample_ids are not present in the manifest",
                details={
                    "missing": missing_ids,
                    "available_count": len(all_records),
                    "hint": "only manifest-validated sample_ids may be added to a pool",
                },
            )

        # --- Validate family consistency ---
        families = {all_records[sid].get("family_id") for sid in ids}
        if len(families) != 1:
            raise PoolError(
                "POOL_FAMILY_MISMATCH",
                "all pool samples must belong to the same family",
                details={"families": sorted(str(f) for f in families)},
            )
        family_id = next(iter(families))
        if not isinstance(family_id, str) or not family_id:
            raise PoolError(
                "POOL_MANIFEST_PARSE_ERROR",
                "family_id missing from manifest record",
            )

        # --- Validate parameter fields for retrieval ---
        candidates: list[_PoolCandidate] = []
        for sid in ids:
            record = all_records[sid]
            normalized_block = (
                record.get("parameters", {}).get("normalized", {})
            )
            # Check all PARAMETER_ORDER fields present and numeric
            missing_fields = [
                f for f in PARAMETER_ORDER
                if f not in normalized_block
                or not isinstance(normalized_block[f], (int, float))
                or isinstance(normalized_block[f], bool)
                or not math.isfinite(float(normalized_block[f]))
            ]
            if missing_fields:
                raise PoolError(
                    "POOL_INVALID_PARAMETERS",
                    f"sample {sid!r} has invalid or missing normalized parameters",
                    details={"sample_id": sid, "missing_or_invalid": missing_fields},
                )
            candidates.append(_PoolCandidate(
                sample_id=sid,
                family_id=family_id,
                normalized={f: normalized_block[f] for f in PARAMETER_ORDER},
                record=record,
            ))

        effective_policy = policy if policy is not None else DistancePolicy(catalog_ranges())
        try:
            effective_policy.validate()
        except RetrievalError as exc:
            raise PoolError(
                "POOL_DISTANCE_POLICY_INVALID",
                f"distance policy validation failed: {exc}",
                details={"retrieval_error": exc.code},
            ) from exc

        return cls(
            family_id=family_id,
            candidates=tuple(candidates),
            policy=effective_policy,
            manifest_path=manifest_file,
            manifest_sha256=manifest_sha256,
            manifest_version=manifest_version,
            default_top_k=default_top_k,
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def describe(self) -> list[PoolEntry]:
        """Return safe display entries for all pool candidates.

        Never exposes evaluator labels, held-out truth, IR content,
        STEP content, or source CAD.
        """
        return [_safe_pool_entry(c.record) for c in self._candidates]

    # ------------------------------------------------------------------
    # In-pool retrieval
    # ------------------------------------------------------------------

    def query(
        self,
        parameters: Mapping[str, Any],
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Score all pool candidates and return top-k by distance ascending.

        Uses the RET-002 DistancePolicy applied within the pool only.

        Parameters
        ----------
        parameters:
            Normalized query parameters (all six frozen fields, bare numbers in
            mm with second_screw in {0, 1}).
        top_k:
            Number of results to return.  Defaults to ``default_top_k``.
            Must be in [1, candidate_count].

        Returns
        -------
        dict
            Pool-retrieval result with ``results`` list (rank ascending),
            ``pool_version``, ``candidates_considered``, ``top_k``.

        Raises
        ------
        PoolError
            If top_k is out of range or parameters are invalid.
        """
        # Resolve top_k
        resolved_k = self.default_top_k if top_k is None else top_k
        if isinstance(resolved_k, bool) or not isinstance(resolved_k, int):
            raise PoolError(
                "POOL_INVALID_TOP_K",
                "top_k must be an integer",
                details={"top_k": repr(resolved_k)},
            )
        if resolved_k < 1:
            raise PoolError(
                "POOL_INVALID_TOP_K",
                "top_k must be at least 1",
                details={"top_k": resolved_k},
            )
        if resolved_k > self.candidate_count:
            raise PoolError(
                "POOL_TOP_K_OUT_OF_RANGE",
                "top_k exceeds the number of pool candidates",
                details={"top_k": resolved_k, "candidate_count": self.candidate_count},
            )

        # Validate query parameters
        if not isinstance(parameters, Mapping):
            raise PoolError(
                "POOL_INVALID_PARAMETERS",
                "query parameters must be a mapping",
                details={"type": type(parameters).__name__},
            )
        normalized: dict[str, Any] = {}
        for field in CONTINUOUS_FIELDS:
            value = parameters.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise PoolError(
                    "POOL_INVALID_PARAMETERS",
                    f"query parameter {field!r} must be a finite number in mm",
                    details={"field": field, "value": repr(value)},
                )
            normalized[field] = value
        second = parameters.get("second_screw")
        if isinstance(second, bool) or not isinstance(second, int) or second not in (0, 1):
            raise PoolError(
                "POOL_INVALID_PARAMETERS",
                "second_screw must be integer 0 or 1",
                details={"value": repr(second)},
            )
        normalized["second_screw"] = second

        # Score all pool candidates
        scored: list[tuple[float, str, _PoolCandidate, dict[str, Any]]] = []
        for candidate in self._candidates:
            distance = self.policy.score(normalized, candidate.normalized)
            scored.append((distance["total"], candidate.sample_id, candidate, distance))
        scored.sort(key=lambda item: (item[0], item[1]))

        results = []
        for rank, (_total, _sid, candidate, distance) in enumerate(
            scored[:resolved_k], start=1
        ):
            record = candidate.record
            source = record["source"]
            params = record["parameters"]
            results.append({
                "rank": rank,
                "sample_id": candidate.sample_id,
                "family_id": record["family_id"],
                "sample_kind": record["sample_kind"],
                "split_role": record["split"]["role"],
                "parameters_normalized": {
                    field: params["normalized"][field] for field in PARAMETER_ORDER
                },
                "distance": {
                    "policy_id": distance["policy_id"],
                    "total": distance["total"],
                    "continuous_mean": distance["continuous_mean"],
                    "discrete_term": distance["discrete_term"],
                },
                "validation_status": record["validation"]["final_stage"],
                "validation_is_valid": bool(
                    record["validation"].get("native_geometry", {}).get("is_valid", False)
                ),
                "source_repository": source["repository"],
                "source_release_qualified": bool(source.get("release_qualified", False)),
            })

        return {
            "pool_version": POOL_VERSION,
            "family_id": self.family_id,
            "manifest_sha256": self.manifest_sha256,
            "pool_sample_ids": list(self.sample_ids),
            "candidates_considered": self.candidate_count,
            "top_k": resolved_k,
            "query_parameters": {field: normalized[field] for field in PARAMETER_ORDER},
            "results": results,
            "data_boundary": {
                "reads_manifest_structured_fields": True,
                "reads_ir_files": False,
                "reads_step_files": False,
                "reads_evaluator_labels": False,
                "reads_held_out_truth": False,
                "reads_source_cad": False,
                "reads_raw": False,
            },
        }
