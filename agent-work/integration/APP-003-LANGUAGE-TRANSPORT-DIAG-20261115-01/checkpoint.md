# APP-003-LANGUAGE-TRANSPORT-DIAG-20261115-01 checkpoint

- 日期：2026-11-15
- 状态：review
- 负责人：Codex 中枢
- 目标：在不修改历史 batch、不读取 raw 正文、不触网的前提下，判断现有证据能否解释 `app003-product-language-20261114-01` 的 L03–L10 transport failures。

## 输入与边界

- 历史 batch：`app003-product-language-20261114-01`；summary=`partial`，budget ledger 显示 2/20 次预留。
- 只读取执行报告、batch summary、budget ledger 的脱敏状态/错误/attempt 元数据，以及当前 formal runner、预算 transport、DeepSeek transport、retry 代码。
- 不读取 raw response body、`.env`、API key 或 evaluator labels；不修改/重跑/追加请求到历史 batch；不运行 CAD；不调用任何网络/provider。
- `FORMAL_EVALUATION_ALLOWED=False` 保持。

## 已确认发现

1. `batch_summary.json` 中 L03–L10 均为 `TRANSPORT_ERROR`，`cause_code=other_non_retryable`、`attempt_outcome=non_retryable`，未记录 HTTP 状态。该摘要没有足以把根因细分为认证、请求格式、服务端状态或连接问题的信息。
2. `budget_ledger.json` 只含 L01、L02 两条预算预留，均为 `is_model_call=true` 且 `outcome=success`；L03–L10 没有对应的预算预留记录。
3. `BudgetLedger` 对每条逻辑输入以 `max_attempts_per_run` 限额，并另以 `max_chat_attempts_for(provider)` 限制 provider 级 chat 总数。产品语言授权 profile 当前将 accessor 错误返回为每条 2 次；因此前两条成功预留后，后续输入的预算预留会在本地被拒绝，尚未进入 `DeepSeekTransport.send()`。runner 将预算拒绝映射为非重试 transport error，能够产生 summary 中的 `other_non_retryable` 现象。
4. summary 的 artifact hash 仅包括 contract、evaluator labels、inputs、prompt file 和 prompt version，没有记录 source commit/runtime revision；summary 也没有保留 L03–L10 的 per-run `llm_meta.attempt_count` 或 HTTP status。因此仅凭当前留存证据无法恢复当时执行代码及 transport 调用细节。
5. 检查了该 batch 的非 raw 文件清单和对应任务目录的文件清单；batch 中只有 `batch_summary.json`、`budget_ledger.json` 与 `raw/` 子目录，任务记录中没有独立的运行终端日志或脱敏 Adapter attempt dump。仅查看 evaluator labels 文件名，未打开文件。

## 结论

离线复现确认当前 checkout 中的 provider 级 chat cap 误设为 2，会在 L01/L02 两次预留后阻止后续输入预留；模拟十条非重试失败时，修正 cap 后十条均有 ledger 记录。该模式与历史 batch 的 2 条 ledger 预留和 L03–L10 错误相符。由于历史 batch 未保存 source commit/runtime revision，仍不能证明当时运行的代码与当前错误版本完全一致；历史根因因此只能记为“当前实现可复现且高度吻合”，不能作绝对归因。不能把旧错误称为 provider 权限或网络响应。历史 batch 仍只读。

修正候选将 `max_chat_attempts_for(provider)` 设为批次额度 20；`BudgetLedger` 独立保留 `max_attempts_per_run=2`，故每条最多 2 次、全批最多 20 次的批准边界不变。固定 CAD venv 下 scope + formal runner 100/100 通过。没有证据表明需要真实 provider 请求来验证这个本地预算门缺陷，因此不创建新 live batch；如以后要诊断真实 provider/网络，仍须新的 scope、batch、preflight 和授权。

## 下一步

1. 对授权 accessor 修正及其 10-input ledger 回归进行独立代码复核；确认通过后合并，并在合并基线上复跑专项测试。
2. 保持历史 batch 只读。当前缺陷可由离线预算门测试验证，不为重复证明本地逻辑而创建 live batch。
3. 若之后需要单独判断 provider/网络行为，再准备新的窄 scope、新 batch ID 和 offline formal preflight，并在任何 live 请求前取得该 batch 的明确执行授权。

## 验证记录

- 仓库：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
- 初始基线：`main=7e92073`；诊断文档随后在 `f146b31`、`0e4a4c4` 更新。预算修正开始前 checkout 为 `main=0e4a4c4`，三个代码/测试文件已有未提交变更；本轮将变更保留并移至 `codex/APP-003-LANGUAGE-TRANSPORT-BUDGET-FIX`。
- 定向复核：`BudgetLedger.reserve_attempt()` 对 per-run 与 provider/chat 总额度的检查顺序；授权 profile accessor；formal runner 预算异常映射。
- 固定 CAD venv：`PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner -q`，100/100 通过。该套件包括 10 条模拟非重试失败均产生 ledger reservation 的回归，也包括 FakeTransport 正常/拒绝路径；未调用网络/provider。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m py_compile src/llm/product_language_authorization.py tests/integration/test_product_language_formal_runner.py tests/integration/test_product_language_scope.py`：通过；`git diff --check`：通过。
- 未读取历史 raw 正文、`.env`、API key 或 evaluator labels；未读取或修改历史 batch 文件；未运行 CAD；`FORMAL_EVALUATION_ALLOWED=False` 未改变。
