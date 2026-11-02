# CAD-005/006 canonical binding correction checkpoint (R2)

```text
task=CAD-005/006
phase=canonical-binding-fix
status=review
changed=src/cad_compilation/ir.py; src/cad_compilation/compiler.py; tests/cad_compilation/test_compiler.py; this checkpoint; docs/WORKLOG.md (append only)
verified=CAD compiler 13 tests; schema 17 tests; typed IR schema/axis 5 tests; py_compile; git diff --check; canonical accepted examples compile and STEP readback; no-HashCode OCP probe
rejected_mutations=radial_offset; hole_len; angle
node_ids_cases=stable node path; semantic nodes.0 index path; global path empty; malformed non-object nodes schema failure empty
tolerance_policy=CAD-006.geometry-comparison.v1 (unchanged)
known_limits=single macOS arm64/Python 3.11.18/CadQuery 2.3.0/OCP 7.9.3.0 environment; cross-platform and other CadQuery/OCP combinations unverified; source family and IR v0 scope unchanged
next=Codex 中枢独立复核
```

## 修正内容

- `ir.py` 在 accepted IR 语义阶段对首族七节点图实施逐节点精确绑定。参数引用、目录键、登记公式完整树、常量/单位、节点输出、依赖、properties、placement、第二孔条件及结果分支均与 IR v0 mapping 和标准示例比较。只忽略 JSON 对象键顺序，不执行表达式。
- 不符合绑定的输入以稳定 semantic 错误拒绝，路径包含节点 ID 和具体 input；验证发生于 `_cq_runtime()` 与 `_native_build()` 之前。回归测试对 radial offset、hole length 和主孔角度突变验证 runtime/build mock 未调用且输出目录没有 STEP。
- 错误序列化从稳定节点路径和 `nodes.0` / `nodes[index]` 数组索引路径提取真实 `node_id`。全局错误及无法关联节点的错误保持空数组。非对象节点不会令定位过程本身抛错。
- 移除了编译器 `_cq_runtime()` 对所有 OCP `TopoDS_*` 类型注入 `HashCode=id(self)` 的全局 monkey patch。项目固定环境探针显示 CadQuery 2.3.0、OCP 7.9.3.0，`TopoDS_Shape.HashCode` 在 `_cq_runtime()` 前后均不存在；修订后 13 项 CAD 测试中的合法 IR 原生构造、精确重复摘要、STEP 导出/回读通过。

## OCP 兼容性风险

固定 BenchCAD 快照 `framework/bench2/execute.py` 和 `render.py` 对其隔离执行器/editor 注入该补丁，并称其用于兼容 CadQuery 2.3 / OCP 7.9；执行器说明导出器会触及 `HashCode`。本 CAD 编译器直接构造和导出路径在固定环境经真实合法案例测试不依赖此方法，删除补丁避免改变进程内所有拓扑对象的 identity/hash 行为。但其他 CadQuery API、CQ-editor、BenchCAD 隔离执行器或其他 OCP 版本的兼容性未由本任务证明，不能据此推断全局安全；若后续调用这些路径，应针对其调用栈单独验证并优先采用局部适配。

## 定向复核与验证

- 续任复核基线：审查记录 `agent-work/reviews/CAD-005-006-implementation-codex-review.md` 和原 checkpoint `checkpoint-implementation.md`；原 10 项 CAD 基线在本轮初始检查中通过。
- 正常案例：`legal-catalog-row.json`、`legal-second-screw.json` 完整 native 构造及 STEP 回读通过；同进程精确重复比较和 native→STEP 固定比较策略通过。
- 失败案例：三种核心绑定突变均在 semantic 阶段拒绝；mock 证明 `_cq_runtime`、`_native_build` 未调用，输出目录无 STEP。
- `PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -v` — PASS, 13 tests.
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v` — PASS, 17 tests.
- `work/benchcad-output/venv/bin/python -m unittest tests.typed_cad_ir.test_schema_contract tests.typed_cad_ir.test_axis_mapping -v` — PASS, 5 tests.
- `PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 work/benchcad-output/venv/bin/python -m py_compile src/cad_compilation/*.py tests/cad_compilation/*.py` — PASS.
- `git diff --check` — PASS.
- OCP runtime probe — `HashCode` absent before and after `_cq_runtime()` on CadQuery 2.3.0 / OCP 7.9.3.0.
- CAD-006 policy ID and thresholds, `tolerance-results.json`, `tolerance-preflight.md`, ADR-0008, IR spec §9.2 remain unchanged; no 45-case tolerance measurement rerun.

## 冻结材料交接说明

IR v0 spec §11 currently describes `legal-second-screw.json` as schema/semantic-valid but not yet CAD-constructed or STEP-validated. That sentence is stale after the previously reviewed CAD-005/006 implementation evidence. Suggested additive note for Codex 中枢: record that the canonical second-screw example has now passed CAD native construction and STEP readback in the pinned environment, while preserving the existing cross-platform limits. This Agent did not edit frozen IR materials.

The implementation remains `review`; this checkpoint does not mark CAD-005/006 done and does not authorize push.
