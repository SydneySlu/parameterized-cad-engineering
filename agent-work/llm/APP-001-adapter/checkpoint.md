# APP-001-ADAPTER checkpoint

```text
task=APP-001-ADAPTER
status=in_progress
work_root=/Users/syd/Desktop/参数化 cad 工程辅助设计
formal_evaluation_gate=false
APP-001-PREP=review
APP-001=planned
```

## M0 interface and boundary inventory

Date: 2026-11-05. Performed before any implementation, per task prompt section 3.

### Repository state

- `git rev-parse --show-toplevel` returns the shared project root; working tree
  was clean on `main`, ahead of `origin/main` by 3 commits (APP-001 freeze
  prep).
- `.env` exists and is git-ignored (`git check-ignore -v .env` passes). Its
  value was never read, printed, copied, or committed. Only an existence
  check was performed.
- `work/` is git-ignored; run artifacts will be written to
  `work/app001-runs/` and never committed.

### Python and test runner

- System Python: `Python 3.10.12` on Darwin arm64. No `pytest` installed in
  the system interpreter; existing tests use `unittest` and are run with
  `PYTHONPATH=src python3 -m unittest`.
- The venv at `work/benchcad-output/venv/bin/python3` is a broken symbolic
  link and is not usable in this environment; it is not needed for this task
  because CAD runtime (CadQuery/OCP) is never imported here.
- Existing schema tests pass with system Python:
  `PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar`
  → 17 tests, OK.
- Decision: use the standard library only; no new dependencies. Tests run
  under `unittest` with `PYTHONPATH=src`.

### Frozen contract versions (authoritative)

- Model output contract: `app001-io.v1` (frozen by ADR-0013).
- Prompt: `app001-extraction.v2` (`prompt-v2.md`, frozen).
- Acceptance set: `acceptance-set-v0` (9 evaluator-only cases, frozen;
  `formal_evaluation_allowed=false`). Only file structure/version checked;
  labels were never read into model input, tests, or run logs.
- Family/schema: `set_screw_shaft_collar` / `set_screw_shaft_collar.v0`.
- Cloud: DeepSeek, request model `deepseek-flash`, Base URL
  `https://api.deepseek.com`, OpenAI-compatible Chat Completions, explicit
  `thinking: {"type":"disabled"}`.
- Local: Ollama `qwen3:8b`, digest/ID `500a1f067a9f`, `think=false`.
- Shared decode: `temperature=0`, `top_p=1`, `max_output_tokens=512`,
  `seed=271828`. DeepSeek sends `max_tokens`; Ollama sends `num_predict`.
- Retry: max 2 retries (3 total attempts), only for connection/read timeout,
  connection interruption, HTTP 429, HTTP 5xx; backoff 1s, 2s. Non-retryable:
  auth/permission, malformed request, context overflow, invalid JSON,
  contract/schema/rule/CAD failures.

### Schema API (src/schema/set_screw_shaft_collar.py)

- `validate_parameters(payload)`, `validate_json(document)`,
  `resolve_parameters(payload)` → `ValidationResult`.
- `ValidationResult` fields: `ok: bool`, `schema_version: str`,
  `family_id: str`, `normalized: dict | None`, `provenance: dict`,
  `errors: tuple[RuleViolation, ...]`.
- `RuleViolation` fields: `code: str`, `fields: tuple[str, ...]`,
  `message: str`, `stage: str` (default `"schema"`).
- Serialization: `.as_dict()`, `.to_json(indent=...)`, `.from_json(document)`.
- Accepts either a flat parameter object or a formal envelope
  `{schema_version, family_id, parameters}`; unknown envelope/parameter
  fields are rejected with stable error codes (`UNKNOWN_FIELD`,
  `MISSING_REQUIRED`, `CATALOG_CHOICE`, `CATALOG_MISMATCH`,
  `SECOND_SCREW_CONSTRAINT`, `WALL_THICKNESS_TOO_SMALL`,
  `WIDTH_SUPPORT_TOO_SMALL`, etc.).
- Constants: `FAMILY_ID = "set_screw_shaft_collar"`,
  `SCHEMA_VERSION = "set_screw_shaft_collar.v0"`,
  `SOURCE_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"`,
  `CANONICAL_LENGTH_UNIT = "mm"`, `CATALOG_ROWS` (15 rows).

### CAD compiler entry (src/cad_compilation/)

- `compile_ir(raw, *, output_dir=None)` → `CompilationResult`; requires
  CadQuery/OCP (lazy import). `validate_ir(raw)` → `list[CadError]`.
- `validate_document(document)` → `list[CadError]` (IR semantic validation).
- `PARAMETER_ORDER = ["bore_d", "outer_d", "screw_d", "screw_len",
  "second_screw", "width"]` (defined in `ir.py`).
