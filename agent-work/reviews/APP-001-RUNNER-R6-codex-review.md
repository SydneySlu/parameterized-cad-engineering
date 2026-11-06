# APP-001-RUNNER-R6 Codex 中枢独立审查

日期：2026-11-07
审查对象：本地分支 `cc/APP-001-RUNNER-R3` 的 commit `9d83219` 及其 R2-R6 交接材料
审查方式：本机源码检查、独立测试复跑、正常/失败路径抽查；未调用真实 API、未读取 API key、未运行正式 APP-001。

## 结论

R2-R6 的代码修复和测试证据通过本次中枢独立审查。预算 reservation 的进程内并发领取已由 `BudgetLedger._thread_lock` 与 `_claim_pending_reservation()` 共同保护；C1 `RetrievalIndex` 的 manifest、策略、候选角色和默认 top-k 均与冻结 RET-002 配置绑定。

`APP-001-RUNNER` 仍保持 `review`，因为 `9d83219` 尚未 push 或合入 `main`。这不是代码阻塞，而是仓库交付状态门。合入前不得把 runner 标记为 `done`，也不得启动正式评测。

## 独立验证

使用 Python 3.11.18、`PYTHONPATH=src:.`：

```text
tests.llm.test_r3_fixes                 51 passed
tests.llm.test_r3_regression            22 passed
tests/llm 全量                          389 passed, 8 skipped
tests/schema 全量                       17 passed
py_compile budget.py real_transport.py  passed
git diff --check                         passed
```

8 个 skip 是已记录的 FUSE lock 清理限制，不计入通过；没有新增失败。

正常路径抽查：R3 专项中的 DeepSeek 正常预算领取、Ollama tags→chat 两阶段记账和合法冻结 RetrievalIndex 均通过。

失败路径抽查：R6 两线程争抢同一 reservation 时恰好一个 token 成功，另一个在网络调用前以 `BudgetBypassError` 拒绝；R5 的错误 `candidate_roles`、缺失字段和错误 `default_top_k` 均在正式运行前拒绝。

## Git 与交接状态

- 审查开始时工作区干净，HEAD 为 `9d83219`；审查结论和项目状态随后通过独立文档提交同步。
- `.git/index.lock` 当前不存在；未删除仍由进程持有的其他 Git maintenance lock。
- R3-FIX-R2/R3/R4/R5/R6 checkpoint、handoff 和 WORKLOG 均已纳入本地 commit。
- `PROJECT_STATUS.md`、`PROJECT_PLAN.md` 已同步为 R6 独立复核通过、等待 push/合入 main。

## 保留限制

- 没有真实 DeepSeek/Ollama 请求，因此尚无模型质量、token、费用或延迟结果。
- Ollama `/api/tags` 计入物理 HTTP 预算但不计入每 logical run 的模型调用额度，导致其可用 chat 额度低于 54；这是已确认的 ADR-0014 口径。
- 8 个 FUSE lock skip 仍需在原生非 FUSE 环境重新运行时才能解除。

## 下一步

1. 将 `9d83219` push 并合入 `main`。
2. 合入后按 ADR-0014 既有授权运行 APP-001 第一阶段：9 样例、C0/C1、双模型、36 个逻辑运行，物理 HTTP 总上限 108。
3. 正式运行结果完成中枢验收后，再更新 APP-001 和 RET-003 的结果状态。
