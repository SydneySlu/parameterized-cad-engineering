# Typed CAD IR v0（IR-001）

状态：`review`，等待 Codex 中枢审查后再交给 CAD-005/006。本文是首族 `set_screw_shaft_collar` 的接口规范，不是 CadQuery/OCP 实现。

## 1. 目标与边界

Typed CAD IR v0 把 CAD-003 的已解析参数、确定的特征顺序、依赖和可验证约束编码为一个可解析的中间表示。它表达“要构造什么”和“构造后必须检查什么”，不携带 Python、CadQuery、OCP 对象或任意可执行代码。编译器只能实现白名单 `node_type` 和白名单声明式表达式；遇到未知节点、引用或扩展必须拒绝，而不是猜测。

v0 只支持 `set_screw_shaft_collar`。其构造过程是：解析 GN 705 目录行，按目录行补全派生字段，建立带倒角的环形回转体，按 `screw_d` 的 ISO 261 粗牙查表构造径向紧定螺钉孔切削体，按 0° 和可选 135° 位置依次做布尔差，输出一个预期的单一 solid。固定源码当前实现是 `revolved_ring_approximation`。源码注释所称 M3–M8 可能 no-op 指先前尝试的 helical sweep 布尔，不是当前环形 cutter；R3 通过无孔基体对照复测当前 M6/M12 环形 cutter 均实际移除体积。IR 不把环形近似宣称为真实螺旋螺纹。

v0 不表达自由曲面、草图约束求解、任意 Python、任意 CadQuery 链式调用、装配、多零件、材料/表面处理、真实螺旋扫描、外部图纸读取、网格修复或自动改参。第二族只通过扩展边界预留，不代表已经支持。

## 2. 版本、族和来源

顶层字段的含义如下：

| 字段 | 规则 |
|---|---|
| `ir_version` | 固定为 `typed-cad-ir.v0`；表示字段和语义契约。 |
| `ir_revision` | 当前接口修订为 `0.2.0`。几何比较策略独立由 `CAD-006.geometry-comparison.v1` 标识，不改变 IR JSON 字段结构。 |
| `family.family_id` | 固定为 `set_screw_shaft_collar`；必须与 CAD-003 一致。 |
| `family.extension_namespace` | 固定为 `family.set_screw_shaft_collar.v0`；族特异内容放在此命名空间下。 |
| `source.schema_version` | `set_screw_shaft_collar.v0`，表示输入契约版本。 |
| `source.source_commit` | 固定为 DATA-003 BenchCAD commit `035f467142888edfd0bd7cd73906f9b155c8f43c`；Schema 和语义检查都拒绝其他 commit。其他 commit 不能作为同一 v0 数据契约的替代来源。 |
| `source.adapter_id/version` | 标识 Schema→IR 适配器；本规范建议 `benchcad.set_screw_shaft_collar` / `0.1.0`。 |
| `source.snapshot_status` | 当前首族适配器固定为 `reproducibility_partial`；`reproducible` 不是本适配器可用的 v0 值。 |

`family` 下的 `common` 语义由本规范定义，`family_data` 是族扩展数据。第二族可以使用相同公共包络，但必须使用新的 `family_id`、自己的 `schema_version`、适配器版本和 `family_data` 命名空间。目录名与族 ID 不一致时（例如 DATA-003 记录的 `slotted_din_rail`）必须分别保存 `directory_id` 和 `family_id`，不得静默归一化。

## 3. 参数模型和来源

`parameters` 是数组而非无序的自由字典；每项必须有唯一 `parameter_id`、类型、规范单位、规范化值和来源。首族 v0 固定按 `parameter_id` 字典序序列化：`bore_d, outer_d, screw_d, screw_len, second_screw, width`。JSON Schema 检查该顺序，反序列化语义检查用 `IR_PARAMETER_ORDER_MISMATCH` 重复确认。`input` 只在调用方显式提供值时保留原始值和单位，避免单位来源丢失。

来源枚举只有：

- `user_explicit`：用户在 CAD-003 输入中提供；长度可以先是 `cm`、`m` 或 `in`，IR 中 `value` 已归一化为 mm，`input` 保留原单位。
- `catalog_derived`：由 `bore_d` 选择的 GN 705 目录行派生 `outer_d`、`width`、`screw_d`、`screw_len`。
- `rule_derived`：由 `bore_d > 70` 规则派生 `second_screw`。

`source_ref` 必须指向可追溯证据，例如 `CAD-003.field:outer_d`、`GN705.catalog_row:bore_d=20` 或 `CAD-003.rule:second_screw_threshold`。`unit` 使用 `mm` 或无量纲 `1`；不能用空字符串表达单位。

