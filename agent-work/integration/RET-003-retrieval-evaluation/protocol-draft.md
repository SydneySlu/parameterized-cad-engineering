# RET-003 探索性检索收益评测协议草案

状态：`review`（里程碑 1；等待 Codex 中枢书面放行）  
任务：RET-003  
协议版本：`RET-003.protocol.v0-draft`  
日期：2026-11-03

## 1. 范围和结论门槛

本协议只针对 BenchCAD 社区族 `set_screw_shaft_collar`，读取 RET-001
`manifest-v0.jsonl` 的 15 条真实目录记录和 RET-002 的确定性输出。manifest
SHA-256 为
`b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`，切分为
development 9、retrieval_source 3、heldout_evaluation 3，
`split_status=provisional_small_n`。这不是正式 benchmark；held-out 结果只逐例描述，
不报告统计显著性、泛化率或跨族能力。

里程碑 1 只冻结协议和查询清单，不运行正式三条件对照，不改 RET-002 配置，不选择新
权重，不生成或伪造 LLM 输出。当前 APP-001 尚未提供固定模型、Prompt、输入集和下游
求解器，因此本协议把工作拆成“当前可做的检索级诊断”和“APP-001 之后的端到端试验”。
检索级诊断不能冒充下游任务收益。

## 2. 评测问题与假设

**Q1：** 在 3 条候选和 3 条 held-out 真值的范围内，RET-002 是否能稳定给出参数上较近、
且角色隔离正确的参考候选？

**Q2：** 检索候选与无检索、人工模板/规则条件相比，是否有可观察的下游字段、Schema、
CAD 或 STEP 收益？当前没有固定下游组件，Q2 的端到端答案暂为 `not_measured`。

**Q3：** 连续字段等权（每个字段权重 0.2、取五字段均值）和 `second_screw` 权重 0.5
是否改变排序？当前只把它作为 RET-002 主策略的固定事实；3 个候选不足以评价权重的
泛化价值。任何敏感性分析都必须另行预注册，不能覆盖主策略或用 held-out 选权重。

**Q4：** 当前接口是否支持自然语言/LLM 收益评测？结论是“接口可作为候选参考输入，
但 APP-001 完成前不可公平测量”；参数查询结果不替代自然语言评测。

预注册的描述性假设（不是显著性检验）：

- H1：合法的 RET-002 查询返回结果全部来自 `retrieval_source`，排序在同一固定环境
  内和独立进程中稳定。
- H2：对 held-out 查询，top-1 参数距离和逐字段误差可逐例报告，但由于真值不在候选
  池中，不能把“命中真值目录行”作为成功率。
- H3：如果未来同一 APP-001 求解器在三条件下运行，检索条件只有在字段/规则/CAD
  通过率相对无检索和模板条件改善且没有增加错误覆盖时，才可作为 Prompt 集成候选。

## 3. 冻结查询集和角色隔离

机器可读清单见同目录 `query-set-draft.json`。正式主查询为 manifest 中的三个
`heldout_evaluation` 记录：`catalog-bore-012`、`catalog-bore-035`、
`catalog-bore-080`。查询参数只在运行时按 `sample_id` 从 manifest 的
`parameters.normalized` 读取，清单不复制参数值或新增样本。每条查询的真值是同一个
manifest 记录，仅用于逐例误差比较和报告，不可进入候选池、距离范围拟合、权重选择或
Prompt 示范。

另列两个非主结果的接口诊断：`catalog-bore-020`（正常目录内 envelope）和
`catalog-bore-080`（second_screw=1 边界 flat 查询）；它们用于重放和泄漏检查，不计入
任何“held-out 收益”分母。结构化失败诊断从已有 `catalog-bore-020` 引用并删除一个
字段，不能由失败样本生成新的目录记录。

候选构造必须等价于：

```text
RetrievalIndex.from_config(
  agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json
)
```

其 `candidate_roles` 只能是 `retrieval_source`，当前候选为
`catalog-bore-006/020/050`；held-out 和 development 永远排除。任何结果行都必须保留
`sample_id`、`split.role`、manifest hash 和 `policy_id`，并在结果中写明
`split_status=provisional_small_n`。

## 4. 三个条件的定义