- The compiler accepts serialized IR JSON only; it does not accept raw
  CAD-003 parameters. A validated IR document with `status="accepted"` is
  required before build.

### Parameter → IR mapping status (key decision point)

- A mapping **spec** exists: `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
  (IR-001 status: `review`).
- A **task-specific generator** implements that mapping:
  `agent-work/data/RET-001-retrieval-manifest/generator/generate_manifest.py::build_accepted_ir`
  substitutes the six normalized parameters into a deepcopy of the frozen
  `legal-catalog-row.json` template. This lives under `agent-work/` (RET-001
  task), not under `src/`, and is not packaged as a reusable adapter module.
- There is **no frozen, reviewed, src-level** parameter→IR adapter that this
  task is authorized to call. Per task prompt section 3, the adapter will
  therefore implement only through the CAD-003 projection/validation stage
  and keep IR/CAD/STEP as `not_run` / `blocked_no_approved_ir_mapping`.
- The handoff will flag that Codex hub must first freeze a src-level
  mapping contract before end-to-end CAD/STEP can be claimed.

### Security boundaries confirmed

- No real DeepSeek API or Ollama calls; no runtime probes. No reading of
  `.env`, API keys, or Authorization headers. Tests use injected fake/mock
  transport only.
- No running of the nine frozen acceptance samples; no copying of labels
  into model input, tests, or run logs.
- Formal evaluation gate default-off (fail closed). Any runnable model
  CLI/API entry must fail closed.
- Raw model responses are controlled by an explicit retention policy and
  written only to the git-ignored `work/app001-runs/` directory.
- No full provider error bodies, request headers, Authorization, or hidden
  reasoning content in logs. Stable error code/stage/fields plus necessary
  redacted summaries only.

## Milestones

- M0: interface inventory — **done**.
- M1: minimal data model, strict parser, projector, run record, transport,
  providers, retry, cost, gate, adapter — **done**.
- M2: dual provider mock adapter + retry with injectable clock/sleeper — **done**.
- M3: deterministic post-processing + staged logging + construction gate +
  default-off eval gate — **done**.
- M4: tests (85/85 pass), secret scan, diff check, README, checkpoint/handoff — **done**.

## M4 final verification

### Test run (exact command and result)

```
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
```

Result: **85 tests, 0 failures, 0 errors, OK** (2026-11-05)

### Schema regression (existing)

```
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
```

Result: **17 tests, OK** — no regressions.

### Compile check

```
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py
```

Result: **OK** (all 10 source + 5 test files compile clean)

### Secret scan

```
git diff --check
grep -rn "DEEPSEEK_API_KEY|sk-[A-Za-z0-9]|Bearer [A-Za-z0-9]" src/llm/ tests/llm/
```

Result: Only synthetic test fixtures found (e.g. `"sk-test-secret-key-value"`,
`"Bearer dummy"`, `os.environ.get("DEEPSEEK_API_KEY")`).  No real keys.
`git diff --check` passed.

### No CAD runtime imports

```
grep -rn "import cadquery|from cad_compilation.compiler import compile_ir" src/llm/ tests/llm/
```

Result: **no matches** — the CAD runtime is never imported by the adapter or tests.

### Formal evaluation gate check

Confirmed: `gate.formal_evaluation_allowed()` returns `False`; all adapter
runs invoke `require_formal_evaluation_allowed()` when `allow_real_network=True`.
Test `test_adapter_with_allow_real_network_trips_gate` verifies this.

## Files changed

### New (untracked, to be committed)

```
src/llm/__init__.py
src/llm/README.md
src/llm/adapter.py
src/llm/contract.py
src/llm/cost.py
src/llm/gate.py
src/llm/parser.py
src/llm/projector.py
src/llm/providers.py
src/llm/retry.py
src/llm/runrecord.py
src/llm/transport.py
tests/llm/__init__.py
tests/llm/test_adapter.py
tests/llm/test_cost.py
tests/llm/test_parser.py
tests/llm/test_providers.py
tests/llm/test_retry.py
tests/llm/test_security.py
agent-work/llm/APP-001-adapter/checkpoint.md
agent-work/llm/APP-001-adapter/handoff.md
```

### Modified

```
docs/WORKLOG.md  (append-only entries for M0/M1/M2/M3/M4)
```

## Status

```text
task=APP-001-ADAPTER
status=review
APP-001-PREP=review
APP-001=planned
formal_evaluation_allowed=false
commit=e496ac0 (feat: implement APP-001 dual-baseline execution adapter with mock transport [APP-001-ADAPTER])
```
