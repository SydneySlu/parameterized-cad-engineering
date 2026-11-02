# IR-001-R3-FIX 修正 Agent 初始化 Prompt

你正在参与“参数化 CAD 工程辅助设计”项目。你的任务 ID 是 **IR-001-R3-FIX**，目标是修正 IR-001-R3 Typed CAD IR v0 契约中已经由 Codex 中枢确认的两个阻塞问题，并交付可复审的修正结果。

## 项目根目录与工作边界

项目根目录固定为：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

开始前必须：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
```

不得在自己的 Agent 输出目录、`/mnt/outputs` 或其他位置建立第二份项目副本。临时脚本可以放在系统临时目录，但最终验证记录、测试和文档必须放入仓库规定目录。

先阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_PLAN.md`
- `docs/DECISIONS.md`
- `docs/TASKS.md`
- `docs/coordination/handoff-review-protocol.md`
- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
- `agent-work/typed-cad-ir/IR-001-v0/review-r3.md`
- `agent-work/reviews/IR-001-R3-codex-review.md`

开始实现前，必须在 `docs/WORKLOG.md` 追加 `IR-001-R3-FIX / in_progress`，并先完成续任 Agent 定向复核：

```text
handoff_successor_check:
  predecessor=IR-001-R3
  files_format=<文件和 JSON 格式检查>
  core_rerun=<至少一条 R3 核心验证命令>
  normal_case=<一个 accepted 正常案例>
  failure_case=<一个 rejected 或 validation failure 案例>
  interface=<与本次修正输入输出一致性>
  limits=<geometry_tolerance pending_measurement、family_scope awaiting_owner_confirmation 等限制>
  result=pass | review | blocked
  blocking_issue=<若有>
```

发现前序记录与实际结果不一致时，先记录问题，不要直接覆盖原交付。

## 允许修改的范围

本任务只允许修正 IR-001-v0 契约、示例、语义验证说明、针对契约的回归测试、checkpoint 和工作日志。可以新增：

- `agent-work/typed-cad-ir/IR-001-v0/` 下的契约文档、示例和验证记录；
- `tests/typed_cad_ir/` 或仓库已有对应测试目录下的契约测试；
- `agent-work/reviews/` 下的交接/修正记录。

不得：

- 实现 CAD-005 Typed CAD IR 编译器；
- 实现 CAD-006 几何/STEP 验证器；
- 修改 `src/cad_compilation/` 生产实现；
- 修改 CAD-003、DATA-003 的既有契约或 BenchCAD 源快照；
- 增加第二零件族；
- 冻结首族范围；
- 冻结尚未测量的几何浮点容差；
- 引入自由 Python/CadQuery 字符串执行；
- 把构造成功、STEP 写出成功写成几何验证通过。

## 必须修正的问题一：回转轴坐标契约

R3 当前错误地把以下调用解释成世界 Y 轴：

```python
cq.Workplane("XZ").revolve(
    360,
    axisStart=(0, 0, 0),
    axisEnd=(0, 1, 0),
)
```

CadQuery 2.3 会把 revolve 的轴端点按当前 Workplane 坐标解释。对 `Workplane("XZ")`：

- 局部 X → 世界 X；
- 局部 Y → 世界 Z；
- 局部 Z → 世界 -Y；
- 因此局部 `axisEnd=(0,1,0)` 对应世界 +Z。

固定源码构造 `bore_d=20, outer_d=32, width=14` 的包围盒为约：

```
32.0000002 × 32.0000002 × 14.0 mm
```

说明套环的轴向宽度位于世界 Z。

请统一修正：

- `ir-v0.schema.json`；
- `ir-v0-spec.md`；
- `mapping.md`；
- 所有 accepted/rejected/validation 示例；
- `semantic-validation.md`；
- checkpoint/review 或相关交接记录。

建议保留现有 `axis` 字段但明确它表示世界轴，并把契约写成：

```text
workplane = XZ
axis_local = [0, 1, 0]
axis = Z                 # 世界回转轴
profile local x = radial coordinate → world X
profile local y = axial coordinate → world Z
profile local z/normal = world -Y
```

如果你认为需要使用不同字段名，必须在 checkpoint 中说明兼容性影响，并同步修改全部示例与语义检查；不能只修改文字而保留自相矛盾的 Schema 常量。

同时保留并明确 cutter 的已有 placement 事实：

- cutter 局部 +Z；
- 绕世界/局部定义清楚的 +Y 旋转 90° 后沿世界 +X；
- 平移到 `(radial_offset, 0, width/2)`；
- 再绕世界 +Z 按 `angle_deg` 旋转；
- 0° 在 +X，135° 位于 (-X,+Y) 象限；
- `screw_len` 不能作为孔深。

