# APP-002-INTEGRATION-A2-SCOPE checkpoint

## Status: done（scope 准备、独立复核和合入完成；live 执行待单独授权）

日期：2026-11-11。负责人：CC（实现阶段）。

---

## M1：接口核对与连接层分析（完成）

### 核心连接关系

A2 不重复实现后端，只添加"LLM 调用 → pipeline 调用"的连接层：

| 层 | 已有 / 新增 | 文件 |
|---|---|---|
| prompt 加载 | 已有 | `src/llm/prompt_loader.py`（`load_frozen_prompt()`） |
| request 构建 | 已有 | `src/llm/providers.py`（`build_deepseek_request()`） |
| transport / 重试 | 已有 | `src/llm/transport.py`、`src/llm/retry.py` |
| 解析 | 已有 | `src/llm/parser.py`（`parse_response()`） |
| projection | 已有 | `src/llm/projector.py`（`project_to_cad003()`） |
| Schema 验证 | 已有 | `src/schema/set_screw_shaft_collar.py`（`validate_parameters()`） |
| pipeline | 已有 | `src/integration/pipeline.py`（`run_pipeline()`） |
| 预算账本 | 已有 | `src/llm/budget.py`（`BudgetLedger` / `BudgetAwareTransport`） |
| 实 HTTP transport | 已有 | `src/llm/real_transport.py`（`DeepSeekTransport`） |
| **A2 授权 profile** | **新增** | `src/llm/a2_authorization.py` |
| **A2 受控入口** | **新增** | `src/integration/a2_runner.py` |

关键接口决策：
- `Adapter.run()` 的正式路径（`BudgetAwareTransport`）不需要修改；A2 在 is_formal 时传入 `A2IntegrationAuthorization` 实例。
- mock/offline 路径绕过 Adapter 的 `type(transport) is FakeTransport` 检查，直接调用 `send_with_retry → parse_response → project_to_cad003 → validate_parameters → run_pipeline()`。
- raw 留存路径：正式模式写入 `work/app001-runs/{batch_id}/raw/`（在 `BudgetLedger` 的 canonical root 内）；mock 模式从 FakeTransport 直接获取响应体。
- pipeline 输出：`work/app001-runs/{batch_id}/pipeline-runs/`（`run_pipeline()` 无路径限制，A2 runner 自行指定）。
- `BudgetLedger` 的 canonical root 是 `work/app001-runs/`；A2 batch_id 格式 `app002-a2-smoke-YYYYMMDD-NN` 自然落入其中，无需修改账本。

---

## M2：A2 授权 profile（完成）

文件：`src/llm/a2_authorization.py`

| 常量 | 值 |
|---|---|
| `A2_PROFILE_ID` | `app002-integration-a2.v1` |
| `A2_SAMPLE_SET` | `a2-integration-smoke.v1` |
| `A2_INPUT_IDS` | `("A2-24mm", "A2-80mm", "A2-ask-bore")` |
| `A2_INPUTS_SHA256` | `d290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b` |
| `A2_LABELS_SHA256` | `67fe1e68ed27fbaef420846ac2f7eb92abb402b49134a058f676a4bdb965d6e7` |
| provider | DeepSeek `deepseek-flash`（Ollama 不纳入） |
| condition | C0 only |
| max HTTP | 9（3 runs × 3 attempts） |
| `enable_cad_pipeline` | `True`（显式授权 pipeline 调用） |

`A2IntegrationAuthorization` 继承 `FormalRunAuthorization`，覆盖 `__post_init__` 做完整 A2 scope 检查，所有不符合冻结常量的构造均 raise `AuthorizationScopeError`。

---

## M3：冻结输入和标签（完成）

| 文件 | SHA-256 |
|---|---|
| `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json` | `d290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b` |
| `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/evaluator-labels.json` | `67fe1e68ed27fbaef420846ac2f7eb92abb402b49134a058f676a4bdb965d6e7` |

model-inputs.json 仅含 `input_id`、`condition`、`natural_language`，不含任何 evaluator-only 字段。evaluator-labels.json 仅供人工评估，不进入 runner、prompt、adapter 或任何 transport。

---

