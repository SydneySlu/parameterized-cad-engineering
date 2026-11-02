# CAD-005/006 阶段 1 容差测量 checkpoint

```text
task=CAD-005/006-tolerance
status=review
phase=tolerance-preflight
changed=agent-work/cad-validation/CAD-005-006/tolerance_measurement.py; agent-work/cad-validation/CAD-005-006/tolerance-results.json; agent-work/cad-validation/CAD-005-006/tolerance-preflight.md; agent-work/cad-validation/CAD-005-006/checkpoint-tolerance.md; docs/WORKLOG.md
commit=see git log for test: measure cad geometry tolerances [CAD-005/006]
verified=45/45 native builds and 45/45 STEP readbacks passed; native repeatability and roundtrip statistics recorded below
ir_version=typed-cad-ir.v0, revision=0.2.0
schema_version=set_screw_shaft_collar.v0, sha256=000396c9e26bf592db022baeeb9b9af1e2a0571a7f8a0a8c3c1baed4e431bdc5
source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c
next=wait for Codex 中枢 independent review; only then may phase 2 start
```

## 修改文件

- `agent-work/cad-validation/CAD-005-006/tolerance_measurement.py`：固定 BenchCAD API/raw 快照测量脚本；不复制或修改 BenchCAD 源码。
- `agent-work/cad-validation/CAD-005-006/tolerance-results.json`：15 个合法目录行、每行 3 次构造和 STEP 回读的原始指标与误差摘要。
- `agent-work/cad-validation/CAD-005-006/tolerance-preflight.md`：阶段 1 测量说明、汇总表、候选阈值和限制。
- 本 checkpoint 与 `docs/WORKLOG.md`：交接、门控和验证记录。

## 实际命令和结果

| 命令 | 实际结果 |
|---|---|
| `work/benchcad-output/venv/bin/python agent-work/cad-validation/CAD-005-006/tolerance_measurement.py` | PASS；`records=45`、`successful_records=45`、`native_repeat_comparisons=30`、`roundtrip_comparisons=45`；退出码 0 |
| `/tmp/cad005006-r2-jsonschema-venv/bin/python` 的 Draft 2020-12 schema check + 6 个 IR 示例 | PASS；包含新增 `build-failure.json`，对应 IR revision `0.2.0` |
| `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v` | PASS；17 项 |
| `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py` | PASS |
| `work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py` | PASS；合法案例为 1 solid；规则拒绝案例被 `check()` 拒绝；绕过 `outer_d < bore_d` 规则的事实结果为 3 solids |
| `python3 -m py_compile agent-work/cad-validation/CAD-005-006/tolerance_measurement.py` | PASS |
| `git diff --check` | PASS |

系统 Python 的 `tests/cad_compilation/test_handoff.py` 因缺少 CadQuery 仍不可运行；项目隔离环境是本次有效验证环境。该环境差异保留在前序 R2 交接记录中。

## 样本覆盖

覆盖全部 15 个合法目录 `bore_d={5,6,8,10,12,16,20,24,30,35,40,50,60,70,80}`，每行重复 3 次，共 45 次 native build 和 45 次 STEP readback。`bore_d=20, second_screw=0` 是合法 catalog row；`bore_d=80, second_screw=1` 是合法 hard boundary；所有目录行 `spec.check()` 均返回空错误。结构计数在全部 native/readback 记录中均为 1 solid、1 shell，`isValid() == true`。

保留的对抗事实：`outer_d < bore_d` 应在 preflight 拒绝，但绕过 preflight 可得到 3 solids；`second_screw=1` 在 `bore_d=20` 被规则拒绝。缺少关键参数、重复 node id、错误 source commit、未来依赖、未登记公式和不一致 `validation_result` 尚属于阶段 2 语义/preflight 测试计划。

未覆盖跨平台确定性、完整 B-Rep 拓扑等价、工程强度/碰撞/有限元安全、真实螺旋螺纹等价，以及阶段 2 编译器和验证器行为。

## 误差统计与候选阈值

同一环境内 30 个相邻重复比较（15 行 × 2）的体积、包围盒、排序面面积和排序边长最大差均为 `0.0`。这只说明本环境和本快照下的重复结果，不证明跨平台确定性。

45 个 native build → STEP readback 比较的最大观测误差及 2×候选值如下。候选值仅供 Codex 中枢审查，未写入 `src/cad_compilation`，不是冻结的 CAD-006 策略：

| 指标 | 最大绝对误差 | 最大相对误差 | 2×观测候选 |
|---|---:|---:|---:|
| volume (mm³) | `0.0340786283195` | `1.97024648349e-06` | `0.0681572566391` abs / `3.94049296697e-06` rel |
| bbox coordinates (mm) | `3.5527136788e-15` | `1.76052790829e-15` | `7.1054273576e-15` abs / `3.52105581658e-15` rel |
| sorted face areas (mm²) | `0.003967669644` | `7.19713167552e-06` | `0.007935339288` abs / `1.4394263351e-05` rel |
| sorted edge lengths (mm) | `2.79570571138e-07` | `1.47760136545e-08` | `5.59141142276e-07` abs / `2.95520273091e-08` rel |

每个目录的 3 个 STEP 字节 SHA-256 均不同（45/45 个 hash 全部不同），因此 hash 只能作为附加信息，不能作为重复性判据。

## 环境、来源与限制

- Python `3.11.18`，CadQuery `2.3.0`，OCP `7.9.3.0`，NumPy `1.26.4`，macOS arm64。
- 固定 BenchCAD source commit `035f467142888edfd0bd7cd73906f9b155c8f43c`；快照状态为 `reproducibility_partial`。
- 使用 `typed-cad-ir.v0` revision `0.2.0` 和 `set_screw_shaft_collar.v0` schema；脚本显式记录 CQ 2.3/OCP 7.9 的 `OCP.TopoDS.HashCode` fallback shim。
- 线程模型仍是 `revolved_ring_approximation`，`helical_thread_supported=false`；许可证范围仍为 `license_scope_uncertain`。
- 该测量不证明跨平台复现、完整实体等价、强度或安全性，也未把观察误差直接转为生产验证器阈值。

## 门控

本阶段保持 `status=review`。必须等待 Codex 中枢独立审查样本选择、指标定义、候选裕量和已知限制，并明确放行后，才能进入阶段 2 的 CAD-005 编译器与 CAD-006 验证器实现；本提交不启动阶段 2，也不把任务标记为 `done`。
