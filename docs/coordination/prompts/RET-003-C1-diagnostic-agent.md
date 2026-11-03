# RET-003 C1 检索级诊断执行 Prompt

你是参数化 CAD 工程辅助设计项目的 CC 执行 Agent。本任务只执行已获中枢批准的 **C1 (`ret002_parametric_v1`) 检索级诊断**，产出可复跑脚本、逐例机器结果和简短分析。Codex 中枢负责独立验收。

## 1. 当前授权

RET-003 里程碑 1 协议已通过 Codex 中枢复审。当前允许：

- 用冻结的 RET-002 配置和策略运行 C1；
- 用 query set 中 3 个 held-out 主查询逐例计算检索候选距离和参数误差；
- 分开运行并报告 2 个接口诊断和 1 个结构化失败诊断；
- 记录候选角色、排序、查询状态和确定性复跑结果。

当前不允许：

- 运行 C0、C2O `catalog_rule_oracle_v0` 或任何公平 C2；
- 修改 RET-002 参数、候选角色、权重、policy id、manifest 或 query set；
- 进行权重敏感性分析、调参、选择“最佳”候选或使用 held-out 选策略；
- 声称 C1 改善了自然语言抽取、Prompt、Schema/CAD/STEP 成功率、用户效用或泛化能力；
- 读取 STEP、渲染图、IR 文件、第三方图纸，下载 BenchCAD Public/Core，或生成 CAD 几何。

本任务的 held-out 主查询是从 manifest 读取的精确结构化参数，不是自然语言用户输入。结果只能说明固定 RET-002 策略在这些已知参数查询上的检索行为，不代表真实用户输入上的收益。

## 2. 根目录和启动检查

在当前设备的共享 Git 根目录工作。当前设备预期路径：

```text
/Users/syd/Desktop/参数化 cad 工程辅助设计
```

启动时执行并记录：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
git log --oneline -8
```

如果设备路径不同，以 `git rev-parse --show-toplevel` 为准并写入 checkpoint。开始时必须确认工作树干净；若有未提交改动，先记录并停止，不得覆盖。

先阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
agent-work/reviews/RET-001-codex-review.md
agent-work/reviews/RET-002-codex-review.md
agent-work/reviews/RET-003-codex-review.md
agent-work/data/RET-001-retrieval-manifest/README.md
agent-work/data/RET-001-retrieval-manifest/checkpoint.md
agent-work/data/RET-001-retrieval-manifest/handoff.md
agent-work/integration/RET-002-retrieval-baseline/README.md
agent-work/integration/RET-002-retrieval-baseline/checkpoint.md
agent-work/integration/RET-002-retrieval-baseline/handoff.md
agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json
agent-work/integration/RET-003-retrieval-evaluation/protocol-draft.md
agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json
agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
agent-work/integration/RET-003-retrieval-evaluation/handoff.md
src/retrieval/
tests/retrieval/test_retrieval_baseline.py
```

RET-003 的授权与数据边界以 `agent-work/reviews/RET-003-codex-review.md` 和已更新的协议为准；若文件与本 Prompt 冲突、manifest hash 不匹配、或上游记录状态异常，先报告 `review`/`blocked` 并暂停。

## 3. 高风险交接定向复核

RET-001 → RET-002 → RET-003 是高风险数据交接。执行诊断前必须：

1. 运行 RET-001 `verify_manifest.py --tracked-only`，确认 15 条记录、660 项检查、0 失败和冻结 manifest hash；该脚本会写入带时间戳的 `verification-report.json`。在干净工作树下先将该文件临时备份到系统临时目录，运行后检查 diff，再把该报告精确恢复到原内容，不能留下复跑噪声。
2. 运行 RET-002 30 项检索单测。
3. 运行 RET-002 smoke；通过 `--report` 把新报告写到系统临时目录，避免覆盖仓库内报告。
4. 实际抽查一个正常查询、`bore_d=80` held-out 边界查询和一个失败查询；确认候选只来自 `retrieval_source`，失败被结构化拒绝。
5. 核对 RET-001 manifest SHA、15 行规模、角色 9/3/3、RET-002 policy id、候选角色及 `provisional_small_n` 限制。

建议命令（根据 README 核对实际入口）：

```bash
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python \
agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py --tracked-only

PYTHONPATH=src work/benchcad-output/venv/bin/python \
-m unittest discover -s tests/retrieval -v

PYTHONPATH=src work/benchcad-output/venv/bin/python \
agent-work/integration/RET-002-retrieval-baseline/run_smoke.py \
--report /tmp/ret003-ret002-smoke-report.json
```

不要用 `git checkout`、`git restore` 或 reset 清理运行副作用。只在启动时确认工作树干净并备份了精确原件后，才可恢复本次验证唯一改写的 `verification-report.json`；发现额外差异立即停止并报告。

