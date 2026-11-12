# 项目状态

更新时间：2026-11-12

## 当前结论

- 项目路线已收敛为轻量版。
- 当前首要目标是自然语言→v5 抽取/决策→Schema→Typed CAD IR→CadQuery→几何验证→STEP 的最小闭环，再做必要产品包装（ADR-0020）。小样本检索研究独立保留，不作为闭环前置门。
- v5 保持当前 prompt/契约/hash 作为首个集成基线；一般优化不启动 v6。首个真实闭环优先沿用已审查 DeepSeek `deepseek-flash` 配置，Qwen 后续兼容。
- 监督微调和强化学习不作为首期交付依赖；如后续需要，只做独立实验。
- 根据导师建议，当前数据方向优先利用 BenchCAD 2.0 社区参数化零件族；首期范围已由 ADR-0007 冻结为 `set_screw_shaft_collar`，使用固定 source commit 和项目侧适配/验证，不扩展第二族作为首期交付依赖。
- GitHub 远程仓库已配置：`https://github.com/SydneySlu/parameterized-cad-engineering.git`；本机 `main` 跟踪 `origin/main`。本轮启动为干净 `993a5b1`、领先已缓存远端 12 个提交；本轮不 push，提交后的实际差异以 Git 为准。
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
| DATA-002 | BenchCAD 数据优先接入计划与族级试审 | Codex + 用户/导师 | deferred | 首期范围已收缩为单族；后续扩族不属于首期交付 |
| DATA-003 | BenchCAD 首族来源、环境与许可证边界 | DATA-003 Agent + Codex | done | 固定 commit、快照可复现性、生成资产与第三方材料许可证审计；审查记录已完成 |
| CAD-002 | 冻结首期零件族 | 项目负责人 + Codex | done | ADR-0007；`set_screw_shaft_collar` 与固定 commit |
| CAD-003 | 参数 Schema 与规则校验 | CC + Codex | review | 单族 Schema/单位/目录与来源规则已实现并供下游使用，本轮固定环境 17 项复验通过；早期 checkpoint 保留 review，不把历史状态误作未实现，也不声称跨族完成 |
| IR-001 | Typed CAD IR v0 设计与复核 | Codex + 独立复核 Codex | review | 单族 IR v0.2.0 已有规范、语义验证和后端接入；本轮 5 项 IR 回归通过，可复用；缺正式 Schema→IR 集成 adapter，比较策略由 CAD-006.geometry-comparison.v1 独立版本化 |
| INFRA-005 | 中枢编排、阶段性同步和仓库体检 | Codex | done | prompt 模板、checkpoint 规则、体检脚本 |
| INFRA-006 | 中枢私有审查台账与独立复核约定 | Codex | done | 仓库外本地台账；关键结论可由第二对话框复核 |
| INFRA-007 | 轻量版 Agent 分工与依赖初步规划 | Codex | done | 分工、边界、阶段和接口依赖文档 |
| INFRA-008 | 迁移共享项目基座并建立 Agent 工作区 | Codex | done | 目标目录、职责子目录和路径规则 |
| CAD-005/006-R2 | 修复 CAD 编译交接边界并完成中枢复核 | Codex | done | 可导入包边界、仓库内交接 smoke test、R2 审查记录；当时尚未启动的正式实现由下方 CAD-005/006 任务承接 |
| CAD-005/006 | Typed CAD IR 编译器与几何/STEP 验证器 | 原 CAD-005/006 Agent + Codex | done | `df78f4f` 修复 canonical input 绑定和错误 `node_ids`；中枢独立重跑 CAD 13 项、Schema 17 项、IR 契约/轴向 5 项及 `py_compile`，全部通过；审查记录已同步到主线 |
| RET-001 | 单族检索样本 manifest | DSH + CC + Codex | done | 15/15 目录行通过 Schema、IR、CAD 构造、native 重复和 STEP 回读；manifest 825 项、tracked-only 660 项校验通过；split 为 provisional_small_n |
| RET-003 | 单族检索诊断与下游收益评测 | Codex + CC | deferred | C1 检索级诊断已验收；12-run 下游收益研究离线关口已通过，真实执行暂缓（ADR-0020），不阻塞 CAD 集成；收益仍 not_measured，不预设正收益 |
| APP-001-PREP | 模型基线、输入输出契约与小型验收集冻结 | LLM Agent + Codex + 用户 | done | 最终中枢验收通过，详见 `agent-work/reviews/APP-001-PREP-FINAL-ACCEPTANCE.md` |
| APP-001-ADAPTER | 双基线执行适配器与分阶段运行记录 | CC + Codex | done | R3-FIX 经中枢独立验收通过，详见 `agent-work/reviews/APP-001-ADAPTER-R3-FIX-codex-review.md` |
| APP-001-RUNNER | 第一阶段受控运行入口、预算和模型身份边界 | CC + Codex | done | R2-R6 修复已合入 `main`（`9d83219`，状态文档 `53f6c49`）；中枢独立复核在 Python 3.11.18 下确认 389 项 LLM 测试通过、8 项环境限制跳过，17 项 Schema 测试通过。详见 `agent-work/reviews/APP-001-RUNNER-R6-codex-review.md` |
| APP-001 | LLM 结构化抽取与决策基线 | Codex + CC | review | v5已作为集成基线（ADR-0020），整体待整链验收；不再开展无明确假设的版本对照。v3/v4 历史批次保持只读；v5 批次 `app001-phase1-v5-20261111-01` 已完成只读收束审查：36 条记录、32 个模型响应、4 个 C1 请求前阻塞、48 次账本尝试（预算内）；32/32 解析通过，20/32 通过 CAD-003 Schema，决策分布 answer=20/ask=2/refuse=10。未运行 C2/IR/CAD/geometry/STEP，详见 `agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md` |
| APP-001-AUDIT-EVIDENCE-R1 | 失败响应证据留存与请求前阻塞审计补强 | CC + Codex | done | `0a49fb2`、`2581a10` 及中枢审查 `60f4fa2` 已在 main；Python 3.11.18 专项/全量和 A02/A04/A07 回归复核通过，8 个既有 FUSE 限制 skip；详见 `agent-work/reviews/APP-001-AUDIT-EVIDENCE-R1-codex-review.md` |
| APP-001-DECISION-QUALITY-ANALYSIS | 第四批次 8 条 Schema 拒绝行为诊断 | Codex | review | 只读逐条核对完成：8/8 显式字段值与冻结样例一致，拒绝均符合 CAD-003；7/8 `decision=answer` 与样例要求的澄清/拒绝不符，详见 `agent-work/reviews/APP-001-phase1-20261107-04-schema-decision-analysis.md` |
| APP-001-DECISION-POLICY-V3-DRAFT | 候选决策策略 v3 与版本化激活 | CC + Codex | done | ADR-0016 已接受；v3 激活与 v2 历史审计入口经 Codex 独立复核并合入 `main`（`7dc7a37`），LLM 576 项通过（8 个既有 FUSE skip）、Schema 17 项通过。真实模型效果未测，FORMAL_EVALUATION_ALLOWED 仍为 False |
| APP-001-V3-DECISION-FIX-DRAFT | v3 观测偏差对应的 v4 离线候选修正 | Codex | done | P1/P2 checker 修正和离线候选准备已在 Python 3.11.18 下复核并提交（`6d1f90a`、`9f424d0`）；ADR-0017 已被项目负责人批准策略方向，相关激活已在 `main` 完成。见 `agent-work/llm/APP-001-V3-DECISION-FIX-DRAFT/checkpoint.md` |
| APP-001-V4-ACTIVATION | extraction v4 版本化激活实现 | CC + Codex | done | 激活提交 `85f9e71`、closeout `f858be8` 和合入审查 `c18fd35` 已进入 `main`；Python 3.11.18 下 71 专项、685 LLM（8 个既有 FUSE skip）、17 Schema 通过，v4/v3/acceptance-set 哈希核对一致，正式 gate 仍关闭。真实 v4 模型效果尚未测量。 |
| APP-001-PREFLIGHT-TEST-ISOLATION-FIX | 修复正式评测前置测试的 batch_id 碰撞 | CC + Codex | done | `e47af64` 实现 UUID 测试隔离，`d422877` 完成中枢独立审查并已合入 `main`；Python 3.11.18 下 `test_r3_fixes` 51/51、LLM 全量 685 通过（8 个既有 FUSE skip）、Schema 17/17 通过。未改变生产代码、授权范围或正式批次。 |
| APP-001-V4-FORMAL-EFFECT-EVALUATION | v4 真实模型效果评测 | Codex + 项目负责人 + CC | review | 批次 `app001-phase1-v4-20261109-01` 已完成 36 条逻辑记录、32 条模型响应和 4 条 C1 请求前阻塞；48 次物理 HTTP 均在预算内。字段/证据/解析 32/32 通过，但有 3 条 Ollama 决策偏差和 2 条 DeepSeek A05 envelope 自洽性问题；详见 `agent-work/reviews/APP-001-phase1-v4-20261109-01-codex-review.md`。 |
| APP-001-V4-QUALITY-FIX-CANDIDATE | v4 决策质量离线候选修正 | CC + Codex | done | R1 提交 `d706639` 已经 Codex 离线复核：78 项专项、191 项定向回归通过，正式 `llm` 导入、P2-5 冲突和数值归一化边界通过；其后 v5 候选与激活已通过独立审查并合入 main；此行为已并入 v5 的前置候选，不再是当前未激活阻塞。 |
| APP-001-V5-PROMPT-CANDIDATE | 针对 v4 已确认决策偏差准备 v5 离线 prompt 候选 | Codex | done | 独立离线审查通过，候选提交 `582a123` 已随 v5 激活链合入 `main`；离线候选不构成模型效果证据。 |
| APP-001-V5-ACTIVATION-PREP | v5 版本化激活准备与 ADR-0018 提案 | Codex + 项目负责人 | done | 准备包及 v4 回滚锚点 `687495b` 已合入 `main`；ADR-0018 已接受。 |
| APP-001-V5-ACTIVATION | v5 生产版本化激活 | Codex + Codex 中枢 | done | `2c70225` 已合入并推送至 `main`；中枢审查通过，Python 3.11.18 激活/兼容专项 72 项通过。运行时默认 v5，v2/v3/v4 保留显式历史审计；formal evaluation gate 仍为 `False`。 |
| APP-001-V5-FORMAL-EFFECT-EVALUATION | v5 真实模型效果评测 | Codex + 项目负责人 | done | 唯一批次 `app001-phase1-v5-20261111-01` 已真实运行：32/36 模型响应、4 条 C1 请求前阻塞、48 次账本尝试；32/32 解析通过、20/32 Schema 通过。32 个 raw 文件存在且哈希匹配，但实际位于批次根目录，偏离授权指定的 `raw/` 子目录。runner 已窄修为后续正式运行写入 `batch/raw/`；历史批次未移动/重跑。分支已合入并推送，Codex 在 `main=95d1dcb` 上复验：LLM 842 通过/8 个既有 FUSE skip，Schema 17 通过，runner+v5 入口 101 通过/1 个既有 skip；详见审查记录。后续真实运行需新入口基线、新 batch ID 和单独授权。 |
| APP-001-NEXT-REAL-MODEL-EVALUATION | v5 held-out 检索对照 | Codex + 项目负责人 | deferred | R2 与 CLI 补测已验收；本轮在 993a5b1 完成 final offline preflight：12 组合、索引校验通过、预算可行 global=44/Ollama=26、目录不存在。无正式 batch ID/请求授权；研究恢复须重验当前基线并单独授权，不阻塞集成。详见集成基线 preflight 报告 |
| APP-002-INTEGRATION-A1 | 最小后端连接层与离线统一入口 | CC 实现 / Codex 中枢独立验收 | done | `d6faf70` 已合入并推送 `main`；固定环境集成 81、CAD 13、Schema 17 通过；bore24 合成 envelope 实际生成并回读 STEP，P1 fail-closed 成功门经独立复核通过 |
| APP-002-INTEGRATION-A2-SCOPE | 真实模型整链范围与受控入口 | Codex 中枢 | review | ADR-0021 A2 专用 gate 保持全局 `FORMAL_EVALUATION_ALLOWED=False`。`...-03` 获批后实际运行 3 条 DeepSeek 请求：2 条 answer 因系统 Python 缺 `jsonschema` 在 IR Schema 校验失败、无 STEP；1 条 ask 正确停止；summary=`partial`，3/9 HTTP。`...-01`/`...-02`/`...-03` 均只读保留。固定 CAD venv 已核实依赖；后续使用新 batch ID、固定 venv，并另行申请 live 批准 |

