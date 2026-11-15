# APP-004-LIVE-WEB-DEMO checkpoint

- Date: 2026-11-16
- Status: `in_progress` — scope proposal milestone
- Branch: `codex/APP-004-LIVE-WEB-DEMO`
- Base: `d0355c05652885ed0dc15b6d868c9d0e801524bb`
- Goal: prepare a tightly scoped real-LLM localhost web demo; no live execution in this milestone.

## Current milestone

Proposed two-input profile: supported bore24 success candidate and collar-plus-anodizing boundary challenge. DeepSeek `deepseek-flash`, C0, no retrieval, max 2 attempts per input / 4 HTTP total. Only D01 can be CAD-eligible, and only after explicit per-run confirmation; D02 is hard-denied from CAD regardless of model output.

## Handoff self-check

```text
changed=agent-work/integration/APP-004-LIVE-WEB-DEMO/{scope.md,model-inputs.json,evaluator-labels.json,checkpoint.md}; proposed ADR-0026; PROJECT_STATUS/PROJECT_PLAN/WORKLOG entries
commands=Python JSON/ID/separation/hash check PASS (inputs 4c97a043e1547831fd92f3f7a95ba65b6ea6734b073f2ce9687454143ed65841; labels 4eff6146ee2b1809a9720407eceb605257340204fbca409a2c35e94295c5e091); git diff --check PASS; proposed batch output directory absent PASS
confirmed=main and origin/main were both d0355c05652885ed0dc15b6d868c9d0e801524bb; worktree clean before branch creation; current ProductLiveService is FakeTransport-only; formal ProductLive batch runner has a separate approval-bound live path; APP-003 next-language runner is offline-only under ADR-0025
unresolved=scope owner acceptance; implementation and independent review; fixed-CAD/browser validation
next_agent_focus=after scope acceptance, implement the smallest scope-bound localhost live entry without changing global formal gate or old profiles/batches; prove zero side effects before approval/preflight and D02 can never call CAD
```

## Not done in this milestone

- No source code or web route changes yet.
- No batch directory, ledger, or formal preflight created/run.
- No credentials or `.env` read; no model/network/CAD/STEP execution.
- `FORMAL_EVALUATION_ALLOWED=False` unchanged.
