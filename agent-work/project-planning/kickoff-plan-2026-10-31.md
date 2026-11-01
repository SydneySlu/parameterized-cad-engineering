# 项目启动计划：单族来源审计与最小核验

- 日期：2026-10-31
- 任务：PLAN-001
- 性质：规划草案，待项目负责人确认后交由 Codex 中枢拆分正式任务
- 目标：以一个 BenchCAD 2.0 社区参数化零件族作为首个纵向切片，建立从来源、环境、参数规格到最小 CAD 验证的可追溯起点。

## 1. 是否适合作为项目起点

适合。它能同时验证数据来源、运行环境、参数 Schema 输入、Typed CAD IR 所需字段、原生 `build()` 调用和项目侧验证边界，风险低于先做大规模数据整理或先优化 Prompt。

本计划不要求下载 BenchCAD 全量数据集，也不使用 Public/Core 评测集作为训练或检索语料。首轮只核验社区仓库中的一个具体族及其运行所需的最小根目录文件。

## 2. 首轮对象（项目负责人已确认首族，第二族仍待确认）

项目负责人已确认首个纵向切片采用：`set_screw_shaft_collar`。

选择依据：参数关系集中在轴孔、外径和径向紧定螺钉，既有可检查的几何特征，也有参数耦合，适合作为第一条纵向切片。

第二个族暂建议采用：`slotted_din_rail`。

选择依据：长尺寸、重复槽、槽数/槽距关系与第一族结构差异明显，可用于检验 family adapter 和 IR 的跨族边界。

第二个族仍需后续确认。首族虽然已由项目负责人确认，但正式执行前仍必须以当前 BenchCAD 仓库的实际目录、状态、许可证、依赖和运行结果完成核验；如果首个族在当前版本无法稳定运行，应记录阻塞并评估是否退回 `speaker_pole_mount_socket`。本节的范围确认先写入 kickoff plan，正式项目状态和 ADR 由 Codex 中枢同步。

## 3. 数据源和下载边界

### 主数据源

- 来源仓库：`https://github.com/BenchCAD-org/benchcad-2.git`
- 使用资产：仓库中的社区族源文件及其生成/验证工具。
- 首轮需要：目标族目录、运行所需的仓库根目录配置、许可证、依赖文件和官方命令。
- 首轮不需要：BenchCAD Public/Core、完整公开评测集、全量族实例、大批量 STEP/网格/渲染文件。

### 下载路径

项目负责人已确认外部源代码放在项目根目录下的忽略目录：

```text
/Users/syd/Desktop/参数化 cad 工程辅助设计/work/benchcad-source/benchcad-2
```

`work/` 已在项目 `.gitignore` 中忽略，适合放外部 checkout、依赖缓存和临时构造产物。项目正式记录只保存来源 URL、commit、族路径、许可证、命令、manifest 和摘要，不把外部仓库副本提交到项目 Git。