本族参数表：

| 参数 | 类型/单位 | 必填与来源 | 语义 |
|---|---|---|---|
| `bore_d` | `number` / `mm` | 必填，通常 `user_explicit` | 15 个 GN 705 离散目录选择值。 |
| `outer_d` | `number` / `mm` | 可省略，`catalog_derived` | 目录行 d2。 |
| `width` | `number` / `mm` | 可省略，`catalog_derived` | 目录行 b js14。 |
| `screw_d` | `number` / `mm` | 可省略，`catalog_derived` | 目录行 d3 主径。 |
| `screw_len` | `number` / `mm` | 可省略，`catalog_derived` | 目录行 d3 长度；它保留在 IR 中，但 v0 几何节点不把它当作孔深。 |
| `second_screw` | `integer` / `1` | 可省略，`rule_derived` | `1 iff bore_d > 70`；第二孔角度固定为 135°。 |

参数完整性和目录耦合在构造前执行。显式提供的派生值必须与所选目录行完全一致；缺失的非选择字段由适配器写入 IR 并标为派生。IR 中所有六项都必须存在，除非顶层 `status` 为 `rejected` 且错误发生在参数解析阶段。

## 4. 声明式表达式和引用

节点输入使用以下有限表达式，不允许字符串代码：

- `parameter_ref`：引用 `parameter_id`；
- `node_output_ref`：引用已经产生的 `output_id`；
- `literal`：带单位的数值常量；
- `lookup`：只允许已登记的表，例如 `iso261.coarse_pitch_mm`；
- `formula`：只允许注册的算术/几何公式 ID，参数作为结构化 `args` 传入。

实现必须先检查引用存在、单位兼容和公式白名单，再按 `ordinal` 和依赖拓扑顺序执行。`formula_id` 不是 Python 表达式。v0 公式注册表如下；所有实数输入必须有限，输出也必须有限。长度单位为 mm、角度为 deg、无量纲为 `1`。不支持面积、体积或单位复合；加减、min/max 必须同单位，`half` 保留单位。乘法仅接受长度×无量纲或无量纲×无量纲，输出分别为长度或无量纲。

| `formula_id` | 固定 args（顺序无关、名字必须精确） | 类型/单位 | 定义域和结果 |
|---|---|---|---|
| `half_difference` | `outer_d`, `bore_d` | 两个长度 mm → 长度 mm | `(minuend-subtrahend)/2`；有限实数；负值可计算，但用作壁厚时要求正值。 |
| `half` | `value` | 长度→长度或 `1`→`1` | `value/2`；有限实数。 |
| `multiply` | `value`, `factor` | 长度×`1`（任何方向）→长度，或 `1`×`1`→`1` | 普通实数乘法；禁止长度×长度。 |
| `add` | `left`, `right` | 同单位（mm/mm、deg/deg、1/1）→同单位 | `left+right`。 |
| `subtract` | `left`, `right` | 同单位→同单位 | `left-right`；负结果可计算，几何域另行拒绝。 |
| `min` / `max` | `values`（至少 2 个同单位表达式） | 同单位→同单位 | 数值最小/最大值；参数必须有限。 |
| `collar_chamfer` | `bore_d`, `wall`, `width` | mm, mm, mm → mm | `min(max(0.25, 0.012*bore_d), 0.18*wall, 0.08*width)`；构造前要求 `wall>0, width>0`，结果可因退化输入为 0/负值，必须拒绝而不是绝对值修正。 |
| `thread_minor_radius` | `thread_d`, `pitch` | mm, mm → mm | `thread_d/2 - 0.5413*pitch`；源代码常量精确为 `0.5413`；要求 `thread_d>0,pitch>0,result>0`，否则 `IR_FORMULA_DOMAIN_ERROR`。 |
| `thread_countersink_radius` | `thread_d`, `pitch` | mm, mm → mm | `thread_d/2 + 0.1*pitch`；要求 `thread_d>0,pitch>0` 且有限。 |
| `thread_turn_count` | `z1`, `z0`, `pitch` | mm, mm, mm → 无量纲整数 | 与 Python `max(1, int((z1-z0)/pitch))` 相同：`pitch>0`，先 IEEE 双精度除法，再向 0 截断，最后与 1 取 max。几何有效域另要求 `z1>=z0`；`z1=z0` 返回 1，`0<z1-z0<pitch` 也返回 1。负区间数学上仍返回 1，但属于几何域拒绝。超出有符号 32-bit 整数范围拒绝。 |

