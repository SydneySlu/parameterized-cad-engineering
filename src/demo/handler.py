"""Demo run handler: manual parameters → real local STEP (APP-003-C1, ADR-0022).

Design constraints:
- No LLM calls, no network requests, no .env reads.
- Reuses run_pipeline, validate_parameters, build_ir_from_schema_payload, compile_ir.
- Each run uses a new UUID and an isolated directory under work/demo-runs/.
- Only successful runs expose STEP for download.
- Download requests validated against in-memory registry (no disk scan).
- Failed runs never expose STEP from prior runs.
- Path traversal and symlink escapes rejected at download time.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Catalog constants (imported, not duplicated)
# ---------------------------------------------------------------------------
from schema.set_screw_shaft_collar import CATALOG_ROWS, SCHEMA_VERSION, FAMILY_ID
from llm.contract import CONTRACT_VERSION, PROMPT_VERSION

# Valid bore_d values from the GN 705 catalog
CATALOG_BORE_VALUES: tuple[int, ...] = tuple(row[0] for row in CATALOG_ROWS)

# Full catalog table as dict: bore_d → {outer_d, screw_d, screw_len, width}
CATALOG_TABLE: dict[int, dict[str, int]] = {
    row[0]: {"bore_d": row[0], "outer_d": row[1], "screw_d": row[2],
             "screw_len": row[3], "width": row[4]}
    for row in CATALOG_ROWS
}

# Catalog table as JSON-safe list for embedding in HTML
CATALOG_TABLE_JS: list[dict[str, int]] = [
    {"bore_d": row[0], "outer_d": row[1], "screw_d": row[2],
     "screw_len": row[3], "width": row[4],
     "second_screw": 1 if row[0] > 70 else 0}
    for row in CATALOG_ROWS
]


def _parse_bore_d(value: Any) -> int:
    """Parse an integer bore value without silently truncating decimals.

    JSON form submissions normally provide an integer or an integer string.
    Integral floats are accepted for compatibility with callers that decode
    numeric JSON as ``float``; non-integral values and booleans are rejected.
    """
    if isinstance(value, bool):
        raise ValueError("bore_d must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError("bore_d must be an integer; decimal values are not allowed")
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)
        raise ValueError("bore_d must be an integer; decimal values are not allowed")
    raise ValueError("bore_d must be an integer")

# Output root for demo runs (git-ignored via work/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEMO_OUTPUT_ROOT: Path = _REPO_ROOT / "work" / "demo-runs"

# UUID v4 pattern for validating run_id from URL
_UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DemoRunResult:
    """Result of one demo run."""

    run_id: str
    status: str           # success | ask | blocked | failed | error | invalid_input
    stage: str            # pipeline stage at which status was determined
    errors: list[dict[str, Any]]
    request_text: str
    bore_d_input: int | None          # user-provided bore_d
    parameters: dict[str, Any] | None  # normalized parameter values
    provenance: dict[str, str] | None  # parameter sources from schema
    ir_document: dict[str, Any] | None # IR document
    validation_summary: dict[str, Any] | None  # geometry/STEP validation details
    step_sha256: str | None            # Only set on success
    step_bytes: int | None             # Only set on success
    _step_path: str | None = dc_field(default=None, repr=False)  # internal only
    _run_dir: str | None = dc_field(default=None, repr=False)    # internal only

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "stage": self.stage,
            "errors": self.errors,
            "request_text": self.request_text,
            "bore_d_input": self.bore_d_input,
            "parameters": self.parameters,
            "provenance": self.provenance,
            "ir_document": self.ir_document,
            "validation_summary": self.validation_summary,
            "step_sha256": self.step_sha256,
            "step_bytes": self.step_bytes,
        }


# ---------------------------------------------------------------------------
# Envelope builder (synthetic, for run_pipeline)
# ---------------------------------------------------------------------------

def _build_demo_envelope(request_text: str, bore_d: int) -> str:
    """Build a synthetic app001-io.v1 envelope from manual user input.

    The envelope uses decision="answer" with only the user-provided bore_d.
    All other parameters are derived by the schema layer from bore_d.
    source="user_input" is a valid EVIDENCE_SOURCE_VALUES entry.
    extraction_source is set to envelope_fixture_label="demo_manual_input"
    via run_pipeline's parameter (the EXTRACTION_SOURCE constant in pipeline.py
    is "synthetic_fixture" but that is an internal tracking label, not shown
    to the user; the UI overrides the display label).
    """
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": "answer",
        "extracted_parameters": {
            "bore_d": bore_d,
        },
        "unsupported_requests": [],
        "evidence": [
            {
                "field": "bore_d",
                "quote": str(bore_d),
                "source": "user_input",
            }
        ],
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    return json.dumps(envelope, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Evidence reader (reads pipeline-saved files from run_dir)
# ---------------------------------------------------------------------------

def _read_run_evidence(run_dir: Path) -> dict[str, Any]:
    """Read additional evidence files saved by run_pipeline."""
    evidence: dict[str, Any] = {}

    # Schema result → provenance + normalized params
    schema_path = run_dir / "schema_result.json"
    if schema_path.is_file():
        try:
            schema_data = json.loads(schema_path.read_text("utf-8"))
            evidence["provenance"] = schema_data.get("provenance") or {}
            evidence["normalized"] = schema_data.get("normalized") or {}
        except Exception:
            pass

    # IR document
    ir_path = run_dir / "input_ir.json"
    if ir_path.is_file():
        try:
            evidence["ir_document"] = json.loads(ir_path.read_text("utf-8"))
        except Exception:
            pass

    # Compilation result → validation summary
    # native_geometry uses: "solids", "faces", "edges", "vertices" (not *_count)
    # STEP readback pass lives at manifest["step_readback"]["comparison"]["pass"]
    comp_path = run_dir / "compilation_result.json"
    if comp_path.is_file():
        try:
            comp_data = json.loads(comp_path.read_text("utf-8"))
            manifest = comp_data.get("manifest") or {}
            native_geo = manifest.get("native_geometry") or {}
            step_info = manifest.get("step") or {}
            step_readback = manifest.get("step_readback") or {}
            readback_comparison = step_readback.get("comparison") or {}
            evidence["validation_summary"] = {
                "solid_count": native_geo.get("solids"),
                "is_valid": native_geo.get("is_valid"),
                "volume_mm3": native_geo.get("volume_mm3"),
                "face_count": native_geo.get("faces"),
                "edge_count": native_geo.get("edges"),
                "vertex_count": native_geo.get("vertices"),
                "step_bytes": step_info.get("bytes"),
                "step_sha256": step_info.get("sha256"),
                "readback_pass": readback_comparison.get("pass"),
            }
        except Exception:
            pass

    return evidence


# ---------------------------------------------------------------------------
# DemoHandler
# ---------------------------------------------------------------------------

class DemoHandler:
    """Thread-unsafe single-process demo run handler.

    Maintains an in-memory registry of runs keyed by run_id.
    Thread safety is not required: the demo server is single-threaded.
    """

    def __init__(self, output_root: Path | None = None) -> None:
        self._output_root = Path(output_root) if output_root else DEFAULT_DEMO_OUTPUT_ROOT
        self._registry: dict[str, DemoRunResult] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, request_text: str, bore_d_raw: Any) -> DemoRunResult:
        """Run the demo pipeline with manually provided bore_d.

        Parameters
        ----------
        request_text:
            Free-text requirement (provenance / traceability). Not parsed.
        bore_d_raw:
            bore_d value from the form. Must be convertible to int and
            present in CATALOG_BORE_VALUES.
        """
        # --- Input validation (before any CAD call) ---
        try:
            bore_d = _parse_bore_d(bore_d_raw)
        except (TypeError, ValueError):
            rid = str(uuid.uuid4())
            result = DemoRunResult(
                run_id=rid,
                status="invalid_input",
                stage="input_validation",
                errors=[{
                    "code": "BORE_TYPE_ERROR",
                    "message": f"bore_d must be an integer, got: {bore_d_raw!r}",
                    "fields": ["bore_d"],
                }],
                request_text=request_text,
                bore_d_input=None,
                parameters=None,
                provenance=None,
                ir_document=None,
                validation_summary=None,
                step_sha256=None,
                step_bytes=None,
            )
            self._registry[rid] = result
            return result

        if bore_d not in CATALOG_BORE_VALUES:
            rid = str(uuid.uuid4())
            result = DemoRunResult(
                run_id=rid,
                status="invalid_input",
                stage="input_validation",
                errors=[{
                    "code": "BORE_NOT_IN_CATALOG",
                    "message": (
                        f"bore_d={bore_d} is not a valid GN 705 catalog value. "
                        f"Valid values: {sorted(CATALOG_BORE_VALUES)}"
                    ),
                    "fields": ["bore_d"],
                }],
                request_text=request_text,
                bore_d_input=bore_d,
                parameters=None,
                provenance=None,
                ir_document=None,
                validation_summary=None,
                step_sha256=None,
                step_bytes=None,
            )
            self._registry[rid] = result
            return result

        # --- Build synthetic envelope and call run_pipeline ---
        from integration.pipeline import run_pipeline

        envelope_json = _build_demo_envelope(request_text, bore_d)
        pipeline_result = run_pipeline(
            request_text,
            envelope_json,
            output_root=self._output_root,
            envelope_fixture_label="demo_manual_input",
        )

        # --- Read additional evidence from saved files ---
        run_dir = Path(pipeline_result.run_dir) if pipeline_result.run_dir else None
        evidence: dict[str, Any] = {}
        if run_dir and run_dir.is_dir():
            evidence = _read_run_evidence(run_dir)

        # --- Build DemoRunResult ---
        step_sha256: str | None = None
        step_bytes_val: int | None = None
        if pipeline_result.status == "success" and pipeline_result.ir_index:
            step_sha256 = pipeline_result.ir_index.get("step_sha256")
            step_bytes_val = pipeline_result.ir_index.get("step_bytes")

        result = DemoRunResult(
            run_id=pipeline_result.run_id,
            status=pipeline_result.status,
            stage=pipeline_result.stage,
            errors=pipeline_result.errors,
            request_text=request_text,
            bore_d_input=bore_d,
            parameters=evidence.get("normalized") or pipeline_result.parameters,
            provenance=evidence.get("provenance"),
            ir_document=evidence.get("ir_document"),
            validation_summary=evidence.get("validation_summary"),
            step_sha256=step_sha256,
            step_bytes=step_bytes_val,
            _step_path=pipeline_result.step_path,
            _run_dir=pipeline_result.run_dir,
        )
        self._registry[pipeline_result.run_id] = result
        return result

    def get_run(self, run_id: str) -> DemoRunResult | None:
        """Return a run by ID, or None if not found."""
        return self._registry.get(run_id)

    def get_step_bytes_secure(self, run_id: str) -> bytes | None:
        """Return STEP file bytes for a successful run, or None on any failure.

        Security checks performed:
        1. run_id must be in the in-memory registry (not disk scan).
        2. Run must have status="success".
        3. STEP path must resolve inside the run's cad_output/ directory.
        4. No symlink escapes.
        5. File must exist and be non-empty.
        6. Content SHA-256 must match the stored hash.
        """
        result = self._registry.get(run_id)
        if result is None:
            return None
        if result.status != "success":
            return None

        step_path_str = result._step_path
        run_dir_str = result._run_dir
        expected_sha256 = result.step_sha256

        if not step_path_str or not run_dir_str or not expected_sha256:
            return None

        step_path = Path(step_path_str)
        expected_prefix = Path(run_dir_str) / "cad_output"

        # Canonical containment check
        try:
            canonical_step = step_path.resolve()
            canonical_prefix = expected_prefix.resolve()
            canonical_step.relative_to(canonical_prefix)
        except (ValueError, OSError):
            return None

        # Reject symlinks
        if canonical_step.is_symlink():
            return None

        # File must exist and be non-empty
        if not canonical_step.is_file():
            return None
        if canonical_step.stat().st_size == 0:
            return None

        # Content hash must match stored hash
        content = canonical_step.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_sha256:
            return None

        return content

    def is_valid_run_id(self, run_id: str) -> bool:
        """Return True iff run_id matches the UUID v4 pattern."""
        return bool(_UUID_PATTERN.match(run_id))
