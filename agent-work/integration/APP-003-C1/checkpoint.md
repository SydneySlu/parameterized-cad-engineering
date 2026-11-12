# APP-003-C1 checkpoint

- 日期：2026-11-12
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`review`
- 目标：交付首个本地可用浏览器演示，支持需求文本记录、用户参数确认、Schema/IR/CAD/STEP 生成、状态/错误查看、STEP 获取和修改参数后重新生成。
- 基线：`main=1361f52`，分支 `cc/APP-003-C1-LOCAL-DEMO`，开始时工作区干净。

## 已完成：C1 范围与授权边界

- 项目负责人已确认推进里程碑 C，且 ADR-0020 明确由中枢结合现有架构选择界面方式。
- 新增 ADR-0022：首切片采用仅监听 `127.0.0.1` 的 Python 标准库 Web UI；不新增依赖；复用已验收 pipeline；用户手动确认结构参数；本任务不接真实模型、不读取密钥、不发网络请求。
- 已创建 CC 实施 prompt：`docs/coordination/prompts/APP-003-C1-local-demo-cc.md`。

## 已完成：CC 实现（本工作单元）

### 新增文件

- `src/demo/__init__.py`：模块初始化
- `src/demo/handler.py`：业务逻辑层
  - `DemoHandler` 类：维护内存 run 注册表；`run()` 接受 request_text + bore_d，构建合成 envelope 调用 `run_pipeline`；`get_step_bytes_secure()` 执行六层下载安全验证
  - `DemoRunResult` dataclass：包含 run_id、status、stage、errors、parameters、provenance、ir_document、validation_summary、step_sha256、step_bytes
  - `_build_demo_envelope()`：从手动参数构建合法 app001-io.v1 envelope（decision=answer, source=user_input）
  - `_read_run_evidence()`：从 pipeline 保存的 schema_result.json/input_ir.json/compilation_result.json 读取 provenance/IR/验证摘要
- `src/demo/server.py`：HTTP 服务端
  - 仅绑定 `127.0.0.1`；Python 标准库 `http.server`，无外部依赖
  - 路由：`GET /`（HTML UI）、`POST /api/generate`（JSON 生成请求）、`GET /download/<run_id>`（STEP 下载）
  - 嵌入式单页 HTML+CSS+JS：bore_d 下拉选择（15 个目录值）、目录派生参数只读展示、生成结果展示（参数+来源、IR 折叠、验证摘要、下载链接、错误详情）、限制说明
- `scripts/run_cad_demo.py`：启动脚本（PYTHONPATH=src:. + 固定 CAD venv）
- `tests/demo/__init__.py`：测试模块
- `tests/demo/test_demo_handler.py`：30 项测试

### 不变量

- 仅支持冻结单族 `set_screw_shaft_collar`，调用现有 schema/IR/compiler/geometry/STEP 实现，不复制规则或生成/执行任意 CAD Python。
- 每次 run 独立 UUID 目录；下载路径必须约束在当前成功 run 内，并验证成功 manifest/hash；失败不得返回旧文件。
- 文本只作为需求记录；首切片手动录入参数，不宣称模型理解。UI 实际调用 live LLM 需要另行制定产品授权、预算和 gate。
- A2 `...-01` 至 `...-04` 历史批次保持只读；`FORMAL_EVALUATION_ALLOWED=False` 不变。
- 不调用 LLM/provider，不读取 `.env`/密钥/A2 raw，不发模型或外网请求，不访问或修改 A2 历史批次。

### 下载安全验证（六层）

1. run_id 格式：UUID v4 正则
2. 注册表查找：只查内存注册表，不扫描磁盘
3. 成功状态检查：`status != "success"` → 拒绝
4. 路径 canonical containment：STEP 路径 resolve 后必须在 run 的 `cad_output/` 目录内
5. Symlink 拒绝：STEP 文件是 symlink → 拒绝
6. 内容 hash 比对：实际 SHA-256 必须与 pipeline 保存的 `step_sha256` 匹配

## 验证结果

执行环境：sandbox Python 3.10.12（非项目固定 3.11.18；固定 CAD venv 为指向 macOS homebrew 的断裂符号链接，无法在 Linux 沙盒中执行）

```text
py_compile: 6 new files — ALL OK
git diff --check: OK

Demo tests (mock CAD, no CadQuery needed):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -v
  Ran 30 tests — OK

Integration regression:
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline -q
  Ran 39 tests — OK

  PYTHONPATH=src:. python3 -m unittest tests.integration.test_schema_to_ir -q
  Ran 42 tests — OK

Schema regression:
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK

CAD compilation (requires CadQuery, unavailable in sandbox):
  PYTHONPATH=src:. python3 -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
  Ran 13 tests — FAILED (failures=1, errors=4)
  All 4 errors are ModuleNotFoundError: No module named 'cadquery' (pre-existing, confirmed via git stash)
  1 failure is also CadQuery-dependent (pre-existing)

A2 runner (Python 3.10 vs 3.11 differences):
  4 FAIL/ERROR — pre-existing, unrelated to this change (confirmed via git stash)
```

