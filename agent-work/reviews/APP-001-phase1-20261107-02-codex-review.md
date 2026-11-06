# APP-001 Phase 1 第二批次审查

- 批次：`app001-phase1-20261107-02`
- 审查日期：2026-11-07
- 状态：`review`
- 主线：`641b4b7`（已合入 `APP-001-PHASE1-FIX`）
- 运行范围：9 条冻结样例 × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b`
- 记录：`work/app001-runs/app001-phase1-20261107-02/runs.jsonl`

## 执行事实

- `runs.jsonl` 共 36 条逻辑运行记录，旧批次 `app001-phase1-20261107-01` 未被覆盖。
- C0 共 18 条，全部完成一次模型调用；C1 共 18 条，其中 14 条完成模型调用、4 条在请求前安全阻塞。
- 总计 32 条模型调用完成：DeepSeek 16、Ollama 16。
- 4 条 C1 阻塞：A04 两个模型因自然语言无法安全提取 `bore_d`；A07 两个模型因显式参数超出目录，CAD-003 envelope 无法通过 Schema，RET-002 拒绝查询。
- `budget_ledger.json` 记录 48 次物理 HTTP：DeepSeek `/chat/completions` 16 次、Ollama `/api/tags` 16 次、Ollama `/api/chat` 16 次。总批次上限 108、每 provider 上限 54，均未触及；没有重试。
- 32 个原始响应写入 Git 忽略的 `work/app001-runs/app001-phase1-20261107-02/`。
- C2 未运行；IR、CAD、geometry、STEP 均为 `not_run` 或阻塞。

## 已恢复的运行指标

- 16 条 DeepSeek 记录均落盘 `cloud_input_tokens`、`cloud_output_tokens`、`cloud_total_tokens`、缓存命中/未命中 token、费用金额、币种和价格来源。
- 16 条 Ollama 记录保留本地耗时；未伪造云端 token 或费用。
- DeepSeek 运行时模型均为 `deepseek-flash`，provider 按协议记录为 `not_exposed`。

## 结果解释边界

32 条记录的 `model_call` 阶段为 `pass`，但 32 条均在解析阶段出现 `MISSING_ENVELOPE_KEY`，随后 construction gate 阻塞。因此这些记录证明传输、usage/cost 和延迟链路已工作，不代表字段抽取、Schema 或 CAD 成功，也不能发布模型质量指标。

C1 现在对可由 CAD-003 envelope 验证的输入能够生成 retrieval context；缺少安全查询参数或超出目录的样例会在请求前阻塞。是否要求所有 C1 样例都进入模型调用，需要另行冻结“部分显式参数查询”的评测口径，不能用评测标签或默认值补齐。

## 当前阻塞项

1. **响应 envelope 合规性**：DeepSeek 和 Ollama 的 32 条模型响应都缺少冻结契约要求的 envelope 字段（至少 `contract_version`、`prompt_version`）。需要修复 Prompt/响应契约或确认服务端 JSON 输出约束，再以新批次验证；不能将 model-call pass 作为抽取成功。
2. **C1 覆盖口径**：A04、A07 的安全阻塞如实保留。若要让 A07 进入 RET-002 最近邻查询，必须先冻结允许从自然语言抽取完整 flat 六字段的契约；不得读取 evaluator-only 标签或猜测缺失字段。

## 后续要求

- 保留 `app001-phase1-20261107-02` 全部记录和原始响应，不与第一批次混合统计。（目录名实际为 `app001-phase1-20261107-02`。）
- 在响应 envelope 契约和 C1 覆盖口径明确、经中枢审查前，不再启动新的真实模型批次。
- C2、IR/CAD/geometry/STEP 继续禁用。