## 当前缺口与限制

- A1 的语言层到后端连接已完成并合入 `main`；A2 已产生真实模型 answer/ask 证据，但真实模型→STEP 仍未完成。`...-03` 的两条合法 answer 因调用解释器缺 `jsonschema` 在 IR 校验前 fail closed；固定 CAD venv 包含所需依赖。旧评测 runner 不自动获得 CAD 权限，A2 继续使用专用受控入口。
- 已有后端并非零进度。本轮固定 Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 环境下 CAD 13 项、Schema/IR 22 项通过，包含真实本地构造、STEP 导出与回读；这不是自然语言真实模型整链证据。
- v5 已有固定九案例真实双模型证据，当前没有真实模型→STEP 的整链验收。新模型整链需新受控 scope、输入、预算、batch ID 与项目负责人授权；旧 Schema-only 和 held-out scope 不自动扩展。
- 15 行覆盖当前冻结单族全部合法目录配置，不是语言训练样本；九案例的条件/模型运行次数不是独立用户需求数。语言覆盖、运行稳定性、跨族扩展分别规划。
- 历史 v3/v4 决策缺陷保留为版本证据，不冒充当前 v5 阻塞。v5 历史 32 个 raw 位于批次根目录的授权路径偏离仍如实保留；不移动、不改写、不重跑、不混合统计。
- 固定环境以外的可移植性、许可/发布范围、螺纹环形近似限制仍保留；几何/STEP 通过不构成制造认证。

