# APP-001-ADAPTER-R1：修正适配器安全边界与契约缺口

你是 CC 执行 Agent，任务 ID 为 `APP-001-ADAPTER-R1`。本轮只修复 Codex 中枢审查发现的问题，补齐回归测试和交接文档；不重写适配器，不扩展产品功能，不运行正式模型评测。

## 1. 启动与事实源

先确认仓库：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
git log -4 --oneline
```

开始前必须阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_PLAN.md`
- `docs/WORKLOG.md`
- `docs/DECISIONS.md`
- `docs/coordination/handoff-review-protocol.md`
- `agent-work/reviews/APP-001-ADAPTER-codex-review.md`
- `docs/coordination/APP-001-baseline-contract.md`
- `docs/coordination/prompts/APP-001-adapter-logger-cc-agent.md`
- `src/llm/README.md`
- `agent-work/llm/APP-001-adapter/checkpoint.md`
- `agent-work/llm/APP-001-adapter/handoff.md`
- `agent-work/llm/APP-001-baseline-prep/prompt-output-contract-v1.md`
- `agent-work/llm/APP-001-baseline-prep/prompt-v2.md`

若实现与已冻结契约冲突，先记录 `review`/`blocked` 并停止受影响部分；不得自行修改 ADR、验收样例、Schema、IR、CAD 编译器或检索策略。

## 2. 本轮边界

- 只改 `src/llm/`、`tests/llm/`、`src/llm/README.md`、`agent-work/llm/APP-001-adapter/checkpoint.md`、`agent-work/llm/APP-001-adapter/handoff.md` 和必要的 `docs/WORKLOG.md`。
- 不访问、读取、打印或探测 `.env`、真实 API key、Authorization header；不得发起 DeepSeek/Ollama 请求，不得新增或运行可实际联网的 transport。
- 不读取九条冻结验收标签，不运行验收样例，不生成正式指标。所有新增 fixture 必须是手写合成数据。
- 不更改冻结 prompt/协议/样例、ADR、`src/schema/`、IR/CAD 编译或 RET 模块。
- 不删除或覆盖中枢审查记录。修改应保持窄范围并保留可审计历史。
- 完成后创建一个修正 commit，任务状态保持 `review`；不要 push、合并或标记 `done`。

## 3. 必须修复项

### 3.1 mock 路径的密钥隔离与 FakeTransport 脱敏

审查证明当前 `build_deepseek_request()` 会读取 `DEEPSEEK_API_KEY`，而 FakeTransport 保存的请求仍含 Authorization。

- Fake/mock 运行不得读取环境变量、`.env` 或凭据；mock request 不得附带 authorization。
- FakeTransport 的 `calls` / `last_call()` 必须保存脱敏副本，不得留存 authorization 值；`repr`、异常、断言消息和日志同样不得泄露。
- 不在本任务中实现真实凭据装配。未来真实凭据只能在正式评测门已通过之后，由真实 transport 边界按需读取；当前没有运行时授权。
- 新增回归测试：设置合成环境变量并监视环境访问，运行 DeepSeek fake 路径，证明没有读取该变量、request/fake 记录均无认证值。测试结束应恢复环境，不使用真实 key。
- 修正目前反向断言“FakeTransport 会保留 Bearer secret”的测试。

### 3.2 正式评测门必须在 transport 执行前 fail closed

审查证明 `Adapter.run()` 默认会调用任意注入的 transport，`allow_real_network=False` 不是安全边界。

- FakeTransport 可在正式评测门关闭时供单元测试使用。
- 任何非 FakeTransport 的 transport（包括自定义/未知 transport）在门关闭时必须于 `send()` 之前被拒绝；不得靠调用方记得传布尔参数，不得加入环境变量/CLI 绕过项。
- 评测门拒绝必须发生在 credentials/environment lookup 和 transport `send()` 之前。
- 本任务不得打开正式门、不得增设 live HTTP transport，也不得以 class-name 字符串或任意调用者可伪造的标记作为唯一安全判断。
- 用一个不会联网、只记录调用次数的自定义哑 transport 测试：默认调用时门应拒绝，`send_calls == 0`。同时保留 fake transport 可运行的测试。

### 3.3 用量不完整或相互矛盾时不得估算费用

审查证明 cache hit/miss 同时缺失时，当前逻辑会假设全是 cache miss。

- 按冻结价卡回算时，prompt/input token、cache hit、cache miss、output token 等必需 usage 都必须来自实际响应且为有效的非负整数；缺失、类型错误或不一致时费用为 `not_available`，并写稳定、具体的原因。
- 不得用“全部 cache miss”等默认拆分补数。
- 至少校验 `cached_input_tokens + cache_miss_input_tokens == prompt_tokens`；若 API usage 的字段语义让该等式不成立，停止并记录差异，不自行调整定义。
- 补测：两项 cache 字段同时缺失、缺一项、负数/布尔/字符串、与 prompt 总数不一致、完整合法数据。
- 更新 README/handoff 的费用描述，与实现和冻结契约一致。

### 3.4 总耗时包括退避等待

审查证明当前 `total_elapsed_ms` 只累计 request duration，漏掉 1s/2s backoff。

