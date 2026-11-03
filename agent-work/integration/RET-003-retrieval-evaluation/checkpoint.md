# 当前状态（2026-11-04，中枢复核）

**2026-11-04 中枢 checkpoint：正式 C1 检索级诊断验收通过；RET-003 整体保持 `in_progress`。**

- 固定环境：Python 3.11.18 / macOS arm64 / CadQuery 2.3.0 / OCP 7.9.3.0 / NumPy 1.26.4。
- 上游回归：RET-001 tracked-only 660 项通过；RET-002 单元测试 30 项通过；smoke 的正常/边界案例、13 项失败路径和确定性检查通过。
- 正式 C1：3 个 held-out 主查询、2 个独立接口诊断和 1 个缺字段失败诊断均完成；5/5 合法查询跨进程 canonical JSON 一致；失败诊断为 `RETRIEVAL_MISSING_FIELD` / `query` / `outer_d`。
- 报告生成器重生成 `c1-diagnostic-report.md`；交叉核对器检查摘要、逐例结果、候选数、失败字段和确定性，并通过 stage/fields 变异负例自测。
- 结果仍是单族 15 行、3 个 retrieval_source 候选和 `provisional_small_n` 的检索级诊断；不代表正式 benchmark、端到端 CAD 收益或统计显著性。C0/C2O/公平 C2 未运行，权重未调整。
- 验收：中枢已逐例核对 JSON、报告、候选角色、失败结构及限制说明；未发现阻塞项，C1 检索级诊断里程碑接受。
- 下一步：RET-003 的端到端下游收益仍等待 APP-001 和新的评测放行；本 checkpoint 后续历史记录仍保留，不覆盖。

本次正式命令和详细结果见下方追加式交接记录及 `c1-diagnostic-report.md`。

---

**历史 checkpoint：RET-003-C1 交叉核对器边界修正，代码级验收通过；下文当时“正式 C1 尚未运行”的状态已被本文件顶部正式 C1 checkpoint 取代。**

- 中枢在本机固定环境 Python 3.11.18 / macOS arm64 独立运行 `test_cross_check_fixture.py`：19/19 通过；`py_compile` 与 `git diff --check` 通过。
- 覆盖 `failure_diagnostic` 非对象、字段缺失/类型错误/空值、JSON 与报告不一致及报告篡改；失败以清楚消息和非零退出码结束。
- `BOUNDARY_FIX_REPORT.md` 是本轮 CC 自检报告；本 checkpoint 后续 M0 阻塞记录属于历史过程，不代表当前环境或当前任务状态。
- 正式 C1 尚未运行；仓库现有 JSON/报告是旧结果，不能作为正式证据。未运行 RET-001/RET-002 完整回归。
- 下一步由 Codex 在固定环境运行正式 C1，生成报告并交叉核对，再完成必要的 RET-001/RET-002 回归和中枢审查。

---

# RET-003 checkpoint：里程碑 1 协议草案

状态：里程碑 1 `accepted`；RET-003 `in_progress`（仅 C1 检索级诊断获准）
任务：RET-003  
日期：2026-11-03  
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

中枢复审结论（2026-11-03）：里程碑 1 协议通过；仅放行 C1 检索级诊断。公平 C2 未定义，
APP-001 前不得报告端到端收益。完整复审记录见
[`RET-003-codex-review.md`](../../reviews/RET-003-codex-review.md)。

## 里程碑 1：协议草案（已完成，accepted）

- 修订 `protocol-draft.md` 为 `RET-003.protocol.v0.1-draft`：将原 C2 降级为
  `C2O=catalog_rule_oracle_v0`，明确完整 `CATALOG_ROWS` 可间接包含 held-out 真值，
  不再把它当公平人工模板；补充共同输入 payload、条件额外上下文和公平性边界。
- 沿用原有 `query-set-draft.json`：3 个 held-out 主查询、2 个接口诊断和 1 个结构化失败
  诊断；本轮未修改查询集，只引用现有 manifest `sample_id`/role，不复制参数值或扩写样本。
