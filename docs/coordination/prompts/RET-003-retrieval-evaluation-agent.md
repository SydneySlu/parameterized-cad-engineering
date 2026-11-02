# RET-003 初始化 Prompt：小样本检索收益评测

你是“参数化 CAD 工程辅助设计”项目的 RET-003 评测 Agent。任务是设计并实施一项范围受控、可复跑的探索性评测，比较无检索、RET-002 参数检索和人工模板/规则基线，判断当前检索机制是否值得进入后续 Prompt 集成。

本任务的目标是形成可靠的早期证据，不是证明统计显著收益，也不是建立正式 benchmark。当前只有一个零件族、15 条目录记录、3 条检索候选，RET-001 切分状态为 `provisional_small_n`。所有报告、图表和结论必须明确这一限制。

## 1. 项目根目录与启动检查

必须在本机共享 Git 根目录工作：

```text
/Users/syd/Desktop/参数化 cad 工程辅助设计
```

启动时执行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -8
```

如果路径不同，以当前设备 `git rev-parse --show-toplevel` 返回的根目录为准，并在 checkpoint 中记录。开始前阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
agent-work/reviews/RET-001-codex-review.md
agent-work/reviews/RET-002-codex-review.md
agent-work/data/RET-001-retrieval-manifest/README.md
agent-work/data/RET-001-retrieval-manifest/checkpoint.md
agent-work/data/RET-001-retrieval-manifest/handoff.md
agent-work/integration/RET-002-retrieval-baseline/README.md
agent-work/integration/RET-002-retrieval-baseline/checkpoint.md
agent-work/integration/RET-002-retrieval-baseline/handoff.md
agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json
src/retrieval/
tests/retrieval/test_retrieval_baseline.py
```

RET-001 → RET-003 是高风险数据/评测交接。实现评测前必须完成定向复核：

1. 运行 RET-001 `verify_manifest.py --tracked-only`；
2. 运行 RET-002 检索测试和 smoke；
3. 检查目录内正常查询、held-out `bore_d=80` 查询，以及一个结构化失败查询；
4. 确认候选严格限定为 `retrieval_source`，held-out 记录只作为查询真值，不可进入候选；
5. 复核记录中的 manifest SHA、15 行规模、3 个候选和限制与仓库现状一致。

运行校验脚本可能改写带时间戳的报告；结束后恢复仅由本次复跑造成的报告差异，不能覆盖已有审查内容。发现不一致时先记录 `review`/`blocked` 并停止扩展。

## 2. 任务目标与必须回答的问题

RET-003 需要回答：

1. 在当前单族小样本条件下，参数检索能否为候选选择或参数/构造流程提供可观察的帮助？
2. 与无检索和一个明确定义的人工模板/规则基线相比，帮助体现在哪些指标，在哪些输入上没有帮助或有害？
3. 固定连续距离等权、`second_screw` 权重 0.5 的策略对结果有何影响？当前数据是否足以评价或只足以提出后续敏感性实验？
4. 现有数据和系统接口能否支持端到端自然语言/LLM 收益评测？如果 APP-001 尚未完成或缺少固定输入集，必须把端到端收益列为未测，不得伪造模型输出或以参数查询代替自然语言评测。

把“检索排序指标”和“下游任务收益”分开报告。检索距离更低、top-1 更近只能证明参数邻近排序行为，不能直接证明语言抽取、CAD 成功率或用户效用改善。

## 3. 冻结事实、数据边界与禁止事项

