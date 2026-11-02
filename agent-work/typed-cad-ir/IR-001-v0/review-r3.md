# IR-001-R3 Typed CAD IR v0 最终契约审查

日期：2026-11-02
状态：`review`；仅提供当前单族条件下的契约冻结建议。
`family_scope=awaiting_owner_confirmation`：`docs/PROJECT_STATUS.md` 明确首族尚未由负责人冻结，DECISIONS 中无正式接纳决议。该事实阻止项目整体最终冻结，不阻止本轮审查单族条件契约。

## 结论摘要

| 契约 | 建议状态 | 说明 |
|---|---|---|
| `formula_units` | `frozen` | 固定公式 ID、参数名/形状、有限数要求、单位传播和几何定义。Schema 示例同步；独立纯 Python 测试通过。 |
| `coordinate_placement` | `frozen` | 固定 XZ 工作平面、Y 回转轴和 `Rz*T*Ry` 列向量变换；placement 已改为 Schema 可检查的有序结构，OCP 探针通过。 |
| `geometry_tolerance` | `pending_measurement` | 离散硬门槛冻结；数值容差给出候选但 DATA-003 误差范围和缺失原始摘要不足以冻结，CAD-005/006 不得据此声称 ready。 |
| `failure_taxonomy` | `frozen` | 定义 parse/schema/preflight/build/post_geometry/step_export/step_readback 错误族、重试、定位、前后置分层；任何 STEP 写出成功均不代表验证成功。 |

## 固定来源及交接复核

固定 BenchCAD 来源为 `035f467142888edfd0bd7cd73906f9b155c8f43c`。API 快照目录自己的 Git HEAD 为导入提交 `b33b469f357f6bd8064c879b8c4aec7e1c4a7807`，不能当作来源 commit；DATA-003 的 `SNAPSHOT-MANIFEST.json` 记录上游 commit、217/217 blob 下载。R3 用 `git hash-object` 核对快照 `part.py`、`spec.py`、`pyproject.toml`，三者都与该上游 manifest blob SHA 一致。`uv.lock` 不在 API snapshot 目录，不能声称核验其文件哈希；环境记录和完整 raw 快照 manifest 保留其证据。快照状态继续是 `reproducibility_partial`。

依 handoff protocol 完成前序复核：IR/CAD-003 文件和五例存在、均为合法 JSON；Draft 2020-12 `check_schema` + 五例运行通过；`/tmp/ir001r2_validate.py` 五例语义检查通过且 12 个反例拒绝；CAD-003 17 项测试通过；项目 venv 的仓库内 `tests/cad_compilation/test_handoff.py` 通过，合法目录案例 build 为 1 solid，错误第二螺钉规则拒绝。系统 Python 缺 CadQuery，故交接测试只在记录的隔离 venv 通过，不将系统 Python 结果写成通过。

## A. 声明式公式和量纲

证据：IR 五例中的实际公式为 `half_difference`, `half`, `multiply`, `add`, `subtract`, `collar_chamfer`；线程公式注册为 `thread_minor_radius`, `thread_countersink_radius`, `thread_turn_count`；`min/max` 注册为可变长、同单位聚合。固定源 `part.py` 的倒角公式是 `min(max(0.25,bore_d*0.012),wall*0.18,width*0.08)`；`_tapped_hole` 给出精确螺纹公式和 `max(1,int((z1-z0)/pitch))`。

决策：`mm/deg/1` 是唯一基础单位；加减/min/max 同单位，half 保单位，乘法只允许长度×标量或无量纲×无量纲；不生成复合单位。公式参数严格用规范表命名并按键读取，`min/max` 使用 `values` 数组且至少两项。所有数值有限。thread-turn-count 保持 Python 向零截断行为，再与 1 取 max；pitch 必须正且几何域 `z1>=z0`。M3/M4/M5/M6/M8/M10/M12 coarse pitch 分别为 0.5/0.7/0.8/1/1.25/1.5/1.75 mm。零、负壁厚/宽度、非正小径、单位不匹配、非法长度乘法、NaN/Inf 均拒绝。

可复现数值脚本 `/tmp/ir001_r3_formula_test.py`：代表性长度/标量合法算术、M6/M12 螺纹公式、second_screw 共用表达式及 7 类无效/边界拒绝通过。该脚本是纯 Python，无 CAD 导入和副作用。

## B. 坐标和 placement

证据：固定源 `Workplane("XZ")`、8 点 profile、`revolve(360,(0,0,0),(0,1,0))` 与 cutter 的 `rotate Y 90 → translate(bore_r-0.5,0,width/2) → rotate Z angle`。`shape.revolve_profile` 明确映射 profile `(radius,Y axial)`，实体长轴为世界 Y。cutter 局部 +Z 经初转到 +X，再世界平移和绕世界原点 Z 转角。angle 0 在 +X；135 在 (-X,+Y) 象限；`screw_len` 永不作孔深。

原 schema placement 仅描述 axis/degrees/ref，缺坐标系、中心和运算次序。R3 改成三步、闭合枚举结构：局部原点 `Ry(90°)`，world 平移 `(radial_offset,0,axial)`，绕世界原点 `Rz(angle_deg)`；列向量左乘 `Rz*T*Ry`。`ir-v0.schema.json` 和三个 accepted 示例同步；不执行 placement 文本。

`/tmp/ir001_r3_transform_probe.py` 在固定 OCP 环境验证局部 +Z 方向及 angle 0/135 的位置；两合法目录案例 bbox 与 DATA-003 记录 `(32,32,14)`、`(110,110,22)` 对应。第二孔目录案例只是同一 bore_d=80 hard boundary，不算独立范围点。

