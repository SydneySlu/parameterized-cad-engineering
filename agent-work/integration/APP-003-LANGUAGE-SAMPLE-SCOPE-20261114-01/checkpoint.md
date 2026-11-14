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

### CC 窄修：summary 更新失败处理、异常脱敏、output_root 清理（本轮）

#### 修复 1：summary 更新失败必须尽力结束批次状态

- `writer.update_run()` 失败时设置 `summary_write_failed=True` 并 `break` 停止后续输入处理。
- `finally` 块中：若 `summary_write_failed`，尝试 `writer.finalize(batch_status="aborted")`；成功时 `summary_finalize_error="summary_write_failed_finalized_aborted"`。
- 若 finalize 也失败，`summary_finalize_error="summary_write_failed_and_finalize_failed"`；不泄露绝对路径或异常原文。
- 正常路径（无 update 失败）的 finalize 失败报告为 `"summary_finalize_failed"`（稳定 token）。
- 新增 4 项端到端回归测试（formal 路径 + 全面 mock）：update 失败停止循环、finalize 可恢复报 aborted、双重失败报告、无虚假 complete。

#### 修复 2：异常信息稳定化和脱敏

- formal Adapter 异常：`{"code": "ADAPTER_EXCEPTION", "exception_type": type(exc).__name__, "message": "adapter raised an unexpected exception"}`，不写入 `str(exc)`。
- mock transport 异常：`{"code": "TRANSPORT_EXCEPTION", "exception_type": type(exc).__name__, "message": "transport raised an unexpected exception"}`。
- 新增测试：敏感标记 `SECRET_API_KEY_leaked_in_exception_text` 不进入 `result.as_dict()`、errors 或 summary；已有 attempt 计数和错误分类不回退。

#### 修复 3：清理 raw output_root 接口歧义

- 移除 `run_product_language_formal_batch()` 的 `output_root` 参数（死变量，formal raw 路径始终为 canonical `work/app001-runs/{batch_id}/raw`）。
- 新增测试：函数签名无 `output_root`；raw 路径绑定 canonical batch/raw；mock 模式不创建 canonical batch 目录。

#### 修复 4：同步交接文档

- 更新 checkpoint、PROJECT_STATUS.md、PROJECT_PLAN.md、WORKLOG；修正"formal runner 尚未实现"等过时描述；状态仍为 `review`，`e7e2952`+本轮窄修 commit 尚未通过中枢复核。

### 验证命令与结果

| 命令 | 结果 |
|---|---|
| `py_compile`（3 个文件） | 通过 |
| `git diff --check` | 通过 |
| `test_product_language_scope + test_product_language_formal_runner` | 96/96 通过 |
| `test_product_live` | 109/109 通过（无回退） |
| `tests/schema` | 17/17 通过 |

### 已知限制与未运行项

- 系统 Python 3.10 用于本轮测试（venv Python 3.11.18 在 Linux 沙盒中是断链）；固定 CAD venv 回归留待 Codex 独立复核时在原始 macOS 环境中运行。
- `tests.demo.*` 和 `tests/cad_compilation` 的既有失败（CadQuery/OCP 缺失）与 e7e2952 基线同量，本轮无新增。
- 真实网络请求仍未执行；无 `.env`/API key 读取；无 DeepSeek HTTP；无目标 batch 目录创建；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 分支：`cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER`，尚未 push 或 merge。

### 自检（窄修）

handoff_self_check:
  changed=src/integration/product_language_formal_runner.py, tests/integration/test_product_language_formal_runner.py, docs/PROJECT_STATUS.md, docs/PROJECT_PLAN.md, docs/WORKLOG.md, agent-work/integration/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01/checkpoint.md
  commands=py_compile 3/3; git diff --check pass; test_product_language_scope+formal_runner 96/96; test_product_live 109/109; schema 17/17; cad_compilation 既有 failures=7 errors=5 (与 e7e2952 基线同量)
  confirmed=summary update_run 失败停止循环并 finalize aborted; 双重失败报告稳定 token; 异常 str(exc) 不进入 result/summary; output_root 参数已移除; raw 路径绑定 canonical; FORMAL_EVALUATION_ALLOWED 不变
  unresolved=固定 CAD venv (Python 3.11.18) 全量回归未在此环境运行; formal live 路径 (transport=None) 仅通过 mock 测试间接验证
  next_agent_focus=Codex 独立复核：在 macOS 固定 CAD venv 下重跑全回归；确认 summary 更新失败处理、异常脱敏和 output_root 移除无回退；确认 FORMAL_EVALUATION_ALLOWED 不变；批准后方可真实 DeepSeek 执行。

### CC 第三轮窄修（Adapter 异常分支 break、脱敏测试修正、文档更新）

#### 修复 1：Adapter 异常分支 continue → break

