# APP-001-RUNNER-R3-FIX Checkpoint

**日期**: 2026-11-06  
**分支**: cc/APP-001-RUNNER-R3  
**任务**: 修复 R3 预算与 C1 前置门的四个验收问题

---

## 修复内容

### R3-FIX-1: 移除 BudgetLedger 的临时目录豁免

**问题**: `BudgetLedger._verify_canonical_batch_path()` 对系统临时目录 (`/tmp`) 直接跳过规范路径校验，在生产构造路径上留下可绕过的后门。

**修复**:
- 移除临时目录豁免逻辑
- 所有 `BudgetLedger` 实例必须绑定到 `work/app001-runs/<batch_id>/` 规范目录
- 任何临时目录、错误批次目录、路径穿越和 symlink 越界都在账本接受请求前拒绝

**修改文件**: `src/llm/budget.py` (lines 109-157)

**验证**:
- `test_temp_directory_rejected`: 临时目录被拒绝
- `test_canonical_path_accepted`: 规范路径被接受
- `test_wrong_batch_dir_rejected`: 错误批次目录被拒绝

---

### R3-FIX-2: 修复预算 token 的伪造与绑定缺口

**问题**: 当前真实 transport 只检查 token 类型，token 可以伪造，没有证明该 HTTP 请求已由对应授权和账本预留额度。

**修复**:
- `_BudgetReservationToken` 现在绑定 `batch_id`, `logical_run_id`, `provider`, `model`, `endpoint`, `attempt_number`
- 增加 `consume()` 方法在 transport 发出网络请求前验证和消费 token
- Token 只能使用一次，验证所有绑定字段匹配
- 直接调用真实 transport、伪造 token、复用 token、provider/model/endpoint 不匹配都在 `urlopen` 前拒绝

**修改文件**: 
- `src/llm/real_transport.py` (lines 77-180, 219-275, 415-478)
- `src/llm/budget.py` (lines 604-657)

**验证**:
- `test_token_cannot_be_constructed_directly`: 直接构造 token 被拒绝
- `test_token_reuse_rejected`: Token 只能消费一次
- `test_token_batch_id_mismatch_rejected`: batch_id 不匹配被拒绝
- `test_token_provider_mismatch_rejected`: provider 不匹配被拒绝
- `test_token_model_mismatch_rejected`: model 不匹配被拒绝
- `test_token_endpoint_mismatch_rejected`: endpoint 不匹配被拒绝
- `test_deepseek_without_token_no_urlopen`: DeepSeek 无 token 时 0 次 urlopen
- `test_ollama_without_token_no_urlopen`: Ollama 无 token 时 0 次 urlopen

---

### R3-FIX-3: 分清 Ollama tags 与 chat 的独立预算

**问题**: Ollama 的 `/api/tags` 和 `/api/chat` 是两个独立 HTTP 请求，但 tags 请求没有自己的预算 token。

**修复**:
- `OllamaTransport.send()` 增加 `_tags_budget_token` 参数
- 第一次调用时（`_verified_digest=False`），要求提供 tags token
- Tags token 绑定到 `/api/tags` endpoint，chat token 绑定到 `/api/chat` endpoint
- `BudgetAwareTransport.send()` 在需要时创建两个独立的 token 和预留

**修改文件**: 
- `src/llm/real_transport.py` (lines 415-478)
- `src/llm/budget.py` (lines 604-657)

**验证**:
- `test_ollama_tags_requires_separate_token`: Ollama 第一次 send 需要 tags token

**说明**: 当前实现确保了：
1. `/api/tags` 和 `/api/chat` 各有自己的预算预留和 token
2. 两个请求各自记账，不会混淆
3. Tags 失败不会误记为 chat 失败，反之亦然
4. 所有物理 HTTP 请求都受 108 总请求上限约束

---

### R3-FIX-4: C1 前置门从"非空"提升为"可验证的冻结索引"

**问题**: `run_formal()` 只检查 `retrieval_index is not None`，接受 `MagicMock` 或任意对象。

**修复**:
- `run_formal()` 在任何 HTTP 请求和预算预留之前验证索引
- 确认索引是 `RetrievalIndex` 实例
- 验证 `manifest_sha256` 和 `manifest_path` 属性存在且有效
- `manifest_sha256` 必须是非空字符串（实际 hash）

