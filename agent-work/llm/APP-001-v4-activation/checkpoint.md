# APP-001-V4-ACTIVATION checkpoint

- Task ID: `APP-001-V4-ACTIVATION`
- Date: 2026-11-08
- Agent: CC
- Status: review (awaiting Codex hub independent review and merge to main)
- Branch: `cc/APP-001-V4-ACTIVATION`
- Baseline: `1d84b12` (`origin/codex/APP-001-V3-DECISION-FIX-DRAFT`)
- Activation commit: `3b1e353`

## Approval basis

Project lead has approved ADR-0017 strategy direction.  This commit records
that decision in the repository as the approved activation implementation.
Completion does not authorize real model requests or formal evaluation batches.

## Delivery identity

```
production_prompt_version: app001-extraction.v4
contract_version:          app001-io.v1
acceptance_set:            acceptance-set-v0 (9 cases, unchanged)
prompt_file:               agent-work/llm/APP-001-v4-activation/prompt-v4.md
prompt_file_sha256:        73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc
source_candidate_sha256:   145cb487830f22d210a53ad17b1d0c9870512d44b6cace2cb9ef2be8b590606f
acceptance_set_sha256:     ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf
v3_rollback_sha256:        3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b
FORMAL_EVALUATION_ALLOWED: False (unchanged)
```

## Production files changed

| File | Change |
|---|---|
| `src/llm/contract.py` | `PROMPT_VERSION` → `app001-extraction.v4`; comment updated |
| `src/llm/prompt_loader.py` | `FROZEN_PROMPT_PATH` → `APP-001-v4-activation/prompt-v4.md`; `FROZEN_PROMPT_VERSION` / `_VERSION_MARKER` / `FROZEN_PROMPT_FILE_SHA256` updated to v4 values; docstring updated |
| `src/llm/parser.py` | Default parser doc updated to v4; `_LEGACY_AUDIT_PROMPT_VERSIONS` extended with `"app001-extraction.v3"` |

## New activation package files

```
agent-work/llm/APP-001-v4-activation/prompt-v4.md     (frozen prompt)
agent-work/llm/APP-001-v4-activation/manifest.json    (hash manifest)
agent-work/llm/APP-001-v4-activation/README.md        (rollback/scope doc)
agent-work/llm/APP-001-v4-activation/checkpoint.md    (this file)
```

## Test files updated (existing regression fixtures bumped to v4)

```
tests/llm/test_parser.py           (default body v3→v4; new v3/v4 legacy tests)
tests/llm/test_envelope_fix.py     (hash anchor + version string checks → v4)
tests/llm/test_adapter.py          (fixture body v3→v4)
tests/llm/test_security.py         (fixture body v3→v4)
tests/llm/test_r1_regression.py    (fixture body v3→v4)
tests/llm/test_r2_regression.py    (fixture body v3→v4)
tests/llm/test_r3_regression.py    (fixture body v3→v4)
```

## New test file

```
tests/llm/test_v4_activation.py    (71 new tests; all 8 requirement areas)
```

## Verification (CC — VM Python 3.10.12; project fixed baseline is 3.11.18)

Note: the VM runs Python 3.10.12, not the project-fixed 3.11.18.  Codex hub
must re-verify on Mac `/opt/homebrew/bin/python3.11` (Python 3.11.18) before
marking the activation done.

```
PYTHONPATH=src:. python3 -m unittest tests.llm.test_v4_activation -q
  → Ran 71 tests in 0.017s  OK

PYTHONPATH=src:. python3 -m unittest tests.llm.test_decision_policy_v4_candidate -q
  → (part of discover below)

PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q
  → Ran 685 tests in 2.442s  OK (skipped=8)

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q
  → Ran 17 tests in 0.001s  OK

python3 -m py_compile src/llm/contract.py src/llm/parser.py \
  src/llm/prompt_loader.py tests/llm/test_v4_activation.py \
  tests/llm/test_parser.py tests/llm/test_envelope_fix.py \
  tests/llm/test_r1_regression.py tests/llm/test_r2_regression.py \
  tests/llm/test_r3_regression.py tests/llm/test_adapter.py \
  tests/llm/test_security.py
  → OK (no output)

git diff --check
  → OK (no whitespace errors)
```

