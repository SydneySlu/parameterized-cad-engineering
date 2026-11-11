# APP-002-INTEGRATION-A1 checkpoint — M1/M2 implementation

## Status: in_progress (M1 ✓, M2 ✓, M3 pending Codex review)

日期：2026-11-11。执行者：CC。
本次为 WIP 实现提交；独立验收由 Codex 中枢在 Mac 固定 CAD 环境下完成。

---

## 分支与代码基线

- 起始 HEAD：`7411d65`（cc/APP-002-INTEGRATION-A1 分支基点）
- 分支：`cc/APP-002-INTEGRATION-A1`
- 本轮无 push/merge；WIP commit 在分支内

---

## 新增文件

| 文件 | 说明 |
|---|---|
| `src/integration/__init__.py` | 包入口，导出 AdapterResult、build_ir_from_schema_payload、PipelineResult、run_pipeline |
| `src/integration/schema_to_ir.py` | 正式 Schema→IR adapter；固定 source commit/adapter_id/adapter_version；始终内部重验 |
| `src/integration/pipeline.py` | 统一离线 pipeline；parse→gate→Schema→IR→CAD→STEP；run 隔离；证据文件 |
| `src/integration/README.md` | 用法说明、CLI 命令、status 表、run 目录结构 |
| `scripts/run_cad_pipeline.py` | 统一 CLI；--request/--synthetic-envelope/--output-root/--json；退出码 0/1/2 |
| `tests/integration/__init__.py` | 测试包 |
| `tests/integration/test_schema_to_ir.py` | 42 项 adapter 测试（见下） |
| `tests/integration/test_pipeline.py` | 29 项 pipeline 测试（见下） |
| `tests/integration/fixtures/answer-bore24.json` | 合成 v5 envelope，bore_d=24 |
| `tests/integration/fixtures/answer-bore20.json` | bore_d=20 |
| `tests/integration/fixtures/answer-bore16cm.json` | bore_d={value:1.6, unit:cm} |
| `tests/integration/fixtures/answer-bore70.json` | bore_d=70 |
| `tests/integration/fixtures/answer-bore80.json` | bore_d=80 |
| `tests/integration/fixtures/ask-missing-bore.json` | decision=ask |
| `tests/integration/fixtures/refuse-unsupported.json` | answer+unsupported_requests非空 |
| `tests/integration/fixtures/answer-missing-fields.json` | answer+missing_fields非空 |
| `tests/integration/fixtures/refuse-decision.json` | decision=refuse |

---

## 实际执行命令与结果（VM，Python 3.10，无 cadquery）

```bash
# py_compile 通过
PYTHONPATH=src:. python3 -m py_compile src/integration/__init__.py src/integration/schema_to_ir.py src/integration/pipeline.py scripts/run_cad_pipeline.py
# 结果：通过

# 集成测试（全量）
PYTHONPATH=src:. python3 -m unittest discover -s tests/integration -p 'test_*.py' -q
# 结果：Ran 71 tests; OK

# Schema 回归（防止新文件破坏已有实现）
PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
# 结果：Ran 17 tests; OK

# tests/cad_compilation（需要 cadquery）
# 状态：not_run_no_cad_runtime（VM 无 /opt/homebrew/opt/python@3.11）
# Mac 固定环境已验证 13 项通过（来自 preflight 报告）

# tests/llm（需要 Python 3.11 / FUSE mock 环境）
# 状态：not_run（VM Python 3.10；历史上 842+8skip 通过，见 APP-001 审查）
```

---

## 关键设计决策记录

### 1. Schema→IR adapter (schema_to_ir.py)

- **始终内部重验**：`build_ir_from_schema_payload` 调用 `validate_parameters` 而不信任外部 ok=True
- **adapter_id/adapter_version 固定**：IR JSON schema 有 const 约束（`benchcad.set_screw_shaft_collar` / `0.1.0`），适配器遵守之；`ADAPTER_VERSION` 常量供外部调用方记录版本
- **input 字段保留原始值**：裸数字→`{value:N, unit:"mm"}`，measurement object→原样保留（如 1.6cm）
- **second_screw=1 iff bore_d>70**：bore_d=70→0（rule_derived），bore_d=80→1（rule_derived）；bore_d=75 被拒绝（非目录值）
- **screw_len 是目录字段**，不是孔深，不映射为孔深公式
- **canonical nodes 为模块级常量**：七节点固定图不依赖参数值，只有 parameters 列表变化

