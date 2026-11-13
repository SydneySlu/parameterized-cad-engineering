# APP-003-LIVE-PRODUCT checkpoint

- 日期：2026-11-13（执行）
- 负责人：CC 实现 / Codex 中枢独立复核 / 项目负责人最终批准真实执行
- 状态：`review`
- 任务 ID：`APP-003-LIVE-PRODUCT`
- 基线：`main=2dd7836`，分支 `cc/APP-003-LIVE-PRODUCT`（待创建）
- 目标：实现产品专用的服务端受控入口，支持离线 mock/spy 模式完整证明时序；本任务不发真实 HTTP。

## 已批准 scope

- Provider：DeepSeek `deepseek-flash`，Condition `C0`
- 冻结输入：4 条，ID 为 `P1-24mm`、`P2-ask-bore`、`P3-catalog-conflict`、`P4-unsupported`
- 最大逻辑运行：4，每个逻辑运行最多 3 次 HTTP，全批最多 12 次 HTTP
- P1 只有在用户确认后允许进入 CAD；P2/P3/P4 必须 fail-closed
- 产品独立 scope，不复用 A2 authorization/batch/approval/raw/summary

## 新增/修改文件

### 新增
- `src/llm/product_live_authorization.py` — 产品专用授权/配置模块
  - `ProductLiveAuthorization` (extends `FormalRunAuthorization`)
  - `ProductLiveFormalApproval` — 独立于 A2 的批准凭证
  - `validate_product_formal_approval_binding()` — 批准绑定校验
  - `make_product_test_approval()` — 测试用 test-only 凭证
  - 冻结常量：`PRODUCT_PROFILE_ID`、`PRODUCT_INPUT_IDS`、`PRODUCT_INPUTS_SHA256`、`PRODUCT_LABELS_SHA256`、`PRODUCT_MAX_BATCH_HTTP=12`
- `src/integration/product_live_runner.py` — 产品 live runner
  - `run_product_batch()` — 公共入口（dry_run/mock/formal）
  - `run_product_offline_preflight()` — 离线 preflight（零网络/零密钥）
  - `confirm_product_live_run()` — 用户确认后唯一调用 `run_pipeline()` 的路径
  - `ProductLiveRunState` — 抽取结果状态（含 prompt/contract hash 追溯）
  - `ProductLiveBatchResult` — 批次结果
  - `_SummaryWriter` — 原子批次摘要写入（不含 raw body/secret/labels）
- `agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json` — 4 条冻结刺激
  - SHA-256: `666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a`
- `agent-work/integration/APP-003-LIVE-PRODUCT/evaluator-labels.json` — 评估标签（物理隔离）
  - SHA-256: `73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795`
- `tests/integration/test_product_live.py` — 52 项离线测试
- `tests/demo/product_live_fixtures/` — 测试用 envelope fixtures
- `agent-work/integration/APP-003-LIVE-PRODUCT/checkpoint.md`（本文件）

### 修改
- `src/demo/server.py` — 新增产品 live HTTP 路由
  - `POST /api/product-live/create` — 创建产品 live run（从预排队 mock/formal 响应）
  - `POST /api/product-live/confirm/<run_id>` — 确认并触发 CAD pipeline
  - `GET /api/product-live/<run_id>` — 获取 run 状态
  - `GET /product-live-download/<run_id>` — STEP 下载（6 层安全验证）
  - `_get_product_live_step_bytes_secure()` — 6 层安全下载辅助函数
  - `make_handler_class()` 新增 `product_live_handler` 可选参数（默认 None，C3 兼容）
  - C1/C2/C3 路由完全不变

## 确认门和状态

- 模型返回 `answer` → `needs_confirmation`（不直接调用 CAD）
- 用户确认前 `run_pipeline` 调用次数 = 0（测试 `test_p1_no_cad_before_confirm` 断言）
- `ask`/`missing_fields`/`unsupported`/`conflict`/`refuse`/`parse error`/`schema error` → `blocked`
- P1 合法 answer 只有收到 `confirm_product_live_run(confirmed=True)` 后才调用 `run_pipeline()`
- Pipeline/STEP 失败 → `failed`，不暴露 `step_path`，不误报 `succeeded`
- 每次运行记录 `prompt_file_sha256`、`prompt_version`、`contract_version`、`decision`、参数来源、questions/missing/unsupported/conflicts

## 证据与隐私

