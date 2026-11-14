# APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 checkpoint

- 日期：2026-11-14
- 状态：review
- 目的：形成失败路径修复复核后可供负责人审阅的语言样本 scope，并在负责人批准后完成新 batch 的离线 formal preflight；不调用模型、不建 batch、不执行 live 请求。

## 产物

- `model-inputs.json`：10 条中文需求输入；SHA-256 `8339431ee66a14d838cdbded48240019254182886c85af5cd611e04eaf361801`
- `evaluator-labels.json`：独立标签；SHA-256 `a5055025e4a01740b9bc25daa5ab51e43bdac9748151ccd10c152cdf7151bcf9`
- `scope.md`：候选假设、DeepSeek/C0/no-retrieval、重试/预算和执行前条件。
- `formal-preflight.json`：`app003-product-language-20261114-01` 的批准绑定与离线 preflight 记录。

## 已确认限制

现有 Product Live profile 只绑定 P1–P4，不能直接运行十条新输入。新的版本化 authorization profile、输入/labels 隔离和离线 formal preflight 已完成并通过复核；不能扩写旧批次、旧授权或把评测标签输入模型。本 checkpoint 记录的是已批准的准备 scope，不代表正式 runner 已可发送请求。

## 下一步

离线 formal preflight 已通过并写入 `formal-preflight.json`。真实执行仍被 runner gate 阻断：`run_product_language_batch()` 明确抛出 `offline-preflight-only`，尚无经过独立复核的 formal runner、BudgetLedger、raw/summary 留存与执行报告链路。下一步应先由 CC 实现独立 formal runner，再做固定环境离线测试和独立复核；在该 gate 关闭前不得发送 DeepSeek 请求。

## 本轮实现与验证

- 新增 `src/llm/product_language_authorization.py`、`src/integration/product_language_runner.py`、`tests/integration/test_product_language_scope.py`。
- 固定 CAD venv Python 3.11.18：专项测试 8/8 通过；3 个文件 `py_compile` 通过；`git diff --check` 通过。
- 正常案例：preflight 规划 10 条 logical runs、20 次 HTTP 上限，输入 hash 通过。
- 失败案例：输入 hash 错误、已有 batch 目录、错误 profile/hash、错误授权类型均 fail-closed；执行 API 明确抛出 offline-preflight-only；spy 确认不读 labels、不读凭据、不触网。
- 未调用 DeepSeek、未读取 `.env`/API key、未创建 batch、未执行 CAD。
- 2026-11-14：负责人批准准备 `app003-product-language-20261114-01` 并推进真实 DeepSeek 执行；固定 CAD venv 离线 preflight 通过：10 条输入、20 HTTP 上限、hash/顺序/provider/model/condition/目录检查均通过。记录见 `formal-preflight.json`。本次仍未读取凭据、创建 batch 或触网。

## 下一步

独立复核已通过；具体 batch ID 与 formal preflight 已准备并记录。真实模型执行授权已由负责人给出，但技术执行 gate 仍为 formal runner 未实现；不得将该批准解释为绕过 `offline-preflight-only`。

### 窄修：417139f

- 修复 `ProductLanguageAuthorization.max_chat_attempts_for()` 返回批次上限的问题，正式 accessor 现在强制每条输入最多 2 次；新增反向测试。
- 固定 CAD venv 专项仍为 8/8，`py_compile` 与 `git diff --check` 通过。

## CC 实现：formal runner（本轮）

### 新增产物

- `src/llm/product_language_authorization.py`：扩展 `ProductLanguageFormalApproval`、`ProductLanguageApprovalValidationError`、`validate_product_language_formal_approval_binding`、`make_language_test_approval`；`PRODUCT_LANGUAGE_PROMPT_SHA256` 导入。
- `src/integration/product_language_formal_runner.py`：scope-bound formal runner，包含：
  - 授权、批准、preflight 七层门控（所有 side effects 前完成）
  - `BudgetLedger`+`BudgetAwareTransport` 路径（formal/live）
  - FakeTransport mock 路径（测试用）
  - `_SummaryWriter`：原子写入，仅输出 repo-relative 路径、SHA-256 和批准字段
  - raw 留存路径：`work/app001-runs/{batch_id}/raw/`
  - `run_language_offline_preflight()`、`run_product_language_formal_batch()`
  - 无 CAD/IR/STEP 管道，永不调用 `run_pipeline()`
  - 全批失败时 `batch_status=failed`，非 `complete`
  - `FORMAL_EVALUATION_ALLOWED` 不变
- `tests/integration/test_product_language_formal_runner.py`：76 项专项测试，系统 Python 3.10 通过。

### 验证命令与结果

| 命令 | 结果 |
|---|---|
| `py_compile`（3 个文件） | 通过 |
| `git diff --check` | 通过 |
| `python3 -m unittest tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner` | 84/84 通过 |

正常案例：10 条输入 mock 执行返回 `llm_status=answer`，10 个 input_id 顺序与冻结常量一致，CAD pipeline spy 为零调用。
失败案例：test-only 批准、batch_id 不匹配、错误授权类型均在任何 side effect 前 fail-closed；输入 hash 错误、已有 batch 目录返回 preflight 失败结果；auth 错误的 transport 返回 `llm_status=error`，`batch_status`（逻辑验证）= `failed` 而非 `complete`。

### 已知限制与未运行项

- 系统 Python 3.10 用于本轮测试（venv Python 3.11.18 在 Linux 沙盒中是断链，无法使用）；固定 CAD venv 回归（test_product_live.py 等）留待 Codex 独立复核时在原始 macOS 环境中运行。
- `test_product_live.py` 的 3 个 symlink 相关 ERROR 为 Linux 沙盒权限限制，与本轮无关，本轮无修改 product_live 任何文件。
- 真实网络请求仍未执行；无 `.env`/API key 读取；无 DeepSeek HTTP 调用；无目标 batch 目录创建。
- formal runner 创建 batch 基础设施（BudgetLedger、summary writer、batch dir）仅在 `transport=None`（live 模式）时。mock 模式（FakeTransport）无基础设施，仅测试 preflight + 执行逻辑。
- 分支：`cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER`，尚未 push 或 merge。

### 自检

handoff_self_check:
  changed=src/llm/product_language_authorization.py, src/integration/product_language_formal_runner.py, tests/integration/test_product_language_formal_runner.py, agent-work/integration/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01/checkpoint.md, docs/WORKLOG.md
  commands=py_compile 3/3; git diff --check pass; test_product_language_scope 8/8; test_product_language_formal_runner 76/76; combined 84/84
  confirmed=authorization gate, approval binding, preflight fail-closed, mock execution 10 inputs correct order, CAD never called, labels never read, FORMAL_EVALUATION_ALLOWED unchanged, batch_status logic (all-error→failed not complete), _SummaryWriter path traversal rejected, no absolute paths or secrets in summary
  unresolved=fixed CAD venv (Python 3.11.18) full regression not run in this environment; formal live path (transport=None) not exercised in tests (requires credentials); formal batch infrastructure only tested via _SummaryWriter direct tests
  next_agent_focus=Codex 独立复核：在 macOS 固定 CAD venv 下重跑 Product Live 全回归（108/108 预期）和新专项 76/76；确认 BudgetLedger canonical path check 在正式运行时有效；确认 evaluator labels spy 在 live 模式下也为零；确认 FORMAL_EVALUATION_ALLOWED 不变；批准后方可真实 DeepSeek 执行。
