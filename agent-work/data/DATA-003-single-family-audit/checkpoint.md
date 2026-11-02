# DATA-003 checkpoint

更新时间：2026-11-01  
完成比例：约 90%（来源/候选/环境/单族 smoke 已完成；待中枢审查并决定是否补做第二族完整 STEP smoke）

## 已验证

- 已阅读项目协作、状态、计划、任务、决策、数据库计划和 DATA-003 工作区说明。
- 已固定 BenchCAD `main` commit `035f467142888edfd0bd7cd73906f9b155c8f43c`，记录 remote；确认三个候选族真实存在、文件齐全、family.json 与状态信息。
- 已核对仓库 README、pyproject、LICENSE、STATUS；记录官方 CLI、Python API、MIT/CC-BY 分层与不确定范围。
- 已在 macOS arm64 隔离 Python 3.11.18 环境安装声明的 CadQuery/OCP/Numpy 版本；三个候选官方 `bench2 validate --seeds 1` 均 PASS。
- 已对 `set_screw_shaft_collar` 完成合法目录行、合法 hard 边界、参数约束非法、几何非法四类 smoke；均记录 build/check/实体/有效性/STEP 导出和回读。
- 已重复合法案例两次：几何指标稳定，STEP 文件哈希不同；已记录差异和解释限制。
- 已保存最小 manifest 草案；标记为审计材料，不是生产 Schema/Typed CAD IR。

## 剩余范围与风险

- `slotted_din_rail` 和 `speaker_pole_mount_socket` 已完成官方 validate，但尚未做同等完整的项目侧 STEP 回读表。
- `set_screw_shaft_collar` 的非法输入被 `check()` 拒绝但原生 build 仍能构造；其中 `outer_d < bore_d` 产生 3 solids，属于验证风险。
- STEP 字节哈希不稳定，不能用字节哈希作为唯一重复性标准。
- 族状态仅到 MERGED；无 release-qualified 证据；生成/派生资产及 NOTES 中第三方材料许可证需中枢复核，当前写 `status_uncertain`/`license_scope_uncertain`。
- 初次网络 clone 的 sparse/promisor checkout 在 index-pack 阶段长时间未完成并留下不完整工作树；审计使用同 commit 的 raw 源码快照，二者都在 ignored `work/`，未进入 Git。

## 下一步

1. Codex 中枢审查来源、LICENSE 分层、STATUS 解释和 smoke 风险。
2. 如需 DATA-002 的“双族端到端”门，沿相同方法补做 `slotted_din_rail` 或 `speaker_pole_mount_socket` 的完整 STEP 表。
3. 只有中枢审查并决定族范围后，才把草案字段交给 Schema/Typed CAD IR 任务；本任务不冻结接口或族选择。

## DATA-003-R1 补充 checkpoint

- 已确认原有 promisor checkout 不是干净完整工作树，不能用于可复现归档。
- `git archive` 因缺 blob 生成 0 字节无效结果；GitHub codeload 在当前网络多次截断。
- 已从固定 commit 的递归 tree/raw blob 建立 217/217 文件的 API/raw 快照，记录每个 blob SHA、文件 SHA-256 和 tar SHA-256；状态明确为 `reproducibility_partial`。
- 已对 `legal_catalog_row` 和 `legal_hard_boundary` 的两次 STEP 回读计算 solids、shells、faces、edges、vertices、有效性、体积、包围盒、量化排序面面积摘要和边长摘要。
- 两个案例的 STEP 字节哈希仍不同，但上述几何/实体指标和归一化面/边摘要均一致；结论限定为“几何/实体级指标稳定，拓扑等价尚未完全证明”。
- 剩余范围：中枢复核 raw 快照是否足以满足复现门；网络恢复后优先建立真正 clean checkout/git archive。未修改正式状态、任务表或 ADR。

## DATA-003-R2 来源、快照与许可证边界复核

完成日期：2026-11-02。首族按项目 ADR-0007 / 当前 `docs/PROJECT_STATUS.md` 固定为 `set_screw_shaft_collar`；本补充不重新选择族，不修改正式状态、任务表或决策记录。

