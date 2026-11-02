# IR v0 反序列化语义检查

Draft 2020-12 JSON Schema 负责结构、常量、枚举、参数类型/值类型和 `status` 互斥关系。以下检查依赖数组中元素之间的关系，必须由 IR 反序列化器在 Schema 通过后执行；Schema 通过不等于语义检查通过。

## 稳定错误码

| 检查 | 错误码 | 规则 |
|---|---|---|
| 参数 ID | `IR_DUPLICATE_PARAMETER_ID` | 六个首族参数各出现一次；accepted IR 恰好六项。 |
| 节点 ID | `IR_DUPLICATE_NODE_ID` | `node_id` 在 IR 内唯一。 |
| 输出 ID | `IR_DUPLICATE_OUTPUT_ID` | 所有节点的 `output_id` 全局唯一。 |
| 约束 ID | `IR_DUPLICATE_CONSTRAINT_ID` | `constraint_id` 在 IR 内唯一。 |
| 序号 | `IR_ORDINAL_NOT_CONTIGUOUS` | accepted 节点的 ordinal 是 `0..N-1`，按数组排序后仍与数组顺序一致。 |
| 依赖 | `IR_DEPENDENCY_NOT_PREVIOUS` | `depends_on` 只能指向存在且 ordinal 更小的节点。 |
| 依赖图 | `IR_DEPENDENCY_CYCLE` | 节点依赖图必须无环。 |
| 引用 | `IR_REFERENCE_NOT_FOUND` | parameter/output/constraint/catalog/formula 引用目标必须存在。 |
| 条件 | `IR_CONDITION_PARAMETER_NOT_FOUND`、`IR_CONDITION_TYPE_MISMATCH` | `enabled_if.parameter_id` 必须是已有参数，`equals` 的 JSON 类型必须与参数 `type` 一致；`second_screw` 只能比较整数 0 或 1。 |
| 公式 | `IR_UNREGISTERED_FORMULA` | `formula_id` 必须来自 v0 注册表；递归检查所有 args。 |
| 执行入口 | `IR_EXECUTION_STRING_FORBIDDEN` | 不允许把 expression、placement 或 properties 字符串当作代码；节点 inputs 只能是五种结构化表达式。 |
| 首族包络 | `IR_FAMILY_MISMATCH`、`IR_SCHEMA_VERSION_MISMATCH`、`IR_SNAPSHOT_STATUS_UNSUPPORTED` | v0 首族必须分别为 `set_screw_shaft_collar`、`family.set_screw_shaft_collar.v0`、`set_screw_shaft_collar.v0`、`reproducibility_partial`。 |
| 来源提交 | `IR_SOURCE_COMMIT_MISMATCH` | `source.source_commit` 必须是 `035f467142888edfd0bd7cd73906f9b155c8f43c`；其他 commit 不能伪装为同一 CAD-003 数据契约。 |
| 节点输入 | `IR_NODE_INPUT_MISSING`、`IR_NODE_INPUT_KIND_MISMATCH` | 每种 `node_type` 必须满足 Schema 登记的固定输入名和 expression kind；核心输入不能由 `family_extension` 替代。 |
| 节点输出 | `IR_NODE_OUTPUT_CONTRACT_MISMATCH` | 输出 ID/kind 必须与 node type 契约一致，并且 output ID 全局唯一。 |
| 节点属性 | `IR_NODE_PROPERTIES_CONTRACT_MISMATCH` | `properties` 必须满足对应 node type 的登记常量和结构；不得依赖任意扩展字段改变核心语义。 |
| 后置结果 | `IR_VALIDATION_RESULT_ERRORS_INCONSISTENT`、`IR_VALIDATION_STAGE_MISMATCH`、`IR_VALIDATION_STAGE_ORDER_INVALID` | `ok=true` 必须 errors 为空，`ok=false` 必须至少一个 error；每个 error.stage 必须等于 result.stage；`completed_stages` 必须与前置成功阶段序列完全相等。 |
| 回转坐标 | `IR_REVOLVE_AXIS_CONTRACT_MISMATCH` | `shape.revolve_profile` 必须为 `workplane=XZ, axis_local=[0,1,0], axis=Z`；`axis` 表示世界轴。 |
| 参数顺序 | `IR_PARAMETER_ORDER_MISMATCH` | accepted v0 参数数组固定按字典序：`bore_d, outer_d, screw_d, screw_len, second_screw, width`。 |
| 族规则 | `IR_SECOND_SCREW_CONSTRAINT` | `second_screw=1` 只允许 `bore_d > 70`；首族结构检查应在构造器前拒绝冲突输入。 |

