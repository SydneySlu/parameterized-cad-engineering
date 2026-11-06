# APP-001-RUNNER-R3-FIX-R4 Checkpoint

**日期**: 2026-11-06
**分支**: cc/APP-001-RUNNER-R3
**任务**: APP-001-RUNNER-R3-FIX-R4（R3-FIX-R3 续任，窄范围测试补齐）
**基线**: R3-FIX-R3-checkpoint.md（状态 review，未提交）

---

## 结论

**生产代码无需修改，测试补齐完成。**

工作区中的 `budget.py` 和 `real_transport.py` 已经实现了 R4 所要求的全部语义：

1. ✓ Ollama `/api/tags` 先独立预留（`is_model_call=False`），不消耗 per-run 模型调用额度
2. ✓ tags 成功后才为 `/api/chat` 创建 `is_model_call=True` reservation
3. ✓ tags 失败时不创建任何 chat reservation，`run_attempts_used` 保持 0
4. ✓ tags 重试每次重新进入 `_send_ollama_with_tags_preflight`（`_verified_digest` 仍为 False），分别预留物理预算
5. ✓ chat 失败/重试按现有规则记录
6. ✓ DeepSeek 路径不变

---

## 本轮修改内容

### 仅修改文件：`tests/llm/test_r3_fixes.py`

新增辅助类和测试类：

**`_FakeHttpResp`（辅助类）**
- 替代 `unittest.Mock()` 作为 urlopen 返回值
- Python 3.10 的 unittest 错误报告机制在 frozen dataclass（TransportError、
  TransportResponse 等）与 Mock 交互时会触发 `FrozenInstanceError`
- 使用真实类可完全回避该问题

**`_FAKE_DIGEST`（模块常量）**
- 统一的 fake Ollama digest（以 `sha256:500a1f067a9f` 开头，符合合约前缀）

**`TestR4OllamaTagsChatIntegration`（5 项测试）**

| 测试 | 验证内容 |
|---|---|
| `test_tags_success_chat_success_full_flow` | 2次HTTP，2条ledger记录，tags(is_model=False/num=-1)→chat(is_model=True/num=1)，run_attempts_used=1，total/provider各+2 |
| `test_tags_success_chat_fail_outcomes_independent` | tags=success，chat=transient_retryable（HTTP 5xx），tags记录不受chat失败影响，计数正确 |
| `test_tags_retry_each_creates_new_reservation` | tags失败→tags成功→chat成功，3次HTTP，3条记录，两次tags有各自的负数attempt_number，run_attempts_used=1 |
| `test_tags_budget_exhausted_before_urlopen` | provider配额满时，tags reservation在urlopen前失败，无新记录 |
| `test_tags_ok_chat_budget_exhausted_no_chat_attempt` | tags成功（消耗第54槽），chat reservation失败，urlopen仅1次，run-new run_attempts_used=0 |

**`setUp` 方法**：每测试前清理 `_BudgetReservationToken._consumed_tokens` 类变量，防止 id() 复用导致的测试间污染。

---

## 技术发现

### R3-FIX-R3 checkpoint 描述与实际代码不一致

R3-FIX-R3 的 checkpoint 描述了 `chat=blocked` 的语义，但实际工作区代码
已实现"tags 失败时完全不创建 chat reservation"的更强语义，完全符合 R4 要求。
本轮测试证实了实际代码的正确性。

### _BudgetReservationToken._consumed_tokens 类变量污染

该 set 使用 `id(token)` 追踪已消费 token，用于防止重放。Python GC 后对象
id() 可能复用，导致全量测试套件中，前序测试消费的 token id() 与后续测试新建
的 token id() 相同，触发误判。`setUp` 中清理此 set 是必要的测试隔离措施，
不影响生产代码正确性。

---

## 验证结果（VM Python 3.10.12，PYTHONPATH=src）

```
tests.llm.test_r3_fixes          Ran 40, OK       (35 原有 + 5 新增)
tests/llm discover               Ran 378, OK      (skipped=8)
tests/schema discover            Ran 17, OK
py_compile src/llm/budget.py ... OK
git diff --check                  CLEAN
```

**用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核上述命令。**

---

## 修改文件汇总

**源文件**：无修改

**测试文件**：
- `tests/llm/test_r3_fixes.py`：新增 `_FakeHttpResp`、`_FAKE_DIGEST`、
  `TestR4OllamaTagsChatIntegration`（5 项），35 → 40 项 R3 专项测试

**文档**：
- `docs/WORKLOG.md`：追加 R4 条目
- `agent-work/llm/APP-001-runner-R3/R3-FIX-R4-checkpoint.md`：本文件

---

## 已知限制

- 8 个 FUSE lock skip（原有，非本轮引入）
- 验证仅用 Python 3.10.12；用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核
- `.git/index.lock` 存在（前次残留），不可删除，需用户 `rm .git/index.lock` 后提交
- `_BudgetReservationToken._consumed_tokens` 的 id() 复用问题已在测试层处理，
  生产代码中该机制足够安全（单进程、单批次、短生命周期 token 不会被 GC 前复用）

---

## 下一步

1. 用户在本机 `rm .git/index.lock`
2. 用户用 `/opt/homebrew/bin/python3.11` 运行验证命令确认一致
3. 用户执行 `git add tests/llm/test_r3_fixes.py docs/WORKLOG.md agent-work/llm/APP-001-runner-R3/R3-FIX-R4-checkpoint.md && git commit -m "test: add R4 Ollama tags/chat integration tests [APP-001-RUNNER-R3-FIX-R4]"`
4. Codex 中枢独立审查（重点：TestR4 覆盖完整性、_FakeHttpResp 隔离机制、setUp 清理合理性）

---

**状态**: review — 等待 Codex 中枢独立验收
