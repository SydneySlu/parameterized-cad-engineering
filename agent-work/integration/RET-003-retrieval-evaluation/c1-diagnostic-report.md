# RET-003 C1 检索级诊断报告

状态：`review`（等待 Codex 中枢独立审查）
任务：RET-003 里程碑 C1
日期：2026-11-04
协议版本：`RET-003.protocol.v0.1-draft`
查询集版本：`RET-003.query-set.v0-draft`

## 1. 执行范围与边界

本报告仅包含已获 Codex 中枢批准的 **C1 检索级诊断**：

- 3 个 held-out 主查询（逐例记录）
- 2 个接口诊断（分开报告，不计入主查询分母）
- 1 个结构化失败诊断
- 每个合法查询完成独立进程确定性复跑

**未执行**：C0 无检索、C2O 目录规则 oracle、公平 C2、权重敏感性分析。

**未测量**：端到端字段精确率、Schema 通过率、CAD 构造通过率、STEP 回读通过率。这些指标需要 APP-001 完成后的统一下游求解器，当前状态为 `not_measured`。

**数据边界**：
- Manifest: `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`
- 记录: 15 条（development 9 / retrieval_source 3 / heldout_evaluation 3）
- Policy: `RET-002.parametric_distance.v1`（冻结权重 0.2/0.5）
- Split: `provisional_small_n`（**不是正式 benchmark**）
- 候选: 仅 `retrieval_source` 3 条（bore_d = 6, 20, 50）

## 2. 主查询结果（3 个 held-out）

### 2.1 heldout-bore-012

- **查询样本**: `set_screw_shaft_collar/catalog-bore-012`
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池（设计正确）
- **独立进程确定性**: ✓ SHA-256 一致

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete |
|---:|---|---|---:|---:|---:|
| 1 | set_screw_shaft_collar/catalog-bore-020 | retrieval_source | 0.066333 | 0.066333 | 0.0 |
| 2 | set_screw_shaft_collar/catalog-bore-006 | retrieval_source | 0.167944 | 0.167944 | 0.0 |
| 3 | set_screw_shaft_collar/catalog-bore-050 | retrieval_source | 0.481222 | 0.481222 | 0.0 |

**字段误差（Top-1 vs 查询真值）**:

- `bore_d`: 8
- `outer_d`: 10
- `screw_d`: 0
- `screw_len`: 0
- `width`: 2
- `second_screw`: 0

**观察**: Top-1 是 `catalog-bore-020`（距离 0.066333）。

### 2.2 heldout-bore-035

- **查询样本**: `set_screw_shaft_collar/catalog-bore-035`
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池（设计正确）
- **独立进程确定性**: ✓ SHA-256 一致

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete |
|---:|---|---|---:|---:|---:|
| 1 | set_screw_shaft_collar/catalog-bore-020 | retrieval_source | 0.207444 | 0.207444 | 0.0 |
| 2 | set_screw_shaft_collar/catalog-bore-050 | retrieval_source | 0.207444 | 0.207444 | 0.0 |
| 3 | set_screw_shaft_collar/catalog-bore-006 | retrieval_source | 0.441722 | 0.441722 | 0.0 |

**字段误差（Top-1 vs 查询真值）**:

- `bore_d`: 15
- `outer_d`: 24
- `screw_d`: 2
- `screw_len`: 4
- `width`: 2
- `second_screw`: 0

**观察**: Top-1 是 `catalog-bore-020`（距离 0.207444）。

### 2.3 heldout-bore-080

- **查询样本**: `set_screw_shaft_collar/catalog-bore-080`
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池（设计正确）
- **独立进程确定性**: ✓ SHA-256 一致

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete |
|---:|---|---|---:|---:|---:|
| 1 | set_screw_shaft_collar/catalog-bore-050 | retrieval_source | 0.784444 | 0.284444 | 0.5 |
| 2 | set_screw_shaft_collar/catalog-bore-020 | retrieval_source | 1.199333 | 0.699333 | 0.5 |
| 3 | set_screw_shaft_collar/catalog-bore-006 | retrieval_source | 1.433611 | 0.933611 | 0.5 |

**字段误差（Top-1 vs 查询真值）**:

- `bore_d`: 30
- `outer_d`: 30
- `screw_d`: 2
- `screw_len`: 4
- `width`: 4
- `second_screw`: 1

**观察**: Top-1 是 `catalog-bore-050`（距离 0.784444）。

## 3. 接口诊断（2 个，分开报告）

### 3.1 diagnostic-source-bore-020

- **查询**: `set_screw_shaft_collar/catalog-bore-020`
- **Query status**: `catalog_validated`
- **Top-1**: `set_screw_shaft_collar/catalog-bore-020`（距离 0.000000）
- **独立进程确定性**: ✓ SHA-256 一致

**观察**: ✓ 目录内精确匹配返回自身，距离为 0，符合预期。

### 3.2 diagnostic-heldout-bore-080-boundary

- **查询**: `set_screw_shaft_collar/catalog-bore-080`
- **Query status**: `catalog_validated`
- **Top-1**: `set_screw_shaft_collar/catalog-bore-050`（距离 0.784444）
- **独立进程确定性**: ✓ SHA-256 一致

**观察**: ✓ held-out 查询未泄漏到候选池，无泄漏。

## 4. 结构化失败诊断

