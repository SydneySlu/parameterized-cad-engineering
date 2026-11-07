# APP-001-PHASE1-ENVELOPE-FIX 中枢独立审查

- 审查日期：2026-11-07
- 本地工作树：`cc/APP-001-PHASE1-ENVELOPE-FIX`
- 基线：`16c15ac`
- 结论：`review`；代码修复和测试证据通过定向复核，但尚不可合入或启动新正式批次

## 已确认

- `src/llm/prompt_loader.py` 的最小改动与根因一致：system 段保留 fenced JSON 内容，仅跳过围栏行；因此冻结 envelope 示例中的 `contract_version` 和 `prompt_version` 会进入实际 system prompt。
- 冻结 artifact 未修改。当前 `prompt-v2.md` SHA-256 为 `d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`，与固定锚点一致。
- 当前 loader 输出包含两个版本字段且不含 Markdown fence；system prompt hash 为 `0e457d216bb5a633aece258f647804b0ba9ae3e76a7e48a7e0cce898690ec533`。
- 未发现对正式批次、acceptance set、ADR-0014、C1 逻辑、C2 或 IR/CAD/STEP 的工作树改动。
- 未发起真实模型请求；未读取或输出 API key。

## 中枢复核命令

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_envelope_fix -v`：38 passed
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q`：453 passed，8 skipped（既有 FUSE 环境限制）
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q`：17 passed
- `/opt/homebrew/bin/python3.11 -m py_compile src/llm/prompt_loader.py tests/llm/test_envelope_fix.py`：通过
- `git diff --check`：通过

## 阻塞项

1. 报告声明的 `agent-work/llm/APP-001-PHASE1-ENVELOPE-FIX/checkpoint.md` 在本地不存在，违反交接协议要求的 checkpoint 自检证据。
2. 当前 HEAD 仍为 `16c15ac`；`src/llm/prompt_loader.py`、`tests/llm/test_envelope_fix.py` 和 `docs/WORKLOG.md` 尚未形成 commit，远端分支也未推送。
3. `src/llm/prompt_loader.py::_parse_artifact` 的函数 docstring 仍写着 system JSON 示例“跳过”、system prompt 仅包含 prose，与修复后的行为矛盾。应在同一窄范围提交中更新文档，避免后续交接误判。

## 放行边界

- 该修复可在补齐 checkpoint、修正文档、提交并推送后重新审查。
- 在新提交进入 `main` 且中枢复核通过前，不启动第三个真实批次。
- 即使合入，也只能以新的唯一批次验证 envelope；旧批次 `-01`、`-02` 保留并继续作为诊断证据。
- 当前锁文件由 `com.apple.Virtualization.VirtualMachine` 持有；应先停止持有它的 VM/FUSE 会话，再确认无 git 进程后删除 `.git/index.lock`，不要盲删。

## 下一步

让 CC 仅补齐上述三个交付缺口：生成并提交 checkpoint、修正 `_parse_artifact` docstring、完成 commit/push；不得修改 prompt artifact、正式批次、评测范围或启动真实模型。之后再做一次中枢复核。

