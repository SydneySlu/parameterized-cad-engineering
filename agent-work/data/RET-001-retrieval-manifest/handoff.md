# RET-001 handoff — 检索样本 manifest v0

状态：`review`（交接 Agent 自检完成；等待续任 Agent 定向复核与 Codex 中枢独立审查）
交接方：RET-001 数据与检索样本 Agent（DSH）
交付提交：`71125d2`（manifest/schema/报告/生成器/交接文档；WORKLOG 记录见下一提交）
交付目录：`agent-work/data/RET-001-retrieval-manifest/`
固定环境：Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 / NumPy 1.26.4 / macOS arm64

## 1. 修改了什么

新增（均在允许范围内）：

```text
agent-work/data/RET-001-retrieval-manifest/
├── README.md                     manifest 契约、字段语义、split、许可边界、限制
├── manifest.schema.json          Draft 2020-12 记录 Schema
├── manifest-v0.jsonl            15 条样本记录（一行一条，按目录行排序）
├── generation-report.json       生成报告（环境、逐样本结果、负对照、泄漏检查）
├── verification-report.json     verify_manifest.py 的校验结论
├── replay-report.json           replay_check.py 的新进程复跑结论
├── inputs/                      15 个最小 CAD-003 envelope（只有 bore_d）
├── ir/                          15 个 accepted IR（typed-cad-ir.v0 / 0.2.0）
├── generator/generate_manifest.py
├── generator/verify_manifest.py
├── generator/replay_check.py
├── checkpoint.md
└── handoff.md（本文件）
```

只追加：`docs/WORKLOG.md`。
未修改：`src/**`、`agent-work/typed-cad-ir/**`、`agent-work/cad-validation/**`、`docs/DECISIONS.md`、
`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`、`database/**`。

## 2. 文件格式与入口

- `manifest-v0.jsonl`：15 行，每行一个 JSON 对象，末行含换行，无空行；字段契约见
  `manifest.schema.json`（`additionalProperties: false`）。
- `ir/*.json`：`typed-cad-ir.v0` revision `0.2.0`、`status=accepted`，固定七节点图；
  与冻结示例的差异只有 `parameters` 数值/provenance、`source_ref` 中的 `bore_d`，以及
  `execution.tolerance_profile`。
- `inputs/*.json`：正式 CAD-003 envelope，只含 `bore_d`。
- `generation-report.json`：机器可读主报告；`leakage_checks`、`negative_controls`、`split_plan`
  是审查重点。
- STEP 与完整 validation 工件在 ignored `work/ret-001-output/`，manifest 记录路径 + sha256 + bytes。

## 3. 核心命令与预期结果（续任者必须至少重跑一条）

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"

# A. 数据完整性（不需要 CAD 运行时影响；需要固定 venv 的 jsonschema）
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py
# 预期：records=15 lines=15 checks_passed=825 failures=0 / RESULT: PASS

# B. 新进程几何复跑（约 4 秒）
... generator/replay_check.py
# 预期：catalog-bore-020 与 catalog-bore-080 pass=True（native_match=True, readback=True）；
#       tampered_radial_offset / catalog_mismatch pass=True 且两次一致 / RESULT: PASS

# C. 干净检出可用的静态检查（跳过 ignored 工件）
... generator/verify_manifest.py --tracked-only

