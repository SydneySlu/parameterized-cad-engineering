# 复杂任务的进度同步

复杂任务可以在中途同步，不需要等到完整交付。同步的目标是让中枢知道“已经可靠完成什么、还缺什么、是否需要调整方向”。

## 推荐拆分方式

一个复杂 task 至少拆成：

1. **准备**：确认输入、接口、依赖和范围。
2. **最小闭环**：完成一个最小可运行或可审查样例。
3. **扩展**：补充边界、错误处理、批量样本或性能。
4. **验收**：运行测试、整理文档、交付 commit。

每个阶段都可以单独产生 checkpoint。阶段之间应尽量有可恢复的 commit。

## 阶段性 checkpoint 格式

追加到 `docs/WORKLOG.md`：

```text
### <TASK-ID> / <agent-id> / checkpoint

- 完成度：<例如 2/4 个里程碑>
- 已完成：<具体文件、接口或实验>
- 已验证：<命令和结果>
- 未完成：<剩余工作>
- 风险/阻塞：<没有则写 none>
- 下一步：<下一阶段>
- commit：<short sha；没有则写 working tree>
```

## 中途向 Codex 汇报的 prompt

```text
task=<TASK-ID>
status=in_progress
checkpoint=<当前里程碑>
done=<已经完成的内容>
verified=<已经运行的检查>
remaining=<剩余内容>
risks=<风险或阻塞>
proposal=<是否需要调整拆分、范围或依赖>
```

## 中途同步后的处理

Codex 会根据 checkpoint 做三种处理：

- 继续原任务：边界和依赖没有变化；
- 拆分 follow-up：当前结果可以保留，但剩余内容应变成新的 task；
- 暂停/阻塞：缺少用户决策、数据许可或外部资源，先保留 checkpoint，不扩大修改。

