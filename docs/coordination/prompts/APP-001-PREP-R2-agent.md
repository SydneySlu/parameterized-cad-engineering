# APP-001-PREP-R2：运行时能力核验与实验材料冻结

你是 APP-001-PREP 的续任 Agent。任务目标是补齐首轮正式 LLM 评测前的准备工作，并提交供 Codex 中枢独立审查的结果。本任务**不运行正式验收集、不做云端/本地模型对照、不生成任何性能结论，也不放行 APP-001**。

## 仓库与启动检查

工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`。先运行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
```

必须确认根目录正确且工作树无他人未提交修改。若有不属于本任务的改动、index lock、分支落后或任务材料与记录冲突，停止并报告，不覆盖、不清理、不擅自切换分支。

阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`、`docs/coordination/APP-001-baseline-contract.md`，以及本任务目录中的 `checkpoint.md`、`handoff.md`、`model-baselines-v0.yaml`、`acceptance-set-v0.json`、`prompt-output-contract-v0.md`、`runtime-probe-2026-11-05.json`。另核对 CAD-003 schema README、RET-003 protocol 与 Ollama 官方文档/当前运行环境。执行前序交接的定向复核：重跑契约中一个正常和一个失败样例的静态/规则检查，不调用 LLM 验收集。

## 已冻结决策和基线

- 云端 provider：DeepSeek；请求模型 ID：`deepseek-flash`；官方标注版本：`DeepSeek-V4.1-Flash-1017`；Base URL：`https://api.deepseek.com`。
- 首轮 DeepSeek 正式基线显式关闭思考模式：每次请求发送 `thinking: {"type":"disabled"}`。该设置已由负责人确认并记录在 ADR-0012，不能依赖 API 默认行为。
- 云端 key 仅通过本机根目录 `.env` 的 `DEEPSEEK_API_KEY` 读取，或从同名环境变量读取。**不得读取后输出、记录、复制、提交或发送 key；不改写 `.env`；不把 key 放进命令行参数、shell history、报告、日志或聊天。** 当前仓库根 `.env.example` 是已跟踪模板，绝不能填真实 key。
- 已有一次极小非评测 API probe：响应 `model=deepseek-flash`，无 provider 字段，usage/cache 字段可用；该 probe 的参数、用量及限制记录在 `runtime-probe-2026-11-05.json`。不得重复完整 probe，除非 seed 能力核验所必需。
- 本地基线：Ollama `qwen3:8b`，期望 digest/ID `500a1f067a9f`，设备 MacBook Air M5 16 GB。Windows CPU 是独立迁移探索，不并入本次基线。
- 共同设置仍是 temperature=0、top_p=1、max output=512；seed 固定若支持，不支持则记明。只对暂时性请求故障最多重试两次。正式运行尚未获准。
- 输入输出契约中的 `acceptance-set-v0.json` 仍是 evaluator-only 草案，标签不得注入模型。模型只抽取用户显式参数；目录/阈值派生由确定性规则负责。

## 工作范围和阶段门

### M0：复核现状与环境

记录 Python、OS/架构、Ollama CLI/API 版本、模型 tag/digest 是否匹配，以及 API key 是否存在（只检查存在性，绝不打印值）。不要把本地环境不匹配变成正式实验结果。若 Ollama 不可用，记录阻塞证据，继续做不依赖其运行的材料审查。

### M1：DeepSeek seed 能力最小核验

先查 DeepSeek 当前官方 API 文档是否明确支持 Chat Completions 的 `seed` 参数。若证据仍不足，允许用 `DEEPSEEK_API_KEY` 做最多两次极短、无验收样本的能力探测：同一固定短提示、同一 `seed`、`temperature=0`、`top_p=1`、小 `max_tokens`、JSON mode、思考 disabled。只记录 HTTP/API 是否接受 seed、响应中是否回显 seed（若有）、响应 `model`、usage/cache、request ID 是否存在（不要保存 ID），并注明“接受参数不证明输出确定性”。不保存 reply 内容，不因输出差异重试，不生成模型质量分数。若请求以不支持参数报错，保留脱敏错误类别/HTTP 状态，不保存完整错误正文或 headers。不得测试其他参数组合。

若 seed 核验会产生额外费用，先使用已知最小 token 上限并在 checkpoint 标注预估极低用量；不能把 token 估算称为实际费用。调用失败或 key 不可用时，写 `blocked` / `not_verified`，不要尝试查看或修复 key。

### M2：Ollama 本地模型思考模式与接口核验

