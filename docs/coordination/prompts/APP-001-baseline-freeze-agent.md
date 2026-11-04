# APP-001-PREP：基线身份、输入输出契约与小型验收集准备

你是 APP-001 的准备 Agent。你的任务是把正式 LLM 实验所需的协议和小型验收集整理成可审查草案；本轮不运行正式模型对照，不生成字段、Schema、CAD 或 STEP 成绩。

## 启动与交接

工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`。开始前运行 `git rev-parse --show-toplevel`，并阅读 `AGENTS.md`、项目状态/计划/日志/决策、`docs/coordination/handoff-review-protocol.md`、`docs/coordination/APP-001-baseline-contract.md`、CAD-003 Schema README 和 RET-003 protocol。发现记录互相矛盾时先标记 `review`，不要自行改写既有接口。

## 已给定的基线

- 云端：DeepSeek v4.1 Flash 1017，作为主效果基线。若能访问已有 API 配置，只记录 provider、返回的 `model` 字段和非敏感运行信息；绝不记录密钥。若无法访问，写 `model_id_pending_runtime_probe`，不得猜测 ID。
- 本地：Ollama `qwen3:8b`，digest/ID `500a1f067a9f`，作为部署、成本和延迟对照。
- 首期本地设备：MacBook Air M5，16 GB RAM，512 GB SSD。未来 Windows CPU 设备只作独立迁移探索，不与 Mac 基线合并。

## 允许修改和交付目录

只在 `agent-work/llm/APP-001-baseline-prep/` 创建本任务材料，另只追加 `docs/WORKLOG.md`。交付：

1. `model-baselines-v0.yaml`：模型标签、provider 状态、API 返回身份字段、Ollama digest、设备、解码参数待填项和版本记录字段；不得包含密钥。
2. `acceptance-set-v0.json`：至少 8 类小样本草案，覆盖完整描述、仅 `bore_d`、单位换算、缺失 `bore_d`、目录冲突、`second_screw` 边界、越界/不支持请求、检索示例不能照抄。每条包含自然语言输入、人工确认参数/派生值、预期追问或拒绝、不可接受的编造行为。
3. `prompt-output-contract-v0.md`：Prompt 版本、共同输入、输出 JSON envelope、证据/缺失字段/追问/confidence 语义、禁止自由 CAD 代码、错误和超时记录格式。
4. `checkpoint.md` 和 `handoff.md`：按三层交接协议记录检查、未完成内容和下一 Agent 关注点。

验收集必须标为草案 `review`，经 Codex 中枢和项目负责人确认后才冻结；不得直接拿草案跑正式评测。

## 指标口径

明确三层测量顺序：

1. 模型运行后测字段 exact match（数值先归一化到 mm）、缺失关键字段识别、追问/拒绝正确性、Schema/规则通过率、延迟和成本。
2. 同一模型输出接入 `Typed CAD IR → CadQuery/OCP → 几何/族规则 → STEP 回读` 后，再测 IR 接受率、CAD 构造成功率、几何/规则通过率和 STEP 回读通过率。
3. 只有输入、模型、Prompt、解码参数和后处理完全共同的 C0/C1 才能比较；公平 C2 不在本任务定义。

## 严格禁止

- 不运行正式云端或本地模型对照；不生成或覆盖正式 C1/C0 结果；
- 不修改 Schema、Typed CAD IR、CAD 编译器、验证器和 RET-002 权重；
- 不把目录真值直接塞进模型输出；不提交 API key、私有样本或大型生成物；
- 不宣称端到端指标已经测量。

## 交接和提交

追加 `docs/WORKLOG.md`，记录任务 ID、文件、实际检查命令、结果和限制；提交：

```text
docs: draft APP-001 baseline and acceptance contract [APP-001-PREP]
```

保持 `review`，等待 Codex 中枢独立审查。报告明确哪些字段已固定、哪些仍待负责人确认，以及是否成功读取 API 返回的真实 `model` 字段。
