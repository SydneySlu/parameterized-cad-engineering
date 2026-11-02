# 工作日志

本文件只追加。每次工作完成后记录实际动作、结果、验证和下一步；聊天中的口头进展不作为唯一记录。

## 2026-10-28

### INFRA-001 / Codex / done

- 动作：检查工作区并初始化项目协作基础，建立 `AGENTS.md`、状态页、计划页、任务看板、决策记录和 `.gitignore`。
- 结果：仓库内形成统一入口；所有 Agent 可按同一协议读取当前状态和认领任务。
- 验证：文件结构检查通过；待 Git 首次提交。
- 下一步：配置远程仓库并验证跨设备同步（INFRA-003）。

### INFRA-002 / Codex / done

- 动作：比较 `profile-pack` 与仓库内项目管理协议。
- 结果：确认 `profile-pack` 适合作为本机 Agent 上下文/决策辅助层；Git 文档与提交历史作为项目事实源。
- 依据：Profile Pack README 和 `docs/evaluation/decision-layer.md`，其 Project Profile 与决策日志是 local-only MVP，未提供远程多用户同步。
- 下一步：远程仓库配置后，再决定是否在各 Agent 主机接入 Profile Pack。

### INFRA-003 / Codex / blocked

- 动作：初始化本地 Git 仓库并完成首个可审查提交。
- 结果：commit `ece00b0`（`docs: establish cross-agent project foundation [INFRA-001]`）；仓库当前分支为 `main`，尚未绑定远程。
- 验证：`git status --short --branch` 显示工作区干净；已检查暂存内容，未纳入论文原始缓存和生成渲染物。
- 阻塞：尚未提供 GitHub/GitLab 仓库 URL 或远程访问方式。
- 下一步：绑定远程后执行首次 `push -u origin main`，并在另一设备做 clone/pull 验证。

### INFRA-004 / Codex / done

- 动作：增加 `docs/coordination/agent-bootstrap.md` 和 `CONTRIBUTING.md`，明确 Codex、CC、DSH 的职责、启动提示和交接格式。
- 结果：新聊天框或新设备只需读取仓库文件即可获得相同协作协议；不依赖某个聊天框保留上下文。
- 验证：文档链接和任务 ID 与 `AGENTS.md`、`docs/TASKS.md` 一致。
- 下一步：远程仓库配置后，把同一套启动协议提供给每个 Agent 的宿主配置。

### INFRA-005 / Codex / done

- 动作：增加中枢编排协议、复杂任务 checkpoint 规范和 `scripts/check_project_state.py` 仓库体检脚本。
- 结果：复杂任务可以分阶段同步；Codex 中枢负责生成 Agent 初始化 prompt、检查依赖和审查阶段性结果。
- 验证：运行 `python3 scripts/check_project_state.py`，通过；当前唯一仓库警告是尚未配置远程。
- commit：`0e75325`（`docs: add checkpoint orchestration and repo checks [INFRA-005]`）。
- 下一步：后续每个实现任务按 checkpoint 方式推进，阶段结果先进入 `review`，合并后再标记 `done`。

### INFRA-006 / Codex / done

- 动作：建立仓库外的本地中枢审查台账，并明确私有台账、共享事实源和独立复核对话框的边界。
- 结果：任务分派、prompt 摘要、checkpoint、审查问题和修正 commit 可集中追踪；项目共享事实仍以 Git 为准。台账路径为本地用户数据目录，不纳入仓库。
- 验证：确认台账文件权限为仅当前用户读写；运行仓库体检和 `git diff --check`。
- 下一步：每次分派、checkpoint、审查和修正时更新台账；重要结论按需发起另一个 Codex 对话框的独立复核。

## 2026-11-01

### CAD-005/006-R1 / CAD 执行 Agent / in_progress

**第一阶段：三层交接检查（完成）**

- 动作：
  1. 阅读 AGENTS.md、PROJECT_STATUS.md、PROJECT_PLAN.md、TASKS.md、DECISIONS.md、coordination/handoff-review-protocol.md
  2. 读取前序任务 DATA-003、CAD-003、IR-001 的 checkpoint 和代码
  3. 执行第二层定向复核：复跑 DATA-003 smoke 命令，验证 4 个案例（合法、边界、约束非法、几何非法）
  4. 设置开发环境：CadQuery 2.3.0 + OCP 7.9.3.0 + Python 3.10
  5. 理解 IR v0 结构：节点类型、表达式类型、公式集合、验证指标