- 在 `adapter_result = run_adapter.run(...)` 抛异常时，`writer.update_run(result)` 失败后立即设置 `summary_write_failed = True` 并 `break`。
- 此前该分支在 write 失败后仍执行 `continue`，导致后续 logical run 继续处理；与正常结果分支（write 失败即 break）不一致。
- 新增端到端回归测试：`test_adapter_exception_with_update_run_failure_stops_loop`（Adapter 抛异常 + update_run 失败，断言 adapter 只被调用 1 次、results 只有 1 条、finalize_error 为双重失败稳定 token）。
- 新增磁盘断言测试：`test_update_run_failure_writes_aborted_to_disk`（finalize 可恢复时读取 `batch_summary.json`，断言磁盘 `batch_status == "aborted"`）。

#### 修复 2：异常脱敏测试修正

- `test_mock_transport_exception_does_not_leak_sensitive_marker`：内部类 `SensitiveTransport.send` 改用外层闭包变量 `marker`（`marker = self.SENSITIVE_MARKER`），不再访问不存在的 `self.SENSITIVE_MARKER`（内部类属性）。
- `test_formal_adapter_exception_sanitized`：改用 `transport=None` formal 路径 + 全面 mock（`_CANONICAL_RUN_ROOT`、`load_deepseek_environment`、`BudgetLedger._verify_canonical_batch_path`、`DeepSeekTransport.send`、`Adapter.run`），真正通过 `Adapter.run` 触发包含 marker 的异常，断言 marker 不出现在 `result.as_dict()`、`batch_summary.json` 和错误 dict 中，且 `code="ADAPTER_EXCEPTION"`、`exception_type` 存在、`message` 为固定稳定字符串。

#### 修复 3：文档更新

- PROJECT_STATUS.md：修正"窄修 commit 待提交"等过时描述，记录 `e7e2952` 和 `8a6a062` 均已提交；第三轮窄修 commit 随本行更新。
- WORKLOG.md：追加本轮修复记录。

### 验证命令与结果

| 命令 | 结果 |
|---|---|
| `py_compile`（2 个文件） | 通过 |
| `git diff --check` | 通过 |
| `test_product_language_scope + test_product_language_formal_runner` | 98/98 通过 |
| `test_product_live` | 109/109 通过 |
| `tests/schema` | 17/17 通过 |

### 已知限制

- 系统 Python 3.10 / Linux 沙盒；固定 CAD venv (Python 3.11.18) 全量回归留待 Codex 复核。
- `tests.demo.*` 和 `tests/cad_compilation` 既有失败与本轮无关。
- 真实 DeepSeek HTTP 仍未执行；`FORMAL_EVALUATION_ALLOWED=False` 不变。

### 自检（第三轮）

handoff_self_check:
  changed=src/integration/product_language_formal_runner.py, tests/integration/test_product_language_formal_runner.py, docs/PROJECT_STATUS.md, docs/WORKLOG.md, agent-work/integration/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01/checkpoint.md
  commands=py_compile 2/2; git diff --check pass; test_product_language_scope+formal_runner 98/98; test_product_live 109/109; schema 17/17
  confirmed=Adapter 异常分支 write 失败后 break 停止后续输入; disk batch_status=aborted 验证; 敏感 marker 不泄漏（formal Adapter 路径真正触发）; stable code/message/exception_type 验证; FORMAL_EVALUATION_ALLOWED 不变
  unresolved=固定 CAD venv (Python 3.11.18) 全量回归未在此环境运行
  next_agent_focus=Codex 独立复核：在 macOS 固定 CAD venv 下重跑全回归（test_product_language_scope 8/8、formal_runner 98/98 预期）；确认 Adapter 异常 break 路径无回退；确认敏感 marker 不泄漏（formal 路径）；确认 FORMAL_EVALUATION_ALLOWED 不变；批准后方可真实 DeepSeek 执行。

### Codex 小修与重新验收（2026-11-15）

- 范围：在 `test_formal_adapter_exception_sanitized` 中将 `batch_summary.json` 的条件式检查改为必须存在后再检查敏感 marker；同步 `PROJECT_STATUS.md` 和 `PROJECT_PLAN.md` 中的第三轮窄修提交状态。
- 基线：分支 `cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER`，起始 HEAD `9a0bb0f`，工作区干净。
- 基线验证：固定 CAD venv Python 3.11.18 下 `PYTHONPATH=src:. ... -m unittest tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner -q`，98/98 通过。
- 修复：脱敏测试要求 summary 文件存在且 marker 不在 summary 中，并在 `TemporaryDirectory` 退出前完成断言。首次硬断言运行暴露了断言写在临时目录清理之后的问题，现已将断言移动到目录生命周期内。
- 验证：固定 CAD venv Python 3.11.18 下语言 scope + formal runner **98/98**；Product Live **109/109**；测试文件 `py_compile` 通过；`git diff --check` 通过。Product Live 有既有 HTTP socket `ResourceWarning`，测试仍通过。
- 限制：未执行 formal live、未读取凭据或 labels、未创建 batch；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 提交：`633fc8d`（`test: require persisted sanitized summary`）；分支仍为 `cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER`，任务状态 `review`，尚未 push/merge。

