# APP-001 决策策略 v4 候选稿

- 日期：2026-11-07
- 状态：candidate draft，未冻结、未激活
- 当前生产版本：`app001-extraction.v3`
- 候选版本：`app001-extraction.v4`
- 关联：ADR-0013、ADR-0016；v3 批次审查 `agent-work/reviews/APP-001-phase1-v3-20261107-01-codex-review.md`
- 边界：不改冻结 I/O 契约、acceptance-set、CAD-003 Schema、parser、adapter、runner、v3 prompt 或旧批次；不发起模型请求。

## 1. 背景和目标

v3 正式批次的 32 条模型响应均正确抽取显式字段并通过解析/契约；偏差集中在 Ollama 的三条决策结果及一条不支持请求标签词形变体：

- A03 C0/C1：用户给出 `1.6 cm`，可精确归一到目录值 16 mm；Ollama 输出 `refuse`，期望 `answer`。
- A08 C1：用户明确给出 `bore_d=24 mm`，检索参考示例为 20；Ollama 输出 `ask`，期望 `answer`。
- A07 C0：应拒绝，并记录 `anodizing`；Ollama 输出 `anodized`。

v4 候选只澄清上述边界，保留 v3 decision gate。目标测试映射是三类偏差均有对应的离线策略要求，同时不损害 A01/A02/A06 正常案例及 A04/A05/A07/A09 的拒绝/澄清安全边界。

## 2. 候选规则

1. **可精确换算的单位**：长度值精确换算为 mm 后若等于冻结目录中的合法值，来源单位不是拒绝或追问理由。A03 的 `1.6 cm` 等于 16 mm，应提取 `bore_d=16`、保留原单位证据并允许 `answer`。换算结果不匹配目录时仍执行既有 gate。
2. **不可信检索参考**：检索示例不能改变用户意图，也不能单独制造歧义。A08 用户明确指定 `bore_d=24 mm` 时，应提取 24 并允许 `answer`，即使参考示例显示 20。用户输入自身有歧义/冲突时仍走既有 `ask`/`refuse`。
3. **unsupported 规范标签**：每项仍须依据用户原话并附 evidence；等价表述输出稳定规范名。阳极氧化、anodize、anodized、anodizing 均规范为 `anodizing`；法兰/ flange 规范为 `flange`；键槽/keyway 规范为 `keyway`。保留用户原文作为 quote，不添加未请求项目。
4. **安全 gate 不变**：沿用 v3 中 `answer` 的 bore_d 目录成员、无 unsupported 和无可见自相矛盾等前置条件，以及 CAD-003 的最终确定性校验；不静默改写显式主张。

显式 `bore_d` 必须属于 15 个离散目录 selector；“5–80 mm”只是数值边界，不是连续可选范围。因此 `75 mm` 虽在数值边界内，仍属于非目录值，必须保留用户主张并 `refuse`，不能吸附到 70 或 80。

## 3. 冻结样例回归映射

| 样例/观测 | 离线期望 |
|---|---|
| A03 C0、C1 | decision=`answer`；bore_d=16；证据保留 `1.6 cm` |
| A08 C1 | decision=`answer`；bore_d=24；不复制参考值 20、不追问 |
| A07 C0 | decision=`refuse`；unsupported 包含规范名 `anodizing`；证据 quote 保留“阳极氧化” |
| A01/A02/A06 | 仍允许 `answer` |
| A04/A05/A09 | 不允许 `answer` |
| A07 bore_d=75 | 不允许 `answer`，不吸附目录值 |

这些是 prompt 规格和离线 checker 的验收目标，不是对模型效果的断言。`acceptance-set-v0.json` 保持原样；正式评分仍按其原始 evaluator labels，不把 v4 的规范名要求回写到历史批次。

## 4. 版本和激活边界

候选 prompt 位于 `prompt-v4-candidate.md`，当前生产仍使用独立冻结的 v3 激活副本。若要激活 v4，需负责人另行接受版本变更决策，再整体更新 `contract.py` 版本常量、parser、prompt loader hash/path、激活 manifest 和回归测试；保留 v3 文件及哈希作为回滚目标。真实模型复测需新的唯一批次 ID 和单独授权。

## 5. 当前验证边界

文本/离线测试只能验证候选文件、显式规则和接口不变量，不能证明模型会遵循指令。验收后下一步是由中枢审查是否将候选冻结为 v4；模型效果只能在明确授权的新批次中验证。
