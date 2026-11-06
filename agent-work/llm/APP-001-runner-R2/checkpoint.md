# APP-001-RUNNER-R2 checkpoint

task=APP-001-RUNNER-R2
status=review
work_root=/Users/syd/Desktop/参数化 cad 工程辅助设计
predecessor_commit=f64d08a (APP-001-RUNNER-R1)
date=2026-11-06
agent=Codex

## Scope

Close the two blocking findings from the independent R1 review:
1. Prevent a caller from using a bare FormalRunAuthorization with an arbitrary transport to bypass the physical-attempt budget ledger.
2. Require exact Ollama model identity `qwen3:8b`, not a family/name substring match.

No real API/model requests were made. Formal run data was not generated.

## Changes

- `Adapter.run()` now accepts formal execution only through the exact `BudgetAwareTransport` type, and checks authorization identity, real inner transport, provider/model pair, query, condition and adapter run ID before prompt loading or transport send.
- `FormalRunAuthorization.provider_model_is_allowed()` now validates the two authorized provider/model pairs, not the Cartesian product of provider and model sets.
- `BudgetAwareTransport` is bound to its ledger authorization and exact real transport class/provider/model; it validates condition and canonical logical run ID and reports binding metadata to the Adapter.
- `BudgetLedger.reserve_attempt()` now enforces the frozen 36 logical-run maximum in addition to 3-per-run, 54-per-provider and 108-total attempt caps.
- `OllamaTransport` now obtains installed model names and digests from `/api/tags`, requires exactly one `qwen3:8b` entry and the frozen digest prefix, and rejects a response whose runtime model is missing or differs from `qwen3:8b`.
- `src/llm/README.md` reflects the current narrow ADR-0014 authorization path and review status.
- Added boundary regression tests in `tests/llm/test_runner_r1.py`.

## Verification

Python: `/opt/homebrew/Cellar/python@3.11/3.11.18/Frameworks/Python.framework/Versions/3.11/bin/python3.11` (3.11.18)

- `PYTHONPATH=src $PY311 -m unittest tests.llm.test_runner_r1` — 50 tests passed.
- `PYTHONPATH=src $PY311 -m unittest discover -s tests/llm` — 326 tests passed, 1 skipped.
- `PYTHONPATH=src $PY311 -m unittest tests.schema.test_set_screw_shaft_collar` — 17 tests passed.
- `PYTHONPATH=src $PY311 -m py_compile src/llm/{authorization,budget,runner,adapter,real_transport}.py tests/llm/test_runner_r1.py` — passed.
- `git diff --check` — passed.
- Regression cases verify bare custom transport, FakeTransport wrapped as formal, crossed provider/model, wrong run binding, wrong Ollama tag (`qwen3:14b`), family-only name, duplicate exact entries, missing digest and wrong chat response model all reject before an unauthorized model request.

## Limits

- Live Ollama `/api/tags` and `/api/chat` identity verification has not been run; it remains for the authorized formal environment.
- No formal APP-001 run or real DeepSeek request was made.
- `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.
- APP-001 remains planned pending independent review of this repair and the full controlled runner.

## Commit

- `ecc3163` — `fix: bind APP-001 runs to budget ledger [APP-001-RUNNER-R2]`
- Status remains `review`; not pushed.
