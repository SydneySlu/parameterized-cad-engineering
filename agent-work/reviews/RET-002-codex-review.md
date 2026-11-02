# RET-002 Codex 中枢审查

- 日期：2026-11-03
- 任务：RET-002
- 审查提交：`cc8ad9c`、`1753d7d`、`53b4fc9`
- 状态：`review`
- 结论：核心基线证据通过，但存在一个需要修正的策略契约问题，暂不标记 `done`，暂不放行 RET-003。

## 审查范围

审查了 `src/retrieval/**`、`tests/retrieval/**`、
`agent-work/integration/RET-002-retrieval-baseline/**`、RET-001 manifest 交接记录和
相关工作日志。确认 RET-002 没有修改 Schema、Typed CAD IR、CAD 编译器/验证器、CAD-006
容差策略或 RET-001 manifest，也没有读取或提交 STEP、渲染图和第三方图纸。

## 独立验证

以下命令在项目根目录重新运行：

```text
tests/retrieval: 24 passed
run_smoke.py: 3 个正常/边界案例通过，13/13 失败案例按预期拒绝，70 项检查通过
RET-001 verify_manifest.py --tracked-only: 660 checks passed, 0 failures
tests/schema: 17 passed
tests/typed_cad_ir: 5 passed
tests/cad_compilation: 13 passed
py_compile: passed
git diff --check: passed
```

复核确认：

- `bore_d=20` 正常查询返回 `catalog-bore-020`，距离为 0；
- `bore_d=18` 行间 flat 查询标记为 `out_of_catalog_or_unvalidated`；
- `bore_d=80` / `second_screw=1` 的 held-out 行没有进入候选，候选角色全部为
  `retrieval_source`；
- 缺字段、未知字段、未知族、非有限值、非法 `top_k`、空/未知候选角色和重复候选均返回
  结构化 `RetrievalError`；
- 进程内重复和两个独立进程复放得到逐字一致的 canonical JSON；
- `provisional_small_n`、15 条 manifest、3 条候选、manifest hash、许可证和单环境限制均在
  结果和报告中保留。

复核命令会改写带时间字段的运行报告，审查后已恢复
`agent-work/data/RET-001-retrieval-manifest/verification-report.json` 和
`agent-work/integration/RET-002-retrieval-baseline/smoke-report.json`，工作树无运行噪声。

## 必须修正的问题

`RetrievalIndex.from_manifest(..., policy=...)` 接受自定义 `DistancePolicy`，而
`DistancePolicy.validate()` 只检查字段集合、有限性和权重，没有检查连续字段范围必须等于冻结的
15 行 GN 705 目录范围。实际复核中，替换 `bore_d` 范围为 `(0, 1)` 仍能成功创建索引；输出却继续标记
`policy_id=RET-002.parametric_distance.v1`。这会让调用方在不改变 policy id 的情况下改变距离语义，
破坏“固定范围/固定策略”和结果可追溯性。

修正要求：

1. 让 `DistancePolicy.validate()` 拒绝任何与 `catalog_ranges()` 不一致的范围，或移除这个可改变策略的
   公共覆盖入口；
2. 增加一个回归测试，证明自定义范围以结构化配置错误拒绝；
3. 保持现有正常查询、排序、候选角色边界、manifest hash 和所有数据/许可证限制不变；
4. 修正后重新运行 RET-002 单元测试和 smoke，并提交新的修正 checkpoint，状态仍为 `review`，由中枢
   再复核。

配置文件中 `weights.total_formula` 和 `tiebreak` 的文字字段目前由实现侧固定输出，加载器未单独校验这两个
描述字符串；这不是当前放行的主要阻塞项，但后续可在策略版本化时补充。

## 保留限制

- 只覆盖 `set_screw_shaft_collar` 的 15 条真实目录行，候选只有 3 条；
- `split_status=provisional_small_n`，不是正式 benchmark；
- 距离是参数近邻度，不代表几何等价、制造可行性、强度安全或生成质量；
- 只验证 Python 3.11.18 / macOS arm64 / CadQuery 2.3.0 / OCP 7.9.3.0；
- `reproducibility_partial`、`MERGED`/非 `release-qualified`、`license_scope_uncertain`、
  `revolved_ring_approximation` 和 `helical_thread_supported=false` 继续有效；
- 不读取 STEP/渲染物，不下载 BenchCAD Public/Core，不扩展第二族。

## 审查决定

RET-002 的主体实现和验证证据满足任务目标，但在策略可变性修正前保持 `review`。修正完成并通过
中枢复核后，才能把 RET-002 标记为 `done`，再决定是否启动 RET-003。
