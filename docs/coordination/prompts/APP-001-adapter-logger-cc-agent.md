# APP-001-ADAPTER：LLM 适配器与分阶段运行记录实现 Prompt

你是本任务的 CC 执行 Agent，任务 ID 为 `APP-001-ADAPTER`。本任务只实现并测试 APP-001 的执行适配器和安全运行记录，不执行正式模型评测。

## 0. 启动与仓库约束

先确认仓库根目录：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
```

必须在共享 Git 仓库中工作。先阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md` 和 `docs/coordination/handoff-review-protocol.md`，再阅读本 Prompt 指定的 APP-001 契约、冻结 Prompt、基线、样例文件及其最近 checkpoint/handoff。当前正式契约以 ADR-0013 和以下文件为准：

- `docs/coordination/APP-001-baseline-contract.md`
- `agent-work/llm/APP-001-baseline-prep/prompt-output-contract-v1.md`
- `agent-work/llm/APP-001-baseline-prep/prompt-v2.md`
- `agent-work/llm/APP-001-baseline-prep/model-baselines-v0.yaml`
- `agent-work/llm/APP-001-baseline-prep/checkpoint.md`
- `agent-work/llm/APP-001-baseline-prep/handoff.md`
- `src/schema/set_screw_shaft_collar.py`
- `src/cad_compilation/`
- `agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json`（只可检查文件结构/版本；标签是真值，不得放入模型输入、测试 prompt 或普通运行日志）

如果本 Prompt 与冻结契约冲突，以冻结契约为准，记录差异并停止受影响的实现；不得自行修改冻结协议。

## 1. 目标与范围

实现可由注入式 transport 测试的双基线执行适配层：

1. DeepSeek `deepseek-flash` Chat Completions 请求适配；
2. Ollama `qwen3:8b` 本地请求适配；
3. 严格解析并校验 `app001-io.v1` / `app001-extraction.v2` 输出；
4. 将模型原始 `extracted_parameters` 独立投影为 CAD-003 正式 envelope，并调用现有 Schema API；
5. 按阶段记录模型调用、解析、契约校验、CAD-003 投影/规则校验以及可选 CAD/STEP 下游阶段的状态与元数据；
6. 提供默认关闭的正式运行门。普通测试和默认命令不得访问网络或读取密钥。

本任务完成后应能用 mock transport 对正常响应、协议错误、瞬时故障重试和非重试错误做完整验证，并能输出不含秘密的结构化运行记录。

## 2. 强制安全边界

- **不得调用真实 DeepSeek API 或 Ollama，不得进行 runtime probe。** 不得访问或打印 `.env`、API key、Authorization header，也不得用凭据探测连接。测试一律使用注入的 fake/mock transport。
- **不得运行九条冻结验收样例或从中复制任何标签。** 不得生成正式效果、成本、延迟、字段抽取、Schema、CAD、几何或 STEP 指标；正式结果保持 `not_measured`。
- 正式评测门必须默认关闭。任何可运行模型的 CLI/API 入口都必须 fail closed；除非后续另有项目负责人授权，本任务不添加能绕过评测门的参数或环境变量。
- 密钥只允许在未来获准运行时从 `DEEPSEEK_API_KEY` 或安全运行环境读取，并仅进入请求认证头。禁止出现在日志、异常、repr、测试快照或提交文件中。Ollama 本地调用不得要求云端密钥。
- 原始模型回复可能包含用户输入或不合规内容：运行产物默认写到 Git 忽略的 `work/app001-runs/`；不要将原始请求、原始回复、私有数据或生成的 CAD/STEP 文件提交。跟踪文件仅包含合成 fixture、代码、测试和不含敏感内容的模板/说明。
- 不记录完整 provider 错误 body、请求头、Authorization、隐藏思维内容或未经批准的用户原文。稳定错误 code/stage/fields 与必要的脱敏摘要足够。

## 3. 先做接口盘点；遇到缺口不得造接口

实现前先完成简短的 M0 接口核对并记录到本任务 checkpoint：

- Python 兼容性和现有测试运行方式；避免无必要的新依赖；
- DeepSeek 及 Ollama 的冻结请求参数、响应字段和重试契约；
- `validate_parameters` / `validate_json` / `resolve_parameters` 的真实签名与返回结构；
- CAD 编译器入口、IR 示例与已接受的参数→IR 映射是否存在。

当前已知 Schema API 在 `src/schema/set_screw_shaft_collar.py`；CAD 编译入口为 `cad_compilation.compile_ir(raw, output_dir=...)`。**不要臆造参数到 IR 的映射。** 如果仓库没有已审查、可由六个 CAD-003 字段生成的正式 IR 映射：