实际 IR 示例使用 `half_difference`, `half`, `multiply`, `add`, `subtract` 和 `collar_chamfer`；三个线程公式是被登记、由 cutter 定义消费的契约，不代表当前示例把中间半径/圈数单独作为输入节点。`min/max` 的单一表达结构使用 `args.values` 数组；所有其他函数使用表中具名键。参数缺失/多余键、单位冲突、非有限值和非法运算分别拒绝，稳定码为 `IR_FORMULA_ARGUMENT_ERROR`、`IR_UNIT_MISMATCH`、`IR_FORMULA_DOMAIN_ERROR`。合法案例含长度×无量纲；长度+无量纲、长度×长度、除零、NaN/Inf、`pitch<=0`、非正 minor radius 均是拒绝案例。常量 ISO 261 coarse pitch（mm）按 GN 705 所有 `screw_d` 行固定为：M3 0.5、M4 0.7、M5 0.8、M6 1.0、M8 1.25、M10 1.5、M12 1.75。

`constraint.expression` 只是审计和展示文本；实际执行必须按登记的 `constraint_id` 调用白名单解释器，不能对该字符串执行 `eval`、`exec` 或任意代码。节点 `properties` 只允许本 Schema 登记的元数据（例如 `thread_model`、结构化 `placement`）或 `family_extension` 下的族扩展字段。编译器不得把 `properties`、placement 文本或任何其他字符串当作代码。可执行的节点输入只能是上述五种结构化表达式。

## 5. 节点、ID 和执行顺序

节点 ID 在 IR 内唯一，使用稳定前缀和序号；`ordinal` 从 0 连续递增。每个 `depends_on` 必须只引用更小 `ordinal` 的节点；同一输入 IR 的节点列表不得因软件实现而重排。`enabled_if` 是结构化条件，目前只允许 `parameter_equals`，用于第二螺钉节点。

v0 核心节点白名单及其不可省略的最小契约如下。JSON Schema 按 `node_type` 分派检查这些输入名、expression kind、输出 ID/kind 和 properties；反序列化器用稳定错误码重复检查引用存在性和跨节点关系。`family_extension` 不能替代这些核心字段。

| `node_type` | 作用 | 关键输入/输出 |
|---|---|---|
| `catalog.resolve` | 输入 `bore_d: parameter_ref`；输出 `resolved_parameters: resolved_parameters`；properties 必须为 `catalog_key=bore_d` 和固定集合 `resolved_fields=[outer_d,width,screw_d,screw_len,second_screw]`。 |
| `shape.revolve_profile` | 输入 `bore_d, outer_d, width, chamfer`；输出 `collar_base: shape`；properties 必须为 `profile_kind=chamfered_annulus`、`workplane=XZ`、`axis_local=[0,1,0]`、`axis=Z`（世界轴）、`revolve_degrees=360`。 |
| `feature.tapped_hole_cutter` | 输入 `thread_d, pitch, angle_deg, over, wall, hole_len, z_in, z_out, radial_offset, axial`；输出 `hole_cutter_primary` 或 `hole_cutter_secondary: cutter`；properties 必须登记 `thread_model`、`helical_thread_supported`、`placement_model`、结构化 `placement`。 |
| `boolean.cut` | 输入 `base: node_output_ref`、`tool: node_output_ref`；输出 `solid_after_primary` 或 `solid_after_secondary: solid_candidate`；properties 必须含 `base_ref`、`tool_ref`、`operation=difference`。 |
| `result.single_solid` | 输入 `second_screw: parameter_ref`；输出 `part: part`；properties 必须为 `select_if_zero=solid_after_primary`、`select_if_one=solid_after_secondary`。 |

缺失输入、错误 expression kind、输出契约不匹配或 properties 不匹配分别使用 `IR_NODE_INPUT_MISSING`、`IR_NODE_INPUT_KIND_MISMATCH`、`IR_NODE_OUTPUT_CONTRACT_MISMATCH`、`IR_NODE_PROPERTIES_CONTRACT_MISMATCH`。CAD-005 不得自行猜测节点契约。

`shape.revolve_profile` 的 `profile_kind` 必须为 `chamfered_annulus`；倒角参数按源构造器的 `min(max(0.25, bore_d*0.012), wall*0.18, width*0.08)` 以注册公式表达。两个 `feature.tapped_hole_cutter` 节点必须具有相同的几何输入契约，区别仅为 `enabled_if` 和 `angle_deg`：主孔为 0°，条件第二孔为 135°。它们必须显式提供以下结构化输入：

