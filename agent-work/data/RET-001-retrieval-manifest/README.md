# RET-001 检索样本 manifest v0

状态：`review`（等待 Codex 中枢独立审查；未标记 done，未 push）
任务：RET-001 单族检索样本 manifest 与样本构建
族：`set_screw_shaft_collar`（ADR-0007 冻结，首期唯一族）

本目录是首期单族的检索样本 manifest v0。它只构建**数据与样本记录**，不实现检索排序、向量库、LLM Prompt 或 RET-002/RET-003 评测算法。

## 1. 范围与事实

| 项 | 值 |
|---|---|
| repository | `https://github.com/BenchCAD-org/benchcad-2` |
| source_commit | `035f467142888edfd0bd7cd73906f9b155c8f43c` |
| family_path | `designs/set_screw_shaft_collar` |
| family_status | `MERGED`（非 release-qualified） |
| snapshot_status | `reproducibility_partial` |
| 目录行 | 15 个合法 `bore_d`：5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80 mm |
| IR | `typed-cad-ir.v0`，revision `0.2.0` |
| 几何策略 | `CAD-006.geometry-comparison.v1` |
| Schema | `set_screw_shaft_collar.v0` |
| 环境 | Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 / NumPy 1.26.4 / macOS arm64 |

**样本数只有 15 个，这是事实而不是抽样结果。** 该族在固定 commit 的 `spec.py` 中只有这 15 个 GN 705 目录行，且项目 Schema 只接受目录耦合的取值；随机生成 50–100 个"合法样本"会违反源数据契约。扩展方案见第 8 节。

## 2. 文件

| 文件 | 作用 |
|---|---|
| `manifest-v0.jsonl` | 15 条样本记录，一行一条，按目录行序号排序 |
| `manifest.schema.json` | 记录的 Draft 2020-12 JSON Schema |
| `generation-report.json` | 生成摘要：环境、来源、split 表、逐样本结果、失败对照、泄漏检查、hash |
| `verification-report.json` | `verify_manifest.py` 的独立校验结果（JSONL/JSON Schema/provenance/hash/IR 复核/split 隔离） |
| `replay-report.json` | `replay_check.py` 的新进程复跑结果：2 个正常样本 + 2 个失败对照，各跑 2 次 |
| `inputs/` | 15 个最小 CAD-003 envelope，只有 `bore_d`（派生字段由族规则补全） |
| `ir/` | 15 个 accepted IR（IR v0.2.0 固定七节点图，仅参数值/provenance 不同） |
| `generator/` | 可复用生成器、独立校验器、复跑脚本 |
| `checkpoint.md` / `handoff.md` | 交接自检与续任复核说明 |

## 3. 每条记录回答什么

```text
来源      source.repository / source_commit / family_path / family_status /
          release_qualified / snapshot_status / license_scope / catalog_row(index,row)
参数      parameters.normalized（六字段）/ units / provenance（每字段 source + source_ref）
          / catalog_key / input_payload(path + sha256)
IR        ir.ir_version / ir_revision / status / schema_path + schema_sha256 / path + sha256
产物      artifacts.step(path, sha256, bytes, ignored_local_artifact, license_scope_uncertain)
          / artifacts.render = null / artifacts.validation_result(path + sha256)
验证      validation.schema / family_rules / cad_compile / completed_stages / final_stage
          / native_geometry / native_repeatability / step_readback / policy_id
切分      split.role / group_id / split_rule / split_status
生成      generation.*（generator、template hash、无 seed、Python/CadQuery/OCP/NumPy、平台、时间）
边界      limitations
```

字段语义中有三处需要显式说明：

1. **`validation.native_geometry` 不内联完整数组**：面面积和边长数组保存在被忽略的 `artifacts.validation_result` 工件里，manifest 记录数组长度与 `sha256`，`verify_manifest.py` 会重算比对。体积、bbox、拓扑计数、`is_valid` 直接内联。
2. **`step_readback` 只记录 CAD-006 结构化比较**：bbox 绝对差、体积/面面积/边长的 abs+rel、硬拓扑不匹配列表和回读几何摘要。**STEP SHA-256 只作产物标识**，不参与几何判定。
3. **`execution.tolerance_profile`**：生成的 IR 写 `CAD-006.geometry-comparison.v1`（IR 规范 §9.2 / ADR-0008 现行策略）。冻结示例 `legal-catalog-row.json` 里仍是历史值 `CAD-006.pending.v0`；该示例在冻结目录内，本任务未修改，已在 checkpoint 记录为待中枢决定的文档不一致。

## 4. 生成流水线