必须增加或更新回归验证，不能只依赖文字：

1. 直接验证 `Workplane("XZ").plane.toWorldCoords((0,1,0)) == (0,0,1))；
2. 用固定 BenchCAD 源码构造合法目录案例，验证 bbox 的 X/Y 为直径、Z 为 width；
3. 验证 Schema 中的 axis/workplane/axis_local 字段与上述语义一致；
4. 验证 placement 探针仍通过。

## 必须修正的问题二：build 阶段失败的结果契约

当前错误枚举和错误分类已经包含 `build` 阶段，例如 `CAD_BUILD_NODE_ERROR`，但 `validation_result` 的分支只允许：

```text
post_geometry
step_export
step_readback
```

accepted IR 又不允许顶层 `errors`，所以构造阶段失败没有合法的持久化位置。

请在以下两种设计中进行明确选择，并记录理由：

### 推荐设计：扩展 accepted IR 的 validation_result

将 `validation_result` 扩展为允许 `stage="build"` 的失败分支：

```json
{
  "ok": false,
  "stage": "build",
  "errors": [
    {
      "code": "CAD_BUILD_NODE_ERROR",
      "stage": "build",
      "severity": "error",
      "fields": [],
      "node_ids": ["n1.collar.revolve"],
      "message": "...",
      "retryable": false
    }
  ],
  "metrics": {}
}
```

要求：

- `accepted` IR 可以携带 `validation_result.stage="build"` 且 `ok=false`；
- build 失败不能伪装成 `post_geometry` 失败；
- build 失败不能回填为顶层参数 `errors`；
- `validation_result.ok=true` 仍必须有空 errors；
- `validation_result.ok=false` 必须至少有一个 error；
- 每个 error.stage 必须与 validation_result.stage 相同；
- 确保 `step_export` / `step_readback` 只在前一阶段成功后出现；
- 保留 `rejected` IR 不带 validation_result 的规则。

如选择其他设计，必须说明为什么推荐设计不适用，并完整定义 accepted IR 的状态、字段、Schema、语义校验和示例；不得留下“未来再决定”。

至少新增一个 Schema 合法的 build-failure 示例，或将现有 validation failure 示例明确改为 build 失败示例，并新增一个仍为 post_geometry 失败的示例，证明两个阶段不会混淆。更新 `semantic-validation.md` 的算法、错误码责任边界和反例。

## 验证要求

至少运行并记录以下检查：

```bash
# JSON 与 Schema
python3 -m json.tool agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json
python3 -m json.tool agent-work/typed-cad-ir/IR-001-v0/examples/*.json
# 使用仓库已有/项目隔离的 jsonschema 环境执行 Draft 2020-12 self-check
# 五个原有示例 + 新增/修改的 build-failure 示例全部验证

# 既有回归
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py

# 语义、坐标和构造失败契约
# 运行更新后的 IR 语义检查
# 运行 Workplane 坐标映射/bbox 回归测试
# 运行 build-stage validation_result Schema/语义测试
```

未实际运行的命令必须写为 `not_run`，不能写 PASS。系统 Python 缺少 CadQuery 时，必须明确记录 `blocked`，并使用已验证的项目 Python 3.11/CadQuery 2.3/OCP 7.9 环境运行 CAD 检查。

## 交付文件与 checkpoint

完成后必须更新：

- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
- `agent-work/typed-cad-ir/IR-001-v0/review-r3.md`（保留历史事实，并追加 R3-FIX 结果；不要删除旧记录）
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
- `agent-work/typed-cad-ir/IR-001-v0/mapping.md`
- `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
- 相关 examples 和契约测试
- `docs/WORKLOG.md`

checkpoint 必须包含：

```text
task=IR-001-R3-FIX
status=review | blocked
changed=<文件>
verified=<实际命令和结果>
handoff_self_check:
  changed=<...>
  commands=<...>
  confirmed=<...>
  unresolved=<...>
  next_agent_focus=<...>
known_limits=geometry_tolerance:pending_measurement; family_scope:awaiting_owner_confirmation; snapshot_status:reproducibility_partial
next=Codex 中枢独立复审；不得写成 CAD-005/006 done
commit=<short sha>
```

完成后只提交本任务范围内的文件，提交信息建议：

```
fix: repair IR-001-R3 axis and build failure contract [IR-001-R3-FIX]
```

不要自行 push 远程仓库。完成后把 commit、变更文件、验证结果、未解决限制和下一步写入 checkpoint，并等待 Codex 中枢复审。
