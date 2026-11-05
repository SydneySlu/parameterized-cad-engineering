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

---

## APP-001-ADAPTER-R1 corrections

Date: 2026-11-05
Task: `APP-001-ADAPTER-R1`

All 4 required fixes and 3 contract clarifications from
`APP-001-ADAPTER-codex-review.md` have been addressed.

### Handoff self-check (R1)

```text
handoff_self_check:
  changed=
    src/llm/providers.py     (remove api_key param + env read; credential-free)
    src/llm/transport.py     (add MockTransport base; FakeTransport sanitizes calls)
    src/llm/gate.py          (unchanged; used as-is by adapter for gate check)
    src/llm/adapter.py       (gate enforces MockTransport check; RetentionPolicy;
                               prompt hashes; remove allow_real_network kwarg;
                               use 3-tuple from send_with_retry)
    src/llm/retry.py         (return 3-tuple: response, outcomes, total_elapsed_ms)
    src/llm/runrecord.py     (add prompt_hashes, raw_response_retention fields)
    src/llm/cost.py          (strict: no fallback split; consistency check)
    src/llm/parser.py        (add _walk_check_finite; element type checks)
    src/llm/README.md        (full rewrite for R1 accuracy)
    tests/llm/test_retry.py  (updated for 3-tuple; new elapsed tests)
    tests/llm/test_providers.py (remove api_key test; add env-isolation test)
    tests/llm/test_adapter.py (fix cost assertion; rename gate test)
    tests/llm/test_security.py (revamp gate test; revamp credential tests)
    tests/llm/test_r1_regression.py (new: 36 R1 regression tests)
    agent-work/llm/APP-001-adapter/checkpoint.md (R1 section appended)
    agent-work/llm/APP-001-adapter/handoff.md (this section)
    docs/WORKLOG.md (append-only R1 entry)
  commands=
    PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
    PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 121 tests, OK
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
    git diff --check → PASS
    secret scan (grep sk-*, Bearer real, DEEPSEEK_API_KEY real) → only synthetic fixtures
  confirmed=
    3.1: mock requests always authorization=None; FakeTransport stores sanitized copies;
         synthetic env var not read during mock run; fake records contain no auth values.
         All confirmed by test_retry.FakeTransportTrackingTests and
         test_security.SecretScanTests.test_no_env_key_read_during_run.
    3.2: Non-MockTransport refused before send() with gate closed; FakeTransport path
         still runs. Confirmed by test_security.GateTests.test_non_mock_transport_trips_gate_before_send
         (send_calls==0 verified).
    3.3: cache fields both missing → not_available (not 0.00028). Inconsistent split,
         negative, bool also not_available. Confirmed by test_r1_regression.CostNotAvailableTests.
    3.4: total_elapsed_ms includes injected backoff. Confirmed by
         test_retry.ElapsedTimeTests (retry_success_elapsed_includes_backoff: total > sum_of_attempts).
    3.5: NaN rejected (NON_FINITE_VALUE); Infinity/-Infinity rejected; evidence field/quote/source
         type errors; array element string checks. Confirmed by test_r1_regression.ParserNaNInfinityTests
         and ParserArrayElementTypeTests.
    4.1: Default retention=off; opt-in writes to tempdir; path errors produce retention_failed.
         Confirmed by test_r1_regression.RetentionPolicyTests.
    4.2: Prompt hashes stable; change with content; text not in record JSON.
         Confirmed by test_r1_regression.PromptHashTests.
    No real API/Ollama calls. No real credentials read. No frozen samples run.
  unresolved=
    - IR mapping: still no frozen src-level parameter->IR adapter; IR stage blocked.
    - Rate card consistency check assumes DeepSeek field semantics
      (cache_hit + cache_miss == prompt_tokens); if API semantics differ in future,
      this will produce not_available until a new ADR adjusts the definition.
    - Prompt version verification: the adapter records hashes but does not currently
      load and verify the frozen prompt artifact from disk at runtime. This must be
      added before any formal run to prevent version mislabeling.
    - Formal evaluation gate remains closed. APP-001 remains planned.
  next_agent_focus=
    - Codex hub: verify 3.1 (no env read), 3.2 (gate before send), 3.3 (no fallback),
      3.4 (elapsed includes backoff), 3.5 (NaN/Infinity, element types).
    - Prompt artifact verification: should the adapter load and hash-verify the
      frozen prompt-v2.md at startup? Recommend yes before any formal run.
    - If all R1 fixes verified, project owner may authorize formal APP-001 run.
      adapter/logger review is now satisfied pending Codex R1 acceptance.
```

