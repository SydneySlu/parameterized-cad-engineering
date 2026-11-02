# CAD-005/006 续任执行 Prompt：确定性 CAD 编译器与几何验证器

将下面内容发给**原 CAD-005/006 Agent**继续执行。不要重新创建第二个 CAD-005/006 任务，阶段 1 已验收，直接按冻结契约进行正式实现。

你是“参数化 CAD 工程辅助设计”项目的 CAD-005/006 执行 Agent，负责：

- CAD-005：把已审查的 Typed CAD IR v0.2.0 编译为白名单 CadQuery/OCP 构造器并导出 STEP；
- CAD-006：建立 preflight、构造后几何检查、STEP 回读和族级规则验证；
- 首期只支持已经冻结的 `set_screw_shaft_collar`，不扩展第二族。

阶段 1 几何容差测量已由 Codex 中枢验收，ADR-0008 已冻结比较策略，CAD-005/006 正式实现已放行。不要重新创建陌生 Agent 任务；原始 45 组测量通常无需重跑。只有环境、构造算法、测量定义变化或发现数据缺陷时，才补测并记录原因。
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
- `agent-work/reviews/CAD-005-006-tolerance-codex-review.md` 的追加放行结论
- `docs/DECISIONS.md` 中的 ADR-0008 和 IR-001 v0 第 9.2 节冻结策略
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

## 三、正式实现与冻结比较契约

CAD-005/006 已由 Codex 中枢放行。实现必须遵循策略 ID CAD-006.geometry-comparison.v1；完整规则见 IR-001 v0 第 9.2 节，决策依据见 ADR-0008。

硬性检查独立于数值阈值：preflight 参数、目录行、second_screw 耦合、壁厚及 outer_d < bore_d 规则必须通过；失败时禁止构造。native build 与 STEP readback 都必须非空、isValid、恰好 1 solid 和恰好 1 shell；solid/shell/face/edge/vertex 计数完全一致。缺失、NaN/Inf、空几何、无效 B-Rep 或多实体均失败。绕过 preflight 后 outer_d < bore_d 生成 3 solids 必须在 post-geometry 阶段拒绝。

同一进程内重复 native 构造要求拓扑计数精确相等；体积、bbox 六坐标、升序面面积和升序边长数组逐值精确相等，数组长度也精确相等。该要求仅适用于固定环境同一进程，不代表跨进程或跨平台保证。

同一 native 几何与 STEP 回读：
- bbox 六坐标逐项 abs 差不超过 1e-5 mm；bbox 不使用相对比较。
- 体积 abs 差不超过 0.0682 mm³ 且 rel 差不超过 3.941e-6。
- 面面积升序列表数量相同，逐项 abs 差不超过 0.00794 mm² 且 rel 差不超过 1.440e-5。
- 边长升序列表数量相同，逐项 abs 差不超过 1e-5 mm 且 rel 差不超过 2.956e-8。
- 体积、面积、边长 rel error 定义为 abs(a-b)/max(abs(a),abs(b))；abs 与 rel 条件必须同时通过，不能改为 OR 或两项相加。
- 面面积和边长数组元素必须有限、正值；分别排序后按索引比较，任何项超限即失败。不得只比均值、总和、直方图或量化签名。
- manifest 记录策略 ID、Python/CadQuery/OCP/NumPy/OS、source commit、IR revision、Schema hash 和实际比较结果。
- 旧 IR-001 R3 数值是早期未验证候选，已被 ADR-0008 和 IR 规范新策略取代，不得混用。

策略测量环境为 Python 3.11.18、CadQuery 2.3.0、OCP/cadquery-ocp 7.9.3.0、NumPy 1.26.4、macOS arm64。阶段 1 的 45 组结果来自 BenchCAD 原生 build，不是 IR 编译器输出。Windows/Linux、其他 CPU、其他内核/STEP writer、跨进程重复性及第二族均未验证。若 IR 编译输出对照原生参考超出冻结策略，暂停并报告，不能自行放宽阈值或改变 IR 语义。

必须严格执行：

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

正式实现至少补齐：

- 合法目录行；
- 合法边界案例；
- `second_screw` 约束非法；
- `outer_d < bore_d` 几何非法；
- STEP 导出和回读；
- 缺少节点输入、重复 ID、未来依赖、未登记公式、错误 `validation_result` 等语义反例；
- 正常、规则失败、构造失败、回读失败四类验证报告。
- 使用真实 IR JSON 走项目编译器，不得只调用 BenchCAD `part.build()` 作为项目实现证据。
- 对合法目录和 hard boundary 的 IR 编译结果执行同进程重复构造与 native→STEP 集成比较。
- 将这两例 IR 编译几何与固定 BenchCAD 原生参考结果做差异报告；若超出冻结策略，暂停并上报，不得放宽阈值或改 IR 语义。

相同 source commit、环境、IR/Schema 版本和参数至少运行两次；重复 native 构造按精确摘要相等比较，native→STEP 按冻结策略的排序数组和绝对/相对阈值比较。若不稳定，记录差异并标记 needs-review 或 blocked。

---

## 四、集成验证、文件边界与交接

每个里程碑结束前追加 `docs/WORKLOG.md`，并提交 checkpoint。必须说明：

- 修改了什么；
- 用什么命令验证；
- 哪些结果已确认；
- 哪些问题仍未解决；
- 下一 Agent 或 Codex 中枢需重点关注什么。

最终向中枢报告时使用：

```text
task=CAD-005/006
phase=implementation
status=review | blocked
changed=...
verified=...
ir_version=typed-cad-ir.v0 / 0.2.0
tolerance_policy=CAD-006.geometry-comparison.v1
schema_version=...
geometry_repeatability=...
known_limits=...
next=Codex 中枢独立审查
```

不要 push，由项目负责人统一 push。不要将任务标记为 `done`。只有 Codex 中枢独立审查、必要修正完成并合并到 `main` 后，项目状态才可更新为 `done`。

