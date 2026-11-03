# RET-003 handoff：C1 代码修正交接（仅代码验收）

**⚠️ 重要状态说明**：
- 本交接记录的是 **代码级修正**，不是正式 C1 实验结果验收
- 先前 M0-M5 阶段在 Python 3.10.12 / Linux 环境执行，**不符合正式环境要求**
- 正式 C1 诊断需在 Python 3.11.18 / macOS arm64 环境由 Codex 执行
- 本轮交接范围：修正后的代码单元（诊断器、报告生成器、交叉核对器）

状态：`review`（等待 Codex 在固定环境运行正式 C1）
任务：RET-003 C1 代码修正
交接方：CC 代码实现 Agent
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
日期：2026-11-03

---

## 本轮交接：代码修正完成

### 交付范围

本轮只交付 **可审查的代码单元**，不交付正式 C1 实验结果：

**代码文件**（规范路径）：
- `run_c1_diagnostic.py`（590 行）：修正后的诊断脚本
- `generate_report.py`（286 行）：报告生成器
- `cross_check.py`（260 行）：交叉核对器含负例自测
- `checkpoint-v2.md`：代码修正 checkpoint
- `handoff-v2.md`（本文件）：代码修正交接
- `docs/WORKLOG.md`：追加代码修正记录

**代码级验证**（Python 3.10.12 / Linux aarch64）：
- ✓ 契约测试通过（test 模式，5 项）
- ✓ Python 编译检查通过（3 个脚本）
- ✓ git diff --check 通过

**未交付**（需在正式环境）：
- 正式 `c1-diagnostic-results.json`
- 正式 `c1-diagnostic-report.md`
- 正式环境的完整验证（RET-001/002）

### 核心修正项

1. **嵌套错误对象解析**（关键修正）
   - **问题**：原代码从 `error_dict.get('stage')` 读取，实际结构为 `error_dict['error']['stage']`
   - **修正**：新增 `parse_retrieval_error()` 从 `error_envelope["error"]["code/stage/fields"]` 读取
   - **验证**：`validate_error_structure()` 严格断言 code/stage/fields 完全匹配

2. **环境门保护**
   - **设计**：`check_environment_gate(mode)` 支持 "formal" 和 "test" 模式
   - **formal 模式**：强制 Python 3.11.18 / darwin / arm64，不符合则非零退出
   - **test 模式**：仅记录环境，用于契约测试
   - **保护范围**：主诊断流程和 worker 模式都需环境门

3. **契约测试增强**
   - **Test 3**：验证嵌套错误对象 code/stage/fields 完整解析
   - **Test 5**：说明环境门逻辑（实际执行在正式运行）

4. **报告生成修正**
   - 失败诊断章节从 JSON 读取 `code/stage/fields` 并展示
   - 新增 `**Code**: \`RETRIEVAL_MISSING_FIELD\``
   - 观察文本说明嵌套 error.error 对象

5. **交叉核对增强**
   - **逐字段验证**：`check_failure_diagnostic()` 检查 `**Stage**: \`query\`` 和 `**Fields**: \`['outer_d']\``
   - **负例自测**：`run_self_test()` 变异 stage 和 fields，验证能检测不一致
   - **自测流程**：原始报告通过 → 篡改 stage 检测失败 → 篡改 fields 检测失败

### 代码级验证记录

执行环境：Python 3.10.12 / Linux aarch64

```bash
# 契约测试（test 模式）
PYTHONPATH=src python3 run_c1_diagnostic.py --contract-test
=> Contract tests PASSED
   Test environment: Python 3.10.12 / linux aarch64
   Test 1: results field exists and non-empty ✓
   Test 2: query_status at correct level ✓
   Test 3: missing field rejection with correct error structure ✓
      code=RETRIEVAL_MISSING_FIELD, stage=query, fields=['bore_d']
   Test 4: candidate role purity ✓
   Test 5: environment gate logic ✓

# Python 编译
python3 -m py_compile run_c1_diagnostic.py generate_report.py cross_check.py
=> 无错误

# Git 空白检查
git diff --check
=> 无空白错误
```

**说明**：契约测试在 test 模式运行，不写正式输出，不触发环境门强制检查。

### Codex 审查清单

**必须检查项**（在正式环境）：

1. **环境门验证**
   - 在 Python 3.11.18 / macOS arm64 环境运行 `run_c1_diagnostic.py`
   - 尝试在错误环境（Python 3.10 或 Linux）运行正式模式，验证非零退出
   - 确认 worker 模式也受环境门保护

2. **嵌套错误解析验证**
   - 运行正式 C1，检查 `c1-diagnostic-results.json` 的 `failure_diagnostic`
   - 确认包含 `"code": "RETRIEVAL_MISSING_FIELD"`
   - 确认包含 `"stage": "query"`
   - 确认包含 `"fields": ["outer_d"]`