```text
wall          = half_difference(outer_d, bore_d)
over          = literal(0.5, mm)
hole_len      = add(wall, multiply(over, literal(2, 1)))
z_in          = over
z_out         = add(over, wall)
radial_offset = subtract(half(bore_d), literal(0.5, mm))
axial         = multiply(width, literal(0.5, 1))
```

这对应源 `part.py` 的 `hole_len = wall + 2*over`、`z_in=over`、`z_out=over+wall`、`translate((bore_r-0.5, 0, width/2))`。`Workplane("XZ")` 的局部 x/y/z 分别映射为世界 +X/+Z/-Y，法向为世界 -Y；polyline 第一坐标是径向半径（bore_r 到 od_r），第二坐标是套环轴向高度（0 到 width）。`revolve` 的 `axisStart`/`axisEnd` 按当前 Workplane 局部坐标解释，因此局部 `axisEnd=(0,1,0)` 映射为世界 +Z；契约显式记录 `workplane=XZ`, `axis_local=[0,1,0]`, `axis=Z`（世界轴）。套环轴向范围为世界 Z `[0,width]`，径向圆柱包络在 XY 平面。固定源码 `bore_d=20, outer_d=32, width=14` 的 bbox 约为 `32.0000002 × 32.0000002 × 14.0 mm`。局部 cutter 原点为其旋转实体局部原点，轴沿 +Z，长度从 z=0 到 `hole_len`；+Z 为由内孔向外径的 cutter 正方向。

placement 必须按 Schema 的有序结构执行，齐次列向量左乘：`p_world = Rz(angle_deg) · T(radial_offset,0,axial) · Ry(90°) · p_local`。第一转绕 cutter-local 原点及局部 +Y 轴，方向按右手规则；平移为世界向量 `(bore_d/2-0.5,0,width/2)`；最终转绕世界原点、世界 +Z 轴。`angle_deg=0` 时入口在 `(+radial_offset,0,width/2)`、径向向量为 +X；135° 时为 `(-radial_offset/√2,+radial_offset/√2,width/2)`，轴向仍 +X 先转为该径向方向。90° 的初转将 +Z 映射到 +X。禁止把 135° 误当局部角或绕 cutter 中心旋转。主孔/第二孔的世界位置与 DATA-003 两合法案例 bbox 对照为 `(32,32,14)` 和 `(110,110,22)` mm；旋转不改变包围盒理论尺寸，STEP 导出实测至多约 2e-7 mm 偏差。`screw_len` 是 GN 705 紧定螺钉目录长度，不能当孔深。

`shape.revolve_profile` 轮廓各点为 `(径向半径, Workplane 局部 y)`，分别映射到世界 X/Z；其外/内半径及 8 点折线见源 `part.py`，宽度沿世界 Z。`over=0.5 mm`、回转轴和放置关系都必须由输入/登记的 placement 元数据表达，不能让编译器猜测。`thread_model` 必须为 `revolved_ring_approximation`，`helical_thread_supported` 必须为 `false`，两个孔节点都要明确记录。`screw_len` 仍是目录/任务字段，严禁作为 `hole_len` 或其他孔深输入。

标准合法案例的节点顺序为：解析目录、回转基体、主孔切削、主孔布尔差；当 `second_screw=1` 时再执行第二孔切削、第二孔布尔差，最后输出 `result.single_solid`。即使节点声明了条件，依赖图仍必须完整可检查。

固定图中的 `n6.result` 可以依赖条件节点 `n5.cut.secondary`；当条件为假时，该依赖被标记为 skipped，`select_if_zero` 选择主孔结果。编译器不得因为节点被跳过而重新编号或改变其他节点的 ID。

## 6. 约束、规则和几何验证的分层

`constraints` 只描述可在参数/引用层检查的约束，并带 `constraint_id`、`kind`、`fields`、`expression`、`enforced_at` 和 `source_ref`。本族至少包含：

1. `catalog_row_coupling`：`(outer_d, screw_d, screw_len, width) = catalog[bore_d]`，`enforced_at=preflight`；
2. `second_screw_threshold`：`second_screw == 1 iff bore_d > 70`，`enforced_at=preflight`；
3. `outer_d_gt_bore_d`：`outer_d > bore_d`，`enforced_at=preflight`；
4. `wall_thickness`：`(outer_d-bore_d)/2 > 0.65*screw_d`，`enforced_at=preflight`；
5. `axial_support`：`width >= 1.45*screw_d`，`enforced_at=preflight`；
6. `single_solid_target`：最终应为一个 valid solid，`enforced_at=post_geometry`；
7. `step_roundtrip`：STEP 导出后必须成功回读且实体摘要满足契约，`enforced_at=step_readback`。

