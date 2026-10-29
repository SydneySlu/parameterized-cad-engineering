# PLAN-001 规划阶段 checkpoint：仓库阅读与现状基线

- 日期：2026-10-30
- 任务：PLAN-001
- 阶段完成比例：约 25%（仅完成项目基座核对、必读材料阅读和规划基线记录；尚未完成范围确认、接口设计或执行验收）
- 状态：review

## 已确认内容

- Git 根目录为 `/Users/syd/Desktop/参数化 cad 工程辅助设计`，与项目协作约定一致。
- 轻量版主链为 Typed CAD IR、确定性 CAD 构造/验证和小样本检索；监督微调和强化学习不属于首期交付依赖。
- BenchCAD 社区参数化族优先路线处于 ADR-0005 proposed，首期族数量和具体族尚未冻结。
- 当前计划以族级状态/许可/环境核查和两个结构不同族 smoke test 作为建议门槛；这仍是规划建议，不是已完成工程事实。
- 正式状态、计划、任务、决策由 Codex 中枢维护；本 Agent 只在 `agent-work/project-planning/` 记录讨论草案。

## 未决范围

- 研究材料迁移到 `database/` 的现有未提交改动由谁提交、何时完成审查。
- 首期采用“两族门控后扩展”还是“全部当前可用族首轮覆盖”。
- 首轮族、固定 commit、许可/状态/环境核验标准、smoke test 验收阈值。
- Schema、Typed CAD IR、family adapter 的冻结顺序，以及独立复核范围。

## 依据

已阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`docs/DECISIONS.md`、`docs/coordination/agent-work-allocation.md`、`agent-work/README.md`、`agent-work/project-planning/README.md`、`docs/research/README.md`、`database/README.md` 及数据库下三份 BenchCAD/CADBench/Seek-CAD 研究与计划材料；并核对 `git rev-parse --show-toplevel`、`git status --short --branch` 和未提交 diff。

## 风险

- 工作树已有其他任务的未提交路径迁移改动；若与本轮规划提交混淆，可能导致错误合并或遗漏。
- 研究材料中 BenchCAD 的“目标族数量”“已合并数量”“release-qualified 状态”有明确区分，后续不得把目标数量当作现成可用数据。
- 在首期族和接口未冻结前，提前并行实现会造成 Schema/IR/构造器反复返工。

## 下一步

请项目负责人优先选择 A（首期零件族与两族 smoke test 决策门）、B（Typed CAD IR/Schema/adapter 接口冻结顺序）或 C（12 周阶段、资源和验收阈值）作为下一轮讨论主题。涉及范围、架构或交付标准的结论需交 Codex 中枢审查并由其更新正式文档。

## 限制

本 checkpoint 没有编写或修改生产代码、测试、CAD 构造器、验证器、数据处理脚本、Prompt 实现，也没有下载、整理或运行数据集。
