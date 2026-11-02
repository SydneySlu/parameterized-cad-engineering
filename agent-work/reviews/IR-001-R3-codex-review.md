# IR-001-R3 Codex 中枢审查记录

日期：2026-11-02
审查对象：本地提交 `fcb88b7`、`30845d4` 及其 IR-001-R3 文档交付
状态：`needs_revision`；暂不可作为 CAD-005/006 的稳定实施接口。

## 审查结论

R3 对公式/单位契约、示例和错误分层做了大量有价值的收敛，声明的 Schema、语义反例、CAD-003 测试、公式、placement 和螺纹探针均可复跑。但有两项接口阻塞问题：套环回转轴的坐标系解释错误；`build` 阶段失败无法通过当前 `validation_result` Schema 表达。此外，几何容差仍为 `pending_measurement`，首族仍等待负责人确认。修正并复审前，不应启动正式 CAD-005/006。

## 阻塞问题

### 1. 回转轴被误标为世界 Y，实际是世界 Z

R3 的 `shape.revolve_profile.properties.axis` 在 Schema 中固定为 `Y`。`ir-v0-spec.md` 还称 `axisStart=(0,0,0)` 和 `axisEnd=(0,1,0)` 是世界坐标，并把轮廓第二坐标及零件轴向称为世界 Y。

这与 CadQuery 2.3 的实际语义不符。`Workplane.revolve` 文档和实现明确说明 `axisStart`、`axisEnd` 相对当前 Workplane，并通过 Workplane 平面映射至世界坐标。对 `Workplane("XZ")`，局部基向量映射为：局部 X→世界 X、局部 Y→世界 Z、局部 Z→世界 -Y。因此传入局部 `axisEnd=(0,1,0)` 后，回转轴是世界 Z。

独立复核证据：

- 固定 BenchCAD 源码构造 `bore_d=20, outer_d=32, width=14` 后，OCP 包围盒为 `32.0000002 × 32.0000002 × 14.0 mm`，轴向高度落在 Z。
- 实测 `Workplane("XZ").plane.toWorldCoords((0,1,0)) == (0,0,1)`。
- 固定源码中的 cutter 从局部 +Z 绕世界 +Y 旋转 90° 后沿 +X，再在 Z=`width/2` 处定位并按世界 Z 旋转；这与 Z 轴向套环一致。

需要统一修正 Schema 的轴字段/语义、规范中的轴向及 profile 描述、mapping、示例说明和 review 结论。建议把“输入 Workplane 局部轴”与“最终世界轴”分开命名，例如同时明确 `axis_local=[0,1,0]`、`workplane=XZ`、`axis_world=Z`，避免再次混淆。placement 的几何变换探针结果本身通过，但不能抵消回转轴字段错误。

### 2. `build` 错误阶段无法序列化为 `validation_result`

错误 Schema 的 `stage` 枚举包含 `build`，错误分类表也列有 `CAD_BUILD_NODE_ERROR` 等构造失败码。但 `validation_result` 的成功/失败分支只允许 `post_geometry`、`step_export`、`step_readback`，不允许 `build`。与此同时，规范规定 accepted IR 不能带顶层 `errors`，而顶层 `errors` 只用于 rejected/preflight 路径。因此一个已接受 IR 在 CadQuery 构造阶段失败时，没有符合现有 Schema 的记录位置。

需明确构造失败的状态与持久化位置，并让规范、Schema、示例和测试保持一致。不能只把 `build` 加进顶层通用错误枚举，而不定义 accepted IR 下如何表示它。

## 非阻塞但仍是进入实现前置条件

- `geometry_tolerance=pending_measurement` 是诚实且正确的状态；候选数值阈值没有 DATA-003 原始数据支撑，不能冻结。需要按 R3 所列最小补测保存构造及 STEP 回读的未量化指标，再制定 CAD-006 比较策略。
- `family_scope=awaiting_owner_confirmation`。`set_screw_shaft_collar` 只能作为条件性单族契约，不能写成负责人已批准的项目范围。
- BenchCAD 源快照仍为 `reproducibility_partial`，许可证/生成资产发布范围仍未完全确认；R3 正确保留了这些限制。

