# CAD-005/006-R2 Codex 中枢审查记录

日期：2026-11-02  
审查人：Codex 中枢  
审查对象：`7595fff`、`bf5b18d` 及本轮文档修整  
状态：`done`（R2 修正已在本地 `main` 验证；正式 CAD-005/006 仍为 `planned`）

## 审查结论

CAD-005/006-R2 修正通过，可以把修正后的交接结果交给后续正式实现任务。R2 只恢复了可导入的包边界、仓库内交接 smoke test 和准确的环境/限制记录，没有实现 Typed CAD IR 编译器或 CAD-006 几何/STEP 验证器。

## 独立验证

- `PYTHONPATH=src python3 -c "import cad_compilation"`：通过。
- `python3 -m py_compile $(find src/cad_compilation -name '*.py' -print)`：通过。
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`：17 项通过。
- `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`：通过；正常案例为 1 solid，非法 `second_screw` 被拒绝。
- `python3 tests/cad_compilation/test_handoff.py`：明确返回 `blocked`，原因是系统 Python 3.9.6 没有 CadQuery；这不是通过或失败的伪装。
- `work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py`：通过；绕过规则时 `outer_d < bore_d` 仍产生 3 solids，风险被保留。
- `git diff --check HEAD~2..HEAD`：通过。

## 范围与接口判断

- `src/cad_compilation/__init__.py` 是诚实的可导入骨架，没有导出不存在的编译器、验证器或结果类。
- 交接脚本位于仓库 `tests/cad_compilation/test_handoff.py`，读取固定 BenchCAD 快照，不复制或修改源快照。
- R2 没有新增第二零件族、训练数据、自由代码执行路径或 CAD-005/006 生产实现。
- Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4 是当前已验证环境；Python 3.10 未验证。
- STEP 字节哈希不作为几何一致性的唯一依据；`reproducibility_partial`、环形螺纹近似和多实体风险继续有效。

## 后续门槛

正式启动 CAD-005/006 前，必须重新冻结公式单位契约、五类 IR 节点的坐标/placement 解释、几何摘要容差和 STEP 回读失败分类，并在实现任务中覆盖五个 IR 示例及正常/失败/回读失败案例。当前不能把 CAD-005 或 CAD-006 标记为 `done`。