- 实现到 CAD-003 的抽取/投影/验证阶段；
- 在运行记录中明确 `ir/cad/step.status = not_run` 或 `blocked_no_approved_ir_mapping`；
- 保持 CAD/STEP 钩子为明确接口或只读阶段记录；
- 在 handoff 报告中指出需要 Codex 中枢先冻结映射契约，不能生成临时 IR 来声称端到端已通。

不得修改 Schema、IR、CAD 编译器、容差策略、检索策略、冻结样例真值或 ADR 来迁就适配器。发现现有接口不一致时，记录 review/blocked 并只完成不依赖争议接口的部分。

## 4. 冻结行为必须精确保留

### 模型输入与输出

- 输入严格遵守冻结 Prompt：`query_id`、固定 `family_id`、原始自然语言输入、可空 reference context。C0 无检索；如实现 C1 输入结构，只允许显式传入 RET-002 候选的 reference-only 字段。不得把 evaluator 标签、held-out truth、目录行、预期答案、IR/CAD/STEP 或私有源样本注入模型。
- 使用固定系统 Prompt `prompt-v2.md`；不要复制或重写成另一个版本。保存 prompt/contract 版本及输入/context hash。
- 模型输出只允许冻结 envelope 的键和值；严格验证 UTF-8 JSON 对象、精确键集合、版本字面量、decision enum、各字段类型及 evidence entry。额外文字、代码围栏、多个 JSON、缺字段、额外键、错误 enum/type 都是 protocol failure；不得自动清理或修复后再评分。
- `confidence` 只原样记录诊断值（契约要求 null；若不符则 contract failure），不得参与路由、重试、放行或评分。
- 即使 decision 为 ask/refuse、含 unsupported request、字段缺失或规则冲突，也保留模型显式抽取字段和可审计阶段结果；不得因此丢失抽取记录。

### CAD-003 确定性投影

- 将显式 `extracted_parameters` 映射到且只映射到 `{ "schema_version": "set_screw_shaft_collar.v0", "family_id": "set_screw_shaft_collar", "parameters": {...} }`。拒绝未知参数键，不把 catalog/规则派生值注入模型抽取层。
- 使用现有 schema API 进行归一化、目录耦合、缺失字段和规则判断；记录原始抽取、投影 payload、Schema 结果为三个不同阶段。
- Schema 失败时仍保留 extraction 评分所需的显式字段，但不可进入 IR/CAD。只有 `decision=answer`、`unsupported_requests` 为空且 CAD-003 校验通过才标记 `construction_ready=true`。
- 不将 schema pass 宣称为 IR/CAD/几何/STEP 成功。

### 双 Provider 与重试

- DeepSeek：配置名 `DeepSeek`、请求模型 `deepseek-flash`、OpenAI-compatible Base URL `https://api.deepseek.com`；显式发送 `thinking: {"type":"disabled"}`。请求参数遵守冻结 YAML：temperature 0、top_p 1、max output 512、seed 271828、JSON mode（使用已确认的 API 字段名）。记录 configured provider/model 与 runtime response provider/model 分开；响应未提供 provider 时记 `not_exposed`。
- Ollama：模型 `qwen3:8b`、digest `500a1f067a9f`；使用已核验的 Ollama API 和 `think=false`、JSON format、temperature 0、top_p 1、num_predict 512、seed 271828（若既有配置对字段名/有效设置有不同明文定义，以冻结配置为准并记录实际值）。不可把 DeepSeek 专属 thinking 参数发给 Ollama，也不可宣称两者语义等价。
- 每个 query 初始调用加最多 2 次重试，只重试连接/读取超时、连接中断、HTTP 429、HTTP 5xx；固定退避 1 秒、2 秒。测试中注入 sleeper/clock，不能让单测真实等待。认证/权限、错误请求、上下文超限、无效 JSON、契约/Schema/规则/CAD 失败不重试。
- 保存逐 attempt 记录及累计 attempt count、total elapsed。云端 usage 记录 prompt/completion/total 与 cache hit/miss tokens；费用只按已冻结价卡和请求时段从实际 usage 计算，缺字段则 `not_available`。本地只记录每样本推理 wall time；云端 token/cost 字段标记 not applicable。不能将 mock usage 写成实测。

## 5. 实现和文件布局

