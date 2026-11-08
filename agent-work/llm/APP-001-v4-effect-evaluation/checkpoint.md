# APP-001-V4-FORMAL-EFFECT-EVALUATION checkpoint

- Status: planned / blocked pending P1 and P2 closeout
- Owner: Codex hub (planning and preflight), CC (later execution)
- Production baseline: `main` at `abcb8f0`
- Prompt: `app001-extraction.v4`
- No real model request has been authorized or started by this work unit.

## Current handoff

- Readiness review: `agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md`
- Authorization template: `authorization-request-template.md`
- Existing formal authorization path: `src/llm/authorization.py`
- Existing runner: `src/llm/runner.py`

## Blocking conditions

1. ADR-0015 evidence-null decision gate needs an explicit closeout entry after the merged parser fix and independent review.
2. ADR-0014 historical v2 scope wording needs a v4 current-scope amendment or equivalent synchronization before authorization.
3. Project owner must approve one new unique batch ID and the exact frozen full scope.

## Boundary

- Do not call DeepSeek/Ollama.
- Do not read or print API keys.
- Do not modify old batches.
- Do not run C2, IR, CAD, geometry, or STEP.
- Do not change production code to make a narrower or different authorization scope fit.

## handoff_self_check

```text
changed=readiness review, authorization template, checkpoint, status/plan/worklog
commands=repository/remote checks and source/decision inspection completed
confirmed=v4 production identity, exact current authorization scope, budget limits,
          retrieval-index gate, runtime/provider freeze and old-batch isolation
unresolved=P1/P2 decision/documentation gates; owner authorization; preflight checks
next_agent_focus=close decisions, run Codex preflight, then hand CC the approved batch
result=review
```
