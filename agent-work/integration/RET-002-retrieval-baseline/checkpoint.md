# RET-002 checkpoint — 单族确定性检索基线

状态：`review`（交接 Agent 自检完成；等待续任 Agent 定向复核与 Codex 中枢独立审查；未标记 done，未 push）
修正记录：2026-11-03 已修复自定义距离范围可绕过冻结 policy id 的问题，见第 9 节；当前检索测试 30 项。
任务：RET-002
目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
启动 HEAD：`d5f01f1`（启动时工作树干净，`main` 与 `origin/main` 同步）
smoke 里程碑：2026-11-03 首次通过 3 正常/边界 + 13 失败 + 跨进程确定性（本文件已记录）
交付提交：本任务最终 commit（提交信息 `feat: add deterministic retrieval baseline [RET-002]`）；未 push

## 1. 启动检查

- `git rev-parse --show-toplevel` 等于规定根目录；
- `git status --short --branch` 干净；`git log --oneline -6` 最新为 `d5f01f1 docs: prepare retrieval baseline prompt [RET-002]`；
- 已阅读 AGENTS、PROJECT_STATUS、PROJECT_PLAN、WORKLOG、DECISIONS、TASKS、handoff-review-protocol、
  RET-001 中枢审查、RET-001 README/checkpoint/handoff/manifest schema/verifier、IR v0 规范和
  `src/schema/set_screw_shaft_collar.py`；
- 固定环境：Python 3.11.18（`work/benchcad-output/venv`）、macOS 26.6.2 arm64、Darwin 25.6.0。

## 2. RET-001 续任定向复核（高风险数据交接）

```text
handoff_successor_check:
  predecessor=RET-001 checkpoint/handoff（71125d2 + 6c7bae4 中枢复核）
  files_format=manifest-v0.jsonl 15 行、manifest.schema.json、generator/verify_manifest.py、
               README/checkpoint/handoff 均存在且可解析
  core_rerun=verify_manifest.py --tracked-only -> records=15 lines=15 checks_passed=660
             failures=0 / RESULT: PASS（exit 0）
  normal_case=catalog-bore-020（retrieval_source，单 solid/单 shell/valid，体积 6712.631936 mm³）
              catalog-bore-080（heldout_evaluation，second_screw=1，74 面/149 边）
  failure_case=replay_check.py -> tampered_radial_offset pass=True（semantic 阶段
               IR_NODE_INPUT_KIND_MISMATCH，node_ids=["n2.hole.primary"]）；
               catalog_mismatch pass=True（schema 阶段 CATALOG_MISMATCH）；
               两个负对照各跑 2 次一致；STEP 字节不同按策略允许
  interface=输入为 manifest 参数/特征字段，输出为检索候选记录；未修改 IR、Schema 或 CAD 构造接口
  limits=provisional_small_n、reproducibility_partial、MERGED、license_scope_uncertain、
         revolved_ring_approximation 均保留
  result=pass
  blocking_issue=none
```

### 2.1 记录差异（已解释，不覆盖 RET-001）

RET-001 checkpoint 的 hash 表中 `manifest-v0.jsonl` 为
`37818543d6bb9f3622c9f22a9c2b4f3853beb46ad6eecc1da501bf0cd0af64dc`，仓库当前实际为
`b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`。差异来源是中枢提交
`6c7bae4`（`docs: accept retrieval manifest review [RET-001]`）明确重新生成了 manifest 和
generation-report，以同步 `tolerance_profile=CAD-006.geometry-comparison.v1`；该提交同时更新了
verification/replay report 和 IR 示例。重新运行的 `--tracked-only` 校验 660 项 0 失败，因此这是
**已声明的再生成**，不是未记录的数据篡改。本任务未修改 RET-001 目录中的任何文件，并在
`retrieval-config.json` 中固定当前 hash；若 manifest 再生成，配置必须由负责人显式更新。

另外，`verify_manifest.py` / `replay_check.py` 每次运行都会重写 RET-001 目录下的
`verification-report.json` / `replay-report.json`（内容主要是运行时间和工件检查范围）。复核完成后
已用 `git checkout --` 将这两个文件恢复到 HEAD，RET-001 目录净改动为 0；manifest 本身未被重写。

## 3. 设计决策

