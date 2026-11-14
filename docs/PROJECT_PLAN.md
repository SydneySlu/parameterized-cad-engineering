# 项目计划

本计划用于跨 Agent 和跨设备同步，不替代详细技术方案。每次范围变化必须同步 `docs/DECISIONS.md`。

轻量版首期的 Agent 分工、边界、依赖和阶段性交付见 [`docs/coordination/agent-work-allocation.md`](coordination/agent-work-allocation.md)。各阶段 Prompt 和交接记录按任务保存在 `docs/coordination/prompts/` 及其历史归档目录中。

## 当前主线与里程碑（ADR-0020、ADR-0023，2026-11-13）

首要目标是自然语言→v5→Schema→Typed CAD IR→CadQuery→几何验证→STEP，再做最小产品包装。v5 是当前集成基线，不因一般优化启动 v6。下列历史模块计划用于资产追溯，执行优先级以本节为准。

| 里程碑 | 工作单元 / 负责人 | 当前状态与退出条件 |
|---|---|---|
| A：最小后端集成 | A1 `APP-002-INTEGRATION-A1`：CC 实现，中枢独立验收 | done；`d6faf70` 已合入 `main`。需求文本+合成 v5 envelope 经严格 gate、正式 Schema→IR adapter、现有编译器生成真实 STEP，并保存可追溯记录；合成提取不得称真实模型理解 |
| A：接入真实提取 | A2 `APP-002-INTEGRATION-A2-SCOPE`：Codex 中枢推进受控 live 整链 | done；runtime guard 与缺依赖零调用回归已合入 `main=0b02a26`，固定 CAD venv Python 3.11.18 下 A2 98 项、Integration 179 项通过。获批批次 `app002-a2-smoke-20261112-04` 使用 3/9 HTTP：24 mm 与 80 mm 两条 answer 均通过 Schema、IR、CAD、STEP 导出/回读，缺孔径输入为 ask 且停止构造。Codex 中枢完成独立只读复核；批次只读保留 |
| B：最小整链验收 | Codex 中枢：复用既有测试并补做缺失案例 | done；六类验收均有证据：真实模型 24 mm 合法值、80 mm 第二螺钉边界、缺参 ask；合成 envelope 的 1.6 cm→16 mm 本地真实 CAD/STEP；显式目录冲突在 Schema 阶段阻断且 CAD 未调用；真实编译器链注入 STEP 导出失败后 status=failed、无 STEP/index。固定 CAD venv 下 A2 98、Integration 179、CAD 13、Schema 17 项通过。合成离线结果不计作额外 live 语言样本 |
| C：最小可用演示 | APP-003-C1：CC 实现，中枢验收 | done；已合入并推送至 `main=07a98d1`。固定 CAD venv 回归及真实 localhost 24/80 mm STEP、边界阻断、下载安全和 run 隔离烟测通过。三维预览与部署后置；当前演示仅手动确认参数，不调用 LLM。证据见 `agent-work/reviews/APP-003-C1-codex-review.md` |
| C：自然语言产品闭环 | APP-003-C2-NL-PRODUCT-FLOW：已有 C1 CC 对话框实现，Codex 中枢独立验收 | done；`d839954` 已合入 `main`。固定 CAD venv 回归和真实 localhost create→confirm→get→download 烟测通过；synthetic fixture 模式下 bore24、bore80 与 ask 补参生成真实 STEP，非法 HTTP 确认类型 400 且零 CAD 调用。详见 C2 checkpoint。 |
| C：自然语言确认界面 | APP-003-C3-PRODUCT-UI：已有 C1/C2 CC 对话框实现，Codex 中枢独立验收 | done；`f105fc4` 已合入并推送 `main`。固定 CAD venv 的 demo/integration 264、Schema 17、CAD 13，localhost 及浏览器验证均通过：ask-extra 空确认阻断、ask-missing 空 patch 阻断、补 bore_d=16 后真实 STEP 下载 hash 匹配、XSS 纯文本和 reset 清理均已确认。后续 live extraction 仍需新 scope 和授权。 |
| C：产品真实抽取 scope | APP-003-LIVE-SCOPE：Codex 中枢准备 scope，CC 实现受控入口 | done；`db26fda` 已合入 `main`，固定 CAD venv 独立复核通过。受控 API 已具备自然语言抽取结果、确认和 STEP 下载链路，但尚未接入浏览器 UI，也未执行真实 provider 请求。 |
| C：产品 live 确认界面 | APP-003-LIVE-UI：CC 接入受控 live API，Codex 中枢复核 | done；`8dce35a` 已合入并推送 `main`，固定 CAD venv 与 localhost 浏览器验收完成。下一步若执行真实 provider，必须另立 live scope、预算、preflight、batch ID 和负责人批准。 |
| C：产品 live smoke 准备与运行 | `APP-003-LIVE-PREFLIGHT-20261113-01`：Codex 中枢 + 项目负责人 | done；旧 batch `app003-product-live-20261113-01` 按批准 scope 执行 4 次 HTTP，均在解析/Envelope 阶段失败、无 CAD/STEP，批次只读保留。错误映射/脱敏与 HTTP raw path 隔离修复已在 `d80fd43` 合入本地 `main`，独立复核 `pass`；固定 CAD venv 回归通过。 |
| C：新产品 live smoke 正式运行 | `APP-003-LIVE-PREFLIGHT-20261114-01`：Codex 中枢 + 项目负责人 | review；batch 已执行 4/12 HTTP，P1–P4 均在响应前以 `TRANSPORT_ERROR/authentication_or_permission` 失败，summary=`failed`，无 CAD/STEP。只读诊断发现 `.env` 有非空 DeepSeek key，但 formal runner 未加载 `.env`，而 transport 只读进程环境；`5bf82ce`/`df3f7b4` fail-closed 加载修复已通过独立复核，固定 CAD venv 凭据专项 9/9、Product Live 107/107 和 diff check 通过。不能由旧结果判断账户权限；若要验证 provider，须另建 scope/batch/approval/preflight 并获新执行授权。 |
| C：凭据修复后 provider diagnostic | `APP-003-LIVE-PREFLIGHT-20261114-02`：Codex 中枢 + 项目负责人 | done；原 batch 按冻结 scope 完成 4/12 次真实 DeepSeek HTTP并经独立复核 `pass`。P1 随后经负责人单独确认 `bore_d=24`，在隔离目录完成 CAD/STEP/readback；P2 ask、P3/P4 refuse 均保持阻断。原 batch 只读，语义质量未评估。 |
| C：失败路径收束与语言样本设计 | `APP-003-FAILURE-PATHS-LANGUAGE-MATRIX`：Codex 中枢先行，随后独立复核 | review；失败路径修复和 10 条输入 scope 已独立复核通过。新 batch `app003-product-language-20261114-01` 的离线 formal preflight 已通过（DeepSeek `deepseek-flash`/C0，10 条，最多 20 HTTP）。formal runner 已在分支 `cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER` 实现（`e7e2952` 初始实现、`8a6a062` 与 `9a0bb0f` 窄修），含七层门控、BudgetLedger、raw/summary 隔离、异常脱敏和 update_run 失败尽力 finalize；尚未通过 Codex 中枢独立复核；真实请求仍为 blocked。 |