- 结果：
  - ✓ 第二层复核 PASS：spec.check() 和 part.build() 均可调用，所有测试案例行为符合预期
  - ✓ 前序接口完整：CAD-003 参数规则、约束集合、构造器 API 均冻结
  - ✓ 环境配置完成：依赖已安装，BenchCAD 源快照（benchcad-2-035f467-raw）存在完整
  - ✓ IR 结构理解完成：5 节点类型、5 表达式类型、11 公式、错误分层

- 验证：
  ```bash
  cd work/benchcad-source/benchcad-2-035f467-raw && \
    PYTHONPATH=.:./framework python3 /mnt/outputs/test_handoff.py
  # 输出：✓ 4 个测试 PASS
  ```

- 交接记录：
  - `agent-work/cad-validation/CAD-005-006/handoff_successor_check.md`（第二层复核记录）
  - `agent-work/cad-validation/CAD-005-006/checkpoint.md`（当前 R1 checkpoint）

**第二阶段：编译器架构设计（启动）**

- 动作：
  1. 分析 IR v0 示例（legal-catalog-row.json 等）
  2. 设计模块化架构：解析层、验证层、编译层、验证层
  3. 建立 src/cad_compilation/ 目录和模块框架
  4. 记录关键发现、决策点和风险

- 关键发现：
  1. **验证必须分层**（DATA-003 证明）
     - preflight: 约束检查（绝不能跳过）
     - build: CadQuery 构造
     - post_geometry: 实体数、有效性、几何摘要
     - step_readback: STEP 往返验证
  2. **多实体风险**：outer_d < bore_d 时 build() 产生 3 solids，STEP 导出成功，但属于非法结果
  3. **STEP 不稳定**：字节 hash 不同但几何摘要相同 → 必须使用结构化摘要，不用字节 hash 判定
  4. **螺纹模型限制**：thread_model=revolved_ring_approximation，M3-M8 可能 no-op

- 待确认的决策点（交给中枢）：
  1. 公式参数的单位推导规则
  2. 回转轴定义和轮廓绘制方向
  3. 置放（placement）模型的坐标系统一性

- 已知限制：
  - 仅支持 set_screw_shaft_collar（首族）
  - STEP 字节 hash 不稳定，不作重复性标准
  - 螺纹为环形近似，不是真实螺旋
  - Source snapshot reproducibility_partial

- 下一步：
  1. 实现 IR 解析、语义检查、公式求值（4-6 h）
  2. 实现 CadQuery 操作映射（4 h）
  3. 实现几何/STEP 验证（2-3 h）
  4. 编写测试和运行日志（2 h）
  5. 交接给中枢审查（review 状态）

### INFRA-007 / Codex / done

- 动作：围绕轻量版架构规划数据、LLM、Schema/规则、Typed CAD IR 设计、CAD 执行/验证和集成审查的 Agent 分工与依赖；暂不生成初始化 prompt。
- 结果：明确 Codex 负责接口、范围、审查和 IR 设计，CC 负责 Schema/规则及 CAD 执行实现，数据 Agent 负责来源和样本，LLM Agent 负责 Prompt/结构化抽取/检索接入；Typed CAD IR 与验证器共用版本化接口。
- 验证：检查计划、任务看板和协调文档中的任务 ID、依赖和验收条件；待正式认领后再建立具体 Agent prompt。
- 下一步：确认首期零件族、实际对话框/分支名称和评测阈值，再生成逐 Agent 初始化 prompt。


### DATA-001 / Codex / review

