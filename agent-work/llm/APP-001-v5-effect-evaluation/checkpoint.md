# APP-001-V5-FORMAL-EFFECT-EVALUATION checkpoint

## Status

`in_progress` — v5 is active on main and the project owner instructed this
task to reach real-model testing. The controlled v5 entry point and its offline
guards are being prepared. No model chat request has been made yet.

## Identity and scope

- Main baseline: `2c702257ed56b3d9e49209f0455c2aaffb608b8b`.
- Unique batch: `app001-phase1-v5-20261111-01`.
- Authorization and fixed scope: `authorization.md`.
- Prompt: v5, SHA-256 `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`.
- Acceptance set: 9 frozen cases; C0/C1; DeepSeek and Ollama; 36 logical runs;
  caps of 108 total / 54 per provider / 3 per run.
- C2, IR, CAD, geometry, and STEP remain disabled.
- Prior v2/v3/v4 batch directories and records remain read-only.

## Work completed

- Corrected project status and plan after confirming `main` and `origin/main`
  both contain v5 activation commit `2c70225`.
- Added v5-specific runner `scripts/run_app001_v5_formal_batch.py`; it pins the
  v5 prompt and activation manifest, ADR-0015 Ollama version/model/schema,
  RET-002 manifest, unique batch scope hash, clean worktree, and output directory
  absence before execution.
- Added offline protections and dry-run coverage in
  `tests/llm/test_run_script_v5_batch.py`.

## Validation and next gate

Validation (Mac, Python 3.11.18):

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_run_script_v5_batch -q` — 27 passed.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` — 838 passed, 8 existing FUSE skips.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q` — 17 passed.
- `py_compile` for the v5 runner/tests and `git diff --check` — passed.
- `App001Runner.dry_run()` — 36 combinations; no network calls.

The first focused run exposed that ADR-0015's `d82e53ad…` hash is the
historical v2 Ollama schema. The v5 schema includes the v5 prompt version and
hashes to `7c201710fae0ff3cc3b811c28739393762f1886a5e79bd255cbda8671ac03143`;
the authorization record and test now pin this recomputed active hash. This
was corrected before any model call.

Next: commit the reviewed runner/docs, then execute the v5 script. Its online
preflight runs immediately before the batch and must pass before any chat call.
If a preflight fails, stop and record the blocker. If it passes, run only this
batch, preserve raw responses under the ignored directory, and report measured
results separately from offline tests.

## Constraints

- Do not use `scripts/run_app001_v4_formal_batch.py`.
- Do not alter production code, prompt, Schema, budget, authorization logic, or
  old batches.
- Do not print, persist in tracked files, or send the API key value.
- Do not exceed the fixed retry/physical request caps.
- Record C1 request-before blocking, failures, 5xx, runtime model identities,
  raw evidence retention, and cost/latency evidence without converting them
  into success claims.