## 最小算法

1. 先用 `ir-v0.schema.json` Draft 2020-12 校验；Schema 失败不得进入构造器。
2. 收集参数、节点、输出和约束 ID，按表中错误码检查唯一性；accepted 参数顺序必须是 `bore_d, outer_d, screw_d, screw_len, second_screw, width`。
3. 检查 `ordinal == range(len(nodes))`，再检查每个 dependency 的目标存在、目标 ordinal 更小；对图运行 DFS，发现回边即 `IR_DEPENDENCY_CYCLE`。
4. 按 `node_type` 检查固定 inputs、outputs 和 properties 契约；缺字段、kind 不匹配、输出不匹配或属性不匹配分别返回 `IR_NODE_INPUT_MISSING`、`IR_NODE_INPUT_KIND_MISMATCH`、`IR_NODE_OUTPUT_CONTRACT_MISMATCH`、`IR_NODE_PROPERTIES_CONTRACT_MISMATCH`。
5. 递归遍历每个 node input 和 `enabled_if`：检查 parameter/output 引用目标、lookup/formula 注册表和单位；不解析自由字符串。`second_screw=1` 时检查 `bore_d > 70`。
6. 检查 accepted 六参数的名称、类型、单位、`second_screw` 0/1、首族常量、固定 source commit 和 `snapshot_status`；rejected 只允许错误记录和空节点，不允许 `validation_result`。
7. 检查 `shape.revolve_profile.properties` 的 `workplane=XZ, axis_local=[0,1,0], axis=Z`。CadQuery 的 revolve 轴端点按 Workplane 局部坐标解释；XZ 平面局部 y 映射到世界 +Z，因此 profile 的宽度沿世界 Z。
8. 若存在 `validation_result`，检查 `ok` 与 errors 数量一致、每个 error.stage 等于 result.stage，并检查阶段顺序。合法序列为 `build: completed_stages=[]`、`post_geometry: [build]`、`step_export: [build, post_geometry]`、`step_readback: [build, post_geometry, step_export]`；每个已列阶段都必须实际成功。`build` 失败只允许出现在 accepted IR 的 validation_result，不能放在顶层 `errors` 或伪装成 `post_geometry`；rejected IR 仍不带 validation_result。后续阶段只有在前一阶段成功后才能启动。Schema 约束阶段列表，语义适配器检查其与实际执行事件一致。

## 本轮反例结果

以下反例由临时 Python 检查脚本构造，不写入生产代码或仓库测试：

| 反例 | 预期结果 |
|---|---|
| accepted 同时添加顶层 `errors` | Draft 2020-12 拒绝（状态条件的 `not.required`）。 |
| rejected 同时添加 `validation_result` | Draft 2020-12 拒绝。 |
| 复制 `bore_d` 参数、节点 ID、输出 ID | Schema 对参数类型仍可通过时，语义检查分别返回 `IR_DUPLICATE_PARAMETER_ID`、`IR_DUPLICATE_NODE_ID`、`IR_DUPLICATE_OUTPUT_ID`。 |
| 删除 ordinal 1 或让依赖指向未来节点 | 语义检查返回 `IR_ORDINAL_NOT_CONTIGUOUS` 或 `IR_DEPENDENCY_NOT_PREVIOUS`。 |
| 公式改为 `eval` 或 `formula_id=python_eval` | Schema/语义检查返回 `IR_UNREGISTERED_FORMULA` 或 `IR_EXECUTION_STRING_FORBIDDEN`。 |
| `snapshot_status=reproducible` | Schema 拒绝；若未来 Schema 为兼容枚举，语义检查必须返回 `IR_SNAPSHOT_STATUS_UNSUPPORTED`。 |
| `source_commit` 改为其他 40 位哈希 | Schema 拒绝；若未来保留通用哈希形状，语义检查返回 `IR_SOURCE_COMMIT_MISMATCH`。 |
| 删除 `feature.tapped_hole_cutter.thread_d` | Schema 拒绝或语义检查返回 `IR_NODE_INPUT_MISSING`。 |
| 删除 `boolean.cut.base`/`tool` | Schema 拒绝或语义检查返回 `IR_NODE_INPUT_MISSING`。 |
| 删除 `result.single_solid.select_if_one` | Schema 拒绝或语义检查返回 `IR_NODE_PROPERTIES_CONTRACT_MISMATCH`。 |
| `validation_result.ok=true` 但 errors 非空，或 `ok=false` 但 errors 为空 | Schema 拒绝或返回 `IR_VALIDATION_RESULT_ERRORS_INCONSISTENT`。 |
| validation error.stage 与 result.stage 不同 | Schema 拒绝或返回 `IR_VALIDATION_STAGE_MISMATCH`。 |
| build failure 使用 `post_geometry` 标签、写到顶层参数 `errors`，或声称 build 已完成 | Schema 拒绝或返回 `IR_VALIDATION_STAGE_ORDER_INVALID`；构造错误码属于 `CAD_BUILD_*`，不能用 `GEOMETRY_*`。 |
| `step_export` 缺少成功的 build/post_geometry，或 `step_readback` 缺少成功的 step_export | Schema 拒绝或返回 `IR_VALIDATION_STAGE_ORDER_INVALID`；不能从导出或回读状态推断前置阶段成功。 |
| revolve `axis=Y`、workplane 缺失/不是 XZ，或 axis_local 不是 `[0,1,0]` | Schema 拒绝或返回 `IR_REVOLVE_AXIS_CONTRACT_MISMATCH`；局部轴和世界轴必须分开表达。 |
| accepted 参数数组乱序 | Schema 拒绝或返回 `IR_PARAMETER_ORDER_MISMATCH`。 |
| `second_screw=1` 且 `bore_d<=70` | Schema 可检查类型，语义检查返回 `IR_SECOND_SCREW_CONSTRAINT`。 |

