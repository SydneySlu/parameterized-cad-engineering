# APP-001-PREP-FINAL-REVIEW 中枢复核

日期：2026-11-05  
审查方式：只读仓库复核与静态验证；未调用 DeepSeek/Ollama，未读取真实 API key，未运行九条冻结验收样例。

## 判断

状态：`needs_revision`

APP-001-PREP 的冻结契约和模型配置内容基本通过，但交接文档存在当前状态不一致，暂不能标记 `done`。这不是模型配置或输入隔离阻塞，而是必须在正式运行前修正的可追溯性问题。

## 已通过项目

- 仓库工作树干净，`main` 与 `origin/main` 同步。
- `acceptance-set-v0.json` 可解析，标记为 evaluator-only，`formal_evaluation_allowed=false`。
- `prompt-v2.md`、`prompt-output-contract-v1.md` 和 `app001-io.v1` 版本关系一致；Prompt 文件哈希为适配器冻结锚点。
- `model-baselines-v0.yaml` 可由 Ruby YAML 解析，状态仍为 `review`。
- 云端配置区分 `deepseek-flash` 请求 ID 与 `DeepSeek-V4.1-Flash-1017` 文档版本；运行时 `model`、provider、usage/cache 仍按契约单独记录。
- 本地配置为 Ollama `qwen3:8b`、ID `500a1f067a9f`；`think=false` 与 DeepSeek disabled thinking 被明确视为不同控制，不宣称语义等价。
- Prompt 明确禁止 evaluator truth、完整目录行、IR/CAD/STEP 真值和私有样本进入模型输入；C0/C1 reference context 边界清楚。
- 显式参数抽取、Schema/CAD-003 投影、IR/CAD/STEP 和资源指标分层；`confidence` 不参与路由或评分；失败样本保留在分母。
- `APP-001-ADAPTER-R3-FIX` 已由中枢验收，170 个 LLM 测试和 17 个 Schema 测试通过。

独立复跑：

```text
python3 -m json.tool agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json -> OK
ruby -e 'require "yaml"; YAML.load_file("agent-work/llm/APP-001-baseline-prep/model-baselines-v0.yaml")' -> OK
PYTHONPATH=src python3 -m unittest discover -s tests/llm -q -> 170 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q -> 17 tests, OK
```

## 必须修正的问题

`agent-work/llm/APP-001-baseline-prep/handoff.md` 的当前 ADR-0013 段仍写：

> Remaining gate: implement and review the execution adapter/logger

该表述已经过时，因为 `APP-001-ADAPTER-R3-FIX` 已通过中枢验收并在项目状态中标记为 `done`。同一 handoff 的 `unresolved` 和 checkpoint 顶部当前权威说明也应追加说明 adapter 已完成，剩余门槛只有：

1. PREP 文档状态同步和本次中枢最终复核；
2. 项目负责人单独授权正式运行。

历史 M0-M3/R1/R2 内容可以保留，但必须在最新追加段中明确其为历史记录。

## 当前禁止事项

- `APP-001-PREP` 保持 `review`，不得标记 `done`。
- `APP-001` 保持 `planned`。
- 不调用九条冻结样例，不进行正式 C0/C1 模型运行。
- 不生成字段、Schema、CAD、STEP、费用或延迟正式指标。
- IR → Typed CAD IR 映射仍未冻结，不能宣称端到端 CAD/STEP 已就绪。

## 下一步

给 PREP 原 Agent 一个窄范围文档收尾任务：追加当前 handoff/checkpoint，明确 adapter 已验收、formal gate 仍关闭、剩余只有 owner authorization；同步 `docs/WORKLOG.md`。完成后由中枢重新复核并决定是否将 APP-001-PREP 标记为 `done`。
