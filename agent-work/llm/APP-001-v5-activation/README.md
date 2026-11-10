# APP-001 extraction v5 activation

## Status: active in this branch; review required before main

This package freezes the v5 production prompt and records its provenance and rollback target. The runtime changes are intentionally narrow: `app001-io.v1` remains the envelope contract, while the active prompt policy advances from v4 to v5 under accepted ADR-0018.

Activation does not authorize model calls or a formal evaluation batch. `FORMAL_EVALUATION_ALLOWED` remains false. The existing formal batch script is explicitly bound to v4 and must not be used for v5. Any v5 effect evaluation requires a separately reviewed v5-capable controlled entry point, a new unique `batch_id`, explicit project-owner authorization, and Codex final preflight. Existing v2/v3/v4 batches stay read-only and are never pooled with v5 results.

## Identity

See `manifest.json` for full hashes. The active prompt is `prompt-v5.md`; v4 is retained as the explicit rollback target. The activation-preparation copy and reviewed candidate source hashes are recorded separately.

## Runtime changes

- `PROMPT_VERSION` and prompt-loader path/version/hash anchor point to v5.
- The default parser accepts v5 only. The explicit historical audit parser retains v2, v3, and v4.
- Envelope keys, CAD schema, budgets, retry policy, authorization logic, and the formal evaluation gate are unchanged.

## Rollback

If a protocol or runtime inconsistency is found before any v5 evaluation, restore `contract.py`, `prompt_loader.py`, and parser default/legacy version handling to v4 values recorded in `manifest.json`. Preserve the v5 prompt and all old batch evidence. Rollback does not authorize rerunning v4 or changing any historical batch.