下载前必须先确认路径：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
mkdir -p work/benchcad-source
git clone --filter=blob:none https://github.com/BenchCAD-org/benchcad-2.git work/benchcad-source/benchcad-2
cd work/benchcad-source/benchcad-2
git rev-parse --show-toplevel
git remote -v
git status --short --branch
```

如果仓库已存在，不重复 clone；先检查 remote、当前分支和工作树，再获取并固定 commit。目标族核验完成后使用 detached HEAD 或只读 checkout，避免在外部源仓库产生未记录修改。

## 4. 分阶段实施

### 阶段 0：启动前确认

输入：项目负责人对数据源和候选族的确认。

动作：确认是否采用 BenchCAD 社区族、是否接受“先一族再第二族”、首轮是否只做参数化工程零件生成；记录候选族和回退族。

输出：启动边界记录、候选族列表、未决问题。

通过条件：不再把 Public/Core 或其他未授权数据当作首轮输入。

### 阶段 1：来源和版本核验

动作：读取仓库 README、LICENSE、状态/设计说明、依赖文件和官方运行说明；列出目标族目录；固定 commit；记录族状态和许可适用范围。

输出：来源审计表，至少包含：

```text
source_url
source_commit
family_id
family_path
repository_license
family_status
source_evidence
dependency_files
official_run_command
```

通过条件：别人可以按记录定位到相同源代码和相同族目录。

### 阶段 2：环境准备和只读 smoke test

动作：在隔离 Python 环境中按仓库声明安装依赖；记录操作系统、CPU 架构、Python、CadQuery/OCP 和其他关键版本；先运行官方最小 validate/preview/build 命令。

输出：环境记录、命令记录、首次运行日志。

通过条件：不修改 BenchCAD 原始族代码即可读取参数规格，并完成一次官方构造或验证入口调用。

### 阶段 3：族级参数和约束审计

动作：对照 `part.py`、`spec.py`、`family.json` 和等价的 `check()`/约束入口，记录 `build()` 参数、类型、单位、范围、离散选项、默认值、参数耦合、错误文案和实体数量约定；检查是否有随机采样或外部文件依赖。

输出：项目侧族审计表和 Schema 草案，不写生产 Schema 实现。

通过条件：`build()` 参数与参数规格可以逐项对应；关键约束和来源可解释；明确哪些字段来自用户、推导或 sampler。

### 阶段 4：最小构造、导出和回读

动作：准备三类参数：一个明确合法组合、一个边界组合、一个违反约束组合。分别调用原生构造/检查入口；对合法实例导出 STEP 并回读；记录实体数量、有效性和至少一项关键几何量。

输出：少量临时 CAD 产物（保存在 `work/` 或 `artifacts/generated/`，不提交）、验证日志和最小 manifest。

通过条件：合法输入可构造并导出；非法输入被拒绝或明确标记；STEP 可回读；错误分类可记录。

### 阶段 5：确定性和交接

动作：相同 commit、环境和参数重复运行两次；比较几何/拓扑结果，不以 STEP 字节哈希作为唯一依据；保存命令、参数、版本、结果和文件哈希。

输出：来源审计包、环境记录、最小 manifest、运行日志、失败案例摘要和下一阶段建议。

通过条件：结果在允许的文件元数据差异之外保持几何一致，且交接材料足以供 Schema/IR Agent 使用。

## 5. 软件和机器安排

### MacBook Air M5 16GB/512GB

建议作为首选启动机器，用于 Git checkout、源码阅读、环境安装、少量构造、STEP 回读、Schema/IR 草案和日志整理。首轮不需要大容量数据，也不需要同时保存大量渲染结果。

关键风险是 macOS ARM 与 CadQuery/OCP 依赖兼容性，因此阶段 2 应尽早验证；不能预先保证兼容，必须以实际安装和最小命令结果为准。

### Windows + 1TB 外置硬盘

首轮不是前置条件。可作为后续批量实例、渲染、STEP/网格缓存和环境对照机。若 Mac ARM 依赖无法稳定运行，或生成产物超过 512GB 可用空间，再把 Windows 纳入主运行路径。

外置硬盘中的大文件不作为 Git 事实源；用 manifest 记录设备、路径、源 commit、生成命令和哈希。两台机器之间同步代码和配置，避免直接复制未说明的生成物。

### 必需软件类别

- Git：获取并固定源仓库 commit。
- Python：版本以 BenchCAD 仓库声明为准，使用隔离虚拟环境。
- BenchCAD 声明的 CadQuery/OCP 及其依赖：不自行猜测版本。
- 基础 shell 工具：用于路径、版本和日志核验。
- STEP/CAD 查看或回读工具：优先使用项目/BenchCAD 已声明的工具链；若需额外软件，先记录版本和用途。

## 6. 项目负责人和 Agent 分工

### 项目负责人

- 确认数据源是否就是 BenchCAD 社区族。
- 在候选族中确认首个族、第二族和回退策略。
- 决定是否允许外部源代码 checkout 到 `work/`，以及最终可公开资产边界。
- 提供或确认 Mac 的系统权限、磁盘空间和是否可使用 Windows/外置硬盘。
- 对许可证解释、首期范围和验收门做最终裁决。

### PLAN-001 总体规划 Agent

- 维护本启动计划、讨论记录、待决问题和 checkpoint。
- 把用户确认转成供 Codex 中枢审查的范围建议和任务依赖。
- 不直接编写生产代码、验证器、数据处理脚本或 Prompt 实现。
- 不把未运行的计划写成已完成事实。

### Codex 中枢

- 审查首期族和范围是否需要 ADR。
- 把阶段 1–5 拆成正式任务并指定执行 Agent。
- 冻结 Schema/IR 接口和验收标准后，再允许 CC/DSH 实现。

### CC / CAD 执行 Agent

- 在接口冻结后负责环境适配、构造器包装、STEP 回读和验证实现。
- 发现原生族无法表达需求时提交阻塞或变更建议，不自行改变 IR 语义。

### DSH / 数据 Agent

- 在来源边界确认后负责只读族级 manifest、参数实例清单、去重和样本记录。
- 不下载或整理受限 Public/Core，不自行扩大族范围。

## 7. 首轮验收清单

```text
[ ] 项目根目录和外部 checkout 路径核对通过
[ ] source URL、commit、family_id、族路径已固定
[ ] LICENSE、族状态和来源证据已记录
[ ] 依赖版本和官方运行命令已记录
[ ] Mac ARM 环境或 Windows 回退环境完成最小运行判断
[ ] build() 与 spec/PARAM_SPEC 字段逐项对应
[ ] 合法参数可构造
[ ] 边界参数结果已记录
[ ] 非法参数被拒绝或错误可解释
[ ] STEP 可导出并回读
[ ] 重复运行的几何结果一致
[ ] manifest、运行日志和失败案例摘要已保存
[ ] Codex 中枢审查是否进入 Schema/IR 阶段
```

## 8. 明确不在本启动阶段做的事

- 不下载 BenchCAD Public/Core。
- 不下载或生成全量族实例。
- 不把 BenchCAD 原生构造器重写成新构造器。
- 不让 LLM 直接生成自由 CadQuery 代码。
- 不在接口未冻结前批量制作检索库或自然语言 benchmark。
- 不把外部源码、STEP、网格或缓存直接提交到项目 Git。

## 9. 启动后的下一道决策门

只有阶段 1–5 通过，才进入：

```text
族级 Schema v0
→ Typed CAD IR v0
→ family adapter
→ 第二族复核
→ 小样本 manifest 与任务集
→ LLM/检索对照
```

