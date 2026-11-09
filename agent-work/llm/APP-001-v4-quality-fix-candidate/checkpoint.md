# APP-001-V4-QUALITY-FIX-CANDIDATE checkpoint (R1)

- Status: in_progress / R1 corrections complete; awaiting Codex re-review
- Owner: CC (R1 implementation), Codex hub (independent re-review)
- Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`
- Base HEAD at R1 start: `136cd49` (includes Codex review prompt for R1)
- No real model request has been made at any point.

## R1 corrections applied

### R1-1: Import path

Changed `from ..schema.set_screw_shaft_collar` to `from schema.set_screw_shaft_collar`
(absolute import).  Module now importable under both:

- `PYTHONPATH=src`: `import llm.decision_policy_v5_candidate` ✓
- `PYTHONPATH=src:.`: `import src.llm.decision_policy_v5_candidate` ✓

### R1-2: P2-5 catalog/rule conflict + P1 conflict suppression

- Added `_has_deterministic_conflict()` helper.
- Added P2-5 in `_check_p2_5_catalog()`: fires when `decision=answer` with
  catalog conflict (outer_d mismatch) or rule conflict (second_screw rule).
- P1-1 now suppressed when `_has_deterministic_conflict()` returns True;
  ask/refuse with a legitimate conflict is NOT flagged as over-refusal.

### R1-3: Numeric normalization

- `_normalize_bore_d()` added: handles bare int/float (24 → 24, 24.0 → 24),
  measurement objects ({"value":1.6,"unit":"cm"} → 16), unknown unit → None,
  non-finite → None, fractional mm → None.
- `_bore_d_from_envelope()` now delegates to `_normalize_bore_d()`.

## Modified files

- `src/llm/decision_policy_v5_candidate.py` — R1 corrections
- `tests/llm/test_decision_policy_v5_candidate.py` — expanded to 78 tests (was 51)
- `agent-work/llm/APP-001-v4-quality-fix-candidate/candidate-strategy.md` — R1 rules added
- `agent-work/llm/APP-001-v4-quality-fix-candidate/checkpoint.md` — this file
- `agent-work/llm/APP-001-v4-quality-fix-candidate/handoff.md` — updated
- `docs/WORKLOG.md` — appended

No production files modified.

## Actual verification commands and results (R1, Python 3.11.17 in VM)

```
python3.11 -m py_compile src/llm/decision_policy_v5_candidate.py
tests/llm/test_decision_policy_v5_candidate.py
→ ok (no output)

PYTHONPATH=src python3.11 -c
  'import llm.decision_policy_v5_candidate as m; print(m.CANDIDATE_VERSION)'
→ app001-extraction.v5-candidate

PYTHONPATH=src:. python3.11 -m unittest
  tests.llm.test_decision_policy_v5_candidate -q
→ Ran 78 tests in 0.029s  OK

PYTHONPATH=src:. python3.11 -m unittest
  tests.llm.test_decision_policy_v4_candidate
  tests.llm.test_decision_policy_v3_candidate
  tests.llm.test_authorization tests.llm.test_parser
  tests.llm.test_budget tests.llm.test_run_script_v4_batch -q
→ Ran 191 tests in 0.584s  OK (skipped=6)

git diff --check → clean
```

Note: Python 3.11.17 is the uv-installed VM interpreter; project venv uses
3.11.18 on Mac (symlink broken in VM). Behavior is identical for pure-Python
stdlib code; the 3.11.17 result is valid evidence for Mac 3.11.18 execution.

## Normal case (actual output)

```python
env = {'decision':'answer','extracted_parameters':{'bore_d':24},
       'missing_fields':[],'unsupported_requests':[]}
check_v5_envelope(env, condition_id='C0')
→ V5CheckResult(ok=True, p1_violations=(), p2_violations=(), violations=(), condition_id='C0')
```

## Failure case — P1-1 (A02-C1 refuse, observed deviation)

```python
env = {'decision':'refuse','extracted_parameters':{'bore_d':24},
       'missing_fields':[],'unsupported_requests':[]}
check_v5_envelope(env, condition_id='C1')
→ V5CheckResult(ok=False,
    p1_violations=(V5ViolationDetail(rule_id='P1-1',
      message='decision=refuse is not justified when bore_d is a valid catalog value, ...'),),
    p2_violations=(), violations=(...), condition_id='C1')
```

## Failure case — P2-5 (A05 answer + catalog conflict)

```python
env = {'decision':'answer','extracted_parameters':{'bore_d':20,'outer_d':40},
       'missing_fields':[],'unsupported_requests':[]}
check_v5_envelope(env, condition_id='C0')
→ V5CheckResult(ok=False,
    p1_violations=(),
    p2_violations=(V5ViolationDetail(rule_id='P2-5',
      message='decision=answer but explicit outer_d conflicts with the catalog row for bore_d=20: '
              'catalog expects outer_d=32, envelope has outer_d=40; ...'),),
    violations=(...), condition_id='C0')
```

## handoff_successor_check

```text
branch=cc/APP-001-V4-QUALITY-FIX-CANDIDATE
head_at_r1_start=136cd49
reran=tests.llm.test_decision_policy_v5_candidate → 78/78 passed
normal_case=A02-C0 answer bore_d=24 → ok=True, violations=()
failure_case_p1=A02-C1 refuse bore_d=24 → ok=False, P1-1
failure_case_p2=A05 answer bore_d=20 outer_d=40 → ok=False, P2-5
r1_1=PYTHONPATH=src import llm.decision_policy_v5_candidate → ok
r1_2=P2-5 fires for answer+conflict; P1 suppressed for ask/refuse+conflict
r1_3=normalize 24.0→24, {1.6,cm}→16, inches→None, inf→None
production_isolation=v5 not imported by adapter/parser/runner/contract/prompt_loader (text+AST)
unresolved=Codex re-review; activation requires new batch_id + new authorization
next_agent_focus=Codex re-runs R1 verification commands and decides whether to
                 advance candidate to next stage
result=pass
```

## Boundary

- No model call, no network access, no API key read or printed.
- No production code, prompt, schema, budget, authorization, or old batch modified.
- No new formal batch created or authorized.
- `FORMAL_EVALUATION_ALLOWED` remains `False`.
- Offline checker pass ≠ model effect pass.
