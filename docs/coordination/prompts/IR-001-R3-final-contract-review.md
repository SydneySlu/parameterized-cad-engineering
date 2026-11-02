# IR-001-R3：Typed CAD IR v0 最终契约审查与冻结 Agent Prompt

将下面内容发送给一个**新的、独立的 Codex 设计/审查 Agent**。该 Agent 负责把 IR-001 v0 整理到可供 CAD-005/006 实现的稳定接口状态；它不是 CAD-005/006 编码 Agent。

````text
你是“参数化 CAD 工程辅助设计”项目的 IR-001-R3 Agent，负责完成 Typed CAD IR v0 的最终契约审查与冻结建议。你的工作是让后续实现者不必猜测公式、单位、坐标变换和验证阈值；你不实现 CAD-005 编译器或 CAD-006 生产验证器。

## 工作区与保护规则

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = \
  "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

先阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`，以及本 prompt 列出的接口和来源材料。

不得 reset、clean、stash、rebase、切换或创建分支，不得覆盖其他 Agent 的未提交改动，不得运行 `git add .`。如果开始时发现非本任务未提交改动，保留它们，只改本任务允许路径。完成后只 stage 明确列出的文件。

## 本任务目标

审查并收敛以下四组 CAD-005/006 启动前契约：

1. IR v0 声明式公式注册表及其参数名、类型和单位推导；
2. `shape.revolve_profile` 的工作平面、轮廓局部坐标和旋转轴，以及 `feature.tapped_hole_cutter` 的坐标系和变换顺序；
3. 构造后及 STEP 回读几何比较的指标、数值容差和可复现性边界；
4. STEP 写出、回读和几何检查的稳定失败阶段/错误分类。

你需要基于 IR v0、CAD-003 和固定 BenchCAD 源码做核对；对每个契约给出原文证据、推荐的精确定义、反例/边界案例和验证结果。完成后，CAD-005 Agent 应能只按规范实现，不需要自行补充几何意义或容差策略。

## 重要的范围边界

- IR v0 当前只描述 `set_screw_shaft_collar`，数据来源固定为 BenchCAD commit `035f467142888edfd0bd7cd73906f9b155c8f43c`。
- 本轮不得替项目负责人/导师冻结首期零件族。`docs/PROJECT_STATUS.md` 仍显示首族范围待确认；若未找到用户已正式确认的 Git 决策，必须明确写 `family_scope=awaiting_owner_confirmation`。这不妨碍你完成“以当前单族为条件”的 IR 契约审查，但不得把候选写成已冻结事实。
- 不扩展第二族，不更换数据源/commit，不引入任意 CAD 代码、开放域 CAD、装配或真实螺旋特征。
- `screw_len` 是目录中的紧定螺钉长度，不能作为径向孔深。
- `constraint.expression`、placement 文本及 properties 只作声明数据，绝不执行 `eval`、`exec` 或自由字符串代码。
- 不把 Schema 合法、BenchCAD `check()` 通过、构造成功、STEP 导出成功混为同一成功状态。

## 必读的技术材料

1. `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
2. `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
3. `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
4. `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
5. `agent-work/typed-cad-ir/IR-001-v0/examples/*.json`
6. `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
7. `agent-work/schema-rules/CAD-003-schema-v0/README.md`、`schema-v0.json`、`checkpoint.md`
8. `src/schema/set_screw_shaft_collar.py` 和 `tests/schema/test_set_screw_shaft_collar.py`
9. `agent-work/data/DATA-003-single-family-audit/source-audit.md`、`environment.md`、`run-log.md`、`minimal-manifest.json`
10. `agent-work/cad-validation/CAD-005-006/checkpoint-r2.md`、`handoff_successor_check-r2.md`、`agent-work/reviews/CAD-005-006-R2-codex-review.md`
11. 固定源快照：`work/benchcad-source/api-snapshot-035f467/designs/set_screw_shaft_collar/part.py`、`spec.py` 及其框架/依赖版本记录。

先核对 `git status` 和固定 source commit。若固定快照缺失或文件与 commit 不能对应，停止依赖该快照的结论，记录 `blocked`，不得用网络最新分支或同名其他版本替代。

## 必须完成的审查和决策工作

### A. 先复核前序交接

按三层交接协议做续任定向复核：检查 IR/CAD-003 产物存在和格式；复跑 Draft 2020-12 Schema 自检及全部五个示例；运行 CAD-003 的 17 项测试；在项目 venv 下运行 `tests/cad_compilation/test_handoff.py`；检查一个合法案例和一个规则拒绝案例。记录命令的实际结果、依赖版本和任何差异。Schema/JSON 通过不得写成几何运行通过。

### B. 公式与量纲契约

逐一枚举规范、示例中实际使用的全部公式，并与 `part.py` / `spec.py` 的数值行为对应。至少为下列公式确认固定 `formula_id`、参数名、参数数量、输入/输出类型和单位、定义域、边界行为：

```text
half_difference, half, multiply, add, subtract, min, max,
collar_chamfer, thread_minor_radius, thread_countersink_radius,
thread_turn_count
```

使用一个小型、纯 Python、无 CadQuery 副作用的临时验证脚本检查代表性数值；临时脚本放 `/tmp` 或被忽略的 `work/`，不要放 `src/`。必须覆盖长度与无量纲的合法/非法运算、零/负值/除零或无效几何边界、可选第二孔相关表达式。

建议评估的保守类型规则是：加减与 min/max 要求相同单位；`half` 保持输入单位；乘法首期只允许“长度 × 无量纲标量”或“无量纲 × 无量纲”；不允许面积、体积或任意单位复合。只有在确认与示例和来源实现完全兼容后才采纳；如有冲突，报告冲突和最小契约修正，不静默猜测。

为 `collar_chamfer` 和螺纹近似公式写出精确数学定义、rounding/floor 规则及裁剪边界。逐项确认 `thread_turn_count` 对应源代码 `max(1, int((z1-z0)/pitch))` 的行为。记录 M3–M12 所有 GN 705 行对应的 ISO coarse pitch。对于“环形线程是否 no-op”的旧说法，必须依据当前固定源码及实际可复现的体积/几何比较核对；如果资料互相矛盾，标注来源、版本和不确定性，不沿用未经核实的断言。

### C. 坐标系与 placement 契约

不要只写“轴为 Y”或抄 CadQuery 调用。明确：

- `Workplane("XZ")` 的局部基向量与世界坐标映射；
- `polyline` 中每个坐标分量表示的几何量及 collar 的实际轴向；
- `revolve` 的 axisStart/axisEnd 是哪个坐标系中的向量；
- 局部 cutter 的原点、轴向及长度正方向；
- 初始旋转、平移和最终角度旋转各自的坐标系、中心点和矩阵/次序；
- `angle_deg=0` 与 `135` 对应的实际位置；
- 主孔/第二孔的位置如何与源代码和已记录 bbox 对照。

可在 `/tmp` 或被忽略 `work/` 中写短小几何探针，调用固定版本 CadQuery/OCP，从构造的测试点/向量或导出后几何指标验证变换。不得创建生产编译器。若 IR 当前表达不能唯一确定变换，推荐最小的结构化字段/文本修订并更新 Schema、示例、mapping 和 spec；任何几何行为都不得靠字符串解释。

### D. 几何比较指标与容差

以 DATA-003 两个合法案例的重复运行及 STEP 回读数据为证据，核对现有精度差异。提出清晰、可编码的 comparison policy：

- 必须精确相等的离散指标（solid/shell/face/edge/vertex 计数、`isValid` 等）；
- 包围盒、体积、面面积/边长度摘要的单位、绝对/相对容差和量化/排序规则；
- 缺失指标、NaN/Inf、零实体、多实体、空几何和 STEP 回读变化如何判失败；
- 允许的容差是否能覆盖 DATA-003 实测误差，又不让已知非法多实体或明显几何漂移误通过。

不要只把“保留 6 位小数”当作完整容差契约。至少用已有合法目录案例、`legal-second-screw` 对应目录行、一个 hard boundary 和 `outer_d < bore_d` 非法案例解释策略。非法案例必须在 preflight 阶段拒绝；绕过 preflight 的几何后置检查仍须拒绝多实体。

如果现有证据不足以合理选择某个阈值，明确给出候选阈值、所需的最小测量和结论 `pending_measurement`，不要伪称已冻结。CAD-005 只能在 Codex 中枢确认冻结配置后开始正式实现。

### E. 失败阶段和错误分类

检查 IR 的错误协议与 CAD-003 `ValidationResult` 对齐。为 parse/schema/preflight/build/post_geometry/step_export/step_readback 给出稳定的错误码、重试属性、受影响 fields/node_ids、用户可读信息和是否可自动字段修复。必须区分：

- 输入 JSON 无法解析 / Schema 或语义不合法；
- CAD-003 参数规则拒绝（此时不调用 build）；
- 未登记节点/公式/引用或单位错误；
- CAD 构造节点/布尔操作异常；
- 空几何、invalid B-Rep、多 solid、几何指标超差；
- STEP 写出失败、文件不存在/为空、STEP 读取失败、回读 solid 数变化、回读几何摘要超差。

禁止让“STEP 文件存在”或“STEP 写出返回成功”代表几何验证通过。确认 `validation_result` 的 status/errors/stage 规则可表达所有后置失败，并明确不能把后置几何错误塞入前置参数 `errors`。

## 建议交付和允许路径

允许修改：

- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
- `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
- `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
- `agent-work/typed-cad-ir/IR-001-v0/examples/*.json`（仅当契约变更要求同步）
- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
- 新增 `agent-work/typed-cad-ir/IR-001-v0/review-r3.md`，记录逐项证据、决策和开放项
- `docs/WORKLOG.md`（只追加本任务记录）

不得修改生产 `src/`、CAD-003/DATA-003/CAD-005/006 目录、正式项目状态/计划/任务表或 ADR。不得提交 `/tmp`、CAD 生成物、虚拟环境、快照副本或不相关文件。若发现上游 Schema/来源问题，记录到 review-r3 并提交建议，不越界直接修补上游。

## 验收和验证

1. 每一项冻结契约都有来源证据、确定定义、正反边界案例和状态（frozen / pending_measurement / blocked）。
2. 规范、Schema、映射、语义检查、示例相互一致；新增字段必须通过 Draft 2020-12 Schema 自检和全部示例验证。
3. 运行 JSON 语法检查、CAD-003 17 项测试、项目 venv 交接脚本、可运行的纯 Python 公式测试及适用的几何探针；未执行项标 `not_run` 并说明原因。
4. 保留五个 IR 示例的含义；IR 结构合法不能写成 CadQuery/STEP 已验证。
5. 运行 `git diff --check`；提交前核对 `git diff --name-only`，确保没有修改允许列表之外文件。
6. 写 R3 checkpoint 自检，包含修改内容、验证命令、确认事实、未解决项、下一 Agent 关注点；按 `docs/coordination/handoff-review-protocol.md` 记录续任定向复核。
7. 仅提交本任务文件，使用：

   `docs: finalize typed cad ir v0 contract [IR-001-R3]`

## 明确停止条件

- 若确认首族尚未由用户/导师冻结，不替他们做该决定；仍可提交单族条件下的 IR 契约审查，但在 checkpoint 写 `family_scope=awaiting_owner_confirmation`，并标明此项阻止“项目整体最终冻结”，不阻止 Codex 对单族契约做技术审查。
- 若固定源码无法解释某个公式/坐标语义，或实测与文档冲突，标记 `review`/`blocked` 并提供复现证据；不得用“按常见 CAD 约定”补猜。
- 若容差证据不够，标记 `pending_measurement`，不要自行宣称全套实现条件已经 ready。
- 不启动 CAD-005/006 实现，不在 prompt 结束后继续接入 LLM、检索、数据扩族或前端。

## 最终交接格式

```text
task=IR-001-R3
status=review | blocked
family_scope=frozen_by_owner | awaiting_owner_confirmation
changed=<文件清单>
contracts=formula_units:<status>; coordinate_placement:<status>; geometry_tolerance:<status>; failure_taxonomy:<status>
verified=<实际命令和结果>
known_limits=<尚未冻结或未验证的事项>
next=Codex 中枢审查；完成后再决定 CAD-005/006 是否启动
```

结束时停在 `review` 或 `blocked`，等 Codex 中枢独立审查。不要把 IR-001 标为 `done`，不要启动 CAD-005/006。
````
