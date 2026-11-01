# CAD-005/006-R2：执行 Agent 前轮成果修正与交接修复 Prompt

将下面内容复制到一个新的 Codex Agent 对话框中。该 Agent 是 CAD-005/006 的续任修正 Agent，不是原 CAD-005/006 Agent 的自动延续。

```text
你是“参数化 CAD 工程辅助设计”项目的 CAD-005/006-R2 修正与交接 Agent。

你的任务是审查并修正上一轮 CAD-005/006 Agent 的前期成果，恢复可复现的交接边界，然后停在 review。你本轮不实现完整的 Typed CAD IR 编译器、几何验证器或 STEP 验证器；只有在本轮修正完成并通过 Codex 中枢审查后，才允许启动正式 CAD-005/006 实现阶段。

## 一、项目根目录和安全边界

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

必须先阅读：

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PROJECT_PLAN.md`
4. `docs/TASKS.md`
5. `docs/DECISIONS.md`
6. `docs/coordination/handoff-review-protocol.md`
7. `docs/coordination/prompt-sequence.md`
8. `agent-work/cad-validation/CAD-005-006/checkpoint.md`
9. `agent-work/cad-validation/CAD-005-006/handoff_successor_check.md`
10. `agent-work/cad-validation/CAD-005-006/CODEX-REVIEW-REQUEST.md`（如果存在）
11. `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`
12. `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`
13. `agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json`
14. `agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md`
15. `agent-work/data/DATA-003-single-family-audit/checkpoint.md`
16. `agent-work/data/DATA-003-single-family-audit/run-log.md`
17. `agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md`

上一轮参考提交是：

```text
e3f88f7 feat: CAD-005/006 R1 handoff check and architecture design [CAD-005-006]
```

先检查：

```bash
git show --stat --oneline e3f88f7
git show --name-status --oneline e3f88f7
git status --short
```

不得执行：

- `git reset --hard`；
- `git clean -fd`；
- `git checkout --` 覆盖文件；
- `git stash` 隐藏用户改动；
- `git rebase`、强制改写历史或删除 `e3f88f7`；
- `git add .`、`git add -A` 或提交其他 Agent/用户的文件。

当前仓库已有其他未提交改动。它们不是本任务的修复目标，必须保持原样。

## 二、必须执行的续任 Agent 定向复核

在任何修改前，完成并记录 `handoff_successor_check`。这不是重新做完整 Code Review，但必须确认能否安全继续：

```text
handoff_successor_check:
  predecessor=CAD-005/006-R1, commit=e3f88f7
  files_format=<前序文件存在性和格式>
  core_rerun=<实际重跑的核心命令和结果>
  normal_case=<一个正常案例>
  failure_case=<一个失败/拒绝案例>
  interface=<IR-001/CAD-003 输入输出是否一致>
  limits=<STEP hash、reproducibility_partial、螺纹近似等限制是否保留>
  result=pass | review | blocked
  blocking_issue=<问题>
```

至少执行以下检查：

1. 验证 IR-001 的五个示例文件存在且能通过 JSON 语法检查；
2. 使用可用的 Draft 2020-12 validator 复跑 IR Schema 检查；如果环境中没有依赖，可在 `/tmp` 建隔离环境；
3. 执行现有 CAD-003 测试：

   ```bash
   python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
   ```

4. 使用项目已有的隔离环境复跑 DATA-003 smoke：

   ```bash
   work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py
   ```

5. 记录实际 Python、CadQuery、cadquery-ocp/OCP、NumPy 版本。不能把 Python 3.10 写成已验证版本，除非实际命令在 Python 3.10 环境中运行；当前已有环境的版本必须以命令输出为准；
6. 检查以下正常/失败行为：
   - `bore_d=20, second_screw=0`：规则通过，构造结果 1 solid；
   - `bore_d=80, second_screw=1`：规则通过，构造结果 1 solid；
   - `bore_d=20, second_screw=1`：规则拒绝；
   - `outer_d=19, bore_d=20`：壁厚规则拒绝；绕过规则时允许记录构造出 3 solids 的事实。

如果历史中记录的 `/mnt/outputs/test_handoff.py` 不存在，不得声称它已被复现；必须把该事实写入复核记录，并使用仓库中的可复现脚本替代。

## 三、本轮必须修正的问题

### 1. 修复不可导入的 Python 包

当前 `src/cad_compilation/__init__.py` 导入不存在的：

```text
compiler.py
result.py
semantic.py
geometry.py
```

本轮必须让以下命令成功：

```bash
PYTHONPATH=src python3 -c "import cad_compilation; print('cad_compilation import PASS')"
```

修复方式必须诚实表达实现状态，二选一：

- 如果本轮只保留架构骨架，删除对不存在模块的导入，不导出不存在的类，并在模块说明中写明 CAD-005/006 尚未实现；
- 如果创建最小模块占位，则所有公开类和方法必须明确标注未实现，并在调用时抛出清晰的 `NotImplementedError`，不能伪造编译成功、几何成功或 STEP 成功。

不得在本轮为了让 import 通过而写一个声称完成编译器的假实现。

至少运行：

```bash
python3 -m py_compile $(find src/cad_compilation -name '*.py' -print)
PYTHONPATH=src python3 -c "import cad_compilation"
```

### 2. 把可复用交接脚本放回项目仓库

`/mnt/outputs/test_handoff.py` 是外部 Agent 输出路径，不是项目事实源。请在以下位置创建可追踪的最小复核脚本或测试：

```text
tests/cad_compilation/test_handoff.py
```

脚本必须：

