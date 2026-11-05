# APP-001-ADAPTER-R2 Codex 独立复核

- 日期：2026-11-05
- 审查人：Codex 中枢
- 审查范围：`c9abdcb` 实现修正与 `405f933` 状态同步
- 结论：**review / 部分有效，但不验收通过；不得启动正式 APP-001。**

## 已确认有效

- 评测门使用 `type(transport) is FakeTransport`，自定义 `MockTransport` 子类和普通 duck-type transport 会在 `send()` 前被拒绝。
- `_resolve_canonical_path()` 会解析路径并拒绝逃出 canonical `work/app001-runs/` 的路径。用临时符号链接指向外部目录复核，逃逸被拒绝；检查未留下 ignored 临时文件。
- Prompt loader 可读取冻结文件、抽取系统段和用户模板，并将双花括号占位符规范化为 `.format()` 使用的单花括号形式。
- 本次没有调用真实 API、读取密钥或运行冻结验收集。

## 未通过项

### 1. Prompt 校验有公开绕过参数

`Adapter.run(..., verify_frozen_prompt=False)` 是公共参数，调用者可以关闭校验。R2 Prompt 明确禁止新增公共 `skip_verification`/`allow_arbitrary_prompt` 绕过。新增测试还专门证明关闭校验后任意合成 Prompt 能到达 transport；我用 `FakeTransport` 复核，`send()` 调用次数为 1。

此外，`_prompt_loader_path` 也是 `run()` 可传入参数，可将校验目标换成调用者指定的文件。当前 loader 只用“文本中包含 `app001-extraction.v2`”判定版本并返回硬编码版本；没有固定 artifact digest 或严格版本元数据解析。修改 artifact 的正文但保留该字符串，仍可被加载成冻结版本。需要让正式运行 API 无法关闭验证、无法替换 artifact；测试应通过独立的内部 verifier/loader 单元测试或可信依赖注入完成，而不能从生产 `run()` 暴露绕过。

### 2. Retention 的测试专用标记可由普通调用者直接构造

`RetentionPolicy._test_only` 是 dataclass 构造字段；`RetentionPolicy(retain_raw=True, base_dir=<任意路径>, _test_only=True)` 可以直接创建。`Adapter.run()` 遇到此标志时会自动允许测试路径并调用 `_retain_response(..., _allow_test_path=True)`。

我用合成响应在仓库外临时目录复核：即使不调用 `RetentionPolicy.for_test()`，直接设置 `_test_only=True` 也成功写出 raw response。因而“生产路径拒绝 test-only policy”的实现与注释不符。测试标志必须不能由普通公开构造参数伪造；更稳妥的测试方式是只对路径策略/低层 writer 做临时目录单测，生产 Adapter 始终固定 canonical ignored root。

### 3. 交接报告高估测试覆盖

- `test_r2_regression.py` 顶部说明声称覆盖符号链接逃逸，但文件中没有 symlink 测试；当前代码路径经独立临时复核通过，但交接测试清单应准确。
- “artifact 损坏”验证仅覆盖缺失文件，没有覆盖保留版本字符串但正文被篡改的 artifact。
- 不存在生产 API 下真实冻结 Prompt 与 mock transport 完整成功路径的集成测试；已有匹配验证只直接调用 verifier，完整 Adapter 集成采用了关闭校验的测试入口。

## 独立验证

```text
PYTHONPATH=src python3 -m unittest discover -s tests/llm -q
  → 143 tests, OK
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q
  → 17 tests, OK
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py
  → OK
git diff --check
  → PASS
```

附加合成检查：

- 越界 symlink → 拒绝；
- `verify_frozen_prompt=False` + 任意 Prompt + exact `FakeTransport` → send 调用 1 次；
- 手工构造 `_test_only=True` RetentionPolicy + 外部临时目录 → raw response 成功写入；
- 临时 symlink 检查已清理，`git status` 保持干净。

没有真实网络访问、真实凭据读取、真实模型运行、九条验收样例运行或正式指标生成。

## 状态与下一步

- `APP-001-ADAPTER` 维持 `review`；R2 不验收通过。
- `APP-001-PREP=review`、`APP-001=planned`、`formal_evaluation_allowed=false` 保持。
- IR → Typed CAD IR 映射未冻结仍属后续依赖，不是 R2 缺陷，也不得臆造。
- 下一步仅需修复 Prompt 校验入口和 Retention 测试路径伪造，并补齐准确的回归测试/交接记录；中枢复核通过前不启动正式 APP-001。
- 当前本地 `main` 比 `origin/main` 超前 2 个提交，工作树干净；本审查提交尚未 push。