```text
inputs/catalog-bore-0XX.json          （只含 bore_d 的最小 envelope）
        ↓ schema.set_screw_shaft_collar.validate_parameters
normalized + provenance             （目录行派生 + second_screw 规则派生）
        ↓ 适配（复制冻结七节点模板，仅替换 parameters）
ir/catalog-bore-0XX.json            （accepted，IR v0.2.0）
        ↓ ir-v0.schema.json（Draft 2020-12）+ IR 语义校验
        ↓ cad_compilation.compile_ir()
native 构造 → 同进程重复比较 → CAD-006 几何门槛 → STEP 导出 → STEP 回读比较
        ↓
work/ret-001-output/cad/.../*.step （被 .gitignore 排除）
work/ret-001-output/validation/...  （被 .gitignore 排除）
        ↓
manifest-v0.jsonl 的一条记录
```

生成器不修改 `src/schema/**`、`src/cad_compilation/**`、IR 规范或示例，只读复用。

## 5. 复现命令

在仓库根目录执行（固定环境）：

```bash
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python agent-work/data/RET-001-retrieval-manifest/generator/generate_manifest.py

PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py

PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python agent-work/data/RET-001-retrieval-manifest/generator/replay_check.py
```

`verify_manifest.py --tracked-only` 可跳过被忽略的 STEP/validation 工件，用于只检查已提交内容的干净检出。

重新生成时的可复现边界：参数、IR 内容与几何摘要应逐值不变；**会变化的只有** `generated_at`、被忽略 validation 工件内的耗时字段（其 hash 进而进入记录）以及 STEP 字节。`replay_check.py` 已在独立进程验证前两项稳定，STEP 字节按策略允许不同。

## 6. Split 与泄漏控制

- 最小分组键：`family_id + catalog row`，即 `group_id = catalog-row-bore-0XX`；15 条记录 = 15 组，一组只属于一个 role。
- 分配规则（确定性，按 `bore_d` 升序序号 i）：`i % 5 == 1` → `retrieval_source`；`i % 5 == 4` → `heldout_evaluation`；其余 → `development`。
- 结果：development 9 / retrieval_source 3 / heldout_evaluation 3。
- `split_status = provisional_small_n`。**这不是冻结的评测切分**，只是可复算的临时分组建议；正式切分必须由 RET-003 + Codex 审查后另行冻结。

| bore_d | role | 说明 |
|---:|---|---|
| 5, 8, 10, 16, 24, 30, 40, 60, 70 | development | 9 行 |
| 6, 20, 50 | retrieval_source | 3 行，含中位行 20 |
| 12, 35, 80 | heldout_evaluation | 3 行，含 `second_screw=1` 的硬边界 80 |

泄漏检查（`generation-report.json → leakage_checks`，`verify_manifest.py` 复核）：

- 同一目录行不会出现在两个 split；跨 split 组重叠 = 0；
- 15 个参数 JSON 两两不同；
- 15 个几何指纹（6 位量化体积 + bbox + 拓扑计数）两两不同，最小成对体积相对差 ≈ 0.093（9.3%），不存在近重复几何；
- 未使用随机重复实例充当独立数据，`generation.seed = null`。

## 7. 结果

15/15 通过：Schema、族规则、accepted IR（JSON Schema + 语义）、`compile_ir`、同进程重复比较、STEP 回读比较。每例均为单 solid、单 shell、`isValid=true`。

| # | bore_d | 目录行 (bore, outer, screw_d, screw_len, width) | role | 体积 mm³ | 面/边 | 回读 |
|---:|---:|---|---|---:|---|---|
| 0 | 5 | (5, 10, 3, 4, 6) | development | 335.684 | 27/57 | pass |
| 1 | 6 | (6, 12, 4, 5, 8) | retrieval_source | 642.752 | 27/57 | pass |
| 2 | 8 | (8, 16, 4, 6, 8) | development | 1160.152 | 31/65 | pass |
| 3 | 10 | (10, 20, 5, 8, 10) | development | 2268.991 | 31/65 | pass |
| 4 | 12 | (12, 22, 6, 8, 12) | heldout_evaluation | 3081.009 | 27/57 | pass |
| 5 | 16 | (16, 28, 6, 8, 12) | development | 4828.618 | 31/65 | pass |
| 6 | 20 | (20, 32, 6, 8, 14) | retrieval_source | 6712.632 | 29/59 | pass |
| 7 | 24 | (24, 40, 8, 12, 16) | development | 12513.345 | 35/73 | pass |
| 8 | 30 | (30, 45, 8, 10, 16) | development | 13795.502 | 31/65 | pass |
| 9 | 35 | (35, 56, 8, 12, 16) | heldout_evaluation | 23523.950 | 41/83 | pass |
| 10 | 40 | (40, 63, 10, 16, 18) | development | 32660.578 | 39/81 | pass |
| 11 | 50 | (50, 80, 10, 16, 18) | retrieval_source | 54010.088 | 47/97 | pass |
| 12 | 60 | (60, 90, 10, 16, 20) | development | 69465.078 | 45/91 | pass |
| 13 | 70 | (70, 100, 10, 20, 20) | development | 78758.192 | 45/91 | pass |
| 14 | 80 | (80, 110, 12, 20, 22) | heldout_evaluation | 95092.285 | 74/149 | pass |

