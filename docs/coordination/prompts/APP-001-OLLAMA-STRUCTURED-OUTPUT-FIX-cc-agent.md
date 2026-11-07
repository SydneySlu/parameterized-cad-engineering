# APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX：收紧 Ollama 数值输出类型

你是 CC 编程 Agent。任务 ID：`APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`。只处理 Ollama `qwen3:8b` 请求的结构化 JSON 类型约束和无网络测试；不要扩展成 Prompt 重写、parser 宽容化或重新评测任务。

## 事实源和启动检查

必须在本机共享仓库根目录工作：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
git log -5 --oneline --decorate
```

开始前阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`、`agent-work/reviews/APP-001-phase1-20261107-03-codex-review.md`、冻结的 `agent-work/llm/APP-001-baseline-prep/prompt-v2.md`、`src/llm/providers.py`、`src/llm/contract.py`、`src/llm/parser.py`、`tests/llm/test_providers.py` 和 `tests/llm/test_envelope_fix.py`。确认当前分支从最新 `main` 开始；使用 `cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`，不得在旧分支、旧 clone 或 CC outputs 目录工作。若仓库状态、基线或分支不符，先报告并停止，不要覆盖其他工作。

在修改前完成交接定向复核并写入 checkpoint：重跑一个现有核心测试；确认一个合法数字输出可由 parser 接受，一个数值字符串（如 `"24 mm"`）被 parser 拒绝；确认 prompt artifact hash 与主线冻结值一致。这里不得调用模型或网络。

## 已确认问题

第三批 `app001-phase1-20261107-03` 的 Ollama C0 有 8 条响应被严格 parser 以 `EXTRACTED_TYPE_ERROR` 拒绝：模型把数值写成带单位字符串（如 `"24 mm"`、`"1.6 cm"`、`"70 mm"`、`"0"`）。parser 按冻结契约正确拒绝这些类型；不得为消除失败而将字符串强制转换成数字、放宽 parser、改写或覆盖旧批次。

当前 `build_ollama_request()` 使用 `body["format"] = "json"`，只能要求 JSON 格式，不能约束参数的 JSON 类型。修正目标是让 Ollama 在生成时收到与 `app001-io.v1` 一致的 JSON Schema 格式约束。

## 严格范围

允许修改：

- `src/llm/providers.py`：Ollama 专属的冻结 JSON Schema 常量及请求构造；
- `src/llm/contract.py`：仅在配置快照需要复用稳定标识/版本常量时才改，优先避免改动；
- `tests/llm/test_providers.py`，必要时少量扩展 `tests/llm/test_envelope_fix.py`；
- `src/llm/README.md`；
- `agent-work/llm/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX/checkpoint.md` 和 `handoff.md`；
- 只追加 `docs/WORKLOG.md`。

禁止修改：

- `prompt-v2.md`、其 SHA-256 锚点、Prompt 内容或版本；
- `src/llm/parser.py` 的拒绝行为、`adapter.py`、正式 runner/预算/授权逻辑；
- 冻结 acceptance set、Schema/CAD-003、C1/C0 组装、ADR-0014 和任何既有审查/批次文件；
- DeepSeek 请求、模型/解码共享参数、正式评测门；
- `work/app001-runs/app001-phase1-20261107-01/-02/-03/` 下任何内容。

不得访问 `.env` 或真实密钥；不得进行任何 HTTP/模型调用；不得运行正式 runner、冻结样例或创建新批次；不得运行 C2、IR、CAD、geometry、STEP。

## 实现要求