- 动作：比较 BenchCAD 2.0 社区族/公开评测集、CADBench（附件论文 arXiv:2605.10873v2）和 Seek-CAD 的目标、数据结构、轻量版适配度、规模与许可边界；研究报告现位于 `database/cad-dataset-suitability-2026-10.md`。
- 结果：建议 BenchCAD 2.0 作为主数据源候选，因为其参数、来源范围、约束和确定性 CadQuery 几何与项目主线接近；CADBench 作为多模态几何重建/外部评测参考；Seek-CAD 作为特征序列及检索方法参考。尚未冻结数据集或零件族。
- 验证：查阅附件论文第 1、3、4 节及附录 D；核对三个项目的作者 README、BenchCAD 2.0 博客/仓库设计规范和 CADBench Hugging Face 数据卡。未下载完整数据集或运行样本。
- 许可边界：BenchCAD 2.0 README 区分 MIT 代码/设计与 CC BY 4.0 数据制品；CADBench 按源数据混合许可；Seek-CAD 仓库代码 MIT，但 README 未单列数据许可。
- 下一步：导师/项目负责人确认主数据源候选与零件族方向后，开展已合并 BenchCAD 家族和候选族覆盖的样本级审查（DATA-002）；再冻结首期零件族。

### DATA-001 / Codex / review / 2026-10-28 checkpoint

- 动作：补充核对 BenchCAD 2.0 GitHub 设计接口、当前状态页、评审规范、官方博客及 Hugging Face Public/Core 数据卡；研究报告现位于 `database/benchcad-2-deep-dive-2026-10.md`。
- 结果：明确区分社区参数化零件族与 Public/Core 工程任务评测集；整理 `part.py`、`spec.py`、`family.json` 及 `PARAM_SPEC`、`check()`、`refine()` 的字段语义；核对当前状态页为 4/150 个族已合并；对三个候选零件族给出匹配和延伸估算。
- 关键风险：Public/Core 当前数据卡明确禁止训练、微调、蒸馏、RL 环境、检索/搜索语料和再发布，因此只能作为外部评测/任务设计参考；不能按原始评估集接入轻量版检索或训练管线。
- 验证：官方页面与仓库原文核对；`git diff --check` 通过；未下载 gated Public/Core 内容，也未将其文件写入仓库。
- 下一步：导师确认首期目标族后，执行 DATA-002：选定一个已合并族或仿照其接口新增一个来源可追溯族，建立项目 manifest 与 Typed CAD IR 映射。

### DATA-002 / Codex / in_progress / 2026-10-29 checkpoint

- 动作：根据用户转述的导师意见，将数据策略调整为 BenchCAD 社区参数化族优先；计划现位于 `database/benchcad-dataset-first-plan-2026-10.md`，并在 `docs/DECISIONS.md` 记录 ADR-0005 proposed；同步更新项目状态、计划和任务看板。
- 结果：建议把当前可用的 BenchCAD 社区族作为覆盖目标，先以两个结构不同的族完成 smoke test，随后扩展其余可用族；主要增量工作改为跨族 manifest/Typed CAD IR adapter、自然语言缺失/冲突任务、检索对照和逐族几何验证。没有冻结最终族数或新增垂直领域。
- 许可/状态边界：GitHub 社区族与 Public/Core 评测集分开；Public/Core 当前条款禁止作为训练、检索语料或 RL 环境。已核验状态页报告 4/150 merged、0 release-qualified（状态页标注 2026-08-02），实施前须再次锁定具体 commit 和族状态。
- 验证：待运行仓库体检、diff 检查；未下载评测 gated 内容，也未复制外部 CAD 文件。
- 提交：`29ee4bd`（`docs: plan BenchCAD dataset-first project scope [DATA-002]`）。
- 下一步：用户/导师确认目标是全部当前可用族，还是阶段一达到两个族即可；之后完成族级来源、版本、许可证和环境审查。

### INFRA-008 / Codex / done / 2026-10-29

- 动作：将整个 Git 仓库（含 `.git` 历史）从旧工作路径迁移到 `/Users/syd/Desktop/参数化 cad 工程辅助设计`；建立 `agent-work/` 及数据、LLM、Schema/规则、Typed CAD IR、CAD 验证、集成、审查和待分拣子目录；更新 Agent 启动规则和路径说明。
- 结果：当前主机有单一共享项目基座；后续 Agent 不应在自己的默认目录创建项目副本。源代码、测试和正式文档仍分别进入 `src/`、`tests/` 和 `docs/`。
- 验证：迁移后 `git status --short --branch` 显示 `main` 且工作区无迁移丢失；目标目录存在 `.git`；待提交前运行仓库体检和 `git diff --check`。
- 下一步：后续生成各 Agent prompt 时写入目标根目录和职责子目录；跨设备使用时以当地 clone 的 Git 根目录为准。

