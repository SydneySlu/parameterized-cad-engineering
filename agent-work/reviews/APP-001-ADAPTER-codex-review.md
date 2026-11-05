# APP-001-ADAPTER Codex 独立审查

- 日期：2026-11-05
- 审查人：Codex 中枢
- 审查范围：`e496ac0` 实现提交及 `9cd1f98` 状态同步提交
- 结论：**review / 需要修正；当前不验收通过，不放行正式 APP-001。**

## 已核实的部分

- 提交范围与交接文档相符：`src/llm/` 双 Provider 请求构造、严格解析、CAD-003 投影、重试、费用/运行记录及 mock 测试均已提交。
- 使用 README 指定命令 `PYTHONPATH=src python3 -m unittest discover -s tests/llm -v`，实测 85 项通过；没有发起网络请求或读取 `.env`。未运行验收集。
- 固定 DeepSeek/Ollama 请求参数分开，抽取与 CAD-003 投影/校验分阶段，IR/CAD/几何/STEP 没有伪报通过。
- 仓库当前 `main` 比 `origin/main` 超前 5 个提交，包含本任务实现和状态提交；没有未提交改动。

直接运行 `python3 -m unittest discover -s tests/llm -v` 会因 `src/` 未进入导入路径而报 19 个 `ModuleNotFoundError: schema`。项目 README 已明确规定 `PYTHONPATH=src` 的运行方式，所以按指定命令通过是有效测试证据，但后续可考虑统一仓库测试入口。

## 必须修正

### 1. Mock 路径会读取并携带环境 API key（高优先级）

`build_deepseek_request()` 在没有显式 key 时调用 `_resolve_deepseek_auth()`，读取 `os.environ["DEEPSEEK_API_KEY"]`；适配器在 fake transport 路径也会调用该 builder。`FakeTransport.send()` 把原始 `PreparedRequest` 存入 `calls`，其中仍含 `authorization`。这与“实现和测试阶段不读取凭据、fake transport 不保留认证值”的任务边界冲突。

复核使用合成变量 `synthetic-test-only`，观察到 `fake_request_has_authorization: True`。没有读取真实 `.env` 或真实 key。

修正要求：mock 请求不读取环境变量、不附带认证；凭据解析应限于未来明确获准的真实传输层。FakeTransport 的记录必须保存脱敏请求副本，任何 `repr`/断言/异常均不得暴露认证值。新增“设置合成环境变量后 mock 调用不读/不保留凭据”的回归测试。

### 2. 正式评测门可由自定义 transport 默认参数绕过（高优先级）

`Adapter.run(..., allow_real_network=False)` 只在显式传入 `True` 时检查正式评测门；默认路径会无条件调用注入的 `transport.send()`。因此任何自定义 HTTP transport 都能在默认参数下执行。代码注释将其称为调用方责任，但实现 Prompt 要求 runnable model entry fail closed。

复核用一个只计数、不访问网络的合成 transport，默认 `allow_real_network=False` 时仍实际调用一次（`custom_transport_calls_with_default_gate_argument: 1`）。

修正要求：在 transport 边界建立不可误用的区分：测试 fake transport 可在评测门关闭时运行；任何可能联网的 transport 必须在网络/凭据访问前被正式评测门拒绝。不能依赖调用方记得传布尔参数；不要添加环境变量绕过开关。以自定义“联网型”哑 transport 测试验证门在 `send()` 前拒绝。

### 3. 缓存 token 缺失时仍虚构费用拆分（高优先级）

`compute_cloud_cost()` 在 `cached_input_tokens` 和 `cache_miss_input_tokens` 同时缺失时，将全部 prompt token 假设成 cache miss 并继续算费；这违反冻结契约中“缓存字段缺失则费用 `not_available`，不估算”的口径。handoff 声称缺字段即 `not_available`，但没有覆盖此情形。

复核传入 prompt=100、output=10、cache hit/miss 均缺失，函数仍返回 `cost_amount=0.00028`、`not_available=false`。

修正要求：只有实际 usage 含完整 cache hit/miss 数值且其它必需 usage 可用时才回算；任一必要值缺失或分配与 prompt 总数不一致时，费用标为 `not_available` 并记录原因。更新现有费用测试及 README/handoff 口径。

### 4. 重试等待没有计入总耗时（高优先级）

`send_with_retry()` 仅累计每次 `transport.send()` 的 duration；注入的 1s/2s backoff 没被 `total_elapsed_ms` 或 Ollama `local_wall_time_ms` 计入。该字段按契约是样本总耗时，会系统性低估有重试样本的本地墙钟时延，也使云端与本地运行记录中的 total elapsed 不完整。

复核模拟首次请求 10 ms、1 秒退避、第二次请求 10 ms：attempt duration 合计 20 ms，但时钟实际经过 1.02 秒。

修正要求：同时保留每次请求 duration 与完整样本 elapsed（含 backoff）；耗时测量起点在第一次请求前，终点在最终返回/失败后。用可注入 clock/sleeper 验证成功重试和耗尽重试的总耗时。

## 还需补齐的契约检查

- 严格 JSON parser 使用 Python `json.loads` 默认解析器，接受标准 JSON 不允许的 `NaN`/`Infinity`；evidence 的 `field`/`quote`/`source` 值类型以及 `missing_fields`、`questions`、`unsupported_requests` 的数组元素类型没有严格校验。复核合成响应中 `outer_d: NaN`、`evidence.field: 7`、`quote: false`、数字 missing field/布尔 question 被 parser 接受。需拒绝非有限数，并逐项校验冻结契约要求的字符串/字段类型。
- 交接声称原始输出按策略保存至忽略目录，但代码中 parser 明确不保留原文，`RunRecord` 无原始响应写入/保留策略实现。正式评测前必须有明确的 opt-in retention 接口或修订文档为“不保存原文，仅 hash/脱敏结构化结果”，不能声称当前已实现 raw-response retention。
- `AdapterInput` 接受任意 system prompt 与 user template，运行记录却固定写 `app001-extraction.v2`，且没有 Prompt hash。为了将来防止记录错标，正式运行入口应从被冻结 artifact 加载 prompt，或至少校验/记录 prompt 内容 hash；这项可以随后续真实运行 transport 接入补齐，但在任何正式样例运行前必须解决。

## 当前状态与下一步

- `APP-001-ADAPTER` 保持 `review`，不能标记 `done`；`APP-001-PREP=review`、`APP-001=planned`、`formal_evaluation_allowed=false` 不变。
- 85 项当前测试通过只说明已有测试覆盖路径通过；上述几个边界未被测到，因此不能据此验收。
- 请 CC 按上述 4 项必须修正及“还需补齐的契约检查”完成窄范围修订，更新测试、README、checkpoint/handoff，再提交修正。修正后由 Codex 中枢重审。
- 修正前不 push/合并实现，不调用 DeepSeek/Ollama，不运行冻结九条样例或正式指标。

## 实际验证命令

```text
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
  → Ran 85 tests, OK

git diff --check
  → PASS（审查开始时工作树干净）

三项合成边界复核
  → fake transport 保留 authorization: True
  → 缓存 hit/miss 缺失仍输出费用: 0.00028
  → 10ms + 1s backoff + 10ms 重试的 elapsed 总计仅记录 20ms
  → 默认参数下任意注入 transport 被调用
  → NaN 与错误 evidence/list 元素类型解析通过
```
