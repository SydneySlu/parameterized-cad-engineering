# APP-001-V4-FORMAL-EFFECT-EVALUATION checkpoint

- Status: in_progress / run script and tests committed; awaiting Mac execution
- Owner: Codex hub (planning and preflight), CC (script and tests), Wang sikai (Mac execution)
- Production baseline: `main` / `origin/main` at `cc3dfbbae3562b287860c04d7b3e72a161139386`
- Prompt: `app001-extraction.v4`
- No real model request has been made at any point.

## Approved batch

- `batch_id`: `app001-phase1-v4-20261109-01`
- `requested_by`: Wang sikai
- `approved_by`: Wang sikai
- `approval_timestamp`: `2026-11-09 00:10 Asia/Shanghai`
- `authorization_scope_hash`: `a57b69664e816be709cc7dfd049dbad389461203857f27ea3ffe302729d04c5f`
- `raw_retention_path`: `work/app001-runs/app001-phase1-v4-20261109-01/raw/`

## Run script

- Path: `scripts/run_app001_v4_formal_batch.py`
- Tests: `tests/llm/test_run_script_v4_batch.py` — 19 tests, all passed
- Committed in this round as `scripts/[hash]` (see WORKLOG for commit hash)

## Commit validation policy (script)

- HEAD must equal `BASELINE_COMMIT` (`cc3dfbb`) OR be a descendant of it.
- If descendant: `git diff --name-only cc3dfbb HEAD -- <PRODUCTION_PATHS>` must return empty.
- Protected production paths cover: `src/llm/`, `src/retrieval/`, `src/schema/`,
  `src/cad_compilation/`, `prompt-v4.md`, `acceptance-set-v0.json`,
  `retrieval-config.json`, `manifest-v0.jsonl`.
- Commits adding only scripts, tests, and docs pass the descendant check.

## Batch directory protection (script)

- Abort if `work/app001-runs/app001-phase1-v4-20261109-01` exists for any reason,
  whether empty or containing files.

## Current handoff

- Readiness review: `agent-work/reviews/APP-001-V4-FORMAL-RUN-READINESS.md`
- Authorization template: `authorization-request-template.md`
- Formal authorization path: `src/llm/authorization.py`
- Runner: `src/llm/runner.py`
- Run script: `scripts/run_app001_v4_formal_batch.py`

## Closed preconditions

- ADR-0015 evidence-null gate: closed by `docs/DECISIONS.md` ADR-0015-CLOSEOUT.
- ADR-0014 scope synchronization: current v4 inherited scope appended as ADR-0014-AMENDMENT.
- Batch authorized by project owner Wang sikai at `cc3dfbb`.
- Script commit validation: descendant-aware, production-diff-guarded — closed.
- Batch dir protection: any-existence check — closed.
- Offline test suite (19 tests): all passed — closed.

## Remaining gate

- Wang sikai runs the script on Mac (Python 3.11.18, local Ollama) and reports results.
- CC appends result summary to WORKLOG and commits.
- Codex reviews results in a separate session.

## Mac execution command

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
source .env
PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/run_app001_v4_formal_batch.py
```

## Boundary

- Do not call DeepSeek/Ollama except via the above command on Mac.
- Do not read or print API key values.
- Do not modify old batches.
- Do not run C2, IR, CAD, geometry, or STEP.
- Do not change production code, prompt, schema, budget, or authorization scope.

## Test evidence (final)

| Suite | Tests | Result | Runtime |
|-------|-------|--------|---------|
| CommitValidation | 8 | pass | Python 3.11.17 |
| BatchDirProtection (ensure_batch_dir_absent) | 3 | pass | Python 3.11.17 |
| OllamaRuntime (check_ollama_runtime) | 5 | pass | Python 3.11.17 |
| SyntaxAndImport | 3 | pass | Python 3.11.17 |
| DryRun | 3 | pass | Python 3.11.17 |
| **Total** | **22** | **pass** | |

## handoff_self_check

```text
changed=run script (ensure_batch_dir_absent + check_ollama_runtime extracted),
        tests (22, all call real helpers), checkpoint, WORKLOG
commands=python3.11 py_compile (script + tests),
         PYTHONPATH=src:. python3.11 pytest tests/llm/test_run_script_v4_batch.py → 22 passed,
         same suite on python3.10 → 22 passed
confirmed=production paths untouched, scope hash correct, batch dir absent,
          no model request, no API key read or print,
          batch/Ollama tests call real extracted functions (not _abort mock)
unresolved=Mac execution by Wang sikai; Codex result review
next_agent_focus=after Mac run, CC appends result WORKLOG entry and commits;
                 then Codex reviews in separate session
result=pass
```
