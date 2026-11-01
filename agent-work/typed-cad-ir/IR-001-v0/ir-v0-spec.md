# Typed CAD IR v0（IR-001）

状态：`review`，等待 Codex 中枢审查后再交给 CAD-005/006。本文是首族 `set_screw_shaft_collar` 的接口规范，不是 CadQuery/OCP 实现。

## 1. 目标与边界

Typed CAD IR v0 把 CAD-003 的已解析参数、确定的特征顺序、依赖和可验证约束编码为一个可解析的中间表示。它表达“要构造什么”和“构造后必须检查什么”，不携带 Python、CadQuery、OCP 对象或任意可执行代码。编译器只能实现白名单 `node_type` 和白名单声明式表达式；遇到未知节点、引用或扩展必须拒绝，而不是猜测。

v0 只支持 `set_screw_shaft_collar`。其构造过程是：解析 GN 705 目录行，按目录行补全派生字段，建立带倒角的环形回转体，按 `screw_d` 的 ISO 261 粗牙查表构造径向紧定螺钉孔切削体，按 0° 和可选 135° 位置依次做布尔差，输出一个预期的单一 solid。源码中“螺纹切削在 M3–M8 可能 no-op”的事实由 `thread_model` 和验证契约保留；IR 不把环形近似宣称为真实螺旋螺纹。

v0 不表达自由曲面、草图约束求解、任意 Python、任意 CadQuery 链式调用、装配、多零件、材料/表面处理、真实螺旋扫描、外部图纸读取、网格修复或自动改参。第二族只通过扩展边界预留，不代表已经支持。

## 2. 版本、族和来源

顶层字段的含义如下：

| 字段 | 规则 |
|---|---|
| `ir_version` | 固定为 `typed-cad-ir.v0`；表示字段和语义契约。 |
| `ir_revision` | 当前为 `0.1.0`。同一 v0 内只允许兼容的可选字段和文档修订。 |
| `family.family_id` | 固定为 `set_screw_shaft_collar`；必须与 CAD-003 一致。 |
| `family.extension_namespace` | 固定为 `family.set_screw_shaft_collar.v0`；族特异内容放在此命名空间下。 |
| `source.schema_version` | `set_screw_shaft_collar.v0`，表示输入契约版本。 |
| `source.source_commit` | DATA-003 固定 BenchCAD commit `035f467142888edfd0bd7cd73906f9b155c8f43c`。 |
| `source.adapter_id/version` | 标识 Schema→IR 适配器；本规范建议 `benchcad.set_screw_shaft_collar` / `0.1.0`。 |
| `source.snapshot_status` | 固定记录 `reproducibility_partial`，不能省略或改写成完全可复现。 |

`family` 下的 `common` 语义由本规范定义，`family_data` 是族扩展数据。第二族可以使用相同公共包络，但必须使用新的 `family_id`、自己的 `schema_version`、适配器版本和 `family_data` 命名空间。目录名与族 ID 不一致时（例如 DATA-003 记录的 `slotted_din_rail`）必须分别保存 `directory_id` 和 `family_id`，不得静默归一化。

## 3. 参数模型和来源

`parameters` 是数组而非无序的自由字典；每项必须有唯一 `parameter_id`、类型、规范单位、规范化值和来源。数组按 `parameter_id` 的字典序序列化，便于稳定比较。`input` 只在调用方显式提供值时保留原始值和单位，避免单位来源丢失。

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

实现必须先检查引用存在、单位兼容和公式白名单，再按 `ordinal` 和依赖拓扑顺序执行。`formula_id` 不是 Python 表达式。v0 登记的公式为：`half_difference`、`multiply`、`add`、`subtract`、`min`、`max`、`collar_chamfer`、`thread_minor_radius`、`thread_countersink_radius`、`thread_turn_count`。

## 5. 节点、ID 和执行顺序

节点 ID 在 IR 内唯一，使用稳定前缀和序号；`ordinal` 从 0 连续递增。每个 `depends_on` 必须只引用更小 `ordinal` 的节点；同一输入 IR 的节点列表不得因软件实现而重排。`enabled_if` 是结构化条件，目前只允许 `parameter_equals`，用于第二螺钉节点。

v0 核心节点白名单：

| `node_type` | 作用 | 关键输入/输出 |
|---|---|---|
| `catalog.resolve` | 记录目录行解析和六个最终参数 | `bore_d`；输出 `resolved_parameters` |
| `shape.revolve_profile` | 回转带内外倒角的环形截面 | `bore_d/outer_d/width`；输出 `collar_base` |
| `feature.tapped_hole_cutter` | 生成一个径向孔的切削体 | `screw_d`、查表 pitch、`angle_deg`；输出 `hole_cutter` |
| `boolean.cut` | 从上一个实体中减去一个切削体 | `base`、`tool`；输出 `solid_candidate` |
| `result.single_solid` | 声明最终结果和后置检查目标 | `solid_candidate`；输出 `part` |

`shape.revolve_profile` 的 `profile_kind` 必须为 `chamfered_annulus`；倒角参数按源构造器的 `min(max(0.25, bore_d*0.012), wall*0.18, width*0.08)` 以注册公式表达。`feature.tapped_hole_cutter` 的 `thread_model` 为 `revolved_ring_approximation`，并记录 `helical_thread_supported: false`。`over=0.5 mm`、径向平移 `bore_r-0.5 mm`、轴向位置 `width/2` 和角度列表属于族扩展数据，不能被编译器悄悄改写。

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

参数规则和几何验证结果是两个不同对象：参数错误进入顶层 `errors` 且 `stage=schema/preflight`；构造后的实体计数、`isValid()`、体积、包围盒、面/边摘要进入 `validation_result` 且 `stage=post_geometry`；STEP 导出/回读进入 `stage=step_export/step_readback`。验证结果不得反写为参数来源或约束通过。