- 资产核验：Schema 已实现；单族 IR v0.2.0 与白名单编译器/几何/STEP 回读已有固定环境证据。A1 已补齐正式语言→Schema→IR→CAD 连接层；固定环境 CAD 13 项、Schema/IR 22 项及 A1 集成 81 项复验通过，不重做后端。
- 复用 RET-001 的全部 15 行单族目录回归证据；它不是 15 条语言训练样本，九案例的条件/模型运行也不是独立需求样本数。
- v5 fixed-set 真实双模型评测已完成。A2 `...-03` 的两条 answer 因系统 Python 缺少 `jsonschema` 未通过 IR Schema 阶段，一条 ask 正确停止；该历史批次只读保留。runtime guard 已合入并在固定 CAD venv 下复验。获批批次 `...-04` 在 CAD venv 中完成 3 次真实 DeepSeek 请求：24 mm 与 80 mm answer 均生成并回读 STEP，缺孔径请求为 ask；账本 3/9，Codex 中枢独立核对了 summary、预算、raw 文件路径/哈希元数据、IR/STEP 与 index/manifest hash 及 readback comparison。批次只读保留，证据见 A2 checkpoint 与独立审查报告。ADR-0021 专用 gate 不改变全局 gate。held-out 检索对照仍 deferred，不阻塞 A/B/C。
- 里程碑 B 已完成固定环境定向验收。单位换算使用合成 envelope 和真实本地 CAD/STEP，不冒充真实模型语言理解；显式冲突与导出失败均验证不误报成功。已完成六类链路验收不等于广泛语言覆盖；是否增加 live 样本留待负责人根据具体语言风险假设另行决定，任何新增请求都须新的 batch scope、预算、ID 和授权。
- 里程碑 C 已完成 C1 手动参数演示和 C2/C3 离线自然语言产品流程。新 batch `app003-product-live-20261114-02` 在凭据入口修复后完成 4/12 次真实请求并经独立复核 `pass`；P1 随后经负责人单独确认 `bore_d=24`，隔离 confirmation run 完成 CAD/STEP/readback；P2 ask 与 P3/P4 refuse 均阻断。原 batch 只读，本轮不代表广泛语言质量结论。
- A1 交付与证据见 [`agent-work/integration/APP-002-INTEGRATION-A1/checkpoint.md`](../agent-work/integration/APP-002-INTEGRATION-A1/checkpoint.md)；A2 scope 准备（CC 实现）见 [`agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/checkpoint.md`](../agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/checkpoint.md)，scope 草案见 [`agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md`](../agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md)。
- 下周导师展示目标：合法需求产 STEP、边界几何正确、非法/不完整阻断、参数/IR/验证可查；未达成前区分模块演示与整链演示。

