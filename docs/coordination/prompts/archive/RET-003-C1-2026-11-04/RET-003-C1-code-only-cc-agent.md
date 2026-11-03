# RET-003 C1 code-only 修正 Prompt（CC）

你是 RET-003 C1 的代码实现 Agent。本轮只修复诊断器、报告生成器和交叉核对器，不执行正式 C1 诊断，不生成正式结果。正式诊断将由 Codex 在本机固定 macOS 环境运行。

任务状态保持 `review`。不得 push；完成可审查的代码单元后，按项目约定提交限定范围内的文件，并交 Codex 中枢独立审查。

## 本轮目标

修正当前 C1 代码中已确认的问题：

1. 结构化失败对象的 `code`、`stage`、`fields` 位于 `error_details["error"]` 内；现有代码从错误包络顶层取值，导致 `stage` 和 `fields` 为 null。
2. 契约测试必须验证错误对象完整结构及拒绝路径，不能只验证错误码。
3. 报告交叉核对必须逐项校验失败诊断的 code、stage、fields，不能只确认报告里出现了错误码。
4. 正式运行入口必须有明确的环境门；契约测试可在当前 Agent 环境运行，但不得因此绕过正式运行环境门。
5. 正式入口使用唯一规范路径 `run_c1_diagnostic.py`。现有 `run_c1_diagnostic_v2.py` 只可作为参考；不要再创建 v3 脚本或删除历史文件。

## 环境与执行边界

本轮是代码实现，不是正式实验。你可能处于 Linux/Python 3.10 环境，项目 Mac venv 的绝对路径在该会话中可能不可用；这不阻止本轮编码和纯契约测试，也不授权你改变项目环境基线。

- 可以用当前可用的 Python 运行纯契约测试、交叉核对自测和 `py_compile`，并如实记录 Python/OS/架构。这些只能作为代码级验证，不能作为正式 C1 结果。
- 不得运行 `run_c1_diagnostic.py` 的正式模式或 worker 模式，不得生成、覆盖、修补或重新标注正式 JSON/Markdown 结果。
- 不得创建新的环境阻塞报告。当前 `ENVIRONMENT_GATE_BLOCKED.md` 是历史记录，保留原样。
- 不得修改 Python/CadQuery/OCP 环境基线、依赖版本、manifest、query set、RET-002 策略或候选。
- `.git/index.lock` 若存在，不删除、不绕过，不执行暂存或提交；在交接中报告即可。

正式运行的环境门必须在诊断主模式和 worker 模式执行任何查询或写入前检查：Python `3.11.18`、`sys.platform == "darwin"`、机器架构为 `arm64`。任一不符就非零退出且不触碰正式输出。`--contract-test` 等纯测试模式可在其他环境运行，但必须明确不会生成正式结果。用可注入的环境值对环境门做单元测试，不要伪造当前进程环境来运行正式模式。

## 开始前

在当前 Git 根目录运行并记录：

```text
git rev-parse --show-toplevel
git status --short --branch
git log --oneline -8
```

阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`、`docs/TASKS.md`、`docs/coordination/handoff-review-protocol.md`、`agent-work/reviews/RET-003-codex-review.md`，以及本任务现有脚本、结果、报告、checkpoint/handoff 和 RET-002 的 `src/retrieval/baseline.py`、`src/retrieval/errors.py`。

工作树包含之前的未提交产物。不得 reset、restore、checkout、清理或覆盖无关改动。先区分本轮允许修改的文件与既有文件。

## 实现要求

### 1. 规范诊断脚本

以 `agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py` 为唯一规范入口，吸收当前 v2 中仍需保留的实现。正式结果路径固定为 `c1-diagnostic-results.json` 和 `c1-diagnostic-report.md`；报告生成器与交叉核对器的默认路径也必须指向这两个规范产物，不再默认写入 `-v2` 文件。至少保留：正确读取 RET-002 的 `results`、从 `query.query_status` 读取状态、五个合法查询分别进行独立 OS 进程复跑、canonical SHA-256 比较、候选角色限制、逐候选字段误差和 fail-closed 行为。

不要把检索异常静默转换成空列表、null 或成功状态。`query_status` 缺失、results 为空、候选字段缺失或角色越界均须非零退出。

### 2. 结构化错误解析

实现可单测的错误解析逻辑，从 RET-002 的嵌套形态读取：

```json
{
  "ok": false,
  "error": {
    "code": "RETRIEVAL_MISSING_FIELD",
    "stage": "query",
    "fields": ["outer_d"]
  }
}
```

正式失败诊断必须严格验证 `code == "RETRIEVAL_MISSING_FIELD"`、`stage == "query"`、`fields == ["outer_d"]`。任一字段缺失、类型错误或值不符时，以非零退出码结束。序列化到正式结果时，将校验后的值写入 `failure_diagnostic.code`、`failure_diagnostic.stage` 和 `failure_diagnostic.fields`，并保留完整原始结构化错误供追溯。

### 3. 报告生成与交叉核对

`generate_report.py` 从结果 JSON 生成报告；失败诊断部分展示实际 JSON 中的 code、stage、fields，不自行推断或手填。

`cross_check.py` 必须将报告中失败诊断的 code、stage、fields 与 JSON 逐字段比对。错误码只出现在报告其他位置不能算通过；缺字段、重复/含糊字段、值不匹配都应失败。

为交叉核对增加可重复的自测：先确认规范报告通过，再分别破坏临时报告副本中的 stage 和 fields，确保每种变异都会导致非零退出。自测只能操作系统临时目录或内存，不得改正式报告。

### 4. 契约测试

通过现有 `--contract-test` 或等价测试模式覆盖以下内容：

- 正确嵌套错误解析得到预期 code/stage/fields；
- 缺失 error、缺失 code/stage/fields、错误 code、错误 stage、错误 fields 和错误类型均被拒绝；
- 环境门接受注入的 `3.11.18/darwin/arm64`，拒绝 Python 版本、平台或架构任一不匹配的值；
- 正式模式与 worker 模式都受环境门保护；测试模式不会写正式输出；
- 交叉核对能拒绝报告中被篡改的 stage 和 fields。

契约测试应尽量使用小型内存 fixture，不依赖生成真实 C1 结果。不要新建大型测试框架或无关生产模块。

## 允许修改的文件

- `agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py`
- `agent-work/integration/RET-003-retrieval-evaluation/generate_report.py`
- `agent-work/integration/RET-003-retrieval-evaluation/cross_check.py`
- `agent-work/integration/RET-003-retrieval-evaluation/checkpoint-v2.md`（在文首加醒目状态说明，并追加本轮代码修正记录；历史 M1-M5 声称不构成正式结果验收）
- `agent-work/integration/RET-003-retrieval-evaluation/handoff-v2.md`（在文首加醒目状态说明，并追加本轮交接）
- `docs/WORKLOG.md`（只追加）

不得修改或新增正式结果 JSON/报告、其他 v2/v3 文件、`ENVIRONMENT_GATE_BLOCKED.md`、`ENVIRONMENT_MISMATCH.md`、RET-001/RET-002、`src/**`、`tests/**`、protocol、query set、依赖配置或 CAD/IR 文件。若发现需要扩大文件范围，先停下并在 checkpoint 说明原因，不自行扩展。

## 验证与交接

在当前 Agent 环境只运行代码级验证，并记录真实解释器、平台、命令和退出码：

- `run_c1_diagnostic.py --contract-test`；
- `cross_check.py` 的自测（包括 stage/fields 变异负例）；
- 三个脚本的 `py_compile`；
- `git diff --check`。

不得声称完成了正式 C1、五查询实验、正式环境复跑或 RET-001/RET-002 完整回归。正式运行由 Codex 在 Mac 固定环境另行执行。

在 checkpoint/handoff 文首明确：先前 v2 的 Linux/Python 3.10 执行不符合正式环境，M1-M5 的阶段记录不能视为正式 C1 验收；本轮只验收代码级测试，正式 JSON/报告仍未验收。保留历史记录并追加本轮信息，不重写 WORKLOG 历史。记录修改文件、代码级验证、环境门设计、未运行的正式检查、下一步由 Codex 在固定环境执行正式 C1。`WORKLOG.md` 只追加。只提交本 Prompt 允许的代码与记录文件，不要 stage 其他已有改动；提交后保持 `review`，不得 push。