## M4：A2 受控入口与离线测试（完成）

文件：`src/integration/a2_runner.py`

入口函数：
- `run_a2_offline_preflight(authorization, *, batch_dir=None)` — 检查 inputs SHA-256、budget 可行性、batch dir 不存在、prompt 可加载；无网络/密钥读取
- `run_a2_batch(*, authorization, dry_run=True, transport=None, output_root=None)` — 主入口；`dry_run=True` 只返回 plan；`dry_run=False` + `transport=FakeTransport` 执行 mock；`dry_run=False` + `transport=None` 准备正式路径（尚未授权）

测试文件：`tests/integration/test_a2_runner.py`，40 项，涵盖：

| 类别 | 覆盖 |
|---|---|
| 授权 scope 验证 | 10 项：合法构造、错误 profile_id、Ollama 拒绝、pipeline 关闭拒绝、空 batch_id、错误 hash |
| offline preflight | 4 项：通过、budget 数字、batch dir 已存在拒绝、inputs SHA-256 被篡改拒绝 |
| dry-run / 无副作用 | 5 项：plan 返回、input IDs、无网络调用、labels 不出现在输出、budget 计划 |
| gate 关闭零副作用 | 2 项：FakeTransport 允许 mock（no real HTTP）、非 FakeTransport 拒绝 |
| mock 成功路径 | 3 项：answer→pipeline 调用 2 次、success 字段正确、step_path 来自当前 run |
| mock ask 路径 | 2 项：pipeline 不调用、questions 记录 |
| mock refuse 路径 | 1 项：pipeline 不调用 |
| mock blocked 路径 | 1 项：missing_fields → pipeline 不调用、step_path=None |
| mock pipeline 失败 | 2 项：failed 状态、step_path=None |
| 输入/标签隔离 | 4 项：labels 不在 plan、inputs SHA-256 匹配、加载无 label 字段、IDs 一致 |
| prompt/版本/hash 锚定 | 3 项：prompt_version、contract_version、prompt_hashes 存在 |
| budget 计划正确性 | 3 项：数字、provider、input_ids |

### 验证命令与结果（VM，Python 3.10，无 cadquery）

```bash
PYTHONPATH=src:. python3 -m py_compile src/llm/a2_authorization.py src/integration/a2_runner.py
# 结果：通过

PYTHONPATH=src:. python3 -m unittest tests.integration.test_a2_runner -v
# 结果：Ran 40 tests; OK

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
# 结果：Ran 17 tests; OK（新文件不影响 Schema 测试）

git diff --check
# 结果：通过（所有新文件均为 untracked）
```

---

## M5：scope 草案（完成，待批准）

见 `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md`。

---

## 未运行项

- `tests/llm/`（LLM 全量）：需 Python 3.11.18 / FUSE mock；VM 未运行；历史已验证 842+8skip 通过（不受新文件影响）
- `tests/cad_compilation/`（CAD 13 项）：需 cadquery/OCP；VM 未运行；新文件不改编译器
- 真实 DeepSeek HTTP 调用：尚无 live 授权，不运行

## 待授权内容

1. Codex 中枢独立复核本 checkpoint 和实现（`a2_authorization.py`、`a2_runner.py`、`test_a2_runner.py`）
2. 项目负责人批准 scope 草案（`scope-draft.md`）
3. 项目负责人填写并批准具体 `batch_id` 和完整授权模板
4. live preflight 在 Mac 固定环境（Python 3.11.18）通过
5. 以上全部通过后，才可执行真实 DeepSeek 请求

## handoff_self_check

```text
changed=src/llm/a2_authorization.py(新建), src/integration/a2_runner.py(新建),
         tests/integration/test_a2_runner.py(新建),
         agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json(新建),
         agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/evaluator-labels.json(新建),
         agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md(新建),
         agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/checkpoint.md(更新)
commands=py_compile(a2_authorization.py, a2_runner.py)通过;
         40项 test_a2_runner 通过;
         17项 Schema 通过;
         git diff --check 通过
confirmed=授权 scope 10项测试; preflight 4项; dry-run 5项; gate 2项; mock success/ask/refuse/blocked/pipeline-fail 9项; 隔离/版本/hash/budget 10项
unresolved=Python 3.11.18 LLM 全量（历史通过，新文件不影响）; cadquery 路径; live preflight 和 live 授权
not_changed=pipeline.py, schema_to_ir.py, adapter.py, contract.py, 旧 runner, 历史批次; FORMAL_EVALUATION_ALLOWED=False
```

