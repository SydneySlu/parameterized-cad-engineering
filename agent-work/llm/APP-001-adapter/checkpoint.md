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

---

## APP-001-ADAPTER-R1 corrections (2026-11-05)

Codex review `APP-001-ADAPTER-codex-review.md` flagged 4 required fixes and
3 contract clarifications.  All 7 have been addressed.

### Fixes applied

**3.1 Mock credential isolation:**
- `build_deepseek_request()` no longer reads `os.environ["DEEPSEEK_API_KEY"]`
  or accepts an `api_key` parameter.  All mock-path requests have `authorization=None`.
- `FakeTransport.send()` now stores `request.sanitized()` (authorization cleared)
  in `calls`.  `last_call()` also returns the sanitized copy.
- Removed the `api_key` kwarg from `build_deepseek_request()`.
- Added `MockTransport` base class so the gate can distinguish safe mock
  transports from potentially network-capable ones.

**3.2 Formal evaluation gate enforced unconditionally:**
- `Adapter.run()` no longer accepts `allow_real_network` kwarg.
- Gate check: any transport that is NOT a `MockTransport` subclass is refused
  before `send()` is called, unconditionally.  `FakeTransport` is a
  `MockTransport` and always allowed.  No env variable bypass.

**3.3 Cost not_available on incomplete/inconsistent usage:**
- `compute_cloud_cost()` no longer falls back to treating all prompt tokens as
  cache miss.  Both cache fields must be present, non-negative integers.
- Added consistency check: `cache_hit + cache_miss == prompt_tokens` required.
  If not, cost is `not_available` with an explicit reason string.
- Bool, negative, or missing fields all yield `not_available`.

**3.4 Total elapsed includes backoff:**
- `send_with_retry()` now returns a 3-tuple: `(response, outcomes, total_elapsed_ms)`.
- `total_elapsed_ms` is measured from before the first attempt to after the
  final outcome, including all sleeper calls.
- `RunRecord.total_elapsed_ms` and `local_wall_time_ms` use this value.

**3.5 Strict JSON parser:**
- Added `_walk_check_finite()` post-parse walk to reject non-finite floats
  (NaN, ±Infinity) from non-standard JSON parsers.  Python 3.10's `json.loads`
  accepts bare `NaN`; the walk catches it with `NON_FINITE_VALUE`.
- Added per-element type checks for `unsupported_requests`, `missing_fields`,
  `questions` (each element must be a string).
- Added per-field type checks for evidence entries: `field`, `quote`, `source`
  must all be strings.

**4.1 Raw response retention implemented:**
- Added `RetentionPolicy` dataclass to `adapter.py`.  Default: `retain_raw=False`.
- `_retain_response()` writes to a git-ignored `base_dir` only when explicitly
  enabled.  Returns metadata dict (retained, path, body_length, body_sha256).
- `RunRecord.raw_response_retention` carries this metadata.  Raw body never
  appears in `RunRecord` JSON, stdout, or tracked files.
- Retention failures (OSError) recorded with `retention_failed: true`; not
  silently swallowed.

**4.2 Prompt hash recorded:**
- `AdapterInput` gains `system_prompt_sha256()`, `user_template_sha256()`,
  `rendered_payload_sha256(rendered_user)` methods.
- `RunRecord.prompt_hashes` dict records all three SHA-256 hashes.
- The adapter stores prompt hashes before the first transport call.
- Prompt text is never stored in the run record.

### Test additions

36 new tests across `test_retry.py` (elapsed time) and new
`test_r1_regression.py` (cost, parser, retention, prompt hash).

### Verification commands

```text
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py  → OK
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v       → 121 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
git diff --check  → PASS
```

### Status

```text
task=APP-001-ADAPTER-R1
status=review
APP-001-PREP=review
APP-001=planned
formal_evaluation_allowed=false
commit=2a324f7 (fix: address APP-001-ADAPTER Codex review R1 corrections [APP-001-ADAPTER-R1])
```

---

## APP-001-ADAPTER-R2 corrections (2026-11-05)

Codex review `APP-001-ADAPTER-R1-codex-review.md` flagged 3 remaining issues.
All 3 have been addressed.

### Fixes applied

**4.1 Gate exact type check (R1 → R2):**
- Changed gate from `isinstance(transport, MockTransport)` to
  `type(self.transport) is FakeTransport`.
- Any MockTransport subclass, duck-type, or anonymous transport is refused
  before `send()`; only exact `FakeTransport` type is allowed.
- Existing tests updated to add `verify_frozen_prompt=False` where needed
  (all synthetic-prompt tests bypass prompt verification as intended).

**4.2 Retention path fixed to work/app001-runs/:**
- Added `_resolve_canonical_path()` that validates paths against
  `work/app001-runs/` before any write.
- `RetentionPolicy.validate_for_production()` raises
  `RETENTION_PATH_OUTSIDE_IGNORED_DIR` for out-of-bounds paths.
- Added `RetentionPolicy.for_test(base_dir)` factory (test-only; raises
  `RETENTION_TEST_ONLY_POLICY` if `validate_for_production()` is called).
- `_retain_response()` now uses `_allow_test_path` flag for test-only paths.

**4.3 Frozen prompt artifact verification:**
- New module `src/llm/prompt_loader.py`:
  - `load_frozen_prompt()` reads `prompt-v2.md`, verifies version marker,
    extracts system prompt (prose) and user template (fenced block).
  - Normalizes `{{placeholder}}` → `{placeholder}` for Python .format().
  - `verify_adapter_input()` checks system prompt + user template hash.
  - `FrozenPromptMismatchError` raised on artifact missing/unreadable/mismatch.
