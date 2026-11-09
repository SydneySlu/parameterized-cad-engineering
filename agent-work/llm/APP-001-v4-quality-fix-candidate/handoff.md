# APP-001-V4-QUALITY-FIX-CANDIDATE handoff (R1)

From: CC (R1 round)
To: Codex hub (independent re-review)
Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`
R1 HEAD: see `git log --oneline -1`

## What was done in R1

R1-1  Import: `from schema.set_screw_shaft_collar` (absolute).
      `PYTHONPATH=src python3.11 -c 'import llm.decision_policy_v5_candidate as m'` → works.

R1-2  P2-5: `decision=answer` + catalog conflict (outer_d mismatch) or rule
      conflict (second_screw rule) → P2-5 violation.
      P1-1 suppression: ask/refuse with a deterministic conflict does NOT fire P1-1
      (the conflict is the valid reason for the decision).

R1-3  `_normalize_bore_d()`: 24.0 → 24; {"value":1.6,"unit":"cm"} → 16;
      unknown unit → None; non-finite → None; fractional mm → None.

## Verification to reproduce on Mac (Python 3.11.18)

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"

/opt/homebrew/bin/python3.11 -m py_compile \
  src/llm/decision_policy_v5_candidate.py \
  tests/llm/test_decision_policy_v5_candidate.py

PYTHONPATH=src /opt/homebrew/bin/python3.11 -c \
  'import llm.decision_policy_v5_candidate as m; print(m.CANDIDATE_VERSION)'
# Expected: app001-extraction.v5-candidate

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_decision_policy_v5_candidate -q
# Expected: Ran 78 tests ... OK

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_decision_policy_v4_candidate \
  tests.llm.test_decision_policy_v3_candidate \
  tests.llm.test_authorization tests.llm.test_parser \
  tests.llm.test_budget tests.llm.test_run_script_v4_batch -q
# Expected: Ran 191 tests ... OK (skipped=6)

git diff --check
# Expected: (no output — clean)
```

## Key cases to spot-check

Normal (ok=True):
```python
check_v5_envelope(
  {'decision':'answer','extracted_parameters':{'bore_d':24},
   'missing_fields':[],'unsupported_requests':[]},
  condition_id='C0')
→ ok=True
```

P1-1 violation (A02/A08 C1 refuse):
```python
check_v5_envelope(
  {'decision':'refuse','extracted_parameters':{'bore_d':24},
   'missing_fields':[],'unsupported_requests':[]},
  condition_id='C1')
→ ok=False, p1_violations=[P1-1]
```

P2-5 violation (A05 answer + outer_d conflict):
```python
check_v5_envelope(
  {'decision':'answer','extracted_parameters':{'bore_d':20,'outer_d':40},
   'missing_fields':[],'unsupported_requests':[]},
  condition_id='C0')
→ ok=False, p2_violations=[P2-5]
```

P1 suppression correct (A05 ask/refuse with conflict NOT over-refusal):
```python
check_v5_envelope(
  {'decision':'ask','extracted_parameters':{'bore_d':20,'outer_d':40},
   'missing_fields':[],'unsupported_requests':[]},
  condition_id='C0')
→ ok=True  (P1 suppressed; conflict is the valid reason)
```

Normalization (bore_d=24.0 and measurement object):
```python
from llm.decision_policy_v5_candidate import _normalize_bore_d, _is_catalog_bore_d
_normalize_bore_d(24.0)                       # → 24
_normalize_bore_d({'value':1.6,'unit':'cm'})  # → 16
_normalize_bore_d({'value':1.6,'unit':'in'})  # → None
_is_catalog_bore_d(24)                         # → True
_is_catalog_bore_d(16)                         # → True
```

## Unresolved

- Codex independent re-review.
- No activation: `PROMPT_VERSION` remains `app001-extraction.v4`.
- Any future formal test requires a new unique `batch_id`, Codex preflight,
  and project-owner authorization.

## Constraints carried forward

- Do NOT merge to main without Codex re-review.
- Do NOT modify `work/app001-runs/app001-phase1-v4-20261109-01/` or any old batch.
- Do NOT change `FORMAL_EVALUATION_ALLOWED`, `FROZEN_PROMPT_*`, or production PROMPT_VERSION.