## handoff_successor_check（Codex 中枢须核验）

在 Mac 固定环境（Python 3.11.18）：

1. **全量 LLM 测试不受影响**：
   ```bash
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -p 'test_*.py' -q
   # 预期：842+8skip OK
   ```

2. **A2 runner 新增测试**：
   ```bash
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.integration.test_a2_runner -v
   # 预期：40 tests OK
   ```

3. **集成测试回归（已知 VM 失败原因是 cadquery 缺失）**：
   ```bash
   PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q
   # 预期：81+40=121 tests OK（其中 81 项是 A1 原有集成，40 项是 A2 新增）
   ```

4. **Schema + a2_authorization py_compile**：
   ```bash
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m py_compile src/llm/a2_authorization.py src/integration/a2_runner.py
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -p 'test_*.py' -q
   # 预期：通过 / 17 OK
   ```

5. **dry-run preflight**：
   ```bash
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -c "
   from integration.a2_runner import run_a2_batch
   from llm.a2_authorization import authorize_a2_run
   auth = authorize_a2_run(batch_id='app002-a2-smoke-preflight-check')
   r = run_a2_batch(authorization=auth, dry_run=True)
   print('preflight_ok:', r.preflight_ok)
   print('planned_runs:', len(r.planned_runs))
   assert r.preflight_ok, f'FAIL: {r.preflight_errors}'
   print('PASS')
   "
   ```

6. **inputs SHA-256 核对**（防止文件被改）：
   ```bash
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -c "
   import hashlib
   h = hashlib.sha256(open('agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json','rb').read()).hexdigest()
   assert h == 'd290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b', f'MISMATCH: {h}'
   print('inputs SHA-256 OK:', h)
   "
   ```

7. **git diff --check**：无空白错误

8. **任何测试失败或 hash 不匹配**：标记 blocked，记录具体错误代码，不合入 main，不发 live 请求。

---

## R1-CORRECTION-2（2026-11-11，CC）

### 状态：review（待 Codex 中枢独立复核）

### 基线

- 父提交：`230609c`（R1-CORRECTION）
- 工作区开始时干净

### 修复内容

#### 1. 补全正式 answer 路径的 raw retention 传递

`_run_one_logical()` 的 answer 路径在取得 `adapter_result.record` 后，统一从 `record.raw_response_retention` 复制 `answer_retention_meta`。三个 answer 分支（pipeline 成功、raw 不可用/读取失败、pipeline 异常）全部传入 `raw_retention_meta=answer_retention_meta`。

关键约束：
- `raw_retention_path` 只使用 retention metadata 中确认的 repo-relative retained path
- `raw_sha256` 只由 `raw_retention_meta["body_sha256"]` 提供，不从 `ir_index["envelope_sha256"]` 推导
- 无模型响应时 `raw_retention_meta=None`，不伪造 hash
- mock/dry-run 行为不变

#### 2. finalize 失败端到端测试（`TestA2R1Correction2`）

`test_finalize_failure_in_formal_path_via_writer_patch`：
- patch `_SummaryWriter.finalize` → `SummaryWriteError`
- patch `BudgetLedger`、`BudgetAwareTransport`、`DeepSeekTransport`、`_run_one_logical` 使用 mock 替身
- 验证：`summary_finalize_error` 非空；3 条结果完整；`release_lock` 调用；`run_pipeline` 未调用
- 不发网络、不读密钥、不调用真实 DeepSeek

### 新增文件/改动

| 文件 | 改动 |
|---|---|
| `src/integration/a2_runner.py` | answer 路径 3 分支补 `raw_retention_meta=answer_retention_meta` |
| `tests/integration/test_a2_runner.py` | +6 项 `TestA2R1Correction2`（87 项总计） |

