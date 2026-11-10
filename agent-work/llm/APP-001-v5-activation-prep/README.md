# APP-001 v5 activation preparation

## Status: proposed; not active

This package stages the v5 prompt identity, source provenance, hashes, acceptance-set reference, and rollback target for review. It does not change the production prompt. Production remains `app001-extraction.v4` under `app001-io.v1`.

No decision to activate v5 is recorded here. The linked ADR-0018 is proposed and requires project-owner review. This package does not authorize real-model requests or a formal evaluation batch.

## Contents

| File | Purpose |
|---|---|
| `prompt-v5.md` | Version-normalized activation-preparation copy of the reviewed candidate; not loaded by production |
| `manifest.json` | Candidate/source hashes, frozen evaluation references, current production identity, prerequisites, rollback target |
| `README.md` | Status and operational boundaries |
| `checkpoint.md` | Preparation evidence and handoff self-check |
| `handoff.md` | Independent review focus |

## Identity

See `manifest.json` for full hashes. At preparation time:

```text
candidate_prompt_version: app001-extraction.v5
production_prompt_version: app001-extraction.v4
contract_version: app001-io.v1
acceptance_set: acceptance-set-v0 (9 cases)
production_files_changed: false
formal_evaluation_authorized: false
rollback_target: app001-extraction.v4
```

The v5 prompt copy differs from the reviewed candidate only in the prompt-version literal and candidate-only heading labels. The source candidate hash and activation-preparation copy hash are recorded separately.

## Activation prerequisites

1. Project owner reviews and accepts the proposed strategy in ADR-0018.
2. A separate activation implementation updates `contract.py`, parser version handling, prompt-loader path/version/hash anchors, activation documentation, and compatibility tests as one atomic unit.
3. Codex independently reviews the implementation and verifies the required suites under Python 3.11.18 before merge to `main`.
4. A real-model evaluation requires a separate new unique `batch_id`, explicit owner authorization, and Codex preflight after activation. Existing batches remain read-only and are never pooled with v5 results.

## Rollback target

Rollback target is the current frozen v4 prompt:

- file: `../APP-001-v4-activation/prompt-v4.md`
- SHA-256: recorded as `rollback_prompt_file_sha256` in `manifest.json`

No rollback is performed by this preparation task. Historical prompts and batches must remain untouched.
