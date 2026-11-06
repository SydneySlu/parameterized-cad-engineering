# APP-001-RUNNER-R2 handoff

Date: 2026-11-06
Task: APP-001-RUNNER-R2
Status: review
Predecessor: `f64d08a` (`APP-001-RUNNER-R1`)
Work root: `/Users/syd/Desktop/参数化 cad 工程辅助设计`

## Self-check

```text
handoff_self_check:
  changed=
    src/llm/authorization.py
    src/llm/budget.py
    src/llm/runner.py
    src/llm/adapter.py
    src/llm/real_transport.py
    src/llm/README.md
    tests/llm/test_runner_r1.py
    agent-work/llm/APP-001-runner-R2/checkpoint.md
    agent-work/llm/APP-001-runner-R2/handoff.md
    docs/WORKLOG.md
  commands=
    Python 3.11.18: tests.llm.test_runner_r1 — 50 passed
    Python 3.11.18: discover -s tests/llm — 326 passed, 1 skipped
    Python 3.11.18: tests.schema.test_set_screw_shaft_collar — 17 passed
    Python 3.11.18: py_compile changed implementation/tests — passed
    git diff --check — passed
  confirmed=
    arbitrary direct transport plus FormalRunAuthorization is rejected before send
    FormalRunAuthorization accepts only DeepSeek/deepseek-flash and Ollama/qwen3:8b pairs
    formal Adapter checks exact budget wrapper and binds authorization, provider/model, query, condition and run ID
    budget ledger enforces 36 distinct logical runs as well as 3/54/108 attempt ceilings
    Ollama inventory requires one exact qwen3:8b tag and correct digest prefix
    Ollama chat response must return exact qwen3:8b model label
    formal_evaluation_allowed remains false; no model/API calls made
  unresolved=
    live Ollama runtime identity and real DeepSeek path not exercised
    Codex independent review remains required; no formal evaluation may start before review
  next_agent_focus=
    independently test direct Adapter bypass rejection and budget reservation on allowed formal wrapper
    inspect /api/tags name/digest assumptions against the installed Ollama version before formal run
    confirm batch logical-run cap, retry caps and no model call on all mismatch paths
```

## Result

The two R1 review blockers have code and regression coverage. This handoff does not mark APP-001 done or authorize a real run; it requests Codex hub review. No push was performed.
