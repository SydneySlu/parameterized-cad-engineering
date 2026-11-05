# APP-001-ADAPTER-R2：窄范围安全边界与冻结 Prompt 核验修正

你是 CC 执行 Agent，任务 ID 为 `APP-001-ADAPTER-R2`。本轮只修复 Codex 中枢复核确认的三个适配器缺口，补齐最小回归测试和交接记录。不要重写适配器，不扩展产品功能，不运行正式模型评测。

## 1. 启动与事实源

先确认仓库：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
git log -6 --oneline
```

开始前必须阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/PROJECT_PLAN.md`
- `docs/WORKLOG.md`
- `docs/DECISIONS.md`
- `docs/coordination/handoff-review-protocol.md`
- `agent-work/reviews/APP-001-ADAPTER-R1-codex-review.md`
- `docs/coordination/prompts/APP-001-adapter-logger-cc-agent.md`
- `docs/coordination/prompts/APP-001-ADAPTER-R1-correction-cc-agent.md`
- `docs/coordination/APP-001-baseline-contract.md`
- `agent-work/llm/APP-001-baseline-prep/prompt-v2.md`
- `agent-work/llm/APP-001-adapter/checkpoint.md`
- `agent-work/llm/APP-001-adapter/handoff.md`

若代码与冻结契约冲突，先记录 `review`/`blocked`，不要自行改 ADR、冻结 Prompt、验收样例、Schema、IR、CAD 编译器或检索策略。

## 2. 严格边界

本轮允许修改：

- `src/llm/`
- `tests/llm/`
- `src/llm/README.md`
- `agent-work/llm/APP-001-adapter/checkpoint.md`
- `agent-work/llm/APP-001-adapter/handoff.md`
- `docs/WORKLOG.md`（只追加）

本轮禁止：

- 访问、读取、打印或探测 `.env`、真实 API key、Authorization header；
- 发起 DeepSeek/Ollama 请求、运行 runtime probe 或加载真实模型；
- 运行九条 evaluator-only 冻结样例，读取其标签，或生成正式指标；
- 打开 `formal_evaluation_allowed`，添加环境变量/CLI 绕过或 live HTTP transport；
- 修改 `src/schema/`、IR/CAD/STEP、RET 模块、ADR、冻结 Prompt 和冻结样例；
- 通过新增任意 `skip_verification`、`allow_*`、`test_mode` 公共参数绕过本轮安全门；
- 创建重复的 `v2/v3` 大脚本、CC outputs 文件或临时产物堆积。

完成后提交一个修正 commit，状态保持 `review`；不要 push、合并或标记 `done`。

## 3. 当前已确认的问题

Codex 已独立复核并记录在 `agent-work/reviews/APP-001-ADAPTER-R1-codex-review.md`：

1. `Adapter.run()` 使用 `isinstance(transport, MockTransport)`，任意自定义 `MockTransport` 子类都能在门关闭时调用 `send()`。
2. `RetentionPolicy.base_dir` 可被指定为任意路径，raw response 可以写到 `work/app001-runs/` 之外。
3. 运行记录虽然保存传入 Prompt 的 hash，但没有加载和核对冻结的 `prompt-v2.md`，任意 Prompt 仍可能被标成 `app001-extraction.v2`。

## 4. 必须完成的修正

### 4.1 评测门不能被 MockTransport 子类伪造

- 在 `formal_evaluation_allowed=false` 时，仅允许仓库内明确的 `FakeTransport` 测试实现通过；未知 transport、自定义 `MockTransport` 子类、仅实现 `send()` 的哑对象都必须在调用 `send()` 前被拒绝。
- 不得继续用公开可继承的 `MockTransport` 作为唯一放行依据。推荐使用精确类型/受控注册表等不可由普通调用者伪造的判断；如果选择其他方案，必须在交接中解释其安全边界。
- 拒绝发生在任何 credentials/environment lookup 和 `send()` 之前。
- 保留 `FakeTransport` 的全部既有测试能力；不得打开正式评测门。
- 新增合成回归测试：自定义 `MockTransport` 子类的 `send_calls == 0`；普通自定义 transport 的 `send_calls == 0`；`FakeTransport` 在门关闭时仍可运行；不得通过调用者布尔参数或环境变量改变结论。

