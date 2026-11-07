# APP-001 Decision Policy v3 (candidate, unactivated)

- 日期：2026-11-07
- 状态：candidate draft，未冻结、未激活
- 关联：ADR-0013（冻结 v2 协议）；`agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate.md`
- 范围：本文档定义候选决策策略 v3 的 decision-gate 规则，映射到冻结 I/O 契约和 acceptance-set 期望行为。不修改冻结 prompt-v2.md、哈希锚点、acceptance-set、parser、adapter 或任何已冻结接口。

## 1. 背景

APP-001 第四批次 8 条 Schema 拒绝的只读分析（`agent-work/reviews/APP-001-phase1-20261107-04-schema-decision-analysis.md`）发现：

- 8/8 显式字段抽取值与冻结样例一致，CAD-003 拒绝符合冻结规则。
- 7/8 返回 `decision=answer`，与样例要求的澄清/拒绝不符。
- 具体偏差：A04 缺 bore_d 仍 answer；A05 目录耦合冲突仍 answer（DeepSeek C1 除外，正确 ask）；A07 目录外 + 不支持请求仍 answer；A09 规则冲突仍 answer。
- A07 Ollama 的 unsupported evidence 覆盖不完整。

本次 Codex 复核指出：原候选 prompt 未向模型提供目录/规则信息，因此 A05/A09 的隐藏冲突标记测试不能证明模型可从可见输入识别冲突；原 prompt 把 5–80 的数值范围误当作完整目录有效性检查。本修正将冻结目录和 second_screw 规则作为候选 prompt 的只读判定参考，并对照 CAD-003 常量验证表格一致性。

主要问题在 `decision` 行为，不是抽取错误或 CAD-003 规则错误。

## 2. 冻结 I/O 契约允许的 decision 值

根据 `src/llm/contract.py` 第 67 行：

```python
DECISION_VALUES: Final[frozenset[str]] = frozenset({"answer", "ask", "refuse"})
```

构造门（来自 prompt-v2.md 第 31 行和 prompt-output-contract-v1.md 第 37 行）：

> 只有 `decision=answer`、无不支持请求且 CAD-003 校验通过时才允许继续 Typed CAD IR/CAD。

v3 候选策略不改 I/O 契约的 decision 值集合，不改构造门定义，不改 envelope 结构。v3 只在 prompt 层面使 decision 选择规则更明确。

## 3. v3 decision-gate 规则

### 3.1 `answer` 的前置条件

`answer` 仅当以下全部条件为真时允许：

| # | 前置条件 | 模型可检测性 |
|---|---|---|
| 1 | `bore_d` 出现在 `extracted_parameters` 中 | 可检测（用户是否说了 bore_d） |
| 2 | `bore_d` 是冻结 CAD-003 目录表中的 15 个精确值之一；仅处于 5–80 mm 范围不够 | 可检测（候选 prompt 附带只读目录决策表） |
| 3 | `unsupported_requests` 为空 | 可检测（用户是否请求了非族特征） |
| 4 | 用户输入中无可直接检测的自相矛盾 | 可检测（用户是否在同一段话中给出直接矛盾的值） |

候选 prompt 的 model-visible context 包含从冻结 CAD-003 `CATALOG_ROWS` 派生的只读表和 `second_screw = 1 iff bore_d > 70` 规则。模型可据此识别被明确提供的耦合参数冲突，并将其作为追问/拒绝依据；它不得据表补造用户未说的字段。确定性 CAD-003 仍会独立验证完整投影并保持最终权威。静态兼容性测试逐行核对 prompt 表与 CAD-003 常量完全一致。

### 3.2 `ask` 的条件

当构造前置条件不满足但用户可通过补充信息合理解决时，输出 `ask`：

- `bore_d` 缺失：列入 `missing_fields`，提出具体追问，保留其他显式主张。
- 用户在同一段话中直接给出互相矛盾的显式值：追问哪个规格为准，保留双方主张。
- 用户措辞表明存在可通过单次澄清解决的歧义。

### 3.3 `refuse` 的条件

当在冻结族范围内无法构造时，输出 `refuse`：

- `bore_d` 显式给出但不属于 15 个离散目录选项（包括范围内的 75 mm，或低于 5 / 高于 80 mm）：保留主张，拒绝构造，不吸附到最近目录值。
- 用户请求冻结族之外的特征（法兰、键槽、材料、镀层、螺纹螺距、倒角、制造公差等）：逐项记入 `unsupported_requests`，拒绝构造。
- 请求根本超出 `set_screw_shaft_collar` 族范围。

### 3.4 多条件优先级

