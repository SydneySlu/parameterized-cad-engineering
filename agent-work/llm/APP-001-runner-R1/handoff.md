# APP-001-RUNNER-R1 handoff

Date: 2026-11-06
Task: APP-001-RUNNER-R1
Status: review
Predecessor commit: 7cd8369 (APP-001-RUNNER-001)
Work root: /Users/syd/Desktop/参数化 cad 工程辅助设计

## Self-check

```text
handoff_self_check:
  changed=
    src/llm/contract.py          (added ACCEPTANCE_SET_SHA256 constant)
    src/llm/conditions.py        (full rewrite: extract_bore_d_mm, no fixed bore_d=20)
    src/llm/budget.py            (added BudgetAwareTransport class)
    src/llm/runner.py            (use BudgetAwareTransport, enforce SHA-256, fail-closed on interrupted runs)
    src/llm/real_transport.py    (strict digest prefix check, actual-value recording)
    src/llm/adapter.py           (record actual local digest from usage field)
    tests/llm/test_runner_r1.py  (new, 40 tests covering all 4 fixes)
    agent-work/llm/APP-001-runner-R1/checkpoint.md (this session's checkpoint)
    agent-work/llm/APP-001-runner-R1/handoff.md (this file)
    docs/WORKLOG.md (appended)

  commands=
    PYTHONPATH=src python3 -m py_compile src/llm/{contract,conditions,budget,runner,real_transport,adapter}.py tests/llm/test_runner_r1.py → OK
    PYTHONPATH=src python3 -m unittest tests.llm.test_runner_r1 → 40 tests OK
    PYTHONPATH=src python3 -m unittest discover -s tests/llm → 316 tests OK (skipped=1)
    PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar → 17 tests OK
    git diff --check → OK
    secret scan (DEEPSEEK_API_KEY=) → no hardcoded keys
    work/app001-runs/ confirmed git-ignored (.gitignore:40 work/)

  confirmed=
    ACCEPTANCE_SET_SHA256 constant matches actual file (sha256sum verified)
    _load_projection() passes SHA-256; tampered NLI/query_id/evaluator fields all rejected
    BudgetAwareTransport reserves one slot per send(); 2 reservations for 1 retry + success
    108th request allowed; 109th refused before FakeTransport.send() is called
    Provider 54-limit and per-run 3-limit enforced before any network call
    C1 no longer uses fixed bore_d=20; blocks with C1_NO_SAFE_QUERY_PARAMETER when NLI lacks bore_d
    bore_d extraction: "bore_d=24 mm", "1.6 cm → 16 mm", "轴孔直径 20 mm", A08-structural-ref
    Ollama digest: strict startswith(); contains-but-not-prefix rejected; missing digest rejected
    Actual digest recorded from /api/show, not from frozen constant
    DeepSeekTransport has no _actual_digest or _verified_digest attributes
    All 316 tests pass; no formal network calls; FORMAL_EVALUATION_ALLOWED=False

  unresolved=
    - Python 3.11.18 not directly accessible in Linux sandbox (macOS venv symlink broken); tests run under 3.10.12
    - C1 blocked for A04/A07/A09 (no parseable bore_d in NLI) — correct per spec; Codex hub to confirm behavior is acceptable
    - Interrupted-run fail-closed marks `interrupted_fail_closed`; recovery mechanism not implemented (fail-closed is safe)
    - Ollama digest verification tests use monkey-patched functions, not live Ollama
    - TOCTOU in prompt_loader.py persists (inherited from R3)

  next_agent_focus=
    Codex hub: verify SHA-256 enforcement, per-attempt budget counting, C1 bore_d extraction accuracy,
    Ollama strict digest, no evaluator label leakage, no network calls, 316/316 pass.
    Confirm C1-blocked behavior for A04/A07/A09 is acceptable for Phase 1.
    After this review, project owner can authorize formal APP-001 run.
```

## Summary of what changed vs R1 baseline

| Module | Change |
|---|---|
| `contract.py` | +`ACCEPTANCE_SET_SHA256` constant |
| `conditions.py` | Full rewrite: `extract_bore_d_mm()`, no fixed bore_d=20, blocks C1 when NLI lacks bore_d |
| `budget.py` | +`BudgetAwareTransport`: per-send() atomic reservation |
| `runner.py` | Uses BudgetAwareTransport; enforces SHA-256; fail-closed on incomplete reservations |
| `real_transport.py` | Strict startswith() digest check; actual digest/model_name recording |
| `adapter.py` | Records actual local digest from usage field, not frozen constant |
| `test_runner_r1.py` | 40 new tests covering all 4 fixes |

## Formal evaluation not run

No formal 9-case evaluation was run during this task. No real DeepSeek or Ollama requests were made. No model quality, latency, or cost results exist. All formal metrics remain `not_measured`.
