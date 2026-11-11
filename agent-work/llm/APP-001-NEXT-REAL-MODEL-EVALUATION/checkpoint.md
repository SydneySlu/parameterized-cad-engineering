# APP-001-NEXT-REAL-MODEL-EVALUATION checkpoint

## Status

`in_progress` — ADR-0019 records the accepted controlled-input protocol,
12-run matrix, and owner-approved physical-request budget. Frozen inputs and
labels pass hash and manifest checks. The implementation must enforce chat
caps of 36 total / 18 per provider / 3 per logical run, plus 20 identity
requests (2 Ollama batch preflight and up to 18 runtime tags: 6 Ollama runs ×
3 attempts), for hard physical-HTTP caps of 44 total, 18 DeepSeek, and 26
Ollama. All category, provider, and global caps apply together; category
caps do not add to a larger effective total. No batch ID has been assigned
and no model or preflight request is authorized. Implement and independently
review the dedicated fail-closed profile and entrypoint before final preflight.

## Repository and predecessor facts

- Repository: `/Users/syd/Desktop/参数化 cad 工程辅助设计`.
- Branch: `main`; baseline commit at task start `1f31871`.
- `origin/main` was behind the local main history at task start; current
  repository state and any later commits must be rechecked before execution.
- Worktree has task changes in ADR-0019, status/plan/log, and the two frozen
  JSON artifacts; these are not yet committed in the task-start snapshot.
- Proposal: `agent-work/inbox/APP-001-NEXT-REAL-MODEL-EVALUATION-PROPOSAL.md`.
- Predecessor v5 batch `app001-phase1-v5-20261111-01` is immutable and read-only.
  Its historical raw path deviation remains documented; never move, rewrite,
  rerun, or combine it with a future batch.

## Proposed scope retained

- Question: compare v5 outputs and deterministic CAD-003 acceptance with/without
  RET-002 retrieval for the three RET-003 held-out cases, case by case.
- Matrix: 3 cases × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b` = 12
  logical runs; chat maximum 3/run, 36 total, 18/provider. Physical HTTP
  maximum 44 total, 18 DeepSeek and 26 Ollama; identities have a separate
  maximum of 20 total (2 batch preflight + up to 18 runtime `/api/tags`).
- C1 uses only RET-002 `retrieval_source` candidates. Exclude C2/C2O and all
  IR/CAD/geometry/STEP execution. `provisional_small_n` requires per-case
  reporting and forbids broad generalization claims.

## Offline validation and evidence

Environment: Python 3.11.18 (macOS arm64). No model/network request, credential
or `.env` read, batch directory creation, or formal-run execution occurred.

Commands and results:

```text
git rev-parse --show-toplevel
  -> /Users/syd/Desktop/参数化 cad 工程辅助设计
git status --short --branch
  -> main...origin/main [ahead 2] (clean before this checkpoint)
git rev-parse HEAD
  -> 2054565b15ba232d151664bfa832b77be10d5a14
/opt/homebrew/bin/python3.11 --version
  -> Python 3.11.18
Read acceptance-set-v0.json model-visible case IDs/NLI/claims
  -> 9 acceptance cases; no RET-003 held-out query IDs; bore_d=80 case
     explicitly claims second_screw=0 and is a rule-conflict case
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 - [read-only projection/plan check]
  -> normal: frozen nine-case projection generates 36 combinations
  -> failure: three-case projection rejected: expected 9 acceptance cases, got 3
```

The initially attempted helper name `load_acceptance_set` does not exist; the
correct production API is `project_acceptance_set`. The corrected command above
used the actual API, pinned the acceptance-set SHA-256, and checked normal and
rejection paths. This was an inspection-command correction, not a code defect.

## Resolved design gates

1. **Natural-language input provenance:** RET-003's held-out records reference
   manifest parameters as evaluator truth; they do not freeze natural-language
   requests. The acceptance set's existing requests do not correspond to the
   three held-out IDs, and the bore_d=80 sample has a separate explicit rule
   conflict. Do not invent or derive user wording from held-out truth. An
   input-construction protocol and separate model-visible/evaluator-only
   artifact must be defined, frozen, hashed, and independently checked for
   leakage before execution work continues.
2. **Exact-scope authorization:** `FormalRunAuthorization` and
   `generate_combinations()` are explicitly frozen to acceptance-set-v0, 9
   cases, C0/C1, 2 providers, 36 logical runs and 108/54 attempt caps. The
   normal plan returns 36; a 3-case projection fails closed. Do not bypass the
   factory, relax it globally, or reuse `scripts/run_app001_v5_formal_batch.py`.
   ADR-0019 now records a separate exact 12-run path with 12/36/18 caps and
   hash-bound inputs. The existing factory and entrypoint remain unchanged.

## Frozen-input successor check (2026-11-11)

Environment: Python 3.11.18 (macOS arm64). Read-only; no model/network request,
secret or `.env` access, or batch directory creation.

```text
SHA-256 model-inputs.json -> c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6
SHA-256 evaluator-labels.json -> bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a
SHA-256 RET-001 manifest -> b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297
```

All three hashes match ADR-0019 and the labels' source manifest. The three
model-visible IDs map one-to-one to three labels; each explicit bore value
matches the NLI; each full expected parameter object matches its manifest row.
The model-input artifact contains no sample IDs or expected schema parameters.

```text
handoff_successor_check:
  predecessor=APP-001-NEXT-REAL-MODEL-EVALUATION offline preflight; checkpoint at 1f31871 plus ADR-0019/input artifacts
  files_format=pass; both JSON files parse; exact hashes and 3-case shape verified
  core_rerun=Python 3.11.18 read-only artifact/manifest/hash check; pass
  normal_case=APP001-HO-02 / bore_d=35 matches heldout-bore-035 manifest row; pass
  failure_case=existing FormalRunAuthorization rejects 3-case projection with expected-9-case guard; pass (prior checkpoint evidence)
  interface=labels are evaluator-only and separate; model input only has neutral ID and NLI; pass
  limits=provisional_small_n; synthetic inputs; no inference beyond 3 cases; no model authorization
  result=in_progress
  blocking_issue=none; owner-approved caps are recorded in ADR-0019; implementation/review/preflight remain