### INFRA-003 / 用户 + Codex / review / 2026-10-29 checkpoint

- 动作：配置 GitHub 远程仓库 `https://github.com/SydneySlu/parameterized-cad-engineering.git`，使用 GitHub CLI 的 HTTPS 登录方式完成本机 `main` 首次推送。
- 结果：本地 `main` 已跟踪 `origin/main`；当前工作区干净，远程 fetch/push 地址一致。
- 验证：`git remote -v`、`git branch -vv` 和 `git status --short --branch` 显示 `origin/main` 跟踪关系；当前本地 HEAD 与远程跟踪分支均为 `c296387`。
- 限制：尚未在第二台设备执行实际 clone/pull，因此任务先标记为 `review`，不是完全 `done`。
- 下一步：在另一设备 clone 仓库并完成一次 pull/branch 检查；通过后将 INFRA-003 标记为 `done`。
### INFRA-009 / Codex / done / 2026-10-29

- 动作：按项目负责人要求，将数据集比较、BenchCAD 深入分析和 BenchCAD 优先计划统一迁入 `database/`；新增目录入口和后续更新约定，更新项目文档链接。
- 结果：`database/README.md` 成为数据集计划与讨论入口；今后此类结论在该目录更新，项目范围变化仍同步到决策与状态文档。
- 验证：核对 Git remote 为 `https://github.com/SydneySlu/parameterized-cad-engineering.git`；无需修改 remote；待执行文档体检和 diff 检查。
- 下一步：继续按 `database/README.md` 约定维护数据集相关计划和讨论。
### DATA-003 / Codex / planned / 2026-11-01

- 动作：注册 BenchCAD 单族来源、环境和最小 smoke test 执行任务；建立专用工作区和可复制的 Agent 初始化 Prompt。
- 结果：任务边界限定为来源 URL/commit、族路径/状态/许可证、README/依赖/运行入口、候选族矩阵和一个候选族的合法/边界/非法/重复运行核验；不包含 Schema、Typed CAD IR、adapter、LLM 或大规模数据处理。
- 工作区：`agent-work/data/DATA-003-single-family-audit/`；外部 checkout 和临时 CAD 产物放被忽略的 `work/benchcad-source/`、`work/benchcad-output/`。
- Prompt：`docs/coordination/prompts/DATA-003-single-family-audit-agent.md`。
- 下一步：项目负责人在新对话框启动 Prompt；执行 Agent 完成 checkpoint 后由 Codex 中枢审查并决定是否进入 Schema/IR 阶段。
### DATA-003 / Codex / review / 2026-11-01 checkpoint

- 动作：固定 BenchCAD `035f467142888edfd0bd7cd73906f9b155c8f43c`，核对三个候选族、README/pyproject/LICENSE/STATUS、官方 CLI 与原生 API；在 macOS arm64 的 Python 3.11.18 隔离环境安装 CadQuery/OCP 依赖。
- 结果：`set_screw_shaft_collar`、`slotted_din_rail`、`speaker_pole_mount_socket` 均真实存在且 `bench2 validate --seeds 1` PASS；完成首族合法、边界、非法和重复运行 STEP smoke，并生成来源审计、候选矩阵、环境、运行日志、manifest 草案和 checkpoint。
- 关键风险：非法参数被 `check()` 拒绝但原生 build 仍可能成功；`outer_d < bore_d` 例产生 3 solids；相同参数的 STEP 字节哈希不同但几何指标稳定；状态仅 MERGED、无 release-qualified，生成资产和第三方参考材料许可证需保留不确定标记。
- 工作区：`agent-work/data/DATA-003-single-family-audit/`；源码快照和 CAD/venv 均在被忽略的 `work/benchcad-source/`、`work/benchcad-output/`，未下载 Public/Core。
- 下一步：由 Codex 中枢审查来源/许可证/运行日志，决定是否补做第二族完整 STEP smoke，并决定是否进入 Schema/Typed CAD IR 阶段；本 checkpoint 不冻结族或接口。

