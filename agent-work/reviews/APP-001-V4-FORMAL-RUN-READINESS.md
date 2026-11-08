# APP-001 v4 正式效果评测运行前审查

- Task ID: `APP-001-V4-FORMAL-EFFECT-EVALUATION`
- Status: `in_progress` (authorization recorded; CC execution pending)
- Prepared by: Codex hub
- Date: 2026-11-08
- Preflight code baseline: `main` / `origin/main` at `80cad1b7fc110e0aa10c63aced7271749c3ffadf`
- Scope: 只准备运行前审查和授权材料；不发起模型请求，不读取密钥值，不创建正式批次。

## 当前生产身份

```text
contract_version: app001-io.v1
prompt_version: app001-extraction.v4
prompt_sha256: 73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc
acceptance_set: acceptance-set-v0
acceptance_set_sha256: ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf
cad_schema_version: set_screw_shaft_collar.v0
cad_schema_source_commit: 035f467142888edfd0bd7cd73906f9b155c8f43c
formal_evaluation_allowed: False
```

当前授权工厂 `authorize_phase1_run()` 从生产常量读取协议版本，因此实际 v4 授权 scope 为：

```text
protocol_versions: {app001-io.v1, app001-extraction.v4}
sample_set: acceptance-set-v0
conditions: {C0, C1}
providers: {DeepSeek, Ollama}
models: {deepseek-flash, qwen3:8b}
max_logical_runs: 36
max_attempts_per_run: 3
max_batch_attempts: 108
max_provider_attempts: 54
ir_cad_geometry_step_disabled: True
```

这不是一份授权；它只是从当前代码和冻结配置读出的预期 scope。`batch_id` 必须是新的唯一值，不能复用旧批次。

## 前置项关闭状态

### P1：evidence null 决策门 — closed

`APP-001-EVIDENCE-CONTRACT-FIX` 已在 `main`，commit `352ef8a` 的 parser 修复已通过 Python 3.11.18 独立测试；关闭记录已追加到 `docs/DECISIONS.md` 的 `ADR-0015-CLOSEOUT`，并明确不构成正式运行授权。

证据：`agent-work/reviews/APP-001-EVIDENCE-CONTRACT-FIX-codex-review.md`；该门已关闭，但旧批次仍只读。

### P2：ADR-0014 scope 文档同步 — closed

ADR-0014 的原始授权表保留 `app001-extraction.v2` 作为历史批次证据；`ADR-0014-AMENDMENT` 已同步当前生产 v4 的继承 scope。当前 `src/llm/authorization.py` 动态读取生产 `PROMPT_VERSION`，因此本批次使用 v4；唯一 `batch_id` 和负责人批准已记录在授权模板中。

证据：`docs/DECISIONS.md`、v4 manifest、`src/llm/authorization.py` 和 runner 入口一致；旧 v2/v3 批次和历史授权证据保持只读。

### P3：本机运行环境检查

在真实请求前由执行者记录，不把检查结果当作模型效果：

- `/opt/homebrew/bin/python3.11 --version` 为 3.11.18；
- `main` 与 `origin/main` 同步到批准的提交；
- Ollama 使用 ADR-0015 冻结的 Homebrew `0.40.14`、`qwen3:8b` 和 digest 前缀 `500a1f067a9f`；
- Ollama `format_schema_sha256` 为当前 v4 实际值 `04d159d287e093b92e2b0157e46e9b1d7b549fa8b81b20ee08da9e1e5f610e70`；ADR-0015 中的 `d82e53ad…` 保留为 v2 历史 smoke 证据，不能与 v4 混用；
- `DEEPSEEK_API_KEY` 只做存在性检查，不打印值；当前 preflight shell 未注入该变量，仓库根目录 `.env` 文件存在但未读取；
- RET-002 `RetrievalIndex` 从冻结 manifest/config 构造，并通过 runner 的 manifest、policy、candidate_roles、default_top_k 身份门；
- 新的 `work/app001-runs/<batch-id>/` 目录不存在，旧批次不覆盖。

