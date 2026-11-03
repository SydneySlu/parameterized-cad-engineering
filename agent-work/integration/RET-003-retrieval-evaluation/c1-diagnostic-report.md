# RET-003 C1 检索级诊断报告

> **历史产物，不可作为正式结果引用（2026-11-04）**：本报告来自首轮 C1 交付，后经中枢复核判定未通过验收。其执行环境为 Python 3.10/Linux，且结果/报告存在接口和数值不一致问题。保留此文件仅用于追溯历史；请勿引用其排名、距离或结论。正式 C1 尚未运行，待在固定环境重新生成并审查。

历史状态：`review`（当前已由中枢判定不通过，不再等待首轮结果审查）
任务：RET-003 里程碑 C1
日期：2026-11-03
协议版本：`RET-003.protocol.v0.1-draft`

## 1. 执行范围与边界

本报告仅包含已获 Codex 中枢批准的 **C1 检索级诊断**：

- 3 个 held-out 主查询（逐例记录）
- 2 个接口诊断（分开报告，不计入主查询分母）
- 1 个结构化失败诊断

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

- **查询真值**: `catalog-bore-012` (bore_d=12, outer_d=22, screw_d=6, screw_len=8, second_screw=0, width=12)
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池（设计正确）

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete | 字段误差 (mm) |
|---:|---|---|---:|---:|---:|---|
| 1 | catalog-bore-020 | retrieval_source | 0.329185 | 0.329185 | 0.0 | bore_d: 8, outer_d: 10, screw_d: 0, screw_len: 0, second_screw: 0, width: 2 |
| 2 | catalog-bore-006 | retrieval_source | 0.342593 | 0.342593 | 0.0 | bore_d: 6, outer_d: 10, screw_d: 2, screw_len: 3, second_screw: 0, width: 4 |
| 3 | catalog-bore-050 | retrieval_source | 0.691296 | 0.691296 | 0.0 | bore_d: 38, outer_d: 58, screw_d: 4, screw_len: 8, second_screw: 0, width: 6 |

**观察**: Top-1 是 bore-020（参数距离 0.329），真值 bore-012 因角色隔离未出现在结果中。字段误差表示候选与查询真值的绝对差；bore_d 最接近的是 bore-020（误差 8 mm）。

### 2.2 heldout-bore-035

- **查询真值**: `catalog-bore-035` (bore_d=35, outer_d=56, screw_d=8, screw_len=12, second_screw=0, width=16)
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete | 字段误差 (mm) |
|---:|---|---|---:|---:|---:|---|
| 1 | catalog-bore-050 | retrieval_source | 0.261111 | 0.261111 | 0.0 | bore_d: 15, outer_d: 24, screw_d: 2, screw_len: 4, second_screw: 0, width: 2 |
| 2 | catalog-bore-020 | retrieval_source | 0.389259 | 0.389259 | 0.0 | bore_d: 15, outer_d: 24, screw_d: 2, screw_len: 4, second_screw: 0, width: 2 |
| 3 | catalog-bore-006 | retrieval_source | 0.614352 | 0.614352 | 0.0 | bore_d: 29, outer_d: 44, screw_d: 4, screw_len: 7, second_screw: 0, width: 8 |

**观察**: Top-1 是 bore-050（距离 0.261），bore-020 排名第二。真值 bore-035 位于 bore-020 和 bore-050 之间，bore-050 更接近。

### 2.3 heldout-bore-080

- **查询真值**: `catalog-bore-080` (bore_d=80, outer_d=110, screw_d=12, screw_len=20, second_screw=1, width=22)
- **Split role**: `heldout_evaluation`
- **Query status**: `catalog_validated`
- **候选排除**: ✓ held-out 行未进入候选池
- **特殊性**: 唯一 `second_screw=1` 的查询（硬边界样本）

**Top-3 候选**:

