# 项目状态

更新时间：2026-11-08

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
| APP-001 | LLM 结构化抽取与 Prompt 对照 | LLM Agent + 用户 | review | v3 批次 `app001-phase1-v3-20261107-01` 已按授权完成：36/36 逻辑记录、32 条模型响应、4 条 C1 请求前阻塞、48 次物理 HTTP（含 16 次 Ollama `/api/tags`，预算内）。32/32 响应通过 parse/contract/projection，20/32 通过 CAD-003 Schema；显式字段 32/32 精确，决策 29/32，Ollama 有 3 条决策/unsupported 标签不一致。DeepSeek token/费用和 Ollama 延迟已独立复核；C2、IR/CAD/geometry/STEP 未运行。批次仍为 review，详见 `agent-work/reviews/APP-001-phase1-v3-20261107-01-codex-review.md` |
| APP-001-AUDIT-EVIDENCE-R1 | 失败响应证据留存与请求前阻塞审计补强 | CC + Codex | done | `0a49fb2`、`2581a10` 及中枢审查 `60f4fa2` 已在 main；Python 3.11.18 专项/全量和 A02/A04/A07 回归复核通过，8 个既有 FUSE 限制 skip；详见 `agent-work/reviews/APP-001-AUDIT-EVIDENCE-R1-codex-review.md` |
| APP-001-DECISION-QUALITY-ANALYSIS | 第四批次 8 条 Schema 拒绝行为诊断 | Codex | review | 只读逐条核对完成：8/8 显式字段值与冻结样例一致，拒绝均符合 CAD-003；7/8 `decision=answer` 与样例要求的澄清/拒绝不符，详见 `agent-work/reviews/APP-001-phase1-20261107-04-schema-decision-analysis.md` |
| APP-001-DECISION-POLICY-V3-DRAFT | 候选决策策略 v3 与版本化激活 | CC + Codex | done | ADR-0016 已接受；v3 激活与 v2 历史审计入口经 Codex 独立复核并合入 `main`（`7dc7a37`），LLM 576 项通过（8 个既有 FUSE skip）、Schema 17 项通过。真实模型效果未测，FORMAL_EVALUATION_ALLOWED 仍为 False |
| APP-001-V3-DECISION-FIX-DRAFT | v3 观测偏差对应的 v4 离线候选修正 | Codex | done | P1/P2 checker 修正和离线候选准备已在 Python 3.11.18 下复核并提交（`6d1f90a`、`9f424d0`）；ADR-0017 已被项目负责人批准策略方向，相关激活已在 `main` 完成。见 `agent-work/llm/APP-001-V3-DECISION-FIX-DRAFT/checkpoint.md` |
| APP-001-V4-ACTIVATION | extraction v4 版本化激活实现 | CC + Codex | done | 激活提交 `85f9e71`、closeout `f858be8` 和合入审查 `c18fd35` 已进入 `main`；Python 3.11.18 下 71 专项、685 LLM（8 个既有 FUSE skip）、17 Schema 通过，v4/v3/acceptance-set 哈希核对一致，正式 gate 仍关闭。真实 v4 模型效果尚未测量。 |
| APP-001-PREFLIGHT-TEST-ISOLATION-FIX | 修复正式评测前置测试的 batch_id 碰撞 | CC + Codex | done | `e47af64` 实现 UUID 测试隔离，`d422877` 完成中枢独立审查并已合入 `main`；Python 3.11.18 下 `test_r3_fixes` 51/51、LLM 全量 685 通过（8 个既有 FUSE skip）、Schema 17/17 通过。未改变生产代码、授权范围或正式批次。 |
| APP-001-V4-FORMAL-EFFECT-EVALUATION | v4 真实模型效果评测 | Codex + 项目负责人 + CC | review | 批次 `app001-phase1-v4-20261109-01` 已完成 36 条逻辑记录、32 条模型响应和 4 条 C1 请求前阻塞；48 次物理 HTTP 均在预算内。字段/证据/解析 32/32 通过，但有 3 条 Ollama 决策偏差和 2 条 DeepSeek A05 envelope 自洽性问题；详见 `agent-work/reviews/APP-001-phase1-v4-20261109-01-codex-review.md`。 |
| APP-001-V4-QUALITY-FIX-CANDIDATE | v4 决策质量离线候选修正 | CC + Codex | review | R1 提交 `d706639` 已经 Codex 离线复核：78 项专项、191 项定向回归通过，正式 `llm` 导入、P2-5 冲突和数值归一化边界通过；候选仍未合并/激活。 |
| APP-001-V5-PROMPT-CANDIDATE | 针对 v4 已确认决策偏差准备 v5 离线 prompt 候选 | Codex | review | 候选 prompt 与 A01-A09 策略映射已准备；checker 对所有显式目录耦合字段的冲突覆盖已补齐。Python 3.11.18 下 LLM 800 项（8 个既有 skip）、Schema 17 项通过；未激活、未运行模型，等待独立审查。 |

