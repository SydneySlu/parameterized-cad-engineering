"""APP-003-C2: Offline natural-language product flow (ADR-0023).

Design constraints:
- No LLM calls, no network requests, no .env reads.
- create_product_run: parse + project + Schema preflight only; zero compile_ir calls.
- confirm_product_run: creates a child run, calls run_pipeline on it.
- Each run has a UUID; child runs carry parent_run_id.
- confirmation_revision mismatch → blocked (STALE_REVISION).
- Failed/blocked runs never expose STEP from prior runs.
- Download reuses same 6-layer security as C1 DemoHandler.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

from llm.contract import CONTRACT_VERSION, PROMPT_VERSION, EXTRACTABLE_FIELDS

# ---------------------------------------------------------------------------
# Product status constants (ADR-0023 state machine)
# ---------------------------------------------------------------------------
PRODUCT_STATUS_REQUEST_RECEIVED = "request_received"
PRODUCT_STATUS_EXTRACTION_PENDING = "extraction_pending"
PRODUCT_STATUS_NEEDS_CONFIRMATION = "needs_confirmation"
PRODUCT_STATUS_BLOCKED = "blocked"
PRODUCT_STATUS_CONSTRUCTING = "constructing"
PRODUCT_STATUS_SUCCEEDED = "succeeded"
PRODUCT_STATUS_FAILED = "failed"

# ---------------------------------------------------------------------------
# Fixture registry: fixture_id → repo-relative path
# ---------------------------------------------------------------------------
_FIXTURE_REGISTRY: dict[str, str] = {
    "c2-answer-bore24": "tests/demo/fixtures/c2-answer-bore24.json",
    "c2-ask-missing-bore": "tests/demo/fixtures/c2-ask-missing-bore.json",
    "c2-answer-catalog-conflict": "tests/demo/fixtures/c2-answer-catalog-conflict.json",
    "c2-answer-unsupported": "tests/demo/fixtures/c2-answer-unsupported.json",
    "c2-ask-extra-question": "tests/demo/fixtures/c2-ask-extra-question.json",
    "c2-refuse": "tests/demo/fixtures/c2-refuse.json",
    "c2-answer-schema-fail": "tests/demo/fixtures/c2-answer-schema-fail.json",
    "c2-answer-bore80": "tests/demo/fixtures/c2-answer-bore80.json",
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C2_OUTPUT_ROOT: Path = _REPO_ROOT / "work" / "product-flow-runs"
_UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)


# ---------------------------------------------------------------------------
# ProductRunRecord dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProductRunRecord:
    """Record for one product flow run (ADR-0023)."""

    run_id: str
    parent_run_id: str | None
    confirmation_revision: int        # starts at 0
    created_at: str                   # ISO 8601
    request_text: str
    extraction_source: str            # always "synthetic_fixture"
    envelope_fixture_label: str       # fixture filename
    decision: str
    extracted_parameters: dict[str, Any]
    user_explicit_parameters: dict[str, Any]
    catalog_derived_parameters: dict[str, Any]
    rule_derived_parameters: dict[str, Any]
    missing_fields: list[str]
    unsupported_requests: list[str]
    questions: list[str]
    conflicts: list[dict[str, Any]]   # [{code, fields, message}]
    confirmation: dict[str, Any]      # {required, confirmed, patch, revision, actor, confirmed_at}
    product_status: str               # one of the 7 constants above
    pipeline_status: str | None
    pipeline_stage: str | None
    schema_result: dict[str, Any] | None
    ir_document: dict[str, Any] | None
    validation_summary: dict[str, Any] | None
    errors: list[dict[str, Any]]
    step_sha256: str | None
    step_bytes: int | None
    # --- ADR-0023 evidence fields (repo-relative, no absolute paths) ---
    envelope_fixture_path: str | None = None      # repo-relative path to fixture JSON
    envelope_fixture_sha256: str | None = None    # SHA-256 of fixture file bytes
    pipeline_run_id: str | None = None            # run_pipeline's internal run_id
    pipeline_run_dir_relative: str | None = None # repo-relative path to pipeline run dir
    step_path_relative: str | None = None         # repo-relative path to STEP file (child only)
    # --- internal fields (not in as_dict) ---
    _step_path: str | None = dc_field(default=None, repr=False)
    _run_dir: str | None = dc_field(default=None, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "confirmation_revision": self.confirmation_revision,
            "created_at": self.created_at,
            "request_text": self.request_text,
            "extraction_source": self.extraction_source,
            "envelope_fixture_label": self.envelope_fixture_label,
            "envelope_fixture_path": self.envelope_fixture_path,
            "envelope_fixture_sha256": self.envelope_fixture_sha256,
            "decision": self.decision,
            "extracted_parameters": self.extracted_parameters,
            "user_explicit_parameters": self.user_explicit_parameters,
            "catalog_derived_parameters": self.catalog_derived_parameters,
            "rule_derived_parameters": self.rule_derived_parameters,
            "missing_fields": self.missing_fields,
            "unsupported_requests": self.unsupported_requests,
            "questions": self.questions,
            "conflicts": self.conflicts,
            "confirmation": self.confirmation,
            "product_status": self.product_status,
            "pipeline_status": self.pipeline_status,
            "pipeline_stage": self.pipeline_stage,
            "pipeline_run_id": self.pipeline_run_id,
            "pipeline_run_dir_relative": self.pipeline_run_dir_relative,
            "step_path_relative": self.step_path_relative,
            "schema_result": self.schema_result,
            "ir_document": self.ir_document,
            "validation_summary": self.validation_summary,
            "errors": self.errors,
            "step_sha256": self.step_sha256,
            "step_bytes": self.step_bytes,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_run_id() -> str:
    return str(uuid.uuid4())


def _build_answer_envelope(extracted: dict[str, Any]) -> str:
    """Build a synthetic app001-io.v1 envelope from merged extracted params.

    Used by confirm_product_run to create a child run envelope.
    Only includes fields that are in EXTRACTABLE_FIELDS.
    """
    safe = {k: v for k, v in extracted.items() if k in EXTRACTABLE_FIELDS and v is not None}
    evidence = [
        {"field": k, "quote": str(v), "source": "user_input"}
        for k, v in safe.items()
    ]
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "decision": "answer",
        "extracted_parameters": safe,
        "unsupported_requests": [],
        "evidence": evidence,
        "missing_fields": [],
        "questions": [],
        "confidence": None,
    }
    return json.dumps(envelope, ensure_ascii=False)


def _read_run_evidence(run_dir: Path) -> dict[str, Any]:
    """Read pipeline-saved evidence files (mirrors C1 handler logic)."""
    evidence: dict[str, Any] = {}
    schema_path = run_dir / "schema_result.json"
    if schema_path.is_file():
        try:
            d = json.loads(schema_path.read_text("utf-8"))
            evidence["provenance"] = d.get("provenance") or {}
            evidence["normalized"] = d.get("normalized") or {}
        except Exception:
            pass
    ir_path = run_dir / "input_ir.json"
    if ir_path.is_file():
        try:
            evidence["ir_document"] = json.loads(ir_path.read_text("utf-8"))
        except Exception:
            pass
    comp_path = run_dir / "compilation_result.json"
    if comp_path.is_file():
        try:
            cd = json.loads(comp_path.read_text("utf-8"))
            manifest = cd.get("manifest") or {}
            native_geo = manifest.get("native_geometry") or {}
            step_info = manifest.get("step") or {}
            step_readback = manifest.get("step_readback") or {}
            readback_cmp = step_readback.get("comparison") or {}
            evidence["validation_summary"] = {
                "solid_count": native_geo.get("solids"),
                "is_valid": native_geo.get("is_valid"),
                "volume_mm3": native_geo.get("volume_mm3"),
                "face_count": native_geo.get("faces"),
                "edge_count": native_geo.get("edges"),
                "vertex_count": native_geo.get("vertices"),
                "step_bytes": step_info.get("bytes"),
                "step_sha256": step_info.get("sha256"),
                "readback_pass": readback_cmp.get("pass"),
            }
        except Exception:
            pass
    return evidence


# ---------------------------------------------------------------------------
# ProductFlowHandler
# ---------------------------------------------------------------------------

class ProductFlowHandler:
    """Offline natural-language product flow handler (ADR-0023).

    Maintains a separate in-memory registry from C1 DemoHandler.
    Thread safety not required: single-threaded demo server.
    """

    def __init__(
        self,
        output_root: Path | None = None,
        fixture_registry: dict[str, str] | None = None,
    ) -> None:
        self._output_root = Path(output_root) if output_root else DEFAULT_C2_OUTPUT_ROOT
        self._registry: dict[str, ProductRunRecord] = {}
        self._fixture_registry = fixture_registry if fixture_registry is not None else _FIXTURE_REGISTRY

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_product_run(self, request_text: str, fixture_id: str) -> ProductRunRecord:
        """Create a product run from a fixture envelope.

        Steps: load fixture → parse → preflight (project + Schema).
        Never calls compile_ir or run_pipeline.
        """
        rid = _new_run_id()
        now = _now_iso()

        # Fixture lookup
        rel_path = self._fixture_registry.get(fixture_id)
        if rel_path is None:
            rec = self._make_blocked_record(
                rid, now, request_text, fixture_id,
                "UNKNOWN_FIXTURE_ID",
                f"fixture_id {fixture_id!r} not in registry",
            )
            self._registry[rid] = rec
            return rec

        fixture_abs = _REPO_ROOT / rel_path
        if not fixture_abs.is_file():
            rec = self._make_blocked_record(
                rid, now, request_text, fixture_id,
                "FIXTURE_FILE_NOT_FOUND",
                f"fixture file not found: {rel_path}",
            )
            self._registry[rid] = rec
            return rec

        try:
            raw_envelope = fixture_abs.read_text("utf-8")
        except OSError as exc:
            rec = self._make_blocked_record(
                rid, now, request_text, fixture_id,
                "FIXTURE_READ_ERROR", str(exc),
            )
            self._registry[rid] = rec
            return rec

        # Compute fixture provenance (repo-relative path and SHA-256)
        fixture_sha256 = hashlib.sha256(raw_envelope.encode("utf-8")).hexdigest()
        try:
            fixture_rel_path = str(fixture_abs.resolve().relative_to(_REPO_ROOT.resolve()))
        except ValueError:
            fixture_rel_path = rel_path  # fallback to registry value

        # Parse envelope (no CAD)
        from llm.parser import parse_response
        parse_result = parse_response(raw_envelope)
        if not parse_result.ok:
            rec = ProductRunRecord(
                run_id=rid, parent_run_id=None,
                confirmation_revision=0, created_at=now,
                request_text=request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=fixture_id,
                envelope_fixture_path=fixture_rel_path,
                envelope_fixture_sha256=fixture_sha256,
                decision="",
                extracted_parameters={}, user_explicit_parameters={},
                catalog_derived_parameters={}, rule_derived_parameters={},
                missing_fields=[], unsupported_requests=[], questions=[],
                conflicts=[],
                confirmation={"required": False, "confirmed": False, "patch": {},
                              "revision": 0, "actor": None, "confirmed_at": None},
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status="error", pipeline_stage="parse",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[e.as_dict() for e in parse_result.errors],
                step_sha256=None, step_bytes=None,
            )
            self._registry[rid] = rec
            return rec

        env = parse_result.envelope
        assert env is not None

        decision = env.decision
        extracted = dict(env.extracted_parameters)
        missing_fields = list(env.missing_fields)
        unsupported = list(env.unsupported_requests)
        questions = list(env.questions)

        # Preflight: project + validate_parameters (no CAD)
        from llm.projector import project_to_cad003
        from schema.set_screw_shaft_collar import validate_parameters

        conflicts: list[dict[str, Any]] = []
        schema_res_dict: dict[str, Any] | None = None
        catalog_derived: dict[str, Any] = {}
        rule_derived: dict[str, Any] = {}

        # Only preflight if decision=answer and we have something to check
        if decision == "answer" and extracted:
            proj = project_to_cad003(extracted)
            if proj.ok and proj.projected_payload:
                schema_val = validate_parameters(proj.projected_payload)
                schema_res_dict = schema_val.as_dict()
                if not schema_val.ok:
                    for err in schema_val.errors:
                        conflicts.append(err.as_dict())
                else:
                    # Populate derived param dicts from provenance
                    prov = dict(schema_val.provenance)
                    norm = schema_val.normalized or {}
                    for field, source in prov.items():
                        if source == "catalog_derived":
                            catalog_derived[field] = norm.get(field)
                        elif source == "rule_derived":
                            rule_derived[field] = norm.get(field)
            elif not proj.ok:
                conflicts.extend(list(proj.errors))

        # Determine product status
        if decision == "refuse":
            product_status = PRODUCT_STATUS_BLOCKED
            errors = [{"code": "DECISION_REFUSE", "message": "decision=refuse; construction blocked"}]
        elif unsupported:
            product_status = PRODUCT_STATUS_BLOCKED
            errors = [{"code": "UNSUPPORTED_REQUESTS",
                       "message": f"unsupported_requests is not empty: {unsupported}",
                       "fields": unsupported}]
        elif conflicts:
            product_status = PRODUCT_STATUS_BLOCKED
            errors = conflicts
        elif decision == "ask" or "bore_d" in missing_fields:
            product_status = PRODUCT_STATUS_NEEDS_CONFIRMATION
            errors = []
        else:
            # answer + preflight passed → needs_confirmation (wait for user confirm)
            product_status = PRODUCT_STATUS_NEEDS_CONFIRMATION
            errors = []

        confirmation_required = product_status == PRODUCT_STATUS_NEEDS_CONFIRMATION

        rec = ProductRunRecord(
            run_id=rid, parent_run_id=None,
            confirmation_revision=0, created_at=now,
            request_text=request_text,
            extraction_source="synthetic_fixture",
            envelope_fixture_label=fixture_id,
            envelope_fixture_path=fixture_rel_path,
            envelope_fixture_sha256=fixture_sha256,
            decision=decision,
            extracted_parameters=extracted,
            user_explicit_parameters={},
            catalog_derived_parameters=catalog_derived,
            rule_derived_parameters=rule_derived,
            missing_fields=missing_fields,
            unsupported_requests=unsupported,
            questions=questions,
            conflicts=conflicts,
            confirmation={
                "required": confirmation_required,
                "confirmed": False,
                "patch": {},
                "revision": 0,
                "actor": None,
                "confirmed_at": None,
            },
            product_status=product_status,
            pipeline_status=None, pipeline_stage=None,
            schema_result=schema_res_dict,
            ir_document=None, validation_summary=None,
            errors=errors,
            step_sha256=None, step_bytes=None,
        )
        self._registry[rid] = rec
        return rec

    def confirm_product_run(
        self,
        run_id: str,
        confirmation_revision: int,
        confirmed: bool,
        patch: dict[str, Any],
    ) -> ProductRunRecord:
        """Confirm or modify a product run; creates a child run on success."""
        now = _now_iso()

        # Lookup
        parent_rec = self._registry.get(run_id)
        if parent_rec is None:
            # Return a transient error record (not stored)
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=0, created_at=now,
                request_text="", extraction_source="synthetic_fixture",
                envelope_fixture_label="",
                decision="", extracted_parameters={},
                user_explicit_parameters={}, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=[], unsupported_requests=[],
                questions=[], conflicts=[],
                confirmation={"required": False, "confirmed": False, "patch": {},
                              "revision": 0, "actor": None, "confirmed_at": None},
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status="error", pipeline_stage="confirm",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[{"code": "RUN_NOT_FOUND", "message": f"run_id {run_id!r} not found"}],
                step_sha256=None, step_bytes=None,
            )

        # Stale revision check
        if confirmation_revision != parent_rec.confirmation_revision:
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters={}, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=parent_rec.conflicts,
                confirmation=parent_rec.confirmation,
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="confirm",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[{"code": "STALE_REVISION",
                         "message": f"confirmation_revision={confirmation_revision} != "
                                    f"expected {parent_rec.confirmation_revision}"}],
                step_sha256=None, step_bytes=None,
            )

        # Must be in needs_confirmation
        if parent_rec.product_status != PRODUCT_STATUS_NEEDS_CONFIRMATION:
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters={}, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=parent_rec.conflicts,
                confirmation=parent_rec.confirmation,
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="confirm",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[{"code": "NOT_CONFIRMABLE",
                         "message": f"run is in status={parent_rec.product_status!r}; "
                                    "only needs_confirmation runs can be confirmed"}],
                step_sha256=None, step_bytes=None,
            )

        # confirmed=False → blocked
        if not confirmed:
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters={}, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=parent_rec.conflicts,
                confirmation={**parent_rec.confirmation, "confirmed": False},
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="confirm",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[{"code": "CONFIRMATION_REJECTED",
                         "message": "confirmed=False; construction blocked"}],
                step_sha256=None, step_bytes=None,
            )

        # Validate patch fields
        unknown_patch_fields = [k for k in patch if k not in EXTRACTABLE_FIELDS]
        if unknown_patch_fields:
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters={}, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=parent_rec.conflicts,
                confirmation=parent_rec.confirmation,
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="confirm",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=[{"code": "PATCH_UNKNOWN_FIELD",
                         "message": f"unknown fields in patch: {unknown_patch_fields}",
                         "fields": unknown_patch_fields}],
                step_sha256=None, step_bytes=None,
            )

        # Validate bore_d in patch if present
        if "bore_d" in patch:
            from schema.set_screw_shaft_collar import CATALOG_ROWS
            valid_bores = {row[0] for row in CATALOG_ROWS}
            try:
                bore_val = int(patch["bore_d"])
                if bore_val not in valid_bores:
                    raise ValueError("not in catalog")
            except (TypeError, ValueError):
                return ProductRunRecord(
                    run_id=run_id, parent_run_id=None,
                    confirmation_revision=parent_rec.confirmation_revision,
                    created_at=now, request_text=parent_rec.request_text,
                    extraction_source="synthetic_fixture",
                    envelope_fixture_label=parent_rec.envelope_fixture_label,
                    decision=parent_rec.decision,
                    extracted_parameters=parent_rec.extracted_parameters,
                    user_explicit_parameters={}, catalog_derived_parameters={},
                    rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                    unsupported_requests=parent_rec.unsupported_requests,
                    questions=parent_rec.questions, conflicts=parent_rec.conflicts,
                    confirmation=parent_rec.confirmation,
                    product_status=PRODUCT_STATUS_BLOCKED,
                    pipeline_status=None, pipeline_stage="confirm",
                    schema_result=None, ir_document=None, validation_summary=None,
                    errors=[{"code": "PATCH_BORE_NOT_IN_CATALOG",
                             "message": f"bore_d={patch['bore_d']!r} in patch is not a "
                                        "valid GN 705 catalog value"}],
                    step_sha256=None, step_bytes=None,
                )

        # Merge patch into extracted parameters
        merged = {**parent_rec.extracted_parameters, **patch}
        user_explicit = {k: v for k, v in merged.items() if k in patch}

        # Schema validation of merged params
        from llm.projector import project_to_cad003
        from schema.set_screw_shaft_collar import validate_parameters
        proj = project_to_cad003(merged)
        if not proj.ok:
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters=user_explicit, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=[],
                confirmation=parent_rec.confirmation,
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="projection",
                schema_result=None, ir_document=None, validation_summary=None,
                errors=list(proj.errors),
                step_sha256=None, step_bytes=None,
            )

        schema_val = validate_parameters(proj.projected_payload)
        if not schema_val.ok:
            conflicts = [e.as_dict() for e in schema_val.errors]
            return ProductRunRecord(
                run_id=run_id, parent_run_id=None,
                confirmation_revision=parent_rec.confirmation_revision,
                created_at=now, request_text=parent_rec.request_text,
                extraction_source="synthetic_fixture",
                envelope_fixture_label=parent_rec.envelope_fixture_label,
                decision=parent_rec.decision,
                extracted_parameters=parent_rec.extracted_parameters,
                user_explicit_parameters=user_explicit, catalog_derived_parameters={},
                rule_derived_parameters={}, missing_fields=parent_rec.missing_fields,
                unsupported_requests=parent_rec.unsupported_requests,
                questions=parent_rec.questions, conflicts=conflicts,
                confirmation=parent_rec.confirmation,
                product_status=PRODUCT_STATUS_BLOCKED,
                pipeline_status=None, pipeline_stage="schema",
                schema_result=schema_val.as_dict(), ir_document=None, validation_summary=None,
                errors=conflicts,
                step_sha256=None, step_bytes=None,
            )

        # Schema passed → build provenance maps
        prov = dict(schema_val.provenance)
        norm = schema_val.normalized or {}
        catalog_derived: dict[str, Any] = {}
        rule_derived: dict[str, Any] = {}
        for field, source in prov.items():
            if source == "catalog_derived":
                catalog_derived[field] = norm.get(field)
            elif source == "rule_derived":
                rule_derived[field] = norm.get(field)

        # Bug fix 1: Parent run MUST remain immutable.
        # Do NOT mutate parent_rec.confirmation or any other parent field.
        # Confirmation evidence is recorded only on the new child run.

        # Create child run
        child_rid = _new_run_id()
        envelope_json = _build_answer_envelope(merged)

        from integration.pipeline import run_pipeline
        from demo.handler import _read_run_evidence

        child_rec = ProductRunRecord(
            run_id=child_rid,
            parent_run_id=run_id,
            confirmation_revision=0,
            created_at=now,
            request_text=parent_rec.request_text,
            extraction_source="synthetic_fixture",
            envelope_fixture_label=parent_rec.envelope_fixture_label,
            envelope_fixture_path=parent_rec.envelope_fixture_path,
            envelope_fixture_sha256=parent_rec.envelope_fixture_sha256,
            decision="answer",
            extracted_parameters=merged,
            user_explicit_parameters=user_explicit,
            catalog_derived_parameters=catalog_derived,
            rule_derived_parameters=rule_derived,
            missing_fields=[],
            unsupported_requests=[],
            questions=[],
            conflicts=[],
            confirmation={
                "required": False, "confirmed": True,
                "patch": dict(patch), "revision": 0,
                "actor": "user", "confirmed_at": now,
            },
            product_status=PRODUCT_STATUS_CONSTRUCTING,
            pipeline_status=None, pipeline_stage=None,
            schema_result=schema_val.as_dict(),
            ir_document=None, validation_summary=None,
            errors=[],
            step_sha256=None, step_bytes=None,
            pipeline_run_id=None,
            pipeline_run_dir_relative=None,
            step_path_relative=None,
        )
        self._registry[child_rid] = child_rec

        # Bug fix 2: Wrap run_pipeline in try/except so unexpected exceptions
        # result in product_status="failed" rather than an unhandled exception.
        try:
            pipeline_result = run_pipeline(
                parent_rec.request_text,
                envelope_json,
                output_root=self._output_root,
                envelope_fixture_label=parent_rec.envelope_fixture_label,
            )
        except Exception as exc:
            child_rec.product_status = PRODUCT_STATUS_FAILED
            child_rec.pipeline_status = "error"
            child_rec.pipeline_stage = "pipeline_exception"
            child_rec.errors = [{
                "code": "PIPELINE_EXCEPTION",
                "stage": "pipeline_exception",
                "message": f"{type(exc).__name__}: {str(exc)[:300]}",
            }]
            child_rec._step_path = None
            child_rec._run_dir = None
            return child_rec

        run_dir = Path(pipeline_result.run_dir) if pipeline_result.run_dir else None
        evidence: dict[str, Any] = {}
        if run_dir and run_dir.is_dir():
            evidence = _read_run_evidence(run_dir)

        # Bug fix 3: Populate evidence/provenance fields (ADR-0023 record contract).
        # Use repo-relative paths in as_dict(); never expose absolute paths.
        pipeline_run_id = pipeline_result.run_id
        pipeline_run_dir_rel: str | None = None
        if pipeline_result.run_dir:
            try:
                pipeline_run_dir_rel = str(
                    Path(pipeline_result.run_dir).resolve().relative_to(_REPO_ROOT.resolve())
                )
            except ValueError:
                pipeline_run_dir_rel = None  # outside repo — omit

        if pipeline_result.status == "success":
            child_rec.product_status = PRODUCT_STATUS_SUCCEEDED
            child_rec.pipeline_status = "success"
            child_rec.pipeline_stage = pipeline_result.stage
            child_rec.pipeline_run_id = pipeline_run_id
            child_rec.pipeline_run_dir_relative = pipeline_run_dir_rel
            if pipeline_result.ir_index:
                child_rec.step_sha256 = pipeline_result.ir_index.get("step_sha256")
                child_rec.step_bytes = pipeline_result.ir_index.get("step_bytes")
                # Repo-relative STEP path for traceability (never the absolute path)
                raw_step_path = pipeline_result.ir_index.get("step_path")
                if raw_step_path:
                    try:
                        child_rec.step_path_relative = str(
                            Path(raw_step_path).resolve().relative_to(_REPO_ROOT.resolve())
                        )
                    except ValueError:
                        child_rec.step_path_relative = None
            child_rec.ir_document = evidence.get("ir_document")
            child_rec.validation_summary = evidence.get("validation_summary")
            child_rec._step_path = pipeline_result.step_path
            child_rec._run_dir = pipeline_result.run_dir
        else:
            child_rec.product_status = PRODUCT_STATUS_FAILED
            child_rec.pipeline_status = pipeline_result.status
            child_rec.pipeline_stage = pipeline_result.stage
            child_rec.pipeline_run_id = pipeline_run_id
            child_rec.pipeline_run_dir_relative = pipeline_run_dir_rel
            child_rec.errors = pipeline_result.errors
            child_rec._step_path = None
            child_rec._run_dir = pipeline_result.run_dir

        return child_rec

    def get_product_run(self, run_id: str) -> ProductRunRecord | None:
        return self._registry.get(run_id)

    def get_product_step_bytes_secure(self, run_id: str) -> bytes | None:
        """6-layer security (mirrors C1 DemoHandler.get_step_bytes_secure)."""
        rec = self._registry.get(run_id)
        if rec is None:
            return None
        if rec.product_status != PRODUCT_STATUS_SUCCEEDED:
            return None
        step_path_str = rec._step_path
        run_dir_str = rec._run_dir
        expected_sha256 = rec.step_sha256
        if not step_path_str or not run_dir_str or not expected_sha256:
            return None
        step_path = Path(step_path_str)
        expected_prefix = Path(run_dir_str) / "cad_output"
        try:
            canonical_step = step_path.resolve()
            canonical_prefix = expected_prefix.resolve()
            canonical_step.relative_to(canonical_prefix)
        except (ValueError, OSError):
            return None
        if canonical_step.is_symlink():
            return None
        if not canonical_step.is_file() or canonical_step.stat().st_size == 0:
            return None
        content = canonical_step.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            return None
        return content

    def is_valid_run_id(self, run_id: str) -> bool:
        return bool(_UUID_PATTERN.match(run_id))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_blocked_record(
        self,
        rid: str,
        now: str,
        request_text: str,
        fixture_id: str,
        code: str,
        message: str,
        envelope_fixture_path: str | None = None,
        envelope_fixture_sha256: str | None = None,
    ) -> ProductRunRecord:
        return ProductRunRecord(
            run_id=rid, parent_run_id=None,
            confirmation_revision=0, created_at=now,
            request_text=request_text,
            extraction_source="synthetic_fixture",
            envelope_fixture_label=fixture_id,
            envelope_fixture_path=envelope_fixture_path,
            envelope_fixture_sha256=envelope_fixture_sha256,
            decision="",
            extracted_parameters={}, user_explicit_parameters={},
            catalog_derived_parameters={}, rule_derived_parameters={},
            missing_fields=[], unsupported_requests=[], questions=[],
            conflicts=[],
            confirmation={"required": False, "confirmed": False, "patch": {},
                          "revision": 0, "actor": None, "confirmed_at": None},
            product_status=PRODUCT_STATUS_BLOCKED,
            pipeline_status="error", pipeline_stage="setup",
            schema_result=None, ir_document=None, validation_summary=None,
            errors=[{"code": code, "message": message}],
            step_sha256=None, step_bytes=None,
            pipeline_run_id=None, pipeline_run_dir_relative=None,
            step_path_relative=None,
        )
