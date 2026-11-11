# APP-001 next real-model evaluation proposal

Status: experiment question/scope approved in principle by the project owner;
pre-execution design is blocked on input provenance and a new exact-scope
authorization path. This is not a batch authorization or permission to issue
model requests.

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

1. Resolve the input source: RET-003 provides structured manifest references,
   not frozen natural-language requests. The existing nine-case acceptance set
   contains no matching held-out query IDs; its bore_d=80 case is an explicit
   rule-conflict case and cannot stand in for a clean held-out request. Do not
   derive or invent natural-language inputs from held-out truth without an
   explicitly reviewed input-construction protocol. Freeze model-visible
   inputs separately from evaluator-only labels and truth, then independently
   check leakage.
2. Define a new, fail-closed authorization/combination scope for exactly the
   three held-out IDs × C0/C1 × the two fixed providers (12 logical runs), with
   3 attempts per run, 36 total, 18/provider, and C2/IR/CAD/geometry/STEP
   disabled. Existing `FormalRunAuthorization` and `generate_combinations()`
   are frozen to the nine-case acceptance set and 36 logical runs; they reject
   a three-case projection. Do not bypass them or reuse the old v5 entrypoint.
   Record any required policy change in `docs/DECISIONS.md` before
   implementation.
3. Implement a new controlled entrypoint against the current reviewed main
   baseline. Do not retrofit the old v5 entrypoint. Add offline tests for the
   exact 12 combinations, scope/hash rejection, model identity, clean batch
   directory, corrected raw path, budget caps, and no request before preflight.
4. Run the prescribed Python 3.11.18 regression and handoff checks; complete
   independent review and Codex final preflight.
5. Only then present the concrete new batch ID and authorization record for
   project-owner approval. A prior batch approval does not carry over.
6. Run the real providers only after that separate explicit approval and a
   successful online preflight. Keep the batch immutable and report results
   with the stated per-case limitations.

## Codex offline validation (2026-11-11)

- Result: `blocked`; no batch ID assigned. The approved experimental question
  is retained, but the execution design is not yet sufficiently specified to
  freeze or authorize.
- Python 3.11.18 read-only checks confirmed the acceptance-set hash and
  projection. Its nine model-visible natural-language inputs are existing
  acceptance cases, not the three RET-003 held-out query IDs. The `bore_d=80`
  acceptance case includes an explicit `second_screw=0` rule conflict, so it
  is not an equivalent clean held-out request.
- Existing authorization/combination path normal case: the frozen projection
  generates 36 combinations. Failure case: a 3-case projection is rejected
  with `expected 9 acceptance cases, got 3`. Authorization caps and sample set
  are hard-coded for the 36-run acceptance-set-v0 experiment.
- No code or runtime configuration changed; no model/network request, key or
  `.env` access, batch directory creation, or formal-run attempt occurred.
- See `agent-work/llm/APP-001-NEXT-REAL-MODEL-EVALUATION/checkpoint.md` for
  commands, evidence, and required owner decision.

## Decision requested

The project owner has approved the experiment question/scope in principle and
asked Codex to validate offline before assigning a batch ID. The validation
found the two blockers above. Resolve the natural-language input provenance
and approve the required exact 12-run authorization design before the
entrypoint is implemented. No batch ID is assigned here and no model run is
authorized.
