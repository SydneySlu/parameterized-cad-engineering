"""RET-002 deterministic, explainable single-family retrieval baseline.

Public entry points:

    from retrieval import RetrievalIndex, RetrievalError
    index = RetrievalIndex.from_manifest(manifest_path, {"retrieval_source"})
    result = index.query(family_id="set_screw_shaft_collar", parameters={...}, top_k=3)

Run Python with `PYTHONPATH=src` (the same convention as the other packages).
"""

from .baseline import RetrievalIndex, RetrievalResult
from .config import (
    CONFIG_VERSION,
    CONTINUOUS_FIELDS,
    DEFAULT_CANDIDATE_ROLES,
    DEFAULT_CONFIG_REL_PATH,
    DEFAULT_TOP_K,
    DISCRETE_FIELDS,
    MANIFEST_REL_PATH,
    PARAMETER_ORDER,
    POLICY_ID,
    RETRIEVAL_VERSION,
    SPLIT_STATUS,
    RetrievalConfig,
    catalog_ranges,
)
from .distance import DistancePolicy
from .errors import RetrievalError

__all__ = [
    "CONFIG_VERSION",
    "CONTINUOUS_FIELDS",
    "DEFAULT_CANDIDATE_ROLES",
    "DEFAULT_CONFIG_REL_PATH",
    "DEFAULT_TOP_K",
    "DISCRETE_FIELDS",
    "DistancePolicy",
    "MANIFEST_REL_PATH",
    "PARAMETER_ORDER",
    "POLICY_ID",
    "RETRIEVAL_VERSION",
    "RetrievalConfig",
    "RetrievalError",
    "RetrievalIndex",
    "RetrievalResult",
    "SPLIT_STATUS",
    "catalog_ranges",
]