## 运行边界

- 允许：当前 v4 prompt、9 条 acceptance-set 样例、C0/C1、DeepSeek `deepseek-flash`、Ollama `qwen3:8b`。
- 预算：36 个逻辑运行；每 run 最多 3 次尝试；全批次最多 108 次物理请求；每 provider 最多 54 次。
- 必须保留：runs JSONL、预算账本、raw response、请求前阻塞证据和模型身份/解码参数。
- 禁止：修改旧批次、混合 v3/v4 统计、读取或输出 evaluator-only 标签、修改 prompt/Schema/runner 以迁就单条响应、C2、IR、CAD、geometry、STEP。
- 5xx 继续遵循 ADR-0010 的最多两次重试；不能用增加重试次数掩盖服务不稳定。

## Final preflight 结果（无模型调用）

已在当前共享仓库完成以下只读检查：

- `main` 与 `origin/main` 同步：`80cad1b7fc110e0aa10c63aced7271749c3ffadf`；无 `.git/index.lock`；
- `/opt/homebrew/bin/python3.11 --version`：`Python 3.11.18`；
- v4 prompt 文件 SHA-256、loader 常量和 manifest 一致：`73cb6b8f…`；
- 当前 v4 Ollama Schema SHA-256：`04d159d2…`；旧 `d82e53ad…` 仅作 v2 历史证据；
- Ollama `0.40.14` 可访问，`qwen3:8b` digest 为 `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`；
- RET-002 冻结身份：manifest SHA-256 `b7b6c737…`、`candidate_roles=('retrieval_source',)`、`default_top_k=3`；
- 旧批次目录保持存在且未修改；未创建拟议 v4 新批次目录；
- Python 3.11.18 下 v4 activation 专项 71/71、关键 parser/provider/R3 回归 114/114、Schema 17/17、py_compile 和 `git diff --check` 通过；
- LLM 全量 685 项在 `d422877` 的测试隔离修复后稳定通过，8 项既有 FUSE skip；该修复已合入当前主线，未改生产代码；
- 未调用 DeepSeek/Ollama chat 接口、未读取密钥值、未产生正式运行产物。

当前 preflight 结论为 `pass`：技术前置项 P1/P2 已关闭，项目负责人已批准新唯一 `batch_id` `app001-phase1-v4-20261109-01` 和固定完整 scope。授权 scope hash 为 `a57b69664e816be709cc7dfd049dbad389461203857f27ea3ffe302729d04c5f`。

## 放行顺序

1. CC 使用现有 runner 执行已批准的 `app001-phase1-v4-20261109-01`；不得修改生产代码、prompt、Schema、预算或授权工厂。
3. Codex 独立复核 raw response、预算、身份、解析、Schema、决策、失败证据和 provider 错误；真实效果结论与离线测试分开报告。

## 当前结论

`APP-001-V4-FORMAL-EFFECT-EVALUATION` 处于 `in_progress`。v4 已是生产离线契约，P1/P2 已关闭，项目负责人已批准唯一批次和固定 scope；当前可由 CC 执行，Codex 尚未对任何模型结果作效果结论。

## handoff_self_check

```text
changed=agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md,
        agent-work/llm/APP-001-v4-effect-evaluation/authorization-request-template.md,
        agent-work/llm/APP-001-v4-effect-evaluation/checkpoint.md,
        docs/PROJECT_STATUS.md, docs/WORKLOG.md
commands=main/origin sync, Python 3.11.18, prompt/schema/hash and runtime identity checks;
         no model chat request and no key value access
confirmed=v4 identity, approved batch identity, dynamic authorization scope, 36/108/54 budget,
          retrieval identity gate, old-batch read-only boundary, P1/P2 closed, no model request started by Codex
unresolved=CC execution and post-run Codex result review
next_agent_focus=CC executes only the approved batch with the existing runner
```
