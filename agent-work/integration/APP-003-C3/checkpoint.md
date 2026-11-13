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


## 窄修 R2（本提交，ask 错误放行修复）

### 复现事实

`c2-ask-extra-question` fixture：`decision=ask`、`questions=["请确认安装方式？"]`、`missing_fields=[]`、`extracted_parameters={bore_d:24}`。

旧行为：`create_product_run` 返回 `needs_confirmation`，UI 显示"确认并生成 STEP"按钮；提交空 patch 后，`confirm_product_run` 通过 Schema 预检（bore_d 存在，合法）直接进入 `run_pipeline`，返回 `succeeded` 并生成 STEP。这是构造门缺陷：有未回答的澄清问题，但被当作确认。

### 修复 1：product_flow.py — API 层 fail-closed 门

在 `confirm_product_run()` 的 patch 验证之前（行 515，原 `# Validate patch fields`），新增"未回答问题"门：

```python
if parent_rec.decision == "ask" and parent_rec.questions:
    unresolved_missing = [f for f in parent_rec.missing_fields if f not in patch]
    if unresolved_missing or not parent_rec.missing_fields:
        return ProductRunRecord(..., product_status=PRODUCT_STATUS_BLOCKED,
            errors=[{"code": "QUESTIONS_UNANSWERED", ...}])
```

逻辑：
- 若 `decision=ask` 且 `questions` 非空：
  - 若 `missing_fields=[]`（如 ask-extra-question）：问题无法通过参数 patch 回答 → 阻断
  - 若 `missing_fields` 非空但 patch 未覆盖全部缺参（如 ask-missing-bore 空 patch）→ 阻断
  - 若 `missing_fields=[bore_d]` 且 patch 提供了 `bore_d` → 允许继续（原有路径）

### 修复 2：server.py — UI 层防护（defence-in-depth）

`renderConfirmSection()` 新增判断：若 `decision=ask` + `questions` 非空 + `missing_fields` 为空，不显示确认按钮，改为展示问题列表和阻断说明：

```js
const hasUnanswerableQuestions = d.decision === 'ask' && (d.questions||[]).length > 0
  && (d.missing_fields||[]).length === 0;
if (hasUnanswerableQuestions) {
  // 展示问题、显示阻断说明、不显示确认按钮
} else {
  // 正常显示参数补充表单和确认按钮
}
```

## Codex 中枢独立复核（2026-11-13）

- 复核对象：`cc/APP-003-C3-PRODUCT-UI`，HEAD `f258480`，父提交 `a305352`；复核时工作区干净。
- 固定环境：`work/benchcad-output/venv/bin/python`，Python 3.11.18，CadQuery/OCP 可用。
- 回归命令：
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.demo.test_product_flow tests.demo.test_product_ui tests.demo.test_demo_handler tests.integration.test_pipeline tests.integration.test_schema_to_ir -q` — **264 项通过**。
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q` — **17 项通过**。
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q` — **13 项通过**。
  - `py_compile`（product_flow/server 和两个 demo 测试文件）、`git diff --check` — 通过。
- localhost E2E（`127.0.0.1:18082`，临时 output root）：
  - `c2-ask-extra-question` create → 空 patch confirm 返回 `blocked` + `QUESTIONS_UNANSWERED`；没有 STEP/hash/bytes，GET parent 前后完整 JSON 相同。
  - `c2-ask-missing-bore` 空 patch confirm 返回 `blocked` + `QUESTIONS_UNANSWERED`。
  - 新建 ask-missing parent 后以 `patch={bore_d:16}` confirm，生成 succeeded child；STEP 137034 bytes，下载成功，下载 SHA-256 与结果字段一致；parent 前后完整 JSON 相同。
  - UI 逻辑代码检查确认 ask-extra 隐藏确认按钮并展示未回答问题；测试套件覆盖路由和 UI 内容。未进行真实浏览器视觉/DevTools 执行检查。
- 限制：测试有既有 `ResourceWarning` 和 CadQuery/NumPy 上游弃用警告，不影响通过结果。浏览器 DevTools XSS 验证仍未运行。
- 结论：ask 未回答问题的 API 构造门和对应离线 UI 逻辑通过独立复核；当前交付保持 `review`，等待负责人合入 `main`。本复核未运行模型、未读取密钥/`.env`、未发 provider 请求，也未改变授权或全局 gate。

## 浏览器验收（2026-11-13）

- 环境：固定 CAD venv 启动 `scripts/run_cad_demo.py --port 18083 --output-root /tmp/app003-c3-browser-review-runs`，通过浏览器打开 `http://127.0.0.1:18083/product`；服务关闭后临时产物未纳入仓库。
- 页面基础：`GET /product` 正常加载；离线 synthetic 警告、单族限制、STEP 免责声明和 fixture 下拉列表可见。
- XSS：输入 `<img src=x onerror=window.__c3_xss=1>` 后创建 `c2-answer-bore24`，页面以文本显示 payload，DOM 中没有图片元素，`window.__c3_xss` 未被设置。
- ask-extra：创建 `c2-ask-extra-question` 后页面展示问题“请确认安装方式？”及阻断说明；页面按钮仅有“创建产品运行”，没有“确认并生成 STEP”。
- ask-missing：创建 `c2-ask-missing-bore` 后显示 `bore_d` 必填输入；填写 `16` 并确认后页面显示 `succeeded`、几何摘要、STEP SHA-256 和下载链接。下载得到 137034 字节，SHA-256 为 `3ed46b402be57b693d6816c5cf0eb210ea8c3abeeb6c240d7756f93b02f3419f`，与页面展示一致。
- reset：点击“新建另一个需求”后 request、fixture、confirm 和 result 区域均清空，旧 hash/下载链接不残留。
- 结论：浏览器视觉/交互、XSS 事件、ask 阻断、补参构造/下载和 reset 验收通过；C3 仍保持 `review`，待负责人合入 `main` 后再标记 `done`。本验收未调用模型/provider、未读取密钥/`.env`、未创建 batch。

