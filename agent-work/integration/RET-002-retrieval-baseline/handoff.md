# RET-002 handoff — 单族确定性检索基线

状态：`review`（2026-11-03 已修正策略范围可绕过问题，等待 Codex 中枢重新审查；未 push、未标 done）
任务：RET-002
族：`set_screw_shaft_collar`
交付提交：`feat: add deterministic retrieval baseline [RET-002]`（本任务最终 commit）
交付目录：`agent-work/integration/RET-002-retrieval-baseline/`
固定环境：Python 3.11.18 / macOS 26.6.2 arm64 / Darwin 25.6.0

## 1. 修改了什么

新增生产代码：

```text
src/retrieval/__init__.py
src/retrieval/baseline.py
src/retrieval/distance.py
src/retrieval/config.py
src/retrieval/errors.py
```

新增测试：`tests/retrieval/__init__.py`、`tests/retrieval/test_retrieval_baseline.py`（原 24 项；策略修正后 30 项）。

新增集成材料：`agent-work/integration/RET-002-retrieval-baseline/` 下 README、checkpoint、
handoff、retrieval-config.json、run_smoke.py、replay_query.py、smoke-report.json、examples/×3。

只追加：`docs/WORKLOG.md`。

未修改：Schema、Typed CAD IR、CAD 编译器/验证器、容差策略、RET-001 manifest、DECISIONS、
PROJECT_STATUS、PROJECT_PLAN、TASKS、database。未读取或生成 STEP/渲染物。

## 2. 入口、格式与接口

- 公共入口：`src/retrieval/__init__.py` → `RetrievalIndex` / `RetrievalError` /
  `RetrievalConfig` / `DistancePolicy`。
- 构建：`RetrievalIndex.from_manifest(manifest_path, candidate_roles={...})` 或
  `RetrievalIndex.from_config(config_path)`。
- 查询：`index.query(family_id, parameters, top_k)`；返回 `RetrievalResult`，
  可用 `.as_dict()`、`.to_json()`、`.to_canonical_json()`、`.sha256()`。
- 输入：
  - CAD-003 envelope（含 `schema_version`/`family_id`/`parameters` 标记）→ 现有
    `validate_parameters` 归一化，必须通过 Schema；
  - flat 六字段（mm）→ 完整才接受；Schema 拒绝时继续近邻并标记
    `out_of_catalog_or_unvalidated`。
- 输出：候选 `sample_id`、`split.role/group_id/split_status`、`source.source_commit`、
  `ir.path/sha256`、字段级距离、验证摘要、限制；顶层带 `split_status=provisional_small_n`。
- 错误：`RetrievalError.as_dict()` 给稳定 `code/stage/fields/message/details`。
- 数据边界：只读 RET-001 manifest JSONL，不读 IR 文件/STEP/渲染/第三方图纸；manifest 中
  `ir.sha256` 和验证摘要原样携带。

## 3. 核心命令与预期结果（续任者必须至少重跑一条）

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"

# A. 30 项单元测试（原 24 + 策略范围回归 6，约 0.1 秒）
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v
# 预期：Ran 30 tests ... OK

# B. smoke（约 2-3 秒，含两个子进程）
PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
# 预期：3 cases PASS；failure cases 13/13；checks=70 failed=0；
#       determinism pass=True；RESULT: PASS

# C. RET-001 数据完整性（约 1 秒）
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python \
  agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py --tracked-only
# 预期：records=15 checks_passed=660 failures=0 / RESULT: PASS

# D. 单查询复放（跨进程确定性）
PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/replay_query.py \
  --config agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json \
  --case agent-work/integration/RET-002-retrieval-baseline/examples/query-in-catalog.json
