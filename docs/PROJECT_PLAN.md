# 项目计划

本计划用于跨 Agent 和跨设备同步，不替代详细技术方案。每次范围变化必须同步 `docs/DECISIONS.md`。

轻量版首期的 Agent 分工、边界、依赖和阶段性交付见 [`docs/coordination/agent-work-allocation.md`](coordination/agent-work-allocation.md)。当前只完成初步规划，尚未生成初始化 prompt 或正式认领任务。

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

- [x] 初评 BenchCAD 2.0、CADBench、Seek-CAD 的数据适配性与许可边界（DATA-001；结论见 `docs/research/cad-dataset-suitability-2026-10.md`）
- [ ] 建立 BenchCAD 多族数据优先试点：锁定具体 commit，检查许可/状态/环境，先用两个结构不同的社区族跑通 smoke test，再决定是否扩展到更多族（DATA-002；建议见 `docs/research/benchcad-dataset-first-plan-2026-10.md`）
- [ ] 导师确认数据优先路线和首期族数量（CAD-001）
- [ ] 冻结首期 BenchCAD 社区族集合、支持任务和不支持项（CAD-002）
- [ ] 定义跨族 manifest/adapter 与参数 Schema 映射、单位、来源和缺失字段（CAD-003）
- [ ] 按族、目录行和 near-duplicate group 建固定评测切分，避免实例泄漏（CAD-004）

## 阶段 2：Typed CAD IR 和确定性主线

- [ ] 设计 IR v0：特征节点、参数、单位、依赖、约束和来源（IR-001）
- [ ] 设计特征 ID、引用和错误码（IR-002）
- [ ] 建立白名单 CadQuery/OCP 编译器（CAD-005）
- [ ] 建立实体有效性、STEP 回读和零件族规则验证器（CAD-006）
- [ ] 建立输入、IR、构造、验证、输出的版本化运行日志（IR-003）

## 阶段 3：小样本检索

- [ ] 定义样本 manifest：参数 JSON、IR、渲染图、STEP、验证结果和来源（RET-001）
- [ ] 实现按零件类型、特征、孔位/接口和归一化尺寸的检索（RET-002）
- [ ] 评估无检索、检索和人工模板三种条件（RET-003）
- [ ] 规定检索示例如何进入 Prompt，并防止把示例直接当作真值（RET-004）

## 阶段 4：轻量版交付

- [ ] 接入云端/本地 LLM，统一结构化输出协议（APP-001）
- [ ] 实现有限验证和字段修复循环（APP-002）
- [ ] 建立 API、演示界面、部署说明和失败案例库（APP-003）
- [ ] 完成技术验收与交付记录（APP-004）