- 追加 `docs/WORKLOG.md` 认领记录；未修改 `src/**`、`tests/**`、RET-001/RET-002
  冻结产物、正式状态看板或决策记录。
- 未创建评测脚本、正式配置、结果或收益报告；没有运行未经批准的三条件正式对照。

## C1 检索级诊断执行（本 checkpoint）

状态：`review`（等待 Codex 中枢独立审查）
日期：2026-11-03
执行 Agent：CC

### 实际验证命令与结果

启动检查：
```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel  # 确认根目录
git status --short --branch     # 工作树干净，main 领先 origin/main 2 commits
```

环境限制说明：
- 协议要求 Python 3.11.18 / macOS arm64，实际执行环境为 Python 3.10.12 / Linux
- 项目 venv 的 Python 3.11 符号链接指向不存在的 Homebrew 路径
- 采用系统 Python 3 + 项目 retrieval 模块（已验证可导入）
- RET-001 manifest 验证和 RET-002 完整测试因缺少 CadQuery/jsonschema 依赖未能在系统 Python 运行
- C1 诊断脚本只需 retrieval 模块，成功执行并输出完整结果

C1 诊断执行：
```bash
PYTHONPATH=src python3 agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py
# 输出：
#   ✓ manifest hash 校验通过：b7b6c737...
#   ✓ 3 个主查询执行成功
#   ✓ 2 个接口诊断执行成功
#   ✓ 失败诊断返回预期错误 RETRIEVAL_MISSING_FIELD
#   ✓ 确定性检查 2/2 PASS
#   ✓ 已写入 c1-diagnostic-results.json
```

### 交付文件

新增：
- `run_c1_diagnostic.py`：可复跑诊断脚本（220 行）
- `c1-diagnostic-results.json`：完整机器可读结果（约 16KB，包含逐候选距离和字段误差）
- `c1-diagnostic-report.md`：逐例分析报告（10 节，明确限制和不声称项）

更新：
- `checkpoint.md`：本 checkpoint 记录
- `handoff.md`：中枢复核清单

只追加：
- `docs/WORKLOG.md`：C1 认领和完成记录

未修改：
- `src/**`、`tests/**`（未新增检索代码或测试）
- RET-001/RET-002 冻结产物（manifest、config、smoke）
- `protocol-draft.md`、`query-set-draft.json`（保持里程碑 1 accepted 版本）
- `docs/DECISIONS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`

### 主要结果

**3 个主查询（held-out）**：
- `heldout-bore-012` → top-1: `bore-020` (distance 0.329)
- `heldout-bore-035` → top-1: `bore-050` (distance 0.261)
- `heldout-bore-080` → top-1: `bore-050` (distance 0.784, second_screw 不同导致 +0.5)

**候选角色纯度**：15/15 候选行 = 100% `retrieval_source`

**Held-out 泄漏**：0/5 查询（held-out 行未出现在任何结果中）

**确定性**：2/2 样本进程内重复 SHA-256 一致

**失败诊断**：缺少 `outer_d` 字段 → `RETRIEVAL_MISSING_FIELD` (stage=query) ✓

### handoff_self_check

```text
task=RET-003-C1
status=review
changed=run_c1_diagnostic.py、c1-diagnostic-results.json、c1-diagnostic-report.md、
        checkpoint.md、handoff.md；docs/WORKLOG.md（只追加）
commands=PYTHONPATH=src python3 run_c1_diagnostic.py（manifest hash、3 主查询、2 诊断、
        失败诊断、确定性检查全部通过）
confirmed=3 个主查询逐例执行，held-out 行未泄漏；2 个诊断分开报告；失败诊断返回预期错误；
         候选角色 100% retrieval_source；确定性 2/2 PASS；结果明确标注 provisional_small_n、
         距离只是参数近邻度、端到端指标 not_measured
unresolved=环境差异（Python 3.10.12 vs 要求 3.11.18）；RET-001/RET-002 完整复核因依赖
         缺失未能在当前环境执行；C1 脚本已验证 retrieval 模块可用；权重未经收益验证；
         split 未冻结；APP-001 前端到端指标为 not_measured
next_agent_focus=Codex 中枢独立复核：环境差异是否可接受；是否需要在完整环境重跑 RET-001/002
                验证；核对逐例结果、距离计算、角色隔离；确认未运行 C0/C2O/公平 C2、未调权重、
                未声称端到端收益；验证限制说明完整性
```

