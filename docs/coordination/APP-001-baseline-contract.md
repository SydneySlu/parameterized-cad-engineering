# APP-001 基线与评测契约（草案）

状态：`review`；模型输出契约 `app001-io.v1`、Prompt `app001-extraction.v2` 和 evaluator-only `acceptance-set-v0` 已由 Codex 中枢审查并经项目负责人确认冻结。正式运行仍需 adapter/logger 实现及审查、记录运行环境，并由项目负责人明确授权。

## 基线

| 条件 | 模型 | 作用 | 首期环境 |
|---|---|---|---|
| 云端 | 请求模型 ID `deepseek-flash`；官方文档标注版本 `DeepSeek-V4.1-Flash-1017`（运行时仍记录响应 `model`） | 主效果基线 | `https://api.deepseek.com`，OpenAI 兼容 Chat Completions |
| 本地 | Ollama `qwen3:8b`，digest/ID `500a1f067a9f` | 本地部署、成本和延迟对照 | MacBook Air M5，16 GB RAM，512 GB SSD |

云端运行必须分别记录配置的 provider、配置模型名、API 返回的 provider（若有）和 API 返回的 `model` 字段、请求日期、解码参数和客户端版本。当前官方 Chat Completions 示例使用 `model: deepseek-flash`，响应包含 `model`、`usage.prompt_tokens`、`usage.completion_tokens`、`usage.total_tokens`、`usage.prompt_cache_hit_tokens`、`usage.prompt_cache_miss_tokens` 及 `usage.prompt_tokens_details.cached_tokens`；文档示例没有 provider 响应字段，故运行记录中 `runtime_returned_provider` 应为 `not_exposed`，除非实际响应另有提供。endpoint 只记非敏感标识，不记录密钥。若运行时身份与配置标签不一致，保留两者并进入 `review`，不得猜测或静默改名。

密钥只通过环境变量 `DEEPSEEK_API_KEY` 提供。本机开发时可在仓库根目录 `.env` 中填写；该文件由 `.gitignore` 排除。模板为根目录 `.env.example`，模板只含变量名和占位说明，绝不填真实密钥。程序通过 `python-dotenv`（或等效环境加载器）读取 `.env`，API 客户端只从 `os.environ["DEEPSEEK_API_KEY"]` 取值；日志不得打印密钥、Authorization header 或完整请求头。

### DeepSeek API 价目表与调用能力（官方文档快照）

官方价目表于 2026-11-05 核对，价格单位为 CNY/百万 token：

| 时段 | 输入缓存命中 | 输入缓存未命中 | 输出 |
|---|---:|---:|---:|
| 空闲 | ¥0.02 | ¥1.00 | ¥4.00 |
| 高峰 | ¥0.04 | ¥2.00 | ¥8.00 |

北京时间工作日（中国法定节假日除外）09:00–12:00、14:00–18:00 为高峰；其余时间（含周末和法定节假日）为空闲。成本回算必须依据请求时间、响应中的缓存命中/未命中/输出 token 数和该次运行所引用的价目表快照；价目可能变化，不能把本表视为永久费率。

官方文档称 API 支持 JSON 输出及思考/非思考模式，默认开启思考模式。项目负责人已确认首轮云端基线显式关闭思考模式，请求必须包含 `thinking: {"type":"disabled"}`，不能依赖服务默认值。每条运行记录保存实际发送的 thinking setting。seed 已由两次最小运行时探测确认被 API 接受，但这不是输出确定性保证。此项只固定云端 DeepSeek API 参数；本地 Ollama 的运行模式需按其运行时配置单独记录，不得将 DeepSeek API 参数伪装成 Ollama 参数。

2026-11-05 已完成最小 runtime probes：请求配置 `deepseek-flash`，响应 `model=deepseek-flash`；响应包含 usage token 与 cache 字段、无 provider 字段；JSON 模式正常；两次短 seed 探测均被接受。Ollama 0.33.2 的 `/api/chat` 与 `/api/generate` 均接受 `think=false` 和 JSON 输出设置。以上只是能力探测，不是模型质量、时延基准或确定性结论；没有保存回复正文或密钥。详见 [`runtime-probe-2026-11-05.json`](../../agent-work/llm/APP-001-baseline-prep/runtime-probe-2026-11-05.json)。

MacBook Air M5 是首期本地基线。未来 Windows CPU 设备可做迁移和成本探索，但必须单独记录操作系统、CPU、运行时、量化方式和线程配置，不能与 Mac 基线合并计算延迟或吞吐。

## 共同输入和输出

每条输入固定保存：自然语言需求、可选参考图像的文件哈希、是否注入检索示例、Prompt 版本、模型身份和解码参数。模型只能输出结构化意图/参数候选，不输出自由 CAD 代码。

已冻结的模型输出协议版本为 `app001-io.v1` / `app001-extraction.v2`，完整契约见 [`prompt-output-contract-v1.md`](../../agent-work/llm/APP-001-baseline-prep/prompt-output-contract-v1.md)。模型只返回显式参数抽取结果，不生成可直接送入 CAD 的 `cad_parameters`：