前五项来自 CAD-003，失败时**必须先于 `build()`** 返回规则错误。DATA-003 已证明绕过 `check()` 后非法壁厚仍可能构造成功并产生 3 solids；因此构造成功或 STEP 导出成功都不能覆盖规则拒绝。

参数规则和构造/几何验证结果是不同对象：参数错误进入顶层 `errors` 且 `stage=schema/preflight`；`accepted` IR 的构造失败写入 `validation_result` 且 `stage=build, ok=false`，不得伪装成 `post_geometry` 或顶层参数错误；构造成功后，实体计数、`isValid()`、体积、包围盒、面/边摘要进入 `stage=post_geometry`；STEP 导出/回读依次进入 `stage=step_export/step_readback`。每个结果列出精确的 `completed_stages`：build 失败为 `[]`，post_geometry 为 `[build]`，step_export 为 `[build, post_geometry]`，step_readback 为 `[build, post_geometry, step_export]`。只有前置阶段成功后才能进入下一阶段。验证结果不得反写为参数来源或约束通过。`validation_result.ok=true` 时 `errors` 必须为空；`ok=false` 时至少有一条 error，且每条 error 的 `stage` 必须与 result stage 一致。`validation_result` 只能出现在 `status=accepted` 的 IR 中；`rejected` IR 仍只用顶层 `errors`，不带 `validation_result`。

## 7. 错误协议

每个错误至少包含：`code`、`stage`、`severity`、`fields`、`node_ids`、`message`、`retryable`。错误阶段和稳定码如下。schema 阶段包含 IR 语义检查；CAD-003 参数结果进入 preflight；CAD 构造进入 build。

| 阶段 | 稳定码 | 自动重试/字段修复 | fields/node_ids 和用户提示 |
|---|---|---|---|
| `parse` | `IR_INVALID_JSON`, `IR_ROOT_TYPE_INVALID` | 不重试；只可建议语法修正，不自动改值 | JSON pointer；提示解析位置/期望根对象。 |
| `schema` | `IR_SCHEMA_INVALID`, `IR_VERSION_UNSUPPORTED`, `IR_FAMILY_MISMATCH`, `IR_SOURCE_COMMIT_MISMATCH`, `IR_UNKNOWN_NODE_TYPE`, `IR_UNREGISTERED_FORMULA`, `IR_REFERENCE_NOT_FOUND`, `IR_UNIT_MISMATCH`, `IR_FORMULA_DOMAIN_ERROR` | 不重试；可以提示字段名/缺项，禁止解释/执行字符串 | 参数名、JSON pointer、node_id；提示具体路径、值和期望契约。 |
| `preflight` | CAD-003 原码 `MISSING_REQUIRED`, `CATALOG_CHOICE`, `CATALOG_MISMATCH`, `SECOND_SCREW_CONSTRAINT`, `WALL_THICKNESS_TOO_SMALL`, `WIDTH_SUPPORT_TOO_SMALL`, `OUTER_DIAMETER_NOT_GREATER`, `UNSUPPORTED_UNIT` | 不重试；只能按目录补缺失派生项，不覆盖显式冲突 | fields 是参数名、node_ids=[]；说明目录/规则及边界；必须不调用 build。 |
| `build` | `CAD_BUILD_NODE_ERROR`, `CAD_BUILD_BOOLEAN_ERROR`, `CAD_BUILD_UNSUPPORTED_FEATURE` | 确定性几何错误不重试；进程/资源瞬时错误至多重试一次；不自动改字段 | 相关 node_id、参数 fields；提示节点、白名单操作和异常摘要。 |
| `post_geometry` | `GEOMETRY_EMPTY`, `GEOMETRY_INVALID`, `GEOMETRY_MULTI_SOLID`, `GEOMETRY_METRIC_MISSING`, `GEOMETRY_METRIC_NONFINITE`, `GEOMETRY_METRIC_OUT_OF_TOLERANCE` | 不重试、不自动字段修复 | 输出/节点和指标字段；给出观察值、期望值、阈值。 |
| `step_export` | `STEP_EXPORT_ERROR`, `STEP_FILE_MISSING`, `STEP_FILE_EMPTY` | 瞬时 I/O 错误最多重试一次；不自动改字段 | part 输出及路径字段；提示写出异常/文件状态。 |
| `step_readback` | `STEP_READBACK_ERROR`, `STEP_READBACK_EMPTY`, `STEP_READBACK_MULTI_SOLID`, `STEP_READBACK_METRIC_MISSING`, `STEP_READBACK_METRIC_NONFINITE`, `STEP_METRIC_MISMATCH` | 瞬时 I/O 错误最多重试一次；不自动改字段 | part 输出和比较指标；提示回读实体数、缺失值或几何差值。 |

