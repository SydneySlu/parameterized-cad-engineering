# 参数化 CAD 生成系统

这是一个面向单一工程零件族的轻量版 CAD 生成项目。核心路线是：

```text
自然语言 / 可选图像 / 示例零件
  -> 结构化参数 JSON
  -> Typed CAD IR
  -> 确定性编译器
  -> CadQuery / OCP 构造
  -> 几何、STEP 和规则验证
  -> 可编辑 CAD 结果与报告
```

项目的首期亮点是 **Typed CAD IR** 和 **小样本检索**。LLM 负责理解需求和提出参数候选；确定性构造器和验证器负责生成与检查几何。首期不把监督微调、强化学习、通用视觉世界模型或跨零件族泛化作为交付依赖。

## 从哪里开始

当前主机的项目基座是 `/Users/syd/Desktop/参数化 cad 工程辅助设计`。所有 Agent 先进入这个目录并用 `git rev-parse --show-toplevel` 检查根目录；按职责划分的中间工作区见 [`agent-work/README.md`](agent-work/README.md)。

1. 阅读 [`AGENTS.md`](AGENTS.md)。
2. 阅读 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。
3. 阅读 [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)。
4. 阅读 [`docs/DECISIONS.md`](docs/DECISIONS.md)。
5. 需要接任务时，在 [`docs/TASKS.md`](docs/TASKS.md) 认领任务，并在 [`docs/WORKLOG.md`](docs/WORKLOG.md) 留痕。

## 目录约定

- `docs/`：状态、计划、决策、研究报告和协作协议。
- `src/`：实现代码；当前骨架阶段可为空。
- `tests/`：验证和回归测试。
- `data/`：经过许可核验的数据；原始和私有数据默认不入 Git。
- `artifacts/`：实验清单和可审查结果；大型生成文件默认不入 Git。
- `references/`：公开、可再分发的参考材料或链接；未确认许可的文件放 `references/private/`。
- `agent-work/`：按 Agent 职责划分的共享中间工作区；不替代 `src/`、`tests/`、`docs/` 和 `data/` 的正式目录规则。

## Git 协作

每个可审查工作单元都应有一个任务 ID、一个 commit 和一条工作日志。远程仓库 URL 尚未配置时，可以先在本地提交；配置远程后再按 `docs/coordination/git-sync.md` 推送。

