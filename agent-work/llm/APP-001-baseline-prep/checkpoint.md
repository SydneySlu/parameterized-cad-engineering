# APP-001-PREP checkpoint

> Current authority (2026-11-05): protocol `app001-io.v1` / Prompt `app001-extraction.v2` and evaluator-only `acceptance-set-v0` are frozen by ADR-0013. Explicit model claims are separate from adapter-generated CAD-003 payloads. Adapter/logger implementation and review are complete; APP-001-PREP remains `review` pending this document status closeout and Codex final review. Formal runs still require separate project-owner authorization. Earlier M0-M3 sections below document historical preparation evidence.

```text
task=APP-001-PREP
status=review
work_root=/Users/syd/Desktop/参数化 cad 工程辅助设计
formal_evaluation_gate=false
changed=prompt-v1.md; acceptance-set-v0.json candidate-freeze metadata; model-baselines-v0.yaml; prompt-output-contract-v0.md; runtime-probe-2026-11-05.json; this checkpoint/handoff; PROJECT_STATUS/TASKS; append-only WORKLOG
```

## M0 environment and handoff successor check

- Git root is the requested project root; startup `git status --short --branch` was clean on `main...origin/main`.
- Runtime: Python 3.9.6; Darwin 25.6.0; arm64; Ollama CLI/API 0.33.2; Ollama service reachable at `127.0.0.1:11434`.
- `ollama list` reports `qwen3:8b` ID `500a1f067a9f`, matching the frozen local tag/digest. `/api/show` reports family `qwen3`, 8.2B, Q4_K_M and a template.
- Root `.env` exists and `DEEPSEEK_API_KEY` is present only as an existence check; the value was never printed, copied, logged, or committed. `git check-ignore -v .env` passes and `.env` is absent from the index.
- Normal CAD-003 case: strict envelope with `bore_d=24` passed and normalized catalog fields. Failure case: strict envelope without `bore_d` returned `MISSING_REQUIRED`; no default was supplied.

## M1 DeepSeek seed capability

- Official Chat Completions page checked 2026-11-05; it documents temperature/top_p/thinking but does not clearly document `seed`, so runtime capability was probed.
- Exactly two identical short, non-evaluation requests were sent with `seed=271828`, `temperature=0`, `top_p=1`, `max_tokens=8`, JSON mode, `thinking: {"type":"disabled"}`, and `stream=false`.
- Both returned HTTP 200, accepted the parameter, reported `model=deepseek-flash`, no exposed provider, request ID present (not saved), and usage/cache metadata. Reply content and headers were not saved.
- YAML/runtime record classifies `seed` as `supported` at runtime. This is parameter acceptance only; it is not a determinism guarantee and produced no model-quality or repetition result. Calculated cost from actual usage and the dated rate card is recorded as CNY 0.000232 for the two requests; the earlier identity probe remains CNY 0.000128.

## M2 Ollama capability

- Two independent short probes used `think=false`, `format=json`, `temperature=0`, `top_p=1`, `num_predict=8`, `seed=271828`, and `stream=false`, one through `/api/chat` and one through `/api/generate`.
- Both returned HTTP 200, valid JSON, and no thinking field. Runtime metadata was retained without response text. This establishes a usable no-think configuration for this Ollama runtime, but does not claim provider-level equivalence with DeepSeek.
- Local cost is not applicable; probe wall times were runtime metadata only and are not formal latency results.

## M3 candidate freeze

- `prompt-v1.md` is a versioned system/user template. It strictly separates explicit extraction from deterministic catalog/rule derivation, makes retrieval context untrusted, and excludes evaluator truth from model input.
- The nine-case `acceptance-set-v0.json` remains evaluator-only and `review`; `candidate_freeze=true` and `formal_evaluation_allowed=false` are explicit. Labels were not injected into any probe.
- `prompt-output-contract-v0.md` now points to `app001-extraction.v1` and retains the strict CAD-003 projection, failure denominator, retry, cost, and latency rules. All formal outcomes remain `not_measured`.
- DeepSeek formal requests must send `thinking: {"type":"disabled"}`. Ollama uses the separately verified `think=false` runtime setting; comparison remains mode-not-fully-equivalent pending hub review.

