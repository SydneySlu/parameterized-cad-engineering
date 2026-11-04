# APP-001-PREP handoff

Date: 2026-11-04
Task: `APP-001-PREP`
Status: `review`
Work root: `/Users/syd/Desktop/参数化 cad 工程辅助设计`

## Delivered

- `model-baselines-v0.yaml`: fixed user-provided labels, Ollama digest and Mac device; records cloud API model as `model_id_pending_runtime_probe`; decoding and runtime version fields are pending.
- `acceptance-set-v0.json`: nine evaluator-labeled examples covering the requested eight categories plus an explicit `second_screw` rule conflict. Status remains `review`; evaluator labels are explicitly not model-visible.
- `prompt-output-contract-v0.md`: proposes a versioned transport envelope, evidence/missing/question/confidence semantics, strict CAD-003 projection boundary, error/timeout shape, measurement order and comparison rule.
- `checkpoint.md`: records self-check, limitations, successor check pending and hub review pending.

## Confirmed and not confirmed

Confirmed from project records: DeepSeek v4.1 Flash 1017 is the cloud label; Ollama `qwen3:8b` digest/ID is `500a1f067a9f`; first local baseline device is MacBook Air M5, 16 GB RAM, 512 GB SSD; CAD-003's sole required selector is `bore_d`; catalog-derived fields and the strict `second_screw == 1 iff bore_d > 70` rule; RET-003 candidates are references, not answers. API-returned identity was **not** retrieved: common environment-variable presence check found no configured key, no request was made, and the artifact uses `model_id_pending_runtime_probe`.

Still requiring project-owner confirmation: provider/endpoint and returned `model`; Prompt and sample freeze; temperature/top-p/max tokens/seed/stop behavior; confidence use; retry/timeout and cost recording policy. The proposed output only carries user-explicit parameters into CAD-003 and leaves supported derivation to deterministic rules; review this responsibility boundary before freeze.

## Verification and limits

Commands and results are recorded in `docs/WORKLOG.md`. This work only drafts and inspects protocol materials. No formal cloud/local comparison, no model output, and no C0/C1, Schema, IR, CAD, geometry or STEP performance result was generated. No API key was read, written or committed. All outcome metrics remain `not_measured`.

## Handoff self-check

```text
handoff_self_check:
  changed=the four draft artifacts, this handoff, checkpoint, and append-only WORKLOG entry
  commands=see WORKLOG; no API request or formal experiment
  confirmed=baseline labels and device; Schema derivation and rejection semantics; retrieval example boundary
  unresolved=API model identity; owner choices for decoding and protocol; independent Codex review
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
  limits=recorded above; no formal model outputs
  result=review
  blocking_issue=successor review and Codex hub independent review pending
```

Next step: the successor/Codex hub should validate the labels and transport-to-CAD-003 projection, then ask the project owner to confirm unresolved protocol fields. Do not freeze this draft or start formal APP-001 until that review and confirmation are recorded.
