# RET-002 单族确定性检索基线

状态：`review`（2026-11-03 已修正自定义距离范围可绕过问题，等待 Codex 中枢重新审查；未标记 done，未 push）
任务：RET-002
族：`set_screw_shaft_collar`（ADR-0007 首期唯一族）
检索策略：`RET-002.parametric_distance.v1`
split 状态：`provisional_small_n`（**不是正式评测集**）

本目录实现一个可复现、可解释、无外部服务依赖的单族参数近邻检索基线。它只消费 RET-001 manifest 的结构化字段，不读取 STEP、渲染图、IR 文件或第三方图纸，不引入向量库、embedding、LLM、训练或新样本。

## 1. 事实与边界

| 项 | 值 |
|---|---|
| manifest | `agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl` |
| manifest SHA-256 | `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297` |
| manifest 记录 | 15 条（development 9 / retrieval_source 3 / heldout_evaluation 3） |
| 候选角色 | 仅 `retrieval_source`（3 条：bore_d = 6, 20, 50） |
| 查询族 | 仅 `set_screw_shaft_collar` |
| 参数单位 | 内部统一 mm；`second_screw` ∈ {0, 1}，无量纲 |
| Schema | `set_screw_shaft_collar.v0`（envelope 归一化直接调用现有 Schema） |
| IR | `typed-cad-ir.v0` / revision `0.2.0`（只读取 manifest 中的路径与 sha256） |
| 几何策略 | `CAD-006.geometry-comparison.v1`（只读取 manifest 中的验证摘要） |
| Python / OS | Python 3.11.18 (CPython) / macOS 26.6.2 arm64，Darwin 25.6.0 |
| 是否读取 STEP | **否**；也不读取渲染图、IR 文件和 BenchCAD Public/Core |

数据边界：候选只来自显式指定的 candidate role；held-out 行不会因 top_k 或排序被隐式混入。检索分数只表示参数近邻度，不表示 CAD 几何等价、可制造性、强度安全或生成质量。生成 STEP/渲染物的许可仍是 `license_scope_uncertain`，本任务不读取、不提交、不再发布。

## 2. 文件、模块入口与测试

生产代码：

```text
src/retrieval/__init__.py     公共导出：RetrievalIndex / RetrievalError / RetrievalConfig / DistancePolicy
src/retrieval/baseline.py     manifest 索引、查询归一化、稳定排序、结果序列化
src/retrieval/distance.py     RET-002.parametric_distance.v1 距离实现
src/retrieval/config.py       frozen ranges/weights、配置加载与校验
src/retrieval/errors.py       结构化 RetrievalError
```

测试：

```text
tests/retrieval/test_retrieval_baseline.py   30 项 unittest（原 24 + 策略范围契约回归 6）
```

集成与报告：

```text
agent-work/integration/RET-002-retrieval-baseline/
├── README.md                 本文件
├── checkpoint.md             交接自检与 RET-001 续任复核
├── handoff.md                续任 Agent 复核清单
├── retrieval-config.json     固定 candidate roles、ranges、weights、manifest hash
├── run_smoke.py              正常/边界/失败/确定性 smoke
├── replay_query.py           单查询复放，用于跨进程逐字一致检查
├── smoke-report.json         机器可读运行报告
└── examples/
    ├── query-in-catalog.json
    ├── query-between-catalog-rows.json
    └── query-invalid.json
```

调用方式（仓库根目录，`PYTHONPATH=src`）：

```python
from retrieval import RetrievalIndex

index = RetrievalIndex.from_manifest(
    "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl",
    candidate_roles={"retrieval_source"},   # 必须显式传入
)
result = index.query(
    family_id="set_screw_shaft_collar",
    parameters={
        "bore_d": 18,
        "outer_d": 30,
        "screw_d": 6,
        "screw_len": 8,
        "second_screw": 0,
        "width": 14,
    },
    top_k=3,
)
print(result.to_json())
print(result.sha256())
```

或从配置文件构建（会校验 manifest SHA-256、ranges 和 weights）：

```python
index = RetrievalIndex.from_config(
    "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json"
)
```

失败以 `RetrievalError` 抛出，`exc.as_dict()` 返回稳定的 `code/stage/fields/message/details`。

## 3. 查询形式与状态

### 3.1 CAD-003 envelope（先过 Schema）

