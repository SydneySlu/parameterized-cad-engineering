# A2 受控真实整链 scope 草案

**状态：待项目负责人批准**
**日期：2026-11-11**
**负责人：CC（准备）/ Codex 中枢（复核）/ 项目负责人（批准）**

---

## 目的

本草案描述 `APP-002-INTEGRATION-A2-SCOPE` 任务中拟执行的最小真实模型整链 smoke 测试。这不是完整效果评测，也不代表语言泛化结论；目的是在受控条件下验证"真实 DeepSeek 响应→Schema→IR→CadQuery→几何/STEP"路径是否可端到端通过，并产生可追溯的证据。

---

## 草案 scope

### provider / model

- **Provider**：DeepSeek（已审查配置）
- **Model**：`deepseek-flash`
- **Condition**：C0（无检索上下文），沿用已审查的零样本路径
- **Ollama / qwen3:8b**：不纳入本次最小 smoke；待首次整链通过后由负责人单独授权

### 代表性输入（3 条）

| 输入 ID | 自然语言 | 目的 |
|---|---|---|
| `A2-24mm` | 请按 GN 705 做一个轴环，轴孔直径 24 mm。 | 标准合法孔径，预期 answer+Schema 通过，STEP 成功 |
| `A2-80mm` | 请按 GN 705 做一个轴环，轴孔直径 80 mm。 | 第二螺钉边界（bore_d=80 → second_screw=1），预期 STEP 含第二孔 |
| `A2-ask-bore` | 请按 GN 705 做一个轴环。 | 缺少 bore_d，预期 decision=ask，pipeline 不调用 |

这 3 条是受控合成评测刺激，不代表历史真实用户原话。

### 预算

| 类别 | 上限 |
|---|---|
| 逻辑运行 | 3 |
| 每运行 chat 尝试次数 | 3 |
| 全批最大 HTTP 请求 | 9（= 3 × 3） |
| DeepSeek HTTP 上限 | 9 |

预算说明：每次 HTTP 请求在触网前必须预留账本额度；任何上限先耗尽时 fail-closed。

### 路径与目录

| 类型 | 路径（批次目录下） |
|---|---|
| LLM 账本与 raw 留存 | `work/app001-runs/{batch_id}/` |
| raw 响应 | `work/app001-runs/{batch_id}/raw/` |
| pipeline 运行证据 | `work/app001-runs/{batch_id}/pipeline-runs/` |
| 结果摘要 | `work/app001-runs/{batch_id}/batch_summary.json` |

其中 `work/app001-runs/` 已被 `.gitignore` 排除。batch_id 建议格式：`app002-a2-smoke-YYYYMMDD-NN`，须唯一。

### 错误码与退出码

| 错误码 | 含义 |
|---|---|
| `GATE_MISSING_FIELDS` | missing_fields 不为空，pipeline 不调用 |
| `GATE_UNSUPPORTED` | unsupported_requests 不为空，pipeline 不调用 |
| `TRANSPORT_EXCEPTION` | transport 异常，整个 run 状态=error |
| `NO_RESPONSE` | 重试耗尽无响应 |
| `PARSE_ERROR` | envelope 解析失败 |
| `PIPELINE_EXCEPTION` | pipeline 调用抛出异常 |
| `RAW_NOT_RETAINED` | 正式模式下 raw 未留存，无法调用 pipeline |
| `RAW_READ_ERROR` | 正式模式下 raw 文件读取失败 |
| `INVALID_MOCK_TRANSPORT` | mock 路径收到非 FakeTransport |

**退出码（CLI）**：0=全批运行完毕（个别 run 可能失败）；1=preflight 失败；2=batch 级错误（所有 run 均未启动）。

### 评测限制（需明确告知）

- 只有 3 条受控合成输入，不代表真实用户语言分布或模型泛化能力。
- 本次不测 Ollama；不测 C1 检索路径；不测跨族 Schema。
- 每条输入最多 3 次 transport attempt，不是独立 run。
- 结果仅描述这 3 条在固定 DeepSeek `deepseek-flash` 和 C0 配置下的端到端行为。
- 几何/STEP 通过不等于制造认证；螺纹环形近似限制保留。
- 不宣称测试结论等同于真实用户场景效果。

---

## 进入 live preflight 的前置条件

以下所有项必须通过后，才可在 DeepSeek 执行真实 HTTP：

1. Codex 中枢独立复核本 A2 scope 草案和实现（`a2_authorization.py`、`a2_runner.py`、`test_a2_runner.py`）通过
2. 项目负责人明确批准本 scope 草案，含输入清单、预算和 batch_id 命名格式
3. 项目负责人填写并批准具体 batch_id 和完整授权模板
4. live preflight 在 Mac 固定 Python 3.11.18 环境下通过（`run_a2_batch(dry_run=True)` 和 `run_a2_offline_preflight()` 返回 `ok=True`）
5. `FORMAL_EVALUATION_ALLOWED` 保持 `False`，不得修改

---

## 记录

| 项 | 值 |
|---|---|
| inputs SHA-256 | `d290dc61599237fced58dabf491b1daedeb6dab6fffb8be6b6f068f24ad35f9b` |
| evaluator-labels SHA-256 | `67fe1e68ed27fbaef420846ac2f7eb92abb402b49134a058f676a4bdb965d6e7` |
| profile_id | `app002-integration-a2.v1` |
| 授权 profile 文件 | `src/llm/a2_authorization.py` |
| runner 文件 | `src/integration/a2_runner.py` |
| 测试文件 | `tests/integration/test_a2_runner.py` |
| 本草案文件 | `agent-work/integration/APP-002-INTEGRATION-A2-SCOPE/scope-draft.md` |