## Normal and failure paths

Normal path: v4 envelope (contract_version=app001-io.v1,
prompt_version=app001-extraction.v4) is accepted by the default parser.
bore_d=24 with retrieval=20 returns answer. 1.6 cm → 16 mm returns answer.

Failure path: v3 envelope rejected by default parser (PROMPT_VERSION_MISMATCH).
bore_d=75 returns refuse. Missing bore_d returns ask, not answer. v1 passed
to parse_response_for_version raises ValueError.  v3 is accessible via the
explicit legacy audit entry point.

## Unresolved limitations

1. CC environment is Python 3.10.12; project fixed baseline is 3.11.18.
   Codex hub must re-verify on 3.11.18 before the activation can be merged.
2. Model effectiveness is unknown.  This activation only updates the offline
   contract; no real model calls have been made.
3. A new unique formal batch ID and explicit project-lead authorization are
   required before any DeepSeek/Ollama requests can be made against v4.

## Rollback steps

If the activation causes issues after merge:
1. `git revert <activation-commit>` or restore the three production files
   manually (see README.md rollback section).
2. Run `PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q` to
   confirm v3 tests pass.
3. Do NOT modify or delete v3 or v4 history files.

## Next gate

Codex hub independent review on Mac Python 3.11.18; merge to main; then
(separately) project lead must authorize a new unique batch ID before any
real model requests are made against v4.

## handoff_self_check

```
handoff_self_check:
  changed=src/llm/contract.py, src/llm/parser.py, src/llm/prompt_loader.py,
          agent-work/llm/APP-001-v4-activation/ (4 new files),
          tests/llm/test_v4_activation.py (new, 71 tests),
          tests/llm/test_parser.py, test_envelope_fix.py, test_adapter.py,
          test_security.py, test_r1_regression.py, test_r2_regression.py,
          test_r3_regression.py,
          docs/DECISIONS.md (ADR-0017 updated to accepted),
          docs/PROJECT_STATUS.md, docs/WORKLOG.md
  commands=
    discover tests/llm: 685 OK / 8 skipped (existing FUSE)
    discover tests/schema: 17 OK
    test_v4_activation: 71 OK
    py_compile all modified files: OK
    git diff --check: OK
  confirmed=
    FORMAL_EVALUATION_ALLOWED=False unchanged;
    v3 prompt SHA-256 unchanged (3dd8bd55…);
    acceptance-set SHA-256 unchanged (ed59e2b6…);
    v4 prompt SHA-256=73cb6b8f… matches manifest and loader constant;
    checker not imported by production modules;
    v2/v3 legacy audit parser paths working;
    no model calls, no key reads, no batch changes
  unresolved=
    Python 3.10.12 (VM) vs 3.11.18 (project fixed); Codex hub must re-verify;
    model effectiveness unknown, no formal batch authorized
  next_agent_focus=
    Codex hub: re-run full suite on /opt/homebrew/bin/python3.11 (3.11.18);
    verify v4 prompt SHA-256 and manifest; confirm v3 rollback file unchanged;
    confirm FORMAL_EVALUATION_ALLOWED still False; confirm no key reads;
    merge to main only after independent verification passes
```

## Prohibition compliance

- No DeepSeek, Ollama, or any real model/API calls.
- No API key reads or prints.
- No formal evaluation batch created, started, or modified.
- No model samples re-run.
- No acceptance-set, old batch, A03/A07/A08 historical results, v2/v3 prompt
  files, or old manifest modified.
- No C2, IR, CAD, geometry, or STEP stages run.
- No provider, budget, authorization, or retry config changes.
- Not pushed. Not merged. Not committed to main.
- No git lock found or deleted.