- `Adapter.run()` calls `verify_adapter_input()` before `send()` by default.
- `verify_frozen_prompt=False` available for test-only synthetic prompts.
- `_prompt_loader_path` test parameter for pointing at custom artifact files.

### New test files

`tests/llm/test_r2_regression.py`: 22 tests covering:
- 4.1: MockTransport subclass refused (send_calls=0); duck-type refused;
  FakeTransport exact type passes; FakeTransport subclass refused; gate
  fires before env read.
- 4.2: Production policy external path rejected; path traversal rejected;
  for_test() writes to tempdir; test-only policy rejected by validate_for_production;
  write failure recorded not swallowed; default no-write behavior.
- 4.3: Correct frozen prompt passes; modified system/template rejected; missing
  artifact rejected; send_calls=0 on all failure paths; prompt text not in record;
  hashes match frozen artifact.

### Verification commands

```text
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 143 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
git diff --check → PASS
secret scan → no real credentials
```

### Status

```text
task=APP-001-ADAPTER-R2
status=review
APP-001-PREP=review
APP-001=planned
formal_evaluation_allowed=false
commit=c9abdcb
```

---

## APP-001-ADAPTER-R3 corrections (2026-11-05)

Codex review `APP-001-ADAPTER-R2-codex-review.md` flagged 2 remaining issues.
Both addressed.

### Fixes applied

**A. Prompt verification bypass removed:**
- Removed `verify_frozen_prompt` and `_prompt_loader_path` parameters from
  `Adapter.run()`. Verification is now unconditional.
- Added `FROZEN_PROMPT_FILE_SHA256` constant to `prompt_loader.py`:
  SHA-256 of frozen `prompt-v2.md` bytes. File hash is checked when loading
  from the canonical path; modified content (even if version string is
  preserved) raises `FrozenPromptMismatchError`.
- All tests that needed synthetic prompts now use `_frozen_input()` from the
  new `tests/llm/_frozen_helpers.py` (loads the real frozen artifact content).

**B. Retention `_test_only` bypass removed:**
- Removed `_test_only` dataclass field from `RetentionPolicy`.
- Removed `for_test()` factory from `RetentionPolicy`.
- Removed `validate_for_production()` method from `RetentionPolicy`.
- Removed `_allow_test_path` parameter from `_retain_response()`.
- Extracted `_write_raw_to_dir()` as a private function that tests can call
  directly with a tempdir; production `Adapter` always uses canonical root.
- `_retain_response()` now always resolves via `policy.resolved_dir()` which
  calls `_resolve_canonical_path()` and rejects external paths.

### Test additions

- `tests/llm/_frozen_helpers.py`: shared `_frozen_input()` helper.
- `tests/llm/test_r3_regression.py`: 19 new R3 regression tests.
- Updated `test_adapter.py`, `test_security.py`, `test_r1_regression.py`,
  `test_r2_regression.py` to use `_frozen_input()` and remove bypasses.

### Verification

```text
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 167 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
git diff --check → PASS
git ls-files work/ → (empty; no run artifacts committed)
```

### Status

```text
task=APP-001-ADAPTER-R3
status=review
commit=750897d
```

---

## APP-001-ADAPTER-R3-FIX (2026-11-05)

R3 代码主体已完成；本轮补齐 R3 审查要求的证据和文档同步。

### Fixes applied

1. **篡改 artifact 测试修正:**
   - `test_tampered_artifact_rejected_by_file_hash` 现在真正创建临时篡改文件
     （保留 `app001-extraction.v2` 版本标记，修改正文内容），调用私有
     `_verify_file_hash()` 函数加载并断言抛出 `FrozenPromptMismatchError`。
   - 新增 `test_tampered_file_hash_differs_from_anchor` 验证篡改内容 hash 与
     锚点不同。
   - 新增私有 `_verify_file_hash()` 辅助函数到 `prompt_loader.py`，不暴露
     为 Adapter 公开参数。

2. **symlink 越界测试补齐:**
   - `test_symlink_escape_rejected`: 在 `work/app001-runs/` 下创建指向临时
     外部目录的 symlink，调用 `_resolve_canonical_path()` 断言抛出
     `RETENTION_PATH_OUTSIDE_IGNORED_DIR`，并验证外部目录无文件。
   - `test_symlink_escape_rejected_by_retain_response`: 通过 `_retain_response()`
     验证 symlink 越界被拒绝且外部目录无 raw response 文件。
   - 不支持 symlink 的平台使用 `skipTest` 明确跳过。

3. **README 同步:**
   - 评测门规则更新为：只允许精确类型 `FakeTransport`；MockTransport 子类、
     FakeTransport 子类和 duck-type 均拒绝。
   - Retention 说明更新为：生产路径固定 canonical `work/app001-runs/`；
     `base_dir` 越界、路径穿越和 symlink 越界均拒绝；私有
     `_write_raw_to_dir()` 不是生产绕过接口。
   - Prompt 验证说明更新为：`Adapter.run()` 无条件核验，无绕过参数。

### Verification

```text
PYTHONPATH=src python3 -m unittest discover -s tests/llm -q → 170 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q → 17 tests, OK
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
git diff --check → PASS
git ls-files work/ → (empty)
git status --short → clean except staged R3-FIX changes
inspect.signature(Adapter.run) → no verify_frozen_prompt or _prompt_loader_path
RetentionPolicy fields → no _test_only; no for_test() factory
```

### Status

```text
task=APP-001-ADAPTER-R3-FIX
status=review
APP-001-PREP=review
APP-001=planned
formal_evaluation_allowed=false
commit=c0543d6
```

真实模型、九条冻结样例、正式字段/CAD/STEP 指标均未运行。
IR → Typed CAD IR 映射仍未冻结，不属本任务。
