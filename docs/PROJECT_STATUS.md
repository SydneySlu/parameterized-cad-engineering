# 项目状态

更新时间：2026-11-07

## 当前结论

- 项目路线已收敛为轻量版。
- 首期创新重点是 `Typed CAD IR`、确定性 CAD 构造/验证和小样本检索。
- 监督微调和强化学习不作为首期交付依赖；如后续需要，只做独立实验。
- 根据导师建议，当前数据方向优先利用 BenchCAD 2.0 社区参数化零件族；首期范围已由 ADR-0007 冻结为 `set_screw_shaft_collar`，使用固定 source commit 和项目侧适配/验证，不扩展第二族作为首期交付依赖。
- GitHub 远程仓库已配置：`https://github.com/SydneySlu/parameterized-cad-engineering.git`；本机 `main` 已推送并跟踪 `origin/main`。
- 数据集选型、许可核查、处理计划与后续讨论统一维护在 [`database/README.md`](../database/README.md) 及其索引文件中。
- `profile-pack` 暂定为可选的 Agent 上下文与决策辅助层，Git 文档和提交历史仍是进度事实源。
- 当前主机的共享项目基座已迁移到 `/Users/syd/Desktop/参数化 cad 工程辅助设计`；Agent 工作区为 `agent-work/`，旧路径不再作为项目副本使用。

## 已完成

- 完成 BenchCAD 2.0、CADBench 与 Seek-CAD 数据源的适配性和许可边界初评；BenchCAD 2.0 社区族作为主数据源，CADBench 用作评测参考，Seek-CAD 用作序列/检索方法参考。
- 已冻结首期零件族 `set_screw_shaft_collar`，固定 BenchCAD commit `035f467142888edfd0bd7cd73906f9b155c8f43c`；DATA-003 来源、快照和许可证补充审计已由 Codex 中枢复核完成，限制见审查记录。
- RET-001 单族 manifest 已完成中枢复核：覆盖 15 个冻结目录行，完整记录参数、IR、构造/几何/STEP 验证、来源、hash 和临时 split；split 仍为 `provisional_small_n`，生成 STEP 仍为 `license_scope_uncertain`。
- RET-002 单族确定性检索基线已完成主体实现、策略范围修正和中枢复核，状态为 `done`；split 仍为 `provisional_small_n`，不得当作正式 benchmark。

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
| CAD-001 | 候选零件族比较 | Codex | done | 数据、规则、应用和生成难点对比 |
| DATA-001 | 评估开源 CAD 数据源与扩展路径 | Codex | review | 三数据源适配性评估；建议优先 BenchCAD 社区族 |
| DATA-002 | BenchCAD 数据优先接入计划与族级试审 | Codex + 用户/导师 | review | 首期范围已收缩为单族；后续扩族不属于首期交付 |
| DATA-003 | BenchCAD 首族来源、环境与许可证边界 | DATA-003 Agent + Codex | done | 固定 commit、快照可复现性、生成资产与第三方材料许可证审计；审查记录已完成 |
| CAD-002 | 冻结首期零件族 | 项目负责人 + Codex | done | ADR-0007；`set_screw_shaft_collar` 与固定 commit |
| CAD-003 | 参数 Schema 与规则校验 | CC | planned | 字段、单位、边界、来源和缺失规则 |
| IR-001 | Typed CAD IR v0 设计与复核 | Codex + 独立复核 Codex | review | 单族 IR v0.2.0；比较策略由 CAD-006.geometry-comparison.v1 独立版本化 |
| INFRA-005 | 中枢编排、阶段性同步和仓库体检 | Codex | done | prompt 模板、checkpoint 规则、体检脚本 |
| INFRA-006 | 中枢私有审查台账与独立复核约定 | Codex | done | 仓库外本地台账；关键结论可由第二对话框复核 |
| INFRA-007 | 轻量版 Agent 分工与依赖初步规划 | Codex | done | 分工、边界、阶段和接口依赖文档 |
| INFRA-008 | 迁移共享项目基座并建立 Agent 工作区 | Codex | done | 目标目录、职责子目录和路径规则 |
| CAD-005/006-R2 | 修复 CAD 编译交接边界并完成中枢复核 | Codex | done | 可导入包边界、仓库内交接 smoke test、R2 审查记录；当时尚未启动的正式实现由下方 CAD-005/006 任务承接 |
| CAD-005/006 | Typed CAD IR 编译器与几何/STEP 验证器 | 原 CAD-005/006 Agent + Codex | done | `df78f4f` 修复 canonical input 绑定和错误 `node_ids`；中枢独立重跑 CAD 13 项、Schema 17 项、IR 契约/轴向 5 项及 `py_compile`，全部通过；审查记录已同步到主线 |
| RET-001 | 单族检索样本 manifest | DSH + CC + Codex | done | 15/15 目录行通过 Schema、IR、CAD 构造、native 重复和 STEP 回读；manifest 825 项、tracked-only 660 项校验通过；split 为 provisional_small_n |
| RET-003 | 单族检索诊断与下游收益评测 | Codex + CC | in_progress | C1 检索级诊断已在固定环境运行并经中枢验收；3 个主查询、2 个接口诊断、1 个失败诊断通过，5/5 跨进程确定性检查通过；RET-001/002 回归通过。端到端下游收益仍 not_measured，等待 APP-001 和新的评测放行 |
| APP-001-PREP | 模型基线、输入输出契约与小型验收集冻结 | LLM Agent + Codex + 用户 | done | 最终中枢验收通过，详见 `agent-work/reviews/APP-001-PREP-FINAL-ACCEPTANCE.md` |
| APP-001-ADAPTER | 双基线执行适配器与分阶段运行记录 | CC + Codex | done | R3-FIX 经中枢独立验收通过，详见 `agent-work/reviews/APP-001-ADAPTER-R3-FIX-codex-review.md` |
| APP-001-RUNNER | 第一阶段受控运行入口、预算和模型身份边界 | CC + Codex | done | R2-R6 修复已合入 `main`（`9d83219`，状态文档 `53f6c49`）；中枢独立复核在 Python 3.11.18 下确认 389 项 LLM 测试通过、8 项环境限制跳过，17 项 Schema 测试通过。详见 `agent-work/reviews/APP-001-RUNNER-R6-codex-review.md` |
| APP-001 | LLM 结构化抽取与 Prompt 对照 | LLM Agent + 用户 | review | 修复后第三批次 `app001-phase1-20261107-03` 已完成：36/36 逻辑记录、32 条模型调用、4 条 C1 请求前阻塞、48 次物理 HTTP；DeepSeek envelope 16/16、Ollama C1 7/7 通过，Ollama C0 有 8 条严格类型拒绝。usage/cost、延迟和显式字段诊断已落盘，但 CAD/STEP 未运行，不能发布端到端构造指标。详见 `agent-work/reviews/APP-001-phase1-20261107-03-codex-review.md` |