```text
task=DATA-003-R2
status=review
family_id=set_screw_shaft_collar
source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c
source_snapshot=reproducibility_partial
changed=agent-work/data/DATA-003-single-family-audit/source-audit.md; environment.md; license-matrix.md; minimal-manifest.json; checkpoint.md; docs/WORKLOG.md (append only)
verified=git rev-parse/status confirmed the existing checkout is incomplete at the fixed HEAD; raw-snapshot `bench2 validate set_screw_shaft_collar --seeds 1` PASS; fixed family.json ID/path and build()/check() present; source blob manifest has 217/217 files; tar SHA-256 b390bc953416cfcf27b94b4ec1f497a0ba0ee5f3afb04c4b8454c411fc3c33ad; JSON parse and diff checks run before commit
license_scope=source/design code MIT with notice; official released dataset artifacts separately CC BY 4.0; generated STEP/renderings/meshes and third-party NOTES materials license_scope_uncertain; Public/Core not downloaded or used
confirmed=repository URL, fixed commit, family ID/path, family.json, part.py::build, spec.py::check, source STATUS MERGED and 0 release-qualified; README/LICENSE license split; API/raw snapshot records 217 commit blobs and 0 missing
unresolved=no complete Git checkout or official git archive; upstream clarification needed on whether generated STEP/renderings are distributable and on permissions for referenced JW Winco drawings/SVG/photo; per-file raw snapshot is replayable but not a clean Git snapshot
next=Codex 中枢复核来源、快照和许可证边界
```

### 定向复核与自检

**handoff_successor_check**

- predecessor：DATA-003-R1 checkpoint（本文件上节）；未假定存在 R1 独立 Git commit。
- files_format：现存 manifest 可解析，raw snapshot manifest 记录固定 commit、217 个文件和逐 blob 证据；本轮增加的族许可矩阵为 Markdown 表。
- core_rerun：在 `work/benchcad-source/benchcad-2-035f467-raw/` 运行 `work/benchcad-output/venv/bin/bench2 validate set_screw_shaft_collar --seeds 1`，PASS。
- normal_case：raw snapshot 中 `designs/set_screw_shaft_collar/family.json` 存在且 family 值与固定 ID 一致；`part.py::build()`、`spec.py::check()` 存在。
- failure_case：`work/benchcad-source/benchcad-2` 的 HEAD 是固定 commit，但 `git status` 有大量 staged deletions，README.md 与族 part.py 缺失；不得作为干净 checkout。
- interface：固定输入与 ADR-0007 及当前项目状态页一致；输出仍是审计证据/草案，不建立生产 Schema/Typed CAD IR。
- limits：保留 `reproducibility_partial`、`license_scope_uncertain`、未 release-qualified、Public/Core 未下载的事实。
- result=review
- blocking_issue=当前没有完整 Git checkout/archive；生成 STEP/渲染物和外链第三方材料的再发布许可仍缺少上游明确证据。

**handoff_self_check**

- changed：本 checkpoint、source audit、environment、license matrix、manifest；WORKLOG 仅追加 DATA-003-R2 行。
- commands：核心 validate PASS；固定 commit/status 和不完整 checkout 缺文件复核；raw blob manifest 217/217 检查；tar SHA-256 复核；JSON 与 `git diff --check` 结果以最终提交前检查记录为准。
- confirmed：仓库 URL、commit、族 ID/path、构造和 check 入口、源状态页记录、许可文字边界及 partial 快照证据。
- unresolved：完整 Git 快照失败原因仍未解除；输出几何与 NOTES 外链资料授权未获确认。
- next_agent_focus：Codex 中枢优先审查 API/raw 证据是否够用、MIT/CC BY 范围的解释，以及生成 CAD 和第三方材料的后续允许用途；不得将本任务标记为 release-qualified。

## DATA-003-R2 Codex 中枢独立复审

- 状态：`done`（审计交付完成；外部许可和完整 Git 快照限制保留）。
- 复核：固定族、217/217 raw blob 清单、tar SHA-256、manifest、raw 快照官方 validate 和原 promisor checkout 失败反例均独立复跑；结果见 `agent-work/reviews/DATA-003-R2-codex-review.md`。
- 放行：可以交给单族 manifest、CAD-005/006 和检索样本工作；下游必须继续携带 `reproducibility_partial`、`license_scope_uncertain`、`MERGED`/非 `release-qualified` 限制。
