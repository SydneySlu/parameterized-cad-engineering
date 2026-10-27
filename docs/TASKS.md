# 任务看板

状态：`planned` / `in_progress` / `blocked` / `review` / `done` / `deferred`。

| ID | 任务 | 负责人 | 状态 | 依赖 | 验收条件 |
|---|---|---|---|---|---|
| INFRA-001 | Git 初始化与协作协议 | Codex | done | - | 仓库可提交，所有 Agent 有统一入口 |
| INFRA-002 | 状态、计划、决策、日志骨架 | Codex | done | INFRA-001 | 文件存在且互相链接 |
| INFRA-003 | 远程仓库与跨设备同步 | 用户 + Codex | blocked | GitHub 仓库 URL | 新设备可 clone，首次 push 成功 |
| INFRA-004 | Agent 配置入口 | Codex + 用户 | planned | INFRA-003 | Codex/CC/DSH 可找到同一状态和任务 |
| INFRA-005 | 中枢编排、阶段性同步和仓库体检 | Codex | done | INFRA-001 | 有 prompt 模板、checkpoint 规则和体检脚本 |
| INFRA-006 | 中枢私有审查台账与独立复核约定 | Codex | done | INFRA-005 | 仓库外台账已建立，事实源与复核边界写入决策记录 |
| CAD-001 | 候选零件族比较 | Codex | planned | - | 有数据/规则/应用/生成难点对比 |
| CAD-002 | 冻结首期零件族 | 用户 + 导师 | planned | CAD-001 | 决策记录明确范围和不支持项 |
| CAD-003 | 参数 Schema v0 | CC | planned | CAD-002 | 有字段、单位、边界、来源和缺失规则 |
| CAD-004 | 评测集切分 | Codex + CC | planned | CAD-002 | 模板近重复不会跨训练/测试泄漏 |
| IR-001 | Typed CAD IR v0 | CC + Codex | planned | CAD-003 | 至少一个样例可校验和序列化 |
| CAD-005 | 确定性 CAD 编译器 | CC | planned | IR-001 | 同一 IR 可复现生成结果 |
| CAD-006 | 几何与规则验证器 | CC | planned | CAD-005 | 能报告成功、失败原因和错误字段 |
| RET-001 | 检索样本 manifest | DSH + CC | planned | CAD-006 | 样本来源和验证结果可追溯 |
| RET-003 | 检索收益评测 | Codex + CC | planned | RET-001 | 有固定集和三条件对照 |

## 认领格式

在聊天中认领后，追加到 `docs/WORKLOG.md`：

```text
[YYYY-MM-DD HH:MM] agent=<id> task=<id> status=in_progress
scope=<本次改动范围>
next=<完成后的下一步>
```

