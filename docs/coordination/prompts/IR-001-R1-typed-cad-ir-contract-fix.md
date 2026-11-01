# IR-001-R1：Typed CAD IR v0 契约修正 Agent Prompt

将下面内容复制到负责 IR-001 修正的 Codex/设计 Agent 对话框中。

```text
你是“参数化 CAD 工程辅助设计”项目的 IR-001-R1 Agent，负责根据 Codex 中枢的审查结果修正 Typed CAD IR v0 的接口契约。

本任务只修正 IR v0 的规范、JSON Schema、映射、示例和验证记录，不实现 CadQuery/OCP 编译器、几何验证器、LLM、检索系统或生产代码。

## 项目根目录

当前主机项目根目录：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

先执行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

不要在 Agent 默认目录建立副本；不要 reset、clean、stash、rebase 或覆盖其他 Agent 的未提交改动。只修改本任务允许的文件。

## 必读材料

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PROJECT_PLAN.md`
4. `docs/TASKS.md`
5. `docs/DECISIONS.md`
6. `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
7. `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
8. `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
9. `agent-work/typed-cad-ir/IR-001-v0/examples/`
10. `agent-work/data/DATA-003-single-family-audit/source-audit.md`
11. `agent-work/data/DATA-003-single-family-audit/run-log.md`
12. `work/benchcad-source/benchcad-2-035f467-raw/designs/set_screw_shaft_collar/part.py`

DATA-003 已确认的事实必须保留：`spec.check()` 必须先于 `build()`；绕过规则时原生构造可能接受非法参数或产生多实体；STEP 字节哈希不稳定；源码快照状态为 `reproducibility_partial`；M3–M8 的真实螺旋布尔操作可能 no-op，当前只能记录为环形线程近似。

## 本轮必须修正的契约问题

### 1. 明确前置拒绝与后置验证的互斥关系

规范正文和 JSON Schema 必须一致：

- `status=rejected` 必须有顶层 `errors`，`nodes` 必须为空，并且不得有 `validation_result`；
- `status=accepted` 不得有顶层 `errors`；可以有 `validation_result`，因为 accepted 只表示 IR 和前置规则通过；
- 后置几何或 STEP 失败使用 `status=accepted` + `validation_result.ok=false`，不能改成顶层 `errors`；
- 前置规则失败不能生成可执行节点。

用 JSON Schema 条件约束表达上述边界，并在 `ir-v0-spec.md`、`mapping.md` 中保持同一语义。

### 2. 修正可复现性状态边界

当前 v0 规范规定 BenchCAD 首族必须记录 `snapshot_status=reproducibility_partial`，不能声称源码、外部图纸和生成资产已经完全可复现。请让 Schema、正文和示例一致：

- 对当前首族适配器，不能把 `reproducible` 当作合法的 v0 状态；
- 如果保留未来状态枚举，必须明确它不是当前适配器可用值，并由语义检查拒绝；
- 不得删除 STEP 字节 hash 不稳定和许可证/外部资产边界说明。

### 3. 补齐 `feature.tapped_hole_cutter` 的确定性几何语义

当前节点只写了 `screw_d`、pitch、角度和 `over`，但 DATA-003 的源构造器还使用以下确定性关系：

```text
wall = (outer_d - bore_d) / 2
hole_len = wall + 2 * over
z_in = over
z_out = over + wall
radial_offset = bore_d / 2 - 0.5 mm
axial = width / 2
```

请用现有的结构化表达式和白名单公式补齐这些输入，或设计一个明确登记的族语义对象。不得继续依赖编译器猜测，也不得把可执行公式写成任意 Python 字符串。

要求：

- 主孔和条件第二孔的节点契约一致；
- 角度 0°/135°、`over=0.5 mm`、回转轴和放置关系与 `part.py` 对齐；
- `thread_model=revolved_ring_approximation` 和 `helical_thread_supported=false` 在两个孔节点中都明确记录；
- `screw_len` 继续作为目录/任务字段，不得误用为孔深；
- 如果某个表达式必须延后到 CAD-005 注册，写入未决项并给出 CAD-005 的明确输入要求，不能静默硬编码。

### 4. 限定自由字符串的作用

请在规范中明确：

- `constraint.expression` 是审计/展示文本，实际执行必须通过登记的 `constraint_id` 和白名单解释器；
- 节点 `properties` 只能承载已登记的元数据或族扩展字段；
- 编译器不得对 `constraint.expression`、`properties`、placement 文本调用 `eval`、`exec` 或任意代码解释；
- 可执行的节点输入只能使用 `parameter_ref`、`node_output_ref`、`literal`、`lookup` 和登记的 `formula`。

### 5. 补强结构 Schema 与语义校验边界

请根据 v0 的实际范围收紧或明确以下内容：

- 六个首族参数的 `type` 与 `value` 类型一致；`second_screw` 必须是整数 0/1；
- `parameter_id`、`node_id`、`output_id`、`constraint_id` 在 IR 内唯一；
- `ordinal` 从 0 连续递增；
- `depends_on` 只引用更早节点，引用目标和输出目标必须存在，依赖图必须无环；
- `enabled_if` 的参数存在且类型/值匹配；
- v0 的 `family_id`、`extension_namespace`、`source.schema_version` 与首族契约一致。若不全部由 JSON Schema 表达，必须在正文明确“这是反序列化后的语义检查”，并给出稳定错误码和检查责任边界。

不要为了追求通用性重新设计开放域 CAD IR；只修正首族 v0 的契约，并保留第二族扩展边界。

## 允许修改的文件

只允许修改：

- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
- `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
- `agent-work/typed-cad-ir/IR-001-v0/examples/*.json`
- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`

如需补充反例或验证说明，可在同一目录新增 `semantic-validation.md`；不得修改 `src/`、生产测试、CAD-003 文件、DATA-003 文件或其他 Agent 的未提交文件。

## 验证要求

至少完成并记录：

1. `python3 -m json.tool` 检查 Schema 和全部示例；
2. 使用 Draft 2020-12 JSON Schema 验证器检查四个现有示例；如果仓库没有依赖，使用隔离临时环境，不要把临时依赖提交进仓库；
3. 增加或临时验证以下反例确实被拒绝：
   - accepted 同时携带 errors；
   - rejected 同时携带 validation_result；
   - duplicate parameter/node/output ID；
   - ordinal 不连续或依赖未来节点；
   - 未登记公式或任意字符串执行入口；
   - `snapshot_status=reproducible`（如果本轮决定对 v0 收紧）；
4. 检查合法、缺失参数、second_screw 规则拒绝和几何验证失败四个示例仍符合新的契约；
5. `git diff --check` 通过；
6. checkpoint 真实记录“完整 JSON Schema 验证”与“仅 JSON 语法/结构检查”的区别，不得夸大验证范围。

## 明确不做

- 不实现 CAD-005 编译器；
- 不实现 CAD-006 几何/STEP 验证器；
- 不修改 BenchCAD 源码；
- 不改变 CAD-003 参数规则的事实含义；
- 不加入真实螺旋线程、装配、多族泛化或任意 Python 执行；
- 不删除已记录的许可证、快照和 STEP hash 限制；
- 不修改其他 Agent 的工作文件。

## 三层交接检查（高风险任务，必须执行）

本任务涉及接口、数据来源或 CAD 执行链，必须执行 `docs/coordination/handoff-review-protocol.md` 中的 double check。

如果本任务是续任任务，开始实现前必须：

1. 阅读上一个 Agent 的 checkpoint、交接文档和提交；
2. 复跑至少一条上一个 Agent 声称通过的核心命令；
3. 检查一个正常案例和一个失败/拒绝案例；
4. 确认输入输出接口、版本、来源和已知限制与本任务一致。

如果交接记录与实际结果不一致，先记录 `review` 或 `blocked`，不要直接覆盖前一个 Agent 的成果。

完成交接前必须记录：修改内容、实际命令及结果、已确认内容、未解决问题和下一 Agent 的重点。`checkpoint.md` 中必须包含 `handoff_self_check` 和（如有前序任务）`handoff_successor_check`。续任复核是定向复核，不替代 Codex 中枢的最终独立审查。

## 交接格式

完成后在 `checkpoint.md` 中写明：

```text
task=IR-001-R1
status=review | blocked
changed=<文件列表>
verified=<命令、验证器和结果>
contract_fixes=<本轮修正的契约>
known_limits=<仍未冻结的 CAD-005/006 输入或容差>
next=Codex 中枢复核后再交给 CAD-005/006
```

追加 `docs/WORKLOG.md` 的 checkpoint，并提交一个只包含本任务文件的 commit，提交信息使用：

`docs: tighten typed cad ir v0 contract [IR-001-R1]`

不要自行启动 CAD-005/006；完成后等待 Codex 中枢审查。
```