## 4. 诊断输入和查询集合

只使用：

```text
agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl
agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json
agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json
```

要求 manifest SHA-256 固定为：

```text
b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297
```

查询集定义的 3 个主查询必须逐例运行：

- `heldout-bore-012` → `catalog-bore-012`（held-out）
- `heldout-bore-035` → `catalog-bore-035`（held-out）
- `heldout-bore-080` → `catalog-bore-080`（held-out）

另将 2 个接口诊断分开记录：`diagnostic-source-bore-020` 和 `diagnostic-heldout-bore-080-boundary`。结构化失败诊断从 `catalog-bore-020` 的 `parameters.normalized` 复制到内存后，按 query set 删除 `outer_d`，预期 `RETRIEVAL_MISSING_FIELD`。

每个合法查询参数只从对应 manifest `parameters.normalized` 读取。不得复制/改写查询值、创建新样本或把 held-out 行加入索引。索引必须只由冻结 `retrieval-config.json` 构造；候选角色只有 `retrieval_source`，即 3 个 `catalog-bore-006/020/050`。不得更改 query set。

## 5. 实现和结果要求

在 `agent-work/integration/RET-003-retrieval-evaluation/` 内新增小型可复跑脚本，例如 `run_c1_diagnostic.py`。若脚本不需要额外配置，勿另造配置格式。脚本从仓库根目录运行，默认读取上面三份冻结输入并校验 manifest hash、query id、角色及 policy id；校验不符时 fail closed。

输出文件：

```text
agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json
agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md
```

JSON 应逐例保留：

- 协议/query-set 版本、manifest SHA、RET-002 `policy_id`、split 状态和环境版本；
- `query_id`、对应 `sample_id`、角色、查询状态和结构化错误（如有）；
- 所有 top-k 候选的 `sample_id`、`split.role`、rank、总距离、连续距离、离散项及逐字段距离；
- 对 3 个主查询，逐候选列出相对该查询真值的六字段绝对误差；明确它只是给定真值参数下的逐例误差，不用于选策略或选择候选；
- 对 2 个诊断查询单独标记 `diagnostic`，不得混入 3 个主查询的任何分母；
- 失败诊断保留错误码、stage、fields，不丢弃失败行；
- 每个合法查询通过独立进程至少复跑两次，记录完整 canonical 结果 SHA/输出相等性。确定性不通过时保留差异并停止对结果作解释。

Markdown 报告只做逐例描述，分开主查询、接口诊断和失败诊断，列清每例 top-1/top-k 与距离、held-out 排除情况、稳定性和异常。不得把 3 个 held-out 聚合成“准确率”“泛化率”“检索提升率”或统计结论。

必须明确注明：这是一组参数值来自 held-out manifest 的结构化查询诊断，不是自然语言输入评测；距离表示参数近邻度，不表示几何等价、制造可行性、强度、安全或 CAD 生成质量。APP-001 前端到端字段/Schema/CAD/STEP/成本指标均为 `not_measured`。

## 6. 文件边界

仅允许新增或修改：

```text
agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py
agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json
agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md
agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
agent-work/integration/RET-003-retrieval-evaluation/handoff.md
docs/WORKLOG.md                 # 只追加
```

不得修改 `src/**`、`tests/**`、RET-001/RET-002 文件、query set、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`docs/DECISIONS.md` 或审查结论。发现需要扩大范围时先停下申请中枢决定。

## 7. 里程碑、验证和交接

先在 `docs/WORKLOG.md` 追加 `RET-003-C1` 认领记录并保持 `in_progress`。中途若依赖缺失或数据边界不清，立即记录 `blocked` checkpoint，不扩大范围。

完成后至少验证：

```text
RET-001 tracked-only: 15 rows / 660 checks / 0 failures
RET-002 tests: 30 passed
RET-002 smoke: expected cases pass; report written outside tracked repo
C1 main queries: 3/3 executed, candidate roles all retrieval_source
C1 diagnostics: 2/2 recorded separately
failure diagnostic: expected RETRIEVAL_MISSING_FIELD
independent-process determinism: pass for every legal query
JSON parse and report/result cross-check: pass
python -m py_compile run_c1_diagnostic.py: pass
git diff --check: pass
```

更新 checkpoint 和 handoff，记录实际命令及原始结果、文件、未决风险、已知限制和下一步；追加 WORKLOG 并提交一个可审查 commit，commit message 使用：

```text
feat: add RET-003 C1 retrieval diagnostic [RET-003]
```

任务完成后状态保持 `review`，不要标 `done`，不要 push；交给 Codex 中枢独立复核。中枢复核前不能将其用于项目结论。
