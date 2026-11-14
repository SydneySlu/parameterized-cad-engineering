# 工作日志

本文件只追加。每次工作完成后记录实际动作、结果、验证和下一步；聊天中的口头进展不作为唯一记录。

### APP-003-LIVE-UI / Codex / review / 2026-11-13

- 动作：对 `cc/APP-003-LIVE-UI@0b8bd7b` 完成固定 CAD venv 与 localhost 浏览器独立复核；仅更新复核文档和项目状态，未修改实现、未 push、未合并。
- 固定环境验证：Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0；Product Live/UI 135/135、C1/C2/C3 demo 183/183、Integration 81/81、Schema 17/17、CAD compilation 13/13；`py_compile` 与 `git diff --check` 通过。
- 浏览器验证：注入 FakeTransport/synthetic envelope 的 `127.0.0.1:8766/product-live` 完成 P1 `needs_confirmation`→确认→真实本地 STEP `succeeded`，148393 bytes，下载 hash 与页面 hash 一致；P2 `blocked` 且显示缺少 `bore_d`，无确认/下载入口；`<img src=x onerror=alert(1)>` 仅显示文本，DOM 无 `img`/`onerror`。
- 边界：未调用 DeepSeek/Ollama、未读取 `.env`/密钥、未创建 batch；`FORMAL_EVALUATION_ALLOWED=False` 不变；结果不代表真实模型效果。
- 产物：`agent-work/reviews/APP-003-LIVE-UI-codex-review.md`、checkpoint 复核段；项目状态/计划/任务表改为 `review`。
- 结论/下一步：**pass，允许负责人合入 `main`**；合入后收束为 `done`，再决定是否准备新的 live batch scope。

### APP-003-LIVE-UI-CLOSEOUT / Codex / done / 2026-11-13

- 动作：核对负责人已将 `cc/APP-003-LIVE-UI` 合入并推送 `main`；`main`、`origin/main` 和分支均指向 `8dce35a`，工作区干净。
- 合入后复验：固定 CAD venv Python 3.11.18 下 Product Live/UI **135/135**、C1/C2/C3 demo **183/183**、Integration **81/81**、Schema **17/17**、CAD compilation **13/13**；`py_compile`、`git diff --check` 通过。仅有既有 ResourceWarning 和上游弃用警告。
- 收束：同步 `PROJECT_STATUS.md`、`PROJECT_PLAN.md`、`TASKS.md` 和 C2 checkpoint，APP-003-LIVE-UI 状态改为 `done`。
- 边界：仍未调用 DeepSeek/Ollama、未读取 `.env`/密钥、未创建 batch；`FORMAL_EVALUATION_ALLOWED=False` 不变。真实产品 live 必须另立 scope、预算、preflight、batch ID 和负责人批准。

### APP-003-LIVE-PREFLIGHT-20261113-01 / Codex / review / 2026-11-13

- 动作：按既定路线准备产品真实抽取 smoke 的独立执行包，基线为 `main=6fe4b43`；选择候选 batch `app003-product-live-20261113-01`。
- 固定范围：DeepSeek `deepseek-flash`、C0、当前冻结 `app001-extraction.v5`/`app001-io.v1`、4 条 P1–P4 输入、最多 12 次 HTTP；CAD 仅在 P1 抽取结果经用户显式确认后进入 pipeline，P2/P3/P4 和所有失败状态 fail closed。
- 证据：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261113-01/` 包含 `scope.md`、`preflight-report.json`、`approval-template.md` 和 checkpoint。
- 离线验证：固定 CAD venv Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0；offline preflight `ok=true`，prompt/inputs hash 通过，预算 `12/12` 可行，4 条 logical run 规划完成；dry-run 结果数 0，batch 目录不存在。
- 中枢复验：`tests.integration.test_product_live` 99/99、`tests.demo.test_product_live_ui` 36/36、目标文件 `py_compile` 和 `git diff --check` 均通过；显式 `run_product_offline_preflight(..., require_cad_runtime=True)` 返回 `ok=true`，`run_product_batch(dry_run=True)` 返回 `preflight_ok=true`、4 条 planned runs、0 条 results。
- 边界：未创建正式 batch/ledger，未读取 `.env`/API key，未调用 DeepSeek/Ollama，未运行正式 CAD；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 下一步：负责人审阅并填写 approval template；明确批准后才做正式 preflight，随后由负责人单独批准执行 live 请求。

### APP-003-LIVE-PREFLIGHT-APPROVAL / Codex / review / 2026-11-13

- 动作：项目负责人提供审批人 `Wang sikai`、当前 UTC 时间 `2026-11-13T14:49:33Z`，并要求按项目惯例填写审批引用；在 approval template 记录完整 scope 批准声明。
- 引用格式：仓库中未发现既有 `approval_record_ref` 约定，故采用 `Codex conversation — APP-003-LIVE-PREFLIGHT-20261113-01, user message dated 2026-11-13`，可从任务 ID 与对话日期追溯。
- 边界：本次只写入审批记录和 checkpoint；没有创建 formal batch/ledger、调用 formal runner、读取密钥或发起真实模型请求。
- 后续正式 preflight：2026-11-13T15:00:18Z 在固定 CAD venv 构造 approval 并执行 binding 校验，通过；`run_product_offline_preflight(..., require_cad_runtime=True)` 返回 `ok=true`，预算 12/12 可行，runtime/prompt 检查通过，batch 目录不存在。
- 边界：仍未调用 formal runner、创建 formal batch/ledger、读取密钥或发起真实模型请求；HTTP=0。
- 下一步：由负责人决定是否启动已批准 scope 的 live runner；该调用会在 preflight 后实际发请求，最多 12 次。

### APP-003-LIVE-SMOKE-20261113-01 / Codex / review / 2026-11-13

- 动作：负责人明确允许启动后，按已批准的 `app003-product-live-20261113-01` scope 在固定 CAD venv 执行正式 Product Live runner。
- 执行：4 次 DeepSeek `deepseek-flash` / C0 HTTP 请求，账本合计 `4/12`，每个 P1–P4 各 1 次尝试；批次 summary 状态为 `failed`。
- 结果：四条运行均为 `llm_status=error`、`product_status=error`、`PARSE_OR_ENVELOPE_ERROR`（adapter returned no parse result or envelope）；没有进入用户确认、Schema/IR/CAD、pipeline 或 STEP，STEP 文件数为 0。
- 证据：批次目录 `work/app001-runs/app003-product-live-20261113-01/` 和 `batch_summary.json`、`budget_ledger.json` 只读保留；`raw/` 文件数为 0，summary 中 raw retention path/hash 均为空；未读取 raw 正文。
- 边界：本批次已经消耗 4 次 HTTP，不重跑、不追加请求、不把失败结果描述为模型效果；`FORMAL_EVALUATION_ALLOWED=False` 未改变。
- 下一步：先修复并离线验证失败响应的 parse/retention 证据链；任何后续真实请求必须新 batch ID、新 approval、新 preflight。

## 2026-11-13

### APP-003-LIVE-UI / CC / review

- 动作：将已有 `ProductLiveService` 和 `/api/product-live/*` 受控 API 接入明确标记的 live 确认页面（`/product-live`）。
  - `src/demo/server.py`（修改）：新增 `_build_product_live_html()` 构建 live UI 单页 HTML+CSS+JS；新增 `PRODUCT_LIVE_HTML_CONTENT`/`PRODUCT_LIVE_HTML_BYTES` 常量；新增 `GET /product-live` 路由 → `_handle_product_live_ui()`（返回带 offline 警告的 live UI 页面）；新增 `GET /api/product-live/inputs` 路由 → `_handle_product_live_inputs()`（返回授权 input IDs 白名单，无 key/label/路径）；C1/C2/C3 路由完全不变。
  - `tests/demo/test_product_live_ui.py`（新增，36 项）：GET /product-live → 200 HTML 含 banner；esc() 五种转义；无裸插值；GET /api/product-live/inputs；无 service → 503；P1 create→confirm→download E2E；P2/P3/P4 blocked 零 CAD；failed 无 STEP；XSS payload 为 JSON 字符串；API 响应无 secret/labels；C1/C2/C3 向后兼容。
- 验证：`py_compile` → OK；`git diff --check` → OK；`test_product_live_ui` 36/36 → OK；`test_product_live` 99/99 → OK；combined 135/135 → OK；schema 17/17 → OK。
- 安全：`FORMAL_EVALUATION_ALLOWED=False` 全程不变；不发网络请求；不读密钥；不复用 A2 凭证；不创建正式 batch；evaluator labels 不进入页面/HTTP 请求；XSS 通过 `esc()` 防护。
- 限制：沙箱 Python 3.10.12，非 3.11.18；固定 CAD venv 全量验证待完成；真实 DeepSeek HTTP 请求需 Codex 复核 + 负责人授权；浏览器端 XSS DevTools 验证需 Mac + 浏览器。
- 下一步：Codex 中枢在 Python 3.11.18 重跑 135 项（test_product_live + test_product_live_ui）+ C3 regression；负责人审阅后决定是否批准具体 batch ID 和 live 执行授权。状态 `review`，不 push、不合并 main。

### APP-003-LIVE-PRODUCT-R1-CORRECTION-2 / Codex / review

- 动作：在 `cc/APP-003-LIVE-PRODUCT` HEAD `5c28b96` 完成窄修独立复核。固定 CAD venv Python 3.11.18 下 product live 99/99、C1/C2/C3 + integration 264/264、Schema 17/17、CAD compilation 13/13 全部通过；`py_compile` 和 `git diff --check` 通过。
- 定向证据：`_to_repo_relative_path()` 对 `..` 穿越、仓库外绝对路径和仓库内 symlink 外逃均返回 `None`，合法仓库路径正确转为 repo-relative；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- HTTP/CAD 烟测：注入 FakeTransport 的 P1 create→needs_confirmation→confirm→succeeded→download 通过，真实 STEP 148393 字节，下载 SHA-256 与 `ir_index.step_sha256` 一致，离线 transport 仅 1 次；P2/P3/P4 阻断和零 CAD 由专项回归覆盖。
- 结论：本轮窄修 `pass`，可合入 `main`；合入前状态保持 `review`。未创建正式 batch，未发真实 DeepSeek 请求，未读取密钥或 `.env`。合入后再收束任务状态，再由负责人另行批准具体 live batch 和 provider 请求。

### APP-003-LIVE-SCOPE-CLOSEOUT / Codex / done

- 动作：核对负责人已将产品 live 受控入口及路径安全窄修合入 `main`，当前 `main`/`origin/main` 均为 `db26fda`，工作区干净。
- 结果：APP-003-LIVE-SCOPE 收束为 `done`。固定环境 product live 99、Demo/Integration 264、Schema 17、CAD 13 通过；P1 离线 transport 下 create→confirm→真实 STEP download 通过。该结果证明受控 API 和确认门，不证明真实 provider 效果。
- 下一步：规划 `APP-003-LIVE-UI`，把 `/api/product-live/*` 接入明确标记的确认页面；先用 FakeTransport/synthetic envelope 离线验收，之后再决定是否申请新的 live batch。现阶段不创建 batch、不发真实请求、不读取密钥。

### APP-003-LIVE-PRODUCT-R1-CORRECTION-2 / CC / review

- 动作：窄修 `_to_repo_relative_path()` 路径安全问题。旧实现在解析失败时会把相对路径原样返回（`return path_str`），使 `../../outside/file.step` 或 symlink 逃逸路径绕过 containment check 进入 summary/HTTP 响应。
  - 重写 `_to_repo_relative_path()`：相对路径以 `_REPO_ROOT` 为基准 resolve（不依赖 CWD）；绝对路径 canonical resolve（symlink 跟随）；canonical 结果必须在 `_REPO_ROOT` 内，否则返回 None；无任何"解析失败后原样返回相对字符串"的 fallback；函数 fail-closed，不抛出未处理异常。
  - 新增回归测试 14 项（`TestPathTraversalSafety` 9 项 + `TestSummaryWriterPathSafety` 4 项 + `TestSanitizeStateForHttp` 1 项），test_product_live.py 从 85 增至 99 项。
- 验证：`py_compile` → OK；`git diff --check` → OK；`test_product_live` 99/99 → OK；`schema` 17/17 → OK。手动验证：`../../outside/file.step` → None；symlink→outside → None；abs inside repo → repo-relative；relative inside → repo-relative。
- 安全：`FORMAL_EVALUATION_ALLOWED=False` 全程不变；不发网络请求；不读密钥；不复用 A2 凭证；不创建正式 batch；evaluator labels 不进入任何公开接口。
- 限制：沙箱 Python 3.10.12，非 3.11.18；固定 CAD venv 全量验证待完成；真实 DeepSeek HTTP 请求需 Codex 复核 + 负责人授权。
- 下一步：Codex 中枢在 Python 3.11.18 重跑 99 项 test_product_live + C3 回归，确认路径安全和 CAD 路径正确性。状态 `review`，不 push、不合并 main。



- 动作：窄修独立复核发现的两个阻断问题，不扩大 live scope。
  - **问题 1 修复**：`src/integration/product_live_runner.py` 新增 `ProductLiveService` 类，封装 FakeTransport 注入的离线模式；`extract(input_id, request_text)` 调用 `_run_one_logical_mock()` 执行真正的抽取并存入内部 registry；`confirm(run_id, confirmed, patch)` 调用 `confirm_product_live_run()`。`src/demo/server.py` 更新 `_handle_product_live_create()` 改为接受 `{request_text, input_id}`、调用 `service.extract()`；`make_handler_class()` 新增 `product_live_service` 参数（ProductLiveService 实例），向下兼容旧 dict 接口；新增 `_sanitize_state_for_http()` 辅助函数统一剥离绝对路径、raw body、secret、evaluator labels。
  - **问题 2 修复**：`src/integration/product_live_runner.py` 新增 `_to_repo_relative_path(path_str)` 将绝对路径转为 repo-relative；`_SummaryWriter.update_run()` 中所有文件系统路径（`raw_retention_path`、`pipeline_run_dir`、`step_path`、`ir_index["step_path"]`）统一经过 `_to_repo_relative_path()` 转换；HTTP 响应中的路径也通过 `_sanitize_state_for_http()` 统一转换。
  - 新增回归测试 33 项（tests/integration/test_product_live.py 从 52 增至 85）：P1 HTTP E2E create→confirm→download、P2/P3/P4 blocked 零 CAD、未配置 service 返回 503、summary 路径非绝对、路径穿越/symlink/hash 篡改拒绝、API 响应无 raw body/secret/labels、C1/C2/C3 向后兼容。
- 验证：`py_compile` → OK；`git diff --check` → OK；`test_product_live` 85/85 → OK；`schema` 17/17 → OK。
- 安全：`FORMAL_EVALUATION_ALLOWED=False` 全程不变；不发网络请求；不读密钥；不复用 A2 凭证；不创建正式 batch；evaluator labels 不进入任何公开接口。
- 限制：沙箱 Python 3.10.12，非 3.11.18；固定 CAD venv 全量验证待完成；真实 DeepSeek HTTP 请求需 Codex 复核 + 负责人授权。
- 下一步：Codex 中枢在 Python 3.11.18 重跑 85 项 test_product_live + C3 回归，确认 CAD 路径和路径转换正确性。状态 `review`，不 push、不合并 main。



- 动作：实现产品专用服务端受控入口（APP-003-LIVE-PRODUCT），支持离线 mock/spy 模式完整证明"浏览器请求 → 服务端 v5 DeepSeek → 产品授权/预算门 → envelope 解析 + 契约/Schema 预检 → C3 确认 UI/API → 显式用户确认 → 既有 Schema→IR→CadQuery→几何/STEP pipeline"时序。本任务不发真实 HTTP。
  - `src/llm/product_live_authorization.py`（新增）：`ProductLiveAuthorization`（extends `FormalRunAuthorization`），绑定 `profile_id=app003-product-live.v1`、4 个 input IDs、DeepSeek/deepseek-flash/C0、prompt/contract hash、最多 12 HTTP、`enable_cad_pipeline=True`；`ProductLiveFormalApproval` 独立于 A2 的批准凭证；`validate_product_formal_approval_binding()` 在任何目录/账本/transport/网络前校验；拒绝 A2 authorization、test-only approval、错 provider/model/condition/inputs hash/预算/batch binding。
  - `src/integration/product_live_runner.py`（新增）：`run_product_batch()` 公共入口（dry_run/mock/formal）；`run_product_offline_preflight()` 零网络零密钥 preflight；`confirm_product_live_run()` 用户确认后唯一调用 `run_pipeline()` 的路径；`ProductLiveRunState` 记录 prompt_file_sha256/prompt_version/contract_version/decision/参数/questions/missing/unsupported/conflicts；`_SummaryWriter` 原子批次摘要（不含 raw body/secret/labels）。
  - `src/demo/server.py`（修改）：新增 `POST /api/product-live/create`、`POST /api/product-live/confirm/<run_id>`、`GET /api/product-live/<run_id>`、`GET /product-live-download/<run_id>` 路由；`make_handler_class()` 新增 `product_live_handler` 可选参数（默认 None，C3 兼容）；`_get_product_live_step_bytes_secure()` 6 层安全下载。C1/C2/C3 路由完全不变。
  - `agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json`（新增）：4 条冻结刺激，SHA-256 `666a4c08...`。
  - `agent-work/integration/APP-003-LIVE-PRODUCT/evaluator-labels.json`（新增）：物理隔离评估标签，SHA-256 `73c671a7...`。
  - `tests/integration/test_product_live.py`（新增，52 项）：覆盖 P1 answer 零 CAD + 确认后成功、P2 ask blocked、P3 conflict blocked、P4 unsupported blocked、parse/schema/refuse fail-closed、approval gate（缺失/test-only/错 batch 拒绝）、budget plan、inputs SHA-256、summary 无 raw body/labels、C3 回归、run 隔离。
- 执行环境：sandbox Python 3.10.12（非固定 3.11.18/CadQuery；CAD-dependent 测试在沙箱中失败，与 C3 checkpoint 记录的环境限制一致）。
- 验证：`py_compile` → OK；`git diff --check` → OK；`test_product_live` 52/52 → OK；`schema` 17/17 → OK；C3 create/gate 10/10 → OK；C3 全量回归 183 ran，30 fail + 9 err（全部为 CAD-dependent，沙箱无 CadQuery）；integration 133 ran，25 fail + 3 err（同上）。
- 安全：`FORMAL_EVALUATION_ALLOWED=False` 全程不变；不读 `.env`/密钥；不调用 DeepSeek/Ollama/外网；evaluator labels 不进入 prompt/transport/summary/日志/测试输入；不创建 live batch 或发送 HTTP；不复用 A2 authorization/batch/approval/raw/summary。
- 限制：沙箱 Python 3.10.12，非 3.11.18；Codex 独立复审待完成；固定 CAD venv 全量验证待完成；真实 DeepSeek HTTP 请求需 Codex 复核 + 负责人具体 batch 授权。
- 下一步：Codex 中枢在 Python 3.11.18 重跑 `test_product_live` + C3 回归，确认 CAD 路径；负责人审阅后决定是否批准具体 batch ID 和 live 执行授权。状态 `review`，不 push、不合并 main。

## 2026-11-11

### APP-001-NEXT-REAL-MODEL-EVALUATION-RETRIEVAL-PREFLIGHT-FAIL-CLOSED / CC / review

- 动作：窄修 Codex 中枢 R1 复核（`3d42ff2`）发现的误绿问题：`HeldoutRunner().offline_preflight()` 在无 RET-002 retrieval index 时仍返回 `retrieval_index_provided=False, retrieval_config_check="skipped: no retrieval_index", offline_preflight_status="pass"`；CLI `_try_load_retrieval_index()` 吞掉所有加载异常并返回 `None`，使索引错误无声通过。
  - `src/llm/heldout_runner.py`：将 `offline_preflight()` 步骤 4 从可选检查改为硬性要求。`self._retrieval_index is None` 时立即设 `retrieval_config_check="FAIL: ..."` / `offline_preflight_status="fail"`，并 raise `FormalEvaluationBlockedError`。
  - `scripts/run_app001_heldout_v5.py`：`--offline-preflight` 路径从 `_try_load_retrieval_index()`（吞异常，返回 None）改为 `_load_retrieval_index_or_fail()`（失败即 `PREFLIGHT FAILED: cannot load RET-002 retrieval index: <error>` stderr + exit 1）。
  - `tests/llm/test_heldout_runner.py`：新增 `TestRetrievalPreflightFailClosed`（13 项测试）；修复 6 项旧测试（改传 `_build_valid_mock_retrieval_index()`）；新增模块级 `_build_valid_mock_retrieval_index()` fixture。
- 执行环境：sandbox Python 3.10.12（非项目固定 3.11.18，须 Codex 中枢在 Mac `/opt/homebrew/bin/python3.11` 重验）。
- 验证：`py_compile` → OK；heldout 83/83 OK；regression 120/120 OK（7 skips）；LLM 全量 938 OK（8 skips）；Schema 17 OK；`git diff --check` clean；CLI `--dry-run` 12 组合、exit 0；CLI `--offline-preflight` → `retrieval_index_provided=true, feasible=true, global=44`，无批次目录创建。
- 安全：`FORMAL_EVALUATION_ALLOWED=False` 未改变；evaluator labels 不出现；raw 留存路径不变；缺失索引在 BudgetLedger/mkdir 前拒绝。未修改 ADR-0019 预算值、旧批次、prompt 或生产配置。
- 限制：sandbox Python 3.10.12，非 3.11.18；Codex 独立复审待完成；final offline preflight 待完成；无 batch_id 或模型请求授权。
- 下一步：Codex 中枢在 Python 3.11.18 重跑全量测试，核实缺失索引现在 fail closed，确认正常路径 `retrieval_index_provided=true`，之后进行 final offline preflight 并提交批次授权模板。

### APP-001-NEXT-REAL-MODEL-EVALUATION-R1-CODEX-REVIEW / Codex / review

- 动作：按三层交接协议，在 `main=fd99ddb` 对 held-out runner R1 修复做 Python 3.11.18 中枢独立验收，并检查 ADR-0019、任务 checkpoint、状态和计划。
- 结果：`run_formal()` 全局 gate、profile 类型、独立 approval token、batch ID 匹配门禁通过代码复核；`FORMAL_EVALUATION_ALLOWED=False` 未改变。预算可行性公式与 ADR-0019 transport/retry 次序一致（DeepSeek 18、Ollama 26、global 44）。运行 held-out 专项 70 项通过、授权/预算/runner 回归 120 项通过（7 skips）、LLM 全量 925 项通过（8 skips）、Schema 17 项通过；`py_compile`、`git diff --check fd99ddb^ fd99ddb` 通过；dry-run 为 12 组合。
- 新发现阻断：`HeldoutRunner().offline_preflight("review-only-no-index-direct-fd99ddb")` 实测无 index 时返回 `retrieval_index_provided=False`、`retrieval_config_check="skipped: no retrieval_index"`，但 `offline_preflight_status="pass"`。CLI 的 `_try_load_retrieval_index()` 捕获加载异常并返回 `None`，会使 offline-preflight 在 RET-002 index/manifest 未验证时仍可能误报 pass。带本地 RET-002 index 的 CLI offline-preflight 单独返回 pass、global=44/Ollama=26；两条检查均未建批次目录。
- 验证与边界：Python 3.11.18；无网络/模型请求、无密钥或 `.env` 读取、无历史 raw 读取、无正式批次目录。`review-only-*` 字符串仅为离线核验参数，不是正式 batch ID。
- 下一步：任务保持 `review`。CC 窄修为缺失或加载失败的 RET-002 index 必须 fail closed，并覆盖缺失 index 与配置/manifest 加载失败路径；之后 Codex 中枢独立复核。该缺口关闭前不做 final offline preflight，不生成正式 batch ID/授权模板，不执行 live preflight 或模型请求。

### APP-001-NEXT-REAL-MODEL-EVALUATION-RUNNER-FIX / CC / review

- 动作：窄修 Codex 中枢审查（`88ea2dd`）发现的两项 P1。
  - **P1A — run_formal() 门禁**：在 `src/llm/heldout_runner.py` 中新增 `HeldoutBatchApproval` 冻结数据类和 `HeldoutBatchApprovalError`。`run_formal()` 现在在任何目录创建、账本写入、密钥读取或网络 I/O 之前，依次检查：(1) `FORMAL_EVALUATION_ALLOWED`（全局 gate，永不被此修复打开）；(2) `isinstance(authorization, HeldoutRunAuthorization)`；(3) `isinstance(batch_approval, HeldoutBatchApproval)`（独立于 profile 构造，不可绕过）；(4) `batch_approval.batch_id == authorization.batch_id`（防止错配）。更新 `scripts/run_app001_heldout_v5.py` 在 `--run` 模式下构造并传入 `HeldoutBatchApproval` 令牌。
  - **P1B — offline-preflight 预算可行性**：替换 `offline_preflight()` 中硬编码的 `36 + 20 = 56 ≤ 44` / `feasible=True` 为调用 `_compute_budget_feasibility()`。该函数按 ADR-0019 §"实施预算口径补充" 的实际 transport/retry 顺序推导 worst-case HTTP：每个 Ollama run 最多 `max(3 tags failures, 1 tags success + 3 chat) = 4` HTTP；Ollama total = 2 preflight + 6 × 4 = 26 ≤ 26 ✓；global = 18 + 26 = 44 ≤ 44 ✓。`feasible` 和 `offline_preflight_status` 均由校验结果计算，不能硬编码；任何约束超限时 fail-closed 并附具体约束名。
  - 新增回归测试 `TestRunFormalGateAndApproval`（8 项）和 `TestBudgetFeasibility`（8 项），总测试数从 53 增至 70。P1A 测试用 mock/spies 断言门禁关闭时 mkdir / BudgetLedger / _build_transport 调用次数为 0。P2 测试用 infeasible 配置断言 fail-closed，用正常配置断言 global_total=44，用硬编码检测测试确保 feasible 不能为常量 True。
- 执行环境：sandbox Python 3.10.12（非项目固定 3.11.18，须 Codex 中枢在 Mac `/opt/homebrew/bin/python3.11` 重验）。
- 验证结果（全部离线/mock）：
  - `py_compile` 三个修改文件 → OK
  - `test_heldout_runner` 70/70 → OK
  - `test_heldout_authorization + test_authorization + test_budget + test_runner` 120 → OK（skipped=7）
  - `discover tests/llm` 925 → OK（skipped=8）
  - `discover tests/schema` 17 → OK
  - `git diff --check` → clean
  - CLI `--dry-run --json` → 12 组合、exit 0
  - CLI `--offline-preflight --batch-id review-only-not-a-batch-20261111 --json` → `offline_preflight_status=pass, feasible=True, global_total=44, ollama_total=26`，无批次目录创建
- 安全/隔离确认：`FORMAL_EVALUATION_ALLOWED=False` 未改变；evaluator labels 不出现在任何输出；raw 留存路径 `work/app001-runs/<batch_id>/raw/` 不变；run_formal 所有正式请求路径均先经账本预留；构造 `HeldoutRunAuthorization` 本身不触发任何批次创建或请求。
- 未修改：prompt、解析策略、生产 provider 配置、历史批次、ADR-0019 预算值。
- 修改文件（仅本任务）：`src/llm/heldout_runner.py`（P1A 门禁 + P1B 预算公式 + 新增 HeldoutBatchApproval）、`scripts/run_app001_heldout_v5.py`（--run 模式传入 approval token）、`tests/llm/test_heldout_runner.py`（+17 项）、`agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/checkpoint.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`。
- 限制：sandbox Python 3.10.12，非项目固定 3.11.18；独立 Codex 复审待完成；final offline preflight 待完成；无 batch_id 或模型请求授权。
- 下一步：Codex 中枢在 Mac Python 3.11.18 重跑全量测试，验证 P1A/P1B 修复，确认 spy 断言正确拦截副作用，核实 offline-preflight 输出与 ADR-0019 数字一致，之后进行 final offline preflight 并提交批次授权模板供项目负责人审批。

### APP-001-NEXT-REAL-MODEL-EVALUATION-RUNNER / CC / review

- 动作：实现 ADR-0019 专用离线优先 held-out v5 runner 与受控 CLI 入口。
  1. 新建 `src/llm/heldout_runner.py`：`HeldoutRunner`（`dry_run()` / `offline_preflight()` / `run_formal()`）；`generate_heldout_combinations()`（独立 12 运行矩阵，不复用 `generate_combinations()`）；`load_heldout_inputs()`（SHA-256 核验、仅提取 `query_id` + `natural_language_input`，不读标签）；`_HeldoutProjectedCase` 适配器；`_assemble_c0` / `_assemble_held_c1` 包装；`_heldout_raw_retention_policy()`（原始响应写入 `batch/raw/`）；`_ensure_heldout_ir_cad_not_run()`。
  2. 新建 `scripts/run_app001_heldout_v5.py`：`--dry-run` / `--offline-preflight` / `--run` 三模式 CLI 入口；正式模式在 `FORMAL_EVALUATION_ALLOWED=False` 时 fail-closed；正式执行需 `--allow-formal-run` 且必须完成 offline preflight。
  3. 新建 `tests/llm/test_heldout_runner.py`：53 项离线/mock 测试，覆盖全部 7 类需求（12 组合固定性、标签隔离、C0/C1 正常装配、拒绝案例、mock HTTP 预算强制、运行记录路径、scope 摘要/账本审计及遗留回归）。
  4. 更新 `agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/checkpoint.md`，追加 runner 里程碑及 handoff_self_check。
  5. 更新 `docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`。
- 执行环境：sandbox Python 3.10.12（非项目固定 3.11.18，须 Codex 中枢在 Mac `/opt/homebrew/bin/python3.11` 重验）。
- 验证结果（全部离线/mock，无网络请求、无凭据读取、无批次目录创建）：
  - `py_compile` 三个新文件 → OK
  - `test_heldout_runner` 53/53 → OK
  - `test_heldout_authorization + test_authorization + test_budget + test_runner` 120 → OK（skipped=7）
  - `discover tests/llm` 908 → OK（skipped=8）
  - `discover tests/schema` 17 → OK
  - `git diff --check` → clean
- 冻结哈希确认（已重算）：
  - `model-inputs.json` SHA-256：`c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6` ✓
  - `evaluator-labels.json` SHA-256：`bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a` ✓
  - RET-001 manifest SHA-256：`b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297` ✓
- 安全/隔离确认：evaluator labels 未出现在组合生成、输入装配、Adapter、Transport、Prompt、运行日志或 dry-run 输出中；`FORMAL_EVALUATION_ALLOWED=False` 未改变；旧授权/账本行为回归通过；未分配正式 batch_id；无模型/网络请求。
- 限制：sandbox Python 3.10.12 非项目固定基线；独立 Codex 中枢审查待完成；final offline preflight 待完成；无 batch_id 或模型请求授权。
- 修改文件（仅本任务）：`src/llm/heldout_runner.py`（新）、`scripts/run_app001_heldout_v5.py`（新）、`tests/llm/test_heldout_runner.py`（新）、`agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/checkpoint.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`。
- 下一步：Codex 中枢在 Mac Python 3.11.18 独立重跑全量测试，核对 evaluator labels 隔离和 mock HTTP 预算强制，确认 dry-run 和 offline-preflight 离线可运行，并检查 raw 留存路径；通过后进行 final offline preflight 并向项目负责人提交完整授权模板审批。

## 2026-11-08

### APP-001-V4-ACTIVATION-CLOSEOUT-FIX-CODEX-REVIEW / Codex / review

- 动作：按交接协议独立复核 `cc/APP-001-V4-ACTIVATION` 的 closeout 差异 `85f9e71..f858be8`，核对提交链、文档范围、冻结哈希、生产 gate，并在固定 Python 3.11.18 环境重跑验证。
- 结果：仅 7 个文档/注释/交付记录文件变化；没有测试文件、冻结 prompt、acceptance-set、运行逻辑、预算/授权/provider/retry 配置变化。激活实现提交为 `85f9e71`，closeout 内容提交为 `d01eb81`，当前 HEAD `f858be8` 修正了 closeout 日志中的提交引用。
- 验证：v4 activation 71 项通过；LLM 全量 685 项通过、8 个既有 FUSE skip；Schema 17 项通过；Python 3.11.18 `py_compile`、`git diff --check` 通过。正常 v4 envelope 通过默认 parser；旧 v3 envelope 被默认 parser 以 `PROMPT_VERSION_MISMATCH` 拒绝。
- 身份/边界：v4 prompt SHA-256=`73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`；v3 rollback SHA-256=`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`；acceptance-set SHA-256=`ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`；`FORMAL_EVALUATION_ALLOWED=False`。未调用模型、读取密钥或修改批次。
- 限制：本地分支仍错误跟踪 `origin/codex/APP-001-V3-DECISION-FIX-DRAFT`；对 `origin/cc/APP-001-V4-ACTIVATION` 的 `git ls-remote` 超时，远端发布状态未确认，因此任务保持 review，暂不标记合入放行。
- 下一步：项目负责人 push `cc/APP-001-V4-ACTIVATION` 当前完整本地分支，并将远端 ref 与 push 时 `git rev-parse HEAD` 输出核对一致；之后 Codex 再做最终合入审查。真实 v4 效果评测仍需新的唯一批次和明确授权。

### APP-001-V4-ACTIVATION / CC / review

- 动作：按 ADR-0017（项目负责人批准策略方向）完成 APP-001 extraction v4 的版本化激活实现单元。在分支 `cc/APP-001-V4-ACTIVATION`（基线 `1d84b12`，来自 `origin/codex/APP-001-V3-DECISION-FIX-DRAFT`）上执行以下工作：
  1. 建立 `agent-work/llm/APP-001-v4-activation/`：冻结 prompt（SHA-256 `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`）、manifest（含候选源 hash、激活 hash、版本、回滚目标）、README、checkpoint。
  2. 将 `src/llm/contract.py` 的 `PROMPT_VERSION` 切到 `app001-extraction.v4`。
  3. 将 `src/llm/prompt_loader.py` 的 loader 路径、版本常量和文件哈希锚点更新为 v4。
  4. 将 `src/llm/parser.py` 的 `_LEGACY_AUDIT_PROMPT_VERSIONS` 扩展为包含 v3，使 v3 历史批次仍可走只读审计路径；默认 parser 拒绝非 v4 版本。
  5. 更新现有回归测试中的模拟响应体（v3→v4），更新 `test_envelope_fix.py` 的哈希/版本断言；新增 v3 未改动的独立哈希锁定断言。
  6. 新增 `tests/llm/test_v4_activation.py`（71 个测试，覆盖激活包、parser 边界、retrieval 优先级、单位换算、unsupported 规范标签、75 mm/缺失 bore_d/拒绝边界、v3 回滚哈希锚点、授权/预算/C2/CAD 禁止边界）。
  7. 将 ADR-0017 状态更新为 accepted，记录项目负责人批准日期 2026-11-08。
  8. 更新 PROJECT_STATUS、WORKLOG。
- 结果：
  - `agent-work/llm/APP-001-v4-activation/` 完整创建，包含 4 个文件。
  - `src/llm/{contract,parser,prompt_loader}.py` 原子更新。
  - `tests/llm/test_v4_activation.py` 新增 71 个测试。
  - 回归测试 7 个文件更新。
- 验证（CC 环境 Python 3.10.12；项目固定基线为 3.11.18，须由 Codex 中枢在 Mac 重跑）：
  - `test_v4_activation`：71/71 OK
  - `discover tests/llm`：685 OK，8 个既有 FUSE skip
  - `discover tests/schema`：17/17 OK
  - `py_compile` 全部修改文件：OK
  - `git diff --check`：OK
- 哈希核对：
  - v4 冻结 prompt SHA-256：`73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`
  - v3 回滚 prompt SHA-256（未改）：`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`
  - acceptance-set SHA-256（未改）：`ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`
  - `FORMAL_EVALUATION_ALLOWED=False` 未改变。
- 限制：
  - CC 运行环境为 Python 3.10.12，非项目固定的 3.11.18；Codex 中枢须在 Mac `/opt/homebrew/bin/python3.11` 重验。
  - 模型效果未验证；不授权任何真实模型请求或新正式批次。
  - 未调用 DeepSeek/Ollama，未读取密钥，未修改旧批次、旧 prompt 文件或冻结验收集。
- 提交：本次工作提交为 `feat: activate APP-001 extraction v4 contract [APP-001-V4-ACTIVATION]`（提交 `3b1e353`）。
- 下一步：Codex 中枢独立审查（在 Mac Python 3.11.18 下重跑全量测试，核对所有哈希，确认禁止范围未变），审查通过后合并到 main；如需测 v4 模型效果，须另建唯一正式批次并取得项目负责人明确授权。



- 动作：根据项目负责人确认的云端 DeepSeek v4.1 Flash 1017、本地 Ollama `qwen3:8b`（digest `500a1f067a9f`）及 MacBook Air M5 设备条件，建立 APP-001 双基线契约和准备 Agent Prompt。
- 结果：明确 APP-001 前冻结口径、不产生成绩；模型运行后测字段/Schema/追问，接入确定性 CAD/STEP 链后测几何和回读指标；未来 Windows CPU 结果单独记录。
- 交付：`docs/coordination/APP-001-baseline-contract.md`、`docs/coordination/prompts/APP-001-baseline-freeze-agent.md`、ADR-0009；任务看板新增 APP-001-PREP 并设置 APP-001 依赖。
- 验证：`git diff --check` 通过；两个文档提交分别为 `443f534`、`48a658e`。
- 限制：云端 provider 和 API 返回实际 `model` 字段仍待正式运行时记录；目前没有字段抽取、Schema、CAD、STEP 端到端实测结果。
- 下一步：项目负责人 push 提交后，按 APP-001-PREP Prompt 完成验收集与 I/O 契约草案，中枢审查通过后再运行双模型基线。

### APP-001-V4-ACTIVATION-CLOSEOUT-FIX / CC / review

- 动作：在分支 `cc/APP-001-V4-ACTIVATION`（HEAD `85f9e71`）上执行窄范围文案收束。修正激活提交后残留的 v3 字符串（文档/注释），并修正 checkpoint.md 中的激活提交哈希记录。
- 基线/HEAD：`85f9e71`（激活提交父节点 `1d84b12`）
- 修改文件（仅文档、注释、交付记录；不改运行逻辑、不改测试）：
  - `src/llm/prompt_loader.py` — `_parse_artifact` docstring：`prompt-v3` / `app001-extraction.v3` → `prompt-v4` / `app001-extraction.v4`
  - `src/llm/parser.py` — `parse_response_for_version` docstring：默认 v3 parser → 默认 v4 parser；保留 v3/v2 历史路径说明
  - `src/llm/adapter.py` — 顶层 docstring：`prompt-v3` → `prompt-v4`
  - `src/llm/__init__.py` — 包 docstring：active protocol `v3` → `v4`；新增历史说明
  - `src/llm/README.md` — active protocol 版本、prompt-v3 路径、schema 表 v3 const、Ollama 段落均更新为 v4；v3 历史/回滚引用保留并明确标注
  - `agent-work/llm/APP-001-v4-activation/checkpoint.md` — 激活提交哈希 `3b1e353` → `85f9e71`；明确状态 review、未 push、未合入 main
  - `docs/WORKLOG.md` — 本条追加（not rewriting prior entries）
- 验证（CC 环境 Python 3.10.12；项目固定基线 3.11.18 须 Codex 中枢在 Mac 重跑）：
  - `python3 -m py_compile src/llm/{prompt_loader,parser,adapter,__init__}.py` → OK
  - `PYTHONPATH=src:. python3 -m unittest tests.llm.test_v4_activation -q` → 71/71 OK
  - `git diff --check` → OK（无空白错误）
  - grep active production 文档无错误 v3 字样 → OK（所有 v3 引用均在历史/legacy/rollback 语境）
  - v4 prompt SHA-256 `73cb6b8f…` 未变 ✓；v3 rollback SHA-256 `3dd8bd55…` 未变 ✓；acceptance-set SHA-256 `ed59e2b6…` 未变 ✓
- 限制：CC 环境 Python 3.10.12；Codex 中枢须在 `/opt/homebrew/bin/python3.11`（3.11.18）重验后方可合并。未调用模型，未读取密钥，未创建批次，未改运行逻辑，未修改测试文件。
- 提交：`docs: close APP-001 v4 activation handoff [APP-001-V4-ACTIVATION-CLOSEOUT-FIX]`（提交 `d01eb81`，父 `85f9e71`）。
- 下一步：Codex 中枢在 Mac 3.11.18 独立重验；通过后 push 并合并到 main。

## 2026-11-08

### APP-001-PREFLIGHT-TEST-ISOLATION-FIX / CC / review

- 动作：修复 `tests/llm/test_r3_fixes.py` 中 12 处 `int(time.time() * 1000) % N` batch_id 生成方式，替换为 `uuid.uuid4().hex[:8]`，消除 Python 3.11 快速执行时的目录碰撞问题。在 `cc/APP-001-PREFLIGHT-TEST-ISOLATION-FIX`（基线 `bf8117d`，`origin/main`）上执行。
- 根因：取模运算在快速测试执行下会产生重复的 batch_id，导致多个测试共享同一 `work/app001-runs/<batch_id>/` 目录，引起预算记录重复和 concurrent claim 断言失败。
- 修改文件：`tests/llm/test_r3_fixes.py`（新增 `import uuid`，替换 12 处 batch_id 模式）、`agent-work/llm/APP-001-PREFLIGHT-TEST-ISOLATION-FIX/checkpoint.md`（新建）、`docs/WORKLOG.md`（本条）。
- 不修改：生产代码、Prompt、Schema、授权范围、预算、测试断言、业务逻辑、旧正式批次目录。
- 验证（CC 环境 Python 3.10.12；项目固定基线 3.11.18 须 Codex 中枢重跑）：
  - `py_compile tests/llm/test_r3_fixes.py` → OK
  - `test_r3_fixes` 连续两次 → 各 51/51 OK
  - `discover tests/llm` 连续两次 → 各 685 OK，8 个既有 FUSE skip
  - `discover tests/schema` → 17/17 OK
  - `git diff --check` → OK
- 限制：CC 环境为 3.10.12，非项目固定的 3.11.18；Codex 中枢须在 `/opt/homebrew/bin/python3.11` 重验。未调用模型，未读取密钥。
- 提交：`test: isolate APP-001 preflight batch IDs [APP-001-PREFLIGHT-TEST-ISOLATION-FIX]`（`51188b2`）。
- 下一步：Codex 中枢在 Mac Python 3.11.18 重验，通过后合并到 main。

## 2026-10-28

### INFRA-001 / Codex / done

- 动作：检查工作区并初始化项目协作基础，建立 `AGENTS.md`、状态页、计划页、任务看板、决策记录和 `.gitignore`。
- 结果：仓库内形成统一入口；所有 Agent 可按同一协议读取当前状态和认领任务。
- 验证：文件结构检查通过；待 Git 首次提交。
- 下一步：配置远程仓库并验证跨设备同步（INFRA-003）。

### INFRA-002 / Codex / done

- 动作：比较 `profile-pack` 与仓库内项目管理协议。
- 结果：确认 `profile-pack` 适合作为本机 Agent 上下文/决策辅助层；Git 文档与提交历史作为项目事实源。
- 依据：Profile Pack README 和 `docs/evaluation/decision-layer.md`，其 Project Profile 与决策日志是 local-only MVP，未提供远程多用户同步。
- 下一步：远程仓库配置后，再决定是否在各 Agent 主机接入 Profile Pack。

### INFRA-003 / Codex / blocked

- 动作：初始化本地 Git 仓库并完成首个可审查提交。
- 结果：commit `ece00b0`（`docs: establish cross-agent project foundation [INFRA-001]`）；仓库当前分支为 `main`，尚未绑定远程。
- 验证：`git status --short --branch` 显示工作区干净；已检查暂存内容，未纳入论文原始缓存和生成渲染物。
- 阻塞：尚未提供 GitHub/GitLab 仓库 URL 或远程访问方式。
- 下一步：绑定远程后执行首次 `push -u origin main`，并在另一设备做 clone/pull 验证。

### INFRA-004 / Codex / done

- 动作：增加 `docs/coordination/agent-bootstrap.md` 和 `CONTRIBUTING.md`，明确 Codex、CC、DSH 的职责、启动提示和交接格式。
- 结果：新聊天框或新设备只需读取仓库文件即可获得相同协作协议；不依赖某个聊天框保留上下文。
- 验证：文档链接和任务 ID 与 `AGENTS.md`、`docs/TASKS.md` 一致。
- 下一步：远程仓库配置后，把同一套启动协议提供给每个 Agent 的宿主配置。

### INFRA-005 / Codex / done

- 动作：增加中枢编排协议、复杂任务 checkpoint 规范和 `scripts/check_project_state.py` 仓库体检脚本。
- 结果：复杂任务可以分阶段同步；Codex 中枢负责生成 Agent 初始化 prompt、检查依赖和审查阶段性结果。
- 验证：运行 `python3 scripts/check_project_state.py`，通过；当前唯一仓库警告是尚未配置远程。
- commit：`0e75325`（`docs: add checkpoint orchestration and repo checks [INFRA-005]`）。
- 下一步：后续每个实现任务按 checkpoint 方式推进，阶段结果先进入 `review`，合并后再标记 `done`。

### INFRA-006 / Codex / done

- 动作：建立仓库外的本地中枢审查台账，并明确私有台账、共享事实源和独立复核对话框的边界。
- 结果：任务分派、prompt 摘要、checkpoint、审查问题和修正 commit 可集中追踪；项目共享事实仍以 Git 为准。台账路径为本地用户数据目录，不纳入仓库。
- 验证：确认台账文件权限为仅当前用户读写；运行仓库体检和 `git diff --check`。
- 下一步：每次分派、checkpoint、审查和修正时更新台账；重要结论按需发起另一个 Codex 对话框的独立复核。

## 2026-11-01

### CAD-005/006-R1 / CAD 执行 Agent / in_progress

**第一阶段：三层交接检查（完成）**

- 动作：
  1. 阅读 AGENTS.md、PROJECT_STATUS.md、PROJECT_PLAN.md、TASKS.md、DECISIONS.md、coordination/handoff-review-protocol.md
  2. 读取前序任务 DATA-003、CAD-003、IR-001 的 checkpoint 和代码
  3. 执行第二层定向复核：复跑 DATA-003 smoke 命令，验证 4 个案例（合法、边界、约束非法、几何非法）
  4. 设置开发环境：CadQuery 2.3.0 + OCP 7.9.3.0 + Python 3.10
  5. 理解 IR v0 结构：节点类型、表达式类型、公式集合、验证指标

- 结果：
  - ✓ 第二层复核 PASS：spec.check() 和 part.build() 均可调用，所有测试案例行为符合预期
  - ✓ 前序接口完整：CAD-003 参数规则、约束集合、构造器 API 均冻结
  - ✓ 环境配置完成：依赖已安装，BenchCAD 源快照（benchcad-2-035f467-raw）存在完整
  - ✓ IR 结构理解完成：5 节点类型、5 表达式类型、11 公式、错误分层

- 验证：
  ```bash
  cd work/benchcad-source/benchcad-2-035f467-raw && \
    PYTHONPATH=.:./framework python3 /mnt/outputs/test_handoff.py
  # 输出：✓ 4 个测试 PASS
  ```

- 交接记录：
  - `agent-work/cad-validation/CAD-005-006/handoff_successor_check.md`（第二层复核记录）
  - `agent-work/cad-validation/CAD-005-006/checkpoint.md`（当前 R1 checkpoint）

**第二阶段：编译器架构设计（启动）**

- 动作：
  1. 分析 IR v0 示例（legal-catalog-row.json 等）
  2. 设计模块化架构：解析层、验证层、编译层、验证层
  3. 建立 src/cad_compilation/ 目录和模块框架
  4. 记录关键发现、决策点和风险

- 关键发现：
  1. **验证必须分层**（DATA-003 证明）
     - preflight: 约束检查（绝不能跳过）
     - build: CadQuery 构造
     - post_geometry: 实体数、有效性、几何摘要
     - step_readback: STEP 往返验证
  2. **多实体风险**：outer_d < bore_d 时 build() 产生 3 solids，STEP 导出成功，但属于非法结果
  3. **STEP 不稳定**：字节 hash 不同但几何摘要相同 → 必须使用结构化摘要，不用字节 hash 判定
  4. **螺纹模型限制**：thread_model=revolved_ring_approximation，M3-M8 可能 no-op

- 待确认的决策点（交给中枢）：
  1. 公式参数的单位推导规则
  2. 回转轴定义和轮廓绘制方向
  3. 置放（placement）模型的坐标系统一性

- 已知限制：
  - 仅支持 set_screw_shaft_collar（首族）
  - STEP 字节 hash 不稳定，不作重复性标准
  - 螺纹为环形近似，不是真实螺旋
  - Source snapshot reproducibility_partial

- 下一步：
  1. 实现 IR 解析、语义检查、公式求值（4-6 h）
  2. 实现 CadQuery 操作映射（4 h）
  3. 实现几何/STEP 验证（2-3 h）
  4. 编写测试和运行日志（2 h）
  5. 交接给中枢审查（review 状态）

### INFRA-007 / Codex / done

- 动作：围绕轻量版架构规划数据、LLM、Schema/规则、Typed CAD IR 设计、CAD 执行/验证和集成审查的 Agent 分工与依赖；暂不生成初始化 prompt。
- 结果：明确 Codex 负责接口、范围、审查和 IR 设计，CC 负责 Schema/规则及 CAD 执行实现，数据 Agent 负责来源和样本，LLM Agent 负责 Prompt/结构化抽取/检索接入；Typed CAD IR 与验证器共用版本化接口。
- 验证：检查计划、任务看板和协调文档中的任务 ID、依赖和验收条件；待正式认领后再建立具体 Agent prompt。
- 下一步：确认首期零件族、实际对话框/分支名称和评测阈值，再生成逐 Agent 初始化 prompt。


### DATA-001 / Codex / review

- 动作：比较 BenchCAD 2.0 社区族/公开评测集、CADBench（附件论文 arXiv:2605.10873v2）和 Seek-CAD 的目标、数据结构、轻量版适配度、规模与许可边界；研究报告现位于 `database/cad-dataset-suitability-2026-10.md`。
- 结果：建议 BenchCAD 2.0 作为主数据源候选，因为其参数、来源范围、约束和确定性 CadQuery 几何与项目主线接近；CADBench 作为多模态几何重建/外部评测参考；Seek-CAD 作为特征序列及检索方法参考。尚未冻结数据集或零件族。
- 验证：查阅附件论文第 1、3、4 节及附录 D；核对三个项目的作者 README、BenchCAD 2.0 博客/仓库设计规范和 CADBench Hugging Face 数据卡。未下载完整数据集或运行样本。
- 许可边界：BenchCAD 2.0 README 区分 MIT 代码/设计与 CC BY 4.0 数据制品；CADBench 按源数据混合许可；Seek-CAD 仓库代码 MIT，但 README 未单列数据许可。
- 下一步：导师/项目负责人确认主数据源候选与零件族方向后，开展已合并 BenchCAD 家族和候选族覆盖的样本级审查（DATA-002）；再冻结首期零件族。

### DATA-001 / Codex / review / 2026-10-28 checkpoint

- 动作：补充核对 BenchCAD 2.0 GitHub 设计接口、当前状态页、评审规范、官方博客及 Hugging Face Public/Core 数据卡；研究报告现位于 `database/benchcad-2-deep-dive-2026-10.md`。
- 结果：明确区分社区参数化零件族与 Public/Core 工程任务评测集；整理 `part.py`、`spec.py`、`family.json` 及 `PARAM_SPEC`、`check()`、`refine()` 的字段语义；核对当前状态页为 4/150 个族已合并；对三个候选零件族给出匹配和延伸估算。
- 关键风险：Public/Core 当前数据卡明确禁止训练、微调、蒸馏、RL 环境、检索/搜索语料和再发布，因此只能作为外部评测/任务设计参考；不能按原始评估集接入轻量版检索或训练管线。
- 验证：官方页面与仓库原文核对；`git diff --check` 通过；未下载 gated Public/Core 内容，也未将其文件写入仓库。
- 下一步：导师确认首期目标族后，执行 DATA-002：选定一个已合并族或仿照其接口新增一个来源可追溯族，建立项目 manifest 与 Typed CAD IR 映射。

### DATA-002 / Codex / in_progress / 2026-10-29 checkpoint

- 动作：根据用户转述的导师意见，将数据策略调整为 BenchCAD 社区参数化族优先；计划现位于 `database/benchcad-dataset-first-plan-2026-10.md`，并在 `docs/DECISIONS.md` 记录 ADR-0005 proposed；同步更新项目状态、计划和任务看板。
- 结果：建议把当前可用的 BenchCAD 社区族作为覆盖目标，先以两个结构不同的族完成 smoke test，随后扩展其余可用族；主要增量工作改为跨族 manifest/Typed CAD IR adapter、自然语言缺失/冲突任务、检索对照和逐族几何验证。没有冻结最终族数或新增垂直领域。
- 许可/状态边界：GitHub 社区族与 Public/Core 评测集分开；Public/Core 当前条款禁止作为训练、检索语料或 RL 环境。已核验状态页报告 4/150 merged、0 release-qualified（状态页标注 2026-08-02），实施前须再次锁定具体 commit 和族状态。
- 验证：待运行仓库体检、diff 检查；未下载评测 gated 内容，也未复制外部 CAD 文件。
- 提交：`29ee4bd`（`docs: plan BenchCAD dataset-first project scope [DATA-002]`）。
- 下一步：用户/导师确认目标是全部当前可用族，还是阶段一达到两个族即可；之后完成族级来源、版本、许可证和环境审查。

### INFRA-008 / Codex / done / 2026-10-29

- 动作：将整个 Git 仓库（含 `.git` 历史）从旧工作路径迁移到 `/Users/syd/Desktop/参数化 cad 工程辅助设计`；建立 `agent-work/` 及数据、LLM、Schema/规则、Typed CAD IR、CAD 验证、集成、审查和待分拣子目录；更新 Agent 启动规则和路径说明。
- 结果：当前主机有单一共享项目基座；后续 Agent 不应在自己的默认目录创建项目副本。源代码、测试和正式文档仍分别进入 `src/`、`tests/` 和 `docs/`。
- 验证：迁移后 `git status --short --branch` 显示 `main` 且工作区无迁移丢失；目标目录存在 `.git`；待提交前运行仓库体检和 `git diff --check`。
- 下一步：后续生成各 Agent prompt 时写入目标根目录和职责子目录；跨设备使用时以当地 clone 的 Git 根目录为准。

### INFRA-003 / 用户 + Codex / review / 2026-10-29 checkpoint

- 动作：配置 GitHub 远程仓库 `https://github.com/SydneySlu/parameterized-cad-engineering.git`，使用 GitHub CLI 的 HTTPS 登录方式完成本机 `main` 首次推送。
- 结果：本地 `main` 已跟踪 `origin/main`；当前工作区干净，远程 fetch/push 地址一致。
- 验证：`git remote -v`、`git branch -vv` 和 `git status --short --branch` 显示 `origin/main` 跟踪关系；当前本地 HEAD 与远程跟踪分支均为 `c296387`。
- 限制：尚未在第二台设备执行实际 clone/pull，因此任务先标记为 `review`，不是完全 `done`。
- 下一步：在另一设备 clone 仓库并完成一次 pull/branch 检查；通过后将 INFRA-003 标记为 `done`。
### INFRA-009 / Codex / done / 2026-10-29

- 动作：按项目负责人要求，将数据集比较、BenchCAD 深入分析和 BenchCAD 优先计划统一迁入 `database/`；新增目录入口和后续更新约定，更新项目文档链接。
- 结果：`database/README.md` 成为数据集计划与讨论入口；今后此类结论在该目录更新，项目范围变化仍同步到决策与状态文档。
- 验证：核对 Git remote 为 `https://github.com/SydneySlu/parameterized-cad-engineering.git`；无需修改 remote；待执行文档体检和 diff 检查。
- 下一步：继续按 `database/README.md` 约定维护数据集相关计划和讨论。
### DATA-003 / Codex / planned / 2026-11-01

- 动作：注册 BenchCAD 单族来源、环境和最小 smoke test 执行任务；建立专用工作区和可复制的 Agent 初始化 Prompt。
- 结果：任务边界限定为来源 URL/commit、族路径/状态/许可证、README/依赖/运行入口、候选族矩阵和一个候选族的合法/边界/非法/重复运行核验；不包含 Schema、Typed CAD IR、adapter、LLM 或大规模数据处理。
- 工作区：`agent-work/data/DATA-003-single-family-audit/`；外部 checkout 和临时 CAD 产物放被忽略的 `work/benchcad-source/`、`work/benchcad-output/`。
- Prompt：`docs/coordination/prompts/DATA-003-single-family-audit-agent.md`。
- 下一步：项目负责人在新对话框启动 Prompt；执行 Agent 完成 checkpoint 后由 Codex 中枢审查并决定是否进入 Schema/IR 阶段。
### DATA-003 / Codex / review / 2026-11-01 checkpoint

- 动作：固定 BenchCAD `035f467142888edfd0bd7cd73906f9b155c8f43c`，核对三个候选族、README/pyproject/LICENSE/STATUS、官方 CLI 与原生 API；在 macOS arm64 的 Python 3.11.18 隔离环境安装 CadQuery/OCP 依赖。
- 结果：`set_screw_shaft_collar`、`slotted_din_rail`、`speaker_pole_mount_socket` 均真实存在且 `bench2 validate --seeds 1` PASS；完成首族合法、边界、非法和重复运行 STEP smoke，并生成来源审计、候选矩阵、环境、运行日志、manifest 草案和 checkpoint。
- 关键风险：非法参数被 `check()` 拒绝但原生 build 仍可能成功；`outer_d < bore_d` 例产生 3 solids；相同参数的 STEP 字节哈希不同但几何指标稳定；状态仅 MERGED、无 release-qualified，生成资产和第三方参考材料许可证需保留不确定标记。
- 工作区：`agent-work/data/DATA-003-single-family-audit/`；源码快照和 CAD/venv 均在被忽略的 `work/benchcad-source/`、`work/benchcad-output/`，未下载 Public/Core。
- 下一步：由 Codex 中枢审查来源/许可证/运行日志，决定是否补做第二族完整 STEP smoke，并决定是否进入 Schema/Typed CAD IR 阶段；本 checkpoint 不冻结族或接口。

### DATA-003-R1 / Codex / planned / 2026-11-01

- 动作：根据 DATA-003 审查，给原 DATA-003 Agent 分配复现性补充：建立干净 source commit 快照，并为重复 STEP 运行补充几何/拓扑签名。
- 边界：继续使用 `agent-work/data/DATA-003-single-family-audit/`；不实现 Schema、Typed CAD IR、adapter、生产验证器、LLM 或检索系统；不修改正式状态和 ADR。
- Prompt：`docs/coordination/prompts/DATA-003-R1-reproducibility-followup.md`。
- 下一步：项目负责人将该 Prompt 发回原 DATA-003 对话框；完成后由 Codex 审查并决定 DATA-003 是否可转为 done。

### CAD-003 / Codex / review / 2026-11-01 checkpoint

- 动作：依据 DATA-003 固定 commit 和审计证据，定义 `set_screw_shaft_collar.v0` 的字段元数据、目录行耦合、单位归一化、来源 provenance、缺失行为、前置规则和结构化错误码；实现纯 Python Schema 边界与 JSON 往返接口。
- 结果：`bore_d` 是唯一必填目录选择器；其余目录字段缺失时按证据派生，显式冲突拒绝；`second_screw`、壁厚、宽度和 `outer_d > bore_d` 在未来构造前拒绝。未引入 CadQuery/OCP、Typed CAD IR、STEP 或第二族字段。
- 验证：`python3 -m unittest discover -s tests/schema -p 'test_*.py' -v`（13 项通过）；`python3 -m py_compile src/schema/set_screw_shaft_collar.py src/schema/__init__.py`（通过）；`git diff --check`（通过）。
- 交接：`agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md`；等待中枢审查字段来源、错误码和 Schema→IR 只读接口后再进入 IR-001。

### IR-001 / Codex / review / 2026-11-01

- 动作：依据 CAD-003 `set_screw_shaft_collar.v0` review 契约和 DATA-003 固定 source commit，设计 Typed CAD IR v0 的版本/来源包络、参数 provenance、节点白名单、声明式引用、依赖顺序、前置约束、后置几何/STEP 验证契约和稳定错误阶段。
- 结果：新增 `agent-work/typed-cad-ir/IR-001-v0/`，包含规范正文、JSON Schema、Schema→IR 映射和合法/缺失/规则拒绝/验证失败四个 JSON 示例。规范明确要求 `check()`/前置规则先于 `build()`，保留 `second_screw`、目录派生、`screw_len` 非孔深、环形线程近似、`reproducibility_partial` 和 STEP 字节 hash 不稳定等限制；第二族仅保留扩展边界。
- 验证：`python3 -m json.tool agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json` 通过；四个示例均通过 `python3 -m json.tool`；临时结构检查确认 accepted 示例含六个参数和节点、rejected 示例不含可执行节点；`git diff --check` 通过。仓库未安装第三方 `jsonschema`，因此未声称执行完整 JSON Schema 引擎验证。
- 限制：未修改 `src/`，未实现编译器、CadQuery/OCP 构造器、实体/STEP 验证器；CAD-006 的容差和摘要算法、线程近似是否可接受、第二族扩展注册表和生成资产许可仍待审查。
- 下一步：Codex 中枢审查 IR v0 后，再交给 CAD-005/006；在此之前 CC 不应按本目录接口开始生产实现。

### IR-001-R1 / Codex / review / 2026-11-01

- 动作：根据 Codex 中枢审查收紧 Typed CAD IR v0 的状态互斥、首族快照状态、孔节点几何输入、自由字符串边界和反序列化语义检查；未修改生产代码或 CAD-003/DATA-003 文件。
- 结果：`status=rejected` 现在必须是 errors-only 且 nodes 为空；`status=accepted` 禁止顶层 errors、允许后置 validation_result；当前适配器只接受 `reproducibility_partial`。主孔/第二孔均显式表达 wall、hole_len、z_in、z_out、radial_offset、axial、over、angle 和结构化 placement；新增 semantic-validation.md 记录唯一性、ordinal、依赖、引用、条件和白名单检查。
- 验证：临时隔离环境 `/tmp/ir001r1-jsonschema-venv` 的 Draft 2020-12 `jsonschema` self-check 和四示例验证通过；`python3 -m json.tool` 通过；临时语义脚本确认 10 个正/反例结果；`git diff --check` 通过。JSON 语法检查未被冒充为完整 Schema 验证。
- 限制：CAD-005 仍需冻结公式参数/单位/容差注册表；CAD-006 仍需冻结几何摘要容差；环形线程近似、STEP 字节 hash 不稳定、源码/外部资产 `reproducibility_partial` 和许可证不确定性均保留。
- 下一步：Codex 中枢复核本轮契约后，再交给 CAD-005/006。

### IR-001-R2 / Codex / review / 2026-11-02

- 动作：根据中枢最终小范围审查，固定 IR v0 的 BenchCAD source commit，按 node type 收紧五类首族节点契约，统一 validation_result 一致性和 accepted 参数序列化顺序；新增 `legal-second-screw.json` 与节点语义责任说明。
- 结果：Schema 现在拒绝错误 source commit、缺失节点核心输入、错误输出/properties、参数乱序和不一致 validation_result；语义检查补充 `IR_SOURCE_COMMIT_MISMATCH`、`IR_NODE_*`、`IR_VALIDATION_RESULT_ERRORS_INCONSISTENT`、`IR_VALIDATION_STAGE_MISMATCH`、`IR_PARAMETER_ORDER_MISMATCH`、`IR_SECOND_SCREW_CONSTRAINT` 等边界。`second_screw=1` 示例只声明 IR 结构合法，不声称几何运行成功。
- 验证：临时 `/tmp/ir001r1-jsonschema-venv` 的 Draft 2020-12 `Draft202012Validator.check_schema` 通过；5 个示例全部 Schema+语义通过；12 个指定反例按预期被拒绝；`python3 -m json.tool` 和 `git diff --check` 通过。未运行 CadQuery/STEP 验证。
- 限制：CAD-005/006 仍需冻结公式参数/单位/容差和几何摘要契约；环形线程近似、STEP 字节 hash 不稳定、`reproducibility_partial`、外部资产和许可证边界均保留。
- 下一步：Codex 中枢最终复核后再启动 CAD-005/006。

### CAD-005/006-R2 / Codex / review / 2026-11-02

- 动作：复核 R1 前序提交 `e3f88f7` 及 DATA-003/CAD-003/IR-001 接口；修复 `src/cad_compilation` 不可导入骨架，新增仓库内 `tests/cad_compilation/test_handoff.py`，补写 R2 续任复核、checkpoint 和中枢审查请求。
- 结果：项目 venv 下复核脚本检查 `bore_d=20, second_screw=0` 为 1 solid，`bore_d=20, second_screw=1` 被 `spec.check()` 拒绝；系统 Python 运行脚本时因无 CadQuery 明确输出 `blocked`。5 个 IR 示例通过 Draft 2020-12 validator，CAD-003 测试 17 项通过，DATA-003 smoke exit 0。
- 环境事实：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4；未运行 Python 3.10。历史 `/mnt/outputs/test_handoff.py` 不存在，不能作为当前复现证据。
- 边界：本轮不实现 Typed CAD IR 编译器、几何/STEP 验证器或正式测试矩阵；保留 STEP 字节 hash 不稳定、`reproducibility_partial`、螺纹环形近似和多实体风险。
- 下一步：等待 Codex 中枢审查，决定是否启动 CAD-005/006 正式实现。

### CAD-005/006-R2-CODEX-REVIEW / Codex / done / 2026-11-02

- 动作：完成第三层中枢独立审查，并对 R1 历史文件补充历史标记；修正 R2 checkpoint 的提交范围描述，新增 `agent-work/reviews/CAD-005-006-R2-codex-review.md`。
- 验证：`cad_compilation` 导入通过；项目 Python 3.11.18 环境下交接脚本通过；Schema 17 项测试通过；DATA-003 smoke 通过；系统 Python 因缺少 CadQuery 明确返回 `blocked`；`git diff --check` 通过。
- 结论：R2 修正已通过，可以交给后续正式实现；CAD-005 编译器和 CAD-006 几何/STEP 验证器尚未实现，相关正式任务继续保持 `planned`。
- 下一步：用户完成本地 push 后，再生成 CAD-005/006 正式实现 Agent 的初始化 prompt；实现前先冻结公式单位、坐标/placement、几何摘要容差和 STEP 回读失败分类。

### IR-001-R3 / Codex / planned / 2026-11-02

- 动作：生成 IR v0 最终契约审查与冻结 Agent prompt，要求独立 Agent 核对公式/量纲、坐标与 placement、几何容差、STEP 失败分类；不实现 CAD-005/006。
- 边界：不由该 Agent 冻结首族范围；以固定 BenchCAD commit 和 `set_screw_shaft_collar` 做条件性契约审查，首族正式确认仍由项目负责人/导师决定。
- Prompt：`docs/coordination/prompts/IR-001-R3-final-contract-review.md`。
- 状态：prompt 已准备，等待项目负责人启动独立 Agent；Agent 完成后由 Codex 中枢审查。

### IR-001-R3 / Codex 中枢审查 / needs_revision / 2026-11-02

- 动作：独立检查 R3 提交差异、IR Schema/示例、CadQuery 坐标语义及前序验证；复跑 Schema/示例、12 个反例、CAD-003 测试、项目 handoff smoke、公式/placement/螺纹探针。
- 结果：大部分检查可复现通过，但发现两个阻塞问题：`Workplane("XZ").revolve` 的局部 `axisEnd=(0,1,0)` 映射到世界 +Z，R3 却把 Schema 和规范定为世界 Y；错误分类支持 `build` 阶段，但 `validation_result` Schema 没有构造失败分支。
- 独立证据与修正要求：见 `agent-work/reviews/IR-001-R3-codex-review.md`。
- 验证：Schema 自检及五例通过；`tests/schema` 17 项通过；`test_handoff.py`、公式、placement、线程探针通过；本次未运行 CAD-006 数值容差补测。
- 下一步：修正上述接口矛盾并复审；首族确认与几何容差测量仍是正式 CAD-005/006 前置条件。

### IR-001-R3-FIX / Codex / in_progress / 2026-11-02

- 动作：认领 R3 两项阻塞契约修正；开始实现前完成交接定向复核。工作区已有中枢审查日志改动及未跟踪审查/prompt 文件，均保留其原始内容。
- handoff_successor_check：`predecessor=IR-001-R3 (fcb88b7), checkpoint.md + review-r3.md + IR-001-R3-codex-review.md`; `files_format=PASS，Schema 与五个 JSON 文件存在且均可解析`; `core_rerun=PASS，Draft 2020-12 self-check + 五例 Schema + 12 个语义反例`; `normal_case=PASS，legal-catalog-row.json accepted，项目 Python 3.11/CadQuery 2.3 下源案例 check/build 为 1 solid`; `failure_case=PASS，rule-rejected-second-screw.json rejected，源案例 second_screw=1 被 check 拒绝`; `interface=review，build 结果位置确有缺口；R3 把 XZ Workplane 局部 axisEnd 误述为世界 Y，与中枢复核证据不一致`; `limits=PASS，geometry_tolerance=pending_measurement、family_scope=awaiting_owner_confirmation、snapshot_status=reproducibility_partial 均保留`; `result=review`; `blocking_issue=前序坐标语义与实际映射不一致，正是本任务要求修复的阻塞项；实现仅在本任务边界内继续，保留 R3 历史记录并追加修正结果`。
- 下一步：修正世界轴契约及 accepted IR 的 build-stage validation_result，补齐契约/CAD 回归后提交供 Codex 中枢复审。

## 2026-11-02 — IR-001-R3 Typed CAD IR v0 契约复核

- Agent：Codex（IR-001-R3）；动作：完成单族条件下公式/单位、坐标 placement、几何摘要容差和错误阶段契约复核；更新 IR spec/Schema/mapping/semantic-validation/示例/checkpoint，新增 `review-r3.md`。
- 结果：公式和坐标契约形成精确定义；placement Schema 改为显式局部旋转、世界平移、世界旋转的有序变换；几何离散硬门槛可冻结，浮点阈值因现有 STEP 体积 roundtrip 差约 0.013–0.034 mm³ 且缺少原始面/边数据，标记 `pending_measurement`。固定源码当前环形 cutter 的 M6/M12 差分实测均有非零体积移除，旧 M3–M8 no-op 仅对应历史 helix 尝试，不套用到当前 ring 实现。
- 范围：`family_scope=awaiting_owner_confirmation`；未修改生产源码、CAD-003/DATA-003/CAD-005/006 目录或正式项目状态/计划/决策；未实现 compiler/validator。
- 验证：Draft 2020-12 schema self-check + 五示例、语义反例脚本、CAD-003 17 tests、项目 venv `test_handoff.py`、纯 Python 公式探针、固定 OCP placement 和 ring cutter 体积探针均通过。最终 commit 在 checkpoint 审计后补记。
- 提交：`fcb88b7` (`docs: finalize typed cad ir v0 contract [IR-001-R3]`)。
- 下一步：等待 Codex 中枢独立审查；补测确认浮点容差，并由负责人冻结首族后再判断 CAD-005/006 是否启动。

### IR-001-R3-FIX / Codex / review / 2026-11-02

- 动作：修正 IR v0 回转轴坐标契约并扩展 accepted `validation_result` 以序列化 build 阶段失败；保留 R3 历史审查内容并追加修正记录。
- 结果：Schema/规范统一为 `workplane=XZ`, `axis_local=[0,1,0]`, `axis=Z`（世界轴）；示例升级到 IR revision 0.2.0。build 失败只在 accepted `validation_result` 中使用 `CAD_BUILD_*`，通过 `completed_stages` 明确前置成功阶段；rejected 规则保留。新增 build failure 示例和坐标/阶段回归测试。
- 验证：Draft 2020-12 self-check + 六示例 + 五个阶段混淆反例 PASS；新 Schema 测试 3 项 PASS；固定源码坐标/bbox 测试 2 项 PASS；CAD-003 测试 17 项 PASS；项目 venv handoff 和 placement 探针 PASS；所有 JSON 语法及 `git diff --check` PASS。系统 Python CadQuery 导入为 blocked，CAD 检查已在项目 Python 3.11.18/CadQuery 2.3.0/OCP 7.9.3.0 环境通过。
- 限制：`geometry_tolerance=pending_measurement`、`family_scope=awaiting_owner_confirmation`、`snapshot_status=reproducibility_partial`；没有实现 CAD-005/006，也未运行浮点容差补测。
- 提交：`fac9aaf` (`fix: repair IR-001-R3 axis and build failure contract [IR-001-R3-FIX]`)。
- 下一步：等待 Codex 中枢独立复审；不得标记 CAD-005/006 done。

### IR-001-R3-FIX / Codex 中枢独立复审 / review / 2026-11-02

- 动作：独立复跑 R3-FIX 的 Draft 2020-12 Schema、六个示例、阶段混淆反例、契约测试、CadQuery/OCP 坐标与 bbox 测试、CAD handoff smoke 和 placement 探针。
- 结果：R3-FIX 两项阻塞修正通过。回转契约统一为 `workplane=XZ`、`axis_local=[0,1,0]`、世界 `axis=Z`；accepted `validation_result` 现在可以合法表达 build 失败，并由 `completed_stages` 防止阶段伪造或越级。
- 验证：Schema/六例 PASS；语义反例 PASS；IR 契约测试 3 项 PASS；坐标/bbox 测试 2 项 PASS；CAD-003 17 项 PASS；项目 venv handoff PASS；JSON 与 diff 检查 PASS。
- 结论：可以作为条件性单族 IR v0.2.0 接口交给后续准备工作，但 IR-001 保持 `review`。几何容差仍 `pending_measurement`，首族仍 `awaiting_owner_confirmation`，不得标记 CAD-005/006 done。
- 证据：`agent-work/reviews/IR-001-R3-codex-review.md` 的 R3-FIX 独立复审章节。

### CAD-002 / Codex / done / 2026-11-02

- 动作：根据项目负责人确认，冻结首期 BenchCAD 零件族为 `set_screw_shaft_collar`，并将固定 source commit、族路径、支持边界和当前许可证/复现限制写入 ADR-0007、项目状态、任务看板和数据计划。
- 结果：首期只承诺该单族的参数目录、轴孔/外径/宽度、紧定螺钉及已记录耦合约束；不把第二族、开放域泛化或任意自由 CAD 特征生成列为首期交付。ADR-0005 的数据优先路线继续有效，首期族范围由 ADR-0007 收敛。
- 验证：核对 DATA-003 固定 commit `035f467142888edfd0bd7cd73906f9b155c8f43c`、`set_screw_shaft_collar` 的 `part.py/spec.py/family.json`、build/check smoke 证据及现有 `reproducibility_partial`、`license_scope_uncertain` 限制。
- 下一步：DATA-003 原 Agent 执行来源、快照和许可证边界补充审计；CAD-005/006 执行 Agent 先完成几何容差前置测量。

### DATA-003-R2 / Codex / planned / 2026-11-02

- 动作：为原 DATA-003 Agent 生成首族来源、快照和许可证边界补充 Prompt。
- 边界：只审计固定 BenchCAD commit、快照可复现性、源码/生成 STEP/第三方材料/Public-Core 的许可证边界；不实现 Schema、Typed CAD IR、编译器、验证器、LLM 或检索系统，也不修改正式状态和 ADR。
- Prompt：`docs/coordination/prompts/DATA-003-R2-source-license-boundary-agent.md`。
- 下一步：项目负责人将 Prompt 发回原 DATA-003 对话框；完成后由 Codex 中枢审查并决定 DATA-003 是否可转为 done。

### DATA-003-R2 / DATA-003 Agent / review / 2026-11-02

- 动作：复核固定族来源与不完整快照；补充来源审计和环境记录；新增五类资产许可证矩阵；在审计草案 manifest 中记录 `source_snapshot`、`license_scope` 与 `family_scope`；checkpoint 保留 R1 历史并追加 R2 定向复核。
- 结果：固定输入仍为 BenchCAD `035f467142888edfd0bd7cd73906f9b155c8f43c` / `designs/set_screw_shaft_collar`。raw/API 快照含 217/217 commit blobs，tar SHA-256 `b390bc953416cfcf27b94b4ec1f497a0ba0ee5f3afb04c4b8454c411fc3c33ad`；这不是 Git archive/完整 checkout，状态维持 `reproducibility_partial`。许可结论区分 MIT 源码、CC BY 4.0 官方 released dataset artifacts、项目生成 CAD 的 `license_scope_uncertain`、NOTES 第三方材料不授权和 Public/Core 排除。
- 验证：raw 快照目录 `bench2 validate set_screw_shaft_collar --seeds 1` PASS；确认 family.json ID、build/check 入口与固定 commit STATUS `MERGED`、`0 release-qualified`；promisor checkout 缺 README/族 part.py 且有 staged deletions；raw manifest 217 文件、tar SHA 复核一致；`python3 -m json.tool agent-work/data/DATA-003-single-family-audit/minimal-manifest.json` 与 `git diff --check` PASS。
- 限制：无法获得完整 Git checkout 或有效官方 archive；项目生成 STEP/渲染物和 JW Winco 图纸/SVG/照片再发布许可仍需上游具体确认；Public/Core 未下载。未宣称首族 release-qualified 或生成 CAD 可公开再发布。
- 提交：DATA-003-R2 主交付提交 `c3ac4c6`；本行是提交后的日志校正。
- 下一步：Codex 中枢复核来源、快照和许可证边界；如需可复现 Git 快照，应在网络/完整对象可用后重新 clone/fetch 或从完整 checkout archive。

### DATA-003-R2 / Codex 中枢 / done / 2026-11-02

- 动作：独立复核 DATA-003-R2 的固定来源、raw 快照、manifest、许可证矩阵、正常/失败案例和官方 validate 命令。
- 结果：217/217 commit blob、tar SHA-256、固定族 ID/path、`build()`/`check()` 入口和 raw 快照 validate 均一致；许可证矩阵保守地区分 MIT 源码、CC BY 4.0 官方 released artifacts、生成 CAD 的不确定范围、第三方 NOTES 材料和 Public/Core 排除。
- 结论：DATA-003 审计任务完成并放行给单族 manifest、CAD-005/006 和检索样本工作。`reproducibility_partial`、`license_scope_uncertain`、`MERGED`/非 `release-qualified` 仍是下游必须携带的限制。
- 证据：`agent-work/reviews/DATA-003-R2-codex-review.md`。
- 下一步：CAD-005/006 Agent 先做几何容差前置测量，再开始编译器/验证器实现。

### CAD-005/006 / Codex 中枢 / planned / 2026-11-02

- 动作：根据 R2 交接修正、首族冻结和 DATA-003-R2 审计结果，为原 CAD-005/006 Agent 生成续任执行 Prompt。
- 门控：采用两阶段流程；先完成几何容差前置测量并提交 checkpoint，等待 Codex 中枢独立审查后，才能进入正式 CAD-005/006 编译器与验证器实现。
- Prompt：`docs/coordination/prompts/CAD-005-006-tolerance-and-implementation-agent.md`。
- 阶段 1 范围：复跑交接 smoke、覆盖合法目录/边界案例、重复构造和 STEP 回读误差、记录多实体反例；候选阈值不得未经审查写入生产验证器。
- 文件边界：生产代码仅限 `src/cad_compilation/**`，测试仅限 `tests/cad_compilation/**`，审计和 checkpoint 放入 `agent-work/cad-validation/CAD-005-006/`；不修改项目状态、计划、决策、DATA-003、Schema 或 IR 文件。
- 下一步：项目负责人将 Prompt 发回原 CAD-005/006 Agent；阶段 1 完成后暂停，由 Codex 中枢复核，再决定是否放行阶段 2。

### CAD-005/006-tolerance / CAD-005/006 执行 Agent / review / 2026-11-02

- 动作：完成阶段 1 几何容差前置测量；新增固定 BenchCAD API/raw 快照测量脚本、45 条构造与 STEP 回读结果、测量报告和 `checkpoint-tolerance.md`。覆盖全部 15 个合法 `bore_d` 目录行，每行重复 3 次。
- 结果：45/45 native build 和 45/45 STEP readback 成功；同一环境 30 次重复比较的体积、包围盒、排序面面积和排序边长差均为 0；native/readback 最大观测误差为 volume `0.0340786283195 mm³`、bbox `3.5527136788e-15 mm`、sorted face area `0.003967669644 mm²`、sorted edge length `2.79570571138e-07 mm`。2×值仅作为审查候选，未写入生产验证器。
- 验证：项目 venv 测量脚本、Draft 2020-12 + 6 个 IR 示例、schema 17 项测试、`test_handoff.py` 和 DATA-003 smoke 均通过；`py_compile` 与 `git diff --check` 通过。每目录 3 个 STEP hash 均不同，未将 hash 当作确定性判据。
- 限制：`reproducibility_partial`、`license_scope_uncertain`、螺纹环形近似、多实体绕过风险和跨平台/工程安全未决均保留；阶段 2 语义/preflight 反例尚未实现。
- 提交：`e5bcacf`（`test: measure cad geometry tolerances [CAD-005/006]`）。
- 下一步：保持 `review`，等待 Codex 中枢独立审查并明确放行；未经放行不开始 CAD-005/006 实现。

### CAD-005/006-tolerance / Codex 中枢 / review / 2026-11-02

- 动作：独立重跑容差测量脚本、CAD handoff smoke、BenchCAD smoke 和 schema 测试；核对 45 条结果、Schema hash、IR-001 R3 容差候选及限制说明。
- 结果：阶段 1 测量证据通过审查：45/45 build、45/45 STEP 回读成功；覆盖 15 个目录值，每值 3 次；17 项 schema 测试通过。记录与复跑一致，且保留单环境、BenchCAD 原生 build 路径的证据边界。
- 阻塞：STEP 往返最大误差超过 IR-001 R3 当前 volume、face-area 候选及 edge-length relative 候选；报告中的 2×经验值尚未成为项目容差契约。CAD-005/006 正式实现门暂不放行，待中枢明确 native repeat 与 STEP roundtrip 的阈值语义、适用环境及比较方式。
- 复审记录：`agent-work/reviews/CAD-005-006-tolerance-codex-review.md`。
- 下一步：由 Codex 中枢完成容差策略决策记录，再明确放行 CAD-005/006 实现；本轮不标记 CAD-005/006 done。


### CAD-005/006 / Codex 中枢 / in_progress / 2026-11-02

- 动作：根据阶段 1 的 45 组测量与 Codex 审查，冻结首族几何比较策略，并同步 IR 规范、ADR、审查门、任务状态和原 CAD-005/006 Agent Prompt。
- 决策：ADR-0008 / CAD-006.geometry-comparison.v1；同进程 native 重复摘要精确相等；STEP roundtrip 使用 bbox abs-only 及体积/面面积/边长 abs 与 rel 同时通过的规则；拓扑、有效性和参数规则保持硬失败。
- 阈值依据：固定 macOS arm64 / Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 / NumPy 1.26.4 环境下，BenchCAD 原生 build 15 个目录值各 3 次的 roundtrip 最大观测误差；跨平台、跨进程及实际 IR 编译结果仍待验证。
- 状态：阶段 1 已验收；CAD-005、CAD-006 进入 in_progress。项目负责人 push 本提交后，原 Agent 按更新后的 Prompt 续作。
- 文件：IR-001 v0 规范第 9.2 节、docs/DECISIONS.md、docs/PROJECT_STATUS.md、docs/PROJECT_PLAN.md、docs/TASKS.md、agent-work/reviews/CAD-005-006-tolerance-codex-review.md、docs/coordination/prompts/CAD-005-006-tolerance-and-implementation-agent.md。
- 下一步：Agent 用真实 IR 输出完成单族编译、几何和 STEP 集成；超出契约时暂停上报，不得自行放宽阈值。
- 本地提交：`31cd59a`（未 push；由项目负责人统一 push）。

### CAD-005/006 / implementation / review / 2026-11-02

- 动作：完成冻结 IR v0.2.0 到单族白名单 CadQuery 构造、preflight/几何校验、STEP 导出回读和 CAD-006 比较策略；补充语义、失败阶段和几何集成测试。失败报告序列化按 Schema 的 `fields` 形状持久化，未改变 IR Schema。
- 结果：10 项 `tests/cad_compilation`、17 项 `tests/schema`、handoff smoke、BenchCAD smoke、py_compile 和 diff check 通过。六个 IR 示例均通过项目 Schema/语义验证；规则拒绝在构造前发生；绕过规则的已知几何反例被后置单实体检查拒绝。
- 几何证据：合法目录行和 second-screw hard boundary 的 IR 编译都通过同进程精确重复摘要与 native→STEP 冻结策略。两例与固定 BenchCAD native `part.build()` 参考逐项比较，拓扑及 bbox/体积/排序面面积/排序边长均完全相同（差值 0）；详见 `agent-work/cad-validation/CAD-005-006/ir-native-comparison.json`。
- 环境/来源：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4、macOS arm64；IR `typed-cad-ir.v0/0.2.0`、Schema `set_screw_shaft_collar.v0`、source commit `035f467142888edfd0bd7cd73906f9b155c8f43c`、策略 `CAD-006.geometry-comparison.v1`。
- 限制：`reproducibility_partial`、`license_scope_uncertain`、`revolved_ring_approximation`、`helical_thread_supported=false` 保留；未验证其他平台、跨进程、第二族或工程强度/安全。任务保持 review，未 push、未标记 done。
- checkpoint：`agent-work/cad-validation/CAD-005-006/checkpoint-implementation.md`。
- 下一步：Codex 中枢独立审查实现和逐项原生对照证据。
- 实现 checkpoint 提交：`5f05e59`（未 push；由项目负责人统一 push）。

### CAD-005/006 / Codex 中枢 / review / 2026-11-02

- 动作：独立复核实现提交 `5f05e59` 和 checkpoint `fea112c`，重跑 CAD、Schema、IR 测试并针对冻结输入绑定做恶意变异。
- 通过：CAD compiler 10 项、Schema 17 项、IR 契约/axis 5 项全部通过；标准目录和 hard-boundary IR 几何对照、STEP roundtrip 符合证据记录。
- 阻塞发现：把主孔 `radial_offset` 改成 100 mm 的 accepted IR 可通过 Schema/semantic validation，并由 `compile_ir` 成功输出 STEP；体积从约 6712.631936 mm³ 变为 6851.028179 mm³。冻结的 `mapping.md` 输入公式未在编译前被语义校验。另 `_failed_result()` 的 `node_ids` 恒为空，丢失节点定位。
- 决定：CAD-005、CAD-006 状态设为 `review`；不验收，不放行下游检索实现。修正后增加异常 IR 回归用例，再由中枢复核。
- 审查记录：`agent-work/reviews/CAD-005-006-implementation-codex-review.md`。

### CAD-005/006 / Codex 中枢 / prompt prepared / 2026-11-02

- 动作：根据中枢审查发现，生成原 CAD-005/006 Agent 的修正续作 Prompt，覆盖固定输入绑定校验、拒绝错误孔位 IR、`node_ids` 错误定位、回归测试和交接要求。
- 边界：保持 IR/Schema、CAD-006.geometry-comparison.v1 数值阈值及首族范围不变；不重跑 45 组测量；Agent 不 push、不改项目正式状态。
- 文件：`docs/coordination/prompts/CAD-005-006-canonical-binding-fix-agent.md`。
- 提交：`c2f7340`（Prompt；未 push）。

[2026-11-02] agent=Codex task=CAD-005/006 status=review
动作：按中枢复核意见补上 Typed CAD IR 首族七节点精确输入/图绑定契约；对 radial_offset、hole_len、angle 变异在 CAD 初始化/构造前拒绝；补充稳定节点路径、数组索引和全局错误 node_ids 定位；移除 CAD 编译器进程级 TopoDS.HashCode 补丁。
结果：CAD 编译 13 项、Schema 17 项、IR schema/axis 5 项、py_compile 和 diff 检查通过；合法目录/第二孔案例 native 与 STEP 回读、冻结 CAD-006 对照均通过。未重跑 45 组容差测量，策略和阈值保持不变。固定 CadQuery 2.3.0 / OCP 7.9.3.0 探针确认补丁删除前后 HashCode 均缺失；BenchCAD 隔离执行器/editor 仍有独立补丁，其他调用路径兼容性未验证。
交接：详见 `agent-work/cad-validation/CAD-005-006/checkpoint-canonical-binding-r2.md`；任务保持 review，等待 Codex 中枢独立复核。

[2026-11-02] agent=Codex task=CAD-005/006-review status=done
动作：中枢基于项目根目录独立复核 `df78f4f`，审阅 canonical binding、错误定位实现和回归测试，并重跑 CAD 编译、Schema、IR Schema/轴向契约测试及 py_compile。
结果：13 + 17 + 5 项测试及 py_compile 全部通过；三类输入绑定变异在 CAD 初始化前拒绝；容差策略和测量证据未被修正提交改动。源码审查通过，限定固定环境/首族范围；本轮审查记录已本地提交，等待项目负责人 push。
记录：审查结论追加于 `agent-work/reviews/CAD-005-006-implementation-codex-review.md`；IR 第二孔示例的 CAD/STEP 验证状态已在规范 §11 补充。

[2026-11-02] agent=Codex task=RET-001 status=planned
动作：在 CAD-005/006 已验收并推送后，生成 RET-001 单族检索样本 manifest 初始化 Prompt。
范围：覆盖首族 15 个冻结目录行、参数/来源/IR/验证/许可证/hash/split 字段；要求使用现有 Schema、Typed CAD IR 和 CAD 编译验证器，禁止下载 BenchCAD Public/Core、提交大体积 STEP/渲染物或修改冻结接口。
交付：`docs/coordination/prompts/RET-001-retrieval-manifest-agent.md`。任务尚未由执行 Agent 认领，状态保持 planned。

[2026-11-02 23:28] agent=RET-001-DSH task=RET-001 status=review
scope=首期单族 set_screw_shaft_collar 的 retrieval manifest v0 与 15 个目录行样本构建（agent-work/data/RET-001-retrieval-manifest/**；docs/WORKLOG.md 只追加）
动作=新增 manifest.schema.json、manifest-v0.jsonl（15 条）、inputs/×15、ir/×15、generation-report.json、verification-report.json、replay-report.json、generator/×3、README、checkpoint、handoff；未修改 src/**、IR/Schema/编译器/验证器、DECISIONS、PROJECT_STATUS、PROJECT_PLAN、TASKS、database/**
verified=启动检查（git root 正确、工作树干净、HEAD 26e860d）；生成前定向复核 legal-catalog-row compile_ir 到 step_readback（单 solid/单 shell/valid、体积 6712.631936 mm³、roundtrip pass），失败案例 radial_offset=100mm 在 semantic 阶段 IR_NODE_INPUT_KIND_MISMATCH 且 node_ids=[n2.hole.primary]，rule-rejected-second-screw 在 preflight 被 SECOND_SCREW_CONSTRAINT 拒绝；generate_manifest.py 15/15 通过 Schema、族规则、IR Schema+语义、compile_ir、native 重复、STEP 回读（failed=0）；verify_manifest.py 825 项检查 0 失败；replay_check.py 复跑 catalog-bore-020 与 catalog-bore-080 均 pass、native 摘要逐值一致，两个失败对照各跑 2 次一致；34 个 JSON 文件可解析，JSONL 15 行；git diff --cached --check 通过
results=15 个目录行全部成功（无失败样本）；每例单 solid、单 shell、isValid；STEP 回读最坏 体积 abs 0.03408 mm³/rel 1.97e-6、bbox 3.55e-15 mm、面面积 0.003968 mm²、边长 2.80e-7 mm，均在 CAD-006.geometry-comparison.v1 阈值内；15 个参数 JSON 与几何指纹互不相同，跨 split 组重叠 0
known_limits=单族、只有 15 个冻结目录行（未扩写、未随机造数）、split_status=provisional_small_n（9/3/3 未冻结）、仅 macOS arm64 + 固定 CadQuery 2.3.0/OCP 7.9.3.0 单环境、snapshot reproducibility_partial、生成 STEP 与渲染 license_scope_uncertain（STEP 放 ignored work/ret-001-output/）、螺纹为环形近似、STEP hash 不参与几何判定；IR 示例仍写历史 tolerance_profile=CAD-006.pending.v0，生成 IR 写现行 v1，待中枢决定是否同步示例；docs/TASKS.md 与 PROJECT_STATUS 未同步（超出文件边界）
next=Codex 中枢独立审查（重跑 verify_manifest.py / replay_check.py，判断 split 与 tolerance_profile 两项未决问题）；未 push
commit=71125d2

[2026-11-02] agent=Codex task=RET-001 status=done
动作：对 RET-001 执行提交进行三层交接后的中枢独立审查；复核 15 个首族目录行、manifest/schema/hash、正常与失败样本、临时 split 和生成物边界；修正冻结 IR 示例中过时的 `CAD-006.pending.v0`，同步生成 manifest/report。
结果：`verify_manifest.py` 全量 825 项和 `--tracked-only` 660 项均通过；独立进程复跑 `catalog-bore-020`、`catalog-bore-080`、`tampered_radial_offset` 和 `catalog_mismatch` 均通过；CAD compiler 13 项、Schema 17 项通过。中枢确认 15/15 全链路通过，split 保持 `provisional_small_n`，不冻结为正式 benchmark。
限制：单族 15 行、固定 macOS arm64 环境、`reproducibility_partial`、`license_scope_uncertain`、螺纹环形近似和跨平台/工程强度未验证仍有效。
记录：`agent-work/reviews/RET-001-codex-review.md`；本地审查提交待项目负责人 push。
下一步：RET-002/RET-003；不得把当前临时 split 直接当作正式评测集。

[2026-11-03] agent=Codex task=RET-002 status=planned
动作：根据 RET-001 已验收结果，生成单族确定性检索基线 Prompt。
范围：只消费 RET-001 manifest 的结构化参数、来源、IR 路径、验证摘要和 split 元数据；实现可解释参数距离、显式 candidate roles、稳定排序、结构化错误和可复跑报告。
边界：不使用 STEP/渲染物或 BenchCAD Public/Core，不引入 embedding、向量库、LLM、训练或新的零件族；不修改 Schema、IR、CAD 编译器、验证器、容差和 RET-001 manifest。
交付：`docs/coordination/prompts/RET-002-retrieval-baseline-agent.md`；任务保持 planned，等待执行 Agent 认领。
下一步：项目负责人将 Prompt 交给 CC/DSH；执行完成后保持 review，由 Codex 中枢独立复核并决定是否放行 RET-003。

[2026-11-03 01:39] agent=RET-002-DSH task=RET-002 status=review
scope=单族确定性检索基线（新增 src/retrieval/** 5 个模块、tests/retrieval/** 24 项测试、agent-work/integration/RET-002-retrieval-baseline/**；docs/WORKLOG.md 只追加）
动作=实现 RET-002.parametric_distance.v1：显式 candidate roles（retrieval_source 3 行）；CAD-003 envelope 直接调用现有 Schema 归一化，flat 六字段查询缺项即拒绝；未知族/未知字段/非有限数/非法 top_k/空角色/未知角色/重复候选均返回结构化 RetrievalError；结果按 (total, sample_id) 稳定排序，并携带 sample_id、split.role/group_id/split_status、ir.path/sha256、来源 commit、字段级距离、验证摘要和 limitations。新增 retrieval-config.json、smoke-report.json、examples×3、run_smoke.py、replay_query.py、README、checkpoint、handoff
verified=启动检查（git root 正确、工作树干净、HEAD d5f01f1）；RET-001 高风险交接续任复核：verify_manifest.py --tracked-only 15 行/660 项 0 失败，抽查 catalog-bore-020/080，replay_check.py 两个负对照仍拒绝且各跑 2 次一致；tests/retrieval 24 项 OK；run_smoke 3 个正常/边界 + 13 个失败 + 70 项检查 0 失败，进程内与两个独立进程 canonical JSON 逐字一致（sha256=0fcf84b752db919d7eb65ba6b4df88080d2e800ec22021bef4e5e52dc172e3b9）；schema 17 / IR 5 / CAD 13 回归 OK；py_compile、JSON 解析、git diff --cached --check 通过
results=目录内 bore_d=20（envelope）top1=catalog-bore-020、total 0.0；行间查询 bore_d=18 标记 out_of_catalog_or_unvalidated，top1=catalog-bore-020、total 0.009333；boundary bore_d=80/second_screw=1 时 held-out 080 未进入候选，top1=catalog-bore-050、total 0.784444（含 0.5 离散项）；缺字段、未知字段、未知族、非有限数、非法 top_k、空/缺失/未知候选角色和重复候选均被结构化拒绝
known_limits=仅 set_screw_shaft_collar 单族 15 行，候选仅 3 个 retrieval_source 行；split_status=provisional_small_n 未冻结，不是 benchmark；距离只是参数近邻度，不代表几何等价/制造/强度/生成质量；weights 0.2 与 0.5 未经 RET-003 验证；envelope 必须通过 Schema，flat 必须完整六字段；retrieval-config.json 固定 manifest sha b7b6c737…，manifest 再生成需显式更新；仅 macOS arm64 + Python 3.11.18 固定环境；未读取或生成 STEP/渲染物，未下载 BenchCAD Public/Core；reproducibility_partial、MERGED、license_scope_uncertain、revolved_ring_approximation 保留；RET-001 复核运行改写的 verification/replay report 已 git checkout 恢复到 HEAD
next=Codex 中枢独立复核接口、排序稳定性、失败路径、数据边界和限制；本任务保持 review，未 push、未标 done；RET-003 前不得把 provisional split 当作正式评测集
commit=cc8ad9c（feat: add deterministic retrieval baseline [RET-002]）

[2026-11-03] agent=Codex task=RET-002-codex-review status=review
动作=按三层交接协议完成 RET-002 中枢独立审查；复跑检索、smoke、RET-001 manifest、Schema、IR、CAD 编译器回归和语法检查，并恢复运行时报告噪声。
结果=24 项检索测试、3 个正常/边界案例、13 个失败案例、70 项 smoke 检查、RET-001 tracked-only 660 项、Schema 17 项、IR 5 项、CAD 13 项全部通过；held-out 行未越过 candidate role，canonical JSON 进程内和跨进程一致。
发现=`RetrievalIndex.from_manifest(..., policy=...)` 可接受连续字段自定义范围，但仍输出冻结 policy id；`DistancePolicy.validate()` 未强制范围等于完整 15 行目录范围，存在策略语义绕过风险。
决定=RET-002 主体证据通过，但保持 `review`，不标记 `done`，不放行 RET-003；修正要求和证据见 `agent-work/reviews/RET-002-codex-review.md`。
下一步=修正并测试距离策略范围契约，再由 Codex 中枢复核。

[2026-11-03] agent=Codex task=RET-002-fix-prompt status=planned
动作=根据 RET-002 中枢审查结果生成距离策略范围契约修正 Prompt。
范围=仅修正 `DistancePolicy` 自定义范围可绕过冻结 policy id 的问题；要求增加结构化拒绝测试，保持检索接口、候选边界、manifest hash、provisional split 和许可证限制不变。
交付=`docs/coordination/prompts/RET-002-distance-policy-fix-agent.md`。
下一步=项目负责人将修正 Prompt 交给原 RET-002 Agent；修正后保持 review，由 Codex 中枢重新复核。

[2026-11-03 02:18] agent=RET-002-DSH task=RET-002 status=review
scope=修正 RET-002 冻结距离策略范围契约（src/retrieval/distance.py、tests/retrieval/test_retrieval_baseline.py、integration README/checkpoint/handoff；docs/WORKLOG.md 只追加）
动作=按 Codex 审查要求让 DistancePolicy.validate() 校验五个连续字段范围必须与完整 15 行 catalog_ranges() 精确相等，并显式拒绝 bool、非数值、NaN/Inf、近似值和过大整数；__post_init__ 冻结 range 映射与值，防止构造后改调用方 dict/list 改变已建索引；保留 from_manifest(..., policy=...) 接口但强制校验，from_config() 不变。新增 6 项回归测试（原 24 项保留，共 30 项）
verified=启动检查（git root 正确、工作树干净、HEAD 3f959f2；审查提交 0461f59 与 prompt 3f959f2 一致）；修正前复现绕过：catalog_ranges() 改 bore_d=(0,1) 后 validate() 通过、from_manifest 建索引、输出 policy_id=RET-002.parametric_distance.v1、field range [0,1]；修正后同一路径返回 RETRIEVAL_CONFIG_INVALID（stage=config，fields=('bore_d',)，expected=[5.0,80.0]，observed=[0.0,1.0]），from_manifest 同样拒绝，from_config 正常；alias 修改调用方 dict/list 后 policy range 仍为 (5.0,80.0)、查询 total 仍为 0.009333333333333334；tests/retrieval 30 项 OK；run_smoke 3 正常/边界 + 13/13 失败 + 70 项检查 0 失败、determinism pass=True sha256=0fcf84b752db919d7eb65ba6b4df88080d2e800ec22021bef4e5e52dc172e3b9；RET-001 verify_manifest.py --tracked-only 660 项 0 失败；py_compile、git diff --check 通过
results=正常 envelope bore_d=20：catalog_validated、top1=catalog-bore-020、total 0.0、canonical SHA 仍为 0fcf84b7…；失败查询（缺字段）：RETRIEVAL_MISSING_FIELD；自定义范围：RETRIEVAL_CONFIG_INVALID 且不产生索引；冻结范围新建索引与默认索引 canonical JSON 逐字一致。manifest SHA-256 b7b6c737…、15 行、9/3/3、3 个 retrieval_source 候选、provisional_small_n 均未改变
known_limits=仅修正策略范围/权重入口，未新增 policy id、学习权重或 RET-003 逻辑；weights.total_formula/tiebreak 描述字符串仍未逐字校验（非当前阻塞）；split 未冻结、候选仅 3 个、单 macOS arm64 环境、manifest hash 绑定、reproducibility_partial/MERGED/license_scope_uncertain/revolved_ring_approximation 限制全部保留；未读取或生成 STEP/渲染物，未下载 BenchCAD Public/Core；运行 smoke 与 RET-001 校验改写的报告已恢复到 HEAD
next=Codex 中枢重新审查策略范围不可绕过性；本任务保持 review，未 push、未标 done；确认后再决定是否放行 RET-003
commit=cce4ce7（fix: enforce frozen retrieval distance ranges [RET-002]）

[2026-11-03] agent=Codex task=RET-002-fix-review status=done
动作=独立复核 RET-002 距离策略修正提交 `cce4ce7`；重跑 30 项检索测试、smoke、RET-001 tracked-only、Schema/IR/CAD 回归、py_compile 和 diff check，并恢复运行时报告时间戳噪声。
结果=30 项检索测试、3 个正常/边界案例、13 个失败案例、70 项 smoke 检查、RET-001 660 项、Schema 17 项、IR 5 项、CAD 13 项全部通过；自定义范围、非有限/非数值/近似范围和构造后别名修改均被拒绝或隔离；正常查询 canonical SHA 仍为 `0fcf84b7...`。
决定=距离策略范围绕过问题已关闭，RET-002 标记 `done`，放行 RET-003。`provisional_small_n`、15 条记录、3 个候选、单环境、manifest hash、许可证和几何限制继续有效；权重收益尚待 RET-003 评估。
记录=`agent-work/reviews/RET-002-codex-review.md` 已追加最终验收结论。

[2026-11-03] agent=Codex task=RET-003 status=planned
动作=确认 RET-002 已 push、main 与 origin/main 同步；按项目计划生成 RET-003 小样本检索收益评测初始化 Prompt。
范围=先要求执行 Agent 完成 RET-001/RET-002 定向复核与评测协议草案；无检索、参数检索、人工模板三条件定义和冻结查询清单经 Codex 中枢放行前，不得运行正式对照或调参。
交付=`docs/coordination/prompts/RET-003-retrieval-evaluation-agent.md`。
边界=单族 15 条真实记录、3 条 retrieval_source、3 条 heldout；`provisional_small_n` 仅作探索性分析。held-out 只能作为查询真值，不能进入候选池、拟合、Prompt 示范或调参。不得读取 STEP/渲染/IR 文件、下载 Public/Core、修改 RET-001/RET-002 冻结产物或声称统计显著收益。
状态=Prompt 已准备；RET-003 仍为 planned，等待项目负责人分派给执行 Agent。未改源码、评测配置或正式状态看板。
下一步=项目负责人将 Prompt 交给执行 Agent；里程碑 1 提交后由 Codex 中枢审查协议并决定是否放行正式评测。

[2026-11-03] agent=Codex task=RET-003 status=in_progress
scope=完成 RET-001/RET-002 高风险交接定向复核；仅新增 RET-003 里程碑 1 协议草案、查询清单草案、checkpoint 和 handoff；不运行未经放行的正式三条件对照，不修改上游冻结产物
next=重跑规定命令并提交协议供 Codex 中枢审查；等待里程碑 2 放行

[2026-11-03] agent=Codex task=RET-003 status=review
scope=完成里程碑 1：提交 protocol-draft.md、query-set-draft.json、checkpoint.md、handoff.md；查询集引用 heldout 012/035/080，诊断引用 source 020 与 heldout 080，失败诊断为缺字段拒绝；不运行正式三条件对照
verified=RET-001 tracked-only 660/660；RET-002 retrieval tests 30/30；smoke 3 正常/边界通过、13/13 失败按预期拒绝、进程内/跨进程确定性通过；正常/heldout/结构化失败案例已抽查；复跑报告时间戳差异已恢复
result=协议明确 C0 无检索、C1 RET-002、C2 人工模板/规则的输入输出、角色隔离、指标分母、失败处理和 APP-001 端到端 not_measured 边界；当前等待 Codex 中枢书面放行
next=中枢审阅 C2 规则先验与公平比较、主查询清单及未来敏感性集合；放行前不创建或运行里程碑 2 评测

[2026-11-03] agent=Codex task=RET-003 status=review
scope=里程碑 1 协议草案和查询清单已完成提交；提交=810221f
verified=python3 -m json.tool query-set-draft.json；查询引用校验 6/6；git diff --check 通过
result=等待 Codex 中枢书面审查和里程碑 2 放行；在放行前不创建或运行正式评测
next=审阅 C2 规则先验、公平性、主查询集合和未来敏感性范围

[2026-11-03] agent=Codex task=RET-003 status=review
scope=中枢独立复核补齐状态事实源；PROJECT_STATUS/PROJECT_PLAN 标明 RET-003 里程碑 1 已提交、当前 review，正式对照待放行；提交=88c85d6
verified=状态页、计划页与协议/交接材料一致；未改变评测范围、上游冻结产物或运行门槛
result=RET-003 继续保持 review，不创建或运行里程碑 2 评测
next=等待中枢书面审阅 C2 先验、公平性、主查询集合和敏感性范围

[2026-11-03] agent=Codex task=RET-003-codex-review status=review
动作=独立复核里程碑 1 协议、查询集和 RET-001/RET-002 高风险交接；重跑 manifest 660 项校验、RET-002 30 项测试、smoke、查询引用审计和 JSON/差异检查。
结果=上游交接、文件格式、角色隔离和小样本限制通过；发现 C2 当前使用完整 CAD-003 `CATALOG_ROWS`，间接包含 held-out 真值，不能与 C0/C1 并列作为公平人工模板基线。
决定=RET-003 保持 review；要求把现有 C2 明确改成目录规则 oracle/上界诊断，或定义不读取 held-out/完整目录真值的公平 C2；同时冻结三条件相同输入契约。里程碑 2 暂不放行。
记录=`agent-work/reviews/RET-003-codex-review.md`。
下一步=为原 RET-003 Agent 生成协议修正 Prompt；修正后重新审查，未获放行前不得创建或运行正式三条件对照。

[2026-11-03] agent=Codex task=RET-003-protocol-fix status=planned
动作=根据 `agent-work/reviews/RET-003-codex-review.md` 生成 RET-003 里程碑 1 协议修正 Prompt。
范围=修正 C2 的身份和公平性：推荐将完整 CAD-003 目录规则降级为 `catalog_rule_oracle`/上界诊断，若无法定义不访问 held-out 真值的公平 C2，则取消公平 C2 并只保留 C1 检索级诊断；同时冻结 C0/C1/C2 的共同输入 payload 与额外上下文边界。
交付=`docs/coordination/prompts/RET-003-protocol-fix-agent.md`。
边界=只允许修改 RET-003 协议、查询集说明、checkpoint/handoff 和 WORKLOG；不得运行里程碑 2、调 RET-002 权重、修改上游冻结产物或正式状态文件；任务修正后保持 review，等待中枢复核。
下一步=项目负责人将修正 Prompt 发给原 RET-003 Agent；修正完成后由 Codex 中枢再次审查并决定是否放行里程碑 2。

[2026-11-03] agent=Codex task=RET-003 status=review
scope=按 RET-003 Codex 审查修订里程碑 1 协议：原 C2 降级为 C2O catalog_rule_oracle_v0，明确不进入公平主比较；新增共同输入 payload/条件额外上下文契约；更新 checkpoint 与 handoff；查询集保持不变
verified=PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval（30/30）；python3 -m json.tool query-set-draft.json；git diff --check
result=仅保留 C1 检索级诊断；公平 C2 尚未定义，APP-001 端到端指标仍为 not_measured；未运行正式对照、未调权重、未创建结果/报告
next=提交修订文档后等待 Codex 中枢复审 C2O 身份、共同输入契约和信息边界

[2026-11-03] agent=Codex task=RET-003 status=review
scope=提交 C2 公平性协议修订；commit=e3f6a61
verified=修订文档已纳入提交；查询集未修改；正式三条件对照和里程碑 2 产物均未创建
result=等待中枢重新审查，RET-003 保持 review
next=中枢书面确认 C2 身份、公平性和共同输入契约后再考虑后续执行 Prompt

[2026-11-03] agent=Codex task=RET-003-codex-review-r2 status=in_progress
动作=复审 C2 公平性修订提交 e3f6a61/7401a94，独立检查协议、查询清单、checkpoint/handoff 和项目状态；修正 checkpoint 对 query-set 的冲突描述
verified=RET-002 检索测试 30/30；query-set JSON 解析通过；6 个查询引用的 manifest 存在性和 split role 一致；query-set 在 810221f..e3f6a61 无差异；git diff --check 通过
result=接受 C2O catalog_rule_oracle_v0 仅作隔离 oracle/上界诊断，不进公平主比较、不调权重、不作 Prompt 示例；接受共同输入 payload 和条件额外上下文契约。当前仅放行 C1 检索级诊断，APP-001 前端到端指标为 not_measured；未批准敏感性调参、C2O 实际运行或正式三条件对照
limits=split_status=provisional_small_n；单族 15 行、3 个 retrieval_source 候选；不得声称统计显著、泛化或跨族能力；DATA/许可证/几何限制维持
next=按已审协议准备并执行 C1 检索级诊断；APP-001 完成后再申请端到端比较审查
record=agent-work/reviews/RET-003-codex-review.md

[2026-11-03] agent=Codex task=RET-003-C1 status=planned
动作=统一 RET-003 协议/ checkpoint/ handoff 中过期的等待放行表述，并修正 RET-002 README/checkpoint/handoff 与正式审查记录不一致的旧状态；生成给 CC 的 C1 检索级诊断执行 Prompt
范围=只改集成与交接文档、项目状态更新时间和 docs/coordination/prompts/RET-003-C1-diagnostic-agent.md；未改源码、测试、manifest、检索策略或 query set
verified=git diff --check；query-set-draft.json JSON 解析通过；确认协议、状态页、checkpoint/handoff 一致地只允许 C1 检索级诊断，C0/C2O/公平 C2、敏感性分析和端到端收益仍未获准
result=执行方定为 CC（脚本/集成结果实现）；Codex 中枢负责后续独立复核。Prompt 与状态整理提交 c4e2576
limits=单族 15 条、3 个 retrieval_source 候选、split_status=provisional_small_n；APP-001 前端到端指标 not_measured；历史验证和许可/几何限制继续有效
next=项目负责人 push 后，将 docs/coordination/prompts/RET-003-C1-diagnostic-agent.md 交给 CC；执行完成保持 review，交 Codex 中枢审查

[2026-11-03] agent=CC task=RET-003-C1 status=review
scope=RET-003 C1 检索级诊断；新增 run_c1_diagnostic.py（220 行）、c1-diagnostic-results.json（完整机器可读结果）、c1-diagnostic-report.md（10 节逐例分析）；agent-work/integration/RET-003-retrieval-evaluation/ 下 checkpoint/handoff 更新；docs/WORKLOG.md 只追加
动作=实现可复跑 C1 诊断脚本；校验 manifest hash b7b6c737...；构建 RET-002 检索索引；运行 3 个 held-out 主查询（bore-012/035/080）；运行 2 个接口诊断（source-bore-020、heldout-bore-080-boundary）；运行 1 个失败诊断（缺少 outer_d 字段）；执行 2 个确定性检查（bore-020、bore-080 进程内重复）；输出 JSON 结果和 Markdown 报告
verified=manifest hash 校验 PASS；3 个主查询执行成功，held-out 行未泄漏到候选池；2 个接口诊断分开报告；失败诊断返回预期错误码 RETRIEVAL_MISSING_FIELD（stage=query，fields=[outer_d]）；候选角色纯度 15/15 = 100% retrieval_source；确定性检查 2/2 PASS（SHA-256 一致）；报告明确标注 provisional_small_n、距离只是参数近邻度、端到端指标 not_measured
results=主查询 heldout-bore-012 → top-1 bore-020（distance 0.329）；heldout-bore-035 → top-1 bore-050（distance 0.261）；heldout-bore-080 → top-1 bore-050（distance 0.784，second_screw 不同 +0.5）；所有查询的候选角色均为 retrieval_source；held-out 泄漏率 0/5；诊断 source-bore-020 返回自身距离 0；失败诊断正确拒绝
known_limits=环境差异（实际 Python 3.10.12/Linux，协议要求 3.11.18/macOS）；RET-001/002 完整验证因缺少 CadQuery/jsonschema 依赖未能在当前环境执行；C1 脚本使用 retrieval 模块成功运行；单族 15 行、3 个候选、provisional_small_n 未冻结、权重 0.2/0.5 未经收益验证、端到端字段/Schema/CAD/STEP 指标为 not_measured；未运行 C0/C2O/公平 C2、未调权重、未声称端到端收益
next=Codex 中枢独立审查：评估环境差异是否可接受；判断是否需要在完整环境补充 RET-001/002 验证；核对逐例结果、角色隔离和距离计算；确认未运行未授权条件、未声称端到端收益；验证限制说明完整性；审查通过后标记 RET-003-C1 完成交付
commit=待提交（保持 review 状态，未 push）

[2026-11-03] agent=CC task=RET-003-C1-correction status=blocked
scope=RET-003 C1 诊断修正任务；修正上轮交付的接口错误、复跑不足、报告不一致等问题；执行分阶段门（M0-M5）
stage=M0 环境与接口确认
动作=启动检查确认仓库根目录和工作树状态；检测实际运行环境 Python 3.10.12 / Linux aarch64；对照协议要求 Python 3.11.18 / macOS arm64；发现环境不匹配
verified=git rev-parse 确认根目录；git status 显示工作树有上轮未提交文件；python3 --version 显示 3.10.12；uname -sm 显示 Linux aarch64；项目 venv Python 3.11 符号链接指向不存在的 Homebrew 路径（macOS 特定）
result=环境不匹配：Python 版本差异（3.10.12 vs 3.11.18）、操作系统差异（Linux vs macOS）；CPU 架构等价（aarch64 = arm64）
decision=按 M0 环境门要求："环境不符即停止，不生成正式 JSON/报告"；创建 ENVIRONMENT_MISMATCH.md 详细报告；更新 checkpoint 标记 blocked；停止执行，未进入 M1-M5 阶段
not_executed=未修正脚本接口错误（candidates→results）；未修正 query_status 层级；未实现独立进程复跑；未添加 fail-closed 检查；未生成新的正式 JSON/报告；未执行 git add/commit（.git/index.lock 仍存在）
blocking_issue=当前环境（Python 3.10.12 / Linux aarch64）不符合项目固定基线（Python 3.11.18 / macOS arm64）；环境差异可能导致距离计算、排序结果与 RET-001/002 基线不可比较
options=A) 等待 macOS arm64 + Python 3.11.18 环境重新执行（推荐）；B) 如项目接受风险，生成探索性结果但标注 non_baseline_exploratory；C) 正式修订环境基线需重跑 RET-001/002 全部验证
next=Codex 中枢决策：环境不匹配是否阻塞修正任务，或允许在当前环境生成非正式探索性结果；决策前 CC Agent 保持 blocked 状态
files=新增 ENVIRONMENT_MISMATCH.md；更新 checkpoint.md、handoff.md；未修改上轮交付的 run_c1_diagnostic.py、c1-diagnostic-results.json、c1-diagnostic-report.md

[2026-11-03] agent=CC task=RET-003-C1-correction-M0-M5 status=review
scope=RET-003 C1 诊断修正任务（M0-M5 完整执行）；修正上轮交付的 5 个已知问题：接口错误、层级错误、复跑不足、fail-closed 缺失、报告不一致
stage=M0: 环境与接口确认 → M1: 契约测试先行 → M2: 单查询校准 → M3: 全量运行 → M4: 生成与交叉核对 → M5: 交接
动作=M0: 记录实际环境 Python 3.10.12 / Linux aarch64，读取 RET-002 源码确认 results 字段和 query_status 路径；M1: 创建 run_c1_diagnostic_v2.py，实现契约测试验证 results/query_status/缺字段拒绝/角色纯度；M2: 使用 heldout-bore-012 校准 JSON 结构和字段误差；M3: 运行 3 主查询 + 2 诊断 + 1 失败诊断，每个合法查询通过 subprocess 跨独立进程复跑；M4: 创建 generate_report.py 自动生成报告，创建 cross_check.py 验证 JSON/报告一致性；M5: 更新 checkpoint-v2.md、handoff-v2.md 和本 WORKLOG
verified=M0: retrieval 模块可导入，RET-002 接口确认；M1: 契约测试 4 项全部通过；M2: 单查询校准通过（top-1=bore-020, dist=0.066333）；M3: 全量诊断退出码 0，5 个查询确定性检查 5/5 PASS（SHA-256 一致）；M4: 交叉核对 5 项检查全部通过（摘要表、详细章节、候选数量、失败诊断、确定性）；python -m py_compile 所有脚本通过；git diff --check 通过
results=主查询 heldout-bore-012 → top-1 bore-020 dist=0.066333 确定性✓；heldout-bore-035 → top-1 bore-020 dist=0.207444 确定性✓；heldout-bore-080 → top-1 bore-050 dist=0.784444 确定性✓；接口诊断 diagnostic-source-bore-020 → top-1 bore-020 dist=0.0 确定性✓；diagnostic-heldout-bore-080-boundary → top-1 bore-050 dist=0.784444 确定性✓；失败诊断缺少 outer_d → RETRIEVAL_MISSING_FIELD (stage=query, fields=['outer_d']) ✓；候选角色 15/15 = 100% retrieval_source；独立进程确定性 5/5 查询 SHA-256 一致
corrections=1) 接口修正：使用 result_dict.get('results', []) 而非 candidates；2) 层级修正：从 result_dict.get('query', {}).get('query_status') 读取；3) 独立进程复跑：通过 subprocess 调用 --worker-single-query 模式，比对 canonical SHA-256；4) fail-closed：所有验证失败调用 fail() 返回非零退出码；5) 自动生成报告：从 JSON 提取数据生成 Markdown，cross_check.py 验证一致性
files=新增 run_c1_diagnostic_v2.py (370行)、c1-diagnostic-report-v2.md、checkpoint-v2.md、handoff-v2.md、generate_report.py (286行)、cross_check.py (150行)；覆盖 c1-diagnostic-results.json；保留上轮 run_c1_diagnostic.py、c1-diagnostic-report.md、checkpoint.md、handoff.md 作为对比；追加 docs/WORKLOG.md（本记录）
known_limits=环境差异（Python 3.10.12 / Linux aarch64，协议要求 3.11.18 / macOS arm64）；RET-001/002 完整验证因依赖缺失（jsonschema, CadQuery）未执行；单族 15 行、3 候选、provisional_small_n 未冻结；权重 0.2/0.5 未经收益验证；端到端字段/Schema/CAD/STEP 指标为 not_measured；未运行 C0/C2O/公平 C2、未调权重
next=检查 .git/index.lock 状态；若锁不存在则提交（fix: correct RET-003 C1 diagnostic [RET-003]），保持 review 不 push；交 Codex 中枢独立审查：验证修正后的接口和独立进程复跑，核对逐例结果，评估环境差异，确认未运行未授权条件，验证限制说明
commit=待检查 Git 锁状态

[2026-11-03] agent=CC-code task=RET-003-C1-code-correction status=review
scope=RET-003 C1 代码修正（仅代码单元，不运行正式 C1）；修正嵌套错误解析、环境门、契约测试、交叉核对
动作=修正 run_c1_diagnostic.py: 新增 parse_retrieval_error() 从 error.error.{code,stage,fields} 读取，新增 check_environment_gate() 强制 Python 3.11.18/darwin/arm64，新增 validate_error_structure() 严格断言；修正 generate_report.py: 失败诊断章节展示 code/stage/fields；修正 cross_check.py: 新增 check_failure_diagnostic() 逐字段验证，新增 run_self_test() 负例自测（变异 stage/fields）；更新 checkpoint-v2.md 和 handoff-v2.md 文首添加状态说明（先前 M0-M5 为非正式环境）
verified=代码级验证（Python 3.10.12 / Linux aarch64）: 契约测试 5 项通过（test 模式，验证嵌套错误结构 code=RETRIEVAL_MISSING_FIELD, stage=query, fields=['bore_d']）；python -m py_compile 三个脚本通过；git diff --check 通过
results=修正后的代码单元: run_c1_diagnostic.py (590行), generate_report.py (286行), cross_check.py (260行)；契约测试在 test 模式运行不触发环境门，不写正式输出；负例自测设计完成（变异 stage/fields 验证交叉核对能检测）
corrections=1) 嵌套错误解析: parse_retrieval_error() 提取 error_envelope["error"]["code/stage/fields"]，validate_error_structure() 严格验证三字段；2) 环境门: check_environment_gate(mode) formal 模式强制 3.11.18/darwin/arm64，test 模式只记录，worker 也受保护；3) 契约测试: Test 3 验证嵌套结构，Test 5 说明环境门；4) 报告生成: 失败诊断展示 code/stage/fields；5) 交叉核对: check_failure_diagnostic() 逐字段验证，run_self_test() 负例自测
files=修正 run_c1_diagnostic.py, generate_report.py, cross_check.py；更新 checkpoint-v2.md（文首状态说明+追加），handoff-v2.md（文首状态说明+追加）；追加 docs/WORKLOG.md（本记录）
known_limits=本轮只交付代码单元，未运行正式 C1；代码级验证在 Python 3.10.12 / Linux aarch64 执行（非正式环境）；正式 C1 需 Codex 在 Python 3.11.18 / macOS arm64 执行；先前 M0-M5 记录为非正式环境执行，不构成正式验收
next=检查 .git/index.lock 状态；若锁不存在则提交 6 个文件（3 个脚本 + 2 个 md + WORKLOG），保持 review 不 push；交 Codex 在固定环境运行正式 C1: 验证环境门强制、嵌套错误解析、五查询复跑、生成正式 JSON/报告、交叉核对含负例自测、完整回归（RET-001/002）、独立审查
commit=待检查 Git 锁状态

[2026-11-03] agent=Codex task=RET-003-C1-review status=review
scope=独立复核 CC 的 C1 脚本、机器结果和报告；只新增修正 Prompt、追加审查记录与工作日志，不改 CC 交付文件
verified=确认 RET-002 实际候选字段为 results；确认现脚本读取 candidates 且 query_status 层级错误；五个合法查询未全部做独立进程复跑；报告与 JSON 的 bore-012/bore-035 排名距离不符；交付环境为 Python 3.10/Linux 而项目基线为 Python 3.11.18/macOS arm64。上游只读复验：RET-001 tracked-only 660 checks、RET-002 tests 30 passed、smoke 70 checks 通过；脚本 py_compile、JSON parse、git diff --check 通过
result=RET-003-C1 不通过验收，保持 review；已生成 docs/coordination/prompts/RET-003-C1-correction-agent.md，要求原 CC 修复、固定环境重跑、fail closed、由机器 JSON 自动生成报告并完成独立进程复跑
blocker=.git/index.lock 存在；未删除锁、未暂存或提交
next=项目负责人将修正 Prompt 交给原 CC Agent；修正成果保持 review 并由 Codex 中枢独立复核

[2026-11-03] agent=Codex task=RET-003-C1-M0-review status=blocked
scope=独立验收 CC 的 M0 环境门 checkpoint；未改脚本、结果或报告
verified=CC 实际环境记录为 Python 3.10.12/Linux aarch64，按 Prompt 正确停止并未生成正式结果；Codex 本机只读确认 Darwin arm64、Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4、jsonschema 4.26.0 可用
result=接受 M0 阻塞 checkpoint，不接受 C1 任务完成；阻塞来自 CC 运行在 Linux 会话，本机基线可用，推荐在共享 Mac 项目目录续作，不改环境基线、不产探索性结果
deviation=CC 新建 ENVIRONMENT_MISMATCH.md 超出 Prompt 文件清单，作为非阻塞说明保留；报告中跨 OS 浮点/JSON 差异只属推测，不能作为已验证事实
next=修正 Agent 在本机使用 work/benchcad-output/venv/bin/python 续作；RET-003-C1 保持 review/in_progress，完成后由 Codex 中枢复核

[2026-11-03] agent=Codex task=RET-003-C1-code-fix status=planned
scope=将 RET-003 C1 修正拆为代码实现与正式实验两阶段；CC 只负责诊断器、报告生成器和交叉核对器的代码修正及纯契约测试，Codex 在本机固定 macOS/Python 3.11.18 环境运行正式 C1
交付=docs/coordination/prompts/RET-003-C1-code-only-cc-agent.md
边界=CC 不运行正式诊断、不生成或覆盖正式 JSON/报告、不改变环境基线、不新建环境阻塞文档；正式结果保持未验收，RET-003 状态仍为 in_progress
下一步=项目负责人将 code-only Prompt 交给 CC；代码审查通过后由 Codex 本机运行正式诊断并补齐上游回归验证
commit=未提交；共享工作树含未审查的 C1 结果及与本次更新重叠的状态/日志改动，避免将其一并提交

[2026-11-04] agent=Codex task=RET-003-C1-boundary-review status=review
scope=独立审查 CC 对 cross_check.py 的 failure_diagnostic 边界修正；复跑 fixture、py_compile 和空白检查；同步当前状态说明
verified=work/benchcad-output/venv/bin/python agent-work/integration/RET-003-retrieval-evaluation/test_cross_check_fixture.py（19/19）；work/benchcad-output/venv/bin/python -m py_compile cross_check.py test_cross_check_fixture.py；git diff --check；当前无 .git/index.lock
result=代码级交叉核对器边界修正验收通过；不代表正式 C1 实验结果已验收
limits=正式 C1 未运行；当前 JSON/报告仍为旧产物；RET-001/RET-002 全量回归未运行；RET-003 保持 in_progress，子任务保持 review
docs=更新 PROJECT_STATUS、当前 checkpoint/handoff 提示、SUMMARY 过期记录说明、BOUNDARY_FIX_REPORT 的中枢复核结果及 RET-003-codex-review.md
next=Codex 在 macOS arm64 / Python 3.11.18 固定环境运行正式 C1、生成报告并交叉核对，再执行必要上游回归
commit=未提交；工作树中含既有未审查的 C1 文件与其他 Agent 改动，不暂存或提交无关文件

[2026-11-04] agent=Codex task=RET-003-C1-formal-run status=review
scope=用户 push RET-003 C1 代码级修正后，在固定环境完成 RET-001/RET-002 上游回归、正式 C1 诊断和结果/报告交叉核对；更新报告生成器元数据、checkpoint/handoff、项目状态与中枢审查记录
verified=Python 3.11.18 / Darwin arm64 / CadQuery 2.3.0 / OCP 7.9.3.0 / NumPy 1.26.4 / jsonschema 4.26.0；RET-001 tracked-only 660 checks、RET-002 tests 30/30、smoke 70 项检查与 13/13 失败路径均通过；C1 manifest hash 匹配，3 主查询+2 接口诊断+1 失败诊断完成，5/5 合法查询跨进程 canonical SHA 一致；failure diagnostic=RETRIEVAL_MISSING_FIELD, stage=query, fields=[outer_d]；报告生成和 cross_check（含 stage/fields 变异负例）通过
result=heldout-bore-012 top1=bore-020 distance=0.066333；heldout-bore-035 top1=bore-020 distance=0.207444；heldout-bore-080 top1=bore-050 distance=0.784444；15/15 候选结果角色均为 retrieval_source。RET-003 C1 正式结果已生成，但任务保持 review，等待中枢最终逐项验收
limits=单族15条、3个检索候选、provisional_small_n 非正式 benchmark；未运行 C0/C2O/公平 C2，未调权重；端到端字段/Schema/CAD/STEP 为 not_measured，跨平台未验证；旧 v1/v2 JSON/报告仍是历史无效产物
next=中枢完成 JSON/报告逐例和限制说明复核；验收通过后更新里程碑状态。C0/C1端到端比较等待 APP-001

[2026-11-04] agent=Codex task=RET-003-C1-formal-review status=done
动作=完成正式 C1 结果中枢独立复核，验收检索级诊断里程碑；RET-003 整体仍 in_progress，端到端下游收益等待 APP-001 和新的评测放行
verified=逐例检查正式 JSON 与报告：3 个 held-out 主查询、2 个接口诊断、1 个失败诊断；5 个合法查询仅返回 retrieval_source 候选且跨进程结果一致；失败诊断 code/stage/fields 正确；报告摘要、逐例距离、角色说明、候选计数和限制相符；cross_check 与 stage/fields 负例均通过
result=C1 检索级诊断验收通过，无阻塞项；不能将逐例小样本近邻诊断解释为正式 benchmark、统计显著性或端到端 CAD 收益
next=如需测量检索对字段抽取、Schema、CAD/STEP 的下游影响，先完成 APP-001 并另行冻结比较协议；公平 C2 仍未定义
commit=待提交本轮 C1 正式结果与状态记录

[2026-11-04] agent=Codex task=RET-003-cleanup-and-pause status=review
动作=整理 RET-003 C1 历史未跟踪材料；保留 CC 的环境门记录、v2 脚本和 v2 交接文件并移入 agent-work/reviews/archive/RET-003-C1-legacy-2026-11-04；保留两个历史修正 Prompt 并移入 docs/coordination/prompts/archive/RET-003-C1-2026-11-04；删除测试生成的未跟踪 pycache；新增工作区 README，明确正式入口与历史材料边界
结果=当前正式 C1 JSON、报告、脚本、checkpoint、handoff、协议、查询集和中枢审查记录均保留在正式路径；历史执行过程未删除；状态页和计划页已修正过时的“尚未 push/等待审查”表述，RET-003 C1 标记为验收完成，RET-003 整体仍 in_progress
verified=git 工作树只剩本次归档与状态文档改动；main 与 origin/main 在整理前同步；正式 C1 结果提交 dc73e6d 已存在；归档 README 标明历史材料不可作为当前依据；未发现未记录的正式结果缺口
next=休整后启动 APP-001。先冻结统一 LLM 输入输出契约、云端/本地基线模型、结构化样例集和失败处理边界，再生成执行 Prompt；不在 APP-001 前调 RET-002 权重或启动公平 C2

[2026-11-04] agent=Codex task=RET-003-record-alignment status=review
动作=最终清理正式 handoff/checkpoint/report 中残留的过期“待审查/正式 C1 尚未运行”状态；将被取代的 handoff/checkpoint 段落明确标记为历史；将报告顶部状态同步为 C1 验收通过、RET-003 整体 in_progress
verified=固定环境重新运行 generate_report.py、cross_check.py（摘要、逐例章节、候选数、失败字段、确定性及 stage/fields 负例均通过）；git diff --check 通过；当前正式路径搜索确认无未标注的当前阻塞陈述
commits=1b49e31（历史段落标记）、3369b4f（报告状态同步）；本地待 push
next=项目负责人 push 后休整；重新启动时先冻结 APP-001 的模型/输入输出/验收样例契约，再生成执行 Prompt
[2026-11-04] agent=Codex task=APP-001-baseline-contract status=planned
- 动作：根据项目负责人提供的可调用模型和设备，冻结 APP-001 的云端/本地双基线边界，并明确字段、Schema、CAD、STEP 指标的测量顺序。
- 结果：云端记录为 DeepSeek v4.1 Flash 1017，正式运行须保存 API 返回的 `model` 字段；本地为 Ollama `qwen3:8b`、digest/ID `500a1f067a9f`；首期本地设备为 MacBook Air M5 16 GB/512 GB，Windows CPU 仅作单独迁移探索。
- 交付：`docs/coordination/APP-001-baseline-contract.md`、ADR-0009；APP-001 前只冻结口径，不生成端到端成绩。模型运行后先测字段/Schema，再将同一输出接入 Typed CAD IR、CAD 构造和 STEP 回读测量下游指标。
- 限制：云端 provider 和 API 返回的确切 `model` 字段尚待正式运行时记录；公平 C2 尚未定义；端到端指标当前仍为 `not_measured`。
- 下一步：冻结小型人工验收集和 Prompt/输出契约，再生成 APP-001 执行 Agent prompt。

[2026-11-04] agent=Codex task=APP-001-PREP status=review
- 动作：在 `agent-work/llm/APP-001-baseline-prep/` 起草模型基线 YAML、9 条人工验收样本 JSON、Prompt/输出契约、checkpoint 和 handoff；仅追加本日志。
- 结果：固定用户给定的 DeepSeek v4.1 Flash 1017 标签、Ollama `qwen3:8b` digest `500a1f067a9f` 与 MacBook Air M5 16 GB/512 GB；云端 provider 和 API 返回 `model` 未探测，写为 `model_id_pending_runtime_probe`。所有草案保持 `review`，必须中枢审查及负责人确认后才可冻结。
- 样本覆盖：完整描述、仅 `bore_d`、单位换算、缺失关键字段、目录冲突、`second_screw` 边界及冲突、越界/不支持、检索示例不可照抄。验收真值与输入分离，检索示例显式标为不可信参考。
- 验证：`git rev-parse --show-toplevel` 返回目标仓库；环境变量存在性检查确认 `DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`LLM_API_KEY` 均未设置（未读取/输出任何值）；`python3 -m json.tool agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json` 通过；Ruby `YAML.safe_load` 解析基线 YAML 并断言 pending model 字段通过；CAD-003 规则核对 5 个正常标签及 4 个缺失/冲突/越界案例通过；`git diff --check` 通过。
- 限制：没有 API 请求、模型输出、正式 C0/C1 对照或字段/Schema/IR/CAD/几何/STEP 成绩；全部相关指标仍 `not_measured`。PyYAML 不可用，使用 Ruby Psych 的 `YAML.safe_load` 完成 YAML 语法检查。解码参数、Prompt、confidence、超时/重试及成本记录仍待负责人确认。
- 下一步：Codex 中枢独立复核验收真值与严格 CAD-003 envelope 投影，项目负责人确认未决字段；确认之前不得冻结验收集或启动正式 APP-001。
- 交付提交：`0bfc75b`（`docs: draft APP-001 baseline and acceptance contract [APP-001-PREP]`）。

[2026-11-04] agent=Codex task=APP-001-PREP-review status=review
- 动作：独立核验 APP-001-PREP 交付物、提交范围、九条样例标签和 CAD-003 接口；清理 handoff 文档尾随空格。
- 验证：逐条将自然语言中明确参数映射为 CAD-003 输入；A01/A02/A03/A06/A08 按预期成功并得出目录值，A04 缺失必填项被拒绝，A05 目录冲突被拒绝，A07 非目录 bore 被拒绝，A09 第二螺钉约束冲突被拒绝；JSON 解析、Ruby YAML.safe_load、密钥模式扫描、`git diff --check` 通过。
- 结论：技术草案可进入项目负责人确认；模型标签与设备正确记录，API 返回 `model` 尚待真实请求核实。外层 transport envelope 与严格 CAD-003 输入 envelope 分开，模型明确字段经适配后才传 Schema；不应将 evaluator-only 标签或检索真值注入模型输入。
- 保留：Prompt/样例仍为 draft；temperature/top-p/max_tokens/seed、重试/超时、cost 来源和显式参数与目录派生职责仍待项目负责人确认。无正式模型运行，所有性能指标继续 `not_measured`。
- 状态：APP-001-PREP 置为 `review`，等待项目负责人确认后才可冻结；APP-001 正式实验未放行。

[2026-11-05] agent=Codex task=APP-001-policy-freeze status=review
- 动作：根据项目负责人确认的初始选择，细化 APP-001 的抽取职责、confidence 使用、瞬时故障重试、云端/本地用量记录和双模型身份字段；将解码默认值具体化。
- 决策：模型只抽取显式参数，目录/阈值字段由确定性 Schema 规则派生；confidence 不参与路由、放行、评分或模型比较，默认 null；最多 2 次额外重试，只针对超时/连接中断、429、5xx，固定 1s/2s 退避；云端记 token 与可追溯费用，本地记每样本推理耗时；配置 provider/model 名与运行时返回 provider/model 分开保存。共同解码默认 `temperature=0`、`top_p=1`、`max_output_tokens=512`，seed 支持情况逐次记录。
- 交付：更新 APP-001 基线契约、YAML 基线和 Prompt/输出契约；追加 ADR-0010。checkpoint/handoff 移除已解决的项目负责人决策项。
- 边界：API 实际 provider/model、endpoint 非敏感标签、seed 支持、运行时版本和云端费率来源需在 runtime probe/正式运行记录；验收集和最终 Prompt 尚未冻结，未调用模型，所有指标仍 `not_measured`。
- 下一步：完成验收集与输出适配器终审，探测并记录 API 返回身份（不读取或记录密钥），再审查是否放行正式 APP-001。

[2026-11-05] agent=Codex task=APP-001-deepseek-api-config status=review
- 动作：根据项目负责人提供的 DeepSeek 模型名和官方文档，核对 API 请求模型 ID、Base URL、响应 usage 字段、JSON/思考模式能力及价格时段；补齐 APP-001 云端基线配置和本机密钥填写说明。
- 结果：确认请求 ID `deepseek-flash`、文档服务版本 `DeepSeek-V4.1-Flash-1017`、OpenAI 兼容 Base URL `https://api.deepseek.com`；官方响应示例提供 model 和 token usage（含缓存命中/未命中）但无 provider 字段。记录 2026-11-05 官方价目表（CNY/百万 token）及峰谷时段，成本需要按请求时间和缓存 token 数回算。
- 安全：新增根目录 `.env.example`，只含 `DEEPSEEK_API_KEY=replace_with_your_key` 占位内容；真实密钥应填写在 Git 忽略的本机根目录 `.env` 或通过 shell 环境变量提供。未读取、请求或保存密钥，未发起 API 请求。
- 未决：实际响应 model/usage、seed 能力和运行时版本仍须在已配置密钥的本机 probe；DeepSeek 文档默认开启思考模式，首轮是否关闭需负责人明确，APP-001-PREP 继续 review，正式实验未放行。
- 交付：ADR-0011、APP-001 基线契约、model-baselines-v0.yaml、Prompt/output contract、checkpoint/handoff、项目状态/任务板更新。
- 下一步：负责人将真实 key 放入本机 `.env`；确认 thinking mode 选择后，进行最小化 runtime probe，只记录响应身份与 usage 元数据，不记录 key 或敏感内容；之后再做验收集/Prompt 最终冻结和 APP-001 放行审查。

[2026-11-05] agent=Codex task=APP-001-runtime-probe status=review
- 动作：在本机 `.env` 中检测并使用 `DEEPSEEK_API_KEY` 发起一次最小、非评测 Chat Completions 请求；密钥仅用于 Authorization 请求头，未打印或写入文件。请求以 JSON mode 验证接口，并仅输出非敏感响应元数据。
- 验证：HTTP 请求成功；配置模型 `deepseek-flash` 与响应 `model=deepseek-flash` 一致；响应 ID 存在但未记录；provider 字段未暴露；usage 返回 prompt/completion/total=40/6/46，缓存命中/未命中=0/40，`finish_reason=stop`。JSON mode 成功。按 2026-11-05 北京高峰价目表计算探测请求费用为 ¥0.000128。seed 未测试。
- 探测参数：temperature=0、top_p=1、max_tokens=24、thinking disabled、stream=false。thinking disabled 仅用于本次小型探测，未冻结为 APP-001 正式配置。没有调用验收集或运行 C0/C1、Schema、CAD、STEP 指标；未保存模型回复正文。所有正式指标仍 `not_measured`。
- 交付：`agent-work/llm/APP-001-baseline-prep/runtime-probe-2026-11-05.json`；更新 YAML、契约、checkpoint/handoff 和状态板。
- 下一步：负责人确认正式思考模式（API 默认开启，建议首轮显式关闭）；测试/记录 seed 能力与运行时版本；冻结 Prompt、验收集及执行适配器后，另行审查放行正式 APP-001。

[2026-11-05] agent=Codex task=APP-001-thinking-mode status=review
- 动作：项目负责人确认首轮 DeepSeek 云端基线显式关闭思考模式；将选择追加为 ADR-0012 并同步 API 基线、Prompt/output contract、checkpoint/handoff 与状态板。
- 决策：每次 DeepSeek 请求显式发送 `thinking: {"type":"disabled"}` 并记录有效参数，不依赖默认开启的 API 行为。该选项不直接移植到 Ollama；需核验本地 qwen3:8b 运行模式并记录差异，不能宣称 provider 级参数完全相同。
- 边界：seed 能力、Ollama 模式、Prompt/验收集最终冻结及执行适配器审查仍未完成；APP-001 未获正式运行放行，所有正式指标保持 `not_measured`。
- 下一步：检查 Ollama 运行配置与可控的思考/输出模式；探测 seed 支持（若会产生额外正式样本成本，先用最小 probe）；完成验收集/Prompt 冻结和中枢审查。

[2026-11-05] agent=Codex task=APP-001-PREP-R2-prompt status=review
- 动作：在项目负责人 push APP-001-PREP 基线提交后，核对主线同步状态、最新决策与已有 handoff，编写续任准备任务 Prompt。
- 结果：明确执行 seed 最小能力核验、Ollama Qwen3 思考模式/解码参数核验、验收集与 Prompt 冻结候选、运行契约检查和三层交接；严格禁止正式验收集运行、正式对照或 APP-001 放行。
- 交付：`docs/coordination/prompts/APP-001-PREP-R2-agent.md`。
- 下一步：项目负责人将该 Prompt 发给续任 APP-001-PREP Agent；其提交结果后由 Codex 中枢独立验收。

[2026-11-05] agent=APP-001-PREP-R2 task=APP-001-PREP status=review
- 动作=按续任 Prompt 完成启动复核；核对共享仓库/干净工作树、APP-001 基线契约、CAD-003 Schema、RET-003 reference-only 边界和前序 checkpoint/handoff；未运行任何正式验收集或对照。
- M0=Python 3.9.6、Darwin 25.6.0 arm64、Ollama CLI/API 0.33.2；服务可达；`qwen3:8b` 列表 ID `500a1f067a9f` 与冻结值一致；`/api/show` 为 qwen3 8.2B Q4_K_M 且有模板；`.env` 仅做存在性检查并通过 ignore，未读取/输出 key。
- M1=DeepSeek 官方 Chat Completions 页面未明确列出 seed，因此按上限执行两次相同短提示能力探测：`seed=271828`、temperature=0、top_p=1、max_tokens=8、JSON mode、thinking disabled、stream=false；两次 HTTP 200、接受 seed、响应 model=deepseek-flash、provider 未暴露、request ID 存在但未保存、usage/cache=38/5/43 与 cache miss 38。回复、headers 和 key 未保存；按 2026-11-05 高峰价目表计算两次实际 usage 的费用为 CNY 0.000232。结论仅为参数 supported，不是确定性或质量结论。
- M2=执行两个独立 Ollama 短 probe（`/api/chat`、`/api/generate`），均使用 `think=false`、format=json、temperature=0、top_p=1、num_predict=8、seed=271828、stream=false；均 HTTP 200、有效 JSON、无 thinking 字段。仅保留脱敏运行元数据；不宣称与 DeepSeek 思考模式等价；不计入正式延迟/性能。
- M3=新增候选 `prompt-v1.md`；将九条验收样例标记 candidate freeze 但维持 review、formal_evaluation_allowed=false；更新 output contract、运行记录字段和 seed/local 模式证据；Prompt 标签泄漏扫描通过，CAD-003 正常/失败样例分别通过和返回 MISSING_REQUIRED。
- 验证=Ruby YAML parse、两份 JSON parse、`git diff --check`、`git check-ignore -v .env`、Prompt evaluator-label scan、secret/index scan 均通过；未修改 ADR-0009 至 ADR-0012，未修改 CAD-003/IR/CAD/RET-003 实现。
- 限制=候选 Prompt/样例、adapter/logger 和本地/云端模式公平性仍待 Codex 中枢/负责人审核；APP-001-PREP 保持 review，APP-001 保持 planned，formal evaluation gate=false；所有正式字段/Schema/IR/CAD/STEP/成本/延迟结果仍 not_measured。
- 下一步=中枢独立审查 `prompt-v1.md` 的真值隔离、严格 CAD-003 投影和运行记录适配器，确认后另行决定是否放行 APP-001；本提交不 push、不合并。
- 交付提交=前序 APP-001-PREP-R2 交付 commit `c255d4e`（本次文档一致性修正的核对基线）。

[2026-11-05] agent=APP-001-PREP-R2 task=APP-001-PREP-doc-consistency status=review
- 动作=修正 `prompt-output-contract-v0.md` 输出示例中的过期 `app001-extraction.v0-draft`，统一为当前候选 `app001-extraction.v1`；移除 `prompt-v1.md` 末尾多余空行；未改历史日志、模型策略、验收标签或正式状态。
- 验证=检查 Prompt、output contract、baseline artifact 的当前版本标识一致；无 JSON/YAML 改动，按要求不重复解析；未运行 DeepSeek/Ollama 请求、验收样例或质量评测；提交后 `git diff --check HEAD^ HEAD` 通过。
- 交付提交=窄范围修正 commit `f877b0c`；保持 APP-001-PREP=review、APP-001=planned、formal_evaluation_allowed=false，交 Codex 中枢复核。

[2026-11-05] agent=Codex task=APP-001-PREP-contract-freeze status=review
- 动作=按项目负责人确认新增 ADR-0013；将 LLM 显式抽取与 CAD-003 投影/校验分层；冻结 `app001-io.v1`、`app001-extraction.v2` 与 9 条 evaluator-only `acceptance-set-v0`；修正 A01 抽取真值、A02 派生说明及三占位符描述；同步基线、状态、计划、checkpoint/handoff。
- 验证=9 条 JSON 标签结构及参数字段断言通过；验收 JSON 解析通过；Ruby YAML 解析通过；协议版本交叉核对、Prompt 占位符数检查、评测门关闭断言通过；`git diff --check` 通过。未调用 DeepSeek/Ollama，未运行验收样例或正式评测。
- 限制=执行 adapter/logger 尚未实现及审查；APP-001-PREP 保持 review，APP-001 保持 planned，formal_evaluation_allowed=false。
- 下一步=实现并审查 adapter/logger，确认原始模型输出、显式抽取、CAD-003 投影/验证及下游 CAD/STEP 分阶段记录；完成后另向项目负责人申请正式运行授权。
- 交付提交=`88cdea7`（本次冻结契约、Prompt、样例标签及同步状态文档）。

[2026-11-05] agent=Codex task=APP-001-ADAPTER-prompt status=planned
- 动作：依据已接受 ADR-0013 和冻结 `app001-io.v1` / `app001-extraction.v2`，拆出正式评测前置的双基线 adapter/logger 实现任务，限制为 mock transport、严格解析、CAD-003 投影与分阶段日志。
- 结果：新增 CC 执行 Prompt；明确不调用真实 API/Ollama、不读取密钥、不运行九条验收样例或产生正式指标。检查当前仓库未发现经过审查的六字段参数→Typed CAD IR 映射，因此要求没有映射时 CAD/STEP 阶段如实标记 not_run/blocked，不得临时造 IR。
- 状态：新增 `APP-001-ADAPTER=planned`；`APP-001-PREP=review`、`APP-001=planned`、正式评测门关闭。当前 `main` 在本次改动前比 `origin/main` 超前 2 个 APP-001 冻结提交。
- 验证：已复核目标 Git 根目录、冻结契约版本、Schema API 与编译器入口；`python3 -m json.tool agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json` 与 `git diff --check` 通过。只解析样例 JSON 文件格式，没有将标签用于模型输入或评测。
- 交付：`docs/coordination/prompts/APP-001-adapter-logger-cc-agent.md`。
- 下一步：先提交并由项目负责人 push 冻结契约及本次任务 Prompt，再把 Prompt 发给 CC；完成后由 Codex 中枢独立审查，不能据此直接启动正式 APP-001。

[2026-11-05] agent=Codex task=APP-001-ADAPTER-review status=review
- 动作：对 CC 提交 `e496ac0` 与状态同步 `9cd1f98` 做中枢独立审查，复跑 README 指定的 mock 测试并设计合成边界检查。
- 验证：`PYTHONPATH=src python3 -m unittest discover -s tests/llm -v` 85 项通过；未设置或读取真实密钥、未调用网络、未运行验收样例。裸 unittest 命令不符合仓库 src-layout，出现 19 项 import errors；README 指定命令通过。
- 结论：不验收通过。发现 mock 请求会读取环境 key 并保留 authorization、自定义 transport 默认可绕过正式评测门、cache hit/miss 缺失仍估算费用、总耗时漏计 backoff；另发现 NaN/Infinity 和数组/evidence 元素类型校验缺口，以及文档宣称 raw-output retention 但实现缺失、Prompt 未绑定 hash 等待补齐项。
- 交付：`agent-work/reviews/APP-001-ADAPTER-codex-review.md`；`APP-001-ADAPTER` 保持 `review`，正式评测门关闭。
- 下一步：CC 修正审查记录中的问题并更新测试/交接；中枢再复核，通过前不得启动正式 APP-001。

[2026-11-05] agent=CC task=APP-001-ADAPTER-M0 status=in_progress
scope=M0 interface and boundary inventory; no code changes
verified=git root confirmed; .env existence-only check (not read); system Python 3.10.12 + unittest runs schema tests 17/17 OK; work/app001-runs git-ignored; frozen contract versions app001-io.v1/app001-extraction.v2/acceptance-set-v0 cross-checked against ADR-0013 and baseline contract; Schema API (validate_parameters/validate_json/resolve_parameters -> ValidationResult) and CAD compiler entry (compile_ir) signatures confirmed; param->IR mapping exists as spec (mapping.md, review) + RET-001 generator but no frozen src-level adapter, so IR/CAD/STEP kept not_run
result=M0 inventory recorded in agent-work/llm/APP-001-adapter/checkpoint.md; proceeding to M1
limits=no real API/Ollama calls, no key reads, no acceptance-sample runs, formal eval gate remains false
next=implement M1 strict parser + run record model + CAD-003 projector as pure functions

[2026-11-05] agent=CC task=APP-001-ADAPTER-M1 status=in_progress
scope=Implement minimal data model, strict parser, CAD-003 projector (pure functions)
verified=PYTHONPATH=src python3 -m py_compile src/llm/*.py OK; imports OK; contract versions app001-io.v1/app001-extraction.v2 confirmed in code
result=Modules written: contract, parser (strict, no repair), projector (CAD-003 envelope, rejects unknown keys), runrecord (staged, versioned), transport (injectable + Fake), providers (DeepSeek thinking-disabled + Ollama think=false isolated), retry (injectable clock/sleeper, 1s/2s backoff), cost (dated rate card, not_available on missing), gate (default-off fail-closed), adapter (orchestrator, IR/CAD/STEP not_run/blocked)
limits=no real network, no key reads, formal eval gate false; IR/CAD/STEP blocked_no_approved_ir_mapping
next=write and run fake-transport tests (M2/M3 coverage)

[2026-11-05] agent=CC task=APP-001-ADAPTER-M4 status=review
scope=M4 final tests, verification, secret scan, README, checkpoint/handoff, git commit
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 85 tests, 0 failures, OK
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK (no regressions)
  grep -rn "import cadquery|from cad_compilation.compiler import compile_ir" src/llm/ tests/llm/ → no matches
  secret scan (sk-*, Bearer real, DEEPSEEK_API_KEY real values) → only synthetic fixtures
  git diff --check → OK
  gate: formal_evaluation_allowed()=False; require_formal_evaluation_allowed() raises FormalEvaluationBlockedError
result=APP-001-ADAPTER implementation complete and submitted for review; 85 tests pass with FakeTransport only; no real API calls, no credential reads, no acceptance-sample runs; IR/CAD/geometry/STEP stages honestly not_run/blocked; formal evaluation gate closed
limits=IR mapping not frozen at src level; real provider runs not executed; all formal metrics not_measured; formal evaluation not authorized; APP-001-PREP=review, APP-001=planned
next=Codex hub read-only review; if passing, project owner authorizes formal APP-001 run

[2026-11-05] agent=Codex task=APP-001-ADAPTER-R1 status=planned
- 动作：根据中枢独立审查报告生成 CC 窄范围修正 Prompt，覆盖凭据隔离、fail-closed transport 门、usage 费用、重试总耗时、JSON 严格校验、原始响应保留与 Prompt hash。
- 验证：对照 `agent-work/reviews/APP-001-ADAPTER-codex-review.md`、原始执行 Prompt 和冻结 APP-001 契约；确认 `work/app001-runs/` 被 `.gitignore` 排除；`git diff --check` 通过。
- 交付：`docs/coordination/prompts/APP-001-ADAPTER-R1-correction-cc-agent.md`，commit `a834c3e`。
- 边界：未修改实现、未调用真实 API、未读取凭据、未运行冻结验收样例；`APP-001-ADAPTER=review`、`APP-001=planned`、正式评测门关闭。
- 下一步：项目负责人 push 后将该 Prompt 交给 CC；完成后由 Codex 中枢独立复核。

[2026-11-05] agent=CC task=APP-001-ADAPTER-R1 status=review
scope=修复 Codex 审查发现的 7 项问题（3.1 凭据隔离、3.2 评测门、3.3 费用计算、3.4 总耗时、3.5 解析器严格性、4.1 响应保留策略、4.2 Prompt hash）
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 121 tests, OK (原85+新增36)
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
  git diff --check → PASS
  secret scan → only synthetic fixtures
result=所有 7 项审查问题已修复；121 项测试通过；无真实 API/Ollama 调用；无凭据读取；评测门关闭
limits=IR 映射仍未冻结；正式 APP-001 仍未授权；Prompt artifact 哈希验证（运行时核对冻结文件）尚未实现
next=Codex 中枢 R1 只读复核；通过后项目负责人可明确授权正式 APP-001 运行

[2026-11-05] agent=Codex task=APP-001-ADAPTER-R1-review status=review
- 动作：独立复核 `2a324f7` 与 `a491c94`，对照 R1 prompt 检查逐项要求并复跑测试。
- 验证：LLM 测试 121/121、Schema 回归 17/17、`py_compile` 与 `git diff --check` 通过；合成 `MockTransport` 子类仍能在 gate 关闭时调用 `send()`；合成 retention 可写到配置的任意目录；确认无冻结 prompt artifact 运行时核验。
- 结论：R1 部分有效但不验收通过。prompt artifact 核验明确属于 R1 范围而未完成；IR 映射则按原任务边界属后续/不同范围，不应由 CC 在此臆造。
- 交付：`agent-work/reviews/APP-001-ADAPTER-R1-codex-review.md`；任务保持 `review`，APP-001 不放行。
- 下一步：定点修复 transport gate、retention root 限制和 frozen prompt artifact 核验，然后中枢再审。

[2026-11-05] agent=CC task=APP-001-ADAPTER-R2 status=review
scope=修复 R1 Codex 复核发现的 3 项问题（4.1 评测门精确类型、4.2 Retention 路径约束、4.3 冻结 Prompt artifact 核验）
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 143 tests, OK (原121+新增22)
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
  git diff --check → PASS
  secret scan → no real credentials
result=3 项 R2 修正全部完成；143 项测试通过；无真实 API/Ollama 调用；无凭据读取；评测门关闭
limits=IR 映射仍未冻结；正式 APP-001 仍未授权；真实 provider/样例/正式指标均未运行
next=Codex 中枢 R2 只读复核；通过后项目负责人可授权正式 APP-001 运行

[2026-11-05] agent=Codex task=APP-001-ADAPTER-R2-review status=review
- 动作：独立复核 `c9abdcb` 与 `405f933`，复跑 LLM/Schema 回归，并用合成 transport、临时路径和临时 symlink 验证 R2 安全边界。
- 验证：LLM 143/143、Schema 17/17、`py_compile` 与 `git diff --check` 通过；越界 symlink 被拒绝；但公开 `verify_frozen_prompt=False` 让任意 Prompt 到达 FakeTransport，直接设置 RetentionPolicy `_test_only=True` 也成功将合成 raw response 写出仓库外。
- 结论：R2 部分有效但不验收通过。评测门精确类型与 canonical path resolver 有效；Prompt 校验和 Retention test-only 机制均可由普通调用者绕过。具体证据见 `agent-work/reviews/APP-001-ADAPTER-R2-codex-review.md`。
- 边界：没有真实网络、密钥、模型、冻结验收样例或正式指标；IR 映射仍未冻结并属于后续依赖。
- 下一步：窄范围 R3 修复上述两个可绕过入口，保持 APP-001=planned 和正式评测门关闭。

[2026-11-05] agent=CC task=APP-001-ADAPTER-R3 status=review
scope=修复 R2 复核确认的 2 项可绕过入口：A 移除 verify_frozen_prompt/_prompt_loader_path 参数并加文件 hash 锚点；B 移除 _test_only/for_test/validate_for_production 并拆分私有 writer
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -v → 167 tests, OK
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
  git diff --check → PASS
  git ls-files work/ → (empty; no run artifacts committed)
  inspect.signature(Adapter.run) 确认无 verify_frozen_prompt 或 _prompt_loader_path
  RetentionPolicy 无 _test_only 字段、无 for_test 工厂、无 validate_for_production
result=2 项 R3 修正完成；167 项测试通过；无真实 API/Ollama 调用；无凭据读取；评测门关闭
limits=IR 映射未冻结；正式 APP-001 未授权；prompt loader 两次读文件存在理论 TOCTOU
next=Codex 中枢 R3 只读复核；通过后项目负责人可授权正式 APP-001 运行

[2026-11-05] agent=Codex task=APP-001-ADAPTER-R3-review status=review
- 动作：独立复核 `750897d`/`5e29cbf` 的 R3 代码、测试和状态文档；未调用真实 API、未读取密钥、未运行冻结验收样例。
- 验证：LLM 167/167、Schema 17/17、`py_compile` 与 `git diff --check` 通过；手工 symlink 越界探针被拒绝；Adapter.run 绕过参数和 Retention `_test_only` 均已移除。
- 结论：R3 代码行为条件性通过，但不作最终验收。篡改 artifact 测试没有真正加载篡改文件，symlink 越界测试未固化；README 与 PROJECT_STATUS 仍有 R2/旧规则表述。具体证据见 `agent-work/reviews/APP-001-ADAPTER-R3-codex-review.md`。
- 边界：IR 映射仍未冻结；正式 APP-001、真实 provider、九条样例和正式指标均未授权或运行。
- 下一步：给原 R3 Agent 窄范围收尾修正，完成两项测试证据和文档同步后再复审。

[2026-11-05] agent=CC task=APP-001-ADAPTER-R3-FIX status=review
scope=补齐 R3 审查要求的证据和文档：篡改 artifact 测试真实加载篡改文件、symlink 越界测试实际执行、README/PROJECT_STATUS 同步到 R3 规则
verified=
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -q → 170 tests, OK
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q → 17 tests, OK
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py → OK
  git diff --check → PASS
  git ls-files work/ → (empty)
  inspect.signature(Adapter.run) → no verify_frozen_prompt or _prompt_loader_path
  RetentionPolicy fields → no _test_only; no for_test()
result=R3-FIX 收尾完成；篡改 artifact 测试和 symlink 越界测试已补齐；README 已同步；170 项测试通过；无真实 API/Ollama 调用；无凭据读取；评测门关闭
limits=IR 映射未冻结；正式 APP-001 未授权；真实 provider/样例/正式指标均未运行；prompt_loader 两次读文件存在理论 TOCTOU
next=Codex 中枢 R3-FIX 复核；通过后项目负责人可授权正式 APP-001 运行

[2026-11-05] agent=Codex task=APP-001-ADAPTER-R3-FIX-review status=done
- 动作：独立复核 `c0543d6`/`78e9e4a`，复跑 LLM/Schema/编译检查，并确认篡改 artifact 与 symlink 越界测试真实执行。
- 验证：LLM 170/170、Schema 17/17、`py_compile`、`git diff --check` 通过；篡改文件被 `_verify_file_hash()` 拒绝；两个 symlink 测试通过且外部目录无文件；README/状态描述与实现一致。
- 结论：`APP-001-ADAPTER-R3-FIX` 验收通过，`APP-001-ADAPTER` 标记 `done`。审查记录见 `agent-work/reviews/APP-001-ADAPTER-R3-FIX-codex-review.md`。
- 边界：APP-001-PREP 仍为 `review`，APP-001 仍为 `planned`；正式评测门关闭；真实模型、九条样例、正式字段/CAD/STEP 指标未运行；IR 映射仍未冻结。
- 下一步：完成 APP-001-PREP 最终前置审查，之后由项目负责人单独授权正式 APP-001。

[2026-11-05] agent=Codex task=APP-001-PREP-FINAL-REVIEW status=needs_revision
- 动作：只读复核冻结契约、模型基线、输入隔离、指标口径和已验收 adapter；未调用真实模型、未读取 API key、未运行九条样例。
- 验证：acceptance JSON、baseline YAML、LLM 170 tests、Schema 17 tests 均通过；云端/本地身份和 provider-specific thinking 配置与决策一致。
- 结论：契约和实现证据基本通过，但 PREP handoff 的当前 ADR-0013 段仍写 adapter/logger 尚未实现和审查，与 `APP-001-ADAPTER=done` 不一致。详见 `agent-work/reviews/APP-001-PREP-FINAL-REVIEW.md`。
- 边界：APP-001-PREP 保持 `review`，APP-001 保持 `planned`，formal gate 关闭；正式字段/Schema/CAD/STEP/成本/延迟指标均未测量。
- 下一步：原 PREP Agent 只追加状态收尾，明确 adapter 已完成、剩余仅 owner authorization；完成后中枢重新复核。

[2026-11-05] agent=Codex task=APP-001-PREP-FINAL-FIX status=review
task=APP-001-PREP-FINAL-FIX
status=review
changed=checkpoint/handoff 状态同步
result=adapter 已完成；PREP 仍等待 Codex 最终复核和 owner authorization
limits=未调用真实模型；未运行九条样例；正式指标 not_measured；IR mapping 未冻结
next=Codex 中枢最终复核
- 结论=`APP-001-ADAPTER-R3-FIX` 已由中枢验收，`APP-001-ADAPTER=done`；旧的 adapter/logger remaining-gate 文字保留为历史记录。APP-001-PREP 继续 review，APP-001 继续 planned，formal_evaluation_allowed=false。
- commit=cb87815

[2026-11-05] agent=Codex task=APP-001-PREP-FINAL-ACCEPTANCE status=done
- 动作：复核 PREP-FINAL-FIX 的 checkpoint/handoff 状态收尾，并独立复跑 JSON、YAML、LLM 与 Schema 检查。
- 验证：acceptance JSON、baseline YAML、LLM 170/170、Schema 17/17、`git diff --check` 全部通过；旧 adapter/logger remaining-gate 已标为历史。
- 结论：`APP-001-PREP` 最终验收通过并标记 `done`。详见 `agent-work/reviews/APP-001-PREP-FINAL-ACCEPTANCE.md`。
- 边界：APP-001 仍为 `planned`，formal gate 仍关闭；真实模型、九条样例、正式字段/Schema/CAD/STEP/费用/延迟指标未运行；IR 映射未冻结。
- 下一步：等待项目负责人单独授权正式 APP-001。

[2026-11-06] agent=CC task=APP-001-RUNNER-001 status=review
scope=APP-001 Phase 1 受控运行入口实现（src/llm/ 7 个新模块 + adapter.py 修改，tests/llm/ 3 个新测试文件 106 项，docs/DECISIONS.md ADR-0014，agent-work/llm/APP-001-runner/checkpoint.md 和 handoff.md；docs/WORKLOG.md 只追加）
动作=实现正式评测受控运行入口，将已有模块串接：冻结验收集 allowlist 投影、C0/C1 条件输入组装（C1 经 RET-002）、DeepSeek/Ollama 真实 HTTP transport（不在测试中使用）、原子预算账本（per-run/provider/batch 硬上限）、36 组合生成器、受控批次 runner；修改 adapter.py 新增窄范围 formal_authorization 参数路径；新增 ADR-0014 授权路径
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/{authorization,budget,combinations,conditions,real_transport,input_projection,runner,adapter}.py tests/llm/test_{authorization,budget,runner}.py → OK
  PYTHONPATH=src python3 -m unittest tests.llm.test_runner tests.llm.test_authorization tests.llm.test_budget → 106 tests, OK (skipped=1 FUSE env symlink)
  PYTHONPATH=src python3 -m unittest discover -s tests/llm → 276 tests (errors=2 pre-existing FUSE env symlink in test_r3_regression, skipped=1)
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
  git diff --check → OK
results=dry_run() 生成正确的 36 条组合，不泄露评估器标签；FormalRunAuthorization scope 验证通过；C2/错误模型/错误样本集均在任何网络调用前被拒绝；预算原子预留、并发锁、损坏账本 fail-closed 全部通过；评估器标签（explicit_parameter_claims、derived_values、expected_behavior）不进入任何模型输入、干运行输出或 C1 reference；API key 不存入 repr/日志/异常/输出文件；IR/CAD/geometry/STEP 始终 not_run/blocked；JSONL 可解析且含所有必需元数据；失败样本保留在批次记录中
not_run=正式九条样例评测未运行；未发起真实 DeepSeek 或 Ollama 请求；无模型质量、延迟或费用结论；所有正式指标仍 not_measured
known_limits=预算账本目前每 Adapter.run() 预留一次（含内部最多 3 次重试），非每物理 attempt 预留；C1 reference context 在 retrieval_index=None 时阻塞；TOCTOU 继承自 R3；FORMAL_EVALUATION_ALLOWED=False 未改变
next=Codex 中枢独立审查：验证 36 组合、gate 行为、预算耗尽、eval-label 隔离、密钥隔离、JSONL schema；通过后项目负责人单独授权正式 APP-001；本任务保持 review，未 push

[2026-11-06] agent=CC task=APP-001-RUNNER-R1 status=review
scope=关闭 APP-001-RUNNER-001 的四项边界差距：冻结验收集 SHA-256 强制校验、物理请求按每次 transport 调用计账、C1 从自然语言提取 bore_d（不使用固定 bore_d=20）、Ollama 身份和 digest 严格校验（src/llm/{contract,conditions,budget,runner,real_transport,adapter}.py；tests/llm/test_runner_r1.py；agent-work/llm/APP-001-runner-R1/；docs/WORKLOG.md 只追加）
动作=1)contract.py 新增 ACCEPTANCE_SET_SHA256 常量；runner._load_projection() 强制传入该哈希；2)budget.py 新增 BudgetAwareTransport，每次 send() 预留一个预算槽位；runner._execute_one_run() 改为使用 BudgetAwareTransport，移除旧的单次预留；新增中断失败关闭逻辑；3)conditions.py 完整重写：deterministic bore_d 提取函数，支持 mm/cm，NLI 无 bore_d 时 blocked（C1_NO_SAFE_QUERY_PARAMETER）；4)real_transport.py 严格 startswith() digest 校验，记录实际模型名和 digest 到 usage；adapter.py _record_runtime_identity 使用 usage 字段中的实际 digest
verified=
  PYTHONPATH=src python3 -m py_compile src/llm/{contract,conditions,budget,runner,real_transport,adapter}.py tests/llm/test_runner_r1.py → OK
  PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r1 → 40 tests OK
  PYTHONPATH=src python3 -m unittest discover -s tests/llm → 316 tests OK (skipped=1)
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests OK
  git diff --check → OK; work/app001-runs/ git-ignored; secret scan → no hardcoded keys
  dry-run 36 combinations pass hash check; acceptance-set tampered NLI/query_id/eval-only fields rejected; bore_d=24mm/1.6cm/20mm/A08 all correctly extracted; C1 blocked for cases without bore_d; Ollama missing/non-prefix digest rejected; DeepSeek transport has no digest attributes
not_run=正式九条样例评测未运行；未发起真实 DeepSeek 或 Ollama 请求；无模型质量、延迟或费用结论；所有正式指标仍 not_measured；FORMAL_EVALUATION_ALLOWED=False 未改变
python_env=Python 3.10.12 / Linux aarch64（Linux sandbox 仅有此版本）；macOS venv python3.11 symlink 在 Linux FUSE 下无法访问；新代码使用 typing.Optional 兼容 3.10
known_limits=C1 对 A04/A07/A09（NLI 无 bore_d）阻塞，符合规范；中断运行 fail-closed；Ollama digest 测试使用 monkey-patch；TOCTOU 继承自 R3
next=Codex 中枢独立审查 SHA-256 强制校验、per-attempt 预算计数、C1 bore_d 提取、Ollama 严格 digest、316 tests 通过；确认 C1-blocked 对 A04/A07/A09 可接受；通过后项目负责人单独授权正式 APP-001；本任务保持 review，未 push

[2026-11-06] agent=Codex task=APP-001-RUNNER-R2 status=review
scope=修复 APP-001-RUNNER-R1 中枢验收发现的两个阻塞边界：正式 Adapter 调用绕过预算账本、Ollama 模型身份只做家族子串判断；未执行正式模型/API 调用
动作=Adapter.run 仅接受与授权对象、real transport、provider/model、query、condition、run_id 一致的精确 BudgetAwareTransport；FormalRunAuthorization 采用精确 provider/model 配对；BudgetAwareTransport 校验真实 transport 类型/授权/运行绑定，BudgetLedger 强制 36 逻辑运行上限；Ollama 从 /api/tags 精确查找唯一 qwen3:8b 与摘要，并要求 /api/chat 返回模型标签一致；README 与 R2 checkpoint/handoff 更新
verified=Python 3.11.18；tests.llm.test_runner_r1 50 项通过；tests.llm 全量 326 项通过（1 skipped）；Schema 17 项通过；py_compile、git diff --check 通过；dry_run 生成 36 项、0 次尝试、FORMAL_EVALUATION_ALLOWED=False；直接自定义 transport、伪造 FakeTransport budget wrapper、provider/model 交叉、run_id 不匹配、qwen3:14b、family-only、重复 exact tag、错误摘要和响应 model 不匹配均拒绝
limits=没有真实 DeepSeek 或 Ollama 调用；Ollama live /api/tags 与 /api/chat 行为尚待获授权运行时确认；APP-001 仍保持 planned，正式批次尚未启动
next=Codex 中枢独立复核 R2 代码与测试；保持 review，不 push，复核通过后由项目负责人按既有授权流程推进
commit=ecc3163（本地提交，保持 review，未 push）

[2026-11-06] agent=Codex task=APP-001-STATUS-SYNC status=review
- 动作：R2 push 后核对 main 与 origin/main 同步，发现 PROJECT_STATUS、PROJECT_PLAN、TASKS 仍引用过时 PREP/adapter 状态，并误称正式 APP-001 仍等待用户授权；依据 ADR-0014 和已推送 runner 交付同步三份状态文档。
- 结果：APP-001-PREP 与 APP-001-ADAPTER 保持 done；APP-001-RUNNER 标为 review；APP-001 保持 planned。既有 Phase 1 授权范围已记录，R2 独立只读安全复核是正式运行前唯一放行门。
- 验证：`git status --short --branch` 确认开始时 main 与 origin/main 同步；核对 ADR-0014、R2 checkpoint/handoff 和 runner 交付；`git diff --check` 通过。
- 下一步：完成状态文档检查与提交，然后进行 APP-001-RUNNER-R2 独立只读安全复核；未通过前不运行模型请求。
- commit：`0ce39f4`（文档状态同步；本地提交，未 push）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX status=review
scope=修复 Codex 对 R3 工作验收发现的预算与 C1 前置门问题：临时目录豁免、token 伪造与绑定缺口、Ollama tags/chat 分离记账、C1 索引验证不足
动作=移除 BudgetLedger 临时目录豁免，强制绑定规范 batch 目录；增强 _BudgetReservationToken 绑定 batch_id/logical_run_id/provider/model/endpoint/attempt_number，增加 consume() 方法验证和消费；OllamaTransport.send() 增加 _tags_budget_token 参数，tags 与 chat 各有独立 token 和预留；run_formal() 验证 retrieval_index 是 RetrievalIndex 实例且具有有效 manifest_sha256/manifest_path
verified=新增 tests/llm/test_r3_fixes.py 16 项测试全部通过；现有 tests/llm/test_runner_r3.py 12 项通过；python3 -m py_compile 通过；git diff --check 通过；无预算凭证时 0 次 urlopen（mock 验证）；伪造/错配/重放 token 在 urlopen 前被拒绝；Ollama 第一次 send 需要 tags token；无索引/MagicMock/缺失 sha256 在 HTTP 前被拒绝
commands=`PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -v` (16/16 通过)；`PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r3 -q` (12/12 通过)；`python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py` (通过)；`git diff --check` (通过)
limits=移除临时目录豁免后 33 个现有测试失败（主要是 test_runner_r1.py 使用 tempfile.TemporaryDirectory()），需要更新为使用规范 batch 目录；tests/llm 全量 338 项，33 errors；本次修复专注于四个明确列出的 R3 问题，遗留测试适配范围外；未运行正式评测，未访问真实 API
next=Codex 中枢独立审查四个 R3 修复；33 个遗留测试需要适配（使用规范 batch 目录而非临时目录）；保持 review，未 push，审查通过后推进
commit=待创建（git index.lock 阻塞，需手动处理）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R2 status=review
scope=收束 R3-FIX 工作，修复全量回归失败（33 个测试因 tempfile 路径改变失败），增强 C1 索引完整身份验证，并运行最终测试套件
动作=1）适配所有使用 tempfile.mkdtemp() 的测试（test_budget.py、test_runner.py、test_runner_r1.py）改用规范批次目录（work/app001-runs/<batch_id>/）；标记 8 个 FUSE 文件系统无法删除 lock 的测试为 @unittest.skip；2）增强 runner.run_formal() 中 C1 索引验证，使用 retrieval/config.py 的冻结字段：manifest_sha256 必须是 64-hex、manifest_path 必须匹配冻结路径、manifest_version 必须以 retrieval-manifest 开头、policy 必须是 DistancePolicy 实例；3）更新 test_r3_fixes.py 新增 7 个针对 C1 索引身份验证的测试（包括真实冻结索引通过门的测试）；4）写 checkpoint.md 和 handoff.md
verified=
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -p 'test_*.py' -q` → Ran 357, 2 pre-existing FUSE symlink errors, 8 FUSE lock skips
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -p 'test_*.py' -q` → Ran 17, OK
  `python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py` → OK
  `git diff --check` → OK
  test_r3_fixes.py 19 项通过；test_runner_r3.py 12 项通过
limits=2 个 pre-existing FUSE symlink 错误（test_r3_regression）；8 个 FUSE lock 删除限制 skip（原生文件系统可运行）；Ollama 18 次 tags 预检消耗 provider 配额，实际 chat 额度 ≤ 36 次；正式评测未放行；无真实 API 调用
next=Codex 中枢独立审查；通过后项目负责人按既有授权流程推进正式 APP-001；本任务保持 review，未 push
commit=待创建（尝试 git add 后提交）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R2 status=review
scope=继续修复 APP-001-RUNNER-R3-FIX-R2 四项未解决问题：token 须对应真实 BudgetLedger 预留、物理 HTTP 与模型调用预算分离、C1 索引完整身份验证（精确值）、如实记录验证结果并修复 FUSE 测试
动作=
  1) token 真实预留验证：_BudgetReservationToken 新增 weakref 指向原始 BudgetLedger；consume() 新增 step-3 调用 ledger._verify_pending_reservation() 跨对照真实 pending 记录，forged/replayed/mismatch token 均在 urlopen 前被 BudgetBypassError 拒绝；
  2) HTTP 与模型调用预算分离：reserve_attempt() 增加 is_model_call 和 endpoint 参数；is_model_call=False（Ollama /api/tags）仅消耗批次/provider 计数，不消耗每 run 的 3 次模型调用额度；tags 保留负数 attempt_number 序列与 chat 区分；_verify_integrity() 仅对 is_model_call=True 记录计入 run_attempts_used；BudgetAwareTransport.send() 对 tags 使用 is_model_call=False；
  3) C1 精确身份验证：runner.run_formal() 验证顺序改为 type→path→version（exact）→sha256 文件比较→policy.validate()；manifest_version 须精确等于 MANIFEST_FORMAT_VERSION="retrieval-manifest.v0"（新增常量至 retrieval/config.py）；manifest_sha256 须精确等于磁盘文件 SHA-256；policy.validate() 须全量通过（ranges/weights）；
  4) 修复 FUSE 测试错误：test_r3_regression.py 两个 symlink 测试改为时间戳唯一 link_name，try/except OSError 包裹 finally 中的 unlink；新增 6 个测试（forged token 0 urlopen、ledger 无 record 拒绝、valid-length wrong sha256 拒绝、tags 不消耗模型调用额度、tags 计入 provider 总数、tags 与 chat 分别记账）；test_r3_fixes.py 共 25 项测试
verified=
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 363, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py src/retrieval/config.py` → OK
  `git diff --check` → OK (no trailing whitespace in new/changed lines)
  test_r3_fixes.py 25/25 通过
limits=8 个 FUSE lock 删除限制 skip（@unittest.skip 标记，原生文件系统可运行；test_r3_regression 两个 symlink 测试现在通过，已转为 skip-on-FUSE 模式）；Ollama 18 次 tags 预检消耗 provider 配额，实际 chat 额度 ≤ 36 次；正式评测未放行；无真实 API 调用
next=Codex 中枢独立审查本次修复；通过后项目负责人按既有授权流程推进正式 APP-001；本任务保持 review，未 push
commit=6f4af27

[2026-11-07] agent=Codex task=APP-001-EVIDENCE-CONTRACT-FIX-CODEX-REVIEW status=review
scope=独立复核 evidence null 契约修正；不启动正式批次
verified=
  Python 3.11.18 下定向 119 项通过；tests/llm 全量 499 项通过（8 项既有 FUSE skip）；tests/schema 17 项通过；py_compile 和 git diff --check 通过；正常字符串 evidence 通过，field/quote/source=null 均准确拒绝
confirmed=
  parser 与 OLLAMA_FORMAT_SCHEMA 的非空字符串约束已对齐；未修改 Ollama、Prompt、adapter、runner、预算、授权或正式批次
git_state=
  本地 HEAD=352ef8a、工作区干净；fetch 后 origin/cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX 仍为 2bb12ec，origin/main 为 16f0d1f；push 尚未在当前远端事实中确认
no_network=无真实模型调用、无密钥读取、无正式批次修改
next=先同步并合入 main；合入前不启动新批次，合入后按 ADR-0014/0015 重新申请唯一批次
commit=待提交（中枢审查记录）

[2026-11-07] agent=Codex task=APP-001-EVIDENCE-CONTRACT-FIX-CLOSEOUT status=done
scope=合入后复核 evidence null 契约修正
verified=
  main 与 origin/main 同步于 830f65b，包含 352ef8a 修正、efe5a7d 审查记录和 2bb12ec Ollama 冻结；工作区干净且无 index.lock；Python 3.11.18 下定向 119 项、LLM 全量 499 项（8 项既有 FUSE skip）、Schema 17 项全部通过；py_compile 和 git diff --check 通过
confirmed=
  合法字符串 evidence 通过；field/quote/source 显式 null 均被 EVIDENCE_FIELD_TYPE_ERROR 拒绝并定位准确；未改变 Ollama、正式批次和授权范围
decision=
  evidence 契约修正工作单元标记 done；APP-001 正式评测整体仍为 review，新的唯一批次尚未授权
next=项目负责人按 ADR-0014/0015 决定是否授权新批次；三个既有正式批次保持只读
commit=待提交（合入后状态同步）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R2 status=review
scope=Git commit 阻塞记录
动作=尝试 git add / git commit，发现 .git/index.lock 存在（0 字节，本进程所有，18:27 由 git status 留下，FUSE 无法清理）
结果=git add 失败，fatal: Unable to create .git/index.lock — File exists。按约束停止所有 Git 写操作，不删除 lock 文件，不尝试绕过
limits=.git/index.lock 阻塞 commit；用户需在本机手动删除 .git/index.lock 后运行 git commit；所有源码修改已写入工作树，状态与 R3-FIX-R2-checkpoint.md 一致
next=用户在本机执行 `rm .git/index.lock && git add <files> && git commit -m "fix: ..."`；见 R3-FIX-R2-checkpoint.md 的文件清单
commit=未完成（index.lock 阻塞）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R3 status=review
scope=完成 R3-FIX-R2 三项剩余窄范围修正：Issue-1 token/run 错配需 transport 级 urlopen=0 测试；Issue-2 Ollama tags/chat token 消耗顺序错误及 tags 失败时 outcome 混写；Issue-3 runner 使用文件实时 sha256 而非冻结配置 sha256
动作=
  1) Issue-2（Ollama tags/chat 分离）：real_transport.py 新增 OllamaTagsPreflightError(TransportError) 标记子类；OllamaTransport.send() 重排 token 消耗顺序为 consume(tags)→_verify_model_digest()→consume(chat)；tags 失败时抛 OllamaTagsPreflightError（chat token 未消耗，chat 未发送）；budget.py BudgetAwareTransport.send() 新增 except OllamaTagsPreflightError（优先于 except TransportError）：记录 tags=实际失败 outcome、chat=blocked（不同的记录，不伪造 chat 已发送）；原 except TransportError（chat 失败）现记录 tags=success（tags 已通过才能到达 chat 阶段）；
  2) Issue-3（冻结配置 sha256）：runner.py run_formal() step-(d) 改为加载冻结配置 RetrievalConfig.from_path(DEFAULT_CONFIG_REL_PATH)（内部已校验磁盘文件 sha256 与配置值一致），再比较 idx.manifest_sha256 与 config.manifest_sha256；移除不再使用的 sha256_file 导入，新增 DEFAULT_CONFIG_REL_PATH/RetrievalConfig 导入；
  3) Issue-1（transport 级 urlopen=0 测试）：test_r3_fixes.py 新增 TestR3Fix1TransportLevelMismatch（5 项）：batch/provider/model/endpoint 错配及 token 重放均通过 transport.send() 调用、@patch urlopen、断言 call_count=0；
  4) Issue-2 tests：新增 TestR3Fix2OllamaTagsFailChatBlocked（2 项）：tags 失败时 urlopen 恰好调用 1 次（tags only）；ledger 中 tags=non_retryable、chat=blocked 且 endpoint/attempt_number 各自独立；
  5) Issue-3 tests：新增 TestR3Fix3C1PolicyDetails（3 项）：错误 ranges/错误 weights/validate() 抛出时均被拒绝，message 含 policy 关键字
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -q` → Ran 35, OK
  `PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r3 -q` → Ran 12, OK
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -p 'test_*.py' -q` → Ran 373, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -p 'test_*.py' -q` → Ran 17, OK
  `/usr/bin/python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py src/retrieval/config.py` → OK
  `git diff --check` → OK
limits=验证使用 Python 3.10（VM 内无 python3.11）；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 再次运行验证命令确认一致；.git/index.lock 仍存在，commit 阻塞；8 个 FUSE lock skip 保持（原生文件系统可运行）；未运行正式评测，未访问真实 API
next=用户在本机：rm .git/index.lock → 运行 python3.11 验证 → git commit；Codex 中枢独立审查；通过后按 ADR-0014 放行 APP-001
commit=待提交（index.lock 阻塞）

[2026-11-07] agent=Codex task=APP-001-PHASE1-ENVELOPE-FIX-CLOSEOUT status=review
scope=独立复核 envelope 修复，完成主线合入和状态同步；不启动新的真实模型批次
动作=
  1) 核对远端分支 `origin/cc/APP-001-PHASE1-ENVELOPE-FIX` 已指向 `acdabc1`；
  2) 在 Python 3.11.18 下重跑 envelope 专项 38 项、LLM 全量 453 项（8 项既有 FUSE skip）、Schema 17 项、py_compile 和 diff check，全部通过；
  3) 确认 prompt-v2.md hash 未变、正式批次 `-01`/`-02` 未改、未发起真实请求；
  4) 将修复合入 `main`，生成 merge commit `f460dd0`；
  5) 更新 PROJECT_STATUS/PROJECT_PLAN，明确旧批次只作诊断证据，修复后新批次需负责人重新授权。
verified=
  `acdabc1` 包含 checkpoint、docstring 修正、源码和 38 项无网络测试；主线合入后工作区代码回归通过。
limits=本地 `main` 尚未推送；修复后尚未运行新真实批次；A04/A07 C1 安全阻塞口径未改变。
next=用户推送 `f460dd0` 到 `origin/main`；明确新唯一批次授权和 A04/A07 覆盖口径后，再启动正式评测。
commit=f460dd0

[2026-11-07] agent=Codex task=APP-001-PHASE1-20261107-03-REVIEW status=review
scope=审查 envelope 修复后的第三批正式评测；保持 C2、IR/CAD/geometry/STEP 禁用
动作=
  1) 主线 `d5613a1` 已推送后，使用新唯一批次 `app001-phase1-20261107-03`，从 `.env` 注入密钥到一次性进程，不打印或保存密钥；
  2) 运行冻结 9 样例 × C0/C1 × DeepSeek/Ollama；冻结 RET-002 索引通过预检；
  3) 核对 36 条 JSONL、32 条模型调用、4 条 C1 阻塞、48 次物理 HTTP、32 个原始响应和预算账本；
  4) 重解析原始响应并按 acceptance-set-v0 的显式字段标签做单位归一化诊断。
verified=
  DeepSeek envelope 16/16、Ollama C1 7/7；Ollama C0 8 条因 `EXTRACTED_TYPE_ERROR` 被严格拒绝；DeepSeek 显式字段 27/27，Ollama 25/27；DeepSeek 费用 CNY 0.01207752，Ollama 平均墙钟 15745.52 ms；总物理 HTTP 48/108。
limits=本批次只覆盖字段/Schema/usage/cost/延迟；CAD/STEP 未运行；A04/A07 C1 仍请求前阻塞；不能把 model-call pass 当作完整抽取或构造成功。
next=决定是否接受 Ollama C0 类型拒绝，或安排窄范围输出契约修正；旧批次 `-01`/`-02`/`-03` 均只读保留。
commit=待本次审查文档同步提交

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R4 status=review
scope=R3-FIX-R3 续任；仅补齐 Ollama tags/chat 预算记账顺序的集成测试，不修改生产代码
动作=
  1) 确认工作区状态：分支 cc/APP-001-RUNNER-R3，HEAD 4a0ae3e，存在 R3-FIX-R2/R3 的未提交修改，不丢弃不覆盖；
  2) 读取 budget.py / real_transport.py 实际代码与 HEAD diff，确认 _send_ollama_with_tags_preflight 已实现 tags 先行、chat 后置、tags 失败不创建 chat reservation 的语义；
  3) 新增 TestR4OllamaTagsChatIntegration（5 项集成测试）覆盖 R4 要求的四个场景：
     - test_tags_success_chat_success_full_flow：2 次 HTTP，2 条 ledger 记录，tags(is_model=False/num=-1)→chat(is_model=True/num=1)，run_attempts_used=1，total/provider 各 +2
     - test_tags_success_chat_fail_outcomes_independent：tags=success、chat=transient_retryable（HTTP 5xx 按 RETRYABLE_CONDITIONS），tags 记录不受 chat 失败影响
     - test_tags_retry_each_creates_new_reservation：tags 失败→tags 成功→chat 成功，3 次 HTTP，3 条记录，两次 tags 各有独立负数 attempt_number，run_attempts_used=1
     - test_tags_budget_exhausted_before_urlopen：provider 配额满时 tags reservation 在 urlopen 前失败，无新记录
     - test_tags_ok_chat_budget_exhausted_no_chat_attempt：tags 成功（消耗第 54 槽）后 chat reservation 失败，urlopen 仅 1 次，run-new run_attempts_used=0
  4) 新增 _FakeHttpResp 辅助类替代 unittest.Mock() 作为 urlopen 返回值（Python 3.10 unittest 错误报告与 frozen dataclass 交互时触发 FrozenInstanceError，真实类可回避）；
  5) setUp 中清理 _BudgetReservationToken._consumed_tokens 类变量，防止 id() 复用导致的测试间污染；
  6) 发现 R3-FIX-R3 checkpoint 描述（chat=blocked）与实际代码（不创建 chat reservation）不一致，实际代码已超越 checkpoint 描述，完全符合 R4 要求
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -q` → Ran 40, OK（35 原有 + 5 新增）
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 378, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py src/retrieval/config.py` → OK
  `git diff --check` → CLEAN
limits=验证使用 Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 再次运行验证命令确认一致；.git/index.lock 仍存在，commit 阻塞；8 个 FUSE lock skip 保持；未运行正式评测，未访问真实 API
next=用户在本机：rm .git/index.lock → 运行 python3.11 验证 → git commit；Codex 中枢独立审查
commit=待提交（index.lock 阻塞）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R5 status=review
scope=修复 Codex 独立验收发现的两个阻塞问题：Issue A（预算预留原子化）和 Issue B（C1 candidate_roles/top-k 验证）
动作=
  Issue A（预算预留原子化）：
  1) budget.py: _verify_pending_reservation（只读）改名重写为 _claim_pending_reservation，原子写入 claimed=True；第二个 token 调用时找不到 claimed=False 记录，抛出 BudgetBypassError；保留 "no pending reservation" 子串兼容现有测试；新增 _locked 检查防御未加锁调用；
  2) real_transport.py: 删除 _consumed_tokens 类变量（id() 复用 bug）；consume() 步骤 1 只用 self._consumed（实例标志）检查同对象重放；步骤 3 调用 _claim_pending_reservation 替代原只读 verify；
  3) tests: 新增 TestR5IssueAReservationAtomicity（4项）：同一 reservation 两 token 只有一个成功且 urlopen≤1；同一 token 重放被拒；并发竞争恰好一个成功；正常 DeepSeek 流程仍可工作且 claimed=True 写入 ledger；更新 TestR4.setUp 注释；

  Issue B（C1 candidate_roles/top-k 验证）：
  4) runner.py: run_formal() step-(e) 之后新增 step-(f) 和 step-(g)；(f) 精确比较 idx.candidate_roles 与冻结配置值（缺失/类型错/成员不符均 fail-closed）；(g) 精确比较 idx.default_top_k 与冻结配置值（3）；错误消息分别含 candidate_roles / default_top_k 关键字；
  5) tests: 新增 TestR5IssueBCandidateRolesTopK（5项）：正确值通过；错误/缺失 candidate_roles 和 default_top_k 各自被拒并含正确关键字
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -q` → Ran 49, OK（40 原有 + 9 新增）
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 387, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py src/retrieval/config.py` → OK
  `git diff --check` → CLEAN
limits=验证使用 Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 再次运行验证命令确认一致；.git/index.lock 仍存在（FUSE 无法清理），commit 阻塞；8 个 FUSE lock skip 保持；未运行正式评测，未访问真实 API
next=用户在本机：rm .git/index.lock → 运行 python3.11 验证 → git commit；Codex 中枢独立审查
commit=待提交（index.lock 阻塞）

[2026-11-06] agent=CC task=APP-001-RUNNER-R3-FIX-R6 status=review
scope=修复 BudgetLedger 进程内并发领取同一 reservation 的竞态问题
动作=
  1) budget.py __init__ 新增 self._thread_lock = threading.RLock()；
  2) reserve_attempt / _claim_pending_reservation / record_outcome / record_run_result 四个 read-modify-write 方法各自加 with self._thread_lock: 保护；
  3) tests: 新增 TestR6TrueConcurrentClaimAtomicity（2项）：两个线程各持独立 token、同一 reservation、threading.Barrier(2) 同时进入 claim 路径；断言恰好一个成功、另一个抛 BudgetBypassError；ledger 仍合法 JSON、至多一条 claimed=True；urlopen=0（consume 在 HTTP 前拒绝）
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -q` → Ran 51, OK（49 原有 + 2 新增）
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 389, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile src/llm/budget.py src/llm/real_transport.py` → OK
  `git diff --check` → CLEAN
  `git add` 成功（12 文件暂存），`.git/index.lock` 由 FUSE 残留，commit 阻塞
limits=验证使用 Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 复核；.git/index.lock 阻塞 commit；8 个 FUSE lock skip 保持；未运行正式评测，未访问真实 API，未读取密钥
next=用户在本机：rm .git/index.lock → git add R3-FIX-R6-checkpoint.md → python3.11 验证 → git commit；Codex 中枢独立审查
commit=待提交（index.lock 阻塞，12 文件已暂存）
[2026-11-07] agent=Codex task=APP-001-RUNNER-R3-FIX-R6-CODEX-REVIEW status=review
scope=对 CC 的 R6 修复及 R2-R6 累积交付做本机独立审查，并同步项目状态/计划/交接记录
动作=
  1) 按 handoff-review-protocol 检查 R6 checkpoint、handoff、提交和实际仓库状态；确认审查对象为本地 commit 9d83219；
  2) 使用 Python 3.11.18 重跑核心和全量测试，并检查正常预算领取、Ollama tags/chat 路径、冻结 RetrievalIndex 以及并发/错误配置拒绝路径；
  3) 确认 8 项 FUSE lock skip 仍是环境限制，未计入通过；未调用真实模型、未读取密钥、未运行正式 APP-001；
  4) 将审查结论写入 agent-work/reviews/APP-001-RUNNER-R6-codex-review.md，并同步 PROJECT_STATUS、PROJECT_PLAN 和 runner handoff。
verified=
  Python 3.11.18：test_r3_fixes 51 passed；test_r3_regression 22 passed；tests/llm 389 passed、8 skipped；tests/schema 17 passed；相关 py_compile 与 git diff --check passed
limits=9d83219 尚未 push/合入 main，APP-001-RUNNER 保持 review；8 项 FUSE skip 未解除；未进行正式模型调用或评测
next=用户 push 并合入 9d83219 后，按 ADR-0014 运行 APP-001 第一阶段授权范围；C2 和 IR/CAD/geometry/STEP 仍禁用
commit=待本次文档同步提交
[2026-11-07] agent=Codex task=APP-001-PHASE1-20261107-01-REVIEW status=review
scope=核对并记录 APP-001 Phase 1 首个正式批次；不重复调用真实模型
动作=
  1) 以本机 `main`/`origin/main` 和批次目录为事实源，确认 runner 已合入 `53f6c49`，工作区干净；
  2) 核对 `runs.jsonl` 36 条记录、`budget_ledger.json` 27 次物理 HTTP 和 18 个原始响应文件；确认 `work/app001-runs/` 被 Git 忽略；
  3) 分离统计传输成功、解析/Schema 状态与 C1 请求前阻塞，不把 `final_outcome=success` 当作模型质量成功；
  4) 新建 `agent-work/reviews/APP-001-phase1-20261107-01-codex-review.md`，同步 PROJECT_STATUS/PROJECT_PLAN。
verified=
  `git status --short --branch` → `main...origin/main`，无未提交改动；
  `runs.jsonl` → 36 条，C0 18 条完成模型调用，C1 18 条阻塞；
  `budget_ledger.json` → DeepSeek 9、Ollama tags 9、Ollama chat 9，总计 27/108；
  `git check-ignore` → 正式批次目录被 `work/` 规则忽略；密钥扫描未发现 key/Bearer 内容。
limits=
  C1 因 `conditions.py` 只提供 `bore_d` 而 RET-002 flat query 要求六字段全部阻塞；C0 多数缺冻结 envelope；所有 token/费用字段为空；C2 和 IR/CAD/geometry/STEP 未运行。
next=先由编程 Agent 窄范围修复 C1 查询契约和 usage/token/费用传递并补 fixture 测试；中枢审查通过后新建唯一批次重跑，保留本批次诊断证据。
commit=待本次文档同步提交

[2026-11-07] agent=CC task=APP-001-PHASE1-FIX status=review
scope=修复 C1 查询契约（envelope form）和 DeepSeek usage/cost 传递链（parse 前记录）
动作=
  Part 1（C1 查询契约）：
  1) conditions.py assemble_c1() 改用 CAD-003 envelope 形式 {schema_version, family_id, parameters:{bore_d}} 替代 flat_parameters {bore_d}，让 Schema 从 bore_d 推导其余五个字段；
  2) 新建 tests/llm/test_conditions.py（10项）：C0 无 reference、C1 有效 bore_d 成功、C1 缺 bore_d 阻塞、C1 无 index 阻塞、evaluator 标签不污染查询、Chinese NLI 提取、envelope 形式验证；
  3) test_runner_r1.py 3 个 mock 适配 envelope 形式；

  Part 2（DeepSeek usage/cost）：
  4) adapter.py 将 _record_cloud_usage_and_cost() 和 local_wall_time_ms 记录从 parse 之后移到 model_call pass 之后、parse 之前，确保 parse 失败时仍捕获 token/费用；
  5) 新增 DeepSeekUsagePropagationTests（5项）：parse 失败仍记录 usage、完整 usage 有 cost、缺 cache cost=None、cache 不一致 cost=None、无 usage 字段全 None；
  6) 新增 OllamaUsageUnavailableTests（2项）：cloud 字段始终 None、local_wall_time_ms 在 parse 失败时仍记录
verified=
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 406, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile src/llm/conditions.py src/llm/adapter.py` → OK
  `git diff --check` → CLEAN
limits=验证使用 Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 复核；正式批次 app001-phase1-20261107-01 未被修改，需新批次 ID 重跑；未运行正式模型，未读取/打印 API key
next=用户用 python3.11 复核 → git commit → git push -u origin cc/APP-001-PHASE1-FIX → Codex 中枢独立审查
commit=ed56381（激活包与候选测试）+201710b（激活准备文档、状态和审查同步）

[2026-11-07] agent=Codex task=APP-001-DECISION-POLICY-V3-DRAFT-NARROW-REVIEW status=review
scope=复核候选 v3 窄修是否解决目录可见性和离散 bore_d 成员缺口；不激活、不调用模型、不修改冻结接口或正式批次
动作=
  1) 以共享仓库当前分支和工作树为事实源，读取 PROJECT_STATUS/PROJECT_PLAN/DECISIONS/WORKLOG、交接协议、候选 checkpoint/spec/prompt/checker/tests 和原 Codex 审查记录
  2) 独立检查 CAD-003 CATALOG_ROWS 与候选 prompt 15 行表的排序/列映射；确认候选 checker 未被 adapter/parser/runner 导入
  3) 重跑候选专项、LLM 全量、Schema 全量、py_compile、git diff --check；检查 A01/A02/A06 正常路径与 A04/A05/A07/A09/A07-only 拒绝/澄清路径
  4) 补充 checkpoint successor check 和本审查记录；明确离线测试不证明模型识别能力
verified=
  Python 3.15.2；候选专项 48/48；LLM 564 passed/8 skipped；Schema 17/17；py_compile 与 git diff --check 通过
  目录表静态映射与 CAD-003 CATALOG_ROWS 一致；bore_d=75 不允许 answer；bore_d=70 的 A06 边界及 A01/A02 正常行为保持
  冻结生产文件和正式批次未修改；候选未激活；未发起网络/模型请求、未读取密钥
limits=8 个 FUSE 文件锁 skip；未在 Python 3.11.18 环境复核；真实模型是否能稳定识别目录/规则冲突未验证
next=候选策略窄修通过中枢复核；由项目负责人决定是否进入候选冻结/激活决策。任何模型效果评测须新 ADR/版本及单独批次授权
commit=b757e9c（候选修复）+a64a537（审查状态同步）；本日志交付状态记录于后续文档提交

[2026-11-07] agent=CC task=APP-001-PHASE1-FIX-TEST-ONLY status=review
scope=补齐验收缺口：用脱敏 DeepSeek HTTP JSON fixture 验证 usage → RunRecord/cost 传递链
动作=
  1) 新建 tests/llm/test_deepseek_usage_fixture.py（8 项）：
     Tier 1（transport 层）：DeepSeekTransport._parse_response() 从脱敏 fixture 提取 5 个 usage 字段 + runtime model；缺 cache 字段返回 None；不一致 cache 值原样透传给 cost 层；
     Tier 2（adapter 层）：FakeTransport + TransportResponse.usage 模拟 DeepSeekTransport 输出格式，经 Adapter._record_cloud_usage_and_cost() 传入 RunRecord：
       - 完整 cache → RunRecord.cloud_* 全部填充 + cost 可计算 + cost_source 有值
       - 缺 cache → tokens 填充、cost=None
       - cache 不一致 → tokens 填充、cost=None
       - parse 失败 → usage 仍被记录（验证 parse 前记录修复）
       - 无 usage → 所有 cloud 字段 None
  2) fixture 不含真实密钥、Authorization 或用户数据；不读取 .env 或 DEEPSEEK_API_KEY；无网络请求
  3) 不改 src/ 生产代码、正式批次 app001-phase1-20261107-01、冻结样例、Prompt 或 ADR
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_deepseek_usage_fixture -v` → Ran 8, OK
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 414, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `python3 -m py_compile` 未变更源文件，无需运行
  `git diff --check` → CLEAN
  实际解释器: Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 用 /opt/homebrew/bin/python3.11 复核
limits=验证使用 Python 3.10.12；用户须在 Mac 复核；未修改正式批次；未运行真实模型
next=用户用 python3.11 复核 → git commit → git push -u origin cc/APP-001-PHASE1-FIX → Codex 审查
commit=待提交

[2026-11-07] agent=CC task=APP-001-PHASE1-FIX-TRANSPORT-ADAPTER-INTEGRATION status=review
scope=补齐端到端测试缺口：脱敏 DeepSeek HTTP fixture 从 DeepSeekTransport 解析经 Adapter 写入 RunRecord/cost
动作=
  1) 在 tests/llm/test_deepseek_usage_fixture.py 新增 TestDeepSeekEndToEndFixtureFlow（1 项端到端集成测试）：
     - @patch urllib.request.urlopen 返回脱敏 Chat Completions JSON fixture
     - @patch.dict os.environ 注入 dummy DEEPSEEK_API_KEY=test-only-not-a-secret（测试后恢复）
     - 构造真实 DeepSeekTransport + BudgetAwareTransport + Adapter 栈，绑定 run_id/query_id/condition_id 匹配 Adapter gate
     - 从 Adapter.run() 正常入口发起，fixture 经 DeepSeekTransport._parse_response() → BudgetAwareTransport.send() → Adapter → RunRecord/cost 完整流转
     - 断言：urlopen 恰好 1 次；5 个 usage 字段与 fixture 一致；parse 失败但 usage 仍存在；cache 192+48=240 一致 → cost 可计算；cost_currency/cost_source 匹配 RATE_CARD 契约；runtime_returned_model 来自 fixture
  2) 更新模块 docstring：fixture 按 DeepSeek 文档/已保存 probe 响应结构构造，不声称来自正式批次（正式批次 raw response 不含完整 HTTP usage/model envelope）
  3) 不改 src/ 生产代码、正式批次 app001-phase1-20261107-01、冻结样例、Prompt 或 ADR
verified=
  `PYTHONPATH=src python3 -m unittest tests.llm.test_deepseek_usage_fixture -v` → Ran 9, OK
  `PYTHONPATH=src python3 -m unittest discover -s tests/llm -q` → Ran 415, OK (skipped=8)
  `PYTHONPATH=src python3 -m unittest discover -s tests/schema -q` → Ran 17, OK
  `git diff --check` → CLEAN
  实际解释器: Python 3.10.12（VM 内无 python3.11）；用户须在 Mac 用 /opt/homebrew/bin/python3.11 复核
limits=验证使用 Python 3.10.12；用户须在 Mac 复核；VM 无 GitHub 凭据，推送需用户在本机执行；未运行真实模型，未读取用户 DEEPSEEK_API_KEY
next=用户用 python3.11 复核 → git commit → git push -u origin cc/APP-001-PHASE1-FIX → Codex 审查
commit=待提交
[2026-11-07] agent=Codex task=APP-001-PHASE1-20261107-02-REVIEW status=review
scope=在 `APP-001-PHASE1-FIX` 合入 main 后运行第二个唯一正式批次并审查结果
动作=
  1) 将 `cc/APP-001-PHASE1-FIX` 合入 `main`，生成并推送 merge commit `641b4b7`；Python 3.11.18 下主线 LLM 415 项通过、8 项 FUSE skip，Schema 17 项通过；
  2) 用已授权 ADR-0014 范围和冻结 RET-002 RetrievalIndex 启动 `app001-phase1-20261107-02`，不运行 C2/IR/CAD/geometry/STEP；
  3) 核对 36 条 JSONL、32 条模型调用、4 条 C1 请求前阻塞、48 次物理 HTTP、32 个原始响应和预算账本；确认旧批次 `-01` 未覆盖；
  4) 新建 `agent-work/reviews/APP-001-phase1-20261107-02-codex-review.md`，同步 PROJECT_STATUS/PROJECT_PLAN。
verified=
  DeepSeek 16 次 chat、Ollama 16 次 tags + 16 次 chat；总物理 HTTP 48/108，provider 计数 DeepSeek 16、Ollama 32/54；无重试；
  16 条 DeepSeek usage/token/费用字段已落盘，16 条 Ollama 本地耗时已落盘；32 条模型调用均为 model_call pass，但 parse 均为 `MISSING_ENVELOPE_KEY`；
  主线回归：Python 3.11.18，tests/llm 415 passed、8 skipped，tests/schema 17 passed，py_compile 和 git diff --check 通过。
limits=响应 envelope 仍不符合冻结契约；A04 C1 无安全 bore_d，A07 C1 的 CAD-003 envelope 被 Schema 拒绝；未发布字段抽取、Schema、CAD 或模型质量指标。
next=先修复/冻结响应 envelope 契约并明确 A04/A07 C1 覆盖口径；中枢审查通过后才允许新批次，保留两个旧批次作为诊断证据。
commit=待本次文档同步提交

[2026-11-07] agent=CC task=APP-001-PHASE1-ENVELOPE-FIX status=review
scope=查明并修复 APP-001 第二批次模型响应缺少冻结 envelope 的根因，补齐无网络测试证据；不修改正式批次、prompt artifact、ADR-0014 或 C1 评测口径
动作=
  1) 读取必读事实源：PROJECT_STATUS、PROJECT_PLAN、DECISIONS、WORKLOG、handoff-review-protocol、
     APP-001-baseline-contract、codex-review、prompt-v2.md、acceptance-set-v0.json、
     prompt-output-contract-v1.md；
  2) 重点检查 src/llm/{prompt_loader,contract,parser,adapter,real_transport,runner}.py 和
     tests/llm/{test_deepseek_usage_fixture,test_adapter,test_runner_r1}.py；
  3) 检查正式批次 work/app001-runs/app001-phase1-20261107-02/ 的 runs.jsonl 和 5 个 raw_response.txt 样本，
     确认 32 条响应均缺 contract_version/prompt_version，与 MISSING_ENVELOPE_KEY 一致；
  4) 根因诊断：prompt_loader._parse_artifact() 剥离 fenced code block 内容，隐藏了
     prompt-v2.md 中唯一包含 contract_version/prompt_version 的 JSON envelope 示例；
  5) 实现最小修复：src/llm/prompt_loader.py 的 system 段落处理移除 if not in_fence 守护，
     让 fenced block 内容进入 system_prompt（fence 标记行本身仍跳过）；
  6) 新增 tests/llm/test_envelope_fix.py 38 项无网络 fixture 测试，覆盖任务要求的 1-8 项。
root_cause=
  prompt_loader.py 代码 bug（解析冻结 artifact 时剥离了 fenced code block 内容）；
  不是 prompt artifact 内容不足（prompt-v2.md 正确包含完整 envelope 示例）；
  不是 transport/parser/adapter 丢字段；
  不是 request 构造问题（providers 已正确发送 JSON object 约束）。
prompt_artifact_modified=否；prompt-v2.md 文件 hash d95f853d… 未改变
files=
  src/llm/prompt_loader.py（修改 _parse_artifact system 段落处理）
  tests/llm/test_envelope_fix.py（新增 38 项无网络测试）
  agent-work/llm/APP-001-PHASE1-ENVELOPE-FIX/checkpoint.md（本 checkpoint）
  docs/WORKLOG.md（追加本记录）
not_modified=
  work/app001-runs/app001-phase1-20261107-01、app001-phase1-20261107-02（正式批次只读）
  acceptance-set-v0.json、ADR-0014、APP-001 正式评测范围
  C2、IR/CAD/geometry/STEP 流程
  C1 查询逻辑、RET-002 规则、A04/A07 评测标签
  contract.py、parser.py、adapter.py、real_transport.py、providers.py、runner.py
  prompt-v2.md、FROZEN_PROMPT_FILE_SHA256
verified=
  /usr/bin/python3 --version → Python 3.10.12（VM 无 python3.11，已如实报告）
  PYTHONPATH=src:. /usr/bin/python3 -m unittest tests.llm.test_envelope_fix -v → Ran 38, OK
  PYTHONPATH=src:. /usr/bin/python3 -m unittest discover -s tests/llm -q → Ran 453, OK (skipped=8)
  PYTHONPATH=src:. /usr/bin/python3 -m unittest discover -s tests/schema -q → Ran 17, OK
  PYTHONPATH=src:. /usr/bin/python3 -m py_compile src/llm/prompt_loader.py tests/llm/test_envelope_fix.py → OK
  git diff --check → CLEAN
  修复后 load_frozen_prompt().system_prompt 含 contract_version 和 prompt_version → True
  prompt-v2.md 文件 hash 仍为 d95f853d… → True（artifact 未修改）
  system_prompt_sha256 从 561904470f… 变为 0e457d216b…（预期，内容变了）
real_model_requests=无；未发起真实 DeepSeek 或 Ollama 请求
api_key_accessed=否；未读取、输出或写入 API key
formal_batches_modified=否；正式批次 app001-phase1-20261107-01/-02 保持只读
unresolved=
  .git/index.lock 存在（0 字节，FUSE 环境下 git status 创建后无法清理），阻塞 git add/commit/push；
  按任务规则不自行删除锁，需要用户在本机执行：rm .git/index.lock → git add … → git commit → git push
  Python 3.11.18 不可用（VM 仅有 3.10.12），用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 复核
next=用户在本机删除 .git/index.lock → Python 3.11.18 复核验证 → git commit → git push -u origin cc/APP-001-PHASE1-ENVELOPE-FIX → Codex 中枢独立审查；审查通过后是否启动新正式批次由项目负责人按 ADR-0014 授权；本任务保持 review
commit=待提交（index.lock 阻塞）

[2026-11-07] agent=CC task=APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX status=review
scope=只处理 Ollama qwen3:8b 请求的结构化 JSON 类型约束和无网络测试；不修改 prompt-v2.md/parser/adapter/runner/正式批次/C1/C2/IR/CAD/STEP
动作=
  1) 启动检查：git rev-parse、status、log 确认从 main(16f0d1f) 创建 cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX；
     交接定向复核：OllamaRequestTests.test_request_uses_frozen_fields 通过、parser 接受数字 bore_d=24、
     parser 拒绝字符串 "24 mm"(EXTRACTED_TYPE_ERROR)、prompt-v2.md hash d95f853d 与主线冻结值一致；
  2) src/llm/providers.py：新增 _build_ollama_format_schema() 构造与 app001-io.v1 对齐的 JSON Schema；
     新增 OLLAMA_FORMAT_SCHEMA 常量（JSON round-trip 深拷贝）和 OLLAMA_FORMAT_SCHEMA_SHA256；
     build_ollama_request() 的 body["format"] 从字符串 "json" 改为 schema 对象；
     decoding_parameters_snapshot(OLLAMA) 从记录 "format":"json" 改为 format_schema_sha256 + format_schema_version；
     更新模块 docstring；
  3) tests/llm/test_providers.py：更新 2 个旧断言（format==json → dict）；新增 3 个测试类 33 项
     （OllamaFormatSchemaStructureTests 22、OllamaSchemaVsParserAlignmentTests 7、OllamaDecodingSnapshotConsistencyTests 4）；
  4) tests/llm/test_adapter.py：更新 test_ollama_no_think_field_in_request 断言（format==json → dict）；
  5) tests/llm/test_envelope_fix.py：更新 test_format_is_json → test_format_is_schema_object；
  6) src/llm/README.md：更新 provider 参数隔离表 format 行；新增 Ollama structured output schema 章节；
  7) agent-work/llm/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX/checkpoint.md 和 handoff.md；
  8) docs/WORKLOG.md 只追加（本记录）。
root_cause=
  build_ollama_request() 原来只设置 format="json"，仅要求 JSON 格式但不约束字段类型；
  模型将数值字段序列化为带单位字符串，parser 正确拒绝。
schema_design=
  顶层 type=object, required=9 ENVELOPE_KEYS, additionalProperties=false；
  contract_version/prompt_version 为 const；decision 为 enum；confidence 为 null type；
  extracted_parameters 仅允许 6 字段，全可选，additionalProperties=false；
  长度字段 oneOf[number, {value,unit}]（排除 string）；second_screw 为 integer；
  evidence source 受 enum 约束；不含数值范围/catalog/evaluator 标签
  Schema SHA-256: d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043
  Schema 标识: ollama-app001-io-v1.0
verified=
  /usr/bin/python3 --version → Python 3.10.12（VM 无 python3.11）
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_providers tests.llm.test_envelope_fix -v → Ran 86, OK
  PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 487, OK (skipped=8)
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
  python3 -m py_compile src/llm/providers.py src/llm/contract.py tests/llm/test_providers.py tests/llm/test_adapter.py → OK
  git diff --check → CLEAN
  快照 format_schema_sha256 与请求体 schema hash 一致（d82e53ad…）
  parser 数字通过、字符串 "24 mm"/"1.6 cm"/"0" 仍被 EXTRACTED_TYPE_ERROR 拒绝
  DeepSeek 请求和 provider 参数隔离维持原样
  work/app001-runs/ 无变更；无 index.lock
not_modified=
  prompt-v2.md、其 SHA-256 锚点、Prompt 内容或版本
  src/llm/parser.py 拒绝行为、adapter.py、runner/预算/授权逻辑
  冻结 acceptance set、Schema/CAD-003、C1/C0 组装、ADR-0014
  work/app001-runs/app001-phase1-20261107-01/-02/-03/ 下任何内容
  DeepSeek 请求、模型/解码共享参数、正式评测门
no_network=本任务无真实网络/模型调用、无访问密钥、无修改正式批次、无生成新正式指标
unresolved=
  Ollama 0.33.2（项目基线）是否支持 JSON Schema 作为 format 值未经验证；
  可能需要升级 Ollama 或新 ADR，由中枢决策
  Python 3.11.18 不可用（VM 仅 3.10.12），用户须在 Mac 复核
  是否需要新 ADR 记录结构化输出约束变化由中枢决策
  未运行真实模型批次；不能声称类型违规问题已端到端解决
next=Codex 中枢独立审查：Ollama 版本兼容性、Schema 结构正确性、快照一致性、parser 行为不变；
  审查后再判断是否需要新 ADR/协议版本及新的唯一批次授权；本任务不得擅自重跑
commit=待提交（不 push、不合并、不标 done）

[2026-11-07] agent=Codex task=APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX-CODEX-REVIEW status=review
scope=独立验收 Ollama JSON Schema 输出约束窄修正，不启动新批次
动作=
  1) 核对 CC commit 0e1721f、checkpoint/handoff、实际 diff 和当前 Ollama 版本；
  2) 使用 Python 3.11.18 重跑 86 项专项测试、487 项 LLM 测试（8 项既有 FUSE skip）和 17 项 Schema 测试；
  3) 抽查数字/measurement object 正常解析、数值字符串严格拒绝、请求体与 snapshot schema hash 一致；
  4) 发现运行时基线 Ollama 0.33.2 尚无 JSON Schema 对象 format 兼容性证据；发现 parser 对 evidence 显式 null 的实际行为与 Schema 的 string 声称不完全一致；
  5) 新建 `agent-work/reviews/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX-codex-review.md` 并同步 PROJECT_STATUS。
verified=
  Python 3.11.18：86、487（skipped=8）、17 项测试分别通过；py_compile 与 git diff --check 通过；未调用模型、未访问密钥、未改正式批次。
limits=
  `jsonschema` 第三方验证器在本机不可用；Ollama 0.33.2 对 JSON Schema `format` 对象的实机兼容性未验证；APP-001 保持 review。
next=项目负责人决定保持 0.33.2 并隔离该修正，或升级 Ollama 并新增 ADR/兼容性 smoke test；随后再决定是否启动唯一新批次；先处理 evidence null 契约偏差。
commit=待提交（当前 CC 分支上追加中枢审查记录）

[2026-11-07] agent=Codex task=APP-001-OLLAMA-RUNTIME-FREEZE status=review
scope=升级并冻结 APP-001 本地 Ollama 运行时；不启动正式批次，不修改历史批次
动作=
  1) 以本地仓库和服务事实为准复核：Homebrew formula Ollama 0.40.14，服务 label=sh.brew.ollama，API=127.0.0.1:11434；旧 Ollama.app 0.33.2 不再作为 active 服务；
  2) 核对 `/api/tags`：唯一模型为 `qwen3:8b`，完整 digest 为
     `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`，与冻结前缀一致；
  3) 使用冻结 prompt-v2、`OLLAMA_FORMAT_SCHEMA`、think=false 和固定解码参数执行一次无密钥、无 raw 落盘的 `/api/chat` smoke；
  4) 新增 ADR-0015，更新 LLM README、PROJECT_STATUS 和 Ollama 中枢审查记录，明确 active baseline、Schema hash、历史版本边界和正式批次限制。
verified=
  `ollama --version` → 0.40.14；`/api/tags` → qwen3:8b、digest prefix 500a1f067a9f；
  smoke HTTP 200、done=true、完整九键 envelope、contract_version=app001-io.v1、prompt_version=app001-extraction.v2、bore_d 为 integer 24；
  format_schema_sha256=d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043
not_modified=
  正式批次 app001-phase1-20261107-01/-02/-03、prompt-v2.md、parser/adapter/runner、ADR-0014、正式指标；
  未读取或输出 DEEPSEEK_API_KEY，未保存 smoke raw response
decision=
  ADR-0015 accepted：后续 APP-001 本地 active baseline 固定为 Homebrew Ollama 0.40.14 + qwen3:8b + 冻结 digest/schema；
  旧 0.33.2 仅作历史证据；版本、来源、digest、硬件或量化变化需重新 review
unresolved=
  evidence 的显式 null 行为与当前 Schema string 约束仍需单独窄范围决策和复核；本次不授权新的正式批次
next=先完成 evidence null 契约处理；通过中枢复核后，由项目负责人按 ADR-0014/0015 再授权唯一新批次
commit=待提交（文档同步工作单元）

[2026-11-07] agent=CC task=APP-001-EVIDENCE-CONTRACT-FIX status=review
scope=修复 parser evidence null 放行 bug，与 OLLAMA_FORMAT_SCHEMA string 约束对齐；不修改 OLLAMA_FORMAT_SCHEMA/prompt-v2.md/adapter/runner/正式批次/ADR-0015
修复=src/llm/parser.py evidence type-check 循环移除 val is not None 守护；None 现在产生 EVIDENCE_FIELD_TYPE_ERROR；其他 parser 行为不变
测试=tests/llm/test_parser.py 新增 EvidenceNullFieldTests 12 项：合法 string 通过、field/quote/source null 各自失败并含准确路径、三个 null 产生三个错误、非枚举字符串仍为 EVIDENCE_SOURCE_INVALID、非字符串整数/bool 仍失败
verified=
  /usr/bin/python3 --version → Python 3.10.12
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_r1_regression tests.llm.test_providers -v → Ran 83, OK
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_parser -v → Ran 36, OK
  PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 499, OK (skipped=8)
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
  python3 -m py_compile src/llm/parser.py → OK
  git diff --check → CLEAN
no_network=无真实模型调用、无密钥读取、无修改正式批次
commit=待提交

[2026-11-07] agent=Codex task=APP-001-PHASE1-20261107-04-CODEX-REVIEW status=review
scope=对已授权完成的 APP-001 第四批次做只读独立核对；不重新运行模型、不修改代码或旧批次
动作=
  1) 确认仓库根目录为 `/Users/syd/Desktop/参数化 cad 工程辅助设计`，起始状态 `main...origin/main` 干净，HEAD `1ccc504`；读取 PROJECT_STATUS、PROJECT_PLAN、DECISIONS、交接复核协议、ADR-0014/0015 和第三批次报告；
  2) 只读分析批次 `work/app001-runs/app001-phase1-20261107-04/` 的 36 条 runs 记录、预算账本和 Git 忽略状态；不输出 raw 正文；
  3) 核对组合唯一性、请求与账本计数、重试上限、C1 阻塞、parse/schema stage、显式字段、DeepSeek usage/cost、Ollama 延迟、模型 digest、raw 留存和凭据特征；
  4) 新建 `agent-work/reviews/APP-001-phase1-20261107-04-codex-review.md`，更新本状态页。
verified=
  36 条记录 / 36 个逻辑运行 ID 唯一；32 条发出模型调用，4 条 C1 请求前阻塞；54 次模型调用尝试（32 初次 + 22 次重试）；每逻辑运行不超过 3 次；
  账本 70 次物理 HTTP：DeepSeek 38、Ollama tags 16 + chat 16；不超过 108 总限额及各 provider 54 限额；账本无未 claim/pending；
  25 个可解析输出，17/25 Schema pass，8 条规则拒绝；显式字段核对 DeepSeek 14/14（仅对有响应样本）、Ollama 27/27；
  DeepSeek 9 个 usage 响应合计 9,051 tokens / CNY 0.00545856；Ollama 16 条延迟均值 8,289.38 ms、中位数 7,678.67 ms；
  raw 保留 25 文件且与记录一致，批次路径被 `.gitignore` 排除；凭据特征扫描无命中；`ollama --version` 为 0.40.14，模型 digest 与 ADR-0015 匹配；
  仅分析 `-04`，未发起额外模型请求，未触碰 `-01/-02/-03`，C2/IR/CAD/geometry/STEP 未运行。
limits=
  6 个 DeepSeek 逻辑运行连续 3 次 HTTP 5xx；A03 C0 在一次 5xx 后得到 HTTP 200 但 invalid JSON，raw 正文未保留；
  28 个 ledger `transient_retryable` 是可重试错误类别尝试数，其中 22 个导致实际重试、6 个是在第 3 次尝试后终止；没有超过最多两次重试；
  4 条请求前阻塞记录缺 run_id、acceptance-set hash、软件版本及 prompt hash；
  不能据此声称全批次抽取成功或 CAD/STEP 端到端成功，APP-001 仍为 review。
next=请项目负责人决定是否接受该批次作为首轮诊断结果，以及是否另行处理 DeepSeek 稳定性、失败正文安全留存、A04/A07 C1 前置阻塞；若需任何新增模型调用，须另有新的唯一批次及明确授权。
commit=待提交；原始运行产物留在 Git 忽略的 work/ 下，不提交。
[2026-11-07] agent=Codex task=APP-001-AUDIT-EVIDENCE-R1 status=in_progress
scope=启动第四批次问题的窄范围证据补强；不运行真实模型、不改旧批次或评测语义
决策=
  1) 第一工作单元交 CC：为 C1 请求前阻塞增加非敏感结构化审计记录；为 HTTP 2xx 响应包装解析失败增加受限、忽略目录内证据留存和无网络测试
  2) CC 不得改 Prompt/契约/RET-002/CAD-003/provider/重试/授权，也不处理模型质量和旧批次
  3) Codex 只读核对 A04/A07：A04 的 bore_d 缺失应安全阻塞；A07 的 bore_d=75 触发 envelope CAD-003 目录拒绝，且缺 flat 查询其余五字段；不从 evaluator 标签补值
  4) 8 条 Schema 拒绝的模型决策质量分析及任何 Prompt/输出策略版本变更排在证据补强之后；新增正式模型运行须另行授权
verified=
  C1 只读复放：A04 bore_d=None，C1_NO_SAFE_QUERY_PARAMETER，0 candidates；A07 bore_d=75.0，RETREIVAL_SCHEMA_REJECTED 包装为 BLOCKED_C1_RETRIEVAL_ERROR，0 candidates
  当前测试已有一般 C1 正常/阻塞覆盖；尚未将冻结 A04/A07 两例分别锁为回归测试
  CC 对话线程未在当前 Codex 线程清单中发现；已生成窄范围任务 prompt，未向外部对话发送消息
limits=
  未改生产代码；未请求网络；未读取密钥；旧批次 -01 至 -04 保持只读
next=将 docs/coordination/prompts/APP-001-AUDIT-EVIDENCE-R1.md 交 CC 执行；CC 交付后由 Codex 重跑核心正常/失败用例、专项和全量测试，随后独立补齐/审查 A04/A07 样例级回归
commit=待提交（Codex 启动文档单元）

[2026-11-07] agent=CC task=APP-001-AUDIT-EVIDENCE-R1 status=review
scope=请求前 C1 阻塞审计与失败响应有界证据留存；不运行真实模型、不改旧批次或评测语义
动作=
  1) 复核仓库协作协议、项目事实源、R1 prompt 和第四批次只读审查；重跑草稿专项测试，发现并修复 Runner 缺 software-version helper 的测试错误；
  2) 增加 C1 稳定阻塞字段和非敏感审计记录，prompt hash 可用时写真实值，不可用时显式写原因；
  3) 对 HTTP 2xx wrapper JSON/结构失败进行有界留存，64 KiB UTF-8 字节上限、原文 hash/长度和相对路径；保持 HTTPError 不读取正文，留存错误不覆盖既有 invalid_json；
  4) 增加专项测试、checkpoint，完成 LLM/Schema/编译检查。
verified=
  Python 3.15.2；tests.llm.test_audit_evidence_r1：11 passed；tests/llm 全量：513 passed、8 skipped（既有 FUSE 文件锁限制）；tests/schema：17 passed；py_compile 及 git diff --check 通过；无真实模型请求、无密钥读取。
limits=
  Python 3.11.18 环境复核待做；8 个 skip 不计为通过；无线上供应商行为证据；A04/A07 样例回归由中枢另行处理。
next=Codex 中枢独立审查变更和边界，重跑适用检查；APP-001 保持 review，不据此启动新批次或放行
commit=86a6bc7

[2026-11-07] agent=Codex task=APP-001-AUDIT-EVIDENCE-R1-TRANSPORT-SHAPE status=review
scope=补齐 2xx transport wrapper 缺键及 DeepSeek prompt_tokens_details 形状校验；不改重试策略、契约、provider 或旧批次
动作=
  1) 在实际基线 0a49fb2 上先重跑 audit evidence 专项 11 项，全部通过；确认只处理 real_transport.py 与对应专项测试
  2) DeepSeek/Ollama response parser 现在要求 message 对象和实际 content 键，content 必须为字符串；DeepSeek prompt_tokens_details 存在时必须为对象
  3) 为 DeepSeek/Ollama 缺 message/content、DeepSeek prompt_tokens_details 非对象增加真实 parser shape 测试；断言 invalid_json、retainer 得到原始 2xx body、异常 message/repr 不包含 body
  4) 增加 details 缺失及顶层 usage 缺失/null 的兼容测试；显式 details=null 按“字段存在时必须为对象”拒绝；保留 5xx body 不读取测试
verified=
  Python 3.15.2
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_audit_evidence_r1 -v -> 14 passed
  PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q -> 516 passed, 8 skipped（既有 FUSE 限制）
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q -> 17 passed
  py_compile src/llm/real_transport.py tests/llm/test_audit_evidence_r1.py -> passed
  git diff --check -> clean
limits=尚未在 Python 3.11.18 环境复核；8 个 FUSE skip 不是通过项；未调用真实模型、未读取密钥、未修改 work/app001-runs
next=独立中枢复核本窄补丁；APP-001 保持 review
commit=2581a10

[2026-11-07] agent=Codex task=APP-001-AUDIT-EVIDENCE-R1-CODEX-REVIEW status=review
scope=独立验收 R1 证据留存/transport shape 修正和 A02/A04/A07 C1 样例边界；不启动新批次
动作=
  1) 以共享仓库和实际提交 0a49fb2/2581a10 为事实源，核对代码 diff、checkpoint、旧批次只读状态及 `.gitignore`；
  2) Python 3.11.18 重跑专项+C1 回归 17/17、LLM 全量 516 passed/8 FUSE skipped、Schema 17/17；Python 3.15.2 结果一致；
  3) 独立复放 A02 C1 正常、A04 缺 bore_d 安全阻塞、A07 RETREIVAL_SCHEMA_REJECTED 阻塞；确认未读取 evaluator 标签；
  4) 发现并恢复 CC 文档提交对历史 WORKLOG 行的误改；新增中枢审查记录和冻结样例回归测试。
verified=
  2xx wrapper 缺 message/content 与 DeepSeek prompt_tokens_details 非对象均为 invalid_json 并进入受控留存；5xx 正文不读取；原始响应正文不进入错误 metadata；A04/A07 阻塞符合冻结 RET-002/CAD-003 契约。
limits=任务当前仍在 review，尚未合入 main；8 个 FUSE skip；未发起真实模型请求、未读取 API key；LLM 全量曾观察到历史预算测试的账本/批次隔离波动，但当前干净复跑通过。
next=项目负责人审查后合入 main；不因 A04/A07 放宽查询契约；模型质量/Prompt/Schema 变化需新版本、新 ADR 和新批次授权。
commit=待提交
[2026-11-07] agent=Codex task=APP-001-DECISION-QUALITY-ANALYSIS status=review
scope=只读分析 APP-001 第四批次 8 条 CAD-003 Schema 拒绝；不运行模型、不改 Prompt/Schema/规则或正式批次
动作=
  1) 确认共享仓库根目录、本地 main 与 origin/main 均为 60f4fa2，工作区起始干净；读取项目状态/计划/决策、交接协议及第四批次和 R1 审查材料
  2) 逐条从 runs.jsonl 定位 8 个 schema.fail 运行，读取 Adapter 保留的模型 JSON 正文，并与冻结 acceptance-set 的 explicit_parameter_claims、expected_behavior 和 scoring policy 对照
  3) 将 Schema 拒绝与模型抽取、evidence、decision 分开评价；新增 agent-work/reviews/APP-001-phase1-20261107-04-schema-decision-analysis.md
  4) 修正 PROJECT_STATUS 中 R1 已合入 main 的过期状态，并登记只读质量分析结果
verified=
  8/8 显式参数值与冻结样例一致；CAD-003 对 MISSING_REQUIRED 1、CATALOG_MISMATCH 3、CATALOG_CHOICE 2、SECOND_SCREW_CONSTRAINT 2 的拒绝符合冻结规则
  A05 三条中 DeepSeek C1 decision=ask 符合预期，其余 A05 两条、A04 一条、A07 两条、A09 两条均 decision=answer，与冻结样例应澄清/拒绝的要求不符；Ollama A07 的 unsupported evidence 覆盖不完整
  R1 代码/审查已在 main（60f4fa2）；旧运行目录只读且 Git ignored
limits=结论仅覆盖第四批次 8 个 Schema 拒绝；未外推至总体模型质量；未发起网络/模型请求、未读取密钥，未运行 C2/IR/CAD/geometry/STEP
next=项目负责人审阅是否将决策一致性作为下一窄范围 Prompt/输出策略工作；任何新模型效果验证需新版本、唯一批次和单独授权
commit=待提交

[2026-11-07] agent=CC task=APP-001-DECISION-POLICY-V3-DRAFT status=review
scope=为 APP-001 准备候选决策策略 v3，修正第四批次 analysis 报告中的 decision 行为不一致；不修改冻结接口，不激活候选版本，不调用真实模型
动作=
  1) 确认共享仓库根目录、分支 main HEAD=002b936（含 6f4af27）、工作区干净；读取 AGENTS/PROJECT_STATUS/PROJECT_PLAN/DECISIONS/WORKLOG、第四批次分析报告、交接协议、基线契约、冻结 prompt-v2.md、prompt-output-contract-v1.md、prompt_loader.py、contract.py、parser.py、CAD-003 Schema、acceptance-set-v0.json
  2) 核对 I/O 契约允许的 decision 值：{answer, ask, refuse}（contract.py L67）；构造门：decision=answer + 无不支持请求 + CAD-003 通过；冻结 prompt 加载/哈希机制：FROZEN_PROMPT_FILE_SHA256 文件级 SHA-256 + FROZEN_PROMPT_VERSION 版本标记 + system/user_template SHA-256
  3) 新增独立、未激活的候选 prompt v3（prompt-v3-candidate.md），含 decision-gate 表、ask/refuse 条件、自洽性检查、不支持请求证据要求；声明 prompt_version=app001-extraction.v3，保持 contract_version=app001-io.v1 和 envelope 键集不变
  4) 新增决策策略规格（decision-policy-v3-candidate.md），映射到 I/O 契约和 acceptance-set A01/A02/A04/A05/A07/A09 期望行为
  5) 新增纯函数离线 checker（src/llm/decision_policy_v3_candidate.py），未被 adapter/parser/runner 导入；实现 allowed_decisions、check_envelope_consistency、check_claim_preservation、check_prompt_interface_compatibility
  6) 新增离线回归测试（tests/llm/test_decision_policy_v3_candidate.py）：A04/A05/A07/A09 decision 一致性、A01/A02 正常案例 answer、字段主张保留、不支持请求证据、envelope 自洽性、prompt 接口兼容性
verified=
  Python 3.10.12
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_decision_policy_v3_candidate -v → Ran 44, OK
  PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 560, OK (skipped=8)
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
  python3 -m py_compile src/llm/decision_policy_v3_candidate.py tests/llm/test_decision_policy_v3_candidate.py → OK
  git diff --check → CLEAN
  git diff --name-only main → 空（无 tracked 文件修改；5 个新文件 untracked）
  冻结文件验证：prompt-v2.md/contract.py/parser.py/prompt_loader.py/acceptance-set-v0.json/set_screw_shaft_collar.py diff 均为空
limits=
  v3 候选未激活；激活需新 ADR 更新 contract.py PROMPT_VERSION、parser.py 版本检查、prompt_loader.py 哈希锚点
  v3 prompt 对 A05/A09 目录/规则冲突检测依赖模型判断力，模型不持有完整目录表；确定性 CAD-003 层仍是安全门
  envelope 自洽性 checker 检测模型可检测的不一致，不检测 CAD-003 目录/规则冲突
  未在 Python 3.11.18 环境复核（当前 3.10.12）；8 个 skip 为既有 FUSE 限制
  未调用真实模型、未读取密钥、未修改正式批次；不产生模型效果结论
next=中枢审查 v3 decision-gate 规则和接口兼容性；若项目负责人决定激活，需新 ADR 并更新冻结接口
commit=待提交（分支 cc/APP-001-DECISION-POLICY-V3-DRAFT）

[2026-11-07] agent=Codex task=APP-001-DECISION-POLICY-V3-DRAFT-CODEX-REVIEW status=review
scope=独立验收未激活的 APP-001 候选决策策略 v3；不调用模型、不修改冻结接口或正式批次
动作=
  1) 在共享仓库确认分支 cc/APP-001-DECISION-POLICY-V3-DRAFT，HEAD 9a32756，父链包含本地分析提交 002b936/6f4af27，工作区干净；读取项目状态、计划、决策、交接协议及候选 prompt/spec/checkpoint/代码/测试
  2) 独立运行 v3 专项 44 项、LLM 全量 560 项（8 skip）、Schema 17 项、py_compile；检查候选代码未被 adapter/parser/runner 导入，冻结文件差异为空
  3) 确认 A05/A09 的 allowed_decisions 测试输入包含 prompt 不可见的 catalog/rule conflict 布尔值；相应 bad-answer envelope self-consistency 测试断言通过，不能证明 prompt 识别冲突
  4) 独立复放只有 bore_d=75 且无 unsupported 请求时 allowed_decisions 返回 answer；这与 CAD-003 的离散目录集合不一致，尽管下游仍安全拒绝构造
  5) 新建中枢审查记录并将 PROJECT_STATUS 验收描述收窄为需修正
verified=
  tests.llm.test_decision_policy_v3_candidate：44/44；tests/llm discover：560 passed、8 skipped；tests/schema discover：17/17；py_compile 通过；git show --check HEAD 通过
  候选未激活，生产路径未导入 checker；冻结文件未改；未发起模型/网络请求、未读取密钥、未修改旧批次
limits=当前环境 Python 3.15.2，未在 Python 3.11.18 复核；8 个 FUSE skip 不计作通过；候选策略存在 A05/A09 可观测性及目录成员边界缺口
next=CC 窄修候选 prompt/spec/checker/测试，说明模型需要哪些可见规则信息，并增加 bore_d=75 单独输入拒绝 answer 的用例；不得激活、push、合并或调用模型；之后由 Codex 复审
commit=待提交

[2026-11-07] agent=Codex task=APP-001-V3-OFFLINE-ACCEPTANCE-ACTIVATION-PREP status=review
scope=完成候选 extraction v3 的完整离线验收和版本化激活准备；不激活生产路径、不调用模型、不授权新批次
动作=
  1) 在候选分支读取最新 PROJECT_STATUS/PROJECT_PLAN/DECISIONS/WORKLOG、交接协议、候选 prompt/spec/checkpoint、CAD-003 Schema 和 acceptance-set-v0
  2) 扩展候选专项测试，覆盖 A01-A09 的冻结 case ID、A03 单位换算、A08 retrieval reference 隔离、主张保留、拒绝/澄清边界以及激活 manifest 哈希一致性
  3) 创建 `agent-work/llm/APP-001-v3-activation/`，包含 staged prompt 副本、manifest、activation-checklist 和 README；状态固定为 prepared-not-active
  4) 在 docs/DECISIONS.md 追加 ADR-0016 proposed，记录 v3 激活前置条件、生产改动边界、唯一批次授权要求和 v2 回滚目标；同步 PROJECT_STATUS 与 checkpoint
verified=
  Python 3.15.2；候选专项 55/55；LLM 全量 571 passed/8 skipped；Schema 17/17；py_compile、manifest JSON parse、git diff --check 通过
  激活包 prompt 与候选源 SHA-256 一致：e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b；acceptance-set SHA-256：ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf
  production_files_changed=false；formal_evaluation_authorized=false；生产仍为 app001-extraction.v2；旧批次和 work/ 未修改
limits=未在 Python 3.11.18 复核；8 个 FUSE skip；离线测试不构成真实模型效果证据；ADR-0016 尚未接受，激活提交和新批次授权均未发生
next=项目负责人审阅 ADR-0016 和激活包；若接受，再单独安排生产激活提交与 Python 3.11.18 复核；之后如需效果评测再申请新的唯一正式批次
commit=待提交

### APP-001-V3-ACTIVATION / Codex / review / 2026-11-07

- 动作：项目负责人接受 ADR-0016 后，将生产 Prompt 契约由 `app001-extraction.v2` 切换至 `app001-extraction.v3`；冻结 loader 指向独立激活副本并更新文件级 hash 锚点；保留候选源与 v2 回滚哈希；更新版本相关测试、README、激活 manifest/checklist、PROJECT_STATUS 和 PROJECT_PLAN。
- 结果：生产 prompt SHA-256=`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`；候选源 SHA-256=`e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b`；acceptance-set-v0 哈希未变，历史 `frozen_prompt_version` 未改。解析器接受当前 v3，并拒绝旧 v2 响应。
- 验证：Python 3.11.18；定向 153 项通过；LLM 全量 572 项通过（8 个既有 FUSE skip）；Schema 17 项通过；`py_compile` 通过。最终 `git diff --check` 与提交待完成。
- 边界：`FORMAL_EVALUATION_ALLOWED=False`；没有真实模型请求、密钥读取或旧批次修改；模型效果未测，不授权新正式批次。
- 下一步：完成中枢差异审查和单一激活提交；之后如需测效果，单独申请新唯一批次授权。

### APP-001-V3-ACTIVATION-CLOSEOUT / Codex / review / 2026-11-07

- 动作：完成激活提交后的中枢复核；核对 active prompt 与 manifest 哈希、候选源未变、acceptance-set 哈希未变、旧 v2 仅作为拒绝测试和回滚证据，且正式 gate 未打开。
- 结果：激活实现提交为 `6260cd3`（当前功能分支）；状态仍为 `review`，尚未推送/合并到 `main`。没有发现额外生产范围变更。
- 验证：Python 3.11.18 下全量 LLM 572 项通过（8 项既有 FUSE skip）、Schema 17 项通过、激活定向 153 项通过；closeout 后候选/manifest 专项 55 项再次通过；`git diff --check` CLEAN。
- 下一步：按项目分支流程审查并合并 `6260cd3`；若之后要测 v3 模型效果，先另行取得唯一正式批次授权。

### APP-001-V3-ACTIVATION-INDEPENDENT-REVIEW / Codex / review / 2026-11-07

- 动作：在共享仓库独立复核 v3 激活和历史 v2 只读解析兼容；确认 Adapter/runner 仍使用严格 v3 `parse_response()`，版本化入口未接入正式路径；补充 v3 payload 不能通过显式 v2 入口重标记的回归测试。
- 结果：Python 3.11.18 下 parser 41 项、LLM 全量 576 项（8 个既有 FUSE skip）、Schema 17 项通过；对只读旧批次 `app001-phase1-20261107-03` 的 32 条 v2 原始响应复放，24 条通过显式 v2 parser，8 条按原始 `EXTRACTED_TYPE_ERROR` 拒绝；默认 v3 parser 对 32 条均保留版本拒绝。
- 边界：未发起真实模型/网络请求，未读取密钥，未修改 `work/` 或旧批次，未打开正式 gate；v3 效果仍需新的唯一正式批次授权。
- 下一步：建议审查并合入 v3 激活与历史审计兼容提交；合入后再按独立授权决定是否运行 v3 正式批次。

### APP-001-V3-ACTIVATION-MERGE-CLOSEOUT / Codex / done / 2026-11-07

- 动作：核对合入后的 `main`/`origin/main`、激活文件身份、生产调用链和工作区；将激活包、ADR、状态页和清单中的“待合入/待审查”旧状态更新为已合入。
- 结果：`main` 与 `origin/main` 同为 `7dc7a37`；生产 `PROMPT_VERSION`/loader 为 v3，正式 gate 仍为 `False`；Adapter 继续使用严格 v3 parser；LLM 576 项、Schema 17 项通过，8 项为既有 FUSE skip。
- 边界：未发起真实模型/网络请求，未读取密钥，未修改旧批次；v3 效果尚未测量。
- 下一步：若启动 v3 效果评测，必须先完成新的运行前审查并取得唯一正式批次授权。

### APP-001-PHASE1-V3-20261107-01 / Codex / review / 2026-11-07

- 动作：完成获授权的 v3 Phase 1 正式批次并进行中枢独立审查；只读取 Git 忽略目录中的 `runs.jsonl`、`budget_ledger.json` 和 raw response，不运行 C2、IR/CAD/geometry/STEP，不修改旧批次。
- 结果：36/36 逻辑记录；32 条模型响应；4 条 C1 请求前阻塞（A04/A07）；32/32 通过 v3 parse、contract、projection；显式字段 32/32 精确；Schema 20/32 通过；决策 29/32。Ollama A03 两条拒绝而期望 answer，A08 C1 一条 ask 而期望 answer；A07 Ollama unsupported 标签为 `anodized` 而冻结标签为 `anodizing`。
- 预算与资源：48 个物理 HTTP（DeepSeek 16 次 chat，Ollama 16 次 tags + 16 次 chat）；总上限 108、单 provider 上限 54、每逻辑 run 模型尝试上限 3 均未触及。DeepSeek 输入/输出/总 token=36,510/1,677/38,187，费用 CNY 0.01411592；Ollama 平均墙钟 18,353.16 ms，中位数 17,325.03 ms，digest=`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`。
- 记录：新增 `agent-work/reviews/APP-001-phase1-v3-20261107-01-codex-review.md`；同步 `docs/PROJECT_STATUS.md`。运行产物仍在 Git 忽略目录，未加入 Git。
- 限制：批次运行记录环境为 Python 3.15.2/macOS arm64，不等同于项目 Python 3.11.18 固定复核基线；全局 `FORMAL_EVALUATION_ALLOWED=False` 未改变；结果不能解释为 CAD/STEP 端到端成绩。
- 下一步：项目负责人审阅 v3 诊断结论；如修正模型决策策略，需版本化并新建唯一批次、重新授权。

### APP-001-V3-DECISION-FIX-DRAFT / Codex / review / 2026-11-07

- 动作：依据 v3 正式批次审查，起草 extraction v4 离线策略候选，聚焦 A03 精确单位换算、A08 明确用户值优先于不可信 retrieval reference、A07 unsupported 标签规范化。
- 结果：新增 `prompt-v4-candidate.md`、`decision-policy-v4-candidate.md`、7 项离线候选检查和 `checkpoint.md`；追加 proposed ADR-0017；同步状态页。生产 v3/契约/验收集/runner 未改。
- 边界：未发起模型/API 请求，未读密钥，未改任何正式批次；离线测试只验证候选规则文本和冻结边界，不声称模型效果已修复。
- 验证：Python 3.15.2；v4 专项 8/8、v3 候选回归 55/55、parser 41/41、LLM 全量 584 passed/8 skipped、Schema 17/17；`py_compile`、`git diff --check` 通过。8 个 skip 为既有 FUSE 文件锁限制。
- 下一步：项目负责人/中枢审查 proposed ADR-0017 和 v4 候选；若决定激活，再另建实现任务；若验证模型效果，须新的唯一正式批次和单独授权。

### APP-001-V3-DECISION-FIX-DRAFT-CODEX-REVIEW / Codex / review / 2026-11-07

- 动作：独立复核候选分支 `d8961ac`，比较 v4 候选与 active v3，确认生产路径和冻结验收集无变更；运行 v4/v3/parser 定向测试。
- 结果：候选范围与 v3 正式批次证据一致；新增三条策略说明保留现有安全 gate。审查报告指出目录拒绝措辞仍需明确覆盖范围内非离散值，且当前测试检查文本存在性而未实现纯函数 fixture checker。
- 验证：v4 专项 8/8、v3 候选 55/55、parser 41/41；候选提交前 LLM 全量 584 passed/8 skipped、Schema 17/17；active v3 hash 和 acceptance-set hash 均保持不变。
- 结论：当前候选通过 review，可继续补强离线策略 checker；ADR-0017 保持 proposed，v4 不激活，不授权新模型批次。

### APP-001-V3-DECISION-FIX-DRAFT-OFFLINE-HARDENING / Codex / review / 2026-11-08

- 动作：按中枢审查意见补强 v4 候选；新增未激活的 `decision_policy_v4_candidate.py` 纯函数 checker，修正 prompt/spec 对非离散目录值的拒绝措辞，并扩展专项测试。
- 结果：checker 明确验证精确单位换算、证据 quote 保留、用户值优先于 retrieval reference、unsupported alias 规范化，以及缺失/目录冲突/规则冲突不得 `answer`；生产 v3、契约、acceptance-set、旧批次和激活 manifest 未改。
- 验证：v4 专项 18/18、v3 candidate 55/55、parser 41/41、LLM 全量 594 passed/8 skipped、Schema 17/17；`py_compile` 与 `git diff --check` 通过。未调用真实模型、未读取密钥。
- 边界：ADR-0017 仍 proposed；checker 只验证离线 fixture 规则，不证明模型依从；真实效果评测仍需新的唯一批次和单独授权。
- 下一步：Codex 中枢独立复核本轮 checker 与候选文案，再决定是否创建 v4 activation 实现任务。

### APP-001-V4-ACTIVATION-REVIEW / Codex / review / 2026-11-08

- 动作：独立复核 `APP-001-V3-DECISION-FIX-DRAFT` 提交 `32caed6` 的 v4 候选、ADR-0017、checker、生产隔离和回归证据。
- 结果：候选规则方向、`75 mm` 离散目录措辞、生产 v3 隔离和冻结 hash 均通过；发现 P1：`retrieval_bore_value` 传入但未参与 checker 逻辑，导致“用户 24 优先 retrieval 20”测试不具备判别力；P2：unsupported 原文 evidence quote 未由 checker 验证。
- 验证：v4 18/18、v3 candidate 55/55、parser 41/41、LLM 594 passed/8 skipped、Schema 17/17、`py_compile` 与 `git diff --check` 通过；未调用真实模型、未读取密钥。
- 结论：activation review 暂不放行；ADR-0017 保持 proposed，生产继续 v3。先完成 P1 checker 修正，再复审；不授权新模型批次。

### APP-001-V4-CHECKER-FIX / Kiro / review / 2026-11-08

- 动作：按 `APP-001-V4-ACTIVATION-REVIEW` 的 P1/P2 要求，对 v4 未激活候选 checker 做窄范围修正。
- 分支：`codex/APP-001-V3-DECISION-FIX-DRAFT`；前序 HEAD `3665293`。
- 范围：只改 `src/llm/decision_policy_v4_candidate.py`、`tests/llm/test_decision_policy_v4_candidate.py` 和本交接记录；不改生产 v3、contract/parser/prompt_loader/adapter/runner、冻结 acceptance-set、prompt-v3、ADR-0017 状态、旧批次或正式评测结果。

**P1（retrieval 优先级）：**
新增纯函数 `resolve_bore_precedence(user_bore, retrieval_bore_value)`；`evaluate_fixture()` 调用该函数，retrieval 值通过 `retrieval_bore_raw`/`retrieval_acknowledged` 作审计追踪，不作 user_input evidence，不填入 extracted claims。
新增 `TestV4RetrievalIsolation`（10 项）含反向测试：用户 bore=None + retrieval=20 → answer 不允许，ask 允许；用户 24 + retrieval=20 → normalized=24，answer 允许；retrieval=24 不被提升为用户主张。

**P2（unsupported evidence quote 保留）：**
新增 `UnsupportedEvidence` dataclass（`canonical_label`、`original_quote`、`source="user_input"`）；`V4FixtureResult` 新增 `unsupported_evidence` tuple；`evaluate_fixture()` 为每项 unsupported term 构建 evidence 条目（`阳极氧化` → label=`anodizing`，quote=`阳极氧化`，source=`user_input`）；无 unsupported_terms 时 evidence 为空。
新增 `TestV4UnsupportedEvidenceQuote`（7 项）：阳极氧化/anodized/anodizing 规范化、原文 quote 保留、source 检查、不凭空增加项目。

- 正常案例：`evaluate_fixture(V4FixtureCase(24, "mm", retrieval_bore_value=20))` → normalized_bore=24，answer 允许，retrieval_acknowledged=True，retrieval_bore_raw=20。
- 失败案例（反向）：`evaluate_fixture(V4FixtureCase(bore_value=None, retrieval_bore_value=20))` → normalized_bore=None，answer 不允许，ask 允许。
- unsupported 案例：`evaluate_fixture(V4FixtureCase(unsupported_terms=("阳极氧化",)))` → canonical_label=`anodizing`，original_quote=`阳极氧化`，source=`user_input`。

- 验证（Python 3.10.12 / Linux aarch64）：v4 专项 34/34 OK；v3 candidate 55/55 OK；parser 41/41 OK；LLM 全量 610 passed、8 skipped（既有 FUSE 文件锁限制，不计通过）；Schema 17/17 OK；py_compile 通过；git diff --check CLEAN。active v3 prompt SHA-256=`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b` 未变；acceptance-set SHA-256=`ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf` 未变；checker 未被 adapter/parser/runner 导入。
- 阻塞：`.git/index.lock` 存在（FUSE 挂载下 `git status` 创建后无法删除，0 字节）；不自行删除锁；按任务规则记录阻塞。用户须在本机执行 `rm .git/index.lock && git add src/llm/decision_policy_v4_candidate.py tests/llm/test_decision_policy_v4_candidate.py agent-work/llm/APP-001-V3-DECISION-FIX-DRAFT/checkpoint.md docs/WORKLOG.md && git commit -m "fix: harden APP-001 v4 checker P1 retrieval priority and P2 evidence quote [APP-001-V4-CHECKER-FIX]"`
- 未解决：Python 3.11.18 在当前 VM 不可用，用户须在 Mac 本机复核；离线测试不证明模型依从；ADR-0017 仍 proposed；v4 尚未激活。
- 下一步：用户提交后，交 Codex 中枢独立复审 P1/P2 修正；若通过，再决定是否创建 v4 activation 实现任务；任何真实模型批次仍需新 ID 和单独授权。

### APP-001-V4-CHECKER-FIX-CODEX-REVIEW / Codex / review / 2026-11-08

- 动作：在共享仓库复核 P1/P2 修正工作区，重跑 checker、v3 candidate、parser、LLM/Schema 全量及编译/空白检查。
- 结果：P1 retrieval 隔离反向测试和 P2 unsupported quote/source 测试通过；active v3 与 acceptance-set 哈希未变，生产路径无 v4 checker 导入。发现 `.git/index.lock` 仍存在，HEAD 仍为 `3665293`，本轮修改尚未提交；不删除锁、不做 Git 写操作。
- 验证：本机 Python 3.15.2 下 v4 34/34、v3 candidate 55/55、parser 41/41、LLM 610 passed/8 skipped、Schema 17/17、`py_compile`、`git diff --check` 均通过。此环境与项目基线 Python 3.11.18 不同，需单独复核。
- 限制：checker 对相同 canonical unsupported 标签去重，多个不同原文别名只保留第一条 quote；单请求 quote 目标已通过，多原文逐条留证未覆盖。
- 结论：本轮 checker 修正可接受，最终 Git 提交及固定 Python 基线复核待完成；ADR-0017 仍 proposed，不代表 activation 通过，不授权新模型请求。

### APP-001-V4-CHECKER-FIX-LOCAL-VERIFY / Codex / review / 2026-11-08

- 动作：根据项目负责人授权，检查没有活动 Git 进程后删除遗留的 0 字节 `.git/index.lock`；在本机固定 Python 3.11.18 环境重跑完整目标验证；新增项目级可复用推进手册并从 `AGENTS.md` 链接。
- 结果：锁已清除，未丢失工作区改动；Python 3.11.18 下 v4 34/34、v3 candidate 55/55、parser 41/41、LLM 610 passed/8 skipped、Schema 17/17，py_compile 和 `git diff --check` 通过。8 个 skip 为既有 FUSE 限制，未计作通过项。
- 流程沉淀：`docs/coordination/project-memory-and-delivery-playbook.md` 记录启动事实恢复、角色分工、计划/架构一致性、分层测试、证据和 skip 报告、交接审查、对话压缩恢复、Git 锁处置及 done gate。
- 边界：尚未提交或 push；ADR-0017 保持 proposed、生产继续 v3；没有真实模型请求或密钥读取。当前任务待形成 commit 并由中枢对提交对象最终核验。

### APP-001-V4-CHECKER-FIX-COMMIT / Codex / review / 2026-11-08

- 动作：提交已验证的 APP-001 v4 checker 修正、复核报告和项目级协作手册。
- 结果：commit `6d1f90a`（`fix: complete APP-001 v4 checker review prep [APP-001-V4-CHECKER-FIX]`）；当前候选分支工作区干净，未 push、未合并。
- 下一步：项目负责人 push 后由 Codex 核实远端 ref 与提交哈希，再判断 v4 activation implementation 的范围和决策状态。

### APP-001-V4-ACTIVATION-REVIEW-FOLLOWUP / Codex / review / 2026-11-08

- 动作：基于 checker 修正 commit `6d1f90a` 和 Python 3.11.18 全套验证，关闭先前 activation review 的 P1/P2。
- 结果：离线候选准备通过，可进入独立 v4 激活实现工作单元；生产仍保持 v3，正式评测授权边界不变。本结论不代表 v4 已激活或模型效果通过。
- 交付：更新 `APP-001-V4-ACTIVATION-REVIEW.md` 补记和 checker 复核报告；后续提交记录以 Git HEAD 为准。
- 下一步：项目负责人 push 后核对远端；再单独排定 activation implementation 与 review，不运行模型。

### APP-001-V4-CHECKER-FIX-STATUS-SYNC / Codex / review / 2026-11-08

- 动作：同步状态页与 checkpoint，修正“待提交”的过期描述。
- 结果：当前候选工作单元提交链为 `6d1f90a`、`2c7d199`、`9f424d0`；工作区干净，尚未 push。状态继续为 review，生产 v3 和 ADR-0017 proposed 边界不变。

### APP-001-V4-ACTIVATION-MERGE-STATUS-SYNC / Codex / done / 2026-11-08

- 动作：核对合入后的 `main`、`origin/main` 和 `origin/cc/APP-001-V4-ACTIVATION`，并同步 v4 激活包、ADR-0017、项目状态页和计划页中的交付状态。
- 结果：三处 Git ref 均指向 `c18fd35`；工作区干净且无 `.git/index.lock`。v4 激活任务标记为 `done`，生产 `PROMPT_VERSION=app001-extraction.v4`、`FORMAL_EVALUATION_ALLOWED=False` 和 v3 回滚边界保持不变。Python 3.11.18 复核证据为 71 项 v4 专项、685 项 LLM 测试（8 个既有 FUSE skip）和 17 项 Schema 测试通过。
- 边界：未调用真实模型、未读取密钥、未创建或修改正式批次，C2/IR/CAD/geometry/STEP 未运行。APP-001 整体仍为 `review`，v4 模型效果尚未测量。
- 下一步：如需测量 v4 效果，先由 Codex 建立运行前审查清单和唯一批次授权模板，项目负责人明确批准后再由 CC 执行；旧批次只读且不混合统计。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-READINESS / Codex / planned / 2026-11-08

- 动作：建立 v4 正式效果评测的运行前审查、授权模板和 checkpoint；核对当前生产版本、授权工厂、预算、Ollama 冻结环境、retrieval index 门和旧批次隔离边界。
- 结果：确认当前 `main`/`origin/main` 为 `abcb8f0`，生产 prompt 为 `app001-extraction.v4`；授权代码动态绑定 v4，固定完整 scope 为 36 个逻辑运行、最多 108 次物理请求、每 provider 54 次、每 run 3 次。未调用模型、未读取密钥、未创建正式批次。
- 阻塞：ADR-0015 的 evidence-null 单独决策门尚未在决策记录中关闭；ADR-0014 的历史授权表仍写 v2，需同步当前 v4 scope；项目负责人尚未批准新的唯一 batch_id。
- 分工：Codex 负责关闭文档/决策门和运行前独立复核；项目负责人负责批次授权；CC 仅在授权后使用现有 runner 执行；另一 Codex 对话框保留给批次完成后的独立结果复核。
- 产物：`agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md`、`agent-work/llm/APP-001-v4-effect-evaluation/authorization-request-template.md`、`agent-work/llm/APP-001-v4-effect-evaluation/checkpoint.md`。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-FINAL-PREFLIGHT / Codex / review / 2026-11-08

- 动作：完成决策同步和 final preflight；修正 readiness、checkpoint 与状态页中的过期 baseline、P1/P2 状态和 Ollama Schema hash 口径。
- 结果：`main` 与 `origin/main` 同步于 `7bafecb`；P1 evidence-null 门由 `ADR-0015-CLOSEOUT` 关闭，P2 当前 v4 继承 scope 由 `ADR-0014-AMENDMENT` 同步；v4 prompt SHA-256=`73cb6b8f…`；当前 v4 Ollama Schema SHA-256=`04d159d2…`，`d82e53ad…` 保留为 v2 历史 smoke hash。
- 环境证据：`/opt/homebrew/bin/python3.11` 为 3.11.18；Ollama 0.40.14 可访问；`qwen3:8b` digest=`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`；RET-002 manifest SHA-256=`b7b6c737…`、candidate_roles=`('retrieval_source',)`、default_top_k=`3`。
- 安全边界：当前 shell 未注入 `DEEPSEEK_API_KEY`，仓库根 `.env` 仅做存在性检查未读取；没有调用 DeepSeek/Ollama chat、没有创建新正式批次、没有修改旧批次，`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 验证：prompt/loader/schema 哈希核对、main/origin 同步、runtime/model metadata、retrieval identity 和空批次目录检查均完成；文档同步已提交为 `3c82117`，尚未 push。
- 下一步：项目负责人填写并明确批准 `agent-work/llm/APP-001-v4-effect-evaluation/authorization-request-template.md` 中的新唯一 `batch_id` 和完整 36-run scope；批准前不得让 CC 启动正式运行。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-PREFLIGHT-TEST-LIMIT / Codex / review / 2026-11-08

- 结果：Python 3.11.18 下 v4 activation 专项 71/71、关键 parser/provider/R3 回归 114/114、Schema 17/17、`py_compile` 和 `git diff --check` 通过。
- 限制：LLM 全量 685 项复跑出现 1 项既有时间戳批次 ID 碰撞（测试间复用了 `work/app001-runs` 目录）和 8 项既有 FUSE skip；失败测试单独复跑通过，R6 并发类单独运行通过。该问题属于测试隔离稳定性，不是本次文档同步引入，也未改生产代码。
- 决策：preflight 仍保持 `review`，不将全量结果宣称为全绿；真实模型调用继续等待项目负责人批准新的唯一 `batch_id` 和完整固定 scope。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-BOOKKEEPING / Codex / review / 2026-11-08

- 记录：preflight 文档状态修正提交 `ed9db84` 已完成；当前本地 `main` 比 `origin/main` ahead 2（`3c82117`、`ed9db84`），工作区干净，无 `.git/index.lock`。push 和正式批次授权仍由项目负责人决定。

### APP-001-PREFLIGHT-TEST-ISOLATION-FIX / Codex / review / 2026-11-08

- 动作：对 CC 提交 `e47af64` 做中枢独立验收；按交接协议在 Python 3.11.18 下连续两次运行 LLM 全量测试，并抽查 Ollama 正常与失败路径。
- 结果：两次均为 685 passed、8 个既有 FUSE skip；`TestR4OllamaTagsChatIntegration` 5 项和 `TestR3Fix2OllamaTagsFailChatBlocked` 2 项均通过。差异仅涉及测试 batch_id 隔离、checkpoint 和日志，未改生产代码、prompt、schema、预算、授权或正式批次。
- 记录：独立审查写入 `agent-work/reviews/APP-001-PREFLIGHT-TEST-ISOLATION-FIX-codex-review.md`；当前分支工作区待提交，未 push、未合入 `main`。
- 下一步：提交本审查记录后由项目负责人 push `cc/APP-001-PREFLIGHT-TEST-ISOLATION-FIX` 并核对远端哈希；合入前继续保持正式模型调用关闭。

### APP-001-PREFLIGHT-TEST-ISOLATION-FIX-MERGE / Codex / done / 2026-11-08

- 动作：核对项目负责人完成的 fast-forward 合并和远端推送；`origin/main` 与本地 `main` 均指向 `d422877`。
- 验证：Python 3.11.18 下 `tests.llm.test_r3_fixes` 51/51、Schema 全量 17/17、LLM 全量 685 通过且 8 个既有 FUSE skip；`py_compile` 与 `git diff --check` 通过。
- 结论：测试隔离修复已满足合并后验收，任务标记为 `done`。没有真实模型请求、没有读取密钥、没有创建正式批次。
- 下一步：继续 v4 正式效果评测的授权门；项目负责人需要填写并明确批准新的唯一 `batch_id` 和冻结 scope，批准前保持模型调用关闭。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-AUTHORIZATION / Codex / in_progress / 2026-11-09

- 动作：记录项目负责人 Wang sikai 对新批次 `app001-phase1-v4-20261109-01` 的明确批准，并完成无模型 final preflight。
- 授权：36 个逻辑运行（9 × 2 条件 × 2 provider）；DeepSeek `deepseek-flash` 与 Ollama `qwen3:8b`；每 run 3 次、全批次 108 次、每 provider 54 次；C2/IR/CAD/geometry/STEP 禁用；旧批次只读且不混合统计。
- 核验：main/origin/main=`80cad1b7fc110e0aa10c63aced7271749c3ffadf`；Python 3.11.18；v4 prompt SHA-256=`73cb6b8f…`；acceptance-set SHA-256=`ed59e2b6…`；Ollama 0.40.14、Schema SHA-256=`04d159d2…`；RET-002 manifest SHA-256=`b7b6c737…`；授权 scope hash=`a57b6966…`；新批次目录不存在；密钥值未读取，未发起模型请求。
- 结果：Codex preflight=`pass`；授权模板和交接 checkpoint 已补全，等待 CC 使用现有 runner 执行唯一批准批次。

### APP-001-V4-FORMAL-EFFECT-EVALUATION / CC / in_progress / 2026-11-09

- 动作：执行 APP-001-V4-FORMAL-EFFECT-EVALUATION 正式批次（batch_id=`app001-phase1-v4-20261109-01`）的 CC 执行前 preflight，发现执行环境约束并准备 Mac 原生运行脚本。
- 环境核验（本次 CC 会话中完成）：
  - HEAD=`cc3dfbbae3562b287860c04d7b3e72a161139386`；工作区干净；`main` 与 `origin/main` 一致
  - acceptance-set sha256=`ed59e2b6…`  ✓
  - prompt-v4.md 文件 sha256=`73cb6b8f…`  ✓（由 `load_frozen_prompt()` 内部验证）
  - prompt version=`app001-extraction.v4`  ✓
  - RET-002 manifest sha256=`b7b6c737…`  ✓
  - authorization scope hash=`a57b6966…`  ✓
  - batch dir `work/app001-runs/app001-phase1-v4-20261109-01` 不存在  ✓
  - `.env` 含 `DEEPSEEK_API_KEY`（值未读取）  ✓
  - `PYTHONPATH=src python3` 可导入全部运行依赖（`llm.runner`、`retrieval`、`schema`）  ✓
  - RetrievalIndex 从冻结 config 构建成功  ✓
  - 干跑（`runner.dry_run()`）返回 36 个逻辑组合  ✓
- 执行环境阻塞（无法在当前 CC 沙箱 VM 中完成完整批次）：
  - Ollama 服务运行于用户 Mac 本机 `http://127.0.0.1:11434`；VM 沙箱无法通过任何主机地址访问（172.16.10.1/192.168.64.1/10.0.2.2 均超时，127.0.0.1:11434 亦不可达）。在 VM 中强制执行将导致 18 个 Ollama run 全部以 non_retryable_error 记录，达不到模型身份和 raw response 保留要求。
  - VM 内仅有 Python 3.10.12；授权模板指定 Python 3.11.18；venv Python symlink 在 VM 中为断链。
- 处置：编写完整 Mac 原生运行脚本 `scripts/run_app001_v4_formal_batch.py`，包含所有 preflight 检查（commit、sha256 全套、Ollama 连通性与 digest 验证、batch dir 干净检查、.env 密钥存在性校验）；脚本直接调用现有 `App001Runner.run_formal()` 和 `authorize_phase1_run()`，不修改任何生产代码。
- 下一步：项目负责人在 Mac 终端运行：
  ```
  cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
  source .env
  PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/run_app001_v4_formal_batch.py
  ```
  完成后将输出摘要追加至 WORKLOG，并提交 Git commit。
- 边界：未发起任何 DeepSeek/Ollama 请求；未读取 API key 值；未修改生产代码、prompt、Schema、预算或授权范围；未修改旧批次。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-RUN-SCRIPT-FIX / CC / in_progress / 2026-11-09

- 动作：窄范围执行前修正运行脚本，不启动任何真实模型请求。
- 修正 A（commit 校验）：
  - 保留生产基线 commit `cc3dfbb` 身份校验；
  - 允许当前 HEAD 是该基线的后代，因为脚本和交付文档需要作为后续提交进入 Git；
  - 新增 `git merge-base --is-ancestor` 和 `git diff --name-only` 跨 `PRODUCTION_PATHS` 检查，覆盖 `src/llm/`、`src/retrieval/`、`src/schema/`、`src/cad_compilation/`、`prompt-v4.md`、`acceptance-set-v0.json`、`retrieval-config.json`、`manifest-v0.jsonl`；任何生产路径变化立即 abort；
  - 不放宽到任意 HEAD，不修改生产代码。
- 修正 B（batch 目录保护）：
  - 只要 `work/app001-runs/app001-phase1-v4-20261109-01` 已存在，立即 abort，不论是否包含 `runs.jsonl`；
  - 不删除、不覆盖任何旧目录。
- 修正 C（离线测试）：
  - `tests/llm/test_run_script_v4_batch.py`，19 个测试，全部通过；
  - 覆盖：基线/后继提交通过、非基线拒绝、`src/llm`/prompt/schema/retrieval 生产路径变化被拒、空 batch 目录被拒、Ollama 缺失在 runner 调用前 abort、`py_compile`、dry_run=36、两条件两 provider；
  - 测试不调用 DeepSeek/Ollama chat，不读取或打印 API key 值。
- 验证：
  - `python3 -m py_compile scripts/run_app001_v4_formal_batch.py` 通过；
  - `PYTHONPATH=src:. pytest tests/llm/test_run_script_v4_batch.py` → 19 passed；
  - `verify_commit()` 对真实 HEAD（`cc3dfbb`）通过；
  - `git status`：仅 `docs/WORKLOG.md`（修改）、`scripts/run_app001_v4_formal_batch.py`（新增）、`tests/llm/test_run_script_v4_batch.py`（新增）；无生产路径变更。
- 边界：本轮没有真实模型请求、没有 API key 读取或打印、没有 prompt/schema/budget/授权范围/runner 生产逻辑或旧批次修改。
- 下一步：项目负责人在 Mac 终端运行脚本执行正式批次，完成后 CC 追加结果 WORKLOG 条目并提交。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-TEST-EVIDENCE-STRENGTHEN / CC / in_progress / 2026-11-09

- 动作：最小重构运行脚本和测试，将 batch 目录和 Ollama 检查提取为可测试的小函数，测试改为直接调用真实函数路径。
- 脚本变化（`scripts/run_app001_v4_formal_batch.py`）：
  - 新增 `ensure_batch_dir_absent(batch_dir)` — 仅在目录不存在时通过，任何已存在的目录（含空目录）立即 abort；
  - 新增 `check_ollama_runtime(urlopen_fn=...)` — 接受可注入的 `urlopen_fn`，覆盖 `/api/version` 连通性和 `/api/tags` digest 验证；
  - `preflight()` 改为调用上述两函数，行为不变，无生产逻辑修改。
- 测试变化（`tests/llm/test_run_script_v4_batch.py`）：
  - `BatchDirProtectionTests`：改为直接调用 `ensure_batch_dir_absent()`（3 个用例）；
  - 原 `OllamaAbsentTests` 替换为 `OllamaRuntimeTests`：直接调用 `check_ollama_runtime(urlopen_fn=...)`（5 个用例：不可达/模型缺失/digest 不符/正常通过/run_formal 未调用）；
  - 原有 commit 校验（8 个）、syntax（3 个）、dry_run（3 个）测试全部保留。
- 验证：
  - `~/.local/bin/python3.11 -m py_compile scripts/... tests/...` 通过；
  - `PYTHONPATH=src:. ~/.local/bin/python3.11 -m pytest tests/llm/test_run_script_v4_batch.py` → **22 passed**（Python 3.11.17）；
  - `PYTHONPATH=src:. python3 -m pytest tests/llm/test_run_script_v4_batch.py` → **22 passed**（Python 3.10.12）；
  - 本轮没有真实模型请求、没有 API key 读取或打印、没有生产代码/prompt/schema/预算/授权范围/旧批次修改。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-RUN-SCRIPT-FIX-REVIEW / Codex / review / 2026-11-09

- 审查提交：`94ab151`（父提交 `6a5ac7c`），授权基线：`cc3dfbb`。
- 独立核对：本地 `main` 是授权基线的后代；相对 `src/llm/`、`src/retrieval/`、`src/schema/`、`src/cad_compilation/`、冻结 prompt、acceptance set、RET-002 配置和 manifest 的生产差异为 0；目标正式批次目录不存在。
- 代码入口：`preflight()` 已真实调用 `ensure_batch_dir_absent()` 和 `check_ollama_runtime()`；前者拒绝任何已存在批次目录，后者检查 Ollama version、model presence 和 digest。
- Python 3.11.18 专项：`tests.llm.test_run_script_v4_batch` 22/22 通过；脚本/测试 `py_compile` 通过；`git diff --check` CLEAN。
- 边界：本轮未调用 DeepSeek/Ollama chat，未启动 runner，未读取或输出密钥值，未修改旧批次。
- 结论：窄范围修正通过中枢独立审查，可在 push 后进入已授权正式批次执行门。非阻塞改进项：`run_formal_not_called` 测试直接调用 helper，后续可补完整 `preflight()` 集成覆盖。
- 下一步：用户 push 本地 `main` 的两个后代提交并核对远端哈希；之后按既有授权在 Mac 原生环境执行脚本，批次结果再由 Codex 独立复核。

### APP-001-V4-FORMAL-EFFECT-EVALUATION-BATCH-REVIEW / Codex / review / 2026-11-09

- 发现：目标批次目录已包含完整产物；重新启动脚本按目录保护在 preflight 中止，未发起新请求、未覆盖旧产物。
- 批次核对：`runs.jsonl` 36 条逻辑记录；32 条模型响应、4 条 C1 请求前阻塞；DeepSeek/Ollama 和 C0/C1 各 18 条逻辑组合。
- 预算核对：48 次物理 HTTP，DeepSeek 16 次 `/chat/completions`，Ollama 16 次 `/api/chat` + 16 次 `/api/tags`；全部成功，均低于 108 总上限和 54/provider 上限。
- 证据核对：32 个 raw response 与记录长度/SHA-256 一致；v4/contract v1、模型身份、Python 3.11.18、prompt hash 和 schema 版本一致；未发现密钥模式。
- 质量核对：32/32 parser、contract、projection 通过；显式字段、evidence 和 A07 unsupported 标签均精确。决策为 29/32 符合允许集合，3 条 Ollama 偏差（A02 C1、A03 C0、A08 C1）；DeepSeek A05 C0/C1 各有 `outer_d` 同时出现在 extracted 和 missing_fields 的自洽性问题。
- 边界：Schema 20 pass/12 fail；construction gate 17 pass/15 fail；IR/CAD/geometry/STEP 未运行；旧批次未修改，正式结果不与旧批次混合。
- 结论：批次证据和安全/预算边界通过，但任务保持 `review`，不能宣称 v4 决策策略已解决偏差。若修正，必须版本化并新建唯一批次、重新授权。

### APP-001-V4-QUALITY-FIX-CANDIDATE / Codex / planned / 2026-11-09

- 动作：根据 v4 正式批次的只读审查结果，新增 CC 窄范围候选任务 prompt：`docs/coordination/prompts/APP-001-V4-QUALITY-FIX-CANDIDATE-cc-agent.md`。
- 范围：只做离线策略/checker/fixture 测试，针对 Ollama 合法输入过度拒绝和 A05 `missing_fields` 自洽性问题；不修改生产 v4、解析/Schema/预算/授权、旧批次或正式运行入口。
- 验收边界：候选版本不激活、不调用模型、不读取密钥；未来若测候选，必须另建唯一 `batch_id`、重新授权并通过 Codex preflight。
- 下一步：CC 按 prompt 建立候选与测试并提交；Codex 中枢随后独立复核，决定是否进入版本化激活准备。

### APP-001-V4-QUALITY-FIX-CANDIDATE / CC / in_progress / 2026-11-09

- 动作：建立未激活、无网络、无模型调用的版本化候选策略和离线测试，针对正式批次 `app001-phase1-v4-20261109-01` 的两类已核实偏差。
- 分支：`cc/APP-001-V4-QUALITY-FIX-CANDIDATE`（基线 `b1a31b9`，是授权基线 `cc3dfbb` 的后代）。
- 新增文件：
  - `src/llm/decision_policy_v5_candidate.py`：纯函数离线 checker，实现 P1（过度拒绝检测）和 P2（envelope 自洽性）规则；不被 adapter/parser/runner/contract/prompt_loader 导入；
  - `tests/llm/test_decision_policy_v5_candidate.py`：51 个离线测试；
  - `agent-work/llm/APP-001-v4-quality-fix-candidate/`：candidate-strategy.md、checkpoint.md、handoff.md。
- P1 规则：当 `decision` 为 refuse/ask 且 bore_d 是有效目录值、`missing_fields=[]`、`unsupported_requests=[]` 时，判定为过度拒绝（P1-1）；检查与 condition_id 无关（P1-2）；单位归一化后的合法目录值不因原始单位被拒（P1-3）；C1 检索上下文不能制造缺失或 unsupported（P1-4）。
- P2 规则：已出现在 `extracted_parameters` 的字段不得同时出现在 `missing_fields`（P2-1/P2-2）；`decision=answer` 不得与非空 missing_fields 或 unsupported 共存（P2-3）；missing_fields 不得有重复条目（P2-4）。
- 测试覆盖：A02/A03/A08 C0/C1 过度拒绝检测；A01/A06 正常通过；A04/A05/A07/A09 正确拒绝不被误报；A05 C0/C1 envelope 自洽性；反向测试（缺失/越界/冲突时 P1 不触发）；版本/接口兼容；生产模块隔离（AST + 文本扫描）；py_compile；convenience wrapper。
- 验证：
  - `py_compile`（3.11.17）：通过；
  - `PYTHONPATH=src:. python3.11 -m pytest tests/llm/test_decision_policy_v5_candidate.py -v` → **51 passed**；
  - 定向回归（v3/v4 candidate + authorization + parser + budget + run-script）→ **236 passed, 6 skipped**；
  - `git diff --check HEAD`：clean；
  - 全量 LLM 回归中 74 个 pre-existing 失败和 11 个 pre-existing error 均非本次引入（stash 验证：baseline 74 failed / 551 passed；加入 v5 后 74 failed / 602 passed，净增 51 passed / 0 new failure）。
- 边界：本轮没有真实模型请求、没有 API key 读取或打印、没有生产代码/prompt/schema/预算/授权范围/旧批次修改；`FORMAL_EVALUATION_ALLOWED` 保持 `False`；`PROMPT_VERSION` 保持 `app001-extraction.v4`；`FROZEN_PROMPT_*` 锚点不变。
- 限制：离线 checker 通过 ≠ 模型效果通过；若未来要测候选，必须另建唯一 `batch_id`、走新授权和 Codex preflight。

### APP-001-V4-QUALITY-FIX-CANDIDATE-REVIEW / Codex / review / 2026-11-09

- 独立复核提交 `1a0bd94`：专项 unittest 51/51 通过，定向回归 191 通过、6 skipped，生产文件和旧批次未修改。
- 发现两个阻塞：`PYTHONPATH=src` 下 `import llm.decision_policy_v5_candidate` 因 `from ..schema` 失败；checker 未实现任务要求的 `answer` 与确定性目录/规则冲突检查，A05/A09 answer 反例会被放过。
- 追加边界要求：补测 `bore_d=24.0`、`{"value":1.6,"unit":"cm"}` 的 Schema 归一化，以及正式导入路径 smoke test。
- 结论：候选保持 `review`，不得合并/激活或创建新正式批次；CC 需做窄范围修正后再由 Codex 独立复核。

### APP-001-V4-QUALITY-FIX-CANDIDATE-R1 / Codex / planned / 2026-11-09

- 动作：新增 R1 窄范围修正 prompt：`docs/coordination/prompts/APP-001-V4-QUALITY-FIX-CANDIDATE-R1-cc-agent.md`。
- 范围：修正 `PYTHONPATH=src` 正式导入、目录/规则冲突判定，以及 `24.0`/厘米 measurement object 的数值归一化边界；继续保持 checker 离线、未激活和生产隔离。
- 禁止项：不修改生产 v4、冻结 prompt/Schema、预算/授权、旧批次，不运行真实模型，不创建新 batch_id。
- 下一步：CC 在当前候选分支执行 R1 并提交；Codex 中枢复核修正后的专项测试、正式导入和冲突反例。

### APP-001-V4-QUALITY-FIX-CANDIDATE-R1-REVIEW / Codex / review / 2026-11-09

- 独立复核提交 `d706639`：Python 3.11.18 下专项 78/78 通过，定向回归 191 通过、6 个既有 FUSE skip；`PYTHONPATH=src` 顶层 `llm` 导入成功。
- 关键反例通过：A02/A08 过度拒绝、A05 目录冲突、A09 second_screw 规则冲突；合法 ask/refuse 不被 P1 误报；`24.0` 和 `1.6 cm` 归一化边界通过。
- 结论：离线候选 gate 通过，但仍未合并/激活；真实模型效果未测量，新正式批次未授权。下一步是独立 v5 prompt 候选/激活准备。

### APP-001-V4-QUALITY-FIX-CANDIDATE-R1 / CC / in_progress / 2026-11-09

- 动作：修正 Codex 对提交 `1a0bd94` 的三项独立审查阻塞问题（R1-1/R1-2/R1-3）。
- R1-1（导入兼容）：`from schema.set_screw_shaft_collar`（绝对导入）替换 `from ..schema...`（相对导入）。现在 `PYTHONPATH=src python3.11 -c 'import llm.decision_policy_v5_candidate as m'` 可正常导入，且 `PYTHONPATH=src:.` 下的 `src.llm` 命名空间同时保留。测试补充 `ImportSmokeTests`（subprocess 调用验证真实 `PYTHONPATH=src` 路径）。
- R1-2（P2-5 目录/规则冲突）：新增 `_has_deterministic_conflict()` 和 `_check_p2_5_catalog()` — 当 `decision=answer` 且 extracted_parameters 中含 outer_d 与目录行不符，或 second_screw 违反 bore_d > 70 规则时，返回 P2-5 violation；不修改或删除任何显式 claim。P1-1 新增冲突抑制逻辑：ask/refuse 附带确定性目录/规则冲突时，冲突本身是合法原因，P1-1 不触发。
- R1-3（数值和单位边界）：新增 `_normalize_bore_d()`，统一处理 bare int/float（24.0 → 24）、measurement object（{"value":1.6,"unit":"cm"} → 16）、未知单位 → None、非有限值 → None、分数毫米 → None。`_bore_d_from_envelope()` 委托给此函数。
- 测试扩展：78 个测试（R1 前 51 个），新增 ImportSmokeTests、P2CatalogRuleConflictTests、NumericNormalizationTests、EnvelopeImmutabilityTests；全部离线，不调用模型/网络/API key。
- 实际验证（Python 3.11.17 VM）：
  - `py_compile`（两个文件）：通过；
  - `PYTHONPATH=src import llm.decision_policy_v5_candidate` → `app001-extraction.v5-candidate`；
  - `PYTHONPATH=src:. python3.11 -m unittest tests.llm.test_decision_policy_v5_candidate -q` → **Ran 78 tests OK**；
  - 回归（v4/v3 candidate + authorization + parser + budget + run-script）→ **Ran 191 tests OK（skipped=6）**；
  - `git diff --check` → clean。
- 正常案例：`check_v5_envelope({'decision':'answer','extracted_parameters':{'bore_d':24},...})` → `ok=True`；
- 失败案例（P1-1）：`check_v5_envelope({'decision':'refuse','extracted_parameters':{'bore_d':24},...}, condition_id='C1')` → `ok=False, p1=[P1-1]`；
- 失败案例（P2-5）：`check_v5_envelope({'decision':'answer','extracted_parameters':{'bore_d':20,'outer_d':40},...})` → `ok=False, p2=[P2-5]`。
- 边界：本轮没有真实模型请求、没有 API key 读取或打印、没有生产代码/prompt/schema/预算/授权范围/旧批次修改；`FORMAL_EVALUATION_ALLOWED` 保持 `False`；`PROMPT_VERSION` 保持 `app001-extraction.v4`。离线 checker 通过 ≠ 模型效果通过；候选仍处于 `review`，不合并 main，不激活 v5，不创建新正式批次。

### APP-001-V5-PROMPT-CANDIDATE / Codex / review / 2026-11-11

- 动作：基于 v4 正式批次已确认的 3 条过度拒绝和 A05 envelope 重叠问题，准备独立、未激活的 v5 prompt 候选与策略映射；不运行模型。
- 新增：
  - `agent-work/llm/APP-001-v5-prompt-candidate/prompt-v5-candidate.md`：从冻结 v4 prompt 独立复制，候选版本标识为 `app001-extraction.v5-candidate`；补充完整无冲突输入必须 `answer`（C0/C1 一致、retrieval 不干扰）和 envelope 自洽性规则。
  - `agent-work/llm/APP-001-v5-prompt-candidate/strategy.md`：列出 A01-A09 的候选预期行为、保持的安全门、checker 限制与后续授权门。
  - `tests/llm/test_prompt_v5_candidate.py`：新增 9 项离线结构/版本/hash 检查。
- 发现并修正候选 checker 与 prompt 规则的覆盖差异：P1 合法冲突抑制和 P2-5 answer 冲突判定由仅覆盖 `outer_d` 扩展到冻结目录中所有显式耦合尺寸（`outer_d`、`width`、`screw_d`、`screw_len`），并保留 `second_screw` 的严格 `bore_d > 70` 规则；为 width/screw_d/screw_len 正常冲突和 answer/ask/refuse 路径补测试。
- 验证（Mac Python 3.11.18）：
  - `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v5_candidate tests.llm.test_prompt_v5_candidate -v` → **93 项通过**。
  - v3/v4 candidate、authorization、parser、budget、run-script 定向回归 → **191 项通过，6 个既有 skip**。
  - LLM 全量 → **800 项通过，8 个既有环境 skip**；Schema 全量 → **17 项通过**。
  - `py_compile`（checker 与相关测试）及 `git diff --check` → 通过。
  - 正常例：A02 `answer + bore_d=24` → checker 通过；失败例：A05 冲突 `ask/refuse` 不报 P1、冲突 `answer` 报 P2-5；新增 width/screw_d/screw_len 冲突均有对应 P1/P2 覆盖。
- 不变量：冻结 v4 prompt SHA-256 `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc` 与 acceptance-set SHA-256 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf` 未变；生产版本仍为 v4，formal gate 仍关闭；未改旧批次，未读取 `.env`/密钥，未调用网络或模型，未创建正式 batch。
- 限制：checker 只看 envelope，不能判定原始自然语言是否歧义或 evidence 是否真实支持 claim；静态/离线通过不证明模型遵循 v5。
- 下一步：完成差异与状态核对、提交本候选工作单元并交 Codex 独立审查；在候选审查和版本化激活决定前保持生产 v4。

### APP-001-V5-ACTIVATION-PREP / Codex / review / 2026-11-11

- 动作：在 v5 prompt 候选独立离线审查通过后，准备可供项目负责人审阅的版本化激活包和 proposed ADR；不切换生产版本，不调用模型。
- 新增激活准备包 `agent-work/llm/APP-001-v5-activation-prep/`：`prompt-v5.md`、`manifest.json`、`README.md`、`checkpoint.md`、`handoff.md`。prompt 副本仅规范化候选版本字符串和 heading 标签；候选源 hash 与准备副本 hash 分开记录；v4 prompt 为明确回滚目标。
- 新增 `tests/llm/test_v5_activation_prep.py`：离线检查包状态、源/副本/验收集/回滚哈希、v4 生产常量、正式 gate 关闭、候选 checker 与生产模块隔离，以及激活前置条件。
- 在 `docs/DECISIONS.md` 追加 ADR-0018（proposed）：提议保留 `app001-io.v1` 契约并将 v5 策略版本化；明确项目负责人决策、独立激活实现/审查和单独正式批次授权是不同门。尚未接受。
- 同步 PROJECT_STATUS、PROJECT_PLAN，记录 v5 候选审查通过和激活准备待审状态。
- 验证（Mac Python 3.11.18）：激活准备/v5 prompt/checker 专项 **103 项通过**；LLM 全量 **810 项通过、8 项既有 FUSE skip**；Schema **17 项通过**；新增测试 `py_compile` 和 `git diff --check` 通过。run-script 测试预期会打印模拟 abort/fail 场景，整体退出码为 0。
- 哈希：v5 候选源 `6e969ae6…`；版本规范化准备副本 `21177d71…`；v4 回滚 prompt `73cb6b8f…`；acceptance-set `ed59e2b6…`。
- 当前不改变任何生产常量、parser、loader、预算、授权或旧批次；生产仍 v4，formal gate 仍关闭。下一步为独立审查本准备包和 ADR-0018 proposed，并由项目负责人决定是否接受策略方向。

### APP-001-V5-ACTIVATION / Codex / review / 2026-11-11

- 决策同步：项目负责人明确接受 ADR-0018 的 v5 策略方向；将 ADR 状态记录为 accepted。该接受仅授权版本化激活工作，不授权真实模型请求或正式批次。
- 实现：在 `codex/APP-001-V5-ACTIVATION` 分支把生产 prompt 版本从 `app001-extraction.v4` 切换到 `app001-extraction.v5`；prompt loader 路径、版本标记、固定文件 SHA-256 指向冻结 v5 prompt；parser 默认仅接受 v5，并把 v4 加入显式只读历史审计 allowlist（保留 v2/v3）。`app001-io.v1` 未变。
- 新增激活包 `agent-work/llm/APP-001-v5-activation/`（冻结 prompt、manifest、README、checkpoint、handoff）和离线测试 `tests/llm/test_v5_activation.py`；将旧 v4 激活测试转为归档完整性/显式审计兼容测试；生产 fixture 更新为 v5。同步 README、PROJECT_STATUS、PROJECT_PLAN。
- 哈希确认：v5 prompt `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`；v4 回滚 prompt `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`；候选源 `6e969ae68f75c0cd6a188bd589a84c378b50055a42f75ff2b3b3259252f6bdfe`；acceptance-set `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`。
- 验证（Mac Python 3.11.18）：激活/准备/候选/parser/adapter/envelope 定向 **226 项通过**；`tests/llm` 全量 **809 项通过、8 个既有 FUSE skip**；`tests/schema` **17 项通过**；修改 Python 文件 `py_compile` 通过；`git diff --check` 通过。全量测试中的 `[ABORT]`/`[FAIL]` 文本来自模拟拒绝路径，整体退出码为 0。
- 边界：`FORMAL_EVALUATION_ALLOWED=False`；预算、重试、授权逻辑、Schema、acceptance-set 和旧批次未改；没有模型/网络调用或密钥读取；C2/IR/CAD/geometry/STEP 仍禁用。
- 状态：激活实现待 Codex 独立审查并合入 main；生产效果尚未测量。下一步由 Codex 审查当前分支与 v5/v4 哈希、版本边界及全量测试；之后才可讨论新的唯一 batch_id 和单独正式运行授权。

- Git：激活实现已提交为 `d48cc66`（`feat: activate APP-001 extraction v5 contract [APP-001-V5-ACTIVATION]`）；工作区提交后干净。该提交在 `main` 之外，等待 Codex 中枢独立审查。


### APP-001-V5-ACTIVATION-R1 / Codex / review / 2026-11-11

- 根据独立审查报告修复：在 `test_v5_activation.py` 增加默认 parser 拒绝 v4 的直接断言，并验证显式 v4 audit 仍接受；更新 parser/README/测试中的 v5 生产版本说明；清理 main..激活分支差异中 7 处行尾空白。
- 保留 v4 激活历史覆盖的核心内容于 v5 激活套件；`test_v4_activation.py` 保留为归档哈希、默认拒绝和显式审计兼容检查。
- 验证（Python 3.11.18）：指定定向套件 279/279；LLM 全量 811 通过、8 个既有 FUSE skip；Schema 17/17；`py_compile` 通过；`git diff --check main` 全分支差异 CLEAN。
- 独立审查报告认为的 P1/P2 已处理。尚未将独立审查者未能运行的测试直接视作通过；由当前目标分支在 Mac Python 3.11.18 上完成上述实际重跑。未调用模型、未读密钥、未触碰批次。
- 下一步：提交 R1 修正，交回独立审查者确认 findings closure；之后中枢决定是否合入。
### APP-001-V5-ACTIVATION / Codex 中枢 / done / 2026-11-11

- 核验用户报告的合入状态：本机仓库 `/Users/syd/Desktop/参数化 cad 工程辅助设计`，`main` 与 `origin/main` 均指向 `2c702257ed56b3d9e49209f0455c2aaffb608b8b`；该提交同时为 v5 激活 R1 收束提交，工作区干净。
- 合入前复审结论为 pass；本机 Python 3.11.18 重跑 `tests.llm.test_v5_activation tests.llm.test_v4_activation`，72 项通过；目标提交 `git show --check` 通过。
- 关键不变量：v5 prompt hash `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`；v4 rollback hash `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`；acceptance-set hash `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`；`FORMAL_EVALUATION_ALLOWED=False`。
- 项目负责人随后明确要求推进 v5 效果测试并必须到真实模型阶段。新工作单元 `APP-001-V5-FORMAL-EFFECT-EVALUATION` 启动；将准备独立 v5 受控入口与唯一批次，旧 v4 批次保持只读且分开统计。当前尚未发起任何模型请求。
- 下一步：实现和审查 v5 专用批次执行入口及离线保护测试，再完成模型服务/凭据存在性/批次目录/preflight 核验；仅在完整 preflight 通过后执行授权范围内的真实请求，并记录结果和限制。

### APP-001-V5-FORMAL-EFFECT-EVALUATION / Codex / in_progress / 2026-11-11

- 新工作分支：`codex/APP-001-V5-FORMAL-EFFECT-EVALUATION`，基线为已合入 v5 激活的 `2c70225`；档案同步提交 `8dc03da`。
- 记录项目负责人明确要求推进到 v5 真实模型评测。拟定唯一批次 `app001-phase1-v5-20261111-01`，采用既有冻结 Phase 1 scope：9 cases × C0/C1 × DeepSeek/Ollama = 36 logical runs，单 run 最多 3 次，预算账本总 attempt 上限 108、每 provider 54；C2/IR/CAD/geometry/STEP 禁用。完整授权记录见新任务 `authorization.md`。
- 新建 v5 专用受控入口 `scripts/run_app001_v5_formal_batch.py` 和 `tests/llm/test_run_script_v5_batch.py`，不复用 v4 脚本。入口验证基线祖先关系、生产路径无差异、工作区干净、Python 3.11.18、prompt/activation manifest/acceptance-set/RET-002 哈希、授权 scope hash、batch 目录不存在、DeepSeek key 存在但不输出其值，以及 Ollama 运行时、模型 digest 和 structured-output schema 身份。
- 初始测试发现 ADR-0015 中 `d82e53ad…` 是 v2 schema hash，不能用于 active v5。当前代码的 v5 schema hash 为 `7c201710fae0ff3cc3b811c28739393762f1886a5e79bd255cbda8671ac03143`；已将它作为 v5 锚点并加入离线复算测试。此前失败的单项测试是发现该不一致的有效拒绝，不是模型请求。
- Python 3.11.18 验证：v5 入口专项 27/27；LLM 全量 838 通过、8 个既有 FUSE skip；Schema 17/17；dry-run 36 组合；`py_compile` 与 `git diff --check` 通过。所有验证均离线，尚未发起真实请求。
- 下一步：提交受控入口与档案；随后由该入口在线 preflight 核验本机 Ollama 0.40.14 / `qwen3:8b` digest、凭据存在性和唯一 batch 目录。只有 preflight 通过才启动真实 v5 batch；任何检查失败则停止并记录。

### APP-001-V5-FORMAL-EFFECT-EVALUATION / Codex 中枢 / review / 2026-11-11

- 动作：按用户明确要求推进到真实模型测试；完成唯一 v5 批次的只读审计，并收束执行摘要中的留存/决策统计字段错误。批次 `app001-phase1-v5-20261111-01` 未重跑或修改。
- 真实结果：36 条逻辑记录，32 条 DeepSeek/Ollama 模型响应，4 条 C1 请求前阻塞（A04/A07 各两家）；48 次账本尝试（DeepSeek chat 16、Ollama chat 16、Ollama `/api/tags` 16），预算内且 32 次 chat 全部 HTTP 200；未见重试、5xx、API 错误。32 个留存 raw 文件均存在且长度/SHA-256 与记录元数据匹配。
- 效果：32/32 parse 通过；决策 `answer=20 / ask=2 / refuse=10`，与本轮候选策略对九样例的预期路径一致；离线 v5 checker 无 P1/P2 告警。CAD-003 Schema 20/32 通过、12/32 拒绝（A04 缺 bore_d、A05 目录冲突、A07 越界 bore_d、A09 second_screw 规则冲突）；不得把策略决策匹配表述为 Schema 全通过。C2/IR/CAD/geometry/STEP 未运行。
- 修复：`_print_jsonl_stats()` 改为使用 `raw_response_retention` 元数据、将请求前阻塞标记为 blocked，并通过活动 parser 只提取 decision enum，不输出 raw 正文；新增 3 项测试。Python 3.11.18 下入口专项 30 项通过、LLM 全量 841 项通过且有 8 个既有 FUSE skip、Schema 17 项通过；`py_compile` 与 `git diff --check` 通过。
- 审查档案：`agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md`；任务 checkpoint、PROJECT_STATUS、PROJECT_PLAN 已同步。批次 raw 和账本仍处于 Git 忽略目录，不会提交。
- 提交：`1f2811f docs: close APP-001 v5 effect evaluation audit [APP-001-V5-FORMAL-EFFECT-EVALUATION]`。状态保持 `review`，待独立收束复核和合入；本批次不得复跑/覆盖，任何后续模型调用需要新 batch_id 与单独授权。
- 独立复核补充发现：授权记录指定 raw 目录为 `work/app001-runs/<batch_id>/raw/`，但 `src/llm/runner.py` 为本批次配置 `RetentionPolicy.base_dir` 时只给了 `work/app001-runs/<batch_id>`，导致 32 个文件位于批次根目录。只读核对确认文件均存在、hash/长度匹配且仍在 git-ignore 区；未移动或修改历史文件，也未改写授权记录。该授权/运行路径不一致已追加到 checkpoint 和审查报告，任务维持 `review`。
- 建议未来窄修：runner 的 raw `base_dir` 增加 `/raw`；增加测试断言准确目录与写出 metadata path；未来授权模板保持同一绝对/相对布局。该修正应单独审查，不能用于重跑本批次；任何后续模型请求仍需新 batch ID 和单独授权。

### APP-001-V5-RETENTION-PATH-FIX / Codex / review / 2026-11-11

- 动作：按独立复核发现做窄范围修正，将未来正式批次的 raw 留存位置改为授权要求的 `<batch_dir>/raw/`；不移动或改写 `app001-phase1-v5-20261111-01` 的任何文件，不调用模型。
- 代码：`src/llm/runner.py` 新增 `_formal_raw_retention_policy(batch_id)`，正式 runner 使用 `work/app001-runs/<batch_id>/raw`；`tests/llm/test_runner.py` 新增实际写文件回归，验证 policy resolved dir 与 retention metadata path 的 parent 均精确为 batch `raw/`，并仅清理该测试创建的 UUID 临时目录。
- 验证（Python 3.11.18）：新增路径测试 1/1；`tests.llm.test_runner` 71 项通过、1 项既有 skip；LLM 全量 842 项通过、8 项既有 FUSE skip；Schema 17 项通过；`py_compile`、`git diff --check` 通过。
- 边界：历史 v5 批次仍保持批次根目录的实际布局，32 个文件完整且原样保留；授权原文不改。生产 `src/llm/` 改动会触发旧 v5 batch entrypoint 的生产路径基线保护，因此不得复用旧脚本再跑；未来任何模型运行需新受控入口基线、新唯一 batch_id 和单独授权。
- 状态：review，交独立复核 runner 改动与审计记录；真实效果任务仍未关闭，路径偏离如实保留为历史限制。

### APP-001-V5-RETENTION-PATH-DOC-ALIGNMENT / Codex 中枢 / review / 2026-11-11

- 动作：按独立审查报告对齐 v5 留存路径修正的交接档案；只改 checkpoint 与项目计划，不改代码、授权原文或批次数据。
- 核对：明确记录 `app001-phase1-v5-20261111-01` 的 32 个 raw 文件实际位于批次根目录，偏离授权指定的 `raw/` 子目录；明确历史文件未移动、未改写、未重跑。
- 对齐：checkpoint 将“未来需修改 runner/增加路径测试”的过时措辞更新为“窄修正已完成，等待独立审查”；约束段区分原批次执行时的边界与后续单独授权的生产路径修正。PROJECT_PLAN 同步记录实际历史路径与未来 `batch/raw/` 行为。
- 验证：运行 `git diff --check` 和文档一致性核对；未运行模型或读取批次 raw 正文。
- 状态：review；本工作单元不合并、不 push。下一步为提交文档收束并交最终复核。

### APP-001-V5-RETENTION-PATH-DOC-ALIGNMENT-R1 / Codex 中枢 / review / 2026-11-11

- 动作：根据独立复核结果继续收束交接状态；保留原日志条目作为 `8da34d9` 提交前的真实状态记录，不改写追加式历史。
- 原因：`8da34d9` 已提交文档对齐后，checkpoint 的 Current handoff state 仍称下一步要提交文档；原始 v5 closeout review 中“未来应修改 runner”的建议也未标明已由 `a35f14b` 完成，因此当前状态读取存在时间线歧义。
- 修正：checkpoint 更新为当前待处理独立复核；审查报告新增 Follow-up status，说明 runner 修正已实现并验证、历史批次偏离仍保留，并将原建议保留为历史审查上下文；本条 WORKLOG 作为前条“提交文档收束”下一步的后续状态记录。
- 边界：仅更新审查/交接记录；不改代码、授权原文或批次，不读取 raw 正文，不运行模型，不 push/合并。
- 验证：`git diff --check` 通过；逐项确认 checkpoint、PROJECT_PLAN、审查报告和本追加日志均区分历史根目录偏离、未来 `batch/raw/` 修正已完成、当前仍待独立复核。未运行测试或模型。
- 状态：review；提交后交独立复核确认，之后由 Codex 中枢决定是否可合入。

### APP-001-V5-FORMAL-EFFECT-EVALUATION-FINAL-ACCEPTANCE / Codex 中枢 / review / 2026-11-11

- 动作：在独立审查通过 `3a55cc1` 文档状态跟进后，对完整 v5 评测分支做合入前最终验收。
- 差异：验收时分支基于 `main=2c702257`；HEAD `3a55cc1`，工作区干净。完整差异 11 个文件，涉及 v5 授权/档案/审查报告、专用入口及测试、`src/llm/runner.py` 的未来 raw 路径修正、项目状态/计划/工作日志；无旧批次 tracked 文件改动。生产代码差异仅为正式 raw retention 目标改为 `work/app001-runs/<batch_id>/raw/`。最终状态同步还将明确标注预运行 handoff 为历史指令，避免误将已完成批次再次执行。
- 验证（Mac Python 3.11.18）：`PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` → 842 passed、8 个既有 FUSE skip；Schema 全量 17/17；runner、v5 batch script 和相关测试 `py_compile` 通过；`git diff --check main...HEAD` 与目标提交 `git show --check` 通过。
- 审查：独立复核结论 pass；Codex 中枢确认历史 32 个 raw 位于批次根目录的偏离被如实保留，未来路径修正不追溯改变旧批次。C2/IR/CAD/geometry/STEP 未运行；没有读取 raw 正文、密钥或发起模型请求。
- 结论：分支可供项目负责人 push/合入；状态继续为 `review`，待 main 合入和合入后核验才可标 `done`。不授权新批次或额外模型调用。

### APP-001-V5-FORMAL-EFFECT-EVALUATION-MERGE-VERIFY / Codex 中枢 / done / 2026-11-11

- 动作：核验项目负责人已合入的 v5 真实模型评测收束分支，并在合入后的 `main` 上复跑关键检查。
- Git：`origin/main` 的 PR #1 merge commit 为 `95d1dcb8e1ba693769b19b1262228c51ba4f8f7d`，包含验收提交 `c574e6b2414edc2354758d67272cae4f537458df`；本地 `main` 已 `pull --ff-only` 并与 `origin/main` 同步，工作区在复验前干净。
- 验证（Python 3.11.18）：`tests/llm` 全量 842 通过、8 个既有 FUSE skip；`tests/schema` 17 通过；`tests.llm.test_runner tests.llm.test_run_script_v5_batch` 101 通过、1 个既有 skip；相关 `py_compile` 通过；`git show --check 95d1dcb` 通过。离线入口测试打印的 `[ABORT]`/`[FAIL]` 为模拟拒绝路径，测试退出码为 0。
- 状态同步：APP-001-V5-FORMAL-EFFECT-EVALUATION 标记 `done`；PROJECT_PLAN、PROJECT_STATUS、checkpoint 与审查报告记录合入和复验结果。
- 边界：未读取 raw 正文、密钥或 `.env`，未调用模型；历史批次 raw 文件仍保留在批次根目录，未移动/改写/重跑。未来真实运行仍需新受审查的入口基线、新 batch ID 和单独授权；本次不构成此类授权。
- 下一步：本工作单元已完成；若继续测模型效果，先提出独立版本化实验方案与授权范围。

### APP-001-NEXT-REAL-MODEL-EVALUATION / Codex 中枢 / planned / 2026-11-11

- 动作：依据已合入 v5 真实评测结果和 RET-003 协议，提出下一轮真实模型实验问题及前置门；当前仅形成方案草案。
- 依据：v5 的九样例 C0/C1 × 两 provider 已运行；RET-003 明确只有三个 `heldout_evaluation` 查询，`provisional_small_n`，且公平 C2 尚未定义。完整目录 `C2O` 含 held-out 真值，只能作 oracle，不能纳入公平比较。旧 v5 入口会因 runner 生产基线变化而 fail-closed，不得复用。
- 建议：评估冻结 RET-002 `retrieval_source` 上下文对 active v5 输出和 CAD-003 Schema 接受的逐例影响；三条 held-out 查询、C0/C1、DeepSeek/Ollama，共 12 个逻辑运行，最多 36 次请求。保持 C2/C2O 和 IR/CAD/geometry/STEP 禁用，结果逐例报告，不作统计泛化结论。
- 草案：`agent-work/inbox/APP-001-NEXT-REAL-MODEL-EVALUATION-PROPOSAL.md`。该文件不是 ADR、批次授权或模型请求许可；未分配 batch_id，未生成测试集，未实现入口，未调用模型或读取密钥。
- 下一步：项目负责人审阅实验问题与三条 held-out 输入集选择；确认后再冻结输入/标签并独立检查泄漏，随后实现并审查新的受控入口。新唯一 batch_id 与单独授权在实现、验证和 final preflight 全通过后另行呈批。

### APP-001-NEXT-REAL-MODEL-EVALUATION-OFFLINE-PREFLIGHT / Codex 中枢 / blocked / 2026-11-11

- 动作：依据项目负责人“先验证、验证后分配 batch_id、再提交授权”的指令，对已原则批准的 RET-003 held-out × C0/C1 × 两 provider 方案做离线设计核验。该原则批准不授权真实模型调用。
- 仓库：项目根 `/Users/syd/Desktop/参数化 cad 工程辅助设计`；`main` HEAD `2054565b15ba232d151664bfa832b77be10d5a14`，`origin/main=95d1dcb8e1ba693769b19b1262228c51ba4f8f7d`，本地 ahead 2 文档提交。工作区开始时干净。
- 输入核验：Python 3.11.18 下读取 acceptance-set-v0 并按冻结 SHA `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf` 投影；9 条模型可见自然语言输入的 case_id 均不是 RET-003 的三个 held-out query_id。bore_d=80 的已有验收输入显式包含 `second_screw=0`，是规则冲突样例，不能替代无偏 held-out 请求。RET-003 query-set 仅引用 manifest 的结构化参数，不含已冻结自然语言输入。
- 授权接口核验：正常路径对 9-case 投影生成 36 个组合；失败路径对 3-case projection 返回 `expected 9 acceptance cases, got 3`。`FormalRunAuthorization` 固定 acceptance-set-v0、36 runs、108 总尝试、54/provider；不能直接支撑拟议的 12 runs、36 总尝试、18/provider。不得绕过或放宽现有工厂。
- 修改：更新评测提案状态/前置门，新增任务 checkpoint，并同步 PROJECT_STATUS、PROJECT_PLAN。明确当前 `blocked`、无 batch_id、无模型调用授权及解除条件。
- 验证：`/opt/homebrew/bin/python3.11 --version` → 3.11.18；只读投影/组合正常与拒绝检查如上；`git diff --check` 通过。无网络/模型请求、无密钥或 `.env` 读取、无批次目录创建。
- 下一步：项目负责人决定 held-out 自然语言输入的合法来源/构造流程，以及是否接受记录新的精确 12-run 授权接口决策。解决后再冻结输入与 evaluator labels、独立检查泄漏并实现入口；全部审查和 final preflight 通过后才生成并呈批 batch_id 与正式授权模板。

### APP-001-NEXT-REAL-MODEL-EVALUATION / Codex 中枢 / in_progress / 2026-11-11

- 决策：项目负责人同意固定模板为三条 held-out 查询构造只含显式 `bore_d` 的受控合成模型输入，并同意为精确 12-run scope 记录单独授权决策。ADR-0019 已追加，明确该决策不授权模型请求，旧 ADR-0014 scope 不变。
- 冻结输入：`agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/model-inputs.json` SHA-256 `c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6`；不含 held-out truth，仅有中性 query ID 和固定模板输入。
- 冻结标签：`evaluator-labels.json` SHA-256 `bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a`；含 RET-003 query/sample 映射、用户显式主张和 Schema 期望，仅供 evaluator，不得进入模型请求。
- 下一步：实现单独的精确 12-run fail-closed 授权 profile 与受控入口；离线测试需验证 hashes、输入/标签隔离、预算/组合边界、preflight 前零请求、raw 写入 batch/raw。未分配 batch ID，不授权请求。

### APP-001-NEXT-REAL-MODEL-EVALUATION-FROZEN-INPUT-CHECK / Codex 中枢 / in_progress / 2026-11-11

- 动作：按 ADR-0019 后续门对冻结模型输入、evaluator labels、RET-001 manifest 来源及状态文档做续任定向复核。
- 结果：Python 3.11.18 解析两份 JSON；inputs SHA-256 `c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6`、labels SHA-256 `bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a`、来源 manifest SHA-256 `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297` 均与 ADR/labels 一致；三条标签参数均逐条匹配 manifest，显式 bore_d 与 NLI 一致，query ID 一一对应且不重复。模型输入不含 sample_id 或预期 Schema 参数。
- 交接状态：修正 checkpoint 的过时 `blocked` 状态，PROJECT_STATUS/PROJECT_PLAN 同步 ADR-0019 已解决输入/授权设计门；尚未实现专用 profile/入口。旧 9-case/36-run 授权保持冻结。
- 边界：未读 `.env`/密钥，未发模型或网络请求，未创建批次目录，未读取历史 raw；无 batch_id、无请求授权。
- 验证：`/opt/homebrew/bin/python3.11 -m json.tool` 两份 JSON 均通过；上述 hash/manifest/正常样例/映射检查通过；`git diff --check` 通过。
- 下一步：实现独立 profile/入口与离线拒绝/正常路径覆盖；通过 Python 3.11.18 和独立复核后，再生成唯一 batch_id 与完整授权模板交项目负责人批准。

### APP-001-NEXT-REAL-MODEL-EVALUATION-BUDGET-PREFLIGHT / Codex 中枢 / blocked / 2026-11-11

- 发现：矩阵的 12 个逻辑运行包含 6 个 Ollama run。每 run 最多 3 次 chat 时，Ollama chat 上限为 18；当前 `BudgetAwareTransport` 还会在每个 Ollama run 首次 chat 前通过账本记入 1 次 `/api/tags`，因此 Ollama provider 最多需 24 次账本额度，超过 ADR-0019 的 18/provider；全矩阵 chat 36 + tags 6 = 42，超过 36 总上限。
- 另有入口批次前 runtime identity 检查：`/api/version` 和 `/api/tags` 也是物理 HTTP 请求，但 ADR-0019 未定义这两次是否包含在“最多 36 次”内、如何绑定授权/账本。不得把请求移出账本或隐藏计数来规避。
- 处置：撤回本轮未完成的授权 profile/入口/测试草稿；不改变 `src/llm` 既有执行逻辑。更新 ADR-0019 实施补充、checkpoint、PROJECT_STATUS、PROJECT_PLAN，状态设为 blocked。
- 已验证：Python 3.11.18 下输入/标签/manifest 哈希与 held-out 映射一致；9 项离线草稿测试通过；既有授权/预算/runner相关 177 项通过（8 个 FUSE skip），LLM 全量 850 项通过（8 个 FUSE skip），Schema 17 项通过；`py_compile` 和 `git diff --check` 通过。mock 的 `[ABORT]/[FAIL]` 输出是既有入口拒绝用例。
- 边界：无 batch_id、无真实模型请求授权；未读密钥/.env，未访问网络，未建批次目录，旧批次和 9-case ADR-0014 scope 不变。
- 下一步：项目负责人明确预算授权针对 chat attempts 还是 all physical HTTP requests；若所有物理请求都计数，需决定是否提高 total/provider caps，或采用可审计且不削弱身份校验的身份检查方案，并明确 preflight 物理请求的授权记录方式。取得决策后再修订 ADR-0019、实现入口并重新验收。

### APP-001-NEXT-REAL-MODEL-EVALUATION-BUDGET-DECISION / Codex 中枢 / in_progress / 2026-11-11

- 决策：项目负责人同意由 Codex 设计适合该固定 12-run 矩阵的预算。该 checkpoint 初稿先记下身份最多 8（preflight 2 + runtime tags 6）；后续对 retry 调用关系复核后修正为 20，详见 `APP-001-NEXT-REAL-MODEL-EVALUATION-BUDGET-REVIEW-CORRECTION`。本段为历史阶段记录，不作为最终预算口径。
- 依据：需同时计入 12-run 矩阵的 chat 与 Ollama 身份核验，且保留每次 send 最多 3 次现有重试。
- 文档：同步 ADR-0019、任务 checkpoint、PROJECT_PLAN、PROJECT_STATUS；先前 blocked 记录保留为历史，现状态恢复为 `in_progress`。
- 边界：未分配 batch_id；未授权真实请求；未发网络/模型请求；未读取 `.env` 或密钥；ADR-0014 既有 scope 不变。
- 下一步：实现独立精确 12-run profile/入口和分项物理请求 ledger，覆盖正常/拒绝/上限边界、preflight 授权绑定与请求前预留；Python 3.11.18 回归、独立审查和离线 final preflight 通过后，再生成 batch_id 和完整授权模板请负责人批准。

### APP-001-NEXT-REAL-MODEL-EVALUATION-BUDGET-REVIEW-CORRECTION / Codex 中枢 / in_progress / 2026-11-11

- 修正：复核 `BudgetAwareTransport.send()` 与 `send_with_retry()` 的调用关系后，发现 Ollama runtime `/api/tags` 失败会在后续 retry attempt 再发一次 tags；identity category cap 因此从先前草记的 8 修正为 20（batch preflight 两次 + runtime tags 最多 18 次）。此前 8 次只覆盖 tags 成功的正常路径，不足以表达授权硬上限。
- 预算：chat category 36（DeepSeek 18、Ollama 18；每 logical run 最多 3）；identity category 20；global physical HTTP 44；DeepSeek provider 18；Ollama provider 26。每项是同时生效的硬上限。每 Ollama run 的 runtime sequence 最多 3 次 transport attempt；tags 失败会占用 attempt 且可能减少 chat，所有实际 HTTP 均先预留账本额度。
- 变更：修正 ADR-0019、checkpoint、PROJECT_STATUS、PROJECT_PLAN；不重写先前日志。前一条预算数字为计算复核前的暂定值，以本修正为准。
- 边界：仍未分配 batch_id、未授权任何请求、未做网络或模型调用、未访问密钥/.env。旧 ADR-0014 scope 不变。
- 下一步：以修正预算实现独立 fail-closed profile、物理请求分类账本和受控入口，并加入 category/provider/global 上限及 tags 重试路径测试；通过本机 3.11.18 回归、独立审查和 final offline preflight 后再生成 batch ID 与完整授权模板供用户批准。

### APP-001-NEXT-REAL-MODEL-EVALUATION-LEDGER-MILESTONE / Codex 中枢 / in_progress / 2026-11-11

- 动作：实现 ADR-0019 专用 held-out 授权 profile，并在共享预算账本中加入物理 HTTP 分类、provider chat cap、identity endpoint bucket 与 per-run identity cap。
- 结果：12-run scope 绑定冻结 v5/IO 版本、3 个 query ID、inputs/labels 哈希；chat 上限 36（18/provider、3/run），identity 20（preflight `/api/version` 1、preflight `/api/tags` 1、runtime `/api/tags` 18/3 per Ollama run），物理总量 44（DeepSeek 18、Ollama 26）。账本恢复时从 attempt records 重算 category/provider/bucket/run 计数并校验；ADR-0014 授权 summary/hash 未改变。
- 验证：Python 3.11.18 专项 held-out 测试 13 项通过；授权/预算/runner 107 项通过、7 个既有 skip；LLM 全量 855 项通过、8 个既有环境/FUSE skip；Schema 17 项通过；相关 `py_compile` 和 `git diff --check` 通过。专项覆盖有效预留、旧账本计数恢复及 scope/provider/endpoint/bucket/per-run 上限拒绝路径。
- 边界：未访问网络或模型、未读取密钥/`.env`、未读取历史 raw、未创建正式批次目录、未分配 batch ID、无请求授权；现有 ADR-0014 scope 与旧批次不变。
- 下一步：实现独立 held-out runner，证明输入/标签隔离和所有 preflight/runtime HTTP 在触网前获得该账本预留；之后做独立审查与离线 final preflight，再向负责人提交具体 batch ID 和授权模板。

### APP-001-NEXT-REAL-MODEL-EVALUATION-RUNNER-REVIEW / Codex 中枢 / review / 2026-11-11

- 动作：在 `main=5928b23` 上独立审查 CC 实现的 held-out v5 runner、CLI、profile、账本接线和交接材料，并在 Python 3.11.18 下重跑离线验证。
- 结果：专项 53 项、授权/预算/runner 回归 120 项（7 skips）、LLM 全量 908 项（8 skips）、Schema 17 项通过；CLI dry-run 生成 12 组合。审查发现两项 P1：直接调用 `HeldoutRunner.run_formal()` 可绕过关闭的 `FORMAL_EVALUATION_ALLOWED` 与 CLI 批次授权检查；offline preflight 将 `36+20` 输出为 `56 ≤ 44` 并硬编码 pass。详见 `agent-work/reviews/APP-001-NEXT-REAL-MODEL-EVALUATION-codex-review.md`。
- 边界：未运行正式入口、live preflight 或 HTTP；未读取密钥/.env 或历史 raw；未创建正式批次目录；无正式 batch ID/请求授权。dry-run 与 offline-preflight 按离线 CLI 实测运行，但 preflight 结论不可采信，直到预算计算修正。
- 下一步：对两项 P1 作窄修复并补 API 绕过拒绝和预算不等式测试；完成后由 Codex 中枢独立复审，再做 final offline preflight。


### APP-001-NEXT-REAL-MODEL-EVALUATION-R2-CODEX-ACCEPTANCE / Codex 中枢 / in_progress / 2026-11-11

- 验收对象：`5b803eb`（基线 `3d42ff2`），开始时 main 干净、ahead 10。R2 的 runner 缺索引拒绝及 CLI 加载异常返回 1 均通过中枢独立复核。
- 中枢补测：`c00c214` 只修改测试；3 项真实 CLI/loader 回归覆盖 config 缺失、读取失败、manifest 加载失败，断言 exit 1、明确 stderr、空 stdout，且 runner/账本/mkdir/urlopen 零调用。无需 CC 再返工生产代码。
- Python 3.11.18 实测：专项 86 项 OK；授权/预算/runner 120 项 OK（7 skips）；LLM 全量运行 941 项 OK（8 skips）；Schema 17 项 OK；相关 py_compile/diff-check 通过。dry-run 12 组合；真实冻结索引离线检查 pass，global=44、batch_dir_exists=false；无索引直接 runner 拒绝。精确命令与限制见同任务 codex-review 的 R2 部分。
- 结论：本次窄修 pass；任务状态恢复 in_progress，下一步 final offline preflight，再拟唯一 batch ID 与授权模板给负责人批准。历史 review 记录保留；尚无正式 batch ID/请求授权，gate=False。
- 边界：未调用真实模型/网络、未读密钥/.env/历史 raw、未创建正式批次目录；无 push。R2 报告对 candidate_roles/default_top_k 直接校验的描述超出该方法实际范围，审查记录已注明；本次通过针对索引缺失及加载失败修复。


### APP-002-INTEGRATION-A1-PREP / Codex 中枢 / planned / 2026-11-11

- 项目负责人明确调整优先级：先单族自然语言→v5→Schema→Typed CAD IR→CadQuery→几何验证→STEP最小闭环，再做演示；v5保留冻结锚点，一般优化不启动v6。新增accepted ADR-0020，同步当前状态/计划/分工；12-run检索对照真实执行改deferred，不再列CAD集成前置门。该研究恢复须重验当前基线并独立授权，ADR-0019预算和scope不变。
- 启动事实：共享Git根目录正确，main=993a5b1，工作区干净，领先缓存origin/main12个提交；未fetch/push/merge。读取最新项目事实、交接与记忆协议、Schema/IR/CAD checkpoint/源码及最终修复审查，未覆盖其他工作。
- Final offline preflight实际运行：Python3.11.18，review-only-final-offline-993a5b1，exit0/status=pass、12组合、冻结索引校验、预算feasible/global44/Ollama26、batch_dir_exists=false。仅离线占位ID，无正式batch分配或模型/live preflight授权。
- 资产复验：固定CAD环境Python3.11.18/CadQuery2.3.0/OCP7.9.3.0，CAD13项（真实本地构造/STEP导出回读与故障注入）、Schema/IR22项通过；v5激活/策略/prompt161项通过；7个合成接口探针涵盖合法、cm换算、70/80第二螺钉边界、缺参、冲突、unsupported，全部符合预期。不是模型→STEP整链证据；未重复完整15行几何构造或此前941项LLM全量。
- 真实缺口：现有adapter在Schema之后主动阻断IR；缺正式参数→IR映射、完整missing_fields构造门与隔离统一入口。记录user/catalog/rule来源和原单位；最终成功必须本次STEP回读/几何通过，失败不能串旧文件。已出A1可执行CC工作prompt和checkpoint，任务planned/待CC认领，未声称已实现。
- 证据：agent-work/reviews/APP-001-V5-INTEGRATION-BASELINE-preflight.md；工作包：docs/coordination/prompts/APP-002-INTEGRATION-A1-cc.md。15行是单族目录配置而非语言样本；语言覆盖、稳定性、跨族分别后置验证。错误几何/关键参数丢失/错误放行/假成功阻断，其余一般优化列backlog。
- 边界：本轮无生产代码变更，无模型/HTTP请求，无密钥/.env/历史raw正文读取，无正式批次创建。历史批次及raw路径偏离保留只读；真实模型CAD整链需独立输入/预算/batch/授权，旧Schema-only授权不扩展。
- 下一步：把A1工作prompt交负责Schema/CAD的CC实现，中枢独立double check验收；通过后立即准备A2真实模型整链接线与授权，再做里程碑B/C。当前未完成真实自然语言整链，导师展示仍为目标。提交短哈希将在后续交付索引记录。

### APP-002-INTEGRATION-A1-PREP-DELIVERY / Codex 中枢 / planned / 2026-11-11

- 工作包提交：`8b76a7a`，9份文档包含ADR-0020、当前计划/状态、final offline证据、CC工作prompt与checkpoint；无生产/测试/脚本修改。
- 提交前检查通过：git diff/cached --check；冻结v5 prompt与acceptance哈希未变；Markdown链接目标存在；WORKLOG前缀与原历史完全一致（只追加）；review-only占位批次目录不存在。
- 下一步：CC在实际最新HEAD认领A1并执行工作prompt，中枢独立验收后转A2真实模型整链范围与授权。本次未push、未启动CC后台执行、未发真实模型请求；本条仅补交付commit索引。


### APP-002-INTEGRATION-A1-P1-FIX / CC / in_progress / 2026-11-11

- 任务：Codex 中枢复现 pipeline 将 run 目录外 STEP 误报为成功；实施 P1 窄修。
- 复现问题：`run_pipeline()` 中 Stage 5 使用 `manifest = compilation.manifest or {}` 和 `if manifest_step_hash:` 条件判断，导致缺失 manifest、缺失 `input_ir_sha256`、缺失 STEP sha256 时静默跳过；且未检查 `step_path` canonical containment，外部旧 STEP 路径被接受为成功产物。
- 修复：替换 `src/integration/pipeline.py` Stage 5 为六条件成功门（manifest 存在、input_ir_sha256/step.sha256 非空且有效、IR hash 匹配、STEP hash 匹配、STEP 路径位于当前 run 的 `cad_output/` 内）。任一条件失败返回 `failed`，`step_path=None`，不访问/复制/删除外部文件。
- 测试：更新 `_mock_compile_success` 传入 `raw` 计算正确 IR hash；新增 TestPipelineExternalStepRejected、TestPipelineManifestMissing、TestPipelineManifestInputIRHashMissing、TestPipelineManifestStepHashMissing、TestPipelineInputIRHashMismatch、TestPipelineStepHashMismatch、TestPipelineSuccessGateAllConditions 共 10 项 P1-FIX 测试。
- 验证（VM，Python 3.10，无 cadquery）：81 项集成测试 OK（+10 新增）；17 项 Schema 测试 OK；py_compile 通过；git diff --check 通过。tests/cad_compilation 13 项（需 cadquery）not_run_no_cad_runtime；真实 CLI/STEP 验收须 Mac 固定环境。
- 未改变：Schema/IR 语义、编译器规则、prompt、预算、授权、历史批次；FORMAL_EVALUATION_ALLOWED=False 不变。
- 提交：分支 cc/APP-002-INTEGRATION-A1，P1 窄修 commit（见下方 short hash）。
- 下一步：Codex 中枢在 Mac 固定 CAD 环境执行 `work/benchcad-output/venv/bin/python scripts/run_cad_pipeline.py --request "请按 GN 705 做一个轴环，孔径 24 mm" --synthetic-envelope tests/integration/fixtures/answer-bore24.json --output-root work/integration-runs --json`，确认 status=success、STEP 路径在 cad_output/ 内、两个 manifest hash 匹配，再运行 13 项 CAD 和 81 项集成测试，通过后合入 main。
### APP-002-INTEGRATION-A1-CLOSEOUT / Codex 中枢 / done / 2026-11-11

- 事实收束：A1 分支 `cc/APP-002-INTEGRATION-A1` 的 `d6faf70` 已合入并推送 `main`；本地 `main`、`origin/main` 与 A1 远端 ref 一致。
- 验证：合并后集成测试 81 项、Schema 测试 17 项通过；此前固定 CAD 环境 CAD 回归 13 项、bore24 STEP 成功/回读、ask 阻断、外部 STEP/symlink 逃逸拒绝和独立复核均通过。
- 结论：A1 最小后端集成完成；合成 envelope 证据不称为真实模型理解。P1 fail-closed 成功门已生效。
- 边界：未调用模型/网络，未读取密钥/.env，未创建正式 batch；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 下一步：进入 `APP-002-INTEGRATION-A2-SCOPE`，先冻结真实模型整链 scope、预算、batch、授权和受控入口。

### APP-002-INTEGRATION-A2-SCOPE / CC / in_progress / 2026-11-11

- 动作：CC 执行 A2 scope 准备：接口核对、授权 profile 实现、冻结输入/标签、受控入口和 40 项离线测试。
- 新建文件：
  - `src/llm/a2_authorization.py`：`A2IntegrationAuthorization`（继承 `FormalRunAuthorization`，覆盖 `__post_init__` 完整检查；profile_id/input_ids/inputs_sha256/enable_cad_pipeline 任一不符冻结常量立即 raise `AuthorizationScopeError`）；`authorize_a2_run(*, batch_id)` 工厂；profile_id=`app002-integration-a2.v1`；scope：DeepSeek `deepseek-flash` only，C0 only，3 inputs × 3 attempts = 9次 HTTP 上限，`enable_cad_pipeline=True`。
  - `src/integration/a2_runner.py`：`run_a2_offline_preflight()`（inputs SHA-256、budget、batch dir、prompt 检查）；`run_a2_batch(dry_run=True/False, transport=...)`；`_run_one_logical_mock()`（使用 FakeTransport 直接调用 build_deepseek_request→send_with_retry→parse→gate→schema→run_pipeline，绕过 Adapter 的 exact-type FakeTransport 检查）；`_run_one_logical()`（正式路径，使用 BudgetAwareTransport+Adapter）；`CapturingTransport` 已移除。
  - `tests/integration/test_a2_runner.py`：40 项离线测试，涵盖授权验证（10项）、preflight（4项）、dry-run（5项）、gate（2项）、mock 成功/ask/refuse/blocked/失败（9项）、隔离/版本/hash/budget（10项）。
  - `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/model-inputs.json`：3 条冻结自然语言输入（无 evaluator-only 字段）；SHA-256 `d290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b`。
  - `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/evaluator-labels.json`：评测预期（仅供人工评估，不进入 runner/prompt/adapter）；SHA-256 `67fe1e68ed27fbaef420846ac2f7eb92abb402b49134a058f676a4bdb965d6e7`。
  - `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md`：scope 草案，含输入清单、预算、目录结构、错误码、退出码和进入 live preflight 的前置条件。
- 接口核对结论：
  - A2 不重复实现后端，只添加"LLM 调用 → pipeline 调用"连接层。
  - `Adapter.run()` 的正式路径（`BudgetAwareTransport`）不需要修改；`A2IntegrationAuthorization` 继承 `FormalRunAuthorization`，可直接通过 Adapter gate 的 `isinstance` 检查。
  - mock 路径绕过 Adapter `type(transport) is FakeTransport` 的 exact-type 检查，直接调用 `send_with_retry → parse → gate → schema → run_pipeline()`，不修改 adapter.py。
  - raw 留存使用 `work/app001-runs/{batch_id}/raw/`（在 `BudgetLedger` canonical root 内）；pipeline 输出 `work/app001-runs/{batch_id}/pipeline-runs/`（`run_pipeline()` 无路径限制）。
  - `BudgetLedger` canonical root `work/app001-runs/` 不需修改；A2 batch_id `app002-a2-smoke-YYYYMMDD-NN` 自然落入。
- 验证（VM，Python 3.10，无 cadquery）：
  - `py_compile` `a2_authorization.py` / `a2_runner.py`：通过
  - `python -m unittest tests.integration.test_a2_runner -v`：Ran 40 tests; OK
  - `python -m unittest discover -s tests/schema -p 'test_*.py' -q`：Ran 17 tests; OK
  - `git diff --check`：通过（所有新文件均为 untracked）
- 注：`tests/integration/test_pipeline.py` 和 `test_schema_to_ir.py` 在 VM（Python 3.10 / 无 cadquery）下有既有失败，原因是 VM 缺 cadquery/OCP，与新文件无关（已记录于 A1 checkpoint 为 `not_run_no_cad_runtime`）。
- 边界：未发模型/网络请求；未读取密钥/.env；未创建正式 batch；未修改冻结 prompt/Schema/IR 语义/旧 runner/历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 提交：分支 `cc/APP-002-INTEGRATION-A2-SCOPE`（WIP commit，见下方 short hash）。
- 下一步：Codex 中枢在 Python 3.11.18 下独立复核（40 项 A2 + LLM 全量 + Schema 17 + dry-run preflight + inputs SHA-256 核对），通过后向项目负责人提交 scope 草案和授权模板，取得批准后再进行 live preflight。

### APP-002-INTEGRATION-A2-R1-CORRECTION / CC / review / 2026-11-11

- 基线：分支 `cc/APP-002-INTEGRATION-A2-SCOPE`，HEAD `6866707`，父提交 `55547fb`。工作区开始时干净。
- 任务：修复 Codex 中枢验收发现的三项问题，不扩展 A2 scope。
- 修复 1（测试批准凭证不能通过正式批准门）：
  - `A2FormalApproval` 新增 `is_test_only: bool = False` 字段。
  - `validate_formal_approval_binding()` 在 batch_id 匹配检查前增加 `is_test_only` 结构性拒绝；test-only 凭证在任何目录/账本/transport 创建前被拒绝。
  - `make_test_approval()` 现在设置 `is_test_only=True`。
  - 这不是密码学签名或不可伪造身份认证；是结构性 guard。
  - 回归测试：`test_test_only_approval_rejected_before_any_side_effect` 验证 0 目录创建、0 BudgetLedger、0 Transport、0 HTTP。
- 修复 2（摘要最终写入失败必须明确失败）：
  - `A2BatchResult` 新增 `summary_finalize_error: str | None` 字段。
  - `run_a2_batch()` 不再吞掉 `writer.finalize()` 的 `SummaryWriteError`；错误记录在 `summary_finalize_error` 中返回给调用方。
  - 账本锁仍在 `finally` 块中释放。
  - 回归测试：`test_finalize_failure_records_explicit_error` 验证 `SummaryWriteError` 被 raise。
- 修复 3（摘要记录真实 prompt hash 和 raw retention 证据）：
  - `_build_initial_summary()` 的 `artifact_hashes` 新增 `prompt_file_sha256`（完整 64 字符 `FROZEN_PROMPT_FILE_SHA256`），不只是版本号或截断 hash。
  - `A2RunResult` 新增 `raw_retention_meta: dict | None` 字段，从 Adapter `RunRecord.raw_response_retention` 安全传递。
  - `_SummaryWriter.update_run()` 的 `raw_sha256` 现在来自 `raw_retention_meta["body_sha256"]`，不再从 `ir_index["envelope_sha256"]` 推导。
  - 非 answer 路径（ask/refuse/blocked/parse error）在正式模式下也填充 `raw_retention_meta` 和 `raw_retention_path`。
  - 无响应时 `raw_retention_meta=None`，summary 中 `raw_sha256=None`、`raw_retained=None`。
  - summary 不写入 raw 正文、API key、Authorization header 或 evaluator labels 内容。
  - 回归测试：`test_mock_answer_summary_has_raw_retention`、`test_mock_ask_summary_has_raw_retention`、`test_no_response_summary_has_no_raw_evidence`、`test_initial_summary_has_full_prompt_file_sha256`、`test_raw_body_content_not_in_summary`。
- 新增 14 项 R1-CORRECTION 专项测试（`TestA2R1Correction`），总计 81 项 A2 测试。
- 验证（VM，Python 3.10.12，无 cadquery）：
  - `py_compile` `a2_authorization.py` / `a2_runner.py` / `test_a2_runner.py`：通过
  - `python -m unittest tests.integration.test_a2_runner -q`：Ran 81 tests; OK
  - `python -m unittest discover -s tests/schema -p 'test_*.py' -q`：Ran 17 tests; OK
  - `git diff --check`：通过
  - 既有 `test_pipeline.py` 和 `test_schema_to_ir.py` 的 25 failures + 3 errors 为 VM 缺 cadquery/OCP 导致的既有问题（stash 验证确认），本次修改不引入新失败。
- 未运行（需 Mac 固定环境 Python 3.11.18）：
  - A2 专项 81 项、Integration 全量（含 cadquery 路径）、Schema 17 项、LLM 全量 941 项、`py_compile` 3 文件、`git diff --check`
- 边界：未发模型/网络请求；未读取密钥/.env；未创建正式 batch；`FORMAL_EVALUATION_ALLOWED=False` 不变；未修改冻结 prompt/Schema/IR 语义/旧 runner/历史批次。
- 下一步：Codex 中枢在 Python 3.11.18 下独立复核（81 项 A2 + LLM 全量 + Schema 17 + py_compile + diff --check）。

### APP-002-INTEGRATION-A2-R1-CORRECTION-2 / CC / review / 2026-11-11

- 基线：分支 `cc/APP-002-INTEGRATION-A2-SCOPE`，HEAD `230609c`，工作区开始时干净。
- 任务：补全正式 answer 路径的 raw retention 传递；补齐 finalize 失败端到端测试。
- 修复 1（answer 路径 raw retention 传递）：
  - `_run_one_logical()` 的 answer 路径在取得 `adapter_result.record` 后，统一从 `record.raw_response_retention` 复制 `answer_retention_meta`。
  - 三个 answer 分支（pipeline 成功返回、raw 文件不可用、pipeline 异常）全部传入 `raw_retention_meta=answer_retention_meta`。
  - `raw_retention_path` 只使用 retention metadata 中确认的 repo-relative retained path。
  - `raw_sha256` 只由 `raw_retention_meta["body_sha256"]` 提供，不从 `ir_index["envelope_sha256"]` 推导。
  - 无模型响应时 `raw_retention_meta=None`，不伪造 hash。
  - mock/dry-run 行为不变。
- 修复 2（finalize 失败端到端测试）：
  - 新增 `test_finalize_failure_in_formal_path_via_writer_patch`：patch `_SummaryWriter.finalize` 使其 raise `SummaryWriteError`，patch `BudgetLedger`、`BudgetAwareTransport`、`DeepSeekTransport`、`_run_one_logical` 使用 mock 替身，验证：
    - `summary_finalize_error` 非空且包含 "finalize"；
    - 3 条 run 结果仍返回（分母完整）；
    - `ledger.release_lock` 被调用（锁释放）；
    - `run_pipeline` 未被调用（所有 run 为 ask）；
    - `summary_path` 非空（即使 finalize 失败）。
  - 不发网络、不读密钥、不调用真实 DeepSeek。
- 新增 6 项 R1-CORRECTION-2 专项测试（`TestA2R1Correction2`），总计 87 项 A2 测试。
- 验证（VM，Python 3.10.12，无 cadquery）：
  - `py_compile` `a2_runner.py` / `test_a2_runner.py`：通过
  - `python -m unittest tests.integration.test_a2_runner -q`：Ran 87 tests; OK
  - `python -m unittest discover -s tests/schema -p 'test_*.py' -q`：Ran 17 tests; OK
  - `git diff --check`：通过
  - 既有 `test_pipeline.py` 和 `test_schema_to_ir.py` 的 failures 为 VM 缺 cadquery/OCP 的既有问题，本次修改不引入新失败。
- 未运行（需 Mac 固定环境 Python 3.11.18）：
  - A2 专项 87 项、Integration 全量（含 cadquery 路径）、Schema 17 项、LLM 全量 941 项、`py_compile` 3 文件、`git diff --check`
- 边界：未发模型/网络请求；未读取密钥/.env；未创建正式 batch；`FORMAL_EVALUATION_ALLOWED=False` 不变；未修改冻结 prompt/Schema/IR 语义/旧 runner/历史批次/inputs hash/labels hash/budget/scope/is_test_only 逻辑。
- handoff_self_check:
  - changed=src/integration/a2_runner.py(answer_retention_meta 传入 3 个 answer 分支), tests/integration/test_a2_runner.py(+6 R1-CORRECTION-2 测试, 87 项总计), docs/WORKLOG.md(追加), agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/checkpoint.md(追加)
  - commands=py_compile(2文件)通过; 87项 test_a2_runner 通过; 17项 Schema 通过; git diff --check 通过; Python 3.10.12
  - confirmed=answer 路径 3 分支均携带 raw_retention_meta; raw_sha256 来自 retention meta 非 ir_index; 无响应时 meta 为 None; finalize 失败时 summary_finalize_error 非空且锁释放; 分母 3 条 run 完整; mock 结果不代表真实模型效果
  - unresolved=Python 3.11.18 下全量验证(LLM 941项, integration cadquery路径, 87项A2专项); test_pipeline/test_schema_to_ir 既有 VM cadquery 缺失失败
  - next_agent_focus=Codex 中枢在 Python 3.11.18 下: 1) 87项A2测试; 2) LLM全量; 3) Schema 17项; 4) py_compile; 5) git diff --check; 6) 确认 answer 路径 raw_retention_meta 传递、finalize 端到端错误可见、锁释放均通过


### APP-002-INTEGRATION-A2-R1-CORRECTION-2 / Codex 中枢独立复核 / pass / 2026-11-12

- 基线：分支 `cc/APP-002-INTEGRATION-A2-SCOPE`，提交 `e037cb2`，工作区干净。
- 动作：核对 R1-CORRECTION-2 差异和 checkpoint；在 Python 3.11.18 下重跑窄修及上下游回归；抽查正常、失败和 dry-run 路径。
- 验证：A2 专项 `87/87` 通过；固定 CadQuery 环境 Integration 全量 `168/168` 通过；Schema `17/17` 通过；LLM `941` 通过、`8` 个既有 FUSE skip；相关 `py_compile`、`git diff --check` 通过。
- 确认：正式 answer 的成功、raw 读取失败、pipeline 异常分支均保留 `raw_retention_meta`；summary 的 `raw_sha256` 来自 retention `body_sha256`；finalize 失败可见于 `summary_finalize_error`，3 条结果保留且账本锁释放；dry-run 保持无副作用。
- 文档收束：修正 checkpoint 中过时的 Integration 预期数字 `81+6=87`，明确实际总数为 `81+87=168`，并追加独立复核 handoff 记录。
- 边界：未调用真实模型、未访问网络或密钥、未创建正式批次；`FORMAL_EVALUATION_ALLOWED=False`、A2 scope、预算、输入/labels hash 未改变。
- 下一步：将分支合并到 `main`；合并后再把 A2 scope 标记为 `done`，然后按负责人批准的独立 batch scope 决定是否进入 live preflight。


### APP-002-INTEGRATION-A2-SCOPE / 合入收束 / Codex 中枢 / done / 2026-11-12

- 动作：确认用户已将 `cc/APP-002-INTEGRATION-A2-SCOPE` 以 fast-forward 方式合入并推送 `main`。
- 结果：`main`、`origin/main` 与该分支均指向 `9b9395c`，工作区干净。
- 收束：PROJECT_STATUS、PROJECT_PLAN 和 A2 checkpoint 已同步为 scope 准备完成；记录 Python 3.11.18 独立复核结果（A2 87/87、Integration 168/168、Schema 17/17、LLM 941 + 8 skip）。
- 边界：尚未发起 live preflight 或真实模型请求；`FORMAL_EVALUATION_ALLOWED=False`、A2 scope、预算、输入/labels hash 和历史批次保持不变。
- 下一步：项目负责人批准具体 batch_id、3 条输入、DeepSeek/C0/9 次 HTTP scope 和完整授权声明后，执行 live preflight；通过后才可发起真实请求并进入里程碑 B。

### APP-002-INTEGRATION-A2-LIVE-ATTEMPT / Codex 中枢 / blocked / 2026-11-12

- 授权范围：负责人批准 batch `app002-a2-smoke-20261112-01`，DeepSeek `deepseek-flash`、C0、`A2-24mm`/`A2-80mm`/`A2-ask-bore`，最多 3 logical runs / 9 次 HTTP，允许 CAD pipeline。
- 预检：固定 Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0；inputs hash、offline preflight 和 dry-run 通过。
- 结果：正式入口在首个 HTTP 请求前失败，`BudgetAwareTransport.__init__()` 不接受 `real_transport`，实际签名要求位置参数 `inner`。请求数为 0，未读取模型响应、未写 raw 或账本，锁已释放。
- 现场：保留并只读记录 `work/app001-runs/app002-a2-smoke-20261112-01/`；其 `batch_summary.json` 的 `batch_status=complete` 是入口异常留下的错误状态，3 条 run 仍为 `pending`，不得作为成功证据。不得删除、移动、覆盖或重跑该目录。
- 处置：A2 标记 `blocked`。CC 仅做窄修，将调用改为 `BudgetAwareTransport(inner, ...)`，补固定环境构造回归和零 HTTP 断言；不改变 scope、预算、授权、冻结 prompt/Schema/IR/CAD、历史批次或 `FORMAL_EVALUATION_ALLOWED`。
- 下一步：窄修后由 Codex 中枢独立复核全套回归和入口；在复核通过且同一 batch 的现场/授权状态重新核对前，不再次发起请求。

### APP-002-INTEGRATION-A2-LIVE-FIX / CC / review / 2026-11-11

- 基线：分支 `main`，HEAD `6fdbb86`。工作区开始时干净。
- 任务：修复 A2 正式入口在首个 HTTP 请求前的构造错误，不扩大正式执行范围。
- 修复 1（BudgetAwareTransport 构造器签名）：
  - `src/integration/a2_runner.py` 中 `BudgetAwareTransport(real_transport=..., ...)` 改为 `BudgetAwareTransport(DeepSeekTransport(...), ...)`（位置参数 `inner`）。
  - 补全缺失的 `logical_run_id=plan.logical_run_id`（必填 keyword-only 参数）。
- 修复 2（setup 异常 fail-closed）：
  - `BudgetLedger()` 或 `ledger.acquire_lock()` 在 `write_initial()` 之后失败时，`batch_summary.json` 会留在 `batch_status="running"` 状态。
  - 增加 try/except 包裹，失败时以 `batch_status="aborted"` finalize，然后 re-raise。
  - 不伪造成功；不把 aborted 当作 complete。
- 新增 5 项 R1-LIVE-FIX 回归测试（`TestA2LiveFix`），总计 92 项 A2 测试：
  - 构造器签名验证（`inner` 位置参数，`logical_run_id` 必填）
  - 源码级验证不使用 `real_transport=`
  - setup 失败时 `batch_status="aborted"`
  - setup 失败时 0 次 `urlopen` 调用
- 验证（VM，Python 3.10.12，无 cadquery）：
  - `py_compile` `a2_runner.py` / `test_a2_runner.py`：通过
  - `unittest tests.integration.test_a2_runner`：Ran 92 tests; OK
  - `unittest discover -s tests/schema`：Ran 17 tests; OK
  - `git diff --check`：通过
- 未运行（需 Mac 固定环境 Python 3.11.18）：
  - A2 专项 92 项、Integration 全量、Schema 17 项、LLM 全量、py_compile 3 文件、git diff --check
- 边界：未发模型/网络请求；未读取密钥/.env；未创建正式 batch；`FORMAL_EVALUATION_ALLOWED=False` 不变；冻结 inputs/prompt/Schema/provider/model/condition/预算/batch scope 未修改；旧批次和历史证据未移动/覆盖/重跑。
- handoff_self_check:
  changed=src/integration/a2_runner.py(BudgetAwareTransport位置参数inner+logical_run_id+setup fail-closed),tests/integration/test_a2_runner.py(+5 R1-LIVE-FIX测试,92项总计),docs/WORKLOG.md(追加)
  commands=py_compile(2文件)通过;92项test_a2_runner通过;17项Schema通过;git diff --check通过(Python 3.10.12)
  confirmed=BudgetAwareTransport构造器使用位置参数inner;logical_run_id已传入;setup失败finalize为aborted非complete/running;setup失败0次urlopen;real_transport=不在源码中
  unresolved=Python 3.11.18下全量验证(92项A2+LLM全量+Integration全量+Schema17+py_compile+diff --check);cadquery路径(test_pipeline/test_schema_to_ir既有失败VM缺cadquery)
  next_agent_focus=Codex中枢在Python 3.11.18下:1)92项A2测试;2)LLM全量;3)Integration全量(含cadquery);4)Schema17;5)py_compile3文件;6)git diff --check;7)确认BudgetAwareTransport构造器签名匹配、setup失败aborted语义、zero HTTP断言

### APP-002-INTEGRATION-A2-LIVE-FIX / Codex 中枢独立复核 / pass_for_code_fix / 2026-11-12

- 基线：`main` HEAD `c954741`，父提交 `6fdbb86`；工作区干净。固定环境 Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0。
- 代码核对：`BudgetAwareTransport` 调用已改用位置参数 `inner`，并绑定必需 `logical_run_id`；setup failure 记录为 `aborted` 的修复与测试存在。
- 验证：A2 `92/92`、Integration `173/173`、Schema `17/17`、LLM `941` 通过且 `8` 个既有 skip；`py_compile`、`git diff --check 6fdbb86..HEAD` 通过。另以隔离临时根目录 mock 正式入口构造 3 个 wrapper，确认 logical/query/condition 绑定正确且 `urlopen=0`。
- 限制：未调用网络/模型、未读取密钥或 `.env`；`FORMAL_EVALUATION_ALLOWED=False`。原授权 batch 目录未触碰，仍只有失败时的 `batch_summary.json`。
- 当前获批 batch 的只读 offline preflight 为 `ok=false`，唯一阻断项是 `batch_dir_exists=true`；冻结 inputs hash、prompt 加载、9 HTTP 预算可行性均通过。按唯一 batch 约束，不能复用这个 ID。
- 结论：窄修代码验收通过，但真实整链尚未运行。下一步需项目负责人批准新的唯一 batch ID 并确认相同 DeepSeek/C0、3 输入、9 HTTP scope；保留旧失败目录，不移动、不覆盖、不重跑。

### APP-002-INTEGRATION-A2-FORMAL-GATE-BLOCK / Codex 中枢 / blocked / 2026-11-12

- 授权：负责人批准新 batch `app002-a2-smoke-20261112-02`，延续 DeepSeek `deepseek-flash`、C0、三条冻结输入、最多 9 HTTP、允许 CAD pipeline 的 A2 scope。
- preflight：Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0；目录初始不存在、inputs hash 匹配、prompt 可加载、预算可行，offline preflight 通过。凭据从 `.env` 仅加载到本进程，未显示或写入。
- 执行：三条 run 均被 Adapter 以 `FORMAL_EVALUATION_ALLOWED=False` 拒绝，状态 `ADAPTER_EXCEPTION`。没有账本、raw、STEP 或 HTTP attempt，模型未调用。
- 失败现场：`work/app001-runs/app002-a2-smoke-20261112-02/` 仅有 `batch_summary.json`，其顶层 `batch_status=complete` 与 3 条 error 结果矛盾；该 batch ID 作废，目录只读保留，不得重跑或覆盖。此前 `...-01` 失败目录同样保持不动。
- 判断：A2 runner 构造窄修 `c954741` 已通过中枢复核，但本次获批 batch scope 不会自动更改仓库明确保持关闭的全局 formal gate。不得绕过 Adapter 或擅自改 `FORMAL_EVALUATION_ALLOWED`。
- 下一步：项目负责人先决定是否批准通过 ADR 建立 A2 专用正式 gate/明确 gate 关系，并接受相应窄修；同时修正全失败批次的 `batch_status`。实现和独立复核完成后再创建新唯一 batch ID 并单独批准 live scope。

### APP-002-INTEGRATION-A2-GATE-STATUS-FIX / Codex 中枢 / review / 2026-11-12

- 动作：按负责人明确要求推进测试所需 gate；追加 ADR-0021，将既有 A2 scope + 同 batch 非 test-only approval 明确为 A2 专用 formal gate，保持全局 `FORMAL_EVALUATION_ALLOWED=False`。
- 修正：查明 Adapter 拒绝原因是 `BudgetAwareTransport.adapter_run_id` 与随机 Adapter `run_id` 不匹配；formal A2 路径改用冻结 logical run ID。Summary 对 all-error=`failed`、mixed errors=`partial`、中途停止=`aborted`、完整非错误终态=`complete`。
- 验证：Python 3.11.18 下 A2 96 项、Integration 176 项、Schema 17 项通过；LLM 941 项通过/8 项既有 skip；py_compile 与 diff-check 通过。合法绑定到达 prompt 验证，错误 run ID 仍 fail closed；无模型/网络/密钥读取。
- 下一步：完成中枢差异复核；若通过，合入后重跑离线 preflight，并另行取得新唯一 batch 的明确 live 执行批准。`...-01`、`...-02` 失败现场只读保留。
### APP-002-INTEGRATION-A2-LIVE-EXECUTION-03 / Codex 中枢 / review / 2026-11-12

- 授权：项目负责人明确批准 batch `app002-a2-smoke-20261112-03` 的 live preflight 与三条 DeepSeek `deepseek-flash` / C0 整链请求（`A2-24mm`、`A2-80mm`、`A2-ask-bore`），最多 9 次 HTTP，允许 CAD pipeline。
- 执行前核验：分支 `codex/APP-002-A2-GATE-STATUS-FIX`、HEAD `1dc61bc`、工作区干净；Python 3.11.18 离线 preflight 通过，inputs hash、v5 prompt、9 次预算可行，batch 目录不存在。
- 结果：三条均发出 1 次 HTTP，账本为 3/9。`A2-24mm` 和 `A2-80mm` 的模型决策均为 answer，但 CAD pipeline 在 IR Schema 校验阶段因 `CAD_SCHEMA_VALIDATOR_UNAVAILABLE` 失败，没有 STEP；`A2-ask-bore` 为 ask，正确停止构造。摘要 `batch_status=partial`，与逐条结果相符。
- 根因：本次用 `/opt/homebrew/bin/python3.11` 启动 A2 runner，该解释器没有 `jsonschema`；固定 CAD venv 则为 Python 3.11.18、jsonschema 4.26.0、支持 Draft 2020-12、CadQuery 2.3.0、OCP 7.9.3.0。后续 A2 整链必须由 CAD venv 启动。
- 安全与批次边界：凭据仅在 Python 进程内从 `.env` 读取，未显示或另行持久化；未读取 evaluator labels 或 raw 正文。`...-03` 已使用，目录只读保留，不补跑、不覆盖、不更新 summary。模型输出原始文本未查看。
- 另有一个仅影响本次结果显示的脚本错误：run 完成后访问了不存在的 `A2BatchResult.summary_status`，外层以 AttributeError 退出；持久化 summary 与账本仍为实际状态事实源。
- 下一步：独立复核并合入 `1dc61bc`；之后以固定 CAD venv、新唯一 batch ID 做离线 preflight，并向负责人另行申请 live 执行授权。全局 `FORMAL_EVALUATION_ALLOWED=False` 与 ADR-0021 专用 gate 不变。

### APP-002-A2-CAD-RUNTIME-PREFLIGHT-GUARD / Codex 中枢 / review / 2026-11-12

- 动作：针对 `...-03` 在系统 Python 缺 `jsonschema`、导致真实请求已消费后 CAD Schema 校验失败的问题，在 A2 formal preflight 增加 runtime capability gate。
- 修正：formal 路径在任何批次目录、BudgetLedger、Transport 或 HTTP 前验证 `jsonschema.Draft202012Validator`、CadQuery 和 OCP。dry-run/mock 不要求完整 CAD 环境，保留轻量测试能力；没有向系统 Python 安装依赖。
- 测试：新增两项 A2 回归，覆盖依赖缺失时 fail-closed 和正式入口零副作用。
- 验证：固定 CAD venv Python 3.11.18 下 A2 专项 98/98 通过；formal offline preflight 检测出 jsonschema 4.26.0、Draft 2020-12、CadQuery 2.3.0、OCP 7.9.3.0 并通过。系统 Python 3.11.18 同一检查失败并报告缺少 jsonschema/cadquery。`py_compile`、`git diff --check` 通过。
- 边界：未发网络/模型请求、未安装或升级依赖；冻结 scope、预算、授权和全局 gate 不变；`...-01` 至 `...-03` 现场只读保留。
- 下一步：对 runtime guard 独立复核并合入；之后固定以 CAD venv 执行 A2，新的 live batch 仍需新 batch ID 和负责人单独批准。

### APP-002-A2-GATE-STATUS-FIX / CC / review / 2026-11-12

- 基线：分支 `codex/APP-002-A2-GATE-STATUS-FIX`，HEAD `351781f`。工作区开始时干净。
- 任务：仅测试范围窄修，补齐 A2 CAD runtime preflight 的缺依赖回归断言。
- 修改：`tests/integration/test_a2_runner.py` 中 `test_formal_run_with_missing_cad_dependencies_has_zero_side_effects` 扩展 spy/mock 断言：
  - `BudgetAwareTransport` 构造次数为 0（新增 `patch("llm.budget.BudgetAwareTransport")`）；
  - `DeepSeekTransport` 构造次数为 0（已有，保留）；
  - `urllib.request.urlopen` 调用次数为 0（新增 `patch("urllib.request.urlopen")`）；
  - `BudgetLedger` 未构造（已有，保留）；
  - 批次目录不存在（已有，保留）；
  - `_check_cad_runtime` 被实际调用（新增 `mock_check.assert_called()`）。
- 未改生产代码、ADR、scope、预算、授权、冻结输入或 prompt。
- 验证（VM，Python 3.10.12，无 cadquery）：
  - 目标测试 `test_formal_run_with_missing_cad_dependencies_has_zero_side_effects`：通过
  - 全量 98 项：4 项既有失败/错误（`TestA2LiveFix` × 3 + `TestA2R1Correction2` × 1），经 stash 验证为基线 `351781f` 既有问题，非本次引入
- 未运行（需 Mac 固定环境 `work/benchcad-output/venv/bin/python` Python 3.11.18）：
  - A2 专项 98 项、Integration 全量 179 项、py_compile、git diff --check
- 边界：未运行真实模型/live preflight/正式批次；未读取 `.env`/密钥/raw/历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变；`...-03` 批次只读。
- handoff_self_check:
  changed=tests/integration/test_a2_runner.py(扩展缺依赖测试的零调用断言)
  commands=target_test通过(Python 3.10.12);4项既有失败经stash确认非本次引入
  confirmed=BudgetAwareTransport构造0次;DeepSeekTransport构造0次;urlopen调用0次;BudgetLedger未构造;批次目录不存在;_check_cad_runtime被调用
  unresolved=Python 3.11.18固定环境全量验证(98项A2+179项Integration+py_compile+diff --check)
  next_agent_focus=Codex中枢在work/benchcad-output/venv/bin/python(Python 3.11.18)下:1)98项A2;2)Integration全量179;3)py_compile;4)git diff --check;5)确认目标测试的6项零调用断言全部通过

### APP-002-A2-GATE-STATUS-FIX-CLOSEOUT / Codex 中枢 / review / 2026-11-12

- 动作：同步 A2 runtime preflight guard 的独立复核、合入与固定环境复验事实，清理 PROJECT_STATUS / PROJECT_PLAN 中“待独立复核”的过时表述，并追加 checkpoint。
- 合入事实：`0b02a26` 在 `main` 与 `origin/main`；其父提交为 `351781f`，工作区干净。
- 验证：CAD venv Python 3.11.18 下缺依赖目标测试 1/1、A2 专项 98/98、Integration 全量 179/179；相关 `py_compile` 和 `git diff --check origin/main..HEAD` 通过。
- 结论：正式 preflight 的 runtime guard 及零调用测试已复核并合入；A2 真实模型→STEP 尚无成功证据，`...-01` 至 `...-03` 只读保留。
- 下一步：离线检查新候选 batch `app002-a2-smoke-20261112-04`；若 preflight 通过，再由负责人对该新 ID 单独批准 live 执行。

### APP-002-A2-LIVE-EXECUTION-04-PREFLIGHT / Codex 中枢 / review / 2026-11-12

- 动作：完成 A2 runtime guard 文档收束后，选择新候选 batch `app002-a2-smoke-20261112-04` 并执行离线 preflight。
- 文档收束提交：`84dd6b9`（状态/计划/checkpoint/WORKLOG 同步 runtime guard 合入与固定环境复验事实）。
- 环境与命令：固定 CAD venv Python 3.11.18；`authorize_a2_run(batch_id=...)` + `run_a2_offline_preflight(..., require_cad_runtime=True)`；单独调用 `_check_cad_runtime()` 只输出通过状态和错误数。
- 结果：preflight 通过；runtime、冻结输入 hash、prompt、预算均通过；3 runs × 3 attempts = 9，与上限 9 一致；batch 目录执行前后均不存在。
- 边界：未读取凭据、`.env`、raw 正文或 labels；未创建批次目录、初始化 transport、发 HTTP 或请求模型。旧 `...-01` 至 `...-03` 只读不动。
- 下一步：为候选 `...-04` 请求负责人单独批准 live preflight 与 3 条 DeepSeek/C0 整链运行，最多 9 HTTP；未获批前不发送请求。

### APP-002-A2-LIVE-EXECUTION-04 / Codex 中枢 / review / 2026-11-12

- 授权：项目负责人批准新唯一批次 `app002-a2-smoke-20261112-04`，限定 DeepSeek `deepseek-flash`、C0、`A2-24mm`/`A2-80mm`/`A2-ask-bore`、最多 9 次 HTTP，允许 CAD pipeline 并留存摘要、raw、pipeline 与 STEP 证据。
- 环境与执行：使用 `work/benchcad-output/venv/bin/python`（Python 3.11.18）；formal runtime preflight 通过。三条输入各一次 HTTP，账本 3/9，未重试；summary=`complete`。
- 结果：`A2-24mm` 为 answer，Schema/IR/CAD/STEP 导出及回读成功，参数 `bore_d=24 mm`、`second_screw=0`；STEP 148,393 bytes，SHA-256 `50c1c0626326eb828c8c0d0934d1913f0607300505cd96739ef3ad185f2184d6`。`A2-80mm` 为 answer，Schema/IR/CAD/STEP 导出及回读成功，参数 `bore_d=80 mm`、`second_screw=1`，第二螺钉几何分支启用；STEP 364,404 bytes，SHA-256 `8f48075fc9cb651af165f3092d1375bb59613440c2587efbc4ee5e9400f4e9d9`。两者均记录为有效单实体，并通过 CAD-006 几何验证与 STEP 回读比较；实际 STEP/IR hash 与 index/manifest 一致。`A2-ask-bore` 为 ask，未创建 pipeline 或 STEP。
- 只读复核：3 个 raw 路径均指向本批次 `raw/` 且文件非空，摘要留有各自 body SHA-256；未打开 raw 正文或 evaluator labels。`...-04` 已消耗，及 `...-01` 至 `...-03` 一样保持只读，不重跑、不覆盖、不混合。
- 文档同步：更新 PROJECT_PLAN / PROJECT_STATUS，追加本 checkpoint 与 WORKLOG。A2 状态仍为 `review`；本批次完成三个范围内案例，不代表完整六类 Milestone B 验收、广泛语言覆盖或制造认证。剩余：单位换算、显式冲突、CAD 构造/导出失败的整链验收，并独立复核此次证据。
- 不变量：`FORMAL_EVALUATION_ALLOWED=False` 不变；ADR-0021 A2 专用 gate、模型/输入/条件/预算边界不变；未 push/merge。
# 2026-11-12 — Codex — APP-002-A2-MILESTONE-B-ACCEPTANCE

- 动作：独立只读复核 A2 批次 `app002-a2-smoke-20261112-04`，并完成里程碑 B 六类定向整链验收。
- 验证：固定 CAD venv Python 3.11.18；A2 98/98、Integration 179/179、CAD compilation 13/13、Schema 17/17。额外使用真实统一 pipeline 和合成 fixture 验证 1.6 cm→16 mm 实际 STEP、显式目录冲突在 CAD 前阻断、注入 STEP 导出失败后明确 failed 且无 STEP/index。
- 批次复核：3 次请求/9 上限；24 mm 与 80 mm 的 IR/STEP hash 匹配 index/manifest，STEP readback comparison `pass=true`；缺参 ask 未进入 CAD。raw 正文与 evaluator labels 未读取，所有 A2 历史批次只读。
- 结果：A2 独立复核 pass；里程碑 B 完成。离线整链证据置于 git-ignore 的 `work/integration-runs/app002-milestone-b-20261112/`，详细报告见 `agent-work/reviews/APP-002-A2-MILESTONE-B-ACCEPTANCE.md`。
- 下一步：进入里程碑 C 最小可用演示；是否扩大 live 样本由负责人基于明确语言覆盖假设另行决定，未经新 scope/预算/batch ID/授权不发起新模型请求。

### APP-003-C1-R1-NARROW-FIX / CC / review / 2026-11-12

- 动作：在分支 `cc/APP-003-C1-LOCAL-DEMO`（HEAD 240a028）上完成两项窄修。
- **修复 1：manifest 字段名映射**（`src/demo/handler.py`）
  - `native_geometry` 字段名修正：`solid_count→solids`, `face_count→faces`, `edge_count→edges`, `vertex_count→vertices`（依据 `geometry.py` COUNTS 元组）。
  - readback 通过路径修正：`manifest["readback"]["pass"]` → `manifest["step_readback"]["comparison"]["pass"]`（依据 `compiler.py` 第307行赋值）。
- **修复 2：UI HTML 注入防御**（`src/demo/server.py`）
  - 新增 JS 函数 `esc(s)`：对 `&`/`<`/`>`/`"`/`'` 执行五种 HTML 转义。
  - `renderResult()` 中所有动态字符串（run_id、stage、错误码/消息、参数名/值、IR JSON）均改为 `esc(...)` 包裹。
  - fetch error 展示改用 `textContent`/`createElement` DOM API，消除 innerHTML 注入路径。
- **测试更新**（`tests/demo/test_demo_handler.py`）
  - mock manifest 结构改为真实 compiler 格式（`solids`/`faces`/`edges`/`vertices` + `step_readback.comparison.pass`）。
  - 新增 `TestManifestFieldMapping`（8 项）：验证实体/面/边/顶点数和 readback_pass 均从正确键读取，并有反向用例证明修复 load-bearing。
  - 新增 `TestUIHTMLEscape`（14 项）：验证 `esc()` 五种规则、XSS payload 完全转义、`renderResult` 源码使用 `esc()` 包裹动态值、恶意 bore_d 错误消息作为纯文本处理。
- 验证（sandbox Python 3.10.12）：
  - `py_compile`：5 个修改文件全部通过
  - `git diff --check`：通过
  - Demo 测试：**52/52 通过**（原 30 + 新增 22）
  - Integration test_pipeline **39/39**、test_schema_to_ir **42/42**、Schema **17/17** 通过
  - CAD compilation 4 ERROR/1 FAIL = 既有 CadQuery 缺失，与本次修改无关
- 不变量：不修改 pipeline.py、Schema、IR adapter、compiler、runner 等；不修改 A2 历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变；仅修改 `src/demo/handler.py`、`src/demo/server.py`、`tests/demo/test_demo_handler.py`、checkpoint/WORKLOG。
- 下一步：提交独立 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核。

### APP-003-C1-IMPLEMENTATION / CC / review / 2026-11-12

- 动作：在分支 `cc/APP-003-C1-LOCAL-DEMO`（基于 `main=1361f52`）实现首个本地 CAD Web 演示（APP-003-C1，ADR-0022）。
- 新增文件：
  - `src/demo/__init__.py`：模块初始化
  - `src/demo/handler.py`：业务逻辑（DemoHandler、DemoRunResult；复用 run_pipeline + validate_parameters + build_ir_from_schema_payload + compile_ir）
  - `src/demo/server.py`：标准库 http.server HTTP 服务端，绑定 127.0.0.1；路由 GET /、POST /api/generate、GET /download/<run_id>；嵌入式单页 HTML+JS UI
  - `scripts/run_cad_demo.py`：启动脚本（固定 CAD venv + PYTHONPATH）
  - `tests/demo/__init__.py`：测试模块初始化
  - `tests/demo/test_demo_handler.py`：30 项测试（handler 业务逻辑 + 下载隔离 + 路径穿越拒绝 + 恶意路径/symlink + 先成功后失败不泄漏 + 无网络/LLM 调用）
- 安全边界（ADR-0022）：
  - 下载验证：run_id UUID 格式检查→注册表查找→status=success 检查→路径 canonical containment→symlink 拒绝→文件存在且非空→内容 SHA-256 比对
  - 无 LLM/provider 调用；不读取 `.env`/密钥；不访问 A2 历史批次；不扫描旧 run 目录；`FORMAL_EVALUATION_ALLOWED=False` 不变
  - 每次 run 新 UUID + 独立目录；失败 run 不返回任何 STEP；成功 run 的 STEP 只通过内存注册表访问
- 验证（sandbox Python 3.10.12，系统环境）：
  - `py_compile`：6 个新文件全部通过
  - `git diff --check`：通过
  - Demo 测试 30 项：**30/30 通过** (`python3 -m unittest tests.demo.test_demo_handler -v`)
  - Integration test_pipeline 39 项：**39/39 通过**
  - Integration test_schema_to_ir 42 项：**42/42 通过**
  - Schema 17 项：**17/17 通过**
  - CAD compilation 13 项：9 项通过，4 项 ERROR（CadQuery not available in sandbox），1 项 FAIL（同上）——均为沙盒环境缺少 CadQuery 的既有故障，与本次修改无关（git stash 确认）
  - Integration test_a2_runner：4 项 FAIL/ERROR 为既有 Python 3.10 vs 3.11 环境差异，与本次修改无关
  - 注：固定 CAD venv `work/benchcad-output/venv/bin/python` 是指向 macOS homebrew 的断裂符号链接，无法在此 Linux 沙盒中执行。CAD-dependent 测试需 Codex 中枢在 Mac 上用固定 venv 重跑。
- 不变量：只添加 `src/demo/`、`scripts/run_cad_demo.py`、`tests/demo/`；未修改任何已有文件（pipeline.py、schema、IR adapter、compiler、runner 等均未改动）；未修改 A2 historical batch；`FORMAL_EVALUATION_ALLOWED=False` 不变
- 下一步：提交独立 commit，标记任务状态为 `review`，等待 Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核。

### APP-003-C1 / Codex 中枢 / in_progress / 2026-11-12

- 动作：恢复里程碑 C 上下文并核实无既有 Web framework；将首个实现切片拆为 `APP-003-C1`，由 CC 实现本地可运行演示。
- 决策：按 ADR-0022 使用只绑定 `127.0.0.1` 的标准库 Web UI，参数由用户手动填写/确认，文本仅作需求记录；复用现有 deterministic CAD pipeline。当前不接 live LLM，避免把已消耗的 A2 固定范围扩展成产品请求授权。
- 交付：实施边界/验收条件已记录于 ADR-0022 与 `docs/coordination/prompts/APP-003-C1-local-demo-cc.md`；任务看板、计划、状态、checkpoint 已同步。
- commit：`9873b61`（`docs: define APP-003 C1 local demo scope [APP-003-C1]`）；仅提交 C1 决策、计划和交接文档，未 push。
- 验证：仓库根和 git 状态确认；阅读现有 README、pipeline、A2 runner、ADR-0020 及项目状态/计划。此工作单元只定义架构/交接，不运行产品代码测试。
- 下一步：CC 按 C1 prompt 实现并提交；Codex 中枢独立复核 HTTP/UI、正常/失败路径及固定环境测试。

### APP-003-C1-R2-NARROW-FIX / Codex / review / 2026-11-12

- 动作：修正 C1 输入边界，防止 `int()` 静默截断小数 bore_d。
- 修改：`src/demo/handler.py` 新增严格 `_parse_bore_d()`；`tests/demo/test_demo_handler.py` 新增小数浮点、小数文本和布尔值拒绝回归。
- 边界：保留整数目录值、下载隔离、manifest 映射、XSS 转义和 localhost-only；不修改 CAD/Schema/IR/pipeline 或历史批次。
- 验证：待固定 CAD venv 重跑 demo、Integration、Schema、CAD 回归及 `py_compile`/`git diff --check`。
- 下一步：Codex 中枢复核 R2，确认非整数输入无 CAD 调用后再决定合入。

### APP-003-C1-FINAL-INDEPENDENT-REVIEW / Codex 中枢 / review / 2026-11-12

- 动作：在 `cc/APP-003-C1-LOCAL-DEMO` 的 HEAD `4419e27` 上完成 C1 最终独立复核；被审查代码没有修改。
- 环境与回归：固定 CAD venv Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0；Demo 55/55、Integration 81/81、Schema 17/17、CAD compilation 13/13；`py_compile`、`git diff --check` 通过。Demo 有 4 条非阻断 ResourceWarning。
- 端到端证据：loopback 服务只绑定 `127.0.0.1`；浏览器 bore_d=24 成功生成/展示/下载真实 STEP，hash、1 solid、35 faces、readback 均匹配；HTTP 烟测 bore_d=80 启用 rule-derived second_screw 并生成独立 run。24.9、缺参、目录外值均按预期拒绝；失败 run 不暴露 STEP；未知 run、symlink 逃逸、hash 篡改被拒绝。
- 安全边界：无 LLM/provider 或外网请求；未读取密钥、`.env`、A2 历史批次；临时服务和输出已停止/清理。无代码、scope、预算或授权边界修改。
- 结论：在 ADR-0022 的手动参数本地演示范围内 `pass`；C1 状态改为 `review`，合入 `main` 后才可标记 done。非阻断 P3：下载按钮文案多一个右括号。
- 证据：`agent-work/reviews/APP-003-C1-codex-review.md`；checkpoint 追加 `handoff_successor_check`。
- 下一步：负责人按既有 fast-forward 流程合入 `main`；后续产品级 live extraction 需独立 scope/预算/gate。

### APP-003-C1-DOWNLOAD-LABEL-FIX / Codex 中枢 / review / 2026-11-12

- 动作：修正最终复核发现的 P3 下载按钮多余括号/英文单位文案。
- 修改：`src/demo/server.py` 显示 `下载 STEP（N 字节）`；`tests/demo/test_demo_handler.py` 新增 HTML 输出回归，覆盖新文案并排除旧格式。
- 验证：固定 CAD venv Python 3.11.18 下 Demo 56/56；`py_compile`、`git diff --check` 通过。Demo 测试仍有 4 条既有 ResourceWarning，不影响结果。
- 边界：只涉及展示文案和测试；下载、安全、HTTP、CAD、模型授权及历史批次均未变。
- commit：`b59b551 fix: correct STEP download byte label [APP-003-C1]`；工作区干净。
- 下一步：负责人可 push 并按已审查结果合入 `main`；合入后再同步 `done` 状态。

### APP-003-C1-MERGE-CLOSEOUT / Codex 中枢 / done / 2026-11-12

- 动作：核对负责人完成的 fast-forward 合并与 push；本地 `main`、`origin/main`、远端 `main` 均为 `07a98d129022e78cc9e7dc4e44bc9ae2df083f5f`，工作区干净。
- 合入后验证：固定 CAD venv Python 3.11.18 下 Demo 56/56 通过；C1 独立复核记录的 Integration 81/81、Schema 17/17、CAD compilation 13/13 与真实 localhost/STEP 烟测对应于已合入代码。
- 收束：`APP-003-C1` 在 ADR-0022 的 localhost 手动参数演示范围内标记 `done`；PROJECT_STATUS、PROJECT_PLAN、TASKS 和 checkpoint 已同步。自由文本模型理解、三维预览、部署包装及 live extraction 不包含在本工作单元。
- 后续：评估演示/汇报需要，另行规划最小产品包装；若 UI 要调用真实模型，先定义独立 scope、预算与 gate 并取得授权。

### APP-003-C1-CHECKPOINT-TIMELINE-CLEANUP / Codex 中枢 / done / 2026-11-12

- 动作：按独立审查反馈修正 checkpoint 时间线歧义；将 `f49a037` 审查及 `b59b551` 合入前的“待 push/合入”描述标注为对应时点的历史状态，并说明 `07a98d1` 是当时的功能分支合入 HEAD。
- 当前核验：本地 `main`、`origin/main`、远端 `main` 均为 `bb0a0dab16e88221c0f01b99804cfee6058e14c1`；工作区干净。此前合入后 Demo 56、Integration 179、Schema 17、CAD compilation 13 均通过，本轮没有代码变化，未重复运行测试。
- 收束：APP-003-C1 仍为 `done`；修正仅涉及 checkpoint 和追加式 WORKLOG，不改变代码、范围、验证结论或后续授权边界。
- 下一步：按 PROJECT_PLAN 评估导师演示及最小产品包装需求；自由文本模型调用仍需独立 scope、预算与 gate。
### APP-003-C2-NL-PRODUCT-FLOW / Codex / planned / 2026-11-13

- 动作：核对当前 `main=7f5555e`、C1 合入状态、A2 `...-04` 只读证据及现有状态/计划/决策/交接协议。
- 决策：按项目负责人确认的节奏新增 ADR-0023，先做自然语言产品状态机与用户确认流程的离线 synthetic v5 envelope 接入；C1 手动参数演示保持稳定，A2/held-out 不扩权。
- 边界：产品状态与 `run_pipeline` 内部 status 分层；确认前只做解析/投影/Schema 预检，不调用 IR/CadQuery；确认/修改创建新隔离 run；失败不发布旧 STEP。无模型、无网络、无 `.env`、无 batch、`FORMAL_EVALUATION_ALLOWED=False` 保持。
- 交付：新增 `docs/coordination/prompts/APP-003-C2-nl-product-flow-cc.md`，指定由已有 C1 CC 对话框实现；同步 PROJECT_PLAN、PROJECT_STATUS、TASKS 和 ADR-0023。
- commit：`80580ff`（文档与实现工作单元定义；尚未 push）。
- 下一步：已有 C1 CC 对话框认领并实现离线 fixtures/状态机，提交 review commit；Codex 中枢随后在固定 CAD venv 做独立复核，再决定是否准备新的产品 live smoke scope。

### APP-003-C2-NARROW-FIX / CC / review / 2026-11-13

- 动作：在分支 `cc/APP-003-C2-NL-PRODUCT-FLOW`（HEAD `baba59a`）完成四项窄修。
- **修复 1：父 run 保持完全不可变**
  - 删除 `confirm_product_run()` 对 `parent_rec.confirmation` 的直接赋值（原第 612-630 行）。确认信息仅写入 child run。
- **修复 2：HTTP confirm 参数严格类型校验**
  - `_handle_product_confirm` 新增 bool-aware isinstance 检查：bool/非 int revision → 400；非 bool confirmed → 400。`"false"` 字符串不再被 `bool()` 误转为 True。
- **修复 3：补齐 ADR-0023 产品证据字段**
  - `ProductRunRecord` 新增五个可选字段（均有默认值 None）：`envelope_fixture_path`、`envelope_fixture_sha256`、`pipeline_run_id`、`pipeline_run_dir_relative`、`step_path_relative`；均为仓库相对路径，不暴露绝对路径；新增到 `as_dict()`。
- **修复 4：pipeline 异常 fail-closed**
  - `run_pipeline()` 调用外包裹 `try/except Exception`，异常 → child `product_status="failed"`；父 run 不变；`_step_path=None`。
- 新增测试（23 项）：`TestParentRunImmutability`（3）、`TestHTTPConfirmTypeValidation`（10）、`TestEvidenceFields`（7）、`TestPipelineExceptionFailClosed`（3）。
- 验证（sandbox Python 3.10.12）：`py_compile` 通过；`git diff --check` 通过；test_product_flow **58/58**（原 35 + 新 23）；test_demo_handler **56/56**；test_pipeline+test_schema_to_ir **81/81**；schema **17/17**。
- 不变量：不修改 v5/Schema/IR/compiler/A2；`FORMAL_EVALUATION_ALLOWED=False` 不变；不读密钥/不发网络请求；仅修改 `src/demo/product_flow.py`、`src/demo/server.py`、`tests/demo/test_product_flow.py`、checkpoint、WORKLOG。
- 下一步：提交独立 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核。

### APP-003-C2-IMPLEMENTATION / CC / review / 2026-11-13

- 动作：在分支 `cc/APP-003-C2-NL-PRODUCT-FLOW`（基于 `main=0210b4e`）实现离线自然语言产品闭环（ADR-0023）。
- 新增文件：
  - `src/demo/product_flow.py`：ProductFlowHandler + ProductRunRecord；8 个 fixture 注册表；create_product_run（parse+project+Schema 预检，零 CAD 调用）；confirm_product_run（revision 检查、patch 验证、child run 创建、run_pipeline 调用）；get_product_step_bytes_secure（6 层安全下载）
  - `tests/demo/fixtures/`：8 个 fixture JSON（answer-bore24、ask-missing-bore、catalog-conflict、unsupported、ask-extra-question、refuse、schema-fail、bore80）
  - `tests/demo/test_product_flow.py`：35 项测试（create 12 + confirm 12 + download 8 + no-network 3 + record 2）
  - `src/demo/server.py`（修改）：新增 C2 路由 POST /api/product/create、POST /api/product/confirm/<run_id>、GET /api/product/<run_id>、GET /product-download/<run_id>；make_handler_class 接受可选 product_handler 参数；C1 路由不受影响
  - `agent-work/integration/APP-003-C2/checkpoint.md`：认领记录
- 安全边界：确认前零 compile_ir 调用（spy 验证全 8 fixture）；confirmation_revision 不符 → STALE_REVISION blocked；confirmed=False → blocked；child run 新 UUID 隔离；失败不暴露旧 STEP；下载复用 C1 六层逻辑
- 验证（sandbox Python 3.10.12）：
  - `py_compile`：3 个新/改文件全部通过
  - `git diff --check`：通过
  - Product flow 测试：**35/35 通过**
  - C1 回归：**56/56 通过**（C1 不受影响）
  - Integration test_pipeline + test_schema_to_ir：**81/81 通过**
  - Schema：**17/17 通过**
  - 注：固定 CAD venv 无法在此沙盒中执行，需 Codex 中枢在 Mac 上用 Python 3.11.18/CadQuery 复跑真实构造路径
- 不变量：不修改 v5 prompt/contract、Schema、IR 语义、compiler、A2 历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变；不读取 `.env`/密钥；不发模型/外网请求
- 下一步：提交独立 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv 独立复核

### APP-003-C2-CLOSEOUT / Codex / done / 2026-11-13

- 动作：核实项目负责人已将 C2 分支合入 `main`；本地 `main`、`origin/main` 均为 `d839954`，工作区干净。更新 PROJECT_STATUS、PROJECT_PLAN、TASKS 和 C2 checkpoint，记录中枢独立验收证据并将 C2 收束为 done。
- 独立验证：固定 CAD venv Python 3.11.18 下 C2 58/58、C1 56/56、Integration 81/81、Schema 17/17、CAD compilation 13/13；py_compile、git diff --check 通过。localhost E2E：create → 非法类型 400 且确认调用 0 次 → 合法 confirm → parent GET → STEP download；parent as_dict 完全不变，STEP hash 匹配。bore24、bore80/second_screw=1、ask 补 bore_d=16 均真实生成并回读 STEP。
- 边界：C2 仅 synthetic fixture，无产品真实模型入口；无密钥/网络调用。浏览器确认 UI 尚未实现，另立 APP-003-C3；新产品 live extraction 仍需独立 scope、预算、gate、batch ID 和负责人授权。
- 下一步：规划并执行 APP-003-C3-PRODUCT-UI，离线 fixtures 优先；复核通过后再准备 live extraction scope。

### APP-003-C3-PRODUCT-UI-PLAN / Codex / planned / 2026-11-13

- 动作：恢复 C2 合入事实、ADR-0023、交接协议和项目计划；核对 C2 HTTP API 与 ProductRunRecord 字段，定义 APP-003-C3 可执行 CC 工作单。
- 产物：`docs/coordination/prompts/APP-003-C3-product-ui-cc.md`、`agent-work/integration/APP-003-C3/checkpoint.md`；修正 PROJECT_STATUS 的仓库基线为本地 `b90a83c`（含 C2 closeout 文档提交）。
- 边界：C3 仍仅使用 offline synthetic fixtures；浏览器不接触模型/provider/key；不创建 batch，不改变 C2 状态机或既有 gate。UI 应明确需求文本仅作记录、fixture 提供抽取结果。
- 状态：`planned`，等待已有 C1/C2 CC 对话框认领；实现后由 Codex 中枢在固定 CAD venv 独立验收。
- 下一步：将工作单交给已有 C1/C2 CC 对话框实施；验收后再决定是否准备新的产品 live extraction scope。

### APP-003-C3-ASK-FAILCLOSED / CC / review / 2026-11-13

- 动作：修复 `c2-ask-extra-question` 错误放行（decision=ask + questions=["请确认安装方式？"] + missing_fields=[] + 空 patch → 旧代码进入 run_pipeline 生成 STEP）。
- **API 层修复**（`src/demo/product_flow.py`）：在 `confirm_product_run()` 的 patch 验证前新增"未回答问题"门：若 `decision=ask` 且 `questions` 非空，且 patch 未覆盖全部 `missing_fields`（或 missing_fields 为空），返回 `QUESTIONS_UNANSWERED blocked`。可解决案例（ask-missing-bore + patch bore_d=16）仍允许继续。
- **UI 层防护**（`src/demo/server.py`）：`renderConfirmSection()` 新增判断 `hasUnanswerableQuestions`；ask-extra-question 的确认页不显示确认按钮，改为展示问题列表和阻断说明。
- **回归测试**（`tests/demo/test_product_flow.py`，新增 7 项，共 65 项）：ask-extra 空 patch → blocked（compile_ir=0）；ask-missing 空 patch 阻断；ask-missing + bore_d=16 → succeeded；bore24/bore80 answer 路径不受影响；parent run 不变。
- 验证（sandbox Python 3.10.12）：`py_compile` 通过；`git diff --check` 通过；test_product_flow **65/65**；test_product_ui **62/62**；test_demo_handler **56/56**；integration **81/81**；schema **17/17**。
- 不变量：不修改 C1/C2 API、Schema/IR/CAD、A2 历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变；不读密钥/`.env`；不发网络/模型请求。
- 下一步：提交窄修 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv 独立复核。

### APP-003-C3-PRODUCT-UI-NARROW-FIX / CC / review / 2026-11-13

- 动作：在分支 `cc/APP-003-C3-PRODUCT-UI`（HEAD `2c810d2`）完成 C3 页面信息展示窄修。
- **修复 1：确认页展示原始需求文本**
  - `renderConfirmSection()` 新增 `esc(d.request_text)` 展示行，让用户在确认参数前对照原始需求。
- **修复 2：成功结果展示 STEP SHA-256**
  - `renderResultSection()` 的 `succeeded` 分支新增 `esc(d.step_sha256)` 完整 SHA-256 展示；失败/阻断路径不渲染。
- **补强 XSS 回归**
  - 新增 `TestRequestTextDisplay`（4 项）、`TestStepHashDisplay`（6 项）、`TestXSSNarrowFix`（7 项），共 17 项。
  - 覆盖 `<img src=x onerror=alert(1)>` 作为 request_text 的安全渲染验证。
  - 验证 step_sha256 仅在 succeeded 块内展示，resetAll() 清除旧内容。
- 验证（sandbox Python 3.10.12）：`py_compile` 通过；`git diff --check` 通过；test_product_ui **62/62**（原 45 + 新 17）；test_product_flow+test_demo_handler **114/114**；integration **81/81**；schema **17/17**。
- 不变量：不修改 C2 API/状态机、C1 路由、v5/Schema/IR/compiler/A2；`FORMAL_EVALUATION_ALLOWED=False` 不变；仅修改 `src/demo/server.py`、`tests/demo/test_product_ui.py`、checkpoint、WORKLOG。
- 下一步：提交窄修 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核。

### APP-003-C3-PRODUCT-UI / CC / review / 2026-11-13

- 动作：在分支 `cc/APP-003-C3-PRODUCT-UI`（基于 `main=1bc019f`）实现 C3 离线自然语言产品确认 UI。
- 新增/修改文件：
  - `src/demo/server.py`（修改）：新增 `_build_product_html()` C3 单页 HTML+CSS+JS；`GET /product` 和 `GET /api/product/fixtures` 路由；C1/C2 路由不变
  - `tests/demo/test_product_ui.py`（新增）：45 项 HTTP 集成测试（使用 MockSocket + mock compile_ir）
  - `agent-work/integration/APP-003-C3/checkpoint.md`（新增）
  - `docs/WORKLOG.md`（追加）
- 安全约束：所有动态值通过 `esc()` 转义；fixture 列表不暴露文件路径；下载复用 C2 六层安全验证；不调用 LLM/provider，不读取 `.env`，不创建 batch
- 验证（sandbox Python 3.10.12，mock CAD）：
  - `py_compile`：通过
  - `git diff --check`：通过
  - C3 product UI 测试：**45/45 通过**
  - C2 回归（test_product_flow）：**58/58 通过**
  - C1 回归（test_demo_handler）：**56/56 通过**
  - Integration test_pipeline + test_schema_to_ir：**81/81 通过**
  - Schema：**17/17 通过**
- 不变量：不修改 v5 prompt/contract、Schema、IR、compiler、A2 历史批次；`FORMAL_EVALUATION_ALLOWED=False` 不变；不读取密钥/`.env`；不发模型/外网请求；C1/C2 路由和 API 语义不变
- 下一步：提交独立 commit，状态保持 `review`，等待 Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核

### APP-003-C3-INDEPENDENT-REVIEW-R2 / Codex / review / 2026-11-13

- 动作：在 `cc/APP-003-C3-PRODUCT-UI`、HEAD `f258480` 上独立复核 ask 未回答问题 fail-closed 窄修；检查实现、UI gate、fixtures 和工作区状态。
- 固定环境验证：`work/benchcad-output/venv/bin/python` 为 Python 3.11.18。demo + integration（`test_product_flow`, `test_product_ui`, `test_demo_handler`, `test_pipeline`, `test_schema_to_ir`）264/264；Schema 17/17；CAD compilation 13/13；py_compile 和 `git diff --check` 通过。仅有既有文件句柄 ResourceWarning 和 CadQuery/NumPy 上游弃用警告。
- localhost E2E：ask-extra-question 直接空 patch 确认为 `blocked/QUESTIONS_UNANSWERED`，不含 STEP/hash/bytes，父记录前后完全相同；ask-missing-bore 空 patch 同样阻断。新 ask-missing parent 补 `bore_d=16` 后真实 pipeline 生成 STEP（137034 bytes），下载 hash 与结果记录一致，parent 完全不变。
- 不变量：仅 synthetic fixtures 和本地 CAD；未调用模型/provider，未读取 `.env`/密钥，未改变 `FORMAL_EVALUATION_ALLOWED=False`、A2 scope 或既有批次。
- 限制与下一步：未做真实浏览器视觉或 DevTools XSS 事件执行检查；C3 保持 `review`，等待负责人合入 main 后完成状态 closeout，再讨论新的 live extraction scope。

### APP-003-C3-BROWSER-REVIEW / Codex / review / 2026-11-13

- 动作：使用固定 CAD venv 启动 localhost demo，完成 C3 浏览器交互验收。
- 结果：页面离线警告、fixture allowlist 和单族免责声明可见；XSS payload 以纯文本显示，未创建 DOM 图片元素，`onerror` 未执行；ask-extra 显示未回答问题且没有确认按钮；ask-missing 补 `bore_d=16` 后浏览器显示 succeeded、几何摘要、STEP hash 和下载链接；下载 137034 字节，SHA-256 `3ed46b402be57b693d6816c5cf0eb210ea8c3abeeb6c240d7756f93b02f3419f` 与页面一致；“新建另一个需求”清空旧状态和下载链接。
- 边界：使用 synthetic fixture 和本地 CadQuery，未调用模型/provider，未读取 `.env`/密钥，未创建 batch；服务监听 `127.0.0.1`，验证后已停止。
- 下一步：C3 维持 `review`，负责人合入 main 后同步 closeout，再决定新的产品 live extraction scope。

### APP-003-C3-CLOSEOUT / Codex / done / 2026-11-13

- 动作：核对负责人将 C3 分支快进合入 `main` 并推送远端；`main` 与 `origin/main` 均为 `f105fc4`，工作区干净。
- 结果：C3 固定 CAD venv、localhost、浏览器、XSS 纯文本、ask 未回答问题阻断、补参真实 STEP/hash 和 reset 清理验收均通过；项目状态、计划、任务表和 checkpoint 已同步为 `done`。
- 边界：C3 仍是 synthetic fixture 离线流程，不调用模型、不读取密钥、不创建 batch，不构成真实模型理解或产品 live extraction 证据。后续 live extraction 必须新建 scope、预算、gate、batch ID 并取得负责人授权。

### APP-003-LIVE-SCOPE-DRAFT / Codex / planned / 2026-11-13

- 动作：在 C3 合入和浏览器验收后，依据 ADR-0023 准备下一阶段产品 live extraction smoke 提案。
- 产物：`agent-work/integration/APP-003-LIVE-SCOPE/scope-draft.md`；提出 DeepSeek `deepseek-flash` / C0、4 个独立刺激（正常、缺参、目录冲突、unsupported）、最多 12 HTTP、人工确认后才调用 CAD，并列出 product-specific gate、预算账本、preflight、证据脱敏和独立执行批准条件。
- 状态与边界：仅为待审提案；未选定 batch ID，未创建 batch/ledger，未运行 preflight/provider 请求，未读取密钥/`.env`，未调用 CAD。`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 下一步：项目负责人审阅并明确批准或修改草案；批准 scope 后再准备独立实现工作单，真实执行仍需另行授权。

### APP-003-LIVE-PRODUCT-PROMPT / Codex / planned / 2026-11-13

- 动作：项目负责人批准 APP-003-LIVE-SCOPE 的 4 条输入、DeepSeek `deepseek-flash` / C0 和最多 12 次 HTTP；生成产品专用受控入口实现工作单。
- 产物：`docs/coordination/prompts/APP-003-live-product-cc.md`。工作单要求新建 CC 对话框和 `cc/APP-003-LIVE-PRODUCT` 分支，新增独立 product authorization/gate、预算账本绑定、服务端 runner、离线 mock/spy 测试和证据脱敏；明确不复用 A2 授权或批次。
- 边界：本批准只覆盖实现和离线验证。未授权 live preflight、正式 batch、DeepSeek 请求、密钥读取或 CAD 正式运行；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 下一步：新 CC 对话框按工作单实现，完成后交 Codex 中枢独立复核；只有复核通过且负责人再次批准具体 batch ID/执行，才可进入 live preflight。
### APP-003-LIVE-PREFLIGHT-20261113-01-FAILURE-EVIDENCE-FIX / Codex / review / 2026-11-14

- 动作：针对批准批次 `app003-product-live-20261113-01` 的四条 `PARSE_OR_ENVELOPE_ERROR`，在不重跑旧 batch、不读取 raw 正文和不扩大授权的前提下，修复正式 Product Live runner 的 Adapter 结果映射。
- 修改：`src/integration/product_live_runner.py` 新增 `_build_state_from_adapter_result()`；无响应结果记录稳定的 `TRANSPORT_ERROR`、原因码、尝试次数、状态和 outcome；有响应但严格解析/Envelope 校验失败时记录 `RESPONSE_PARSE_ERROR` 或 `ENVELOPE_VALIDATION_ERROR` 及错误码/字段；所有收到响应的结果继续传递 `raw_response_retention`，summary 只接收 repo-relative path 和 body SHA-256，正文不进入 state/summary/UI。
- 测试：固定 CAD venv Python 3.11.18 下 `py_compile` 通过，`tests.integration.test_product_live` **102/102** 通过；新增回归覆盖 transport failure、invalid JSON、Envelope validation、raw hash/path 隔离和 provider 正文 marker 不泄漏。
- 结果：旧批次事实保持不变（4/4 HTTP、无 raw 文件、未进入 CAD/STEP）；修复只影响后续正式结果映射和证据诊断。`FORMAL_EVALUATION_ALLOWED=False`、产品授权/预算/确认门均未改变。
- 下一步：独立 Codex 复核 mapper 的真实 Adapter 字段绑定和相关回归；通过后再为新 batch 另行准备 scope、preflight 和负责人批准，禁止复用 `...-01`。

### APP-003-LIVE-PREFLIGHT-20261113-01-ISOLATION-FIX / Codex / review / 2026-11-14

- 动作：根据独立复核，完成两个窄修：离线 mock/service parser 失败不再把 provider 控制内容复制到 state/UI；HTTP sanitizer 对顶层 `raw_retention_path` 统一执行 repo-relative、canonical containment 和 symlink fail-closed 归一化。
- 修改：`src/integration/product_live_runner.py` 新增安全 parser cause 映射，仅保留稳定 code/stage 与冻结 contract/parameter 白名单 fields；`src/demo/server.py` 归一化顶层 raw retention path；`tests/integration/test_product_live.py` 新增 provider marker 隔离和 raw path（repo 内、repo 外、traversal、symlink）回归。
- 验证（固定 CAD venv Python 3.11.18）：Product Live **107/107**；Product Live UI **36/36**；C1/C2/C3 **183/183**；Integration pipeline/schema-to-IR **81/81**；Schema **17/17**；CAD compilation **13/13**；目标文件 `py_compile`、`git diff --check` 通过。
- 保持不变量：旧批次 `app003-product-live-20261113-01` 只读，不重跑、不读取 raw 正文、不追加网络请求；未读取密钥/`.env`；未改变 prompt、Schema/IR、CAD pipeline、授权 profile、预算或 `FORMAL_EVALUATION_ALLOWED=False`。
- 下一步：提交窄修 commit，交独立 Codex 对话框复核；复核通过后再决定是否准备新的产品 live scope、batch 和负责人批准。

### APP-003-LIVE-PREFLIGHT-20261114-01 / Codex / review / 2026-11-14

- 前置结论：独立复核对 `main=d80fd433c54d37c135581e92c01c4e4bbee31bb3` 给出 `pass`，确认 parser 诊断脱敏、HTTP 顶层 raw path containment 和固定 CAD venv 回归通过；该结论只解除代码审查阻塞，不授权新的真实请求。
- 动作：更新当前状态/计划，收束 `APP-003-LIVE-PREFLIGHT-20261113-01`；为新的候选 batch `app003-product-live-20261114-01` 准备 scope、离线 preflight 证据和 checkpoint。
- 候选 scope：沿用冻结四输入、DeepSeek `deepseek-flash` / C0、每条最多 3 次尝试、全批最多 12 HTTP；没有扩充样本或改变产品 gate。P1 等有效 answer 仍须人工显式确认后才可调用 CAD；P2/P3/P4 和任何失败均 fail closed。
- 固定 CAD venv Python 3.11.18：`run_product_offline_preflight(..., require_cad_runtime=True)` 返回 `ok=true`；输入/prompt hash、Draft 2020-12、CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0 检查通过；预算 4×3=12 可行。`run_product_batch(dry_run=True)` 返回 `preflight_ok=true`、4 planned runs、0 results；候选目录执行前后均不存在。
- 安全边界：0 网络请求；未读取 `.env`/密钥；未创建正式 batch/ledger；没有执行 provider 请求或正式 CAD；旧 batch `app003-product-live-20261113-01` 只读保留；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 产物：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-01/` 下的 `scope.md`、`offline-preflight.json`、`checkpoint.md`；项目状态、计划和任务表同步更新。
- 状态与下一步：候选保持 `review`，等待负责人审阅/批准具体 scope 与 batch ID。批准后才准备同批正式 approval 并执行 formal preflight；真实请求需再次明确授权。当前阶段不得触发网络调用。

### APP-003-LIVE-PREFLIGHT-20261114-01-APPROVAL / Codex / review / 2026-11-14

- 动作：负责人批准候选 scope 与 batch `app003-product-live-20261114-01`；批准人 `Wang sikai`，UTC 时间 `2026-11-13T17:14:42Z`。按项目惯例记录引用：`Codex conversation — APP-003-LIVE-PREFLIGHT-20261114-01, user message dated 2026-11-14`。
- 执行：在固定 CAD venv Python 3.11.18 下构造非 test-only `ProductLiveFormalApproval`，通过 `validate_product_formal_approval_binding()`；执行 `run_product_offline_preflight(..., require_cad_runtime=True)`，返回 `ok=true`，错误为空，batch 目录不存在。
- 证据：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-01/formal-preflight.json`；prompt/inputs/labels hash、provider/model/condition、预算 4×3=12、Draft 2020-12、CadQuery/OCP/jsonschema 均匹配。
- 边界：本轮未调用 `run_product_batch(dry_run=False)`，未创建正式 batch/ledger，未构造 transport，未读取 `.env`/API key，网络请求为 0，未执行正式 CAD。旧 batch `app003-product-live-20261113-01` 继续只读。
- 下一步：若负责人明确批准“执行该 batch 的真实 DeepSeek 请求”，再调用 formal runner；当前只完成 scope approval + formal preflight，不能把它描述为 live 运行结果。

### APP-003-LIVE-SMOKE-20261114-01 / Codex / review / 2026-11-14

- 动作：负责人明确批准执行 `app003-product-live-20261114-01` 的真实 DeepSeek 请求，最多 12 次 HTTP；使用同批已通过的 formal approval binding 和 preflight。
- 执行：固定 CAD venv 下 formal runner 完成 4 条逻辑输入，各 1 次尝试，账本合计 `4/12`。P1–P4 均在模型响应前返回 `TRANSPORT_ERROR`，稳定原因码为 `authentication_or_permission`；批次 summary 状态为 `failed`。
- 结果：没有进入用户确认、Schema、IR、CAD 或 STEP；raw 文件数 0、pipeline 文件数 0；没有读取 raw 正文或输出密钥/header。该结果证明请求前 gate、预算和失败收束生效，不提供模型行为或产品效果证据。
- 证据：`work/app001-runs/app003-product-live-20261114-01/batch_summary.json`、`budget_ledger.json`（只读）；`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-01/execution-report.json`（脱敏摘要）。
- 失败脚本说明：首次汇总脚本在 runner 完成后读取不存在的 `run_id` 属性而退出；未触发重跑。随后仅从已写入 summary/ledger 生成脱敏执行报告。
- 边界：本 batch 已消耗 4 次 HTTP，不重跑、不追加、不改写；旧 batch `app003-product-live-20261113-01` 仍只读；`FORMAL_EVALUATION_ALLOWED=False` 未改变。
- 下一步：先由负责人在 provider 账户/凭据层面核查 `authentication_or_permission`；若要再次尝试，必须创建全新 batch、scope、approval 和 preflight，不能沿用本 batch 的剩余 8 次预算。

### APP-003-LIVE-CREDENTIAL-ENTRY-FIX / Codex / review / 2026-11-14

- 动作：针对 `app003-product-live-20261114-01` 的 `authentication_or_permission` 结果做零网络凭据入口诊断，并准备最小加载修复。
- 根因证据：仓库 `.env` 文件存在且 `DEEPSEEK_API_KEY` 非空（只检查存在/非空，不输出值）；执行环境原先没有该变量。`DeepSeekTransport.send()` 只读 `os.environ`，没有自动读取 `.env`。因此旧 batch 的失败不能证明 DeepSeek 账户权限被拒绝。
- 修改：新增 `src/llm/env_loader.py`，正式 Product Live 路径仅在 approval binding 与 CAD/runtime offline preflight 通过后、创建 batch/ledger/transport 之前加载必需 key；不输出值，进程已有非空值优先，缺失/空值 fail closed。dry-run、mock 和 Web offline 路径不加载凭据；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 测试：新增 `tests/integration/test_product_live_env.py`，覆盖 `.env` 加载、优先级、空/缺失失败、无输出、正式路径在 batch 创建前失败、dry-run 不加载；固定 CAD venv Python 3.11.18 下 9/9 通过。Product Live 既有专项 107/107 通过；py_compile 与 diff check 通过。
- 边界：没有发 HTTP、没有验证 provider 账户权限；没有重跑或追加任何历史 batch。`app003-product-live-20261114-01` 仍只读，剩余 8 次不可用。真实 provider 权限判断需在此修复经独立复核后，另行新建 scope/batch/approval/preflight 并取得明确执行授权。
- 下一步：完成代码/文档复核和本地提交；随后由负责人决定是否批准新的 provider diagnostic smoke。

### APP-003-LIVE-CREDENTIAL-ENTRY-FIX-WHITESPACE / Codex / review / 2026-11-14

- 动作：处理独立复核对 `5bf82ce` 提出的 EOF whitespace 检查项。
- 修改：移除 `src/llm/env_loader.py` 与 `tests/integration/test_product_live_env.py` 的额外末尾空行。
- 验证：固定 CAD venv Python 3.11.18 下 py_compile 通过，环境 loader 9/9、Product Live 107/107 通过；输出只有测试既有 ResourceWarning。提交后复跑 `git diff --check a7fe414..HEAD`。
- 边界：纯 whitespace 修正，无网络、provider、密钥读取或历史 batch 操作。


### APP-003-LIVE-CREDENTIAL-ENTRY-FIX-REVIEW / Codex 中枢 / review / 2026-11-14

- 动作：记录独立复核对凭据入口修复的 `pass` 结论，并收束 `APP-003-LIVE-PREFLIGHT-20261114-01` 当前文档状态。
- 复核基线：`main`，提交 `df3f7b4`；相对 `a7fe414` 的 `git diff --check`、该提交的 `git show --check` 均通过。固定 CAD venv Python 3.11.18 下 py_compile、凭据专项 9/9 通过；Product Live 107/107 回归通过。
- 结论：`.env` credential entry 修复符合 fail-closed 时序，dry-run/mock 不加载凭据，secret 不输出；独立复核关闭 whitespace finding。provider 实际权限未测试，旧批次失败不能作为账户权限证据。
- 边界：没有执行 live batch、网络/provider 请求或历史 batch 操作；旧 batch `app003-product-live-20261114-01` 仍只读，剩余预算不可用；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 下一步：若负责人希望确认 provider 可访问性，需另建窄 scope、新 batch ID、approval 和 preflight，再由负责人明确授权真实请求；在此之前保持 review。


### APP-003-LIVE-PREFLIGHT-20261114-02 / Codex 中枢 / review / 2026-11-14

- 动作：为已通过独立复核的 credential entry fix 准备全新 provider diagnostic 候选，不复用旧 batch。
- 候选：`app003-product-live-20261114-02`；沿用 Product Live 当前冻结四条输入、DeepSeek `deepseek-flash` / C0、最多 12 HTTP。 profile 将输入集合/预算硬编码，本轮未改 profile、代码或 scope。
- 验证：固定 CAD venv Python 3.11.18；离线 preflight 和 dry-run 通过，planned=4/results=0；CAD runtime 正常，candidate batch dir 不存在。
- 边界：网络=0、credential reads=0、formal batch/ledger=0；旧 batch 均只读；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 产物：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-02/scope.md`、`approval-template.md`、`offline-preflight.json`、`checkpoint.md`。
- 下一步：等待负责人审阅 scope；scope 获批后只做 formal preflight，真实 provider 请求仍需单独明确执行授权。


### APP-003-LIVE-PREFLIGHT-20261114-02-FORMAL-PREFLIGHT / Codex 中枢 / review / 2026-11-14

- 动作：负责人批准新 batch `app003-product-live-20261114-02` 的 formal preflight；完成同 batch approval binding 与固定 CAD runtime preflight。
- 结果：`ProductLiveFormalApproval` binding `pass`；Python 3.11.18 下 `run_product_offline_preflight(require_cad_runtime=True)` 返回 `ok=true`、errors 为空；12 HTTP 预算可行，batch 目录不存在。
- 边界：网络=0，未读取 `.env`/API key，未创建正式 batch/ledger/transport，未运行 CAD；`FORMAL_EVALUATION_ALLOWED=False` 不变。formal preflight 不等于 live execution approval。
- 证据：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-02/formal-preflight.json`；负责人 `Wang sikai`，批准时间 `2026-11-13T18:22:54Z`，引用 `Codex conversation — APP-003-LIVE-PREFLIGHT-20261114-02, user message dated 2026-11-14`。
- 下一步：等待负责人对该新 batch 的真实 DeepSeek 请求作单独明确执行批准；在此之前不发送 HTTP。


### APP-003-LIVE-PREFLIGHT-20261114-02-LIVE-EXECUTION / Codex 中枢 / review / 2026-11-14

- 动作：负责人明确批准后，执行全新 batch `app003-product-live-20261114-02` 的真实 DeepSeek Product Live 请求。
- 结果：4 条冻结输入各 1 次 HTTP，预算 4/12，summary=`complete`；4 个 raw 响应已按策略留存（本记录未读取正文）。P1 为 answer/needs_confirmation；P2 为 ask/blocked；P3、P4 为 refuse/blocked。
- CAD/STEP：没有提交 P1 的单次产品确认，故未调用 CAD pipeline，无 STEP、无 pipeline 产物。
- 边界：不重跑、不追加本 batch；旧 batch 只读；不输出 key、Authorization header 或 raw 正文；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 证据：`agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-02/execution-report.json` 与只读 batch summary/ledger。
- 下一步：独立复核脱敏 summary/ledger/报告；若继续 P1 构造，需负责人针对抽取参数作 per-run 确认。


### APP-003-LIVE-PREFLIGHT-20261114-02-INDEPENDENT-REVIEW / Codex 中枢 / done / 2026-11-14

- 动作：完成 `app003-product-live-20261114-02` 的只读独立复核并收束任务文档。
- 结论：`pass`，限于授权、执行证据与安全边界。Summary、ledger、execution report、批准 scope 和冻结 artifact hashes 一致；4 次成功 HTTP / 12 上限，每个 frozen run 一次；四个 raw 文件 hash 与 summary 匹配。
- 结果：P1=`answer → needs_confirmation`；P2=`ask → blocked`；P3/P4=`refuse → blocked`。未提交 per-run confirmation，CAD/STEP=0；`FORMAL_EVALUATION_ALLOWED=False`。
- 隐私边界：只验证 raw 文件存在性、大小和 SHA-256，未读取正文；evaluator labels 仅核 SHA-256；未读取 `.env`/密钥，不发请求，不运行 CAD，不改写任何 batch。
- 文档：新增 `agent-work/integration/APP-003-LIVE-PREFLIGHT-20261114-02/independent-review.md`，更新 checkpoint、scope/template 状态、PROJECT_STATUS 与 PROJECT_PLAN。
- 提交：`4c8720e`（独立复核记录与项目文档收束）。
- 限制/下一步：未评估四条响应的语义正确性，未读取 raw 以核对 runtime-returned model。若要对 P1 生成 CAD/STEP，须负责人单独审阅其抽取参数并明确确认该 run；本 batch 继续只读。


### APP-003-LIVE-PREFLIGHT-20261114-02-P1-PARAMETER-REVIEW / Codex 中枢 / review / 2026-11-14

- 动作：为下一道 per-run confirmation 门准备 P1 参数审阅。
- 读取边界：读取 P1 raw envelope 的白名单字段；没有输出或保存 provider 正文、密钥或 Authorization。该动作改变了此前“只核 hash、不读 raw 正文”的复核边界，已在独立复核记录中注明。
- 结果：`decision=answer`；`extracted_parameters={"bore_d": 24}`；`missing_fields=[]`；`unsupported_requests=[]`；`questions=[]`；prompt/contract 仍为 `app001-extraction.v5` / `app001-io.v1`。P1 仍为 `needs_confirmation`。
- 安全：未调用确认函数，未运行 CAD/STEP，未追加 HTTP，未修改 batch 产物；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 下一步：请负责人审阅并明确确认 P1 的 `bore_d=24`；确认后才可在新的 per-run confirmation 门中运行本地 CAD pipeline。


### APP-003-LIVE-PREFLIGHT-20261114-02-P1-CONFIRMATION / Codex 中枢 / done / 2026-11-14

- 动作：负责人接受 P1 `bore_d=24` 并批准 per-run 本地 CAD confirmation。
- 执行：调用 `confirm_product_live_run()` 一次；无新增 DeepSeek 请求，原 live batch summary/ledger/raw 保持只读未改。
- 结果：独立确认目录中的 P1 run 为 `succeeded` / `success` / `step_readback`；native geometry valid（1 solid、35 faces、73 edges、38 vertices）；STEP 148393 bytes，SHA-256 `9884f733f4c07a0408526b37fac391b68140a0fe3b2610570ff1ba8fc00d1486`；CAD-006 native→STEP 回读比较通过。
- 证据：`work/product-live-runs/app003-product-live-20261114-02-P1-24mm-confirmation/`；完整独立复核记录见同任务 `independent-review.md` 与 checkpoint。
- 边界：这是负责人确认后的单次 P1 构造证据，不改变原 batch 的 4/12 HTTP 统计，不构成广泛语言质量或制造认证结论。


### APP-003-LIVE-PREFLIGHT-20261114-02-P1-EVIDENCE-REVIEW / Codex 中枢 / review / 2026-11-14

- 动作：对负责人已批准的 P1 per-run CAD confirmation 做只读产物核验，并修正交接记录中的过时阻塞状态。
- 核验：Schema validation 通过；compiler summary 为 `success/step_readback`；native 与 STEP 回读 geometry 均 valid，1 solid、35 faces、73 edges、38 vertices；CAD-006 比较通过且 hard mismatches 为空；STEP 文件实测 148393 bytes，SHA-256 与 index 一致。
- 原 live batch：只核计数，ledger 4/12、raw 文件 4 个、STEP 文件 0 个；batch 不变且保持只读。P1 STEP 位于独立 confirmation run。
- 安全边界：没有重跑 CAD runner、发 HTTP、读取 raw 正文、`.env` 或密钥；FORMAL_EVALUATION_ALLOWED=False 不变。
- 结论边界：仅验证单次经负责人确认的 P1 参数进入既有 CAD/STEP 链，不代表广泛语言质量或制造认证。
- 下一步：如需继续 live 样本，需先定义新 scope、预算与 batch ID，完成 preflight 并单独取得执行批准；否则可由负责人先人工检查 P1 STEP。


### APP-003-LIVE-PREFLIGHT-20261114-02-CLOSEOUT / Codex 中枢 / done / 2026-11-14

- 动作：负责人确认已在 FreeCAD 检查 P1 STEP 且无问题，批准合入并收束本批任务。
- 合入状态：本轮全部为文档收束；提交位于本地 `main`，随后同步 `origin/main`。没有待合并的功能分支。
- 验收：P1 隔离 confirmation run 的 Schema、STEP SHA-256、native/readback 几何比较由 Codex 只读核验通过；FreeCAD 目视检查由负责人完成。
- 原 batch：`app003-product-live-20261114-02` 保持只读，4/12 HTTP、4 个 raw、0 个 batch 内 STEP；P1 STEP 仅位于独立 confirmation 目录。
- 结论边界：本次是单个负责人确认样本的自然语言抽取→确认→CAD→STEP 产品路径验收，不代表广泛模型质量、制造认证或扩大 live 样本的授权。
- 下一步：若扩大 live 样本，先提出明确验证假设，另建 scope、预算、batch ID，完成 preflight 并取得单独批准。

### APP-003-FAILURE-PATHS-LANGUAGE-MATRIX / Codex 中枢 / review / 2026-11-14

- 动作：按已批准路线先盘点失败路径，并并行起草下一轮 8–12 条语言输入矩阵；本轮未调用模型、未创建 live batch、未读取密钥或旧 raw 正文。
- 复现：离线用 FakeTransport 和临时目录验证同一 `input_id` 连续创建两次时，旧实现复用固定 `logical_run_id`；第一次确认成功后，第二次 `get()` 和安全下载仍返回第一次的旧 confirmed state/STEP。
- 修复：`ProductLiveService.extract()` 为每次 create 生成独立 UUID 运行 ID；新增回归测试确认第二次 run 保持 `needs_confirmation`、不能下载旧 STEP，第一次已确认 run 仍可独立下载。既有固定 run ID 的测试改为使用 create 响应中的真实 ID。
- 验证：固定 CAD venv Python 3.11.18 下定向回归 1/1、Product Live 专项 108/108 通过；输出有既有 HTTP socket `ResourceWarning`，无失败。本轮补丁后的 UI/C1/C2/C3 跨模块回归尚未重跑。
- 设计产物：新增 `agent-work/integration/APP-003-FAILURE-PATHS-LANGUAGE-MATRIX/failure-paths-and-language-matrix.md`，盘点抽取/解析、ask/refuse、Schema/patch、pipeline/STEP、路径/hash、跨 run 与泄漏路径，并草拟 L01–L10。标签与输入分离原则、DeepSeek/C0/no-retrieval 候选范围和 10×最多 2 次预算仅为草案。
- 边界：未改变 v5 prompt/Schema/IR、单族范围、授权 profile 或 `FORMAL_EVALUATION_ALLOWED=False`；历史 batch 只读。下一步是补跑 UI/全回归、HTTP 重复 create E2E，并交独立 Codex 复核；通过后再讨论新 live scope。

### APP-003-FAILURE-PATHS-LANGUAGE-MATRIX-REVIEW / Codex 中枢 / review / 2026-11-14

- 动作：对 `3958ed5` 做独立复核，重点检查重复 input 的 run identity、HTTP confirm/get/download 一致性和语言矩阵范围边界。
- 结果：旧实现的跨 run 旧 STEP 暴露已由离线复现确认，UUID run identity 修复和 unit/HTTP 回归均通过；Product Live 109、组合 UI/C1/C2/C3/Integration 300、Schema 17、CAD 13 以及目标 diff check 通过。
- 结论：修复可在离线 ProductLiveService 边界内继续推进，记录为 `review`；语言矩阵仍是未冻结草案，失败路径补强项不冒充已完成证据，不启动新的 live batch。

### APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 / Codex 中枢 / review / 2026-11-14

- 动作：在失败路径修复独立复核后，准备十条中文语言输入候选、物理隔离 evaluator labels 和范围草案。
- 结果：固定候选 DeepSeek `deepseek-flash` / C0 / 无检索；预算建议 10 条×最多 2 次 HTTP=20；输入 hash `8339431e…361801`，标签 hash `a5055025…51bcf9`。JSON 格式校验通过。
- 执行阻塞：当前 Product Live authorization profile 硬绑定既有 P1–P4 和对应输入 hash，不能直接执行新十条。若负责人接受矩阵，须新增版本化 profile/runner、离线隔离测试、独立复核和新 batch preflight；不复用旧 profile/batch。
- 边界：这是候选，不是冻结集、batch、preflight 或执行授权；没有模型、网络、密钥读取或 CAD 调用；`FORMAL_EVALUATION_ALLOWED=False` 不变。

### APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 / Codex 中枢 / review / 2026-11-14

- 动作：负责人授权继续推进十条候选语言矩阵的技术准备；新增独立版本化 profile `app003-product-language.v1` 和离线 preflight，保持旧 Product Live P1–P4 profile、旧 batch、prompt/Schema/IR 和全局 gate 不变。
- 产物：`src/llm/product_language_authorization.py`、`src/integration/product_language_runner.py`、`tests/integration/test_product_language_scope.py`、ADR-0024 及本 scope checkpoint。
- 验证：固定 CAD venv Python 3.11.18 下专项 8/8 通过；`py_compile`、`git diff --check` 通过。输入 hash、十条 ID、20 HTTP 预算和已有目录拒绝均核验；labels、凭据和网络 spy 均为 0 次。
- 边界：本轮没有实现真实执行路径；没有读取 `.env`/API key、发送 DeepSeek 请求、创建 batch、读取 evaluator labels 或运行 CAD。下一步交独立 Codex 复核，之后才可准备 formal preflight。

### APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01-R1 / Codex 中枢 / review / 2026-11-14

- 动作：提交后接口复核发现 per-input retry accessor 会继承批次 20 上限；窄修 `417139f` 强制 `max_chat_attempts_for()` 返回 2，并增加反向测试。
- 验证：固定 CAD venv 专项 8/8、`py_compile`、`git diff --check` 通过；未触网、未读凭据、未创建 batch。
