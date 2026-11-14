# APP-003-LIVE-PREFLIGHT-20261114-02 — Checkpoint

- 日期：2026-11-14
- 状态：`done`（live batch 独立复核通过；P1 per-run confirmation 产物核验和负责人 FreeCAD 目视检查完成；文档已收束）
- 基线：`main=711b4d3`；工作区开始时 clean；本地 main ahead origin/main 13 commits
- batch：`app003-product-live-20261114-02`
- 前置：credential entry fix `df3f7b4` 独立复核 `pass`；未验证 provider 权限

## 已完成

- 选择新 batch ID `app003-product-live-20261114-02`，不复用 2026-11-13 或 2026-11-14-01 的任何预算/证据。
- 由于 profile `app003-product-live.v1` 将四条输入和 12 次上限硬编码，维持四条冻结输入、DeepSeek `deepseek-flash` / C0、最多 12 HTTP；未改代码或授权 profile。
- 固定 CAD venv Python 3.11.18 离线 preflight：`ok=true`、无 errors；CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0、Draft 2020-12 均通过；dry-run planned=4、results=0；candidate directory absent before/after。
- 离线 preflight 不读取凭据；网络请求=0；正式 batch/ledger=0。
- 新建 `scope.md`、`approval-template.md` 和 `offline-preflight.json`；负责人已批准 formal preflight 和 live execution。

## Gate / 下一步

Formal preflight 已通过；负责人随后明确批准本 batch 的真实 DeepSeek 请求。请求已执行 4 次（4/12）；batch 及证据保持只读，不重跑、不追加。

## handoff_self_check

```text
changed=APP-003-LIVE-PREFLIGHT-20261114-02/scope.md,approval-template.md,offline-preflight.json,checkpoint.md; docs/PROJECT_STATUS.md,PROJECT_PLAN.md,TASKS.md,WORKLOG.md
commands=CAD venv Python 3.11.18 run_product_offline_preflight(require_cad_runtime=True): ok; run_product_batch(dry_run=True): preflight_ok, planned=4, results=0; git diff --check
confirmed=batch dir absent; network=0; secrets read=0; formal batch/ledger=0; FORMAL_EVALUATION_ALLOWED=False
unresolved=独立复核 live evidence 与解释边界；provider 已响应但产品效果样本仍仅四条
next_agent_focus=独立复核脱敏 summary/ledger/report；如继续 P1 构造，需单独确认抽取参数并走 per-run confirmation
```


## Formal preflight 结果（2026-11-14）

- 负责人批准：`Wang sikai`，`approved_at_utc=2026-11-13T18:22:54Z`；引用：`Codex conversation — APP-003-LIVE-PREFLIGHT-20261114-02, user message dated 2026-11-14`。批准内容仅覆盖该 batch 的 formal preflight，不授权发送 provider 请求。
- `ProductLiveFormalApproval`（`is_test_only=False`）与同 batch `ProductLiveAuthorization` binding：`pass`。
- 固定 CAD venv Python 3.11.18 下 `run_product_offline_preflight(require_cad_runtime=True)`：`ok=true`，errors 为空；Draft 2020-12、CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0 通过；12 HTTP 预算可行；候选 batch 目录不存在。
- 网络请求：0；未读取 `.env`/API key；未创建正式 batch、BudgetLedger 或 transport；未运行 CAD；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 证据：`formal-preflight.json`。真实 DeepSeek 请求仍需单独、明确的 live execution approval。

### formal_preflight_handoff

```text
changed=formal-preflight.json,checkpoint.md,PROJECT_STATUS/PLAN/TASKS/WORKLOG
commands=ProductLiveFormalApproval binding pass; fixed CAD venv run_product_offline_preflight(require_cad_runtime=True) ok=true; batch_dir_exists=false
confirmed=network=0; secrets_read=false; formal_batch_created=false; live_execution_authorized=false
unresolved=provider account/key acceptance remains unverified
next_agent_focus=await explicit live execution approval for app003-product-live-20261114-02; then execute only this new batch
```


## Live execution 结果（2026-11-14）

- 负责人明确批准执行 `app003-product-live-20261114-02` 的真实 DeepSeek 请求；批准人 `Wang sikai`，批准时间 `2026-11-13T18:28:31Z`，记录引用 `Codex conversation — APP-003-LIVE-PREFLIGHT-20261114-02, user message dated 2026-11-14`。
- 执行结果：batch summary=`complete`；4/4 planned runs 完成；预算账本 4/12，四次均为成功 transport（每 run 一次）；raw 文件 4 个，summary finalize error=None。
- 脱敏 run 结果：
  - `P1-24mm`：`answer` → `needs_confirmation`，1 次 HTTP；没有 per-run 确认，未调用 CAD。
  - `P2-ask-bore`：`ask` → `blocked`，1 次 HTTP。
  - `P3-catalog-conflict`：`refuse` → `blocked`，1 次 HTTP。
  - `P4-unsupported`：`refuse` → `blocked`，1 次 HTTP。