## C. 几何摘要与容差

DATA-003 同一环境两次 STEP 回读的离散拓扑和摘要一致：合法目录案例 1/1/29/59/30 solids/shells/faces/edges/vertices、volume 6712.645162 mm³、bbox 32×32×14 mm；hard boundary 1/1/74/149/75、volume 95092.318591 mm³、bbox 110×110×22 mm。两案例 STEP SHA-256 重跑均不同。输出体积与构造体积差约 0.013–0.034 mm³。manifest 的面/边签名来自 6 位量化，没有原始构造与回读面/边数值向量，也没有足够重复次数。因此：

- 冻结硬门槛：构造和回读都必须非空、无缺失/NaN/Inf，恰好 1 valid solid / 1 shell；solid/shell/face/edge/vertex 整数计数精确匹配本 IR 的同环境基准。容差不允许多实体通过。
- 数值候选：bbox/长度 `abs=1e-5 mm, rel=1e-8`；volume `abs=1e-4 mm³, rel=1e-8`；area `abs=1e-5 mm², rel=1e-8`。面面积/边长度按数值升序排序、列表数量精确相同，再逐项容差比较；6 位量化只用于摘要/显示，不代替容差。这个候选不能覆盖已测 STEP 体积差，因此当前状态必须是 `pending_measurement`，也不依据显示精度把容差放宽。
- 最小补测：合法目录行和 bore_d=80 各三次构造与 STEP 回读，保存未量化 volume/bbox/排序 face area/edge length 原始数组；另测 hard boundary 需明确确认与 legal-second-screw 不重复。再据此确定 roundtrip 与重复运行分别的阈值。
- `outer_d<bore_d` 属 preflight 拒绝；即使刻意跳过 preflight，已知 3 solids 必须由 post-geometry 拒绝。

因此本轮没有冻结全部 CAD-006 数值策略，Codex 中枢确认补测/配置前不得开始正式 CAD-005 实现。

## D. 错误阶段和结果契约

错误通道固定 `parse → schema → preflight → build → post_geometry → step_export → step_readback`。CAD-003 的前置拒绝必须不调用 build；IR 结构/引用/注册表错误归 schema。每条错误含稳定 code/stage/severity/fields/node_ids/message/retryable；仅资源/I-O 瞬时错误允许至多重试一次，字段错误不自动改值。后置几何、导出、回读失败写 accepted IR 的 `validation_result` 且 result/error stage 一致；前置参数错误只能写 rejected IR 顶层 errors。empty/missing/zero solids/invalid B-rep/multi-solid/missing metric/non-finite/mismatch 均硬失败。写 STEP 返回成功、文件非空和 STEP 字节 hash 均不代替 readback geometry check。

Schema 有验证结果成功/失败、stage 和 errors 数量约束，error stage enum 已与契约修订为 `parse`、`build`。稳定错误码明细见 spec §7。若 CAD-005/006 要持久化“导出成功后再读回失败”的多阶段流水线，可在一个 result 的错误列表记录其首个失败阶段；禁止把较早 stage 的错误混入后续 stage result。

## 当前线程模型冲突澄清

固定当前 `part.py` 把空心基体与 `_tapped_hole` 形成的环形 cutter 作差。它的注释称过去试过 helix，M3–M8 布尔会 no-op；这不表示当前环形模型。R3 在固定环境构造无孔 profile 并用当前环形 cutter 对照，M6 移除 138.396242882 mm³，M12 移除 1423.126854189 mm³，均为 1 solid。故“不移除任何材料”的旧 handoff 说法不适用于当前模型。只确认当前环形刀具发生切除，不宣称真实螺旋线程、螺纹配合或工程性能等价；这些功能验收仍待中枢/负责人决定。

## 验证清单与交接

实际验证：

- `Draft202012Validator.check_schema` + 五 IR 示例：PASS。
- `/tmp/ir001r2_validate.py`：5/5 Schema+语义 PASS，12 个指定结构/语义反例拒绝。
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`：17 tests PASS。
- `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`：PASS；合法构造/单实体、规则拒绝。
- `/tmp/ir001_r3_formula_test.py`：PASS；`/tmp/ir001_r3_transform_probe.py` 固定 OCP 环境 PASS；`/tmp/ir001_r3_thread_probe.py` 当前 M6/M12 布尔体积差 PASS。
- `python3 -m json.tool` Schema + 5 JSON：PASS。`git diff --check` 和允许路径审计在提交前执行。

handoff_successor_check:
  predecessor=IR-001-R2 checkpoint，CAD-005/006-R2 checkpoint 和 review
  files_format=IR/CAD-003/schema/checkpoint/示例均存在且可解析；固定源关键文件匹配 DATA-003 上游 manifest blob SHA
  core_rerun=Draft 2020-12 自检和五示例 PASS；CAD-003 17 tests PASS；项目 venv test_handoff PASS
  normal_case=合法目录 bore_d=20 通过 check/build，1 solid
  failure_case=相同目录 second_screw=1 在 check 阶段拒绝；invalid outer_d<bore_d 对照为 bypass 后 3 solids，不能放行
  interface=公式/单位、placement、后置结果与 IR/CAD-003 字段边界已定；CAD-006 浮点阈值仍 pending_measurement
  limits=family_scope 等待负责人；snapshot reproducibility_partial；许可证范围不明；未实现 CAD-005/006
  result=review
  blocking_issue=数值几何容差须补测，首族范围未冻结

下一步：Codex 中枢独立审查此文件及 diff；由其确认补测和最终数值配置，再决定是否启动 CAD-005/006。此 checkpoint 不把 IR-001 标为 done，也不启动编译器或生产验证器。
