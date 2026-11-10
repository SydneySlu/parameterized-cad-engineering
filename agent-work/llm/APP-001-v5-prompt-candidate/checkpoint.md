# APP-001-V5-PROMPT-CANDIDATE checkpoint

- Status: review; offline candidate prepared, awaiting independent Codex review
- Owner: Codex hub
- Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`
- Branch HEAD at task start: `99d0105`
- Production prompt: remains `app001-extraction.v4`
- Candidate prompt SHA-256: `6e969ae68f75c0cd6a188bd589a84c378b50055a42f75ff2b3b3259252f6bdfe`

## Delivered

- `prompt-v5-candidate.md`: separate offline candidate copied from frozen v4; adds complete/conflict-free answer priority, C0/C1 invariance, retrieval non-interference, and envelope consistency checks.
- `strategy.md`: A01-A09 behavior mapping, retained safety gates, checker limits, and future authorization boundary.
- `src/llm/decision_policy_v5_candidate.py`: candidate checker conflict handling aligned with all explicit coupled catalog dimensions (`outer_d`, `width`, `screw_d`, `screw_len`) and `second_screw` rule.
- `tests/llm/test_decision_policy_v5_candidate.py`: width/screw_d/screw_len answer conflict and ask/refuse suppression coverage.
- `tests/llm/test_prompt_v5_candidate.py`: 9 static checks for candidate identity, exact v1 envelope, policy language, case mapping, and frozen hashes.
- `docs/PROJECT_STATUS.md`, `docs/WORKLOG.md`: current review status and appended evidence.

## Verification (Mac Python 3.11.18)

```text
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v5_candidate tests.llm.test_prompt_v5_candidate -q
→ Ran 93 tests, OK

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v4_candidate tests.llm.test_decision_policy_v3_candidate tests.llm.test_authorization tests.llm.test_parser tests.llm.test_budget tests.llm.test_run_script_v4_batch -q
→ Ran 191 tests, OK (skipped=6)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
→ Ran 800 tests, OK (skipped=8)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q
→ Ran 17 tests, OK

/opt/homebrew/bin/python3.11 -m py_compile src/llm/decision_policy_v5_candidate.py tests/llm/test_decision_policy_v5_candidate.py tests/llm/test_prompt_v5_candidate.py
→ OK

git diff --check
→ CLEAN
```

The 8 full-suite skips and 6 targeted skips are existing FUSE/file-lock environment skips. They are not counted as passes.

## Representative cases

- Normal: `answer + bore_d=24 + empty missing/unsupported` → checker `ok=True`.
- Legitimate conflict: `ask/refuse + bore_d=20 + mismatching outer_d/width/screw_d/screw_len` → no P1 over-refusal finding.
- Invalid answer: `answer + bore_d=20 + mismatching outer_d/width/screw_d/screw_len` → P2-5 finding.
- A05 overlap: `outer_d` in both extracted and missing → P2-1; corrected envelope removes overlap.

## Frozen/production boundaries verified

- v4 frozen prompt SHA-256: `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc` (unchanged).
- acceptance-set SHA-256: `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf` (unchanged).
- `PROMPT_VERSION` and `FROZEN_PROMPT_VERSION`: `app001-extraction.v4`.
- `FORMAL_EVALUATION_ALLOWED=False`; candidate checker remains outside production imports.
- No model/network call, `.env`/API-key read, formal batch creation, or old batch modification.

## Limits and next step

The checker sees only the response envelope; it cannot establish whether the original request was ambiguous, whether a claim was explicit, or whether evidence truly supports it. Static and offline tests do not establish model compliance or effectiveness. Review the candidate text against the frozen contract and A01-A09 before considering activation. Any effect run requires a new unique batch ID, explicit owner authorization, and Codex preflight.

## handoff_self_check

```text
handoff_self_check:
  changed=prompt candidate, strategy map, candidate checker/tests, status, worklog
  commands=93 candidate tests; 191 targeted regression tests (6 skipped); 800 LLM tests (8 skipped); 17 Schema tests; py_compile; git diff --check — all executed successfully
  confirmed=exact nine-key app001-io.v1 envelope; v4 prompt and acceptance-set hashes unchanged; candidate P1/P2 rule coverage spans all coupled dimensions and strict second_screw boundary; production v4/gate unchanged
  unresolved=prompt/model behavior not measured; checker cannot inspect natural-language ambiguity/evidence truth; independent Codex review pending
  next_agent_focus=verify prompt priority doesn't weaken missing/non-catalog/unsupported/conflict gates; independently inspect candidate checker mapping against CATALOG_ROWS; verify prompt/manifest/hash and production isolation
```
