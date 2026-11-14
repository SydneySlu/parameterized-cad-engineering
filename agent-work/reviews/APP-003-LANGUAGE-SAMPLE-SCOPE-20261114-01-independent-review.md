# APP-003 language sample formal batch 独立复核

- 日期：2026-11-15
- 批次：`app003-product-language-20261114-01`
- 复核基线：本地 `main=2b20d7c`，工作区干净；本地 main 比 `origin/main` ahead 2（本轮复核未 push）。
- 结论：`review`

## 批次证据

- approval binding：通过。审批人为 `Wang sikai`，scope 绑定 `app003-product-language.v1`、DeepSeek `deepseek-flash`、C0、冻结输入 hash、最多 20 HTTP、无自动 CAD。
- summary：`batch_status=partial`，10 个逻辑 run。
- run 分布：`answer=1`、`refuse=1`、`error=8`；L02 的拒绝为 `GATE_DECISION_REFUSE`，L03–L10 为 `TRANSPORT_ERROR`，均每条 1 次尝试。
- ledger：`total_attempts_used=2`、`max_batch_attempts=20`、每条最多 2 次；ledger 中 2 条 attempt 与 summary 一致。
- raw：2 个文件；两个文件均存在，文件 SHA-256 与 summary 中的 `raw_sha256` 匹配。复核只计算哈希和检查元数据，未语义读取 raw 正文。
- 产物隔离：batch 目录内没有 pipeline 文件或 STEP 文件，CAD 调用数为 0。
- 脱敏：summary、ledger 和执行报告未发现 API key、Authorization 值、绝对路径或 evaluator label 内容；summary 仅保留批准字段、错误分类、相对路径和哈希。
- 历史数据：未修改其他 batch，也未重跑或追加请求。

## 验证命令

- `py_compile src/integration/product_language_formal_runner.py src/llm/product_language_authorization.py`：通过。
- `git diff --check`：通过。
- 合入后重新运行 `tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner`：98 项中 7 项失败。
- 失败集中在正式 batch ID `app003-product-language-20261114-01` 已存在后的 `batch_directory_already_exists`：
  - `TestRunLanguageOfflinePreflight.test_no_network_or_credentials_during_preflight`
  - `TestRunLanguageOfflinePreflight.test_valid_preflight_passes`
  - `TestFormalRunnerMockMode.test_mock_all_answer_returns_ten_results`
  - `TestFormalRunnerMockMode.test_mock_ask_response_gives_blocked_status`
  - `TestFormalRunnerMockMode.test_mock_input_ids_match_planned_runs`
  - `TestAllFailedBatchStatus.test_all_error_results_not_complete_status`
  - `TestInputIntegrity.test_input_ids_in_results_match_frozen_order`

## 判断与后续

这些失败是测试使用正式固定 batch ID、而真实运行已合法创建该目录造成的隔离问题；它们没有覆盖到批次 summary/ledger/raw 证据损坏，也没有证明正式 runner 的 live 结果错误。真实 batch 目录和证据必须保持只读，不能删除或重跑来恢复测试绿灯。

在把任务判为 `pass` 前，应做一个不触碰历史 batch 的测试隔离窄修：让离线/mock 测试使用唯一临时 batch ID 或显式隔离 canonical run root，同时保留一个独立用例断言真实 batch 目录存在时 preflight fail-closed。修复后只需重跑语言 scope + formal runner 专项和 `git diff --check`，再更新本报告结论。
