# RET-004 配对真实 C0/C1 描述性结果

日期：2026-11-16
批次：`ret004-paired-live-20261116-01`
Profile：`ret004-paired-live.v1`
Provider/model：DeepSeek `deepseek-flash`
条件：C0 无检索；C1 注入 RET-002 top-k=3 的 `retrieval_source` 不可信参考

## 结果

本批次包含 2 条冻结输入、4 个 logical run，共使用 4 次 HTTP，预算上限为 8 次。四个 run 均各请求一次并完成终态。

| 输入 | C0 | C1 | 后续链路 |
|---|---|---|---|
| R01 `collar-bore24` | `answer`，`bore_d=24`，需确认 | `answer`，`bore_d=24`，需确认 | 两个条件分别确认后均完成 CAD、STEP 导出和回读 |
| R02 `collar-bore24-anodizing` | `refuse`，包含 `anodizing` | `refuse`，包含 `anodizing` | 两个条件均 `blocked` / `denied_by_scope`，未运行 CAD |

R01 C0 与 C1 的抽取参数相同，均为 `bore_d=24`；两个条件的确定性后续链路结果也均成功。R02 C0 与 C1 的拒绝和 CAD-deny 结果相同。就这两条输入而言，没有观察到检索上下文改变抽取、规则门控或 CAD/STEP 结果的证据。

## 产物与隔离

- batch summary 为 `complete`，4 个计划 run 均有终态。
- ledger 记录 4 次已完成 HTTP 尝试，未超过 8 次批次上限或每 run 2 次上限。
- R01 C0 STEP SHA-256：`831a569efad97a779e7fa3abcfa962cdc54a2cebed5e9fd5e8d75ce1f7c8ad01`。
- R01 C1 STEP SHA-256：`2e1246ec22cfcc0b9642363eff8180ecc9d1be04c0463a6006fe3befb7ebbfee`。
- 两个 STEP 哈希均与 batch summary、pipeline index 和实际文件字节一致。
- R02 没有 pipeline 目录或 STEP 文件。
- 4 个 raw 文件保留相对路径和 SHA-256；本报告未读取 raw 正文、凭据或 evaluator labels。

## 解释边界

这是两个输入上的配对描述性结果，不是统计实验结论。样本量不足以判断检索是否普遍改善真实语言抽取、Schema 通过率、CAD 成功率或用户效用，也不能证明跨族泛化、生产就绪或制造认证。后续若扩大样本，必须另建版本化 scope、预算、preflight、batch 和负责人授权；不得复用本批次。
