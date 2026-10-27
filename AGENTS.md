# 参数化 CAD 项目协作约定

这是一个跨聊天框、跨 Agent、可能跨设备协作的项目。所有参与者在开始工作前必须先阅读本文件，以及：

1. `docs/PROJECT_STATUS.md`：当前事实、已完成内容和阻塞项；
2. `docs/PROJECT_PLAN.md`：阶段、任务和下一步；
3. `docs/WORKLOG.md`：追加式工作日志；
4. `docs/DECISIONS.md`：已经确认的架构和范围决策。

## 事实源和更新规则

- Git 仓库中的 Markdown、代码、配置和提交历史是项目事实源。
- `docs/PROJECT_STATUS.md` 只保留当前状态；重大变化同时追加到 `docs/WORKLOG.md`。
- `docs/WORKLOG.md` 只追加，不重写历史。每条记录包含日期、Agent、任务 ID、动作、结果和下一步。
- 需要改变范围、架构、零件族或交付标准时，先在 `docs/DECISIONS.md` 增加一条决策记录，再改正文档或代码。
- 任何 Agent 完成一个可审查的工作单元后，都要提交 Git commit，并在日志中记录 commit 短哈希。
- 未经明确授权，不提交 API key、私有数据、未授权 CAD 文件或大型生成物；先放入被 `.gitignore` 排除的目录，并在日志中记录来源和处理方式。

## Agent 角色

- **Codex / ChatGPT 中枢**：项目规划、架构分析、技术取舍、任务拆分、跨 Agent 结果复核和决策记录。
- **CC**：主要编程 Agent，负责实现、测试、重构和可运行交付物。
- **DSH**：批量、机械或低风险任务；必须使用任务 ID，并提交输入、输出和抽查结果。
- **其他 Agent**：先认领任务并说明边界；不得覆盖别的 Agent 未合并的工作；发现冲突时记录阻塞并停止扩大修改。

## 分支与提交

- 分支建议：`codex/<task-id>`、`cc/<task-id>`、`dsh/<task-id>`。
- 提交信息格式：`<scope>: <imperative summary> [<task-id>]`，例如 `docs: add project coordination contract [INFRA-001]`。
- 合并前必须说明验证命令、结果和已知限制。
- 只读研究可以不改代码，但应把结论写入对应论文报告或 `docs/research/`，并在工作日志中留下来源。

## 中途同步和阶段性提交

- 复杂任务必须先拆成可检查的里程碑；不要求一次完成整个 task 才能同步。
- 任务进行中使用 `in_progress`，每完成一个里程碑就在 `docs/WORKLOG.md` 追加 checkpoint，说明完成比例、已验证内容、剩余范围和风险。
- 阶段性结果可以提交为 `wip: ... [<task-id>]`，但未经过 Codex 审查和合并的 WIP commit 不代表任务完成。
- 如果遇到依赖缺失、范围不清或架构冲突，立即记录 `blocked` checkpoint，不要继续扩大修改。
- 只有最终结果已经验证并合并到 `main` 后，任务才标记为 `done`。

## 任务状态

统一使用：`planned`、`in_progress`、`blocked`、`review`、`done`、`deferred`。状态变化要同步到 `docs/PROJECT_STATUS.md` 或 `docs/PROJECT_PLAN.md`，不能只在聊天里宣布。

## 每次工作结束前

```text
[ ] 读取了最新 PROJECT_STATUS / PROJECT_PLAN / DECISIONS
[ ] 更新了受影响的文档、代码或实验记录
[ ] 运行了适用的检查并记录结果
[ ] 追加了 WORKLOG
[ ] 提交了 commit，或记录了为什么不能提交
[ ] 标明了下一步和阻塞项
```
