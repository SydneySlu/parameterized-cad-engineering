# APP-001 v4 formal run script fix — Codex independent review

日期：2026-11-09  
任务：`APP-001-V4-FORMAL-EFFECT-EVALUATION`  
审查提交：`94ab151`（父提交 `6a5ac7c`）  
授权基线：`cc3dfbb`  
审查范围：正式批次启动脚本的提交门、批次目录保护、Ollama runtime 检查和离线测试证据。未启动正式批次。

## 结论

本轮修正**通过独立审查，可进入 push 后的正式批次执行门**。提交 `94ab151` 是授权基线的后代；相对授权生产路径无差异；`preflight()` 真实调用 `ensure_batch_dir_absent()` 和 `check_ollama_runtime()`；本机 Python 3.11.18 下专项测试和编译检查通过。

## 已核对内容

- 仓库根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`
- 当前 `main`：`94ab151`，`origin/main` 仍为 `cc3dfbb`，本地 ahead 2；本轮尚未 push。
- `git diff --name-only cc3dfbb..94ab151` 在 `src/llm/`、`src/retrieval/`、`src/schema/`、`src/cad_compilation/`、冻结 prompt、acceptance set、RET-002 config/manifest 范围内为空。
- `preflight()` 在批次目录检查处调用 `ensure_batch_dir_absent(batch_dir)`，在 runner 启动前调用 `check_ollama_runtime()`。
- `ensure_batch_dir_absent()` 对空目录和含 `runs.jsonl` 的目录均立即 abort，不删除、不覆盖；本地目标正式批次目录不存在。
- `check_ollama_runtime()` 依次检查 `/api/version`、`/api/tags` 和 `qwen3:8b` digest；失败时 abort，成功时返回完整 digest。
- 未调用 DeepSeek/Ollama chat，未启动 runner，未读取或输出本轮审查的密钥值，未修改旧批次。

## 实际验证

```text
Python: /opt/homebrew/bin/python3.11 → Python 3.11.18
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_run_script_v4_batch -v
  → Ran 22 tests in 0.043s, OK
/opt/homebrew/bin/python3.11 -m py_compile scripts/run_app001_v4_formal_batch.py tests/llm/test_run_script_v4_batch.py
  → OK
git diff --check
  → CLEAN
test ! -e work/app001-runs/app001-phase1-v4-20261109-01
  → passed; target batch directory absent
```

专项测试实际覆盖：基线/干净后代/非祖先/生产路径差异拒绝；空批次目录和含 `runs.jsonl` 目录拒绝；Ollama 不可达、模型缺失、digest 不匹配拒绝；正常 Ollama 响应返回 digest；dry-run 36 组合、C0/C1 和两 provider。

## 非阻塞改进项

`test_ollama_unreachable_run_formal_not_called` 当前直接调用 `check_ollama_runtime()`，并未完整执行 `preflight()`；因此它本身不能证明入口级调用顺序。当前源码检查已确认 `preflight()` 在 `build_retrieval_index()` 和 `run_batch()` 之前调用该 helper，实际安全行为没有发现缺陷。后续可补一个注入式 `preflight()` 集成测试，但不阻塞本批次启动。

## 下一步门

1. 将本地 `main` 的 `6a5ac7c`、`94ab151` 推送到远端并核对远端哈希。
2. 保持生产路径、prompt、Schema、预算和授权 scope 不变；在 Mac Python 3.11.18 上运行现有 `scripts/run_app001_v4_formal_batch.py`。
3. 批次完成后由 Codex 独立复核 raw response、预算、模型身份、解析、Schema、决策和失败证据；旧批次只读且不混合统计。

本审查不构成新的模型授权，也不改变 `app001-phase1-v4-20261109-01` 的既有授权范围。