### 4.2 raw response 只能写入受控 ignored 目录

- 正式 retention 的根目录固定为仓库内被 `.gitignore` 排除的 `work/app001-runs/`；不得仅靠注释声称 `base_dir` 安全。
- 对正式/普通运行入口，拒绝绝对路径、`..` 越界、符号链接逃逸、仓库 tracked 路径以及任何不在 canonical `work/app001-runs/` 下的路径。拒绝必须发生在写文件前，并在记录中给出稳定的失败状态。
- 保留默认关闭策略；默认运行不得落盘。
- 测试如需临时目录，必须通过明确的测试专用工厂或依赖注入路径实现，并在代码和测试中标明只供测试使用；不能让生产调用者用同一公共参数任意指定路径。测试专用路径不能被正式运行入口接受。
- 使用合成响应测试：默认不保存、合法 ignored 路径可保存、外部路径/路径穿越/符号链接路径拒绝、写入失败不会伪装成成功。不要写入真实用户响应或提交 `work/` 产物。
- 更新 README、checkpoint、handoff，使实际路径约束和测试专用机制一致。

### 4.3 正式运行前核验冻结 Prompt artifact

- 实现一个可审查的冻结 Prompt 加载/核验函数或对象，读取 `agent-work/llm/APP-001-baseline-prep/prompt-v2.md`。
- 核验必须同时覆盖 artifact 的版本 `app001-extraction.v2`、实际 system prompt 内容、实际 user template 内容，以及记录中的 prompt hash 与实际使用内容一致。
- 必须写明并测试 Markdown fenced block 到 AdapterInput 模板的规范化规则（尤其是 `{{query_id}}` 等占位符与运行时 `{query_id}` 形式的转换）。禁止凭文件名或硬编码版本字符串认定通过。
- artifact 不存在、无法读取、版本不符、system/template 内容不符或 hash 不符时，正式运行入口必须在 transport `send()` 前 fail closed；不得把任意 Prompt 继续标成冻结版本。
- 不能为了让既有合成单测通过而增加公共 `skip_verification`/`allow_arbitrary_prompt` 绕过。若测试需要合成 Prompt，使用明确的 mock-only 测试构造，并确保它不能进入正式运行入口；测试必须覆盖真实冻结 artifact 匹配时通过、修改 system prompt 时拒绝、修改 user template 时拒绝、artifact 缺失/损坏时拒绝、拒绝发生前 `send_calls == 0`，以及 Prompt 原文不进入 RunRecord、stdout 或异常。
- 不修改 `prompt-v2.md` 本身。不能读取或复制九条验收样例标签。

## 5. 回归与文档要求

保持已有 R1 行为：凭据不进入 mock 请求或日志；严格 parser、费用、重试耗时、阶段状态和 IR/CAD/STEP 的 `blocked`/`not_run` 语义不得回退。

至少运行并记录：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py
git diff --check
```

还要在交接中给出以下证据：恶意/未知 transport 在门关闭时 `send_calls == 0`；retention 越界路径无法写入、合法 ignored 路径和测试临时路径边界清楚；frozen Prompt artifact 匹配、篡改、缺失三类结果；没有真实网络、真实凭据、真实模型、冻结样例或正式指标。

追加 `checkpoint.md` 和 `handoff.md`，不得覆盖 R1 历史。交接必须包括：

```text
handoff_self_check:
  changed=<文件与 commit>
  commands=<实际命令与结果>
  confirmed=<三项修正的证据，区分 mock 与未来正式运行>
  unresolved=<仍未解决的事项及其是否超出本任务范围>
  next_agent_focus=<Codex 中枢复核重点>
```

明确写出：IR → Typed CAD IR 映射仍未冻结是后续依赖，不得在本轮臆造；真实 provider、九条样例、成本/延迟和 CAD/STEP 正式指标均未运行；`APP-001-ADAPTER` 保持 `review`，`APP-001` 保持 `planned`，正式评测门保持关闭。
