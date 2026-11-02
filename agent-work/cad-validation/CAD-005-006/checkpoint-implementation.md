# CAD-005/006 implementation checkpoint

```text
task=CAD-005/006
phase=implementation
status=review
changed=src/cad_compilation/**; tests/cad_compilation/**; agent-work/cad-validation/CAD-005-006/ir-native-comparison.json; this checkpoint; docs/WORKLOG.md (append only)
verified=10 CAD compiler tests; 17 schema tests; six IR examples; handoff smoke; BenchCAD smoke; py_compile; diff check
ir_version=typed-cad-ir.v0 / 0.2.0
schema_version=set_screw_shaft_collar.v0 / schema sha256=000396c9e26bf592db022baeeb9b9af1e2a0571a7f8a0a8c3c1baed4e431bdc5
tolerance_policy=CAD-006.geometry-comparison.v1
source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c
geometry_repeatability=exact same-process summary equality passed for both legal IR cases; native-to-STEP policy passed for both; IR-native vs fixed BenchCAD native comparison passed with zero metric differences
known_limits=reproducibility_partial; license_scope_uncertain; revolved_ring_approximation; helical_thread_supported=false; macOS arm64 only; not an engineering safety/strength/FEA/collision validation
next=Codex 中枢独立审查
```

## 实现范围

- 新增 JSON 文本入口、Draft 2020-12 Schema 加语义验证、白名单参数/公式解释、冻结七节点图执行及 CadQuery 构造；不执行 IR 中的自由代码。
- 加入 preflight、几何有效性/单实体检查、精确同进程重复摘要、STEP 导出/回读及 CAD-006 几何比较策略；manifest 记录环境、source commit、IR/schema、策略和运行结果。
- 失败报告按冻结 Schema 的错误对象输出，并保留 `validation_result` 的阶段与 `completed_stages` 契约。
- 增加阶段/语义反例测试及两组真实 IR 对固定 BenchCAD 原生参考逐项比较报告：`ir-native-comparison.json`。

## 验证记录

运行环境：项目 venv Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4；macOS arm64。IR revision `0.2.0`，Schema `set_screw_shaft_collar.v0`，source commit `035f467142888edfd0bd7cd73906f9b155c8f43c`。

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -v` | PASS，10 项；含六示例、规则拒绝、错误报告、反例、多实体拒绝、STEP 导出/回读失败注入、两组完整 IR 编译 |
| `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v` | PASS，17 项 |
| `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py` | PASS；固定快照 commit 与正常/拒绝结果符合 R2 交接记录 |
| `work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py` | PASS；合法目录与边界 1 solid；second_screw 规则拒绝；绕过规则的 outer_d < bore_d 输出 3 solids |
| `PYTHONPATH=src work/benchcad-output/venv/bin/python -m py_compile src/cad_compilation/*.py tests/cad_compilation/*.py` | PASS |
| `git diff --check` | PASS |

两个 IR 示例均通过同进程 native 精确摘要重复比较和 native→STEP roundtrip 策略。对照固定 BenchCAD `part.build()` 的 native 几何，目录行与 second-screw hard boundary 的 bbox、体积、排序面面积、排序边长、拓扑计数均逐项相同（误差为 0）；逐项报告和完整摘要见 `ir-native-comparison.json`。无超限，因此未更改冻结阈值或 IR 语义。

## 未解决事项与交接

- 本证据只覆盖固定 macOS arm64 / Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 环境；跨平台、跨进程和第二族未验证。
- 保留 `reproducibility_partial`、`license_scope_uncertain`；螺纹仅为 `revolved_ring_approximation`，不支持真实螺旋螺纹。结果不构成强度、碰撞、有限元或工程安全结论。
- 请 Codex 中枢重点审查白名单构造映射、错误阶段持久化、拓扑/数值逐项比较实现和本轮原生对照记录。项目状态保持 review，不 push，不标记 done。
