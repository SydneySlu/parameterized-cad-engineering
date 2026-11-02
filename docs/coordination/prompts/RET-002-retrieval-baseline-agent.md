# RET-002 初始化 Prompt：单族确定性检索基线

你是“参数化 CAD 工程辅助设计”项目的 RET-002 检索基线 Agent。你的任务是基于已经验收的 RET-001 manifest，实现一个单族、确定性、可解释的小样本检索基线，供后续 RET-003 对照评测和 APP-001 Prompt 注入使用。

## 1. 项目根目录与已验收基线

必须在以下 Git 根目录工作：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

启动时先运行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -6
```

必须先阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
agent-work/reviews/RET-001-codex-review.md
agent-work/data/RET-001-retrieval-manifest/README.md
agent-work/data/RET-001-retrieval-manifest/checkpoint.md
agent-work/data/RET-001-retrieval-manifest/handoff.md
agent-work/data/RET-001-retrieval-manifest/manifest.schema.json
agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl
agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py
agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md
src/schema/set_screw_shaft_collar.py
```

RET-001 是高风险数据交接。开始实现前必须完成定向复核：

1. 重跑 RET-001 的 `verify_manifest.py --tracked-only`；
2. 抽查 `catalog-bore-020` 和 `catalog-bore-080`；
3. 确认一个负对照仍然拒绝；
4. 确认输入为 manifest 参数/特征字段，输出为检索候选记录，不修改 IR 或 CAD 构造接口；
5. 若交接记录和仓库实际不一致，先写 `review` 或 `blocked` checkpoint，不覆盖 RET-001 产物。

## 2. 任务目标

实现一个可复现的检索基线，输入一个已经通过或正在等待 Schema 校验的首族参数查询，输出按明确距离规则排序的候选样本。

首期目标是验证：

- manifest 中的参数、孔位/接口和特征摘要能否支持可解释检索；
- 检索结果能否稳定地进入后续 Prompt；
- 检索候选能否携带 sample_id、IR 路径、来源和验证摘要；
- 在只有 15 个目录行的情况下，系统是否能暴露数据稀疏和边界问题。

本任务不负责：

- 向量数据库、embedding 模型或语义检索模型；
- LLM Prompt、自然语言意图抽取或 APP-001；
- 训练、微调、强化学习或生成新的 CAD 样本；
- RET-003 的正式收益评测或最终 benchmark 切分；
- 修改 Schema、Typed CAD IR、CAD 编译器、几何验证器或 CAD-006 容差策略。

## 3. 输入与数据边界

固定首族：`set_screw_shaft_collar`。

固定数据文件：

```text
agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl
agent-work/data/RET-001-retrieval-manifest/manifest.schema.json
```

只使用 manifest 中的结构化字段：

- `family_id`；
- `parameters.normalized`；
- `parameters.provenance`；
- `source.catalog_row`；
- `validation` 摘要；
- `ir.path`、`ir.sha256` 和 IR 版本；
- `split.role`、`split.group_id` 和 `split_status`；
- `limitations` 与来源/许可证状态。

默认不读取 STEP、渲染图或第三方图纸。STEP 仍然是 `license_scope_uncertain`，不能进入公共检索语料或提交到仓库。

当前真实样本只有 15 个冻结目录行。不得把它们扩写成 50–100 个样本，不得随机复制成独立实例，也不得下载 BenchCAD Public/Core。

## 4. 建议的实现边界

新增代码放在：

```text
src/retrieval/**
tests/retrieval/**
agent-work/integration/RET-002-retrieval-baseline/**
```

如果判断不需要生产代码，可以只在 `agent-work/integration/RET-002-retrieval-baseline/` 内提供可复跑脚本，但必须说明原因。不要把脚本放在 Agent 的 outputs 目录。

建议提供一个小型、无外部服务依赖的接口，例如：

```python
index = RetrievalIndex.from_manifest(path, candidate_roles={"retrieval_source"})
result = index.query(
    family_id="set_screw_shaft_collar",
    parameters={
        "bore_d": 18,
        "outer_d": 30,
        "screw_d": 6,
        "screw_len": 8,
        "second_screw": 0,
        "width": 14,
    },
    top_k=3,
)
```

接口要求：

- 候选角色必须显式传入，或由配置文件明确写出；不能隐式混入 held-out 样本；
- 查询参数必须有单位约定，内部统一使用 mm；若支持原始 CAD-003 envelope，必须调用现有 Schema 进行归一化，不复制规则；
- 不接受未知 `family_id`、未知字段、非有限数或非法 `top_k`；错误应为结构化错误；
- 结果按总距离升序，再按 `sample_id` 做稳定 tie-break；相同输入在同一环境必须得到相同 JSON 结果；
- 每个候选返回 `sample_id`、`family_id`、`split.role`、`group_id`、`ir.path`、`ir.sha256`、来源 commit、距离总分和字段级距离明细；
- 结果中明确注明 `split_status=provisional_small_n`，不得输出“正式评测集”或“泛化准确率”之类未经验证的结论。

## 5. 距离规则