### DATA-003-R1 / Codex / planned / 2026-11-01

- 动作：根据 DATA-003 审查，给原 DATA-003 Agent 分配复现性补充：建立干净 source commit 快照，并为重复 STEP 运行补充几何/拓扑签名。
- 边界：继续使用 `agent-work/data/DATA-003-single-family-audit/`；不实现 Schema、Typed CAD IR、adapter、生产验证器、LLM 或检索系统；不修改正式状态和 ADR。
- Prompt：`docs/coordination/prompts/DATA-003-R1-reproducibility-followup.md`。
- 下一步：项目负责人将该 Prompt 发回原 DATA-003 对话框；完成后由 Codex 审查并决定 DATA-003 是否可转为 done。

### CAD-003 / Codex / review / 2026-11-01 checkpoint

- 动作：依据 DATA-003 固定 commit 和审计证据，定义 `set_screw_shaft_collar.v0` 的字段元数据、目录行耦合、单位归一化、来源 provenance、缺失行为、前置规则和结构化错误码；实现纯 Python Schema 边界与 JSON 往返接口。
- 结果：`bore_d` 是唯一必填目录选择器；其余目录字段缺失时按证据派生，显式冲突拒绝；`second_screw`、壁厚、宽度和 `outer_d > bore_d` 在未来构造前拒绝。未引入 CadQuery/OCP、Typed CAD IR、STEP 或第二族字段。
- 验证：`python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`（13 项通过）；`python3 -m py_compile src/schema/set_screw_shaft_collar.py src/schema/__init__.py`（通过）；`git diff --check`（通过）。
- 交接：`agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md`；等待中枢审查字段来源、错误码和 Schema→IR 只读接口后再进入 IR-001。

### IR-001 / Codex / review / 2026-11-01

- 动作：依据 CAD-003 `set_screw_shaft_collar.v0` review 契约和 DATA-003 固定 source commit，设计 Typed CAD IR v0 的版本/来源包络、参数 provenance、节点白名单、声明式引用、依赖顺序、前置约束、后置几何/STEP 验证契约和稳定错误阶段。
- 结果：新增 `agent-work/typed-cad-ir/IR-001-v0/`，包含规范正文、JSON Schema、Schema→IR 映射和合法/缺失/规则拒绝/验证失败四个 JSON 示例。规范明确要求 `check()`/前置规则先于 `build()`，保留 `second_screw`、目录派生、`screw_len` 非孔深、环形线程近似、`reproducibility_partial` 和 STEP 字节 hash 不稳定等限制；第二族仅保留扩展边界。
- 验证：`python3 -m json.tool agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json` 通过；四个示例均通过 `python3 -m json.tool`；临时结构检查确认 accepted 示例含六个参数和节点、rejected 示例不含可执行节点；`git diff --check` 通过。仓库未安装第三方 `jsonschema`，因此未声称执行完整 JSON Schema 引擎验证。
- 限制：未修改 `src/`，未实现编译器、CadQuery/OCP 构造器、实体/STEP 验证器；CAD-006 的容差和摘要算法、线程近似是否可接受、第二族扩展注册表和生成资产许可仍待审查。
- 下一步：Codex 中枢审查 IR v0 后，再交给 CAD-005/006；在此之前 CC 不应按本目录接口开始生产实现。

### IR-001-R1 / Codex / review / 2026-11-01

