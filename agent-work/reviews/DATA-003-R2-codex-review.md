# DATA-003-R2 Codex 中枢独立审查记录

日期：2026-11-02
审查对象：`c3ac4c6`（DATA-003-R2 主交付）和 `5fc9ef4`（提交记录校正）
审查范围：`set_screw_shaft_collar` 的固定来源、快照证据、许可证边界和交接记录

## 结论

DATA-003-R2 通过审查，可以将 DATA-003 数据审计任务标记为 `done`。这里的 `done` 表示来源、环境、运行、快照限制和许可证边界已经记录完整，不表示 BenchCAD 族已经 `release-qualified`，也不表示项目生成的 STEP/渲染物已经获得公开再发布许可。

## 独立验证

- `minimal-manifest.json` 可由 `python3 -m json.tool` 解析。
- `SNAPSHOT-MANIFEST.json` 记录固定 commit 的 217 个文件，下载 217、缺失 0；固定族 `family.json` 存在且 ID 与目录一致。
- `work/benchcad-source/benchcad-2-035f467-raw.tar` 的 `tar -tf` 条目数为 256，SHA-256 为 `b390bc953416cfcf27b94b4ec1f497a0ba0ee5f3afb04c4b8454c411fc3c33ad`，与记录一致。清单中的 217 个 commit blob 与 tar 条目数是不同统计口径，不能混写。
- 在 raw 快照实际根目录运行 `work/benchcad-output/venv/bin/bench2 validate set_screw_shaft_collar --seeds 1`，结果为 `PASS`。
- 原 promisor checkout 仍有 staged deletions，并缺失 README 和族 `part.py`；复核确认它不能作为干净 checkout。
- `python3 scripts/check_project_state.py` 通过，项目任务 ID 一致。
- `git diff --check origin/main..HEAD` 通过；工作树无未提交改动。

## 逐项判断

1. **来源和范围**：固定仓库 URL、commit、族路径、`family_id`、`build()` 和 `check()` 均与 ADR-0007 和当前项目状态一致。
2. **快照**：API/raw 重建覆盖 217/217 个 commit blob，具备逐文件 blob 和 SHA-256 证据，可用于当前审计和本地 smoke；由于不是完整 Git checkout 或官方 `git archive`，继续标记 `reproducibility_partial`。
3. **许可证**：矩阵正确区分 MIT 源码/designs、单独说明的 CC BY 4.0 released dataset artifacts、项目自行生成 CAD 的 `license_scope_uncertain`、NOTES 中未随仓库分发的第三方材料，以及未下载的 Public/Core。没有把任何不确定项写成可公开发布。
4. **交接**：checkpoint 同时记录了 successor check、self check、正常案例、失败/不完整快照案例、命令和剩余问题，满足高风险数据交接要求。

## 仍然保留的限制

- 网络或完整对象可用后，仍应尝试建立真正的 clean checkout 或官方 archive；成功前不能提高快照状态。
- 在 BenchCAD 上游明确许可前，STEP、渲染图、网格和 NOTES 引用的 JW Winco 图纸/SVG/照片只限本地审计，不进入公开交付、训练或检索语料。
- 固定 commit 的族状态是 `MERGED`，不是 `release-qualified`。
- 几何数值容差仍由 CAD-006 前置测量决定，DATA-003 不冻结该阈值。

## 放行判断

DATA-003 可交给 CAD-005/006 和后续单族 manifest 工作使用，但下游必须继续携带 `source_commit`、`source_snapshot=reproducibility_partial` 和 `license_scope_uncertain`，不得把审计草案升级为正式发布许可或完整复现声明。