## 阶段 0：仓库和协作基础

- [x] 建立 Git 仓库、忽略规则和协作约定（INFRA-001）
- [x] 建立状态、计划、任务、决策和工作日志（INFRA-002）
- [x] 配置远程仓库并完成本机首次 push（INFRA-003；跨设备 clone/pull 待另一设备验证）
- [ ] 为 Codex、CC、DSH 建立各自的 Agent 配置入口（INFRA-004）
- [x] 建立中枢编排、阶段性同步和仓库体检机制（INFRA-005）
- [x] 建立仓库外中枢私有审查台账和独立复核边界（INFRA-006）
- [x] 完成轻量版 Agent 分工与依赖初步规划（INFRA-007）
- [x] 迁移共享项目基座并建立按职责划分的 Agent 工作区（INFRA-008）

## 阶段 1：问题冻结和零件族选择

- [x] 初评 BenchCAD 2.0、CADBench、Seek-CAD 的数据适配性与许可边界（DATA-001；结论见 [`database/cad-dataset-suitability-2026-10.md`](../database/cad-dataset-suitability-2026-10.md)）
- [ ] 【deferred，非首期前置】建立 BenchCAD 多族数据优先试点：锁定具体 commit，检查许可/状态/环境，先用两个结构不同的社区族跑通 smoke test，再决定是否扩展到更多族（DATA-002；建议见 [`database/benchcad-dataset-first-plan-2026-10.md`](../database/benchcad-dataset-first-plan-2026-10.md)）
- [x] 完成第一个单族来源、环境与最小 smoke test 纵向切片（DATA-003；审计与 R2 许可证/快照补充已完成）
- [x] 项目负责人确认数据优先路线和首期族数量（CAD-001；首期为 `set_screw_shaft_collar`）
- [x] 冻结首期 BenchCAD 社区族集合、支持任务和不支持项（CAD-002；决策见 ADR-0007）
- [x] 单族 CAD-003 Schema 已实现字段、单位、来源与缺失/冲突规则，17 项固定环境回归通过；早期任务 checkpoint 仍 review，单族实现可复用
- [ ] 【deferred】跨族 manifest/adapter 与 Schema 扩展；不把跨族设计作为单族闭环前置
- [ ] 按族、目录行和 near-duplicate group 建固定评测切分，避免实例泄漏（CAD-004）

