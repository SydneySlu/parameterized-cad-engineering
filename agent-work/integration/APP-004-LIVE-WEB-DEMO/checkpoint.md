# APP-004-LIVE-WEB-DEMO checkpoint

- Date: 2026-11-16
- Status: `review` — implementation candidate; independent code review pending
- Branch: `codex/APP-004-LIVE-WEB-DEMO`
- Base: `d0355c05652885ed0dc15b6d868c9d0e801524bb`
- Goal: prepare a tightly scoped real-LLM localhost web demo; implementation and FakeTransport browser verification are complete, while formal/live execution remains unauthorized.

## Accepted scope

Proposed two-input profile: supported bore24 success candidate and collar-plus-anodizing boundary challenge. DeepSeek `deepseek-flash`, C0, no retrieval, max 2 attempts per input / 4 HTTP total. Only D01 can be CAD-eligible, and only after explicit per-run confirmation; D02 is hard-denied from CAD regardless of model output.

## Handoff self-check

```text
changed=agent-work/integration/APP-004-LIVE-WEB-DEMO/{scope.md,model-inputs.json,evaluator-labels.json,checkpoint.md}; proposed ADR-0026; PROJECT_STATUS/PROJECT_PLAN/WORKLOG entries
commands=Python JSON/ID/separation/hash check PASS (inputs 4c97a043e1547831fd92f3f7a95ba65b6ea6734b073f2ce9687454143ed65841; labels 4eff6146ee2b1809a9720407eceb605257340204fbca409a2c35e94295c5e091); git diff --check PASS; proposed batch output directory absent PASS
confirmed=main and origin/main were both d0355c05652885ed0dc15b6d868c9d0e801524bb; worktree clean before branch creation; current ProductLiveService is FakeTransport-only; formal ProductLive batch runner has a separate approval-bound live path; APP-003 next-language runner is offline-only under ADR-0025
unresolved=scope owner acceptance; implementation and independent review; fixed-CAD/browser validation
next_agent_focus=after scope acceptance, implement the smallest scope-bound localhost live entry without changing global formal gate or old profiles/batches; prove zero side effects before approval/preflight and D02 can never call CAD
```

## Scope proposal boundary (historical checkpoint)

- No source code or web route changes yet.
- No batch directory, ledger, or formal preflight created/run.
- No credentials or `.env` read; no model/network/CAD/STEP execution.
- `FORMAL_EVALUATION_ALLOWED=False` unchanged.

The owner subsequently accepted and froze the scope recorded in ADR-0026. This acceptance did not authorize formal preflight or a live request.

## Implementation milestone — 2026-11-16

- Owner accepted/froze ADR-0026 scope. This does not authorize formal preflight or live requests.
- Branch/base: `codex/APP-004-LIVE-WEB-DEMO`, base commit `ff3a00d7d65e05197767bfc1766629a7471809f0`; implementation edits are uncommitted at this checkpoint.
- Added `src/llm/app004_live_web_authorization.py`, `src/integration/app004_live_web_runner.py`, and `tests/integration/test_app004_live_web.py`; extended `src/demo/server.py` with `/app004-live` and `/api/app004-live/*` routes.
- Scope is bound to D01/D02 and frozen hashes, DeepSeek `deepseek-flash`/C0, max 2 logical inputs × 2 attempts = 4 HTTP. Browser submits only frozen input ID. D01 requires valid extraction plus explicit confirmation; D02 is always blocked from CAD.
- Independent review during implementation found and corrected approval binding that only compared batch ID; execution-time validation now rechecks full profile/hash/provider/model/condition/budget/CAD fields and exact approval type before preflight or credential loading.
- Download validation now permits only the current service's canonical output root (formal batch root or isolated offline root), rejects symlink leaf and escapes, and verifies STEP SHA-256. Clean shutdown records `partial` if a frozen input was not run.
- Independent review identified two gaps, now addressed in the narrow fix below: prompt/contract hashes are fixed anchors carried by both authorization and approval and recomputed during preflight; free-form approval statement/reference are represented in summary only by SHA-256 fingerprints.
- Fixed CAD venv Python 3.11.18 checks: target `py_compile` passed; `tests.integration.test_app004_live_web` 19/19 passed before final shutdown assertions were added; initial Product Live + UI compatibility run 145/145 passed. Re-run after the final two tests is pending.
- Browser smoke at `http://127.0.0.1:8765/app004-live` with FakeTransport: D01 showed `needs_confirmation`, explicit confirmation generated STEP with SHA-256 `4e60bf23d765e6db991ea0c70e5308a8091c29ab3d4d9bfb2dec2c45eeb2035f`, download endpoint returned HTTP 200; D02 showed `blocked / answer`, `SCOPE_CAD_DENIED`, and no confirmation button. No real model request was sent.
- Not run: formal preflight, `.env`/credential loading, DeepSeek/network, real batch creation, evaluator-label reads, or formal CAD output. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.
- Next: independent review of the committed implementation candidate; apply only review-driven narrow fixes. Any formal preflight/live request needs separate exact-batch owner authorization.

