# CAD-005/006 checkpoint （R1）

日期：2026-11-01  
状态：`in_progress` 阶段 1 完成（交接检查），阶段 2 启动（编译器架构）  
完成比例：约 20%（前期准备和交接），编译器框架搭建中

## 已完成工作

### 1. 三层交接检查

✅ **第一层：交接 Agent 自检**
- DATA-003 checkpoint 记录完整：来源审计、环境、smoke 结果、重复性指标
- CAD-003 checkpoint 记录完整：17 个测试 pass、规则实现完整
- IR-001 checkpoint 记录完整：Schema 验证通过、5 个示例通过语义检查

✅ **第二层：续任 Agent 定向复核**
- 核心命令复现：spec.check() 和 part.build() 均可调用
- 4 个测试案例均通过预期行为
  - legal_catalog_row: check PASS, build OK (1 solid)
  - legal_hard_boundary: check PASS, build OK (1 solid, second_screw=1)
  - invalid_constraint: 被 spec.check() 正确拒绝
  - invalid_geometry: 被 spec.check() 正确拒绝
- 输入输出接口与 IR-001 一致
- 已知限制已确认并保留

✅ **第三层：等待中枢审查**
- 交接记录已保存：`handoff_successor_check.md`
- 环境验证脚本已保存：`test_handoff.py`

### 2. 前置条件验证

✅ **环境**
- CadQuery 2.3.0 + OCP 7.9.3.0 + Python 3.10
- 所有声明依赖均可导入
- BenchCAD 源快照（`benchcad-2-035f467-raw`）存在且完整

✅ **接口完整性**
- CAD-003 参数规则完整（6 字段，bore_d 必填）
- 约束集合冻结（5 项前置规则）
- 构造器单一入口（part.build(**params)）
- 验证 API（spec.check() 返回 error 列表）

✅ **IR v0 结构理解**
- 节点类型 5 个：catalog.resolve, shape.revolve_profile, feature.tapped_hole_cutter, boolean.cut, result.single_solid
- 表达式类型 5 种：parameter_ref, node_output_ref, literal, lookup, formula
- 公式集合 11 个：half, multiply, add, subtract, collar_chamfer, thread_minor_radius, thread_countersink_radius, thread_turn_count, half_difference, min, max
- 错误阶段 5 个：IR_parse, schema/preflight, build, post_geometry, step_export/readback
- 验证指标 10 个：solid_count, shell_count, face_count, edge_count, vertex_count, is_valid, volume_mm3, bbox_mm, face_area_signature, edge_length_signature

### 3. 架构决策

✅ **模块化设计**
- `src/cad_compilation/`：主编译器模块
  - `compiler.py`：IRv0Compiler 主类
  - `result.py`：CompilationResult、ValidationResult 数据结构
  - `semantic.py`：IR 语义检查器
  - `geometry.py`：几何/STEP 验证器
  - `formulas.py`：公式注册表和求值
  - `lookups.py`：查表注册表（ISO 261、GN 705 catalog）
  - `errors.py`：错误码和错误上下文

✅ **数据流**
```
IR JSON (accepted status)
  ↓ parse
IR object (with parameter values)
  ↓ semantic check
Validated IR + parameters + constraints
  ↓ compile
CadQuery nodes + intermediate results
  ↓ execute (topological order)
Final Solid
  ↓ validate_geometry
Solid + metrics + structural signature
  ↓ export_step
STEP file
  ↓ validate_step (readback + compare metrics)
Validation result (pass/fail + metrics diff)
```

✅ **错误处理策略**
- 参数规则失败 → 返回 CompilationResult(success=False, stage='preflight', errors=[...])
- 构造失败 → stage='build'，保留错误节点信息
- 几何失败 → stage='post_geometry'，记录实际指标与期望的差异
- STEP 失败 → stage='step_export' 或 'step_readback'

## 正在进行

### 1. 编译器框架搭建（第 1 周）

```
[██░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 10%

待实现：
- IR JSON schema 验证
- 语义检查器（参数顺序、唯一性、依赖图）
- 表达式求值（嵌套公式、参数引用）
- CadQuery 操作映射
  - catalog.resolve → 参数查表
  - shape.revolve_profile → CadQuery 回转
  - feature.tapped_hole_cutter → CadQuery 孔切削体
  - boolean.cut → CadQuery 布尔差
  - result.single_solid → solid 选择和验证
- 几何验证器（实体计数、有效性、STEP 往返）
```

### 2. 测试用例准备

- legal_catalog_row（bore_d=20）→ IR JSON
- legal_hard_boundary（bore_d=80, second_screw=1）→ IR JSON
- invalid_constraint（second_screw 违反）→ 拒绝
- invalid_geometry（outer_d < bore_d）→ 拒绝

## 关键发现和约束

### 1. 验证流程必须分层

❌ **不能做的事**（DATA-003 已证明）：
- 只调用 build()，不检查约束
- 只判断 STEP 是否导出成功
- 用字节 hash 作为重复性唯一标准
- 把 isValid() 单独当作合法性判定

✅ **必须做的事**：
1. preflight：约束检查（外_d > bore_d, 壁厚, 宽度, 二螺钉阈值）
2. build：CadQuery 构造
3. post_geometry：实体数量（预期 1）、isValid()、几何摘要
4. step_export/readback：导出、回读、摘要对比

### 2. 多实体（3-solids）风险