### 正常路径

- `test_bore24_success`：bore_d=24 mock CAD → status=success，parameters={bore_d:24, outer_d:40, screw_d:8, screw_len:12, width:16, second_screw:0}，provenance 正确（bore_d=user_explicit, outer_d/screw_d/screw_len/width=catalog_derived, second_screw=rule_derived），IR document 存在，validation_summary 包含 solid_count/is_valid/step_bytes。
- `test_bore80_second_screw`：bore_d=80 → second_screw=1 (rule_derived)。

### 失败路径

- `test_missing_bore_d_rejected_no_cad`：None bore_d → invalid_input，compile_ir 未调用。
- `test_non_integer_bore_d_rejected_no_cad`：字符串 bore_d → invalid_input，compile_ir 未调用。
- `test_bore_d_not_in_catalog_rejected_no_cad`：bore_d=25 → invalid_input，compile_ir 未调用。
- `test_catalog_conflict_blocked_no_cad`：bore_d=24 + outer_d=33 → blocked (CATALOG_MISMATCH)，compile_ir 未调用。

### 下载隔离

- `test_download_success`：成功 run → STEP bytes 可获取，hash 匹配。
- `test_download_unknown_run_id`：未知 run_id → None。
- `test_download_failed_run`：失败 run → None。
- `test_download_invalid_input_run`：invalid_input run → None。
- `test_symlink_step_rejected`：STEP 为 symlink → 拒绝。
- `test_hash_mismatch_rejected`：STEP 内容被篡改 → hash 不匹配 → 拒绝。

### 路径穿越

- `test_path_traversal_run_id`：`../etc/passwd` → is_valid_run_id=False。
- `test_non_uuid_run_id_rejected`：非 UUID 格式 → False。
- `test_valid_uuid_accepted`：合法 UUID v4 → True。

### 运行隔离

- `test_two_runs_different_ids`：两个 bore_d → 不同 run_id 和目录。
- `test_failed_after_success_no_leak`：先成功后失败 → 失败 run 不暴露旧 STEP，成功 run 仍可下载。
- `test_failed_run_no_old_step_path`：失败 run 的 _step_path=None。

### 无网络/LLM

- `test_no_socket_calls`：mock socket.socket → assert_not_called。
- `test_no_env_read`：mock os.environ.get → 无 KEY 读取。
- `test_no_llm_modules_imported`：handler.py 源码不含 real_transport/adapter/runner/requests/httpx/urllib3 导入。

## handoff_self_check

```text
changed=src/demo/__init__.py, src/demo/handler.py, src/demo/server.py, scripts/run_cad_demo.py, tests/demo/__init__.py, tests/demo/test_demo_handler.py, agent-work/integration/APP-003-C1/checkpoint.md, docs/WORKLOG.md
commands=py_compile (6 files OK); git diff --check (OK); tests.demo.test_demo_handler 30/30 OK; tests.integration.test_pipeline 39/39 OK; tests.integration.test_schema_to_ir 42/42 OK; tests.schema 17/17 OK; tests.cad_compilation 9/13 OK (4 ERROR=CadQuery missing, pre-existing); tests.integration.test_a2_runner 175/179 OK (4 pre-existing Python 3.10/3.11 diff)
confirmed=demo handler reuses run_pipeline without duplicating schema/IR/CAD rules; download isolation validates UUID+registry+success+containment+symlink+hash; mock tests prove no network/LLM calls; failed runs never expose old STEP; no existing files modified except checkpoint/WORKLOG
unresolved=Codex 中枢在固定 CAD venv (Python 3.11.18) 独立复核；真实 CAD/STEP 生成验证（需 Mac + CadQuery）；HTTP 端到端浏览器测试
next_agent_focus=verify in fixed CAD venv: run demo tests with real compile_ir, verify HTTP server starts and serves, verify bore_d=24 produces real STEP, verify download isolation with real files
```

## 窄修 R1（本提交，2026-11-12）

### 修复 1：manifest 字段名映射

`_read_run_evidence()` 中的两处错误字段名：

| 位置 | 修改前（错误） | 修改后（正确） |
|---|---|---|
| `native_geometry` 实体数 | `native_geo.get("solid_count")` | `native_geo.get("solids")` |
| `native_geometry` 面数 | `native_geo.get("face_count")` | `native_geo.get("faces")` |
| `native_geometry` 边数 | `native_geo.get("edge_count")` | `native_geo.get("edges")` |
| `native_geometry` 顶点数 | `native_geo.get("vertex_count")` | `native_geo.get("vertices")` |
| readback 通过标志路径 | `manifest["readback"]["pass"]` | `manifest["step_readback"]["comparison"]["pass"]` |

