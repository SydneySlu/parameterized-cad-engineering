# APP-003-C2 checkpoint

> 当前收束状态：`done`；已合入 `main`，Codex 中枢独立验收完成。下方实现记录保留原始交接时间线；后续验收和合入证据见文末 closeout。

- 日期：2026-11-13（执行）
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`review`
- 目标：在 C1 旁边新增离线自然语言产品流程（ADR-0023），实现完整状态机、确认门、run 隔离和安全下载。
- 基线：`main=0210b4e`，分支 `cc/APP-003-C2-NL-PRODUCT-FLOW`，开始时工作区干净。

## 认领记录

- 任务 ID：`APP-003-C2-NL-PRODUCT-FLOW`
- 分支：`cc/APP-003-C2-NL-PRODUCT-FLOW`
- 基线 commit：`0210b4e`；C2 初始实现 commit：`baba59a`
- 实现边界：ADR-0023；不修改 v5 prompt/contract、Schema、IR、编译器、A2 历史批次；不读取 `.env`/密钥；不发模型或外网请求；`FORMAL_EVALUATION_ALLOWED=False` 不变。

## 新增/修改文件

- `src/demo/product_flow.py`：ProductFlowHandler + ProductRunRecord（新增）
- `src/demo/server.py`：新增 C2 路由（修改）
- `tests/demo/fixtures/c2-answer-bore24.json`（新增）
- `tests/demo/fixtures/c2-ask-missing-bore.json`（新增）
- `tests/demo/fixtures/c2-answer-catalog-conflict.json`（新增）
- `tests/demo/fixtures/c2-answer-unsupported.json`（新增）
- `tests/demo/fixtures/c2-ask-extra-question.json`（新增）
- `tests/demo/fixtures/c2-refuse.json`（新增）
- `tests/demo/fixtures/c2-answer-schema-fail.json`（新增）
- `tests/demo/fixtures/c2-answer-bore80.json`（新增）
- `tests/demo/test_product_flow.py`：35 项测试（新增）
- `docs/WORKLOG.md`（追加）

## 设计要点

### 产品状态机（ADR-0023）

```
request_received → extraction_pending → needs_confirmation | blocked
needs_confirmation → constructing → succeeded | failed
```

- `needs_confirmation`：decision=ask、缺 bore_d、或 answer+预检通过等待用户确认
- `blocked`：refuse、unsupported_requests、目录冲突、解析失败、确认拒绝、stale revision、patch 无效
- `failed`：CAD/STEP 失败（constructing 阶段）
- `succeeded`：整链通过

### 关键约束

1. **确认前零 CAD 调用**：create_product_run 只执行 parse + project + Schema/规则预检，绝不调用 compile_ir
2. **revision 检查**：confirmation_revision 不符 → STALE_REVISION blocked
3. **child run 隔离**：confirm 后创建新 UUID child run，parent run 不可修改
4. **失败不泄漏**：failed run 的 _step_path=None，get_product_step_bytes_secure 返回 None
5. **注册表隔离**：ProductFlowHandler 有独立 _registry，不访问 DemoHandler 的注册表
6. **下载安全**：复用 C1 六层逻辑（UUID 格式 → 注册表 → succeeded → containment → symlink → hash）

### C2 HTTP 路由（不破坏 C1）

```
POST /api/product/create       → {request_text, fixture_id} → ProductRunRecord.as_dict()
POST /api/product/confirm/<run_id> → {confirmation_revision, confirmed, patch} → ProductRunRecord.as_dict()
GET  /api/product/<run_id>     → ProductRunRecord.as_dict()
GET  /product-download/<run_id> → STEP file (security-validated)
```

## 验证结果

执行环境：sandbox Python 3.10.12（非固定 3.11.18，CadQuery 不可用）

```text
py_compile: src/demo/product_flow.py, src/demo/server.py, tests/demo/test_product_flow.py — OK
git diff --check: OK

Product flow tests (35 项，mock CAD):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow -v
  Ran 35 tests — OK

C1 regression (56 项，mock CAD):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -q
  Ran 56 tests — OK

Combined (91 项):
  PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow tests.demo.test_demo_handler -q
  Ran 91 tests — OK

Integration regression:
  PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
  Ran 81 tests — OK

Schema regression:
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
  Ran 17 tests — OK
```

