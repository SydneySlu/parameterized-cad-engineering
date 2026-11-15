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
3. 当前代码路径中，`BudgetAwareTransport.send()` 先调用 `ledger.reserve_attempt()`，随后才将 budget token 交给 `DeepSeekTransport.send()`。因此 ledger 中没有预留记录，不能支持“L03–L10 已向 provider 发出 HTTP 并收到拒绝”的说法。当前源代码只能作为机制证据；仍需核对批次实际运行时的代码版本和当时日志，才能解释 summary/ledger 差异。
4. summary 的 artifact hash 仅包括 contract、evaluator labels、inputs、prompt file 和 prompt version，没有记录 source commit/runtime revision；summary 也没有保留 L03–L10 的 per-run `llm_meta.attempt_count` 或 HTTP status。因此仅凭当前留存证据无法恢复当时执行代码及 transport 调用细节。

## 结论

只读诊断未能确定 L03–L10 的根因；当前最关键的问题是 summary 显示 transport failures，而 ledger 没有对应请求预留。不能把这 8 条错误归因于 DeepSeek provider 权限或网络，也不能据此认定请求已到达 provider。历史 batch 仍只读。

## 下一步

1. 检查是否还保存有不含 raw/凭据的本次执行终端摘要、实际 checkout commit 和脱敏 Adapter run metadata；不要从 raw body 中寻找答案。
2. 若这些信息不存在或差异仍无法解释，将历史根因记录为不可判定。若负责人希望复现，再准备新的窄 scope、新 batch ID 和 offline formal preflight；在任何 live 请求前取得该 batch 的明确执行授权。

## 验证记录

- 仓库：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
- 基线：`main=7e92073`，开始时与 `origin/main` 同步，工作区干净。
- 只读检查：batch summary/ledger 的 allowlisted metadata；`product_language_formal_runner.py`、`budget.py`、`real_transport.py`、`retry.py` 调用链。
- 结果：summary 与 ledger 的 observations 如上；未运行模型测试，因为本工作单元不修改代码。
- `git diff --check`：文档提交前执行。
