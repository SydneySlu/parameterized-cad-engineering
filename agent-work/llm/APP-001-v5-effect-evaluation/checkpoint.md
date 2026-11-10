# APP-001-V5-FORMAL-EFFECT-EVALUATION checkpoint

## Status

`review` — the authorized v5 real-model batch has completed. The raw/run
evidence is preserved in the git-ignored batch directory. The summary reporter
had a field-path bug; its reporting code and regression tests are now corrected.
The batch itself was not rerun or modified.

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
- Executed the sole authorized batch after preflight passed. The immutable batch
  directory is `work/app001-runs/app001-phase1-v5-20261111-01/` and remains
  git-ignored. Its 36 records and 48-entry budget ledger were audited read-only.
- Found that `_print_jsonl_stats()` looked for top-level `raw_response_path`
  and `decision`, while actual records store retention under
  `raw_response_retention` and require parsing the retained response for its
  decision. Corrected the summary to resolve and verify retained paths, parse
  only the decision enum without printing response text, and label request-
  before blocks as `blocked`. Added three offline regressions.

## Real batch evidence (2026-11-11, Mac Python 3.11.18)

- Runtime identity: Python 3.11.18 / macOS 26.6.2 arm64; all 36 records use
  `app001-extraction.v5` and `app001-io.v1`. Runtime models: DeepSeek
  `deepseek-flash` (16) and Ollama `qwen3:8b` (16), digest
  `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
- Matrix: 36 logical records; 32 model responses and 4 C1 request-before
  blocks (A04 × both providers, A07 × both providers). All 32 retained files
  exist and their saved length/SHA-256 match metadata; the 4 blocked records
  correctly have no raw response.
- Budget ledger: 48 attempts total (DeepSeek 16 chat; Ollama 16 chat plus 16
  `/api/tags` identity checks), within 108 total and 54/provider. All 32 chat
  attempts returned HTTP 200; no retries, 5xx, or API errors.
- Parsed decision distribution: answer=20, ask=2, refuse=10. Per case, both
  providers produced the same decisions: A01/A02/A03/A06/A08 answer; A04 C0
  ask; A05 and A09 refuse; A07 C0 refuse. These outcomes align with the v5
  candidate strategy on this nine-case set. The offline v5 checker reported
  zero P1/P2 violations on the 32 parsed envelopes; this is a diagnostic
  checker result, not a full semantic proof.
- CAD-003 Schema: 20/32 pass, 12/32 fail (6 per provider): A04 C0 missing
  `bore_d` (2); A05 C0/C1 catalog mismatch (4); A07 C0 out-of-catalog choice
  (2); A09 C0/C1 `second_screw` constraint conflict (4). Decision alignment
  does not imply Schema acceptance.
- DeepSeek usage: 51,767 total tokens (50,062 input; 1,705 output), CNY
  0.01561224. Ollama chat latency: 137,948.6 ms total across 16 runs, mean
  8,621.8 ms (range 6,000.2–19,793.2 ms).
- C2, IR, CAD, geometry, and STEP were not run. Old batches remain separate.

## Independent-review finding: retention path mismatch

The authorization says raw responses belong under
`work/app001-runs/<batch_id>/raw/`, but the actual runner configured
`RetentionPolicy.base_dir` as `work/app001-runs/<batch_id>`. The 32 retained
files are at the ignored batch root; all paths exist and match their recorded
length/hash, and there is no `raw/` subdirectory. This is a path-layout
deviation from the approved record, even though the files stayed inside the
ignored batch directory. Do not move or rewrite historical evidence. For a
future run, separately change the retention directory, add an exact-path test,
and align the future authorization template; this batch must not be rerun.
Details are in `agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md`.

## Narrow retention-path correction

- Changed `src/llm/runner.py` so formal raw retention uses
  `work/app001-runs/<batch_id>/raw/` as specified by the authorization contract.
- Added `test_formal_batch_raw_retention_uses_authorized_raw_subdirectory` in
  `tests/llm/test_runner.py`. It resolves the policy, writes one synthetic raw
  response under a unique ignored test batch, asserts the returned metadata
  path's parent is exactly `raw/`, and removes only that test-owned directory.
- Verification on Python 3.11.18: the new path test 1/1; `tests.llm.test_runner`
  71 passed, 1 existing skip; full `tests/llm` 842 passed, 8 existing FUSE
  skips; `tests/schema` 17 passed; `py_compile` and `git diff --check` passed.
- The historical v5 batch directory and its records were not touched. This
  production-path change causes the old v5 batch entrypoint's baseline guard
  to reject a later run; future evaluation requires a reviewed runner baseline,
  a new unique batch ID, and separate authorization. No new model test was run
  or authorized by this narrow correction.

## Handoff successor check

```text
handoff_successor_check:
  predecessor=APP-001-V5-FORMAL-EFFECT-EVALUATION / b20fe44 / checkpoint.md
  files_format=36 valid JSONL records; 48 ledger entries; 32 retained raw files; raw files and ledger remain ignored
  core_rerun=Python 3.11.18; retention path test 1 passed; runner suite 71 passed, 1 skip; llm 842 passed, 8 FUSE skips; schema 17 passed
  normal_case=synthetic retention write returns metadata path under unique batch/raw/
  failure_case=path mismatch finding confirmed read-only; old batch remains untouched and existing block paths remain covered by summary tests
  interface=RetentionPolicy resolves to work/app001-runs/<batch_id>/raw/; adapter metadata stays repo-relative
  limits=Schema 20/32 only; no C2/IR/CAD/geometry/STEP; checker is diagnostic; no causal comparison or broad model-quality claim
  result=review
  blocking_issue=historical batch path deviation remains; correction only applies to future runs, and the old entrypoint correctly rejects changed production baseline
```

## Validation and next gate

Validation (Mac, Python 3.11.18):

- Initial pre-run gate: v5 runner tests 27 passed; LLM suite 838 passed, 8 existing FUSE skips.
- After reporter correction: `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_run_script_v5_batch -q` — 30 passed.
- After reporter correction: `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` — 841 passed, 8 existing FUSE skips.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q` — 17 passed.
- `py_compile` for the v5 runner/tests and `git diff --check` — passed after reporter correction.
- `App001Runner.dry_run()` — 36 combinations; no network calls.

The first focused run exposed that ADR-0015's `d82e53ad…` hash is the
historical v2 Ollama schema. The v5 schema includes the v5 prompt version and
hashes to `7c201710fae0ff3cc3b811c28739393762f1886a5e79bd255cbda8671ac03143`;
the authorization record and test now pin this recomputed active hash. This
was corrected before any model call.

Next: commit the closeout/reporting correction and audit record, then obtain
independent review. The one authorized real batch has already been run; do not
rerun, resume, overwrite, or combine it with any older batch. Any follow-up
model experiment requires a new batch ID and separate authorization.

## Constraints

- Do not use `scripts/run_app001_v4_formal_batch.py`.
- Do not alter production code, prompt, Schema, budget, authorization logic, or
  old batches.
- Do not print, persist in tracked files, or send the API key value.
- Do not exceed the fixed retry/physical request caps.
- Record C1 request-before blocking, failures, 5xx, runtime model identities,
  raw evidence retention, and cost/latency evidence without converting them
  into success claims.
