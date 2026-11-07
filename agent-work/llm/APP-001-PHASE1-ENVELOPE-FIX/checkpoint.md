# APP-001-PHASE1-ENVELOPE-FIX checkpoint

状态：`review`
分支：`cc/APP-001-PHASE1-ENVELOPE-FIX`
基线：`16c15ac`（main）
任务：APP-001-PHASE1-ENVELOPE-FIX

## 修改文件

- `src/llm/prompt_loader.py` — `_parse_artifact` system 段落不再剥离 fenced code block 内容（仅移除 ```fence 标记行）；同步修正 docstring 准确描述保留行为
- `tests/llm/test_envelope_fix.py` — 新增 38 项无网络 fixture 回归测试
- `agent-work/llm/APP-001-PHASE1-ENVELOPE-FIX/checkpoint.md` — 本文件
- `docs/WORKLOG.md` — 追加工作记录

未修改：`prompt-v2.md`、`acceptance-set-v0.json`、ADR-0014、C1 查询逻辑、RET-002 规则、A04/A07 评测标签、`contract.py`/`parser.py`/`adapter.py`/`real_transport.py`/`providers.py`/`runner.py`、正式批次 `app001-phase1-20261107-01`/`-02`、C2/IR/CAD/geometry/STEP。

## 实际验证命令

```
/usr/bin/python3 --version                                   → Python 3.10.12（VM 无 python3.11）
PYTHONPATH=src:. /usr/bin/python3 -m unittest tests.llm.test_envelope_fix -v  → Ran 38, OK
PYTHONPATH=src:. /usr/bin/python3 -m unittest discover -s tests/llm -q         → Ran 453, OK (skipped=8)
PYTHONPATH=src:. /usr/bin/python3 -m unittest discover -s tests/schema -q      → Ran 17, OK
PYTHONPATH=src:. /usr/bin/python3 -m py_compile src/llm/prompt_loader.py tests/llm/test_envelope_fix.py  → OK
git diff --check                              → CLEAN
```

修复后确认：`load_frozen_prompt().system_prompt` 含 `contract_version`/`prompt_version` → True；`prompt-v2.md` 文件 hash `d95f853d…` 未变；`system_prompt_sha256` 从 `561904470f…` 变为 `0e457d216b…`（预期，内容变了）。

## 正常案例

`PromptLoaderIncludesEnvelopeExample.test_system_prompt_contains_envelope_json_example`
验证修复后 system prompt 含完整 JSON envelope 示例：
```
"contract_version": "app001-io.v1"
"prompt_version": "app001-extraction.v2"
```
且不含 ```fence 标记。文件 hash 锚点测试确认 artifact 未被修改。

`ParserAcceptsFullEnvelope.test_full_envelope_parses_ok` 验证完整冻结 envelope 被 parser 接受。

`TransportPreservesContentFields.test_deepseek_content_preserves_all_envelope_fields`
验证 DeepSeek Chat Completions 原始 JSON 的 `choices[0].message.content` 经 transport 提取后传给 parser，所有 envelope 字段保留。

`DeepSeekRequestHasJsonObjectConstraint.test_response_format_is_json_object`
验证 DeepSeek 请求含 `response_format: {"type": "json_object"}`。

## 失败案例

`MissingContractVersionFails.test_missing_contract_version_rejected`
缺 `contract_version` 时 fail-closed，返回 `MISSING_ENVELOPE_KEY`，`envelope` 为 `None`。

`MissingPromptVersionFails.test_missing_prompt_version_rejected`
缺 `prompt_version` 时 fail-closed。

`ExtraKeyRejected.test_extra_key_rejected` 多余字段被拒绝（`EXTRA_ENVELOPE_KEY`）。
`WrongContractVersionRejected.test_wrong_contract_version` 错误版本被拒绝（`CONTRACT_VERSION_MISMATCH`）。
`WrongTypeRejected.test_bool_length_field_rejected` 错误类型被拒绝。

`OllamaRequestHasJsonFormat.test_no_deepseek_thinking_field`
验证 Ollama 请求不携带 DeepSeek 专属 `thinking` 字段。

`FixturesAreDesensitised` 验证 fixture 无 API key/Authorization/Bearer/真实用户数据。

## 未解决问题

1. Python 3.11.18 不可用（VM 仅有 3.10.12）。用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核验证命令。
2. 修复未由 Codex 中枢独立复核。
3. 未运行真实模型批次验证——本任务只准备代码、测试和文档，不运行新正式批次。

## 下一步

1. Codex 中枢独立复核：确认修复正确、测试覆盖、prompt artifact 未变、C1 口径未变。
2. 复核通过后，是否启动新正式批次由项目负责人按 ADR-0014 授权；新批次需新批次 ID，不能覆盖 `-01`/`-02`。
3. 新批次仍不运行 C2/IR/CAD/geometry/STEP。
4. 保持 `review` 状态，不自行合入 `main`。
