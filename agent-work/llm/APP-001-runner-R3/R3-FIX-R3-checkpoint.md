# APP-001-RUNNER-R3-FIX-R3 Checkpoint

**日期**: 2026-11-06
**分支**: cc/APP-001-RUNNER-R3
**任务**: APP-001-RUNNER-R3-FIX-R3（R3-FIX-R2 续任，三项窄范围修正）
**基线**: R3-FIX-R2-checkpoint.md（状态 review，未提交）

---

## 修正内容

本轮仅修改用户明确列出的三个问题，不重新设计 runner，不运行真实 API，不执行正式评测。

### Issue 1：预算 token 必须绑定 logical_run_id

**诊断**: R3-FIX-R2 已实现 token.ledger cross-check（通过 `_verify_pending_reservation`
验证 `logical_run_id/provider/attempt_number/endpoint` 均匹配且 outcome=None），但
缺少 **transport 级 urlopen=0 测试**覆盖 batch/provider/model/endpoint 错配与 token 重放
这 4 个错配场景。`test_r3_fixes.py` 中错配测试仅在 `consume()` 层断言 BudgetBypassError，
未用 `@patch('urllib.request.urlopen')` 证明 `mock_urlopen.call_count == 0`。

**修复**: 新增 `TestR3Fix1TransportLevelMismatch`（5 项测试），每一项通过真实的
`DeepSeekTransport.send(request, _budget_token=token)` 调用，patch urlopen，断言
`mock_urlopen.call_count == 0`：
- batch_id 错配 → "batch_id mismatch"，0 urlopen
- provider 错配 → "provider mismatch"，0 urlopen
- model 错配 → "model mismatch"，0 urlopen
- endpoint 错配 → "endpoint mismatch"，0 urlopen
- token 重放（手动置 `_consumed = True`）→ "already consumed"，0 urlopen

**未改生产代码**: token 绑定逻辑（`consume()` 三步检查 + ledger cross-check）已正确，
本轮仅补齐 transport 级测试证据。

### Issue 2：Ollama tags/chat 必须分别记账且失败状态不能混写

**诊断**: 两处真实 bug：
1. **token 消耗顺序错误**: `OllamaTransport.send()` 先 consume chat token，再 consume
   tags token，再调 `_verify_model_digest()`。若 tags 失败，chat token 已被消耗但 chat
   从未发出，违反 "tags 成功后才允许发送 chat"。
2. **失败状态混写**: `BudgetAwareTransport.send()` 的 `except TransportError` 把同一
   outcome 同时写入 tags 和 chat 两条 reservation。tags 失败时 chat 被错误标记为同一
   HTTP 失败，违反 "chat 不得被记录为同一个 HTTP 失败"、"不得伪造 chat 已发生"。

**修复**:
- `real_transport.py` 新增 `OllamaTagsPreflightError(TransportError)` 标记子类
- `OllamaTransport.send()` 重排顺序：consume(tags) → `_verify_model_digest()` →
  consume(chat) → chat HTTP。tags 失败时包装为 `OllamaTagsPreflightError` 抛出，chat
  token 从未消耗
- `budget.py` `BudgetAwareTransport.send()` 新增 `except OllamaTagsPreflightError`
  （优先于 `except TransportError`）：
  - tags reservation → 实际失败 outcome（按 `is_retryable()` 决定，Ollama 不运行时为
    `non_retryable`）
  - chat reservation → `"blocked"`（沿用项目已有等价状态，表示 chat 未发送/前置阻塞）
- 原 `except TransportError`（chat HTTP 失败）现记录 tags=`success`（tags 已通过才能到
  达 chat 阶段），chat=实际失败 outcome
- `except Exception` 同理：tags 已成功 → `success`，chat → `non_retryable`

**预算口径不变**: tags 仍为 `is_model_call=False`，计入 batch/provider 物理预算，不占
用 logical run 3 次模型调用额度；chat 仍为 `is_model_call=True`。

### Issue 3：C1 检索索引必须匹配冻结 RET-002 配置

**诊断**: R3-FIX-R2 中 `run_formal()` step-(d) 用 `_sha256_file(manifest_path)` 取
**当前磁盘文件 hash** 与 `idx.manifest_sha256` 比较。若有人替换 manifest 文件并重建
index，index 的 sha256 与新文件 hash 同时改变，校验会通过，但与冻结配置记录的预期
sha256（`b7b6c737...`）不一致。要求 "与冻结 RET-002 配置中的预期 SHA-256 一致"。