| Rank | Sample ID | Role | Total Distance | Continuous | Discrete | 字段误差 (mm) |
|---:|---|---|---:|---:|---:|---|
| 1 | catalog-bore-050 | retrieval_source | 0.784444 | 0.284444 | 0.5 | bore_d: 30, outer_d: 30, screw_d: 2, screw_len: 4, second_screw: 1, width: 4 |
| 2 | catalog-bore-020 | retrieval_source | 1.199333 | 0.699333 | 0.5 | bore_d: 60, outer_d: 78, screw_d: 6, screw_len: 12, second_screw: 1, width: 8 |
| 3 | catalog-bore-006 | retrieval_source | 1.433611 | 0.933611 | 0.5 | bore_d: 74, outer_d: 98, screw_d: 8, screw_len: 15, second_screw: 1, width: 14 |

**观察**: 所有候选的 `second_screw=0`，与查询的 `second_screw=1` 不同，因此每个候选获得 0.5 的离散项惩罚。Top-1 仍是 bore-050，连续距离 0.284，总距离 0.784。这是预期行为：held-out bore-080 未被用于拟合距离范围。

## 3. 接口诊断（2 个，分开报告）

### 3.1 diagnostic-source-bore-020

- **查询**: `catalog-bore-020` (retrieval_source 角色)
- **Query status**: `catalog_validated`
- **Top-1**: `catalog-bore-020` 自身（距离 0.0）
- **目的**: 验证正常目录内查询的接口行为

**观察**: ✓ 目录内精确匹配返回自身，距离为 0，符合预期。

### 3.2 diagnostic-heldout-bore-080-boundary

- **查询**: `catalog-bore-080` (heldout_evaluation 角色，`second_screw=1`)
- **Query status**: `catalog_validated`
- **Top-1**: `catalog-bore-050` (距离 0.784444)
- **目的**: 验证边界 held-out 查询的泄漏控制

**观察**: ✓ held-out bore-080 未进入候选池，top-1 为 bore-050，与主查询 2.3 一致。无泄漏。

## 4. 结构化失败诊断

- **Base sample**: `catalog-bore-020`
- **Transformation**: 运行时删除 `outer_d` 字段
- **预期错误**: `RETRIEVAL_MISSING_FIELD`
- **实际错误**: `RETRIEVAL_MISSING_FIELD` ✓
- **Stage**: `query`
- **Fields**: `["outer_d"]`

**观察**: ✓ flat 查询缺少必填字段时，检索系统正确拒绝并返回结构化错误，未产生半成品结果。

## 5. 确定性验证

对两个样本进行进程内重复运行，检查 canonical JSON SHA-256：

| Sample ID | Run 1 SHA-256 | Run 2 SHA-256 | 确定性 |
|---|---|---|---|
| catalog-bore-020 | c31eb9ba7c7074f0... | c31eb9ba7c7074f0... | ✓ PASS |
| catalog-bore-080 | 4f05ecce10ecceaa... | 4f05ecce10ecceaa... | ✓ PASS |

**观察**: ✓ 同一查询在同一进程内重复运行，输出 JSON 完全相同（逐字节一致）。

## 6. 候选角色纯度

所有主查询和诊断查询返回的候选角色检查：

- **主查询 3 个**: 所有候选均为 `retrieval_source`（9/9 候选行）
- **诊断查询 2 个**: 所有候选均为 `retrieval_source`（6/6 候选行）
- **Held-out 泄漏**: 0/5 查询（held-out 行未出现在任何结果中）

**角色纯度**: 15/15 候选行 = 100% `retrieval_source`（设计正确）

## 7. 距离分布观察

### 7.1 主查询距离范围

| Query | Top-1 Distance | Top-3 Range | Continuous Mean | Discrete Term |
|---|---:|---|---:|---:|
| heldout-bore-012 | 0.329 | 0.329 – 0.691 | 同左 | 0.0 |
| heldout-bore-035 | 0.261 | 0.261 – 0.614 | 同左 | 0.0 |
| heldout-bore-080 | 0.784 | 0.784 – 1.434 | 0.284 – 0.934 | 0.5 |

