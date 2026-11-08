# APP-001 v4 正式批次授权模板

> 这是一份待填写、待批准的模板，不是授权本身。填写前不得调用 DeepSeek/Ollama。

## 批次身份

```text
task_id: APP-001-V4-FORMAL-EFFECT-EVALUATION
batch_id: <new-unique-id>
requested_by: <name>
approved_by: <project-owner>
approval_time: <Asia/Shanghai timestamp>
repository_commit: <main commit after P1/P2 closeout>
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
[ ] 我批准使用新的唯一 batch_id，不覆盖任何旧批次。
[ ] 我批准完整的 36 个逻辑运行范围（9 × 2 条件 × 2 provider）。
[ ] 我批准 DeepSeek deepseek-flash 和 Ollama qwen3:8b 两个 provider/model。
[ ] 我批准最多 108 次物理请求、每 provider 最多 54 次、每 run 最多 3 次尝试。
[ ] 我确认 C2、IR、CAD、geometry、STEP 本批次全部禁用。
[ ] 我确认 P1 evidence-null 决策门已关闭，P2 ADR-0014 scope 已同步。
[ ] 我确认旧批次只读，结果不与 v3 或其他版本混合统计。

approval_signature: <project-owner>
approval_timestamp: <timestamp>
```

## 执行者承诺

```text
executor: CC
preflight_commit: <hash>
python: <exact version>
ollama_runtime: <version/service/digest/schema hash>
retrieval_manifest_sha256: <hash>
formal_authorization_scope_hash: <hash>
raw_retention_path: work/app001-runs/<batch-id>/raw/
```

CC 只调用现有 runner，不能修改生产代码、prompt、Schema、预算或授权 scope。遇到 P1/P2 不一致、身份不符、预算异常、请求前阻塞或 5xx 证据不足时停止并记录，不自行扩大范围。

## Codex 放行栏

```text
codex_preflight_result: pass | review | blocked
codex_reviewer: <name>
codex_review_commit: <hash>
codex_notes: <short evidence-based notes>
```
