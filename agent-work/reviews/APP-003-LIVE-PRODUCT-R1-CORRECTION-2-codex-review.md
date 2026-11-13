# APP-003-LIVE-PRODUCT-R1-CORRECTION-2 Codex 独立复核

- 复核日期：2026-11-13
- 分支：`cc/APP-003-LIVE-PRODUCT`
- 复核 HEAD：`5c28b96`
- 父提交：`777b42e`
- 结论：`pass`（可合入 `main`；合入前任务保持 `review`）

## 范围

本轮只复核 `_to_repo_relative_path()` 的路径穿越/symlink 逃逸修复及其回归证据。没有创建正式 batch，没有读取 `.env`/密钥，没有发起真实 DeepSeek 请求，也没有改变 `FORMAL_EVALUATION_ALLOWED=False`、A2 scope、预算或历史批次。

## 固定环境验证

解释器：`work/benchcad-output/venv/bin/python`，Python 3.11.18，CadQuery/OCP 固定环境。

实际运行结果：

- `tests.integration.test_product_live`：99/99 通过。
- C1/C2/C3 与 integration 回归（`test_product_flow`、`test_product_ui`、`test_demo_handler`、`test_pipeline`、`test_schema_to_ir`）：264/264 通过。
- Schema：17/17 通过。
- CAD compilation：13/13 通过。
- `py_compile`（product authorization、product live runner、server、product live tests）：通过。
- `git diff --check`：通过。

测试中出现的 ResourceWarning 和 CadQuery/NumPy 上游弃用警告不影响退出结果；没有测试失败或 skip。

## 定向安全复核

直接调用 `_to_repo_relative_path()` 的结果：

- `../../outside/file.step`、`../outside/file.step`、`../../../etc/passwd`：`None`。
- 仓库外绝对路径：`None`。
- 仓库内 symlink 指向仓库外：`None`。
- 合法仓库内绝对/相对路径：转换为 repo-relative 路径。
- `None`、空字符串和 resolve 异常输入：`None`，不回退原字符串。

检查 `FORMAL_EVALUATION_ALLOWED` 仍为 `False`。默认未注入 service 的服务器路径仍由专项测试确认返回 `PRODUCT_LIVE_DISABLED`。

## 本地 HTTP/CAD 烟测

使用注入的 `FakeTransport`（一条固定 synthetic envelope，不发网络）和真实固定 CadQuery：

1. `POST /api/product-live/create`（P1-24mm）返回 `needs_confirmation`，创建阶段未调用 CAD；
2. `POST /api/product-live/confirm/<run_id>` 返回 `succeeded`；
3. `GET /product-live-download/<run_id>` 返回 148393 字节 STEP；
4. 下载字节 SHA-256 为 `087bd5fe3a5f1efef6da35ad21947a41fcb4383d0d291b07e4649427f1635132`，与响应 `ir_index.step_sha256` 一致；
5. FakeTransport 仅有 1 次离线模型 transport 调用；响应没有暴露绝对 `step_path`。

P2/P3/P4 的阻断和零 CAD 路径由 99 项专项与 HTTP 回归覆盖。

## 判断与下一步

本轮窄修满足验收标准，可以合入 `main`。合入后再在 `main` 上复核提交哈希并把 `APP-003-LIVE-SCOPE` 从 `review` 收束；只有负责人另行批准具体 batch ID、live preflight 和真实 provider 请求后，才能跨过产品 live 执行 gate。
