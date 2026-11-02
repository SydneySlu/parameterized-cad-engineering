"""Deterministic single-family retrieval baseline (RET-002).

The index is a read-only consumer of the RET-001 manifest v0 JSONL.  It reads
only structured manifest fields: parameters, provenance, catalog row, split,
IR path/sha256, validation summary and limitations.  It does not open IR files,
STEP files, render images or third-party drawings, and it does not touch the
Schema, Typed CAD IR or CAD compiler interfaces.

Query forms
-----------
1. `cad003_envelope`: an object carrying `schema_version`, `family_id` and/or
   `parameters`.  It is normalized by `schema.set_screw_shaft_collar`; the
   Schema's own rules (catalog coupling, second-screw threshold, unit parsing)
   are reused, not re-implemented.  The envelope must pass the Schema, so it is
   always `catalog_validated` when it returns results.
2. `flat_parameters`: a complete six-field object with bare numbers in mm
   (and `second_screw` in {0, 1}).  Missing fields are rejected rather than
   defaulted.  If the Schema rejects the complete object, retrieval still runs
   as nearest-neighbour search and the result is marked
   `out_of_catalog_or_unvalidated`.

Ordering is total distance ascending, then sample_id ascending, so equal
inputs produce byte-identical JSON in the same environment.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from schema.set_screw_shaft_collar import validate_parameters

from .config import (
    CATALOG_KEY,
    CONTINUOUS_FIELDS,
    DEFAULT_TOP_K,
    KNOWN_ROLES,
    PARAMETER_ORDER,
    POLICY_ID,
    REPO_ROOT,
    RETRIEVAL_VERSION,
    SPLIT_STATUS,
    RetrievalConfig,
    catalog_ranges,
    normalize_candidate_roles,
    sha256_bytes,
)
from .distance import DistancePolicy
from .errors import RetrievalError


ENVELOPE_MARKERS = frozenset({"schema_version", "family_id", "parameters"})
_SHA256_LENGTH = 64

_NOTES_BASE = (
    "distance is normalized parameter proximity only; it is not CAD geometry equivalence, "
    "manufacturability, strength or generation-quality evidence",
    "split_status=provisional_small_n: candidates come from a provisional small-n grouping, "
    "not a benchmark split and not an accuracy estimate",
    "only manifest v0 structured fields were read; STEP, render images and third-party "
    "drawings were not read",
)


@dataclass(frozen=True)
class _Candidate:
    sample_id: str
    family_id: str
    normalized: dict[str, int | float]
    record: dict[str, Any]


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable query result with deterministic JSON serialization."""

    manifest: Mapping[str, Any]
    family_id: str
    query: Mapping[str, Any]
    candidate_roles: tuple[str, ...]
    top_k: int
    candidates_considered: int
    results: tuple[Mapping[str, Any], ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "retrieval_version": RETRIEVAL_VERSION,
            "policy_id": POLICY_ID,
            "task": "RET-002",
            "family_id": self.family_id,
            "manifest": dict(self.manifest),
            "candidate_roles": list(self.candidate_roles),
            "split_status": SPLIT_STATUS,
            "top_k": self.top_k,
            "candidates_considered": self.candidates_considered,
            "query": dict(self.query),
            "results": [dict(item) for item in self.results],
            "notes": list(self.notes),
            "data_boundary": {
                "reads_manifest": True,
                "reads_step": False,
                "reads_render": False,
                "reads_ir_files": False,
                "reads_external_drawings": False,
            },
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=indent, sort_keys=False)

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return sha256_bytes(self.to_canonical_json().encode("utf-8"))


def _manifest_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(char in "0123456789abcdef" for char in value)
    )


def _invalid_record(line: int, reason: str, *, sample_id: Any = None, field: str | None = None) -> RetrievalError:
    details: dict[str, Any] = {"line": line, "reason": reason}
    if sample_id is not None:
        details["sample_id"] = sample_id
    return RetrievalError(
        "RETRIEVAL_INVALID_RECORD",
        reason,
        stage="index",
        fields=(field,) if field else (),
        details=details,
    )


