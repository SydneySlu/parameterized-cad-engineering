# 项目状态

更新时间：2026-10-29

## 当前结论

- 项目路线已收敛为轻量版。
- 首期创新重点是 `Typed CAD IR`、确定性 CAD 构造/验证和小样本检索。
- 监督微调和强化学习不作为首期交付依赖；如后续需要，只做独立实验。
- 根据导师建议，当前数据方向调整为优先利用 BenchCAD 2.0 社区参数化零件族，尽量直接复用经审查的族定义与构造器；这一数据优先路线已记录为 ADR-0005 proposed，尚未冻结纳入族数量。
- GitHub 远程仓库已配置：`https://github.com/SydneySlu/parameterized-cad-engineering.git`；本机 `main` 已推送并跟踪 `origin/main`。
- `profile-pack` 暂定为可选的 Agent 上下文与决策辅助层，Git 文档和提交历史仍是进度事实源。
- 当前主机的共享项目基座已迁移到 `/Users/syd/Desktop/参数化 cad 工程辅助设计`；Agent 工作区为 `agent-work/`，旧路径不再作为项目副本使用。

## 已完成

- 完成 BenchCAD 2.0、CADBench 与 Seek-CAD 数据源的适配性和许可边界初评；建议 BenchCAD 2.0 社区零件族作为主数据源候选，CADBench 用作评测参考，Seek-CAD 用作序列/检索方法参考。尚未冻结数据集或零件族。

- 形成参数化 CAD 生成系统的轻量版技术路线。
- 完成 SKY-001、Seek-CAD、FutureCAD 以及相关 CAD/DSL 论文的初步对比。
- 形成三个首期候选零件族：工业铝型材框架角码/连接板、机器人末端工具安装转接板、电机安装板/支架。
- 形成交互汇报 HTML、汇报稿和打印版 PDF。
- 建立跨 Agent 协作协议、状态页、计划页、决策记录和工作日志。
- 建立中枢编排协议、复杂任务 checkpoint 规则和仓库体检脚本。

## 当前进行中

| ID | 工作 | 负责人 | 状态 | 输出 |
|---|---|---|---|---|
| INFRA-003 | 远程 Git 仓库与跨设备同步 | 用户 + Codex | review | 本机 `origin`、`main` 跟踪关系和首次 push；跨设备 clone/pull 待验证 |
| CAD-001 | 冻结首期零件族与参数 Schema | Codex + 导师 | planned | 零件族决策、Schema 草案 |
| DATA-001 | 评估开源 CAD 数据源与扩展路径 | Codex | review | 三数据源适配性评估；建议优先 BenchCAD 社区族 |
| DATA-002 | BenchCAD 多族数据优先接入计划与族级试审 | Codex + 用户/导师 | in_progress | 数据优先计划；核对族状态、许可、版本并完成两个族 smoke test |
| CAD-002 | 设计 Typed CAD IR v0 | Codex + CC | planned | IR Schema、示例和编译接口 |
| CAD-003 | 建立小样本检索数据格式 | CC / DSH | planned | 样本 manifest、检索字段 |
| CAD-004 | 实现确定性构造器与验证闭环 | CC | planned | 构造器、验证器、测试 |
| INFRA-005 | 中枢编排、阶段性同步和仓库体检 | Codex | done | prompt 模板、checkpoint 规则、体检脚本 |
| INFRA-006 | 中枢私有审查台账与独立复核约定 | Codex | done | 仓库外本地台账；关键结论可由第二对话框复核 |
| INFRA-007 | 轻量版 Agent 分工与依赖初步规划 | Codex | done | 分工、边界、阶段和接口依赖文档 |
| INFRA-008 | 迁移共享项目基座并建立 Agent 工作区 | Codex | done | 目标目录、职责子目录和路径规则 |

## 阻塞项

- 首期最终零件族尚未由项目负责人冻结。

## 下一步

1. 在另一台设备执行一次 clone/pull 验证，确认跨设备同步链路。
2. 按数据优先计划核对 BenchCAD 当前可用族的状态、许可、版本和本地运行条件。
3. 先选两个结构不同的 BenchCAD 族做 smoke test；根据结果与导师确认首期范围。
4. 建立跨族 manifest/adapter 和 Typed CAD IR v0，再接通原生构造器与验证器。
5. 建立族级切分的检索样本集、自然语言任务集和 A/B/C 对照评测。