```json
{
  "contract_version": "app001-io.v1",
  "prompt_version": "app001-extraction.v2",
  "decision": "answer",
  "extracted_parameters": {},
  "unsupported_requests": [],
  "evidence": [],
  "missing_fields": [],
  "questions": [],
  "confidence": null
}
```

模型只抽取用户明确表达的 CAD-003 参数；`extracted_parameters` 中每个值必须能追溯到输入证据，包括显式但冲突或越界的主张。目录派生值不得由模型生成。用户明确表达的 `second_screw` 主张也须保留，由确定性规则核验；仅在用户未提供时才由阈值规则派生。模型在缺少 `bore_d` 时须追问/拒绝，但仍保留其他显式参数。随后适配器将 `extracted_parameters` 投影为严格 CAD-003 输入并记录独立的验证结果；只有 `decision=answer`、无不支持请求且 CAD-003 通过时才允许继续 Typed CAD IR/CAD。`confidence` 可省略或置为 `null`；不得用于路由、放行或评分。

九条人工验收样例已冻结为 evaluator-only `acceptance-set-v0`。字段抽取只与显式用户主张标签比较；目录/阈值派生结果、追问/拒绝行为和 CAD-003 验证结果分别评分。正式模型运行仍需 adapter/logger 实现并经审查，且由项目负责人另行授权。

## 解码与调用重试

云端与本地使用共同解码设置：`temperature=0`、`top_p=1`、最大输出 `512` tokens。seed 若运行时支持则固定并记录；不支持时记录 `unsupported`，不得因此改变其他参数。每次请求记录实际采用的参数和 provider/runtime 版本。

每个样本最多进行 **2 次重试**（即最多 3 次请求），只对暂时性调用故障重试：连接/读取超时、连接中断、HTTP 429、HTTP 5xx。退避固定为第 1 次重试前 1 秒、第 2 次前 2 秒。认证/权限/请求格式错误、上下文超限、无效 JSON、输出契约错误、Schema/规则拒绝和 CAD 失败均不重试。达到上限仍失败时保留失败样本及总耗时，不删除分母。

## 小型验收集

正式运行前冻结一组人工确认的自然语言样本，至少覆盖：

1. 完整显式描述；
2. 只给 `bore_d`、其余字段由目录规则派生；
3. 单位换算；
4. 缺少 `bore_d` 的追问/拒绝；
5. 显式参数与目录行冲突；
6. `second_screw` 阈值边界；
7. 超出首族支持范围的请求；
8. 检索示例存在但不能直接照抄的请求。

每条样本保存人工真值、允许的派生字段、预期追问/拒绝行为和不可接受的编造字段。样本冻结后，云端和本地条件必须使用同一批输入。

## 指标测量顺序

### APP-001 之前：只冻结口径，不生成结果

- 冻结模型身份、Prompt 版本、输入集、解码参数和日志字段；
- 冻结字段级真值和缺失/冲突处理规则；
- 冻结指标公式和失败分类；
- 确认现有 Schema、Typed CAD IR、CAD 编译器和 STEP 验证器的调用入口。

此阶段的字段抽取、Schema、CAD、STEP 结果均为 `not_measured`。

### APP-001 运行时：测语言和结构化接口

- 字段抽取：逐字段 exact match；数值字段按单位归一化后比较；同时报告显式字段识别和派生字段处理；
- 关键字段识别：缺失 `bore_d` 时是否追问/拒绝；
- 冲突处理：目录冲突、阈值冲突和越界是否拒绝；
- Schema 通过率：模型输出进入 Schema/规则层后通过的样本数 / 总样本数；
- 追问正确率与失败类型。云端记录每次请求及样本汇总的 input/output/total tokens、缓存命中/未命中 input tokens、费用和币种；费用必须来自响应的权威 usage/cost，或按明确版本/日期的 DeepSeek 价目表、请求时段和 token 用量计算并注明来源，无法核实时记 `not_available`，不估算。本地记录每样本墙钟耗时、尝试次数和总耗时，不与云端 token/费用口径混为一项。

### APP-001 输出接入后：测 CAD 和 STEP

对每个模型输出运行同一条确定性链：

```text
模型输出 → Schema/规则 → Typed CAD IR → CadQuery/OCP 构造
         → 实体/族规则验证 → STEP 导出/回读
```

逐级记录：Schema 通过率、IR 接受率、CAD 构造成功率、几何/规则通过率、STEP 回读通过率和失败阶段。只有真正完成 STEP 回读的样本才能计入 STEP 指标；不能把 Schema 通过或检索命中当作 CAD 成功。

### APP-001 之后：才做 C0/C1 下游比较

无检索 C0 与带检索 C1 必须共享模型、Prompt 主体、解码参数、输入集、后处理、Schema、IR、CAD 编译器和验证器。检索额外注入的内容必须单独列出，不能把目录真值直接作为模型输出。公平 C2 仍需另行定义和审查。

## 设备与结果边界

首期结论只覆盖固定模型配置和实际运行设备。模型版本、API 行为、Ollama 版本、量化方式、操作系统或 CAD 运行时变化时，必须新建运行批次并重新记录，不能覆盖旧结果。初始选择已记录在 ADR-0010；输出分层与验收标签冻结见 ADR-0013。正式评测仍被 adapter/logger 实现与审查门及负责人授权门阻止。