### 验证（VM，Python 3.10.12，无 cadquery）

```bash
PYTHONPATH=src:. python3 -m py_compile src/integration/a2_runner.py tests/integration/test_a2_runner.py
# 通过

PYTHONPATH=src:. python3 -m unittest tests.integration.test_a2_runner -q
# Ran 87 tests; OK

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
# Ran 17 tests; OK

git diff --check
# 通过
```

注：结果均为 mock/offline 行为，不代表真实模型效果。

### 未运行项

- Python 3.11.18 下 A2 专项 87 项、LLM 全量、Schema 17 项、Integration 全量、py_compile、git diff --check（需 Mac 固定环境）

### handoff_successor_check（Codex 中枢须核验）

在 Mac 固定环境（Python 3.11.18）：

1. `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m py_compile src/integration/a2_runner.py tests/integration/test_a2_runner.py`
2. `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.integration.test_a2_runner -q` — 预期 87 tests OK
3. `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/integration -p 'test_*.py' -q` — 预期 81+87=168 项全部通过（A1 原有集成 81 项，A2 专项 87 项；固定 CadQuery 环境运行）
4. `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -p 'test_*.py' -q` — 预期 17 OK
5. `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -p 'test_*.py' -q` — 预期 941 OK（8 既有 skip）
6. `git diff --check`
7. 核对：answer 路径 3 分支携带 `raw_retention_meta`；finalize 失败时 `summary_finalize_error` 非空；锁释放；`is_test_only` 拒绝逻辑未修改；`FORMAL_EVALUATION_ALLOWED=False` 未改


## Codex 中枢独立复核（2026-11-12）

### 结果：pass（窄修）；待合并后标记 done

- 提交 `e037cb2` 的代码差异与 R1-CORRECTION-2 记录一致；工作区干净，未发起模型或网络请求。
- Python 3.11.18 验证：A2 专项 `87/87` 通过；固定 CadQuery 环境 Integration 全量 `168/168` 通过；Schema `17/17` 通过；LLM `941` 通过、`8` 个既有 FUSE skip；相关 `py_compile` 和 `git diff --check` 通过。
- 定向复核通过：正式 answer 成功、raw 读取失败、pipeline 异常分支均保留 `raw_retention_meta`；finalize 失败端到端测试确认 `summary_finalize_error` 可见、3 条结果保留且账本锁释放；dry-run 保持无副作用。
- 结论：R1-CORRECTION-2 的实现和测试满足当前窄修验收；该分支尚未合并 `main`，合并后再将 A2 scope 状态更新为 `done` 或进入下一项正式授权流程。

### handoff_successor_check

```text
predecessor=APP-002-INTEGRATION-A2-R1-CORRECTION-2, checkpoint.md, e037cb2
files_format=PASS；代码、专项测试、checkpoint 与 WORKLOG 均存在且工作区干净
core_rerun=PASS；Python 3.11.18 下 A2 87/87、Integration 168/168、Schema 17/17、LLM 941 + 8 skip
normal_case=PASS；dry_run preflight_ok=True，3 个 logical runs 计划生成
failure_case=PASS；finalize 失败端到端测试返回 summary_finalize_error，释放账本锁且不调用 pipeline
interface=PASS；raw_retention_meta 由 formal adapter record 传递，summary 使用 body_sha256
limits=PASS；未运行真实模型/网络，FORMAL_EVALUATION_ALLOWED=False，仍需独立 live scope/approval
result=pass
blocking_issue=无代码阻断；分支尚未合并 main
```

## Live preflight attempt blocked by runner constructor mismatch (2026-11-12)

### Scope and authorization

- Project负责人已明确批准 batch `app002-a2-smoke-20261112-01` 的 live preflight 及 3 条 DeepSeek/C0 整链输入：`A2-24mm`、`A2-80mm`、`A2-ask-bore`。
- 预算和边界未扩大：DeepSeek `deepseek-flash`、C0、最多 3 logical runs、最多 9 次 HTTP，允许 CAD pipeline。

### 实际结果

