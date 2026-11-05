# APP-001-ADAPTER handoff

Date: 2026-11-05
Task: `APP-001-ADAPTER`
Status: `review`
Work root: `/Users/syd/Desktop/参数化 cad 工程辅助设计`

---

## Handoff self-check

```text
handoff_self_check:
  changed=src/llm/* (10 new modules), tests/llm/* (5 new test files),
          agent-work/llm/APP-001-adapter/checkpoint.md,
          agent-work/llm/APP-001-adapter/handoff.md,
          docs/WORKLOG.md (append-only)
  commands=
    1. git rev-parse --show-toplevel → /Users/syd/Desktop/参数化 cad 工程辅助设计 (OK)
    2. git diff --check → OK (no whitespace errors)
    3. PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
    4. PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 85 tests, 0 failures, OK
    5. PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
    6. grep -rn "import cadquery|from cad_compilation.compiler import compile_ir" src/llm/ tests/llm/ → no matches
    7. secret pattern scan (sk-*, Bearer, DEEPSEEK_API_KEY real values) → only synthetic fixtures
    8. .env existence check (never read) → git check-ignore -v .env passed
    9. acceptance-set-v0.json structure check (keys/version only; labels not read) → OK
  confirmed=
    - All 85 tests pass with FakeTransport only; no real network I/O.
    - No acceptance-set labels read, no model calls made, no real credentials accessed.
    - Formal evaluation gate is always False; require_formal_evaluation_allowed() raises.
    - DeepSeek + Ollama request bodies are completely isolated (no cross-contamination).
    - Strict parser rejects: code fences, extra prose, multiple objects, missing/extra keys,
      wrong versions, bad enums, non-null confidence, type errors.
    - construction_ready=true only when decision=answer, unsupported_requests=[], schema passes.
    - IR/CAD/geometry/STEP stages always recorded as blocked/not_run (no fabrication).
    - Run records serialize to valid JSON; all stage statuses are in STAGE_STATUSES vocab.
    - Retry: 3 attempts max, backoff [1s, 2s] injected into tests (no real sleep); retryable
      conditions (429, 5xx, timeout, interruption) retry; auth/permission/etc. stop immediately.
    - Cloud cost computed from actual usage + dated rate card; not_available when fields missing.
    - Local Ollama run: cloud_* fields = None; local_wall_time_ms populated.
  unresolved=
    - IR mapping: no frozen src-level parameter→IR adapter exists; IR stage always blocked.
      Requires Codex hub to freeze a src/llm-level mapping module before end-to-end CAD/STEP.
    - True provider identity: real DeepSeek runtime_returned_model/provider not yet confirmed
      under a formal run; mock uses "deepseek-flash" as the configured value.
    - Real Ollama runtime: no actual Ollama call made; transport and parameter shape confirmed
      by prior M0/M1 capability probes (APP-001-PREP), not by this task.
    - Cost/performance: no formal latency or cost measurements (mock runs only);
      all formal metrics remain not_measured.
    - Rate card: DeepSeek price snapshot from 2026-11-05; rates may change.
    - Cross-process/cross-platform behavior of schema API: assumed stable per existing tests.
    - Acceptance-set v0 evaluation: not run, blocked by formal evaluation gate.
  next_agent_focus=
    - Codex hub: review strict parser boundary (no repair), construction gate logic,
      IR/CAD/STEP not_run/blocked honesty, secret/credential handling.
    - Key question: freeze a src-level parameter→IR adapter so the adapter can route
      construction-ready outputs to compile_ir(); mapping.md spec exists but is not
      a runnable src module.
    - Codex hub: confirm adapter/logger review passes before project owner can authorize
      formal APP-001 run; APP-001 must remain planned until then.
    - Check: does the cost calculation handle the case where API returns cache_hit/miss
      in a different field structure? (Current: uses prompt_cache_hit_tokens /
      prompt_cache_miss_tokens from DeepSeek response, per runtime probe evidence.)
```

---

## Interface inventory results

