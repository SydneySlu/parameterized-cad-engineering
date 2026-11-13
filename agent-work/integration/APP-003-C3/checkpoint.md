# APP-003-C3 checkpoint

- 日期：2026-11-13（执行）
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`review`
- 目标：在现有本地 demo 中增加独立的自然语言确认页面 `/product`，复用 C2 离线产品 API。
- 基线：`main=1bc019f`，分支 `cc/APP-003-C3-PRODUCT-UI`，开始时工作区干净。

## 认领记录

- 任务 ID：`APP-003-C3-PRODUCT-UI`
- 分支：`cc/APP-003-C3-PRODUCT-UI`
- 基线 commit：`1bc019f`
- 实现边界：ADR-0023 C2 API 语义不变；不修改 v5 prompt/contract、Schema、IR、编译器、A2 历史批次；不读取 `.env`/密钥；不发模型或外网请求；`FORMAL_EVALUATION_ALLOWED=False` 不变。

## 新增/修改文件

- `src/demo/server.py`（修改）：
  - 新增 `_build_product_html()` 函数：C3 离线确认 UI 单页 HTML+CSS+JS
  - 新增 `PRODUCT_HTML_CONTENT` / `PRODUCT_HTML_BYTES` 模块级常量
  - 新增 `GET /product` 路由 → `_handle_product_ui()`
  - 新增 `GET /api/product/fixtures` 路由 → `_handle_product_fixtures()`（返回 fixture allowlist，不暴露文件路径）
  - C1 `/`、`/api/generate`、`/download/<run_id>` 路由不变
  - C2 `/api/product/create`、`/api/product/confirm/<run_id>`、`/api/product/<run_id>`、`/product-download/<run_id>` 路由不变
- `tests/demo/test_product_ui.py`（新增）：45 项 HTTP 集成测试
- `agent-work/integration/APP-003-C3/checkpoint.md`（新增，本文件）
- `docs/WORKLOG.md`（追加）

## C3 UI 页面结构

1. **顶部警告条**：醒目黄色，说明"离线 synthetic fixture 模式 — 非真实模型抽取 | 单族 | STEP 通过 ≠ 制造认证"
2. **步骤 1 输入区**：需求文本 textarea + fixture 下拉选择（通过 `/api/product/fixtures` 动态加载）+ 创建按钮
3. **步骤 2 确认区**：展示 run_id、product_status badge、decision、extracted_parameters、catalog_derived（只读）、rule_derived（只读）、missing_fields、questions、conflicts、errors；用户参数补充表单（bore_d 输入）；确认按钮（仅 needs_confirmation）
4. **步骤 3 结果区**：child run_id、product_status、pipeline_status/stage、验证摘要、IR 文档（折叠）、schema_result（折叠）、errors、下载按钮（仅 succeeded）、重置按钮
5. **底部免责声明**

## 安全约束

- 所有动态值通过 `esc()` HTML 转义（`&`/`<`/`>`/`"`/`'` 五种）
- `esc()` 函数在页面 JS 中定义
- fixture 列表只返回 fixture_id，不暴露文件路径
- 下载复用 C2 六层安全验证（UUID 格式 → 注册表 → succeeded → containment → symlink → hash）
- 不调用 LLM/provider，不读取 `.env`，不创建 batch

## 验证结果

执行环境：sandbox Python 3.10.12（非固定 3.11.18，CadQuery 不可用；mock compile_ir）

```text
py_compile: src/demo/server.py, tests/demo/test_product_ui.py — OK
git diff --check: OK

C3 product UI tests (45 项, mock HTTP + mock CAD):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_ui -v
  Ran 45 tests — OK

C2 regression (58 项):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow -q
  Ran 58 tests — OK

C1 regression (56 项):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -q
  Ran 56 tests — OK

Integration regression:
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
  Ran 81 tests — OK

Schema regression:
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK
```

### 测试覆盖

**TestC3ProductPage（8 项）**：
- GET /product → 200 HTML；页面含 offline/synthetic/fixture 离线模式警告；含 esc() 五种转义；含 STEP≠制造认证说明；无裸 ${d.run_id}

**TestC1BackwardCompat（4 项）**：
- GET / → C1 HTML（非 C3 页面）；POST /api/generate 缺 bore_d → 400；未知路径 → 404

**TestProductCreateHTTP（10 项）**：
- bore24 → needs_confirmation；refuse → blocked；unsupported → blocked；conflict → blocked；unknown fixture → blocked；缺 request_text → 400；缺 fixture_id → 400；全 fixture 零 compile_ir 调用

**TestProductConfirmHTTP（13 项）**：
- confirmed="false" → 400；confirmed="true" → 400；confirmed=0 → 400；confirmed=1 → 400；revision="0" → 400；revision="abc" → 400；revision=True → 400；合法 int+bool → 200 child run；bore24 全流程 → succeeded；ask+patch bore16 → succeeded；非 UUID run_id → 400；类型错误零 compile_ir 调用

**TestProductDownloadHTTP（4 项）**：
- needs_confirmation → 403；succeeded → 200 STEP（hash 匹配）；failed → 403；非 UUID → 400

**TestProductUIXSSDefense（5 项）**：
- esc() 含五种转义；无裸 ${d.run_id}；无裸 ${d.pipeline_status}；含离线/synthetic 说明；含 STEP≠制造认证

**TestProductGetHTTP（3 项）**：
- 已知 run → 200；未知 UUID → 404；非 UUID → 400

