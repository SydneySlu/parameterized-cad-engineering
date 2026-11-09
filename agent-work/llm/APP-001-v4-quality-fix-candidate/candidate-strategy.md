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
  AND `unsupported_requests=[]` AND there is no deterministic catalog/rule
  conflict in the extracted fields, the decision is an over-refusal.  The v5
  candidate rule requires `decision=answer` in this situation.

  **Conflict suppression (R1)**: P1-1 is suppressed when the extracted fields
  contain a deterministic catalog/rule conflict (e.g. outer_d mismatch or
  second_screw rule violation).  Such a conflict is a legitimate reason for
  ask/refuse.

- **P1-2** (condition-agnostic): The P1-1 check produces the same result
  regardless of `condition_id` (C0 or C1).

- **P1-3** (unit normalization): A unit-converted bore_d (e.g. 1.6 cm → 16 mm)
  that lands on a valid catalog value is recognized by the normalized integer
  value; captured by P1-1.

- **P1-4** (retrieval non-interference): C1 retrieval reference context must
  not fabricate missing_fields or unsupported_requests.  Enforced transitively.

## P2 rules (candidate checker)

- **P2-1**: No field that appears in `extracted_parameters` may also appear in
  `missing_fields`.

- **P2-2**: Same invariant from the other direction.

- **P2-3**: `decision=answer` must not coexist with non-empty `missing_fields`
  or non-empty `unsupported_requests`.

- **P2-4**: No duplicate entries within `missing_fields`.

- **P2-5 (R1)**: `decision=answer` must not coexist with a deterministic
  CAD-003 catalog or rule conflict:
  (a) explicit `outer_d` disagrees with the catalog row for `bore_d`
      (e.g. bore_d=20 maps to outer_d=32, but envelope has outer_d=40);
  (b) explicit `second_screw` violates the bore_d > 70 rule
      (e.g. bore_d=80 but second_screw=0).
  The checker records the conflict without modifying or removing any explicit
  claim.  P2-5 applies only to `decision=answer`; ask/refuse with the same
  conflict is not flagged (the conflict is the valid reason for ask/refuse).

## R1 additions (this round)

- **R1-1** Import compatibility: `from schema.set_screw_shaft_collar` (absolute
  import). Module importable under `PYTHONPATH=src` as `import llm.decision_policy_v5_candidate`.
- **R1-2** P2-5: `decision=answer` + catalog conflict (outer_d mismatch) or rule
  conflict (second_screw rule) → violation detected.
- **R1-2** P1-1 conflict suppression: ask/refuse with a deterministic conflict
  suppresses P1-1 (the conflict is the valid reason).
- **R1-3** `_normalize_bore_d()`: bare floats (24.0 → 24), measurement objects
  ({"value":1.6,"unit":"cm"} → 16), unknown units → None, non-finite → None,
  fractional mm → None.

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

## R1 additions (Codex review 2026-11-09, corrected in R1 round)

- **R1-1** Import compatibility: changed `from ..schema.set_screw_shaft_collar` to
  `from schema.set_screw_shaft_collar` (absolute import).  Module now importable
  under both `PYTHONPATH=src` (`import llm.decision_policy_v5_candidate`) and
  `PYTHONPATH=src:.` (`import src.llm.decision_policy_v5_candidate`).
- **R1-2** P2-5 catalog/rule conflict detection for `decision=answer`.
- **R1-2** P1-1 conflict suppression: ask/refuse with a deterministic conflict
  is a legitimate decision and must NOT be flagged as over-refusal.
- **R1-3** `_normalize_bore_d()`: handles bare floats (24.0 → 24), measurement
  objects ({"value":1.6,"unit":"cm"} → 16), unknown units → None, non-finite
  floats → None, fractional mm values → None.

- Offline checker pass ≠ model effect pass
- No new formal batch created or authorized
- No effect conclusion drawn
- If a future formal test is needed, a new unique `batch_id` and Codex preflight
  authorization are required