STEP 回读相对 CAD-006 阈值的最坏观测：体积 abs 0.03408 mm³（阈 0.0682）/ rel 1.97e-6（阈 3.941e-6）；bbox abs 3.55e-15 mm（阈 1e-5）；面面积 abs 0.003968 mm²（阈 0.00794）；边长 abs 2.80e-7 mm（阈 1e-5）。全部在冻结阈值内，且与 ADR-0008 的原生测量最大值一致（均未触发放宽）。

失败对照（`generation-report.json → negative_controls`，`replay-report.json` 复跑 2 次，逐次一致）：

- 篡改 accepted IR 的 `n2.hole.primary.inputs.radial_offset` 为 `literal 100 mm` → `IR_NODE_INPUT_KIND_MISMATCH`（stage `semantic`，`node_ids = ["n2.hole.primary"]`），未产生 STEP；
- `bore_d=20` 显式给 `outer_d=33` → `CATALOG_MISMATCH`（stage `schema`）。

首期 15 个合法目录行没有失败样本；失败路径以上述两个负对照记录，错误码、阶段、字段和 node_ids 均可审计。

## 8. 为什么不是 50–100 个样本，以及后续扩展方案

`database/benchcad-dataset-first-plan-2026-10.md` 的 50–100/族是跨族扩展预算。对当前首族：

- 源数据只有 15 个 GN 705 目录行，且 `bore_d` 是离散选择；
- 项目 Schema 明确拒绝目录耦合之外的取值（`CATALOG_MISMATCH`）和越界值；
- 因此把 15 行扩写成"50–100 个真实样本"会是伪造合法真值。

若后续需要更大样本量，需要中枢先决策下列任一路径（本任务未执行，也未自行改架构）：

1. 新增冻结族（每族独立来源/许可/参数审计 + ADR），按同一 manifest 契约扩展；
2. 引入新的参数 Schema 版本，明确放开哪些非目录耦合字段及来源，再重测几何与检索切分；
3. 仅在评测侧使用参数邻域扰动，但必须标为合成并单独切分，不得与目录行真值混为一谈。

## 9. 许可证与产物边界

- BenchCAD 仓库代码与 `designs/*` 按固定 commit 的 README/LICENSE 为 MIT；本项目未复制族源码进交付物。
- 项目自行导出的 STEP、渲染图**不自动**适用 MIT 或数据集 CC BY 4.0，保持 `license_scope_uncertain`，只存放于被 `.gitignore` 排除的 `work/ret-001-output/`，不提交、不再发布。
- 未下载或使用 BenchCAD Public/Core 数据制品；本 manifest 不含训练/检索语料化的 Public/Core 内容。
- `NOTES.md` 提到的第三方图纸/SVG/照片未复制、未下载。

## 10. 已知限制与待审查问题

已经在 manifest 的 `limitations` 中逐条记录，此外需中枢判断：

1. **split 是否可用**：15 组 9/3/3 只能作为临时分组，`provisional_small_n`；是否冻结、是否改为不切分（全部 development）由 RET-003 + 中枢决定。
2. **IR 示例的 `tolerance_profile`**：冻结示例仍写 `CAD-006.pending.v0`（历史候选，已被 §9.2 取代）；本任务生成 IR 写 `CAD-006.geometry-comparison.v1`，未修改示例文件。是否需要同步示例由中枢决定（属 IR-001 文件边界）。
3. **manifest 字段集**：v0 未包含渲染工件（首期非必需）、自然语言任务和检索标签；RET-002/003 若需要新字段，应新建 `retrieval-manifest.v1` 而不是静默扩展。
4. **文档状态**：`docs/TASKS.md` 中 RET-001 仍为 `planned`，超出本任务允许修改范围，需由中枢同步为 `review`。
5. **环境边界**：仅验证固定 macOS arm64 单环境；跨平台、跨进程、其他 CadQuery/OCP/STEP writer 未验证。
6. **几何语义**：螺纹为 `revolved_ring_approximation`，不支持真实螺旋螺纹；STEP 通过不代表制造或功能正确。

## 11. 本 manifest 不声称什么

- 不声称 15 个样本是正式 benchmark 切分；
- 不声称族已 release-qualified，或生成物可公开发布；
- 不把 manifest JSON Schema 通过、STEP 导出成功或 STEP hash 相等当作几何正确性证明；
- 不声称跨族泛化或开放域 CAD 能力。
