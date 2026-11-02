# RET-003 handoff：里程碑 1 协议草案

状态：`review`（等待 Codex 中枢独立审查；未运行正式对照）  
任务：RET-003  
交接方：Codex / RET-003 评测 Agent  
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

## 交付内容

```text
protocol-draft.md       评测协议和放行门
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

## 续任/中枢关注点

```text
predecessor=RET-002（已由中枢放行至 RET-003；manifest/config hash 见 checkpoint）
files_format=四个 RET-003 文档可解析；query-set 只引用现有 sample_id/role
core_rerun=checkpoint.md 中的 verify_manifest、30 tests、smoke、replay 均实际通过
normal_case=source catalog-bore-020；top1 同行、distance 0、3 候选
failure_case=缺少 outer_d 等字段；RETRIEVAL_MISSING_FIELD，结构化拒绝
interface=manifest.parameters.normalized -> RET-002 query；输出保留 role、policy_id、hash
limits=15 行单族、3 候选、provisional_small_n、单固定环境和许可证/几何限制均保留
result=review
blocking_issue=APP-001 尚未完成；C0/C2 端到端比较不能在本里程碑自行执行；等待中枢
               决定 C2 规则先验是否公平且允许进入里程碑 2
```

续任 Agent 若收到放行，应先保持主查询和角色隔离不变，再按协议创建里程碑 2 运行文件；
任何查询、条件、权重、依赖或模型变化必须先追加 checkpoint 并重新请求审查。若放行被拒，
只保留当前 C1 检索级诊断建议，不把参数近邻结果写成语言抽取、CAD 成功率或用户效用收益。