带 `schema_version` / `family_id` / `parameters` 任一标记的对象按 envelope 处理，直接调用 `schema.set_screw_shaft_collar.validate_parameters`。Schema 会完成单位换算、目录行派生和 `second_screw` 规则派生，本实现不复制这些规则。

- 通过 Schema → `input_form=cad003_envelope`，`query_status=catalog_validated`；
- 未通过 Schema → `RETRIEVAL_SCHEMA_REJECTED`，附带 Schema 的错误码、字段和 `schema_errors`。

因此 envelope 只能表达 Schema 认可的目录真值。目录行之间的查询请使用 flat 形式。

### 3.2 Flat canonical parameters（六个字段，mm）

六个字段必须全部给出，缺失字段直接报 `RETRIEVAL_MISSING_FIELD`，不默认 0、不猜测。数值必须是有限数，`second_screw` 必须是整数 0/1。

对完整的 flat 查询仍调用现有 Schema 做一次判定：

- 通过 → `query_status=catalog_validated`；
- 未通过（例如 `bore_d=18` 的 `CATALOG_CHOICE`、耦合错误或 `second_screw` 约束错误）→ 继续近邻检索，但结果标记 `query_status=out_of_catalog_or_unvalidated`，并把 Schema 错误码写入 `query.schema_check.errors`。这不是把查询当成合法目录真值。

### 3.3 状态与限制摘要

| 状态 | 含义 | 是否可作为目录真值 |
|---|---|---|
| `catalog_validated` | 查询通过现有 CAD-003 Schema | 是（仍不等于几何等价） |
| `out_of_catalog_or_unvalidated` | 查询未通过 Schema，仅做参数近邻 | **否** |

`top_k` 必须是 1..候选数的整数；`top_k=0`、负数、布尔、浮点和超过候选数均返回结构化错误。默认 `top_k=3`，与当前 3 个候选一致。

## 4. 距离规则（固定权重）

对五个连续字段：

```text
d_field = abs(query - candidate) / (catalog_max - catalog_min)
continuous_mean = mean(d_bore_d, d_outer_d, d_screw_d, d_screw_len, d_width)
discrete_term = 0.5 * (second_screw differs ? 1 : 0)
total = continuous_mean + discrete_term
```

| 字段 | 目录范围 (mm) | 归一化分母 | 权重 |
|---|---:|---:|---:|
| `bore_d` | 5 – 80 | 75 | 每个连续字段在 mean 中等权，即 0.2 |
| `outer_d` | 10 – 110 | 100 | 同上 |
| `screw_d` | 3 – 12 | 9 | 同上 |
| `screw_len` | 4 – 20 | 16 | 同上 |
| `width` | 6 – 22 | 16 | 同上 |
| `second_screw` | 0 / 1 | 离散 | 固定 0.5 |

规则说明：

- 范围来自**完整 15 行 GN 705 目录**，不是仅 3 个候选行；回归测试核对 `retrieval-config.json` 与 `src/schema` 的 `CATALOG_ROWS` 完全一致。
- 五个连续字段等权平均；`second_screw` 的 0.5 是预先固定的结构性差异项（单螺钉 vs 双螺钉，等价于半个连续均值的满量程），不是从评测集学习或调参得到。改变权重必须换新的 policy id 并经中枢审查，配置加载会拒绝改动。
- **策略范围不可覆盖。** `RET-002.parametric_distance.v1` 的五个连续范围与两个权重是冻结契约。`DistancePolicy.validate()` 要求每个连续字段的 `(min, max)` 与完整目录 `catalog_ranges()` 精确相等，并拒绝非数值、布尔、NaN/Inf、近似值和自定义范围；`RetrievalIndex.from_manifest(..., policy=...)` 会调用该校验，因此不能再借自定义 range 改变语义。范围或权重变更必须建立新 policy id 并经中枢审查。
- `DistancePolicy` 在构造时冻结 range 副本（键和值都不可再由调用方修改），因此索引建好后再改原 dict/list 不会改变已建索引的距离语义。
- 查询超出目录范围时距离可大于 1；这是有意的，表示查询已远离目录范围，而不是被截断。
- 排序键是 `(total, sample_id)` 升序；同分时按 `sample_id` 字典序稳定 tie-break。
- 不使用 STEP/IR hash 计算几何相似度；manifest 中的 hash 只作产物标识。

## 5. 结果字段

每个候选返回：

