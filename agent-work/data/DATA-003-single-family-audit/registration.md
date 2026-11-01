# DATA-003 任务注册

- 任务：BenchCAD 单族来源、环境与最小 smoke test
- 父任务：DATA-002 BenchCAD 多族数据优先接入计划与族级试审
- 状态：planned
- Agent：待项目负责人在新对话框启动
- 工作区：`agent-work/data/DATA-003-single-family-audit/`
- 外部 checkout：`work/benchcad-source/benchcad-2/`（被 Git 忽略）
- 临时产物：`work/benchcad-output/`（被 Git 忽略）
- 允许输出：来源审计、候选族矩阵、环境记录、运行日志、最小 manifest 草案、checkpoint
- 禁止范围：生产 Schema、Typed CAD IR、adapter、验证器、LLM、检索系统和全量数据处理
- 审查人：Codex 中枢
- 完成门：来源/许可证/入口核验，合法/边界/非法参数测试，STEP 或等价几何核验，重复运行记录
- 初始化 Prompt：`docs/coordination/prompts/DATA-003-single-family-audit-agent.md`
