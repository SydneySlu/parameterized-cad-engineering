# RET-003 检索评测工作区

## 当前有效材料

- `protocol-draft.md`：已接受的 C1 协议边界；C2O 只作为 oracle/上界诊断，当前未运行。
- `query-set-draft.json`：冻结的查询引用集合。
- `run_c1_diagnostic.py`：唯一正式 C1 执行入口。
- `c1-diagnostic-results.json`：固定环境生成并验收的正式机器结果。
- `generate_report.py`：从正式 JSON 生成报告。
- `c1-diagnostic-report.md`：由正式 JSON 自动生成并通过交叉核对的报告。
- `cross_check.py`：JSON/报告一致性检查及 stage/fields 负例自测。
- `checkpoint.md`、`handoff.md`：追加式当前 checkpoint 和交接记录。

## 历史材料

`c1-diagnostic-report-v2.md`、`SUMMARY.md` 和 `BOUNDARY_FIX_REPORT.md` 保留为修正过程记录；其中 v2 报告明确标记为历史无效产物。CC 运行在非基线环境时产生的 v2 脚本、环境门报告和 v2 checkpoint/handoff 已移至
`agent-work/reviews/archive/RET-003-C1-legacy-2026-11-04/`。

当前目录中的正式 JSON/报告只反映检索级 C1 诊断：单族、15 条 manifest、3 条 retrieval_source 候选和 `provisional_small_n`。它们不证明端到端 CAD 生成收益；端到端指标等待 APP-001。