`fields` 指向参数或验证字段，`node_ids` 指向相关节点；不适用时使用空数组。错误码在 v0 内不得复用为另一语义。

## 8. JSON 序列化和兼容策略

规范 JSON 见 [`ir-v0.schema.json`](ir-v0.schema.json)。顶层 `status=accepted` 表示 IR 已通过 IR 结构检查和 CAD-003 前置规则；它**不得**带顶层 `errors`，但可以带 `validation_result`。build、后置几何或 STEP 失败必须保持 `status=accepted` 并写 `validation_result.ok=false`。顶层 `status=rejected` 必须带 `errors`、`nodes` 必须为空且不得带 `validation_result`；前置拒绝不能生成可执行节点。该互斥关系由 JSON Schema 的条件约束表达。

本修正将 IR 示例修订号提升为 `0.2.0`：回转节点增加必填 `workplane`/`axis_local` 并将既有 `axis` 明确定义为世界轴；`validation_result` 增加 `completed_stages` 并允许 build 失败分支。旧 `0.1.0` 序列化内容不满足本 Schema，必须在上游适配器按 `0.2.0` 重新生成；字段名 `axis` 保留，但其语义纠正为世界轴，已存在的 R3 世界 Y 常量与解释不兼容。

JSON Schema 只能表达形状、常量、枚举、参数类型/值类型和状态字段互斥。反序列化后的语义检查还必须执行：六个参数 ID 和所有节点/输出/约束 ID 唯一；`ordinal` 从 0 连续递增；`depends_on` 只引用更早节点且依赖图无环；节点输出、参数和约束引用目标存在；`enabled_if` 参数存在且比较值类型相同；首族 `family_id`、`extension_namespace`、`source.schema_version` 和 `snapshot_status` 与本契约一致；表达式只使用登记公式和登记输出。语义检查的稳定错误码、责任边界和最小算法见 [`semantic-validation.md`](semantic-validation.md)。
JSON Schema 还能表达每个核心 `node_type` 的输入/输出/properties 形状以及 `validation_result` 的 errors 数量和 stage。反序列化后的语义检查还必须执行：六个参数 ID 和所有节点/输出/约束 ID 唯一；参数字典序；`ordinal` 从 0 连续递增；`depends_on` 只引用更早节点且依赖图无环；节点输出、参数和约束引用目标存在；`enabled_if` 参数存在且比较值类型相同；首族 `family_id`、`extension_namespace`、`source.schema_version`、固定 `source_commit` 和 `snapshot_status` 与本契约一致；表达式只使用登记公式和登记输出；`second_screw=1` 只允许 `bore_d>70`。语义检查的稳定错误码、责任边界和最小算法见 [`semantic-validation.md`](semantic-validation.md)。

v0 读取策略：

- `ir_version` 不匹配、族 ID 不匹配、未知必需字段、未知节点/公式/引用一律拒绝；
- `ir_revision` 的 patch 更新可以增加 `extensions` 下的可忽略元数据，不能改变现有字段语义；minor 更新只能增加可选字段和白名单成员，并由适配器声明支持范围；
- major 变化必须使用 `typed-cad-ir.v1`，不得让 v0 读者猜测；
- `schema_version`、`source_commit`、`adapter_version` 都参与可复现记录，不能因“同一参数”而省略；
- 反序列化后应按 `parameter_id`、`ordinal` 和引用图重新检查唯一性与拓扑，而非只信任 JSON 顺序。
- 当前首族适配器只接受 `source.snapshot_status=reproducibility_partial`；收到 `reproducible` 必须返回 `IR_SNAPSHOT_STATUS_UNSUPPORTED`。未来适配器若要引入其他状态，必须新增适配器契约，不能让 v0 读者默默放行。
- 当前首族适配器只接受固定 `source.source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c`；收到其他 commit 必须返回 `IR_SOURCE_COMMIT_MISMATCH`。未来适配器若要支持其他来源，必须新增适配器契约和版本，不能让 v0 读者默默放行。

## 9. 可复现性边界

