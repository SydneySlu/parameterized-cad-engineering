# APP-001 next real-model evaluation proposal

Status: proposal for project-owner review; this is not an ADR, batch authorization,
or permission to issue model requests.

## Evidence and open gate

- The v5 batch `app001-phase1-v5-20261111-01` completed the frozen nine-case
  C0/C1 × two-provider matrix: 36 logical slots, 32 model responses and four
  C1 pre-request blocks. It measured 32/32 parsing and 20/32 CAD-003 Schema
  acceptance. It remains a small, case-level evaluation; no broad quality or
  retrieval-benefit claim follows from it.
- The RET-003 protocol's three held-out records are `catalog-bore-012`,
  `catalog-bore-035`, and `catalog-bore-080`; only three `retrieval_source`
  records may enter C1. `split_status` is `provisional_small_n`.
- RET-003 has no fair C2. `C2O` reads the full catalog, including held-out
  values, and is an oracle only. It must not appear in a fair comparison or be
  used as prompt context.
- The old v5 run script is pinned to the previous production baseline and
  correctly rejects later production-path changes. It must not be reused for a
  new run after the runner retention fix.

## Recommended next question

Does adding the frozen RET-002 `retrieval_source` context (C1) change v5 model
outputs and deterministic CAD-003 acceptance for the three RET-003 held-out
queries, compared case-by-case with C0 under identical user input?

This is a small exploratory real-model comparison, not a benchmark or a
statistical generalization claim. Report each held-out case separately and keep
the previous v5 batch as a separate historical result.

## Proposed experimental boundary

- Prompt/contract: active `app001-extraction.v5` / `app001-io.v1`, pinned by
  current main hashes; no prompt or schema changes in this work unit.
- Cases: exactly the three RET-003 held-out sample IDs above. Prepare and
  freeze natural-language inputs and evaluator labels before execution; do not
  expose labels or held-out normalized parameters to the model. C1 candidates
  remain restricted to the three `retrieval_source` rows.
- Conditions: C0 and C1 only, with byte-identical common user payload per
  case; C1 may add only the existing RET-002 reference context. Exclude C2,
  C2O, additional examples, tuning, and changes to retrieval weights.
- Providers/models: DeepSeek `deepseek-flash` and Ollama `qwen3:8b`, only if
  current identity preflight still matches the frozen project baseline.
- Size: 3 cases × 2 conditions × 2 providers = 12 logical runs. Proposed cap:
  3 attempts per run, 36 attempts total and 18 per provider. All failed and
  blocked slots remain in the denominator and are reported separately.
- Outcomes: case-level explicit-field exact match, decision/clarification
  alignment, parser result, CAD-003 Schema result, retrieval-induced changed
  fields, and latency/token/cost where available. No C2/C2O result enters the
  paired comparison. IR/CAD/geometry/STEP remain disabled in this proposal.
- Retention: new unique batch directory using the corrected
  `work/app001-runs/<batch_id>/raw/` layout. Never move, rewrite, rerun, or
  combine the historical batch.

## Required gates before any model request

1. Project owner reviews this question, input construction, and the small-n
   limitation. If accepted, freeze an evaluator-only three-case input/label
   artifact and its hashes; Codex independently checks leakage boundaries.
2. Implement a new controlled entrypoint against the current reviewed main
   baseline. Do not retrofit the old v5 entrypoint. Add offline tests for the
   exact 12 combinations, scope/hash rejection, model identity, clean batch
   directory, corrected raw path, budget caps, and no request before preflight.
3. Run the prescribed Python 3.11.18 regression and handoff checks; complete
   independent review and Codex final preflight.
4. Only then present the concrete new batch ID and authorization record for
   project-owner approval. A prior batch approval does not carry over.
5. Run the real providers only after that separate explicit approval and a
   successful online preflight. Keep the batch immutable and report results
   with the stated per-case limitations.

## Decision requested

Approve or revise the proposed question and scope before implementation. In
particular, confirm whether the three RET-003 held-out cases are the intended
next test set. No batch ID is assigned here and no model run is authorized.