- 固定环境：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0；inputs SHA-256、offline preflight 和 dry-run 均在执行前通过。
- 正式入口在首个 HTTP 请求之前失败，异常为：
  `TypeError: BudgetAwareTransport.__init__() got an unexpected keyword argument 'real_transport'`。
- 根因：`src/integration/a2_runner.py` 以 `real_transport=...` 调用 `BudgetAwareTransport`；实际 `src/llm/budget.py` 构造器签名要求首个位置参数为 `inner`。
- 实际 HTTP 请求数为 0；未读取 DeepSeek 响应，未生成 raw，未生成 `budget_ledger.json`，锁已释放。
- 入口已创建并保留失败现场目录 `work/app001-runs/app002-a2-smoke-20261112-01/`。其中 `batch_summary.json` 仍有 3 条 `pending`，入口异常造成的 `batch_status=complete` 不得作为成功证据。

### 处置与边界

- 当前 A2 状态改为 `blocked`；不得删除、移动、覆盖或重跑该失败现场，不得换 batch ID，不得再次发请求。
- 交给 CC 做窄修：改用 `BudgetAwareTransport(inner, ledger=..., ...)` 的实际接口，并增加固定环境构造回归与零 HTTP 断言；不得修改 scope、预算、授权、prompt、Schema/IR/CAD、历史批次或 `FORMAL_EVALUATION_ALLOWED`。
- 窄修后必须由 Codex 中枢独立重跑 A2、Integration、Schema、LLM 回归及 `py_compile`/`git diff --check`；只有通过后才能重新进行同一 batch 的 preflight/运行授权复核。

## APP-002-INTEGRATION-A2-LIVE-FIX independent review (2026-11-12)

### Result: code fix passes; original batch remains blocked by preserved directory

- Reviewed `c954741` on `main`; diff is limited to `src/integration/a2_runner.py`, `tests/integration/test_a2_runner.py`, and WORKLOG. `BudgetAwareTransport` now receives `DeepSeekTransport(...)` as positional `inner` and the required `logical_run_id`; `BudgetLedger`/lock setup failures attempt to finalize summary as `aborted`.
- Fixed environment: Python 3.11.18, CadQuery 2.3.0, OCP 7.9.3.0.
- Verification: A2 `92/92`; Integration `173/173`; Schema `17/17`; LLM `941 passed, 8 existing skips`; `py_compile` and `git diff --check 6fdbb86..HEAD` passed.
- Additional offline formal-path probe patched `BudgetLedger`, `_run_one_logical`, and `urlopen`; `run_a2_batch()` constructed all three `BudgetAwareTransport` wrappers with the expected logical/query/condition bindings, made 0 HTTP calls, and finalized the isolated probe summary. Probe used a separate temporary root and did not access credentials or the authorized batch.
- `FORMAL_EVALUATION_ALLOWED=False` remains unchanged. No live request, model, key, or `.env` was accessed.
- Existing authorized batch directory remains untouched and contains only the original `batch_summary.json`. Read-only offline preflight returns `ok=false` because `batch_dir_exists=true`; it also confirms frozen inputs hash, prompt load, and 9-request budget feasibility. The preserved directory prevents reusing this batch ID under the runner's unique-batch rule.
- Conclusion: the code defect is fixed and independently verified. No live batch was executed. To proceed, the project owner must approve a new unique batch ID and reaffirm the same 3-run DeepSeek/C0/9-HTTP scope; do not modify or rerun the existing failure directory.

### handoff_successor_check

```text
predecessor=APP-002-INTEGRATION-A2-LIVE-FIX, commit c954741
files_format=PASS; production fix and five focused regression tests present; working tree clean
core_rerun=PASS; Python 3.11.18 A2 92, Integration 173, Schema 17, LLM 941 + 8 existing skips
normal_case=PASS; offline formal-path probe constructed 3 BudgetAwareTransport wrappers with correct bindings
failure_case=PASS; setup failure unit test finalizes aborted and makes 0 urlopen calls
interface=PASS; inner positional arg + required logical_run_id match src/llm/budget.py
limits=PASS; formal gate false; no HTTP/model/key access; original batch untouched
result=pass_for_code_fix; original_batch=blocked_batch_dir_exists
```

## Second approved batch blocked by APP-001 formal gate (2026-11-12)

