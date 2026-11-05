# APP-001-RUNNER-R1 checkpoint

task=APP-001-RUNNER-R1
status=review
work_root=/Users/syd/Desktop/参数化 cad 工程辅助设计
predecessor_commit=7cd8369 (APP-001-RUNNER-001)
formal_evaluation_gate=false (FORMAL_EVALUATION_ALLOWED unchanged in contract.py)
date=2026-11-06
agent=CC

## Predecessor handoff successor check

```text
predecessor=APP-001-RUNNER-001, commit 7cd8369
files_format=PASS: src/llm/ 7 new modules + adapter.py, tests/llm/ 3 test files, checkpoint/handoff exist
core_rerun=PASS: acceptance-set SHA-256 ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf confirmed
  PYTHONPATH=src python3 -m unittest tests.llm.test_runner tests.llm.test_authorization tests.llm.test_budget
  → 106 tests OK (skipped=1) under Python 3.10.12 (only available version in this sandbox)
dry_run=PASS: 36 combinations, no evaluator labels, formal_evaluation_allowed=False
known_limits_preserved=PASS: 4 boundary gaps identified; this R1 task closes all 4
```

## Python environment

- Linux sandbox: Python 3.10.12 (only available version)
- macOS venv symlink (python3.11) broken under Linux FUSE mount — confirmed not accessible
- Noted in handoff: all tests run under Python 3.10.12; correct frozen-env Python 3.11.18 only reachable on the macOS host
- New code uses no 3.10-incompatible syntax; `Optional` uses `typing.Optional` not `X | Y`

## Changes delivered

### Fix 1: Acceptance-set SHA-256 enforcement
- `src/llm/contract.py`: Added `ACCEPTANCE_SET_SHA256 = "ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf"`
- `src/llm/runner.py`: `_load_projection()` now passes `expected_sha256=ACCEPTANCE_SET_SHA256` to `project_acceptance_set()`
- `input_projection.py`: `project_acceptance_set()` already supported `expected_sha256` parameter (R1 activates it)
- Tests: `AcceptanceSetHashTests` (7 tests) in `test_runner_r1.py`

### Fix 2: Per-physical-attempt budget reservation
- `src/llm/budget.py`: Added `BudgetAwareTransport` wrapper class
  - Each `send()` call: reserve_attempt() → inner.send() → record_outcome()
  - Raises `BudgetExhausted` before calling inner.send() if budget exceeded
  - Records correct outcome (success/transient_retryable/non_retryable) per attempt
- `src/llm/runner.py`: `_execute_one_run()` now uses `BudgetAwareTransport` wrapping the real transport; removed old single upfront reservation
- `src/llm/runner.py`: Added fail-closed check for interrupted runs (attempts > 0 but no result → fail closed)
- Tests: `BudgetAwareTransportTests` (8 tests) in `test_runner_r1.py`

### Fix 3: C1 bore_d extraction from NLI
- `src/llm/conditions.py`: Completely rewrote module
  - Added `extract_bore_d_mm(nli)` deterministic regex extractor
  - Supports: `bore_d=24 mm`, `bore_d=24mm`, `轴孔直径 1.6 cm`, `目标轴环的 bore_d 是 24 mm`
  - cm → mm conversion (×10)
  - Falls back to structural reference_context (A08-style) if NLI extraction fails
  - Blocks with `C1_NO_SAFE_QUERY_PARAMETER` when bore_d cannot be safely extracted
  - No fixed fallback bore_d=20
  - Never reads evaluator-only fields
  - Added `bore_d_used_for_query` field to `AssembledInput` for audit
- Tests: `BoreDExtractionTests` (12 tests), `C1AssemblyNoFixedFallbackTests` (6 tests) in `test_runner_r1.py`

### Fix 4: Ollama digest strict verification and actual-value recording
- `src/llm/real_transport.py`:
  - `OllamaTransport.__init__()`: Added `_actual_digest` and `_actual_model_name` instance vars
  - `_verify_model_digest()`: Strict `startswith()` check (no `in` fallback); verifies qwen3 model name; records `_actual_digest`, `_actual_model_name`, `_ollama_version`
  - `_parse_response()`: Includes `local_actual_digest` and `local_actual_model_name` in usage dict
- `src/llm/adapter.py`:
  - `_record_runtime_identity()`: Reads actual digest from `response.usage["local_actual_digest"]` if available; falls back to frozen constant only for FakeTransport/tests (with no false representation)
- Tests: `OllamaDigestTests` (6 tests) in `test_runner_r1.py`

## Verification commands and results

```
PYTHONPATH=src python3 -m py_compile src/llm/contract.py src/llm/conditions.py src/llm/budget.py src/llm/runner.py src/llm/real_transport.py src/llm/adapter.py tests/llm/test_runner_r1.py
→ OK

PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r1 -v
→ Ran 40 tests in 0.150s, OK

PYTHONPATH=src python3 -m unittest discover -s tests/llm
→ Ran 316 tests, OK (skipped=1)
  (Previous pre-existing FUSE symlink errors no longer appear in this run)

PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
→ 17 tests, OK

git diff --check → OK
work/app001-runs/ git-ignored via .gitignore:40 work/ rule → confirmed
secret scan (DEEPSEEK_API_KEY=) → no hardcoded keys found
```

## Known limits and unresolved items

- Python 3.11.18 not accessible in Linux sandbox; tests run under Python 3.10.12. macOS-side Python 3.11.18 is the project baseline; new code uses `typing.Optional` for compatibility.
- No formal 9-case evaluation run; no real DeepSeek/Ollama requests; no performance metrics.
- `FORMAL_EVALUATION_ALLOWED = False` unchanged.
- C1 blocked for cases where NLI has no explicit bore_d and structural reference has no bore_d (e.g. A04 outer_d/width only, A07 bore_d=75 unsupported). This is correct behavior per spec.
- OllamaTransport digest verification tests use injected patched functions (not real Ollama). Live digest verification deferred to formal run environment.
- runner.py interrupted-run fail-closed: marks `interrupted_fail_closed` rather than attempting resume. Codex hub should review if this is acceptable for Phase 1.

## Status

APP-001-RUNNER-R1: review
APP-001: planned (formal evaluation NOT authorized yet)
FORMAL_EVALUATION_ALLOWED: False (unchanged)
No formal 9-case evaluation was run. No real network calls made. All metrics: not_measured.
