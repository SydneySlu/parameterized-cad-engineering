# CC Prompt: APP-001-AUDIT-EVIDENCE-R1

你负责任务 **APP-001-AUDIT-EVIDENCE-R1**：只补强 APP-001 失败响应证据留存与请求前阻塞审计。请先确认共享 Git 根目录，并按 `AGENTS.md` 阅读项目状态、计划、日志、决策、交接复核协议及上一轮第四批次审查/运行记录。源代码修改只发生在该仓库的 `src/` 和 `tests/`；交接材料写入 `agent-work/llm/APP-001-AUDIT-EVIDENCE-R1/`。

## 固定边界

- 只做代码、无网络测试和交接记录；不进行真实 DeepSeek/Ollama 调用，不读取/打印 `.env` 或 `DEEPSEEK_API_KEY`。
- 旧批次 `app001-phase1-20261107-01` 至 `-04` 只读；不得覆盖、回填或重跑。
- 不修改 Prompt 文本/版本、输出契约版本、RET-002 查询或距离语义、CAD-003 Schema、provider 配置、Ollama 版本、重试次数/退避、正式授权逻辑、C2、IR/CAD/STEP。
- 对 5xx 错误不读取或保存 HTTP 错误正文。只考虑 HTTP 成功后 transport 解析响应包装失败的诊断留存，以及现有 adapter 已收到正文后的解析/契约失败留存。
- 不把正文放进异常消息、stdout/stderr、ledger、RunRecord 或 tracked 文件；不得写入输入文本或 evaluator-only 标签。
- 所有可选失败均 fail-closed：若不能确认路径被 `.gitignore` 排除、不能安全截断或写入失败，只记录有限元数据和明确的留存失败状态。

## 工作范围

### A. 请求前阻塞审计记录

当前 runner 对无 `record_dict` 的 blocked 运行只写最小 JSONL。为 C1 请求前阻塞增加稳定结构化审计元数据，至少包含：

- `logical_run_id`、`batch_id`、`query_id`、`condition_id`、configured provider/model；
- acceptance-set version/hash，contract/prompt/adapter 版本，software versions；
- prompt hash：请求未构造时显式标记不可用及原因，不能填伪 hash；若可从冻结 artifact 安全计算实际 system/user template hash，则使用真实 hash；
- `blocked_stage`、稳定 `error_code`、`error_fields`；
- `bore_d_used_for_query`（仅当该值从模型可见输入安全解析得到时）、候选数量/来源 ID 摘要、reference context hash（若有）。

不得记录自然语言输入、evaluator 标签或完整 reference context。保持旧版 runs.jsonl 消费者可读；测试验证字段稳定且敏感字段缺失。避免仅将自由文本 `blocked_reason` 当成机器可读错误码；需要由 `AssembledInput` 提供稳定码/字段时，兼容现有调用方。

### B. HTTP 2xx 响应包装解析失败的受控留存

第四批次 A03 DeepSeek 的 HTTP 200 失败记录在 transport `model_call` 阶段，Adapter 未收到 `TransportResponse`，因此当前 raw retention 未保留证据。实现只覆盖 HTTP 成功响应被 real transport 收到、但响应包装无法按预期解析的路径；不得改变 retry 分类和重试次数。

- 在调用层可用的现有 `RetentionPolicy`/批次目录内完成留存；输出必须位于 `work/app001-runs/<batch_id>/` 下并确认 `.gitignore` 覆盖。
- 设置明确且有测试的字节上限；超限时采用确定性截断并记录原始长度、保存长度、完整正文 SHA-256、是否截断、相对路径/失败码。严禁在元数据或异常中包含正文片段。
- 推荐仅保留受控响应体字节；禁止保留 headers、请求、Authorization 或任何凭据。
- JSON 包装解析成功时仍只向 Adapter 返回模型 `message.content`，不改变现有处理；JSON 包装解析失败时，在抛出原有稳定分类错误前尝试留存诊断正文。留存失败不能覆盖原来的 transport error。
- HTTP 5xx/429/其他 HTTPError 分支维持现状，不读取错误正文、不保存错误正文。
- 为成功包装、无效包装 JSON、超长正文截断、留存失败、5xx 不读取正文、HTTP 2xx 中模型 content 本身 JSON 无效等行为写无网络测试。测试使用 mock urlopen 和临时目录 helper，不触发真实网络。

## 先行检查与验证

开始实现前：

1. 重跑至少一个现有核心测试；
2. 从只读批次材料确认一个正常记录和一个失败/阻塞记录；不得打印 raw 正文；
3. 检查 RunRecord、TransportError/Response、RetentionPolicy、runner 的现有接口，优先保持向后兼容。

完成后运行并记录实际结果：专项测试、`PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q`、Schema 全量测试、相关 `py_compile` 和 `git diff --check`。明确 Python 版本和环境限制，不把 skip/error 写成通过。

## 交付与收束

- 新建 `agent-work/llm/APP-001-AUDIT-EVIDENCE-R1/checkpoint.md`，记录 changed、commands、confirmed、unresolved、next_agent_focus，并附 `handoff_self_check`。
- 追加 `docs/WORKLOG.md`；任务状态保持 `review`，不得声称 APP-001 完成或放行。
- 按提交规范创建一个聚焦 commit；不要 push、合并或改动与本任务无关文件。若 Git 锁阻塞，停止 Git 写操作并报告，不删除锁。
- 最终报告列出 commit、改动文件、实际测试结果、留存边界、限制和任何偏离。遇到不清楚的接口问题先记录 checkpoint，禁止扩大范围。

Codex 中枢将独立复核实现。A04/A07 样例级 C1 诊断测试、8 条 Schema 拒绝的决策质量分析、Prompt/输出策略版本变更和任何新增模型批次均不属于本任务。
