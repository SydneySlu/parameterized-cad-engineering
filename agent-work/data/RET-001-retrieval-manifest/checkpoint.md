# RET-001 checkpoint — 检索样本 manifest v0

状态：`review`
任务：RET-001（单族检索样本 manifest 与样本构建）
目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
基线 HEAD：`26e860d`（启动时干净，`main` 与 `origin/main` 同步）
交付提交：`71125d2`（`feat: add retrieval manifest v0 [RET-001]`；含 manifest、schema、报告、生成器与交接文档）
未 push：按项目约定由负责人确认中枢审查后 push。

## handoff_self_check

```text
task=RET-001
status=review
changed=agent-work/data/RET-001-retrieval-manifest/**（新增：README、manifest.schema.json、
        manifest-v0.jsonl、generation-report.json、verification-report.json、replay-report.json、
        inputs/×15、ir/×15、generator/×3、checkpoint.md、handoff.md）；docs/WORKLOG.md（只追加）；
        ignored：work/ret-001-output/**（STEP/验证工件/复跑产物）
commands=<见下方"执行记录"，全部实际运行>
confirmed=15/15 目录行通过 Schema、族规则、IR Schema+语义、compile_ir、native 重复、STEP 回读；
          manifest JSONL 15 行 + JSON Schema + hash 校验通过（825 项检查，0 失败）；
          正常样本×2 与失败对照×2 在独立进程复跑一致
unresolved=split 仅为 provisional_small_n；IR 示例的 tolerance_profile 仍为历史值；
          docs/TASKS.md 状态未同步（超出文件边界）；仅单环境验证
next_agent_focus=见 handoff.md "续任复核清单"
```

## 1. 定向复核（生成样本前，强制）

启动检查：`git rev-parse --show-toplevel` 正确；`git status --short --branch` 干净；HEAD `26e860d`。
阅读了 AGENTS、PROJECT_STATUS、PROJECT_PLAN、WORKLOG、DECISIONS、TASKS、handoff-review-protocol、
database 两文、DATA-003 三件、IR 规范/映射/Schema、Schema 模块、compiler/ir 实现、CAD-005/006
checkpoint 与中枢审查记录。

随后用临时脚本 `work/ret-001-output/precheck.py`（ignored）复核冻结接口：

| 案例 | 命令要点 | 结果 |
|---|---|---|
| 正常：`examples/legal-catalog-row.json` | `compile_ir(...)` | `ok=True`、`status=step_readback`、单 solid/单 shell、`is_valid=True`、体积 6712.631936 mm³、bbox 32.0000002×32.0000002×14.0 mm、native 重复 pass、roundtrip pass（体积 abs 0.01323） |
| 失败 1：accepted IR 篡改 `n2.hole.primary.inputs.radial_offset` 为 `literal 100 mm` | `validate_ir` + `compile_ir` | semantic 阶段拒绝：`IR_NODE_INPUT_KIND_MISMATCH`，`fields=[nodes.n2.hole.primary.inputs.radial_offset]`，`node_ids=[n2.hole.primary]` |
| 失败 2：`examples/rule-rejected-second-screw.json` | `compile_ir` | preflight 拒绝：`SECOND_SCREW_CONSTRAINT` |

接口确认：输入是首族参数 JSON（CAD-003 envelope），中间是 `typed-cad-ir.v0 / 0.2.0` accepted IR，
输出是现有 `compile_ir()` 的 `CompilationResult`（含 native 几何、STEP 回读比较和运行 manifest）。
与 CAD-005/006 交接记录一致，未发现阻塞性不一致，因此继续生成样本。

## 2. 新增可复用生成器的理由与路径

任务允许范围只有 `agent-work/data/RET-001-retrieval-manifest/**` 与 `docs/WORKLOG.md`，且要求
manifest 可审计、可重放。因此生成器放在任务目录内，不修改 `src/` 或冻结 IR：

- `generator/generate_manifest.py`：Schema → IR → `compile_ir` → manifest 记录 + 生成报告；
- `generator/verify_manifest.py`：独立静态校验（JSONL/JSON Schema/hash/IR 复核/split 隔离）；
- `generator/replay_check.py`：新进程复跑正常样本与失败对照。