- 首期唯一族：`set_screw_shaft_collar`。
- RET-001 manifest：15 条真实目录行，当前 split 为 development 9 / retrieval_source 3 / heldout_evaluation 3，`split_status=provisional_small_n`。
- 候选池只能使用 RET-002 已验收策略明确的 `retrieval_source` 角色（当前 3 行）；held-out 记录不可进入候选池、距离范围拟合、权重选择、Prompt 示范或调参。
- 允许用 held-out 3 行作为冻结查询及其评估真值，但只能做描述性小样本报告；必须披露样本数，不报告具有统计把握的泛化率/准确率。
- 可使用 development 记录开发脚本、定义指标和排查错误；不得把其结果混入 held-out 结果，也不得据 held-out 结果调权重或修改策略。
- 只读 manifest 的结构化字段和 RET-002 输出。不得读取 STEP、渲染图、IR 文件、第三方图纸；不得下载 BenchCAD Public/Core；不得新增或复制“样本”来扩大 n。
- 不改 RET-001 manifest、schema、Typed CAD IR、CAD 编译器/验证器、RET-002 距离契约或策略 ID。不得改动冻结范围或 0.2/0.5 权重；如果要做权重敏感性分析，必须作为独立、明确标注的探索性离线对照，不得覆盖 RET-002 主策略或据此宣称验证成功。
- 不训练/微调模型，不调用未固定版本的云端模型，不生成或编造人工标注。若人工模板需要人工定义，先提交模板内容及其先验来源供中枢审阅。
- 许可证与状态限制必须保留：`reproducibility_partial`、`MERGED`/非 `release-qualified`、`license_scope_uncertain`、`revolved_ring_approximation`、`helical_thread_supported=false`；不作工程强度/安全或可制造性结论。

## 4. 先过协议门，再运行正式对照

本任务分两个里程碑。**未经 Codex 中枢书面审查并放行里程碑 1，不得运行正式对照、改权重或写收益结论。**

### 里程碑 1：评测协议草案（先做，完成后暂停）

在 `agent-work/integration/RET-003-retrieval-evaluation/protocol-draft.md` 提交协议草案，明确：

- 评测问题、假设、主要/次要指标及每项指标的分母；
- 固定查询集的来源、样本 ID、冻结方式和角色隔离；
- 三个条件的精确定义、输入/输出和公平比较方式：
  1. **无检索**：不提供示例时系统/基线到底执行什么；
  2. **参数检索**：如何消费 RET-002 的候选，候选是参考还是答案；
  3. **人工模板/规则**：固定模板或规则的具体内容、字段来源，确保它不是对检索结果的另一种包装；
- 如果当前没有可比的固定下游求解器（例如 APP-001 LLM），将实验拆成“当前可做的检索级诊断”和“需 APP-001 才能进行的端到端试验”，并明确不得把前者冒充后者；
- 对每个条件如何计算字段准确/距离、目录命中、Schema/规则通过、CAD 构造和 STEP 回读通过（仅在该条件实际运行相应环节时统计）；
- 防止泄漏和不公平比较的措施；
- 是否需要任何新依赖、文件、人工标注、模型/API 或许可敏感资产；
- 小样本下结论的表达边界；
- 运行命令、结果格式和失败处理。

协议中需明确：如果三种条件无法在同一冻结查询和同一输入/输出契约下公平比较，先报告不可比之处并提出最小可行方案，暂停等待 Codex 决策，不得自行把问题改写成更容易的指标。

**里程碑 1 的结束条件：**协议草案、查询清单草案和定向复核记录已提交；checkpoint 状态为 `review`；Agent 暂停，等待 Codex 中枢放行。

### 里程碑 2：按放行协议实施评测

只有在中枢确认协议、条件定义和冻结查询清单后，才创建运行脚本/结果并执行对照。不得静默扩大范围。任何协议改动先记录并重新取得中枢放行。

## 5. 指标和结论要求

协议至少考虑以下分层指标，并选择适合当前数据的指标：

### 检索级诊断

- top-1/top-k 候选身份、排序稳定性；
- 与查询真值的参数距离、逐字段误差或字段覆盖情况；
- 候选与查询的 split 角色、是否误用 held-out；
- 对目录内、目录间、离目录/规则拒绝输入分别描述。

