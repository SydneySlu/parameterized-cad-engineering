# APP-001 V5 Formal Effect Evaluation — Codex Closeout Review

**Task:** `APP-001-V5-FORMAL-EFFECT-EVALUATION`
**Batch:** `app001-phase1-v5-20261111-01`
**Review date:** 2026-11-11 (Asia/Shanghai)
**Result:** `review` — the authorized real-model run and read-only evidence audit are complete; closeout correction is prepared for independent review and merge. This does not authorize another model run.

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

## Verification

On Python 3.11.18:

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_run_script_v5_batch -q` — 30 passed.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` — 841 passed, 8 existing FUSE skips.
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q` — 17 passed.
- `python3.11 -m py_compile scripts/run_app001_v5_formal_batch.py tests/llm/test_run_script_v5_batch.py` — passed.
- `git diff --check` — passed.
- Read-only batch audit confirmed record/ledger counts, model identity, decision distribution, schema outcomes, budget, raw file presence and hashes. No model API was called during this review.

The 8 LLM skips are existing FUSE lock-file limitations. The live run completed before the reporter correction; the reporter fix was validated against the already-preserved batch and did not issue requests.

## Decision and next gate

The fixed batch provides real-model effect evidence and the v5 decision paths match the candidate policy on the exercised cases. The 20/32 Schema pass rate remains an important separate downstream result. The sample size and envelope-only checker limit generalization; there is no C2/CAD end-to-end evidence. Preserve the batch unchanged. Independently review this closeout and merge the documentation/reporter correction before marking the task done. Any further model evaluation or prompt/policy change needs a new versioned scope, unique batch ID, and separate authorization.
