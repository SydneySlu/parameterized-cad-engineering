# RET-003 handoff：里程碑 1 协议修正版

状态：里程碑 1 `accepted`；RET-003 `in_progress`（仅 C1 检索级诊断获准）
任务：RET-003
交接方：Codex / RET-003 原执行 Agent
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

当前状态（2026-11-03）：中枢已通过里程碑 1 协议，并仅放行 C1 检索级诊断；公平 C2
仍未定义，APP-001 前端到端比较未放行。不得运行 C0/C2O/公平 C2 或调权重。详见
[`RET-003-codex-review.md`](../../reviews/RET-003-codex-review.md)。

## 交付内容

```text
protocol-draft.md       评测协议和放行门（v0.1；C2O oracle）
query-set-draft.json    3 个主 held-out 查询 + 诊断引用
checkpoint.md           实际复核命令、结果、限制和自检
handoff.md              本交接说明
```

只追加 `docs/WORKLOG.md`。没有修改上游源码、manifest、RET-002 配置、Schema、IR、CAD
编译器/验证器、正式状态页或决策记录；没有提交 STEP、渲染物、第三方图纸或 Public/Core
资产。

## 交接方实际验证

```text
RET-001 verify_manifest.py --tracked-only: 15 records / 660 checks / 0 failures
RET-002 retrieval tests: 30 passed
RET-002 run_smoke.py: 3 cases PASS; 13/13 failures expected; determinism PASS;
                     canonical SHA 0fcf84b7...
RET-002 replay_query.py (catalog-bore-020): catalog_validated, top1 catalog-bore-020,
                                           3 results, SHA 0fcf84b7...
```

定向案例已确认：`catalog-bore-080` held-out 只用于查询，top-1 为
`catalog-bore-050`，结果没有 `catalog-bore-080` 且候选角色全为 `retrieval_source`；
缺少 flat 字段返回 `RETRIEVAL_MISSING_FIELD`。复跑产生的时间戳报告已恢复到 HEAD。

## 当前执行与交接边界

```text
predecessor=RET-002（已由中枢放行至 RET-003；manifest/config hash 见 checkpoint）
files_format=四个 RET-003 文档可解析；query-set 只引用现有 sample_id/role
core_rerun=本轮重跑 RET-002 retrieval unittest 30/30；query JSON 与 diff check 通过；上轮
           verify_manifest/smoke/replay 均实际通过
normal_case=source catalog-bore-020；top1 同行、distance 0、3 候选
failure_case=缺少 outer_d 等字段；RETRIEVAL_MISSING_FIELD，结构化拒绝
interface=manifest.parameters.normalized -> RET-002 query；输出保留 role、policy_id、hash
limits=15 行单族、3 候选、provisional_small_n、单固定环境和许可证/几何限制均保留
result=milestone_1_accepted; RET-003=in_progress
authorized=C1 检索级诊断（3 个主查询 + 2 个分开报告的接口诊断 + 1 个失败诊断）
not_authorized=C0/C2O/fair-C2 comparison; sensitivity analysis; endpoint-level claims
blocking_issue=APP-001 未完成、fair C2 未定义；端到端字段/Schema/CAD/STEP/成本均 not_measured
```

执行 Agent 按独立 C1 Prompt 运行已获准的诊断，保持查询、候选角色和 RET-002 policy 不变；
任何查询、条件、权重、依赖或模型变化必须先追加 checkpoint 并重新请求审查。不得把参数
近邻结果写成语言抽取、CAD 成功率或用户效用收益。
