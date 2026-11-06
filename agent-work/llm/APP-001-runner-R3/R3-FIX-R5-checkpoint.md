# APP-001-RUNNER-R3-FIX-R5 Checkpoint

**日期**: 2026-11-06
**分支**: cc/APP-001-RUNNER-R3
**任务**: APP-001-RUNNER-R3-FIX-R5（修复 Codex 独立验收发现的两个阻塞问题）
**基线**: R3-FIX-R4-checkpoint.md（状态 review，未提交）

---

## 修复内容

### Issue A：预算预留原子化 — 单一消费保证

**问题诊断**：
`_verify_pending_reservation()` 是只读操作，不标记"已领取"。两个独立 token
（对同一 reservation 的 logical_run_id/provider/attempt_number/endpoint）都能
通过读操作，导致同一物理 HTTP 预算槽可被两个 token 各自消费。此外
`_consumed_tokens` 类变量用 `id(token)` 追踪已消费 token，Python GC 回收
后 id() 可复用，新创建的有效 token 可能被误拒。

**修复**：
- `src/llm/budget.py`：
  - 将 `_verify_pending_reservation`（只读）改名并重写为 `_claim_pending_reservation`
  - 找到匹配的 `outcome=None, claimed=False` 记录，将 `claimed=True` 写入
    ledger（原子写入，在文件锁保护下）
  - 第二个 token 调用时找不到 `claimed=False` 的记录，抛出 `BudgetBypassError`
  - 错误消息保留 "no pending reservation" 子串以兼容现有测试
  - 新增 `self._locked` 检查防御未加锁调用
- `src/llm/real_transport.py`：
  - 删除 `_consumed_tokens: set[int] = set()` 类变量（id() 复用 bug）
  - `consume()` 步骤 1 只用 `self._consumed`（实例标志）检查同对象重放
  - 步骤 3 调用 `ledger._claim_pending_reservation()` 替代原只读 verify

**结果**：
- 同一 reservation 只能被一个 token 领取（ledger 层原子保证）
- 同一 token 对象不能消费两次（实例 `_consumed` 标志）
- id() 复用问题彻底消除（不再依赖类级 set）
- TestR4 的 `setUp` 中清理 `_consumed_tokens` 的代码已更新为注释

### Issue B：C1 RetrievalIndex 必须匹配冻结配置的 candidate_roles 和 top-k

**问题诊断**：
`run_formal()` 验证了 RetrievalIndex 类型、manifest 身份及 DistancePolicy，
但没有核对 `candidate_roles` 和 `default_top_k`。任何具有正确 sha256/policy
的 index 都能绕过这两项检查。

冻结值（来自 `agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json`）：
- `candidate_roles = ["retrieval_source"]`
- `default_top_k = 3`（`top_k.default`）

**修复**：
- `src/llm/runner.py`：在 step (e) policy.validate() 之后、`resolve_batch_dir()` 之前
  新增 step (f) 和 step (g)：
  - (f) `candidate_roles`：精确比较 `tuple(idx.candidate_roles)` 与冻结配置值；
    缺失、类型错误或不匹配均 fail-closed
  - (g) `default_top_k`：精确比较 `idx.default_top_k` 与冻结配置值（int 类型
    检查，排除 bool）；缺失、类型错误或不匹配均 fail-closed
  - 错误消息分别包含 "candidate_roles" 和 "default_top_k" 关键字

---

## 修改文件

| 文件 | 变更 |
|---|---|
| `src/llm/budget.py` | `_verify_pending_reservation` → `_claim_pending_reservation`（原子写 claimed=True） |
| `src/llm/real_transport.py` | 删除 `_consumed_tokens` 类变量；`consume()` 只用 `self._consumed` |
| `src/llm/runner.py` | 新增 step (f) candidate_roles 检查，step (g) default_top_k 检查 |
| `tests/llm/test_r3_fixes.py` | 新增 `TestR5IssueAReservationAtomicity`（4项）和 `TestR5IssueBCandidateRolesTopK`（5项）；更新 TestR4.setUp |

---

## 验证结果（VM Python 3.10.12，PYTHONPATH=src）

```
tests.llm.test_r3_fixes          Ran 49, OK       (40 原有 + 9 新增)
tests/llm discover               Ran 387, OK      (skipped=8)
tests/schema discover            Ran 17, OK
py_compile                       OK
git diff --check                  CLEAN
```

**用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核上述命令。**

---

## 新增测试覆盖

### TestR5IssueAReservationAtomicity（4项）

| 测试 | 验证内容 |
|---|---|
| `test_second_token_same_reservation_rejected_before_urlopen` | 同一 reservation 两个 token：第一个成功（1 urlopen），第二个在 urlopen 前拒绝（仍 1 urlopen）|
| `test_same_token_replay_rejected_by_instance_flag` | 同一 token 对象消费两次：第二次被 `self._consumed` 拒绝 |
| `test_concurrent_claim_at_most_one_network_call` | 模拟竞争：恰好一个成功，一个拒绝，至多一次 urlopen |
| `test_normal_deepseek_flow_still_works` | 正常 DeepSeek 完整流程仍可工作，`claimed=True` 写入 ledger |

### TestR5IssueBCandidateRolesTopK（5项）

| 测试 | 验证内容 |
|---|---|
| `test_frozen_index_candidate_roles_and_top_k_pass` | 正确值通过 (f)(g) 检查 |
| `test_wrong_candidate_roles_rejected` | 错误 candidate_roles 被拒绝，消息含 "candidate_roles" |
| `test_missing_candidate_roles_rejected` | 缺失属性被拒绝，消息含 "candidate_roles" |
| `test_wrong_default_top_k_rejected` | 错误 top_k 被拒绝，消息含 "default_top_k" |
| `test_missing_default_top_k_rejected` | 缺失属性被拒绝，消息含 "default_top_k" |

---

## 已知限制

- 8 个 FUSE lock skip（原有，原生 macOS 下可运行）
- 验证仅用 Python 3.10.12；用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核
- `.git/index.lock` 由 FUSE 创建，无法删除；用户需在本机 `rm .git/index.lock` 后提交
- 未运行正式评测，未访问真实 DeepSeek/Ollama API

---

## Git 约束

- `.git/index.lock` 存在（FUSE 创建，不可删除）
- 所有修改已写入工作树，可在本机提交

```bash
rm .git/index.lock
git add src/llm/budget.py src/llm/real_transport.py src/llm/runner.py \
        tests/llm/test_r3_fixes.py docs/WORKLOG.md \
        agent-work/llm/APP-001-runner-R3/handoff.md \
        agent-work/llm/APP-001-runner-R3/R3-FIX-R2-checkpoint.md \
        agent-work/llm/APP-001-runner-R3/R3-FIX-R3-checkpoint.md \
        agent-work/llm/APP-001-runner-R3/R3-FIX-R4-checkpoint.md \
        agent-work/llm/APP-001-runner-R3/R3-FIX-R5-checkpoint.md
git commit -m "fix: reservation atomicity (Issue A) and C1 roles/top-k gate (Issue B) [APP-001-RUNNER-R3-FIX-R5]"
```

---

## 下一步

1. 用户 `rm .git/index.lock` 并用 python3.11 复核验证命令
2. 用户执行上述 `git commit`
3. Codex 中枢独立审查（重点：_claim_pending_reservation 原子写入、claimed 字段与 integrity 兼容性、candidate_roles/top_k 精确比较）
4. 审查通过后按 ADR-0014 既有授权运行 APP-001 第一阶段

---

**状态**: review — 等待 Codex 中枢独立验收
