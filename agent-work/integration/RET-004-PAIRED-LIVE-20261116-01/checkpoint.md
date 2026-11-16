# RET-004 checkpoint

- Task: `RET-004-PAIRED-LIVE-20261116-01`
- Current status: `done` — exact scope accepted, authorized C0/C1 extraction completed, both approved R01 runs completed CAD/STEP readback, R02 remained CAD-denied, independent closeout review passed, and the documentation closeout is merged into local `main`.
- Base: `main` at `b5f5d45ef7635062afe8952b1483e2c068a90fb2` (local main was 14 commits ahead of origin at start).
- Branch: `codex/RET-004-PAIRED-LIVE-PROTOCOL`.

## Initial evidence and interface finding

- Existing `src/llm/conditions.py::assemble_c1()` already uses only natural-language `bore_d`, RET-002, and `retrieval_source` filtering. It serializes an explicit `retrieval_example_untrusted_reference` role and warning; frozen v5 prompt preserves user intent.
- The APP-004 stimulus wording `轴孔孔径为 24 mm` was not recognized by the C1 query regex. Without a narrow compatibility fix, the proposed real C0/C1 comparison would block C1 before model transport and would not test the intended retrieval condition.
- Added support for `轴孔孔径为 <value> <unit>` and two regression tests, including the anodizing input. `tests.llm.test_conditions`: 12/12 pass in system Python 3.10.12. Direct RET-002 assembly confirms both inputs extract 24 mm and return only retrieval-source candidates. An initial exploratory direct retrieval call used an invalid/incomplete envelope and was rejected by Schema; it made no network or file changes. The corrected verification used `assemble_c1()` and passed.

## Candidate experiment

- Two fixed inputs, each paired across C0/C1: a supported bore-24 request and the same request with anodizing unsupported; four logical runs total.
- DeepSeek `deepseek-flash`, frozen v5/contract, RET-002 top-k 3; max 2 attempts/run, max 8 HTTP batch cap.
- R01 may enter CAD only after separate fresh owner confirmation for each condition. R02 is CAD-denied regardless of response.
- Inputs and evaluator labels are physically separate. Proposed scope details are in `scope.md`; proposed stimuli and labels are in separate JSON files.
- Proposed batch ID `ret004-paired-live-20261116-01` is only a candidate and remains unconsumed. No batch directory, ledger, credential read, preflight, network/model request, or CAD run occurred.
- Candidate hashes: inputs `6f2faf8d83aa013c860db4e17593788bc906757660ed8c985f374b6bbe21a457`; labels `fc1691317dfc6452a956bad36fff8e5e6cd3a4d4dbf459d096632e6e4850091e`; RET-002 config `424322f51da78df2a154043d284d307ae285c7d2a2cb659f5517a6ecb847cfc5`; RET-001 manifest `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`.

## Remaining before live-request approval

1. Complete hashes for both JSON files and RET-002 config; bind them in a dedicated versioned authorization profile and formal runner.
2. Run fixed CAD venv tests for the C0/C1 real assembly path, real adapter request construction (with FakeTransport), failure/summary isolation, C0/C1 pairing, CAD confirmation and hard denial.
3. Independent review of scope, code, tests, hashes, retrieval-source filtering, and failure denominators.
4. Ask the owner in this conversation to accept the exact frozen scope, then complete formal preflight; request a separate explicit approval for the exact batch and real DeepSeek requests.

Offline checks verify linkage and fail-closed behavior only. They are not retrieval-effect evidence. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.

## Handoff successor check — protocol/interface preparation

