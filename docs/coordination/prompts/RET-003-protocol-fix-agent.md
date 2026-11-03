# RET-003 修正 Prompt：修正 C2 公平性与三条件输入契约

你是 RET-003 的原执行 Agent。Codex 中枢已完成里程碑 1 独立审查。RET-001/RET-002 的交接证据、查询集格式和角色隔离通过，但当前协议不能放行里程碑 2，原因是 C2 人工规则基线间接使用了 held-out 真值。

本轮只修正里程碑 1 协议，不运行正式三条件对照、不调 RET-002 权重、不创建 `results.json`/正式报告，也不修改 RET-001、RET-002、Schema、IR、CAD 编译器/验证器或项目冻结决策。

## 1. 项目根目录与启动检查

必须在共享项目根目录工作：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -8
```

先阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
agent-work/reviews/RET-003-codex-review.md
agent-work/integration/RET-003-retrieval-evaluation/protocol-draft.md
agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json
agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
agent-work/integration/RET-003-retrieval-evaluation/handoff.md
agent-work/integration/RET-002-retrieval-baseline/README.md
agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json
src/schema/set_screw_shaft_collar.py
```

复跑至少一条上游核心命令，建议：

```bash
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval
```

如复跑 RET-001/RET-002 会改写带时间戳报告，结束后恢复由复跑产生的差异。若审查记录、协议或实际代码不一致，先在 checkpoint 标记 `review`，不要覆盖上游结果。

## 2. 中枢审查结论（必须逐条处理）

当前 C2 定义为：使用 CAD-003 的 `bore_d → CATALOG_ROWS` 精确映射，并由规则派生其他字段。完整 `CATALOG_ROWS` 包含 held-out 查询 `bore_d=12/35/80`，因此 C2 能直接查出 held-out 的精确参数。它不是公平的无检索人工模板，而是目录规则 oracle/上界诊断。

修正后不得再把这个 C2 同时写成“公平基线”和“oracle”。协议必须明确区分：

- **公平主比较条件**：各条件使用同一个冻结输入 payload；每个条件只增加自己允许的上下文；不能访问被禁止的候选、目录真值或 held-out 信息。
- **oracle/上界诊断**：允许使用完整目录规则或真值映射，仅用于说明规则上界，不进入 C0/C1/C2 公平主表，不用于声称检索收益。

## 3. C2 修正方案

请按以下优先顺序决定并写入新版协议：

### 推荐方案：将现有 C2 降级为 oracle，取消当前公平 C2

把原来的 `manual_template_rule_v0_proposed` 重命名为明确的 `catalog_rule_oracle_v0` 或等价名称，并注明：

1. 它使用完整 `CATALOG_ROWS`/CAD-003 目录派生规则；
2. 它可能访问包含 held-out 行的规则知识，因此不是无检索公平基线；
3. 它只能作为单独的上界诊断，不能进入公平三条件主表、不能用于调权重、不能用于构造 Prompt 示例；
4. 当前 APP-001 尚未完成，所以 oracle 也保持 `not_run`。

如果无法定义信息量与输入契约都公平的人工 C2，就明确写：RET-003 当前只执行 C1 检索级诊断；APP-001 完成后再决定是否设计公平的 C0/C2 端到端实验。不要为了满足“三条件”字面要求而保留不公平条件。

### 只有确实可证明公平时才允许保留公平 C2

若你提出新的公平 C2，必须满足并逐条证明：

- 不读取完整 `CATALOG_ROWS`；
- 不访问任何 held-out 行的参数、目录索引、派生字段或真值标签；
- 不使用 development/retrieval_source 样本作为隐藏示例，除非协议明确把它们作为所有条件都可获得的公共先验；
- 与 C0/C1 接收同一个冻结输入 payload；
- 只提供预先冻结的输出骨架、字段格式或明确来源的通用规则；
- 不能把 C1 的候选复制成“人工模板”；
- 能够定义可解释的输入、输出、失败处理和指标分母。

如果不能证明上述条件，必须回到推荐方案，不得自行放行。

## 4. 冻结三条件的共同输入契约

在 `protocol-draft.md` 中新增独立小节，明确未来端到端实验的共同输入契约：

1. C0、C1、C2 对同一 `query_id` 接收完全相同的用户输入 payload（自然语言或已冻结结构化输入），同一 `family_id`、同一单位约定和同一输出 Schema。
2. C0 不收到 RET-002 候选、目录行示例、检索距离或人工规则上下文。
3. C1 只额外收到 RET-002 `retrieval_source` 候选及其允许的结构化元数据；候选是参考，不是真值，不能直接复制 `sample_id` 当作正确答案。
4. 公平 C2（若存在）只额外收到预先冻结且不含 held-out 真值的模板/规则上下文；当前完整 `CATALOG_ROWS` 规则只能归入 oracle。
5. 同一后处理链、Schema、Typed CAD IR、CAD 编译器和几何验证器适用于所有确实运行的条件；缺少 APP-001 时，所有端到端字段/Schema/CAD/STEP 指标保持 `not_measured`。
6. 如果不同条件不能接收信息等价的输入，只能分层报告，不能放到同一收益表中。

同时说明哪些规则属于系统共有的后处理校验，哪些规则属于条件额外提供的先验，避免把“所有条件都会调用 Schema”误写成“人工模板可以查目录”。

## 5. 查询集与数据边界

- 优先保持现有 `query-set-draft.json` 不变：3 个 held-out 主查询、诊断查询和缺字段失败诊断继续只引用已有 `sample_id`。
- 如果修改查询集，必须说明原因、保持 manifest hash 和角色校验，并不得复制参数值或新增样本。
- held-out 只能作为查询真值逐例比较，不能进入候选池、规则拟合、权重选择、Prompt 示例或人工模板定义。
- 当前只有 15 条真实记录、3 个候选，`split_status=provisional_small_n`；不得写成正式 benchmark、统计泛化率或显著收益。

## 6. 允许修改的文件与禁止事项

允许修改：

```text
agent-work/integration/RET-003-retrieval-evaluation/protocol-draft.md
agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json  # 仅有充分理由时
agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
agent-work/integration/RET-003-retrieval-evaluation/handoff.md
docs/WORKLOG.md  # 只追加
```

不要修改：

```text
src/**
tests/**
agent-work/data/RET-001-retrieval-manifest/**
agent-work/integration/RET-002-retrieval-baseline/**
docs/DECISIONS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
```

不要创建或运行 `run_evaluation.py`、`evaluation-config.json`、`results.json`、正式收益报告或任何三条件正式对照。不要修改 RET-002 配置、policy id、范围或权重。

## 7. 交付与验收要求

修正后提交：

1. 新协议版本，例如 `RET-003.protocol.v0.1-draft`；
2. 明确 C2 是公平条件、oracle，还是被取消；
3. 三条件共同输入契约和各自额外上下文表；
4. 公平性/泄漏审查说明；
5. 保留所有小样本、许可证、单环境和 `not_measured` 限制；
6. checkpoint/handoff 中记录实际修改、验证命令、未决问题和下一 Agent 关注点；
7. 状态保持 `review`，不自行标记 `done`，不 push。

至少运行并记录：

```bash
python3 -m json.tool agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json
git diff --check
```

如修改查询集或协议导致上游引用需要重新核验，再运行 RET-001 `--tracked-only` 和 RET-002 smoke，并恢复运行报告噪声。

完成后暂停，等待 Codex 中枢重新审查。只有中枢书面确认 C2 身份、公平性和共同输入契约后，才可能生成里程碑 2 的执行 Prompt。
