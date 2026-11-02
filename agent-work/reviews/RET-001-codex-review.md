# RET-001 Codex 中枢独立审查

日期：2026-11-02
任务：RET-001 单族检索样本 manifest v0
审查范围：提交 `71125d2`、`d03e427` 及本次一致性修正

## 结论

RET-001 通过中枢审查，可以作为 RET-002/RET-003 的单族样本清单与构造证据。任务范围仍是单族 15 个冻结目录行；`split_status=provisional_small_n` 不构成正式 benchmark 切分，生成 STEP 继续受 `license_scope_uncertain` 限制。

## 独立验证

固定环境：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4、macOS arm64。

```text
verify_manifest.py                         15 records / 825 checks / 0 failures
verify_manifest.py --tracked-only          15 records / 660 checks / 0 failures
replay_check.py                            bore-020 PASS; bore-080 PASS;
                                           tampered_radial_offset PASS;
                                           catalog_mismatch PASS;
                                           normal native_match/readback PASS;
                                           STEP byte hash differs as permitted
CAD compiler tests                          13 PASS
Schema tests                                17 PASS
```

抽查确认：

- `catalog-bore-020` 是正常检索样本，单 solid、单 shell、有效实体，STEP 回读通过；
- `catalog-bore-080` 是包含 `second_screw=1` 的边界样本，构造与回读通过；
- `radial_offset=100 mm` 在 semantic 阶段以 `IR_NODE_INPUT_KIND_MISMATCH` 拒绝，并定位到 `n2.hole.primary`；
- `outer_d=33` 与 `bore_d=20` 的目录耦合错误在 schema 阶段以 `CATALOG_MISMATCH` 拒绝；
- 15 个 `family_id + catalog row` 分组不跨 split，split 仍明确标记为临时小样本分组。

## 中枢修正

冻结 IR 示例 `agent-work/typed-cad-ir/IR-001-v0/examples/legal-catalog-row.json` 原先仍使用已被 ADR-0008 取代的 `CAD-006.pending.v0`。已更新为 `CAD-006.geometry-comparison.v1`，并重新生成 manifest/report；生成器、15 个 IR 和验证结果保持通过。

## 不构成阻塞的限制

- 仅覆盖 `set_screw_shaft_collar` 的 15 个目录行；不声称跨族泛化或大规模 benchmark；
- 9/3/3 split 仅为可复算的 provisional grouping，RET-003 决定正式评测切分或不切分；
- 只在固定 macOS arm64 软件环境验证，未声明跨平台、跨进程或其他 STEP writer 一致性；
- BenchCAD 快照是 `reproducibility_partial`，族状态为 `MERGED` 而非 `release-qualified`；
- 生成 STEP/渲染产物保持 `license_scope_uncertain`，仅放在 ignored 工作目录，不提交或再发布；
- 螺纹仍为 `revolved_ring_approximation`，STEP 通过不代表制造或工程强度验证。

## 审查状态

RET-001：`done`（本地 main 已包含执行提交和中枢审查提交，等待项目负责人 push）。下一步是 RET-002/RET-003；不得把当前 provisional split 直接当作最终评测集。