def _require(condition: bool, line: int, reason: str, *, sample_id: Any = None, field: str | None = None) -> None:
    if not condition:
        raise _invalid_record(line, reason, sample_id=sample_id, field=field)


def _validate_record(record: Any, line: int) -> dict[str, Any]:
    _require(isinstance(record, dict), line, "manifest record must be a JSON object")
    sample_id = record.get("sample_id")
    _require(isinstance(sample_id, str) and bool(sample_id), line, "sample_id must be a non-empty string", field="sample_id")
    _require(isinstance(record.get("family_id"), str) and bool(record["family_id"]), line, "family_id must be a non-empty string", sample_id=sample_id, field="family_id")
    _require(isinstance(record.get("sample_kind"), str) and bool(record["sample_kind"]), line, "sample_kind must be a non-empty string", sample_id=sample_id, field="sample_kind")

    parameters = record.get("parameters")
    _require(isinstance(parameters, dict), line, "parameters block is required", sample_id=sample_id, field="parameters")
    normalized = parameters.get("normalized")
    _require(isinstance(normalized, dict), line, "parameters.normalized object is required", sample_id=sample_id, field="parameters.normalized")
    _require(set(normalized) == set(PARAMETER_ORDER), line, "parameters.normalized must contain exactly the six frozen fields", sample_id=sample_id, field="parameters.normalized")
    for field in PARAMETER_ORDER:
        value = normalized[field]
        _require(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)),
            line,
            f"parameters.normalized.{field} must be a finite number",
            sample_id=sample_id,
            field=f"parameters.normalized.{field}",
        )
    _require(
        isinstance(normalized["second_screw"], int)
        and not isinstance(normalized["second_screw"], bool)
        and normalized["second_screw"] in (0, 1),
        line,
        "parameters.normalized.second_screw must be integer 0 or 1",
        sample_id=sample_id,
        field="parameters.normalized.second_screw",
    )
    units = parameters.get("units")
    _require(isinstance(units, dict) and units.get("length") == "mm", line, "parameters.units.length must be mm", sample_id=sample_id, field="parameters.units")
    provenance = parameters.get("provenance")
    _require(isinstance(provenance, dict), line, "parameters.provenance object is required", sample_id=sample_id, field="parameters.provenance")
    for field in PARAMETER_ORDER:
        entry = provenance.get(field)
        _require(
            isinstance(entry, dict) and isinstance(entry.get("source"), str) and bool(entry["source"]),
            line,
            f"parameters.provenance.{field}.source is required",
            sample_id=sample_id,
            field=f"parameters.provenance.{field}",
        )
    input_payload = parameters.get("input_payload")
    _require(
        isinstance(input_payload, dict)
        and isinstance(input_payload.get("path"), str)
        and _is_sha256(input_payload.get("sha256")),
        line,
        "parameters.input_payload must carry a path and sha256",
        sample_id=sample_id,
        field="parameters.input_payload",
    )

    ir = record.get("ir")
    _require(isinstance(ir, dict), line, "ir block is required", sample_id=sample_id, field="ir")
    _require(isinstance(ir.get("path"), str) and bool(ir["path"]), line, "ir.path must be a non-empty string", sample_id=sample_id, field="ir.path")
    _require(_is_sha256(ir.get("sha256")), line, "ir.sha256 must be lowercase 64-hex", sample_id=sample_id, field="ir.sha256")
    for field in ("ir_version", "ir_revision", "status"):
        _require(isinstance(ir.get(field), str) and bool(ir[field]), line, f"ir.{field} must be a non-empty string", sample_id=sample_id, field=f"ir.{field}")

    split = record.get("split")
    _require(isinstance(split, dict), line, "split block is required", sample_id=sample_id, field="split")
    _require(split.get("role") in KNOWN_ROLES, line, "split.role must be a known role", sample_id=sample_id, field="split.role")
    _require(isinstance(split.get("group_id"), str) and bool(split["group_id"]), line, "split.group_id must be a non-empty string", sample_id=sample_id, field="split.group_id")
    _require(split.get("split_status") == SPLIT_STATUS, line, "split.split_status must stay provisional_small_n", sample_id=sample_id, field="split.split_status")
    _require(isinstance(split.get("split_rule"), str) and bool(split["split_rule"]), line, "split.split_rule must be a non-empty string", sample_id=sample_id, field="split.split_rule")

    source = record.get("source")
    _require(isinstance(source, dict), line, "source block is required", sample_id=sample_id, field="source")
    for field in ("repository", "source_commit", "family_path", "family_status", "snapshot_status", "license_scope"):
        _require(isinstance(source.get(field), str) and bool(source[field]), line, f"source.{field} must be a non-empty string", sample_id=sample_id, field=f"source.{field}")
    _require(isinstance(source.get("release_qualified"), bool), line, "source.release_qualified must be a boolean", sample_id=sample_id, field="source.release_qualified")
    catalog_row = source.get("catalog_row")
    _require(isinstance(catalog_row, dict), line, "source.catalog_row is required", sample_id=sample_id, field="source.catalog_row")
    _require(isinstance(catalog_row.get("index"), int) and not isinstance(catalog_row.get("index"), bool), line, "source.catalog_row.index must be an integer", sample_id=sample_id, field="source.catalog_row.index")
    _require(catalog_row.get("key") == CATALOG_KEY, line, "source.catalog_row.key must be bore_d", sample_id=sample_id, field="source.catalog_row.key")
    _require(catalog_row.get("value") == normalized["bore_d"], line, "source.catalog_row.value must equal normalized bore_d", sample_id=sample_id, field="source.catalog_row.value")
    row = catalog_row.get("row")
    _require(isinstance(row, list) and len(row) == 5, line, "source.catalog_row.row must have five values", sample_id=sample_id, field="source.catalog_row.row")
    _require(
        list(row) == [normalized[field] for field in CONTINUOUS_FIELDS],
        line,
        "source.catalog_row.row must equal the normalized catalog fields",
        sample_id=sample_id,
        field="source.catalog_row.row",
    )

    validation = record.get("validation")
    _require(isinstance(validation, dict), line, "validation block is required", sample_id=sample_id, field="validation")
    for field in ("schema", "family_rules", "cad_compile", "final_stage", "policy_id"):
        _require(isinstance(validation.get(field), str) and bool(validation[field]), line, f"validation.{field} must be a non-empty string", sample_id=sample_id, field=f"validation.{field}")
    _require(isinstance(validation.get("completed_stages"), list), line, "validation.completed_stages must be a list", sample_id=sample_id, field="validation.completed_stages")
    native = validation.get("native_geometry")
    _require(isinstance(native, dict), line, "validation.native_geometry is required", sample_id=sample_id, field="validation.native_geometry")
    for field in ("solids", "shells", "faces", "edges", "vertices"):
        _require(isinstance(native.get(field), int) and not isinstance(native.get(field), bool), line, f"validation.native_geometry.{field} must be an integer", sample_id=sample_id, field=f"validation.native_geometry.{field}")
    _require(isinstance(native.get("is_valid"), bool), line, "validation.native_geometry.is_valid must be a boolean", sample_id=sample_id, field="validation.native_geometry.is_valid")
    _require(isinstance(native.get("volume_mm3"), (int, float)) and math.isfinite(float(native["volume_mm3"])), line, "validation.native_geometry.volume_mm3 must be finite", sample_id=sample_id, field="validation.native_geometry.volume_mm3")
    _require(isinstance(native.get("bbox_mm"), dict), line, "validation.native_geometry.bbox_mm is required", sample_id=sample_id, field="validation.native_geometry.bbox_mm")
    repeat = validation.get("native_repeatability")
    _require(isinstance(repeat, dict) and isinstance(repeat.get("pass"), bool), line, "validation.native_repeatability.pass must be a boolean", sample_id=sample_id, field="validation.native_repeatability")
    readback = validation.get("step_readback")
    _require(isinstance(readback, dict) and isinstance(readback.get("pass"), bool), line, "validation.step_readback.pass must be a boolean", sample_id=sample_id, field="validation.step_readback")

    limitations = record.get("limitations")
    _require(
        isinstance(limitations, list) and bool(limitations) and all(isinstance(item, str) for item in limitations),
        line,
        "limitations must be a non-empty list of strings",
        sample_id=sample_id,
        field="limitations",
    )
    return record