## 当前工作单元边界

- `APP-002-INTEGRATION-A1`：已完成；输入需求文本与明确标为 synthetic 的冻结 v5 envelope，复用 parse/project/Schema，经严格构造门与正式 IR 映射，调用真实本地编译器/验证器生成 STEP。
- `APP-002-INTEGRATION-A2-SCOPE`：A2 专用 gate 决策已由 ADR-0021 接受，不打开全局 gate；复核定位出正式 Adapter run ID 与 transport binding 不一致。当前修复该绑定和 all-error summary 状态，既有 `...-01`/`...-02` 均 HTTP=0、目录只读保留。实现复核通过后才为新唯一 batch ID 请求执行批准。
- ask/refuse、missing_fields、unsupported、解析/Schema/IR 失败不调用 CAD；构造/导出/回读失败不能报告成功或发布其他运行旧文件。用户显式值、目录派生值与规则派生值分别保存。
- 本工作包不发模型/网络请求，不读密钥、.env 或历史 raw 正文；不修改冻结 prompt、Schema/IR 语义、预算、A2 输入/模型/condition scope 或旧批次，`FORMAL_EVALUATION_ALLOWED=False` 不变。ADR-0021 仅确认既有 A2 专用授权机制可用于后续独立批准的 batch。
- 错误几何、关键参数丢失、错误放行、假成功属于交付阻断；措辞、额外语言覆盖与新实验进入 backlog，不自动阻断主闭环。