- `sample_id` / `family_id` / `sample_kind`；
- `split.role` / `group_id` / `split_status` / `split_rule`；
- `source.repository` / `source_commit` / `family_path` / `family_status` / `release_qualified` / `snapshot_status` / `license_scope` / `catalog_row`；
- `ir.path` / `ir.sha256` / `ir_version` / `ir_revision` / `status`；
- `parameters.normalized` / `units` / `provenance` / `input_payload`；
- `distance.total` / `continuous_mean` / `discrete_term` / `fields.*.normalized_abs_diff` / `fields.*.contribution` / `second_screw`；
- `validation_summary`（Schema、族规则、编译、native 几何、重复性、STEP 回读摘要）；
- `limitations`（原样保留 manifest 限制）。

结果顶层包含 `split_status=provisional_small_n`、`policy_id`、`manifest` 身份、`data_boundary`（`reads_step=false` 等）和 `notes`。`notes` 明确写明：分数不是几何等价证据，split 不是 benchmark。

## 6. 错误协议

| code | stage | 触发 |
|---|---|---|
| `RETRIEVAL_CONFIG_NOT_FOUND` / `RETRIEVAL_CONFIG_INVALID` | config | 配置文件缺失、版本/policy/族/ranges/weights 不符，或连续字段范围不等于完整目录范围 |
| `RETRIEVAL_MANIFEST_NOT_FOUND` / `RETRIEVAL_MANIFEST_PARSE_ERROR` / `RETRIEVAL_MANIFEST_EMPTY` | index | manifest 不可读、非法 JSON/空行、空文件 |
| `RETRIEVAL_MANIFEST_HASH_MISMATCH` | config/index | manifest 与配置或显式期望 hash 不一致 |
| `RETRIEVAL_INVALID_RECORD` | index | 记录缺字段、单位不是 mm、参数非有限、split_status 不是 provisional_small_n 等 |
| `RETRIEVAL_DUPLICATE_SAMPLE_ID` / `RETRIEVAL_DUPLICATE_GROUP_ID` | index | 重复候选 |
| `RETRIEVAL_FAMILY_MISMATCH` | index | manifest 含多个族 |
| `RETRIEVAL_CANDIDATE_ROLES_REQUIRED` / `RETRIEVAL_EMPTY_CANDIDATE_ROLES` / `RETRIEVAL_INVALID_CANDIDATE_ROLES` / `RETRIEVAL_UNKNOWN_ROLE` | config/index | 候选角色未显式给出、为空、类型错误或不在 manifest 中 |
| `RETRIEVAL_NO_CANDIDATES` | index | 选定角色没有记录 |
| `RETRIEVAL_UNKNOWN_FAMILY` | query | 查询族不是索引族 |
| `RETRIEVAL_UNKNOWN_FIELD` / `RETRIEVAL_MISSING_FIELD` | query | flat 查询含未知字段或缺少六个字段 |
| `RETRIEVAL_INVALID_PARAMETER` | query | 非有限数、布尔、类型错误、`second_screw` 非 0/1 |
| `RETRIEVAL_SCHEMA_REJECTED` | query | envelope 未通过现有 Schema |
| `RETRIEVAL_INVALID_TOP_K` / `RETRIEVAL_TOP_K_OUT_OF_RANGE` | query | top_k 非整数、<1 或大于候选数 |

## 7. 运行结果（2026-11-03，固定环境）

### 7.1 目录内查询（`bore_d=20`）

输入是 CAD-003 envelope（仅 `bore_d=20`），Schema 派生其余五个字段。`query_status=catalog_validated`。

| rank | sample_id | role | total | continuous | discrete | same catalog row |
|---:|---|---|---:|---:|---:|---|
| 1 | `.../catalog-bore-020` | retrieval_source | 0.000000 | 0.000000 | 0.0 | 是 |
| 2 | `.../catalog-bore-006` | retrieval_source | 0.234278 | 0.234278 | 0.0 | 否 |
| 3 | `.../catalog-bore-050` | retrieval_source | 0.414889 | 0.414889 | 0.0 | 否 |

字段级归一化绝对差（rank 1 / 2 / 3）：`bore_d` 0 / 0.186667 / 0.4；`outer_d` 0 / 0.2 / 0.48；`screw_d` 0 / 0.222222 / 0.444444；`screw_len` 0 / 0.1875 / 0.5；`width` 0 / 0.375 / 0.25。

