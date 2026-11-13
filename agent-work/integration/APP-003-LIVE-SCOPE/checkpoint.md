# APP-003 产品 Live Extraction Scope checkpoint

- 任务：`APP-003-LIVE-SCOPE`
- 日期：2026-11-13
- 状态：`planned`（scope 已批准；实现尚未开始）
- 基线：`main` 本地 `4708b33`（C3 closeout 文档提交），远端 `origin/main` 当时为 `f105fc4`；尚未推送 closeout 提交。
- 目标：根据 ADR-0023 为 C3 后续真实产品抽取准备独立、最小、可审阅的 live scope 提案。
- 产物：`scope-draft.md`，包含 4 条候选刺激、候选 DeepSeek C0、12 HTTP 上限、确认门、fail-closed 验收与执行前置条件。
- 未授权事项：没有批准具体 batch ID；没有创建正式 batch/ledger；没有运行 live preflight 或 provider 请求；没有读取密钥/`.env`；没有执行 CAD。
- 下一步：负责人审阅 scope 参数。只有批准 scope 后，才准备专用 product live gate/runner 工作单；具体 live 执行仍须单独 preflight 和明确批准。

## Scope approval / implementation handoff（2026-11-13）

- 项目负责人已批准本 scope 的 4 条输入、DeepSeek `deepseek-flash` / C0 候选和最多 12 次 HTTP。
- 实现工作单：`docs/coordination/prompts/APP-003-live-product-cc.md`。
- 执行安排：新建 CC 对话框，使用 `cc/APP-003-LIVE-PRODUCT` 分支；不在已有 C3 对话框继续实现。
- 本批准仅覆盖实现和离线验证；不授权 live preflight、正式 batch、provider 请求、密钥读取或 CAD 正式运行。