CAD-006 比较策略的硬门槛先冻结：构造后及 STEP 回读后都要求恰好 1 solid、恰好 1 shell、`isValid=true`；solid/shell/face/edge/vertex 计数必须与同一基准运行完全相等；任一缺失、非数、无穷、空形状或实体数为 0 均失败。STEP 回读的 solid 数必须与构造后完全相同且仍为 1。绝不以容差放过多实体。

数值比较候选配置 `CAD-006.pending.v0`：长度/包围盒各分量采用 `abs_tol=1e-5 mm, rel_tol=1e-8`；体积采用 `abs_tol=1e-4 mm³, rel_tol=1e-8`；面面积和边长列表先分别升序排序，数量必须精确相等，再按逐项上述长度/面积对应单位容差比较（面积候选 `abs_tol=1e-5 mm², rel_tol=1e-8`）。仅在需要生成签名时用 6 位小数量化，签名不替代数值容差比较。重复性比较同参同版本两次几何摘要；STEP 回读比较同一次构造与回读。DATA-003 记录的体积 roundtrip 差约 0.013–0.034 mm³，高于候选的严格绝对阈值，现有数据只保存到 6 位，且没有同一精度下的原始构造后面/边数据。因此全套数值阈值状态为 `pending_measurement`，候选不足以宣称通过；最小补测是两合法案例及 `bore_d=80` hard boundary 的构造前导出 B-Rep 摘要 + 回读摘要至少各 3 次，并包含体积、bbox、排序面面积/边长原始数组，以估计运行内和 STEP 往返误差。`legal-second-screw` 与目录行 80 是同一 hard-boundary 参数案例，不能算额外独立范围点。非法 `outer_d<bore_d` 必须由 preflight 拒绝；绕过 preflight 的对抗后置检查必须仍因 `3 solids != 1` 失败。

同一 IR、同一 source commit、同一 adapter、同一 CadQuery/OCP/操作系统和同一容差配置，目标是得到相同的参数解析、节点图、实体数、`isValid()`、量化体积/包围盒以及登记的面面积/边长摘要。DATA-003 只证明当前环境下这些几何/拓扑指标稳定；它没有证明任意 B-Rep 拓扑完全等价。

STEP 字节 SHA-256 **不稳定**，即使几何摘要相同也可能不同；v0 的重复性判定必须使用结构化几何摘要和明确容差，不能要求文件字节相同。CadQuery/OCP、STEP writer、平台或数值容差改变时，只能保证 IR 和参数/依赖层可复现，几何结果需重新验证。`source.snapshot_status=reproducibility_partial` 反映源码快照、外部图纸和生成资产许可/复现边界，不能被编译器改为 `complete`。

### 9.2 当前生效的数值比较策略：CAD-006.geometry-comparison.v1（2026-11-02）

本附录取代本节前文中标为 CAD-006.pending.v0 的数值候选；前文保留为早期审查历史，不再作为生产实现门槛。策略依据 CAD-005/006-tolerance 提交 e5bcacf 的 15 个合法目录值、每值 3 次 native build 和 STEP 回读结果。

硬门槛仍独立于数值容差：构造后及 STEP 回读后都要求恰好 1 solid、恰好 1 shell、isValid=true；solid/shell/face/edge/vertex 计数必须精确相等。缺失、非数、无穷、空形状、无效实体、零实体或多实体均失败。目录/参数耦合、second_screw 规则、outer_d < bore_d preflight 和壁厚规则均须通过；绕过 preflight 后得到 3 solids 仍必须失败。

**同一进程内重复 native 构造：**参数、IR/Schema/adapter/source 和环境相同的重复调用，结构计数必须精确相同；体积、包围盒六坐标、升序面面积和升序边长数组必须逐值精确相等，数组长度精确相同。实测 30 组同进程重复比较均为 0 差异。该规则仅代表本策略固定环境、同一进程中的重复性判据，不构成跨进程或跨平台承诺；STEP 字节不参与判断。

**同一次 native 结果与 STEP 回读：**

- 所有几何摘要必须有限；solid/shell/face/edge/vertex 数量精确相等。
- 包围盒六坐标逐项使用绝对阈值：abs(a-b) <= 1e-5 mm，不使用相对误差。
- 体积、面面积、边长使用相对误差 abs(a-b)/max(abs(a),abs(b))。每项的绝对误差和相对误差必须同时通过（AND）；不得采用 OR 或把两阈值相加。

| 指标 | 绝对误差上限 | 相对误差上限 |
|---|---:|---:|
| 体积 | 0.0682 mm³ | 3.941e-6 |
| 面面积列表逐项 | 0.00794 mm² | 1.440e-5 |
| 边长列表逐项 | 1e-5 mm | 2.956e-8 |