- Python 运行时代码放 `src/llm/`；测试放 `tests/llm/`；任务 checkpoint/handoff 与说明放 `agent-work/llm/APP-001-adapter/`。
- 项目暂无明显的 packaging/依赖声明。优先使用标准库；如果必须添加依赖，先记录必要性、版本和兼容影响，避免为了 HTTP 客户端引入重型依赖。可以采用可注入 transport；真实 HTTP transport 代码可以实现，但不得在本任务运行。
- 运行记录使用带版本的 JSON/JSONL 数据结构，至少保留：run/query/condition ID、UTC 时间、configured/runtime identities、model digest、contract/prompt versions、input/context hash、实际 decoding/runtime settings、软件版本、逐 attempt latency/状态、解析/契约/Schema 状态、Schema 错误 code/stage/fields、construction_ready、usage/cost/local latency、稳定失败 code/stage/fields、IR/CAD/geometry/STEP 状态。
- 每层状态必须能区分 `not_run`、`pass`、`fail`、`blocked`、`not_applicable`；不得用一个总体 boolean 隐去阶段失败。记录中不得写 `STEP pass` 等未执行结论。
- 支持安全的脱敏/保留策略：原始响应由显式运行时策略控制写入被忽略的本地 run directory；测试 fixture 可用合成文本。README 说明保留内容、敏感字段和 ignored 输出路径。
- 不创建大体量脚本、重复的 v2/v3 文件、临时输出堆积或把代码写进 CC 自己的 outputs。只提交规范路径下必要的实现、测试和交接文档。

## 6. 测试要求

使用 fake transport、合成输入和合成响应，至少覆盖：

1. DeepSeek 和 Ollama 请求 payload 的冻结字段、模型身份及 provider-specific 参数隔离；
2. 合法模型响应严格解析；
3. JSON 前后多余文字、代码围栏、多个对象、缺键/多键、wrong version、错误 enum/type/confidence 的 fail-closed 拒绝；
4. 参数缺失、显式目录冲突、未知字段、unsupported/ask/refuse 时的投影与阶段记录；
5. construction_ready 正反门；拒绝结果不会调用任何 CAD/IR callback；
6. 瞬时故障重试次数和退避顺序，non-retryable 错误不重试，耗尽失败保留；
7. usage/cost 计算、cache hit/miss 缺失时 `not_available`、本地无云端费用；
8. 日志序列化、append 行为、异常脱敏和敏感字段扫描；
9. 正常与失败输入均不访问网络、不读取凭据、不写 tracked outputs；默认正式评测门关闭。

测试不得导入或运行冻结验收标签。可使用手写 synthetic fixtures，例如一个最小有效 `bore_d` 抽取响应和一个 `bore_d` 缺失响应；不得与九条验收样例逐条复刻。

## 7. 里程碑与 checkpoint

- **M0 接口与边界核对**：记录仓库状态、Python/测试入口、provider/schema/compiler 接口、IR 映射是否存在；有冲突即先报 review/blocked。
- **M1 最小数据模型与严格解析**：实现 response envelope、运行记录模型、纯函数 parser/projector，并先提交/同步 checkpoint。
- **M2 双 Provider mock adapter**：实现注入式请求、超时/错误分类、重试；仅 fake transport 测试。
- **M3 确定性后处理与日志**：集成 Schema、构造门、分阶段记录、默认关闭的执行门；CAD/STEP 若无冻结映射保持 not_run。
- **M4 测试与交接**：跑适用测试、静态检查、密钥扫描、git diff 检查；写完成 checkpoint/handoff。

每完成一个里程碑，在 `docs/WORKLOG.md` 追加 checkpoint，并在 checkpoint 记 `in_progress`、已验证内容、剩余范围及风险。不要等全部做完才同步。任何无法安全完成的点先标 `review`/`blocked`，不要通过临时放宽契约绕过。

## 8. 验收标准

- 代码位于 `src/llm/`，测试位于 `tests/llm/`，有 README/配置说明与 checkpoint/handoff。
- 两种 provider 均由 fake transport 完整测试，没有真实网络请求或密钥读取。
- 严格输出解析、CAD-003 投影和 construction gate 符合 ADR-0013 与冻结契约。
- 有可验证的重试和逐阶段运行记录；敏感内容不会意外写入跟踪文件或错误日志。
- 所有没有运行的 IR/CAD/几何/STEP 阶段如实记录 `not_run` 或 blocker，不虚构结果。
- 执行适当测试并记录精确命令与结果；不运行正式验收集、C0/C1 或效果指标。
- 保持 `APP-001-PREP=review`、`APP-001=planned`、`formal_evaluation_allowed=false`；不得自行解锁正式实验。
- 完成后提交 Git commit，状态保持 `review`，不 push、不合并；工作日志记录 commit 短哈希。

## 9. 最终交接格式

在 `agent-work/llm/APP-001-adapter/checkpoint.md` 与 `handoff.md` 中写明：

```text
handoff_self_check:
  changed=<改动文件与 commit>
  commands=<实际运行的命令和逐项结果>
  confirmed=<测试验证的行为，区分 mock 与真实运行>
  unresolved=<IR 映射、真实 provider、成本/性能、未运行项>
  next_agent_focus=<中枢复核关注点、建议后续决策>
```

还要明确列出：接口盘点结果、mock 覆盖范围、没有执行的检查、工作树/提交状态、`APP-001` 仍未获正式运行授权。提交后向项目负责人报告 commit 和摘要，等待 Codex 中枢只读审查。