核验 `ollama --version`、服务可用性、模型 digest、模板/参数信息和当前 Ollama 官方文档。可做最多 2 个很短的独立 capability probe，不用项目验收集：确认如何令 Qwen3 输出不带思考过程的结构化 JSON，以及配置 `temperature=0`、`top_p=1`、最大生成长度和 seed 的实际 API 字段/能力。观察时只保存请求配置、版本/digest、成功状态、是否返回有效 JSON、脱敏运行元数据；不得保存模型正文或隐藏思维链。若思考切换不能可靠核验，记录未验证，不要编造“与 DeepSeek 等价”。

### M3：冻结候选 Prompt、验收集和运行记录契约

审查现有九条验收样本及 Prompt/output contract。将可正式使用的 Prompt 独立保存为版本化纯文本文件（例如 `prompt-v1.md`），保证 system/user 模板与契约字段严格一致。逐条核对：自然语言是否只提供允许知道的信息、ground truth/evaluator labels 是否隔离、用户显式参数与目录派生值区分、缺失 `bore_d` 必须 ask/refuse、冲突不得静默修正、retrieval context 不泄漏真值。

冻结候选指标计算、失败分母、token/cost 计算、延迟记录和输出校验路径。显式记录：

- DeepSeek 每次请求发送 thinking disabled；记录请求实际参数，不把 provider 特有字段说成跨模型共同参数。
- Ollama 使用核验到的 Qwen3 no-think 配置；若不能证实等价，将模型比较标为运行模式不完全等价，并提交中枢审查，不擅自放行正式横向结论。
- DeepSeek 的 seed 记录 `supported`、`unsupported` 或 `not_verified`；同一 seed 下最多两次请求只能说明可重复性观察，不能据此宣称 API 有确定性保证。
- 验收集中的期望标签只存在于 evaluator 文件，不进入 prompt 或 query payload。
- 所有 API 错误不得保存 Authorization、key、完整 headers 或可包含敏感信息的原始错误正文。

不得修改 ADR-0009 至 ADR-0012 的已确认决策；如果发现矛盾，提出追加决策建议并暂停相关改动。

### M4：验证和交接

至少执行并记录：

```bash
ruby -e 'require "yaml"; YAML.parse_file("agent-work/llm/APP-001-baseline-prep/model-baselines-v0.yaml")'
python3 -m json.tool agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json >/dev/null
python3 -m json.tool agent-work/llm/APP-001-baseline-prep/runtime-probe-2026-11-05.json >/dev/null
git diff --check
git check-ignore -v .env
```

补充相应的 Prompt/验收标签泄漏检查。必要时跑已有 CAD-003 样例静态校验。不要以新 API probe 结果替代项目规则测试。

更新本目录的 `model-baselines-v0.yaml`、`prompt-output-contract-v0.md`、新增/修订 Prompt 文件、`checkpoint.md`、`handoff.md`；只追加 `docs/WORKLOG.md`，并同步 `docs/PROJECT_STATUS.md`、`docs/TASKS.md`。保持 `APP-001-PREP=review`，保持 `APP-001=planned`，formal evaluation gate 必须仍为 false。Checkpoint/handoff 需明确列出哪些完成、哪些未完成、API probe 的非评测性质、实际命令、资源消耗、环境和下一步中枢审核点。

完成可审查阶段后按仓库要求提交一个 commit，状态保持 `review`，不 push。提交前确认 `.env` 不在 Git index、密钥不存在于 tracked diff 和日志；无需输出 diff 中任何可能敏感的内容。

## 严格禁止

- 不运行九条验收集、正式 C0/C1、端到端字段/Schema/CAD/STEP 评测或性能对比。
- 不把 API seed 小探测包装为模型效果结果、重复性保证或正式实验。
- 不修改 CAD-003、Typed CAD IR、CAD 编译器、CAD 验证器、RET-002 权重、正式验收真值或检索数据库。
- 不读取、打印、写入、复制、提交或外发 API key；不修改 `.env`。
- 不把 `.env.example` 写入真实凭据；不提交 key、headers、响应正文、隐藏思维链或大型生成物。
- 不自行将任务标成 `done`、不合并、不 push、不宣布 APP-001 已获放行。

## 最终交接格式

报告 commit、变更文件、逐阶段结果、seed/Ollama 模式证据、实际检查命令、费用/调用次数（若有）、安全检查、保留限制和所需中枢决策。若任何基础条件不可用，局部报告并停在 `blocked` 或 `review`，不要通过伪造成功来完成检查表。