`examples/build-failure.json` 展示 Schema 合法的 accepted build 失败：错误为 `CAD_BUILD_NODE_ERROR`、stage 为 build、无已完成阶段。`examples/validation-failure.json` 独立保留 post_geometry 的 `GEOMETRY_MULTI_SOLID`，并声明 build 已成功；二者不可互相改标。其他四个原示例继续覆盖正常 accepted 和前置 rejected 路径。

这些检查不证明 CadQuery/OCP 结果有效，也不证明 STEP 字节哈希稳定；它们只保证 IR 输入图可安全、确定地交给白名单编译器。

## 节点契约责任边界

JSON Schema 负责检查每种 `node_type` 的字段存在性、固定输入名、`expression` 结构、输出 ID/kind 和登记 properties 形状。反序列化语义检查负责确认节点输出引用真实存在、`base_ref`/`tool_ref` 与对应 output ID 一致、主孔/第二孔的 `enabled_if` 与 `second_screw` 条件匹配，以及五种节点的依赖顺序。任何一项失败都必须在 CAD-005 前返回上述稳定 `IR_NODE_*` 错误；不能由编译器隐式补字段。


## R3 公式类型与 placement 语义

递归公式检查除白名单外，必须检查确切 args 名/数量与结果单位。首期单位代数仅包含 `mm`、`deg`、`1`；单位相加减/min/max 必须相同，乘法限长度与标量或两个无量纲值。拒绝长度加无量纲、长度乘长度及任何面积/体积中间量。线程 `thread_turn_count` 要与 `max(1,int((z1-z0)/pitch))` 的向零截断及有效几何域 `z1>=z0,pitch>0` 一致。

placement 校验必须逐项匹配 `placement.transforms` 的三操作签名，并按列向量左乘；不允许缺中心/坐标系/顺序后由实现自行补猜。局部 +Z cutter 绕世界 +Y 旋转 90° 后指向世界 +X，平移 `(radial_offset,0,width/2)`，再绕世界 +Z 按 `angle_deg` 旋转。合法第二孔 135° 世界起点应在 X<0,Y>0 象限；零角在 +X。`screw_len` 不作为孔深。properties/placement 中任何字符串只作枚举或引用字段，永不解释为表达式/代码。

几何后置检查对计数和值缺失、NaN/Inf、空几何与多 solid 必须稳定拒绝。preflight 参数错误留在顶层 `errors`；build/post_geometry/step_export/step_readback 失败只放 accepted IR 的 `validation_result.errors`，stage 必须和 result 相同且 completed_stages 精确证明先前成功阶段。DATA-003 仅记录 6 位摘要与 roundtrip 体积误差 0.013–0.034 mm³，故几何比较数值容差标记 `pending_measurement`，不可按候选值声称完成冻结。