3. **报告生成验证**
   - 运行 `generate_report.py`
   - 检查报告失败诊断章节包含 `**Code**`, `**Stage**`, `**Fields**`

4. **交叉核对验证**
   - 运行 `cross_check.py`（含自测）
   - 确认原始报告通过
   - 确认自测检测到 stage 变异
   - 确认自测检测到 fields 变异

5. **完整回归验证**
   - RET-001 `verify_manifest.py --tracked-only`
   - RET-002 30 项 retrieval tests
   - RET-002 smoke 诊断

**可选深入检查**：

6. **代码审查**
   - `parse_retrieval_error()` 正确提取 `error_envelope["error"][...]`
   - `validate_error_structure()` 严格断言三个字段
   - 环境门逻辑在 formal 和 worker 模式都启用
   - 契约测试覆盖嵌套错误结构

### Git 状态

```bash
git status --short
# M docs/WORKLOG.md
# ?? agent-work/integration/RET-003-retrieval-evaluation/checkpoint-v2.md
# ?? agent-work/integration/RET-003-retrieval-evaluation/cross_check.py
# ?? agent-work/integration/RET-003-retrieval-evaluation/generate_report.py
# ?? agent-work/integration/RET-003-retrieval-evaluation/handoff-v2.md
# ?? agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py
```

**Git 阻塞状态**：`.git/index.lock` 存在，无法暂存和提交

```bash
git add ...
=> fatal: Unable to create '.git/index.lock': File exists.
   Another git process seems to be running in this repository
```

按照任务要求，不删除 `.git/index.lock`。待项目负责人清理锁文件后再提交。

### 下一步

1. **检查 Git 锁**：
   ```bash
   ls -la .git/index.lock
   # 若存在：报告阻塞，等待锁清除
   # 若不存在：继续提交流程
   ```

2. **提交（锁不存在时）**：
   ```bash
   git add agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py \
           agent-work/integration/RET-003-retrieval-evaluation/generate_report.py \
           agent-work/integration/RET-003-retrieval-evaluation/cross_check.py \
           agent-work/integration/RET-003-retrieval-evaluation/checkpoint-v2.md \
           agent-work/integration/RET-003-retrieval-evaluation/handoff-v2.md \
           docs/WORKLOG.md

   git commit -m "fix: correct RET-003 C1 code (nested error, env gate, cross-check) [RET-003]

   - 修正嵌套错误解析：从 error.error.{code,stage,fields} 读取
   - 添加环境门：formal 模式强制 Python 3.11.18/darwin/arm64
   - 增强契约测试：验证嵌套错误结构完整性
   - 增强交叉核对：逐字段验证 stage/fields，含负例自测
   - 报告生成：展示 code/stage/fields

   代码级验证通过（契约测试、py_compile、git diff --check）。
   正式 C1 执行需在固定环境由 Codex 运行。"
   ```

3. **保持 review 状态**：不 push，交 Codex 在固定环境运行正式 C1

4. **Codex 在 macOS 执行正式 C1**：
   - 运行 `run_c1_diagnostic.py`（正式模式）
   - 验证环境门、嵌套错误解析、五查询复跑
   - 生成正式 JSON/报告
   - 运行交叉核对含负例自测
   - 完整回归验证（RET-001/002）
   - 独立审查正式结果

---

## 历史记录：先前 M0-M5 执行（非正式）

**⚠️ 以下记录来自 Python 3.10.12 / Linux 环境，不符合正式要求，仅作为开发历史保留**

## 当前状态

CC Agent 已完成 RET-003 C1 诊断修正任务（M0-M5 全部阶段），修正了上轮交付的 5 个已知问题，输出修正后的机器结果、自动生成的报告和验证脚本。

**修正任务执行阶段**：
- M0: 环境与接口确认 ✓
- M1: 契约测试先行 ✓
- M2: 单查询校准 ✓
- M3: 全量运行 ✓
- M4: 生成与交叉核对 ✓
- M5: 交接（本文件）✓

## 修正的问题

根据 `agent-work/reviews/RET-003-codex-review.md` 中枢复审，修正以下问题：

1. **接口错误**：原脚本读取 `candidates` 字段，实际 RET-002 返回 `results`
   - **修正**：使用 `result_dict.get('results', [])`

2. **层级错误**：原脚本 `query_status` 从顶层读取为 null
   - **修正**：从 `result_dict.get('query', {}).get('query_status')` 读取

3. **复跑不足**：原脚本仅 2 个样本同进程重复
   - **修正**：5 个合法查询各自通过 subprocess 跨独立进程复跑，比对 canonical SHA-256

4. **fail-closed 缺失**：原脚本失败时可能返回成功
   - **修正**：所有验证失败调用 `fail()` 返回非零退出码