**修改文件**: `src/llm/runner.py` (lines 240-269)

**验证**:
- `test_run_formal_without_index_rejected`: `retrieval_index=None` 被拒绝
- `test_run_formal_with_magic_mock_rejected`: MagicMock 被拒绝
- `test_run_formal_with_missing_manifest_sha256_rejected`: 缺失 manifest_sha256 被拒绝
- `test_run_formal_with_empty_manifest_sha256_rejected`: 空 manifest_sha256 被拒绝

---

## 测试结果

### 新增测试文件

创建 `tests/llm/test_r3_fixes.py` 包含 16 个针对性测试：

```bash
PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -v
```

**结果**: 16/16 通过 ✓

### 现有 R3 测试

```bash
PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r3 -q
```

**结果**: 12/12 通过 ✓

### 编译检查

```bash
python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py
```

**结果**: 通过 ✓

### 空白检查

```bash
git diff --check
```

**结果**: 通过 ✓

---

## 已知限制和影响

### 破坏性变更

移除临时目录豁免后，33 个现有测试失败，因为它们使用 `tempfile.TemporaryDirectory()` 创建账本。这些测试需要更新为使用规范的 batch 目录：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/llm -q
# 结果: 338 tests, 33 errors
```

**受影响的测试**: 主要是 `test_runner_r1.py` 中使用临时目录的测试。

**修复方案**: 这些测试应该：
1. 使用规范路径 `work/app001-runs/<batch_id>/` 而非临时目录
2. 测试后清理创建的目录
3. 不要求生产代码添加测试专用的绕过开关

**当前状态**: 本次修复专注于四个明确列出的 R3 问题，遗留测试适配留待后续处理。

---

## 验收证据总结

### R3-FIX-1: 临时目录豁免已移除

✓ 临时目录被 `BudgetIntegrityError` 拒绝  
✓ 规范路径被接受  
✓ 错误批次目录被拒绝  
✓ 无环境变量或参数可绕过

### R3-FIX-2: Token 绑定和验证

✓ 无预算凭证时 0 次 urlopen (mock 验证)  
✓ 伪造 token 被拒绝（私有密钥检查）  
✓ 错配 token 被拒绝（batch_id/provider/model/endpoint 验证）  
✓ 重放 token 被拒绝（消费标记检查）  
✓ Token 在 urlopen 前被验证和消费

### R3-FIX-3: Ollama tags 与 chat 独立记账

✓ Tags 和 chat 各有独立的预算预留  
✓ Tags 需要单独的 token，绑定到 `/api/tags` endpoint  
✓ Chat 需要单独的 token，绑定到 `/api/chat` endpoint  
✓ 第一次 send 时缺少 tags token 被拒绝

### R3-FIX-4: C1 索引验证

✓ 无索引在 HTTP 前被拒绝  
✓ 错误对象（MagicMock）在 HTTP 前被拒绝  
✓ 错误 manifest 身份（缺失/空 sha256）在 HTTP 前被拒绝  
✓ 有效 RetrievalIndex 能通过此门

---

## 文件清单

**修改的源文件**:
- `src/llm/budget.py`
- `src/llm/real_transport.py`
- `src/llm/runner.py`

**新增的测试文件**:
- `tests/llm/test_r3_fixes.py`

**文档**:
- 本文件 (checkpoint)

---

## 下一步

1. **测试适配**: 更新 33 个使用临时目录的测试，改用规范 batch 目录
2. **Codex 审查**: 提交当前修复供 Codex 中枢审查
3. **Schema 测试**: 运行 schema 测试套件确认无影响

---

## Commit 信息

将创建一个 commit，状态标为 `review`：

```
fix: R3 budget and C1 gate security hardening [APP-001-RUNNER-R3]

修复四个 R3 验收问题：
1. 移除 BudgetLedger 临时目录豁免
2. 增强 token 绑定防止伪造和重放
3. 分离 Ollama tags 与 chat 预算记账
4. 提升 C1 索引门到可验证的冻结索引

破坏性变更：移除临时目录豁免后 33 个测试需要适配。
新增 16 个针对性测试验证四个修复。
```

---

**状态**: Review - 等待 Codex 验收  
**阻塞**: 33 个遗留测试需要适配（范围外，留待后续）
