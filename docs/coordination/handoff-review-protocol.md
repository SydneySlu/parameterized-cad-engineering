# Agent 交接三层检查协议

本协议用于跨聊天框、跨 Agent 和跨设备的任务交接。它的目的不是让续任 Agent 重做完整 Code Review，而是确认前一个结果是否足以安全支撑下一步工作。

## 三层检查

### 第一层：交接 Agent 自检

原 Agent 在提交前必须在任务 `checkpoint.md` 或交接文档中记录：

```text
handoff_self_check:
  changed=<修改的文件、提交或产物>
  commands=<实际运行的验证命令和结果>
  confirmed=<已经由证据确认的内容>
  unresolved=<仍未解决的问题、限制和未运行的检查>
  next_agent_focus=<续任 Agent 必须优先检查的接口或风险>
```

“通过”只能用于实际运行并得到结果的命令；没有运行的检查必须写成 `not_run`，不能根据预期填写 PASS。

### 第二层：续任 Agent 定向复核

续任 Agent 开始实现前必须先阅读前一个 Agent 的 checkpoint、交接文档和相关提交，然后记录：

```text
handoff_successor_check:
  predecessor=<上一个任务 ID、checkpoint 和 commit>
  files_format=<文件存在、格式和入口是否正确>
  core_rerun=<至少一条核心命令及结果>
  normal_case=<一个正常案例及结果>
  failure_case=<一个失败/拒绝案例及结果>
  interface=<输入输出与本任务是否一致>
  limits=<已知限制是否保留>
  result=pass | review | blocked
  blocking_issue=<若 review/blocked，写明问题>
```

定向复核至少包含一条正常案例和一条失败案例。若前一个任务没有这两类案例，续任 Agent 必须补做，或把状态标记为 `review`/`blocked`，不能直接覆盖上一个成果。

续任 Agent 的复核重点是“能否安全继续”，不是重新审查所有实现细节。发现记录与实际结果不一致时，应先记录问题并停止扩大修改范围。

### 第三层：Codex 中枢独立审查

Codex 中枢负责最终判断：

- 是否满足任务验收标准；
- 是否与总体架构、已冻结决策和上下游接口一致；
- 是否可以合并或交给下游 Agent；
- 是否需要返工、补充证据或标记阻塞。

Agent 的自检和续任复核不能替代中枢审查；中枢也不能只依据 Agent 的“PASS”文字而跳过关键命令和产物检查。

## 风险分级

以下任务强制执行 double check，也就是续任 Agent 必须重跑核心命令并检查一个正常案例和一个失败案例：

- Schema/规则 → Typed CAD IR；
- Typed CAD IR → CAD 编译器；
- CAD 编译器 → 几何/STEP 验证器；
- 数据源 → 训练/检索数据库；
- 会冻结接口、数据格式、版本、来源或许可证判断的任务。

低风险任务（例如批量重命名、格式转换、文档排版）可以只做轻量抽查，但仍需记录文件存在性、一个代表性结果和已知限制。

## 启动前统一要求

所有续任 Agent 在开始实现前执行：

```text
1. 阅读上一个 Agent 的 checkpoint 和交接文档。
2. 复跑至少一条核心验证命令。
3. 检查一个正常案例和一个失败案例。
4. 确认输入接口、输出接口、版本和来源与本任务一致。
5. 确认已知限制没有被交接过程删除或改写。
6. 发现不一致时先记录 review/blocked，不直接覆盖上一个成果。
```

## 与任务状态的关系

- `pass`：可以在既定边界内继续工作，但不代表最终完成；
- `review`：有不一致或证据不足，需要 Codex 中枢判断；
- `blocked`：存在阻止安全继续的缺失、冲突或环境问题；
- 只有中枢审查通过、必要的续任复核完成并合并到 `main` 后，任务才能标记 `done`。
