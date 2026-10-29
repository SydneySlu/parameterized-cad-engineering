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

### INFRA-007 / Codex / done

- 动作：围绕轻量版架构规划数据、LLM、Schema/规则、Typed CAD IR 设计、CAD 执行/验证和集成审查的 Agent 分工与依赖；暂不生成初始化 prompt。
- 结果：明确 Codex 负责接口、范围、审查和 IR 设计，CC 负责 Schema/规则及 CAD 执行实现，数据 Agent 负责来源和样本，LLM Agent 负责 Prompt/结构化抽取/检索接入；Typed CAD IR 与验证器共用版本化接口。
- 验证：检查计划、任务看板和协调文档中的任务 ID、依赖和验收条件；待正式认领后再建立具体 Agent prompt。
- 下一步：确认首期零件族、实际对话框/分支名称和评测阈值，再生成逐 Agent 初始化 prompt。


### DATA-001 / Codex / review

- 动作：比较 BenchCAD 2.0 社区族/公开评测集、CADBench（附件论文 arXiv:2605.10873v2）和 Seek-CAD 的目标、数据结构、轻量版适配度、规模与许可边界；新增研究报告 `docs/research/cad-dataset-suitability-2026-10.md`。
- 结果：建议 BenchCAD 2.0 作为主数据源候选，因为其参数、来源范围、约束和确定性 CadQuery 几何与项目主线接近；CADBench 作为多模态几何重建/外部评测参考；Seek-CAD 作为特征序列及检索方法参考。尚未冻结数据集或零件族。
- 验证：查阅附件论文第 1、3、4 节及附录 D；核对三个项目的作者 README、BenchCAD 2.0 博客/仓库设计规范和 CADBench Hugging Face 数据卡。未下载完整数据集或运行样本。
- 许可边界：BenchCAD 2.0 README 区分 MIT 代码/设计与 CC BY 4.0 数据制品；CADBench 按源数据混合许可；Seek-CAD 仓库代码 MIT，但 README 未单列数据许可。
- 下一步：导师/项目负责人确认主数据源候选与零件族方向后，开展已合并 BenchCAD 家族和候选族覆盖的样本级审查（DATA-002）；再冻结首期零件族。

### DATA-001 / Codex / review / 2026-10-28 checkpoint

- 动作：补充核对 BenchCAD 2.0 GitHub 设计接口、当前状态页、评审规范、官方博客及 Hugging Face Public/Core 数据卡；新增 `docs/research/benchcad-2-deep-dive-2026-10.md`。
- 结果：明确区分社区参数化零件族与 Public/Core 工程任务评测集；整理 `part.py`、`spec.py`、`family.json` 及 `PARAM_SPEC`、`check()`、`refine()` 的字段语义；核对当前状态页为 4/150 个族已合并；对三个候选零件族给出匹配和延伸估算。
- 关键风险：Public/Core 当前数据卡明确禁止训练、微调、蒸馏、RL 环境、检索/搜索语料和再发布，因此只能作为外部评测/任务设计参考；不能按原始评估集接入轻量版检索或训练管线。
- 验证：官方页面与仓库原文核对；`git diff --check` 通过；未下载 gated Public/Core 内容，也未将其文件写入仓库。
- 下一步：导师确认首期目标族后，执行 DATA-002：选定一个已合并族或仿照其接口新增一个来源可追溯族，建立项目 manifest 与 Typed CAD IR 映射。

### DATA-002 / Codex / in_progress / 2026-10-29 checkpoint

- 动作：根据用户转述的导师意见，将数据策略调整为 BenchCAD 社区参数化族优先；新增 `docs/research/benchcad-dataset-first-plan-2026-10.md`，并在 `docs/DECISIONS.md` 记录 ADR-0005 proposed；同步更新项目状态、计划和任务看板。
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
