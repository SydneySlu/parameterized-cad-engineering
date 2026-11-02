# DATA-003-R2：首族来源、快照与许可证边界补充审计 Prompt

请由刚刚完成 DATA-003 的原 Agent 继续执行本任务，使用原聊天框和当前项目工作区，不要重新分配陌生的数据 Agent。本轮任务只处理首期已冻结族 `set_screw_shaft_collar` 的来源、快照可复现性和许可证边界，不实现 Schema、Typed CAD IR、CAD 编译器、验证器、LLM、检索系统或大规模数据处理。

## 项目范围和当前决策

项目根目录：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = \
"/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

首期零件族已经由 ADR-0007 冻结，不要重新选择候选族：

```text
family_id: set_screw_shaft_collar
family_path: designs/set_screw_shaft_collar
repository: https://github.com/BenchCAD-org/benchcad-2
source_commit: 035f467142888edfd0bd7cd73906f9b155c8f43c
```

请先阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_PLAN.md`
- `docs/TASKS.md`
- `docs/DECISIONS.md`
- `docs/coordination/handoff-review-protocol.md`
- `agent-work/data/DATA-003-single-family-audit/checkpoint.md`
- `agent-work/data/DATA-003-single-family-audit/source-audit.md`
- `agent-work/data/DATA-003-single-family-audit/environment.md`
- `agent-work/data/DATA-003-single-family-audit/minimal-manifest.json`

不要 reset、clean、覆盖或提交其他 Agent 的未提交改动。所有正式文件只能写入：

```text
agent-work/data/DATA-003-single-family-audit/
docs/WORKLOG.md
```

外部 checkout、archive、解压源码、虚拟环境和临时 CAD 产物必须放在被忽略的 `work/benchcad-source/` 或 `work/benchcad-output/`，不得把大文件、第三方源码快照或生成 STEP 加入项目 Git。

## A. 来源与快照复核

确认以下事实仍然对应固定 commit：仓库 URL、commit、族路径、`family_id`、`part.py`、`spec.py`、`family.json`、`build()`、`check()` 和当前状态页记录。

优先尝试建立真正干净的固定 commit 快照：

1. 新建 ignored 目录，完整 clone/fetch 到 `035f467142888edfd0bd7cd73906f9b155c8f43c`；或
2. 在已有完整 Git checkout 中用 `git archive` 生成固定 commit 的 tar，再解压到 ignored 目录。

至少记录：

```bash
git rev-parse HEAD
git status --short --branch
git ls-tree -r --name-only HEAD | wc -l
shasum -a 256 <archive-or-snapshot>
```

关键文件必须存在并记录实际运行目录。若网络、promisor checkout 或服务限制导致无法获得完整 checkout/archive，不要伪造成功；继续使用现有 API/raw 快照，但在 `environment.md`、`checkpoint.md` 和 manifest 中明确：

```text
source_snapshot=reproducibility_partial
```

同时记录已覆盖的文件数量、每个文件的 commit/blob 证据（可获得时）、缺失原因以及后续补救方式。不得把 API/raw 快照写成官方 Git archive 或“完全可复现”。

## B. 许可证边界审计

建立或更新族级许可证矩阵，至少逐项区分：

1. BenchCAD 仓库代码、`designs/set_screw_shaft_collar` 源文件和框架代码；
2. BenchCAD 官方 released dataset artifacts；
3. 本项目运行生成的 STEP、渲染图和其他派生 CAD；
4. `NOTES.md` 中提到但未随仓库分发的标准图纸、产品图片、下载文件和外部链接；
5. BenchCAD Public/Core 评测资产。

当前已知边界必须保留并核对：

- 仓库 README/LICENSE 将源码和 designs 说明为 MIT；
- released dataset artifacts 另有 CC BY 4.0 说明，不能自动套用到本项目自行生成的 STEP；
- `set_screw_shaft_collar/NOTES.md` 提到的第三方标准图纸、SVG、照片不因存在引用就获得再发布许可；
- Public/Core 不进入本项目训练、检索或再发布语料；
- 在证据不足时使用 `license_scope_uncertain`，写出需要向上游确认的具体问题和可接受的项目内使用方式（例如仅本地实验、只发布代码/manifest、不发布第三方材料）。

不要凭仓库名称、文件扩展名或“开源”字样推断派生资产可以公开发布。不要复制第三方标准图纸、图片或下载文件到项目目录。

## C. 交付物

在原 DATA-003 工作区中追加或修订：

- `source-audit.md`：补充固定 commit、族路径和快照证据；
- `environment.md`：补充实际快照类型、文件数量、哈希、运行目录和失败原因；
- `license-matrix.md`：新增逐类资产、证据、允许用途、禁止用途、待确认事项和署名要求；
- `minimal-manifest.json`：保留审计草案性质，增加 `source_snapshot`、`license_scope` 和 `family_scope` 字段或等价记录；不得把它升级为正式 Schema/Typed CAD IR；
- `checkpoint.md`：追加本轮结果，不删除 DATA-003/R1 历史事实。

如修改 `docs/WORKLOG.md`，只追加一条 DATA-003-R2 记录，不改写其他 Agent 的历史记录。不要修改 `docs/DECISIONS.md`、`docs/PROJECT_STATUS.md` 或 `docs/TASKS.md`；首族冻结已经由 Codex 中枢完成，正式状态由中枢维护。

## D. 三层交接检查

本任务涉及数据来源、许可证和复现边界，必须执行定向 double check：

1. **开始前**：复跑上一轮至少一条核心命令，并检查一个正常族目录文件和一个失败/不完整快照情况；确认输入 commit、族 ID 与本任务一致。
2. **提交前自检**：记录修改内容、实际命令、结果、已确认事实、未解决问题和下一 Agent 重点。
3. **不要越权**：发现许可或快照证据不足时记录 `review`/`blocked`，不要用猜测填空，也不要修改项目范围来绕过问题。

## 验收格式

checkpoint 追加以下字段：

```text
task=DATA-003-R2
status=review | blocked | done
family_id=set_screw_shaft_collar
source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c
source_snapshot=full_checkout | git_archive | reproducibility_partial
changed=...
verified=...
license_scope=...
confirmed=...
unresolved=...
next=Codex 中枢复核来源、快照和许可证边界
```

完成后只提交本任务允许路径，并把 commit、checkpoint 路径和未解决事项发回中枢。不要宣称首族已经 `release-qualified`，不要宣称生成 STEP 可以公开再发布，也不要宣称快照完全可复现，除非有对应证据。
