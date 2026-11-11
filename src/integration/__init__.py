"""Integration layer: synthetic v5 envelope → real local CAD/STEP.

This package connects the frozen v5 extraction contract to the existing
Schema → IR → CAD compilation pipeline via a strict construction gate and
a formal Schema→IR adapter.  It does not call real models or network services.
"""

from .schema_to_ir import ADAPTER_VERSION, AdapterResult, build_ir_from_schema_payload
from .pipeline import PipelineResult, run_pipeline

__all__ = [
    "ADAPTER_VERSION",
    "AdapterResult",
    "build_ir_from_schema_payload",
    "PipelineResult",
    "run_pipeline",
]