## Validation commands

Passed:

```text
PYTHONPATH=src python3 <normal/failure CAD-003 static check>
ruby -e 'require "yaml"; YAML.parse_file("agent-work/llm/APP-001-baseline-prep/model-baselines-v0.yaml")'
python3 -m json.tool agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json >/dev/null
python3 -m json.tool agent-work/llm/APP-001-baseline-prep/runtime-probe-2026-11-05.json >/dev/null
git diff --check
git check-ignore -v .env
prompt evaluator-label leak scan (PASS)
```

No acceptance sample, formal C0/C1, cloud/local comparison, Schema/IR/CAD/STEP run, or performance conclusion was produced. No API key, Authorization header, response body, hidden reasoning, or full provider error was stored.

## Earlier Codex hub decisions (historical; resolved by ADR-0013)

Historical note: the protocol/prompt/label review was resolved by ADR-0013. The then-current statement that adapter/logger implementation and review remained is superseded by the later `APP-001-ADAPTER-R3-FIX` acceptance. Current status and remaining gates are recorded in `APP-001-PREP-FINAL-FIX` below.

## APP-001-PREP-R2 document consistency correction

- Corrected the required output example in `prompt-output-contract-v0.md` from the stale `app001-extraction.v0-draft` label to the candidate `app001-extraction.v1` label.
- Removed the extra trailing blank line from `prompt-v1.md`.
- Repository search confirmed current Prompt version references in the Prompt, output contract, and baseline artifact are all `app001-extraction.v1`; historical records were not changed.
- No JSON/YAML files were modified in this correction, so no parser rerun was required. `git diff --check HEAD^ HEAD` was run for the correction commit; no model/API requests or acceptance samples were run.
- Prior delivery commit recorded for traceability: `c255d4e`. Status remains `APP-001-PREP=review`, `APP-001=planned`, `formal_evaluation_allowed=false`.

## ADR-0013 freeze checkpoint (historical; before adapter R3-FIX acceptance)

- Frozen model contract: `app001-io.v1`; frozen prompt: `app001-extraction.v2`; frozen evaluator-only case set: `acceptance-set-v0` (9 cases).
- Model output preserves explicit claims in `extracted_parameters` and unsupported requests separately; deterministic adapter generates the CAD-003 projection and validation record. Extraction, dialogue/safety, CAD-003, and downstream CAD/STEP outcomes have separate scoring stages.
- A01 labels only its three user-stated dimensions as extraction truth. Explicit `second_screw` claims in A06/A09 are retained for deterministic rule checking. A04/A05/A07/A09 preserve claims even though they cannot proceed to construction.
- Historical gate statement: formal evaluation was blocked pending adapter/logger implementation and review plus separate owner authorization. The adapter/logger condition was later satisfied by the accepted `APP-001-ADAPTER-R3-FIX`; explicit owner authorization is still required before any formal run. No model call or acceptance-set run was made for this freeze.

## APP-001-PREP-FINAL-FIX

- `APP-001-ADAPTER-R3-FIX` 已由 Codex 中枢验收通过；`APP-001-ADAPTER=done`。adapter/logger 已完成，并经 170 个 LLM 测试、17 个 Schema 测试验证。
- `APP-001-PREP` 当前仍为 `review`；`APP-001` 当前仍为 `planned`；`formal_evaluation_allowed=false`。
- 九条 evaluator-only 样例仍未运行；真实 DeepSeek/Ollama 正式运行仍未进行。
- 正式字段、Schema、CAD、STEP、费用和延迟指标仍为 `not_measured`；IR → Typed CAD IR 映射仍未冻结。
- 本阶段剩余事项是本次文档状态收尾和 Codex 最终复核；最终模型运行仍需项目负责人单独授权。
- 历史记录说明：下文早期阶段的 gate 描述反映当时状态，不代表当前 adapter 未完成。原句 `Remaining gate: implement and review the execution adapter/logger` 是历史记录，现已由 `APP-001-ADAPTER-R3-FIX` 验收结果取代。
