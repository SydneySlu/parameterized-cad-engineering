# APP-001 extraction v5 prompt candidate strategy

## Status and purpose

`app001-extraction.v5-candidate` is an offline-only prompt candidate. It is not active, does not alter the production v4 loader, and is not authorization to run a model batch. Its scope is limited to the confirmed v4 decision and envelope-consistency deviations.

Evidence sources:

- `agent-work/reviews/APP-001-phase1-v4-20261109-01-codex-review.md`
- `agent-work/llm/APP-001-v4-quality-fix-candidate/candidate-strategy.md`
- `src/llm/decision_policy_v5_candidate.py`
- frozen `acceptance-set-v0.json`

## Intended behavior changes

1. **P1, complete conflict-free input:** when the user explicitly provides a catalog-valid `bore_d`, no required input is missing, no unsupported feature is requested, and no explicit coupled catalog/rule value conflicts, the model must choose `answer` in both C0 and C1. Retrieval references cannot create another user intent or justify asking the user to repeat a clear value.
2. **P2, envelope consistency:** a field cannot be both extracted and missing; `missing_fields` cannot contain duplicates; `answer` cannot coexist with missing or unsupported items or an explicit catalog/rule conflict.
3. Preserve all v4 safety and extraction boundaries: only explicit user claims are extracted; retain conflicting claims and evidence; do not derive catalog values; retain the 15-row selector gate, unsupported-request refusal, missing-`bore_d` behavior, and strict `second_screw == 1 iff bore_d > 70` rule.

## Acceptance-set mapping (offline expected behavior)

| Case | v5 candidate expectation | Relevant gate |
|---|---|---|
| A01 | `answer`; extract only explicit `bore_d`, `outer_d`, `width` | Complete valid request; no derived fields |
| A02 C0/C1 | `answer`; only explicit `bore_d=24` | P1: no re-ask; condition-independent |
| A03 | `answer`; normalize `1.6 cm` to `16 mm`, preserve source quote | P1: valid unit conversion |
| A04 | `ask` or `refuse`; preserve explicit fields and mark missing `bore_d` | Missing required selector remains a blocker |
| A05 C0/C1 | `ask` or `refuse`; preserve `bore_d=20` and `outer_d=40`; never list `outer_d` as missing | Real catalog conflict; P2 overlap guard |
| A06 | `answer`; `bore_d=70`, `second_screw=0` | Strict `>70` boundary |
| A07 | `refuse`; preserve `bore_d=75`, report flange/keyway/anodizing as unsupported | Non-catalog value and unsupported requests remain blockers |
| A08 C0/C1 | `answer`; use user `bore_d=24`, do not copy retrieved `bore_d=20` or its dimensions | Retrieval is reference only; P1 condition-independent |
| A09 | `ask` or `refuse`; preserve `bore_d=80` and `second_screw=0` | Explicit family-rule conflict remains a blocker |

The table is a candidate acceptance mapping, not evaluator data to inject into model prompts. The runtime user-message template remains unchanged and must not contain case IDs, expected behavior, labels, derived values, or unacceptable-output annotations.

## Checker alignment and limits

The v5 offline checker now treats all explicitly supplied coupled dimensions (`outer_d`, `width`, `screw_d`, `screw_len`) as catalog conflicts for P1 suppression and P2-5 answer rejection, in addition to the `second_screw` rule. It uses the frozen `CATALOG_ROWS` and the existing numeric/unit normalization helper. This keeps the checker aligned with the full v4 decision gate rather than only the two observed field examples.

The checker sees an output envelope, not the original natural-language request. It cannot determine whether the original wording was ambiguous, whether a claim was truly explicit, or whether the evidence quote faithfully supports it. P1 results are therefore offline consistency diagnostics for the declared envelope and known fixtures; they are not a substitute for raw input/output review or a model-effect evaluation.

## Invariants

- I/O contract stays `app001-io.v1`, with the exact existing nine-key envelope.
- Candidate output identifies itself as `app001-extraction.v5-candidate` only in the candidate artifact.
- Production remains `app001-extraction.v4`; `FROZEN_PROMPT_*` anchors and `FORMAL_EVALUATION_ALLOWED=False` remain unchanged.
- No model/network call, `.env` read, API-key access, formal batch creation, or old-batch modification.
- Offline prompt/checker tests establish artifact and deterministic-rule consistency only; they do not establish model compliance or effectiveness.
- Any later model-effect test needs a new unique batch ID, a new explicit owner authorization, and Codex preflight. Existing v4 batches remain read-only and are never pooled with a v5 batch.
