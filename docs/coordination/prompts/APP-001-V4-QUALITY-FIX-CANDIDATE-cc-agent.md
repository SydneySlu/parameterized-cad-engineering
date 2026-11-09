# APP-001-V4-QUALITY-FIX-CANDIDATE：离线决策质量候选修正

## 任务定位

针对正式批次 `app001-phase1-v4-20261109-01` 的两类已核实偏差，建立**未激活、无网络、无模型调用**的版本化候选策略和离线测试。此任务只准备候选，不改变生产 v4，不重跑或修改旧批次，也不申请新的正式运行授权。

执行者：CC。分支建议：`cc/APP-001-V4-QUALITY-FIX-CANDIDATE`。

## 开始前必须核对

在共享仓库 `/Users/syd/Desktop/参数化 cad 工程辅助设计` 内工作，先阅读：

1. `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`；
2. `docs/coordination/handoff-review-protocol.md`、`docs/coordination/project-memory-and-delivery-playbook.md`；
3. `agent-work/reviews/APP-001-phase1-v4-20261109-01-codex-review.md`；
4. `agent-work/llm/APP-001-v4-activation/prompt-v4.md`、`agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json`；
5. 当前 v4 checker/候选测试及 `src/llm/parser.py`、`src/llm/contract.py` 的实际接口。

开始实现前写入 checkpoint 的 `handoff_successor_check`，至少重跑一条现有离线核心测试，并检查一个正常案例和一个拒绝案例。若工作区、基线或交接记录不一致，先标记 `review`/`blocked`，不要覆盖既有工作。

## 已确认的输入证据

只读参考 `work/app001-runs/app001-phase1-v4-20261109-01/runs.jsonl` 和 raw response：

- Ollama 过度拒绝：A02 C1、A03 C0、A08 C1。三条均正确提取了显式字段、`missing_fields=[]`、`unsupported_requests=[]`，且确定性 Schema 通过；应允许 `decision=answer`。
- DeepSeek A05 C0/C1：`extracted_parameters` 已含 `bore_d=20` 和 `outer_d=40`，但 `missing_fields` 仍含 `outer_d`；该 envelope 不自洽。

这些证据只用于离线测试和策略说明，不得复制 evaluator 标签进模型输入。

## 允许的修改范围

只允许新增或修改以下候选/测试/交付记录文件：

- `agent-work/llm/APP-001-v4-quality-fix-candidate/` 下的候选策略、候选 prompt 说明、manifest/checkpoint/handoff；
- `src/llm/decision_policy_v5_candidate.py` 或同等命名的**纯函数离线 checker**，不得被 `adapter.py`、`parser.py`、`runner.py`、`contract.py`、`prompt_loader.py` 导入；
- 对应 `tests/llm/test_decision_policy_v5_candidate.py` 或等价专项测试；
- `docs/WORKLOG.md` 追加一条记录；必要时在 `docs/PROJECT_STATUS.md` 只更新任务状态/下一步。

不得修改：

- 生产 `prompt-v4.md`、`src/llm/contract.py`、`src/llm/prompt_loader.py`、`src/llm/parser.py`、`src/llm/adapter.py`、`src/llm/providers.py`、`src/llm/runner.py`；
- `acceptance-set-v0.json`、RET-002、CAD-003、ADR、预算/授权逻辑；
- `work/app001-runs/app001-phase1-v4-20261109-01/` 及任何旧批次。

## 候选必须表达的规则

### P1：合法显式输入不因 C1 检索而过度拒绝

候选规则必须明确：

1. 用户已明确给出合法目录 `bore_d`，且没有 `missing_fields`、`unsupported_requests` 或目录/规则冲突时，`decision` 允许且应优先为 `answer`；
2. C1 的 retrieval reference 只能作为不可信参考，不能制造“用户输入不完整/有歧义”，也不能覆盖用户显式值；
3. C0 与 C1 在同一用户输入上不能仅因是否提供 retrieval context 而改变 `answer`/`ask`/`refuse`；
4. 单位可精确归一化（例如 `1.6 cm -> 16 mm`）且归一化值为合法目录值时，不得仅因原始单位而拒绝；
5. 仍保留 A04 缺失 `bore_d`、A05 目录冲突、A07 越界/unsupported、A09 规则冲突的拒绝或澄清边界。

### P2：envelope 自洽性

候选 checker 必须拒绝以下不一致：

1. `missing_fields` 中的每个字段必须确实不在 `extracted_parameters` 中；
2. 已出现在 `extracted_parameters` 的显式字段不得同时列为 `missing_fields`，即使该字段与目录冲突；
3. A05 应保留 `bore_d=20`、`outer_d=40`，将冲突交给确定性 Schema/决策，不得把 `outer_d` 伪装为缺失；
4. `decision=answer` 仍不得与非空 `missing_fields`、非空 `unsupported_requests` 或确定性冲突共存；
5. checker 不得自动修正、删除或改写模型的显式 claim，只能返回可审计的拒绝原因。

## 测试最低要求

离线 fixture 测试至少覆盖：

- A02 C0/C1、A03 C0/C1、A08 C0/C1：合法输入均允许 `answer`，C0/C1 decision 一致；
- A01/A06：正常与边界正常路径不被过度拒绝；
- A04、A05、A07、A09：缺失、目录冲突、越界/unsupported、规则冲突仍不能 `answer`；
- A05 的两个 envelope：`outer_d` 不得进入 `missing_fields`；
- 反向测试：把合法输入改成缺失/unsupported/冲突时，checker 必须失败；
- 候选版本/9 键 envelope/decision 枚举/显式字段保留与当前 `app001-io.v1` 兼容；
- 生产模块导入隔离：候选 checker 不被正式 adapter/parser/runner 路径导入。

测试只可使用脱敏 fixture/Fake 数据，不得访问网络、`.env`、API key 或真实 Ollama/DeepSeek。

## 版本和交付边界

- 候选可以使用 `app001-extraction.v5-candidate` 等明确标识，但不得更新生产 `PROMPT_VERSION`，不得修改 `FROZEN_PROMPT_*` 锚点。
- 不创建或修改正式批次，不生成效果结论，不改变 `FORMAL_EVALUATION_ALLOWED`。
- 完成后必须提交 Git commit，追加 `docs/WORKLOG.md`，checkpoint/handoff 写明：修改文件、实际命令、正常/失败案例、版本/hash、未解决限制和下一 Agent 关注点。
- 报告中明确区分：离线 checker 通过 ≠ 模型效果通过；若未来要测候选，必须另建唯一 `batch_id`、走新授权和 Codex preflight。

## 退出条件

专项测试、受影响的 LLM/schema 回归、`py_compile` 和 `git diff --check` 实际通过；工作区干净；提交已创建。不得 push、合并或启动正式批次，除非后续另行授权。