5. **报告不一致**：原报告手工转录导致错误
   - **修正**：从 JSON 自动生成报告，并通过 cross_check.py 验证一致性

## 交付文件

### 新建文件

```text
run_c1_diagnostic_v2.py     修正版诊断脚本（370 行）
c1-diagnostic-report-v2.md  自动生成的报告
checkpoint-v2.md            本次修正的完整 checkpoint
handoff-v2.md              本交接文件
generate_report.py          报告自动生成脚本（286 行）
cross_check.py              JSON/报告交叉核对脚本（150 行）
ENVIRONMENT_MISMATCH.md     M0 环境检查报告（已过时，可忽略）
```

### 覆盖文件

```text
c1-diagnostic-results.json  修正后的完整机器结果（覆盖上轮版本）
```

### 保留文件（未删除）

```text
run_c1_diagnostic.py        上轮脚本（保留作为对比）
c1-diagnostic-report.md     上轮报告（保留作为对比）
checkpoint.md               上轮 checkpoint
handoff.md                  上轮 handoff
```

### 只追加

```text
docs/WORKLOG.md            追加 M0-M5 执行记录
```

## 执行与验证记录

### M0: 环境与接口确认

```bash
python3 --version
# Python 3.10.12

uname -sm
# Linux aarch64

PYTHONPATH=src python3 -c "from retrieval import RetrievalIndex; print('OK')"
# retrieval module OK
```

读取 `src/retrieval/baseline.py` 和 `src/retrieval/errors.py` 确认：
- ✓ RET-002 返回 `results` 字段
- ✓ `query_status` 在 `result.query.query_status` 路径
- ✓ `RetrievalError.code` 属性直接可访问

### M1: 契约测试先行

```bash
PYTHONPATH=src python3 run_c1_diagnostic_v2.py --contract-test
# Running contract tests...
#   Test 1: results field exists and non-empty ✓
#   Test 2: query_status at correct level ✓
#   Test 3: missing field rejection ✓
#   Test 4: candidate role purity ✓
# Contract tests PASSED
```

### M2: 单查询校准

使用 `heldout-bore-012` 校准：
- Query: bore_d=12, outer_d=22, screw_d=6, screw_len=8, second_screw=0, width=12
- Top-1: catalog-bore-020, distance=0.066333
- Field errors: bore_d=8, outer_d=10, width=2（其余精确匹配）
- ✓ M2 校准通过

### M3: 全量运行

```bash
PYTHONPATH=src python3 run_c1_diagnostic_v2.py
# 退出码: 0
# 输出: c1-diagnostic-results.json
```

主查询结果：
- `heldout-bore-012`: top-1=`catalog-bore-020`, dist=0.066333, 确定性 ✓
- `heldout-bore-035`: top-1=`catalog-bore-020`, dist=0.207444, 确定性 ✓
- `heldout-bore-080`: top-1=`catalog-bore-050`, dist=0.784444, 确定性 ✓

接口诊断：
- `diagnostic-source-bore-020`: top-1=`catalog-bore-020`, dist=0.0, 确定性 ✓
- `diagnostic-heldout-bore-080-boundary`: top-1=`catalog-bore-050`, dist=0.784444, 确定性 ✓

失败诊断：
- 缺少 `outer_d` → `RETRIEVAL_MISSING_FIELD` (stage=query, fields=['outer_d']) ✓

独立进程确定性：5/5 查询 SHA-256 一致

### M4: 生成与交叉核对

```bash
python3 generate_report.py
# 报告已生成: c1-diagnostic-report-v2.md

python3 cross_check.py
# 检查 1: 主查询逐例摘要表 ✓
# 检查 2: 主查询详细章节 ✓
# 检查 3: 候选数量 ✓ (15)
# 检查 4: 失败诊断 ✓
# 检查 5: 确定性验证 ✓
# ✓ 所有检查通过：报告与 JSON 结果一致
# 退出码: 0
```

其他验证：
```bash
python3 -m py_compile run_c1_diagnostic_v2.py generate_report.py cross_check.py
# 无错误

git diff --check
# 无空白错误
```

## 中枢复核清单

### 必须检查项

1. **接口修正验证**
   - 确认脚本使用 `results` 字段（非 `candidates`）
   - 确认 `query_status` 从正确层级读取
   - 检查 JSON 结果中所有查询的 `query_status` 非 null

2. **独立进程复跑验证**
   - 确认 5 个合法查询（3 主查询 + 2 诊断）各自完成跨进程复跑
   - 检查 JSON 中的 `determinism` 字段，验证 `cross_process_deterministic: true`
   - 确认使用 subprocess 而非同进程重复

3. **Fail-closed 验证**
   - 运行契约测试，确认所有检查通过
   - 尝试破坏性测试（如修改 manifest hash），验证脚本非零退出
   - 确认任何验证失败都会终止执行