```

## Required next gate

The project owner accepted strict all-physical-HTTP accounting with separate
chat and identity subcaps. Implement and test the dedicated profile and
entrypoint without changing ADR-0014 or production v5 protocol. Every HTTP
request, including failed preflight/identity calls and retries, must have an
authorization-bound ledger reservation before network I/O. Run Python 3.11.18
regressions, independent review, and offline final preflight. Only after those
gates should a unique batch ID and complete authorization template be
presented for approval. Live preflight and chat requests both require that
approval and must be covered by the same batch budget.

## Budget-ledger implementation milestone (2026-11-11)

Status remains `in_progress`. Added the dedicated `HeldoutRunAuthorization`
profile and category-aware ledger enforcement for ADR-0019. The profile pins
the exact 12 logical runs, v5/IO contract, frozen input and evaluator-label
hashes, 36 chat attempts, 20 identity attempts and 44 physical HTTP attempts.
Provider caps are 18 DeepSeek and 26 Ollama; chat caps are 18/provider.
Identity caps are one preflight `/api/version`, one preflight `/api/tags`, and
18 runtime `/api/tags` total with at most three per Ollama logical run.

The ledger now records category, chat-by-provider, identity-by-bucket and
identity-by-run counters, reconstructs those counts from attempt records on
recovery, and rejects reservations that exceed any category/provider/global
cap. The legacy authorization summary/scope hash remains unchanged; legacy
non-model attempts retain their previous auxiliary accounting behavior.

Successor checks and validation (Python 3.11.18, macOS arm64):

```text
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_heldout_authorization -q
  -> 13 tests, OK (normal exact profile; scope, provider, endpoint, bucket, per-run cap and legacy-ledger recovery checks)
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_authorization tests.llm.test_budget tests.llm.test_runner -q
  -> 107 tests, OK, 7 skipped
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
  -> 855 tests, OK, 8 skipped
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q
  -> 17 tests, OK
py_compile (authorization, budget, heldout_authorization, heldout tests)
  -> OK
git diff --check
  -> clean
```

The skips are existing environment/FUSE limitations. No network/model request,
credential or `.env` read, historical raw read, or formal batch directory
creation occurred. No batch ID or request authorization exists.

```text
handoff_successor_check:
  predecessor=ADR-0019 accepted input/budget scope; current checkpoint and a6d97c8 frozen-input milestone
  files_format=pass; new profile and tests import under Python 3.11.18
  core_rerun=heldout authorization/budget suite; 13 passed
  normal_case=authorized held-out logical run reserves chat within provider/run caps; pass
  failure_case=duplicate preflight endpoint, fourth runtime identity call, wrong endpoint/provider and expanded scope reject; pass
  interface=profile pins the three neutral query IDs and exact input/label hashes; pass
  limits=budget layer only; dedicated runner, label isolation at execution, preflight reservation wiring and final offline preflight remain
  result=in_progress
  blocking_issue=none
```

Next: implement the dedicated offline-first runner and prove that every live
HTTP path obtains a ledger reservation before network I/O. Do not assign a
batch ID or perform network/model calls before independent review and final
offline preflight.

## Handoff self-check

```text
handoff_self_check:
  changed=ADR-0019 budget decision; checkpoint; PROJECT_STATUS; PROJECT_PLAN; WORKLOG; frozen input/label artifacts retained
  commands=Python 3.11.18 input/label/manifest hash and mapping check; git diff --check; request-budget call-path inspection
  confirmed=frozen artifacts match ADR hashes and RET-001 rows; approved budget is chat 36, identity 20, HTTP 44 total, DeepSeek 18, Ollama 26; old 9-case authorization unchanged; no request sent
  unresolved=dedicated authorization/profile/entrypoint, category-aware persistent ledger and test/review gates remain unimplemented
  next_agent_focus=implement and independently verify authorization-bound reservation for preflight and all runtime HTTP; do not assign batch_id or call network before final authorization
```