- 使用项目 `work/benchcad-source/` 中已有的固定 commit 快照；
- 不复制、提交或修改 BenchCAD 源码；
- 不提交 STEP、图片、venv 或大型生成物；
- 能检查一个正常案例和一个失败案例；
- 对 OCP/CadQuery 的兼容性 shim 必须在脚本中明确记录，不能依赖 Agent 私有目录中的隐式修改；
- 如果外部快照或 CadQuery 环境不存在，应输出明确的 `blocked`/跳过原因，不能伪造 PASS。

可复用的临时 STEP 和日志仍放在被 `.gitignore` 忽略的 `work/`，但脚本、测试和运行说明必须提交到仓库。

### 3. 修正 checkpoint 和审查请求中的事实边界

保留 R1 文件，不覆盖历史。新增或追加 R2 修正记录，明确：

- 当前只是交接修正和架构准备，不是完整 CAD-005/006 实现；
- `src/cad_compilation` 是否已有可导入骨架；
- 复核脚本的仓库路径；
- 实际使用的 Python/CadQuery/OCP 版本；
- 哪些命令真实运行过；
- 哪些检查只依赖历史记录，当前未重跑；
- `legal-second-screw.json` 和 `validation-failure.json` 是后续必须纳入实现测试的案例；
- 仍保留 STEP 字节 hash 不稳定、螺纹环形近似、多实体风险和 `reproducibility_partial`。

建议新增：

```text
agent-work/cad-validation/CAD-005-006/checkpoint-r2.md
agent-work/cad-validation/CAD-005-006/handoff_successor_check-r2.md
```

更新 `CODEX-REVIEW-REQUEST.md` 时只能修改该文件本身，不得顺手修改项目状态、规划、研究或数据库文件。

### 4. 修正实现计划，而不是提前实现完整编译器

计划必须从“4 类测试”修正为至少包含：

1. `legal-catalog-row.json`；
2. `legal-second-screw.json`；
3. `missing-bore.json` 或前置规则拒绝；
4. `rule-rejected-second-screw.json`；
5. `validation-failure.json`；
6. STEP 导出/回读失败；
7. IR 语义反例：错误 source commit、缺失节点输入、重复 ID、未来依赖、未登记公式、错误 `validation_result`。

本轮只修正计划和交接证据，不实现这些编译器测试本身。

## 四、明确保留的 CAD-005/006 实现约束

后续正式实现必须遵守，但本轮不要实现：

### 公式单位

应在正式实现前冻结为 typed unit contract：

- `half(x)` 保留单位；
- `add/subtract` 要求输入单位一致；
- `multiply` 首期只允许一个无量纲标量和一个长度量，结果为长度；
- 不允许用通用 `mm × mm` 规则掩盖单位错误；
- 公式注册表必须写明参数名、输入单位和输出单位。

### 坐标和 placement

必须按 IR-001 与 BenchCAD `part.py` 的证据实现：

```text
Workplane("XZ")
沿 Y 轴回转 360°
cutter 局部沿 +Z
绕 Y 轴 90°
按 radial_offset、axial 平移
绕 Z 轴按 angle_deg 旋转
```

不能把这些关系重新变成自由字符串，也不能由编译器自行猜测。

### 验证分层

```text
IR JSON/schema/semantic check
→ preflight 规则
→ build
→ post_geometry
→ STEP export
→ STEP readback
```

不能信任 `status=accepted` 字段而跳过语义检查，也不能把 STEP 导出成功当作几何合法。STEP 字节 hash 只能记录，不能作为唯一重复性判据。

## 五、严格文件范围

本轮只允许修改或新增：

```text
src/cad_compilation/**
tests/cad_compilation/**
agent-work/cad-validation/CAD-005-006/**
docs/WORKLOG.md（只追加一条 R2 checkpoint）
```

禁止修改：

```text
README.md
agent-work/README.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
docs/DECISIONS.md
docs/research/**
database/**
agent-work/data/**
agent-work/schema-rules/**
agent-work/typed-cad-ir/**
```

不得删除或重写已有 R1 checkpoint。发现前序提交包含无关文件时，只在 R2 交接报告中记录，不通过历史重写修复。

## 六、提交和验证要求

提交前必须运行：

```bash
python3 -m py_compile $(find src/cad_compilation -name '*.py' -print)
PYTHONPATH=src python3 -c "import cad_compilation"
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py
python3 tests/cad_compilation/test_handoff.py
git diff --check
```

如果某条命令因环境缺失无法运行，必须记录 `not_run` 或 `blocked` 及原因，不得写 PASS。

提交前执行：

```bash
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```

暂存时只能使用明确路径，例如：

```bash
git add src/cad_compilation tests/cad_compilation agent-work/cad-validation/CAD-005-006 docs/WORKLOG.md
```

如果 `docs/WORKLOG.md` 中存在其他 Agent 的未提交改动，不能直接整体暂存；应使用补丁方式只暂存自己的新增段落，或不提交该文件并在 checkpoint 说明原因。

提交信息使用：

```text
fix: repair CAD-005/006 handoff artifacts [CAD-005-006-R2]
```

提交前必须确认 staged diff 只包含本任务允许路径。不要把用户已有改动、项目迁移、数据库、研究文件或无关 README 放入提交。

## 七、最终交接格式

在 `checkpoint-r2.md` 中写明：

```text
task=CAD-005/006-R2
status=review | blocked
changed=<本轮实际修改的文件>
commit=<本轮 commit>
handoff_successor_check=<文件路径>
verified=<每条命令及真实结果>
import_status=pass | blocked
script_status=<仓库脚本路径及结果>
scope_check=<staged diff 是否仅包含允许路径>
known_limits=<尚未实现的编译器/验证器能力和环境限制>
next=Codex 中枢审查后，决定是否启动 CAD-005/006 正式实现
```

完成后状态只能是 `review` 或 `blocked`。不要标记 CAD-005/006 为 `done`，不要启动 DATA-004、LLM 或检索任务。
```
