# APP-001 Decision Policy v3 Candidate Checkpoint

- 日期：2026-11-07
- Agent：CC
- 任务：APP-001-DECISION-POLICY-V3-DRAFT
- 状态：candidate draft，未冻结、未激活；已按 Codex review 做窄范围修正，等待复审
- 分支：`cc/APP-001-DECISION-POLICY-V3-DRAFT`（未 push，未合并到 main）

## 范围

为 APP-001 准备一个候选的新版本决策策略（v3），修正第四批次分析报告中发现的 `decision` 行为不一致：

1. 必填字段/目录选择器缺失时，不得输出 `answer`；按现有契约选择 `ask` 或 `refuse`。
2. 用户显式参数与目录耦合或确定性规则冲突时，保留原始显式主张，不得静默改值；按现有契约要求澄清或拒绝。
3. 存在不支持请求时，不得把请求描述为可完成；按现有契约拒绝，并为不支持项提供符合契约的证据。
4. 只有满足现有构造门条件时才可输出 `answer`。

## 交付物

| 文件 | 用途 |
|---|---|
| `agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate.md` | 候选 prompt v3，含 decision-gate 表、自洽性检查、不支持请求证据要求 |
| `agent-work/llm/APP-001-baseline-prep/decision-policy-v3-candidate.md` | 策略规格，映射到 I/O 契约和 acceptance-set 期望行为 |
| `src/llm/decision_policy_v3_candidate.py` | 纯函数离线 checker，未被 adapter/parser/runner 导入 |
| `tests/llm/test_decision_policy_v3_candidate.py` | 离线回归测试，44 项 |
| `agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate-checkpoint.md` | 本文件 |

## 未修改的冻结接口

- `prompt-v2.md` — 不修改
- `prompt_loader.py` 的 `FROZEN_PROMPT_FILE_SHA256` / `FROZEN_PROMPT_VERSION` — 不修改
- `acceptance-set-v0.json` — 不修改
- `contract.py` 的 `PROMPT_VERSION` — 不修改（v3 使用独立候选常量 `CANDIDATE_PROMPT_VERSION`）
- `parser.py` — 不修改
- `adapter.py` — 不修改
- `runner.py` — 不修改
- CAD-003 Schema (`src/schema/set_screw_shaft_collar.py`) — 不修改
- RET-002 查询、provider 参数、重试策略、预算/授权 — 不修改
- `work/app001-runs/` 正式批次 — 不修改

## 接口兼容性

v3 候选保持以下不变：

- `contract_version`: `app001-io.v1`（与 v2 相同）
- envelope 键集：9 键不变
- `decision` 值集合：`{answer, ask, refuse}` 不变
- `EXTRACTABLE_FIELDS`: 6 字段不变
- `evidence` 结构：`{field, quote, source}` 不变
- `EVIDENCE_SOURCE_VALUES`: `{user_input, retrieval_reference}` 不变
- 构造门定义：`decision=answer` + 无不支持请求 + CAD-003 通过，不变

v3 候选变更：

- `prompt_version`: `app001-extraction.v2` → `app001-extraction.v3`（候选）
- prompt 内容：新增 decision-gate 表、自洽性检查、不支持请求证据要求
- 决策参考：候选 prompt 附带 15 行冻结 GN 705 目录表及 `second_screw = 1 iff bore_d > 70` 规则；checker 静态比对 prompt 表与 CAD-003 `CATALOG_ROWS`，未修改 Schema
- `answer` 对 `bore_d` 的限制从仅数值范围修正为必须为精确目录值；增加 `bore_d=75` 单独出现的拒绝案例和 A06 `bore_d=70` 边界正常案例

激活 v3 需更新的冻结接口（需新 ADR）：

- `contract.py` 的 `PROMPT_VERSION`
- `parser.py` 的版本检查
- `prompt_loader.py` 的 `FROZEN_PROMPT_PATH` / `FROZEN_PROMPT_VERSION` / `FROZEN_PROMPT_FILE_SHA256`

## 离线验证（Codex 窄修复复核）

| 检查 | 命令 | 结果 |
|---|---|---|
| v3 专项测试 | `PYTHONPATH=src:. python3 -m unittest tests.llm.test_decision_policy_v3_candidate -v` | 48 passed |
| LLM 全量回归 | `PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q` | 564 passed, 8 skipped |
| Schema 测试 | `PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q` | 17 passed |
| py_compile | `python3 -m py_compile src/llm/decision_policy_v3_candidate.py tests/llm/test_decision_policy_v3_candidate.py` | OK |
| git diff --check | `git diff --check` | CLEAN |

Python 版本：3.15.2（当前环境；未在 Python 3.11.18 复核）

8 个 skip 为既有 FUSE 文件锁限制，不是本工作单元引入。专项正常案例包括 A01/A02/A06；拒绝/澄清案例包括 A04/A05/A07/A07-only/A09。静态测试逐行比较 prompt 表和 CAD-003 冻结目录。

## 测试覆盖