1. **两种查询形式，规则不复制。**
   - CAD-003 envelope：直接调用 `validate_parameters`，由 Schema 做单位换算、目录耦合和
     `second_screw` 派生；未通过 Schema 则结构化拒绝。
   - flat canonical parameters：要求六个字段齐全（mm），缺失不默认；对完整对象仍调用 Schema 判定。
     Schema 拒绝时继续近邻检索，但标记 `out_of_catalog_or_unvalidated`，不把查询当目录真值。
   选择理由：envelope 表达“Schema 可见的真值”，flat 表达“等待校验的检索查询”；两者都不复制
   CAD-003 规则。目录行之间的查询用 flat 表达。
2. **距离规则固定。** 五个连续字段用完整 15 行目录范围归一化后等权平均；`second_screw` 不同
   加 0.5。0.5 是预先固定的结构性差异（单/双螺钉），不是从数据或评测集调参得到；配置加载会拒绝
   改动 weights，要求新 policy id。查询超出目录范围时距离可大于 1，并在 README 说明。
3. **候选角色显式。** `from_manifest` 的 `candidate_roles` 没有默认值；配置显式写
   `["retrieval_source"]`。未知角色、空角色、缺失角色都 fail closed；重复 sample_id/group_id 拒绝。
4. **排序与 top_k。** 排序键 `(total, sample_id)`；`top_k` 必须是 1..候选数的整数，不静默截断。
   当前候选 3 个，默认 `top_k=3`。
5. **错误协议。** 所有失败均为 `RetrievalError`，带 `code/stage/fields/message/details`；
   index/config/query 三个阶段分开，非法输入不会产生半成品结果。
6. **数据边界。** 只读 manifest JSONL；不打开 IR 文件、STEP、渲染图或第三方图纸；manifest 中的
   IR/验证 hash 原样携带。结果 `data_boundary` 明确记录 `reads_step=false` 等。
7. **配置绑定。** `retrieval-config.json` 固定 manifest 路径、SHA-256、ranges、weights 和
   candidate roles；`RetrievalIndex.from_config` 会校验 manifest hash 和 ranges 与
   `src/schema.CATALOG_ROWS` 一致。

## 4. 修改文件

生产代码（新增）：

```text
src/retrieval/__init__.py
src/retrieval/baseline.py
src/retrieval/distance.py
src/retrieval/config.py
src/retrieval/errors.py
```

测试（新增）：`tests/retrieval/__init__.py`、`tests/retrieval/test_retrieval_baseline.py`（原始 24 项；策略修正后 30 项）。

集成目录（新增）：`agent-work/integration/RET-002-retrieval-baseline/` 下 README、checkpoint、
handoff、retrieval-config.json、run_smoke.py、replay_query.py、smoke-report.json、
examples/×3。

只追加：`docs/WORKLOG.md`。

