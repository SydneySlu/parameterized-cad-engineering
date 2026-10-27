# Codex 中枢工作协议

Codex / ChatGPT 中枢负责把用户目标转成可执行任务，并维护跨 Agent 的一致状态。它不是只负责分配任务，还负责检查任务之间的依赖、复核结果和发现仓库状态错误。

## 中枢开始一个新阶段时

1. 读取 `PROJECT_STATUS.md`、`PROJECT_PLAN.md`、`TASKS.md`、`DECISIONS.md` 和最近的 `WORKLOG.md`。
2. 检查当前分支、未提交修改、远程状态和任务状态是否一致。
3. 把目标拆成有依赖关系的 task ID，并明确每个任务的输入、输出、边界和验收条件。
4. 为每个 Agent 生成单独的初始化 prompt，包含 agentId、task ID、工作目录、允许修改范围和交接格式。
5. 将架构变化写成 ADR，将普通实现工作写入任务和计划，不把临时想法当作项目事实。

## 中枢接收阶段性结果时

检查四件事：

- 结果是否对应已认领的 task ID；
- 修改是否超出 Agent 的范围或改变了未批准的架构；
- 验证命令是否真实运行，结果是否可复现；
- 状态页、任务看板、工作日志和 commit 是否一致。

阶段结果可以退回继续开发，也可以拆出新的 follow-up task。不能因为 Agent 返回了“完成”就直接把任务标为 `done`。

## 中枢生成 Agent prompt 的固定字段

```text
project=<项目名>
agent_id=<codex | cc | dsh | other>
task_id=<任务 ID>
objective=<本次只完成的目标>
read_first=<必须读取的文件>
allowed_scope=<允许修改的目录或文件>
out_of_scope=<明确不做的内容>
checkpoints=<中途需要同步的里程碑>
acceptance=<验收条件>
handoff=<最终交接格式>
```

## 仓库体检

每次合并前运行：

```bash
python3 scripts/check_project_state.py
git diff --check
git status --short --branch
```

体检脚本发现的错误必须修复，警告必须在工作日志中解释。