## 未运行项

- 固定 CAD venv (Python 3.11.18/CadQuery 2.3.0) 下全量测试（真实 compile_ir）
- GET /product 浏览器端到端烟测（需 Mac + 浏览器）
- HTTP 端到端真实 bore24 create→confirm→download STEP 烟测

## handoff_self_check

```text
changed=src/demo/server.py (C3 routes + product HTML), tests/demo/test_product_ui.py (new, 45 tests), agent-work/integration/APP-003-C3/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_ui 45/45 OK; test_product_flow 58/58 OK; test_demo_handler 56/56 OK; test_pipeline+test_schema_to_ir 81/81 OK; schema 17/17 OK
confirmed=GET /product returns C3 HTML with offline disclaimer and esc(); GET /api/product/fixtures returns allowlist without file paths; C1 / and /api/generate backward compatible; C2 API unchanged; confirm type validation (string "false"→400, int 0/1→400, string revision→400); full create→confirm→download flow works; failed/blocked runs return 403 on download; no compile_ir called during create; no LLM/.env/network
unresolved=Codex 中枢在固定 CAD venv (Python 3.11.18) 验证真实构造路径; browser-based E2E test
next_agent_focus=Run under real CadQuery: verify bore24 full flow at HTTP level; verify browser renders /product page correctly; verify fixture dropdown loads
```

## 下一步

- 状态 `review`，等待 Codex 中枢独立验收
- 不 push，不合并 main，不自行标记 done


## 窄修 R1（本提交，APP-003-C3-PRODUCT-UI-NARROW-FIX）

### 修复 1：确认页展示原始需求文本

**问题**：`renderConfirmSection()` 未展示 API 响应中的 `request_text`，用户在确认参数前无法对照原始需求。

**修复**：在 `renderConfirmSection()` 顶部信息块中添加 `request_text` 展示行，使用 `esc(d.request_text)` 安全渲染：
```
if (d.request_text) html += `<div ...><b>原始需求文本（仅作记录）:</b><br>${esc(d.request_text)}</div>`;
```
样式区块（左边框 + 灰色背景）以区别于参数区域。

### 修复 2：成功结果展示 STEP SHA-256

**问题**：`renderResultSection()` 的 `succeeded` 分支仅展示下载按钮，未展示 `step_sha256`；用户无法核对下载文件完整性。

**修复**：在 `succeeded` 分支（下载按钮之前）添加 SHA-256 展示，使用 `esc(d.step_sha256)`：
```
if (d.step_sha256) {
  html += `<div><b>STEP SHA-256:</b><br><code>${esc(d.step_sha256)}</code></div>`;
}
```
失败/阻断路径完全不渲染 step_sha256（该分支不在 `if (d.product_status === 'succeeded')` 块中）。

### 新增回归测试（17 项，test_product_ui.py）

**TestRequestTextDisplay（4 项）**：
- PRODUCT_HTML 中 `esc(d.request_text)` 存在且无裸插值
- API 响应包含 request_text 字段，值与输入一致
- 中文需求文本正确往返

**TestStepHashDisplay（6 项）**：
- PRODUCT_HTML 中 `esc(d.step_sha256)` 在 succeeded 块内
- succeeded 响应包含 64 字节 hex step_sha256
- failed 响应的 step_sha256=None
- blocked 响应的 step_sha256=None
- 下载文件实际 hash 匹配 step_sha256

**TestXSSNarrowFix（7 项）**：
- 无裸 `${d.request_text}` 插值
- 无裸 `${d.step_sha256}` 插值
- `esc(d.step_sha256)` 存在于 PRODUCT_HTML
- `esc(d.request_text)` 存在于 PRODUCT_HTML
- `<img src=x onerror=...>` 作为 JSON 字符串返回（JSON 上下文安全）
- resetAll() 清除 result-area（避免旧 hash 残留）
- step_sha256 仅在 succeeded 块内

### 验证结果（窄修后，sandbox Python 3.10.12）

```text
py_compile: src/demo/server.py, tests/demo/test_product_ui.py — OK
git diff --check: OK

C3 product UI tests:
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_ui -q
  Ran 62 tests (原 45 + 新 17) — OK

C2 + C1 regression:
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow tests.demo.test_demo_handler -q
  Ran 114 tests — OK

Integration regression:
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
  Ran 81 tests — OK

Schema regression:
  Ran 17 tests — OK
```

### handoff_self_check（R1 更新）

```text
changed=src/demo/server.py (renderConfirmSection + renderResultSection), tests/demo/test_product_ui.py (62 tests), agent-work/integration/APP-003-C3/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_ui 62/62 OK; test_product_flow+test_demo_handler 114/114 OK; integration 81/81 OK; schema 17/17 OK
confirmed=esc(d.request_text) in renderConfirmSection; esc(d.step_sha256) inside succeeded block only; failed/blocked runs have step_sha256=null in response; resetAll() clears result-area; XSS payload returned as JSON string (browser esc() handles display); no bare interpolation of new fields; C1/C2 APIs unchanged; no LLM/.env/network
unresolved=固定 CAD venv (Python 3.11.18) 下真实 compile_ir 路径验证；浏览器端 XSS 验证（需 Mac + DevTools 确认 onerror 未执行）
next_agent_focus=1) run under real CadQuery: bore24/bore80 full flow, verify step_sha256 in page; 2) browser DevTools: confirm esc() renders request_text with XSS payload as text; 3) verify resetAll() on second run shows no residual hash
```