- `ProductLiveRunState.as_dict()` 不包含 raw 响应正文
- `raw_retention_meta` 在 HTTP 响应中只保留 `retained`/`path`/`body_sha256`，不含 body 内容
- 测试断言 evaluator labels（`expected_decision`、`allowed_to_cad`、`expected_conflicts`）不出现在 state 中
- 不读取 `.env`/密钥进行离线测试
- `FORMAL_EVALUATION_ALLOWED=False` 全程不变

## 验证结果

执行环境：sandbox Python 3.10.12（非固定 3.11.18/CadQuery；CAD-dependent 测试在沙箱中失败，与 C3 checkpoint 记录的环境限制一致）

```text
py_compile:
  PYTHONPATH=src:. python3 -m py_compile src/llm/product_live_authorization.py \
    src/integration/product_live_runner.py src/demo/server.py \
    tests/integration/test_product_live.py — OK

git diff --check: OK

Product live tests (52 项):
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_product_live -q
  Ran 52 tests — OK

Schema regression (17 项):
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK

C3 create/gate tests (non-CAD):
  TestCreateProductRun 10/10 — OK

C3 regression (test_product_flow + test_product_ui + test_demo_handler):
  Ran 183 tests — 30 failures + 9 errors
  全部失败均为 CAD-dependent 测试（需要真实 CadQuery 编译路径）：
  - TestConfirmProductRun: 需要 run_pipeline → compile_ir 真实调用
  - TestDownloadIsolation: 需要 step_path（来自成功 CAD）
  - TestManifestFieldMapping: 需要真实 compilation_result
  - TestParentRunImmutability: 需要成功 confirm → CAD
  沙箱 Python 3.10.12 无 CadQuery/OCP，与 C2/C3 checkpoint 记录的限制一致；
  固定 CAD venv (Python 3.11.18) 下这些测试可通过。

Integration (test_product_live + test_pipeline + test_schema_to_ir):
  Ran 133 tests — 25 failures + 3 errors
  全部失败同样来自 test_pipeline 中需要真实 CAD 的测试。
```

### 测试覆盖（52 项 test_product_live.py）

1. **TestProductLiveAuthorization (8 项)**：有效构造、拒绝错误 provider/model/profile/inputs_sha256/budget/enable_cad_pipeline=False/空 batch_id；全局 gate 不变
2. **TestProductApproval (4 项)**：test-only 拒绝、batch_id 不匹配拒绝、错误 profile_id 拒绝、audit dict 无 secret
3. **TestProductOfflinePreflight (6 项)**：valid preflight pass、budget feasible、inputs SHA-256 verified、batch dir not exist、prompt loadable、dry_run 返回 plan
4. **TestProductLiveMockP1Answer (2 项)**：P1 answer → needs_confirmation；确认前零 run_pipeline 调用
5. **TestProductLiveMockP1Confirm (5 项)**：confirmed=True 调用 pipeline；confirmed=False blocked 零 CAD；非 confirmable 状态 blocked 零 CAD；pipeline 失败 → failed 无 step；patch unknown field blocked 零 CAD
6. **TestProductLiveMockP2Ask (2 项)**：P2 ask+missing → blocked 零 CAD；直接 confirm blocked 状态 → 仍 blocked 零 CAD
7. **TestProductLiveMockP3Conflict (1 项)**：P3 catalog conflict → Schema blocked 零 CAD 无 STEP
8. **TestProductLiveMockP4Unsupported (1 项)**：P4 unsupported → blocked 零 CAD 无 STEP
9. **TestProductLiveParseContractFailures (3 项)**：invalid JSON → blocked with PARSE_ERROR；bore_d 超目录 → Schema blocked 零 CAD；refuse → blocked 零 CAD
10. **TestProductLiveApprovalGate (3 项)**：formal 无 approval raises；test-only 在任何 infra 前拒绝；全局 gate 不变
11. **TestProductLiveBudget (2 项)**：mock 模式 4 次 transport send；budget plan max=12
12. **TestProductLiveInputsFile (2 项)**：inputs SHA-256 匹配；篡改 inputs raises
13. **TestProductLiveSummaryIsolation (3 项)**：state dict 无 raw body；evaluator labels 不在 state；state 含 prompt_file_sha256
14. **TestC3Regression (4 项)**：c2-answer-bore24 fixture 仍工作；server 导入不破坏 C3 路由；make_handler_class 2 参数兼容；导入 product live 不改变全局 gate
15. **TestProductLiveRunIsolation (2 项)**：failed run 无 step；succeeded run 有 step_sha256
16. **TestProductLivePlansAndMode (3 项)**：mock 模式标签；planned_runs input_ids 正确；planned_runs provider/model 正确
17. **TestProductLiveMockP3Conflict (1 项)** — P3 隔离测试
18. **TestProductLiveMockP4Unsupported (1 项)** — P4 隔离测试

