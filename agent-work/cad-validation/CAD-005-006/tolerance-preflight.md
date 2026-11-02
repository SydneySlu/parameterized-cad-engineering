# CAD-005/006 阶段 1：几何容差前置测量

日期：2026-11-02  
任务：`CAD-005/006-tolerance`  
状态：`review`（等待 Codex 中枢独立审查；未启动阶段 2）

## 测量边界

测量脚本 `tolerance_measurement.py` 只读取固定 BenchCAD API/raw 快照 `work/benchcad-source/api-snapshot-035f467/` 的 `set_screw_shaft_collar` `part.py`/`spec.py`，不复制、修改或提交 BenchCAD 源码。每个合法目录行重复构造 3 次，构造后导出 STEP 并用同一 CadQuery/OCP 环境回读。临时 STEP 仅写入被 `.gitignore` 忽略的 `work/benchcad-output/tolerance-measurement/`。

测量覆盖 15 个目录 `bore_d`：`5, 6, 8, 10, 12, 16, 20, 24, 30, 35, 40, 50, 60, 70, 80`，共 45 次 native build、45 次 STEP readback。`bore_d=20, second_screw=0` 对应 legal catalog row；`bore_d=80, second_screw=1` 对应合法 hard boundary。所有合法目录行的 `spec.check()` 均返回空错误。

## 环境和来源