### Verification follow-up — 2026-11-16

- Fixed CAD venv Python 3.11.18: target `py_compile` PASS; `tests.integration.test_app004_live_web` **22/22 PASS**; `tests.integration.test_product_live tests.demo.test_product_live_ui` **145/145 PASS**; `git diff --check` PASS.
- Approval mutation tests now cover all approval scope fields and mutated authorization hashes; both fail before offline preflight and credential loading.
- Secure download tests cover in-root bytes/hash success, outside-root rejection, and symlink-leaf rejection. Shutdown tests prove an unrun input finalizes as `partial` while both input IDs permit `complete`.
- Browser FakeTransport smoke confirmed D01 STEP response/download and D02 blocked UI. Local test server was stopped after verification.
- Broader fixed-environment regression after final changes: `tests.demo.test_demo_handler tests.demo.test_product_flow tests.demo.test_product_ui` **183/183 PASS**; `tests.integration.test_pipeline tests.integration.test_schema_to_ir tests.schema` **81/81 PASS**. Existing ResourceWarnings concern file/socket handles in legacy tests and did not cause failures.

### Candidate handoff — 2026-11-16

- Commit: `173636b` (`feat: add scoped live web demo [APP-004-LIVE-WEB-DEMO]`); branch `codex/APP-004-LIVE-WEB-DEMO`; implementation candidate is committed.
- Documentation reconciliation: scope file reflects accepted/frozen state and separates scope acceptance from execution authorization; checkpoint and project plan identify independent review as the next gate.
- Central review: target suite rerun in fixed CAD venv **22/22 PASS**; `py_compile` on the four changed Python files PASS; `git diff --check` and staged diff check PASS; frozen input/label hashes match scope.
- Current status: `review`; no formal preflight, batch/ledger creation, credential read, model/network call, or live CAD run. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.
- Next: independent read-only review of commit `173636b` against base `ff3a00d7d65e05197767bfc1766629a7471809f0`; only after a pass may the owner consider separate exact-batch execution authorization.

### Review fix — 2026-11-16

- Finding: predecessor review `review` found APP004 prompt hash derived from the runtime constant rather than an independent scope anchor, no contract hash binding, and unsanitized free-form approval fields in summary.
- Fix: bind fixed SHA-256 anchors for frozen prompt-v5 and `src/llm/contract.py` into authorization and approval validation; preflight hashes both canonical files. Summary stores only hashes of approval statement/reference, never their raw values. Scope records both anchors.
- Verification: `tests.integration.test_app004_live_web` **25/25 PASS**; target `py_compile` PASS. Additional compatibility/full suite reruns pending.
- Follow-up fixed-environment regression: Product Live/UI **145/145**, C1/C2/C3 demo **183/183**, pipeline/schema **81/81**; target compilation and diff checks pass. Existing ResourceWarnings are in legacy tests and did not fail.
- Status: `review`; no formal preflight, batch creation, credentials, network, model or live CAD use. `FORMAL_EVALUATION_ALLOWED=False` unchanged.
- Narrow-fix commit: `0addfc2` (`fix: bind APP-004 artifacts and sanitize approval audit [APP-004-LIVE-WEB-DEMO]`).
- Next: request an independent read-only re-review of `173636b..0addfc2`.

### Approval mutation gate fix — 2026-11-16

- Finding: independent review of `ed629822000f13c6495c3c5d3ba982f64167c997` found that `validate_app004_approval_binding()` did not revalidate `approval_record_ref` and other free approval fields after low-level mutation. A malformed approval could pass the gate and fail later during summary generation, after preflight, credential loading, and batch/ledger setup.
- Fix: the execution gate now reruns all `App004LiveWebApproval` constructor invariants before preflight. It strictly checks exact types for frozen scope fields, optional `approval_record_ref`, and boolean `is_test_only`; malformed approval fields are rejected with `App004ApprovalValidationError` before side effects.
- Regression: new test mutates `approval_record_ref`, `approver`, timestamp, statement, and `is_test_only`; each case asserts preflight, credential loader, `Path.mkdir`, and `BudgetLedger` are never called.
- Verification in fixed CAD venv Python 3.11.18: target `py_compile` PASS; `tests.integration.test_app004_live_web` **26/26 PASS**; Product Live/UI **145/145 PASS**; C1/C2/C3 demo **183/183 PASS**; pipeline/schema **81/81 PASS**; `git diff --check` PASS. Existing ResourceWarnings appeared in compatibility suites; no test failures.
- Boundaries: no formal preflight, batch/ledger creation, `.env` or credential read, evaluator-label content read, DeepSeek/network request, or real CAD execution. `FORMAL_EVALUATION_ALLOWED=False` unchanged.
- Status: `review`; this fix awaits independent read-only review. Any formal execution remains subject to separate exact-batch owner authorization.
- Implementation commit: `2451a47` (`fix: revalidate APP-004 approval at execution gate [APP-004-LIVE-WEB-DEMO]`).

