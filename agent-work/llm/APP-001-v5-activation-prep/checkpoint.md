# APP-001-V5-ACTIVATION-PREP checkpoint

- Status: review; activation preparation package awaits independent review and project-owner decision
- Branch: `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`
- Preparation baseline: `582a1234e5603861ad98f605d76af4efaf9b1334`
- Current production: `app001-extraction.v4`; `app001-io.v1`
- ADR-0018: proposed, not accepted

## Delivered

- `prompt-v5.md`: version-normalized copy for a possible future activation; it is not loaded by production.
- `manifest.json`: records the candidate/source hash, activation-copy hash, acceptance-set hash, current production identity, v4 rollback target, and explicit prerequisites.
- `README.md`: documents status and separates activation implementation from model-effect authorization.
- `tests/llm/test_v5_activation_prep.py`: offline package identity, hash, production isolation, current-v4, and non-authorization checks.
- `docs/DECISIONS.md`: appended proposed ADR-0018; no activation or evaluation approval is asserted.

## Verification (Mac Python 3.11.18)

```text
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_v5_activation_prep tests.llm.test_prompt_v5_candidate tests.llm.test_decision_policy_v5_candidate -q
→ Ran 103 tests, OK

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
→ Ran 810 tests, OK (skipped=8)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q
→ Ran 17 tests, OK

/opt/homebrew/bin/python3.11 -m py_compile tests/llm/test_v5_activation_prep.py
→ OK

git diff --check
→ CLEAN
```

The 8 skips are existing FUSE file-lock environment skips; simulated abort/fail output in the run-script tests is expected and the suite exits 0.

## Boundaries

No production constants or parser/loader behavior changed. No model/network call, `.env` or key read, formal batch creation, old-batch access, or evaluation authorization.

## Next gate

Independent Codex review of this preparation package and proposed ADR text. Project owner then decides whether to accept ADR-0018 and commission a separate activation implementation. No v5 production switch occurs in this task.
