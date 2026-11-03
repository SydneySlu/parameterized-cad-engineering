# RET-003 C1 Code-Only 收尾修正总结

> **历史记录提示（2026-11-04）**：本文记录上一轮 code-only 修正，后续边界修正已更新测试和错误处理。当前状态以 [`BOUNDARY_FIX_REPORT.md`](BOUNDARY_FIX_REPORT.md) 及最新 checkpoint/handoff 为准。当前无已确认的 `.git/index.lock`；正式 C1 仍未运行。下方旧路径、旧测试覆盖和旧锁状态保留作历史，不应按当前状态执行。

**状态**: 已被 2026-11-04 后续复核取代；仅作历史参考
**任务**: RET-003 C1 代码收尾修正（仅代码级，未运行正式 C1）
**日期**: 2026-11-03

---

## 修正内容

### 1. 环境门可注入测试

**问题**: 原 Test 5 只打印声明，未实际验证不匹配环境被拒绝

**修正**:
- `check_environment_gate()` 增加 `injected_python/platform/machine` 参数
- `test_environment_gate_logic()` 测试 4 种场景：
  - ✓ 正确环境 (3.11.18/darwin/arm64) 通过
  - ✓ Python 版本不匹配 (3.10.12) 被拒绝
  - ✓ 平台不匹配 (linux) 被拒绝
  - ✓ 架构不匹配 (x86_64) 被拒绝

### 2. Worker 模式环境门顺序

**问题**: Worker 模式在环境检查前加载 manifest

**修正**:
- Worker 模式先调用 `check_environment_gate(mode="formal")`
- 环境门通过后再加载 manifest 和执行查询

### 3. 路径统一

**问题**:
- `generate_report.py` 默认输出 `c1-diagnostic-report-v2.md`
- `cross_check.py` 默认读取 `c1-diagnostic-report.md`
- 接口不一致

**修正**:
- `run_c1_diagnostic.py` 定义常量 `OUTPUT_JSON_PATH` 和 `OUTPUT_REPORT_PATH`
- `generate_report.py` 默认输出 `c1-diagnostic-report.md`（移除 -v2 后缀）
- `cross_check.py` 默认读取 `c1-diagnostic-report.md`
- 三个脚本使用一致的规范路径

### 4. 增强错误处理

**问题**: `cross_check.py` 在 JSON 缺少字段时抛出 KeyError

**修正**:
- `check_failure_diagnostic()` 使用 `.get()` 安全读取字段
- 缺少 code/stage/fields 返回清楚的错误消息：
  - "JSON failure_diagnostic 缺少 'code' 字段"
  - "JSON failure_diagnostic 缺少 'stage' 字段"
  - "JSON failure_diagnostic 缺少 'fields' 字段"
- fields 类型错误返回："JSON failure_diagnostic 'fields' 类型错误: 期望 list，实际 str"

### 5. Fixture 测试

**新增**: `test_cross_check_fixture.py` 临时测试脚本

测试场景：
1. ✓ 合法 JSON + 报告通过
2. ✓ 缺少 failure_diagnostic.code 被明确拒绝
3. ✓ 缺少 failure_diagnostic.stage 被明确拒绝
4. ✓ 缺少 failure_diagnostic.fields 被明确拒绝
5. ✓ fields 类型错误（字符串而非列表）被拒绝
6. ✓ 报告 stage 篡改被检测
7. ✓ 报告 fields 篡改被检测

测试只操作系统临时目录，不修改仓库中的正式 JSON/报告。

---

## 代码级验证结果

执行环境：Python 3.10.12 / Linux aarch64（非正式环境）

### 契约测试

```bash
PYTHONPATH=src python3 run_c1_diagnostic.py --contract-test
```

**输出**:
```
Running contract tests...
  Test environment: Python 3.10.12 / linux aarch64
  Test 1: results field exists and non-empty
    ✓ results field exists with 3 candidates
  Test 2: query_status at correct level
    ✓ query_status = catalog_validated
  Test 3: missing field rejection with correct error structure
    ✓ missing field correctly rejected
      code=RETRIEVAL_MISSING_FIELD, stage=query, fields=['bore_d']
  Test 4: candidate role purity
    ✓ all candidates have role=retrieval_source
  Test 5: environment gate logic (injected values)
    ✓ Correct environment accepted (3.11.18/darwin/arm64)
    ✓ Python version mismatch rejected (3.10.12)
    ✓ Platform mismatch rejected (linux)
    ✓ Machine architecture mismatch rejected (x86_64)
Contract tests PASSED
```

