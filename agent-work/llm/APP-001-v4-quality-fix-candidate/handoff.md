# APP-001-V4-QUALITY-FIX-CANDIDATE handoff

From: CC  
To: Codex hub (independent review)  
Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`  
Base commit: see `git log --oneline -1`

## What was done

1. Created `src/llm/decision_policy_v5_candidate.py` — pure-function offline
   checker implementing P1 (over-refusal detection) and P2 (envelope
   self-consistency) rules.  Not imported by any production path.
2. Created `tests/llm/test_decision_policy_v5_candidate.py` — 51 offline tests,
   all passing on Python 3.11.17.  Cover all required fixture cases from the task.
3. Created `agent-work/llm/APP-001-v4-quality-fix-candidate/candidate-strategy.md`
   describing the rules, confirmed deviations addressed, and preserved boundaries.

## Verification to reproduce

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m pytest \
  tests/llm/test_decision_policy_v5_candidate.py -v
# Expected: 51 passed

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m pytest \
  tests/llm/test_decision_policy_v4_candidate.py \
  tests/llm/test_decision_policy_v3_candidate.py \
  tests/llm/test_authorization.py \
  tests/llm/test_parser.py -q
# Expected: 163 passed (no regression)

PYTHONPATH=src /opt/homebrew/bin/python3.11 tests/schema/test_set_screw_shaft_collar.py
# Expected: 17 passed
```

## Key normal and rejection cases for review

Normal (passes P1/P2):
- `check_v5_envelope({"decision":"answer","extracted_parameters":{"bore_d":24},"missing_fields":[],"unsupported_requests":[]})` → ok=True

P1 violation:
- `check_v5_envelope({"decision":"refuse","extracted_parameters":{"bore_d":24},"missing_fields":[],"unsupported_requests":[]}, condition_id="C1")` → ok=False, P1-1

P2 violation:
- `check_v5_envelope({"decision":"ask","extracted_parameters":{"bore_d":20,"outer_d":40},"missing_fields":["outer_d"],"unsupported_requests":[]})` → ok=False, P2-1

Correctly NOT flagged:
- bore_d=75 + refuse → ok=True (P1 silent)
- bore_d absent + refuse → ok=True (P1 silent)
- bore_d=20 + catalog conflict (missing_fields non-empty) + ask → ok=True (P1 silent)

## Unresolved

- Codex independent review of rule correctness and completeness.
- No activation decision made; production v4 is unchanged.
- Any future formal test of a v5 prompt requires a new unique `batch_id`,
  new Codex preflight, and project-owner authorization.

## Constraints carried forward

- Do NOT merge to main without Codex review.
- Do NOT modify `work/app001-runs/app001-phase1-v4-20261109-01/` or any old batch.
- Do NOT change `FORMAL_EVALUATION_ALLOWED`, `FROZEN_PROMPT_*`, or production PROMPT_VERSION.
