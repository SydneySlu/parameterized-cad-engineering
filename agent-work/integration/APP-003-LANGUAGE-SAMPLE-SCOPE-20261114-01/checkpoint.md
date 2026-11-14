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

## 独立复核

handoff_successor_check:
  predecessor=APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 / commits 50eda5c, 417139f, 34a65e0
  files_format=pass; profile, runner, tests and frozen input/label files exist and import
  core_rerun=pass; fixed CAD venv language scope 8/8 and affected regressions 109+300+17+13 passed
  normal_case=pass; offline preflight planned 10 logical runs and 20 HTTP with input hash verified
  failure_case=pass; wrong hash/profile/type, existing batch directory and execution API all fail closed
  interface=pass; new profile is isolated from legacy P1-P4 Product Live profile and labels are not loaded
  limits=pass; no model request, credential read, batch creation or CAD execution was performed
  result=pass
  blocking_issue=execution remains blocked by the explicitly offline-preflight-only runner; a separately reviewed formal runner with budget ledger/raw-summary retention is required before any DeepSeek request