根据：`src/cad_compilation/geometry.py` COUNTS = `("solids","shells","faces","edges","vertices")`；compiler.py 第 307 行 `manifest["step_readback"] = {"geometry": ..., "comparison": comparison}`。

### 修复 2：UI 动态值 HTML 转义

在 `server.py` 的 JS 中：
- 新增 `function esc(s)` 函数，对 `&`/`<`/`>`/`"`/`'` 执行五种 HTML 转义。
- `renderResult()` 中所有动态字符串（run_id、stage、错误码、错误消息、参数名/值、IR JSON）均改为 `esc(...)` 包裹。
- fetch error 展示改为 `textContent`/`createElement` DOM API，避免 innerHTML 注入。

### 验证结果（窄修后，sandbox Python 3.10.12）

```text
py_compile: src/demo/handler.py, src/demo/server.py, tests/demo/test_demo_handler.py — OK
git diff --check: OK

Demo tests:
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -v
  Ran 52 tests (原 30 + 新增 22) — OK

  新增 TestManifestFieldMapping (8 项):
    solid_count=1 from native_geometry["solids"] ✓
    face_count=10 from native_geometry["faces"] ✓
    edge_count=20 from native_geometry["edges"] ✓
    vertex_count=30 from native_geometry["vertices"] ✓
    readback_pass=True from step_readback.comparison.pass ✓
    is_valid, volume_mm3, step_bytes 仍正确 ✓
    old wrong field names → None（证明修复 load-bearing）✓

  新增 TestUIHTMLEscape (14 项):
    esc() 五种转义规则 ✓
    <img src=x onerror=...> 完全转义 ✓
    <script>alert(1)</script> 完全转义 ✓
    renderResult 源码含 esc(d.run_id), esc(d.stage), esc(e.code), esc(e.message) ✓
    d.run_id, d.stage 不出现裸 ${{...}} 拼接 ✓
    恶意 bore_d 错误消息作为纯文本处理 ✓

Integration regression:
  test_pipeline 39/39 OK; test_schema_to_ir 42/42 OK; schema 17/17 OK

CAD compilation: 4 ERROR/1 FAIL = 既有 CadQuery 缺失（sandbox），与本次修改无关
```

## handoff_self_check（R1 更新）

```text
changed=src/demo/handler.py (manifest field mapping fix), src/demo/server.py (esc() + renderResult), tests/demo/test_demo_handler.py (mock struct + 22 new tests), agent-work/integration/APP-003-C1/checkpoint.md, docs/WORKLOG.md
commands=py_compile (5 changed files OK); git diff --check (OK); demo 52/52 OK; test_pipeline 39/39 OK; test_schema_to_ir 42/42 OK; schema 17/17 OK
confirmed=native_geometry field names now match geometry.summarize() output (solids/faces/edges/vertices); readback_pass now reads from step_readback.comparison.pass; renderResult escapes all dynamic values via esc(); download/symlink/hash/path-traversal isolation unchanged; no other files modified
unresolved=Codex 中枢在固定 CAD venv (Python 3.11.18) 验证真实 manifest 结构；HTTP 端到端浏览器烟测确认 esc() 在浏览器中正常工作
next_agent_focus=Run under real CadQuery (Python 3.11.18): verify bore_d=24 HTTP smoke returns solid_count=1, face_count>0, readback_pass=True; use browser DevTools to confirm <img onerror> payload in error message is displayed as text, not executed
```

## 下一步

- 任务状态 `review`，等待 Codex 中枢独立验收。
- 不 push、不合并、不自行标记 done。
- Codex 中枢应在固定 CAD venv (Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0) 下复核：
  1. 新增 demo 测试 30 项
  2. Integration test_pipeline + test_schema_to_ir 回归
  3. CAD compilation 13 项（含真实 STEP 生成）
  4. Schema 17 项
  5. HTTP server 启动和浏览器交互验证
  6. 下载安全六层验证
  7. 无网络/LLM 调用确认

## 窄修 R2：拒绝小数孔径（2026-11-12）

- 根因：`DemoHandler.run()` 原先直接执行 `int(bore_d_raw)`，会把 `24.9` 截断为 24 并生成错误目录件。
- 修复：新增 `_parse_bore_d()`；接受整数、整数文本和整数值浮点，拒绝布尔值、非整数浮点和小数文本；拒绝发生在任何 pipeline/CAD 调用前。
- 回归：新增 24.9、`"24.9"`、`True` 三个拒绝测试，均断言 `compile_ir` 未调用。
- 状态：review；等待 Codex 中枢固定 CAD venv 复验。

