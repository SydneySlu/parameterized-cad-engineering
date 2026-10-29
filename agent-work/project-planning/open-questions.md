# 总体推进待决问题

由总体规划 Agent 与项目负责人共同维护。每项问题使用稳定编号，记录提出日期、影响范围、候选答案、依赖和当前状态。正式决策确认后保留原问题记录，并链接到对应 ADR 或任务。

## 状态

使用 `open`、`needs-user-confirmation`、`needs-codex-review`、`resolved`、`deferred`。

## 当前问题

### PQ-001：研究资料迁移改动的提交边界

- 提出日期：2026-10-30
- 状态：needs-codex-review
- 问题：`README.md`、`docs/PROJECT_PLAN.md`、`docs/PROJECT_STATUS.md`、`docs/TASKS.md`、`docs/WORKLOG.md` 和 `docs/research/README.md` 有未提交修改，三份旧研究文件显示删除，同时 `database/` 下对应文件为未跟踪；这些内容与 `WORKLOG` 中的 INFRA-009 迁移记录一致，但尚未形成当前工作树可见的提交。
- 影响：事实源路径和后续 diff/合并边界可能被误判；PLAN-001 不能覆盖或代提交该改动。
- 依据：`git status --short --branch`、`git diff --name-status`、`docs/WORKLOG.md` INFRA-009 记录。
- 下一步：由项目负责人/Codex 中枢确认是否保留该迁移、由谁提交，以及是否需要补一次仓库体检。

### PQ-002：首期 BenchCAD 覆盖门槛

- 提出日期：2026-10-30
- 状态：needs-user-confirmation
- 问题：首期是否以两个结构不同族完成端到端最小闭环作为交付门槛，并把扩展到更多当前可用族作为后续决策门，还是首轮就要求覆盖全部当前可用族。
- 影响：决定 DATA-002、CAD-001/CAD-002 的范围、资源和并行方式。
- 依据：ADR-0005 proposed、`database/benchcad-dataset-first-plan-2026-10.md` 第 1、6、9 节。
- 候选：两族门控（建议草案，风险较低）；全部当前可用族首轮覆盖（覆盖更广但集成风险更高）。

### PQ-003：首轮族和验收阈值

- 提出日期：2026-10-30
- 状态：open
- 问题：两族具体选哪些，固定哪个源 commit，如何核验状态/许可证/运行环境，以及 smoke test 至少需要哪些构造、STEP、规则和回读证据。
- 影响：决定 manifest/adapter、IR v0 和评测切分能否冻结。
- 依据：`database/benchcad-dataset-first-plan-2026-10.md` 第 3、4、5 节；目前仓库只有族级建议，没有本轮运行结果。
- 下一步：在 PQ-002 确认后形成族级审查清单，由执行 Agent 按清单验证。

### PQ-004：接口冻结和独立复核顺序

- 提出日期：2026-10-30
- 状态：open
- 问题：是否先冻结族级 manifest/Schema 最小字段，再冻结 Typed CAD IR v0；IR 是否只覆盖两个族的公共信封和族特异字段；哪些错误码、验证指标和交付阈值需要第二个 Codex 对话框独立复核。
- 影响：决定 Schema、IR、构造器、验证器和 LLM/检索任务的并行边界。
- 依据：`docs/coordination/agent-work-allocation.md` 第 69–92 行及 `docs/PROJECT_PLAN.md` 阶段 1–3。
- 下一步：在首期范围明确后比较“先 Schema 后 IR”和“先 IR 公共信封后 Schema”的接口方案。
