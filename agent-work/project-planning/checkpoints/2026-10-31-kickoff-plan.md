# PLAN-001 规划阶段 checkpoint：单族来源审计启动计划

- 日期：2026-10-31
- 阶段完成比例：约 45%（启动计划已形成；尚未下载、固定 commit 或运行族级 smoke test）
- 状态：review

## 已确认内容

- “选择一个具体族、获取源码、完成最小核验”可以作为项目启动点。
- 首轮不需要下载 BenchCAD 全量数据集；社区族源代码和最小运行依赖足够启动来源审计。
- 外部 checkout 建议放在项目根目录下被忽略的 `work/benchcad-source/benchcad-2`，项目 Git 只记录来源和验证证据。
- MacBook Air M5 先作为首轮环境候选；Windows + 1TB 外置硬盘作为批量产物/兼容性回退环境。

## 计划输出

已创建 `agent-work/project-planning/kickoff-plan-2026-10-31.md`，包含候选族、下载路径、阶段 0–5、软件、角色分工、验收清单和明确不做事项。

## 未决范围

- 用户是否确认 BenchCAD 社区族、首族/第二族候选和 checkout 路径。
- 当前仓库的实际族状态、许可证、依赖和 Mac ARM 兼容性。
- 派生实例、STEP、渲染结果和 manifest 的公开边界。

## 限制

本 checkpoint 只记录规划，没有下载、整理或运行数据集，没有修改生产代码、测试、构造器、验证器、数据处理脚本或 Prompt 实现。

