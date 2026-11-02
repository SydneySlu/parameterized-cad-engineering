# CAD-005/006 修正续作 Prompt：固定 IR 输入绑定与结构化错误定位

请将本 Prompt 发给**原 CAD-005/006 执行 Agent**继续修正。不要另起一份 CAD-005/006 实现，也不要重做已通过的 45 组容差测量。项目负责人统一 push；本轮不要 push，也不要把任务标成 `done`。

## 任务背景

Codex 中枢已复核实现提交 `5f05e59`、checkpoint `fea112c`，并独立重跑了 CAD 编译 10 项、Schema 17 项和 IR 契约/轴向 5 项，全部通过。但中枢发现一个必须修复的核心问题：

对 `legal-catalog-row.json`，将 `nodes[2].inputs.radial_offset` 换成 `{"kind":"literal","value":100,"unit":"mm"}` 后：Draft 2020-12 Schema 和 `validate_ir()` 都接受；`compile_ir()` 仍返回 `ok=true, status=step_readback`。生成体积由约 `6712.631936 mm³` 变为 `6851.028179 mm³`，几何没有按冻结映射形成预期主孔。原因是当前验证器检查了节点字段名和表达式白名单，却没有检查核心输入绑定是否符合首族已冻结的映射。

此外，`_failed_result()` 对所有运行时错误都写 `node_ids=[]`，即使错误字段已经指向某个节点。这丢失了 IR 错误协议要求的节点定位。

## 目标与冻结边界

本轮只修复上述两项，并补齐验证和交接记录：

1. 只有符合 `agent-work/typed-cad-ir/IR-001-v0/mapping.md` 及首族示例中冻结绑定的 accepted IR 才能进入 CAD 构造。
2. 对错误输入绑定给出稳定、可定位的结构化拒绝结果，并保证拒绝发生在 CadQuery/OCP 初始化和构造之前。
3. 有节点上下文的运行时错误必须在 `node_ids` 填入真实节点 ID；没有节点上下文时才允许为空。
4. 保持 CAD-006 数值策略 `CAD-006.geometry-comparison.v1`、阈值、IR JSON 字段、首族范围和坐标/placement 语义不变。

不得通过放宽规则、忽略额外字段或只在测试中拦截特定 `radial_offset=100` 值来修复。不得用自由字符串、`eval`/`exec` 或模型生成代码执行表达式。

## 启动前复核

先确认仓库根目录和工作区状态，不得覆盖其他 Agent 改动：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -5
```

阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`、本 Prompt、`agent-work/reviews/CAD-005-006-implementation-codex-review.md`、`agent-work/cad-validation/CAD-005-006/checkpoint-implementation.md`、IR v0 `mapping.md`、`semantic-validation.md`、Schema、规范和六个示例。至少重跑一次当前 CAD 编译测试，确认审查记录可复现；如果仓库或交接状态与记录不一致，先写 `review/blocked` checkpoint 并暂停。

## 实现要求 A：校验冻结的节点输入绑定

在语义验证/编译前置阶段，为首族固定七节点图建立严格、显式、可审计的输入绑定契约。检查应按 `node_id` 和输入字段定位，不能只检查字段集合或公式 ID 是否属于白名单。比较 JSON 表达式树时忽略对象键的序列化顺序，但不得把不同参数、常量、单位或公式组合视为等价。

至少覆盖以下约束，具体树结构以 `mapping.md` 和标准 IR 示例为准：

- `n0.catalog.resolve`：目录选择输入必须来自 `bore_d`；不能把其他参数或任意 literal 当目录键。
- `n1.collar.revolve`：`bore_d`、`outer_d`、`width` 来自相应冻结参数；`chamfer` 必须是登记的 `collar_chamfer` 输入绑定。
- `n2.hole.primary` 与 `n4.hole.secondary`：螺纹直径、ISO 261 粗牙 pitch、角度、`over`、`wall`、`hole_len`、`z_in`、`z_out`、`radial_offset`、`axial` 必须分别符合冻结映射；主孔角为 0°，第二孔角为 135°，第二孔启用条件保持 `second_screw=1`。
- 映射中的固定关系必须被逐项校验：
  - `wall = half_difference(outer_d, bore_d)`；
  - `over = literal(0.5, mm)`；
  - `hole_len = add(wall, multiply(over, literal(2, 1)))`；
  - `z_in = over`；
  - `z_out = add(over, wall)`；
  - `radial_offset = subtract(half(bore_d), literal(0.5, mm))`；
  - `axial = multiply(width, literal(0.5, 1))`。
- `n3.cut.primary`、`n5.cut.secondary` 的 base/tool 输入和 properties 引用必须与固定上游输出匹配；`n6.result` 的 selector 输入和零/一分支引用必须匹配固定图。
- `thread_model=revolved_ring_approximation`、`helical_thread_supported=false`、回转轴和 placement 约束必须继续符合 IR v0 契约。

若发现上面清单和已冻结示例/规范有矛盾，**暂停并上报 Codex**；不得自行改变 IR 语义、ADR、Schema 版本或容差。

