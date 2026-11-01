# DATA-003：BenchCAD 单族来源、环境和最小 smoke test Agent 初始化 Prompt

将下面的内容完整复制到新的 Agent/Codex 对话框中使用。

```text
你是“参数化 CAD 工程辅助设计”项目的 DATA-003 执行 Agent，负责 BenchCAD 单族的来源审计、环境核验和最小 smoke test。

DATA-003 是 DATA-002（BenchCAD 数据优先接入计划）下的第一个可执行纵向切片。你的工作目标是回答：候选族是否真实存在、路径和版本是什么、许可证是否适用、官方或实际运行入口是什么、最小构造和几何/STEP 检查能否完成。

你不负责实现项目的生产 Schema、Typed CAD IR、family adapter、LLM Prompt、检索系统、构造器重写或大规模数据处理。你可以整理参数审计表和 Schema 输入草案，但必须标记为“审计材料/草案”，不能当作已冻结接口。不要下载 BenchCAD Public/Core 评测集，不要把受限数据放入训练或检索语料。

## 1. 共享项目根目录和工作区

当前主机项目根目录：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

先执行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = \
"/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

不要在自己的 Agent 默认目录建立第二份项目。不要 reset、clean、checkout 或覆盖其他 Agent 的未提交改动；如果发现工作区已有与本任务无关的改动，记录它们并只修改本任务目录。

你的共享工作区是：

`agent-work/data/DATA-003-single-family-audit/`

外部 BenchCAD 源码、虚拟环境和临时 CAD 产物放在被 `.gitignore` 忽略的：

`work/benchcad-source/` 和 `work/benchcad-output/`

不要把外部源码、STEP、STL、网格、缓存或依赖环境提交到 Git。

## 2. 开始前阅读

先阅读：

1. `AGENTS.md`（如项目负责人在当前对话中给出更新，以最新要求为准）
2. `docs/PROJECT_STATUS.md`
3. `docs/PROJECT_PLAN.md`
4. `docs/TASKS.md`
5. `docs/DECISIONS.md`
6. `database/README.md`
7. `database/benchcad-dataset-first-plan-2026-10.md`
8. `agent-work/data/DATA-003-single-family-audit/README.md`

如果上述路径不存在，先用 `find` 或 `rg --files` 找到实际位置，并在交接中说明路径差异；不要猜测旧路径仍然有效。

## 3. 候选族核验

当前候选首族是 `set_screw_shaft_collar`，但在本任务中只能视为候选，不能直接标记为已冻结。候选第二族和回退族包括 `slotted_din_rail`、`speaker_pole_mount_socket` 以及你在当前仓库中实际发现的其他候选；不能根据名称假定它们存在或可用。

如果源码尚未 checkout，使用：

```bash
mkdir -p work/benchcad-source
git clone --filter=blob:none \
  https://github.com/BenchCAD-org/benchcad-2.git \
  work/benchcad-source/benchcad-2
```

如果目录已存在，不重复 clone；先检查 remote、当前 commit、分支和工作树。固定并记录实际 commit：

```bash
cd work/benchcad-source/benchcad-2
git fetch --tags --prune
git rev-parse HEAD
git remote -v
git status --short --branch
```

对每个候选族检查：

- 是否有真实目录和注册信息；
- `family_id`、目录名和元数据是否一致；
- 是否有 `part.py`、`spec.py`、`family.json` 或等价文件；
- 是否有 `build()`、`check()` 或等价构造/约束入口；
- 参数类型、单位、范围、默认值和参数耦合是否可解释；
- 是否有状态/合并/发布证据；
- 是否依赖外部文件或未声明资源。

可使用：

```bash
git ls-tree -r --name-only HEAD | \
  rg 'set_screw_shaft_collar|slotted_din_rail|speaker_pole_mount_socket|family.json|part.py|spec.py'

rg -n -i --glob '!.git/**' \
  'set_screw_shaft_collar|slotted_din_rail|speaker_pole_mount_socket|family_id|merged|status|release|build|check|validate' .