## 阶段 2：Typed CAD IR 和确定性主线

- [x] 单族 IR v0.2.0 规范、语义验证与后端接入已存在（IR-001 R3 修复已验收）；正式语言参数→IR adapter 已由 A1 提供，不重做 IR
- [x] 首族 IR 已定义固定节点、引用、错误码及 canonical 检查；跨族扩展 deferred（IR-002）
- [x] 建立白名单 CadQuery/OCP 编译器（CAD-005；canonical 输入绑定经中枢复核，固定环境测试通过）
- [x] 建立实体有效性、STEP 回读和零件族规则验证器（CAD-006；冻结容差策略实现并通过固定环境标准/边界/失败路径测试）
- [ ] 建立语言输入、Schema、IR、验证、STEP 的统一运行关联（IR-003，纳入 A1，复用已有 CAD manifest）

## 阶段 3：小样本检索

- [x] 定义样本 manifest：参数 JSON、IR、STEP、验证结果和来源（RET-001；单族 15 行，split 仍为 provisional_small_n）
- [x] 实现按零件类型、特征、孔位/接口和归一化尺寸的检索（RET-002；单族确定性参数距离基线已验收，split 仍为 provisional_small_n）
- [x] 完成 C1 检索级诊断（RET-003；固定环境运行、上游回归、结果/报告交叉核对和中枢验收均通过；公平 C2 尚未定义，端到端收益仍需等 APP-001）
- [ ] 规定检索示例如何进入 Prompt，并防止把示例直接当作真值（RET-004）

## 阶段 4：轻量版交付

- [x] 实现并审查云端/本地 LLM adapter/logger（APP-001-ADAPTER；已通过 R3-FIX 中枢验收）
- [x] 实现并合入 APP-001 第一阶段受控 runner（APP-001-RUNNER-001/R1/R2；R2-R6 修复合入 `main`，中枢独立复核通过）
- [x] 按 ADR-0014 运行 APP-001 第一阶段诊断批次（`app001-phase1-20261107-01`、`app001-phase1-20261107-02`；每批 36 条逻辑运行、物理 HTTP 未超过 108；IR/CAD/geometry/STEP 禁用）；第二批次的 envelope 缺失已定位并由 `APP-001-PHASE1-ENVELOPE-FIX` 修复、合入 `main`，旧批次仍仅作诊断证据；修复后正式批次待重新授权，详见 [`agent-work/reviews/APP-001-phase1-20261107-02-codex-review.md`](../agent-work/reviews/APP-001-phase1-20261107-02-codex-review.md)
- [x] 按接受的 ADR-0016 将生产 prompt/解析契约切换到 `app001-extraction.v3`；Python 3.11.18 离线验证通过；真实模型效果评测仍需新的唯一批次授权
- [x] 按接受的 ADR-0017 将生产 prompt/解析契约切换到 `app001-extraction.v4`；合入提交 `c18fd35` 已完成 Python 3.11.18 离线复核；真实模型效果评测仍需新的唯一批次授权
- [x] 实现最小集成连接层与严格构造门（APP-002-INTEGRATION-A1，`d6faf70`）；自动字段修复循环后置，不阻塞首次成功闭环
- [x] 建立 API、演示界面、部署说明和失败案例库的 C1 手动参数切片（APP-003-C1）
- [x] 接通自然语言产品状态机、确认流程与离线 envelope fixtures（APP-003-C2-NL-PRODUCT-FLOW；ADR-0023；`d839954` 已合入并验收）
- [x] 合入并收束已通过独立验收的离线产品确认 UI（APP-003-C3-PRODUCT-UI；`f105fc4`，浏览器/localhost/CAD 验收完成）
- [x] 审阅并批准 APP-003-LIVE-SCOPE 草案；为新建 CC 对话框生成独立实现工作单
- [x] `APP-003-LIVE-PREFLIGHT-20261114-02`：冻结 scope 已获批，formal preflight 与单独 live execution approval 均有记录；4/12 次真实请求完成，独立复核 `pass`，batch 只读；报告见 `agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-02/independent-review.md`
- [ ] 完成技术验收与交付记录（APP-004）