### Scope and authorization

- Project负责人批准继续同一 A2 scope，使用新唯一 batch `app002-a2-smoke-20261112-02`：DeepSeek `deepseek-flash`、C0、`A2-24mm`/`A2-80mm`/`A2-ask-bore`、最多 3 logical runs / 9 HTTP、允许 CAD pipeline。
- 既有 `...-01` 目录保持原样，没有删除、移动或覆盖。

### Preflight and execution result

- 固定环境：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0。
- batch `...-02` 离线 preflight 通过：目录初始不存在、inputs SHA-256 匹配、prompt 可加载、预算上限 9 可行。
- `.env` 中凭据只加载到当前进程，未显示或写入值。
- 正式入口启动后，三条 logical runs 全部返回 `ADAPTER_EXCEPTION`，拒绝原因是全局 `FORMAL_EVALUATION_ALLOWED=False`；Adapter 明确要求正式 run gate 开启。
- 没有 `budget_ledger.json`、raw 文件或 STEP；HTTP 请求/attempt 数为 0。模型未被调用。
- 新目录 `work/app001-runs/app002-a2-smoke-20261112-02/` 已创建，仅含 `batch_summary.json`。summary 错误地显示 `batch_status=complete`，但三个 run 均为 error；不得将其视为成功证据。该目录和 batch ID 必须保留，禁止覆盖或重跑。

### 当前阻断与边界

- A2 transport 构造器窄修 `c954741` 已通过中枢代码复核；本次没有发现新的网络或预算绕过。
- 项目事实源仍要求 `FORMAL_EVALUATION_ALLOWED=False`。本次 batch 授权没有明确变更这一全局 gate 的决策；不得绕过 Adapter、临时 monkey patch 或直接修改常量。
- 当前需先决策是否通过 ADR 为 A2 建立明确、受控的正式 gate 路径（同时定义与 APP-001 全局 gate 的关系）；并窄修 runner，让所有 runs 失败时 batch summary 标为 failed/aborted，而非 complete。完成实现、独立审查后，新的 live attempt 仍需新唯一 batch ID 和负责人批准。
- 现有 `...-01`、`...-02` 两个 batch 目录均只读保留、不得重跑；不得扩大输入/provider/condition/预算，不改变 prompt/Schema/IR/CAD 或旧批次。

## APP-002-INTEGRATION-A2-GATE-STATUS-FIX / Codex 中枢 / review / 2026-11-12

### 范围与决策

- 基线：`main=fa87db7`，工作区干净；在 `codex/APP-002-A2-GATE-STATUS-FIX` 隔离分支实施。
- 项目负责人明确要求打开测试需要的权限和 gate。新增 ADR-0021，接受既有 A2 专用 scope + 同 batch 非 test-only approval 作为 formal gate；APP-001 全局 `FORMAL_EVALUATION_ALLOWED=False` 保持不变，未给其他入口授权。
- 旧批次 `app002-a2-smoke-20261112-01` 与 `...-02` 仅依据既有记录保持只读；本次没有读写其目录或 raw 内容，也没有尝试复用 batch ID。

### 定向复核发现与修正

- 根因：A2 创建的 `BudgetAwareTransport.adapter_run_id` 是 `plan.logical_run_id`，但 `_run_one_logical()` 为 Adapter 生成 UUID `run_id`。Adapter 对两者做严格相等校验，因此凭证与 transport 绑定不匹配，拒绝发生在 HTTP 前。
- 修正：formal A2 路径将 Adapter `run_id` 设为同一冻结 logical run ID；非正式路径仍用 UUID。新增针对真实 Adapter gate 的无网络测试：正确绑定通过 gate 到冻结 prompt 验证，错误 ID 仍 fail closed。
- 修正 batch 状态：计划项均返回 `error`/`failed` 时 final summary 为 `failed`；混合失败为 `partial`；运行未完成计划即中止为 `aborted`；全部运行到达非错误终态（含 ask/refuse/blocked）才为 `complete`。

### 验证