DATA-003 发现：当 outer_d < bore_d 时，即使约束被 check() 拒绝，若直接调用 build()：
- 构造仍成功（不抛错）
- 产生 3 个 solids（非法结果）
- STEP 导出成功（不抛错）
- STEP 回读成功（拓扑仍为 3 solids）

**结论**：STEP 导出/回读成功 ≠ 参数/几何合法。CAD-006 验证器必须检查 solid_count==1。

### 3. STEP 不稳定

DATA-003-R1 数据：
- 同参数两次运行，几何摘要完全相同
- STEP 文件字节 SHA-256 完全不同
- 原因未追溯（可能是 STEP writer、平台、数值容差）

**结论**：可记录 STEP 字节 hash 作参考，但不能用于重复性判定。使用结构化几何摘要（面积排序、边长排序）。

### 4. 螺纹模型限制

IR-001 规范：`thread_model=revolved_ring_approximation`，不声称真实螺旋。  
BenchCAD 源注释：M3–M8 螺纹可能 no-op。

**结论**：
- IR 编译器不能生成真实螺旋扫描
- CAD-006 应检查孔实际移除体积是否符合预期
- 不能声称真实螺纹功能

## 风险和决策点

### 1. 公式参数单位

IR-001 spec 中公式如 `half(x)`、`add(x, y)` 等没有显式标注参数单位。

**决策待确认**（CAD-005 中等风险项）：
- 是否从参数类型推导单位？（例如 half(bore_d) → bore_d 是 mm 所以返回 mm）
- add(wall, multiply(over, 2)) 中 over 是 0.5 mm，literal(2) 是无量纲，multiply 返回 mm 还是继续无量纲？
- 是否要求所有公式参数显式标注单位，或允许隐式推导？

**当前假设**（待中枢确认）：
- 数值参数保留其原始单位（mm 或 1）
- 公式返回单位取决于操作（multiply 的两个参数单位相乘，divide 相除）
- CAD-005 可以临时硬编码单位推导，后续由中枢冻结为 spec

### 2. 回转轴定义

IR 中 `properties.axis="Y"` 和 `revolve_degrees=360`。

**假设**（待确认）：
- Y 轴是环中心轴（旋转轴）
- 轮廓在 XZ 平面或 YZ 平面绘制？
- 倒角方向（内侧还是外侧）？

**当前计划**：参考 BenchCAD 源代码 `part.py` 的实际 CadQuery 调用，直接复用其几何逻辑。

### 3. 置放（placement）模型

IR 中 tapped_hole_cutter 节点包含结构化 placement：
```json
"placement": {
  "cutter_local_axis": "Z",
  "initial_rotation": {"axis": "Y", "degrees": 90},
  "translation": {...},
  "final_rotation": {"axis": "Z", "angle_ref": "angle_deg"}
}
```

**假设**：
- 孔切削体（cutter）在本地坐标系中沿 Z 轴
- 先绕 Y 轴旋转 90°（使其沿 X）
- 按 translation 平移（radial_offset, axial）
- 最后绕 Z 轴旋转 angle_deg（0° 主孔，135° 副孔）

**当前计划**：直接按规范实现，若有偏差由中枢反馈。

## 已知限制

❌ **不涉及**（首期边界外）：
- 第二族支持（结构预留，不实现）
- LLM 代码生成（IR 白名单限制，不执行自由代码）
- 并发或缓存优化
- 图形界面或渲染
- 许可证检查（sourcing decision 由中枢决）

✓ **已明确范围**：
- 仅 set_screw_shaft_collar
- 确定性重复性指标（几何摘要、实体计数）
- 结构化错误报告
- 4 类测试案例和运行日志

## 下一步（第 2 周）

### 实现计划

1. **IR 解析和验证** （4 h）
   - JSON Schema 验证（使用 jsonschema 包或手动检查）
   - 语义检查器（参数顺序、唯一性、拓扑）
   - 错误上下文建立

2. **公式和查表求值** （2 h）
   - 公式注册表（11 个公式）
   - ISO 261 粗牙查表
   - GN 705 目录查表（从 CAD-003 复用或参考）

3. **CadQuery 操作映射** （4 h）
   - shape.revolve_profile → 倒角环形回转
   - feature.tapped_hole_cutter → 孔切削体（考虑 M3-M8 no-op）
   - boolean.cut → 差集
   - result.single_solid → solid 选择

4. **几何验证** （2 h）
   - 实体计数、有效性检查
   - 体积、包围盒、面积/边长摘要
   - 量化精度和签名算法

5. **STEP 往返验证** （1 h）
   - 导出、回读
   - 摘要对比（允许容差）
   - 差异报告

6. **测试和运行日志** （2 h）
   - 4 类测试用例
   - 版本化日志（软件版本、IR 版本、参数、结果）
   - 结构化 manifest

### 交接准备

- 完整源代码和单元测试（tests/ 下）
- 可运行的演示脚本（4 类案例）
- 运行日志和 manifest（agent-work/cad-validation/CAD-005-006/run-log.md）
- 自检清单（handoff_self_check）

## 交接格式（最终）

```text
task=CAD-005/006-R1
status=review
changed=src/cad_compilation/...; tests/cad_compilation/...; agent-work/cad-validation/CAD-005-006/...
verified=<所有测试命令和结果>
ir_version=typed-cad-ir.v0
geometry_repeatability=<4 类案例各运行两次，指标稳定性报告>
known_limits=<未涉及的族、环境、许可证等>
next=中枢审查后交给 DATA-004 或集成评测
```
