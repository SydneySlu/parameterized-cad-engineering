# APP-001 v4 正式批次授权模板

> 这是一份待填写、待批准的模板，不是授权本身。填写前不得调用 DeepSeek/Ollama。

## 批次身份

```text
task_id: APP-001-V4-FORMAL-EFFECT-EVALUATION
batch_id: app001-phase1-v4-20261109-01
requested_by: Wang sikai
approved_by: Wang sikai
approval_time: 2026-11-09 00:10 Asia/Shanghai
repository_commit: 80cad1b7fc110e0aa10c63aced7271749c3ffadf
```

## 固定 scope（不得自行修改）

```text
contract_version: app001-io.v1
prompt_version: app001-extraction.v4
prompt_sha256: 73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc
sample_set: acceptance-set-v0 (9 cases)
conditions: C0, C1
providers/models: DeepSeek/deepseek-flash; Ollama/qwen3:8b
max_logical_runs: 36
max_attempts_per_run: 3
max_batch_attempts: 108
max_provider_attempts: 54
ir_cad_geometry_step: disabled
```

> `prompt_sha256` 必须由运行前脚本从文件重新计算；上面的值只是模板锚点，若不一致立即停止。

## 项目负责人明确确认

```text
[x] 我批准使用新的唯一 batch_id，不覆盖任何旧批次。
[x] 我批准完整的 36 个逻辑运行范围（9 × 2 条件 × 2 provider）。
[x] 我批准 DeepSeek deepseek-flash 和 Ollama qwen3:8b 两个 provider/model。
[x] 我批准最多 108 次物理请求、每 provider 最多 54 次、每 run 最多 3 次尝试。
[x] 我确认 C2、IR、CAD、geometry、STEP 本批次全部禁用。
[x] 我确认 P1 evidence-null 决策门已关闭，P2 ADR-0014 scope 已同步。
[x] 我确认旧批次只读，结果不与 v3 或其他版本混合统计。

approval_signature: Wang sikai
approval_timestamp: 2026-11-09 00:10 Asia/Shanghai
```

## 执行者承诺

```text
executor: CC
preflight_commit: 80cad1b7fc110e0aa10c63aced7271749c3ffadf
python: 3.11.18 (/opt/homebrew/bin/python3.11)
ollama_runtime: Homebrew formula 0.40.14; service sh.brew.ollama; model qwen3:8b; digest prefix 500a1f067a9f; format_schema_sha256 04d159b287e093b92e2b0157e46e9b1d7b549fa8b81b20ee08da9e1e5f610e70
retrieval_manifest_sha256: b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297
formal_authorization_scope_hash: a57b69664e816be709cc7dfd049dbad389461203857f27ea3ffe302729d04c5f
raw_retention_path: work/app001-runs/app001-phase1-v4-20261109-01/raw/
```

CC 只调用现有 runner，不能修改生产代码、prompt、Schema、预算或授权 scope。遇到 P1/P2 不一致、身份不符、预算异常、请求前阻塞或 5xx 证据不足时停止并记录，不自行扩大范围。

## Codex 放行栏

```text
codex_preflight_result: pass
codex_reviewer: Codex hub
codex_review_commit: 80cad1b7fc110e0aa10c63aced7271749c3ffadf
codex_notes: Batch ID is new and its run directory is absent; v4 prompt/loader hash, acceptance-set hash, Ollama schema hash, RET-002 manifest identity, authorization scope (36/108/54/3), and Python 3.11.18 runtime match frozen records. No model request or key value access occurred during preflight.
```