Python 3.11.18，均为离线/本地测试，未读取凭据、未发 HTTP、未运行模型：

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.integration.test_a2_runner -q`：96 项通过。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q`：176 项通过。
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -p 'test_*.py' -q`：17 项通过。
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -p 'test_*.py' -q`：941 项通过、8 项既有 skip。
- `py_compile`（runner + A2 tests）和 `git diff --check`：通过。
- 正常路径：正确 A2 transport/Adapter run binding 通过 gate 并到达 prompt 验证 sentinel；ask mock 终态回归保持通过。
- 失败路径：错误 Adapter run ID 仍触发 `FormalEvaluationBlockedError`；三条全 error formal summary 为 `failed`。

### 限制与下一步

- 本提交只完成权限决策和离线代码修正，不是 live 执行批准；无真实模型整链成功证据。
- A2 固定输入、DeepSeek `deepseek-flash`、C0、3 logical runs、9 HTTP cap 和 CAD pipeline scope 未变；预算预留逻辑未改；`FORMAL_EVALUATION_ALLOWED=False` 未变。
- handoff_self_check：`changed=ADR-0021, A2 formal run ID binding, summary status semantics, four focused regression tests, PROJECT_PLAN/PROJECT_STATUS/checkpoint/WORKLOG; commands=A2 96, integration 176, schema 17, LLM 941+8 existing skips, py_compile, diff-check all pass; confirmed=valid A2 binding accepted before prompt validation, mismatched ID rejected, all-error summary failed, global gate remains false; unresolved=independent review/merge and new batch approval; next_agent_focus=review ADR scope, Adapter positive/negative gate test, batch status aggregation, and no change to old batch artifacts or global gate`。
- 下一步：中枢完成独立差异复核并合入后，重新执行新的离线 preflight；再向项目负责人申请一个未使用的新 batch ID 的 live preflight + 三条 DeepSeek/C0 整链执行批准。

## APP-002-INTEGRATION-A2-LIVE-EXECUTION-03 / Codex 中枢 / review / 2026-11-12

### 授权与执行范围

- 负责人明确批准 batch `app002-a2-smoke-20261112-03` 的 live preflight 和三条 DeepSeek `deepseek-flash` / C0 整链输入：`A2-24mm`、`A2-80mm`、`A2-ask-bore`；每批最多 9 次 HTTP，允许 A2 CAD pipeline。
- 执行前核实当前分支 `codex/APP-002-A2-GATE-STATUS-FIX`、HEAD `1dc61bc`、工作区干净；当前代码修复尚未合入 `main`。
- Python 3.11.18 离线 preflight 通过：冻结 inputs hash 匹配、v5 prompt 可加载、预算 9/9 可行，batch 目录不存在。
- 凭据只在一个 Python 进程内从 `.env` 提取到 `DEEPSEEK_API_KEY`；未打印、未写入其他文件。未读取 evaluator labels 或 raw 正文。

### 真实执行结果

- batch 目录：`work/app001-runs/app002-a2-smoke-20261112-03/`。该批次现已使用，必须只读保留，不得复用、覆盖或重跑。
- 三条输入均实际发出 1 次 HTTP；账本合计 3/9 次，三条 attempt 均返回成功的 HTTP transport 状态。
- `A2-24mm`、`A2-80mm`：LLM 状态为 `answer`，但 CAD pipeline 在 IR Schema 校验处失败，错误码均为 `CAD_SCHEMA_VALIDATOR_UNAVAILABLE`；没有 STEP。
- `A2-ask-bore`：LLM 状态为 `ask`，按构造门正确停止，没有调用 CAD。
- `batch_summary.json` 最终 `batch_status=partial`，与两条 pipeline 失败、一条 ask 的结果一致；raw 留存位于该批次 `raw/`，summary 仅保存路径和 SHA-256。
- 没有读取或输出 raw 正文、密钥值；没有检查 evaluator labels。

### 根因与处置

