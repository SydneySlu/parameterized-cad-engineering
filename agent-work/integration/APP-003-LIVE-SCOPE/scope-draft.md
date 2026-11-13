# APP-003 产品 Live Extraction Smoke Scope（草案）

**状态：提案，待项目负责人审阅与批准；不可执行**
**日期：2026-11-13**
**关联：ADR-0023、APP-003-C1/C2/C3**

## 目的与边界

在 C3 离线产品 UI 已合入并通过浏览器验收后，准备一个最小产品入口真实抽取 smoke scope，验证“浏览器请求 → 服务端受控 v5 抽取 → 用户确认 → 既有 Schema/IR/CAD/STEP”连接是否能安全运行。它不是完整效果评测、语言泛化评测或制造认证。

本文件仅供审阅，不授权 live preflight、batch 创建、provider 请求或 CAD pipeline 执行。需先由负责人批准 scope、明确唯一 batch ID，并在实现、固定环境验证及 live preflight 通过后再次明确批准具体执行。旧 A2 授权和 batch 不适用。

## 候选 provider 与运行方式

- 候选：DeepSeek `deepseek-flash`，条件 C0（无检索上下文）；不纳入 Ollama 或检索。
- 契约：当前冻结 `app001-io.v1` / `app001-extraction.v5`。实现前重新核对当前 `main` 上 prompt、contract、Schema 和 model identity，并冻结其 SHA-256；本草案不预先填写 hash。
- 尝试上限：每个逻辑输入最多 3 次 HTTP；4 个输入最多 12 次 HTTP。任何重试都必须先占用同一批次预算账本，预算耗尽即停止。
- 建议 batch ID 格式：`app003-product-live-YYYYMMDD-NN`；现在不预分配 ID。
- 只允许服务端 transport 持有 provider 访问权。浏览器不接触 API key、Authorization header、raw response 或 transport 凭证。

## 候选输入集（4 条）

| ID | 冻结刺激文本 | 目标行为 / 安全验收 |
|---|---|---|
| `P1-24mm` | `请按 GN 705 做一个轴环，轴孔直径 24 mm。` | 抽取合法 bore_d；呈现来源和确认界面。只有人审阅抽取结果后显式确认才允许 CAD；检查真实 STEP、readback、下载和 hash。 |
| `P2-ask-bore` | `请按 GN 705 做一个轴环。` | 信息不足时应追问 bore_d；无论模型输出 answer/ask，任何缺关键参数或未回答问题都必须阻断 CAD。不得自动填默认孔径。 |
| `P3-catalog-conflict` | `请按 GN 705 做一个轴环，轴孔直径 24 mm，外径 33 mm。` | 冻结目录中不存在该显式组合。冲突必须以 Schema/规则失败阻断；不得静默覆盖外径或构造 STEP。若抽取遗漏冲突字段，也要记录为抽取错误，不能把运行算作成功。 |
| `P4-unsupported` | `请按 GN 705 做一个轴环，轴孔直径 24 mm，并要求阳极氧化表面处理。` | 明确 unsupported 请求应阻断 CAD；不得因几何参数合法而忽略 unsupported 请求。 |

四条刺激必须与 evaluator-only 标签分开存储。模型请求包仅含原始刺激、冻结 prompt/contract 所需上下文，不含目标状态、预期字段、评分标签或审查提示。

## 产品确认与构造门

1. 对每条刺激请求真实抽取并落盘可追溯摘要；model raw 按批准的 retention policy 隔离存储，summary 只写相对路径与 hash，不写正文、密钥或 header。
2. answer 结果先进入 UI 的 `needs_confirmation`，必须由负责人/测试操作员逐项检查需求、显式字段、目录/规则派生字段、警告与冲突。只有 P1 且 Schema/规则检查通过时，才在 UI 明确确认后调用 CAD。
3. P2、P3、P4 应停止在 ask/blocked/failed 对应的安全状态，不得显示可下载 STEP；不得通过空 patch 或隐藏 UI 路径绕过服务端 gate。
4. 任何解析、契约、Schema、IR、CAD、几何、STEP 导出/回读错误均不得报告 succeeded，也不得返回其他 run 的产物。
5. 本 scope 的 pipeline 权限仅来自本批次独立 product gate；不改变 `FORMAL_EVALUATION_ALLOWED=False`，不复用 A2 authorization/profile/batch。

## 预算与输出证据

- 最大逻辑输入数：4。
- 最大 HTTP：12（4 × 每输入最多 3 次尝试），provider 上限同为 12。
- 至少需要新建独立 product authorization、batch summary、budget ledger 与 fail-closed preflight；在上述实现经复核前不得执行本草案。
- 每条 run 记录 run_id、输入 ID/hash、prompt/contract/model identity、请求尝试数、decision、各类参数及来源、questions/missing/unsupported/conflicts、服务端确认记录、Schema/IR/CAD/STEP 状态、错误码、raw/STEP 相对路径与 SHA-256。
- evaluator labels 与生产运行目录分离；summary 不含 raw 正文、API key、Authorization header 或 evaluator-only 标签。
- 验收结论只描述本次 4 个刺激在冻结模型和配置下的行为，不声称统计显著性或广泛泛化。

## 执行前置条件

1. 项目负责人审阅并批准 provider/model、四条冻结输入、预算、人工确认门、raw 留存与证据路径。
2. Codex 中枢检查现有 live adapter/runner 是否能安全复用；如需产品独立 gate、服务端 transport 或预算账本，先由 CC 实现并独立复核，禁止直接把 A2 gate 接进产品入口。
3. 离线测试覆盖 HTTP 入口零调用、预算耗尽、test-only approval 拒绝、错误 binding、模型 ask/refuse/unsupported/conflict、用户确认前 compile_ir=0、显式确认成功、pipeline 失败无 STEP、run 隔离、raw/summary 脱敏。
4. 固定 CAD venv 下专项、LLM、Schema、Integration、CAD 回归及 localhost/browser 离线 E2E 通过。
5. 对具体 batch ID、preflight 结果和执行操作再次征得负责人明确批准后，才可发真实 provider 请求。批准前不读取密钥、不创建正式 batch、不触网。

## 待负责人确认

- 是否接受 DeepSeek `deepseek-flash` / C0 候选。
- 是否接受 4 条输入及总预算 12 HTTP；若减少输入，需确认保留哪些负例类别。
- raw response 留存期限与批次目录位置（遵守现有忽略和权限规则）。
- 人工确认者和执行时段；确认必须发生在抽取结果展示之后、CAD 构造之前。
- 是否把 live smoke 的 P1 成功 STEP 作为本次目标；安全负例不得触发 CAD。