**结果**: ✓ 5 项测试全部通过

### Fixture 测试

```bash
python3 test_cross_check_fixture.py
```

**输出**:
```
临时 fixture 测试：cross_check.py 异常处理
============================================================

测试 1: 合法 JSON + 报告
  ✓ 合法输入通过

测试 2: 缺少 failure_diagnostic.code
  ✓ 缺少 code 被明确拒绝

测试 3: 缺少 failure_diagnostic.stage
  ✓ 缺少 stage 被明确拒绝

测试 4: 缺少 failure_diagnostic.fields
  ✓ 缺少 fields 被明确拒绝

测试 5: fields 类型错误（字符串而非列表）
  ✓ fields 类型错误被明确拒绝

测试 6: 报告 stage 篡改
  ✓ 报告 stage 篡改被检测

测试 7: 报告 fields 篡改
  ✓ 报告 fields 篡改被检测

============================================================
✓ 所有 fixture 测试通过
  - 合法输入通过
  - 缺少 code/stage/fields 被明确拒绝
  - fields 类型错误被拒绝
  - 报告 stage/fields 篡改被检测
```

**结果**: ✓ 7 项测试全部通过

### Python 编译检查

```bash
python3 -m py_compile run_c1_diagnostic.py generate_report.py cross_check.py
```

**结果**: ✓ 无错误

### Git 空白检查

```bash
git diff --check
```

**结果**: ✓ 无空白错误

---

## 修改的文件

1. **run_c1_diagnostic.py** (约 650 行)
   - 新增 `injected_*` 参数到 `check_environment_gate()`
   - 新增 `test_environment_gate_logic()` 可注入环境测试
   - Worker 模式先调用环境门再加载数据
   - 定义 `OUTPUT_JSON_PATH` 和 `OUTPUT_REPORT_PATH` 常量

2. **generate_report.py** (286 行)
   - 修正默认输出路径为 `c1-diagnostic-report.md`
   - 文档字符串说明规范路径

3. **cross_check.py** (约 300 行)
   - `check_failure_diagnostic()` 使用 `.get()` 安全读取
   - 缺失字段返回清楚的错误消息
   - fields 类型错误返回类型信息
   - 文档字符串说明规范路径

4. **test_cross_check_fixture.py** (新建，约 250 行)
   - 临时测试脚本，验证 cross_check.py 异常处理
   - 7 项测试覆盖合法/缺失/类型错误/篡改场景
   - 只操作系统临时目录

5. **SUMMARY.md** (本文件)
   - 收尾修正总结

---

## 未执行的工作

按照任务要求，以下工作未执行：

- ❌ 未运行正式 C1 诊断
- ❌ 未生成正式 `c1-diagnostic-results.json`
- ❌ 未生成正式 `c1-diagnostic-report.md`
- ❌ 未覆盖仓库中的正式 JSON/报告
- ❌ 未运行 RET-001 `verify_manifest.py --tracked-only`
- ❌ 未运行 RET-002 30 项 retrieval tests
- ❌ 未运行 RET-002 smoke 诊断
- ❌ 未执行 git add/commit
- ❌ 未删除或创建 .git/index.lock

**原因**: 本轮只修正代码单元，正式 C1 需在 Python 3.11.18 / macOS arm64 环境由 Codex 执行。

---

## 已知限制

1. **代码级验证环境**: Python 3.10.12 / Linux aarch64，不符合正式要求
2. **正式结果未验收**: 仓库中现有的 JSON/报告仍是旧产物（含 stage/fields 为 null）
3. **Git 索引锁**: `.git/index.lock` 存在，无法提交
4. **临时测试脚本**: `test_cross_check_fixture.py` 为临时文件，不作为正式交付

---

## Codex 后续任务

在 Python 3.11.18 / macOS arm64 环境：

1. 运行 `run_c1_diagnostic.py`（正式模式）
2. 验证环境门正确拒绝不匹配环境
3. 验证正式 JSON 的 `failure_diagnostic.code/stage/fields` 正确
4. 运行 `generate_report.py` 生成正式报告
5. 运行 `cross_check.py` 含负例自测
6. 运行 RET-001/002 完整回归验证
7. 独立审查正式结果

**交付状态**: 保持 `review`，等待 Codex 在固定环境执行正式 C1