### Codex 中枢独立复核（R1）

handoff_successor_check:
  predecessor=APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01; R1 fix 633fc8d; documentation c38167d
  files_format=pass; changed paths and commit contents match checkpoint; worktree clean
  core_rerun=pass; fixed CAD venv Python 3.11.18: language scope+formal runner 98/98; Product Live 109/109; py_compile and git diff --check pass
  normal_case=pass; FakeTransport all-answer scenario returns 10 answer runs
  failure_case=pass; formal Adapter exception remains sanitized in result/errors/on-disk batch_summary.json; summary existence required before temp cleanup
  interface=pass; no runner API or frozen input/profile/hash/budget changes in R1
  limits=pass; no real provider request, credentials, evaluator labels, batch creation, or change to FORMAL_EVALUATION_ALLOWED=False
  result=pass
  blocking_issue=none for R1; branch still awaits merge to main and post-merge verification before task completion

- 独立审查记录：`agent-work/reviews/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER-R1-codex-review.md`。

### 合入后复验与收束（2026-11-15）

- 本地 `main` 已包含 formal runner 分支及独立验收记录，HEAD=`6e74487`；工作区干净；`main` 比 `origin/main` ahead 15，尚未 push。
- 合入后固定 CAD venv Python 3.11.18 复验：`tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner` 为 98/98；`tests.integration.test_product_live` 为 109/109，均通过。Product Live 测试输出既有 HTTP socket `ResourceWarning`，不影响退出结果。
- 合入后确认：formal runner、输入/profile/hash/预算和 summary/raw 隔离行为未改变；`FORMAL_EVALUATION_ALLOWED=False` 保持；未读取凭据或 evaluator labels，未创建目标 batch，未发送网络请求。
- 当前状态仍为 `review`，因为真实 DeepSeek 执行尚未开始。下一步由负责人决定是否 push；若启动真实运行，必须沿用已通过的离线 formal preflight，先取得该 batch 的明确执行授权，再创建 batch 并执行，随后由独立复核核对 summary、预算、raw/hash 和失败收束。

### 真实执行授权准备（2026-11-15）

- 已确认 `main` 与 `origin/main` 同步于 `9fc2778`，工作区干净。
- 对既定 batch `app003-product-language-20261114-01` 在固定 CAD venv Python 3.11.18 重跑离线 formal preflight：`ok=true`；10 条冻结输入、inputs hash、prompt hash、DeepSeek `deepseek-flash`/C0、最多 20 HTTP（每条最多 2 次）均通过；batch 目录不存在；未读 evaluator labels、凭据，网络请求为 0。
- 代码的正式执行门要求 `ProductLanguageFormalApproval(is_test_only=False)` 在创建 batch 目录、ledger、transport、读取凭据和网络请求之前完成绑定校验。因此当前不创建实际 batch 目录；已生成 `execution-authorization-request.json` 供负责人审阅和授权。
- 待负责人明确授权后，才创建该 batch 的 canonical 目录并执行真实 DeepSeek 请求；执行后保持无 CAD 管道，由独立复核检查 20 次预算、raw/hash、summary 脱敏和失败收束。

### 真实执行（2026-11-14 UTC）

- 负责人批准执行 `app003-product-language-20261114-01`；approval 记录为 `Wang sikai`、`2026-11-14T18:14:10Z`，精确绑定十条输入、DeepSeek `deepseek-flash`/C0、最多 20 HTTP、无自动 CAD。
- 固定 CAD venv formal runner 实际处理 10 条逻辑输入，使用 2 次 HTTP：L01=`answer`，L02=`refuse`，L03–L10=`TRANSPORT_ERROR`；批次 summary=`partial`，ledger `2/20`。
- 只读证据核对：raw 文件 2 个并有哈希元数据；无 pipeline 文件、无 STEP 文件；没有调用 CAD；summary 未读取 raw 正文，不含 raw 正文、绝对路径或 evaluator labels。历史批次未修改。
- 脱敏执行报告：`execution-report.json`。当前状态为 `review`，等待独立复核；不得把本批次结果扩大为十条语言样本的完整模型效果结论。

### 独立复核（2026-11-15）

- 批次证据一致性通过：approval binding、summary/ledger（2/20）、10 条 run 状态、2 个 raw 文件哈希、无 pipeline/STEP、脱敏边界均通过；复核未语义读取 raw 正文。
- 结论保持 `review`：合入后重跑语言专项时 98 项有 7 项失败，根因是测试固定使用已经合法创建的正式 batch ID，触发 `batch_directory_already_exists`。真实 batch 不删除、不重跑。
- 独立审查记录：`agent-work/reviews/APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01-independent-review.md`。
- 下一步：由 CC 做测试隔离窄修（唯一临时 batch ID 或隔离 canonical run root），并保留真实目录已存在时 fail-closed 的反向测试；修复后再复验并更新结论。
