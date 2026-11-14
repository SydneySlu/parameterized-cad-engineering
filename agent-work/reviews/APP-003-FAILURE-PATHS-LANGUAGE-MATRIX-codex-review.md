# APP-003-FAILURE-PATHS-LANGUAGE-MATRIX Codex 复核

- 日期：2026-11-14
- 复核分支：`codex/APP-003-FAILURE-PATHS-LANGUAGE-MATRIX`
- HEAD：`3958ed5`
- 基线：`main=5d46abf`
- 结论：`review`

## 复核范围

本轮只检查失败路径收束补丁、ProductLiveService 的 run identity/API/download 一致性，以及语言矩阵草案的范围边界。没有调用 DeepSeek 或其他模型，没有创建 batch，没有读取 `.env`、API key 或历史 raw 正文。

## 已确认

1. 旧实现对同一 frozen `input_id` 生成固定 `logical_run_id`；离线复现显示第二次 create 会被 `get()` 和下载入口解析为第一次已确认的 STEP。
2. `ProductLiveService.extract()` 现在为每次 create 生成独立 UUID 后缀。`confirm()`、`get()`、`get_step_bytes_secure()` 均继续以返回给客户端的完整 logical run ID 作为键。
3. 新增 unit 和 HTTP E2E 回归：第二次同输入 run 为 `needs_confirmation` 且下载 403；第一次确认 run 仍可下载原 STEP。没有修改正式 Product Live batch runner 的冻结逻辑 ID。
4. 语言矩阵只写入 agent-work 草案，明确 evaluator-only 标签不进入模型输入，候选仍为 DeepSeek/C0/无检索，未冻结、未授权、未执行。

## 实际验证

```text
Python 3.11.18: Product Live 109/109
UI + C1/C2/C3 + pipeline/schema-to-IR: 300/300
Schema: 17/17
CAD compilation: 13/13
target isolation tests: 2/2
py_compile: pass
git diff --check main...HEAD: pass
```

测试输出包含既有 HTTP socket/file `ResourceWarning` 和 CadQuery/pyparsing 弃用警告；没有测试失败。

## 保留事项

- 语言矩阵仍需独立审阅输入意图、预期 decision、预算与标签隔离，不能直接生成 live batch。
- 失败路径盘点提出的非法 patch、pipeline/回读失败 HTTP 组合和泄漏组合测试仍是可选的下一轮补强；当前已有 runner/service 级证据，不把这些建议描述成已验证缺陷。
- 只有完成矩阵审阅、建立新 scope、offline preflight 并取得负责人明确授权后，才能执行新的真实请求。

## 复核结论

本补丁可以在当前离线产品服务边界内继续推进，但任务保持 `review`，不标记 `done`，不合并到 `main`，也不扩大 live 样本。
