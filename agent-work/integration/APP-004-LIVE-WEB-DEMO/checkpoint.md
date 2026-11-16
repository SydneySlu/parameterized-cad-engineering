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
