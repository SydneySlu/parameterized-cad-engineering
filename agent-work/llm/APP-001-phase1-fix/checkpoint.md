# APP-001-PHASE1-FIX Checkpoint

**日期**: 2026-11-07
**分支**: cc/APP-001-PHASE1-FIX
**基线**: main @ e1d84a8
**状态**: review

---

## 修复内容

### Part 1: C1 查询契约修复

**问题**: `assemble_c1()` 传递 `{"bore_d": bore_d}` 给 RET-002，但 RET-002 的 flat_parameters 形式要求全部六个冻结字段，导致正式批次中 18 个 C1 全部在请求前阻塞（16 条因 RETRIEVAL_MISSING_FIELD，2 条因无法提取 bore_d）。

**修复**: `src/llm/conditions.py` — `assemble_c1()` 改用 CAD-003 envelope 形式：
```python
query_params = {
    "schema_version": SCHEMA_VERSION,
    "family_id": FAMILY_ID,
    "parameters": {"bore_d": bore_d},
}
```
这样 RET-002 通过 `_normalize_envelope()` 路径，Schema 从 bore_d 推导其余五个字段，无需用户输入或猜测。

**测试**: 新建 `tests/llm/test_conditions.py`（10 项）：
- C0 始终无 reference_context
- C1 有效 bore_d=20mm → 3 个候选，无阻塞
- C1 缺 bore_d → C1_NO_SAFE_QUERY_PARAMETER
- C1 无 retrieval_index → 阻塞
- evaluator-only 标签不污染查询（ref_struct 中 999.0 被忽略，NLI 的 20.0 胜出）
- Chinese NLI "轴孔直径20mm" → 正确提取
- envelope 形式而非 flat_parameters（否则会被 RETRIEVAL_MISSING_FIELD 阻塞）
- reference_context 不含 ground_truth/evaluator 等标签

**已有测试适配**: `tests/llm/test_runner_r1.py` 中 3 个 mock 改为 envelope 形式（`parameters["parameters"]["bore_d"]`）。

### Part 2: DeepSeek usage/token/费用传递链修复

**问题**: 正式批次中 DeepSeek C0 的所有 usage 字段为空（cloud_input_tokens=None 等）。根因：`adapter.py` 中 `_record_cloud_usage_and_cost()` 在 parse 检查之后调用，但所有 C0 在 parse 阶段失败（MISSING_ENVELOPE_KEY），导致提前 return，usage 永远不被记录。

**修复**: `src/llm/adapter.py` — 将 cloud usage/cost 和 local timing 的记录从 parse 之后移到 parse 之前（model_call pass 之后立即记录），确保即使 parse 失败也能捕获 token 和费用数据。

**测试**: `tests/llm/test_adapter.py` 新增 `DeepSeekUsagePropagationTests`（5 项）和 `OllamaUsageUnavailableTests`（2 项）：
- parse 失败时 usage 仍被记录（100/25/125/80/20）
- 完整 usage + cache → cost 被计算
- 缺 cache 字段 → cost 为 None（不猜测）
- cache_hit + cache_miss ≠ prompt_tokens → cost 为 None
- 无 usage → 所有 cloud 字段为 None
- Ollama cloud 字段始终为 None
- Ollama local_wall_time_ms 在 parse 失败时仍被记录

---

## 修改文件

| 文件 | 变更 |
|---|---|
| `src/llm/conditions.py` | `assemble_c1()` 改用 CAD-003 envelope 查询形式 |
| `src/llm/adapter.py` | usage/cost 和 local timing 记录移到 parse 之前 |
| `tests/llm/test_conditions.py` | 新建，10 项 C0/C1 条件组装测试 |
| `tests/llm/test_adapter.py` | 新增 7 项 usage propagation 测试 |
| `tests/llm/test_runner_r1.py` | 3 个 C1 mock 适配 envelope 形式 |

---

## 验证结果（VM Python 3.10.12，PYTHONPATH=src）

```
tests.llm.test_conditions       Ran 10, OK
tests.llm.test_adapter          Ran 21, OK
tests.llm.test_runner_r1        Ran 6, OK  (C1AssemblyNoFixedFallbackTests)
tests/llm discover              Ran 406, OK (skipped=8)
tests/schema discover           Ran 17, OK
py_compile                      OK
git diff --check                CLEAN
```

**用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核上述命令。**

---

## 未解决问题

- 8 个 FUSE lock skip（原有，非本轮引入）
- 验证仅用 Python 3.10.12；用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核
- 正式批次 `app001-phase1-20261107-01` 未被修改，需新批次 ID 重跑才能验证修复效果
- response envelope 与冻结契约不一致（MISSING_ENVELOPE_KEY）仍未修复，属于 Prompt/服务响应契约问题

---

**没有运行正式模型，没有读取或打印 API key，没有修改旧正式批次。**
