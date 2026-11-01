# IR-001-R2：Typed CAD IR v0 最终契约小修正 Agent Prompt

将下面内容复制到负责 IR-001-R2 修正的 Codex/设计 Agent 对话框中。

```text
你是“参数化 CAD 工程辅助设计”项目的 IR-001-R2 Agent，负责对 Typed CAD IR v0 做最后一轮小范围契约修正。

本任务只修正 IR-001-v0 的规范、JSON Schema、语义检查说明、示例和 checkpoint。不要实现 CAD-005 编译器、CAD-006 几何/STEP 验证器、LLM、检索或生产代码，也不要扩大到第二族通用 IR 设计。

## 项目根目录与安全边界

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

先阅读：

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PROJECT_PLAN.md`
4. `docs/TASKS.md`
5. `docs/DECISIONS.md`
6. `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
7. `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
8. `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
9. `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
10. `agent-work/typed-cad-ir/IR-001-v0/examples/`
11. `agent-work/data/DATA-003-single-family-audit/source-audit.md`
12. `agent-work/data/DATA-003-single-family-audit/run-log.md`

不要 reset、clean、stash、rebase 或覆盖其他 Agent 的改动。当前仓库可能有与本任务无关的未提交文件，只修改本任务允许的路径。

## R1 已经确立、不得回退的事实

- v0 只支持 `set_screw_shaft_collar`。
- 当前固定 BenchCAD source commit 是：
  `035f467142888edfd0bd7cd73906f9b155c8f43c`
- 当前适配器的 `snapshot_status` 只能是 `reproducibility_partial`。
- `status=rejected` 是 errors-only、nodes 为空、不得有 `validation_result`；
  `status=accepted` 不得有顶层 `errors`，可以携带后置 `validation_result`。
- `feature.tapped_hole_cutter` 使用结构化 `wall`、`over`、`hole_len`、`z_in`、`z_out`、`radial_offset`、`axial`、`angle_deg` 和 ISO pitch lookup；`screw_len` 不能作为孔深。
- `constraint.expression`、placement 文本和 properties 不能执行；禁止 `eval`、`exec` 和任意 Python 字符串解释。
- STEP 字节 hash 不稳定；`revolved_ring_approximation` 不得描述为真实螺旋线程。

## 本轮必须完成的四项修正

### 1. 固定 source commit

让 Schema 和语义检查都能拒绝错误的 `source.source_commit`：

```text
035f467142888edfd0bd7cd73906f9b155c8f43c
```

推荐在 JSON Schema 中使用 `const`；如果保留一般 40 位哈希的结构定义，也必须增加首族语义检查错误码，例如：

```text
IR_SOURCE_COMMIT_MISMATCH
```

正文、mapping 和 semantic-validation 必须说明：当前 v0 适配器不能把其他 commit 当作同一数据契约。不要修改 DATA-003 的来源事实。

### 2. 明确每种 node_type 的输入、输出和 properties 契约

当前 Schema 仍可能放行“节点类型正确但缺少关键输入”的对象。请补齐首族五种节点的最小契约，至少覆盖：

```text
catalog.resolve
  inputs: bore_d(parameter_ref)
  outputs: resolved_parameters(resolved_parameters)
  properties: catalog_key=bore_d, resolved_fields 为固定目录字段集合

shape.revolve_profile
  inputs: bore_d, outer_d, width, chamfer
  outputs: collar_base(shape)
  properties: profile_kind=chamfered_annulus, axis=Y, revolve_degrees=360

feature.tapped_hole_cutter
  inputs: thread_d, pitch, angle_deg, over, wall, hole_len, z_in, z_out,
          radial_offset, axial
  outputs: hole_cutter_primary 或 hole_cutter_secondary(cutter)
  properties: thread_model、helical_thread_supported、placement_model、placement

boolean.cut
  inputs: base(node_output_ref), tool(node_output_ref)
  outputs: solid_candidate
  properties: base_ref、tool_ref、operation=difference

result.single_solid
  inputs: second_screw(parameter_ref)
  outputs: part(part)
  properties: select_if_zero=solid_after_primary,
              select_if_one=solid_after_secondary
```

可以用 `if/then`、`oneOf`、固定 `properties` 或 semantic-validation 组合表达，但必须明确哪些由 JSON Schema 检查，哪些由反序列化器检查。至少加入稳定错误码，例如：

```text
IR_NODE_INPUT_MISSING
IR_NODE_INPUT_KIND_MISMATCH
IR_NODE_OUTPUT_CONTRACT_MISMATCH
IR_NODE_PROPERTIES_CONTRACT_MISMATCH
```

`node_type` 与输入/输出的契约不能由 CAD-005 Agent 自行猜测。允许保留 `family_extension`，但首族核心节点不能通过任意扩展字段替代必需输入。

### 3. 固定 validation_result 的一致性

明确并验证以下规则：

- `validation_result.ok=true` 时，`validation_result.errors` 必须为空；
- `validation_result.ok=false` 时，`validation_result.errors` 必须至少有一条；
- `validation_result.stage` 必须与错误阶段一致；允许 `post_geometry`、`step_export`、`step_readback` 的后置失败；
- `validation_result` 只能出现在 `status=accepted` 的 IR 中；
- 几何/STEP 后置失败继续保持 `status=accepted`，由 `validation_result.ok=false` 表达，不能改写为顶层 `errors`。

