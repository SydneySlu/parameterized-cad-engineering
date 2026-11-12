# APP-003-C2 checkpoint

- 日期：2026-11-13（执行）
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`review`
- 目标：在 C1 旁边新增离线自然语言产品流程（ADR-0023），实现完整状态机、确认门、run 隔离和安全下载。
- 基线：`main=0210b4e`，分支 `cc/APP-003-C2-NL-PRODUCT-FLOW`，开始时工作区干净。

## 认领记录

- 任务 ID：`APP-003-C2-NL-PRODUCT-FLOW`
- 分支：`cc/APP-003-C2-NL-PRODUCT-FLOW`
- 基线 commit：`0210b4e`
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