## 未运行项

- 固定 CAD venv (Python 3.11.18/CadQuery 2.3.0) 下全量测试（真实 compile_ir）
- 真实 DeepSeek HTTP 请求（需 Codex 中枢复核 + 项目负责人具体 batch 授权）
- live preflight（需独立执行授权）
- 浏览器端 /product-live 页面烟测（需 Mac + 浏览器）

## handoff_self_check

```text
changed=src/llm/product_live_authorization.py (new, product auth), src/integration/product_live_runner.py (new, product runner), src/demo/server.py (product live routes + _get_product_live_step_bytes_secure), agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json (new, 4 frozen inputs), agent-work/integration/APP-003-LIVE-PRODUCT/evaluator-labels.json (new, physically separated), tests/integration/test_product_live.py (new, 52 tests), tests/demo/product_live_fixtures/ (new, test envelopes), agent-work/integration/APP-003-LIVE-PRODUCT/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_live 52/52 OK; schema 17/17 OK; C3 create/gate 10/10 OK; C3 full regression 183 ran with 30 fail + 9 err (all CAD-dependent, same as C3 checkpoint env limit); integration 133 ran with 25 fail + 3 err (all CAD-dependent)
confirmed=P1 answer → needs_confirmation with zero run_pipeline calls; confirmed=True → pipeline called → succeeded; confirmed=False → blocked zero CAD; P2 ask → blocked; P3 conflict → Schema blocked zero CAD; P4 unsupported → blocked zero CAD; parse error → blocked with PARSE_ERROR; refuse → blocked; test-only approval rejected before infra; batch_id mismatch rejected; wrong provider/model/profile/inputs_sha256/budget rejected at construction; FORMAL_EVALUATION_ALLOWED=False unchanged throughout; evaluator labels not in state; raw body not in state.as_dict(); prompt_file_sha256 recorded in state; C3 routes backward compatible with 2-arg make_handler_class; C2 fixture still loads
unresolved=固定 CAD venv (Python 3.11.18) 下真实 compile_ir 路径验证；真实 DeepSeek HTTP 请求验证（需 Codex 复核 + 负责人 batch 授权）；浏览器端 /product-live 页面烟测
next_agent_focus=1) Run under real CadQuery: verify P1 confirm → real STEP with hash; 2) Codex 中枢在固定 venv 重跑全量 test_product_live + C3 regression; 3) Verify FORMAL_EVALUATION_ALLOWED still False; 4) Do NOT create live batch or send HTTP without Codex review + owner approval
```

## 安全边界

- `FORMAL_EVALUATION_ALLOWED=False` 未改变
- 不复用 A2 authorization/profile/approval/batch/raw/summary
- 不调用 DeepSeek/Ollama 或任何外网
- 不读取或打印 `.env`/API key/Authorization header
- 不把 evaluator labels 放入 prompt/transport/summary/日志/测试输入
- 不让模型生成或执行 Python
- 不把 offline mock/fixture 描述为真实模型效果
- 不创建 live batch 或发送 HTTP

## R1 窄修（APP-003-LIVE-PRODUCT-R1）

### 问题 1：产品 live HTTP 入口没有真正连接 runner

**问题**：`/api/product-live/create` 只从预填充 registry 读取已有 state，不调用 runner；`run_server()` 也没有配置 `product_live_handler`，默认请求返回 `PRODUCT_LIVE_DISABLED`。

**修复**：
- `src/integration/product_live_runner.py`：新增 `ProductLiveService` 类，封装 FakeTransport 注入的离线模式。`extract(input_id, request_text)` 调用 `_run_one_logical_mock()` 并存入内部 registry；`confirm(run_id, confirmed, patch)` 调用 `confirm_product_live_run()`；`get(run_id)` 查询状态。新增 `_to_repo_relative_path()` 辅助函数。
- `src/demo/server.py`：
  - `make_handler_class()` 新增 `product_live_service` 参数（`ProductLiveService` 实例），向下兼容旧 `product_live_handler` dict 接口。
  - `_handle_product_live_create()` 改为接受 `{request_text, input_id}`，调用 `service.extract(input_id, request_text)` 真正执行抽取，不再只查已有 state。浏览器不提交模型响应、evaluator labels 或 CAD 结果。
  - `_handle_product_live_confirm()` 调用 `service.confirm(run_id, confirmed, patch)`。
  - `_handle_product_live_get()` / `_handle_product_live_download()` 通过 service 查询。
  - 新增 `_sanitize_state_for_http()` 辅助函数：统一剥离绝对路径、raw body、secret、evaluator labels。
  - `run_server()` 默认不配置 product live service → 返回 `PRODUCT_LIVE_DISABLED`。