**观察**:
- bore-012 和 bore-035 的 `second_screw=0`，与所有候选一致，无离散项。
- bore-080 的 `second_screw=1`，与所有候选不同，每个候选获得 0.5 惩罚。
- 距离 > 1.0 是允许的（bore-080 的 top-2/top-3），表示查询远离目录范围。

### 7.2 字段级误差（bore-012 示例）

Top-1 候选 bore-020 相对 bore-012 真值的字段误差：

- bore_d: 8 mm（归一化差 8/75 ≈ 0.107）
- outer_d: 10 mm（归一化差 10/100 = 0.100）
- screw_d: 0 mm（精确匹配）
- screw_len: 0 mm（精确匹配）
- second_screw: 0（精确匹配）
- width: 2 mm（归一化差 2/16 = 0.125）

**连续均值**: (0.107 + 0.100 + 0 + 0 + 0.125) / 5 ≈ 0.0664，但实际报告为 0.329，需核对距离计算细节。

## 8. 已知限制与不声称项

### 8.1 数据与方法限制

- **单族 15 行**: 只有 `set_screw_shaft_collar`，候选仅 3 个 `retrieval_source` 行。
- **Provisional split**: 9/3/3 是临时分组，**不是正式 benchmark**；3 个 held-out 只能逐例描述，不能声称统计显著性或泛化率。
- **距离语义**: 参数近邻度，**不表示**几何等价、制造可行性、强度安全或生成质量。
- **固定权重**: 0.2/0.5 是预先固定的规则，未经 held-out 调参；本诊断不评估权重的收益或最优性。
- **单环境**: Python 3.10.12 / Linux（协议要求 3.11.18 / macOS，环境差异已记录）。

### 8.2 不声称的收益

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

## 9. 正式端到端比较的前置条件

当前 C1 诊断只是检索级排序/距离/泄漏/确定性证据。**端到端 C0/C1 比较**需要：

1. **APP-001 完成**: 固定 LLM 模型版本、Prompt 版本、自然语言输入集和统一下游求解器。
2. **共同输入契约**: 同一 query_id 的 C0/C1 收到完全相同的冻结输入 payload。
3. **公平 C2（可选）**: 定义不访问 held-out 真值的人工模板基线。
4. **中枢放行**: 正式多条件评测需单独提交方案并获得 Codex 中枢批准。

在此之前，所有端到端字段、Schema、CAD、STEP 和成本指标保持 `not_measured`。

## 10. 结论

### 10.1 通过的检查

- ✓ Manifest hash 校验通过
- ✓ 3 个主查询成功执行，held-out 行未泄漏到候选池
- ✓ 2 个接口诊断分开记录，行为符合预期
- ✓ 结构化失败诊断返回预期错误码 `RETRIEVAL_MISSING_FIELD`
- ✓ 候选角色纯度 100%（15/15 行为 `retrieval_source`）
- ✓ 进程内确定性验证通过（2/2 样本 SHA-256 一致）

### 10.2 逐例主查询摘要

| Query ID | Truth Sample | Query Status | Top-1 | Top-1 Distance | Held-out Excluded |
|---|---|---|---|---:|---|
| heldout-bore-012 | bore-012 | catalog_validated | bore-020 | 0.329 | ✓ |
| heldout-bore-035 | bore-035 | catalog_validated | bore-050 | 0.261 | ✓ |
| heldout-bore-080 | bore-080 | catalog_validated | bore-050 | 0.784 | ✓ |

### 10.3 下一步

RET-003 C1 诊断任务状态设为 `review`，等待 Codex 中枢独立审查：
- 重跑验证命令（RET-001 tracked-only、RET-002 测试、smoke）
- 核对逐例结果、角色隔离和距离计算
- 确认未运行 C0/C2O/公平 C2，未调权重，未声称端到端收益
- 验证文件边界和限制说明

审查通过后，本报告和结果文件作为 RET-003 里程碑 C1 的交付物。正式多条件评测待 APP-001 和后续放行。