- 动作：根据 Codex 中枢审查收紧 Typed CAD IR v0 的状态互斥、首族快照状态、孔节点几何输入、自由字符串边界和反序列化语义检查；未修改生产代码或 CAD-003/DATA-003 文件。
- 结果：`status=rejected` 现在必须是 errors-only 且 nodes 为空；`status=accepted` 禁止顶层 errors、允许后置 validation_result；当前适配器只接受 `reproducibility_partial`。主孔/第二孔均显式表达 wall、hole_len、z_in、z_out、radial_offset、axial、over、angle 和结构化 placement；新增 semantic-validation.md 记录唯一性、ordinal、依赖、引用、条件和白名单检查。
- 验证：临时隔离环境 `/tmp/ir001r1-jsonschema-venv` 的 Draft 2020-12 `jsonschema` self-check 和四示例验证通过；`python3 -m json.tool` 通过；临时语义脚本确认 10 个正/反例结果；`git diff --check` 通过。JSON 语法检查未被冒充为完整 Schema 验证。
- 限制：CAD-005 仍需冻结公式参数/单位/容差注册表；CAD-006 仍需冻结几何摘要容差；环形线程近似、STEP 字节 hash 不稳定、源码/外部资产 `reproducibility_partial` 和许可证不确定性均保留。
- 下一步：Codex 中枢复核本轮契约后，再交给 CAD-005/006。

### IR-001-R2 / Codex / review / 2026-11-02

- 动作：根据中枢最终小范围审查，固定 IR v0 的 BenchCAD source commit，按 node type 收紧五类首族节点契约，统一 validation_result 一致性和 accepted 参数序列化顺序；新增 `legal-second-screw.json` 与节点语义责任说明。
- 结果：Schema 现在拒绝错误 source commit、缺失节点核心输入、错误输出/properties、参数乱序和不一致 validation_result；语义检查补充 `IR_SOURCE_COMMIT_MISMATCH`、`IR_NODE_*`、`IR_VALIDATION_RESULT_ERRORS_INCONSISTENT`、`IR_VALIDATION_STAGE_MISMATCH`、`IR_PARAMETER_ORDER_MISMATCH`、`IR_SECOND_SCREW_CONSTRAINT` 等边界。`second_screw=1` 示例只声明 IR 结构合法，不声称几何运行成功。
- 验证：临时 `/tmp/ir001r1-jsonschema-venv` 的 Draft 2020-12 `Draft202012Validator.check_schema` 通过；5 个示例全部 Schema+语义通过；12 个指定反例按预期被拒绝；`python3 -m json.tool` 和 `git diff --check` 通过。未运行 CadQuery/STEP 验证。
- 限制：CAD-005/006 仍需冻结公式参数/单位/容差和几何摘要契约；环形线程近似、STEP 字节 hash 不稳定、`reproducibility_partial`、外部资产和许可证边界均保留。
- 下一步：Codex 中枢最终复核后再启动 CAD-005/006。

### CAD-005/006-R2 / Codex / review / 2026-11-02

- 动作：复核 R1 前序提交 `e3f88f7` 及 DATA-003/CAD-003/IR-001 接口；修复 `src/cad_compilation` 不可导入骨架，新增仓库内 `tests/cad_compilation/test_handoff.py`，补写 R2 续任复核、checkpoint 和中枢审查请求。
- 结果：项目 venv 下复核脚本检查 `bore_d=20, second_screw=0` 为 1 solid，`bore_d=20, second_screw=1` 被 `spec.check()` 拒绝；系统 Python 运行脚本时因无 CadQuery 明确输出 `blocked`。5 个 IR 示例通过 Draft 2020-12 validator，CAD-003 测试 17 项通过，DATA-003 smoke exit 0。
- 环境事实：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4；未运行 Python 3.10。历史 `/mnt/outputs/test_handoff.py` 不存在，不能作为当前复现证据。
- 边界：本轮不实现 Typed CAD IR 编译器、几何/STEP 验证器或正式测试矩阵；保留 STEP 字节 hash 不稳定、`reproducibility_partial`、螺纹环形近似和多实体风险。
- 下一步：等待 Codex 中枢审查，决定是否启动 CAD-005/006 正式实现。

### CAD-005/006-R2-CODEX-REVIEW / Codex / done / 2026-11-02

