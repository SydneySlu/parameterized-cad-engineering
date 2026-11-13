# APP-003-LIVE-UI checkpoint

- 日期：2026-11-13（执行）
- 负责人：CC 实现 / Codex 中枢独立复核 / 项目负责人后续决定是否批准真实 batch
- 状态：`review`
- 任务 ID：`APP-003-LIVE-UI`
- 基线：`main=888080a`，分支 `cc/APP-003-LIVE-UI`
- 目标：将已有 ProductLiveService 和 /api/product-live/* 受控 API 接入明确标记的 live 确认页面；本任务只做 UI 接入和离线验证，不执行真实 DeepSeek 请求，不创建正式 batch，不读取 .env/API key，不修改 FORMAL_EVALUATION_ALLOWED。

## 认领记录

- 任务 ID：`APP-003-LIVE-UI`
- 分支：`cc/APP-003-LIVE-UI`（从 `main=888080a` 创建）
- 基线核对：99 项 test_product_live 全部通过（sandbox Python 3.10.12）

## 新增/修改文件

### 新增
- `src/demo/server.py`（`_build_product_live_html()`、`PRODUCT_LIVE_HTML_CONTENT`/`PRODUCT_LIVE_HTML_BYTES`、`_handle_product_live_ui()`、`_handle_product_live_inputs()`）
- `tests/demo/test_product_live_ui.py`（36 项离线 HTTP E2E 测试）
- `agent-work/integration/APP-003-LIVE-UI/checkpoint.md`（本文件）

### 修改
- `src/demo/server.py`：
  - 新增 `GET /product-live` 路由 → `_handle_product_live_ui()`（返回 live UI HTML）
  - 新增 `GET /api/product-live/inputs` 路由 → `_handle_product_live_inputs()`（返回授权 input IDs，无 key/label/路径）
  - `do_GET` 新增 `/product-live` 和 `/api/product-live/inputs` 分支
  - C1/C2/C3 路由完全不变；`make_handler_class` 签名不变
- `docs/WORKLOG.md`（追加）

## /product-live 页面特性

### 页面标注（满足任务要求）
- 顶部黄色警告条：「受控 Product Live UI — offline/mock transport 或 synthetic envelope | 非真实模型效果 | 单族 set_screw_shaft_collar (GN 705) | STEP 通过 ≠ 制造认证 | 不接触 API key 或 raw response」
- 底部免责声明：测试使用 offline/mock transport，不构成真实模型理解证据

### 状态覆盖
页面展示 `needs_confirmation`、`blocked`、`succeeded`、`failed`、`disabled` 状态；根据服务端 `product_status` 字段展示，不基于 HTTP 200 猜测成功。

### 安全
- 所有动态值通过 `esc()` HTML 转义（`&`/`<`/`>`/`"`/`'` 五种）
- 无裸 `${d.xxx}` 插值（通过 `test_product_live_page_no_bare_interpolation` 验证）
- 页面不调用 DeepSeek、不读取 `.env`、不暴露 API key/Authorization header/raw response body/evaluator labels
- 默认无 service → `PRODUCT_LIVE_DISABLED`（不尝试真实请求）

### 确认流程
- 创建阶段（`/api/product-live/create`）调用 `ProductLiveService.extract()`，返回 `needs_confirmation` 或 `blocked`
- 确认阶段（`/api/product-live/confirm/<run_id>`）调用 `ProductLiveService.confirm()`，唯一进入 `run_pipeline()` 的路径
- P1 answer 只在用户点击"确认并生成 STEP"后才触发 CAD
- P2/P3/P4 显示对应错误信息，不显示确认按钮（P2 ask 显示 questions/missing_fields；P3 显示冲突；P4 显示 unsupported_requests）
- 失败或阻断状态不显示下载按钮

## 验证结果

执行环境：sandbox Python 3.10.12（非固定 3.11.18/CadQuery；CAD-dependent 测试会失败，与 C3 checkpoint 记录的环境限制一致）

```text
py_compile:
  PYTHONPATH=src:. python3 -m py_compile src/demo/server.py \
    tests/demo/test_product_live_ui.py — OK

git diff --check — OK

Product live UI tests (36 项):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_live_ui -q
  Ran 36 tests — OK

Product live integration tests (99 项):
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_product_live -q
  Ran 99 tests — OK

Combined (135 项):
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_product_live tests.demo.test_product_live_ui -q
  Ran 135 tests — OK

Schema regression (17 项):
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK
```

### 测试覆盖（36 项 test_product_live_ui.py）

**TestProductLivePage (6 项)**：
- GET /product-live → 200 HTML；含 offline/mock/非真实模型/STEP≠制造认证 banner
- 页面含 esc() 函数
- esc() 含五种转义
- 页面无裸 ${d.xxx} 插值（全部 wrapped in esc()）
- GET /api/product-live/inputs → 200 含 P1-P4 input IDs
- 无 service → 503

**TestProductLiveUIP1Flow (4 项)**：
- P1 create → needs_confirmation，run_pipeline=0，无 step_path in response
- P1 confirm → succeeded（mock pipeline），ir_index.step_sha256 正确
- P1 download → 200 STEP bytes 正确
- P1 download SHA-256 匹配 ir_index.step_sha256

**TestProductLiveUIBlockedPaths (5 项)**：
- P2 ask → blocked，missing_fields 含 bore_d，run_pipeline=0
- P2 confirm → 仍 blocked，run_pipeline=0
- P3 conflict → blocked，conflicts 非空，run_pipeline=0
- P4 unsupported → blocked，unsupported_requests 含 anodizing，run_pipeline=0
- P2 blocked 下载 → 403

**TestProductLiveUIFailure (4 项)**：
- Pipeline failed → product_status=failed，无 step_path/ir_index
- Failed run 下载 → 403
- Parse error → blocked with PARSE_ERROR
- Refuse → blocked

**TestProductLiveUISecurity (9 项)**：
- XSS payload 在 JSON 响应中作为字符串（不执行）
- API 响应无 api_key/authorization/bearer/expected_decision/allowed_to_cad/expected_conflicts
- 无 service create → 503 PRODUCT_LIVE_DISABLED
- 无 service confirm → 503
- 无 service download → 503
- response 无绝对路径
- confirmed=False → blocked 零 CAD
- confirmed="true"（字符串）→ 400
- 缺 request_text → 400；缺 input_id → 400

**TestBackwardCompat (8 项)**：
- GET / → C1 HTML 正常
- GET /product → C3 HTML（含"离线 synthetic fixture"）
- make_handler_class 2 参数仍工作
- FORMAL_EVALUATION_ALLOWED=False
- /product-live 与 C3 /product 内容不同（不混淆）
- POST /api/product/create (C2) 仍工作

## 未运行项

- 固定 CAD venv (Python 3.11.18/CadQuery 2.3.0) 下全量测试（真实 compile_ir）
- 真实 DeepSeek HTTP 请求（需 Codex 中枢复核 + 负责人具体 batch 授权）
- 浏览器端 /product-live 页面真实交互、XSS DevTools 验证（需 Mac + 浏览器）
- P1 confirm 真实 STEP 路径（需 CadQuery 环境）

## handoff_self_check

```text
changed=src/demo/server.py (_build_product_live_html + PRODUCT_LIVE_HTML_CONTENT/BYTES + GET /product-live route + GET /api/product-live/inputs route + _handle_product_live_ui + _handle_product_live_inputs), tests/demo/test_product_live_ui.py (new, 36 tests), agent-work/integration/APP-003-LIVE-UI/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_live_ui 36/36 OK; test_product_live 99/99 OK; combined 135/135 OK; schema 17/17 OK
confirmed=GET /product-live returns live UI HTML with banners; page has esc() with 5 char escapes; page no bare ${d.xxx} interpolation; GET /api/product-live/inputs returns P1-P4 when configured; no service → PRODUCT_LIVE_DISABLED; P1 create → needs_confirmation run_pipeline=0; P1 confirm → succeeded mock pipeline; P1 download succeeds hash matches; P2 blocked no CAD; P3 conflict blocked no CAD; P4 unsupported blocked no CAD; parse error blocked; refuse blocked; failed no STEP; XSS payload as JSON string not executed; no API key/authorization/labels in response; C1/C2/C3 backward compatible; FORMAL_EVALUATION_ALLOWED=False unchanged
unresolved=固定 CAD venv (Python 3.11.18) 下真实 compile_ir 验证；真实 DeepSeek HTTP 请求（需 Codex 复核 + 负责人 batch 授权）；浏览器端 XSS DevTools 验证；P1 confirm 真实 STEP
next_agent_focus=1) Run under real CadQuery (Python 3.11.18): verify P1 confirm → real STEP and /product-live page renders correctly; 2) Codex 独立复核在固定 venv 重跑 135 项（test_product_live + test_product_live_ui）+ C3 regression; 3) FORMAL_EVALUATION_ALLOWED still False; 4) Do NOT create live batch without Codex review + owner approval
```

## Codex 独立复核（2026-11-13）

- 分支/提交：`cc/APP-003-LIVE-UI` / `0b8bd7b`；工作区干净；未 push、未合并。
- 固定环境：`work/benchcad-output/venv/bin/python`，Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0。
- 回归结果：`tests.demo.test_product_live_ui` + `tests.integration.test_product_live` **135/135**；C1/C2/C3 demo 回归 **183/183**；Integration pipeline/schema-to-IR **81/81**；Schema **17/17**；CAD compilation **13/13**；`py_compile`、`git diff --check` 均通过。仅有既有 ResourceWarning 和上游弃用警告。
- 浏览器证据（localhost `127.0.0.1:8766`，注入 FakeTransport/synthetic envelope）：P1 `needs_confirmation` → 用户确认 → `succeeded`，STEP 148393 bytes，页面 hash 与下载文件 `5ead6f40673fb0887b8eaa6172819289a3de76b64ef9c6fb70a66858d8c8c113` 一致；P2 显示 `blocked`、`missing_fields=bore_d` 和问题，未显示确认/下载入口；恶意 request text `<img src=x onerror=alert(1)>` 仅作为文本显示，DOM 中 `img=0` 且没有 `onerror` 属性。
- 边界：所有验证使用离线注入 transport 和本地 CAD；未调用 DeepSeek/Ollama、未读取 `.env`/密钥、未创建 batch；`FORMAL_EVALUATION_ALLOWED=False` 未改变；不构成真实模型效果证据。
- 结论：**pass，允许负责人合入 `main`**。合入后再将 APP-003-LIVE-UI 收束为 `done`；真实 provider 请求仍需新 batch scope、预算、preflight 和负责人单独批准。

## 安全边界

- `FORMAL_EVALUATION_ALLOWED=False` 全程不变
- 不调用 DeepSeek/Ollama 或任何外网
- 不读取或打印 `.env`/API key/Authorization header
- 不把 evaluator labels 放入 prompt/transport/summary/日志/页面/测试输入
- 不让模型生成或执行 Python
- 不把 offline mock/fixture 描述为真实模型效果
- 不创建 live batch 或发送 HTTP
- 不复用或修改 A2 authorization/batch/approval/raw/summary
