# APP-002-INTEGRATION-A2-SCOPE checkpoint

## Status: in_progress（CC 实现完成，待 Codex 中枢独立复核）

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