UI 修复不能替代 API 层门——直接 HTTP POST confirm 也被 `QUESTIONS_UNANSWERED` 阻断。

### 新增回归测试（7 项，test_product_flow.py）

| 测试 | 覆盖 |
|---|---|
| `test_ask_extra_question_empty_patch_blocked` | ask-extra 空 patch → QUESTIONS_UNANSWERED blocked；compile_ir=0 |
| `test_ask_extra_question_no_step_produced` | blocked confirm 无 step_sha256/step_path |
| `test_ask_extra_question_parent_unchanged_after_blocked_confirm` | parent run 完全不变 |
| `test_ask_missing_bore_empty_patch_blocked` | ask-missing-bore 空 patch 不构造 |
| `test_ask_missing_bore_valid_patch_succeeds` | ask-missing-bore + bore_d=16 → succeeded；parent 不变 |
| `test_bore24_confirm_still_succeeds` | bore24（answer，无问题）confirm 仍成功 |
| `test_bore80_confirm_still_succeeds` | bore80（answer，无问题）confirm 仍成功 |

### 验证结果（sandbox Python 3.10.12）

```text
py_compile: src/demo/product_flow.py, src/demo/server.py, tests/demo/test_product_flow.py — OK
git diff --check: OK

C2 product flow tests (new 65):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow -q
  Ran 65 tests (原 58 + 新 7) — OK

C3 product UI tests:
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_ui -q
  Ran 62 tests — OK

C1 regression:
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -q
  Ran 56 tests — OK

Integration:
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
  Ran 81 tests — OK

Schema:
  Ran 17 tests — OK
```

### handoff_self_check（R2 更新）

```text
changed=src/demo/product_flow.py (QUESTIONS_UNANSWERED gate in confirm_product_run), src/demo/server.py (UI: hide confirm btn for unresolvable ask), tests/demo/test_product_flow.py (65 tests), agent-work/integration/APP-003-C3/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_flow 65/65 OK; test_product_ui 62/62 OK; test_demo_handler 56/56 OK; integration 81/81 OK; schema 17/17 OK
confirmed=ask-extra-question empty patch → QUESTIONS_UNANSWERED blocked, compile_ir=0, step_path=None, parent unchanged; ask-missing-bore empty patch blocked, bore_d=16 patch succeeds; bore24/bore80 answer paths unaffected; R1 fixes preserved (request_text display, step_sha256 on success, XSS regression)
unresolved=固定 CAD venv (Python 3.11.18) 下真实路径验证；浏览器端 UI 层测试（ask-extra 确认按钮不可见）
next_agent_focus=1) run under real CadQuery: ask-missing-bore patch bore_d=16 → real STEP; 2) browser: verify ask-extra shows no confirm button; 3) verify ask-extra HTTP POST confirm still blocked at API level
```