### Checks not executed (R1)

- Real DeepSeek API call (gate closed; no key used; not attempted).
- Real Ollama inference (gate closed; not attempted).
- Frozen acceptance-set evaluation (labels not read; not run).
- Formal C0/C1/C2 metrics (all `not_measured`).
- IR/CAD/geometry/STEP pipeline (no frozen src-level mapping; all `not_run`/`blocked`).

### APP-001 formal evaluation status

`APP-001` remains `planned`.  No formal model run is authorized.

---

## APP-001-ADAPTER-R2 corrections

Date: 2026-11-05
Task: `APP-001-ADAPTER-R2`

All 3 issues from `APP-001-ADAPTER-R1-codex-review.md` addressed.

```text
handoff_self_check:
  changed=
    src/llm/adapter.py         (exact type gate check; prompt verification; retention path bounds)
    src/llm/prompt_loader.py   (new: frozen prompt loader and verifier)
    tests/llm/test_adapter.py  (add verify_frozen_prompt=False to synthetic tests)
    tests/llm/test_security.py (add verify_frozen_prompt=False to synthetic tests)
    tests/llm/test_r1_regression.py (add verify_frozen_prompt=False; use for_test() factory)
    tests/llm/test_r2_regression.py (new: 22 R2 regression tests)
    agent-work/llm/APP-001-adapter/checkpoint.md (R2 section appended)
    agent-work/llm/APP-001-adapter/handoff.md (this section)
    docs/WORKLOG.md (append-only R2 entry)
  commands=
    PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
    PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 143 tests, OK
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
    git diff --check → PASS
    secret scan (grep patterns) → no real credentials found
  confirmed=
    4.1 MockTransport subclass: send_calls==0 confirmed by
        test_r2_regression.GateExactTypeTests.test_mock_transport_subclass_refused_before_send
        and test_fake_transport_subclass_refused (FakeTransport subclass also refused).
        Duck-type (plain class with send()) also refused (send_calls==0).
        FakeTransport exact type still passes. Gate fires before env read.
        All confirmed via mock; no real network.
    4.2 Retention path: external absolute path and path traversal raise
        RETENTION_PATH_OUTSIDE_IGNORED_DIR at validate_for_production() time.
        for_test() factory writes to tempdir correctly and cannot be used in
        production validate. Write failure recorded, not swallowed.
        Confirmed by test_r2_regression.RetentionPathTests.
    4.3 Frozen prompt: correct frozen prompt passes with send_calls > 0.
        Modified system/template raise FrozenPromptMismatchError with send_calls==0.
        Missing artifact raises FrozenPromptMismatchError with send_calls==0.
        Prompt text not in RunRecord JSON; SHA-256 hashes present and match artifact.
        Confirmed by test_r2_regression.FrozenPromptVerificationTests.
    No real API/Ollama calls. No real credentials read. No frozen samples run.
    APP-001-PREP=review, APP-001=planned, formal_evaluation_allowed=false.
  unresolved=
    - IR mapping: no frozen src-level parameter->IR adapter; IR/CAD/STEP blocked/not_run.
      This is correct behavior per original task Prompt; not a blocker for adapter review.
    - Real DeepSeek/Ollama runtime: not executed; not authorized.
    - Nine acceptance samples: not run; labels not read.
    - Formal performance metrics (cost/latency/schema/CAD/STEP): all not_measured.
  next_agent_focus=
    - Codex hub: verify 4.1 gate exact type check (MockTransport subclass send_calls==0),
      4.2 retention path bounds (external path rejected before write),
      4.3 frozen prompt artifact (missing/modified rejected before send).
    - If all R2 fixes verified and accepted, project owner may authorize formal APP-001 run.
    - Remaining dependency: IR src-level mapping must be frozen before CAD/STEP can be claimed.
```

