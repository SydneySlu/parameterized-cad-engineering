# CAD-003 Schema → Typed CAD IR v0 映射

本文只定义只读适配，不实现构造器。输入是 CAD-003 的正式 envelope 或其已由 Schema 规则层解析的 `ValidationResult`；只有 `ok=true` 才能生成 `status=accepted` 的 IR。当前适配器只写 `source.snapshot_status=reproducibility_partial`；不得把当前首族写成 `reproducible`。

## 1. 入口和拒绝点

1. 解析 JSON；失败写 `IR_INVALID_JSON`，不生成节点。
2. 校验 `schema_version`, `family_id` 和参数对象形状。未知字段、缺 `bore_d` 或单位错误沿用 CAD-003 错误码，阶段为 `schema`。
3. 以 `bore_d` 查目录行，补全四个目录字段；按 `bore_d > 70` 补全 `second_screw`。显式派生字段与目录行不一致时写 `CATALOG_MISMATCH`，不调用构造器。
4. 执行 `outer_d > bore_d`、壁厚和宽度规则。任何错误都生成 `status=rejected` 的错误记录，不生成可执行 `nodes`，且不写 `validation_result`。
5. 只有全部通过时，按本表构造六个参数项、约束项和固定节点图。

`status=accepted` 表示 IR 和前置规则通过，不保证 CAD 成功；它不得带顶层 `errors`，但可在构造/后置阶段追加 `validation_result`。若几何或 STEP 验证失败，保持 `status=accepted`、写 `validation_result.ok=false`，不得把后置失败转成顶层 `errors`。

## 2. 参数映射

| CAD-003 字段 | IR `parameter_id` | IR 类型/单位 | IR 来源 | `source_ref` |
|---|---|---|---|---|
| `bore_d` | `bore_d` | number/mm | `user_explicit` | `CAD-003.field:bore_d` |
| `outer_d` | `outer_d` | number/mm | 显式则 `user_explicit`，缺失则 `catalog_derived` | `CAD-003.field:outer_d` 或 `GN705.catalog_row:bore_d={bore}` |
| `width` | `width` | number/mm | 显式则 `user_explicit`，缺失则 `catalog_derived` | 同上 |
| `screw_d` | `screw_d` | number/mm | 显式则 `user_explicit`，缺失则 `catalog_derived` | 同上 |
| `screw_len` | `screw_len` | number/mm | 显式则 `user_explicit`，缺失则 `catalog_derived` | 同上 |
| `second_screw` | `second_screw` | integer/1 | 显式则 `user_explicit`，缺失则 `rule_derived` | `CAD-003.rule:second_screw_threshold` |

显式输入的原始 `{value, unit}` 写入参数项的 `input`；`value` 永远是归一化 mm。裸数字的 `input.unit` 记录为 `mm`，因为 CAD-003 将裸数字解释为规范单位。派生值没有伪造的用户输入。

## 3. 节点映射

| 顺序/ID | `node_type` | 输入绑定 | 输出 | 依赖 |
|---:|---|---|---|---|
| 0 / `n0.catalog.resolve` | `catalog.resolve` | `bore_d`、目录表 `gn705.gn705_metric_v0` | `resolved_parameters` | — |
| 1 / `n1.collar.revolve` | `shape.revolve_profile` | `bore_d`、`outer_d`、`width`，`collar_chamfer` 公式 | `collar_base` | n0 |
| 2 / `n2.hole.primary` | `feature.tapped_hole_cutter` | `screw_d`、pitch lookup、`angle_deg=0`、`over=0.5 mm`、`wall`、`hole_len`、`z_in`、`z_out`、`radial_offset`、`axial` | `hole_cutter_primary` | n1 |
| 3 / `n3.cut.primary` | `boolean.cut` | `base=collar_base`、`tool=hole_cutter_primary` | `solid_after_primary` | n1,n2 |
| 4 / `n4.hole.secondary` | `feature.tapped_hole_cutter` | 与主孔完全相同，`angle_deg=135`；仅 `second_screw=1` | `hole_cutter_secondary` | n3 |
| 5 / `n5.cut.secondary` | `boolean.cut` | `base=solid_after_primary`、`tool=hole_cutter_secondary`；仅 `second_screw=1` | `solid_after_secondary` | n3,n4 |
| 6 / `n6.result` | `result.single_solid` | `solid_after_primary` 或 `solid_after_secondary` | `part` | n3 或 n5 |

节点 4/5 始终可出现在固定 v0 图中，但 `enabled_if` 为 `second_screw == 1`。当值为 0 时，编译器必须把它们标记为 skipped，不能把它们改成另一个操作或改变后续节点 ID。`n6.result` 的 `input` 用同一条件表达式选择上游输出。

两个孔节点的结构化输入必须按下式生成，不能从字符串或 `screw_len` 猜测：

```text
wall          = half_difference(outer_d, bore_d)
over          = literal(0.5, mm)
hole_len      = add(wall, multiply(over, literal(2, 1)))
z_in          = over
z_out         = add(over, wall)
radial_offset = subtract(half(bore_d), literal(0.5, mm))
axial         = multiply(width, literal(0.5, 1))
```

两节点均须带 `thread_model=revolved_ring_approximation`、`helical_thread_supported=false` 和登记的 placement 元数据：局部 +Z cutter 绕 Y 轴 90° 到 +X，按 `radial_offset`/`axial` 平移，再绕 Z 轴按 `angle_deg` 旋转。CAD-005 必须注册上述公式的参数名、单位传播和容差；placement 元数据只用于白名单解释，不得执行其中的自由字符串。

## 4. 约束映射

CAD-003 的四条参数/规则关系直接进入 `constraints`，保留 `source_ref` 和 `enforced_at=preflight`。`single_solid_target` 和 `step_roundtrip` 是新增的后置契约，不改变 Schema 的 `ok` 语义：

- `Schema ok=true`：仅表示可安全调用构造器；
- `post_geometry ok=true`：表示实体有效、数量和几何摘要满足 CAD-006 契约；
- `step_readback ok=true`：表示导出并回读的实体满足相同后置契约。

`constraint.expression` 是审计/展示文本；适配器和验证器必须按登记的 `constraint_id` 使用白名单解释器。不得对 expression、placement 或 node properties 调用 `eval`/`exec`。节点 inputs 只能使用 `parameter_ref`、`node_output_ref`、`literal`、`lookup` 和登记的 `formula`。

## 5. 版本和适配器规则

适配器必须把 CAD-003 的 `schema_version`、DATA-003 `source_commit` 和自己的 `adapter_version` 原样写入 `source`。更新目录值或规则时创建新的 Schema/adapter 版本，不能只更新 IR 文件中的数值。适配器不得把 `ValidationResult.errors` 清空后继续生成 IR，也不得从 `build()` 的“成功”推断参数规则通过。

JSON Schema 未覆盖的唯一性、拓扑和引用检查必须由反序列化语义检查完成，使用 [`semantic-validation.md`](semantic-validation.md) 中的稳定错误码：参数/节点/输出/约束 ID 唯一，ordinal 连续，依赖只指向更早节点且无环，所有引用存在，`enabled_if` 参数和值类型匹配，首族固定版本/族/快照状态一致，公式和节点类型在白名单中。
