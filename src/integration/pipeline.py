"""Unified offline CAD pipeline: synthetic envelope → real local STEP.

Accepts a requirement text and a path to a synthetic v5 fixture envelope,
runs the full parse → gate → Schema → IR → CAD chain, isolates each run in
its own UUID directory under ``work/integration-runs/``, and writes evidence
files for every stage.

A1 boundary
-----------
- extraction_source is always ``"synthetic_fixture"``.
- No real model calls, no network requests, no .env / key reads.
- Failure at any stage produces a detailed error record and an empty step_path.
- Previous runs are never searched for STEP files; every new run is independent.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm.parser import parse_response
from llm.projector import project_to_cad003
from schema.set_screw_shaft_collar import validate_parameters
from integration.schema_to_ir import build_ir_from_schema_payload

# compile_ir is imported at module level so it can be mocked in tests.
# The cadquery runtime may not be available (e.g. in CI without CAD env);
# in that case the import still succeeds (it only needs jsonschema), but
# actual compilation will fail at build time with CAD_RUNTIME_UNAVAILABLE.
try:
    from cad_compilation import compile_ir as _compile_ir
except ImportError:
    _compile_ir = None


def compile_ir(raw, *, output_dir=None):
    """Delegate to cad_compilation.compile_ir, with a guard for missing runtime."""
    if _compile_ir is None:
        raise ImportError("cad_compilation is not available")
    return _compile_ir(raw, output_dir=output_dir)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXTRACTION_SOURCE: str = "synthetic_fixture"
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_ROOT: Path = _REPO_ROOT / "work" / "integration-runs"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """The complete result of one pipeline run.

    ``status`` vocabulary
    ---------------------
    success  – compiler.ok=True, status=step_readback, STEP file verified.
    ask      – model/fixture said ask; questions returned.
    refuse   – model/fixture said refuse; no STEP.
    blocked  – gate blocked (missing_fields, unsupported, schema reject, …).
    failed   – CAD compilation or STEP export/readback failed.
    error    – internal pipeline error (bad envelope, parse failure, …).
    """

    run_id: str
    extraction_source: str
    status: str
    stage: str
    errors: list[dict[str, Any]]
    questions: list[str]
    request_text: str
    envelope_fixture_label: str
    parameters: dict[str, Any] | None
    ir_index: dict[str, Any] | None
    step_path: str | None          # only set on status==success
    run_dir: str | None            # git-ignored run directory (diagnostics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "extraction_source": self.extraction_source,
            "status": self.status,
            "stage": self.stage,
            "errors": self.errors,
            "questions": self.questions,
            "request_text": self.request_text,
            "envelope_fixture_label": self.envelope_fixture_label,
            "parameters": self.parameters,
            "ir_index": self.ir_index,
            "step_path": self.step_path,
            "run_dir": self.run_dir,
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_pipeline(
    request_text: str,
    raw_envelope: str | bytes,
    *,
    output_root: str | os.PathLike[str] | None = None,
    envelope_fixture_label: str = "synthetic_fixture",
    run_id: str | None = None,
) -> PipelineResult:
    """Run the full offline pipeline for one synthetic envelope.

    Parameters
    ----------
    request_text:
        The natural language requirement text (provenance / traceability).
        Not parsed further in A1; passed through to the run record.
    raw_envelope:
        The raw synthetic v5 envelope as JSON string or bytes.
        Must satisfy the frozen ``app001-io.v1`` contract.
    output_root:
        Root directory for run directories.  Defaults to
        ``work/integration-runs/`` (git-ignored).
    envelope_fixture_label:
        A short label identifying the fixture source (e.g. a fixture filename).
        A1 always sets extraction_source="synthetic_fixture" in the result.
    run_id:
        Override the auto-generated UUID (useful for tests that need
        deterministic directory names).  Must not already exist under
        output_root; raises ValueError if it does.

    Returns
    -------
    PipelineResult
        status=success  → step_path is set; ir_index contains all hashes.
        status≠success  → step_path is None; errors/questions explain the
                          blocking condition.
    """
    out_root = Path(output_root) if output_root is not None else _DEFAULT_OUTPUT_ROOT

    # Assign run ID.
    rid = run_id if run_id is not None else str(uuid.uuid4())
    run_dir = _atomic_create_run_dir(out_root, rid)

    return _execute(
        request_text=request_text,
        raw_envelope=raw_envelope,
        envelope_fixture_label=envelope_fixture_label,
        run_id=rid,
        run_dir=run_dir,
    )


# ---------------------------------------------------------------------------
# Internal pipeline
# ---------------------------------------------------------------------------


def _execute(
    *,
    request_text: str,
    raw_envelope: str | bytes,
    envelope_fixture_label: str,
    run_id: str,
    run_dir: Path,
) -> PipelineResult:
    """Full pipeline execution inside the run directory."""

    def _fail(status: str, stage: str, errors: list[dict[str, Any]],
              questions: list[str] | None = None) -> PipelineResult:
        _write_json(run_dir / "summary.json", {
            "run_id": run_id,
            "status": status,
            "stage": stage,
            "errors": errors,
            "questions": questions or [],
        })
        return PipelineResult(
            run_id=run_id,
            extraction_source=EXTRACTION_SOURCE,
            status=status,
            stage=stage,
            errors=errors,
            questions=questions or [],
            request_text=request_text,
            envelope_fixture_label=envelope_fixture_label,
            parameters=None,
            ir_index=None,
            step_path=None,
            run_dir=str(run_dir),
        )

    # Save input evidence.
    envelope_bytes = (
        raw_envelope.encode("utf-8")
        if isinstance(raw_envelope, str)
        else raw_envelope
    )
    envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
    _write_json(run_dir / "input.json", {
        "run_id": run_id,
        "extraction_source": EXTRACTION_SOURCE,
        "request_text": request_text,
        "envelope_fixture_label": envelope_fixture_label,
        "envelope_sha256": envelope_hash,
    })
    _write_bytes(run_dir / "envelope.json", envelope_bytes)

    # ------------------------------------------------------------------ #
    # Stage 1: parse
    # ------------------------------------------------------------------ #
    parse_result = parse_response(raw_envelope)
    if not parse_result.ok:
        stage_errors = [e.as_dict() for e in parse_result.errors]
        return _fail("error", "parse", stage_errors)

    envelope = parse_result.envelope
    assert envelope is not None  # guaranteed when ok=True

    # ------------------------------------------------------------------ #
    # Stage 2: construction gate
    #   Checks decision, missing_fields, unsupported_requests, and
    #   then projection + Schema.  All five conditions must pass.
    # ------------------------------------------------------------------ #

    # 2a. Decision must be "answer".
    if envelope.decision == "ask":
        return _fail("ask", "gate",
                     [{"code": "GATE_DECISION_ASK",
                       "message": f"decision=ask; model requested clarification"}],
                     list(envelope.questions))

    if envelope.decision != "answer":
        return _fail("refuse", "gate",
                     [{"code": "GATE_DECISION_REFUSE",
                       "message": f"decision={envelope.decision!r}; construction blocked"}])

    # 2b. missing_fields must be empty.
    if envelope.missing_fields:
        return _fail("blocked", "gate",
                     [{"code": "GATE_MISSING_FIELDS",
                       "fields": list(envelope.missing_fields),
                       "message": f"missing_fields is not empty: {envelope.missing_fields}"}])

    # 2c. unsupported_requests must be empty.
    if envelope.unsupported_requests:
        return _fail("blocked", "gate",
                     [{"code": "GATE_UNSUPPORTED_REQUESTS",
                       "fields": list(envelope.unsupported_requests),
                       "message": f"unsupported_requests is not empty: {envelope.unsupported_requests}"}])

    # 2d. Project to CAD-003.
    projection = project_to_cad003(envelope.extracted_parameters)
    if not projection.ok:
        return _fail("blocked", "projection",
                     list(projection.errors))

    projected_payload = projection.projected_payload
    assert projected_payload is not None  # guaranteed when ok=True

    # 2e. Schema validation (re-run with raw projected payload).
    schema_result = validate_parameters(projected_payload)
    if not schema_result.ok:
        return _fail("blocked", "schema",
                     [e.as_dict() for e in schema_result.errors])

    # Save Schema evidence.
    _write_json(run_dir / "schema_result.json", {
        "projected_payload": projected_payload,
        "validation_ok": schema_result.ok,
        "schema_version": schema_result.schema_version,
        "normalized": schema_result.normalized,
        "provenance": dict(schema_result.provenance),
        "errors": [],
    })

    # ------------------------------------------------------------------ #
    # Stage 3: Schema → IR adapter
    # ------------------------------------------------------------------ #
    adapter_result = build_ir_from_schema_payload(projected_payload)

    if adapter_result.status != "accepted":
        return _fail("failed" if adapter_result.status == "ir_invalid" else "blocked",
                     adapter_result.stage,
                     adapter_result.errors)

    ir_json_str = adapter_result.ir_json
    assert ir_json_str is not None
    ir_bytes = ir_json_str.encode("utf-8")
    ir_hash = hashlib.sha256(ir_bytes).hexdigest()

    input_ir_path = run_dir / "input_ir.json"
    _write_bytes(input_ir_path, ir_bytes)

    # ------------------------------------------------------------------ #
    # Stage 4: compile_ir (real local CAD/STEP)
    # ------------------------------------------------------------------ #
    cad_output_dir = run_dir / "cad_output"
    cad_output_dir.mkdir(exist_ok=True)

    try:
        compilation = compile_ir(ir_bytes, output_dir=cad_output_dir)
    except ImportError as exc:
        return _fail("failed", "cad_import",
                     [{"code": "CAD_RUNTIME_UNAVAILABLE",
                       "message": f"Cannot import cad_compilation: {exc}"}])

    # Save compilation result.
    _write_json(run_dir / "compilation_result.json", compilation.as_dict())

    if not compilation.ok or compilation.status != "step_readback":
        stage = compilation.status if compilation.status else "cad"
        errors = compilation.errors if compilation.errors else [
            {"code": "CAD_FAILED", "stage": stage, "message": "compilation not ok"}
        ]
        return _fail("failed", stage, errors)

    # ------------------------------------------------------------------ #
    # Stage 5: Verify STEP file integrity — fail closed on every condition.
    #
    # All six conditions MUST pass to publish step_path:
    #  1. compilation.ok=True and status=step_readback  (checked in stage 4)
    #  2. STEP canonical path is inside this run's cad_output/ directory
    #  3. compilation.manifest, manifest["input_ir_sha256"], and
    #     manifest["step"]["sha256"] all exist and are non-empty strings
    #  4. manifest["input_ir_sha256"] matches the IR bytes sent to the compiler
    #  5. manifest["step"]["sha256"] matches the actual STEP file content hash
    #  6. STEP file exists and is non-empty
    #
    # Any condition that fails → status=failed, step_path=None, ir_index=None.
    # We never copy, move, or delete external files.
    # ------------------------------------------------------------------ #

    # --- Condition 1: already checked above (ok=True, status=step_readback) ---

    # --- Condition 3a: manifest must be a non-None dict ---
    manifest = compilation.manifest
    if not isinstance(manifest, dict):
        return _fail("failed", "step_readback",
                     [{"code": "MANIFEST_MISSING",
                       "message": "compiler returned no manifest (None or non-dict); "
                                  "cannot verify STEP provenance"}])

    # --- Condition 3b: manifest["input_ir_sha256"] must be a non-empty string ---
    manifest_ir_hash = manifest.get("input_ir_sha256")
    if not isinstance(manifest_ir_hash, str) or not manifest_ir_hash:
        return _fail("failed", "step_readback",
                     [{"code": "MANIFEST_INPUT_IR_SHA256_MISSING",
                       "message": "manifest is missing or has empty input_ir_sha256; "
                                  "cannot verify IR provenance"}])

    # --- Condition 4: manifest["input_ir_sha256"] must match THIS run's IR hash ---
    if manifest_ir_hash != ir_hash:
        return _fail("failed", "step_readback",
                     [{"code": "INPUT_IR_HASH_MISMATCH",
                       "message": "manifest.input_ir_sha256 does not match the IR "
                                  "bytes sent to compile_ir in this run",
                       "manifest_hash": manifest_ir_hash,
                       "actual_ir_hash": ir_hash}])

    # --- Condition 3c: manifest["step"]["sha256"] must be a non-empty string ---
    manifest_step = manifest.get("step")
    if not isinstance(manifest_step, dict):
        return _fail("failed", "step_readback",
                     [{"code": "MANIFEST_STEP_MISSING",
                       "message": "manifest is missing the 'step' sub-dict; "
                                  "cannot verify STEP hash"}])
    manifest_step_hash = manifest_step.get("sha256")
    if not isinstance(manifest_step_hash, str) or not manifest_step_hash:
        return _fail("failed", "step_readback",
                     [{"code": "MANIFEST_STEP_SHA256_MISSING",
                       "message": "manifest.step.sha256 is missing or empty; "
                                  "cannot verify STEP content"}])

    # --- Condition 2: STEP path must be a non-empty string first ---
    step_path_str = compilation.step_path
    if not step_path_str:
        return _fail("failed", "step_readback",
                     [{"code": "CAD_STEP_PATH_MISSING",
                       "message": "step_path not returned by compiler"}])

    # Resolve canonical paths.  Symlinks that escape the run directory are
    # rejected; we do not follow them to external locations.
    try:
        canonical_cad_output = cad_output_dir.resolve()
    except OSError:
        canonical_cad_output = cad_output_dir.absolute()

    step_path_unresolved = Path(step_path_str)
    try:
        canonical_step_path = step_path_unresolved.resolve()
    except OSError:
        canonical_step_path = step_path_unresolved.absolute()

    try:
        canonical_step_path.relative_to(canonical_cad_output)
    except ValueError:
        return _fail("failed", "step_readback",
                     [{"code": "STEP_PATH_OUTSIDE_RUN_DIR",
                       "message": "STEP path resolves outside this run's cad_output/ "
                                  "directory; refusing to publish an external STEP file",
                       "step_path": str(step_path_str),
                       "expected_root": str(canonical_cad_output)}])

    # --- Condition 6: file must exist and be non-empty ---
    if not canonical_step_path.is_file() or canonical_step_path.stat().st_size == 0:
        return _fail("failed", "step_readback",
                     [{"code": "CAD_STEP_FILE_EMPTY",
                       "message": "STEP file missing or empty after compilation"}])

    # --- Condition 5: actual STEP content hash must match manifest ---
    step_hash = hashlib.sha256(canonical_step_path.read_bytes()).hexdigest()
    if step_hash != manifest_step_hash:
        return _fail("failed", "step_readback",
                     [{"code": "STEP_HASH_MISMATCH",
                       "message": "STEP file content hash does not match manifest.step.sha256",
                       "manifest_hash": manifest_step_hash,
                       "actual_hash": step_hash}])

    # All six conditions passed.
    step_path = canonical_step_path

    # Compute result IR hash for the index (informational; not a gate).
    result_ir = compilation.ir
    result_ir_bytes = json.dumps(result_ir, ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8") if result_ir else b""
    result_ir_hash = hashlib.sha256(result_ir_bytes).hexdigest()

    # Build the index.
    ir_index = {
        "run_id": run_id,
        "envelope_sha256": envelope_hash,
        "input_ir_sha256": ir_hash,
        "result_ir_sha256": result_ir_hash,
        "step_sha256": step_hash,
        "step_bytes": step_path.stat().st_size,
        "step_path": str(step_path),
        "compiler_manifest_input_ir_sha256": manifest.get("input_ir_sha256", ""),
    }

    _write_json(run_dir / "index.json", {
        "run_id": run_id,
        "extraction_source": EXTRACTION_SOURCE,
        "request_text": request_text,
        "envelope_fixture_label": envelope_fixture_label,
        **ir_index,
        "schema_version": schema_result.schema_version,
        "normalized_parameters": schema_result.normalized,
        "provenance": dict(schema_result.provenance),
    })

    _write_json(run_dir / "summary.json", {
        "run_id": run_id,
        "status": "success",
        "stage": "step_readback",
        "errors": [],
    })

    return PipelineResult(
        run_id=run_id,
        extraction_source=EXTRACTION_SOURCE,
        status="success",
        stage="step_readback",
        errors=[],
        questions=[],
        request_text=request_text,
        envelope_fixture_label=envelope_fixture_label,
        parameters=schema_result.normalized,
        ir_index=ir_index,
        step_path=str(step_path),
        run_dir=str(run_dir),
    )


# ---------------------------------------------------------------------------
# Run directory isolation
# ---------------------------------------------------------------------------


def _atomic_create_run_dir(output_root: Path, run_id: str) -> Path:
    """Create a new, exclusive run directory.  Raises ValueError if it exists.

    Does not use O_EXCL (not portable across all filesystems); instead uses
    mkdir with exist_ok=False on the leaf directory, which is atomic on
    POSIX for local filesystems.

    Also rejects path traversal and containment escapes.
    """
    # Sanitize run_id: only alphanumeric, hyphens, and underscores.
    safe_chars = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789-_"
    )
    if not run_id or any(c not in safe_chars for c in run_id):
        raise ValueError(
            f"run_id must contain only [a-zA-Z0-9_-], got: {run_id!r}"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    canonical_root = output_root.resolve()

    run_dir = output_root / run_id
    # Canonical containment check before mkdir.
    try:
        candidate = (output_root / run_id).resolve()
    except OSError:
        candidate = (output_root / run_id).absolute()
    try:
        candidate.relative_to(canonical_root)
    except ValueError:
        raise ValueError(
            f"run_id {run_id!r} resolves outside the output root "
            f"{canonical_root}; refusing to create run directory"
        )

    try:
        run_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        raise ValueError(
            f"Run directory already exists: {run_dir}. "
            "Each run must use a unique run_id."
        )

    return run_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)
