# 下一阶段 Agent Prompt 顺序

本文件描述 DATA-003 审查通过后的任务分配顺序。当前只生成 Prompt，不代表这些任务已经启动或完成。

## 已有前置成果

- DATA-003 已完成 `set_screw_shaft_collar` 的来源审计、macOS arm64 环境核验、官方 validate、合法/边界/非法参数 smoke、STEP 回读和重复性记录。
- DATA-003 发现：`check()` 必须先于 `build()`；原生 `build()` 可能接受非法参数并生成多实体结果。
- DATA-003 的 manifest 仍是审计草案，不是冻结 Schema 或 Typed CAD IR。
- 源码快照标记为 `reproducibility_partial`；生成资产和第三方资料的公开许可证仍需单独审查。

## 分配顺序和决策门

### 1. CAD-003：Schema 与规则契约

先依据 DATA-003 审计材料，把族级参数、字段来源、单位、目录行耦合、缺失字段、边界和错误码整理为 Schema v0。这个 Agent 可以实现 Pydantic/JSON Schema 和纯参数规则测试，但不能实现 CAD 构造器或 Typed CAD IR。

通过条件：Schema 能表达首族的合法目录行、关键派生字段、`second_screw` 约束、壁厚/几何前置规则和可解释错误；不把审计草案误称为跨族通用 Schema。

### 2. IR-001：Typed CAD IR v0 设计与复核

Schema 通过后，由 Codex/独立设计 Agent 定义 IR v0：特征节点、参数、单位、来源、依赖、约束、族扩展、错误码、版本和序列化示例。此阶段先不实现 CadQuery 编译器。

通过条件：IR 能忠实表示首族，不把 `build()` 自由代码直接塞入 IR；能区分用户显式输入、目录派生值、规则拒绝和几何验证结果；为第二族保留明确扩展点但不提前泛化。

### 3. CAD-005/006：确定性构造器与验证器

IR v0 经过 Codex 审查后，由 CC 实现白名单 CadQuery/OCP 构造器和几何/STEP/族规则验证器。构造前执行 Schema/规则检查，构造后执行实体有效性、单实体、关键几何量、STEP 回读和错误分类。

通过条件：同一 IR/参数/软件版本可以重复构造；合法输入能导出并回读 STEP；非法输入不会仅因 STEP 导出成功而通过；失败原因能定位到字段、规则、构造或回读阶段。

### 4. DATA-004：第二族完整 smoke 与 adapter 边界核验

主链稳定后，再对 `slotted_din_rail` 或 `speaker_pole_mount_socket` 做完整项目侧 smoke。该 Agent 只验证第二族的来源、参数、构造、STEP 回读和与 IR/Schema 的映射差异，不自行改写 IR 或扩大首期范围。

通过条件：明确哪些字段和验证规则可以复用，哪些必须由族扩展表达；保留 `slotted_din_rail` 目录名与 `family_id` 不一致等适配风险。

## 暂不分配

LLM/Prompt、检索库和端到端有限修复循环暂不先行。它们应在至少一个族的确定性主链通过后，使用冻结的 Schema、IR、验证错误码和固定测试集，避免 Prompt 实验掩盖 CAD 主链问题。
