# APP-001-ADAPTER-R3-FIX Codex 中枢独立验收

日期：2026-11-05  
审查对象：`c0543d6`（实现与测试修正）及 `78e9e4a`（checkpoint 哈希同步）  
审查方式：只读源码复核、独立测试复跑和边界验证；未调用真实 API、未读取真实密钥、未运行九条冻结验收样例。

## 结论

`APP-001-ADAPTER-R3-FIX` 验收通过。R3 审查提出的证据缺口已经关闭，适配器实现、回归测试和说明文档一致。`APP-001-ADAPTER` 可以标记为 `done`。

这只表示双基线适配器的实现和安全边界完成验收，不表示正式 APP-001 已运行，也不表示 CAD/STEP 端到端链路已解锁。

## 独立复核结果

- `test_tampered_artifact_rejected_by_file_hash` 真实创建保留版本标记的篡改文件，调用私有 `_verify_file_hash()`，断言 `FrozenPromptMismatchError`；同时确认篡改哈希与冻结锚点不同。
- `test_symlink_escape_rejected` 和 `test_symlink_escape_rejected_by_retain_response` 实际创建 canonical root 内指向外部临时目录的 symlink，均拒绝越界路径，外部目录保持为空。
- `Adapter.run()` 签名仍无 `verify_frozen_prompt`、`_prompt_loader_path`。
- `RetentionPolicy` 仍无 `_test_only`、`for_test()` 或 `validate_for_production()`。
- README 已准确描述精确 `FakeTransport` 门控、canonical Retention root、symlink 拒绝和无条件 Prompt 校验。
- 独立命令结果：

  ```text
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -q  -> 170 tests, OK
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q -> 17 tests, OK
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py -> OK
  git diff --check -> PASS
  git ls-files work/ -> empty
  ```

工作树在审查开始时干净，当前本地 `main` 仅比 `origin/main` 多 R3-FIX 的两个提交，待负责人 push。

## 保留限制

- `APP-001-PREP` 仍为 `review`，`APP-001` 仍为 `planned`。
- `formal_evaluation_allowed=false`；真实 DeepSeek/Ollama、九条冻结样例和正式字段/CAD/STEP 指标均未运行。
- IR → Typed CAD IR 的 src 级映射仍未冻结，因此 IR/CAD/geometry/STEP 在适配器记录中继续保持 blocked/not_run。
- `prompt_loader` 的双重文件读取 TOCTOU 仍是已记录的 future improvement，不影响当前固定本地 artifact 验收。

## 放行结论

适配器实现可以交给 APP-001 的前置授权审查。启动正式 APP-001 仍需项目负责人单独明确授权，并先确认 APP-001-PREP 的评测样例、模型配置和指标记录方案；本审查不自动授予该授权。
