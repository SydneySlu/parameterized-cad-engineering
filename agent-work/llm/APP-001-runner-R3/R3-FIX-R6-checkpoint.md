# APP-001-RUNNER-R3-FIX-R6 Checkpoint

**日期**: 2026-11-06
**分支**: cc/APP-001-RUNNER-R3
**任务**: APP-001-RUNNER-R3-FIX-R6（进程内并发领取 reservation 的竞态修复）
**基线**: R3-FIX-R5（所有改动均已包含，未提交）

---

## 修复内容

### 唯一修复目标：进程内线程竞态

**问题诊断**：
R3-FIX-R5 的 `_claim_pending_reservation()` 将 read-modify-write 原子化
写入了磁盘 ledger，但没有进程内互斥保护。两个线程在同一进程内同时执行：
1. 线程 A 读取 ledger → 找到 `claimed=False` 记录
2. 线程 B 读取 ledger → 同一读（两者都看到 `claimed=False`）
3. 线程 A 写入 `claimed=True` → 成功
4. 线程 B 读到旧数据，也写入 `claimed=True` → 竞态成功

或者：
- 线程 A 写 temp 文件，线程 B 也在写，`os.replace()` 后者覆盖前者 → 数据丢失
- 线程 A `_write_ledger_atomic` 中 temp 文件被线程 B 的 `os.replace` 覆盖 → 可能 `FileNotFoundError`

**修复**：
`src/llm/budget.py`：

1. `__init__`：新增 `self._thread_lock = threading.RLock()`
2. 以下四个 read-modify-write 方法用 `with self._thread_lock:` 包裹内部逻辑：
   - `reserve_attempt`
   - `_claim_pending_reservation`
   - `record_outcome`
   - `record_run_result`

保留现有跨进程 batch lock（`acquire_lock`/`release_lock`）不变。

---

## 修改文件（本轮 R6 新增改动）

| 文件 | 变更 |
|---|---|
| `src/llm/budget.py` | `__init__` 新增 `threading.RLock`；四个方法加 `with self._thread_lock:` |
| `tests/llm/test_r3_fixes.py` | 新增 `TestR6TrueConcurrentClaimAtomicity`（2 项真实两线程竞态测试） |

---

## 新增测试覆盖

### TestR6TrueConcurrentClaimAtomicity（2项）

两个线程各持一个独立 token，同一 reservation，用 `threading.Barrier(2)` 确保
同时进入 `_claim_pending_reservation`（通过 token.consume() 调用）。

| 测试 | 验证内容 |
|---|---|
| `test_true_concurrent_claim_only_one_succeeds` | 恰好一个线程成功，另一个抛出 BudgetBypassError；urlopen 为 0（consume 在 HTTP 前拒绝）；ledger 恰好一条 claimed=True |
| `test_true_concurrent_claim_no_json_corruption` | 竞态后 ledger 仍为合法 JSON；_read_ledger() 不抛异常；至多一条 claimed=True；恰好一个线程成功 |

---

## 验证结果（VM Python 3.10.12，PYTHONPATH=src）

```
tests.llm.test_r3_fixes          Ran 51, OK       (49 原有 + 2 新增)
tests/llm discover               Ran 389, OK      (skipped=8)
tests/schema discover            Ran 17, OK
py_compile src/llm/budget.py src/llm/real_transport.py → OK
git diff --check                  CLEAN
```

**用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核上述命令。**

---

## 已暂存文件（git add 成功）

```
A  agent-work/llm/APP-001-runner-R3/R3-FIX-R2-checkpoint.md
A  agent-work/llm/APP-001-runner-R3/R3-FIX-R3-checkpoint.md
A  agent-work/llm/APP-001-runner-R3/R3-FIX-R4-checkpoint.md
A  agent-work/llm/APP-001-runner-R3/R3-FIX-R5-checkpoint.md
M  agent-work/llm/APP-001-runner-R3/handoff.md
M  docs/WORKLOG.md
M  src/llm/budget.py
M  src/llm/real_transport.py
M  src/llm/runner.py
M  src/retrieval/config.py
M  tests/llm/test_r3_fixes.py
M  tests/llm/test_r3_regression.py
```

注：`R3-FIX-R6-checkpoint.md` 创建于 git add 之后，需用户在本机补充 add。

## Git 约束

`.git/index.lock` 由 git add 留下（FUSE 无法清理），需用户 `rm .git/index.lock`
再提交：

```bash
rm .git/index.lock
git add agent-work/llm/APP-001-runner-R3/R3-FIX-R6-checkpoint.md
git commit -m "fix: in-process thread mutex for BudgetLedger concurrent claim (R6) [APP-001-RUNNER-R3-FIX-R6]

- BudgetLedger.__init__: add threading.RLock (_thread_lock)
- Wrap reserve_attempt, record_outcome, record_run_result,
  _claim_pending_reservation with self._thread_lock
- TestR6TrueConcurrentClaimAtomicity: 2 true two-thread race tests
- Include all R2/R3/R4/R5 checkpoint and handoff docs

Verification (Python 3.10.12):
  test_r3_fixes: Ran 51, OK | tests/llm: Ran 389, OK (skipped=8)
  schema: Ran 17, OK | py_compile OK | git diff --check CLEAN"
```

---

## 已知限制

- 8 个 FUSE lock skip（原有，非本轮引入）
- 验证仅用 Python 3.10.12；用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核
- `.git/index.lock` 阻塞 commit；用户需在本机 `rm .git/index.lock` 后提交
- 未运行正式评测，未访问真实 DeepSeek/Ollama API，未读取或打印密钥

---

## 下一步

1. 用户在 Mac 本机 `rm .git/index.lock`
2. 用户用 `python3.11` 复核验证命令
3. 用户执行上述 `git commit`
4. Codex 中枢独立审查（重点：RLock 保护的覆盖范围、与文件锁的关系、测试并发性）
5. 审查通过后按 ADR-0014 既有授权运行 APP-001 第一阶段

---

**状态**: review — 等待用户提交后 Codex 中枢独立验收
