# RET-001 初始化 Prompt：单族检索样本 Manifest

你是“参数化 CAD 工程辅助设计”项目的 RET-001 数据与检索样本 Agent。你的任务是围绕已经冻结的首期零件族，建立可审计、可重放、避免评测泄漏的检索样本 manifest v0。

## 1. 项目根目录与当前基线

项目根目录必须是：

`/Users/syd/Desktop/参数化 cad 工程辅助设计`

启动时先执行：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -5
```

当前已验收的前置基线：

- 首期族：`set_screw_shaft_collar`
- BenchCAD 仓库：`https://github.com/BenchCAD-org/benchcad-2`
- 固定 source commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`
- 固定源路径：`designs/set_screw_shaft_collar`
- 快照状态：`reproducibility_partial`
- IR：`typed-cad-ir.v0`，revision `0.2.0`
- 几何比较策略：`CAD-006.geometry-comparison.v1`
- CAD-005/006 修正提交：`df78f4f`
- 当前 CadQuery/OCP 基线：Python 3.11.18、CadQuery 2.3.0、OCP/cadquery-ocp 7.9.3.0、NumPy 1.26.4、macOS arm64

必须先阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
database/README.md
database/benchcad-dataset-first-plan-2026-10.md
agent-work/data/DATA-003-single-family-audit/source-audit.md
agent-work/data/DATA-003-single-family-audit/license-matrix.md
agent-work/data/DATA-003-single-family-audit/minimal-manifest.json
agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md
agent-work/typed-cad-ir/IR-001-v0/mapping.md
agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json
src/schema/set_screw_shaft_collar.py
src/cad_compilation/compiler.py
src/cad_compilation/ir.py
agent-work/cad-validation/CAD-005-006/checkpoint-canonical-binding-r2.md
agent-work/reviews/CAD-005-006-implementation-codex-review.md
```

这是高风险交接。开始生成样本前必须完成定向复核：

1. 重跑至少一条 CAD 编译核心命令；
2. 检查一个正常案例和一个失败案例；
3. 确认输入是首族参数 JSON，输出接口是现有 IR/编译器和验证 manifest；
4. 若交接记录与仓库实际不一致，先写 `review` 或 `blocked` checkpoint，暂停，不覆盖前序成果。

## 2. 本任务目标

建立首期单族的 `retrieval manifest v0`，使每个样本都能回答：

- 来自哪个仓库、commit、族目录和目录行；
- 使用了哪些参数、单位和字段来源；
- 使用哪个 IR 版本和 schema；
- 是否成功通过 Schema、族规则、CAD 构造、实体检查、STEP 回读；
- 生成物位于哪里、哈希是什么、是否允许项目内部使用/再发布；
- 属于开发、检索库还是评测集，是否与其他 split 存在目录行或几何近重复泄漏。

首期只做数据 manifest 和样本构建，不实现检索排序、向量库、LLM Prompt 或 RET-002/RET-003 评测算法。

## 3. 样本范围

冻结族的参数目录在 `src/schema/set_screw_shaft_collar.py` 中有 15 个 `bore_d` 目录行。首轮应覆盖这 15 个合法目录行：

```text
bore_d = 5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80 mm
```

对每个目录行：

1. 用项目 Schema/规则得到规范化参数和 provenance；
2. 生成与 IR v0.2.0 兼容的 accepted IR；
3. 调用现有 `compile_ir()`，完成 native 构造、几何门槛、STEP 导出和 STEP 回读；
4. 保存机器可读验证结果和几何摘要引用；
5. 写入一个稳定、唯一的 manifest 记录。

不要凭空扩展参数空间。首期 Schema 的参数是目录耦合的，不能把任意随机尺寸标成合法真值。若你认为需要 50–100 个样本，必须先记录“当前首族只有 15 个冻结目录行”的事实，并提出后续扩展方案，不能悄悄生成超出 Schema/源数据契约的样本。

## 4. Manifest v0 最小字段

建议在 `agent-work/data/RET-001-retrieval-manifest/` 下建立：

```text
README.md
manifest.schema.json
manifest-v0.jsonl
generation-report.json
checkpoint.md
handoff.md
```

每条 JSONL 记录至少包含：

```json
{
  "manifest_version": "retrieval-manifest.v0",
  "sample_id": "set_screw_shaft_collar/catalog-bore-020",
  "family_id": "set_screw_shaft_collar",
  "sample_kind": "catalog_row",
  "source": {
    "repository": "https://github.com/BenchCAD-org/benchcad-2",
    "source_commit": "035f467142888edfd0bd7cd73906f9b155c8f43c",
    "family_path": "designs/set_screw_shaft_collar",
    "family_status": "MERGED",
    "release_qualified": false,
    "snapshot_status": "reproducibility_partial",
    "license_scope": "source/designs MIT; generated STEP/render scope uncertain"
  },
  "parameters": {
    "normalized": {},
    "units": "mm",
    "provenance": {},
    "catalog_key": "bore_d"
  },
  "ir": {
    "ir_version": "typed-cad-ir.v0",
    "ir_revision": "0.2.0",
    "schema_sha256": "...",
    "path": "...",
    "sha256": "..."
  },
  "artifacts": {
    "step": {
      "path": "...",
      "sha256": "...",
      "bytes": 0,
      "repository_status": "ignored_local_artifact"
    },
    "render": null
  },
  "validation": {
    "schema": "pass",
    "family_rules": "pass",
    "cad_compile": "pass",
    "native_geometry": {},
    "native_repeatability": {},
    "step_readback": {},
    "policy_id": "CAD-006.geometry-comparison.v1"
  },
  "split": {
    "role": "development",
    "group_id": "catalog-row-bore-020",
    "split_rule": "catalog-row-grouped; provisional until RET-003 review"
  },
  "generation": {
    "generator": "project RET-001 generator",
    "seed": null,
    "python": "...",
    "cadquery": "...",
    "ocp": "...",
    "numpy": "..."
  },
  "limitations": [
    "single frozen family",
    "source snapshot reproducibility_partial",
    "generated STEP license scope uncertain"
  ]
}
```