## APP-001 v5 收束与独立研究

- [x] v5 离线 prompt 候选与策略映射（APP-001-V5-PROMPT-CANDIDATE；独立审查通过并随激活链合入 `main`）
- [x] 项目负责人接受 ADR-0018 策略方向（2026-11-11）
- [x] 独立审查并合入 v5 版本化激活（APP-001-V5-ACTIVATION；`2c70225` 已在 `main`，中枢审查通过）
- [x] v5 真实模型效果评测（APP-001-V5-FORMAL-EFFECT-EVALUATION；唯一批次已执行，独立审查和 Codex 中枢最终验收通过，已合入并推送至 `main=95d1dcb`，合入后复验通过；v4 旧批次只读且不得混合统计）
  - 唯一批次 `app001-phase1-v5-20261111-01`：36 条逻辑记录、32 个真实模型响应、4 个 C1 请求前阻塞、48 次账本尝试；32 个 raw 文件实际位于批次根目录（`work/app001-runs/<batch_id>/`），不在授权指定的 `raw/` 子目录；长度/SHA-256 与留存元数据一致。历史文件未移动、改写或重跑。
  - 结果：32/32 响应解析通过；CAD-003 Schema 20/32 通过；决策 answer=20、ask=2、refuse=10；C2/IR/CAD/geometry/STEP 未运行。结果与限制见 `agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md`。
  - 收束期间修复入口摘要字段错配并增加测试；后续 runner raw 留存路径也窄修为未来正式运行精确写入 `batch/raw/`，新增真实文件路径断言。历史批次仍保持上述根目录布局，未重跑。合入后在 Python 3.11.18 下复验：LLM 842 项通过（8 项既有 FUSE skip）、Schema 17 项通过、runner 与 v5 入口 101 项通过（1 项既有 skip）；后续真实运行需新入口基线、新 batch ID 和单独授权。
- [x] final offline preflight：在 `993a5b1` 使用 Python 3.11.18 运行，12 组合、RET-002 索引校验、预算可行性 global=44/Ollama=26、批次目录不存在均通过；仅离线占位 ID，无正式 batch ID 或请求授权。
- [ ] 【deferred】APP-001-NEXT-REAL-MODEL-EVALUATION：12-run held-out 检索收益对照，独立研究，不再是 CAD 集成门。R2 与 CLI 补测已验收，代码保留；恢复须有明确假设、重验当前入口基线并由负责人批准具体 batch。ADR-0019 原 scope/预算不变。

## 验证分层与后续清单

- 首期单族确定性覆盖：复用 15 行目录、Schema/IR/CAD 回归，A1 只补连接层及隔离/失败语义，避免重复堆测试。
- 语言覆盖：主闭环后按真实用语与失败假设增加输入；不将条件/模型重复次数当独立需求，不以无限 prompt 对照代替集成。
- 稳定性：单独规划重复生成、并发、长时运行、输出隔离和失败恢复；当前固定环境回归不证明生产规模稳定。
- 跨族扩展：独立数据/许可证、Schema、IR 和几何契约验证，首期 deferred。
- 交付阻断：错误几何、关键参数丢失、错误放行、假成功；非关键措辞、额外语言、新对照设想及小幅指标波动留 backlog。冻结接口/策略变更仍须版本化与 ADR。
- 保留固定环境、单族、来源许可、螺纹近似及非制造认证限制。所有新真实模型整链请求须新 scope/输入/预算/batch/授权；历史批次只读。