### 测试覆盖

**TestCreateProductRun（12 项）**：
- bore24 → needs_confirmation；ask-missing-bore → needs_confirmation；catalog-conflict → blocked（compile_ir 未调用）；unsupported → blocked；ask-extra-question → needs_confirmation；refuse → blocked；schema-fail（bore25）→ blocked；bore80 → needs_confirmation；extraction_source=synthetic_fixture；unknown fixture_id → blocked

**TestConfirmProductRun（12 项）**：
- bore24 confirm → succeeded（mock）；bore80 confirm → succeeded；stale_revision → blocked；confirmed=False → blocked；unknown run_id → blocked；patch 未知字段 → blocked；patch bore25 → blocked；child run 新 UUID；parent run 保留；CAD 失败 → failed；patch bore16（ask 补参）→ succeeded；blocked run 不可确认

**TestDownloadIsolation（8 项）**：
- succeeded → STEP bytes 可获取且 hash 匹配；failed → None；unknown → None；needs_confirmation → None；非 UUID → is_valid_run_id=False；先成功后失败不泄漏；symlink → None；hash 篡改 → None

**TestNoNetworkNoLLM（3 项）**：
- create 时 compile_ir spy 零调用（全 8 fixture）；无 KEY 读取；不含 real_transport/adapter/runner 导入

**TestRunRecord（2 项）**：as_dict 不含 _step_path/_run_dir；confirmation 字段正确

## 未运行项

- 固定 CAD venv (Python 3.11.18/CadQuery 2.3.0) 下全量测试（真实 compile_ir）
- bore24 HTTP 端到端烟测（需 CadQuery）
- C2 HTTP 路由 HTTP-level 集成测试（server 实例化）

## handoff_self_check

```text
changed=src/demo/product_flow.py (new), src/demo/server.py (C2 routes), tests/demo/fixtures/* (8 JSON), tests/demo/test_product_flow.py (new), agent-work/integration/APP-003-C2/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_flow 35/35 OK; test_demo_handler 56/56 OK; test_pipeline+test_schema_to_ir 81/81 OK; schema 17/17 OK
confirmed=create_product_run never calls compile_ir (spy verified for all 8 fixtures); revision mismatch blocked; child run new UUID, parent preserved; failed runs expose no STEP; download 6-layer security mirrors C1; C1 /api/generate and /download unchanged
unresolved=Codex 中枢在固定 CAD venv (Python 3.11.18) 验证真实构造路径; HTTP 路由端到端测试; C2 完整 UI 展示（当前仅 API，无前端页面）
next_agent_focus=Run under real CadQuery: bore24 confirm → succeeded with real STEP; verify bore80 second_screw=1; verify ask-missing-bore patched with bore_d=16; HTTP smoke test C2 routes; check schema_result/ir_document/validation_summary fields in response
```

## 下一步

- 状态 `review`，等待 Codex 中枢独立验收
- 不 push，不合并 main，不自行标记 done

## Codex 中枢独立验收与合入收束（2026-11-13）

