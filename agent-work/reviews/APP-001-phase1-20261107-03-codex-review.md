# APP-001 Phase 1 第三批次审查

- 批次：`app001-phase1-20261107-03`
- 审查日期：2026-11-07
- 状态：`review`
- 主线：`d5613a1`（envelope 修复已合入并推送）
- 范围：9 条冻结样例 × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b`
- 原始记录：`work/app001-runs/app001-phase1-20261107-03/`

## 执行事实

- `runs.jsonl`：36 条逻辑运行记录；旧批次 `-01`、`-02` 未覆盖。
- 完成模型调用：32 条；C1 请求前阻塞：4 条。
- 物理 HTTP：48 次：
  - DeepSeek chat：16
  - Ollama tags：16
  - Ollama chat：16
- 预算账本：总计 48/108；DeepSeek 16/54；Ollama 32/54；无重试。
- 原始响应：32 个脱敏文件，位于 Git 忽略的批次目录。
- C2、IR、CAD、geometry、STEP：未运行；IR 仍记录为 `blocked_no_approved_ir_mapping` 或 `not_run`。
- 4 条 C1 阻塞保持既有口径：
  - A04 两个模型：无法从允许输入安全提取 `bore_d`；
  - A07 两个模型：CAD-003 envelope 被 Schema 拒绝。

## Envelope 与结构化链路

| provider / condition | 调用数 | envelope parse | Schema pass |
|---|---:|---:|---:|
| DeepSeek / C0 | 9 | 9/9 | 5/9 |
| DeepSeek / C1 | 7 | 7/7 | 5/7 |
| Ollama / C0 | 9 | 1/9 | 1/9 |
| Ollama / C1 | 7 | 7/7 | 5/7 |
| 合计 | 32 | 24/32 | 16/32 |

Ollama C0 的 8 个失败均为严格 parser 的 `EXTRACTED_TYPE_ERROR`：模型把长度/整数显式值写成了带单位字符串，例如 `"24 mm"`、`"1.6 cm"`、`"70 mm"`。这是模型输出契约遵守问题，不能由 Adapter 静默修复。

## 显式字段诊断

按冻结样例的 `explicit_parameter_claims` 做单位归一化后的诊断：

- DeepSeek：27/27 个显式字段值匹配，16/16 条完成调用均字段全匹配。
- Ollama：25/27 个显式字段值匹配，C0 为 13/15，C1 为 12/12；C0 的两项缺失来自上述类型错误。
- DeepSeek C0/C1 均保留了显式值；A05/A09 的冲突由后续 Schema/规则阶段拒绝。
- 本批次未运行 CAD/STEP，因此不能发布 CAD 构造率、几何通过率或 STEP 回读率。

## 运行指标

- DeepSeek：16 条调用，15,463 total tokens；费用合计 CNY 0.01207752；缓存 token、费用来源均已落盘。
- Ollama：16 条调用均记录本地墙钟耗时；平均 15,745.52 ms，中位数 15,353.94 ms，最小 11,853.23 ms，最大 27,761.76 ms。
- API key 未写入运行记录、日志或 Git；批次目录通过 secret scan 未发现 `sk-`、Bearer 或 `DEEPSEEK_API_KEY=`。

## 结论边界

- `APP-001-PHASE1-ENVELOPE-FIX` 已证明 loader 修复有效：修复后 DeepSeek 全部、Ollama C1 全部响应包含并通过 envelope 解析。
- Ollama C0 的类型不合规暴露了模型/条件差异，不能把 24/32 parse pass 当作整体通过。
- 目前可以发布传输、envelope、usage/cost、延迟和显式字段诊断结果；不能发布 CAD/STEP 端到端指标，也不能把 `model_call=pass` 当作完整抽取或构造成功。
- A04/A07 C1 阻塞仍需单独决策；本批次没有改变其口径。

## 后续

1. 保留 `-01`、`-02`、`-03` 三个批次，不混合统计。
2. APP-001 保持 `review`；先决定是否接受“严格类型拒绝”作为首轮结果，还是另开窄范围的 Ollama 输出契约修正。
3. 若继续修正，只允许无网络 parser/输出约束测试和新批次验证；不修改旧批次、不运行 C2/IR/CAD/geometry/STEP。