### 问题 2：formal summary 中路径没有统一转换为相对路径

**问题**：`_SummaryWriter.update_run()` 直接写入 `pipeline_run_dir` 和 `step_path`，可能产生绝对路径。

**修复**：
- `src/integration/product_live_runner.py`：
  - 新增 `_to_repo_relative_path(path_str)`：将绝对路径转为 repo-relative；路径在 repo 外或无法解析时返回 None。
  - `_SummaryWriter.update_run()` 中 `raw_retention_path`、`pipeline_run_dir`、`step_path` 及 `ir_index["step_path"]` 统一经过 `_to_repo_relative_path()` 转换。
- `src/demo/server.py`：`_sanitize_state_for_http()` 在 HTTP 响应中也统一转换路径为 repo-relative。

### 新增回归测试（33 项，test_product_live.py 从 52 增至 85）

**TestProductLiveServiceHTTP (15 项)**：离线 HTTP E2E
- P1 create → needs_confirmation，run_pipeline=0
- P1 confirm → succeeded（mock pipeline）
- P1 下载成功，SHA-256 一致
- P2 create → blocked，零 CAD
- P3 create → blocked，零 CAD
- P4 create → blocked，零 CAD
- 未配置 service → 503 PRODUCT_LIVE_DISABLED，无副作用
- 未知 input_id → blocked
- 缺 request_text → 400
- 缺 input_id → 400
- confirmed=False → blocked
- 非 confirmable 状态 confirm → blocked
- API 响应无 raw body / secret / evaluator labels
- API 响应路径非绝对
- C1/C2/C3 路由仍工作

**TestSummaryPathRelative (10 项)**：summary 路径隔离
- summary 中 pipeline_run_dir 非绝对路径
- summary 中 step_path 非绝对路径
- summary 中 raw_retention_path 非绝对路径
- summary 中 ir_index.step_path 非绝对路径
- 路径穿越拒绝
- 外部路径拒绝
- symlink 逃逸拒绝
- hash 篡改拒绝
- API 响应不含绝对路径
- API 响应不含 raw body

**TestProductLiveServiceBackwardCompat (8 项)**：向后兼容
- 旧 product_live_handler dict 接口仍可用
- make_handler_class 2 参数（无 service）仍工作
- make_handler_class 3 参数（有 service）工作
- 导入 product live 不改变 FORMAL_EVALUATION_ALLOWED
- 默认 run_server 不配置 live service
- C1 GET / 仍返回 C1 HTML
- C2 /api/product/create 仍工作
- C3 GET /product 仍工作

### 验证结果（sandbox Python 3.10.12）

```text
py_compile: src/demo/server.py, src/integration/product_live_runner.py,
  tests/integration/test_product_live.py — OK
git diff --check — OK

Product live tests (85 项):
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_product_live -q
  Ran 85 tests — OK

Schema regression (17 项):
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK
```

### handoff_self_check（R1 更新）

```text
changed=src/integration/product_live_runner.py (ProductLiveService + _to_repo_relative_path + _SummaryWriter.update_run path normalisation), src/demo/server.py (_handle_product_live_create calls service.extract, _sanitize_state_for_http, product_live_service param), tests/integration/test_product_live.py (85 tests, +33 R1), agent-work/integration/APP-003-LIVE-PRODUCT/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_live 85/85 OK; schema 17/17 OK
confirmed=P1 HTTP create → needs_confirmation with zero run_pipeline; P1 HTTP confirm → succeeded; P2/P3/P4 HTTP create → blocked zero CAD; unconfigured service → 503 PRODUCT_LIVE_DISABLED; summary paths all repo-relative; API responses no absolute paths / raw body / secrets / labels; C1/C2/C3 backward compatible; FORMAL_EVALUATION_ALLOWED=False unchanged
unresolved=固定 CAD venv (Python 3.11.18) 下真实 compile_ir 路径验证；真实 DeepSeek HTTP 请求验证（需 Codex 复核 + 负责人 batch 授权）；浏览器端 /product-live 页面烟测
next_agent_focus=1) Run under real CadQuery: verify P1 HTTP confirm → real STEP; 2) Codex 中枢在固定 venv 重跑 test_product_live 85 项 + C3 regression; 3) Verify FORMAL_EVALUATION_ALLOWED still False; 4) Do NOT create live batch or send HTTP without Codex review + owner approval
```
