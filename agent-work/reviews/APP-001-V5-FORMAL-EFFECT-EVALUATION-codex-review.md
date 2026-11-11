# APP-001 V5 Formal Effect Evaluation — Codex Closeout Review

**Task:** `APP-001-V5-FORMAL-EFFECT-EVALUATION`
**Batch:** `app001-phase1-v5-20261111-01`
**Review date:** 2026-11-11 (Asia/Shanghai)
**Initial review result:** `review` — at the time of the initial audit, the authorized real-model run and read-only evidence audit were complete, and closeout correction was prepared for independent review and merge. The current follow-up status is recorded at the end of this report. This does not authorize another model run.

## Scope and provenance

The evaluation used the v5-only controlled entry point and the user-authorized fixed Phase 1 matrix: 9 acceptance cases × C0/C1 × DeepSeek/Ollama, up to 3 attempts per logical run, 108 batch attempts and 54 per provider. The repository baseline was v5 activation `2c702257ed56b3d9e49209f0455c2aaffb608b8b`. Prompt SHA-256 was `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`; contract was `app001-io.v1` and active prompt version was `app001-extraction.v5`.

The ignored batch directory `work/app001-runs/app001-phase1-v5-20261111-01/` contains 36 valid JSONL records, a 48-entry budget ledger, and the retained response files. The directory is ignored by Git and was not modified or rerun during this review. No key or `.env` value was read or emitted in the review.

## Real-model observations

- Runtime recorded in the batch: Python 3.11.18 on macOS 26.6.2 arm64; DeepSeek `deepseek-flash` and Ollama `qwen3:8b`. The qwen digest was `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`, matching the authorized digest prefix.
- 32/36 logical runs returned a model response; the four request-before blocks were A04/C1 and A07/C1 for both providers. The two blocking reason codes were `C1_NO_SAFE_QUERY_PARAMETER` and `RETRIEVAL_SCHEMA_REJECTED`, each appearing twice.
- Budget accounting: 48 attempts total — DeepSeek 16 chat attempts; Ollama 16 chat attempts plus 16 `/api/tags` model-identity checks. The cap was 108 total / 54 per provider. All 32 chat responses were HTTP 200; no retries, 5xx, or API errors were recorded.
- All 32 expected raw responses were retained. Each referenced file exists, and its saved length and SHA-256 match its `raw_response_retention` metadata. The four request-before blocks have no raw response, as expected.
- The 32 responses parsed successfully. Decision distribution: `answer=20`, `ask=2`, `refuse=10`. Both providers made the same decision for each executed case/condition: A01, A02, A03, A06 and A08 answered; A04/C0 asked; A05, A07/C0 and A09 refused. This matches the v5 candidate strategy for the observed acceptance-set paths; it is a nine-case controlled sample, not a broad quality claim.
- The offline v5 candidate checker reported no P1/P2 violations across the 32 parsed envelopes. This checker sees only envelope fields and is diagnostic, not a full semantic or evidence-grounding judge.
- CAD-003 Schema accepted 20/32 model responses and rejected 12/32 (6 per provider): A04/C0 missing required `bore_d` (2); A05/C0 and C1 catalog mismatch (4); A07/C0 out-of-catalog `bore_d` (2); A09/C0 and C1 `second_screw` constraint conflict (4). Refusal/decision alignment therefore does not imply that every extracted envelope passes downstream Schema validation.
- DeepSeek usage was 50,062 input tokens and 1,705 output tokens (51,767 total), with reported cost CNY 0.01561224. Ollama recorded 137,948.6 ms total chat latency across 16 runs, mean 8,621.8 ms (range 6,000.2–19,793.2 ms).
- C2, Typed CAD IR, CAD compilation, geometry, and STEP were not run. No v3/v4 batch data was pooled with this batch.

## Reporter defect found and corrected

The first printed summary reported no retained raw responses and omitted decisions because it looked for top-level `raw_response_path` and `decision` fields. Actual records store retention metadata under `raw_response_retention` and do not duplicate the model decision at the top level. The summary now resolves the recorded retained path, parses the response only to count its decision enum without printing response text, counts request-before blocks as `blocked`, and reports a successful model run with a missing raw file as a retention gap. The corrected summary, recomputed from the existing batch, reports:

```text
Per-provider outcomes: DeepSeek total=18 blocked=2 success=16; Ollama total=18 blocked=2 success=16
Per-condition outcomes: C0 total=18 success=18; C1 total=18 blocked=4 success=14
Decision distribution: answer=20 ask=2 refuse=10
Schema: pass=20 fail=12 other=0
Raw retention: retained=32 missing=0
```

Three offline regression tests cover the real retention field and decision parsing, request-before blocks, and a missing raw file for a completed model run. No batch content or production runtime behavior was changed.

