# APP-001 Decision Policy v3 Candidate 中枢审查

- 日期：2026-11-07
- 任务：`APP-001-DECISION-POLICY-V3-DRAFT`
- 分支：`cc/APP-001-DECISION-POLICY-V3-DRAFT`
- CC 提交：`9a32756`（父链包含 `002b936`、`6f4af27`）
- 结论：候选结构与冻结接口隔离通过；决策策略行为覆盖不足，保持 `review`，暂不建议进入激活决策。

## 通过项

- 交付文件均已提交，工作区干净；v3 candidate checker 未被 adapter/parser/runner 导入，候选未激活。
- `prompt-v2.md`、contract/parser/prompt_loader、冻结 acceptance-set 和 CAD-003 Schema 均无相对基线变更。
- 候选保持 `app001-io.v1`、9-key envelope、现有 decision 值和 evidence 形状；没有触碰旧批次、密钥或模型运行。
- 在当前 Python 3.15.2 环境独立复跑：专项 44/44、LLM 560 passed/8 skipped、Schema 17/17；`py_compile` 和 `git show --check HEAD` 通过。8 个 skip 与既有 FUSE 文件锁限制一致。

## 原始交付的行为策略缺口（当前分支修正待复审）

### A05/A09 的测试输入不是 prompt 可见信息

`CaseCharacteristics` 含 `has_catalog_conflict` / `has_rule_conflict`，`allowed_decisions()` 用这些布尔值让 A05/A09 得到 `{ask, refuse}`。但真实候选 prompt 没有告诉模型 GN 705 目录映射或 `second_screw=1 iff bore_d > 70` 规则，并明确说模型没有目录表、耦合冲突交由确定性层。因此单靠该 prompt，模型不能可靠识别 A05 的 `bore_d=20, outer_d=40` 冲突；A09 也缺少判断规则所需的阈值。测试验证的是“已知冲突时策略应如何选择”，不是 prompt 能否让模型识别该冲突。

对应测试 `test_a05_bad_answer_fails` 和 `test_a09_bad_answer_fails` 目前明确断言坏 `answer` envelope 的一致性 checker 返回通过。这个边界对 self-consistency checker 本身是合理的，但不能被总结成 A05/A09 的决策回归已通过。

### `bore_d` 目录范围与目录选项混淆

候选 prompt 的 `5–80 mm` 只是数值范围，CAD-003 的 `bore_d` 实际必须等于 15 个离散目录值之一。独立调用 `allowed_decisions()` 可确认：仅有 `bore_d=75` 且没有 unsupported request 时结果为 `{answer}`，虽然 75 不在目录中。`check_envelope_consistency()` 也只检查数值范围，不检查目录成员关系。下游 CAD-003 仍会阻止构造，因此不是生产安全绕过，但会留下本次要修正的决策不一致。

## 原始验收结论

原始 `9a32756` 可作为**未激活候选草稿**保留，但不得将其 A05/A07/A09 decision 行为宣称为已由 prompt 解决。随后在同一分支实施了窄范围修正，当前待复审：

1. 让模型具备按冻结规则判断的必要信息，或把规则限定为模型可见输入中确实可判断的情况；若不向模型提供目录/规则信息，就把 A05/A09 标记为待确定性层处理，而不要声称 prompt 本身覆盖。若提出引入新的确定性决策层或接口变化，应停止并报告，不扩展到生产代码。
2. 对目录值使用准确表述：明确 15 个合法 `bore_d` 值，或对非成员值一律禁止 `answer`；至少增加只有 `bore_d=75`、无 unsupported feature 的离线案例。
3. 调整测试和文档的验收声明，区分“给定已检测冲突时的理想决策规则”与“prompt 能否从可见信息识别冲突”。保留 A01/A02/A06 等正常路径，避免过度拒绝。
4. 不激活候选、不更新冻结哈希/契约、不调用模型、不改旧批次、不 push/合并。完成后在原任务分支新增 commit，Codex 再复核。

本审查不否定 candidate checker 对合成状态输入的单元测试价值，也不授权正式 APP-001 新批次。最新修正的复审结果应追加在本记录之后，保留本段作为原始发现。

## 窄修复复审（2026-11-07）

复审范围仍为未激活候选；不调用模型、不改冻结接口或正式批次。窄修复和本审查记录已提交到候选分支，commit `b757e9c`。

### 已验证的修正

- 候选 prompt 现在附带 15 行目录映射和 `second_screw = 1 iff bore_d > 70` 规则；候选 checker 从 CAD-003 `CATALOG_ROWS` 派生允许的 `bore_d` 集合，并逐行核对 prompt 表的列顺序和值。
- `bore_d=75` 即使处于数值区间内也不再允许 `answer`；新增单独 75 的策略拒绝测试及 envelope 自洽性拒绝测试。
- A06 `bore_d=70, second_screw=0` 正常边界仍允许 `answer`；A01/A02 正常案例仍允许 `answer`。
- 文档修正了测试证据的表述：A05/A09 冲突标记是离线策略 checker 的已识别输入；静态 prompt 表和规则可供模型判断，但离线测试不构成模型识别能力证据。
- 候选 checker 仍未被 adapter/parser/runner 导入。生产冻结文件相对基线无变更；未触碰 `work/app001-runs/`。

### 独立验证

- Python 3.15.2：候选专项 48/48 通过；LLM 全量 564 通过、8 项跳过；Schema 17/17 通过。
- `py_compile` 和 `git diff --check` 通过。
- 未在 Python 3.11.18 环境复核；8 项 skip 是既有 FUSE 文件锁限制，不计作通过。
- 未发起网络/模型请求，未读取密钥，未修改正式批次。

### 结论和边界

本轮原先指出的两个代码/规格缺口已修正，离线候选达到可继续评估的状态。它仍只是未激活的候选：真实模型能否稳定根据新增目录表识别目录耦合与规则冲突，离线测试无法证明。该结论不代表 prompt 效果通过，也不构成冻结/激活许可或新批次授权。若项目负责人决定评估模型效果，需先完成候选冻结/激活所需的新 ADR 与版本更新，并单独授权唯一正式批次。