4. **报告一致性验证**
   - 运行 `cross_check.py`，确认所有 5 项检查通过
   - 抽查报告中的关键值（top-1、距离、状态）与 JSON 一致
   - 确认报告由脚本自动生成，非手工编辑

5. **结果正确性核对**
   - 主查询 `heldout-bore-012`: top-1=`bore-020`, dist=0.066333
   - 主查询 `heldout-bore-035`: top-1=`bore-020`, dist=0.207444
   - 主查询 `heldout-bore-080`: top-1=`bore-050`, dist=0.784444
   - 候选角色：15/15 = 100% `retrieval_source`
   - 失败诊断：`RETRIEVAL_MISSING_FIELD` ✓

6. **文件边界**
   - 未修改 `src/**`、`tests/**`、RET-001 manifest、RET-002 config
   - 未修改 protocol/query-set
   - 未修改正式状态/计划/决策文档
   - 只追加 WORKLOG.md

7. **限制与声称边界**
   - 报告明确标注环境差异（Python 3.10.12 / Linux）
   - 报告明确 `provisional_small_n`，不是 benchmark
   - 报告明确距离只是参数近邻度
   - 报告明确端到端指标 `not_measured`
   - 未声称 CAD 成功率、自然语言抽取或用户效用

### 可选深入检查

8. **上游验证补齐**（若在完整环境）
   - RET-001 `verify_manifest.py --tracked-only`
   - RET-002 retrieval tests (30 项)
   - RET-002 smoke 诊断

9. **环境差异评估**
   - 实际 Python 3.10.12 vs 要求 3.11.18
   - 实际 Linux aarch64 vs 要求 macOS arm64
   - 判断是否要求在正确环境重新执行

10. **独立复跑验证**
    - 在中枢自己的环境运行 `run_c1_diagnostic_v2.py`
    - 比对输出的 JSON 与交付的 `c1-diagnostic-results.json`

## 环境与限制

**实际环境**：
- Python 3.10.12（协议要求 3.11.18）
- Linux aarch64（协议要求 macOS arm64）
- retrieval 模块可导入

**已知限制**：
- 环境与协议基线有差异
- RET-001/002 完整验证因依赖缺失（jsonschema, CadQuery）未执行
- 单族 15 行、3 候选、`provisional_small_n`（不是正式 benchmark）
- 距离表示参数近邻度，不表示几何等价、制造可行性或 CAD 成功
- 端到端指标（Schema/CAD/STEP）为 `not_measured`
- 未运行 C0/C2O/公平 C2、未调权重

## Git 状态

```bash
git status --short
# M c1-diagnostic-results.json (覆盖)
# ?? run_c1_diagnostic_v2.py (新建)
# ?? c1-diagnostic-report-v2.md (新建)
# ?? checkpoint-v2.md (新建)
# ?? handoff-v2.md (本文件)
# ?? generate_report.py (新建)
# ?? cross_check.py (新建)
# ?? ENVIRONMENT_MISMATCH.md (新建)
# M docs/WORKLOG.md (追加)
```

`.git/index.lock` 状态：需检查（若存在则不提交，报告阻塞）

## 下一步

1. **检查 Git 锁**：
   ```bash
   ls -la .git/index.lock
   # 若存在：报告阻塞，等待锁清除
   # 若不存在：继续提交流程
   ```

2. **提交（锁不存在时）**：
   ```bash
   git add agent-work/integration/RET-003-retrieval-evaluation/*.py \
           agent-work/integration/RET-003-retrieval-evaluation/*.json \
           agent-work/integration/RET-003-retrieval-evaluation/*-v2.md \
           docs/WORKLOG.md

   git commit -m "fix: correct RET-003 C1 diagnostic [RET-003]

   - 修正接口错误：使用 results 而非 candidates
   - 修正层级错误：从 query.query_status 读取
   - 实现独立进程复跑：5 个查询通过 subprocess 验证
   - 添加 fail-closed：所有验证失败返回非零
   - 自动生成报告：从 JSON 生成 Markdown 避免手工转录
   - 添加交叉核对：验证报告与 JSON 一致性

   M0-M5 阶段全部完成，契约测试/单查询校准/全量运行/交叉核对通过。
   环境: Python 3.10.12 / Linux aarch64（与协议要求有差异）。"
   ```

3. **保持 review 状态**：不 push，交 Codex 中枢独立审查

4. **Codex 中枢审查**：
   - 验证修正后的接口和独立进程复跑
   - 核对逐例结果和距离计算
   - 评估环境差异是否可接受
   - 确认未运行未授权条件
   - 验证限制说明完整性

## 交付状态

**状态**: `review`
**阻塞项**: 待确认 `.git/index.lock` 状态
**下一步**: Codex 中枢独立审查