- 最终提交：`d839954`，已合入 `main`；当前本地 `main` 与 `origin/main` 对齐，工作区干净。
- 独立代码复核：父 run 确认前后 `as_dict()` 完全一致；HTTP 确认字段严格类型校验；产品记录提供 fixture hash/path、pipeline run ID/相对目录、STEP 相对路径/hash/bytes；pipeline 抛异常时 child fail-closed。
- 固定环境：Python 3.11.18 / 固定 CAD venv。
- 回归结果：`tests.demo.test_product_flow` 58/58；`tests.demo.test_demo_handler` 56/56；Integration 81/81；Schema 17/17；CAD compilation 13/13；py_compile 和 `git diff --check` 通过。仅有既有 ResourceWarning 与 CadQuery 上游弃用警告。
- 真实离线 CAD 案例：bore24 成功导出并回读 STEP；bore80 `second_screw=1` 成功；ask 缺 bore_d 的 create 阶段无 CAD 输出目录，补充 bore_d=16 后新 run 成功生成 STEP。
- localhost HTTP E2E：create → 5 种非法类型请求均 HTTP 400 且确认处理调用 0 次 → 合法 confirm → GET parent → download child STEP。父 run 保持完全不变；STEP 下载 SHA-256 匹配记录。
- 证据关联核对：fixture envelope hash 与确认后 pipeline envelope hash 不同，二者可区分；pipeline run id/相对目录、STEP 相对路径和 hash 可在 child 响应中追溯；绝对路径不进入 API 响应。
- 边界：仍是 synthetic fixture 驱动的产品流程，不代表真实模型理解或产品 live extraction；当前提供 API，浏览器确认页面另列 APP-003-C3。无真实模型/外网请求、无密钥读取、无 batch。
- `handoff_successor_check`：

```text
predecessor=APP-003-C2-NARROW-FIX, commit d839954, agent-work/integration/APP-003-C2/checkpoint.md
files_format=父 run 不可变、HTTP 字段严格校验、证据字段和 pipeline exception fail-closed 均经代码审读及定向验证
core_rerun=Python 3.11.18 固定 CAD venv：C2 58/58、C1 56/56、Integration 81/81、Schema 17/17、CAD 13/13；py_compile/git diff --check 通过
normal_case=真实 bore24/bore80 STEP 生成和回读通过；HTTP 下载 hash 匹配
failure_case=HTTP 非法类型 400 且零确认调用；ask create 阶段零 CAD；pipeline exception 返回 failed 且无 STEP
interface=ADR-0023 输入、确认、参数来源、pipeline/STEP 关联字段可追溯
limits=仅 synthetic fixtures；无浏览器确认 UI、无真实模型调用；单族与固定环境限制保留
result=pass
blocking_issue=none
```

- 下一步：执行 APP-003-C3-PRODUCT-UI，继续离线夹具范围；完成独立验收后再准备新的产品 live extraction scope。


## 窄修 R1（本提交，APP-003-C2-NARROW-FIX）

### 修复 1：父 run 保持完全不可变（Bug 1）

**问题**：`confirm_product_run()` 在成功确认后直接执行 `parent_rec.confirmation = {...}` 修改了父 run 的字段。

**修复**：删除对 `parent_rec.confirmation` 的所有直接赋值。确认信息（confirmed=True、patch、actor、confirmed_at）仅写入新的 child run record，父 run 的所有字段保持原样不变。

**验证**：新增 `TestParentRunImmutability`（3 项）：compare `parent.as_dict()` before/after confirm；验证 confirmed 仍为 False；验证 pipeline 异常时父 run 也不变。

### 修复 2：HTTP confirm 参数严格类型校验（Bug 2）

**问题**：`_handle_product_confirm` 使用 `int(revision)` 和 `bool(confirmed)` 隐式转换，导致字符串 `"0"` 被转为 `0`，字符串 `"false"` 被 `bool()` 转为 `True`，整数 `0`/`1` 被 `bool()` 接受。

**修复**：在 HTTP handler 中对两个参数均添加严格 isinstance 检查：
- `confirmation_revision`：`isinstance(revision_raw, bool) or not isinstance(revision_raw, int)` → HTTP 400
- `confirmed`：`not isinstance(confirmed_raw, bool)` → HTTP 400

布尔检查先于 int 检查（Python 中 bool 是 int 子类）。

**验证**：新增 `TestHTTPConfirmTypeValidation`（10 项）：覆盖 `confirmed="false"`、`confirmed="true"`、`confirmed=0`、`confirmed=1`、`revision="0"`、`revision="abc"`、`revision=True`，以及合法 `{revision:0, confirmed:true}` 和 `{revision:0, confirmed:false}`；源码中不含 `int(revision` 或 `bool(confirmed`。

### 修复 3：补齐 ADR-0023 产品证据字段（Bug 3）

