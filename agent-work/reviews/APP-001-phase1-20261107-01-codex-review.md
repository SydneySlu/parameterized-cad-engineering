# APP-001 Phase 1 批次审查

- 批次：`app001-phase1-20261107-01`
- 审查日期：2026-11-07
- 状态：`review`
- 运行入口：已合入 `main` 的 `APP-001-RUNNER`（`9d83219`，状态文档提交 `53f6c49`）
- 运行范围：9 条冻结样例 × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b`
- 记录文件：`work/app001-runs/app001-phase1-20261107-01/runs.jsonl`

## 已确认的执行事实

- `runs.jsonl` 共 36 条逻辑运行记录，覆盖 9 个样例、C0/C1 和两个模型。
- C0 共 18 条：DeepSeek 9 条、Ollama 9 条，均完成一次模型调用；模型调用阶段记录为 `pass`。
- C1 共 18 条：全部在请求模型前阻塞，没有消耗模型调用额度。16 条因 RET-002 flat query 缺少六个冻结字段，2 条因无法从允许的自然语言中安全提取 `bore_d`。
- `budget_ledger.json` 记录 27 次物理 HTTP：DeepSeek `/chat/completions` 9 次、Ollama `/api/tags` 9 次、Ollama `/api/chat` 9 次。总批次上限 108、provider 上限 54，均未触及；没有重试。
- 18 个云端/本地模型原始响应写入 `work/app001-runs/app001-phase1-20261107-01/`，该目录由 `.gitignore` 忽略。
- C2 未运行；IR、CAD、geometry、STEP 均保持 `not_run` 或阻塞状态。
- 本批次运行记录未发现 API key、Bearer 或疑似密钥内容；密钥不写入 Git、日志或聊天。

## 结果解释边界

`final_outcome=success` 只表示该条 C0 的模型调用和传输阶段完成，不表示字段抽取、envelope 解析或 Schema 成功。18 条 C0 均在解析阶段出现 `MISSING_ENVELOPE_KEY`，随后 construction gate 为阻塞，因此本批次不能发布字段准确率、Schema 通过率、CAD 指标或模型质量结论。

当前 36 条记录中的 `cloud_input_tokens`、`cloud_output_tokens`、`cloud_total_tokens`、缓存 token 和费用字段均为空。token/费用链需要单独修复并以 fixture 验证后，才能把正式运行用于成本或 token 指标。

## 阻塞项

1. **C1 输入契约不兼容**：`src/llm/conditions.py::assemble_c1()` 当前只构造 `bore_d` 查询，而 RET-002 flat query 要求六个冻结字段，导致 C1 全部安全阻塞。修复时不得读取 evaluator-only 标签；应先冻结允许的 C1 查询组装契约并补正常/失败测试。
2. **响应 envelope 与冻结契约不一致**：模型返回内容多数缺少 `contract_version`、`prompt_version` 等必需字段。需要先判定这是 Prompt/服务响应契约问题，补充解析和 fixture 证据；不能把 model-call pass 当作抽取成功。
3. **usage/token/费用未落盘**：审查 `real_transport.py` → `adapter.py` → `runrecord.py` → `cost.py` 的传递链，补 DeepSeek usage fixture 测试。未修复前不发布 token、费用、成本效率指标。

## 后续要求

- 保留本批次及其原始响应，不覆盖或重写 `app001-phase1-20261107-01`。
- 先完成上述窄范围代码/契约修复并经测试审查，再创建新的唯一批次 ID 重跑；新批次不能与本批次混合统计。
- 继续保持 C2、IR/CAD/geometry/STEP 禁用，除非另有明确授权和新的范围决策。

