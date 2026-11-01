# CAD-005/006 续任 Agent（CAD-005 执行 Agent） 定向复核记录

日期：2026-11-01
状态：`pass` — 前序任务接口完整、可安全继续实现

## 复核清单

### 1. 前序任务与 checkpoint

| 任务 | 状态 | Checkpoint 时间 | 关键交付 |
|---|---|---|---|
| DATA-003 | review | 2026-11-01 | 单族 smoke、环境、候选矩阵 |
| CAD-003 | review | 2026-10-31 | Schema v0、Python 规则实现、17 个测试 pass |
| IR-001 | review | 2026-11-01 | IR v0 spec、Schema、5 个示例 |

### 2. 前序文件格式与完整性

**✓ 检查通过：**

- `agent-work/data/DATA-003-single-family-audit/checkpoint.md`：完整记录来源审计、环境、smoke 结果和重复性指标；明确标注已知限制和 reproducibility_partial 状态
- `agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md`：17 个单元测试均 pass，Python 验证实现与规则完整
- `agent-work/typed-cad-ir/IR-001-v0/checkpoint.md`：IR Schema JSON、5 个示例均通过 Draft 2020-12 验证，语义检查规则明确
- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md`：完整规范文档，包含版本、参数模型、节点类型、约束和错误协议

### 3. 核心命令复现

**✓ 测试脚本：** `/mnt/outputs/test_handoff.py`  
**✓ 环境：** CadQuery 2.3.0 + OCP 7.9.3.0 + Python 3.10  
**✓ BenchCAD 来源：** `work/benchcad-source/benchcad-2-035f467-raw/`（DATA-003-R1 raw 快照）

**✓ 命令及结果：**

```bash
cd work/benchcad-source/benchcad-2-035f467-raw && \
  PYTHONPATH=.:./framework python3 test_handoff.py

# 输出
✓ legal_case: check PASS, build OK (1 solid)
✓ boundary_case: check PASS, build OK (1 solid, second_screw=1)
✓ invalid_constraint: REJECTED as expected
✓ invalid_geometry: REJECTED as expected
总体结果: ✓ PASS
```

### 4. 正常案例验证

**✓ legal_catalog_row (bore_d=20, second_screw=0)：**
- `spec.check()` 通过，无错误
- `part.build()` 成功，返回 1 个 solid
- 与 DATA-003 run-log 结果一致

**✓ legal_hard_boundary (bore_d=80, second_screw=1)：**
- `spec.check()` 通过，无错误
- `part.build()` 成功，返回 1 个 solid
- 条件第二孔参数正确传递
- 与 DATA-003 run-log 结果一致

### 5. 失败案例验证

**✓ invalid_check_coupling (second_screw=1 但 bore_d=20)：**
- `spec.check()` 返回拒绝，未通过
- 拒绝原因：`second_screw set below d1 > 70`

**✓ invalid_geometry (outer_d=19 < bore_d=20)：**
- `spec.check()` 返回拒绝，未通过
- 拒绝原因：wall thickness 约束

### 6. 输入输出接口确认

**✓ CAD-003 参数输入格式：**
- 6 个参数：`bore_d, outer_d, screw_d, screw_len, second_screw, width`
- `bore_d` 必填，其余 5 个可由目录或规则派生
- 长度单位 mm，`second_screw` 无量纲整数

**✓ spec.check() 输出格式：**
- 返回 error 列表（空 = 通过，非空 = 拒绝）
- 错误含有稳定错误码（e.g., `CATALOG_MISMATCH`, `WALL_THICKNESS_TOO_SMALL`）

**✓ part.build() 输出格式：**
- 返回 CadQuery Solid 对象
- 支持 `.exportStep()` 方法进行 STEP 导出

### 7. 已知限制确认

**✓ 从前序 checkpoint 继承的限制：**

1. STEP 字节 hash 不稳定（DATA-003-R1 已验证）
   - 两次运行的几何/实体指标相同，文件字节哈希不同
   - CAD-006 验证器不应使用字节哈希作为唯一标准

2. M3–M8 螺纹可能 no-op（IR-001 源注释）
   - `thread_model=revolved_ring_approximation` 不声称真实螺旋
   - CAD-006 验证器应检查是否符合预期

3. outer_d < bore_d 时原生 build 产生 3 solids（DATA-003 验证）
   - 约束检查必须先于 build
   - STEP 导出成功不能覆盖规则拒绝

4. Source snapshot 仍为 reproducibility_partial（DATA-003-R1）
   - 217 个 blob 均可追溯
   - 网络恢复后应验证真正 git archive

### 8. 风险评估

**✓ 低风险项：**
- CAD-003 Schema 实现已 17/17 pass
- DATA-003 smoke 结果可完整复现
- BenchCAD API（part.build, spec.check）稳定

**⚠ 中等风险项：**
- CadQuery/OCP 几何验证边界可能随版本变化
  - 当前 CadQuery 2.3.0 + OCP 7.9.3.0
  - 若环境升级，需重新验证 isValid()、solid 数计数等

- STEP 往返稳定性
  - importStep() 可能改变几何内部表示
  - 需验证导出/回读后的几何摘要

### 9. 接口冻结确认

✓ **已冻结的接口：**

- 参数 6 元组（bore_d, outer_d, screw_d, screw_len, second_screw, width）
- 约束集合（目录耦合、第二螺钉阈值、壁厚、宽度）
- 前置规则检查（preflight 阶段必须通过）
- 构造器单一入口（part.build(**params)）

✓ **CAD-005/006 必须遵守的契约：**

- IR v0 节点类型白名单（5 种）
- 约束错误码固定集（CAD-003 规范）
- 验证结果结构（status, validation_result, errors）
- STEP 导出/回读接口

## 复核结论

```text
handoff_successor_check:
  predecessor=DATA-003 (2026-11-01) + CAD-003 (2026-10-31) + IR-001 (2026-11-01)
  files_format=✓ 完整且格式正确
  core_rerun=✓ spec.check() 和 part.build() 均可调用，smoke 命令完整复现
  normal_case=✓ 两个正常案例均通过，与 DATA-003 run-log 一致
  failure_case=✓ 两个失败案例均被 spec.check() 正确拒绝
  interface=✓ CAD-003 输入、spec.check() 输出、part.build() 返回与 IR-001 参数层一致
  limits=✓ 所有已知限制已确认并保留：STEP hash 不稳定、螺纹 no-op、多实体风险、snapshot 部分可复现
  result=pass
  blocking_issue=无
```

## 下一步

CAD-005 实现可安全启动：

1. 构建白名单 IR v0 → CadQuery/OCP 编译器
   - 验证 IR JSON 结构和语义
   - 实现 5 种节点类型的 CadQuery 代码生成
   - 处理公式展开和参数替代

2. 建立 CAD-006 验证器
   - 实体数量检查（预期 1 solid）
   - isValid() 检查
   - 体积、包围盒、几何摘要计算
   - STEP 导出/回读往返验证

3. 集成测试
   - 4 类测试案例（合法、边界、约束非法、几何非法）
   - 版本化运行日志
   - 结构化错误报告

4. 交接给中枢审查
   - CAD-005 代码和测试
   - CAD-006 代码和测试
   - 运行日志和 manifest