- Predecessor: candidate protocol and C1 parser compatibility fix on `98f28c5`; follow-up top-k assertion alignment is in the working tree.
- Files/format: `scope.md`, `model-inputs.json`, and `evaluator-labels.json` are present; JSON artifacts remain physically separate. Their hashes match the candidate hashes above.
- Core rerun: fixed CAD venv Python 3.11.18 ran `tests.llm.test_conditions tests.retrieval.test_retrieval_baseline` — 42/42 passed.
- Normal case: both R01 and R02 C1 assembly extract explicit `bore_d=24`, return three RET-002 `retrieval_source` candidates, and retain the same user text.
- Failure case: C1 input with no explicit bore remains blocked with `C1_NO_SAFE_QUERY_PARAMETER`; it cannot call model transport.
- Interface: existing `AdapterInput` has a single `reference_context` slot; C0 sets it to `None`, C1 receives `assemble_c1()` output. The frozen template/hash stays unchanged. Existing product flow exposes an extraction result in `needs_confirmation`, and `confirm_product_live_run()` is the CAD entry; RET-004 must additionally hard-deny R02 and require separate confirmation for each R01 condition.
- Limits: no RET-004 formal runner/profile, preflight, batch/ledger, credential read, model/network request, or CAD execution has occurred. Scope remains `proposed`; `FORMAL_EVALUATION_ALLOWED=False`.
- Result: `pass` for the narrow C1 assembly handoff; formal runner implementation and independent review remain outstanding.
- Next gate: owner acceptance of the exact RET-004 scope/hash set. Then implement the versioned formal runner and confirm gate, validate in the fixed CAD venv, independently review, run the exact formal preflight, and request a separate explicit approval for real DeepSeek execution.

## Formal runner implementation checkpoint

