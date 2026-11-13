# APP-003-LIVE-PREFLIGHT-20261113-01 checkpoint

- 状态：`review`
- 基线：`main=6fe4b43`
- 候选 batch：`app003-product-live-20261113-01`
- 目标：为产品 live smoke 准备独立 scope、预算、冻结输入绑定、固定环境 preflight 和负责人批准模板。
- 已完成：固定 CAD venv Python 3.11.18 下 offline preflight `ok=true`；budget `12/12` 可行；CAD runtime、prompt、contract、inputs hash 均通过；dry-run 规划 4 条 logical run，结果数为 0；随后按批准 scope 执行正式 batch。
- 批准记录：负责人 Wang sikai 已于 `2026-11-13T14:49:33Z` 提供审批身份和时间；`approval-template.md` 记录本批次完整批准声明，引用 `Codex conversation — APP-003-LIVE-PREFLIGHT-20261113-01, user message dated 2026-11-13`。
- 正式执行前 preflight（2026-11-13T15:00:18Z）：用批准模板字段构造 `ProductLiveFormalApproval`；`validate_product_formal_approval_binding()` 通过；固定 CAD venv `run_product_offline_preflight(..., require_cad_runtime=True)` 返回 `ok=true`，无 errors，12/12 预算可行，CAD runtime/prompt 通过，batch 目录不存在。
- 正式运行结果（批次时间 `2026-11-13T16:04:11Z`–`16:04:15Z`）：4 条 HTTP 请求、每条 1 次尝试、账本合计 4/12；P1–P4 均为 `llm_status=error`、`product_status=error`、`PARSE_OR_ENVELOPE_ERROR`，未进入确认、pipeline、IR 或 STEP；summary `batch_status=failed`。
- 证据核对：批次目录 `work/app001-runs/app003-product-live-20261113-01/` 已创建并只读保留；`raw/` 文件数为 0、STEP 文件数为 0；summary 和 ledger 未读取 raw 正文。
- 当前结论：本批次不得重跑或追加请求；失败响应没有 raw retention 元数据，需先做定向解析/失败响应证据修复、离线回归和新的独立复核。

## Codex 中枢复核（2026-11-13）

- 基线核对：`main` 与 `origin/main` 均为 `6fe4b43`；候选批次目录 `work/app001-runs/app003-product-live-20261113-01/` 不存在。
- 固定环境：`work/benchcad-output/venv/bin/python` 为 Python 3.11.18，CadQuery 2.3.0，OCP 7.9.3.0，jsonschema 4.26.0，Draft 2020-12 可用。
- 离线验证：`tests.integration.test_product_live` 99/99；`tests.demo.test_product_live_ui` 36/36；目标文件 `py_compile` 通过；`git diff --check` 通过。
- 入口验证：`run_product_offline_preflight(..., require_cad_runtime=True)` 返回 `ok=true`；`run_product_batch(dry_run=True)` 返回 `preflight_ok=true`、4 条 planned runs、0 条 results、无 summary 写入。
- 复核边界：没有调用 formal runner、DeepSeek/Ollama、外网或 CAD 正式批次；没有读取 `.env`/API key；approval 仍未提供。

### handoff_self_check

- changed: `scope.md`、`approval-template.md`、`preflight-report.json`、`checkpoint.md`，以及项目状态/计划/任务/工作日志的准备阶段记录；未修改产品代码、冻结 prompt、Schema/IR、A2 授权或旧批次。
- commands: 固定 venv 的 Product Live 99 项、Live UI 36 项、`py_compile`、`git diff --check`、CAD runtime offline preflight、dry-run；均通过。
- confirmed: 4 个冻结 input ID、DeepSeek/deepseek-flash/C0、prompt/inputs/labels hash、12 HTTP 上限、CAD 需确认门、批次目录不存在、零网络/零密钥读取。
- unresolved: 四条真实响应均未形成 parse/envelope；失败响应 raw retention 元数据为空，当前不能判断是 provider 响应形态、adapter 解析还是 retention 路径问题；不得用本批次重试补证据。
- next_agent_focus: CC/Codex 先在离线夹具中复现并修复失败响应的 raw retention 与 parse diagnostics，验证零 CAD、summary=`failed` 和不泄露正文；随后以新 batch ID、新 approval 和新 preflight 再决定是否扩大 live。

## 定向失败证据修复（2026-11-14）

- 状态：`review`
- 改动：`src/integration/product_live_runner.py` 新增 `_build_state_from_adapter_result()`，将正式 Adapter 的 transport failure、严格 parse failure 和 envelope validation failure 分开映射；仅保留稳定错误码/字段、尝试次数、HTTP 状态和安全的 raw retention path/hash 元数据，不复制 provider 响应正文。正式路径对有响应但解析失败的结果继续写入 raw retention 证据；无响应时明确记录 `TRANSPORT_ERROR` 及原因，不再误报 `PARSE_OR_ENVELOPE_ERROR`。
- 测试：`tests/integration/test_product_live.py` 新增 3 项 Adapter 结果映射回归，覆盖无响应 transport、invalid JSON 和 envelope validation；固定 CAD venv `test_product_live` 102/102 通过，目标文件 `py_compile` 通过。
- 保持不变量：未读取旧批次 raw 正文，未重跑/追加 `app003-product-live-20261113-01`，未调用网络或密钥；`FORMAL_EVALUATION_ALLOWED=False`、授权/预算/CAD 确认门和历史证据均未改变。
- 尚未完成：独立复核、文档 closeout，以及任何新 batch 的 scope/preflight/审批。旧批次仍只读；修复通过独立复核前不得发起新的 live 请求。

### handoff_self_check

- changed=`src/integration/product_live_runner.py`, `tests/integration/test_product_live.py`
- commands=`work/benchcad-output/venv/bin/python -m py_compile ...` 通过；`work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_live -q` 102/102 通过
- confirmed=transport 与 parse/envelope 错误分型；parse/envelope 失败保留 raw hash/path 元数据但不保留正文；mapper 的正常 envelope 路径复用既有 gate；新增测试验证 provider 正文 marker 不进入错误证据
- unresolved=尚未运行正式新 batch；尚未由独立 Codex 复核；旧 `...-01` 无 raw 文件的历史事实保持不变
- next_agent_focus=核对 mapper 在真实 Adapter 结果中的 stage/attempt 字段，重跑产品 live/UI 与相关回归，确认 summary 只写相对路径/hash，再决定是否准备新 scope

## 定向隔离窄修（2026-11-14）

- 状态：`review`
- 修复：离线 mock/service parser 失败证据只保留稳定 code/stage 与冻结字段白名单；HTTP 顶层 `raw_retention_path` 经过 repo-relative canonical containment/symlink fail-closed 归一化。
- 回归：固定 CAD venv Product Live 107/107、Product Live UI 36/36、C1/C2/C3 183/183、Integration 81/81、Schema 17/17、CAD 13/13；`py_compile` 与 `git diff --check` 通过。
- 证据边界：旧 `app003-product-live-20261113-01` 不重跑、不读取 raw 正文、不追加网络请求；本轮仍未调用 provider 或读取密钥。
- 下一步：独立 Codex 复核本窄修；通过后才讨论新的产品 live batch。
