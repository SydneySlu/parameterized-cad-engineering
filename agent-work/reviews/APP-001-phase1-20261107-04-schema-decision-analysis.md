# APP-001 第四批次 8 条 Schema 拒绝诊断

- 日期：2026-11-07
- 状态：`review`
- 批次：`app001-phase1-20261107-04`（Git 忽略，只读）
- 基线：`main` / `origin/main`，`60f4fa2`
- 范围：逐条核对 8 个 `schema.status=fail` 的运行记录、受控留存正文和冻结验收集；不运行模型、不改代码/Prompt/Schema/规则、不改批次文件。

## 结论

这 8 条拒绝不能合并解释成“模型抽取错误”。模型对冻结样例中显式字段的数值提取总体准确；CAD-003 对缺必填目录选择器、非目录值、目录耦合冲突及规则冲突作出的拒绝符合冻结规则。主要可改进点在 `decision`：若干输出在已报告缺失、已检测到用户冲突或存在不支持请求时仍返回 `answer`，而不是按验收集要求追问/拒绝。该问题属于对话/安全决策行为，不是放宽 Schema 的理由。

逐样本分类：

| 样例 / 运行 | Schema 拒绝 | 显式抽取与证据 | 决策诊断 |
|---|---|---|---|
| A04 C0 Ollama | `MISSING_REQUIRED(bore_d)` | 保留 `outer_d=32`、`width=14`，并列出缺少 `bore_d`；没有猜测值 | 输出 `answer` 与“缺目录选择器应追问或拒绝”不符。Schema 正确阻止构造。 |
| A05 C0 Ollama | `CATALOG_MISMATCH(bore_d=20, outer_d=40)` | 两个明确主张及各自用户原文证据均正确保留 | 输出 `answer`，未把冲突反映为澄清/拒绝。 |
| A05 C1 DeepSeek | 同上 | 两个主张及证据正确保留 | 输出 `ask`，符合冲突处理预期；缺失派生/目录字段列在 missing 中，不影响用户主张抽取判断。 |
| A05 C1 Ollama | 同上 | 两个主张及证据正确保留 | 输出 `answer`，与冲突处理预期不符。C1 未让检索示例覆盖用户明确值。 |
| A07 C0 DeepSeek | `CATALOG_CHOICE(bore_d=75)` | 保留目录外值 75；识别 flange、keyway、anodized coating 为不支持请求 | 输出 `answer`，与应拒绝构造不符；没有把 75 吸附到邻近目录值。 |
| A07 C0 Ollama | 同上 | 保留目录外值 75；识别法兰、键槽、阳极氧化 | 输出 `answer`，与应拒绝构造不符；evidence 对 bore 有引用，但未为 unsupported 请求逐项提供 evidence，证据完整度较弱。 |
| A09 C0 Ollama | `SECOND_SCREW_CONSTRAINT(bore_d=80, second_screw=0)` | 两个显式且互相冲突的主张及证据均正确保留 | 输出 `answer`，未按冻结规则追问/拒绝；CAD-003 正确拒绝 `80/0` 组合。 |
| A09 C1 Ollama | 同上 | 两个显式主张及证据均正确保留 | 输出 `answer`，同样未按冲突规则澄清/拒绝。 |

## 分类计数

- 目录耦合冲突：A05 共 3 条，`CATALOG_MISMATCH`。显式抽取均正确；DeepSeek C1 的 `ask` 符合预期，其余两条 `answer` 是决策偏差。
- 非目录参数与不支持请求：A07 共 2 条，`CATALOG_CHOICE`。两个模型都保留 `bore_d=75` 并识别不支持特征；两个模型都给出不符合预期的 `answer`。Ollama 的 unsupported evidence 覆盖不完整。
- 显式用户请求与确定性规则冲突：A09 共 2 条，`SECOND_SCREW_CONSTRAINT`。主张抽取准确，两个模型均未选择预期的澄清/拒绝。
- 缺失必填字段：A04 共 1 条，`MISSING_REQUIRED`。缺失识别正确且未猜测，但 `decision=answer` 不符合验收预期。

汇总：8/8 的显式字段和值与冻结验收集一致；8/8 被 CAD-003 正确拒绝；仅 1/8 输出 `decision=ask`，其余 7/8 为 `answer`，与对应样例要求存在决策偏差。这个计数仅描述本批次这 8 个拒绝项，不能外推到所有样例或模型总体质量。

## 解释边界与建议

1. 保持 CAD-003 的拒绝行为。将用户声称的冲突值投影成合法目录值、接受目录外值或覆盖显式规则冲突都会损害冻结的安全边界。
2. 指标应拆开：字段抽取（值是否保留）、evidence 完整性、decision/dialogue 行为、确定性 Schema 验证。不能把 8 个 Schema fail 全都记作抽取 fail，也不能把字段准确当成整体行为通过。
3. 下一轮若处理模型决策质量，应只在新的 Prompt/输出策略版本中明确规定 `missing_fields`、目录/规则冲突和 `unsupported_requests` 与 `decision` 的一致性，并增加离线 fixture/回归测试。任何效果比较需新的唯一批次、明确模型运行授权；本分析不授权模型调用。
4. 本报告没有提出修改冻结样例、CAD-003 规则、RET-002 或既有运行结果。

## 证据与方法

- 逐条读取 `runs.jsonl` 的 `schema`、`projection` 和原始响应留存路径；对文件内容直接按 Adapter 保存的模型 JSON 正文解析，不将其误当作 provider 外层 HTTP 响应。
- 与 `agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json` 中 A04/A05/A07/A09 的自然语言、`explicit_parameter_claims`、`expected_behavior` 和 scoring policy 对照。
- 原始响应未复制进报告；既有 `work/app001-runs/` 文件保持不变且被 Git 忽略。
- 未发起网络或模型请求，未读取密钥，未运行 C2/IR/CAD/geometry/STEP。
