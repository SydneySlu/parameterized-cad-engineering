# 任务看板

状态：`planned` / `in_progress` / `blocked` / `review` / `done` / `deferred`。

| ID | 任务 | 负责人 | 状态 | 依赖 | 验收条件 |
|---|---|---|---|---|---|
| INFRA-001 | Git 初始化与协作协议 | Codex | done | - | 仓库可提交，所有 Agent 有统一入口 |
| INFRA-002 | 状态、计划、决策、日志骨架 | Codex | done | INFRA-001 | 文件存在且互相链接 |
| INFRA-003 | 远程仓库与跨设备同步 | 用户 + Codex | review | GitHub 仓库 URL | 本机首次 push 成功；新设备 clone/pull 待验证 |
| INFRA-004 | Agent 配置入口 | Codex + 用户 | planned | INFRA-003 | Codex/CC/DSH 可找到同一状态和任务 |
| INFRA-005 | 中枢编排、阶段性同步和仓库体检 | Codex | done | INFRA-001 | 有 prompt 模板、checkpoint 规则和体检脚本 |
| INFRA-006 | 中枢私有审查台账与独立复核约定 | Codex | done | INFRA-005 | 仓库外台账已建立，事实源与复核边界写入决策记录 |
| INFRA-007 | 轻量版 Agent 分工与依赖初步规划 | Codex | done | INFRA-006 | 分工、边界、阶段和接口依赖已写入协调文档 |
| INFRA-008 | 迁移共享项目基座并建立 Agent 工作区 | Codex | done | INFRA-007 | 目标目录、职责子目录和路径规则已写入协作协议 |
| DATA-001 | 开源数据源适配性初评 | Codex | review | - | 对 BenchCAD 2.0、CADBench、Seek-CAD 完成数据结构、适配度与许可边界比较；报告见 `database/cad-dataset-suitability-2026-10.md` |
| DATA-002 | BenchCAD 数据优先接入计划与族级试审 | Codex + 用户/导师 | review | DATA-001 | 首期范围收缩为 `set_screw_shaft_collar`；后续扩族另行决策；计划见 `database/benchcad-dataset-first-plan-2026-10.md` |
| DATA-003 | BenchCAD 首族来源、环境与许可证边界 | DATA-003 Agent + Codex | done | DATA-002 | 固定源 commit；完成干净快照或如实保留 partial；核对生成 STEP/渲染物和第三方材料许可；输出更新 manifest 与 checkpoint；Codex 独立复审通过 |
| CAD-001 | 候选零件族比较 | Codex | done | - | 有数据/规则/应用/生成难点对比 |
| CAD-002 | 冻结首期零件族 | 项目负责人 + Codex | done | CAD-001 | ADR-0007 明确 `set_screw_shaft_collar`、固定 commit 和不支持项 |
| CAD-003 | 参数 Schema v0 | CC（Schema/规则角色） | planned | CAD-002 | 有字段、单位、边界、来源和缺失规则 |
| CAD-004 | 评测集切分 | Codex + CC | planned | CAD-002 | 模板近重复不会跨训练/测试泄漏 |
| IR-001 | Typed CAD IR v0 设计与复核 | Codex（设计）+ 独立复核 Codex | review | CAD-003 | 有规范、示例、版本和错误码 |
| CAD-005 | 确定性 CAD 编译器 | 原 CAD-005/006 Agent（CC）+ Codex | done | IR-001, DATA-003 | `df78f4f` 固定七节点输入/图绑定；13 项 CAD 编译测试及独立中枢复核通过 |
| CAD-006 | 几何与规则验证器 | 原 CAD-005/006 Agent（CC）+ Codex | done | CAD-005, DATA-003 | CAD-006.geometry-comparison.v1 未变；标准/边界/native/STEP 与失败路径测试通过；跨平台仍未验证 |
| RET-001 | 检索样本 manifest | DSH + CC + Codex | done | CAD-006 | 15 个首族目录行的 manifest、IR、构造、验证、来源和 hash 可追溯；中枢复核通过，限制见 `agent-work/reviews/RET-001-codex-review.md` |
| RET-002 | 单族确定性检索基线 | CC + DSH + Codex | done | RET-001 | 单族参数距离、候选角色、稳定排序和结构化失败路径通过中枢复核；策略范围修正已验收，限制见 `agent-work/reviews/RET-002-codex-review.md` |
| RET-003 | 单族检索诊断与下游收益评测 | Codex + CC | in_progress | RET-001 | 里程碑 1 协议已通过复审；当前仅允许 C1 检索级诊断；公平端到端比较待 APP-001，公平 C2 尚未定义 |
| APP-001-PREP | 冻结模型基线、输入输出契约与小型验收集 | LLM Agent + Codex + 用户 | done | ADR-0009/0010/0011/0012/0013、CAD-003/IR/CAD 主链 | 冻结 `app001-io.v1` / `app001-extraction.v2` 和 9 条 evaluator-only 样例；最终中枢验收通过 |
| APP-001-ADAPTER | 双基线执行适配器与分阶段运行记录 | CC + Codex | done | APP-001-PREP 冻结契约 | R3-FIX 已中枢验收；详情见 `agent-work/reviews/APP-001-ADAPTER-R3-FIX-codex-review.md` |
| APP-001-RUNNER | 第一阶段受控运行入口与预算/模型身份边界 | CC + Codex | review | APP-001-PREP、APP-001-ADAPTER、ADR-0014 | `APP-001-RUNNER-001`、R1、R2 已推送；R2 等待独立只读安全复核。复核前不得启动正式请求；交接见 `agent-work/llm/APP-001-runner-R2/` |
| APP-001 | LLM 结构化抽取与 Prompt 对照（Phase 1） | Codex + 用户 | planned | APP-001-RUNNER-R2 复核通过 | 用户已授权 9 样例×C0/C1×双模型，共 36 逻辑运行、最多 108 次请求；IR/CAD/geometry/STEP 禁用。待 runner 安全复核通过后启动 |
| APP-002 | 轻量版有限修复循环 | CC（CAD 执行角色） + LLM Agent | planned | CAD-006 | 失败字段可回传并有界重试 |
| APP-003-C1 | 最小本地 Web 演示：参数确认→隔离 CAD/STEP 生成→证据查看/下载/重生成 | CC 实现 / Codex 中枢独立验收 | done | APP-002 A1/A2、里程碑 B、ADR-0022 | 已合入并推送至 `main=07a98d1`；固定 CAD venv 测试、真实 localhost HTTP/STEP、安全、失败阻断和 run 隔离复核通过。独立审查记录见 `agent-work/reviews/APP-003-C1-codex-review.md` |
| APP-003-C2-NL-PRODUCT-FLOW | 自然语言产品流程：offline v5 envelope→确认/补充→Schema/IR/CAD/STEP→证据与隔离 | 已有 C1 CC 对话框 / Codex 中枢独立验收 | done | APP-003-C1、ADR-0023 | `d839954` 已合入；固定 CAD venv 回归与真实 localhost HTTP/STEP 流程通过。仅 synthetic fixtures，不构成模型效果证据。 |
| APP-003-C3-PRODUCT-UI | C2 API 的离线自然语言确认界面 | 已有 C1/C2 CC 对话框实现 / Codex 中枢独立验收 | planned | APP-003-C2、ADR-0023 | 工作单已定义：`docs/coordination/prompts/APP-003-C3-product-ui-cc.md`。离线 fixtures；不接模型、不读取密钥、不创建 batch。验收后再准备新的产品 live extraction scope。 |

## 认领格式

在聊天中认领后，追加到 `docs/WORKLOG.md`：

```text
[YYYY-MM-DD HH:MM] agent=<id> task=<id> status=in_progress
scope=<本次改动范围>
next=<完成后的下一步>
```
