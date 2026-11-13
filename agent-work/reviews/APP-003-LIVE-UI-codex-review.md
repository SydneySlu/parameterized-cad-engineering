# APP-003-LIVE-UI Codex 独立复核

日期：2026-11-13  
分支：`cc/APP-003-LIVE-UI`  
提交：`0b8bd7b`  
状态：`review`

## 复核范围

复核受控 `/product-live` 页面、已有 `/api/product-live/*` API 的连接、确认门、阻断和脱敏边界。没有执行真实 provider 请求、没有创建正式 batch，也没有读取密钥或 `.env`。

## 固定环境回归

使用 `work/benchcad-output/venv/bin/python`（Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0）执行：

```text
tests.demo.test_product_live_ui + tests.integration.test_product_live  135/135
tests.demo.test_product_ui + tests.demo.test_product_flow + tests.demo.test_demo_handler  183/183
tests.integration.test_pipeline + tests.integration.test_schema_to_ir  81/81
tests/schema  17/17
tests/cad_compilation  13/13
py_compile  OK
git diff --check  OK
```

仅出现既有 Python 文件句柄 `ResourceWarning` 和 CadQuery/NumPy 上游弃用警告，没有失败或跳过。

## 浏览器证据

在 `127.0.0.1:8766/product-live` 启动注入 `FakeTransport` 和 synthetic envelope 的本地服务：

- P1：页面先显示 `needs_confirmation`；点击确认后显示 `succeeded`、`step_readback`、STEP 148393 bytes 和 SHA-256。浏览器下载文件的 SHA-256 为 `5ead6f40673fb0887b8eaa6172819289a3de76b64ef9c6fb70a66858d8c8c113`，与页面值一致。
- P2：显示 `blocked`、决策 `ask`、缺少 `bore_d` 和问题文本；没有确认按钮或下载入口。
- XSS：需求文本 `<img src=x onerror=alert(1)>` 在确认区显示为文本；DOM `img` 元素数量为 0，未出现 `onerror` 属性。

## 结论

**Pass。** APP-003-LIVE-UI 的离线/本地 CAD 验收通过，允许负责人将该分支合入 `main`。合入前任务保持 `review`；合入后同步 `PROJECT_STATUS.md`、`PROJECT_PLAN.md`、`TASKS.md` 和 checkpoint 为 `done`。

真实 DeepSeek 产品 live 仍需新的 batch scope、预算、preflight 和负责人明确授权，不能由本次 UI 验收推导。
