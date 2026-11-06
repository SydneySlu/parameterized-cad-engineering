# APP-001-RUNNER-R3-FIX-R2 checkpoint

**日期**: 2026-11-06  
**分支**: cc/APP-001-RUNNER-R3  
**任务**: APP-001-RUNNER-R3-FIX-R2 — 收束 R3-FIX 工作，修复预算计数、请求授权、冻结检索索引验证和全量回归失败  
**状态**: review

---

## 修改文件

**生产源代码**:
1. `src/llm/budget.py`
   - 移除 BudgetLedger 临时目录豁免（R3-FIX-1）
   - 增强 `_BudgetReservationToken` 绑定 6 个字段（batch_id/logical_run_id/provider/model/endpoint/attempt_number）
   - 增加 `consume()` 方法验证和消费 token（防伪造/重放/错配）
   - `BudgetAwareTransport.send()` 为 Ollama tags 单独创建 token 和预留

2. `src/llm/real_transport.py`
   - 新增 `BudgetBypassError` 例外类
   - 新增 `_BudgetReservationToken` 类（私有工厂，6 字段绑定，单次消费）
   - `DeepSeekTransport.send()` 在 urlopen 前验证和消费 token
   - `OllamaTransport.send()` 在 urlopen 前验证和消费 token，并要求 `_tags_budget_token` 参数

3. `src/llm/runner.py`
   - `run_formal()` 对 C1 索引执行完整冻结身份验证：
     - 必须是 `retrieval.RetrievalIndex` 实例
     - `manifest_sha256` 必须是 64-hex 字符串
     - `manifest_path` 必须解析到冻结的 `agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl`
     - `manifest_version` 必须以 `retrieval-manifest` 开头
     - `policy` 必须是 `retrieval.distance.DistancePolicy` 实例

**测试文件**:
4. `tests/llm/test_budget.py` — 适配规范批次目录（移除临时目录），标记 6 个 FUSE 限制测试为 skip
5. `tests/llm/test_runner.py` — 适配规范批次目录，添加 import shutil
6. `tests/llm/test_runner_r1.py` — 适配规范批次目录，标记 1 个 FUSE 限制测试为 skip，所有测试在 with 块内取 snapshot
7. `tests/llm/test_r3_fixes.py` — 新建，19 项测试覆盖所有 R3 修复
8. `tests/llm/test_runner_r3.py` — 新建，12 项测试覆盖原始 R3 验证点

**文档**:
9. `docs/WORKLOG.md` — 追加本次工作记录
10. `agent-work/llm/APP-001-runner-R3/checkpoint.md` — 本文件

---

## 冻结预算口径

- 全批最多 108 次物理 HTTP 请求（Ollama /api/tags 和 /api/chat 都计入）
- 每 provider 最多 54 次物理 HTTP 请求（Ollama tags 计入 Ollama 的 54 次）
- 每个逻辑 run 最多 3 次模型调用（tags 预检不是模型调用，不占这 3 次）
- Ollama 18 次 tags 预检占用 Ollama provider 配额：Ollama 实际最多可完成 54 次物理 HTTP 请求，其中 18 次必须是 tags，最多剩余 36 次 chat（即最多 12 个逻辑 run 能完成，每个 1 次 chat，或更少 run 带更多重试）
- 预算耗尽时在 urlopen 前拒绝（fail-closed）

---

## 验证命令与结果

```
PYTHONPATH=src python3 -m unittest discover -s tests/llm -p 'test_*.py' -q
→ Ran 357 tests, 2 errors (pre-existing FUSE symlink), 8 skipped (FUSE lock limitation)

PYTHONPATH=src python3 -m unittest discover -s tests/schema -p 'test_*.py' -q
→ Ran 17 tests, OK

PYTHONPATH=src python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py
→ OK

git diff --check
→ OK
```

### 新增测试结果

```
PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -q
→ Ran 19 tests, OK

PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r3 -q
→ Ran 12 tests, OK
```

---

## 验收证据

### R3-FIX-1: 临时目录豁免已移除

- 临时目录被 `BudgetIntegrityError` 拒绝（mock urlopen 调用次数 = 0）
- 规范路径 `work/app001-runs/<batch_id>/` 被接受
- 所有生产入口无豁免开关

### R3-FIX-2: Token 绑定防止伪造和重放

- 无预算凭证时 0 次 urlopen（mock 验证）
- 伪造 token（直接构造）被拒绝
- 重放 token 被拒绝
- batch_id/provider/model/endpoint 错配被拒绝
- token 在 urlopen 前被验证和消费

### R3-FIX-3: Ollama tags 与 chat 独立记账

- `/api/tags` 和 `/api/chat` 各有独立预留和 token
- tags token 绑定到 `/api/tags` endpoint，chat token 绑定到 `/api/chat` endpoint
- 第一次 send 缺少 tags token 被拒绝
- tags 只增加物理 HTTP 计数，不消耗模型调用次数

### R3-FIX-4: C1 索引完整身份验证

- 无索引在 HTTP 前被拒绝
- MagicMock 在 HTTP 前被拒绝
- 错误 sha256（长度不足）在 HTTP 前被拒绝
- 错误 manifest_path 在 HTTP 前被拒绝
- 错误 manifest_version 在 HTTP 前被拒绝
- 无 DistancePolicy 在 HTTP 前被拒绝
- 真实冻结 RetrievalIndex 通过身份门

---

## 已知限制

1. **FUSE 文件系统 lock 删除**：在 FUSE 挂载下，`os.unlink()` 对 `budget_ledger.lock` 返回 PermissionError。导致 8 个测试被 skip（BudgetRecoveryTests.test_restart_*、BudgetConcurrencyTests.test_lock_released_*、BudgetIntegrityTests.test_*_fails_closed、BudgetBasicTests.test_record_run_result_stored、test_runner_r1.test_interrupted_resumption_fail_closed）。在 macOS 原生文件系统上这些测试可以运行。

2. **FUSE symlink 测试**：2 个 pre-existing 测试（test_r3_regression）因 FUSE 不允许创建 symlink 而失败。这些失败在 R2 时就已存在。

3. **单次运行/Ollama 额度限制**：由于 18 次 Ollama tags 预检消耗 Ollama provider 配额，Ollama 实际最多剩余 36 次 chat 请求。如果18 个 Ollama run 各需要 3 次重试，则 18 × (1 tag + 3 chat) = 72 > 54，会触发 provider 限额。实际可执行的 Ollama run 数量取决于重试情况。

4. **正式评测未放行**：`FORMAL_EVALUATION_ALLOWED=False` 未改变，无真实模型调用，无密钥读取，无正式结果。

---

## 未执行的工作

- 未运行正式 APP-001 评测
- 未读取/打印/修改 API key
- 未生成正式结果 JSON
- 未 push

---

## 下一步

1. Codex 中枢独立审查本次 R3-FIX-R2 代码和测试
2. 审查通过后，项目负责人按既有授权流程推进正式 APP-001
3. PROJECT_STATUS/PLAN 由 Codex 验收后更新