### 7.2 目录行之间查询（`bore_d=18`，尚未被 Schema 确认为合法真值）

输入是 flat 六字段 `(18, 30, 6, 8, 0, 14)`。Schema 返回 `CATALOG_CHOICE`；检索继续，`query_status=out_of_catalog_or_unvalidated`，所有候选 `same_catalog_row_as_query=false`。

| rank | sample_id | role | total | continuous | discrete | same catalog row |
|---:|---|---|---:|---:|---:|---|
| 1 | `.../catalog-bore-020` | retrieval_source | 0.009333 | 0.009333 | 0.0 | 否 |
| 2 | `.../catalog-bore-006` | retrieval_source | 0.224944 | 0.224944 | 0.0 | 否 |
| 3 | `.../catalog-bore-050` | retrieval_source | 0.424222 | 0.424222 | 0.0 | 否 |

字段级归一化绝对差（rank 1 / 2 / 3）：`bore_d` 0.026667 / 0.16 / 0.426667；`outer_d` 0.02 / 0.18 / 0.5；`screw_d` 0 / 0.222222 / 0.444444；`screw_len` 0 / 0.1875 / 0.5；`width` 0 / 0.375 / 0.25。

### 7.3 `second_screw=1` 的 `bore_d=80` 边界查询

输入 flat 目录行 `(80, 110, 12, 20, 1, 22)`，`query_status=catalog_validated`。`bore_d=80` 是 `heldout_evaluation`，**没有**进入候选；3 个候选全部 `retrieval_source`，且都因 `second_screw` 不同获得 0.5 的离散项。

| rank | sample_id | role | total | continuous | discrete | same catalog row |
|---:|---|---|---:|---:|---:|---|
| 1 | `.../catalog-bore-050` | retrieval_source | 0.784444 | 0.284444 | 0.5 | 否 |
| 2 | `.../catalog-bore-020` | retrieval_source | 1.199333 | 0.699333 | 0.5 | 否 |
| 3 | `.../catalog-bore-006` | retrieval_source | 1.433611 | 0.933611 | 0.5 | 否 |

字段级归一化绝对差（rank 1 / 2 / 3）：`bore_d` 0.4 / 0.8 / 0.986667；`outer_d` 0.3 / 0.78 / 0.98；`screw_d` 0.222222 / 0.666667 / 0.888889；`screw_len` 0.25 / 0.75 / 0.9375；`width` 0.25 / 0.5 / 0.875。

### 7.4 失败与稳定性案例

smoke 共 3 个正常/边界案例、13 个失败案例、70 项检查，全部通过：

| 案例 | 期望 code | 实际 | 通过 |
|---|---|---|---|
| 缺失 `outer_d` | `RETRIEVAL_MISSING_FIELD` | 同，fields=`[outer_d]` | 是 |
| 未知字段 `flange_d` | `RETRIEVAL_UNKNOWN_FIELD` | 同 | 是 |
| 未知族 | `RETRIEVAL_UNKNOWN_FAMILY` | 同 | 是 |
| 非有限 `bore_d=NaN` | `RETRIEVAL_INVALID_PARAMETER` | 同 | 是 |
| `second_screw=2` | `RETRIEVAL_INVALID_PARAMETER` | 同 | 是 |
| `top_k=0` / `top_k=True` | `RETRIEVAL_INVALID_TOP_K` | 同 | 是 |
| `top_k=4`（候选 3） | `RETRIEVAL_TOP_K_OUT_OF_RANGE` | 同 | 是 |
| envelope `bore_d=18` | `RETRIEVAL_SCHEMA_REJECTED` | 同（CATALOG_CHOICE） | 是 |
| 空候选角色 | `RETRIEVAL_EMPTY_CANDIDATE_ROLES` | 同 | 是 |
| 未传候选角色 | `RETRIEVAL_CANDIDATE_ROLES_REQUIRED` | 同 | 是 |
| 未知角色 | `RETRIEVAL_UNKNOWN_ROLE` | 同 | 是 |
| 重复候选行 | `RETRIEVAL_DUPLICATE_SAMPLE_ID` | 同 | 是 |