未修改：`src/schema/**`、`src/cad_compilation/**`、`agent-work/typed-cad-ir/**`、
`agent-work/cad-validation/**`、`agent-work/data/RET-001-retrieval-manifest/**`、
`docs/DECISIONS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、
`database/**`。未读取/生成 STEP 或渲染物；仅在 ignored `work/ret-002-output/` 写入重复候选
manifest 供失败检查。

## 5. 执行记录（实际运行）

```bash
# 30 项检索单元测试（原始 24 + 策略范围回归 6）
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v
# -> Ran 30 tests ... OK

# smoke：3 个正常/边界 + 13 个失败 + 跨进程确定性
PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
# -> 3 cases PASS; failure cases 13/13; checks=70 failed=0; RESULT: PASS
# -> determinism in_process=True cross_process=True
#    sha256=0fcf84b752db919d7eb65ba6b4df88080d2e800ec22021bef4e5e52dc172e3b9

# RET-001 数据完整性复核
... verify_manifest.py --tracked-only
# -> records=15 lines=15 checks_passed=660 failures=0 / RESULT: PASS

# 现有测试回归
PYTHONPATH=src ... -m unittest discover -s tests/schema          # 17 OK
PYTHONPATH=src ... -m unittest discover -s tests/typed_cad_ir    # 5 OK
PYTHONPATH=src:snapshot ... -m unittest discover -s tests/cad_compilation  # 13 OK

# 语法与 JSON
work/benchcad-output/venv/bin/python -m py_compile src/retrieval/*.py \
  agent-work/integration/RET-002-retrieval-baseline/{run_smoke,replay_query}.py
python3 -m json.tool <每个新增 JSON>  # 全部可解析
```

接口自检（与 Prompt 示例一致）：

```text
query_status=out_of_catalog_or_unvalidated
order=['.../catalog-bore-020', '.../catalog-bore-006', '.../catalog-bore-050']
totals=[0.009333333333333334, 0.22494444444444445, 0.42422222222222217]
sha256=eb3d1ffd030b7edbdbf10c9e12b8287bffdebae712f1c4137572cd72ec7049fe
```

## 6. handoff_self_check

```text
task=RET-002
status=review
changed=src/retrieval/**（5 个新模块）；tests/retrieval/**（__init__ + 30 项测试：原 24 + 策略回归 6）；
        agent-work/integration/RET-002-retrieval-baseline/**（README、checkpoint、handoff、
        retrieval-config.json、run_smoke.py、replay_query.py、smoke-report.json、examples/×3）；
        docs/WORKLOG.md（只追加）
commands=见第 5 节，全部实际运行并记录结果
confirmed=30 项检索测试通过（原 24 + 策略回归 6）；3 个正常/边界案例与 13 个失败案例全部通过（70 项检查）；
          同一查询进程内与两个独立进程 canonical JSON 逐字一致；RET-001 --tracked-only
          660 项 0 失败；schema 17 / IR 5 / CAD 13 回归通过；manifest hash、candidate roles、
          provisional split 和限制在结果与报告中保留
unresolved=split 未冻结；候选只有 3 个；envelope 必须通过 Schema 而 flat 必须完整；
          weights 未经 RET-003 验证；单环境；配置与 manifest hash 绑定；
          docs/TASKS.md 与 PROJECT_STATUS 的状态未同步（超出文件边界）
next_agent_focus=见 handoff.md 的复核清单；优先检查 held-out 不越界、失败路径、
          provisional split 表述和 manifest hash 绑定
```

## 7. 未解决 / 交中枢判断

1. **split 未冻结**：9/3/3 仍是 `provisional_small_n`；RET-002 不决定正式 benchmark 切分。
2. **候选稀疏**：只有 3 个 `retrieval_source` 行，`top_k` 上限为 3；排序区分度受数据量限制。
   本任务不通过复制/扩写样本解决。
3. **查询形式取舍**：envelope 严格走 Schema，flat 必须六字段齐全；目录行之间的查询只能用 flat。
   若中枢希望 flat 也支持 `bore_d` 派生，需要新接口决策，不应在本任务中静默改变。
4. **权重 0.5**：预先固定的可解释选择，未做敏感性分析；RET-003 可评估不同权重，但不得把
   在评测集上调出的权重伪装成先验规则。
5. **配置 hash 绑定**：manifest 再生成会使 `retrieval-config.json` 失效；这是 fail-closed 设计，
   需要负责人显式更新并记录。
6. **文档状态**：`docs/TASKS.md` 中 RET-002 仍为 `planned`，`PROJECT_STATUS` 未更新；超出本任务
   允许的文件边界，需中枢同步。
7. **单环境**：只验证固定 macOS arm64；跨平台/跨进程承诺仅限本次记录的确定性检查。
8. **许可证/上游状态**：`reproducibility_partial`、`MERGED`、`license_scope_uncertain`、
   `revolved_ring_approximation` 继续有效；未读取 STEP，未新增族。

## 8. 下一步

- 续任 Agent 按 `handoff.md` 重跑检索测试、smoke、RET-001 `--tracked-only`，并检查
  `catalog-bore-080` 不进入候选、非法输入仍被拒绝、输出未把 provisional split 写成 benchmark。
- 策略范围契约修正已完成（第 9 节），等待 Codex 中枢重新复核；本任务保持 `review`，不 push、不标 `done`。

## 9. 策略范围契约修正（2026-11-03）

状态：`review`（修正完成，等待 Codex 中枢重新复核；未 push、未标 done）

### 9.1 修正前可绕过行为

`RetrievalIndex.from_manifest(..., policy=...)` 接受 `DistancePolicy`，而旧 `validate()` 只检查字段集合、有限性、`min < max` 和权重，没有检查范围是否等于 `catalog_ranges()`。复现结果：

```text
ranges = catalog_ranges(); ranges["bore_d"] = (0.0, 1.0)
DistancePolicy(ranges=ranges).validate()          -> 通过（错误）
RetrievalIndex.from_manifest(..., policy=policy)  -> 建索引成功（错误）
query(...) 输出 policy_id=RET-002.parametric_distance.v1
distance.fields.bore_d.catalog_range_mm = [0.0, 1.0]（错误：语义已改变）
```

### 9.2 修正后拒绝行为

`src/retrieval/distance.py`：

- `validate()` 对每个连续字段要求 `(min, max)` 与 `catalog_ranges()` 精确相等；值必须是 int/float 且非 bool、有限、`min < max`。不相等即抛
  `RetrievalError(code=RETRIEVAL_CONFIG_INVALID, stage=config, fields=(field,))`，`details` 含
  `policy_id`、`expected`、`observed`。
- `DistancePolicy.__post_init__` 冻结 range 的映射和值；构造后修改调用方 dict/list 不会改变
  policy，也不会改变已建索引的距离语义。
- `from_manifest(..., policy=...)` 保持现有接口，但会调用 `validate()`；`from_config()` 路径不变。

实测：

```text
custom policy validate: RETRIEVAL_CONFIG_INVALID config ('bore_d',)
  expected=[5.0, 80.0] observed=[0.0, 1.0]
custom policy from_manifest: RETRIEVAL_CONFIG_INVALID config ('bore_d',)
normal query (envelope bore_d=20): catalog_validated top1=catalog-bore-020 total=0.0
failure query (missing fields): RETRIEVAL_MISSING_FIELD query
alias attempt (mutate caller dict/list after index build): policy range stays (5.0, 80.0),
  query total stays 0.009333333333333334
```

### 9.3 修改文件（本轮）

- `src/retrieval/distance.py`：范围冻结校验与不可变副本。
- `tests/retrieval/test_retrieval_baseline.py`：新增 6 项回归测试（原 24 项保留，共 30 项）。
- `README.md`、`checkpoint.md`、`handoff.md`：策略契约、测试数量和限制说明。
- `docs/WORKLOG.md`：只追加。

未修改：`src/schema/**`、`src/cad_compilation/**`、`agent-work/data/RET-001-retrieval-manifest/**`、
IR/CAD 验证材料、DECISIONS/PROJECT_STATUS/PROJECT_PLAN/TASKS、database。未读取/生成 STEP 或渲染物。

### 9.4 回归测试覆盖

1. `test_distance_policy_rejects_changed_bore_range`
2. `test_distance_policy_rejects_changed_other_continuous_ranges`（outer_d / screw_d / screw_len / width）
3. `test_distance_policy_rejects_non_finite_non_numeric_and_approximate_ranges`（NaN/Inf/bool/"5"/80+1e-12）
4. `test_from_manifest_rejects_custom_policy_range`
5. `test_frozen_catalog_ranges_build_index_and_match_default_results`
6. `test_policy_does_not_alias_caller_range_mapping`

加上原有 24 项，`tests/retrieval` 共 30 项，无原有测试被削弱或删除。

### 9.5 实际运行命令与结果

```bash
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v
# -> Ran 30 tests ... OK

PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
# -> 3 cases PASS; failure cases 13/13; checks=70 failed=0; RESULT: PASS
# -> determinism pass=True sha256=0fcf84b7...

... verify_manifest.py --tracked-only
# -> records=15 checks_passed=660 failures=0 / RESULT: PASS

work/benchcad-output/venv/bin/python -m py_compile src/retrieval/*.py
# -> PY_COMPILE_OK

git diff --check
# -> 通过
```

策略证据：

```text
normal:   catalog_validated catalog-bore-020 total=0.0
          envelope replay sha256=0fcf84b7...（与修正前一致）
failure:  RETRIEVAL_MISSING_FIELD query
          fields=('outer_d','screw_d','screw_len','second_screw','width')
custom:   RETRIEVAL_CONFIG_INVALID config fields=('bore_d',)
          expected=[5.0,80.0] observed=[0.0,1.0]
alias:    policy range remains (5.0, 80.0); query total 0.009333333333333334
```

保留事实：manifest SHA-256 `b7b6c737...`、15 行、9/3/3、3 个 `retrieval_source` 候选、
`provisional_small_n`、单环境与全部许可证/几何限制均未改变。运行 smoke 和 RET-001 校验会重写带
时间字段的报告，已恢复到 HEAD；RET-001 目录净改动为 0。

### 9.6 未解决 / 下一 Agent 关注

1. 本次修正只关闭策略范围/权重入口；仍等待 Codex 中枢重新审查后决定是否标记 `done`。
2. `weights.total_formula` / `tiebreak` 说明字符串未单独校验（审查记录已列为后续可补项，非当前阻塞）。
3. 其余限制（split 未冻结、3 个候选、单环境、manifest hash 绑定、许可边界）保持原样。
4. 下一 Agent 应重跑 30 项测试、smoke、自定义范围拒绝案例，并确认正常/边界查询结果与
   `0fcf84b7...` 一致。
