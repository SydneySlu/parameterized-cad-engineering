# APP-001-ADAPTER-R1 Codex 独立复核

- 日期：2026-11-05
- 审查人：Codex 中枢
- 审查范围：`2a324f7` 实现修正及 `a491c94` 状态同步
- 结论：**review / 部分修正有效，但不验收通过；正式 APP-001 仍不得启动。**

## 可确认已修正

- DeepSeek request builder 不再从环境读取 API key；FakeTransport 保存脱敏 request。
- 缺少 cache hit/miss、无效 token 值或 cache split 与 prompt token 不一致时，费用返回 `not_available`。
- 重试返回完整 elapsed，包含注入的 backoff；逐 attempt latency 仍单独记录。
- parser 检查非有限数值、evidence 字段类型和数组元素类型。
- 运行记录有 system prompt、user template、渲染消息的 SHA-256；不把 prompt 原文写入记录。
- raw response retention 有默认关闭策略，并记录 hash/长度及写入失败元数据。

## 尚未通过的验收项

### 1. Mock transport 安全门可由任意子类绕过（高优先级）

当前 `Adapter.run()` 用 `isinstance(self.transport, MockTransport)` 作为唯一放行条件。`MockTransport` 是公开、可继承的普通基类，因此任何自定义 transport 都能继承它并执行任意 `send()`；这违背 R1 prompt 只允许 FakeTransport 在门关闭时运行、未知 transport 必须 fail closed、不能依赖可伪造标记的要求。

合成哑 transport 复核结果：自定义 `MockTransport` 子类在 `formal_evaluation_allowed=false` 时仍进入 `send()`，`send_calls=1`。未进行任何网络访问。

修正方向：closed-gate 下仅放行不可被任意子类冒充的仓库 fake transport（例如精确允许 `FakeTransport` 类型）；所有其它 transport 在读取凭据和调用 `send()` 前拒绝。补充恶意/未知子类回归测试。

### 2. Retention 目录没有被代码限制为 ignored run directory

R1 prompt 要求 opt-in 原始响应仅能写入被忽略的 `work/app001-runs/`。`RetentionPolicy.base_dir` 当前可由调用者指定为任意路径，`_retain_response()` 会直接创建目录并写入。用临时目录进行的合成检查确认，函数接受并成功写入 `work/app001-runs/` 以外的位置。

默认不开启 retention 是正确的，但不等于 opt-in 写入路径受限。需在实现中约束正式 retention 根目录，且保持测试可以安全使用临时目录（可通过明确的测试专用依赖注入实现，不能让正式调用任意指定 tracked path）。增加拒绝仓库 tracked 路径/越界路径的测试。

### 3. Frozen prompt artifact 未在运行时核验（属于本轮范围）

当前代码计算传入 `AdapterInput` 的 prompt hash，但不加载或核对冻结的 `prompt-v2.md`，也不要求 hash 与冻结 artifact 匹配；记录仍固定写 `app001-extraction.v2`。因此任意 prompt/template 仍可能被标成冻结版本。

CC handoff 将其列为未解决项，并建议之后补做。但 R1 prompt 第 4.2 节明确要求“正式运行入口必须能核对冻结 artifact 与版本，或在无法核对时 fail closed”。这不是 R1 以外的工作，也没有报告技术阻塞；目前属于本轮明确要求未完成。应在正式 APP-001 前修复：加载/校验冻结 artifact；或者在校验能力完成前，正式运行入口保持不可通过的 fail-closed 状态，并有测试证明。

## 不属于 R1 验收范围的保留项

- IR 映射仍未冻结：原始 APP-001-ADAPTER Prompt 第 3 节已明确禁止臆造映射，并要求没有已审查 src-level 映射时将 IR/CAD/STEP 保持 blocked/not_run。CC 如实保留该项是正确的；它不阻止本轮适配器层修正验收，但阻止以后声称 CAD/STEP 端到端已测。
- 真实 DeepSeek/Ollama 运行、九条验收集和正式指标：R1 明确禁止，当前未运行是正确的。

## 独立验证

```text
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
  → 121 tests, OK

PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
  → 17 tests, OK

PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py
  → OK

git diff --check
  → PASS
```

此外，仅使用合成哑 transport 验证 `MockTransport` 子类可以在正式门关闭时调用 `send()`；并使用临时目录验证 retention 路径可被配置到 ignored run directory 以外。没有联网、读取凭据或运行冻结验收样例。

## 状态与下一步

- `APP-001-ADAPTER` 维持 `review`，R1 不验收通过。
- `APP-001-PREP=review`、`APP-001=planned`、`formal_evaluation_allowed=false` 继续保持。
- 下一步给 CC 一份窄范围 R2 修正指令，覆盖 transport 子类门控、retention 路径约束和 frozen prompt artifact 核验；修正后由中枢复审。
- 当前本地 `main` 在 R1 两个提交基础上又产生中枢复核提交；尚未 push。