### 2. Pipeline 构造门 (pipeline.py)

明确分五步（比旧 adapter.construction_ready 更严格）：
1. parse_response 成功
2. decision == "answer"
3. missing_fields == []（旧 adapter 未检查此项）
4. unsupported_requests == []
5. project_to_cad003 + validate_parameters 均成功

### 3. Run 隔离

- UUID 或指定 run_id → `work/integration-runs/<run_id>/`
- mkdir(exist_ok=False) 保证原子独占
- run_id 只允许 [a-zA-Z0-9_-]；含 `..` 或 `/` 的 run_id 被拒绝
- 失败运行不发布 STEP；不返回其他 run 的旧 STEP

### 4. compile_ir 模块级绑定

pipeline.py 在模块级导入（通过包装函数 `compile_ir`），使测试可以通过 `patch("integration.pipeline.compile_ir", ...)` 注入 mock。

---

## 验收证据摘要

| 场景 | VM 结果 | 备注 |
|---|---|---|
| bore_d=24, 20 → accepted IR | ✓ | 参数值/来源/input 正确 |
| bore_d={value:1.6,unit:cm} → value=16mm, input保留 | ✓ | unit 转换+保留 |
| bore_d=70 → second_screw=0 (rule_derived) | ✓ | 阈值严格 >70 |
| bore_d=80 → second_screw=1 (rule_derived) | ✓ | |
| bore_d=75 → rejected CATALOG_CHOICE | ✓ | 非目录值 |
| missing bore → rejected MISSING_REQUIRED | ✓ | |
| ask/refuse/missing_fields/unsupported → blocked/ask/refuse | ✓ | compiler 零调用 |
| CAD failure (mocked) → failed, no STEP | ✓ | |
| duplicate run_id → ValueError | ✓ | 隔离保证 |
| path escape run_id → ValueError | ✓ | 安全边界 |
| 真实本地 CAD/STEP | not_run_no_cad_runtime | 须 Mac + cadquery 环境验收 |

---

## 未运行与已知限制

- `tests/cad_compilation/`（13 项）：需要 cadquery/OCP，VM 无此环境；历史已验证，本次未重跑
- `tests/llm/`（842 项）：需要 Python 3.11 和 FUSE mock；VM 未运行，历史已验证
- 真实本地 CAD/STEP 路径：须由 Codex 中枢在 Mac 固定环境下运行 `work/benchcad-output/venv/bin/python scripts/run_cad_pipeline.py` 验收
- extraction_source 固定为 `synthetic_fixture`；真实模型整链属 A2，未授权

---

## handoff_self_check

```text
changed=src/integration/(四个文件), scripts/run_cad_pipeline.py, tests/integration/(18个文件)
commands=py_compile(4文件)通过; 71项集成测试通过; 17项Schema测试通过
confirmed=gate五条件全检; bore16cm input保留; bore70/80边界正确; run隔离; mock CAD成功/失败路径; adapter始终内部重验
unresolved=真实cadquery/STEP路径须Mac环境验收; LLM测试未在VM运行
not_changed=冻结prompt/Schema/IR语义/编译器规则/adapter历史评测; FORMAL_EVALUATION_ALLOWED=False
```

## handoff_successor_check（Codex 中枢须核验）

在 Mac 固定 CAD 环境（Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0）：

1. **至少一条真实 STEP 成功**：
   ```bash
   PYTHONPATH=src:. work/benchcad-output/venv/bin/python scripts/run_cad_pipeline.py \
       --request "请按 GN 705 做一个轴环，孔径 24 mm" \
       --synthetic-envelope tests/integration/fixtures/answer-bore24.json \
       --output-root work/integration-runs --json
   # 预期：status=success, step_path 非空, ir_index hash 匹配
   ```

2. **bore_d=16cm 单位测试**：envelope `answer-bore16cm.json`，验证 IR value=16，input={1.6,cm}，STEP 几何与bore_d=16目录一致

3. **bore_d=70/80 边界**：确认 second_screw=0/1，STEP 几何/孔数正确

4. **现有测试回归**：
   ```bash
   PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
   # 预期：13 tests OK
   PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -p 'test_*.py' -q
   # 预期：842+8skip OK
   ```

5. **完整集成测试**：
   ```bash
   PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q
   # 预期：71 tests OK（mocked CAD）
   ```

6. **git diff --check**：无空白错误

7. **任何 IR 验证失败、STEP 未生成或 hash 不匹配**：标记 blocked，记录具体错误代码，不合入