## 独立复跑验证

- Draft 2020-12 Schema 自检及 5 个示例：通过。
- `/tmp/ir001r2_validate.py`：5 个示例通过；12 个反例被拒绝。
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`：17 项通过。
- `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`：通过；合法目录案例构造为 1 solid，第二螺钉规则非法案例被拒绝。
- `/tmp/ir001_r3_formula_test.py`：通过。
- `/tmp/ir001_r3_transform_probe.py`：通过其自身的局部 cutter 放置断言；此探针没有检查回转体轴字段，因此未发现上述轴向契约冲突。
- `/tmp/ir001_r3_thread_probe.py`：M6/M12 环形 cutter 均观察到体积减少，符合 R3 所述当前环形近似行为。
- `python3 -m json.tool` 与 `git diff --check HEAD^ HEAD`：通过。

## Git 状态与下一步

审查开始时工作区干净，`main` 相对 `origin/main` 超前两个提交：`fcb88b7`、`30845d4`。本次只新增本审查记录和工作日志条目，没有修改 IR-001-R3 交付文件或提交 Git commit。

下一步：由 IR-001 Agent 修正上述两个阻塞问题，补充针对回转轴坐标映射和 `build` 失败表示的回归验证；Codex 再独立复审。几何容差补测和首族确认仍需在正式 CAD-005/006 实现前处理。

## IR-001-R3-FIX 独立复审

复审对象：`fac9aaf`（契约修正）和 `a02a9c2`（checkpoint）。

### 复审结论

R3-FIX 的两项阻塞修正通过。IR-001 v0.2.0 可以作为**条件性单族接口**交给后续设计讨论和实现准备，但不能把 IR-001 标为项目最终 done，也不能据此宣称 CAD-005/006 已完成或几何容差已冻结。

### 独立验证

- `/tmp/ir001r1-jsonschema-venv/bin/python` 下 Draft 2020-12 Schema 自检、六个示例验证：通过。
- `/tmp/ir001_r3_fix_semantic.py`：六例语义验证通过，build/post_geometry/顶层 errors/阶段顺序等五类反例均按预期拒绝。
- `tests/typed_cad_ir/test_schema_contract.py`：3 项通过。
- `work/benchcad-output/venv/bin/python -m unittest tests.typed_cad_ir.test_axis_mapping -v`：2 项通过；直接确认 XZ 局部 Y 映射到世界 +Z，固定源码 bbox 的轴向宽度位于 Z。
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`：17 项通过。
- `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`：通过；合法案例 1 solid，规则非法案例在前置阶段拒绝。
- `/tmp/ir001_r3_transform_probe.py`：通过。
- 所有示例和 Schema 的 JSON 语法检查、`git diff --check`：通过。

系统 Python 没有 CadQuery；CAD 专项检查在项目 Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0 隔离环境运行。该环境限制已在 checkpoint 中如实记录。

### 接口判断

- 回转节点现在要求 `workplane=XZ`、`axis_local=[0,1,0]`、`axis=Z`，并在 Schema、规范、映射、示例和测试中保持一致。
- accepted IR 的 `validation_result.stage=build` 仅允许失败分支、`CAD_BUILD_*` 错误码和 `completed_stages=[]`；post_geometry、step_export、step_readback 的已完成阶段被逐级约束。
- `rejected` IR 仍只能使用顶层参数/规则错误，不能携带 validation_result。
- R3 中保留的旧世界 Y 表述已明确标记为历史结论，并由 v0.2.0 追加契约取代；不视为当前接口语义。

### 未决门槛

- `geometry_tolerance=pending_measurement`：仍缺少原始构造/回读面边序列和足够重复测量，不能冻结 CAD-006 数值阈值。
- `family_scope=awaiting_owner_confirmation`：`set_screw_shaft_collar` 仍只能视为条件性首族。
- `snapshot_status=reproducibility_partial`、许可证/生成资产范围不确定：保持原限制。

审查状态：`review`（R3-FIX 修正通过，项目级接口尚未最终冻结）。
