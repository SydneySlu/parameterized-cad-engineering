# CAD-003：`set_screw_shaft_collar` Schema v0 与参数规则

状态：`review`（候选首族的 Schema 设计交给中枢审查；不表示首族范围已经由项目负责人冻结）

本目录定义“参数 JSON → 可检查字段与规则”的边界。实现位于
[`src/schema/set_screw_shaft_collar.py`](../../../src/schema/set_screw_shaft_collar.py)，只做纯参数解析、单位归一化、目录耦合和前置规则检查，不导入 CadQuery/OCP，也不构造或导出 CAD。

可供审查和下游读取的静态描述在 [`schema-v0.json`](schema-v0.json)；它由 `schema_descriptor()` 生成，规则执行仍以 Python 实现为准。

## 证据边界

规则来源是 DATA-003 固定 source commit `035f467142888edfd0bd7cd73906f9b155c8f43c` 中的
`designs/set_screw_shaft_collar/spec.py`，以及 DATA-003 的 `source-audit.md`、`run-log.md`：

- 15 个 `CATALOG_ROWS` 是离散目录行，`bore_d` 是目录选择器。
- `outer_d`、`screw_d`、`screw_len`、`width` 是所选目录行的派生值；显式提供时必须与该行完全一致。
- `second_screw` 由 GN 705 说明和 `check()` 规则确定：`1 iff bore_d > 70`。
- 壁厚和轴向支撑规则照录 `check()`：`(outer_d - bore_d)/2 > 0.65*screw_d`，以及 `width >= 1.45*screw_d`。

审计 manifest 仍是草案，不被本实现称为跨族生产 Schema。字段来源的“目录派生”和“规则派生”是审计证据支持的推导；没有为材料、表面处理、螺纹节距、倒角或外部图纸增加输入默认值。

## JSON 边界

规范形式使用 envelope：

```json
{
  "schema_version": "set_screw_shaft_collar.v0",
  "family_id": "set_screw_shaft_collar",
  "parameters": {
    "bore_d": {"value": 20, "unit": "mm"}
  }
}
```

实现也接受仅含参数的扁平对象，便于单元测试和后续适配器过渡。`bore_d` 是唯一必填字段；它是关键目录选择器，缺失时拒绝，不用默认尺寸掩盖缺失。其他五个字段缺失时按各自 `FieldSpec.missing_behavior` 派生：四个来自目录行，`second_screw` 来自阈值规则。显式提供的派生字段不会被静默覆盖，冲突返回 `CATALOG_MISMATCH` 或 `SECOND_SCREW_CONSTRAINT`。

长度字段的规范单位是 mm。裸数字按 mm 解释；也可使用 `{ "value": ..., "unit": "mm|cm|m|in" }`，归一化后再做目录匹配。`second_screw` 是无量纲整数，只接受 `0` 或 `1`。

成功结果包含 `normalized` 和 `provenance`；来源值为 `user_explicit`、`catalog_derived` 或 `rule_derived`。失败结果仍是可序列化对象，每条错误包含稳定 `code`、相关 `fields`、可解释 `message` 和 `stage="schema"`。

`validate_json()` 负责从 JSON 文本进入同一校验路径；`ValidationResult.to_json()` 与 `ValidationResult.from_json()` 可用于结果记录的序列化和反序列化。

## 字段和规则摘要

完整字段元数据由 `schema_descriptor()` 返回，包含名称、类型、单位、证据来源、必填性、缺失行为、允许范围/选项和派生关系。当前字段如下：

| 字段 | 输入/来源 | 单位 | 允许值摘要 | 缺失行为 |
|---|---|---|---|---|
| `bore_d` | 用户显式目录选择 | mm | `5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80` | 缺失拒绝 |
| `outer_d` | 目录行 `d2` | mm | 目录派生值 `10..110` | 按 `bore_d` 派生 |
| `width` | 目录行 `b js14` | mm | 目录派生值 `6..22` | 按 `bore_d` 派生 |
| `screw_d` | 目录行 `d3` 主径 | mm | `3, 4, 5, 6, 8, 10, 12` | 按 `bore_d` 派生 |
| `screw_len` | 目录行 `d3` 长度 | mm | `4, 5, 6, 8, 10, 12, 16, 20` | 按 `bore_d` 派生 |
| `second_screw` | GN 705 大规格说明/规则 | 无量纲整数 | `0` 或 `1` | 按 `bore_d > 70` 派生 |

Schema 层在未来构造前检查：字段类型/单位、未知字段、目录选择、目录耦合、第二螺钉阈值、`outer_d > bore_d`、壁厚严格大于 `0.65*screw_d`、宽度不小于 `1.45*screw_d`。这些检查必须先于 `part.build()`；DATA-003 已证明绕过 `check()` 时非法壁厚仍可能 build 成功并产生 3 solids。

## 明确留给后续验证器的内容

Schema 成功只表示参数边界通过，不表示几何成功。后续 CAD 内核/后置验证器仍需负责：

1. 构造后的实体有效性、单实体/solid 数、shell/face/topology 计数和体积/包围盒；尤其要拒绝 DATA-003 的 3-solids 结果。
2. STEP 导出与回读，以及几何级重复性摘要。STEP 字节 hash 不应直接作为重复性判定。
3. 真实径向攻丝/布尔切割是否移除预期体积。源注释记录 M3–M8 的环形螺纹布尔可能 no-op，Schema 无法判断。
4. 倒角、孔口、孔角度和其他 B-Rep 细节是否符合设计意图。
5. BenchCAD 代码/生成资产/第三方图纸的许可证与发布资格；这些不是参数规则。

本目录不定义 Typed CAD IR、CadQuery/OCP 构造器、STEP 读写、LLM Prompt、检索格式，也不声明对第二族可复用。
