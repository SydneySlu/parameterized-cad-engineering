# APP-001 v4 正式效果评测运行前审查

- Task ID: `APP-001-V4-FORMAL-EFFECT-EVALUATION`
- Status: `planned`
- Prepared by: Codex hub
- Date: 2026-11-08
- Baseline: `main` / `origin/main` at `abcb8f0`
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

## 必须先关闭的前置项

### P1：evidence null 决策门

`docs/DECISIONS.md` 的 ADR-0015 仍要求：在 evidence `null` 契约偏差完成单独决策和 Codex 复核前，不启动新正式批次。`APP-001-EVIDENCE-CONTRACT-FIX` 已在 `main`，commit `352ef8a` 的 parser 修复也已通过 Python 3.11.18 独立测试；但 ADR-0015 的这条边界尚未追加关闭记录。

解除条件：项目负责人确认该修复和审查证据满足 ADR-0015 的单独决策要求，并将结论追加到 `docs/DECISIONS.md` 和 `docs/WORKLOG.md`。在此之前状态保持 `review`。

### P2：ADR-0014 scope 文档同步

ADR-0014 的历史授权表仍显示 `app001-extraction.v2`，而当前 `src/llm/authorization.py` 动态使用生产 `PROMPT_VERSION`，即 v4。运行前必须把 ADR-0014 标成“历史授权基线”，并补充当前 v4 继承的同一运行边界，或者由项目负责人批准一条明确的 ADR amendment。

解除条件：文档中的当前 scope 与代码、v4 manifest、runner 入口一致；旧 v2/v3 批次和历史授权证据保持只读。

### P3：本机运行环境检查

在真实请求前由执行者记录，不把检查结果当作模型效果：

- `/opt/homebrew/bin/python3.11 --version` 为 3.11.18；
- `main` 与 `origin/main` 同步到批准的提交；
- Ollama 使用 ADR-0015 冻结的 Homebrew `0.40.14`、`qwen3:8b` 和 digest 前缀 `500a1f067a9f`；
- Ollama `format_schema_sha256` 为 `d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043`；
- `DEEPSEEK_API_KEY` 只做存在性检查，不打印值；
- RET-002 `RetrievalIndex` 从冻结 manifest/config 构造，并通过 runner 的 manifest、policy、candidate_roles、default_top_k 身份门；
- 新的 `work/app001-runs/<batch-id>/` 目录不存在，旧批次不覆盖。

## 运行边界

- 允许：当前 v4 prompt、9 条 acceptance-set 样例、C0/C1、DeepSeek `deepseek-flash`、Ollama `qwen3:8b`。
- 预算：36 个逻辑运行；每 run 最多 3 次尝试；全批次最多 108 次物理请求；每 provider 最多 54 次。
- 必须保留：runs JSONL、预算账本、raw response、请求前阻塞证据和模型身份/解码参数。
- 禁止：修改旧批次、混合 v3/v4 统计、读取或输出 evaluator-only 标签、修改 prompt/Schema/runner 以迁就单条响应、C2、IR、CAD、geometry、STEP。
- 5xx 继续遵循 ADR-0010 的最多两次重试；不能用增加重试次数掩盖服务不稳定。

## 放行顺序

1. 项目负责人关闭 P1/P2，或明确批准对应 ADR amendment。
2. Codex 根据本文件和授权模板复核当前仓库、环境、冻结 hash、retrieval index 和空批次目录。
3. 项目负责人填写并明确批准授权模板中的唯一 `batch_id`、provider 范围和预算；当前代码只接受冻结的完整 36-run scope，不能临时缩小 provider 或样例范围。
4. CC 使用现有 runner 执行；不得修改生产代码或授权工厂。
5. Codex 独立复核 raw response、预算、身份、解析、Schema、决策、失败证据和 provider 错误；真实效果结论与离线测试分开报告。

## 当前结论

`APP-001-V4-FORMAL-EFFECT-EVALUATION` 尚未放行。v4 已是生产离线契约，但 P1/P2 文档/决策门关闭前不得启动真实模型批次。

## handoff_self_check

```text
changed=agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md,
        agent-work/llm/APP-001-v4-effect-evaluation/authorization-request-template.md,
        agent-work/llm/APP-001-v4-effect-evaluation/checkpoint.md,
        docs/PROJECT_STATUS.md, docs/PROJECT_PLAN.md, docs/WORKLOG.md
commands=git status/rev-parse/remote ref checks; source inspection of authorization.py,
         runner.py, ADR-0014/0015; no model or key access
confirmed=v4 identity, dynamic authorization scope, 36/108/54 budget,
          retrieval identity gate, old-batch read-only boundary
unresolved=P1 evidence-null decision closeout; P2 ADR-0014 v4 scope documentation;
          owner batch authorization; runtime environment checks
next_agent_focus=Codex closes P1/P2 and performs preflight; CC executes only after
                  explicit owner authorization
```