- Python 3.11.18；CadQuery 2.3.0；OCP 7.9.3.0；NumPy 1.26.4；macOS arm64。
- BenchCAD source commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`；快照状态：`reproducibility_partial`。
- IR：`typed-cad-ir.v0`，revision `0.2.0`。
- Schema：`set_screw_shaft_collar.v0`；`ir-v0.schema.json` SHA-256：`000396c9e26bf592db022baeeb9b9af1e2a0571a7f8a0a8c3c1baed4e431bdc5`。
- 脚本显式记录 CQ 2.3/OCP 7.9 `OCP.TopoDS.HashCode` fallback shim。

## 每次记录的指标

`tolerance-results.json` 保存每个 run 的 solids、shells、faces、edges、vertices、`isValid()`、体积、6 个包围盒坐标、排序后的原始面面积数组、排序后的原始边长数组、STEP 字节数/SHA-256、readback 指标及 native→readback 误差。STEP 字节 hash 只作附加信息。

| bore_d | second_screw | native S/Sh/F/E/V | readback S/Sh/F/E/V | native volume mm³ | readback volume mm³ | max volume abs diff | max volume rel diff | distinct STEP hashes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 1/1/27/57/30 | 1/1/27/57/30 | 335.683512 | 335.683512 | 1.63053073e-08 | 4.85734531e-11 | 3/3 |
| 6 | 0 | 1/1/27/57/30 | 1/1/27/57/30 | 642.751816 | 642.751816 | 2.51247911e-11 | 3.90894129e-14 | 3/3 |
| 8 | 0 | 1/1/31/65/34 | 1/1/31/65/34 | 1160.151936 | 1160.151936 | 1.8189894e-12 | 1.56788895e-15 | 3/3 |
| 10 | 0 | 1/1/31/65/34 | 1/1/31/65/34 | 2268.991389 | 2268.991389 | 2.42380338e-10 | 1.06822943e-13 | 3/3 |
| 12 | 0 | 1/1/27/57/30 | 1/1/27/57/30 | 3081.008911 | 3081.008911 | 3.11501935e-10 | 1.01103874e-13 | 3/3 |
| 16 | 0 | 1/1/31/65/34 | 1/1/31/65/34 | 4828.618024 | 4828.618024 | 1.01180376e-07 | 2.09543135e-11 | 3/3 |
| 20 | 0 | 1/1/29/59/30 | 1/1/29/59/30 | 6712.631936 | 6712.645162 | 0.0132255655 | 1.97024648e-06 | 3/3 |
| 24 | 0 | 1/1/35/73/38 | 1/1/35/73/38 | 12513.344685 | 12513.344685 | 1.03955244e-08 | 8.30755062e-13 | 3/3 |
| 30 | 0 | 1/1/31/65/34 | 1/1/31/65/34 | 13795.502252 | 13795.502252 | 2.01751391e-07 | 1.46244324e-11 | 3/3 |
| 35 | 0 | 1/1/41/83/42 | 1/1/41/83/42 | 23523.949993 | 23523.950054 | 6.10800962e-05 | 2.5965068e-09 | 3/3 |
| 40 | 0 | 1/1/39/81/42 | 1/1/39/81/42 | 32660.577637 | 32660.577640 | 3.15068974e-06 | 9.64676672e-11 | 3/3 |
| 50 | 0 | 1/1/47/97/50 | 1/1/47/97/50 | 54010.088039 | 54010.088039 | 6.91215973e-10 | 1.2797905e-14 | 3/3 |
| 60 | 0 | 1/1/45/91/46 | 1/1/45/91/46 | 69465.078004 | 69465.078003 | 1.62667129e-06 | 2.34171088e-11 | 3/3 |
| 70 | 0 | 1/1/45/91/46 | 1/1/45/91/46 | 78758.192428 | 78758.192424 | 3.46424349e-06 | 4.39858177e-11 | 3/3 |
| 80 | 1 | 1/1/74/149/75 | 1/1/74/149/75 | 95092.284512 | 95092.318591 | 0.0340786283 | 3.58374144e-07 | 3/3 |

结构计数在 45 个 native/readback 记录中均为 `solids=1`、`shells=1`，`isValid()` 全部为 true；不同目录的 face/edge/vertex 数随几何复杂度变化，但每个目录的 native 与 readback 计数一致。每个目录 3 次 STEP 字节 hash 均不同（45/45 个 hash 全部不同），因此 hash 不能作为重复性判据。

## 误差统计和候选阈值

### 同一环境内重复构造

30 个相邻重复比较（15 行 × 2）中，体积、包围盒、排序面面积和排序边长的最大绝对/相对差均为 `0.0`。这只说明本次环境/快照/参数下重复构造数值相同，不证明跨平台确定性。

### native build 与 STEP readback

45 个 roundtrip 比较的最大观测误差如下：

| 指标 | 最大绝对误差 | 最大相对误差 | 2×观测值候选（仅供审查） |
|---|---:|---:|---:|
| volume (mm³) | 0.0340786283195 | 1.97024648349e-06 | 0.0681572566391 abs / 3.94049296697e-06 rel |
| bbox coordinates (mm) | 3.5527136788e-15 | 1.76052790829e-15 | 7.1054273576e-15 abs / 3.52105581658e-15 rel |
| sorted face areas (mm²) | 0.003967669644 | 7.19713167552e-06 | 0.007935339288 abs / 1.4394263351e-05 rel |
| sorted edge lengths (mm) | 2.79570571138e-07 | 1.47760136545e-08 | 5.59141142276e-07 abs / 2.95520273091e-08 rel |

The 2× values are explicitly heuristic review candidates generated from this sample; they are not frozen CAD-006 policy and have not been written into production code. Coordinate relative error uses a 1 mm display floor when a coordinate is zero; absolute coordinate error remains primary. The current evidence is still `geometry_tolerance=pending_measurement` until Codex reviews sample selection, metric definitions, and any desired margin.

## Required adversarial follow-up

The measurement confirms the known boundary but does not implement it: `outer_d < bore_d` must be rejected in preflight, while bypassing preflight can produce 3 solids; `second_screw=1` at `bore_d=20` is rejected by `spec.check()`. Missing parameters, duplicate node IDs, wrong source commit, unregistered formulas, future dependencies, and inconsistent `validation_result` remain phase 2 semantic/preflight tests.

## Limits and gate

This measurement does not prove full B-Rep topology equivalence, engineering strength, collision safety, finite-element safety, real helical-thread equivalence, cross-platform reproducibility, or publishability of generated assets. The source snapshot remains `reproducibility_partial`; license scope remains uncertain.

Phase 2 (CAD-005 compiler and CAD-006 validator) must not start until Codex 中枢 independently reviews this artifact and explicitly releases the gate.