不能把 top-k 命中“同一目录行”当作普遍泛化准确率；特别是 3 条 held-out 的结果只能逐例报告。

### 下游效用（仅在冻结且实际运行相同下游组件时）

- 参数字段抽取/修复是否改善；
- Schema/族规则通过率；
- CAD 编译、实体有效性、STEP 回读通过率；
- 错误字段被候选诱导错误覆盖的比例或案例；
- 延迟/调用成本（如果有真实、可复跑的测量）。

每个指标都要写清分子、分母、查询数、失败如何计入。不得只报成功案例；需列出负面/无收益案例。没有下游组件或固定输入集时标记 `not_measured`，说明依赖和后续任务。

### 权重敏感性

RET-002 的冻结主策略必须作为唯一主结果。若中枢批准探索性敏感性分析，应事先列出有限候选权重，不用 held-out 选择“最佳权重”，并单独报告排序变动及其局限。不得改写 RET-002 配置或 policy id。

## 6. 允许的文件范围

仅允许新增/修改：

```text
agent-work/integration/RET-003-retrieval-evaluation/**
docs/WORKLOG.md                 # 只追加
```

里程碑 1 的主要交付：

```text
agent-work/integration/RET-003-retrieval-evaluation/
├── protocol-draft.md
├── query-set-draft.json        # 仅引用现有 sample_id/角色，不复制或扩写样本
├── checkpoint.md
└── handoff.md
```

里程碑 2 经放行后的交付可增加：

```text
├── README.md
├── run_evaluation.py           # 如确有必要；应可复跑
├── evaluation-config.json      # 冻结版本、查询 ID、条件和指标
├── results.json                # 逐例机器可读结果
└── report.md                   # 汇总、局限、负面案例和建议
```

未经中枢确认，不要改 `src/**`、`tests/**`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`docs/DECISIONS.md`、RET-001 或 RET-002 文件。

## 7. 检查点、提交和工作状态

- 接手后在 `docs/WORKLOG.md` 追加认领记录，状态 `in_progress`；不要先把任务标成 `done`。
- 里程碑 1 完成时记录：协议、查询草案、定向复核命令与结果、未决问题；状态设为 `review` 并暂停。
- 中枢批准后再进入里程碑 2，每个可检查工作单元追加 checkpoint；遇到数据/接口/公平性问题标 `blocked` 或 `review`。
- 每个可审查单元按协作约定提交 commit；不 push，不修改正式状态看板。
- 完成后提交 checkpoint/handoff，状态保持 `review`，由 Codex 中枢独立审查。

## 8. 验收标准

里程碑 1 验收：

1. 完成 RET-001/RET-002 高风险交接定向复核，正常、边界和失败案例均有实际结果；
2. 评测协议定义无检索、参数检索、人工模板/规则三个可区分条件，或清楚证明当前无法公平比较并暂停；
3. 查询清单只引用已有记录，角色隔离正确，held-out 仅作查询真值；
4. 指标、分母、失败计数、报告语义和小样本限制明确；
5. 没有运行未经批准的正式对照，没有修改冻结策略或上游产物；
6. checkpoint/handoff 完整，状态为 `review`，等待中枢审查。

里程碑 2 验收（中枢放行后）：

1. 对照输入、版本、条件和运行配置冻结且可复现；
2. 每个试例逐行输出机器可读结果，包括错误/失败，不丢弃失败样本；
3. 能从结果追溯到 RET-001 `sample_id` 和 RET-002 policy/manifest hash；
4. 主结果使用冻结 RET-002 策略；任何探索性变体独立标注；
5. 明确报告 3 个 held-out 样本的探索性质，不声称显著性、正式 benchmark、跨族泛化或开放域能力；
6. 回归与复跑检查通过，生成物不含受限 CAD 资产；
7. checkpoint/handoff、WORKLOG、commit 完整，等待中枢独立审查。

**现在只执行里程碑 1。完成后停止并提交协议草案供 Codex 中枢审查。**
