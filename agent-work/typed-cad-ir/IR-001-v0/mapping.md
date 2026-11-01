# CAD-003 Schema → Typed CAD IR v0 映射

本文只定义只读适配，不实现构造器。输入是 CAD-003 的正式 envelope 或其已由 Schema 规则层解析的 `ValidationResult`；只有 `ok=true` 才能生成 `status=accepted` 的 IR。

## 1. 入口和拒绝点

1. 解析 JSON；失败写 `IR_INVALID_JSON`，不生成节点。
2. 校验 `schema_version`, `family_id` 和参数对象形状。未知字段、缺 `bore_d` 或单位错误沿用 CAD-003 错误码，阶段为 `schema`。
3. 以 `bore_d` 查目录行，补全四个目录字段；按 `bore_d > 70` 补全 `second_screw`。显式派生字段与目录行不一致时写 `CATALOG_MISMATCH`，不调用构造器。
4. 执行 `outer_d > bore_d`、壁厚和宽度规则。任何错误都生成 `status=rejected` 的错误记录，不生成可执行 `nodes`。
5. 只有全部通过时，按本表构造六个参数项、约束项和固定节点图。

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
| 2 / `n2.hole.primary` | `feature.tapped_hole_cutter` | `screw_d`、pitch lookup、`angle_deg=0`、`over=0.5 mm` | `hole_cutter_primary` | n1 |
| 3 / `n3.cut.primary` | `boolean.cut` | `base=collar_base`、`tool=hole_cutter_primary` | `solid_after_primary` | n1,n2 |
| 4 / `n4.hole.secondary` | `feature.tapped_hole_cutter` | `screw_d`、pitch lookup、`angle_deg=135`；仅 `second_screw=1` | `hole_cutter_secondary` | n3 |
| 5 / `n5.cut.secondary` | `boolean.cut` | `base=solid_after_primary`、`tool=hole_cutter_secondary`；仅 `second_screw=1` | `solid_after_secondary` | n3,n4 |
| 6 / `n6.result` | `result.single_solid` | `solid_after_primary` 或 `solid_after_secondary` | `part` | n3 或 n5 |

节点 4/5 始终可出现在固定 v0 图中，但 `enabled_if` 为 `second_screw == 1`。当值为 0 时，编译器必须把它们标记为 skipped，不能把它们改成另一个操作或改变后续节点 ID。`n6.result` 的 `input` 用同一条件表达式选择上游输出。

## 4. 约束映射

CAD-003 的四条参数/规则关系直接进入 `constraints`，保留 `source_ref` 和 `enforced_at=preflight`。`single_solid_target` 和 `step_roundtrip` 是新增的后置契约，不改变 Schema 的 `ok` 语义：

- `Schema ok=true`：仅表示可安全调用构造器；
- `post_geometry ok=true`：表示实体有效、数量和几何摘要满足 CAD-006 契约；
- `step_readback ok=true`：表示导出并回读的实体满足相同后置契约。

## 5. 版本和适配器规则

适配器必须把 CAD-003 的 `schema_version`、DATA-003 `source_commit` 和自己的 `adapter_version` 原样写入 `source`。更新目录值或规则时创建新的 Schema/adapter 版本，不能只更新 IR 文件中的数值。适配器不得把 `ValidationResult.errors` 清空后继续生成 IR，也不得从 `build()` 的“成功”推断参数规则通过。