**修复**: `runner.py` step-(d) 改为加载冻结配置：
```python
_frozen_config = RetrievalConfig.from_path(
    _repo_root / DEFAULT_CONFIG_REL_PATH, repo_root=_repo_root
)
if idx.manifest_sha256 != _frozen_config.manifest_sha256:
    raise FormalEvaluationBlockedError(...)
```
`RetrievalConfig.from_path()` 内部已验证磁盘文件 sha256 与配置 JSON 中记录的预期值
一致（`actual_sha == manifest_sha`），因此一次加载同时建立两条事实链：
1. 磁盘 manifest 文件 hash 与冻结配置预期值一致
2. `idx.manifest_sha256` 与冻结配置预期值一致

**新增测试**: `TestR3Fix3C1PolicyDetails`（3 项）：
- `test_run_formal_with_wrong_policy_ranges_rejected`: 所有 ranges 偏移 +1 →
  `policy.validate()` 抛 `RetrievalError` → `FormalEvaluationBlockedError`
- `test_run_formal_with_wrong_policy_weights_rejected`:
  `continuous_field_weight=0.3`（非冻结 0.2）→ 同上
- `test_run_formal_with_wrong_policy_identity_rejected`: Mock(spec=DistancePolicy)
  的 `validate()` 抛 `RetrievalError` → `FormalEvaluationBlockedError`

三个测试均用真实 manifest sha256 让 step-(d) 通过，再由 policy 校验触发拒绝。使用
项目已有 `DistancePolicy.validate()` 机制，不自行发明 policy identity 值。

---

## 修改文件汇总

**源文件**:
- `src/llm/real_transport.py`: 新增 `OllamaTagsPreflightError`；`OllamaTransport.send()`
  重排 token 消耗顺序（tags first, verify, then chat）
- `src/llm/budget.py`: `BudgetAwareTransport.send()` 新增
  `except OllamaTagsPreflightError`，调整 TransportError/Exception 处理记录独立 outcomes
- `src/llm/runner.py`: step-(d) 改用 `RetrievalConfig.from_path()` 加载冻结配置并比较
  `config.manifest_sha256`；移除 `sha256_file` 导入，新增 `DEFAULT_CONFIG_REL_PATH` 和
  `RetrievalConfig` 导入

**测试文件**:
- `tests/llm/test_r3_fixes.py`: 新增 3 个测试类共 10 项测试
  - `TestR3Fix1TransportLevelMismatch`（5 项）
  - `TestR3Fix2OllamaTagsFailChatBlocked`（2 项）
  - `TestR3Fix3C1PolicyDetails`（3 项）
  - 原 25 项不变，总计 35 项

**文档**:
- `docs/WORKLOG.md`: 追加 R3-FIX-R3 条目
- `agent-work/llm/APP-001-runner-R3/R3-FIX-R3-checkpoint.md`: 本文件

---

## 验证结果

本机 VM 内仅有 Python 3.10.12（`/usr/bin/python3`），无 `/opt/homebrew/bin/python3.11`。
正式验证命令要求使用 Python 3.11.18；用户须在 Mac 本机执行确认一致。

VM 内运行结果（Python 3.10.12，PYTHONPATH=src）：
```
python3 -m unittest tests.llm.test_r3_fixes -q          → Ran 35, OK
python3 -m unittest tests.llm.test_runner_r3 -q          → Ran 12, OK
python3 -m unittest discover -s tests/llm -p 'test_*.py' -q → Ran 373, OK (skipped=8)
python3 -m unittest discover -s tests/schema -p 'test_*.py' -q → Ran 17, OK
python3 -m py_compile src/llm/budget.py src/llm/real_transport.py \
    src/llm/runner.py src/retrieval/config.py           → OK
git diff --check                                          → OK
```

### 8 个 FUSE skip 归类
全部在 `test_budget.py` / `test_runner.py` / `test_runner_r1.py`，原因是 FUSE 文件系统
无法删除 `budget_ledger.lock` 文件。测试逻辑正确，在原生 macOS 文件系统上可运行。已标记
`@unittest.skip("FUSE: cannot delete lock file")`，非本轮改动产生。

### 与 R3-FIX-R2 的测试增量
- R3-FIX-R2: Ran 363, OK (skipped=8) — test_r3_fixes 25 项
- R3-FIX-R3: Ran 373, OK (skipped=8) — test_r3_fixes 35 项（+10 新增）