- **Base sample**: `set_screw_shaft_collar/catalog-bore-020`
- **Transformation**: remove normalized.outer_d at runtime
- **预期错误**: `RETRIEVAL_MISSING_FIELD`
- **实际错误**: `RETRIEVAL_MISSING_FIELD` ✓
- **Code**: `RETRIEVAL_MISSING_FIELD`
- **Stage**: `query`
- **Fields**: `['outer_d']`

**观察**: ✓ flat 查询缺少必填字段时，检索系统正确拒绝并返回结构化错误（嵌套 error.error 对象包含 code/stage/fields），未产生半成品结果。

## 5. 独立进程确定性验证

五个合法查询（3 个主查询 + 2 个接口诊断）各自在独立 OS 进程中复跑，检查 canonical JSON SHA-256：

| Query ID | Run 1 SHA-256 | Run 2 SHA-256 | 确定性 |
|---|---|---|---|
| heldout-bore-012 | f639132d727364ab... | f639132d727364ab... | ✓ PASS |
| heldout-bore-035 | eeaa0730643741c0... | eeaa0730643741c0... | ✓ PASS |
| heldout-bore-080 | 4f05ecce10ecceaa... | 4f05ecce10ecceaa... | ✓ PASS |
| diagnostic-source-bore-020 | c31eb9ba7c7074f0... | c31eb9ba7c7074f0... | ✓ PASS |
| diagnostic-heldout-bore-080-boundary | 4f05ecce10ecceaa... | 4f05ecce10ecceaa... | ✓ PASS |

**观察**: ✓ 所有查询在独立进程间产生完全相同的 canonical JSON（逐字节一致）。

## 6. 候选角色纯度

所有主查询和诊断查询返回的候选角色检查：

- **候选总数**: 15
- **retrieval_source**: 15/15
- **Held-out 泄漏**: 0 个（held-out 行未出现在任何结果中）

**角色纯度**: 15/15 = 100% `retrieval_source`（设计正确）

## 7. 已知限制与不声称项

### 7.1 数据与方法限制

- **单族 15 行**: 只有 `set_screw_shaft_collar`，候选仅 3 个 `retrieval_source` 行。
- **Provisional split**: 9/3/3 是临时分组，**不是正式 benchmark**；3 个 held-out 只能逐例描述，不能声称统计显著性或泛化率。
- **距离语义**: 参数近邻度，**不表示**几何等价、制造可行性、强度安全或生成质量。
- **固定权重**: 0.2/0.5 是预先固定的规则，未经 held-out 调参；本诊断不评估权重的收益或最优性。
- **单环境**: Python 3.11.18 / darwin。

### 7.2 不声称的收益

**C1 检索级诊断不测量**：
- 自然语言输入抽取准确率（需 APP-001 LLM 固定）
- Schema 字段精确率或完整输出通过率（需下游求解器）
- CAD 构造通过率或 STEP 回读通过率（需实际几何验证）
- 用户效用或制造成本收益（超出参数近邻范围）

**不能声称**：
- "C1 检索改善了 CAD 生成成功率"（CAD 未运行）
- "检索提升了自然语言理解"（语言输入未测试）
- "held-out 准确率 X%"（held-out 不在候选池，无法命中）
- "检索泛化到其他零件族"（只有单族）

## 8. 执行与审查说明

本报告由正式 C1 机器结果 JSON 自动生成。诊断脚本在正式运行前已完成接口、错误结构、独立进程复跑和 fail-closed 修正；早期 JSON/报告属于历史无效产物，不作为本次结果依据。

- 正式结果仅来自 Python 3.11.18 / macOS arm64 固定环境运行。
- 本报告的逐例数值、结构化失败诊断和确定性结果均从同目录 JSON 读取；交叉核对器已对两者一致性及 stage/fields 负例变异进行验证。

## 9. 结论

### 9.1 通过的检查

- ✓ Manifest hash 校验通过
- ✓ 契约测试通过（results 字段、query_status 层级、缺字段拒绝、角色纯度及环境门）
- ✓ 3 个主查询成功执行，held-out 行未泄漏到候选池
- ✓ 2 个接口诊断分开记录，行为符合预期
- ✓ 结构化失败诊断返回预期错误码 `RETRIEVAL_MISSING_FIELD`
- ✓ 候选角色纯度 100%（所有候选均为 `retrieval_source`）
- ✓ 独立进程确定性验证通过（5/5 查询 SHA-256 一致）

### 9.2 逐例主查询摘要

| Query ID | Truth Sample | Query Status | Top-1 | Top-1 Distance | Deterministic |
|---|---|---|---|---:|---|
| heldout-bore-012 | catalog-bore-012 | catalog_validated | catalog-bore-020 | 0.066333 | ✓ |
| heldout-bore-035 | catalog-bore-035 | catalog_validated | catalog-bore-020 | 0.207444 | ✓ |
| heldout-bore-080 | catalog-bore-080 | catalog_validated | catalog-bore-050 | 0.784444 | ✓ |

### 9.3 下一步

RET-003 C1 诊断任务状态设为 `review`，等待 Codex 中枢独立审查：
- 验证修正后的接口使用和独立进程复跑
- 核对逐例结果、角色隔离和距离计算
- 确认未运行 C0/C2O/公平 C2，未调权重，未声称端到端收益
- 验证文件边界和限制说明

审查通过后，本报告和结果文件作为 RET-003 里程碑 C1 的交付物。正式多条件评测待 APP-001 和后续放行。