生成器只读复用 `src/schema/set_screw_shaft_collar.py`、`src/cad_compilation/**` 和冻结示例
`agent-work/typed-cad-ir/IR-001-v0/examples/legal-catalog-row.json`（模板 sha256
`4c0d25067206e6a47b9aad4663a288e7f2c8b1141f89569249afe83939f9632b`）。

## 3. 设计决策（需中枢确认）

1. **只生成 15 个样本**：族内只有 15 个冻结目录行，Schema 拒绝目录耦合之外的取值；不扩写、不随机造数。
2. **最小输入**：每条 `inputs/` 只给 `bore_d`，其余字段由族规则派生，从而真实检验 provenance
   （`catalog_derived` / `rule_derived`）。
3. **IR 构造**：复制冻结七节点模板，只替换 `parameters`；节点、约束、`family_data`、
   `validation_contract` 保持逐字一致，未修改 IR 语义。
4. **`execution.tolerance_profile`**：生成 IR 写 `CAD-006.geometry-comparison.v1`（IR 规范 §9.2 /
   ADR-0008 现行策略）。冻结示例文件仍写历史值 `CAD-006.pending.v0`，本任务未修改该文件（属 IR-001
   边界），已列为待中枢决定项。Schema 该字段为自由字符串，结构校验不受影响。
5. **split**：`group_id = catalog-row-bore-0XX`，按 `bore_d` 升序 `i%5` 规则分配
   9/3/3（development/retrieval_source/heldout_evaluation），`split_status=provisional_small_n`，
   `generation.seed=null`。不声称是冻结评测切分。
6. **STEP/渲染**：STEP 写入 ignored `work/ret-001-output/cad/`，不提交；`artifacts.render=null`（首期非必需）。

## 4. 执行记录（实际运行）

固定环境：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4、macOS arm64
（`work/benchcad-output/venv/bin/python`）。

```bash
# 生成 15 条样本
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python agent-work/data/RET-001-retrieval-manifest/generator/generate_manifest.py
# -> records=15；schema/IR/compile/repeat/roundtrip 15/15 pass；failed=0

# 独立校验
... generator/verify_manifest.py
# -> records=15 lines=15 checks_passed=825 failures=0；RESULT: PASS

# 新进程复跑
... generator/replay_check.py
# -> catalog-bore-020 pass=True（native_match=True, readback=True）
#    catalog-bore-080 pass=True（native_match=True, readback=True）
#    tampered_radial_offset pass=True，两次运行一致
#    catalog_mismatch pass=True，两次运行一致
#    RESULT: PASS

# JSON 解析
for f in agent-work/data/RET-001-retrieval-manifest/{*.json,inputs/*.json,ir/*.json};
  do python3 -m json.tool "$f" >/dev/null; done
# -> JSON_OK 34 files；JSONL_LINES 15
```

## 5. 15 个目录行的结果

全部成功；没有失败样本（失败路径用负对照覆盖）。

| bore_d | role | IR | compile | native | readback | 体积 mm³ |
|---:|---|---|---|---|---|---:|
| 5 | development | pass | pass | 1 solid/1 shell/valid | pass | 335.684 |
| 6 | retrieval_source | pass | pass | 1/1/valid | pass | 642.752 |
| 8 | development | pass | pass | 1/1/valid | pass | 1160.152 |
| 10 | development | pass | pass | 1/1/valid | pass | 2268.991 |
| 12 | heldout_evaluation | pass | pass | 1/1/valid | pass | 3081.009 |
| 16 | development | pass | pass | 1/1/valid | pass | 4828.618 |
| 20 | retrieval_source | pass | pass | 1/1/valid | pass | 6712.632 |
| 24 | development | pass | pass | 1/1/valid | pass | 12513.345 |
| 30 | development | pass | pass | 1/1/valid | pass | 13795.502 |
| 35 | heldout_evaluation | pass | pass | 1/1/valid | pass | 23523.950 |
| 40 | development | pass | pass | 1/1/valid | pass | 32660.578 |
| 50 | retrieval_source | pass | pass | 1/1/valid | pass | 54010.088 |
| 60 | development | pass | pass | 1/1/valid | pass | 69465.078 |
| 70 | development | pass | pass | 1/1/valid | pass | 78758.192 |
| 80 | heldout_evaluation | pass | pass | 1/1/valid | pass | 95092.285 |

## 6. Hash 与一致性