def _validation_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    validation = record["validation"]
    native = validation["native_geometry"]
    repeat = validation["native_repeatability"]
    readback = validation["step_readback"]
    readback_geometry = readback.get("readback_geometry", {})
    return {
        "schema": validation["schema"],
        "family_rules": validation["family_rules"],
        "cad_compile": validation["cad_compile"],
        "completed_stages": list(validation["completed_stages"]),
        "final_stage": validation["final_stage"],
        "policy_id": validation["policy_id"],
        "native_geometry": {
            "solids": native["solids"],
            "shells": native["shells"],
            "faces": native["faces"],
            "edges": native["edges"],
            "vertices": native["vertices"],
            "is_valid": native["is_valid"],
            "volume_mm3": native["volume_mm3"],
            "bbox_mm": dict(native["bbox_mm"]),
        },
        "native_repeatability": {
            "pass": repeat["pass"],
            "exact_equal": repeat.get("exact_equal"),
            "policy_id": repeat.get("policy_id"),
        },
        "step_readback": {
            "pass": readback["pass"],
            "policy_id": readback.get("policy_id"),
            "hard_mismatches": list(readback.get("hard_mismatches", [])),
            "bbox_pass": readback.get("bbox_pass"),
            "bbox_max_abs_mm": readback.get("bbox_max_abs_mm"),
            "volume_abs_mm3": readback.get("volume_abs_mm3"),
            "volume_rel": readback.get("volume_rel"),
            "readback_solids": readback_geometry.get("solids"),
            "readback_volume_mm3": readback_geometry.get("volume_mm3"),
        },
    }


