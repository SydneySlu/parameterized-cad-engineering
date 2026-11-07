# APP-001 Phase 1 第四批次独立审查

- 批次：`app001-phase1-20261107-04`
- 审查日期：2026-11-07
- 审查状态：`review`
- 仓库基线：`main` / `origin/main`，`1ccc504`
- 原始运行记录：`work/app001-runs/app001-phase1-20261107-04/`（Git 忽略）
- 范围：9 条冻结样例 × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b`

## 结论

已完成本轮授权的正式运行，预算上限和重试次数均未超出；结果可用于第一阶段诊断，但仍保持 `review`，不能视为全部样例通过，也不能作为 CAD/STEP 端到端成绩。DeepSeek 有 7 个逻辑运行未得到可评估输出（6 个连续 HTTP 5xx 耗尽尝试，1 个响应为无效 JSON）；另有 4 个 C1 逻辑运行按既有安全门在请求前阻塞。25 个可解析响应中，17 个通过 CAD-003 Schema，8 个被规则拒绝。

## 运行完整性与预算

- `runs.jsonl` 共 36 条记录，36 个逻辑运行 ID 唯一，覆盖预期的 9 × 2 × 2 组合；32 条实际发出模型调用，4 条 C1 请求前阻塞。
- 模型调用共 54 次：32 次初始调用及 22 次重试；每个已启动逻辑运行最多 3 次，即初始调用加最多 2 次重试，符合 ADR-0010/授权范围。
- 预算账本记录 70 次物理 HTTP：DeepSeek `/chat/completions` 38 次；Ollama `/api/tags` 16 次、`/api/chat` 16 次。合计 70/108；DeepSeek 38/54，Ollama 32/54。
- 账本中 28 条 `transient_retryable` 是可重试类别的 HTTP 尝试数，不等于实际重试数。22 条增加的模型调用是重试；另有 6 次在每个逻辑运行的第 3 次尝试后终止，已达到授权的重试上限。没有第 4 次模型调用。
- Ollama 每次成功模型运行都对应一条 tags 预检和一条 chat 请求；两者均计入上述物理 HTTP 上限。
- 账本 70 条均已 claim 且有终态；账本涉及的 32 个逻辑运行 ID 均存在于 run 记录中，另 4 个请求前阻塞项按设计不进入账本。原始响应保留 25 个文件，与 25 个可解析模型响应一致，批次目录被 `.gitignore` 排除。

## 输出、Schema 与决策诊断

25 个成功返回且被保留的响应均通过 envelope/contract 解析。Schema 结果如下（仅对可解析响应计分）：

| Provider / 条件 | 发出模型调用 | 可解析响应 | Schema 通过 | Schema 拒绝 |
|---|---:|---:|---:|---:|
| DeepSeek / C0 | 9 | 4 | 3 | 1 |
| DeepSeek / C1 | 7 | 5 | 4 | 1 |
| Ollama / C0 | 9 | 9 | 5 | 4 |
| Ollama / C1 | 7 | 7 | 5 | 2 |
| 合计 | 32 | 25 | 17 | 8 |

Schema 拒绝共 8 条：`CATALOG_MISMATCH` 3、`CATALOG_CHOICE` 2、`SECOND_SCREW_CONSTRAINT` 2、`MISSING_REQUIRED` 1。模型完成输出的决策字段分布为 DeepSeek C0 `answer` 4 条、C1 `answer` 3 条和 `ask` 2 条；Ollama C0/C1 均为 `answer`（9/9、7/7）。决策类别为描述性统计，不替代预先定义的样例级行为评分。

按冻结验收集 `explicit_parameter_claims` 对保留的 JSON 输出做 canonical-mm 数值核对：DeepSeek 14/14 个可核查字段值匹配（9/9 个有响应运行全匹配）；Ollama 27/27 个字段值匹配（16/16 全匹配）。DeepSeek 无输出的 7 个逻辑运行不进入该字段匹配分母，因此该结果不能解释为 DeepSeek 全批次 100% 字段准确。

4 条请求前阻塞与前三批次记录的原因一致：A04 C1 两个 provider 无法从允许输入安全得到 `bore_d`；A07 C1 两个 provider 的 RET-002 查询被 CAD-003 Schema 拒绝。其余 7 个非成功终态均为 DeepSeek：6 个逻辑运行连续 3 次收到 HTTP 5xx；A03 C0 第一次 5xx 后重试得到 HTTP 200，但正文无效 JSON，按不可重试错误结束。

## Token、费用、延迟与环境

- DeepSeek 有 usage 的 9 个成功响应合计：input 8,116（cached 6,528；cache-miss 1,588）、output 935、total 9,051 tokens；按冻结价目表记录费用 CNY 0.00545856。另 7 个失败运行没有可用 usage/cost。
- Ollama 16 个本地响应均记录墙钟延迟：均值 8,289.38 ms，中位数 7,678.67 ms，最小 5,683.87 ms，最大 16,990.46 ms。
- 运行记录报告 Python 3.11.18、macOS 26.6.2 arm64。Ollama 当前本机版本为 0.40.14；16 条运行均为 `qwen3:8b`，完整 digest 为 `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`。
- 对 raw/ledger 仅做布尔型凭据特征扫描，未命中 `sk-`、Bearer 或 `DEEPSEEK_API_KEY=` 模式；未将 API key 写入报告。

## 证据限制与范围边界

- A03 C0 的 HTTP 200 无效 JSON 正文没有被保留（该 run 的 `raw_response_retention` 为空），因此只能依据运行错误字段确认 `invalid_json`，不能事后独立核看正文。建议后续在不改写本批次的前提下，决定失败响应是否也应安全保留。
- 4 条请求前阻塞记录使用简化结构，没有 `run_id`、acceptance-set hash、软件版本或 prompt hash 字段；其组合和阻塞原因可核对，但字段级可追溯性低于 32 条执行记录。
- 本批次的 run 终态 `success` 表示 Adapter/runner 完成该次调用记录，不表示 Schema 通过；判断抽取合格必须看独立 stage 结果。
- IR、CAD 构造、geometry、STEP 均未运行；C2 未运行。不得发布构造率、几何通过率、STEP 回读率或端到端成功率。
- 本次只读核对批次 `-04`，未修改批次 `-01`、`-02`、`-03`，未发起额外模型请求，未修改代码或评测规则。

## 独立复核记录

检查了 `docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/DECISIONS.md`、交接复核协议、ADR-0014/0015、上一批次复核和本批次运行材料；用 Python 只读脚本核对组合唯一性、账本上限、终态、重试、raw 文件计数、Schema stage、usage/cost/延迟和字段值。另确认本机 `ollama --version` 为 0.40.14、工作区开始时为 `main...origin/main` 干净状态。

状态保持 `review`。下一步应由项目负责人决定是否将本批次作为首轮诊断结果接受，以及是否另立窄范围工作处理 DeepSeek 5xx 稳定性/失败正文保留和 C1 A04/A07 前置阻塞；未经新的明确授权，不再发起模型请求，也不扩大到 C2/IR/CAD/STEP。