## 阻塞项

- CAD-005/006 本轮阻塞已解除。跨平台/跨进程及不同 CadQuery/OCP/STEP writer 环境仍未验证；当前实现证据仅覆盖固定软件基线，不构成跨环境承诺。
- APP-001 既有批次均保留且处于 review：v3 批次有 32 条模型响应和 4 条 C1 请求前安全阻塞；显式字段全部精确，决策有 3 条不一致，确定性 Schema 20/32 通过。R1 证据留存和阻塞审计代码已合入 main。C2、IR/CAD/geometry/STEP 未运行，不能发布端到端构造指标。不得重写旧批次或混合统计。
- APP-001-V4-ACTIVATION 已由 Codex 中枢独立审查并合入 `main`（`c18fd35`）；v4 已是生产离线契约版本。唯一批次 `app001-phase1-v4-20261109-01` 已执行并完成独立只读复核，但决策质量和 envelope 自洽性仍有问题，不能宣称策略效果已解决。
- APP-001-PREFLIGHT-TEST-ISOLATION-FIX 已合入 `main`（`d422877`）。Python 3.11.18 下连续全量 LLM 测试稳定为 685 通过、8 个既有 FUSE skip；该修复只影响测试隔离，不构成真实模型效果证据。
- `APP-001-EVIDENCE-CONTRACT-FIX` 已由 `352ef8a` 修复并经 Python 3.11.18 中枢复核；ADR-0015 的 evidence-null 前置门已关闭。ADR-0014 的历史 v2 授权表保留不改，当前 v4 继承 scope 已追加同步记录。

## 当前工作单元边界

- APP-001-AUDIT-EVIDENCE-R1 仅修补失败响应的受控留存和请求前阻塞记录；不改变 Prompt、输出协议、RET-002 策略、重试上限或 provider 配置，不调用真实模型；已合入 main 并通过中枢审查。
- A04 C1 因用户输入缺少 `bore_d` 而正确阻塞；A07 C1 因 `bore_d=75` 不满足 envelope 的 CAD-003 目录校验，且不具备 flat 查询所需六字段而正确阻塞。不得从 evaluator-only 标签补值或猜字段。样例级回归由 Codex 在本工作单元后独立补齐/验收。
- 8 个 Schema 拒绝的只读决策质量分析已完成；若要改 Prompt/输出策略，必须版本化、另建批次，并另行取得新模型运行授权。
- APP-001-DECISION-POLICY-V3-DRAFT 原有缺口已在同一候选分支窄修并经中枢复审通过（`b757e9c`）：候选 prompt 提供冻结目录行和螺钉规则作为可见判定参考，静态测试核对该表与 CAD-003 完全一致；`answer` 要求 `bore_d` 为离散目录值，新增 bore_d=75 拒绝及 A06 边界正常用例。候选未激活，离线测试不构成模型效果结论；不授权新正式批次。
- APP-001 extraction v3 的九样例离线验收已补齐：A01-A09 的 case ID、A03 单位换算、A08 retrieval reference 隔离、主张保留、拒绝/澄清边界和 prompt/激活包哈希均有测试。项目负责人已接受 ADR-0016；v3 激活与显式 v2 历史只读解析入口经 Codex 独立复核并合入 `main`（`7dc7a37`），Python 3.11.18 下 LLM 576 项通过（8 个既有环境 skip）、Schema 17 项通过。该段为历史版本记录；当前 v4 批次已单独授权，效果仍待测量。
- DeepSeek 5xx 继续按 ADR-0010 当前最多两次重试；除非服务状态或错误证据支持，不调整 provider 配置或重试策略。

## 下一步

1. 批次 `app001-phase1-v4-20261109-01` 已完成并经 Codex 独立复核；保留 raw、账本和阻塞证据，不删除或覆盖。
2. `APP-001-V5-PROMPT-CANDIDATE` 当前处于 review；需独立审查 prompt、checker/策略一致性、冻结接口兼容和交付证据。生产 v4、正式 gate 和旧批次保持不变。
3. v5 候选通过独立审查后，再由项目负责人决定是否进入版本化激活；任何模型效果测试都必须建立新版本、新唯一 batch_id 和新授权，不得重跑同一批次或混合统计。
4. 继续保持 C2 和 IR/CAD/geometry/STEP 禁用，除非另行取得明确授权；DeepSeek 5xx 继续遵循 ADR-0010 的重试上限。
5. 第二族扩展另行决策，不作为 APP-001 前置依赖。