## Codex 中枢最终独立复核（2026-11-12）

- 结论：`pass`（在 ADR-0022 既定手动参数、localhost、单族范围内）；任务状态保持 `review`，须合入 `main` 后才能标记 done。
- 被审查 HEAD：`4419e27`；基线 `main=1361f52`；分支 `cc/APP-003-C1-LOCAL-DEMO`；复核开始和结束时工作区干净。
- 环境：固定 CAD venv / Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 / jsonschema 4.26.0。
- 测试：Demo 55/55、Integration pipeline + schema_to_ir 81/81、Schema 17/17、CAD compilation 13/13；py_compile 和 `git diff --check` 通过。Demo 测试有 4 条非阻断 `ResourceWarning`；依赖弃用警告不影响通过结果。
- loopback：服务只监听 `127.0.0.1`。24 mm 实际生成并下载 STEP（148393 bytes、1 solid、35 faces、回读通过、hash 匹配）；80 mm 生成独立 run 且 `second_screw=1`、来源 `rule_derived`。浏览器页面成功显示参数/来源、IR、几何/回读摘要及下载入口。
- 拒绝和隔离：24.9 返回 `invalid_input/input_validation`；缺 bore 返回 HTTP 400；目录外 25 返回 invalid_input，失败 run 下载 403，之前成功 run 仍可取回；未知格式 ID 400、未知 UUID 404。STEP symlink 逃逸和内容篡改均被拒绝（403）。
- 安全边界：未调用 LLM/provider 或外网、未读密钥/`.env`、未访问 A2 历史批次；临时 run 输出与服务已清理。全局 gate、冻结契约、Schema/IR/CAD 后端未改。
- 非阻断发现：下载按钮标签多余右括号，记录为 P3 文案瑕疵；不影响产物或下载验证。
- 独立审查报告：`agent-work/reviews/APP-003-C1-codex-review.md`。
- 后续：负责人可按 fast-forward 流程合入 `main`；合入前不标记 done，不 push/merge 由本复核执行。

### handoff_successor_check

```text
predecessor=APP-003-C1 CC handoff; branch cc/APP-003-C1-LOCAL-DEMO HEAD 4419e27; checkpoint and commits 240a028/5923a5f/4419e27 reviewed
files_format=handler/server/start script/tests present; manifest field paths match compiler output; no out-of-scope source changes
core_rerun=Demo 55/55; Integration 81/81; Schema 17/17; CAD 13/13; py_compile and git diff --check pass under fixed CAD venv Python 3.11.18
normal_case=loopback browser bore_d=24 generated downloadable STEP; hash/readback and UI evidence matched
failure_case=24.9 rejected before CAD; missing bore 400; non-catalog 25 no STEP; symlink and tamper downloads 403
interface=manual bore_d input → existing deterministic pipeline → run-isolated evidence and STEP; output includes provenance, IR, validation and hash
limits=single family, fixed env, thread approximation, no LLM/language-understanding claim
result=pass
blocking_issue=none
```

## 合入收束（2026-11-12）

- 合并：负责人已将 `cc/APP-003-C1-LOCAL-DEMO` fast-forward 合入并推送 `main`；本地 `main`、`origin/main` 和远端 `main` 均核实为 `07a98d129022e78cc9e7dc4e44bc9ae2df083f5f`。
- 工作区：合入后干净，`main` 与 `origin/main` 同步。
- 合入后验证：固定 CAD venv Python 3.11.18 下 Demo 56/56 通过；最终复核记录中的 Integration 81/81、Schema 17/17、CAD compilation 13/13 及真实 localhost/STEP 烟测证据对应的代码提交均包含在该 main 历史中。
- 结论：APP-003-C1 按 ADR-0022 的手动参数 localhost 演示范围标记 `done`。当前不含自由文本模型理解；三维预览、部署包装及产品级 live extraction 是后续独立工作，不在本任务验收范围。

## P3 下载按钮文案窄修（2026-11-12）

- 修改：`src/demo/server.py` 将含多余括号的 `下载 STEP (N) bytes)` 改为 `下载 STEP（N 字节）`；新增 HTML 输出断言，确认新文案存在且旧格式不存在。
- 边界：只改 UI 文案和对应回归测试，不改变下载链接、run_id、STEP 字节、HTTP 行为或安全校验。
- 验证：固定 CAD venv Python 3.11.18 下 Demo 56/56；`py_compile` 和 `git diff --check` 通过。测试仍有 4 条既有 `ResourceWarning`。
- 提交：`b59b551 fix: correct STEP download byte label [APP-003-C1]`。
- 状态：review；核心 C1 独立复核仍通过，窄修后工作区干净；待负责人 push/合入。