# 预期：sha256=0fcf84b752db919d7eb65ba6b4df88080d2e800ec22021bef4e5e52dc172e3b9
```

## 4. 必查的正常/边界/失败案例

| 类型 | 位置 | 预期 |
|---|---|---|
| 正常（目录内） | `examples/query-in-catalog.json`；bore_d=20 envelope | `catalog_validated`；top1 `catalog-bore-020`；total 0.0；same row=true |
| 边界（行之间） | `examples/query-between-catalog-rows.json`；bore_d=18 flat | `out_of_catalog_or_unvalidated`；top1 `catalog-bore-020`；total 0.009333；无 same row |
| 边界（held-out） | smoke 的 `boundary_bore_080_second_screw` | `catalog_validated`；top1 `catalog-bore-050`；**不出现** `catalog-bore-080`；全部候选 role=retrieval_source |
| 失败（缺字段） | `examples/query-invalid.json` | `RETRIEVAL_MISSING_FIELD`，fields=`["outer_d"]` |
| 失败（自定义范围） | `DistancePolicy(ranges=catalog_ranges() 篡改 bore_d=(0,1))` + `from_manifest(..., policy=...)` | `RETRIEVAL_CONFIG_INVALID`，stage=config，fields 含 `bore_d`；不产生索引或结果 |
| 失败（未知族） | smoke inline | `RETRIEVAL_UNKNOWN_FAMILY` |
| 失败（未知字段） | smoke inline | `RETRIEVAL_UNKNOWN_FIELD` |
| 失败（非有限数） | smoke inline | `RETRIEVAL_INVALID_PARAMETER` |
| 失败（top_k） | smoke inline | 0/True → `RETRIEVAL_INVALID_TOP_K`；4 → `RETRIEVAL_TOP_K_OUT_OF_RANGE` |
| 失败（空/缺失/未知角色） | smoke inline | `EMPTY_CANDIDATE_ROLES` / `CANDIDATE_ROLES_REQUIRED` / `UNKNOWN_ROLE` |
| 失败（重复候选） | smoke inline，写入 ignored `work/ret-002-output/duplicate-manifest.jsonl` | `RETRIEVAL_DUPLICATE_SAMPLE_ID` |

确定性：同一查询进程内重复两次、两个独立进程复放，canonical JSON 逐字一致；
`sha256=0fcf84b7...`（目录内案例）。排序键 `(total, sample_id)`。

## 5. 接口确认

- 输入：RET-001 manifest 的结构化参数、来源、IR 路径/hash、验证摘要和 split；查询参数为
  CAD-003 envelope 或六字段 flat（mm）。
- 输出：检索候选记录（JSON），不修改 IR、Schema、CAD 编译器或构造接口。
- 未新增/修改任何冻结接口；检索是 manifest 的只读消费者。
- `split.role` 只用于候选过滤和结果标注；不参与距离计算。

## 6. 已确认 / 未解决

已确认：

- 30 项检索测试通过（原 24 + 策略回归 6）；smoke 3 个正常/边界 + 13 个失败 + 70 项检查全部通过；
- 进程内与跨进程 canonical JSON 一致；固定环境可复现；
- RET-001 `--tracked-only` 660 项 0 失败；schema 17 / IR 5 / CAD 13 回归通过；
- held-out 行（12/35/80）不会进入 `retrieval_source` 候选；
- 自定义连续范围（含别名修改）被 `RETRIEVAL_CONFIG_INVALID` 拒绝，冻结范围仍保持原排序和距离；
- manifest hash `b7b6c737…`、candidate roles、`provisional_small_n` 和全部限制在结果/报告中保留；
- 未读取 STEP/渲染物，未下载 BenchCAD Public/Core，未新增族。

未解决（须中枢判断，不要擅自"修好"）：

1. split 是否冻结仍待 RET-003；当前只是 `provisional_small_n`；
2. 候选只有 3 个 `retrieval_source` 行，`top_k` 上限 3；数据稀疏是事实，不得扩写；
3. envelope 严格过 Schema、flat 必须完整六字段是接口取舍；若要在 flat 形式派生字段，需新决策；
4. `second_screw` 的 0.5 权重是预先固定的工程选择，未做敏感性/收益验证；
5. `retrieval-config.json` 固定 manifest hash，manifest 再生成时需负责人显式更新；
6. `docs/TASKS.md` / `PROJECT_STATUS.md` 的 RET-002 状态未同步（超出本任务文件边界）；
7. 单环境验证；跨平台/跨进程承诺仅限本次记录；
8. `reproducibility_partial`、`MERGED`、`license_scope_uncertain`、`revolved_ring_approximation`
   继续有效；
9. 策略范围修正是本轮唯一改动，仍待 Codex 中枢重新审查后才可标记 `done`。

## 7. 大文件与未提交内容

- 本任务没有 STEP、渲染图、网格或第三方图纸；未读取这些资产。
- 重跑 RET-001 的 `verify_manifest.py` / `replay_check.py` 会重写其 `verification-report.json` /
  `replay-report.json`；本次复核后已恢复到 HEAD，RET-001 目录无净改动。续任者复核后也应恢复，
  不要把 predecessor 的报告时间戳变化当作交付内容。
- smoke 会在 ignored `work/ret-002-output/duplicate-manifest.jsonl` 写入一份重复候选测试
  manifest；被 `.gitignore` 排除，不是交付物。
- 已提交内容只有源码、测试、配置、示例、报告和交接文档。

## 8. 续任 Agent 复核记录模板

```text
handoff_successor_check:
  predecessor=RET-002 checkpoint/handoff（交付 commit 见 git log）
  files_format=<src/retrieval 5 模块、tests/retrieval 30 项、integration 目录文件是否存在且可解析>
  core_rerun=<tests/retrieval 或 run_smoke.py 的实际命令与结果>
  normal_case=<query-in-catalog 或 boundary_bore_080 的结果>
  failure_case=<query-invalid 或 duplicate_candidate 的结果>
  interface=<envelope/flat 输入、RetrievalResult 输出、schema_check/query_status 是否一致>
  limits=<provisional_small_n、3 个候选、单环境、manifest hash 绑定、license 限制是否保留>
  result=pass | review | blocked
  blocking_issue=<若 review/blocked 写明>
