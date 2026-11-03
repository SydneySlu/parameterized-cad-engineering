# RET-003 Codex 中枢审查

- 日期：2026-11-03
- 任务：RET-003
- 审查范围：里程碑 1 协议草案与查询集
- 审查提交：`810221f`、`8fef7fa`、`88c85d6`、`757679e`
- 状态：`review`
- 结论：里程碑 1 的交接、文件格式和数据隔离证据通过；里程碑 2 暂不放行，需先修正 C2 基线的公平性和信息边界。

## 独立复核

在项目根目录重新执行：

```text
RET-001 verify_manifest.py --tracked-only: 15 records / 660 checks / 0 failures
RET-002 retrieval tests: 30 passed
RET-002 run_smoke.py: 3 normal/boundary cases passed; 13/13 failures expected;
                       in-process/cross-process determinism passed
query-set-draft.json: valid JSON; 6/6 manifest references and roles matched
git diff --check: passed
```

运行产生的带时间戳报告已恢复，工作树保持干净，`main` 与 `origin/main` 同步。

已确认：

- `query-set-draft.json` 的 3 个主查询均引用既有 `heldout_evaluation` 记录；参数不复制到查询集；
- `catalog-bore-080` 只作为 held-out 查询真值，不进入 RET-002 的 `retrieval_source` 候选；
- 正常查询、held-out 边界查询和结构化缺字段失败案例均有复核证据；
- manifest hash、RET-002 policy、15 条记录、3 条候选和 `provisional_small_n` 均被保留；
- 未读取 STEP、渲染图、IR 文件、第三方图纸或 BenchCAD Public/Core；未运行未经放行的三条件正式对照；
- 协议正确将 APP-001 缺失时的端到端字段、Schema、CAD、STEP 指标标记为 `not_measured`。

## 必须修正的问题

### C2 不是当前定义下的公平人工模板基线

协议的 C2 `manual_template_rule_v0_proposed` 使用现有 CAD-003 Schema 的 `bore_d` →
`CATALOG_ROWS` 精确映射，并用 `second_screw_threshold` 派生字段。当前
`src/schema/set_screw_shaft_collar.py` 的 `CATALOG_ROWS` 是完整 15 行表，包含作为
held-out 查询的 `bore_d=12/35/80`。因此 C2 可以通过 `bore_d` 直接查出 held-out 的精确
`outer_d/screw_d/screw_len/width`，即使文字上没有读取 held-out manifest，也间接使用了
评测真值。它应被视为**目录规则 oracle / 上界诊断**，不能作为与 C0、C1 并列的公平无检索
基线，也不能据此声称检索带来收益。

里程碑 2 放行前必须二选一并写入新版本协议：

1. 将现有 C2 改名为 `catalog_rule_oracle`，单独报告为上界/诊断，不纳入公平三条件主表；
   或
2. 定义一个不读取完整 `CATALOG_ROWS`、不访问 held-out 真值的公平 C2，例如只提供固定
   输出骨架和输入字段的人工模板；若无法定义有意义且信息等价的规则基线，则明确取消
   C2 端到端比较，只保留 C1 检索级诊断并等待 APP-001。

不能通过措辞把当前 C2 同时称为公平基线和 oracle。新协议必须写清每个条件收到的相同输入、
可用先验、是否允许目录查表、是否允许 Schema 派生，以及 held-out 的访问边界。

### 输入契约仍需进一步冻结

C0 描述为收到“同一查询文本/结构化输入”，C2 则描述为使用固定族、六字段骨架和
`bore_d` 规则。里程碑 2 前应明确三条件是否使用同一个冻结输入 payload；如果输入不等价，
只能做分层诊断，不能把结果放在同一收益表中。

## 已通过但需持续保留的限制

- 只有 `set_screw_shaft_collar` 单族、15 条真实目录行和 3 条 `retrieval_source` 候选；
- `split_status=provisional_small_n`，3 个 held-out 结果只能逐例描述，不是正式 benchmark；
- RET-002 距离只表示参数近邻度，不代表几何等价、制造可行性、强度安全或生成质量；
- 当前没有固定 APP-001 模型、Prompt、自然语言输入集和统一下游求解器，端到端指标必须保持
  `not_measured`；
- `reproducibility_partial`、`MERGED`/非 `release-qualified`、`license_scope_uncertain`、
  `revolved_ring_approximation`、`helical_thread_supported=false` 和单 macOS arm64 环境限制继续有效；
- 不读取或公开 STEP、渲染物、第三方图纸，不下载 BenchCAD Public/Core，不扩展第二族。

## 审查决定

RET-003 里程碑 1 文档质量和交接证据通过，但任务保持 `review`。在 C2 的公平性/上界身份和
三条件输入契约修正并经中枢复核前，不创建或运行里程碑 2 正式评测，不调 RET-002 权重，
不把当前协议写成检索收益结论。

## 修订复审（2026-11-03）

- 审查提交：`e3f6a61`（协议修订）、`7401a94`（修订状态记录）。
- 独立验证：RET-002 检索测试 30/30 通过；`query-set-draft.json` 可解析；6 个主/诊断/失败引用均存在于 RET-001 manifest 且声明角色匹配；`git diff --check` 通过。
- 查询集与基线：`git diff 810221f..e3f6a61 -- .../query-set-draft.json` 无差异；3 个主查询仍是 held-out，仅用作逐例真值；RET-002 候选仍限定为 `retrieval_source`。
- 公平性判断：接受 `C2O: catalog_rule_oracle_v0` 降级身份。完整 `CATALOG_ROWS` 具有 held-out 对应目录值，故 C2O 只能作为单独标注的 oracle/上界诊断，不进入公平主比较、不调权重、不作为 Prompt 示例。当前没有公平 C2。
- 输入和系统边界：接受共同输入 payload、条件额外上下文及系统共有后处理链的区分。APP-001 未完成前，只放行 C1 检索级诊断；C0/C1 端到端字段、Schema、CAD、STEP 和成本指标保持 `not_measured`。本复审不批准敏感性调参或 C2O 实际运行，也不等于放行正式三条件对照。
- 文档修整：checkpoint 的“新增 query-set”与“查询集不变”表述冲突。根据提交差异确认查询集未改，已将该句改为“沿用原有 query-set”；不改变查询清单内容。
- 结论：RET-003 里程碑 1 协议通过；RET-003 总任务继续进行，状态转为 `in_progress`，下一步可按已冻结协议运行 C1 检索级诊断。正式端到端比较须等 APP-001 和新的中枢放行。`provisional_small_n` 等数据限制继续有效。

