# CAD-005/006-R2 修正 checkpoint

```text
task=CAD-005/006-R2
status=review
changed=src/cad_compilation/__init__.py; tests/cad_compilation/test_handoff.py; agent-work/cad-validation/CAD-005-006/checkpoint-r2.md; agent-work/cad-validation/CAD-005-006/handoff_successor_check-r2.md; agent-work/cad-validation/CAD-005-006/CODEX-REVIEW-REQUEST.md; docs/WORKLOG.md
commit=7595fff
handoff_successor_check=agent-work/cad-validation/CAD-005-006/handoff_successor_check-r2.md
verified=see command table below; each result records actual execution
import_status=pass
script_status=work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py -> status=pass; system python3 tests/cad_compilation/test_handoff.py -> status=blocked because cadquery is unavailable
scope_check=R2 changes are limited to the allowed paths; pre-existing untracked CODEX-REVIEW-REQUEST.md was preserved and updated in place
known_limits=CAD-005 compiler and CAD-006 geometry/STEP validator are not implemented; no fake compiler/result classes are exported; STEP byte hash remains unstable; thread is a revolved-ring approximation and may be a no-op for M3-M8; outer_d < bore_d can build/read back as 3 solids when preflight is bypassed; source snapshot remains reproducibility_partial; external asset/license scope remains uncertain; Python 3.10 was not run
next=Codex 中枢审查后，决定是否启动 CAD-005/006 正式实现
```

## 实际验证命令

| 命令 | 结果 |
|---|---|
| `python3 -m py_compile $(find src/cad_compilation -name '*.py' -print)` | PASS |
| `PYTHONPATH=src python3 -c "import cad_compilation; print('cad_compilation import PASS')"` | PASS |
| `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v` | 17 tests PASS |
| `work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py` | exit 0；两个合法案例为 1 solid；coupling 规则和壁厚规则均被 `check()` 拒绝；绕过壁厚规则的事实为 3 solids |
| `/tmp/cad005006-r2-jsonschema-venv/bin/python` 的 Draft 2020-12 `check_schema` + 5 examples | PASS；5 个示例全部通过 |
| `python3 tests/cad_compilation/test_handoff.py` | `status=blocked`；系统 Python 3.9.6 没有 CadQuery |
| `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py` | PASS；固定快照、显式 shim、正常案例和失败案例均检查通过 |
| `git diff --check` | 待提交前复跑 |

## 事实边界

- R1 文件未覆盖或删除；本轮只是修复不可导入包、把交接脚本放回仓库、补写 R2 续任复核和审查请求。
- `legal-catalog-row.json`、`legal-second-screw.json`、`missing-bore.json`、`rule-rejected-second-screw.json`、`validation-failure.json` 已由 Schema validator 检查，但后四类 CAD-005/006 行为仍是后续实现测试，不是本轮已实现能力。
- 后续正式计划至少包含上述五个 IR 案例、STEP 导出/回读失败，以及错误 source commit、缺失节点输入、重复 ID、未来依赖、未登记公式和错误 `validation_result` 等 IR 语义反例；本轮不实现这些测试。
