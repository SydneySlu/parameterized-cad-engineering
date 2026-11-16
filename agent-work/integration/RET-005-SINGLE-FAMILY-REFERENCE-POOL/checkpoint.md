# RET-005 Single-Family Reference Pool — Checkpoint

**状态**: review  
**基线**: main @ 3d42f20  
**作者**: CC (Claude Code)  
**日期**: 2026-11-17

---

## 任务范围

实现 `set_screw_shaft_collar` 单族受控参考池产品闭环：

- 参考池格式与 allowlist（RET-001 manifest 所有15个 sample_id）
- 3–5 数量限制，安全展示字段，禁止 evaluator labels / held-out 真值 / IR 正文 / STEP 正文 / 源 CAD / raw
- 池内检索（复用 RET-002 DistancePolicy）
- 产品模式和 C1 实验模式共享同一个 context assembler（`pool_context.py`）
- 用户参数优先：从用户文本提取显式参数，冲突时在 CAD 前返回稳定错误
- 确认前零 CAD；确认后每 run 独立 STEP 目录；禁止跨 run 文件访问
- FakeTransport 覆盖所有路径（暂不创建 batch、读取凭据、调用真实模型、改变正式 gate）

---

## 实现产物

### 新增源文件

| 文件 | 描述 |
|------|------|
| `src/retrieval/pool.py` | `ReferencePool`：allowlist 校验、3–5 限制、安全展示、池内检索（`PoolError`、`PoolEntry`） |
| `src/llm/pool_context.py` | 共享 context assembler：`assemble_pool_c0`、`assemble_pool_c1`、`extract_explicit_parameters`、`check_user_param_priority` |
| `src/integration/ret005_pool_runner.py` | `Ret005PoolService`（`extract`/`confirm`/`get`/`get_step_bytes_secure`）、`confirm_pool_run`、`PoolRunState` |

### 新增测试文件

| 文件 | 测试数 |
|------|--------|
| `tests/retrieval/test_ret005_pool.py` | 32 项 |
| `tests/integration/test_ret005_pool_runner.py` | 48 项 |

**合计新增测试**: 80 项

---

## 验证结果（sandbox Python 3.10.12）

```
tests.retrieval.test_ret005_pool        Ran 32 tests  OK
tests.integration.test_ret005_pool_runner  Ran 48 tests  OK
合计: Ran 80 tests in 3.1s — OK
```

**py_compile**: 5 个新文件全部通过  
**git diff --check**: clean（无 trailing whitespace）

受影响的现有测试（全部通过，pre-existing CAD venv failures 不变）：
```
tests.integration.test_ret004_paired_runner   24/24  OK
tests.retrieval.test_retrieval_baseline        28/28  OK（via unittest discover）
tests.schema.test_set_screw_shaft_collar      17/17  OK
tests.llm.test_runner                         73/73  OK
```

`tests.integration.test_pipeline` 中 19 failures + 3 errors 为 pre-existing（需要 CadQuery/OCP venv，沙箱不可用），与 RET-005 实现无关。

---

## 不变量确认

| 检查项 | 结果 |
|--------|------|
| `FORMAL_EVALUATION_ALLOWED` | False，不变 |
| `PROMPT_VERSION` (v5) | 不变 |
| `CONTRACT_VERSION` | 不变 |
| RET-001 manifest sha256 | 不变 |
| RET-002 retrieval-config | 不变 |
| 现有 evaluator-labels.json | 未读取、未暴露 |
| CAD 调用 | 仅在 `confirm_pool_run()` 内，确认后才触发 |
| 正式 batch / credentials | 未创建，未读取 |
| 真实模型请求 | 无 |

---

## 安全与数据边界

- Pool 只显示 `sample_id`、`family_id`、`parameters.normalized`、`validation.final_stage`/`is_valid`、`source.*`（安全字段）
- C1 context 只含 `role=pool_retrieval_source_untrusted_reference`、`sample_id`、`family_id`、`parameters`
- C1 context 包含必选不可信参考声明（`_POOL_UNTRUSTED_NOTE`），不可省略
- `get_step_bytes_secure`：5 层安全检查（run_id 范围、cad_output 目录前缀、无 symlink、非空文件、sha256 校验）
- 每个 confirmed run 写入独立 `<output_root>/<run_id>/` 目录

---

## 下一步

状态保持 `review`，等待 Codex 固定 CAD venv (Python 3.11.18 / CadQuery 2.3.0) 验证和独立只读复核。  
合入前不创建正式 batch、不申请 live 执行授权、不修改正式 gate。