## 7. 错误协议

每个错误至少包含：`code`、`stage`、`severity`、`fields`、`node_ids`、`message`、`retryable`。错误阶段和稳定码如下：

| 阶段 | 代码前缀/示例 | 含义 |
|---|---|---|
| IR 解析 | `IR_INVALID_JSON`、`IR_VERSION_UNSUPPORTED`、`IR_UNKNOWN_NODE_TYPE`、`IR_REFERENCE_NOT_FOUND` | IR 文件本身不能解析或不符合 v0。 |
| Schema/前置规则 | CAD-003 原码 `MISSING_REQUIRED`、`CATALOG_CHOICE`、`CATALOG_MISMATCH`、`SECOND_SCREW_CONSTRAINT`、`WALL_THICKNESS_TOO_SMALL`、`WIDTH_SUPPORT_TOO_SMALL`、`OUTER_DIAMETER_NOT_GREATER`、`UNSUPPORTED_UNIT` | 参数缺失、单位、目录或规则失败；不调用构造器。 |
| 构造 | `CAD_BUILD_NODE_ERROR`、`CAD_BUILD_BOOLEAN_ERROR`、`CAD_BUILD_UNSUPPORTED_FEATURE` | 白名单节点执行或布尔操作失败。 |
| 实体/几何 | `GEOMETRY_INVALID`、`GEOMETRY_MULTI_SOLID`、`GEOMETRY_EMPTY`、`GEOMETRY_METRIC_OUT_OF_TOLERANCE` | 构造有结果但实体有效性、单实体或几何摘要不满足契约。 |
| STEP | `STEP_EXPORT_ERROR`、`STEP_READBACK_ERROR`、`STEP_READBACK_MULTI_SOLID`、`STEP_METRIC_MISMATCH` | STEP 写出或回读失败；不能用字节 hash 稳定性替代这些检查。 |

`fields` 指向参数或验证字段，`node_ids` 指向相关节点；不适用时使用空数组。错误码在 v0 内不得复用为另一语义。

## 8. JSON 序列化和兼容策略

规范 JSON 见 [`ir-v0.schema.json`](ir-v0.schema.json)。顶层 `status=accepted` 表示 IR 已通过 IR 结构检查和 CAD-003 前置规则；`status=rejected` 仍可序列化错误和部分输入，但不得有可执行节点。`errors` 和 `validation_result` 是互斥的阶段记录：前置拒绝使用 `errors`，后置失败使用 `validation_result`。

v0 读取策略：

- `ir_version` 不匹配、族 ID 不匹配、未知必需字段、未知节点/公式/引用一律拒绝；
- `ir_revision` 的 patch 更新可以增加 `extensions` 下的可忽略元数据，不能改变现有字段语义；minor 更新只能增加可选字段和白名单成员，并由适配器声明支持范围；
- major 变化必须使用 `typed-cad-ir.v1`，不得让 v0 读者猜测；
- `schema_version`、`source_commit`、`adapter_version` 都参与可复现记录，不能因“同一参数”而省略；
- 反序列化后应按 `parameter_id`、`ordinal` 和引用图重新检查唯一性与拓扑，而非只信任 JSON 顺序。

## 9. 可复现性边界

同一 IR、同一 source commit、同一 adapter、同一 CadQuery/OCP/操作系统和同一容差配置，目标是得到相同的参数解析、节点图、实体数、`isValid()`、量化体积/包围盒以及登记的面面积/边长摘要。DATA-003 只证明当前环境下这些几何/拓扑指标稳定；它没有证明任意 B-Rep 拓扑完全等价。

STEP 字节 SHA-256 **不稳定**，即使几何摘要相同也可能不同；v0 的重复性判定必须使用结构化几何摘要和明确容差，不能要求文件字节相同。CadQuery/OCP、STEP writer、平台或数值容差改变时，只能保证 IR 和参数/依赖层可复现，几何结果需重新验证。`source.snapshot_status=reproducibility_partial` 反映源码快照、外部图纸和生成资产许可/复现边界，不能被编译器改为 `complete`。

## 10. 第二族扩展边界和未决问题

公共包络只承诺版本、族标识、来源、参数来源、节点图、约束和错误协议。新族可以在 `family_data` 中声明自己的目录、节点参数、规则和验证摘要；它不能复用本族的 `wall_thickness`、`second_screw` 或线程规则，除非其 Schema 明确声明同一语义。跨族公共节点只有在 v1 冻结前完成兼容性审查后才能加入核心白名单。

未决问题交给 Codex 审查：

- 是否把 `screw_len` 明确标记为“目录/任务字段”并在所有后续适配器中禁止误作孔深；
- 面/边量化精度、体积/包围盒容差和摘要算法是否冻结为 CAD-006 契约；
- `revolved_ring_approximation` 是否在首期被接受为功能性螺纹近似，或需在构造器层明确降级状态；
- `family_data` 的 JSON Schema URI 和跨族公共节点注册表由谁维护；
- 生成 STEP/渲染图的许可证和可发布范围仍是 `license_scope_uncertain`；
- 是否将 `directory_id` 作为所有族的公共来源字段，而不是只在适配器元数据中保留。

## 11. 交接

```text
task=IR-001
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/...
verified=python3 -m json.tool ir-v0.schema.json；python3 -m json.tool examples/*.json；结构化示例检查（见 checkpoint.md）
ir_version=typed-cad-ir.v0
known_limits=仅 set_screw_shaft_collar；无 CadQuery/OCP 编译器、STEP 验证器、真实螺旋线程、第二族实现；STEP 字节 hash 不稳定
next=Codex 审查后交给 CAD-005/006
```