### Approval string-subclass hardening — 2026-11-16

- Review follow-up: a `str` subclass overriding `strip()` and `encode()` could pass the prior `isinstance(..., str)` check, then raise during approval audit hashing. This was reproduced without invoking the formal runner.
- Fix: constructor and execution-gate checks now require exact `str` for `approver`, `approved_at_utc`, and `approval_statement`. Regression uses a malicious `str` subclass and verifies `prepare_formal()` rejects it before preflight, credential loading, directory creation, or ledger initialization.
- Verification in fixed CAD venv Python 3.11.18: target `py_compile` PASS; APP-004 **26/26 PASS**; Product Live/UI **145/145 PASS**; C1/C2/C3 demo **183/183 PASS**; pipeline/schema **81/81 PASS**; `git diff --check` PASS. Existing compatibility `ResourceWarning`s appeared without failures.
- No formal preflight, batch/ledger creation, credential/evaluator-label read, network/model call, or real CAD execution; `FORMAL_EVALUATION_ALLOWED=False` unchanged. Status remains `review`, pending independent re-review.
- Code commit: `58382d5` (`fix: reject APP-004 approval string subclasses [APP-004-LIVE-WEB-DEMO]`).

### Approved live batch closeout — 2026-11-16

- Authorized batch: `app004-live-web-demo-20261116-01`; profile `app004-live-web-demo.v1`; DeepSeek `deepseek-flash` / C0 / no retrieval; frozen inputs D01 and D02 only; per-input maximum 2 HTTP, batch maximum 4 HTTP. Formal preflight passed before execution; runtime was Python 3.11.18, CadQuery 2.3.0, OCP 7.9.3.0, jsonschema 4.26.0. `FORMAL_EVALUATION_ALLOWED=False` remained unchanged.
- D01 `D01-collar-bore24`: one HTTP attempt; model returned `answer`, `bore_d=24`, no missing/unsupported fields or diagnostics. Following the owner's explicit follow-up instruction to advance D01, the existing run's confirmation endpoint was invoked once. CAD/IR/STEP pipeline succeeded at `step_readback`; run ID `5bcdb6ff-b2c6-4991-a3a5-d3a595fccc4c`; STEP is `work/app001-runs/app004-live-web-demo-20261116-01/pipeline-runs/5bcdb6ff-b2c6-4991-a3a5-d3a595fccc4c/cad_output/8daf31d3c7880ea1.step`, 148393 bytes, SHA-256 `e0f23e1a16885e97f153b7d12fafafa0d18da6e7ac039c877841a5fbfdfd1fe7`. Hash and size matched the service response. FreeCAD 1.1.4 opened and displayed the STEP model.
- D02 `D02-collar-anodizing`: one HTTP attempt; model returned `refuse`, `bore_d=24`, unsupported `anodizing`; product status `blocked`, error code `GATE_DECISION_REFUSE`; no CAD or STEP.
- Budget ledger records 2 chat attempts total (DeepSeek 2; D01 1, D02 1), within 2/input and 4/batch limits. No retries or extra model requests were made. Both raw files exist and were hash-checked without reading their contents: D01 SHA-256 `ea65f31d782e23be413f577c5c1a87bfc9c4d62112c3e2d59f2d9c3e25ee107f`; D02 SHA-256 `c53a9ee292ad047c6d7e1ddf3e8a42605d4509a718da9c84b344063826cd6a04`.
- Service timeout diagnosis: synchronous `HTTPServer` was blocked reading an incomplete request from a Codex network-service connection; the browser and curl waited behind the single request handler. After the user ended the stuck network-service process, the existing server resumed and served read-only GETs. No formal service restart or batch recreation occurred. Normal server shutdown finalized summary at `2026-11-16T07:21:04Z`, `batch_status=complete`, then released the ledger lock.
- Closeout discrepancy: the final summary records D01 `succeeded`, pipeline `success`, and STEP hash, but D01's `raw_retained`, `raw_retention_path`, and `raw_sha256` fields are null/missing even though the D01 raw file exists with the hash above. D02 summary path/hash agrees with its raw file. This record mismatch is left visible for follow-up; no summary or raw file was rewritten, and no raw body was read. Batch outcome is technically complete, but APP-004 remains `review` until this audit-record discrepancy is assessed.
- Evidence boundary: exactly the two approved model calls and one D01 confirmation were performed; no D02 CAD, extra input/provider/model, retrieval, or automatic parameter correction. The run demonstrates a real natural-language→LLM extraction→existing single-family rules/IR/CAD→STEP vertical slice, not broad language quality, arbitrary CAD, second-family support, production readiness, or manufacturing certification.
- Next: assess/fix the D01 raw metadata summary loss without rewriting this historical batch; separately discuss project direction and whether a second family is worth prioritizing. Do not reuse this batch or issue additional model calls.