- Status: `review`; implementation is ready for independent read-only review. Scope remains `proposed`; no batch, formal preflight, credentials, network/model request, or CAD execution occurred.
- Files added: `src/llm/ret004_authorization.py`, `src/integration/ret004_paired_runner.py`, and `tests/integration/test_ret004_paired_runner.py`. Existing retry API gained an optional bounded attempt cap while preserving its default; tests cover the cap.
- Frozen binding: profile `ret004-paired-live.v1`, inputs SHA-256 `6f2faf8d83aa013c860db4e17593788bc906757660ed8c985f374b6bbe21a457`, evaluator labels SHA-256 `fc1691317dfc6452a956bad36fff8e5e6cd3a4d4dbf459d096632e6e4850091e`, RET-002 config SHA-256 `424322f51da78df2a154043d284d307ae285c7d2a2cb659f5517a6ecb847cfc5`, and RET-001 manifest SHA-256 `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`. Prompt and contract hashes are bound in the authorization profile; labels are not opened by the runner.
- Safety/flow: exact C0/C1 input and prompt pairing differs only at `reference_context`; C1 remains RET-002 `retrieval_source`, top-k=3, untrusted reference. Per-run attempt cap=2 and batch cap=8. R01 C0 and C1 confirmations are separate; R02 is hard-denied. Offline FakeTransport cannot enter CAD; confirmation requires an exact boolean and rejects changed in-memory result state. Formal path validates scope/approval and offline artifact/runtime preflight before credential loading and batch/ledger/transport setup. `FORMAL_EVALUATION_ALLOWED=False` unchanged.
- Verification in fixed CAD venv Python 3.11.18:
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m py_compile src/integration/ret004_paired_runner.py src/llm/ret004_authorization.py src/llm/adapter.py src/llm/retry.py tests/integration/test_ret004_paired_runner.py tests/llm/test_retry.py tests/llm/test_conditions.py` — pass.
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_ret004_paired_runner tests.llm.test_conditions tests.llm.test_retry tests.retrieval.test_retrieval_baseline -q` — 76/76 pass.
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/llm -p 'test_*.py' -q` — 945 pass, 8 existing skips.
  - `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_live tests.integration.test_app004_live_web tests.demo.test_product_live_ui tests.integration.test_pipeline tests.integration.test_schema_to_ir -q` — 253/253 pass.
- Normal case: FakeTransport exercised all four logical runs; C0 context is null, paired C1 adds only the three RET-002 references with untrusted role; R01 answer states reach separate pending-confirmation gates.
- Failure cases: retry exhaustion remains within two attempts for that logical run; malformed provider body is sanitized and does not call CAD; R02 answer is still blocked; non-boolean confirmation and mutation of a confirmable result are rejected before CAD; test-only approval cannot enter formal execution/service construction.
- Commit: `da8e6de` (`feat: prepare paired retrieval live runner [RET-004-PAIRED-LIVE-20261116-01]`), based on protocol commit `98f28c5` and `main=b5f5d45`.
- Remaining gates: independent read-only review; owner acceptance of exact scope and hashes; formal preflight after acceptance; a separate exact-batch real DeepSeek authorization. Live outputs remain unmeasured; this offline work does not establish retrieval benefit.

## Independent review findings follow-up

- Review input: independent verdict `review` against `98f28c5..a87734c`, identifying two P1 and two P2 findings.
- Fixes: R01's explicit natural-language `bore_d` is now compared against model extraction before `needs_confirmation`; mismatch/missing explicit value becomes blocked. Batch summary prepopulates all four planned run records, tracks `not_started`/attempted state, and only marks `complete` when every run has a scope-acceptable outcome (R01 success or explicit rejection; R02 refusal with unsupported request). Transport/parse/adapter failures and unexpected R02 answer remain `failed`. RET-004 C1 wrapper rejects structural reference fallback. Summary canonicalizes raw path through `_to_repo_relative_path`; invalid paths are omitted and flagged.
- Regression coverage: mismatching `bore_d=20`; full four planned summary records; failed R02 answer does not complete; supported refusal plus both R01 explicit declines completes; structural-reference query source rejected; absolute raw path sanitized.
- Validation in fixed CAD venv Python 3.11.18: `py_compile` passed; RET-004 + conditions/retry/retrieval **82/82** passed; full LLM suite **945 passed, 8 existing skips**; Product Live/APP-004/UI/pipeline/schema integration **253/253** passed. `git diff --check` and commit check passed.
- State remains `review`; candidate batch absent and unconsumed. No formal preflight, credential/`.env` read, network/model request, live runner, or RET-004 CAD/STEP execution. Offline results remain preparation evidence only, not retrieval-effect evidence.
- Fix commit: `36926de` (`fix: close RET-004 review findings [RET-004-PAIRED-LIVE-20261116-01]`), parent `a87734c`; branch has not been pushed or merged.

## Summary confirmation-status narrow fix

- Scope: make per-run `confirmation_status` truthful after an R01 confirmation. Initial planned rows are `not_started`; extracted R01 rows are `pending`; confirmed/declined R01 rows are recorded as `confirmed`/`declined`; R02 remains `denied_by_scope`.
- Changes: `_planned_run_records()` now includes the initial confirmation state; `_record_state()` checks the service confirmation registry before the extraction status, so a successful CAD result or an explicit decline cannot be overwritten as `pending`.
- Regression coverage: added assertions for pending, denied-by-scope, declined, and confirmed states in `tests/integration/test_ret004_paired_runner.py`.
- Validation (fixed CAD venv Python 3.11.18): targeted RET-004 suite **24/24**, conditions/retry/retrieval **59/59**, affected Product Live/APP-004/UI/pipeline/schema-to-IR **253/253**; `py_compile` and `git diff --check` pass. Initial test run exposed and fixed the status-precedence case before commit.
- Boundary: no scope/hash/input changes; no preflight, batch/ledger, credential read, network/model request, or CAD/STEP execution. `FORMAL_EVALUATION_ALLOWED=False` unchanged. Candidate remains `review` pending independent read-only review.

## Owner scope acceptance and preflight gate

- Owner acceptance: `approver=Wang sikai`; `approved_at_utc=2026-11-16T13:20:20Z`; `approval_record_ref=conversation:RET-004-PAIRED-LIVE-20261116-01-scope-acceptance`.
- Accepted binding: profile `ret004-paired-live.v1`, batch candidate `ret004-paired-live-20261116-01`, the frozen inputs/labels/prompt/contract/RET-001 manifest/RET-002 config hashes recorded above, DeepSeek `deepseek-flash`, C0/C1, four logical runs, maximum eight HTTP attempts.
- Review status: independent read-only review is `pass` at `c212e03`; the scope is accepted, but no formal preflight or live execution has occurred.
- Next gate: run `run_ret004_offline_preflight()` in the fixed CAD venv. This gate must not read credentials, create a batch/ledger, call the network, or run CAD; only a passing preflight permits requesting separate exact-batch live approval.

## Formal preflight result

- Command: `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -c 'from integration.ret004_paired_runner import run_ret004_offline_preflight; ...'`.
- Result: `ok=true`; all bound artifact hashes match; `batch_dir_exists=false`; planned runs `4`; max attempts per run `2`; max batch HTTP `8`; `evaluator_labels_read=false`; `evaluator_labels_sha256_bound=true`; `formal_evaluation_allowed=false`.
- CAD runtime: `cadquery=2.3.0`, `ocp=7.9.3.0`, `jsonschema=4.26.0`, draft 2020-12 supported.
- Boundary: preflight did not load credentials, create batch/ledger/raw directories, call network/model, or run CAD/STEP. Exact-batch live execution remains separately unauthorized until the owner approves it.

## Authorized live extraction result

- Authorization: owner approved the exact batch in this conversation at `2026-11-16T13:25:00Z`; approval bound to `ret004-paired-live-20261116-01`, DeepSeek `deepseek-flash`, C0/C1, 4 logical runs, and max 8 HTTP attempts.
- Execution: formal runner completed 4 physical HTTP requests (one attempt per logical run). The batch summary is `awaiting_confirmation`; no `pipeline-runs` or STEP files were created.
- R01 C0/C1: both returned `decision=answer`, `bore_d=24`, no errors, and `product_status=needs_confirmation`; each remains independently `confirmation_status=pending`. C1 recorded the same retrieval context hash and three retrieval-source candidate IDs.
- R02 C0/C1: both returned `decision=refuse`, represented the unsupported anodizing request, and were forced to `product_status=blocked` with `GATE_DECISION_REFUSE` and `SCOPE_CAD_DENIED`; both remain `confirmation_status=denied_by_scope`.
- Retention: four raw response files and the budget ledger exist under the approved batch directory; summary contains repo-relative raw paths and hashes only. Raw response bodies were not read or copied into project records.
- Next gate: owner must separately confirm R01 C0 and/or R01 C1 after reviewing their extracted results before either condition may enter CAD. R02 cannot enter CAD.

## Owner-confirmed R01 CAD execution and closeout checkpoint

- Authorization: the owner separately confirmed R01 C0 and R01 C1 for CAD after the live extraction results; the R02 CAD-deny remains in force. This closeout records the already completed runs and did not repeat model or CAD execution.
- Batch result: `work/app001-runs/ret004-paired-live-20261116-01/batch_summary.json` reports `batch_status=complete`, four planned runs, and terminal states for all four. R01 C0/C1 each have `decision=answer`, `bore_d=24`, `confirmation_status=confirmed`, `product_status=succeeded`, and `pipeline_status=success`. R02 C0/C1 each have `decision=refuse`, unsupported `anodizing`, `product_status=blocked`, and `confirmation_status=denied_by_scope`; neither has a pipeline or STEP hash.
- Budget and retention: the ledger records 4 claimed/completed HTTP attempts across four logical runs against the approved batch cap of 8. Four raw files remain present; their paths and SHA-256 values are recorded in the summary. This check read only summary/ledger metadata and file names, not raw response bodies.
- CAD evidence: both R01 pipeline summaries report `status=success`, `stage=step_readback`, and no errors. For C0, summary SHA-256 `831a569efad97a779e7fa3abcfa962cdc54a2cebed5e9fd5e8d75ce1f7c8ad01` matches its pipeline index and STEP bytes. For C1, summary SHA-256 `2e1246ec22cfcc0b9642363eff8180ecc9d1be04c0463a6006fe3befb7ebbfee` matches its pipeline index and STEP bytes. Each STEP is 148,393 bytes. R02 has no pipeline directory or STEP artifact.
- Recovery limitation for independent review: the runner has no supported cross-process resume API for pending confirmations. The prior execution reconstructed an ephemeral `RET004PairedService` with `__new__` from summary state, then called the existing confirmation method after checking the binding/result evidence. This was not a persisted recovery interface; review the reconstruction and confirmation binding carefully. No recovery API was added in this closeout.
- Verification: a read-only Python standard-library audit inspected the batch summary, ledger, pipeline summaries/indexes, and STEP file hashes. It confirmed four ledger attempts, `complete`, two successful `step_readback` runs, exact summary/index/file hash agreement, and no R02 CAD artifacts. `git diff --check` passed before the documentation closeout commit.
- Boundaries: no new HTTP request, credential read, preflight, or batch mutation occurred during closeout. No raw body or evaluator labels were read. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged. This two-input paired result is descriptive evidence only; it does not establish statistical retrieval benefit, broad language generalization, production readiness, or manufacturing certification.
- Result: both owner-confirmed R01 conditions completed CAD/STEP readback; R02 remained permanently denied by scope. Independent read-only closeout review returned `pass`, and the closeout is merged into local `main`.
- Next gate: no further RET-004 execution is required. Any future retrieval study must use a new scope, preflight, batch, and authorization. Do not rerun or modify this historical batch.
