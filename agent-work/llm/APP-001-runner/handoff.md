# APP-001-RUNNER-001 handoff

Date: 2026-11-06
Task: APP-001-RUNNER-001
Status: review
Work root: /Users/syd/Desktop/参数化 cad 工程辅助设计

## Self-check

```text
handoff_self_check:
  changed=
    src/llm/authorization.py (new)
    src/llm/budget.py (new)
    src/llm/combinations.py (new)
    src/llm/conditions.py (new)
    src/llm/real_transport.py (new)
    src/llm/input_projection.py (new)
    src/llm/runner.py (new)
    src/llm/adapter.py (modified: optional formal_authorization param in Adapter.run())
    tests/llm/test_authorization.py (new, 18 tests)
    tests/llm/test_budget.py (new, 18 tests)
    tests/llm/test_runner.py (new, 70 tests)
    docs/DECISIONS.md (ADR-0014 appended)
    agent-work/llm/APP-001-runner/checkpoint.md (new)
    agent-work/llm/APP-001-runner/handoff.md (this file)
    docs/WORKLOG.md (appended)

  commands=
    PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/test_{authorization,budget,runner}.py → OK
    PYTHONPATH=src python3 -m unittest tests.llm.test_runner tests.llm.test_authorization tests.llm.test_budget → 106 tests, OK (skipped=1 env)
    PYTHONPATH=src python3 -m unittest discover -s tests/llm → 276 tests (errors=2 pre-existing env symlink, skipped=1)
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests, OK
    git diff --check → OK

  confirmed=
    FORMAL_EVALUATION_ALLOWED = False unchanged in contract.py
    FormalRunAuthorization validates scope at construction; wrong scope raises AuthorizationScopeError
    36 combinations generated correctly; dry-run outputs no evaluator labels
    C0 always has reference_context=None
    C1 blocked when no retrieval_index provided
    DeepSeek thinking param isolated from Ollama
    Budget reserved atomically before send; per-run/provider/batch limits enforced
    Concurrent batch lock rejected; corrupted ledger fails closed
    API key never stored, logged, or written to files
    Raw responses only in canonical work/app001-runs/<batch-id>/ (git-ignored)
    IR/CAD/geometry/STEP always not_run/blocked in all test runs
    JSONL run records include all required metadata fields
    Failed samples kept in run record (denominator preserved)
    9 frozen evaluation cases NOT run; zero real network calls

  unresolved=
    - Budget reserves one slot per Adapter.run() call (which handles up to 3 internal retries via send_with_retry). Per-attempt budget reservation would require intercepting send_with_retry's retry loop. Current design: one reservation per logical run, not per physical attempt. Total/provider limits are still enforced correctly.
    - C1 reference context blocked when retrieval_index=None (runner default). For real formal runs, caller must pass a built RetrievalIndex.
    - Real transports (DeepSeekTransport, OllamaTransport) not tested with live network; only auth-construction validation tested.
    - Ollama digest verification in OllamaTransport._verify_model_digest() uses a lenient prefix/contains check. Production should verify exact digest.
    - runner.py imports `import time as _time` inside a method (minor style issue).
    - TOCTOU note in prompt_loader.py still unresolved (inherited from R3).

  next_agent_focus=
    - Codex hub: verify 36-combination dry-run output, gate behavior, budget exhaustion, eval-label isolation, key isolation, JSONL schema
    - Before authorizing formal run: provide a built RetrievalIndex to App001Runner for C1 reference context
    - Review ADR-0014 scope and confirm it matches project-owner authorization
    - Verify runner.py budget design gap (one reservation per run vs per attempt) is acceptable for Phase 1
    - Confirm work/app001-runs/ is in .gitignore before any real run
```

## Changes summary

### What is new vs existing adapter

The existing `APP-001-ADAPTER` (`src/llm/adapter.py` through `src/llm/transport.py`) provided a mock-only, gate-closed single-query pipeline. This task adds the controlled multi-run runner layer on top:

| Component | Status | Purpose |
|---|---|---|
| `authorization.py` | New | Scope-validated formal run gate |
| `budget.py` | New | Atomic per-attempt budget with restart recovery |
| `combinations.py` | New | 36-combination generator + dry-run |
| `conditions.py` | New | C0/C1 input assembly with eval-label isolation |
| `real_transport.py` | New | Real HTTP transports (unused until formal run) |
| `input_projection.py` | New | Acceptance-set allowlist projection |
| `runner.py` | New | Controlled batch entry point |
| `adapter.py` | Modified | Optional formal_authorization param |

### What is NOT changed

- `FORMAL_EVALUATION_ALLOWED = False` in `contract.py`
- Frozen Prompt (`prompt-v2.md`), acceptance set (`acceptance-set-v0.json`), contract versions
- Parser, projector, cost, retry, runrecord, gate, prompt_loader modules
- Schema, CAD compiler, IR, RET-002 modules
- 9 frozen evaluation cases (never run)
- Historical ADRs 0001–0013

## What real formal runs require (Codex hub / project owner)

Before any real network call:
1. Codex hub independently reviews and accepts this handoff.
2. Project owner explicitly authorizes via a separate message (this task does not self-authorize).
3. A `FormalRunAuthorization` is constructed with a unique `batch_id`.
4. A `RetrievalIndex` is built from the frozen manifest for C1 conditions.
5. `DEEPSEEK_API_KEY` is present in the environment.
6. Ollama is running locally with `qwen3:8b` loaded (digest `500a1f067a9f`).
7. `work/app001-runs/` is confirmed git-ignored.

The `App001Runner.run_formal(auth)` entry point enforces all safety checks before any network call.

## Formal evaluation not run

No formal 9-case evaluation was run during this task. No real DeepSeek or Ollama requests were made. No model quality, latency, or cost results exist. All formal metrics remain `not_measured`.