- 入口由 `/opt/homebrew/bin/python3.11` 运行。该解释器没有安装 `jsonschema`，A2 在线执行仍能发请求，但 A1 pipeline 的 IR Draft 2020-12 验证因此 fail closed。
- 已确认项目固定 CAD 运行时 `work/benchcad-output/venv/bin/python` 同为 Python 3.11.18，具备 `jsonschema 4.26.0`、Draft 2020-12、CadQuery 2.3.0 和 OCP 7.9.3.0。后续执行必须使用该解释器启动整个 A2 runner。
- 结果展示脚本在读取返回对象时错误访问不存在的 `summary_status` 属性，造成外层进程在三条 run 已完成及 summary 写入之后以 AttributeError 退出；这不影响持久化批次事实。应以 `batch_summary.json` 和 `budget_ledger.json` 为批次状态事实源。
- 不在当前 batch 上补跑 CAD 或更新其 summary，以免重写已经完成的批次记录。若要重新取得真实模型→STEP 证据，须改用固定 CAD venv、分配新唯一 batch ID，并由负责人单独批准新批次。

### 验证及 handoff

- 固定环境检查：系统 Python `/opt/homebrew/bin/python3.11` 缺少 `jsonschema`；CAD venv 为 Python 3.11.18 / `jsonschema 4.26.0` / Draft202012Validator / CadQuery 2.3.0 / OCP 7.9.3.0。
- 批次只读统计：3 次预算 attempt，最大 9；结果 2 条 answer→pipeline failed、1 条 ask；summary=`partial`；无 STEP。
- 结论：本次成功验证了真实模型调用、answer/ask 分流和批次留证，但未完成整链 STEP 验收。A2 维持 `review`，不得将本次表述为整链通过。
- 下一步：代码差异复核/合并到 main 后，使用 CAD venv 重跑新 ID 的离线 preflight；向负责人说明 `-03` 作废并只读保留，再申请新的 live 批次授权。全局 `FORMAL_EVALUATION_ALLOWED=False`、ADR-0021 专用 A2 gate、冻结 scope 和预算不变。

## APP-002-A2-CAD-RUNTIME-PREFLIGHT-GUARD / Codex 中枢 / review / 2026-11-12

- 目标：防止 A2 正式执行在不具备 Draft 2020-12 Schema 验证或 CAD 运行时的 Python 环境中先消耗模型 HTTP 预算，再于 CAD 阶段失败。
- 修正：`run_a2_offline_preflight(..., require_cad_runtime=True)` 增加依赖检查，校验 `jsonschema.Draft202012Validator`、CadQuery 和 OCP 可导入；formal `run_a2_batch()` 在任何目录、账本、transport 或 HTTP 前调用此检查。dry-run/mock 保持可在轻量 Python 环境执行。
- 测试：新增两项回归，覆盖 runtime 缺失时 preflight fail closed，以及正式入口零批次目录/零 BudgetLedger/零 DeepSeekTransport 副作用。
- 验证：固定 CAD venv Python 3.11.18 下 A2 专项 98/98 通过；formal runtime preflight 通过并识别 jsonschema 4.26.0、Draft 2020-12、CadQuery 2.3.0、OCP 7.9.3.0。系统 Python 3.11.18 的同一 preflight 失败并列出缺少 jsonschema/cadquery。`py_compile` 与 `git diff --check` 通过。
- 边界：仅预检依赖，不安装/升级 Python 包，不修改冻结模型 scope、预算、授权或 `FORMAL_EVALUATION_ALLOWED=False`；未发网络/模型请求；历史与 `...-03` 批次保持只读。
- handoff_successor_check：`predecessor=APP-002-INTEGRATION-A2-LIVE-EXECUTION-03, commit=192c58c`; `files_format=新增 runtime capability preflight，并保持 dry-run/mock 行为`; `core_rerun=CAD venv A2 suite 98/98 + positive/negative formal preflight`; `normal_case=固定 CAD venv 通过并识别预期依赖版本`; `failure_case=系统 Python 缺 jsonschema/cadquery 时拒绝，正式入口 mock regression 断言零副作用`; `interface=A2 frozen 3-input / DeepSeek C0 / 9 HTTP scope unchanged`; `limits=no live request; batch -03 immutable; new batch requires separate owner approval`; `result=review`。
- 下一步：Codex 中枢独立复核该 guard 并合入后，live 运行统一通过 CAD venv 启动；新 batch ID 和 live 执行仍须项目负责人另行批准。