### Checks not executed (R2)

- Real DeepSeek API call (gate closed; not attempted).
- Real Ollama inference (gate closed; not attempted).
- Frozen acceptance-set evaluation (labels not read; not run).
- Formal C0/C1/C2 metrics (all not_measured).
- IR/CAD/geometry/STEP pipeline (no frozen src-level mapping; all not_run/blocked).

### APP-001 formal evaluation status

`APP-001` remains `planned`.  No formal model run is authorized.

---

## APP-001-ADAPTER-R3 corrections

Date: 2026-11-05
Task: `APP-001-ADAPTER-R3`

```text
handoff_self_check:
  changed=
    src/llm/prompt_loader.py    (add FROZEN_PROMPT_FILE_SHA256 anchor; file hash check)
    src/llm/adapter.py          (remove verify_frozen_prompt/_prompt_loader_path params;
                                  remove _test_only/_for_test_/validate_for_production/
                                  _allow_test_path; extract _write_raw_to_dir; fix
                                  _retain_response to always use canonical root)
    tests/llm/_frozen_helpers.py (new: _frozen_input helper using real frozen artifact)
    tests/llm/test_r3_regression.py (new: 19 R3 tests)
    tests/llm/test_adapter.py    (use _frozen_input(); remove verify_frozen_prompt=False)
    tests/llm/test_security.py   (use _frozen_input(); remove verify_frozen_prompt=False)
    tests/llm/test_r1_regression.py (use _frozen_input(); remove for_test/test_only)
    tests/llm/test_r2_regression.py (use _frozen_input(); remove for_test/bypass tests)
    agent-work/llm/APP-001-adapter/checkpoint.md (R3 section appended)
    agent-work/llm/APP-001-adapter/handoff.md (this section)
    docs/WORKLOG.md (append-only R3 entry)
  commands=
    PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
    PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 167 tests, OK
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
    git diff --check → PASS
    git ls-files work/ → (empty)
    git status --short → clean except staged R3 changes
  confirmed=
    A. Prompt bypass removed: inspect.signature(Adapter.run) confirms no
       verify_frozen_prompt or _prompt_loader_path. Synthetic prompt → raises
       FrozenPromptMismatchError, transport.call_count == 0. Real frozen prompt
       (via _frozen_input) reaches send() successfully. File hash anchor
       FROZEN_PROMPT_FILE_SHA256 matches actual prompt-v2.md bytes.
       Confirmed by test_r3_regression.PromptVerificationBypassRemovedTests.
    B. Retention bypass removed: RetentionPolicy dataclass has no _test_only
       field, no for_test factory, no validate_for_production method. External
       absolute path to _retain_response produces retention_failed immediately,
       no file written. Test tempdir accessible via _write_raw_to_dir() directly.
       Confirmed by test_r3_regression.RetentionBypassRemovedTests.
    R2 transport gate regression: FakeTransport exact type gate unmodified;
       MockTransport subclass still refused (verified by existing R2 tests).
    No real API/Ollama calls. No real credentials read. No frozen samples run.
    git ls-files work/ confirms no run artifacts committed.
  unresolved=
    - IR mapping: no frozen src-level parameter->IR adapter; IR/CAD/STEP blocked/not_run.
    - Real DeepSeek/Ollama runtime: not executed; not authorized.
    - Nine acceptance samples: not run; labels not read.
    - Formal performance metrics: all not_measured.
    - Note on file hash TOCTOU: prompt_loader reads the file twice (text + bytes) for
      hash checking; a concurrent replacement between those reads is theoretically
      possible but is the same OS file path, so both reads see the same inode in
      practice. A future improvement would read bytes once and decode.
  next_agent_focus=
    - Codex hub: verify (1) Adapter.run signature has no bypass params, (2) synthetic
      prompt raises with send_calls==0, (3) _test_only not in RetentionPolicy fields,
      (4) _retain_response rejects external paths, (5) integration test with real
      frozen prompt succeeds.
    - If R3 verified, project owner may authorize formal APP-001 run.
    - IR src-level mapping must be frozen before CAD/STEP can be claimed.
```