策略范围回归（单元测试）：额外 6 项测试覆盖伪造 `bore_d` 或其他连续字段范围、NaN/Inf/bool/字符串/近似值、`from_manifest(..., policy=...)` 入口、冻结范围的正常构建与结果一致性，以及构造后修改调用方 dict/list 的别名攻击。自定义范围均得到 `RETRIEVAL_CONFIG_INVALID`（stage=`config`，fields 含对应字段）；冻结范围仍得到原排序、原距离和原 canonical SHA。

确定性：

- 同一查询在进程内重复两次，canonical JSON 逐字一致；
- 两个独立进程经 `replay_query.py` 运行同一查询，stdout 逐字一致，canonical JSON SHA-256 均为 `0fcf84b752db919d7eb65ba6b4df88080d2e800ec22021bef4e5e52dc172e3b9`；
- 相同输入在同一固定环境得到相同 JSON；跨平台不承诺。

## 8. 复现命令

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"

# 30 项单元测试（原 24 + 策略范围契约回归 6）
PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval -v

# smoke：3 个正常/边界 + 13 个失败 + 跨进程确定性
PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py

# 单个案例复放（输出 canonical JSON hash）
PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/replay_query.py \
  --config agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json \
  --case agent-work/integration/RET-002-retrieval-baseline/examples/query-in-catalog.json

# RET-001 数据完整性（续任复核）
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python \
  agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py --tracked-only
```

`smoke-report.json` 的 `generated_at` 与 `environment` 会随运行变化；案例排序、距离和 canonical SHA 在固定环境保持一致。

## 9. 已知限制

1. **数据稀疏**：真实样本只有 15 个目录行，候选只有 3 个 `retrieval_source` 行；最远和最近候选的区分度有限，`top_k` 最大就是 3。这暴露的是数据边界，不是检索质量结论。
2. **split 是临时的**：9/3/3 的 `provisional_small_n` 不是 benchmark 切分。本任务不评估检索收益，也不输出准确率、召回率或泛化结论。
3. **分数语义有限**：距离只是参数近邻度，不是几何等价、制造可行性、强度安全或生成质量。
4. **flat 形式要求完整六字段**：不会从 `bore_d` 推导；需要派生时使用 envelope。目录行之间的查询只能用 flat 形式，并会被标记为未验证。
5. **同目录行判定只是参数相等**：`same_catalog_row_as_query` 不检查几何或验证结果。
6. **单环境**：只在 Python 3.11.18 / macOS 26.6.2 arm64 上验证；跨平台、跨解释器和不同浮点环境未验证。
7. **候选角色固定**：配置只选 `retrieval_source`；若要改用 development 或显式 held-out，必须显式改配置并重新审查，不能隐式混入。
8. **配置绑定 manifest hash**：manifest 一旦重新生成，`retrieval-config.json` 必须由负责人显式更新 hash；否则加载失败（fail closed）。
9. **不读取 STEP/IR 文件**：`ir.sha256` 和验证摘要直接取自 manifest；本任务不独立重算 IR、STEP 或几何。
10. **许可与上游状态**：`reproducibility_partial`、`MERGED`（非 release-qualified）和 `license_scope_uncertain` 继续有效；未下载 BenchCAD Public/Core，未增加第二族。
11. **权重未经 RET-003 验证**：0.2 / 0.5 是预先固定的透明规则，不代表统计最优；RET-003 才能评估是否有检索收益。
12. **未涉及生成**：不包含 Prompt 注入、LLM、字段修复或 CAD 生成，APP-001/RET-004 未实现。
13. **策略描述字符串未单独校验**：`weights.total_formula` / `tiebreak` 是说明字段，加载器未逐字校验；当前数值范围与权重已冻结，描述字符串的版本化校验留待新 policy 版本补充。

## 10. 下一步建议

1. Codex 中枢重新复核策略范围不可绕过、接口、排序稳定性、失败路径、数据边界和限制；确认后再放行 RET-003。
2. RET-003 决定正式切分或明确不切分；在此之前不得把 9/3/3 当 benchmark。
3. RET-003 设计无检索 / 检索 / 人工模板三条件对照；检索候选只能作为参数与来源参考，不能当目录真值或几何真值。
4. APP-001/RET-004 注入 Prompt 时，应携带 `query_status`、`sample_id`、`ir.path`、`source_commit`、`split.role` 和限制，并禁止把候选直接当作答案。
5. 若后续需要更多候选，先由中枢决定新增族或新 Schema 版本；不要复制、随机扩写或下载 Public/Core 来填量。
