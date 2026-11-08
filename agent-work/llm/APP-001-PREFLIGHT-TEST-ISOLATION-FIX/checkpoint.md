# APP-001-PREFLIGHT-TEST-ISOLATION-FIX checkpoint

- Task ID: `APP-001-PREFLIGHT-TEST-ISOLATION-FIX`
- Date: 2026-11-08
- Agent: CC
- Status: review (pending Codex hub independent verification on Python 3.11.18)
- Branch: `cc/APP-001-PREFLIGHT-TEST-ISOLATION-FIX`
- Baseline: `bf8117d` (`origin/main`)
- Not pushed. Not merged to main.

## Problem

`tests/llm/test_r3_fixes.py` used `int(time.time() * 1000) % N` to generate
`batch_id` values for 12 test instances.  Under Python 3.11.18 tests execute
fast enough that multiple tests within the same second share the same modulo
result, causing batch directory collisions in `work/app001-runs/<batch_id>/`,
duplicate budget records, and concurrent-claim assertion failures.  Tests pass
when run individually (different second) but fail when run together in discover.

## Root cause

`int(time.time() * 1000) % 999999` and `% 99999` produce the same integer for
any two tests executing within the same millisecond window whose modulo result
collides.  With Python 3.11's faster test runner the probability is non-trivial
within a single `discover` run.

## Fix

- Added `import uuid` at module level (line 10 of `tests/llm/test_r3_fixes.py`).
- Replaced all 12 occurrences of `int(time.time() * 1000) % N` with
  `uuid.uuid4().hex[:8]` (8 hex chars = 4 billion unique values per run).
- No test assertions, business logic, import structure, or production code
  changed.

## Files changed

| File | Change |
|---|---|
| `tests/llm/test_r3_fixes.py` | `import uuid` added; 12 batch_id patterns replaced |
| `agent-work/llm/APP-001-PREFLIGHT-TEST-ISOLATION-FIX/checkpoint.md` | this file |
| `docs/WORKLOG.md` | CLOSEOUT record appended |

## Verification (CC — VM Python 3.10.12; Codex hub must re-verify on 3.11.18)

```
python3 -m py_compile tests/llm/test_r3_fixes.py
  → OK

PYTHONPATH=src:. python3 -m unittest tests.llm.test_r3_fixes -q  (run 1)
  → Ran 51 tests  OK

PYTHONPATH=src:. python3 -m unittest tests.llm.test_r3_fixes -q  (run 2)
  → Ran 51 tests  OK

PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q  (run 1)
  → Ran 685 tests  OK  (skipped=8)

PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q  (run 2)
  → Ran 685 tests  OK  (skipped=8)

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q
  → Ran 17 tests  OK

git diff --check
  → OK
```

The 8 existing skips are the pre-existing FUSE file-lock limitations; they are
unrelated to this fix.

## Unresolved limitations

- CC environment is Python 3.10.12.  The reported failures occur on Python
  3.11.18.  Codex hub must re-run on `/opt/homebrew/bin/python3.11` (3.11.18)
  to confirm the fix resolves the collision.
- No production code was changed; no formal evaluation was authorized.
- No model calls, no key reads.

## Prohibition compliance

- No DeepSeek/Ollama calls.
- No API key reads or prints.
- No formal runner started.
- No production code, Prompt, Schema, budget, or authorization changes.
- No test assertions, business logic, or other tests modified.
- Existing formal batch directories not touched.
- Not pushed. Not merged to main.
