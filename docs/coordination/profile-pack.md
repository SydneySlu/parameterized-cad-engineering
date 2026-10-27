# Profile Pack 接入边界

`profile-pack`（https://github.com/SydneySlu/profile-pack）可以作为本地 MCP 上下文层，保存项目级访问范围、决策反馈和 Agent-specific 观察。它适合减少跨聊天框的上下文重复，但当前仓库不依赖它才能运行。

## 推荐用法

- 每个 Agent 使用明确的 `agentId`，例如 `codex`、`cc`、`dsh`。
- 项目资料进入独立 Project Profile，不写入个人 Profile。
- 只把稳定、经过确认的项目偏好或决策上下文放入 Profile Pack。
- 代码、任务状态、实验结果和架构决策仍写回 Git 仓库。

## 暂不做的事

- 不把 localhost Profile Pack 当作跨设备同步服务。
- 不把未审核的 Agent 观察自动升级成项目决策。
- 不把个人敏感信息提交到本项目仓库。