三条件共享同一个族、同一冻结查询、六个字段的 mm/无量纲输出契约和同一后处理校验。
在 APP-001 之前，三条件均标为 `not_run`；只有获得书面放行后才可执行。

### C0：无检索（`no_retrieval_v0`）

未来端到端试验中，求解器收到同一查询文本/结构化输入，不提供 manifest 示例、候选
参数、检索距离、目录表或人工规则提示；它必须独立输出六个冻结字段和 provenance。
不能把“没有候选输出”当作下游成功或失败，字段/Schema/CAD 指标须等 APP-001 实际
运行后计算。当前没有固定模型、Prompt 和自然语言输入，故所有结果为 `not_measured`。

### C1：参数检索（`ret002_parametric_v1`）

使用已验收的 RET-002 `RET-002.parametric_distance.v1`，连续字段范围、字段权重 0.2、
`second_screw` 权重 0.5、排序 `(total, sample_id)` 和 manifest hash 均固定。候选是
参考示例，不是真值或答案；下游求解器必须在输出中独立给出六个字段，不能直接复制
候选的 `sample_id` 作为通过。

当前可运行的部分只有检索级诊断：记录 top-1/top-k 身份、距离、逐字段误差、候选角色、
排序确定性和查询状态。它不测语言抽取、Schema 修复、CAD 构造或 STEP 回读。

### C2：人工模板/规则（`manual_template_rule_v0_proposed`）

这是需要中枢审阅的固定先验基线，内容在运行前一次性冻结，不读取 RET-002 候选：

1. 固定 `family_id=set_screw_shaft_collar` 和六字段输出骨架；
2. 用已有 CAD-003 Schema 的确定性 `bore_d` → GN705 目录行映射填充
   `outer_d/screw_d/screw_len/width`；
3. 用已有 `second_screw_threshold` 规则填充 `second_screw`；
4. `bore_d` 缺失、非目录值或规则拒绝时直接报告拒绝，不做最近邻替换，不读取
   retrieval_source、held-out 或 development 的示例值。

这不是把检索结果改写成另一种 Prompt，而是一个无候选的固定规则上限/先验条件。若中枢
不接受该规则来源或认为 C0/C2 输入信息不等价，应先标记“不可公平比较”，只执行检索级
诊断并暂停，不得自行改写条件。

## 5. 指标、分母和失败处理

### 5.1 当前可做的检索级诊断

| 指标 | 计算 | 分母/失败处理 | 条件 |
|---|---|---|---|
| 候选角色纯度 | 返回行中 `split.role= retrieval_source` 的行数 / 返回总行数 | 每个查询的 top-k 行；结构化拒绝不丢弃，单列为查询失败 | C1 |
| held-out 泄漏率 | 结果中出现 held-out `sample_id` 的查询数 / 主查询数 | 3 个主查询逐例列出，目标为 0；不称为泛化率 | C1 |
| top-1/top-k 身份 | 逐例列出 sample_id 和 rank | held-out 真值因隔离不可能命中；写 `excluded_by_design`，不计作模型准确率 | C1 |
| 参数距离 | RET-002 `distance.total`、五个连续字段归一化误差、`second_screw` mismatch | 每个返回候选一行；查询失败没有距离，另记 error code | C1 |
| 真值参数绝对误差 | 候选字段值与该查询 manifest 真值逐字段比较 | 只对 3 个 held-out 逐例报告，不合并成统计泛化指标 | C1 |
| 排序稳定性 | 同查询进程内和独立进程 canonical JSON 是否逐字一致 | 通过/失败；失败保留完整输出和环境信息 | C1 |
| Schema 状态 | `catalog_validated` 或 `out_of_catalog_or_unvalidated` | 查询数为分母；异常/拒绝计入失败，不删除 | C1 |

C0 没有候选，C2 没有检索候选，因此上述候选指标对它们为 `not_applicable`，不能用
“无结果”与 C1 的 top-1 做公平比较。

### 5.2 仅在 APP-001 后可做的下游效用

三条件必须使用同一固定模型版本、Prompt 版本、解码参数、输入文本、随机种子策略和
输出 JSON 契约。每个查询都保留成功和失败行。