## 阻塞项

- CAD-005/006 本轮阻塞已解除。跨平台/跨进程及不同 CadQuery/OCP/STEP writer 环境仍未验证；当前实现证据仅覆盖固定软件基线，不构成跨环境承诺。
- APP-001 三批次均保留且处于 review：第三批次验证了 loader 修复，但 Ollama C0 的 8 条响应因显式数值类型不合规被严格拒绝。旧批次不能回填或重算；A04/A07 的 4 条 C1 请求前安全阻塞保持原样。Ollama structured-output 窄修正的离线代码测试通过，但当前本机基线仍为 Ollama 0.33.2，JSON Schema 对象 `format` 的运行时兼容性未证明，不能据此启动新批次。

## 下一步

1. 决定是否接受 Ollama C0 严格类型拒绝作为首轮结果，或先解决 Ollama structured-output 运行时兼容性；不得修改三个既有批次。
2. 若继续修正，先明确 Ollama 版本/ADR、补 evidence null 契约处理和兼容性证据，再创建新的唯一批次；三个既有批次不覆盖或混合统计。
3. 继续保持 C2 和 IR/CAD/geometry/STEP 禁用；任何新批次仍严格遵守 ADR-0014 的 36 逻辑运行与 108 物理 HTTP 上限。
4. 第二族扩展另行决策，不作为 APP-001 前置依赖。