## 下一步

1. A1 已完成：固定环境独立验收和合并后回归均通过，证据保存在 A1 checkpoint。
2. **A2 scope 准备已完成并合入 `main`**：`9b9395c` 包含冻结输入、授权 profile、受控入口、正式批准门、summary/raw 证据链及文档收束。
3. 两次 live attempt 均在首个 HTTP 前停止：`...-01` 因构造器参数错误；`...-02` 因 Adapter 的 `FORMAL_EVALUATION_ALLOWED=False`。两批均 HTTP=0，失败目录只读保留。
4. `1dc61bc` 修复通过离线回归；`...-03` live 执行证明 Adapter gate 可到达模型，但系统 Python 缺少 `jsonschema`，两条 answer 未生成 STEP。所有已使用 batch 均只读保留。
5. **当前关口**：先对 `codex/APP-002-A2-GATE-STATUS-FIX` 代码完成独立复核并合入；之后使用 `work/benchcad-output/venv/bin/python`（Python 3.11.18、jsonschema 4.26.0、CadQuery 2.3.0、OCP 7.9.3.0）执行新的离线 preflight，再向负责人申请新唯一 batch ID 的 live 批准。不得重用 `...-03`。
6. 里程碑 C 提供需求、参数/确认、状态/失败原因、结果获取和修改后再生成。下周导师展示是目标；当前只具备模块证据，不宣称真实模型整链已完成。
7. 12-run 检索研究 `deferred`：主闭环完成或出现明确研究假设后再恢复、重验并独立授权；不列为上述步骤前置条件。证据见 [本轮 preflight](../agent-work/reviews/APP-001-V5-INTEGRATION-BASELINE-preflight.md)。