- 保留每次 transport attempt 的耗时字段。
- 增加或调整结果接口，使每样本完整 elapsed 从第一次调用前计时至最终成功/失败，包含所有 backoff；`RunRecord.total_elapsed_ms` 使用该完整 elapsed。Ollama 的本地样本总墙钟时间与其契约口径一致。
- 用可注入 monotonic clock 与 sleeper 测试一次重试成功、两次重试后耗尽：分别验证 request durations、backoff 次数和整体 elapsed。测试不得真实 sleep。
- elapsed 不得简单用 attempt duration 求和。

### 3.5 严格 JSON 与字段类型检查

审查发现默认 `json.loads` 接受 `NaN`/`Infinity`，并漏检 evidence 和若干数组元素类型。

- 拒绝 JSON 标准不接受的 `NaN`、`Infinity`、`-Infinity`。
- 依 `prompt-output-contract-v1.md` 对 evidence 对象的精确键和值类型，以及 `unsupported_requests`、`missing_fields`、`questions` 数组的元素类型逐项验证；不得只检查最外层为 list。
- 数值和 measurement object 的数值必须有限；布尔值不能作为数字。
- 为每一类问题添加合成正/负例测试，包括 `NaN`、正负无穷、错误 evidence field/quote/source 类型、错误数组元素类型、合法边界对象。
- 不自动清洗、转换或修复模型输出。

## 4. 必须澄清并实现的记录契约

### 4.1 原始模型回复保留

现有 README/checkpoint 声称原始响应会保存到忽略目录，但代码并未实现。冻结任务 Prompt 要求原始响应受显式运行时策略控制，正式运行产物落在 Git 忽略的 `work/app001-runs/`。

- 实现明确的 opt-in retention 接口/策略：默认关闭；fake 单测不得写原始回复；当未来正式运行获准且显式启用时，原始响应只可写到 `work/app001-runs/` 下的被忽略路径。
- 不得把原文写进 `RunRecord` JSON、stdout、异常、checkpoint、跟踪文件或 Git；避免错误路径、权限不足时静默声称保存成功。
- 对未保存/已保存/保存失败都记录不含正文的状态与必要元数据。不能落盘时须明确失败并按契约处理，不能把该次运行伪装成完整可复现记录。
- 确认 `work/app001-runs/` 确实被 `.gitignore` 排除；不得在目录中生成或提交真实运行数据。
- 修正 README、checkpoint、handoff 与实现一致。只用合成响应验证策略和路径，不执行正式运行。

### 4.2 记录实际 Prompt hash，避免版本错标

`AdapterInput` 当前允许任意 prompt/template，但运行记录固定写 `app001-extraction.v2` 且无 hash。

- 保留冻结 prompt 版本号，同时在运行记录写入实际 system prompt 与 user prompt template 的 SHA-256；建议另记录最终渲染消息载荷的 hash，以便区分模板与实际输入。
- Hash 应采用文档化、确定性的 UTF-8/JSON 规范化方式，不保存原文到日志。
- 不得声称 arbitrary prompt 就是冻结版本：如果调用内容和冻结 artifact 不同，应通过版本/hash 如实识别；正式运行入口必须能核对冻结 artifact 与版本，或在无法核对时 fail closed。
- 以合成 prompts 验证相同内容 hash 稳定、任何 prompt/template 变更 hash 变化、hash 不泄露 prompt/user 原文。
- 本任务不修改冻结 prompt 本身。

## 5. 交接和文档要求

- 更新 `src/llm/README.md`，确保凭据、评测门、raw response、费用、总耗时和 Prompt hash 的说明逐项与实现一致；删除“从不读取凭据”等不准确描述，精确说明当前 mock-only 行为和未来显式授权流程。
- 更新 checkpoint 与 handoff，追加 R1 内容，不覆盖旧历史。记录原审查缺口逐项如何修复、实际测试命令和结果、未运行项目、剩余风险、提交 hash。
- 按 `docs/coordination/handoff-review-protocol.md` 写完整 `handoff_self_check`。明确本任务没有任何真实 API/Ollama 调用、没有真实凭据读取、没有运行冻结样例。
- 追加 `docs/WORKLOG.md` 记录 task id、commit、动作、验证、状态和下一步。
- 状态仍为 `review`，正式评测门仍为 `false`，`APP-001` 仍为 `planned`。

## 6. 验收命令和交接

运行并逐条记录准确命令和结果，至少包括：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py
git diff --check
```

还需用代码级检查证明：

- 评测门关闭时自定义 transport `send()` 未被调用；FakeTransport 路径仍通过。
- 合成凭据环境变量没有在 mock 路径被读取，且 fake 记录不含认证值。
- 原始响应默认不保留；显式测试策略只写临时/ignored 路径，路径错误或写入失败会如实处理。
- Prompt hash 稳定且随实际 prompt 内容变化。
- 缓存 usage 缺失/不一致时费用为 `not_available`。
- 重试成功和耗尽场景总 elapsed 包含注入的等待。
- parser 拒绝非有限数字及错误元素类型。

完成后提交修正 commit，保持 `review`，不要 push。向项目负责人报告 commit、测试结果、未解决问题及工作树状态，等待 Codex 中枢独立复核；不得启动 APP-001。
