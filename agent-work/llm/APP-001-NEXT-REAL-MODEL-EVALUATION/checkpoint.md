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

## Runner and entrypoint implementation milestone (2026-11-11)

Status: `in_progress` (independent review and final offline preflight remain).

### New files

- `src/llm/heldout_runner.py` — dedicated offline-first held-out v5 runner.
  Implements `HeldoutRunner` with `dry_run()`, `offline_preflight()`, and
  `run_formal()` entry points; `generate_heldout_combinations()` (12-run
  matrix independent of `generate_combinations()`); `load_heldout_inputs()`
  (SHA-256-verified, label-free projection); `_assemble_c0` / `_assemble_held_c1`
  wrappers; `_HeldoutProjectedCase` adapter; `_heldout_raw_retention_policy()`;
  and `_ensure_heldout_ir_cad_not_run()`.  Evaluator labels are never passed to
  combinations, input assembly, Adapter, transports, the Prompt, run records,
  or any log output.
- `scripts/run_app001_heldout_v5.py` — CLI entry point for `--dry-run`,
  `--offline-preflight`, and `--run` modes.  Formal mode is blocked unless
  `FORMAL_EVALUATION_ALLOWED=True` AND `--allow-formal-run` is explicitly
  passed.
- `tests/llm/test_heldout_runner.py` — 53 offline/mock tests covering all 7
  required categories (12 combinations, label isolation, C0/C1 assembly,
  rejection cases, mock HTTP budget enforcement, run record paths, scope
  summary/ledger audit and legacy regressions).

### Validation (Python 3.10.12 in sandbox; production baseline is 3.11.18)

```text
PYTHONPATH=src:. python3 -m py_compile src/llm/heldout_runner.py scripts/run_app001_heldout_v5.py tests/llm/test_heldout_runner.py
  -> OK

PYTHONPATH=src:. python3 -m unittest tests.llm.test_heldout_runner -v
  -> 53 tests, OK

PYTHONPATH=src:. python3 -m unittest tests.llm.test_heldout_authorization tests.llm.test_authorization tests.llm.test_budget tests.llm.test_runner -q
  -> 120 tests, OK (skipped=7)

PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q
  -> 908 tests, OK (skipped=8)

PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q
  -> 17 tests, OK

git diff --check
  -> clean (no whitespace errors)
```

The 8 skips are existing FUSE/environment limitations (Ollama version/connectivity
checks in real-transport tests).  No network call, credential read, formal batch
directory creation, or model request occurred.  No formal batch_id exists.

### Key design decisions enforced

- Evaluator labels are strictly isolated: `load_heldout_inputs()` only extracts
  `query_id` and `natural_language_input`; `HeldoutCase` has no label fields;
  `_HeldoutProjectedCase` has no label fields; blocked audit records exclude
  labels; dry-run and preflight output excludes labels.
- All 12 runs are generated by `generate_heldout_combinations()`, which is
  independent of `generate_combinations()` and validates inputs_sha256,
  query_ids, conditions, providers, and IR/CAD disabled against the authorization.
- `dry_run()` requires no authorization and makes no network calls.
- `offline_preflight()` verifies all hash pins (inputs, labels, RET-001 manifest),
  authorization profile, retrieval config (if provided), batch directory strategy,
  and budget feasibility without any network I/O.
- `run_formal()` is fail-closed: requires `HeldoutRunAuthorization`, retrieval
  index, and passes all preflight checks before constructing any transport.
- Every physical HTTP request goes through `BudgetAwareTransport` → `BudgetLedger`
  reservation before `urlopen`/`send`, verified by mock-HTTP tests.
- `_heldout_raw_retention_policy()` writes raw responses to
  `work/app001-runs/<batch_id>/raw/`.
- `FORMAL_EVALUATION_ALLOWED=False` is never altered.

```text
handoff_successor_check:
  predecessor=budget-ledger milestone (d62e238); current checkpoint plus runner/entrypoint/tests
  files_format=pass; all three new files compile under Python 3.10.12 (proxy for 3.11.18)
  core_rerun=test_heldout_runner 53/53 OK; heldout auth/budget/runner 120/120 OK (7 skips)
  normal_case=dry_run produces 12 combinations, stable SHA-256; C0 assembles for all three queries; C1 assembles with mock retrieval index (retrieval_source candidates only)
  failure_case=bad inputs hash raises HeldoutInputError; existing batch dir raises FormalEvaluationBlockedError; run_formal without HeldoutRunAuthorization raises FormalEvaluationBlockedError; DeepSeek budget exhausted → FakeTransport call count = 0
  interface=labels never reach Adapter/Transport/logs/dry-run; raw retention policy uses batch/raw/; blocked records include no labels
  limits=Python 3.10.12 in sandbox (not 3.11.18); no live preflight or model call authorized; no formal batch_id; independent review pending
  result=in_progress
  blocking_issue=none; pending Codex independent review and final offline preflight
```

## Handoff self-check

```text
handoff_self_check:
  changed=src/llm/heldout_runner.py (new); scripts/run_app001_heldout_v5.py (new); tests/llm/test_heldout_runner.py (new); checkpoint (this update); PROJECT_STATUS; PROJECT_PLAN; WORKLOG
  commands=py_compile all three new files; test_heldout_runner 53/53 OK; heldout auth/budget/runner 120 OK (7 skips); LLM full 908 OK (8 skips); Schema 17 OK; git diff --check clean
  confirmed=all hash pins match ADR-0019; 12 unique combinations; label isolation verified; budget enforcement verified via mock HTTP; blocked cases retained; legacy auth/budget regression passes; FORMAL_EVALUATION_ALLOWED=False unchanged
  unresolved=sandbox uses Python 3.10.12 not 3.11.18; independent Codex review pending; final offline preflight pending; no batch_id or model request authorization
  next_agent_focus=independent review: re-run full test suite under Python 3.11.18; verify evaluator labels never appear in any output path; confirm dry-run/offline-preflight modes work offline; confirm that run_formal is correctly fail-closed; check raw retention path; then present batch_id authorization template to project owner
```
