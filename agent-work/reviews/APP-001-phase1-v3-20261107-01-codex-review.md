# APP-001 Phase 1 v3 正式批次中枢审查

日期：2026-11-07  
批次：`app001-phase1-v3-20261107-01`  
范围：9 个冻结样例 × C0/C1 × DeepSeek/Ollama；仅字段抽取、决策、Schema、token、费用和延迟。

## 审查结论

批次证据完整，预算和模型身份约束通过，可以作为 **v3 Phase 1 诊断批次** 留档。它不能作为 CAD/STEP 端到端成绩，也不能把 Schema 通过率解释成模型决策质量已经解决。

模型调用结果中，32/32 条真实响应通过 v3 parser、contract 和 projection；显式字段 32/32 精确匹配冻结样例；证据数组覆盖每个抽取字段。确定性 CAD-003 Schema 对预期可通过的 20 条全部通过，对预期应拒绝的 12 条全部拒绝。

决策行为为 29/32（仅在有模型响应的分母中计算）：Ollama 在 A03 单位换算上两次输出 `refuse`，应为 `answer`；Ollama 在 A08 C1 输出 `ask`，应为 `answer`。A07 的 Ollama 正确拒绝，但将 `anodizing` 写成 `anodized`，属于 unsupported-request 标签不一致。其余决策符合冻结样例允许范围。

## 覆盖和请求证据

- `runs.jsonl`：36 条逻辑记录，`logical_run_id` 唯一。
- 完成：32 条；失败：0 条；请求前阻塞：4 条；阻塞均为 A04/A07 的 C1，未发起模型请求。
- 原始响应：32 个脱敏 `raw_response.txt`，与 32 条模型响应一一对应。
- 版本：32 条响应均为 `contract_version=app001-io.v1`、`prompt_version=app001-extraction.v3`。
- 系统 Prompt hash：32 条均为 `4c515d0d90bb64ca6bb65bd7e2be6ae50aa042dc7ed635c44774167d433e96f0`；激活文件 hash 仍为 manifest 中的 `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`。
- DeepSeek 16 条响应的运行时模型均为 `deepseek-flash`，provider 按契约记录为 `not_exposed`。
- Ollama 16 条响应的运行时模型均为 `qwen3:8b`，digest 均为 `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`。

## 预算、费用和延迟

账本 `budget_ledger.json` 共记录 48 个物理 HTTP 请求：

| provider | `/api/tags` | 模型请求 | 物理请求 | 预算账本计数 |
|---|---:|---:|---:|---:|
| DeepSeek | 0 | 16 `/chat/completions` | 16 | 16 |
| Ollama | 16 | 16 `/api/chat` | 32 | 32 |
| 合计 | 16 | 32 | 48 | 48 |

因此总物理请求 48 ≤ 108；DeepSeek 16 ≤ 54；Ollama 32 ≤ 54；每个有模型调用的逻辑运行均为 1 次模型尝试 ≤ 3。Ollama `/api/tags` 已计入总账本，且以 `is_model_call=false`、`attempt_number=-1` 单独记录。

DeepSeek token 和费用：输入 36,510、输出 1,677、合计 38,187；缓存命中输入 29,696、未命中输入 6,814；费用合计 CNY 0.01411592。16 条均有费用来源 URL 和 CNY 记录。Ollama 记录 16 条本地墙钟延迟，均有 digest；平均 18,353.16 ms，中位数 17,325.03 ms，范围 12,752.22–36,802.29 ms。

## Schema 和阶段边界

32 条模型响应的阶段统计：

| 阶段 | pass | fail | 说明 |
|---|---:|---:|---|
| model_call | 32 | 0 | 4 条 C1 在请求前阻塞，未进入此阶段 |
| parse | 32 | 0 | v3 envelope 全部可解析 |
| contract | 32 | 0 | 契约键和版本通过 |
| projection | 32 | 0 | 仅抽取字段进入 CAD-003 投影 |
| schema | 20 | 12 | 12 条拒绝分别为缺失、目录冲突、目录外或规则冲突 |
| construction_gate | 17 | 15 | 3 条额外失败来自模型 decision 与可构造状态不一致 |

IR、CAD、geometry、STEP 均未运行；记录中的 IR 阻塞/后续 not_run 是受控边界，不是端到端失败指标。

## 环境和限制

本批次运行记录的软件版本为 Python 3.15.2、macOS 26.6.2 arm64；项目此前的固定复核基线为 Python 3.11.18，因此本批次结果应保留该环境差异，不能声称已在 3.11.18 重复运行。Ollama 为本机已核验的 `qwen3:8b` 和上述 digest。

生产全局 `FORMAL_EVALUATION_ALLOWED` 仍为 `False`；本次真实请求通过具名、范围受限的 `FormalRunAuthorization` 路径执行，未改变全局 gate。没有 C2、IR/CAD/geometry/STEP 请求，没有修改旧批次，也没有将原始响应加入 Git。

## 后续建议

1. 接受本批次作为 v3 的字段、Schema、资源和安全边界诊断证据。
2. 将 3 条决策不一致和 A07 标签变体纳入下一轮窄范围策略/输出修正；若重新测模型，必须新建唯一批次并重新授权。
3. 不用本批次宣称 CAD/STEP 成功率；先独立冻结 IR 映射和下游评测口径。

审查依据：`work/app001-runs/app001-phase1-v3-20261107-01/runs.jsonl`、`budget_ledger.json`、32 个 raw response、激活 manifest、冻结 `acceptance-set-v0.json`。这些运行产物位于 Git 忽略目录，仅作为本机证据保留。
