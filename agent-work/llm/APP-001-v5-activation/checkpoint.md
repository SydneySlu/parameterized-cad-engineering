# APP-001-V5-ACTIVATION checkpoint

## Status

`review` — ADR-0018 strategy accepted by the project owner on 2026-11-11. Activation implementation is on a Codex branch and has not been independently approved or merged to `main`. No real-model evaluation is authorized.

## Scope and changes

- Freeze `prompt-v5.md` and record candidate, preparation, acceptance-set, and v4 rollback hashes in `manifest.json`.
- Switch only the active prompt version/path/hash and parser default version; retain explicit v2/v3/v4 historical audit versions.
- Preserve `app001-io.v1`, CAD schema, budget/retry/authorization, `FORMAL_EVALUATION_ALLOWED=False`, and all prior batches.

## Git state

- Branch: `codex/APP-001-V5-ACTIVATION`
- Activation implementation commit: `d48cc66`
- The worktree was clean immediately after the implementation commit.

## Handoff self-check

```text
handoff_self_check:
  changed=prompt-v5.md, manifest.json, README.md, checkpoint.md, contract.py, prompt_loader.py, parser.py, compatibility tests, project status/plan, WORKLOG, ADR-0018
  commands=Python 3.11.18 targeted activation/prep/candidate/parser/adapter/envelope tests: 279 passed after independent review fixes; LLM discover: 811 passed, 8 skipped; Schema discover: 17 passed; py_compile and full main-to-worktree git diff --check passed
  confirmed=owner accepted ADR-0018; v5 candidate normal and refusal/conflict paths are covered offline; v4 frozen hash remains the rollback anchor
  unresolved=Codex independent review and merge to main remain; existing formal batch script is v4-specific and cannot run v5; no real model effect evidence
  next_agent_focus=verify prompt and manifest hashes; default parser accepts v5 and rejects v4; explicit v4 audit works; formal gate remains false; tests under Python 3.11.18
```
