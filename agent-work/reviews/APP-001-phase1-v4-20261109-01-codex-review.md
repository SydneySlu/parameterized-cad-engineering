# APP-001 v4 formal batch — Codex independent review

日期：2026-11-09  
批次：`app001-phase1-v4-20261109-01`  
授权人：Wang sikai；授权时间：2026-11-09 00:10 Asia/Shanghai  
审查范围：运行产物完整性、预算、模型身份、解析/契约、Schema、决策质量和请求前阻塞。C2、IR/CAD、geometry、STEP 未运行。

## 结论

批次运行证据完整，预算、身份、版本和留存边界通过；批次状态保持 **review**。本批次不应被解释为 v4 决策策略已经解决既有偏差，也不应重跑或覆盖同一 `batch_id`。

当前启动脚本再次运行时按设计在目录保护处 abort，因为该批次目录已有完整产物；这次重试没有发起新的模型请求。

## 运行覆盖与预算

- `runs.jsonl`：36 条逻辑记录，`batch_id` 和 `prompt_version` 全部正确。
- 32 条模型响应成功，4 条 C1 请求前阻塞：A04 两个 provider 为 `C1_NO_SAFE_QUERY_PARAMETER`；A07 两个 provider 为 `RETRIEVAL_SCHEMA_REJECTED`。
- 逻辑覆盖：C0/C1 各 18；DeepSeek/Ollama 各 18；每个 case/provider/condition 组合唯一。
- `budget_ledger.json`：48 次物理 HTTP，均成功：DeepSeek 16 次 `/chat/completions`；Ollama 16 次 `/api/chat` + 16 次 `/api/tags`。总量 48 ≤ 108；DeepSeek 16 ≤ 54；Ollama 32 ≤ 54；模型尝试均为 1 ≤ 3。
- 32 个 raw response 与记录一一对应；路径、长度和 SHA-256 全部匹配；未发现 `sk-`、Bearer、Authorization 或 `DEEPSEEK_API_KEY` 字样。

## 身份和协议

- 运行软件记录：Python 3.11.18、macOS arm64、`app001-adapter.v0`、`set_screw_shaft_collar.v0`。
- 32 条响应均为 `contract_version=app001-io.v1`、`prompt_version=app001-extraction.v4`；system prompt、user template hash 在响应记录中一致。
- DeepSeek 16 条 runtime model 均为 `deepseek-flash`；Ollama 16 条均为 `qwen3:8b`。provider runtime 字段按当前契约为 `not_exposed`，不把它误读成模型身份缺失。
- DeepSeek token：input 41,758，output 1,765，total 43,523；费用合计 CNY 0.01507464，16 条均有 rate-card 来源。
- Ollama 本地延迟：16 条，5,657.396–18,238.015 ms，平均 8,206.001 ms，中位数 7,718.671 ms。

## 解析、字段和确定性阶段

- 对 32 个 raw body 重新调用当前 v4 `parse_response()`：32/32 通过。
- 显式参数与 acceptance-set：32/32 精确匹配；证据均覆盖显式字段；A07 的 `flange`、`keyway`、`anodizing` 标签 2/2 provider 精确保留。
- 阶段统计：model_call/parse/contract/projection 均 32/32 pass；Schema 20 pass、12 fail；construction gate 17 pass、15 fail。IR 记录为受控 blocked/no mapping，CAD、geometry、STEP 均 `not_run`，不作为端到端失败率。

## 决策质量与自洽性问题

按 acceptance-set 允许决策集合核对，32 条模型响应中 29 条符合，3 条不符合：

- Ollama A02 C1：`refuse`，期望 `answer`。
- Ollama A03 C0：`refuse`，期望 `answer`。
- Ollama A08 C1：`refuse`，期望 `answer`。

另有 2 条 envelope 自洽性问题，均为 DeepSeek A05（C0、C1）：`outer_d=40` 已在 `extracted_parameters` 和 user evidence 中保留，却同时出现在 `missing_fields`。这不绕过确定性 Schema，但应作为 v4 输出策略/审计缺陷记录，不能称为完全自洽。

## 边界和下一步

- 本轮未修改生产代码、prompt、Schema、预算、授权或旧批次；未运行 C2/IR/CAD/geometry/STEP。
- 当前批次目录和 raw 产物位于 Git 忽略的 `work/`，不得加入 Git、删除或覆盖。
- 若要修正 3 条决策偏差或 A05 自洽性，必须另行版本化 prompt/输出策略并创建新的唯一批次，不能复用本批次，也不能把新旧统计混合。
- 下一步先由项目负责人决定是否开启新一轮窄范围策略修正；在新授权前保持正式模型 gate 关闭。