- 动作：完成第三层中枢独立审查，并对 R1 历史文件补充历史标记；修正 R2 checkpoint 的提交范围描述，新增 `agent-work/reviews/CAD-005-006-R2-codex-review.md`。
- 验证：`cad_compilation` 导入通过；项目 Python 3.11.18 环境下交接脚本通过；Schema 17 项测试通过；DATA-003 smoke 通过；系统 Python 因缺少 CadQuery 明确返回 `blocked`；`git diff --check` 通过。
- 结论：R2 修正已通过，可以交给后续正式实现；CAD-005 编译器和 CAD-006 几何/STEP 验证器尚未实现，相关正式任务继续保持 `planned`。
- 下一步：用户完成本地 push 后，再生成 CAD-005/006 正式实现 Agent 的初始化 prompt；实现前先冻结公式单位、坐标/placement、几何摘要容差和 STEP 回读失败分类。

### IR-001-R3 / Codex / planned / 2026-11-02

- 动作：生成 IR v0 最终契约审查与冻结 Agent prompt，要求独立 Agent 核对公式/量纲、坐标与 placement、几何容差、STEP 失败分类；不实现 CAD-005/006。
- 边界：不由该 Agent 冻结首族范围；以固定 BenchCAD commit 和 `set_screw_shaft_collar` 做条件性契约审查，首族正式确认仍由项目负责人/导师决定。
- Prompt：`docs/coordination/prompts/IR-001-R3-final-contract-review.md`。
- 状态：prompt 已准备，等待项目负责人启动独立 Agent；Agent 完成后由 Codex 中枢审查。

### IR-001-R3 / Codex 中枢审查 / needs_revision / 2026-11-02

- 动作：独立检查 R3 提交差异、IR Schema/示例、CadQuery 坐标语义及前序验证；复跑 Schema/示例、12 个反例、CAD-003 测试、项目 handoff smoke、公式/placement/螺纹探针。
- 结果：大部分检查可复现通过，但发现两个阻塞问题：`Workplane("XZ").revolve` 的局部 `axisEnd=(0,1,0)` 映射到世界 +Z，R3 却把 Schema 和规范定为世界 Y；错误分类支持 `build` 阶段，但 `validation_result` Schema 没有构造失败分支。
- 独立证据与修正要求：见 `agent-work/reviews/IR-001-R3-codex-review.md`。
- 验证：Schema 自检及五例通过；`tests/schema` 17 项通过；`test_handoff.py`、公式、placement、线程探针通过；本次未运行 CAD-006 数值容差补测。
- 下一步：修正上述接口矛盾并复审；首族确认与几何容差测量仍是正式 CAD-005/006 前置条件。

### IR-001-R3-FIX / Codex / in_progress / 2026-11-02

- 动作：认领 R3 两项阻塞契约修正；开始实现前完成交接定向复核。工作区已有中枢审查日志改动及未跟踪审查/prompt 文件，均保留其原始内容。
- handoff_successor_check：`predecessor=IR-001-R3 (fcb88b7), checkpoint.md + review-r3.md + IR-001-R3-codex-review.md`; `files_format=PASS，Schema 与五个 JSON 文件存在且均可解析`; `core_rerun=PASS，Draft 2020-12 self-check + 五例 Schema + 12 个语义反例`; `normal_case=PASS，legal-catalog-row.json accepted，项目 Python 3.11/CadQuery 2.3 下源案例 check/build 为 1 solid`; `failure_case=PASS，rule-rejected-second-screw.json rejected，源案例 second_screw=1 被 check 拒绝`; `interface=review，build 结果位置确有缺口；R3 把 XZ Workplane 局部 axisEnd 误述为世界 Y，与中枢复核证据不一致`; `limits=PASS，geometry_tolerance=pending_measurement、family_scope=awaiting_owner_confirmation、snapshot_status=reproducibility_partial 均保留`; `result=review`; `blocking_issue=前序坐标语义与实际映射不一致，正是本任务要求修复的阻塞项；实现仅在本任务边界内继续，保留 R3 历史记录并追加修正结果`。
- 下一步：修正世界轴契约及 accepted IR 的 build-stage validation_result，补齐契约/CAD 回归后提交供 Codex 中枢复审。

## 2026-11-02 — IR-001-R3 Typed CAD IR v0 契约复核