| 对象 | sha256 |
|---|---|
| `manifest-v0.jsonl` | `37818543d6bb9f3622c9f22a9c2b4f3853beb46ad6eecc1da501bf0cd0af64dc` |
| `generation-report.json` | `467d3847cc809d3bb8da3b5973289405f7677115f73c0500bf84347048b28fb6` |
| `manifest.schema.json` | `065a8fb6bf4f603e5f6cf79ded7b24f35efb018d1475306da9f37cb4ad179949` |
| `verification-report.json` | `1cf132158d9b7c73ca07987a4f74cd79c945f7d93626d32aed084d4a2acbbf4f` |
| `replay-report.json` | `185bd177897914d139727d492f61a7a5df0eb970077a57cac3d10cbe84e20ac3` |
| IR schema（冻结） | `000396c9e26bf592db022baeeb9b9af1e2a0571a7f8a0a8c3c1baed4e431bdc5` |

（`manifest-v0.jsonl` 与 `generation-report.json` 的 hash 在每次重新生成时可能变化：记录包含
`generated_at`，validation 工件包含耗时字段。已验证参数、IR 内容和几何摘要稳定。）

复现边界：`replay_check.py` 两次运行的 native 几何、数组 hash、状态一致；STEP 字节 sha256 不一致
（符合预期，STEP hash 仅作产物标识）。

## 7. 已确认事实

- 15/15 目录行在现有 Schema/规则/IR/编译器下可生成合法样本，且几何满足 CAD-006 冻结策略；
- 每条记录可回答：仓库、commit、族路径、目录行、参数与 provenance、IR 版本/schema hash、
  五项验证结果、产物 hash 与许可证边界、split/group、泄漏状态；
- STEP 回读最坏误差：体积 abs 0.03408 / rel 1.97e-6，bbox 3.55e-15 mm，面面积 0.003968 mm²，
  边长 2.80e-7 mm，均在冻结阈值内；
- 15 个几何指纹互不相同（最小成对体积相对差 9.3%），参数 JSON 互不相同，跨 split 组重叠 0；
- manifest 目录内共 34 个 JSON 文件均可解析，JSONL 15 行可逐行解析；
- 生成器、校验器、复跑脚本可重复执行，且不修改冻结源码/IR。

## 8. 未解决问题

1. **split 未冻结**：9/3/3 只是可复算的临时分组，`provisional_small_n`；是否保留切分或改为全部
   development，需 RET-003 + 中枢决定。
2. **IR 示例的 `tolerance_profile` 历史值**：示例仍为 `CAD-006.pending.v0`；是否需要更新示例属于
   IR-001 文件边界，本任务未改。
3. **`docs/TASKS.md` / `docs/PROJECT_STATUS.md` 未同步**：超出允许修改范围，需中枢把 RET-001 标为
   `review`。
4. **单环境**：仅 macOS arm64 + 固定 CadQuery/OCP；跨平台、跨进程、其他 STEP writer 未验证。
5. **许可证**：生成 STEP 仍为 `license_scope_uncertain`；未获得上游确认前不发布。
6. **上游状态**：族为 `MERGED`、非 release-qualified；快照为 `reproducibility_partial`。

## 9. 未提交的大文件

- `work/ret-001-output/`（约 4.0 MB）：`cad/**/*.step`（2.39 MB）、`validation/*.json`、
  `replay/`、`precheck.py`、`controls/`。被 `.gitignore` 排除，未提交。
- 已提交内容不含 STEP、渲染图、网格或第三方图纸；`agent-work/data/RET-001-retrieval-manifest/`
  共约 624 KB（其中 `ir/` 321 KB 文本）。

## 10. 下一 Agent / 中枢重点检查

1. 重跑 `verify_manifest.py`（数据完整性）与 `replay_check.py`（几何复跑）；
2. 抽查一条 development 样本（如 `catalog-bore-020`）与一条 heldout 边界样本（`catalog-bore-080`，
   `second_screw=1`）；
3. 抽查失败对照：篡改 `radial_offset` 必须在 semantic 阶段拒绝且无 STEP；
4. 检查 split 是否可接受，或改为不切分；
5. 检查 `tolerance_profile` 的表述与 IR 示例不一致是否需要修正；
6. 检查是否同意把生成器放在任务目录内（未进入 `src/`）。
