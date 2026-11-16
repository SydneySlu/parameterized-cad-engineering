# RET-004 checkpoint

- Task: `RET-004-PAIRED-LIVE-20261116-01`
- Status: `in_progress` — candidate protocol and narrow C1 wording compatibility fix; no scope acceptance or live authorization yet.
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