当多个条件同时适用时，选择最严格的：任一条件要求 `refuse` 则输出 `refuse`；否则任一条件要求 `ask` 则输出 `ask`；仅当无任何条件要求 `ask` 或 `refuse` 时才输出 `answer`。

### 3.5 自洽性检查

在返回前，模型应验证以下不变式：

1. 如果 `missing_fields` 非空，`decision` 不得为 `answer`。
2. 如果 `unsupported_requests` 非空，`decision` 不得为 `answer`。
3. `decision` 为 `answer` 仅当 `bore_d` 存在且属于 15 个离散目录选项。
4. 未静默改值、吸附或替换任何显式主张；`extracted_parameters` 中每个值可追溯到 `evidence` 中的用户引用。

### 3.6 不支持请求的证据要求

`unsupported_requests` 中每个条目必须有对应的 `evidence` 条目，`field` 为不支持项名称，`quote` 为用户原文，`source` 为 `"user_input"`。这修正第四批次中 Ollama A07 的 evidence 覆盖不完整问题。

## 4. 与 acceptance-set 期望行为的映射

| 样例 | 特征 | v3 允许 decision | v2 实际偏差 |
|---|---|---|---|
| A01 | 完整一致描述（bore_d=20, outer_d=32, width=14） | `answer` | 无偏差（v2 正确 answer） |
| A02 | 仅 bore_d=24 | `answer` | 无偏差 |
| A03 | 单位换算（1.6 cm → 16 mm） | `answer` | 无偏差 |
| A04 | 缺 bore_d | `ask` 或 `refuse` | v2 返回 answer（偏差） |
| A05 | 目录耦合冲突（bore_d=20, outer_d=40） | `ask` 或 `refuse` | v2 3/4 返回 answer（偏差），1/4 正确 ask |
| A06 | second_screw 边界（bore_d=70, second_screw=0） | `answer` | 无偏差（边界规则允许 0） |
| A07 | 非目录值 + 不支持请求（bore_d=75, 法兰/键槽/阳极氧化） | `refuse` | v2 返回 answer（偏差） |
| A07-only | 仅非目录值 bore_d=75，无 unsupported 请求 | `refuse` | 候选边界回归，防止把数值范围误当目录选择 |
| A08 | 检索示例不可照抄 | `answer` | 无偏差 |
| A09 | 规则冲突（bore_d=80, second_screw=0） | `ask` 或 `refuse` | v2 返回 answer（偏差） |

## 5. 与冻结接口的兼容性

### 5.1 不变部分

- `contract_version`: `app001-io.v1`（不变）
- envelope 键集：9 个键不变
- `decision` 值集合：`{answer, ask, refuse}` 不变
- `EXTRACTABLE_FIELDS`: 6 个字段不变
- `evidence` 结构：`{field, quote, source}` 不变
- `EVIDENCE_SOURCE_VALUES`: `{user_input, retrieval_reference}` 不变
- 构造门定义：`decision=answer` + 无不支持请求 + CAD-003 通过，不变
- CAD-003 Schema 规则不变
- parser/adapter/runner/budget/authorization/provider/重试策略不变

### 5.2 变更部分（需 ADR 激活）

- `prompt_version`: `app001-extraction.v2` → `app001-extraction.v3`（候选）
- prompt 内容：新增 decision-gate 表、自洽性检查、不支持请求证据要求
- 激活需更新：`contract.py` 的 `PROMPT_VERSION`、`parser.py` 的版本检查、`prompt_loader.py` 的 `FROZEN_PROMPT_PATH`/`FROZEN_PROMPT_VERSION`/`FROZEN_PROMPT_FILE_SHA256`

### 5.3 不激活说明

v3 候选不改变 `FORMAL_EVALUATION_ALLOWED = False`，不授权新正式批次，不产生模型效果结论，不改变旧批次。激活需新 ADR + 中枢审查 + 项目负责人确认。

## 6. 离线验证范围

本文档定义的策略通过以下离线方式验证：

- `src/llm/decision_policy_v3_candidate.py`：纯函数实现 v3 decision-gate 逻辑，输入案例特征，输出允许的 decision 值集合。
- `tests/llm/test_decision_policy_v3_candidate.py`：对 A04/A05/A06/A07/A07-only/A09 和正常案例 A01/A02 做离线回归。
- prompt 内容接口兼容性静态检查：envelope 键集、decision 值、字段集合与冻结契约一致，并逐行核对 prompt 的冻结目录表与 CAD-003 `CATALOG_ROWS` 完全一致。
- `CaseCharacteristics` 中的冲突标记是面向离线策略单测的已识别状态；候选 prompt 已提供可识别冲突所需的目录行与阈值规则。测试不运行模型，不构成模型识别能力/效果证据。

不调用真实模型；不修改正式批次；不产生模型效果结论。
