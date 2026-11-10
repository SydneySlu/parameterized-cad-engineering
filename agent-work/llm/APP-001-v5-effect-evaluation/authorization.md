# APP-001 v5 real-model evaluation authorization

## Authorization source

On 2026-11-11, the project owner explicitly directed Codex to proceed with v5
effect evaluation and required that the work reach real-model testing. This
authorization record scopes that instruction to the existing frozen APP-001
Phase 1 matrix. It does not authorize changes to the prompt, schema, retry
policy, provider configuration, or evaluation stages.

```text
task_id: APP-001-V5-FORMAL-EFFECT-EVALUATION
batch_id: app001-phase1-v5-20261111-01
requested_by: Wang sikai
approved_by: Wang sikai (direct instruction in this conversation)
approval_date: 2026-11-11 Asia/Shanghai
approval_signature: direct user instruction to proceed to real-model testing
repository_baseline: 2c702257ed56b3d9e49209f0455c2aaffb608b8b
authorization_scope_hash: dd7801f24ccc47911458df0dea4a4e251de2b09469bc40baa55807f74736a5b1
```

## Fixed scope

```text
contract_version: app001-io.v1
prompt_version: app001-extraction.v5
prompt_sha256: 18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9
activation_manifest_sha256: a7eeed5fea5ef993fd2a100bae0b8f3d972678ffb989036018ef82af75dd0e16
sample_set: acceptance-set-v0 (9 cases)
conditions: C0, C1
providers/models: DeepSeek/deepseek-flash; Ollama/qwen3:8b
max_logical_runs: 36 (9 cases × 2 conditions × 2 providers)
max_attempts_per_run: 3
max_batch_attempts: 108
max_provider_attempts: 54
Ollama runtime: Homebrew 0.40.14, qwen3:8b digest prefix 500a1f067a9f
Ollama format schema sha256: 7c201710fae0ff3cc3b811c28739393762f1886a5e79bd255cbda8671ac03143
C2/IR/CAD/geometry/STEP: disabled
old batches: read-only; never pool or overwrite
raw retention: work/app001-runs/app001-phase1-v5-20261111-01/raw/ (git-ignored)
```

The ADR-0015 hash `d82e53ad…` is the historical v2 schema fingerprint; the v4
readiness record used `04d159d2…`. The v5 schema embeds the active v5 prompt
version and therefore has its own hash above, recomputed from the current
`OLLAMA_FORMAT_SCHEMA` and checked by the v5 script test and preflight.

The scope hash is recomputed by the v5 batch script and must match before any
provider request. The batch directory must be absent. Preflight requires a
clean descendant of the reviewed baseline, Python 3.11.18, frozen prompt and
manifest hashes, the RET-002 manifest identity, the exact Ollama version/model
digest/schema, and a present `DEEPSEEK_API_KEY`; the key value is never printed
or recorded. Any mismatch aborts the run before model chat calls.

`FORMAL_EVALUATION_ALLOWED` remains `False`; the existing narrow
`FormalRunAuthorization` object is the only path used by the runner. No C2 or
downstream CAD stages are enabled by this task.
