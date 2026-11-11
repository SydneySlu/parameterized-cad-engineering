# Integration Layer: Synthetic Envelope → Real Local STEP

This package connects the frozen v5 extraction contract to the existing
Schema → IR → CAD compilation pipeline via a strict construction gate and
a formal Schema→IR adapter.  It is the implementation of
`APP-002-INTEGRATION-A1`.

## Purpose

- Accepts a **requirement text** (traceability) and a **synthetic v5 fixture envelope** (JSON file).
- Runs: parse → gate → Schema validation → IR adapter → CAD compile → STEP.
- Isolates every run in its own UUID directory under `work/integration-runs/`.
- `extraction_source` is always `"synthetic_fixture"` in A1; no real model calls, no network.

## CLI Usage (real Mac CAD environment)

```bash
PYTHONPATH=src:. work/benchcad-output/venv/bin/python scripts/run_cad_pipeline.py \
    --request "请按 GN 705 做一个轴环，孔径 24 mm" \
    --synthetic-envelope tests/integration/fixtures/answer-bore24.json \
    --output-root work/integration-runs \
    [--run-id my-run-id] \
    [--json]
```

The `--synthetic-envelope` flag is required and explicitly labels the envelope
as a synthetic test fixture, not a live model response.

## Status Vocabulary

| status    | meaning                                                             |
|-----------|---------------------------------------------------------------------|
| `success` | STEP produced, verified, and published; `step_path` is set.        |
| `ask`     | Fixture said `ask`; `questions` returned; no STEP.                 |
| `refuse`  | Fixture said `refuse`; no STEP.                                    |
| `blocked` | Gate blocked (`missing_fields`, `unsupported_requests`, schema).   |
| `failed`  | CAD compilation or STEP export/readback failed; no STEP.           |
| `error`   | Parse error or internal error; no STEP.                            |

Exit codes: 0=success, 1=ask/refuse/blocked, 2=failed/error.

## Construction Gate (all five must pass)

1. `parse_response` succeeds (valid v5 envelope)
2. `decision == "answer"`
3. `missing_fields == []`
4. `unsupported_requests == []`
5. `project_to_cad003` + `validate_parameters` both succeed

## Run Directory Structure

Each run writes to `work/integration-runs/<run_id>/`:

```
input.json           # run metadata and envelope hash
envelope.json        # raw synthetic envelope bytes
schema_result.json   # Schema validation result + provenance
input_ir.json        # accepted Typed CAD IR
cad_output/          # compiler output directory (STEP file inside)
compilation_result.json
index.json           # hash index: envelope, IR, STEP (success only)
summary.json         # run status and stage
```

The `work/integration-runs/` directory is git-ignored.  Failure residuals are
kept for diagnostics only; re-generation requires a new run with a new run ID.

## Key Modules

- `schema_to_ir.py` — deterministic Schema→IR adapter (mapping.md, frozen R3)
- `pipeline.py` — unified offline pipeline with run isolation
- `../scripts/run_cad_pipeline.py` — CLI entry point

## A1 Boundaries

- No model/network calls, no `.env`/key reads.
- `extraction_source` is always `"synthetic_fixture"`.
- Real model integration is A2 (separate scope, separate authorization).
