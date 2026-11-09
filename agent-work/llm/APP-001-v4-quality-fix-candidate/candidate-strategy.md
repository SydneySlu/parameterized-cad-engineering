# APP-001 v5 quality-fix candidate strategy

## Status

UNACTIVATED CANDIDATE — OFFLINE ONLY.  No model call, no network access,
no API key read, no formal batch, no production change.

## Confirmed deviations addressed

Source: `agent-work/reviews/APP-001-phase1-v4-20261109-01-codex-review.md`

### P1 — Ollama over-refusal (3 cases)

| Case | Condition | Model decision | Expected | Root cause |
|------|-----------|---------------|----------|------------|
| A02 | C1 | refuse | answer | Retrieval context confusion |
| A03 | C0 | refuse | answer | Unit conversion (1.6 cm → 16 mm) rejected |
| A08 | C1 | refuse | answer | Retrieval context confusion |

In all three cases the extracted envelope already contained a valid catalog
bore_d, `missing_fields=[]`, and `unsupported_requests=[]`.  The prompt
instruction "Do not ask again for a parameter that is explicit and unambiguous
in the user request merely because untrusted retrieval context contains a
different value" was violated.

### P2 — Envelope self-consistency (2 cases)

| Case | Condition | Issue |
|------|-----------|-------|
| A05 | C0 | `outer_d=40` in both `extracted_parameters` and `missing_fields` |
| A05 | C1 | Same violation under C1 |

## P1 rules (candidate checker)

- **P1-1**: If `decision` is `refuse` or `ask` AND `bore_d` is present in
  `extracted_parameters` as a valid catalog value AND `missing_fields=[]`
  AND `unsupported_requests=[]`, the decision is an over-refusal.  The v5
  candidate rule requires `decision=answer` in this situation.

- **P1-2** (condition-agnostic): The P1-1 check produces the same result
  regardless of `condition_id` (C0 or C1).  Retrieval context cannot create
  missing_fields or unsupported_requests that are absent from the user's own
  input.

- **P1-3** (unit normalization): A unit-converted bore_d (e.g. 1.6 cm → 16 mm)
  that lands on a valid catalog value must not be refused solely because the
  original unit was non-mm.  Captured by P1-1 using the normalized value already
  present in `extracted_parameters`.

- **P1-4** (retrieval non-interference): C1 retrieval reference context must
  not fabricate missing_fields or unsupported_requests.  Enforced transitively:
  when missing_fields and unsupported_requests are already empty and bore_d is
  valid, P1-1 fires regardless of condition_id.

## P2 rules (candidate checker)

- **P2-1**: No field that appears in `extracted_parameters` may also appear in
  `missing_fields`.  A field is either extracted (present) or missing — never
  both.

- **P2-2**: Same invariant stated from the other side (for test coverage).

- **P2-3**: `decision=answer` must not coexist with non-empty `missing_fields`
  or non-empty `unsupported_requests`.

- **P2-4**: No duplicate entries within `missing_fields`.

## Preserved boundaries

- A04 (missing bore_d): refuse/ask valid — P1 does NOT fire (bore_d absent).
- A05 (catalog conflict): ask valid — P1 does NOT fire (missing_fields
  non-empty).  P2-1 fires on the observed deviation (outer_d in both), but not
  on the corrected envelope.
- A07 (out of catalog + unsupported): refuse valid — P1 does NOT fire (bore_d
  not in catalog, unsupported non-empty).
- A09 (rule conflict): refuse/ask valid — P1 does NOT fire (missing_fields
  non-empty).

## Version and isolation

- Candidate version: `app001-extraction.v5-candidate`
- Contract version: `app001-io.v1` (unchanged I/O contract)
- Production `PROMPT_VERSION` remains `app001-extraction.v4`
- `FROZEN_PROMPT_*` anchors unchanged
- `FORMAL_EVALUATION_ALLOWED` remains `False`
- The v5 checker (`src/llm/decision_policy_v5_candidate.py`) is NOT imported
  by adapter, parser, runner, contract, or prompt_loader.

## What this is NOT

- Offline checker pass ≠ model effect pass
- No new formal batch created or authorized
- No effect conclusion drawn
- If a future formal test is needed, a new unique `batch_id` and Codex preflight
  authorization are required
