# APP-001-NEXT-REAL-MODEL-EVALUATION checkpoint

## Status

`blocked` — the project owner approved the proposed experimental question and
scope in principle, and asked Codex to validate the offline design before
assigning a batch ID. Validation found unresolved input-provenance and
authorization-interface blockers. No batch ID has been assigned and no model
request is authorized.

## Repository and predecessor facts

- Repository: `/Users/syd/Desktop/参数化 cad 工程辅助设计`.
- Branch: `main`; HEAD `2054565b15ba232d151664bfa832b77be10d5a14`.
- `origin/main`: `95d1dcb8e1ba693769b19b1262228c51ba4f8f7d`; local main is ahead
  by two documentation commits. Worktree was clean before this checkpoint.
- Proposal: `agent-work/inbox/APP-001-NEXT-REAL-MODEL-EVALUATION-PROPOSAL.md`.
- Predecessor v5 batch `app001-phase1-v5-20261111-01` is immutable and read-only.
  Its historical raw path deviation remains documented; never move, rewrite,
  rerun, or combine it with a future batch.

## Proposed scope retained

- Question: compare v5 outputs and deterministic CAD-003 acceptance with/without
  RET-002 retrieval for the three RET-003 held-out cases, case by case.
- Matrix: 3 cases × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b` = 12
  logical runs; maximum 3 attempts/run, 36 total, 18/provider.
- C1 uses only RET-002 `retrieval_source` candidates. Exclude C2/C2O and all
  IR/CAD/geometry/STEP execution. `provisional_small_n` requires per-case
  reporting and forbids broad generalization claims.

## Offline validation and evidence

Environment: Python 3.11.18 (macOS arm64). No model/network request, credential
or `.env` read, batch directory creation, or formal-run execution occurred.

Commands and results:

```text
git rev-parse --show-toplevel
  -> /Users/syd/Desktop/参数化 cad 工程辅助设计
git status --short --branch
  -> main...origin/main [ahead 2] (clean before this checkpoint)
git rev-parse HEAD
  -> 2054565b15ba232d151664bfa832b77be10d5a14
/opt/homebrew/bin/python3.11 --version
  -> Python 3.11.18
Read acceptance-set-v0.json model-visible case IDs/NLI/claims
  -> 9 acceptance cases; no RET-003 held-out query IDs; bore_d=80 case
     explicitly claims second_screw=0 and is a rule-conflict case
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 - [read-only projection/plan check]
  -> normal: frozen nine-case projection generates 36 combinations
  -> failure: three-case projection rejected: expected 9 acceptance cases, got 3
```

The initially attempted helper name `load_acceptance_set` does not exist; the
correct production API is `project_acceptance_set`. The corrected command above
used the actual API, pinned the acceptance-set SHA-256, and checked normal and
rejection paths. This was an inspection-command correction, not a code defect.

## Blocking issues

1. **Natural-language input provenance:** RET-003's held-out records reference
   manifest parameters as evaluator truth; they do not freeze natural-language
   requests. The acceptance set's existing requests do not correspond to the
   three held-out IDs, and the bore_d=80 sample has a separate explicit rule
   conflict. Do not invent or derive user wording from held-out truth. An
   input-construction protocol and separate model-visible/evaluator-only
   artifact must be defined, frozen, hashed, and independently checked for
   leakage before execution work continues.
2. **Exact-scope authorization:** `FormalRunAuthorization` and
   `generate_combinations()` are explicitly frozen to acceptance-set-v0, 9
   cases, C0/C1, 2 providers, 36 logical runs and 108/54 attempt caps. The
   normal plan returns 36; a 3-case projection fails closed. Do not bypass the
   factory, relax it globally, or reuse `scripts/run_app001_v5_formal_batch.py`.
   A new exact 12-run authorization path and new entrypoint need a recorded
   decision before implementation, with 12/36/18 caps and hash-bound query
   inputs.

## Required next gate

Ask the project owner to resolve/approve:

- whether to author three new natural-language queries under a documented
  protocol that keeps manifest truth evaluator-only, or revise the experiment
  to an already frozen model-visible dataset with an honest held-out mapping;
- the exact-scope new authorization mechanism and its 12-run / 36 total / 18
  per-provider limits.

After that: freeze inputs and labels separately with hashes; run an independent
leakage review; record the necessary ADR/decision; implement a dedicated
fail-closed 12-run entrypoint and offline tests; run Python 3.11.18 regressions;
complete independent review and final preflight. Only then generate a new unique
batch ID and present the complete authorization template for explicit approval.

## Handoff self-check

```text
handoff_self_check:
  changed=proposal status/gates; this checkpoint; PROJECT_STATUS; PROJECT_PLAN; WORKLOG
  commands=Python 3.11.18 pinned acceptance projection and combination normal/failure checks above
  confirmed=approved question/scope in principle; missing held-out NLI; existing scope rejects 3 cases; no model request
  unresolved=input provenance protocol and exact-scope authorization decision
  next_agent_focus=prevent truth-derived prompt leakage and keep existing Phase 1 authorization frozen
```