## Retention-path deviation and remediation

The authorization record specifies `work/app001-runs/<batch_id>/raw/`. The
actual v5 execution configured `RetentionPolicy.base_dir` as
`work/app001-runs/<batch_id>` in `src/llm/runner.py`, so all 32 retained raw
files are at the batch root and no `raw/` subdirectory exists. A read-only
metadata check confirmed that all recorded paths resolve to existing files;
the directory remains git-ignored. The files and JSONL metadata were not moved
or rewritten, because that would alter the historical evidence after execution.

This is an authorization-to-runtime path mismatch and must remain an explicit
review finding. It did not expose the files outside the ignored batch area,
but it means the run did not follow the authorized directory layout. The
authorization text is preserved as written; the discrepancy is documented
here rather than silently editing the approval record.

For any future run, make a separate narrow implementation change to configure
raw retention under `<batch_dir>/raw/`, add a test asserting the exact resolved
directory and resulting metadata path, and update the future authorization
template/checkpoint to match the implementation. Do not use that code change
to rerun or resume this batch. Any additional model request needs a new batch
ID and separate authorization.

The narrow code correction is now prepared in `src/llm/runner.py`: formal
retention uses `work/app001-runs/<batch_id>/raw/`. A new runner regression
creates one synthetic response under a unique ignored test batch and asserts
both the resolved directory and returned metadata path. Python 3.11.18 checks:
the new test 1/1; `tests.llm.test_runner` 71 passed, 1 existing skip; full LLM
suite 842 passed, 8 existing FUSE skips; Schema 17 passed; `py_compile` and
`git diff --check` passed. The old batch was not touched. Since `src/llm/` is
production scope, the existing v5 batch script intentionally rejects a future
run against its old baseline; any later evaluation needs a refreshed reviewed
entrypoint baseline, a new batch ID, and separate authorization.

## Verification

On Python 3.11.18:

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_run_script_v5_batch -q` — 30 passed.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` — 841 passed, 8 existing FUSE skips.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q` — 17 passed.
- `python3.11 -m py_compile scripts/run_app001_v5_formal_batch.py tests/llm/test_run_script_v5_batch.py` — passed.
- `git diff --check` — passed.
- Read-only batch audit confirmed record/ledger counts, model identity, decision distribution, schema outcomes, budget, raw file presence and hashes. No model API was called during this review.

The 8 LLM skips are existing FUSE lock-file limitations. The live run completed before the reporter correction; the reporter fix was validated against the already-preserved batch and did not issue requests.

## Initial review decision and next gate

At the time of the initial review, the fixed batch provided real-model effect evidence and the v5 decision paths matched the candidate policy on the exercised cases. The 20/32 Schema pass rate remains an important separate downstream result. The sample size and envelope-only checker limit generalization; there is no C2/CAD end-to-end evidence. Preserve the batch unchanged. The initial next gate was independent review and merge of the closeout/documentation correction; later status is recorded in the follow-up section. Any further model evaluation or prompt/policy change needs a new versioned scope, unique batch ID, and separate authorization.

## Follow-up status (2026-11-11)

The preceding retention-path section records the finding and recommendation as
they stood during the initial closeout review. The recommended narrow runner
correction was subsequently implemented in `a35f14b` and independently
reviewed: future formal raw retention now targets
`work/app001-runs/<batch_id>/raw/`, with a regression that writes a synthetic
response and checks both the resolved directory and metadata path. The recorded
Python 3.11.18 runner, LLM, Schema, and `git diff --check` validations passed.

The correction applies only to future runs. The 32 historical raw files remain
at the v5 batch root, preserving the documented deviation; they were not
moved, rewritten, or rerun. Commit `8da34d9` aligned the checkpoint and project
plan with that distinction. A subsequent independent review found stale
handoff wording in this report/checkpoint and the WORKLOG next-step entry. This
follow-up updates those current-state references while preserving the earlier
recommendation as historical review context. The documentation-only follow-up
passed independent review. Codex's final branch acceptance also passed on
`3a55cc1`; Python 3.11.18 checks recorded for this acceptance were LLM 842
passed with 8 existing FUSE skips, Schema 17 passed, relevant `py_compile`
passed, and full-branch `git diff --check` passed. The branch was then merged
to `main` by PR #1. Post-merge verification on Python 3.11.18 at
`95d1dcb8e1ba693769b19b1262228c51ba4f8f7d` passed: LLM 842 with 8 existing
FUSE skips, Schema 17, runner plus v5 entrypoint 101 with 1 existing skip,
relevant `py_compile`, and `git show --check`. Local `main` is synchronized
with `origin/main` and clean. Task status is `done`. The historical batch was
not changed or rerun, and this closeout authorizes no additional model run.
