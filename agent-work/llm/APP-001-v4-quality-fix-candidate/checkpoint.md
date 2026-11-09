# APP-001-V4-QUALITY-FIX-CANDIDATE checkpoint

- Status: in_progress / candidate checker and tests written; awaiting Codex review
- Owner: CC (candidate implementation), Codex hub (independent review)
- Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`
- Base: `main` at `b1a31b9` (which is a descendant of the authorized baseline `cc3dfbb`)
- No real model request has been made at any point.

## Modified files

- `src/llm/decision_policy_v5_candidate.py` — NEW: offline P1/P2 checker
- `tests/llm/test_decision_policy_v5_candidate.py` — NEW: 51 offline tests
- `agent-work/llm/APP-001-v4-quality-fix-candidate/candidate-strategy.md` — NEW
- `agent-work/llm/APP-001-v4-quality-fix-candidate/checkpoint.md` — this file
- `agent-work/llm/APP-001-v4-quality-fix-candidate/handoff.md` — NEW
- `docs/WORKLOG.md` — appended

No production files modified: adapter.py, parser.py, runner.py, contract.py,
prompt_loader.py, prompt-v4.md, acceptance-set-v0.json, RET-002, CAD-003,
ADR, budget, authorization, or old batches are all unchanged.

## Verification commands and results

```bash
# Python 3.11.17
~/.local/bin/python3.11 -m py_compile src/llm/decision_policy_v5_candidate.py tests/llm/test_decision_policy_v5_candidate.py
# → ok

PYTHONPATH=src:. ~/.local/bin/python3.11 -m pytest tests/llm/test_decision_policy_v5_candidate.py -v
# → 51 passed in 0.04s

PYTHONPATH=src:. ~/.local/bin/python3.11 -m pytest \
  tests/llm/test_decision_policy_v5_candidate.py \
  tests/llm/test_decision_policy_v4_candidate.py \
  tests/llm/test_decision_policy_v3_candidate.py \
  tests/llm/test_authorization.py \
  tests/llm/test_parser.py \
  tests/llm/test_budget.py \
  tests/llm/test_run_script_v4_batch.py \
  -v
# → 236 passed, 6 skipped, 6 subtests passed in 0.70s

git diff --check HEAD
# → clean
```

## Normal case (passes)

A02 C0 answer with bore_d=24, missing_fields=[], unsupported_requests=[]:
→ check_v5_envelope returns ok=True, zero P1 violations.

## Failure cases (detected)

- A02 C1 refuse with bore_d=24, missing_fields=[], unsupported_requests=[]:
  → P1-1 violation (over-refusal detected).
- A03 C0 refuse with bore_d=16 (unit-converted), missing_fields=[], unsupported_requests=[]:
  → P1-1 violation.
- A08 C1 refuse with bore_d=24, missing_fields=[], unsupported_requests=[]:
  → P1-1 violation.
- A05 C0 ask with outer_d in both extracted_parameters and missing_fields:
  → P2-1 violation (envelope self-consistency).
- A05 C1: same P2-1 violation.

## Reverse cases (correctly NOT flagged)

- A04 refuse/ask without bore_d: P1 does NOT fire (bore_d absent).
- A07 refuse with bore_d=75 (out of catalog) + unsupported: P1 does NOT fire.
- A05 ask with catalog conflict (missing_fields non-empty): P1 does NOT fire.
- A09 refuse with rule conflict: P1 does NOT fire.

## Production isolation

Verified by AST scan and file content check:
- v5 module imports only: stdlib, schema.set_screw_shaft_collar (read-only)
- v5 is NOT imported by: adapter.py, parser.py, runner.py, contract.py, prompt_loader.py

## handoff_successor_check

```text
read=AGENTS.md, PROJECT_STATUS, WORKLOG, DECISIONS, codex review, prompt-v4,
     acceptance-set-v0, parser.py, contract.py, v3/v4 candidate code
reran=tests/llm/test_decision_policy_v4_candidate.py (passing),
      tests/llm/test_authorization.py (passing),
      tests/llm/test_run_script_v4_batch.py (passing)
normal_case=A02 C0 answer with bore_d=24 → v5 ok=True
failure_case=A02 C1 refuse with bore_d=24 → v5 P1-1 violation detected
boundary=A05 outer_d in both extracted and missing → v5 P2-1 violation detected
isolation=v5 not imported by adapter/parser/runner/contract/prompt_loader (AST + text scan)
versions=CANDIDATE_VERSION=app001-extraction.v5-candidate, CONTRACT_VERSION=app001-io.v1
unresolved=Codex independent review; activation requires new batch_id + authorization
next_agent_focus=Codex reviews candidate for correctness and decides whether to
                 authorize a new formal batch with a v5 prompt (if any)
result=pass
```

## Boundary

- No model call, no network access, no API key read or printed.
- No production code, prompt, schema, budget, authorization, or old batch modified.
- No new formal batch created or authorized.
- Offline checker pass ≠ model effect pass.
- If a future formal test is needed, a new unique `batch_id` and Codex preflight
  authorization are required.