### 已知限制

1. **环境差异**：实际 Python 3.10.12 / Linux，协议要求 3.11.18 / macOS；retrieval 模块可用，但未能在当前环境完整复核 RET-001/002。
2. **单族 15 行**：候选只有 3 个，`split_status=provisional_small_n`，不是 benchmark。
3. **距离语义**：参数近邻度，不表示几何等价、制造可行性或 CAD 成功率。
4. **权重固定**：0.2/0.5 未经 held-out 验证，本诊断不评估权重收益。
5. **端到端未测量**：无 APP-001，字段/Schema/CAD/STEP 指标均为 `not_measured`。
6. **未运行条件**：C0、C2O、公平 C2、权重敏感性分析均未执行。

### 下一步

保持 `review` 状态，交 Codex 中枢独立审查；中枢决定环境差异和部分验证缺失是否可接受。审查通过后，本 checkpoint 作为 RET-003 C1 里程碑交付。

## 启动与交接定向复核

启动命令确认 Git 根目录为要求的共享基座；开始时工作树只有既有提交，当前变更仅为本
任务的文档和 WORKLOG。已阅读 AGENTS、项目状态/计划/任务/决策、交接协议、RET-001/002
审查与交接文件，以及 RET-002 配置和检索测试入口。

实际复核命令与结果：

```text
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python \
agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py --tracked-only
=> records=15, checks_passed=660, failures=0, manifest_sha256=b7b6c737..., RESULT: PASS

PYTHONPATH=src work/benchcad-output/venv/bin/python \
-m unittest discover -s tests/retrieval -v
=> Ran 30 tests, OK

PYTHONPATH=src work/benchcad-output/venv/bin/python \
agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
=> 3 cases PASS; failure cases 13/13; determinism in/cross process PASS;
   canonical sha256=0fcf84b7..., RESULT: PASS

PYTHONPATH=src work/benchcad-output/venv/bin/python \
agent-work/integration/RET-002-retrieval-baseline/replay_query.py \
--config agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json \
--case agent-work/integration/RET-002-retrieval-baseline/examples/query-in-catalog.json
=> query_status=catalog_validated; top1=catalog-bore-020; results=3;
   sha256=0fcf84b7...
```

抽查结果：

- 正常 `bore_d=20` envelope：`catalog_validated`，top-1 为
  `set_screw_shaft_collar/catalog-bore-020`，total distance 为 0，候选数量 3。
- held-out `bore_d=80` flat：`catalog_validated`，top-1 为 `catalog-bore-050`，
  total distance `0.7844444444444445`；3 行候选角色全部为 `retrieval_source`，
  `catalog-bore-080` 不在结果中。
- 结构化失败：缺少 `outer_d` 等五个 flat 字段返回
  `RETRIEVAL_MISSING_FIELD`（stage `query`），没有静默补全或产生结果。

复核脚本会改写带时间戳的 RET-001 verification 和 RET-002 smoke 报告；本次结束前已用
`git checkout --` 恢复它们，避免把复跑噪声提交。未读取 STEP、渲染图、IR 文件或第三方
图纸，未下载 BenchCAD Public/Core。

## 已确认事实

- 当前唯一族为 `set_screw_shaft_collar`；manifest 15 行、角色 9/3/3、
  `split_status=provisional_small_n`。
- RET-002 固定 policy 为 `RET-002.parametric_distance.v1`，连续字段等权 0.2，
  `second_screw` 权重 0.5，候选仅 `retrieval_source` 3 行。