对于不符合绑定的 accepted IR：

- 在 build 前返回稳定错误码及正确字段路径，建议使用已有错误协议中合适的 schema/semantic 错误码；若需要新增码，先确认未与现有码冲突并记录在实现报告中，不改 IR 字段结构。
- 不初始化/调用 CadQuery/OCP，不创建 STEP 文件；测试用 mock 断言 `_cq_runtime`、`_native_build` 未被调用，并检查输出目录没有新 STEP。
- 错误中应明确指出 node ID 和不匹配的 input 字段，避免只返回“IR 不支持”。

## 实现要求 B：错误 `node_ids` 定位

修复运行时失败的序列化：

- 有节点上下文的错误把真实 `node_id` 放入 `node_ids`，例如错误路径 `nodes.n1.collar.revolve...` 应输出 `node_ids=["n1.collar.revolve"]`。
- 若错误发生在按数组索引报告的 IR 语义校验阶段，应根据 `nodes[index]` 从已解析 IR 找到对应 `node_id`；无对应节点的全局错误才使用空数组。
- `fields` 仍使用 JSON Pointer/当前稳定字段定位约定；保留 `code`、`stage`、`severity`、`retryable` 等 Schema 字段和阶段语义。
- 不把 build 错误改写成 schema/preflight 错误，也不破坏 `validation_result.completed_stages` 顺序。

## 必须新增的回归用例

测试要证明拒绝行为来自通用绑定契约，而非针对单个数值写特判：

1. 标准 `legal-catalog-row.json`、`legal-second-screw.json` 均通过 Schema、语义校验、完整编译与 STEP 回读。
2. 主孔 `radial_offset=100 mm` 的 IR 被拒绝；`_cq_runtime`、`_native_build` 未调用；没有 STEP 产物。
3. 至少一个错误 `hole_len` 绑定和一个错误孔角（例如主孔改为 90°）在 build 前被拒绝，同样无 STEP 产物。
4. 对合法目录行和合法 hard-boundary 保持同进程 native 精确重复比较及 native→STEP 冻结策略通过；不得放宽阈值。
5. 注入一个带节点字段路径的 build 或 boolean 失败，断言 `node_ids` 指向真实节点；再覆盖一个全局错误仍可 `node_ids=[]`。
6. 原有多实体、规则拒绝、parse/schema、构造/导出/回读错误阶段测试继续通过。

## OCP 兼容补丁风险

`_cq_runtime()` 当前给全局 `TopoDS_*` 类型注入 `HashCode = id(self)`。不要顺手扩大重构；请查明兼容原因，并记录 CadQuery/OCP 版本、调用依赖和该补丁可能影响的拓扑身份/去重语义。若能够用官方 API 或局部兼容层替代，先用针对性测试证明等价；若无法证明安全，保留现状并明确报告给 Codex，不能无证据删除或宣称无风险。

## 文件边界

允许修改：

```text
src/cad_compilation/**
tests/cad_compilation/**
agent-work/cad-validation/CAD-005-006/**
docs/WORKLOG.md   # 只追加
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

如认为 IR 规范第 11 节的第二孔示例状态需要更新，在 checkpoint 中指出过时文字及建议的追加说明，交由 Codex 中枢处理；本轮不要自行改写冻结 IR 文档。源代码放 `src/`，测试放 `tests/`，不得把工作脚本写进 Agent 的 `outputs/`。

## 验证命令

使用项目固定环境执行，不要为方便改系统 Python 或升级 CAD 依赖：

```bash
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -v
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
work/benchcad-output/venv/bin/python -m unittest tests.typed_cad_ir.test_schema_contract tests.typed_cad_ir.test_axis_mapping -v
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 work/benchcad-output/venv/bin/python -m py_compile src/cad_compilation/*.py tests/cad_compilation/*.py
git diff --check
```

不需要重跑 45 组容差测量。必须确认 `tolerance-results.json`、`tolerance-preflight.md`、ADR-0008 和 IR 第 9.2 节阈值未被修改。几何比较策略 ID 继续写入 manifest。

## 交付、checkpoint 和提交

结束前追加 `docs/WORKLOG.md`，更新 `agent-work/cad-validation/CAD-005-006/checkpoint-implementation.md` 或新增 R2 checkpoint，并在报告中清楚区分已修复、已验证和未解决风险。至少记录：

```text
task=CAD-005/006
phase=canonical-binding-fix
status=review | blocked
changed=...
verified=...
rejected_mutations=radial_offset; hole_len; angle
node_ids_cases=...
tolerance_policy=CAD-006.geometry-comparison.v1 (unchanged)
known_limits=...
next=Codex 中枢独立复核
```

`git diff --check` 和允许路径审计通过后，提交一个可审查 commit，提交信息格式：

```text
fix: enforce frozen CAD IR bindings [CAD-005/006]
```

不要 push，不要改项目正式状态，不要将 CAD-005/006 标为 `done`。完成后暂停，等待 Codex 中枢复核。