def _same_catalog_row(query: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return all(query[field] == candidate[field] for field in PARAMETER_ORDER)


def _candidate_entry(
    rank: int,
    candidate: _Candidate,
    distance: Mapping[str, Any],
    query_parameters: Mapping[str, Any],
) -> dict[str, Any]:
    record = candidate.record
    source = record["source"]
    catalog_row = source["catalog_row"]
    parameters = record["parameters"]
    return {
        "rank": rank,
        "sample_id": candidate.sample_id,
        "family_id": record["family_id"],
        "sample_kind": record["sample_kind"],
        "same_catalog_row_as_query": _same_catalog_row(query_parameters, candidate.normalized),
        "split": {
            "role": record["split"]["role"],
            "group_id": record["split"]["group_id"],
            "split_status": record["split"]["split_status"],
            "split_rule": record["split"]["split_rule"],
        },
        "source": {
            "repository": source["repository"],
            "source_commit": source["source_commit"],
            "family_path": source["family_path"],
            "family_status": source["family_status"],
            "release_qualified": source["release_qualified"],
            "snapshot_status": source["snapshot_status"],
            "license_scope": source["license_scope"],
            "catalog_row": {
                "index": catalog_row["index"],
                "key": catalog_row["key"],
                "value": catalog_row["value"],
                "row": list(catalog_row["row"]),
            },
        },
        "ir": {
            "ir_version": record["ir"]["ir_version"],
            "ir_revision": record["ir"]["ir_revision"],
            "status": record["ir"]["status"],
            "path": record["ir"]["path"],
            "sha256": record["ir"]["sha256"],
        },
        "parameters": {
            "normalized": {field: parameters["normalized"][field] for field in PARAMETER_ORDER},
            "units": dict(parameters.get("units", {})),
            "provenance": {
                field: dict(parameters["provenance"][field])
                for field in PARAMETER_ORDER
                if field in parameters["provenance"]
            },
            "input_payload": dict(parameters.get("input_payload", {})),
        },
        "distance": dict(distance),
        "validation_summary": _validation_summary(record),
        "limitations": list(record["limitations"]),
    }


class RetrievalIndex:
    """Immutable manifest-backed candidate index for one frozen family."""

    def __init__(
        self,
        *,
        family_id: str,
        candidates: tuple[_Candidate, ...],
        candidate_roles: tuple[str, ...],
        policy: DistancePolicy,
        manifest_path: Path,
        manifest_sha256: str,
        manifest_version: str,
        role_counts: Mapping[str, int],
        default_top_k: int,
    ) -> None:
        self.family_id = family_id
        self.candidate_roles = candidate_roles
        self.policy = policy
        self.manifest_path = manifest_path
        self.manifest_sha256 = manifest_sha256
        self.manifest_version = manifest_version
        self.default_top_k = default_top_k
        self._candidates = candidates
        self._role_counts = dict(role_counts)

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    @classmethod
    def from_manifest(
        cls,
        path: str | Path,
        candidate_roles: Iterable[str] | None = None,
        *,
        policy: DistancePolicy | None = None,
        source_manifest_sha256: str | None = None,
        repo_root: str | Path | None = None,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> "RetrievalIndex":
        root = Path(repo_root) if repo_root is not None else REPO_ROOT
        manifest_path = Path(path)
        if not manifest_path.is_absolute():
            manifest_path = root / manifest_path
        try:
            raw = manifest_path.read_bytes()
        except OSError as exc:
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_NOT_FOUND",
                "manifest file could not be read",
                stage="index",
                details={"path": str(manifest_path), "error": str(exc)},
            ) from exc
        manifest_sha256 = sha256_bytes(raw)
        if source_manifest_sha256 is not None and source_manifest_sha256 != manifest_sha256:
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_HASH_MISMATCH",
                "manifest sha256 differs from the expected digest",
                stage="index",
                details={"expected": source_manifest_sha256, "actual": manifest_sha256},
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_PARSE_ERROR",
                "manifest is not valid UTF-8",
                stage="index",
                details={"path": str(manifest_path), "error": str(exc)},
            ) from exc
        if not text.strip():
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_EMPTY",
                "manifest contains no records",
                stage="index",
                details={"path": str(manifest_path)},
            )
        lines = text.rstrip("\n").split("\n")
        records: list[dict[str, Any]] = []
        seen_samples: dict[str, int] = {}
        seen_groups: dict[str, int] = {}
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                raise RetrievalError(
                    "RETRIEVAL_MANIFEST_PARSE_ERROR",
                    "manifest contains a blank line",
                    stage="index",
                    details={"line": number, "path": str(manifest_path)},
                )
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RetrievalError(
                    "RETRIEVAL_MANIFEST_PARSE_ERROR",
                    "manifest line is not valid JSON",
                    stage="index",
                    details={"line": number, "error": str(exc), "path": str(manifest_path)},
                ) from exc
            _validate_record(record, number)
            sample_id = record["sample_id"]
            group_id = record["split"]["group_id"]
            if sample_id in seen_samples:
                raise RetrievalError(
                    "RETRIEVAL_DUPLICATE_SAMPLE_ID",
                    "duplicate sample_id in manifest; duplicate candidates are rejected",
                    stage="index",
                    fields=("sample_id",),
                    details={"line": number, "sample_id": sample_id, "first_line": seen_samples[sample_id]},
                )
            if group_id in seen_groups:
                raise RetrievalError(
                    "RETRIEVAL_DUPLICATE_GROUP_ID",
                    "duplicate split group_id in manifest; duplicate candidates are rejected",
                    stage="index",
                    fields=("split.group_id",),
                    details={"line": number, "group_id": group_id, "first_line": seen_groups[group_id]},
                )
            seen_samples[sample_id] = number
            seen_groups[group_id] = number
            records.append(record)

        manifest_version = records[0].get("manifest_version")
        if not isinstance(manifest_version, str) or not manifest_version:
            raise RetrievalError(
                "RETRIEVAL_INVALID_RECORD",
                "manifest_version is missing from the first record",
                stage="index",
                fields=("manifest_version",),
                details={"line": 1},
            )
        for number, record in enumerate(records, start=1):
            if record.get("manifest_version") != manifest_version:
                raise RetrievalError(
                    "RETRIEVAL_INVALID_RECORD",
                    "manifest_version differs between records",
                    stage="index",
                    fields=("manifest_version",),
                    details={"line": number, "expected": manifest_version, "observed": record.get("manifest_version")},
                )

        families = sorted({record["family_id"] for record in records})
        if len(families) != 1:
            raise RetrievalError(
                "RETRIEVAL_FAMILY_MISMATCH",
                "retrieval index v0 supports exactly one family",
                stage="index",
                fields=("family_id",),
                details={"families": families},
            )
        family_id = families[0]

        roles = normalize_candidate_roles(candidate_roles)
        present_roles = sorted({record["split"]["role"] for record in records})
        unknown = [role for role in roles if role not in present_roles]
        if unknown:
            raise RetrievalError(
                "RETRIEVAL_UNKNOWN_ROLE",
                "candidate_roles contains a role that is absent from the manifest",
                stage="index",
                fields=("candidate_roles",),
                details={"requested": list(roles), "available": present_roles},
            )
        selected = [record for record in records if record["split"]["role"] in set(roles)]
        if not selected:
            raise RetrievalError(
                "RETRIEVAL_NO_CANDIDATES",
                "no manifest records match the selected candidate roles",
                stage="index",
                details={"candidate_roles": list(roles), "available": present_roles},
            )

        effective_policy = policy if policy is not None else DistancePolicy(catalog_ranges())
        effective_policy.validate()

        candidates = tuple(
            _Candidate(
                sample_id=record["sample_id"],
                family_id=record["family_id"],
                normalized={field: record["parameters"]["normalized"][field] for field in PARAMETER_ORDER},
                record=record,
            )
            for record in selected
        )
        role_counts = {role: 0 for role in KNOWN_ROLES}
        for record in records:
            role_counts[record["split"]["role"]] = role_counts.get(record["split"]["role"], 0) + 1

        return cls(
            family_id=family_id,
            candidates=candidates,
            candidate_roles=roles,
            policy=effective_policy,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
            manifest_version=manifest_version,
            role_counts=role_counts,
            default_top_k=default_top_k,
        )

    @classmethod
    def from_config(cls, path: str | Path, *, repo_root: str | Path | None = None) -> "RetrievalIndex":
        config = RetrievalConfig.from_path(path, repo_root=repo_root)
        policy = DistancePolicy(config.range_map())
        policy.validate()
        index = cls.from_manifest(
            config.manifest_path,
            config.candidate_roles,
            policy=policy,
            source_manifest_sha256=config.manifest_sha256,
            repo_root=config.repo_root,
            default_top_k=config.default_top_k,
        )
        index.config = config  # type: ignore[attr-defined]
        return index

    def describe(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "manifest": {
                "manifest_version": self.manifest_version,
                "path": _manifest_label(self.manifest_path),
                "sha256": self.manifest_sha256,
                "records": sum(self._role_counts.values()),
                "role_counts": dict(self._role_counts),
            },
            "candidate_roles": list(self.candidate_roles),
            "candidate_count": self.candidate_count,
            "candidate_sample_ids": [candidate.sample_id for candidate in self._candidates],
            "split_status": SPLIT_STATUS,
            "policy": {
                "policy_id": POLICY_ID,
                "ranges": {field: list(self.policy.ranges[field]) for field in CONTINUOUS_FIELDS},
                "continuous_field_weight": self.policy.continuous_field_weight,
                "discrete_weight": self.policy.discrete_weight,
                "tiebreak": "total ascending, then sample_id ascending",
            },
            "default_top_k": self.default_top_k,
        }

    def _normalize_query(
        self,
        family_id: Any,
        parameters: Any,
    ) -> tuple[dict[str, int | float], str, dict[str, Any], str]:
        if not isinstance(family_id, str) or family_id != self.family_id:
            raise RetrievalError(
                "RETRIEVAL_UNKNOWN_FAMILY",
                "query family_id is not the indexed family",
                stage="query",
                fields=("family_id",),
                details={"requested": family_id if isinstance(family_id, str) else repr(family_id), "available": [self.family_id]},
            )
        if not isinstance(parameters, Mapping):
            raise RetrievalError(
                "RETRIEVAL_INVALID_QUERY",
                "parameters must be a JSON object",
                stage="query",
                fields=("parameters",),
                details={"type": type(parameters).__name__},
            )

        if ENVELOPE_MARKERS.intersection(parameters):
            return self._normalize_envelope(parameters)
        return self._normalize_flat(parameters)

    def _normalize_envelope(
        self,
        parameters: Mapping[str, Any],
    ) -> tuple[dict[str, int | float], str, dict[str, Any], str]:
        if "parameters" not in parameters:
            raise RetrievalError(
                "RETRIEVAL_MISSING_FIELD",
                "CAD-003 envelope requires a parameters object",
                stage="query",
                fields=("parameters",),
            )
        result = validate_parameters(dict(parameters))
        schema_errors = [error.as_dict() for error in result.errors]
        if not result.ok or result.normalized is None:
            raise RetrievalError(
                "RETRIEVAL_SCHEMA_REJECTED",
                "CAD-003 Schema rejected the envelope query; the envelope path requires a schema-valid catalog query",
                stage="query",
                fields=tuple(sorted({field for error in result.errors for field in error.fields})),
                details={
                    "schema_version": result.schema_version,
                    "schema_errors": schema_errors,
                    "hint": "use flat canonical parameters (all six fields, bare mm) for out-of-catalog nearest-neighbour queries",
                },
            )
        normalized = {field: result.normalized[field] for field in PARAMETER_ORDER}
        schema_check = {
            "ok": True,
            "schema_version": result.schema_version,
            "errors": schema_errors,
            "provenance": dict(result.provenance),
        }
        return normalized, "cad003_envelope", schema_check, "catalog_validated"

    def _normalize_flat(
        self,
        parameters: Mapping[str, Any],
    ) -> tuple[dict[str, int | float], str, dict[str, Any], str]:
        unknown = sorted(set(parameters) - set(PARAMETER_ORDER))
        if unknown:
            raise RetrievalError(
                "RETRIEVAL_UNKNOWN_FIELD",
                "query contains fields outside the frozen family parameter contract",
                stage="query",
                fields=tuple(unknown),
                details={"unknown": unknown, "allowed": list(PARAMETER_ORDER)},
            )
        missing = [field for field in PARAMETER_ORDER if field not in parameters or parameters[field] is None]
        if missing:
            raise RetrievalError(
                "RETRIEVAL_MISSING_FIELD",
                "flat query must provide all six frozen fields; missing values are not defaulted",
                stage="query",
                fields=tuple(missing),
                details={"missing": missing, "hint": "use a CAD-003 envelope to let the Schema derive catalog fields from bore_d"},
            )
        normalized: dict[str, int | float] = {}
        for field in CONTINUOUS_FIELDS:
            value = parameters[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise RetrievalError(
                    "RETRIEVAL_INVALID_PARAMETER",
                    f"{field} must be a finite number in mm",
                    stage="query",
                    fields=(field,),
                    details={"field": field, "value": repr(value)[:120]},
                )
            normalized[field] = value
        second = parameters["second_screw"]
        if isinstance(second, bool) or not isinstance(second, int) or second not in (0, 1):
            raise RetrievalError(
                "RETRIEVAL_INVALID_PARAMETER",
                "second_screw must be integer 0 or 1",
                stage="query",
                fields=("second_screw",),
                details={"field": "second_screw", "value": repr(second)[:120]},
            )
        normalized["second_screw"] = second

        result = validate_parameters(normalized)
        schema_errors = [error.as_dict() for error in result.errors]
        schema_check = {
            "ok": result.ok,
            "schema_version": result.schema_version,
            "errors": schema_errors,
            "provenance": dict(result.provenance),
        }
        status = "catalog_validated" if result.ok else "out_of_catalog_or_unvalidated"
        return normalized, "flat_parameters", schema_check, status

    def _resolve_top_k(self, top_k: Any) -> int:
        if top_k is None:
            resolved = self.default_top_k
        else:
            if isinstance(top_k, bool) or not isinstance(top_k, int):
                raise RetrievalError(
                    "RETRIEVAL_INVALID_TOP_K",
                    "top_k must be an integer",
                    stage="query",
                    fields=("top_k",),
                    details={"top_k": repr(top_k)[:120]},
                )
            if top_k < 1:
                raise RetrievalError(
                    "RETRIEVAL_INVALID_TOP_K",
                    "top_k must be at least 1",
                    stage="query",
                    fields=("top_k",),
                    details={"top_k": top_k},
                )
            resolved = top_k
        if resolved > self.candidate_count:
            raise RetrievalError(
                "RETRIEVAL_TOP_K_OUT_OF_RANGE",
                "top_k exceeds the number of eligible candidates",
                stage="query",
                fields=("top_k",),
                details={"top_k": resolved, "candidate_count": self.candidate_count},
            )
        return resolved

    def query(
        self,
        family_id: str,
        parameters: Mapping[str, Any],
        top_k: int | None = None,
    ) -> RetrievalResult:
        normalized, input_form, schema_check, query_status = self._normalize_query(family_id, parameters)
        resolved_top_k = self._resolve_top_k(top_k)

        scored: list[tuple[float, str, _Candidate, dict[str, Any]]] = []
        for candidate in self._candidates:
            distance = self.policy.score(normalized, candidate.normalized)
            scored.append((distance["total"], candidate.sample_id, candidate, distance))
        scored.sort(key=lambda item: (item[0], item[1]))

        entries = [
            _candidate_entry(rank, candidate, distance, normalized)
            for rank, (_total, _sample_id, candidate, distance) in enumerate(scored[:resolved_top_k], start=1)
        ]

        notes = [
            *_NOTES_BASE,
            "candidate_roles were fixed when the index was built: "
            + ", ".join(self.candidate_roles)
            + "; rows with other roles are excluded, not scored",
        ]
        if query_status != "catalog_validated":
            notes.append(
                "query_status=out_of_catalog_or_unvalidated: the query is not a Schema-confirmed "
                "catalog truth; results are nearest-neighbour candidates only"
            )

        manifest_block = {
            "manifest_version": self.manifest_version,
            "path": _manifest_label(self.manifest_path),
            "sha256": self.manifest_sha256,
            "records": sum(self._role_counts.values()),
            "candidate_records": self.candidate_count,
            "role_counts": dict(self._role_counts),
        }
        query_block = {
            "input_form": input_form,
            "parameters": {field: normalized[field] for field in PARAMETER_ORDER},
            "units": {"length": "mm", "second_screw": "1 (dimensionless)"},
            "query_status": query_status,
            "schema_check": schema_check,
        }
        return RetrievalResult(
            manifest=manifest_block,
            family_id=self.family_id,
            query=query_block,
            candidate_roles=self.candidate_roles,
            top_k=resolved_top_k,
            candidates_considered=self.candidate_count,
            results=tuple(entries),
            notes=tuple(notes),
        )
