# APP-001-PREP handoff

> Current authority (2026-11-05): see `APP-001-PREP-FINAL-FIX` at the end. Current frozen artifacts are `prompt-v2.md`, `prompt-output-contract-v1.md`, and `acceptance-set-v0.json`. Adapter/logger is complete and accepted; no formal model/evaluation run is authorized.

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

## Handoff self-check (historical; before adapter R3-FIX acceptance)

```text
handoff_self_check:
  changed=prompt-v1, acceptance candidate metadata, baseline YAML, contract, sanitized runtime probe, checkpoint/handoff, status/tasks, WORKLOG append
  commands=Git startup, environment checks, two static CAD-003 cases, YAML/JSON parsing, diff check, ignore and prompt-leak scans all passed
  confirmed=runtime model identity; seed parameter acceptance; Ollama no-think JSON configuration; evaluator/model input separation; secret handling
  historical_unresolved=final hub review, project-owner confirmation, execution adapter/logger review, fair comparison mode equivalence
  historical_next_agent_focus=independently inspect prompt truth isolation and output adapter; keep APP-001 planned and formal gate false
```

## APP-001-PREP-R2 document consistency correction

- Prior delivery commit: `c255d4e`.
- Corrected the output-envelope example's `prompt_version` to `app001-extraction.v1` and removed the extra trailing blank line from `prompt-v1.md`.
- Checked current Prompt version references across `prompt-v1.md`, `prompt-output-contract-v0.md`, and `model-baselines-v0.yaml`; all agree on `app001-extraction.v1`. Historical records were left unchanged.
- No JSON/YAML was changed. Validation is limited to the version-consistency check and `git diff --check HEAD^ HEAD`; no model calls, acceptance samples, or quality measurements were run.
- Handoff remains `review`; Codex hub review is required before any APP-001 release decision.

## ADR-0013 freeze handoff (historical; before adapter R3-FIX acceptance)

- Frozen: `app001-io.v1`, `app001-extraction.v2`, and nine evaluator-only `acceptance-set-v0` cases. Model explicit claims are scored separately from the deterministic CAD-003 projection.
- A01 now scores only user-explicit fields as model extraction; catalog/rule values are evaluated after deterministic projection. The prompt template accurately describes three placeholders; family ID is fixed text.
- Validation performed: JSON parse for the acceptance set; YAML parse for the baseline; protocol/version consistency and evaluator-label isolation checks; `git diff --check`. No LLM/API calls and no sample evaluation were run.
- Historical record (superseded): `Remaining gate: implement and review the execution adapter/logger`. This described the state before adapter R3-FIX acceptance; adapter/logger is now complete and accepted. Explicit project-owner authorization remains required before any formal run. At this historical checkpoint, task status was `APP-001-PREP=review`; `APP-001=planned`.

## APP-001-PREP-FINAL-FIX

- `APP-001-ADAPTER-R3-FIX` 已由 Codex 中枢验收通过；`APP-001-ADAPTER=done`。adapter/logger 已完成，并经过 170 个 LLM 测试、17 个 Schema 测试验证。
- `APP-001-PREP` 当前仍为 `review`；`APP-001` 当前仍为 `planned`；`formal_evaluation_allowed=false`。
- 九条 evaluator-only 样例仍未运行；真实 DeepSeek/Ollama 正式运行仍未进行。
- 正式字段、Schema、CAD、STEP、费用和延迟指标仍为 `not_measured`；IR → Typed CAD IR 映射仍未冻结。
- PREP 剩余事项是本次文档状态收尾和 Codex 最终复核。最终模型运行仍需项目负责人单独授权。
- 历史记录说明：此前 ADR-0013 handoff 中的 `Remaining gate: implement and review the execution adapter/logger` 是历史记录，描述当时尚未完成的事项；adapter/logger 后续已完成并验收，不应再视为当前 gate。