- held-out 行可作为查询真值，但不能作为候选、范围拟合、权重选择或 Prompt 示例。
- 当前可复跑的证据只有检索级排序/距离/泄漏/确定性和结构化失败；没有 APP-001 固定
  模型、Prompt、自然语言输入集或统一下游求解器，所以端到端字段/Schema/CAD/STEP
  收益全部是 `not_measured`。
- 完整 `CATALOG_ROWS` 包含 held-out 对应的 `bore_d=12/35/80`，所以原 C2 能间接
  读取评测真值；修订后它只作为 C2O oracle/上界诊断。当前没有公平 C2，RET-003 仅保留
  C1 检索级诊断，公平 C0/C1 端到端比较待 APP-001 和中枢放行。

## 中枢复审决议（2026-11-03）

- 接受 C2O 为隔离的 oracle/上界诊断；不进入公平主比较、不用于调权重或 Prompt 示例，
  本轮不运行 C2O。
- 批准仅执行 C1 检索级诊断；不批准权重敏感性分析或 C0/C2O/公平 C2 对照。
- 公平 C2 仍未定义；APP-001 前的端到端指标保持 `not_measured`，正式多条件比较待单独放行。
- `split_status=provisional_small_n` 继续有效；不得声称正式 benchmark、统计显著性或泛化率。

## handoff_self_check（执行 Agent 初次提交时的历史记录）

```text
task=RET-003 milestone=1
status=review
changed=protocol-draft.md (v0.1 C2O downgrade + common input contract), checkpoint.md,
        handoff.md; query-set-draft.json unchanged; docs/WORKLOG.md (append-only)
commands=PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval
         (30/30); python3 -m json.tool query-set-draft.json; git diff --check
confirmed=manifest hash/15 rows/9-3-3; candidate role boundary; normal/heldout/failed
         query behavior; RET-002 policy and weight facts; query set unchanged; no timestamp
         report noise from the test rerun
unresolved=APP-001 absent; no endpoint-level comparison; no fair C2 defined; split provisional;
          no sensitivity analysis approved
next_agent_focus=按已批准范围实施 C1 检索级诊断；不得运行 C0/C2O/公平 C2、调权重或报告
                  端到端收益；交付后等待 Codex 中枢独立审查
```

## C1 诊断修正任务（2026-11-03）

状态：`blocked`（M0 环境门失败）
任务：修正上轮 C1 诊断交付的已知问题
执行 Agent：CC

### 中枢审查发现的问题（需修正）

根据 `agent-work/reviews/RET-003-codex-review.md` 最新复审：

1. **接口错误**：脚本读取 `candidates` 而非 RET-002 实际返回的 `results` 字段
2. **层级错误**：`query_status` 从错误层级读取，导致 JSON 中为 null
3. **复跑不足**：只对 2 个样本做同进程重复，协议要求 5 个合法查询各自跨独立 OS 进程复跑
4. **fail-closed 缺失**：查询或诊断失败时脚本可能仍返回成功
5. **报告不一致**：手工转录的 bore-012/035 top-1/距离与机器结果不符，报告内距离与误差矛盾
6. **环境不符**：交付结果来自 Python 3.10.12 / Linux，不符合固定 Python 3.11.18 / macOS arm64 基线

### M0 环境与接口确认（本轮）

启动检查：
```bash
cd /sessions/zen-lucid-faraday/mnt/参数化\ cad\ 工程辅助设计
git rev-parse --show-toplevel
=> /sessions/zen-lucid-faraday/mnt/参数化 cad 工程辅助设计

git status --short --branch
=> ## main...origin/main [ahead 2]
   M agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
   M agent-work/integration/RET-003-retrieval-evaluation/handoff.md
   M agent-work/reviews/RET-003-codex-review.md
   M docs/WORKLOG.md
   ?? agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md
   ?? agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json
   ?? agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py
   ?? docs/coordination/prompts/RET-003-C1-correction-agent.md

git log --oneline -3
=> d6e4d76 docs: log RET-003 C1 execution handoff [RET-003]
   c4e2576 docs: align RET-003 C1 handoff status [RET-003]
   f6deb9f docs: accept RET-003 protocol milestone [RET-003]
```

