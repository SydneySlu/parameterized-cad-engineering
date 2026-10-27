# Git 同步流程

## 首次配置

当前仓库尚未绑定远程 URL。项目负责人提供 GitHub/GitLab 仓库地址后，在仓库根目录执行：

```bash
git remote add origin <repository-url>
git branch -M main
git push -u origin main
```

推送前检查：

```bash
git status --short
git diff --check
git log --oneline -5
```

## Agent 日常流程

```bash
git pull --rebase origin main
git switch -c <agent>/<task-id>
# 完成一个可审查工作单元
git diff --check
git add <files>
git commit -m "<scope>: <summary> [<task-id>]"
git push -u origin <agent>/<task-id>
```

如果不能 push，仍然要提交本地 commit，并在 `docs/WORKLOG.md` 记录阻塞原因和 commit 哈希。

## 跨设备原则

- 新设备先 clone 仓库，再阅读 `AGENTS.md` 和状态页。
- 不把聊天记录作为唯一进度；关键结论必须进入仓库。
- 不在多个设备上同时直接改 `main`；使用任务分支或先 pull --rebase。
- 合并后更新 `docs/PROJECT_STATUS.md`，让下一位 Agent 看到当前事实。