# D. 全量重建（会重写 manifest、忽略工件与 STEP；约 30 秒）
... generator/generate_manifest.py
# 预期：records=15；schema/IR/compile/repeat/roundtrip 15/15 pass；failed=0
```

## 4. 必查的正常/失败案例

| 类型 | 位置 | 预期 |
|---|---|---|
| 正常（中位开发/检索行） | `manifest-v0.jsonl` 的 `set_screw_shaft_collar/catalog-bore-020` | 单 solid/单 shell/valid；体积 6712.632 mm³；roundtrip pass |
| 正常（硬边界 + heldout） | `catalog-bore-080` | `second_screw=1`，两个紧定螺钉孔；74 面/149 边；体积 95092.285 mm³ |
| 失败 1（IR 绑定） | `replay-report.json → negative_controls.tampered_radial_offset` | semantic 阶段 `IR_NODE_INPUT_KIND_MISMATCH`，`node_ids=["n2.hole.primary"]`，无 STEP |
| 失败 2（族规则） | `replay-report.json → negative_controls.catalog_mismatch` | schema 阶段 `CATALOG_MISMATCH`（`outer_d=33` vs 目录 32） |

正常 split 与边界/小样本 split：

- 正常切分：`development`（9 行）与 `retrieval_source`（3 行：6/20/50）；
- 边界或小样本切分：`heldout_evaluation` 只有 3 行（12/35/80），且包含唯一 `second_screw=1`
  的 80 行；因此 `split_status=provisional_small_n`，不得当作正式评测集。

## 5. 接口确认

- 输入：CAD-003 参数 envelope → `src/schema/set_screw_shaft_collar.py::validate_parameters`。
- 中间：`typed-cad-ir.v0 / 0.2.0` accepted IR，JSON Schema `ir-v0.schema.json` + 语义校验。
- 输出：现有 `src/cad_compilation/compiler.py::compile_ir()` 的 `CompilationResult`，
  含 `native_geometry`、`native_repeatability`、`step_readback`、`step`。
- 未新增/修改任何生产接口；生成器是只读消费者。

## 6. 已确认 / 未解决

已确认：

- 15/15 目录行全链路通过；几何与 CAD-006 阈值余量充足（最坏体积 abs 0.03408 < 0.0682）；
- manifest 通过自身 JSON Schema、逐行解析、全部 hash 复核（含 IR schema hash、IR/STEP/工件/payload）；
- 15 个参数 JSON 与 15 个几何指纹互不相同，跨 split 组重叠 0；
- 两次独立进程复跑的正常样本几何摘要逐值一致；STEP 字节不一致按策略不构成失败。

未解决（须中枢判断，不要在未授权时自行"修好"）：

1. split 是否冻结（当前仅 provisional_small_n，9/3/3）；
2. 冻结 IR 示例仍写 `tolerance_profile=CAD-006.pending.v0`，生成 IR 写 `CAD-006.geometry-comparison.v1`；
   是否更新示例属 IR-001 边界；
3. `docs/TASKS.md` / `docs/PROJECT_STATUS.md` 未同步为 `review`（超出文件边界）；
4. 单环境验证；跨平台/跨进程未验证；
5. 生成 STEP 的许可证仍为 `license_scope_uncertain`。

## 7. 大文件与未提交内容

- `work/ret-001-output/`（≈4.0 MB）：STEP（2.39 MB）、validation 工件、replay 输出、`precheck.py`、
  `controls/`。全部被 `.gitignore` 排除，未提交、未外发。
- 已提交内容不含 STEP、渲染图、网格或第三方图纸。

## 8. 续任 Agent 复核记录模板

```text
handoff_successor_check:
  predecessor=RET-001 checkpoint/handoff（交付提交见 WORKLOG）
  files_format=<manifest-v0.jsonl 15 行、schema、generator、README 是否存在且可解析>
  core_rerun=<verify_manifest.py 或 replay_check.py 的实际命令与结果>
  normal_case=<catalog-bore-020 或 catalog-bore-080 的结果>
  failure_case=<tampered_radial_offset 或 catalog_mismatch 的结果>
  interface=<输入 envelope / IR 0.2.0 / compile_ir 输出是否一致>
  limits=<provisional_small_n、单环境、reproducibility_partial、license_scope_uncertain 是否保留>
  result=pass | review | blocked
  blocking_issue=<若 review/blocked 写明>
```

发现交接记录与实际结果不一致时，先写 `review`/`blocked`，不要覆盖已有成果。

## 9. 中枢审查建议顺序

1. 读 `README.md` 第 3/6/8/10 节与 `generation-report.json` 的 `leakage_checks`、`negative_controls`；
2. 重跑 `verify_manifest.py` 与 `replay_check.py`；
3. 抽查 `catalog-bore-020` 与 `catalog-bore-080` 的 IR 与 manifest 记录是否自洽；
4. 判断 split 与 `tolerance_profile` 两项未决问题；
5. 决定 RET-001 是否转 `done` 并 push（本任务不自行标 done、不 push）。
