# APP-001-ADAPTER-R3 Codex 中枢独立复核

日期：2026-11-05  
审查对象：本地 `main` 的 `750897d`（R3 实现）与 `5e29cbf`（checkpoint 哈希同步）  
审查方式：只读源码复核、独立命令复跑、临时边界探针；未调用真实 API、未读取真实密钥、未运行冻结验收样例。

## 结论

状态保持 `review`，R3 **条件性通过代码行为，但暂不最终验收**。生产入口的两个已知绕过在当前实现中已关闭，核心回归均通过；交付证据仍有缺口，且 README/项目状态没有同步到 R3。修正这些问题并复审后，才能考虑放行后续 APP-001 前置评估。

## 已复核通过

- `Adapter.run()` 签名只有 `self, adapter_input, run_id`，不再暴露 `verify_frozen_prompt` 或 `_prompt_loader_path`。
- 合成 Prompt 在 transport `send()` 前抛出 `FrozenPromptMismatchError`，`send_calls=0`；真实冻结 Prompt 配合精确类型 `FakeTransport` 可到达 `send()`。
- `FROZEN_PROMPT_FILE_SHA256` 与当前 canonical `prompt-v2.md` 字节摘要一致。
- `RetentionPolicy` 没有 `_test_only` 字段、`for_test()` 工厂或 `validate_for_production()`；外部绝对路径和 `..` 路径被拒绝，raw 文件不写入仓库外目录。
- 临时 symlink 越界探针经 `_resolve_canonical_path()` 被拒绝；该行为尚未由 R3 测试固化。
- 命令复跑结果：

  ```text
  PYTHONPATH=src python3 -m unittest discover -s tests/llm -q  -> 167 tests, OK
  PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar -q -> 17 tests, OK
  PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py -> OK
  git diff --check -> PASS
  ```

## 必须修正后再验收的问题

### 1. 篡改 artifact 测试名与实际覆盖不一致

`tests/llm/test_r3_regression.py::test_tampered_artifact_rejected_by_file_hash` 创建了临时篡改文件，但没有用 loader 读取该文件，也没有安全地替换/恢复 canonical 文件。测试最后只重新读取未篡改的 canonical 文件并比较其原始 hash，因此不能证明“篡改文件被拒绝”。应改为真正调用一个不改变仓库的纯 loader/hash 校验路径，或使用安全的临时 canonical 文件替换并保证异常恢复；测试必须断言篡改内容被拒绝。

### 2. symlink 越界测试缺失

`tests/llm/test_r2_regression.py` 的模块说明声称覆盖 symlink escape，但文件没有实际 symlink 测试，R3 也没有补上。应在可用平台创建 `work/app001-runs/` 内指向临时外部目录的 symlink，调用 `_resolve_canonical_path()` 或 `_retain_response()`，断言拒绝且外部目录为空；不支持 symlink 的平台应明确跳过并记录原因。

### 3. 文档与项目状态未同步

- `src/llm/README.md` 仍写“非 `MockTransport` 子类才拒绝”，当前实际规则是只允许精确类型 `FakeTransport`；Retention 说明也应明确 canonical root 约束和测试私有 writer 边界。
- `docs/PROJECT_STATUS.md` 仍把 R2 缺口写成当前事实，并把“完成 R3”列为下一步。应改为记录 R3 当前为 `review`、上述两项证据/文档缺口，以及正式 APP-001 仍未授权。
- checkpoint/handoff 可以保留 R1/R2 历史，但 R3 当前交接应列出这些缺口，避免下游误以为已最终通过。

## 范围和限制

- IR 到 Typed CAD IR 的 src 级映射仍未冻结，不能由本任务臆造。
- 真实 DeepSeek/Ollama、九条冻结样例和正式字段/CAD/STEP 指标均未运行；`APP-001` 保持 `planned`，正式评测门保持关闭。
- 当前复核不批准 push 后把 `APP-001-ADAPTER` 标记为 `done`。

## 下一步

给原 R3 Agent 一个窄范围收尾任务：修正真实篡改 artifact 测试、补充 symlink 越界测试、更新 README/PROJECT_STATUS/checkpoint/handoff/WORKLOG，重跑上述回归后提交但不 push。中枢随后复审新增证据。