首版使用透明的参数距离，不要擅自引入学习权重。推荐规则如下；若需要调整，先在 checkpoint 中解释并等待中枢确认：

1. 连续字段：对 `bore_d`、`outer_d`、`screw_d`、`screw_len`、`width` 使用固定目录范围做归一化绝对差：

   `d_field = abs(query - candidate) / (max_value - min_value)`

2. 离散字段：`second_screw` 相同为 0，不同为 1；
3. 总距离：五个连续字段等权平均，再加 `second_screw` 的固定离散项；固定权重必须写在 README 和运行报告中；
4. 缺少查询字段：不得默认为 0 或猜测。要么由 Schema 先补出明确派生字段，要么返回结构化缺失字段错误；
5. 查询落在目录范围外时可以继续做近邻检索，但必须在结果中标记 `query_status=out_of_catalog_or_unvalidated`，不能把查询当成合法目录真值；
6. 不使用 STEP hash 计算几何相似度；hash 只作产物标识。

如果你认为该距离无法支持某类查询，可以提出候选方案，但不要在本任务中直接改成 embedding 或训练模型。

## 6. 交付物

建议建立：

```text
agent-work/integration/RET-002-retrieval-baseline/
├── README.md
├── checkpoint.md
├── handoff.md
├── retrieval-config.json
├── smoke-report.json
└── examples/
    ├── query-in-catalog.json
    ├── query-between-catalog-rows.json
    └── query-invalid.json
```

如果新增 `src/retrieval/` 和 `tests/retrieval/`，必须同步记录模块入口、测试数量和调用方式。

至少覆盖这些案例：

- `bore_d=20` 的目录内查询；
- 位于两个目录行之间、但尚未被 Schema 确认为合法真值的查询；
- `second_screw=1` 的 `bore_d=80` 边界查询；
- 缺少关键字段、未知字段或未知族的失败查询；
- 候选角色为空、`top_k` 越界和重复候选的失败/稳定性检查。

报告至少记录：

- manifest 路径和 SHA-256；
- 使用的 candidate roles、split_status 和 group 规则；
- 距离公式、范围和权重；
- 每个案例的查询状态、候选排序、字段级距离和是否命中同一目录行；
- Python/操作系统版本；
- 是否读取 STEP（首期应为否）；
- 已知限制和下一步建议。

## 7. 文件边界

允许修改：

```text
src/retrieval/**
tests/retrieval/**
agent-work/integration/RET-002-retrieval-baseline/**
docs/WORKLOG.md                                    # 只追加
```

不要修改：

```text
src/schema/**
src/cad_compilation/**
agent-work/typed-cad-ir/**
agent-work/cad-validation/**
agent-work/data/RET-001-retrieval-manifest/**
docs/DECISIONS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
database/**
```

如果 manifest 字段不足、需要改变 split、需要增加第二族、需要改变许可证判断或需要读取 STEP，立即记录 `blocked`，交回 Codex 中枢。

## 8. 三层交接与验收

### 交接 Agent 自检

在 checkpoint/handoff 中记录：

- 修改了哪些源代码、测试和报告；
- 完整运行命令及结果；
- 正常、边界、非法查询是否覆盖；
- 同一查询重复运行是否得到逐字一致的排序结果；
- manifest hash、candidate roles、split_status 和限制是否保留；
- 是否读取或生成了 STEP/渲染物；
- 尚未解决的问题和下一 Agent 关注点。

### 续任 Agent 定向复核

开始前必须：

1. 阅读 checkpoint/handoff 和 RET-001 审查记录；
2. 重跑 manifest `--tracked-only` 校验；
3. 运行一个目录内正常查询和一个非法查询；
4. 运行一个边界查询并检查候选角色没有越界；
5. 确认输出没有把 provisional split 写成正式 benchmark；
6. 发现不一致时先标记 `review` 或 `blocked`，不得覆盖前序成果。

### Codex 中枢审查

完成后保持 `review`，不要自行标记 `done`，不要 push。提交信息格式：

```text
feat: add deterministic retrieval baseline [RET-002]
```

中枢将独立复核接口、排序稳定性、失败路径、数据边界和限制后，决定是否合并并放行 RET-003。

## 9. 明确限制

- 只有单族 15 个真实目录行；
- 当前 split 是 `provisional_small_n`，不是正式 benchmark；
- 只验证固定环境，不作跨平台承诺；
- `reproducibility_partial` 和 `MERGED`/非 `release-qualified` 状态必须继续保留；
- STEP/渲染物是 `license_scope_uncertain`，不提交、不公开、不作为检索输入；
- 螺纹是 `revolved_ring_approximation`，不代表真实螺旋螺纹；
- 检索分数只是参数近邻度，不代表 CAD 几何等价、制造可行性、强度安全或最终生成质量；
- RET-002 不得声称跨族泛化、开放域 CAD 能力或统计显著的检索收益。

开始前先回报启动检查结果；完成一个可运行 smoke slice 后追加 checkpoint，再继续扩展测试和文档。遇到范围、许可或接口冲突立即停止扩大修改。