面面积、边长均要求有限正值，native/readback 数量完全一致；双方分别升序排序后按索引逐项比较，任意一项越界即失败。不得只比均值、总和、直方图或量化摘要。包围盒用绝对值比较，避免坐标为零时相对误差失真。硬拓扑门槛不能被数值阈值覆盖。

体积、面积和边长的绝对/相对阈值是对应观测最大误差的向上取整 2 倍；bbox 和边长绝对值采用 1e-5 mm 的数值比较下限。该策略是 CAD 几何摘要与 STEP 回读的工程验收阈值，不是计量规范或制造公差。策略 ID 必须写入运行/验证 manifest；量化摘要只用于日志或辅助签名，STEP SHA-256 只作产物标识，二者均不能取代直接几何比较。

测量环境为 Python 3.11.18、CadQuery 2.3.0、OCP/cadquery-ocp 7.9.3.0、NumPy 1.26.4、macOS arm64；固定 BenchCAD source commit 为 035f467142888edfd0bd7c73906f9b155c8f43c。测量对象是 BenchCAD 原生 build()，不是项目 IR 编译器。

本策略未验证 Windows/Linux、其他 CPU 架构、其他 Python/CadQuery/OCP/STEP writer 版本、跨进程重复性或第二族。改变环境、构造算法、测量定义或零件族时，须先补充代表性测量并由 Codex 审查，再更新策略版本。CAD-005/006 必须用真实 IR 编译输出测试正常目录、合法 hard boundary、STEP roundtrip 和失败案例；对照 BenchCAD 原生参考几何若超出本策略，须暂停并报告实现差异，不得自行放宽阈值。

IR-001 R3 所列 CAD-006.pending.v0（长度/bbox 1e-5 mm / 1e-8，体积 1e-4 mm³ / 1e-8，面积 1e-5 mm² / 1e-8）是早期未验证候选，现被本策略取代，仅保留在历史审查记录中。IR JSON 字段结构未改变，接口修订仍为 0.2.0；比较行为独立通过策略 ID 版本化。

## 10. 第二族扩展边界和未决问题

公共包络只承诺版本、族标识、来源、参数来源、节点图、约束和错误协议。新族可以在 `family_data` 中声明自己的目录、节点参数、规则和验证摘要；它不能复用本族的 `wall_thickness`、`second_screw` 或线程规则，除非其 Schema 明确声明同一语义。跨族公共节点只有在 v1 冻结前完成兼容性审查后才能加入核心白名单。

未决问题交给 Codex 审查：

- 是否把 `screw_len` 明确标记为“目录/任务字段”并在所有后续适配器中禁止误作孔深；
- 面积/边长数组按升序逐项比较、体积/bbox/面积/边长阈值及摘要策略已由 §9.2 的 CAD-006.geometry-comparison.v1 冻结；跨平台与跨进程行为仍未验证。
- 当前环形螺纹近似已确认发生布尔切除，但其功能精度/与真实螺纹的等价性未审查；是否把它作为首期功能特征仍待负责人/中枢确认。
- `family_data` 的 JSON Schema URI 和跨族公共节点注册表由谁维护；
- 生成 STEP/渲染图的许可证和可发布范围仍是 `license_scope_uncertain`；
- 是否将 `directory_id` 作为所有族的公共来源字段，而不是只在适配器元数据中保留。
- CAD-005 必须在注册表中冻结 `half`、`multiply`、`add`、`subtract` 的参数名、单位推导和数值容差，并逐项检查上述孔节点输入；不能从 placement 字符串推导几何。
- CAD-005 必须按五种 node type 契约消费输入，不能通过 `family_extension` 补齐缺失核心字段。

## 11. 示例状态

`examples/legal-second-screw.json` 是通过 IR Schema 和反序列化语义检查的 `second_screw=1` 结构合法案例，使用 `bore_d=80, outer_d=110, width=22, screw_d=12, screw_len=20`，并包含条件第二孔和 135° 放置。它不声称已经运行 CadQuery/OCP 构造、实体检查或 STEP 回读；CAD-005/006 尚未对该示例执行几何验证。

## 12. 交接

```text
task=IR-001
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/...
verified=python3 -m json.tool ir-v0.schema.json；python3 -m json.tool examples/*.json；结构化示例检查（见 checkpoint.md）
ir_version=typed-cad-ir.v0
known_limits=仅 set_screw_shaft_collar；无 CadQuery/OCP 编译器、STEP 验证器、真实螺旋线程、第二族实现；STEP 字节 hash 不稳定
next=Codex 审查后交给 CAD-005/006
```