- A04（缺 bore_d）：`allowed_decisions` 返回 `{ask, refuse}`，不含 `answer`
- A05（目录耦合冲突）：`allowed_decisions` 返回 `{ask, refuse}`，不含 `answer`
- A07（目录外 + 不支持请求）：`allowed_decisions` 返回 `{refuse}`
- A09（规则冲突）：`allowed_decisions` 返回 `{ask, refuse}`，不含 `answer`
- A01/A02（正常案例）：`allowed_decisions` 返回 `{answer}`
- 字段主张保留：检测静默改值、缺失主张；保留冲突双方的原始值
- 不支持请求证据：每个 unsupported_request 必须有对应 evidence 条目
- envelope 自洽性：`missing_fields` 非空时 answer 失败；`unsupported_requests` 非空时 answer 失败；bore_d 缺失或越界时 answer 失败
- prompt 接口兼容性：envelope 键集、contract_version、prompt_version、decision 值、字段集合与冻结契约一致

## handoff_self_check

```text
handoff_self_check:
  changed=
    agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate.md (新增)
    agent-work/llm/APP-001-baseline-prep/decision-policy-v3-candidate.md (新增)
    agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate-checkpoint.md (新增)
    src/llm/decision_policy_v3_candidate.py (新增)
    tests/llm/test_decision_policy_v3_candidate.py (新增)
  commands=
    python3 --version → Python 3.15.2
    PYTHONPATH=src:. python3 -m unittest tests.llm.test_decision_policy_v3_candidate -v → Ran 48, OK
    PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 564, OK (skipped=8)
    PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
    python3 -m py_compile src/llm/decision_policy_v3_candidate.py tests/llm/test_decision_policy_v3_candidate.py → OK
    git diff --check → CLEAN
  confirmed=
    v3 离线 decision-gate 对 acceptance-set A04/A05/A07/A09 的已识别案例状态给出预期集合；prompt 提供 A05/A09 所需目录行/规则，但单元测试不证明模型能正确识别
    候选离散目录表与冻结 CAD-003 常量逐行一致；bore_d=75 即使无其他 unsupported 请求也不允许 answer
    A06 的 bore_d=70 / second_screw=0 边界仍允许 answer
    A01/A02 正常案例允许 answer（策略不会过度拒绝）
    字段主张保留检测覆盖静默改值和缺失
    不支持请求证据要求覆盖每个 unsupported_request
    v3 prompt envelope 接口与冻结 I/O 契约兼容（键集、decision 值、contract_version 不变）
    冻结文件（prompt-v2.md、哈希锚点、acceptance-set、parser、adapter、CAD-003）未修改
    未调用真实模型、未读取密钥、未修改正式批次
  unresolved=
    v3 候选未激活；激活需新 ADR 更新 contract.py/parser.py/prompt_loader.py
    真实模型能否根据目录表稳定识别耦合/规则冲突未经验证；确定性 CAD-003 层仍是最终安全门
    未在 Python 3.11.18 环境复核（当前为 3.15.2）
    未产生模型效果结论；不授权新正式批次
  next_agent_focus=
    项目负责人决定是否继续保留或启动版本化激活决策；真实模型效果如需验证，必须另行审批唯一批次
    若激活 v3，需新 ADR 并更新 contract.py/parser.py/prompt_loader.py
```

## handoff_successor_check

```text
handoff_successor_check:
  predecessor=APP-001-DECISION-POLICY-V3-DRAFT 原始交付 9a32756 + Codex review a9b95ed；本次窄修工作树改动待提交
  files_format=候选 prompt/spec/checker/测试/checkpoint 均存在；checker 仍未接入 adapter/parser/runner；冻结生产文件未改
  core_rerun=专项测试 48/48；LLM 全量 564 passed/8 skipped；Schema 17/17；Python 3.15.2；py_compile 与 diff --check 通过
  normal_case=A01/A02 answer 可用；A06 的 bore_d=70、second_screw=0 边界 answer 可用
  failure_case=A07-only 的 bore_d=75 返回 refuse；envelope 中 bore_d=75 + answer 被一致性检查拒绝；A04/A05/A07/A09 不允许 answer
  interface=仍保持 app001-io.v1、9-key envelope、decision/evidence 结构和构造门；只更新未激活候选 prompt 内容
  limits=静态表格一致性和离线策略测试不证明真实模型识别能力；未在 Python 3.11.18 复核；8 个 FUSE skip
  result=pass（仅指可在既定边界内继续；候选整体仍待负责人决策）
  blocking_issue=无代码/接口阻塞；不授权激活或模型运行
```

## 限制

- 本工作单元是候选策略和离线行为测试，不是冻结或启用新 prompt。
- 不产生新模型效果结论，不授权新正式批次。
- v3 prompt 对目录耦合冲突和规则冲突的检测依赖模型判断力；模型不持有完整目录表，确定性 CAD-003 层仍是最终安全门。
- envelope 自洽性 checker 检测模型可检测的不一致（missing_fields + answer、unsupported_requests + answer、bore_d 缺失/越界 + answer），不检测 CAD-003 目录/规则冲突（由确定性层负责）。
