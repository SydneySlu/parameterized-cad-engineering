# Agent 启动与交接模板

这个文件用于把同一套项目管理约定带到 Codex、CC、DSH 和新的聊天框。它不是某个平台的私有配置，而是可以随仓库迁移的启动协议。

## 每个 Agent 启动时

```text
你正在参与“参数化 CAD 生成系统”项目。
你的 agentId：<codex | cc | dsh | other>
项目根目录（当前主机）：`/Users/syd/Desktop/参数化 cad 工程辅助设计`。先进入该目录并运行 `git rev-parse --show-toplevel`；不要在自己的 Agent 文件夹建立第二份项目副本。
按职责把中间工作写入 `agent-work/` 对应子目录；源代码、测试和正式项目文档分别写入 `src/`、`tests/` 和 `docs/`。
先阅读 AGENTS.md、docs/PROJECT_STATUS.md、docs/PROJECT_PLAN.md、docs/DECISIONS.md 和 docs/TASKS.md。
只认领一个明确的 task ID；开始前在 docs/WORKLOG.md 记录 status=in_progress。
完成后运行适用检查，更新状态和日志，提交一个可审查的 Git commit。
不要把聊天上下文当成唯一事实源；不要覆盖其他 Agent 的未合并工作。
```

## Codex / ChatGPT 中枢

- 维护项目状态、计划、决策和跨 Agent 交接。
- 在 `docs/TASKS.md` 拆解任务，给出依赖、验收条件和负责人。
- 复核 CC/DSH 的实现和实验结果，再更新 `docs/PROJECT_STATUS.md`。
- 不把没有验证的研究结论写成已完成事实。

## CC 主编程 Agent

- 从 `docs/TASKS.md` 认领实现任务。
- 先确认 IR、Schema、接口或数据格式，再编写代码。
- 每个任务保留最小可运行验证，记录命令和结果。
- 只提交实现和对应测试，架构范围变化另开 ADR。

## DSH 批量 Agent

- 适合批量整理、字段清洗、样本 manifest、来源登记和重复性检查。
- 必须记录输入范围、脚本/命令、输出数量和人工抽查数量。
- 不直接改变核心 Schema 或架构决策；发现异常时标记为 `blocked`。

## 交接最小格式

```text
task=<ID>
status=<done | review | blocked>
commit=<short sha>
changed=<文件或目录>
verified=<命令和结果>
known_limits=<已知限制>
next=<下一步>
```

