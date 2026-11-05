# APP-001-PREP handoff

Date: 2026-11-04
Task: `APP-001-PREP`
Status: `review`
Work root: `/Users/syd/Desktop/参数化 cad 工程辅助设计`

## Delivered

- `model-baselines-v0.yaml`: fixed user-provided labels, Ollama digest and Mac device; records cloud API model as `model_id_pending_runtime_probe`; includes configured/runtime identity fields, shared decoding defaults and transient-only retry policy.
- `acceptance-set-v0.json`: nine evaluator-labeled examples covering the requested eight categories plus an explicit `second_screw` rule conflict. Status remains `review`; evaluator labels are explicitly not model-visible.
- `prompt-output-contract-v0.md`: proposes a versioned transport envelope, evidence/missing/question/confidence semantics, strict CAD-003 projection boundary, error/timeout shape, measurement order and comparison rule.
- `checkpoint.md`: records self-check, limitations, successor check pending and hub review pending.

## Confirmed and not confirmed

Confirmed from project records and official DeepSeek docs: request model ID `deepseek-flash`, documented served version `DeepSeek-V4.1-Flash-1017`, OpenAI-compatible Base URL `https://api.deepseek.com`; Ollama `qwen3:8b` digest/ID is `500a1f067a9f`; first local baseline device is MacBook Air M5, 16 GB RAM, 512 GB SSD; CAD-003's sole required selector is `bore_d`; catalog-derived fields and the strict `second_screw == 1 iff bore_d > 70` rule; RET-003 candidates are references, not answers. Actual API response identity/usage were **not** retrieved because no request was made. `.env.example` documents the `DEEPSEEK_API_KEY` variable; enter the real key only in a local ignored root `.env` or export it in the shell.

Project-owner initial choices: output only user-explicit parameters; confidence is not used in decisions; retry only transient call faults, at most two retries after the initial request; log cloud tokens/fees and local elapsed time; preserve configured and runtime-returned provider/model identities separately. The contract sets temperature 0, top_p 1, max output 512 tokens and seed-if-supported; verify applied settings in each run record.

Still requiring runtime/freeze work: seed support and production runtime versions; verify/log Ollama runtime mode; final prompt/sample freeze; Codex review of the execution adapter/logger. One minimal probe returned `model=deepseek-flash` and usage/cache fields, with no provider response field; its response body was not saved. Official price snapshot observed 2026-11-05 is recorded in the YAML and baseline contract. The owner selected explicit thinking disabled for the first formal DeepSeek baseline; Ollama mode is provider-specific and remains to be verified separately. API credentials were not logged or stored.

## Verification and limits

Commands and results are recorded in `docs/WORKLOG.md`. This work includes one minimal non-evaluation API probe; no acceptance sample, formal cloud/local comparison, or C0/C1, Schema, IR, CAD, geometry or STEP performance result was generated. No API key was logged or stored; `.env.example` contains only a placeholder, and the response body was not saved. All outcome metrics remain `not_measured`.

## Handoff self-check

```text
handoff_self_check:
  changed=the four draft artifacts, this handoff, checkpoint, and append-only WORKLOG entry
  commands=see WORKLOG; no API request or formal experiment
  confirmed=baseline labels and device; Schema derivation and rejection semantics; retrieval example boundary
  unresolved=runtime API identity and seed capability; final sample/prompt freeze; execution adapter/logger review
  next_agent_focus=validate JSON/YAML, sample truth against CAD-003, and adapter projection against strict schema; keep status review
```

## Successor and hub review

```text
handoff_successor_check:
  predecessor=APP-001-PREP, checkpoint.md, draft commit 0bfc75b (follow-up log commit d7486e7)
  files_format=not_run
  core_rerun=not_run
  normal_case=not_run
  failure_case=not_run
  interface=not_run
  limits=recorded above; no formal model outputs; initial policy decisions recorded in ADR-0010
  result=review
  blocking_issue=final prompt/sample freeze and runtime identity probe remain
```

Next step: complete final prompt/sample freeze and runtime identity probe; keep all formal metrics `not_measured` until APP-001 is expressly released.
