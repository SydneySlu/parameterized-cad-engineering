# DATA-003 来源审计（审计材料，未冻结族选择）

核查日期：2026-11-01（Asia/Shanghai）  
来源：`https://github.com/BenchCAD-org/benchcad-2`  
固定 source commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`（`main`，`git rev-parse HEAD`）  
remote：`https://github.com/BenchCAD-org/benchcad-2.git`

## 仓库级证据

- `README.md:21-27` 规定一个族由 `designs/<family>/{part.py,spec.py,family.json}` 组成；`README.md:36-43` 给出官方 `uv sync`、`uv run bench2 validate <family>` 和 `uv run bench2 preview <family>` 命令。
- `README.md:53-55` 说明代码和 designs 为 MIT，已发布 dataset artifacts 为 CC BY 4.0。
- `LICENSE:1-21` 是 MIT 正文；`LICENSE:25-30` 将 HuggingFace 数据集单独标为 CC-BY-4.0。
- `docs/STATUS.md:3-5` 说明状态流转为 `MERGED → GENERATED → QUALIFIED/NEEDS_WORK → RELEASED`，并记录 `4 / 150 families merged`、`0 release-qualified`、更新时间 2026-08-02。
- `docs/STATUS.md:9-12` 将下述三个候选标记为 `MERGED`。这不是 release-qualified 或已发布实例集证据；`status_uncertain` 仍适用于是否已有可再分发生成资产。

## 候选逐族审计

| 候选 | 真实路径/注册 | family_id 与目录 | 构造/约束入口 | 参数和耦合观察 | 状态/发布证据 | 依赖/外部资源 |
|---|---|---|---|---|---|---|
| `set_screw_shaft_collar` | `designs/set_screw_shaft_collar/{family.json,part.py,spec.py,NOTES.md}` | `family.json:2` 一致 | `part.py:24-74 build()`；`spec.py:105-116 check()`；`spec.py:93-102 refine()` | 15 个 GN 705 表行（`spec.py:6-23`）；`bore_d` 为离散 H8 直径，`outer_d/width/screw_d/screw_len/second_screw` 由目录行耦合；单位 mm，`second_screw` 无量纲；`part.py:77-125` 明确为环形近似的 tapped-hole 几何 | `MERGED`（STATUS:10）；无 release-qualified/实例发布证据，`status_uncertain` | `part.py` 只导入 `cadquery`；`NOTES.md` 声明外部标准图纸/下载文件，但这些文件不在族目录快照中，不能当作仓库内资源 |
| `slotted_din_rail` | `designs/slotted_din_rail/{family.json,part.py,spec.py}` | 目录名与 `family.json:2` 的 `slotted_din_rail_th35_7_5` **不完全相同**；应保留两个 ID，不得静默归一化 | `part.py:6-47 build()`；`spec.py:172-190 check()`；`spec.py:153-158 refine()` | `MODEL_ROWS` 四个 DN-R35S 行（`spec.py:4-17`），`model_index` 选择完整目录行，其余 9 个几何字段耦合；`side_relief` 是布尔/无量纲比例特征；其余单位 mm | `MERGED`（STATUS:11）；无 release-qualified/实例发布证据，`status_uncertain` | `part.py` 仅 `cadquery`；无显式外部文件读取 |
| `speaker_pole_mount_socket` | `designs/speaker_pole_mount_socket/{family.json,part.py,spec.py}` | `family.json:2` 与目录一致 | `part.py:6-66 build()`；`spec.py:74-89 check()`；`spec.py:69-71 refine()` | 8 参数；`bore_d/flange_od/flange_t/depth` 有离散 choices，`cup_outer_d` 由 `bore_d + 2 + 2*flange_t` 耦合，`hole_d/hole_bcd` 固定；`bottom_radius` 为 proportion；长度单位 mm，其余直径 mm | `MERGED`（STATUS:12）；无 release-qualified/实例发布证据，`status_uncertain` | `part.py` 仅 `cadquery`；family.json 的 Penn Elcom/Adam Hall 来源为外部资料链接/说明，不是随仓库分发资源 |

## 许可证范围判断

- **仓库代码与族源文件**：按仓库 README/LICENSE，当前固定 commit 下的代码、`designs/*` 和框架适用 MIT；再发布源码需保留 MIT copyright/notice。
- **生成/派生 CAD（STEP、STL、渲染图）**：仓库只明确“released dataset artifacts”CC BY 4.0；本 smoke test 生成物不是官方 released dataset artifact，不能自动套用 CC-BY，也不能据此推断可公开再发布。当前只放在被忽略的 `work/benchcad-output/`，判定为 `license_scope_uncertain`，等待中枢逐项确认派生资产是否允许发布及署名格式。
- **Public/Core 评测数据**：本任务没有下载；项目计划已规定不得放入训练/检索语料。族源代码与评测集是不同资产。
- **族引用的标准图纸/照片/下载文件**：`set_screw_shaft_collar/NOTES.md` 明列 `gn705_standard_sheet.pdf`、工程图 SVG、产品照片，但它们不在本 checkout 的族目录中；第三方材料的版权/许可未由 BenchCAD LICENSE 覆盖，记为 `license_scope_uncertain`，本任务不复制。

## 审计结论

三个候选都是真实存在且有 `part.py/spec.py/family.json` 的已合并族，均有可调用 `build()`、参数规格和 `check()`。`set_screw_shaft_collar` 最适合作为当前首族 smoke slice：参数目录耦合清楚且有明确合法边界/第二紧定螺钉规则；但源码注释承认 M3–M8 的螺纹切割布尔可能不移除体积（`part.py:91-98`），需在项目验证中保留风险。`slotted_din_rail` 的目录 family_id 不一致，是适配/manifest 风险；`speaker_pole_mount_socket` 的部分尺寸是 proportion/外部供应商资料，来源解释性较弱。以上是比较结果，不是首族冻结决定。