| Component | Status | Notes |
|---|---|---|
| Python | 3.10.12 system; unittest; no pytest needed | stdlib only; no new deps |
| DeepSeek request | Confirmed fields from frozen YAML + ADR-0011/12 | `thinking: {type: disabled}`, `max_tokens`, `seed` in body |
| Ollama request | Confirmed from APP-001-PREP capability probe | `think=false`, `format=json`, `num_predict` in `options` |
| Schema API | `validate_parameters`, `validate_json`, `resolve_parameters` → `ValidationResult` | Real signatures confirmed from `src/schema/set_screw_shaft_collar.py` |
| CAD compiler | `compile_ir(raw, output_dir=...)` → `CompilationResult` | Requires CadQuery/OCP; lazy import; not called in this task |
| Parameter→IR mapping | `mapping.md` spec exists; `generate_manifest.py::build_accepted_ir` in agent-work/ (RET-001, not src-level) | **No frozen src-level adapter; IR stays blocked** |

---

## Mock coverage

All tests use `FakeTransport`. Covered:

1. **Provider request payloads:** DeepSeek frozen fields + `thinking` control; Ollama `think=false`, `format=json`, `options`; parameter isolation (no cross-contamination).
2. **Valid response parsing:** complete envelope, `ask`/`refuse`/`answer` decisions, measurement objects, `retrieval_reference` source.
3. **Protocol failures (fail-closed):** code fences, extra prose, multiple JSON objects, missing keys, extra keys, wrong `contract_version`, wrong `prompt_version`, invalid `decision` enum, non-null `confidence`, `extracted_parameters` type errors, unknown parameter keys, `second_screw` type, bad evidence shape, non-array fields, empty body, non-UTF-8 bytes.
4. **Stage recording for bad paths:** missing `bore_d` (ask/refuse) → schema fail + construction_gate fail; catalog conflict (explicit `outer_d` mismatch) → schema fail; `unsupported_requests` non-empty → construction_gate fail; parse failure → schema = not_run.
5. **Construction gate:** true only when `decision=answer` + empty `unsupported_requests` + schema pass; false in all other cases; no CAD/IR callback invoked on false.
6. **Retry:** success on attempt 1 (no sleep), retry after 429 then success (sleep=[1]), exhaust 3×5xx (sleep=[1,2]); auth/malformed/context-overflow stop on attempt 1; all 4 retryable conditions verified; backoff order [1,2] asserted.
7. **Usage/cost:** peak CNY 0.000128 from (0 cache_hit, 40 cache_miss, 6 output); off-peak CNY 0.000064; missing fields → `not_available`; local Ollama → `cloud_*` all None.
8. **Serialization + secret scan:** run records serialize to valid JSON; `formal_evaluation_allowed=false` in JSON; IR/CAD/step all `not_run`/`blocked`; no `sk-*` / `Bearer <real>` / `DEEPSEEK_API_KEY=<value>` in serialized records; `authorization` value not in records.
9. **Gate:** `formal_evaluation_allowed()` = False; `require_formal_evaluation_allowed()` raises `FormalEvaluationBlockedError`; `allow_real_network=True` trips gate before transport is called.

---

## Checks not executed

- Real DeepSeek API call (gate closed; no key used).
- Real Ollama inference (gate closed; no local model loaded).
- Frozen acceptance-set (9 evaluator-only samples not run; labels not read).
- Formal C0/C1/C2 or any effect/cost/latency metrics (all `not_measured`).
- IR/CAD/geometry/STEP pipeline (no frozen src-level mapping; stages honest `not_run`/`blocked`).
- Cross-platform or cross-process schema determinism (assumed per existing schema tests).

---

## Work tree and commit status

```text
# Untracked additions to be committed:
  src/llm/
  tests/llm/
  agent-work/llm/APP-001-adapter/
# Modified (append-only):
  docs/WORKLOG.md
```

Commit: `e496ac0` (`feat: implement APP-001 dual-baseline execution adapter with mock transport [APP-001-ADAPTER]`)

**No push. No merge.** Status remains `review`. Awaiting Codex hub read-only review.

---

## APP-001 formal evaluation status

`APP-001` remains `planned`. No formal model run is authorized. The adapter
implementation and review is one required gate; explicit project-owner authorization
is the second gate. Neither has been satisfied.
