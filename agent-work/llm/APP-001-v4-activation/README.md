# APP-001 v4 Activation Package

## Status: done

This package implements the v4 extraction contract activation as approved by
the project lead under ADR-0017.  The implementation and closeout were
independently reviewed by the Codex hub and merged to `main` in `c18fd35`.
This package still does not authorize a real-model evaluation batch.

## Contents

| File | Purpose |
|---|---|
| `prompt-v4.md` | Frozen activation copy of the v4 system + user prompt |
| `manifest.json` | Source/activation hashes, versions, rollback target |
| `README.md` | This file |
| `checkpoint.md` | Activation checkpoint and handoff record |

## Identity

```
package_id:              APP-001-v4-activation
production_prompt_version: app001-extraction.v4
contract_version:        app001-io.v1
acceptance_set:          acceptance-set-v0 (9 cases)
cad_schema:              set_screw_shaft_collar.v0
prompt_file:             prompt-v4.md
prompt_file_sha256:      73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc
source_candidate:        ../APP-001-baseline-prep/prompt-v4-candidate.md
source_candidate_sha256: 145cb487830f22d210a53ad17b1d0c9870512d44b6cace2cb9ef2be8b590606f
```

## What v4 changes vs v3

1. **Unit normalization** — `1.6 cm` is exactly `16 mm`; a convertible unit
   is not a reason to ask or refuse when the result is a valid catalog value.
2. **User value priority over retrieval** — an explicit `bore_d=24 mm` from
   the user takes precedence over any differing retrieval example; the model
   must not ask which value was intended.
3. **Stable unsupported-request labels** — `anodizing`, `flange`, `keyway`
   are the canonical labels; the user's original wording is preserved as the
   evidence quote.

All v3 safety gates (bore_d catalog membership, unsupported-request blocking,
self-contradiction handling, `75 mm` non-catalog refuse) are preserved
unchanged.

## Rollback

To roll back to v3:
1. Restore `PROMPT_VERSION = "app001-extraction.v3"` in `src/llm/contract.py`.
2. Restore `FROZEN_PROMPT_PATH` to `APP-001-v3-activation/prompt-v3.md` and
   `FROZEN_PROMPT_FILE_SHA256` to
   `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`
   in `src/llm/prompt_loader.py`.
3. Restore `_LEGACY_AUDIT_PROMPT_VERSIONS` to `{"app001-extraction.v2"}` in
   `src/llm/parser.py`.
4. Do NOT delete or modify any v4 or v3 files.  Historical evidence must be
   preserved.

v3 frozen prompt SHA-256:
`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`

## Not authorized by this activation

- No real model calls (DeepSeek or Ollama).
- No new formal evaluation batch.
- No change to `FORMAL_EVALUATION_ALLOWED`.
- No C2, IR, CAD, geometry, or STEP stage execution.
- No API key reads.