- CAD pipeline 未调用，STEP/pipeline 产物为 0。没有读取 raw 正文来生成报告，没有输出 key 或 Authorization header；旧 batch 未修改/重跑；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 证据：`execution-report.json`；原始 batch summary、ledger 与 raw 证据留在 `work/app001-runs/app003-product-live-20261114-02/`，此后只读，不追加请求。
- 结论边界：真实 transport 已成功到达 provider，credential entry 阻塞解除。四条刺激中一条 answer、 一条 ask、两条 refuse；需独立复核并结合安全输出审阅。不得将本批次描述为 STEP 整链成功或广泛语言质量评测。

### execution_handoff

```text
changed=execution-report.json,checkpoint.md,PROJECT_STATUS/PLAN/TASKS/WORKLOG
commands=formal run_product_batch(dry_run=False, transport=None): 4 runs; ledger 4/12; summary complete; raw metadata only inspected; git diff --check
confirmed=P1 needs_confirmation; P2 ask blocked; P3/P4 refuse blocked; no CAD/STEP; old batches untouched
unresolved=independent review of live evidence and interpretation; no product confirmation submitted for P1
next_agent_focus=independently review sanitized summary/ledger/report and request/response hashes without opening raw bodies; decide separately whether user wants to confirm P1 parameters and invoke CAD, which requires explicit per-run confirmation
```

## 独立复核结果（2026-11-14）

- Codex 中枢只读复核结论：`pass`，限于本批授权、执行证据和安全边界；完整记录见 [`independent-review.md`](independent-review.md)。
- Batch summary、ledger、execution report、approval scope 与冻结 inputs/prompt/labels hashes 一致；4 次请求均成功记账，每个 run 一次，总计 4/12。
- 四个 raw 文件仅核验存在性、大小与 SHA-256，hash 全部匹配；未读取正文或 labels 内容，也未读取密钥/`.env`。
- P1=`answer → needs_confirmation`；P2=`ask → blocked`；P3/P4=`refuse → blocked`。CAD pipeline 与 STEP 产物均为 0；`FORMAL_EVALUATION_ALLOWED=False`。
- 限制：未评价四条响应的语义正确性，未检查 raw 内 provider-returned model 字段；不构成广泛语言质量结论。Batch 只读。若继续 P1 构造，需负责人单独审阅参数并确认该 run。

## P1 per-run confirmation（2026-11-14）

- 负责人明确接受 `P1-24mm` 的 envelope 参数 `bore_d=24`，批准该 run 进入本地 CAD pipeline；没有追加 DeepSeek HTTP。
- 确认目录：`work/product-live-runs/app003-product-live-20261114-02-P1-24mm-confirmation/`；原 batch `work/app001-runs/app003-product-live-20261114-02/` 未修改。
- 结果：`succeeded` / `success` / `step_readback`；native geometry valid，1 solid、35 faces、73 edges、38 vertices；STEP 148393 bytes。
- STEP SHA-256：`9884f733f4c07a0408526b37fac391b68140a0fe3b2610570ff1ba8fc00d1486`；native→STEP `CAD-006.geometry-comparison.v1` 回读比较通过，hard mismatches 为空。
- 限制：该证据是单次、已确认的 P1 产品 run；不改变原 batch 的 4/12 HTTP 统计，也不扩大模型质量结论。
- 负责人已使用 FreeCAD 检查该 STEP 文件并确认无问题；此为目视验收记录，不扩大几何验证或制造认证结论。

### 中枢 P1 产物核验（2026-11-14）

- 只读检查独立 confirmation run 的 `summary.json`、`schema_result.json`、`compilation_result.json`、`index.json` 和 STEP 文件；未重跑 pipeline、未调用网络、未读取 `.env`/密钥或原 live raw 正文。
- Schema：`validation_ok=true`、errors 为空；normalized parameters 为 `bore_d=24`、catalog-derived `outer_d=40/screw_d=8/screw_len=12/width=16`、rule-derived `second_screw=0`。
- Compiler：`ok=true`、`status=step_readback`；manifest validation `ok=true`；native 和 STEP readback 均为 valid、1 solid/35 faces/73 edges/38 vertices。`CAD-006.geometry-comparison.v1` comparison `pass=true`，`hard_mismatches=[]`。
- 实际 STEP 文件大小 148393 bytes，实际 SHA-256 与 `index.json` 一致：`9884f733f4c07a0408526b37fac391b68140a0fe3b2610570ff1ba8fc00d1486`。`summary.json` 状态为 `success`、stage 为 `step_readback`、errors 为空。
- 对原 live batch 仅核对文件计数：raw 响应 4 个、STEP 0 个；budget ledger 仍为 4 次 HTTP。原 batch 继续只读，P1 的 STEP 保存在独立 confirmation 目录。
- 结论边界：P1 单例的抽取参数经负责人确认后可通过现有 Schema/CAD/STEP 链；不代表其他输入正确，也不构成广泛语言质量、制造认证或产品发布结论。

```text
handoff_successor_check:
  p1_artifacts=pass; schema validation, compiler summary, native/readback geometry, STEP size and SHA-256 agree
  live_batch=read_only; 4 raw files, 4/12 budget attempts, 0 STEP files
  network_or_secrets=none; no runner rerun, HTTP, .env or key access
  limits=single user-confirmed P1 local CAD result; no broad language-quality claim
  visual_review=project owner inspected the P1 STEP in FreeCAD and accepted it
  next=any additional live sample requires a separate scope, preflight, batch ID and approval
```
