# Agent 工作区

这是项目基座内按职责划分的共享工作区。当前主机的项目根目录是：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

Agent 不得把项目文件写入自己的聊天缓存目录、默认工作目录或其他项目副本。开始任务时先运行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
```

如果设备路径不同，以 `git rev-parse --show-toplevel` 返回的 Git 根目录为准，并在交接中说明实际路径。

## 子目录

- `data/`：数据来源调查、清洗记录、样本 manifest 草稿；原始或未授权数据放在仓库规定的私有/忽略位置。
- `llm/`：模型适配、Prompt、结构化抽取和检索注入实验。
- `schema-rules/`：Schema、单位归一化、参数边界和规则校验实验。
- `typed-cad-ir/`：Typed CAD IR 设计、示例和序列化草稿。
- `cad-validation/`：CadQuery/OCP 构造器、STEP 回读、几何验证和失败案例。
- `integration/`：跨模块集成、端到端运行和验收记录。
- `reviews/`：可共享的审查意见、复核材料和 checkpoint；私有中枢台账仍在仓库外。
- `project-planning/`：总体推进讨论 Agent 的规划记录、待决问题和阶段 checkpoint。
- `inbox/`：尚未归类的交接材料，处理后应移动到对应目录。

源代码放 `src/`，测试放 `tests/`，正式研究/决策/状态材料放 `docs/`。大文件、密钥、私有数据和未授权 CAD 文件遵守根目录 `.gitignore`，不要为了提交而强行加入 Git。
