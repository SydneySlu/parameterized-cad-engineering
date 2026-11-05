# APP-001-RUNNER-001 checkpoint

task=APP-001-RUNNER-001
status=review
work_root=/Users/syd/Desktop/参数化 cad 工程辅助设计
formal_evaluation_gate=false (FORMAL_EVALUATION_ALLOWED unchanged in contract.py)
date=2026-11-06
agent=CC

## Scope and authorization

Per project-owner authorization, Phase 1 runner implemented for:
- 9 frozen acceptance cases × 2 conditions (C0/C1) × 2 models = 36 logical runs
- DeepSeek `deepseek-flash`, Ollama `qwen3:8b`
- Max 3 attempts/run, max 108 batch attempts, max 54/provider
- IR/CAD/geometry/STEP explicitly disabled (not_run/blocked)
- No formal evaluation executed; no real DeepSeek/Ollama calls made

## Delivered files

### Production code (src/llm/)
- `authorization.py` — FormalRunAuthorization scope-validated dataclass + authorize_phase1_run() factory
- `budget.py` — Atomic file-based budget ledger with lock, restart recovery, integrity checks
- `combinations.py` — Deterministic 36-combination generator, dry-run audit output (no eval labels)
- `conditions.py` — C0 (no retrieval) and C1 (RET-002) input assembly with evaluator-label isolation
- `real_transport.py` — DeepSeekTransport, OllamaTransport; key read only in send(), never stored
- `input_projection.py` — Strict allowlist projection of acceptance-set-v0 (evaluator fields stripped)
- `runner.py` — App001Runner with dry_run() and run_formal() entry points
- `adapter.py` — Modified: added optional formal_authorization param to Adapter.run()

### Tests (tests/llm/)
- `test_authorization.py` — 18 tests: scope construction + all rejection cases
- `test_budget.py` — 18 tests: basic counts, exhaustion, recovery, integrity, concurrency
- `test_runner.py` — 70 tests: all 12 required scenarios + provider isolation + input isolation

### Documentation
- `docs/DECISIONS.md` — ADR-0014 appended (narrow-scope Phase 1 authorization path)
- `agent-work/llm/APP-001-runner/checkpoint.md` (this file)
- `agent-work/llm/APP-001-runner/handoff.md`
- `docs/WORKLOG.md` — entry appended

## Verification commands and results

```
PYTHONPATH=src python3 -m py_compile src/llm/authorization.py src/llm/budget.py src/llm/combinations.py src/llm/conditions.py src/llm/real_transport.py src/llm/input_projection.py src/llm/runner.py src/llm/adapter.py tests/llm/test_authorization.py tests/llm/test_budget.py tests/llm/test_runner.py
→ OK (no errors)

PYTHONPATH=src python3 -m unittest tests.llm.test_runner tests.llm.test_authorization tests.llm.test_budget
→ Ran 106 tests, OK (skipped=1: environment symlink FUSE limitation, same as pre-existing suite)

PYTHONPATH=src python3 -m unittest discover -s tests/llm
→ Ran 276 tests, FAILED (errors=2, skipped=1)
  - 2 errors: test_r3_regression.RetentionBypassRemovedTests symlink tests (pre-existing FUSE environment issue, documented in prior WORKLOG)
  - My new 106 tests: 105 pass + 1 env-skip
  - Original 170 tests: same result as before my changes

PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar
→ 17 tests, OK (no regressions)

git diff --check → OK
```

## Normal case verification

```python
# dry_run() generates 36 combinations, returns plan with no evaluator labels
runner = App001Runner(acceptance_set_path="agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json")
summary = runner.dry_run()
# summary.planned_runs == 36
# summary.mode == "dry_run"
# summary.formal_evaluation_allowed == False
# "explicit_parameter_claims" not in json.dumps(summary.dry_run_plan)
```

## Failure case verification

```python
# Wrong scope rejected before any network call
from src.llm.authorization import _valid_kwargs, FormalRunAuthorization, AuthorizationScopeError
try:
    FormalRunAuthorization(**_valid_kwargs(conditions=frozenset({"C0", "C1", "C2"})))
    assert False, "should have raised"
except AuthorizationScopeError:
    pass  # correct

# No authorization + non-FakeTransport → fail-closed
from src.llm.gate import FormalEvaluationBlockedError
from src.llm.adapter import Adapter
from src.llm.transport import MockTransport
class CustomMock(MockTransport):
    def send(self, r): raise AssertionError("should not be called")
try:
    adapter = Adapter(provider="DeepSeek", transport=CustomMock())
    adapter.run(_frozen_input(), run_id="test", formal_authorization=None)
    assert False, "should have raised"
except FormalEvaluationBlockedError:
    pass  # correct
```

## Known limits and unresolved items

- Formal 9-case evaluation NOT run; no real API calls; no performance metrics.
- `FORMAL_EVALUATION_ALLOWED = False` unchanged; unchanged by this ADR.
- Real transport classes (DeepSeekTransport, OllamaTransport) not tested with real network.
- Runner's per-attempt retry loop delegates to existing Adapter.run() which uses send_with_retry internally. The budget ledger reserves one slot per `Adapter.run()` call (not per internal attempt). To budget per internal attempt, the runner would need to intercept each retry. This is a known design gap — the current implementation reserves the full run budget upfront and records outcome after. The budget still prevents exceeding the total batch/provider limits.
- C1 reference context assembly is blocked when no retrieval_index is provided (runner passes None by default).
- ADR-0014 does not authorize running the 9 frozen cases; it only establishes the legal authorization path.
- Codex hub independent review required before formal run authorization.

## Status

APP-001-RUNNER-001: review
APP-001: planned (formal evaluation NOT authorized yet)
APP-001-PREP: done
APP-001-ADAPTER: done
FORMAL_EVALUATION_ALLOWED: False (unchanged)
