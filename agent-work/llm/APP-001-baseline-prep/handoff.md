# APP-001-PREP handoff

Date: 2026-11-05
Task: `APP-001-PREP`
Status: `review`
Work root: `/Users/syd/Desktop/参数化 cad 工程辅助设计`

## Delivered

- `prompt-v1.md`: candidate-frozen system/user template with strict JSON envelope and explicit-vs-derived boundary.
- `acceptance-set-v0.json`: nine evaluator-only cases retained; candidate-freeze metadata added, formal use remains disallowed.
- `model-baselines-v0.yaml`: cloud/local identities, runtime versions, seed status, no-think settings, retry and logging fields updated.
- `runtime-probe-2026-11-05.json`: sanitized DeepSeek seed capability observations appended to the prior identity probe; no reply content or request IDs saved.
- `prompt-output-contract-v0.md`: candidate prompt version and remaining hub checks updated.
- `checkpoint.md`, project status/tasks, and append-only `docs/WORKLOG.md` updated.

## Successor check performed

```text
predecessor=APP-001-PREP draft checkpoint/handoff; prior commits 0bfc75b and d7486e7
files_format=pass; YAML/JSON artifacts parse and prompt file is versioned
core_rerun=CAD-003 strict envelope normal and missing-selector failure check passed
normal_case=bore_d=24 -> schema ok with catalog-derived fields
failure_case=outer_d/width without bore_d -> MISSING_REQUIRED; no guess
interface=prompt inner cad_parameters projects only to CAD-003; retrieval context remains reference-only
limits=review gate, no formal runs, no performance result, no cross-provider equivalence claim retained
result=pass_with_review_gate
blocking_issue=Codex hub/project-owner confirmation and adapter/logger review still required
```

## Probe evidence and limits

DeepSeek seed was accepted twice with the same short prompt and seed (`271828`), returning HTTP 200 and `model=deepseek-flash` with usage/cache metadata. This is a non-evaluation capability observation, not an output-repeatability guarantee. The two calls used at most the permitted probe count and cost CNY 0.000232 by the dated rate-card calculation; the earlier identity probe cost CNY 0.000128. Ollama 0.33.2 accepted `think=false`, JSON format, common decode fields and seed on both `/api/chat` and `/api/generate`; both returned valid JSON without a thinking field. No model response text, hidden reasoning, key, Authorization header, or complete error body was retained.

The local runtime mode is verified as an Ollama capability setting, but is provider-specific. A future cloud/local comparison must disclose that the modes are not established as semantically equivalent. All formal language, Schema, IR, CAD, STEP, latency and cost outcomes remain `not_measured`.

## Handoff self-check

```text
handoff_self_check:
  changed=prompt-v1, acceptance candidate metadata, baseline YAML, contract, sanitized runtime probe, checkpoint/handoff, status/tasks, WORKLOG append
  commands=Git startup, environment checks, two static CAD-003 cases, YAML/JSON parsing, diff check, ignore and prompt-leak scans all passed
  confirmed=runtime model identity; seed parameter acceptance; Ollama no-think JSON configuration; evaluator/model input separation; secret handling
  unresolved=final hub review, project-owner confirmation, execution adapter/logger review, fair comparison mode equivalence
  next_agent_focus=independently inspect prompt truth isolation and output adapter; keep APP-001 planned and formal gate false
```