---

## 实现证据（三点逐条）

### Issue 1 实现
- `real_transport.py:_BudgetReservationToken.consume()` 三步检查链未改：replay →
  field binding（batch/provider/model/endpoint）→ ledger cross-check（含
  `logical_run_id`/`attempt_number`/`endpoint`）
- `budget.py:_verify_pending_reservation()` 未改：ledger 中需存在 matching pending 记录
- 新增 `TestR3Fix1TransportLevelMismatch` 5 项 transport 级测试，全部
  `mock_urlopen.call_count == 0`
- 伪造 token（无 ledger）→ BudgetBypassError "no live ledger reference"，0 urlopen（已有测试
  `test_forged_token_deepseek_no_urlopen`）
- logical run 错配（有 ledger 但无 matching record）→ BudgetBypassError "no pending
  reservation"，0 urlopen（已有测试 `test_token_with_no_matching_ledger_record_rejected`）

### Issue 2 实现
- `real_transport.py:OllamaTransport.send()` 新顺序：先 consume tags token，再
  `_verify_model_digest()`，再 consume chat token
- `OllamaTagsPreflightError` 标记 `TransportError` 子类；tags 失败时 chat token 未消耗
- `budget.py:BudgetAwareTransport.send()` except 顺序：
  `OllamaTagsPreflightError` → `TransportError` → `Exception`
- tags 失败时：tags=non_retryable，chat=blocked（不同 outcome，不同记录）
- tags 成功 chat 失败时：tags=success，chat=transient_retryable 或 non_retryable
- 测试 `test_ollama_tags_fail_urlopen_called_once`: urlopen 恰好 1 次（tags）
- 测试 `test_ollama_tags_fail_outcomes_recorded_independently`: tags=non_retryable，
  chat=blocked，endpoint/attempt_number 各自独立

### Issue 3 实现
- `runner.py:run_formal()` step-(d) 改为 `RetrievalConfig.from_path()` 加载冻结配置
- `_frozen_config.manifest_sha256` 即冻结配置 JSON 中的
  `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`
- `RetrievalConfig.from_path()` 内部 `_verify_integrity` 已校验磁盘文件 sha256 与配置
  预期值一致
- 三个新测试覆盖 wrong ranges / wrong weights / wrong policy identity，全部在 HTTP 前拒绝
- 原有测试 `test_run_formal_with_valid_length_wrong_sha256_rejected` 仍通过：构造
  64-hex 但非冻结值的 sha256，step-(d) 拒绝
- 原有测试 `test_run_formal_with_real_frozen_index_passes_gate` 仍通过：真实
  `RetrievalIndex.from_config(DEFAULT_CONFIG_REL_PATH)` 通过门

---

## 已知限制

- 8 个 FUSE lock skip（已标记，原生 macOS 下可运行，不影响生产代码正确性）
- 验证仅用 Python 3.10.12 运行；用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11`
  再次运行确认一致
- `.git/index.lock` 存在，无法提交（见下方 Git 约束）
- Ollama 18 次 tags 预检仍消耗 provider 物理 HTTP 配额（54 - 18 = 36 次剩余 chat），
  这是 ADR-0014 预算口径的设计决定
- 未访问真实 DeepSeek/Ollama API，未运行正式评测

---

## Git 约束

- `.git/index.lock` 存在（0 字节，由前次 git status 残留，FUSE 无法清理）
- 按 AGENTS.md 约束，不删除 `.git/*lock` 文件，不使用 `GIT_INDEX_FILE`、备用 index、
  reset、rebase 或改写历史
- 所有源码、测试、文档修改已写入工作树，状态与本 checkpoint 一致
- 用户须在本机执行 `rm .git/index.lock && git add <files> && git commit -m "..."`

---

## 下一步

1. 用户在本机 `rm .git/index.lock`
2. 用户用 `/opt/homebrew/bin/python3.11` 运行验证命令确认与 VM Python 3.10 结果一致
3. 用户执行 `git commit`
4. Codex 中枢独立审查本次三项修正（重点：OllamaTagsPreflightError 顺序与 outcome 分离、
   frozen config sha256 比较、transport 级 urlopen=0 测试）
5. 审查通过后项目负责人按 ADR-0014 既有授权运行 APP-001 第一阶段

---

**状态**: review — 等待 Codex 中枢独立验收
