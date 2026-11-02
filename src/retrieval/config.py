"""Frozen configuration and policy constants for the RET-002 baseline.

The distance policy is deliberately not learned and not configurable through
free weights.  `retrieval-config.json` restates the frozen ranges and weights
for auditability, but the loader refuses to run if the file disagrees with the
constants below.  Changing ranges or weights requires a new policy id reviewed
by the Codex hub, not a local configuration edit.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from schema.set_screw_shaft_collar import CATALOG_ROWS, FAMILY_ID, SCHEMA_VERSION

from .errors import RetrievalError


RETRIEVAL_VERSION = "ret-002.retrieval.v1"
CONFIG_VERSION = "ret-002.retrieval-config.v1"
POLICY_ID = "RET-002.parametric_distance.v1"
SPLIT_STATUS = "provisional_small_n"

PARAMETER_ORDER: tuple[str, ...] = (
    "bore_d",
    "outer_d",
    "screw_d",
    "screw_len",
    "second_screw",
    "width",
)
CONTINUOUS_FIELDS: tuple[str, ...] = ("bore_d", "outer_d", "screw_d", "screw_len", "width")
DISCRETE_FIELDS: tuple[str, ...] = ("second_screw",)
CATALOG_KEY = "bore_d"

CONTINUOUS_FIELD_WEIGHT = 0.2
DISCRETE_WEIGHT = 0.5
DEFAULT_TOP_K = 3

KNOWN_ROLES: tuple[str, ...] = ("development", "retrieval_source", "heldout_evaluation")
DEFAULT_CANDIDATE_ROLES: tuple[str, ...] = ("retrieval_source",)
DEFAULT_EXCLUDED_ROLES: tuple[str, ...] = ("development", "heldout_evaluation")

MANIFEST_REL_PATH = "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"
DEFAULT_CONFIG_REL_PATH = "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json"
REPO_ROOT = Path(__file__).resolve().parents[2]

_RANGE_INDICES = {"bore_d": 0, "outer_d": 1, "screw_d": 2, "screw_len": 3, "width": 4}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def catalog_ranges() -> dict[str, tuple[float, float]]:
    """Return the full 15-row GN 705 catalog range per continuous field.

    The range comes from the frozen catalog table in `src/schema`, not from the
    selected candidates, so a three-row candidate role still normalizes against
    the whole catalog span.
    """

    ranges: dict[str, tuple[float, float]] = {}
    for field, index in _RANGE_INDICES.items():
        values = [row[index] for row in CATALOG_ROWS]
        ranges[field] = (float(min(values)), float(max(values)))
    return ranges


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def normalize_candidate_roles(value: Any) -> tuple[str, ...]:
    """Validate and canonicalize the explicit candidate role selection."""

    if value is None:
        raise RetrievalError(
            "RETRIEVAL_CANDIDATE_ROLES_REQUIRED",
            "candidate_roles must be supplied explicitly; the baseline assumes no default role",
            stage="config",
        )
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise RetrievalError(
            "RETRIEVAL_INVALID_CANDIDATE_ROLES",
            "candidate_roles must be a collection of role names, not a string or scalar",
            stage="config",
            details={"value": repr(value)[:200]},
        )
    roles: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise RetrievalError(
                "RETRIEVAL_INVALID_CANDIDATE_ROLES",
                "every candidate role must be a string",
                stage="config",
                details={"value": repr(item)[:200]},
            )
        roles.append(item)
    unique = tuple(sorted(set(roles)))
    if not unique:
        raise RetrievalError(
            "RETRIEVAL_EMPTY_CANDIDATE_ROLES",
            "candidate_roles is empty; at least one role must be selected explicitly",
            stage="config",
        )
    return unique


def _config_error(message: str, *, fields: tuple[str, ...] = (), details: Mapping[str, Any] | None = None) -> RetrievalError:
    return RetrievalError("RETRIEVAL_CONFIG_INVALID", message, stage="config", fields=fields, details=details)


@dataclass(frozen=True)
class RetrievalConfig:
    """Validated view of `retrieval-config.json`."""

    manifest_path: str
    manifest_sha256: str
    candidate_roles: tuple[str, ...]
    ranges: tuple[tuple[str, float, float], ...]
    default_top_k: int
    repo_root: Path
    config_path: str | None = None
    config_sha256: str | None = None

    def range_map(self) -> dict[str, tuple[float, float]]:
        return {field: (low, high) for field, low, high in self.ranges}

    def manifest_file(self) -> Path:
        return self.repo_root / self.manifest_path

    def as_report_dict(self) -> dict[str, Any]:
        return {
            "path": self.config_path,
            "sha256": self.config_sha256,
            "config_version": CONFIG_VERSION,
            "retrieval_policy": POLICY_ID,
            "family_id": FAMILY_ID,
            "manifest": {
                "path": self.manifest_path,
                "sha256": self.manifest_sha256,
            },
            "candidate_roles": list(self.candidate_roles),
            "excluded_roles": list(DEFAULT_EXCLUDED_ROLES),
            "split_status_expected": SPLIT_STATUS,
            "normalization_ranges_mm": {
                field: {"min": low, "max": high} for field, low, high in self.ranges
            },
            "weights": {
                "continuous_field_weight": CONTINUOUS_FIELD_WEIGHT,
                "discrete_second_screw": DISCRETE_WEIGHT,
                "total_formula": (
                    "mean(5 continuous normalized abs diffs) + "
                    "0.5 * (second_screw mismatch)"
                ),
                "tiebreak": "total ascending, then sample_id ascending",
            },
            "top_k": {"default": self.default_top_k, "min": 1, "max": "candidate_count"},
            "units": {"length": "mm", "second_screw": "1 (dimensionless)"},
        }

    @classmethod
    def from_path(cls, path: str | Path, *, repo_root: str | Path | None = None) -> "RetrievalConfig":
        root = Path(repo_root) if repo_root is not None else REPO_ROOT
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = root / config_path
        if not config_path.is_file():
            raise RetrievalError(
                "RETRIEVAL_CONFIG_NOT_FOUND",
                "retrieval config file does not exist",
                stage="config",
                details={"path": str(config_path)},
            )
        raw = config_path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _config_error(
                f"retrieval config is not valid JSON: {exc}",
                details={"path": str(config_path)},
            ) from exc
        if not isinstance(data, Mapping):
            raise _config_error("retrieval config root must be a JSON object")
        config = cls.from_dict(data, repo_root=root)
        try:
            display_path = config_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            display_path = str(config_path)
        return replace(
            config,
            config_path=display_path,
            config_sha256=sha256_bytes(raw),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, repo_root: str | Path | None = None) -> "RetrievalConfig":
        if not isinstance(data, Mapping):
            raise _config_error("retrieval config root must be a JSON object")
        root = Path(repo_root) if repo_root is not None else REPO_ROOT

        if data.get("config_version") != CONFIG_VERSION:
            raise _config_error(
                "config_version must match the frozen retrieval config contract",
                fields=("config_version",),
                details={"expected": CONFIG_VERSION, "observed": data.get("config_version")},
            )
        if data.get("retrieval_policy") != POLICY_ID:
            raise _config_error(
                "retrieval_policy must match the frozen distance policy",
                fields=("retrieval_policy",),
                details={"expected": POLICY_ID, "observed": data.get("retrieval_policy")},
            )
        if data.get("family_id") != FAMILY_ID:
            raise _config_error(
                "retrieval config family_id must be the frozen first family",
                fields=("family_id",),
                details={"expected": FAMILY_ID, "observed": data.get("family_id")},
            )
        if data.get("split_status_expected") not in (None, SPLIT_STATUS):
            raise _config_error(
                "split_status_expected must stay provisional_small_n; a frozen benchmark split requires a new decision",
                fields=("split_status_expected",),
                details={"expected": SPLIT_STATUS, "observed": data.get("split_status_expected")},
            )

        manifest = data.get("manifest")
        if not isinstance(manifest, Mapping):
            raise _config_error("manifest block is required", fields=("manifest",))
        manifest_path = manifest.get("path")
        if manifest_path != MANIFEST_REL_PATH:
            raise _config_error(
                "manifest.path must be the frozen RET-001 single-family manifest",
                fields=("manifest.path",),
                details={"expected": MANIFEST_REL_PATH, "observed": manifest_path},
            )
        manifest_sha = manifest.get("sha256")
        if not isinstance(manifest_sha, str) or not _SHA256_RE.match(manifest_sha):
            raise _config_error(
                "manifest.sha256 must be a lowercase 64-hex digest",
                fields=("manifest.sha256",),
                details={"observed": manifest_sha},
            )
        manifest_file = root / MANIFEST_REL_PATH
        if not manifest_file.is_file():
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_NOT_FOUND",
                "the RET-001 manifest referenced by the config does not exist",
                stage="config",
                details={"path": str(manifest_file)},
            )
        actual_sha = sha256_file(manifest_file)
        if actual_sha != manifest_sha:
            raise RetrievalError(
                "RETRIEVAL_MANIFEST_HASH_MISMATCH",
                "manifest sha256 differs from the value recorded in retrieval-config.json",
                stage="config",
                fields=("manifest.sha256",),
                details={"expected": manifest_sha, "actual": actual_sha},
            )

        roles = normalize_candidate_roles(data.get("candidate_roles"))
        unknown_roles = [role for role in roles if role not in KNOWN_ROLES]
        if unknown_roles:
            raise _config_error(
                "candidate_roles contains an unknown split role",
                fields=("candidate_roles",),
                details={"unknown": unknown_roles, "known": list(KNOWN_ROLES)},
            )

        raw_ranges = data.get("normalization_ranges_mm")
        if not isinstance(raw_ranges, Mapping):
            raise _config_error("normalization_ranges_mm block is required", fields=("normalization_ranges_mm",))
        if set(raw_ranges) != set(CONTINUOUS_FIELDS):
            raise _config_error(
                "normalization_ranges_mm must cover exactly the five continuous fields",
                fields=("normalization_ranges_mm",),
                details={"expected": list(CONTINUOUS_FIELDS), "observed": sorted(raw_ranges)},
            )
        expected_ranges = catalog_ranges()
        ranges: list[tuple[str, float, float]] = []
        for field in CONTINUOUS_FIELDS:
            entry = raw_ranges[field]
            if isinstance(entry, Mapping):
                low, high = entry.get("min"), entry.get("max")
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                low, high = entry[0], entry[1]
            else:
                raise _config_error(
                    "each normalization range must be {min, max} or a two-item array",
                    fields=(f"normalization_ranges_mm.{field}",),
                )
            if not _is_finite_number(low) or not _is_finite_number(high) or not float(high) > float(low):
                raise _config_error(
                    "normalization range must be finite with min < max",
                    fields=(f"normalization_ranges_mm.{field}",),
                    details={"min": repr(low), "max": repr(high)},
                )
            expected_low, expected_high = expected_ranges[field]
            if float(low) != expected_low or float(high) != expected_high:
                raise _config_error(
                    "normalization range differs from the frozen 15-row catalog range",
                    fields=(f"normalization_ranges_mm.{field}",),
                    details={
                        "expected": [expected_low, expected_high],
                        "observed": [float(low), float(high)],
                    },
                )
            ranges.append((field, float(low), float(high)))

        weights = data.get("weights")
        if not isinstance(weights, Mapping):
            raise _config_error("weights block is required", fields=("weights",))
        if weights.get("continuous_field_weight") != CONTINUOUS_FIELD_WEIGHT:
            raise _config_error(
                "continuous field weight is frozen at 0.2; changing it requires a new policy id and Codex review",
                fields=("weights.continuous_field_weight",),
                details={"expected": CONTINUOUS_FIELD_WEIGHT, "observed": weights.get("continuous_field_weight")},
            )
        if weights.get("discrete_second_screw") != DISCRETE_WEIGHT:
            raise _config_error(
                "second_screw discrete weight is frozen at 0.5; changing it requires a new policy id and Codex review",
                fields=("weights.discrete_second_screw",),
                details={"expected": DISCRETE_WEIGHT, "observed": weights.get("discrete_second_screw")},
            )

        top_k = data.get("top_k")
        if not isinstance(top_k, Mapping):
            raise _config_error("top_k block is required", fields=("top_k",))
        default_top_k = top_k.get("default")
        if isinstance(default_top_k, bool) or not isinstance(default_top_k, int) or default_top_k < 1:
            raise _config_error(
                "top_k.default must be a positive integer",
                fields=("top_k.default",),
                details={"observed": repr(default_top_k)},
            )

        return cls(
            manifest_path=MANIFEST_REL_PATH,
            manifest_sha256=manifest_sha,
            candidate_roles=roles,
            ranges=tuple(ranges),
            default_top_k=default_top_k,
            repo_root=root,
        )