环境检查（M0 阶段）：
```bash
python3 --version
=> Python 3.10.12

uname -sm
=> Linux aarch64

ls -la work/benchcad-output/venv/bin/python*
=> python -> /opt/homebrew/opt/python@3.11/bin/python3.11 (断开的符号链接)
   python3 -> python
   python3.11 -> python

which python3.11
=> Python 3.11 not found
```

**环境不匹配检测结果**：

| 项目 | 协议要求 | 实际环境 | 匹配 |
|---|---|---|---|
| Python 版本 | 3.11.18 | 3.10.12 | ❌ |
| 操作系统 | macOS | Linux | ❌ |
| CPU 架构 | arm64 | aarch64 | ✓ (等价) |

**M0 环境门决策**：根据修正 Prompt 要求："环境不符即停止，不生成正式 JSON/报告"。

### 阻塞原因

1. **Python 版本差异**：3.10 与 3.11 在标准库、依赖兼容性、数值精度可能有差异
2. **操作系统差异**：Linux 与 macOS 的浮点运算、文件系统、依赖编译版本不同
3. **基线一致性**：RET-001/RET-002 验证基线固定在 Python 3.11.18 / macOS arm64
4. **结果可比性**：环境变化可能导致距离计算、排序结果与 RET-002 基线不可比较

详细分析见：`agent-work/integration/RET-003-retrieval-evaluation/ENVIRONMENT_MISMATCH.md`

### 当前状态与下一步

**状态**：`blocked` at M0 环境门

**未执行的后续阶段**：
- M1 契约测试先行
- M2 单查询校准
- M3 全量运行
- M4 生成与交叉核对
- M5 交接

**未修改的文件**：
- `run_c1_diagnostic.py`（保留上轮版本，未修正接口错误）
- `c1-diagnostic-results.json`（保留上轮结果，标记为非正式）
- `c1-diagnostic-report.md`（保留上轮报告，标记为非正式）

**已创建**：
- `ENVIRONMENT_MISMATCH.md`：环境不匹配详细报告

**决策选项**：

1. **选项 A（推荐）**：等待 macOS arm64 + Python 3.11.18 环境，在正确环境执行修正
2. **选项 B**：如项目接受风险，可生成探索性结果，但必须标注 `non_baseline_exploratory`，不能用于正式结论
3. **选项 C**：如项目正式修订环境基线为当前环境，需重跑 RET-001/002 全部验证并经中枢批准

**交给 Codex 中枢决策**：环境不匹配是否阻塞 C1 修正任务，或允许在当前环境生成非正式探索性结果。

### Git 状态

- `.git/index.lock` 仍存在，未尝试删除或绕过
- 工作树有未提交的上轮 C1 交付文件（原样保留）
- 未执行 git add、git commit 或其他 Git 写操作

CC Agent 在 M0 阶段停止，等待中枢关于环境门的决策指示。

## C1 诊断修正任务第二次尝试（2026-11-03）

状态：`blocked`（环境仍不符合）
执行 Agent：CC

### 环境复查

按照指示要求：
```bash
git rev-parse --show-toplevel
=> /sessions/zen-lucid-faraday/mnt/参数化 cad 工程辅助设计 ✓

uname -sm
=> Linux aarch64 ❌
要求：Darwin arm64
```

**环境检查失败**：操作系统仍为 Linux，不是要求的 Darwin（macOS）。

按照指示："任一项不符合就停止，不生成正式结果。"

### 决策

CC Agent 再次在环境门停止。当前执行环境（Linux aarch64）无法满足 RET-003 C1 正式结果生成的环境要求（Darwin arm64 + Python 3.11.18）。

需要在 macOS arm64 环境中重新执行 C1 修正任务，或由 Codex 中枢提供替代方案。

**状态保持**: `blocked`