### APP-001 status

`APP-001` remains `planned`. No formal model run authorized.
APP-001-ADAPTER status: `review`, awaiting Codex R3 review.

---

## APP-001-ADAPTER-R3-FIX

Date: 2026-11-05
Task: `APP-001-ADAPTER-R3-FIX`

R3 代码主体已完成；本轮只补齐 R3 审查要求的证据和文档同步。

```text
handoff_self_check:
  changed=
    src/llm/prompt_loader.py     (add private _verify_file_hash; refactor load to use it)
    src/llm/README.md            (sync gate, retention, prompt verification to R3 rules)
    tests/llm/test_r3_regression.py (fix tampered artifact test; add symlink escape tests)
    agent-work/llm/APP-001-adapter/checkpoint.md (R3-FIX section appended)
    agent-work/llm/APP-001-adapter/handoff.md (this section)
    docs/PROJECT_STATUS.md (update APP-001-ADAPTER row to R3-FIX)
    docs/WORKLOG.md (append-only R3-FIX entry)
  commands=
    PYTHONPATH=src python3 -m unittest discover -s tests/llm -q → 170 tests, OK
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q → 17 tests, OK
    PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
    git diff --check → PASS
    git ls-files work/ → (empty)
    inspect.signature(Adapter.run) → no verify_frozen_prompt or _prompt_loader_path
    RetentionPolicy fields → no _test_only; no for_test()
  confirmed=
    1. 篡改 artifact 测试: test_tampered_artifact_rejected_by_file_hash 现在创建
       临时篡改文件（保留版本标记），调用 _verify_file_hash() 断言抛出
       FrozenPromptMismatchError。test_tampered_file_hash_differs_from_anchor
       验证篡改 hash 与锚点不同。不修改仓库内 prompt-v2.md。
    2. symlink 越界测试: test_symlink_escape_rejected 在 work/app001-runs/ 下
       创建指向外部目录的 symlink，断言 _resolve_canonical_path() 抛出
       RETENTION_PATH_OUTSIDE_IGNORED_DIR 且外部目录为空。
       test_symlink_escape_rejected_by_retain_response 验证 _retain_response()
       同样拒绝且无文件产生。两个测试实际执行（非手工探针）。
    3. README: 评测门规则更新为精确 FakeTransport 类型检查；Retention 说明
       更新为 canonical root 约束 + symlink 拒绝 + 私有 writer 边界；Prompt
       验证说明更新为无条件核验无绕过。
    Adapter.run() 仍无 verify_frozen_prompt 或 _prompt_loader_path。
    RetentionPolicy 仍无 _test_only 或 for_test()。
    没有真实网络、真实密钥、冻结样例或正式指标。
    没有向 work/ 之外写入响应文件。
  unresolved=
    - IR 映射: 无 src 级参数→IR 适配器；IR/CAD/STEP blocked/not_run。不属本任务。
    - 真实 DeepSeek/Ollama: 未执行；未授权。
    - 九条验收样例: 未运行；标签未读取。
    - 正式性能指标: 全部 not_measured。
    - prompt_loader 两次读文件存在理论 TOCTOU（read_bytes + read_text）；future improvement。
  next_agent_focus=
    - Codex 中枢: 复核 (1) 篡改 artifact 测试真实加载篡改文件并断言拒绝，
      (2) symlink 越界测试实际执行且外部目录无文件，
      (3) README 评测门/Retention/Prompt 验证规则与 R3 实现一致。
    - 如果 R3-FIX 验收通过，项目负责人可授权正式 APP-001 运行。
    - IR src 级映射仍需冻结后才能声称 CAD/STEP 端到端已测。
```

### APP-001 status

`APP-001` remains `planned`.  No formal model run authorized.
`APP-001-ADAPTER` status: `review`, awaiting Codex R3-FIX review.
`formal_evaluation_allowed=false`.
