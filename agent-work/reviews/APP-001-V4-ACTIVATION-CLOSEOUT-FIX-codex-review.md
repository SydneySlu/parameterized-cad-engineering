# APP-001-V4-ACTIVATION-CLOSEOUT-FIX Codex Review

- Date: 2026-11-08
- Reviewer: Codex hub
- Reviewed commit: `f858be802fb0e5e03996277434ff27f51a5f06ea`
- Parent: `85f9e712f55e2c53484728661b70b7f15846ddeb`
- Branch: `cc/APP-001-V4-ACTIVATION`
- Result: `review` — content and local verification pass; remote publication/hash confirmation remains pending.

## Scope reviewed

Compared `85f9e71..f858be8`. The closeout patch changes only comments/docstrings, package documentation, the activation checkpoint, and the append-only work log. No test file, frozen prompt, contract/runtime behavior, authorization, budget, provider, retry, or formal-run configuration changed.

The activation commit is `85f9e71`; `d01eb81` is the closeout content commit; `f858be8` is its child correcting the work-log commit reference. The final reviewed HEAD is `f858be8`.

## Independent verification

Python `/opt/homebrew/bin/python3.11` is version 3.11.18.

| Check | Result |
|---|---|
| `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_v4_activation -q` | 71 tests passed |
| `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q` | 685 passed, 8 existing FUSE skips |
| `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q` | 17 passed |
| `... -m py_compile` for `prompt_loader.py`, `parser.py`, `adapter.py`, `__init__.py` | passed |
| `git diff --check` | passed |

Normal-path check: loader reports `app001-extraction.v4`; a v4 envelope passes the default parser.

Failure-path check: a v3 envelope is rejected by the default parser with `PROMPT_VERSION_MISMATCH`; historical v3 remains available through the explicit audit parser, covered by the v4 activation tests.

## Identity and boundaries

- v4 prompt SHA-256: `73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc`.
- v3 rollback prompt SHA-256: `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`.
- `acceptance-set-v0.json` SHA-256: `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`.
- `FORMAL_EVALUATION_ALLOWED` remains `False`.
- No real model call, credential read, new batch, or old batch modification was part of this review.

## Findings and next gate

The documentation cleanup is accurate and the local commit chain is internally consistent. The working tree was clean at review start. Local branch configuration still tracks `origin/codex/APP-001-V3-DECISION-FIX-DRAFT`; the correct remote branch `cc/APP-001-V4-ACTIVATION` was not confirmed because `git ls-remote` timed out. Do not report the branch as pushed until a successful remote hash check confirms it.

Next: publish the complete local branch from the project owner's Mac with `git push -u origin cc/APP-001-V4-ACTIVATION`, then compare the remote ref from `git ls-remote --heads origin cc/APP-001-V4-ACTIVATION` against the local `git rev-parse HEAD` at push time. The branch includes the activation, closeout, and Codex review commits. After the hashes match, perform the final merge-to-main review. This review does not authorize a v4 model-effect batch; a new unique batch and explicit authorization remain required.