| 指标 | 分子/分母 | 失败计数 |
|---|---|---|
| 字段精确率 | 所有查询的六字段逐字段 exact match 数 / (查询数 × 6) | 缺失、非法类型、解析失败均为错误字段 |
| 完整输出通过率 | 通过 Schema 与族规则的查询数 / 查询总数 | 任一字段错误、拒绝或超时均失败 |
| CAD 构造通过率 | 实际调用 `compile_ir` 且实体有效的查询数 / 实际调用数 | 编译异常、无效实体、多实体均失败；未调用则 `not_measured` |
| STEP 回读通过率 | 实际导出并通过 CAD-006 回读的查询数 / 实际导出数 | 仅在该条件真实运行并有授权的本地资产时统计；否则 `not_measured` |
| 检索诱导错误率 | C1 相比同查询 C0/C2 新增的错误字段或失败查询数 / 配对查询总数 | 逐例保留错误类型；不以成功案例替代分母 |
| 延迟/调用成本 | 实测 wall time、调用次数或 token（若固定运行器提供） | 缺测写 `not_measured`，不估算 |

当前所有 5.2 指标均为 `not_measured`：APP-001、固定自然语言输入集和统一下游运行器
尚未完成。RET-002 参数查询不能代替这些测量。

## 6. 权重敏感性边界

主结果永远只使用 `RET-002.parametric_distance.v1` 的冻结 0.2/0.5 策略，不修改
`retrieval-config.json` 或 policy id。当前数据只能说明固定策略在 3 个候选上的逐例排序，
不足以判断最优权重或泛化收益。

如中枢在里程碑 2 另行批准探索性离线分析，候选权重必须在运行前写死，例如
`second_screw ∈ {0.0, 0.5, 1.0}`，连续字段保持原策略；只能使用 development 做选择性
排查，不能用 held-out 选“最佳”权重。结果单独标为 sensitivity，不得覆盖主结果，也不
得将排序变化解释为 CAD 或用户收益。

## 7. 防泄漏、公平性和资产边界

- 所有条件使用同一 `query-set-draft.json`、同一族和同一六字段输出契约。
- C1 候选只从 3 条 `retrieval_source` 构造；held-out 只作查询真值，development 只可
  用于协议/脚本开发，二者不进入候选、范围拟合、权重选择或 Prompt 示例。
- C0 不得收到示例或规则；C2 只收到预先冻结的规则文字，不读取候选值；C1 候选只作
  参考，不能当答案复制。
- 不读取 STEP、渲染图、IR 文件、第三方图纸或 BenchCAD Public/Core；不新增样本，
  不训练/微调模型，不调用未固定版本云端模型，不生成人工标签。
- 报告继续披露 `reproducibility_partial`、`MERGED`/非 `release-qualified`、
  `license_scope_uncertain`、`revolved_ring_approximation`、
  `helical_thread_supported=false`，不作强度、安全或可制造性结论。

## 8. 运行和失败处理

里程碑 2 获批后，先依次运行 RET-001 `verify_manifest.py --tracked-only`、RET-002 30
项单测、RET-002 smoke；再由固定脚本读取协议版本、manifest hash、查询 ID 和条件，逐例
写出包括失败的 `results.json`。每次失败保留稳定 error code、stage、fields 和输入
sample_id；不得跳过失败行或只报告成功案例。任何协议、查询、权重或依赖变化都必须先
追加 checkpoint 并重新获得中枢放行。

本里程碑实际重跑结果见 `checkpoint.md`，运行中生成的带时间戳报告已恢复到提交版本。
当前未创建 `run_evaluation.py`、`evaluation-config.json`、`results.json` 或 `report.md`，
因为它们属于里程碑 2。

## 9. 里程碑 1 放行请求

请中枢审阅并明确：

1. 是否接受三个条件的输入/输出定义，尤其是 C2 的 CAD-003 规则先验来源；
2. 是否接受三个 held-out 记录作为唯一主查询，及两个非主结果接口诊断；
3. 是否允许仅执行 C1 检索级诊断，还是必须等 APP-001 才继续；
4. 如批准敏感性分析，是否接受预注册的 `{0.0, 0.5, 1.0}` 候选权重集合。

在这些问题得到书面放行前，RET-003 状态保持 `review`，不运行正式对照、不写收益结论。
