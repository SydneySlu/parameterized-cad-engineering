# CAD-005/006 续任执行 Prompt：几何容差前置测量与确定性 CAD 编译/验证

将下面内容发给**原 CAD-005/006 Agent**继续执行。不要重新创建第二个 CAD-005/006 任务，也不要跳过阶段 1 直接编写生产实现。

你是“参数化 CAD 工程辅助设计”项目的 CAD-005/006 执行 Agent，负责：

- CAD-005：把已审查的 Typed CAD IR v0.2.0 编译为白名单 CadQuery/OCP 构造器并导出 STEP；
- CAD-006：建立 preflight、构造后几何检查、STEP 回读和族级规则验证；
- 首期只支持已经冻结的 `set_screw_shaft_collar`，不扩展第二族。

本任务必须采用“两阶段门控”：

1. **阶段 1：几何容差前置测量**。先测量并记录证据，不能未经审查把候选阈值写死进生产验证器。
2. **阶段 2：正式 CAD-005/006 实现**。只有阶段 1 的交付物经过 Codex 中枢独立审查后才能开始。

---

## 一、项目根目录和文件边界

先执行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

所有工作必须发生在该 Git 根目录。不要 reset、clean、checkout、覆盖其他 Agent 的未提交改动，也不要把脚本写入 CC/Agent 的 outputs 目录。

允许修改：

```text
src/cad_compilation/**
tests/cad_compilation/**
agent-work/cad-validation/CAD-005-006/**
docs/WORKLOG.md           # 只追加
```

禁止修改：

```text
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
docs/DECISIONS.md
database/**
agent-work/data/**
agent-work/schema-rules/**
agent-work/typed-cad-ir/**
```

如果发现需要改变冻结接口、项目状态、计划或决策，先记录 `blocked` 或 `review`，交给 Codex 中枢，不要自行改写。

---

## 二、阶段 0：续任交接复核（开始实现前必须完成）

先阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_PLAN.md`
- `docs/TASKS.md`
- `docs/DECISIONS.md`
- `docs/coordination/handoff-review-protocol.md`
- `agent-work/cad-validation/CAD-005-006/checkpoint-r2.md`
- `agent-work/cad-validation/CAD-005-006/handoff_successor_check-r2.md`
- `agent-work/reviews/CAD-005-006-R2-codex-review.md`
- `agent-work/typed-cad-ir/IR-001-v0/**` 中的全部规范、Schema、示例和语义验证资料
- `agent-work/data/DATA-003-single-family-audit/**` 中的 checkpoint、run-log、环境和许可证审计
- `agent-work/schema-rules/CAD-003-schema-v0/**`

按“三层检查”中的续任 Agent 要求，至少重跑：

1. IR 示例的 JSON Schema/语义检查；
2. `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`；
3. `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`；
4. 一个正常案例；
5. 一个规则拒绝案例；
6. 一个绕过规则后会产生多实体的案例（已知风险：`outer_d < bore_d` 可能得到 3 solids）。

记录：

- 实际命令和输出；
- 与 R2 交接记录是否一致；
- 当前解释器、CadQuery/OCP/NumPy 版本；
- IR revision、Schema revision、BenchCAD source commit；
- 任何不一致、缺失依赖或接口疑点。

若交接结果与记录不一致，先写 `review` 或 `blocked` checkpoint，停止扩大修改，不要覆盖前序成果。

---

## 三、阶段 1：几何容差前置测量（本轮第一目标）

阶段 0 通过后，先建立测量脚本和结果，不得直接实现正式验证器阈值。

### 1. 必测案例

至少覆盖：

```text
legal_catalog_row:
  bore_d=20, outer_d=32, width=14,
  screw_d=6, screw_len=8, second_screw=0

legal_hard_boundary:
  bore_d=80, outer_d=110, width=22,
  screw_d=12, screw_len=20, second_screw=1
```

同时尽量覆盖全部 15 个合法目录 `bore_d` 值。每个案例至少重复 3 次；如果某些目录行无法构造，记录准确原因，不能静默跳过。

每次构造都要记录：

- solids、shells、faces、edges、vertices；
- `isValid()`；
- 体积；
- 包围盒；
- 排序后的面面积摘要；
- 排序后的边长摘要；
- native build 与 STEP readback 的数值差；
- 构造器、CadQuery/OCP、NumPy、Python 版本；
- BenchCAD source commit；
- IR/Schema revision；
- STEP 字节 hash（只能作为附加信息）。

必须区分并测量：

- 同一环境内重复构造误差；
- STEP 导出/回读误差；
- 最大绝对误差、相对误差和建议候选阈值；
- 结构计数是否稳定。

不要把候选阈值写进生产代码，也不要宣称“确定性”已经证明。阶段 1 的结果必须等待 Codex 中枢审查。

### 2. 反例和对抗测试

必须保留并记录：

- `outer_d < bore_d` 在 preflight 中被拒绝；
- 绕过 preflight 后的实际结果可能是 3 solids；
- `second_screw` 约束非法；
- 壁厚不足或等价几何非法；
- 缺少关键参数、重复 node id、错误 source commit、未登记公式等至少能被分类为结构/语义/规则错误（若尚未有运行入口，先记录为阶段 2 测试计划）。

### 3. 阶段 1 交付物

放入：

```text
agent-work/cad-validation/CAD-005-006/tolerance-preflight.md
agent-work/cad-validation/CAD-005-006/tolerance_measurement.py
agent-work/cad-validation/CAD-005-006/tolerance-results.json
agent-work/cad-validation/CAD-005-006/checkpoint-tolerance.md
```

`checkpoint-tolerance.md` 必须包含：

- `task=CAD-005/006-tolerance`
- `status=review` 或 `blocked`
- 修改文件；
- 实际运行命令和结果；
- 样本覆盖范围和未覆盖范围；
- 数值统计与候选阈值（候选，不是冻结值）；
- 环境与来源信息；
- 已知许可证/复现限制；
- 下一步必须由 Codex 中枢审查后才能进入阶段 2。

完成阶段 1 后暂停，不要自行开始阶段 2。提交一个可审查 commit，提交信息使用：

```text
test: measure cad geometry tolerances [CAD-005/006]
```

同时只追加一条 `docs/WORKLOG.md` 记录。不要自行 push；由项目负责人统一 push。

---

## 四、阶段 2：Codex 审查通过后再实现 CAD-005/006

只有收到 Codex 中枢明确放行后，才能继续。

必须严格执行：

```text
parse
→ JSON Schema / semantic
→ unit and parameter normalization
→ preflight
→ whitelist IR compilation
→ build
→ post_geometry
→ STEP export
→ STEP readback
→ structured validation_result and manifest
```

### CAD-005 必须实现

- IR JSON 解析；
- JSON Schema 和语义验证；
- 参数、单位、公式的白名单解释；
- 节点拓扑顺序执行；
- 五类白名单节点：
  - `catalog.resolve`
  - `shape.revolve_profile`
  - `feature.tapped_hole_cutter`
  - `boolean.cut`
  - `result.single_solid`
- 关键坐标语义：
  - `workplane = XZ`
  - `axis_local = [0, 1, 0]`
  - 世界回转轴为 Z；
  - 回转 360°；
  - 孔 cutter 使用 local +Z，按已冻结 placement 规则定位和旋转；
- CadQuery/OCP 构造；
- STEP 导出；
- 运行日志和 manifest。

必须保留 `thread_model=revolved_ring_approximation`，并明确 `helical_thread_supported=false`；`screw_len` 是目录字段，不得擅自解释为孔深。

### CAD-006 必须实现

- preflight 规则验证；
- build 错误；
- 单实体和 `isValid()`；
- 几何摘要；
- STEP 回读；
- 首族规则验证；
- `validation_result` 的阶段顺序、错误码和失败字段；
- 有界、可解释的失败报告。

### 严格禁止

- 执行 LLM 生成的自由 Python/CadQuery 代码；
- 使用 `eval`/`exec` 执行 IR 字符串；
- 绕过 Schema/IR 直接接受任意 dict；
- 修改 BenchCAD 源码或把外部源复制进生产目录；
- 扩展第二族；
- 把 STEP 字节 hash 作为唯一确定性判断；
- 把 `isValid()` 单独视为族规则通过；
- 声称完成强度、结构安全、碰撞或有限元验证；
- 把 `reproducibility_partial` 或 `license_scope_uncertain` 隐藏掉。

阶段 2 至少补齐：

- 合法目录行；
- 合法边界案例；
- `second_screw` 约束非法；
- `outer_d < bore_d` 几何非法；
- STEP 导出和回读；
- 缺少节点输入、重复 ID、未来依赖、未登记公式、错误 `validation_result` 等语义反例；
- 正常、规则失败、构造失败、回读失败四类验证报告。

相同 source commit、环境、IR/Schema 版本和参数至少运行两次，比较结构计数、`isValid()`、体积、包围盒、量化后的面/边摘要和错误阶段。若不稳定，记录具体差异并标记 `needs-review` 或 `blocked`。

---

## 五、交接、自检、提交格式

每个里程碑结束前追加 `docs/WORKLOG.md`，并提交 checkpoint。必须说明：

- 修改了什么；
- 用什么命令验证；
- 哪些结果已确认；
- 哪些问题仍未解决；
- 下一 Agent 或 Codex 中枢需重点关注什么。

最终向中枢报告时使用：

```text
task=CAD-005/006
phase=tolerance-preflight | implementation
status=review | blocked
changed=...
verified=...
ir_version=...
schema_version=...
geometry_repeatability=...
known_limits=...
next=...
```

不要将任务标记为 `done`。只有 Codex 中枢独立审查、必要修正完成并合并到 `main` 后，项目状态才可更新为 `done`。

