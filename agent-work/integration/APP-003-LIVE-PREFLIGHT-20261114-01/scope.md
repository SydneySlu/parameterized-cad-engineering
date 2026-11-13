# APP-003 Product Live Smoke Scope — Candidate 2026-11-14-01

**状态：候选提案，待负责人审阅；不可执行真实请求**
**日期：2026-11-14**
**基线：`main=d80fd433c54d37c135581e92c01c4e4bbee31bb3`**
**候选 batch：`app003-product-live-20261114-01`**

## 目的

在 `APP-003-LIVE-PREFLIGHT-20261113-01` 的代码修复通过独立复核后，用一个全新 batch 验证同一冻结 Product Live scope。上一次真实 batch 的四条输入均在解析/Envelope 阶段失败，未进入用户确认或 CAD；本轮修复改进了错误分类、诊断脱敏和路径隔离。本候选用于重新验证真实 Adapter 结果映射及产品确认链路，不扩大语言样本或产品范围。

这只是候选执行范围。独立复核的 `pass` 和离线 preflight 均不授权 live 请求。负责人须先审阅本文件并批准具体 batch；正式 preflight 和真实请求仍须明确执行授权。

## 固定范围

| 项目 | 候选值 |
|---|---|
| profile | `app003-product-live.v1` |
| sample set | `app003-product-live-smoke.v1` |
| provider / model | DeepSeek / `deepseek-flash` |
| condition | `C0`，无检索 |
| prompt / contract | `app001-extraction.v5` / `app001-io.v1` |
| prompt file SHA-256 | `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9` |
| frozen inputs SHA-256 | `666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a` |
| evaluator labels SHA-256 | `73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795` |
| logical runs | 4 |
| maximum attempts | 3 per logical run; 12 HTTP total |
| CAD pipeline | enabled only after explicit user confirmation of a valid answer |

## 冻结输入与停止规则

本候选沿用 `agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json` 中的既有四条刺激，不修改输入或 evaluator labels：

- `P1-24mm`：合法 24 mm 孔径；须先进入 `needs_confirmation`，再由操作员确认后才允许 CAD。
- `P2-ask-bore`：缺少孔径；应追问或阻断，不得填默认值或运行 CAD。
- `P3-catalog-conflict`：显式目录冲突；必须阻断，不能静默覆盖或生成 STEP。
- `P4-unsupported`：含不支持的表面处理请求；必须阻断，不能因几何字段合法而忽略。

任意 transport、解析、Envelope、Schema、IR、确认、CAD、几何或 STEP 错误均按失败记录；不能报告成功或返回其他 run 的产物。raw 响应按现有隔离策略保存；summary/UI 只保留允许的稳定诊断、repo-relative path 和 hash，不包含 raw 正文、密钥、Authorization header 或 evaluator labels。

## 授权与边界

- 仅使用产品专用 `app003-product-live.v1` gate；不复用 A2 approval、batch 或账本。
- 全局 `FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 旧 batch `app003-product-live-20261113-01` 只读保留；不重跑、不追加请求、不改写历史证据。
- 本候选不授权正式 preflight、创建 batch/ledger、读取 `.env`/密钥、访问 provider、发送 HTTP 或执行正式 CAD。
- 若负责人批准该候选 scope，仍须在正式运行前核对固定 CAD venv、hash、approval binding、batch 目录不存在和最新离线状态；真实执行须另有明确授权。

## 审阅结论

请负责人确认是否批准：同一四条冻结输入、DeepSeek `deepseek-flash` / C0、最多 12 次 HTTP、仅在 P1（或任何其他有效 answer）经人工显式确认后允许 CAD。若需更改输入、预算或处理规则，应先更新 scope 并重新核对 runner 是否支持；当前实现将输入集合和 12 次上限冻结在授权 profile 中。
