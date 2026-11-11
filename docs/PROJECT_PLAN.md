# 项目计划

本计划用于跨 Agent 和跨设备同步，不替代详细技术方案。每次范围变化必须同步 `docs/DECISIONS.md`。

轻量版首期的 Agent 分工、边界、依赖和阶段性交付见 [`docs/coordination/agent-work-allocation.md`](coordination/agent-work-allocation.md)。各阶段 Prompt 和交接记录按任务保存在 `docs/coordination/prompts/` 及其历史归档目录中。

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
- [ ] 建立 BenchCAD 多族数据优先试点：锁定具体 commit，检查许可/状态/环境，先用两个结构不同的社区族跑通 smoke test，再决定是否扩展到更多族（DATA-002；建议见 [`database/benchcad-dataset-first-plan-2026-10.md`](../database/benchcad-dataset-first-plan-2026-10.md)）
- [x] 完成第一个单族来源、环境与最小 smoke test 纵向切片（DATA-003；审计与 R2 许可证/快照补充已完成）
- [x] 项目负责人确认数据优先路线和首期族数量（CAD-001；首期为 `set_screw_shaft_collar`）
- [x] 冻结首期 BenchCAD 社区族集合、支持任务和不支持项（CAD-002；决策见 ADR-0007）
- [ ] 定义跨族 manifest/adapter 与参数 Schema 映射、单位、来源和缺失字段（CAD-003）
- [ ] 按族、目录行和 near-duplicate group 建固定评测切分，避免实例泄漏（CAD-004）

## 阶段 2：Typed CAD IR 和确定性主线

- [ ] 设计 IR v0：特征节点、参数、单位、依赖、约束和来源（IR-001）
- [ ] 设计特征 ID、引用和错误码（IR-002）
- [x] 建立白名单 CadQuery/OCP 编译器（CAD-005；canonical 输入绑定经中枢复核，固定环境测试通过）
- [x] 建立实体有效性、STEP 回读和零件族规则验证器（CAD-006；冻结容差策略实现并通过固定环境标准/边界/失败路径测试）
- [ ] 建立输入、IR、构造、验证、输出的版本化运行日志（IR-003）

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
- [ ] 实现有限验证和字段修复循环（APP-002）
- [ ] 建立 API、演示界面、部署说明和失败案例库（APP-003）
- [ ] 完成技术验收与交付记录（APP-004）

## APP-001 v5 后续门

- [x] v5 离线 prompt 候选与策略映射（APP-001-V5-PROMPT-CANDIDATE；独立审查通过并随激活链合入 `main`）
- [x] 项目负责人接受 ADR-0018 策略方向（2026-11-11）
- [x] 独立审查并合入 v5 版本化激活（APP-001-V5-ACTIVATION；`2c70225` 已在 `main`，中枢审查通过）
- [x] v5 真实模型效果评测（APP-001-V5-FORMAL-EFFECT-EVALUATION；唯一批次已执行，独立审查和 Codex 中枢最终验收通过，已合入并推送至 `main=95d1dcb`，合入后复验通过；v4 旧批次只读且不得混合统计）
  - 唯一批次 `app001-phase1-v5-20261111-01`：36 条逻辑记录、32 个真实模型响应、4 个 C1 请求前阻塞、48 次账本尝试；32 个 raw 文件实际位于批次根目录（`work/app001-runs/<batch_id>/`），不在授权指定的 `raw/` 子目录；长度/SHA-256 与留存元数据一致。历史文件未移动、改写或重跑。
  - 结果：32/32 响应解析通过；CAD-003 Schema 20/32 通过；决策 answer=20、ask=2、refuse=10；C2/IR/CAD/geometry/STEP 未运行。结果与限制见 `agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md`。
  - 收束期间修复入口摘要字段错配并增加测试；后续 runner raw 留存路径也窄修为未来正式运行精确写入 `batch/raw/`，新增真实文件路径断言。历史批次仍保持上述根目录布局，未重跑。合入后在 Python 3.11.18 下复验：LLM 842 项通过（8 项既有 FUSE skip）、Schema 17 项通过、runner 与 v5 入口 101 项通过（1 项既有 skip）；后续真实运行需新入口基线、新 batch ID 和单独授权。
- [ ] 后续 v5 真实模型评测（APP-001-NEXT-REAL-MODEL-EVALUATION；ADR-0019 输入/标签映射已复核；runner API gate/approval 门和预算公式修复已通过 R1 复验；R2 修复 offline-preflight 在缺少 RET-002 index 时误报 pass（`retrieval_config_check=skipped`），现 `offline_preflight()` 在索引缺失/错误时 fail closed，CLI 改用 `_load_retrieval_index_or_fail()`；新增 13 项 `TestRetrievalPreflightFailClosed` 测试。Python 3.10.12 下 heldout 83 项、回归 120 项（7 skips）、LLM 全量 938 项（8 skips）、Schema 17 项通过。须在 Python 3.11.18 下复验后进行 final offline preflight；无 batch ID/模型请求授权）