### D01 raw-retention summary follow-up — 2026-11-16

- Read-only diagnosis: extraction calls `_update_summary(state)` after assigning `raw_retention_meta` and `raw_retention_path`. For D01, confirmation calls `confirm_product_live_run()`, which returns a new `ProductLiveRunState` without copying those raw-retention fields; the subsequent `_update_summary(result)` overwrites the run's previously recorded path/hash/retained fields with null. D02 does not enter confirmation, so its raw metadata remains in summary. This matches the observed historical summary without reading either raw response body.
- Future-run fix: `App004LiveWebService.confirm()` now carries the extraction state's raw retention metadata and path onto the confirmation result before summary update. Added `test_confirmation_preserves_raw_retention_metadata_in_summary`, which injects metadata into an offline state and verifies the confirmed summary retains the repo-relative path, SHA-256, and retained flag; no CAD or network is invoked by the test.
- Validation on the fixed CAD venv: `py_compile` for the runner and test passed; `tests.integration.test_app004_live_web -q` **27/27 passed**; `git diff --check` passed.
- Historical boundary: the approved batch and its `batch_summary.json` remain untouched. D01 raw bytes still exist and their previously recorded SHA-256 remains evidence, but the historical summary's D01 path/hash/retained fields remain absent. No raw response content was read. No new preflight, batch, credential read, model/network request, or CAD run occurred; `FORMAL_EVALUATION_ALLOWED=False` remains.
- Status: `review`; future-run behavior is fixed, but historical audit metadata remains absent from the summary. The task still requires independent review and merge before `done`.
- Next: independent read-only review of this narrow fix; after merge, discuss project direction separately. Do not reuse the historical batch or issue extra requests.

### Regression test discrimination follow-up — 2026-11-16

- Independent review of commit `1ac9342` returned `review` because the new test used `dataclasses.replace(state, ...)`, which inherited raw fields and could pass without the production copy.
- Test correction: the mocked confirmation result now explicitly sets `raw_retention_meta=None` and `raw_retention_path=None`; the test asserts the precondition, then verifies `service.confirm()` restores the extraction metadata in the final summary. It covers both confirmed success and rejected confirmation, with the confirmation function mocked so no CAD executes.
- The production preservation remains intentionally applied to both outcomes because audit metadata describes the prior model response regardless of whether CAD confirmation is accepted.
- Next: rerun fixed-environment APP-004 tests and submit this correction for a fresh read-only review. Historical batch remains untouched and raw response bodies remain unread.

### Independent re-review — 2026-11-16

- Reviewer verdict: `pass` for `1ac9342920d3aea31c44d34f0f0eb89d3c0b4dff..3cda56ee8f8611cc259fc3e598ebc390723f7a13`; target branch/worktree were correct and clean.
- The reviewer confirmed the mocked confirmation result explicitly lacks both raw metadata fields and that both accepted and rejected confirmation paths preserve retained flag, hash, and path in final summary. `confirm_product_live_run()` was mocked; no CAD, batch, model, network, preflight, or raw-body read occurred.
- Fixed CAD venv Python 3.11.18: `py_compile` passed; `tests.integration.test_app004_live_web -q` **27/27 passed**; diff and commit checks passed.
- Scope/boundary: no authorization expansion; `FORMAL_EVALUATION_ALLOWED=False`. Historical batch remains untouched and its D01 summary metadata gap remains unresolved by design.
- Review status: `pass`; task remains `review` until branch commits are merged into `main`. Branch `codex/APP-004-LIVE-WEB-DEMO` is a fast-forward descendant of current `main` (`d0355c0`).
- Next: fast-forward merge into `main`; preserve historical batch read-only. After merge, mark this work unit done and discuss the project's next direction separately.