**问题**：`ProductRunRecord.as_dict()` 缺少 ADR-0023 记录契约中的 fixture provenance 和 pipeline mapping 字段。

**修复**：在 `ProductRunRecord` 中新增五个可选字段（均有默认值 None）：
- `envelope_fixture_path`：fixture JSON 的仓库相对路径
- `envelope_fixture_sha256`：fixture 文件内容的 SHA-256
- `pipeline_run_id`：run_pipeline 返回的内部 run_id
- `pipeline_run_dir_relative`：pipeline run 目录的仓库相对路径
- `step_path_relative`：STEP 文件的仓库相对路径（仅 succeeded）

均在 `as_dict()` 中暴露；绝不暴露绝对路径；`_step_path` / `_run_dir` 仍为 internal。

**验证**：新增 `TestEvidenceFields`（7 项）：验证 fixture_path、fixture_sha256、pipeline_run_id 均非 None；fixture_sha256 匹配真实文件内容；child run 有 step_path_relative 且非绝对路径；failed run 的 step_path_relative=None；as_dict 包含全部新字段。

### 修复 4：pipeline 异常 fail-closed（Bug 4）

**问题**：`run_pipeline()` 的调用外没有 try/except，任何未预期异常都会向上传播而不是 fail-closed。

**修复**：在 `run_pipeline()` 调用外包裹 `try/except Exception`，捕获后设 child run 的 `product_status="failed"`、`pipeline_status="error"`、`pipeline_stage="pipeline_exception"`、`errors=[{code:"PIPELINE_EXCEPTION", ...}]`、`_step_path=None`；父 run 仍不可变。

**验证**：新增 `TestPipelineExceptionFailClosed`（3 项）：RuntimeError → failed；ImportError → failed；任何异常不产生 succeeded；get_product_step_bytes_secure 返回 None。

### 新增测试汇总

| 测试类 | 新增项目数 |
|---|---|
| TestParentRunImmutability | 3 |
| TestHTTPConfirmTypeValidation | 10 |
| TestEvidenceFields | 7 |
| TestPipelineExceptionFailClosed | 3 |
| **合计** | **23** |

### 验证结果（sandbox Python 3.10.12）

```text
py_compile: src/demo/product_flow.py, src/demo/server.py, tests/demo/test_product_flow.py — OK
git diff --check: OK

PYTHONPATH=src:. python3 -m unittest tests.demo.test_product_flow -v
Ran 58 tests (原 35 + 新增 23) — OK

PYTHONPATH=src:. python3 -m unittest tests.demo.test_demo_handler -q
Ran 56 tests — OK (C1 回归无影响)

PYTHONPATH=src:. python3 -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
Ran 81 tests — OK

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
Ran 17 tests — OK
```

### handoff_self_check（R1 更新）

```text
changed=src/demo/product_flow.py (parent immutable + pipeline exception + evidence fields), src/demo/server.py (strict confirm type validation), tests/demo/test_product_flow.py (58 tests), agent-work/integration/APP-003-C2/checkpoint.md, docs/WORKLOG.md
commands=py_compile OK; git diff --check OK; test_product_flow 58/58 OK; test_demo_handler 56/56 OK; test_pipeline+test_schema_to_ir 81/81 OK; schema 17/17 OK
confirmed=parent.as_dict() identical before/after confirm (field-by-field verified); bool(str) coercion now rejected at HTTP layer; pipeline exception caught and returns failed; fixture_sha256 verified against real file content; _step_path/_run_dir still internal; no existing files outside src/demo/ and tests/demo/ modified; FORMAL_EVALUATION_ALLOWED=False unchanged
unresolved=Codex 中枢在固定 CAD venv (Python 3.11.18) 验证真实构造路径；HTTP-level 路由端到端烟测（server 实例化）
next_agent_focus=1) run product flow tests under real CadQuery venv; 2) HTTP smoke: POST create → confirm with valid types → download; 3) verify parent as_dict() unchanged at HTTP layer; 4) verify pipeline_exception path with real import error
```