1. 只对 `build_ollama_request()` 生效：将 `body["format"]` 从字符串 `"json"` 改为 Ollama 支持的 JSON Schema 格式对象。DeepSeek 的 `response_format` 保持原样，provider 参数隔离测试必须继续通过。
2. Schema 必须和当前 parser 的 envelope 键及类型契约对齐：顶层只允许 `ENVELOPE_KEYS`；固定 `contract_version`、`prompt_version`；decision 为既有枚举；`extracted_parameters` 仅允许六个已冻结字段；五个长度字段接受 JSON number 或严格 `{value: number, unit: string}` 对象；`second_screw` 只接受 integer；其余数组、evidence 形状、null confidence 按现有 `app001-io.v1` 契约定义。不要把任何字段设成必须出现在 `extracted_parameters` 中，因为显式提取字段可选。Schema 不得包含 evaluator truth、目录值、样例答案或参数取值范围。
3. `additionalProperties` 和嵌套字段约束应与严格 envelope/parser 对齐。不得通过 Schema 约束合法参数的数值范围、默认值、catalog 行或 CAD-003 规则；这些继续由既有确定性层处理。
4. `decoding_parameters_snapshot(OLLAMA_PROVIDER)` 必须准确反映实际发送的结构化输出配置。避免请求体和快照各自维护两份可能漂移的 Schema；如记录完整 Schema 不合适，记录精确且可审查的结构化格式标识及 schema hash，并在 README/checkpoint 说明。
5. 保持 parser 严格：数字成功、`"24 mm"`/`"0"` 仍失败。Schema 约束只是生成约束，不可声称它保证模型永不违规。
6. 若当前冻结契约、Ollama 支持的 JSON Schema 子集或运行配置存在冲突，不得自行扩大范围；记录 `review`/`blocked` 和冲突证据后停止受影响实现。

## 必须补的无网络测试

- Ollama request 的 `format` 是结构化 schema 对象，而不是 `"json"`；核对冻结顶层键、版本常量、字段类型、可选参数语义和 `additionalProperties`。
- 五个长度字段均允许数字与 `{value, unit}`，但拒绝字符串；`second_screw` 允许整数且拒绝小数/字符串。
- JSON schema 至少通过项目已有 JSON Schema validator 的结构/fixture 验证（若依赖不可用，明确报告并用无网络方式验证）；使用代表性合规 envelope 和数字字符串错误 envelope。
- `parse_response()` 行为不变：数字 envelope 通过，数值字符串 envelope 仍以 `EXTRACTED_TYPE_ERROR` 失败。
- DeepSeek 请求和 Ollama/DeepSeek provider-specific 参数隔离维持原样；Ollama decoding snapshot 与实际 request 配置一致。
- 不得以把 Schema 对象塞入 body 的浅层断言替代类型/拒绝行为验证。

## 验证、交接与交付

至少运行并记录实际解释器版本及完整结果：

```bash
PYTHONPATH=src:. python3 -m unittest tests.llm.test_providers tests.llm.test_envelope_fix -v
PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q
PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q
python3 -m py_compile src/llm/providers.py src/llm/contract.py tests/llm/test_providers.py
git diff --check
```

若环境已有项目指定的 Python 3.11，优先使用它并报告精确版本；否则如实记录现有解释器版本，不得声称用过未安装的版本。检查 `git diff --stat`、完整 diff、`git status --short --branch`、ignored run 目录无变更且无锁/临时文件。对测试结果按实际执行报告，不得把环境 skip 写成 pass。

提交前更新 checkpoint/handoff 和 WORKLOG，状态保持 `review`；提交一个范围清楚的 commit，不 push、不合并、不标 `done`。交接记录必须包含：

```text
handoff_self_check:
  changed=<修改文件与 commit>
  commands=<实际运行的命令和逐项结果>
  confirmed=<Schema 类型约束、parser 严格拒绝行为、配置快照一致性证据>
  unresolved=<限制、兼容性证据和是否需要新增 ADR>
  next_agent_focus=<中枢审查重点>
```

明确声明：本任务没有真实网络/模型调用、没有访问密钥、没有修改任何正式批次，也没有生成新的正式指标。提醒中枢：Ollama 输出约束改变会改变后续运行配置；本任务不得擅自重跑。中枢审查后再判断是否需要新 ADR/协议版本及新的唯一批次授权。
