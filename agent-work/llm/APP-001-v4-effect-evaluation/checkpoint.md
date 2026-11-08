# APP-001-V4-FORMAL-EFFECT-EVALUATION checkpoint

- Status: review / preflight pending owner authorization
- Owner: Codex hub (planning and preflight), CC (later execution)
- Production baseline: `main` / `origin/main` at `7bafecb`
- Prompt: `app001-extraction.v4`
- No real model request has been authorized or started by this work unit.

## Current handoff

- Readiness review: `agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md`
- Authorization template: `authorization-request-template.md`
- Existing formal authorization path: `src/llm/authorization.py`
- Existing runner: `src/llm/runner.py`

## Closed preconditions

- ADR-0015 evidence-null gate: closed by `docs/DECISIONS.md` ADR-0015-CLOSEOUT, based on merged parser fix `352ef8a` and independent review.
- ADR-0014 scope synchronization: current v4 inherited scope appended as ADR-0014-AMENDMENT; original v2 authorization table remains historical and unchanged.

## Remaining approval gate

- Project owner must approve one new unique batch ID and the exact frozen full scope in `authorization-request-template.md`.
- Codex final preflight must pass on the approved `main` commit and fixed runtime before any real request.

## Boundary

- Do not call DeepSeek/Ollama.
- Do not read or print API keys.
- Do not modify old batches.
- Do not run C2, IR, CAD, geometry, or STEP.
- Do not change production code to make a narrower or different authorization scope fit.

## handoff_self_check

```text
changed=readiness review, checkpoint, status/decision/worklog synchronization
commands=main/origin sync, Python 3.11.18, prompt/schema/hash and runtime identity checks;
         no model chat request and no key value access
confirmed=v4 production identity, exact current authorization scope, budget limits,
          retrieval-index gate, runtime/provider freeze, old-batch isolation, P1/P2 closed
unresolved=owner authorization; no model request started
next_agent_focus=project owner fills and approves authorization template, then hand CC the approved batch
result=review
```