字段可以调整，但不能删除 provenance、source commit、IR/schema 版本、验证结果、split/group、许可证边界或 hash。若字段含义不确定，写入 README 和 checkpoint，不要默默假设。

## 5. Split 与泄漏控制

首期只有 15 个目录行，不能把随机重复实例伪装成独立数据。请：

- 以 `family_id + catalog row` 作为最小分组键；
- 每条样本包含稳定 `group_id`；
- 记录 provisional split（例如 development/retrieval/evaluation），并说明分配规则；
- 不允许同一目录行、同一参数 JSON 或 near-duplicate 几何同时出现在 retrieval 与 held-out evaluation；
- 如果 15 行不足以支持有统计意义的切分，明确写 `split_status=provisional_small_n`，不要声称已完成正式 benchmark；
- 不使用 BenchCAD Public/Core 下载制品作为训练、检索语料或再发布内容；
- 不把 `STEP SHA-256` 当几何一致性证明；几何通过必须引用 CAD-006 结构化摘要和策略 ID。

在 manifest 中区分：

```text
retrieval_source / development_sample / heldout_evaluation
```

如果当前无法合理冻结 split，先提交分组表和建议，不要擅自把它写成最终评测切分。

## 6. 生成与验证要求

允许复用现有项目代码和固定快照，但不得修改 IR 语义来适配数据。

推荐使用项目固定环境：

```bash
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python ...
```

至少完成：

1. 15 个目录行的 Schema/族规则检查；
2. 15 个 accepted IR 的 JSON Schema 和语义检查；
3. 15 个 `compile_ir()` 运行；
4. 每个成功样本均记录单 solid、单 shell、`isValid`、体积、bbox、面面积/边长摘要，以及 STEP 回读比较；
5. 记录失败样本（如果有），保留错误码、阶段、字段和 node_ids；
6. 对一个正常样本和一个失败样本分别复跑，确认结果可重现；
7. 对生成的 manifest 做 JSON Schema 校验、JSONL 逐行解析和 hash 校验；
8. 对固定源码、IR、STEP 文件使用 SHA-256；不要提交大体积 STEP/渲染文件，默认放在被 `.gitignore` 排除的 `work/ret-001-output/`；
9. 如果生成渲染图，放在 ignored 输出目录并只在 manifest 中记录路径、hash、视图参数和许可证状态；渲染不是首期必需项。

注意：STEP 的字节 hash 只能作为产物标识。同一几何重复构造的 STEP 字节可能不同，不能因此判为失败或重复。

## 7. 文件边界

允许修改：

```text
agent-work/data/RET-001-retrieval-manifest/**
docs/WORKLOG.md                                    # 只追加
```

如确需新增可复用生成器，先在 checkpoint 说明理由和路径；不要修改：

```text
src/schema/**
src/cad_compilation/**
agent-work/typed-cad-ir/**
agent-work/cad-validation/**
docs/DECISIONS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
database/**
```

若发现 manifest 字段必须改变现有 Schema/IR、零件族范围、许可证或验收标准，立即记录 `blocked`，交回 Codex 中枢，不自行改架构。

## 8. 三层交接与提交要求

### 交接 Agent 自检

在 `checkpoint.md` 和 `handoff.md` 中记录：

- 修改/新增了什么；
- 实际运行的完整命令和结果；
- 15 个目录行分别成功/失败；
- manifest/schema/hash 是否通过；
- 哪些事实已确认；
- 哪些问题仍未解决；
- 下一 Agent 必须重点检查什么；
- 是否生成了未提交的大文件以及它们位于哪里。

### 续任 Agent 定向复核

续任者开始前必须：

1. 阅读 checkpoint/handoff；
2. 重跑至少一条核心 manifest/验证命令；
3. 检查一个成功样本和一个失败样本；
4. 检查一个正常 split 和一个边界/小样本 split；
5. 发现交接不一致时先记录 `review`/ `blocked`，不得覆盖成果。

### Codex 中枢最终审查

你不要把任务自行标记为 `done`。完成后将状态保持 `review`，提交 Git commit，并在 `docs/WORKLOG.md` 追加：

```text
[YYYY-MM-DD HH:MM] agent=<id> task=RET-001 status=review
scope=<manifest 和样本构建范围>
verified=<实际命令和结果>
known_limits=<单族、15 行、小样本 split、许可证/快照限制>
next=Codex 中枢独立审查
commit=<short hash>
```

提交信息格式：

```text
feat: add retrieval manifest v0 [RET-001]
```

不要 push；由项目负责人确认中枢审查通过后 push。

## 9. 明确禁止

- 不下载或使用 BenchCAD Public/Core 数据制品作为训练/检索数据；
- 不把 15 个目录行扩写成“50–100 个真实样本”；
- 不修改冻结的 IR、Schema、CAD 编译器、验证器或 CAD-006 容差；
- 不把生成 STEP、渲染图或第三方图纸直接提交到 Git；
- 不把未验证的参数、几何或许可证信息写成事实；
- 不执行自由 CAD 代码或模型生成代码；
- 不把通过 manifest JSON Schema 当作 CAD 几何正确性的替代；
- 不覆盖其他 Agent 未合并的成果。

开始前先回报启动检查结果；中途按里程碑追加 checkpoint，遇到阻塞立即停止扩大范围。