如果 Draft 2020-12 条件表达式足够清晰，请在 JSON Schema 中表达；否则用 semantic-validation 稳定错误码补齐，并在正文说明责任边界。建议错误码：

```text
IR_VALIDATION_RESULT_ERRORS_INCONSISTENT
IR_VALIDATION_STAGE_MISMATCH
```

同步更新 `validation-failure.json` 和合法示例，使它们符合新规则。

### 4. 统一参数序列化顺序并补充 second_screw=1 合法案例

正文规定参数按 `parameter_id` 字典序序列化，但当前示例顺序不一致。请二选一并全局统一：

- 保留“按 `parameter_id` 字典序”，并把所有 accepted 示例改成：
  `bore_d, outer_d, screw_d, screw_len, second_screw, width`；
- 或修改正文为固定首族顺序，并在所有示例和 mapping 中一致。

推荐采用字典序，因为它更适合稳定序列化和比较。

新增一个合法的 `second_screw=1` 示例，建议：

```text
bore_d=80
outer_d=110
width=22
screw_d=12
screw_len=20
second_screw=1
```

该示例必须包含并通过：

- `n4.hole.secondary` 和 `n5.cut.secondary`；
- `enabled_if.parameter_id=second_screw`、`equals=1`；
- 第二孔 `angle_deg=135`；
- `n6.result` 选择 `solid_after_secondary`；
- 两个孔节点相同的结构化几何输入契约；
- 不把 `screw_len` 当作孔深。

如果不声称该案例已经通过实际 CadQuery 构造，只能把它标记为 IR 结构合法案例，并在说明中写明 CAD-005/006 尚未运行。

## 允许修改的文件

只允许修改：

- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
- `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
- `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
- `agent-work/typed-cad-ir/IR-001-v0/examples/*.json`
- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
- `docs/WORKLOG.md`（只追加 R2 checkpoint）

不得修改 `src/`、CAD-003、DATA-003、CAD-005/006 实现文件或其他 Agent 工作目录。

## 验证要求

必须运行并记录：

1. `python3 -m json.tool` 检查 Schema 和全部示例；
2. Draft 2020-12 JSON Schema validator 检查所有现有和新增示例；
3. Schema 自检 `Draft202012Validator.check_schema(schema)`；
4. 反例至少包括：
   - 错误 `source_commit`；
   - 缺少 `feature.tapped_hole_cutter.thread_d`；
   - 缺少 `boolean.cut.base` 或 `tool`；
   - 缺少/错误的 `result.single_solid` 选择属性；
   - `validation_result.ok=true` 但 errors 非空；
   - `validation_result.ok=false` 但 errors 为空；
   - 参数顺序不符合约定；
   - `second_screw=1` 但 `bore_d<=70`；
5. 语义检查覆盖 ID 唯一性、ordinal、依赖拓扑、引用存在性、条件类型和首族常量；
6. `git diff --check` 通过。

如果环境没有 `jsonschema`，可在 `/tmp` 建隔离环境安装，不得将临时依赖写入仓库。

## 明确不做

- 不实现 CAD-005 编译器或 CAD-006 验证器；
- 不运行或声称完成 CadQuery/STEP 几何验证；
- 不修改 BenchCAD 源码和 CAD-003 参数规则；
- 不引入真实螺旋线程、装配、多族泛化或任意 Python；
- 不把结构合法示例描述成几何成功示例；
- 不删除 `reproducibility_partial`、许可证边界或 STEP hash 不稳定说明。

## 三层交接检查（高风险任务，必须执行）

本任务涉及接口、数据来源或 CAD 执行链，必须执行 `docs/coordination/handoff-review-protocol.md` 中的 double check。

如果本任务是续任任务，开始实现前必须：

1. 阅读上一个 Agent 的 checkpoint、交接文档和提交；
2. 复跑至少一条上一个 Agent 声称通过的核心命令；
3. 检查一个正常案例和一个失败/拒绝案例；
4. 确认输入输出接口、版本、来源和已知限制与本任务一致。

如果交接记录与实际结果不一致，先记录 `review` 或 `blocked`，不要直接覆盖前一个 Agent 的成果。

完成交接前必须记录：修改内容、实际命令及结果、已确认内容、未解决问题和下一 Agent 的重点。`checkpoint.md` 中必须包含 `handoff_self_check` 和（如有前序任务）`handoff_successor_check`。续任复核是定向复核，不替代 Codex 中枢的最终独立审查。

## 交接要求

在 `checkpoint.md` 记录：

```text
task=IR-001-R2
status=review | blocked
changed=<文件列表>
verified=<Schema、语义检查、示例和反例命令结果>
contract_fixes=<source commit、节点契约、validation_result、一致排序、second_screw 合法案例>
known_limits=<仍由 CAD-005/006 冻结的公式、单位、容差和几何运行限制>
next=Codex 中枢最终复核后再启动 CAD-005/006
```

提交信息使用：

`docs: finalize typed cad ir v0 contract [IR-001-R2]`

完成后停在 `review`，不要自行启动 CAD-005/006。
```