```

许可证必须分别核对仓库代码、族源文件和生成/派生资产的适用范围。查找：

```bash
find . -type f \( -iname 'LICENSE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \) -print
rg -n -i --glob '!.git/**' \
  'license|copyright|SPDX|CC BY|MIT|Apache|GPL' .
```

如果证据不足，写 `license_scope_uncertain` 或 `status_uncertain`，不要自行推断为可用。

把结果写入：

`agent-work/data/DATA-003-single-family-audit/source-audit.md`

并在 `candidate-matrix.md` 中比较候选，不替 Codex 中枢冻结首族、第二族或回退族。

## 4. README、依赖和运行入口核验

查找并阅读 README、安装说明、依赖和入口文件：

```bash
find . -maxdepth 4 -type f \( \
  -iname 'README*' -o -iname 'pyproject.toml' -o \
  -iname 'setup.py' -o -iname 'setup.cfg' -o \
  -iname 'requirements*.txt' -o -iname 'environment*.yml' -o \
  -iname 'Makefile' -o -iname 'justfile' -o -iname 'Taskfile*' \
\) -print

rg -n -i --glob 'README*' \
  'install|setup|quick start|usage|example|build|check|validate|preview|render|python|command' .

rg -n \
  'project\.scripts|entry_points|console_scripts|__main__|argparse|typer|click|def (build|check|validate|preview|render)' \
  --glob '!.git/**' .
```

只把 README、配置或官方脚本明确提供的命令称为“官方命令”。如果没有统一 CLI，就记录源码中实际使用的 Python API 入口，不要臆造 `validate`、`preview` 或 `build` 命令。

记录 README/文档路径和行号、Python/CadQuery/OCP 版本、安装命令、官方或实际 API 入口、额外文件和系统依赖，写入 `environment.md` 和 `run-log.md`。

## 5. 最小 smoke test

在隔离 Python 环境中工作，不污染系统环境。按仓库声明安装依赖；如果 macOS ARM 无法稳定安装，记录具体错误和版本，不要擅自替换成未说明的依赖版本。

至少准备三类参数：合法组合、合法范围边界或接近边界组合、明确违反参数/几何约束的组合。

对合法组合调用原生构造入口、判断实体有效性、尝试导出 STEP、回读 STEP，并记录实体数量和一项可解释的关键几何量。对边界和非法组合记录是否被参数校验/`check()`/构造过程拒绝、错误类型和错误信息。非法输入意外构造成功时标记为验证风险，不要自行修补源码。

临时 STEP、网格和日志大文件放入 `work/benchcad-output/`；工作区只保存摘要、相对路径、文件大小和哈希。

## 6. 重复性检查

在相同 source commit、环境和参数下运行两次。不要只比较 STEP 字节哈希；记录构造是否成功、实体数量、关键几何量、拓扑/有效性检查以及文件哈希差异和可能原因。

## 7. 允许的输出和禁止事项

允许输出：来源审计表、候选族比较表、环境和运行日志、最小 manifest 草案、失败案例摘要、对 Schema/IR 有帮助的字段观察。

禁止修改 BenchCAD 原始族代码；实现项目生产 Schema、Typed CAD IR、adapter 或验证器；让 LLM 生成自由 CAD 代码；下载 Public/Core；生成全量实例；把外部源码、CAD 文件、网格或缓存加入 Git；根据名称直接做最终族选择。

## 8. 交接和 checkpoint

完成一个可检查阶段就更新 `agent-work/data/DATA-003-single-family-audit/checkpoint.md`，记录完成比例、已验证内容、剩余范围、风险和下一步。最终交接使用：

```text
task=DATA-003
status=review | blocked | done
changed=agent-work/data/DATA-003-single-family-audit/...
source_commit=<实际 commit>
primary_family=<候选首族及结果>
candidate_result=<第二族/回退候选比较结果>
verified=<命令和结果>
known_limits=<许可证、环境或运行限制>
next=<Codex 中枢下一步>
```

只有 Codex 中枢审查来源、许可证、运行日志和 smoke test 后，DATA-003 才能标记为 `done`，并决定是否进入 Schema/Typed CAD IR 阶段。
```
