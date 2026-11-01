# DATA-003 运行日志

日期：2026-11-01；source commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`。

## 官方验证命令

运行目录：`work/benchcad-source/api-snapshot-035f467/`；解释器：`work/benchcad-output/venv/bin/python`。

```bash
work/benchcad-output/venv/bin/bench2 validate set_screw_shaft_collar --seeds 1
work/benchcad-output/venv/bin/bench2 validate slotted_din_rail --seeds 1
work/benchcad-output/venv/bin/bench2 validate speaker_pole_mount_socket --seeds 1
```

三条命令均退出码 `0`。共同结果是 `family.json`、`build + PARAM_SPEC + check`、参数规格、easy/medium/hard 采样+构造+执行、难度区分、几何唯一性和实体非退化通过；collar 还报告 15/15 `bore_d` coverage，socket 报告 2 个 bore、2 个 flange_od、2 个 flange_t、6 个 depth coverage。第一次运行因 raw 快照缺少 `framework/bench2/__init__.py` 而得到 `ImportError: cannot import name 'Resample'`，补齐同 commit 官方文件后重跑通过；该修复只补临时快照，不改源代码。

## set_screw_shaft_collar 最小 smoke

脚本：`work/benchcad-output/smoke_set_screw.py`；结果 JSON：`work/benchcad-output/smoke-set-screw/smoke-results.json`；临时 STEP 均在同目录。脚本调用原生 `part.build(**params)`、`spec.check(params)`、CadQuery STEP 导出和 `cq.importers.importStep()` 回读。

| case | 参数摘要 | check | build/实体/有效性 | STEP 回读 | 观察 |
|---|---|---|---|---|---|
| legal_catalog_row | `bore_d=20, outer_d=32, width=14, screw_d=6, screw_len=8, second_screw=0` | `[]` | 成功；1 solid；valid；体积约 `6712.632 mm³` | 成功；1 solid；valid；体积 `6712.645 mm³`；bbox `32.0000002 × 32.0000002 × 14 mm` | 合法目录行 |
| legal_hard_boundary | `80,110,22,12,20,1` | `[]` | 成功；1 solid；valid；体积约 `95092.285 mm³` | 成功；1 solid；valid；体积 `95092.319 mm³`；bbox `110.0000002 × 110.0000002 × 22 mm` | 合法范围上边界/第二螺钉 |
| invalid_check_coupling | 与 legal_catalog_row 相同但 `second_screw=1` | 拒绝：`second_screw set below d1 > 70` | 若绕过 check，仍成功；1 solid；valid | 成功；1 solid；valid | **验证风险**：约束拒绝来自 `check()`，构造器本身不拒绝 |
| invalid_geometry | `bore_d=20, outer_d=19, width=14, screw_d=6, screw_len=8, second_screw=0` | 拒绝：`wall <= 0.65*screw_d` | 若绕过 check，仍成功；**3 solids**；valid | 成功；3 solids；valid；体积约 `416.796 mm³`；bbox约 `20 × 20 × 14.18 mm` | **验证风险**：非法壁厚没有由 build 抛错，且产生多实体；不得把“STEP 成功”当作参数合法 |

## 重复性

相同 source commit、同一 venv、同一参数分别运行两次。两次 legal case 的构造成功、实体数、`isValid()`、bbox 和体积相同到报告精度；STEP 字节 hash 不同：

- `legal_catalog_row`：run1 `c3d589c8e7aefabc0f0fb7dd09a553edd1f8afbc929320c625abd52d1ecb1168`，run2 `70dfb4789accd7221920a04a7ce62fc0705a28fad95badbbcd89fa24e66a81a3`
- `legal_hard_boundary`：run1 `f7ebff0ee5b52bcebfa844a190d675f8f407b39c963f6edc4a73a1dd6446676f`，run2 `28c9d658134b3fad0b8704fca0f285d51f21041ffd273b197a5958dfe1f97beb`

差异原因未追溯到源码级 STEP header/实体序列化细节；因此重复性结论是**几何/拓扑指标稳定，文件字节哈希不稳定**。后续验证应比较参数、实体数、validity、bbox、体积及归一化拓扑/网格摘要，不要求 STEP 字节相同。

## 产物摘要

完整 STEP 和环境留在 ignored `work/benchcad-output/`；仓库只保存此摘要、manifest 草案和相对路径。未下载 Public/Core 或其他受限评测数据。
