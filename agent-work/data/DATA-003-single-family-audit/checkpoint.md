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
