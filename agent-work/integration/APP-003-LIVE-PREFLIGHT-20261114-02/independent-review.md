# APP-003-LIVE-PREFLIGHT-20261114-02 — 独立复核

- 日期：2026-11-14
- 复核者：Codex 中枢
- 结论：`pass`（限于授权范围、执行证据和安全边界）
- 复核基线：`main`，HEAD `663ca56`；复核开始时工作区干净，本地 `main` ahead `origin/main` 17 commits。
- 批次：`app003-product-live-20261114-02`；批次目录保持只读。

## 复核结论

批准记录、正式 preflight、execution report、batch summary、budget ledger 和冻结输入范围一致。执行了四条冻结输入，每条一次 DeepSeek `/chat/completions` 请求，共 4/12 次；ledger 的四次 attempt 均标记为成功 model call。Summary 与执行报告的 run 集、状态和 raw hash 一致。P1 为 `answer → needs_confirmation`；P2 为 `ask → blocked`；P3、P4 为 `refuse → blocked`。未提交 P1 的 per-run 参数确认，因此未调用 CAD pipeline，未生成 STEP。

四个 raw 文件只核对存在性、字节数及 SHA-256，没有读取或输出正文；均与 summary 中对应的 `raw_sha256` 相符，路径为仓库内相对路径。冻结 `model-inputs.json`、`evaluator-labels.json`（只计算 hash，不解析标签）和 v5 prompt 文件的 SHA-256 均与批准记录一致。Summary 不含 raw 正文、绝对路径、STEP 路径或 evaluator 标签内容；approval 中仅保存 evaluator-labels hash。`FORMAL_EVALUATION_ALLOWED=False` 保持不变。

## 复核依据

- Batch ID、profile、输入 hash、labels hash、prompt hash、provider/model、condition、12 次 HTTP 上限与批准记录/summary 一致。
- Summary、ledger 与执行报告均覆盖相同四个 logical run；每 run 一次请求，账本总计 4/12。
- 四个 raw 文件均存在，实际 SHA-256 与 summary 元数据逐一匹配。
- `pipeline_directory_count=0`；所有 run 的 `step_path` 和 `pipeline_run_dir` 均为 `null`；执行报告记载 CAD 未调用、STEP 未创建。
- 报告、summary、ledger 未发现 API key 值、Authorization header 或 raw 正文。宽泛 `sk-` 文本扫描会误命中 `DeepSeek` 字符串；逐字段结构核对未发现凭据字段或正文内容。
- 冻结输入、标签文件和 prompt 的 SHA-256 分别匹配批准值；未解析 evaluator 标签内容。
- `git diff --check` 在本次文档改动前通过；复核期间没有运行模型请求、CAD、测试 runner 或历史批次。

## 范围与限制

本结论确认凭据入口修复后 provider transport 可达，并且本 batch 的四个响应被 runner 成功接收和分类；不判断 P1–P4 输出的语义正确性，不构成广泛语言质量评测。为遵守 raw 隔离要求，没有读取 raw 正文，因此没有独立核验 provider 响应正文中的 runtime-returned model 字段。没有重跑或追加本批请求，也未读取密钥、`.env` 或 Authorization header。

负责人随后明确接受 P1 的 `bore_d=24` 并批准该 run 的本地 CAD pipeline。确认结果写入独立目录 `work/product-live-runs/app003-product-live-20261114-02-P1-24mm-confirmation/`；原 live batch 继续只读，未追加 HTTP 或改写 batch summary/ledger/raw。

## 后续 per-run 审阅准备（2026-11-14）

为准备下一道确认门，读取了 P1 raw envelope 的**白名单字段**；没有输出或保存 provider 正文、凭据或 Authorization。P1 envelope 结果为：`decision=answer`，`extracted_parameters={"bore_d": 24}`，`missing_fields=[]`，`unsupported_requests=[]`，`questions=[]`，`prompt_version=app001-extraction.v5`，`contract_version=app001-io.v1`。Summary 未包含这些参数，因此该字段核对需要读取 P1 raw。

确认调用了唯一的 `confirm_product_live_run()` CAD 路径；没有追加 HTTP。P1 confirmation 使用 `bore_d=24`，Schema 校验通过后生成 STEP，目录派生值和规则派生值由确定性 CAD 链补齐。

结果：`product_status=succeeded`、`pipeline_status=success`、`pipeline_stage=step_readback`；native geometry `is_valid=true`、`solids=1`、`faces=35`、`edges=73`、`vertices=38`、`volume_mm3=12513.344684954385`；STEP 148393 bytes，SHA-256 `9884f733f4c07a0408526b37fac391b68140a0fe3b2610570ff1ba8fc00d1486`。`CAD-006.geometry-comparison.v1` 的 native→STEP 回读比较通过，hard mismatches 为空。

## handoff_successor_check

```text
predecessor=APP-003-LIVE-PREFLIGHT-20261114-02; checkpoint.md; execution-report.json; batch app003-product-live-20261114-02
files_format=pass; scope, approvals, preflight, report, summary, ledger and four raw files exist
core_rerun=read-only artifact/hash consistency checks; no runner or network rerun
normal_case=P1 answer -> needs_confirmation; raw file exists and hash matches; no CAD/STEP
failure_case=P2 ask -> blocked; P3/P4 refuse -> blocked; each has one successful HTTP attempt and matching raw hash
interface=pass; four frozen IDs and logical run IDs match approval, summary, ledger and execution report
limits=reviewed; initial batch review was raw-free; a later, explicitly scoped P1 parameter review read only the envelope whitelist fields described above; no secret, evaluator label content, old batch, CAD or network operation accessed
result=pass_with_scoped_parameter_read; P1 confirmation was subsequently approved and its local CAD/STEP artifacts were verified
blocking_issue=none for this scoped review; further live samples require a separate scope, preflight, batch ID and approval
```