```

发现交接记录与实际结果不一致时，先写 `review`/`blocked`，不要覆盖已有成果。

## 9. 中枢审查建议顺序

1. 读 `README.md` 第 3/4/6/7/9 节与 `smoke-report.json` 的 `cases`、`failure_cases`、
   `determinism`；
2. 重跑 `tests/retrieval` 与 `run_smoke.py`，确认 30 项和 70 项检查；
3. 检查 `catalog-bore-080` 是否始终被排除、`query_status` 是否如实标记、失败是否结构化；
4. 检查距离公式、ranges、0.5 权重与排序 tie-break 是否符合任务规则，并验证自定义范围（含构造后改 dict/list）仍被拒绝；
5. 判断接口取舍（envelope 严格 / flat 完整）和 split 问题是否需要返工；
6. 决定 RET-002 是否转 `done`、是否合并并放行 RET-003；本任务不自行标 done、不 push。

## 10. 策略范围契约修正（2026-11-03）

状态：`review`（修正完成，等待 Codex 中枢重新复核；未 push、未标 done）

### 10.1 修正前/后

修正前：`RetrievalIndex.from_manifest(..., policy=...)` 可传入自定义连续范围（例如把
`bore_d` 改成 `(0, 1)`），旧 `DistancePolicy.validate()` 只检查字段集合、有限性和权重，
因此索引可以建立，结果仍输出 `policy_id=RET-002.parametric_distance.v1`，距离语义被静默改变。

修正后：`DistancePolicy.validate()` 要求每个连续字段的 `(min, max)` 与完整目录
`catalog_ranges()` 精确相等，并显式拒绝 bool、非数值、NaN/Inf 和近似值。自定义范围返回：

```text
RETRIEVAL_CONFIG_INVALID
stage=config
fields=("bore_d",)
details.expected=[5.0, 80.0]
details.observed=[0.0, 1.0]
```

`DistancePolicy` 同时冻结 range 的映射和值，索引建好后再修改调用方 dict/list 也不会改变已建索引。
`from_manifest(..., policy=...)` 保留，但必须通过校验；`from_config()` 接口不变。

### 10.2 修改文件

- `src/retrieval/distance.py`：范围精确校验 + 不可变 range 副本。
- `tests/retrieval/test_retrieval_baseline.py`：新增 6 项回归测试，共 30 项。
- `README.md`、`checkpoint.md`、`handoff.md`、`docs/WORKLOG.md`：文档与日志。

未修改 Schema、IR、CAD 编译器/验证器、RET-001 manifest、DECISIONS/PROJECT_STATUS/
PROJECT_PLAN/TASKS、database；未读取或生成 STEP/渲染物。

### 10.3 实际运行

```bash
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v
# Ran 30 tests ... OK

PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
# 3 cases PASS; failure cases 13/13; checks=70 failed=0; determinism pass=True
# sha256=0fcf84b7...

... verify_manifest.py --tracked-only
# records=15 checks_passed=660 failures=0 / RESULT: PASS

work/benchcad-output/venv/bin/python -m py_compile src/retrieval/*.py
# PY_COMPILE_OK
```

正常查询（envelope `bore_d=20`）：`catalog_validated`，top1 `catalog-bore-020`，total 0.0，
canonical SHA 仍为 `0fcf84b7...`。失败查询（缺字段）：`RETRIEVAL_MISSING_FIELD`。
自定义范围查询：`RETRIEVAL_CONFIG_INVALID`（stage=config，fields 含 `bore_d`）。
smoke 和 RET-001 的运行报告已恢复到 HEAD，避免时间戳噪声。

### 10.4 保留限制

manifest SHA-256 `b7b6c737...`、15 条记录、9/3/3、3 个 `retrieval_source` 候选、
`provisional_small_n`、单环境、`reproducibility_partial`、`MERGED`、
`license_scope_uncertain`、`revolved_ring_approximation` 均未改变。

### 10.5 未解决

1. 等待 Codex 中枢重新审查，确认策略范围不可绕过后再标记 `done`。
2. `weights.total_formula` / `tiebreak` 描述字符串仍未逐字校验（后续策略版本化可补，非当前阻塞）。
3. 其他限制与下一 Agent 关注点同第 6 节和 `checkpoint.md` 第 9 节。