- Agent：Codex（IR-001-R3）；动作：完成单族条件下公式/单位、坐标 placement、几何摘要容差和错误阶段契约复核；更新 IR spec/Schema/mapping/semantic-validation/示例/checkpoint，新增 `review-r3.md`。
- 结果：公式和坐标契约形成精确定义；placement Schema 改为显式局部旋转、世界平移、世界旋转的有序变换；几何离散硬门槛可冻结，浮点阈值因现有 STEP 体积 roundtrip 差约 0.013–0.034 mm³ 且缺少原始面/边数据，标记 `pending_measurement`。固定源码当前环形 cutter 的 M6/M12 差分实测均有非零体积移除，旧 M3–M8 no-op 仅对应历史 helix 尝试，不套用到当前 ring 实现。
- 范围：`family_scope=awaiting_owner_confirmation`；未修改生产源码、CAD-003/DATA-003/CAD-005/006 目录或正式项目状态/计划/决策；未实现 compiler/validator。
- 验证：Draft 2020-12 schema self-check + 五示例、语义反例脚本、CAD-003 17 tests、项目 venv `test_handoff.py`、纯 Python 公式探针、固定 OCP placement 和 ring cutter 体积探针均通过。最终 commit 在 checkpoint 审计后补记。
- 提交：`fcb88b7` (`docs: finalize typed cad ir v0 contract [IR-001-R3]`)。
- 下一步：等待 Codex 中枢独立审查；补测确认浮点容差，并由负责人冻结首族后再判断 CAD-005/006 是否启动。

### IR-001-R3-FIX / Codex / review / 2026-11-02

- 动作：修正 IR v0 回转轴坐标契约并扩展 accepted `validation_result` 以序列化 build 阶段失败；保留 R3 历史审查内容并追加修正记录。
- 结果：Schema/规范统一为 `workplane=XZ`, `axis_local=[0,1,0]`, `axis=Z`（世界轴）；示例升级到 IR revision 0.2.0。build 失败只在 accepted `validation_result` 中使用 `CAD_BUILD_*`，通过 `completed_stages` 明确前置成功阶段；rejected 规则保留。新增 build failure 示例和坐标/阶段回归测试。
- 验证：Draft 2020-12 self-check + 六示例 + 五个阶段混淆反例 PASS；新 Schema 测试 3 项 PASS；固定源码坐标/bbox 测试 2 项 PASS；CAD-003 测试 17 项 PASS；项目 venv handoff 和 placement 探针 PASS；所有 JSON 语法及 `git diff --check` PASS。系统 Python CadQuery 导入为 blocked，CAD 检查已在项目 Python 3.11.18/CadQuery 2.3.0/OCP 7.9.3.0 环境通过。
- 限制：`geometry_tolerance=pending_measurement`、`family_scope=awaiting_owner_confirmation`、`snapshot_status=reproducibility_partial`；没有实现 CAD-005/006，也未运行浮点容差补测。
- 提交：`fac9aaf` (`fix: repair IR-001-R3 axis and build failure contract [IR-001-R3-FIX]`)。
- 下一步：等待 Codex 中枢独立复审；不得标记 CAD-005/006 done。

### IR-001-R3-FIX / Codex 中枢独立复审 / review / 2026-11-02

- 动作：独立复跑 R3-FIX 的 Draft 2020-12 Schema、六个示例、阶段混淆反例、契约测试、CadQuery/OCP 坐标与 bbox 测试、CAD handoff smoke 和 placement 探针。
- 结果：R3-FIX 两项阻塞修正通过。回转契约统一为 `workplane=XZ`、`axis_local=[0,1,0]`、世界 `axis=Z`；accepted `validation_result` 现在可以合法表达 build 失败，并由 `completed_stages` 防止阶段伪造或越级。
- 验证：Schema/六例 PASS；语义反例 PASS；IR 契约测试 3 项 PASS；坐标/bbox 测试 2 项 PASS；CAD-003 17 项 PASS；项目 venv handoff PASS；JSON 与 diff 检查 PASS。
- 结论：可以作为条件性单族 IR v0.2.0 接口交给后续准备工作，但 IR-001 保持 `review`。几何容差仍 `pending_measurement`，首族仍 `awaiting_owner_confirmation`，不得标记 CAD-005/006 done。
- 证据：`agent-work/reviews/IR-001-R3-codex-review.md` 的 R3-FIX 独立复审章节。
