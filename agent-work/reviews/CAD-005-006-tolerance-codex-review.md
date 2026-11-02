# CAD-005/006 容差前置测量：Codex 中枢审查

日期：2026-11-02  
审查对象：CAD-005/006-tolerance，提交 `e5bcacf` 与 checkpoint 校正 `7e9f0f0`  
审查状态：`review`  
阶段 2 放行：`held`（现有 IR 数值容差候选与实测最大误差不相容，须先由中枢确定并记录可用策略）

## 结论

阶段 1 的测量工作本身通过审查：覆盖了固定首族全部 15 个合法目录值，每个重复构造 3 次，包含 native 几何指标、STEP 回读和已知多实体对抗事实。脚本在项目隔离环境独立重跑成功，结果仍为 45/45 native build、45/45 STEP readback、30 组同参重复比较和 45 组 roundtrip 比较；schema 测试 17 项、交接 smoke 和 DATA-003 smoke 均通过。

但这不代表几何容差已经冻结，也不能据此宣称 CAD-006 已可按现有 IR 数值候选实现。实测 STEP 往返最大误差超过 IR-001 R3 原候选的 volume、face area 相对/绝对阈值，并略超过 edge-length 相对阈值：

| 指标 | IR-001 R3 候选 | 本轮最大观测误差 | 判断 |
|---|---:|---:|---|
| 体积 | abs 1e-4 mm³ / rel 1e-8 | abs 0.03407863 mm³ / rel 1.97025e-6 | 候选不足 |
| 面积列表逐项 | abs 1e-5 mm² / rel 1e-8 | abs 0.00396767 mm² / rel 7.19713e-6 | 候选不足 |
| 边长列表逐项 | abs 1e-5 mm / rel 1e-8 | abs 2.79571e-7 mm / rel 1.47760e-8 | 相对候选不足；绝对候选覆盖本次误差 |
| 包围盒坐标 | abs 1e-5 mm / rel 1e-8 | abs 3.55271e-15 mm / rel 1.76053e-15 | 本轮观测低于候选 |

测量报告提出的“2×最大观测误差”是合理的审查输入，但仍是单一 macOS arm64 / Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 环境下、对 BenchCAD 原生 `build()` 的经验值。它不是项目 Typed CAD IR 编译器的测量结果，也没有跨平台或跨内核版本证据。必须在中枢决策中明确哪些阈值适用于“同环境重复性”，哪些适用于“同次构造与 STEP 回读”；两者不可混成一个确定性承诺。

## 独立验证

- `work/benchcad-output/venv/bin/python agent-work/cad-validation/CAD-005-006/tolerance_measurement.py`：PASS，45 条记录、45 条成功、30 组 native repeat、45 组 STEP roundtrip。
- `work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py`：PASS；正常目录案例构造为 1 solid，second-screw 规则案例按预期被拒绝。
- `work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py`：PASS；保留合法案例、规则拒绝和绕过规则后多 solid 事实。
- `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`：17 项 PASS。
- 结果 JSON 可解析；记录数、重复次数、Schema SHA-256 和结构汇总相符；`git diff --check` PASS。

独立重跑会重写被跟踪的 `tolerance-results.json` 中 STEP 输出的路径/hash 等易变数据。本审查已恢复该文件到提交版本；该现象也符合报告中“STEP 字节 hash 不作为几何重复性标准”的处理。

## 已确认的事实与边界

- 15 个目录值均有 3 次测量；所有合法 native/readback 结果均为 1 solid、1 shell 且 `isValid() == true`。
- 同一进程/环境内本轮 30 组相邻重复比较的体积、包围盒、排序面面积和排序边长误差均为 0；该结论仅限当前环境和 BenchCAD 原生构造路径。
- `outer_d < bore_d` 被规则层拒绝；绕过规则后出现 3 solids 的风险在既有 smoke 结果中复现。
- 报告保留 `reproducibility_partial`、`license_scope_uncertain`、环形螺纹近似以及不支持强度/安全/有限元结论。
- 本轮没有实现 IR → CadQuery 编译器或生产几何验证器。

## 放行条件

在 CAD-005/006 正式实现开始前，中枢必须先把容差契约写入审查/决策记录，至少明确：

1. native 同参重复比较和 STEP 回读比较分别采用什么阈值；
2. 数值比较是 abs/rel 两者都要通过，还是按 `abs_tol + rel_tol × scale` 等明确组合规则；
3. 面面积/边长列表是否要求元素数量精确相同并按升序逐项比较；
4. 这些阈值只适用于当前固定软件环境，还是要覆盖其他环境；尚无证据的环境必须标成未验证；
5. CAD-005 实际 IR 编译结果应补做至少正常目录与 hard-boundary 的 native/STEP 摘要核验，并在任何阈值变化时报告。

在上述策略决策记录完成前，CAD-005/006 任务仍保持 `planned/review`，不可写成 `done`，也不可宣称容差已经冻结。当前阶段 1 交付可作为合格测量证据，后续修订不需要重跑整个 45 项测量，除非更改环境、指标定义或发现数据/脚本缺陷。

