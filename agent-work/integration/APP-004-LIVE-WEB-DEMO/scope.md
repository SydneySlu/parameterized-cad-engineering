# APP-004-LIVE-WEB-DEMO scope proposal

- 状态：`review`（scope proposal only；未接受、未冻结、未授权执行）
- 日期：2026-11-16
- 任务：`APP-004-LIVE-WEB-DEMO`
- profile：`app004-live-web-demo.v1`
- proposed batch ID：`app004-live-web-demo-20261116-01`
- provider/model/condition：DeepSeek `deepseek-flash` / C0 / no retrieval
- family：`set_screw_shaft_collar` only
- contract/prompt：当前冻结的 `app001-io.v1` / `app001-extraction.v5`

## Goal

Prepare a localhost-only web demonstration that visibly runs the real frozen LLM extraction path for two allowlisted requests, shows the structured result and deterministic checks, and requires a separate human confirmation before CAD construction. This scope is for a short project presentation, not a broad model-quality evaluation.

## Frozen stimuli

The authoritative stimuli are in [`model-inputs.json`](model-inputs.json). The two exact inputs are:

1. `D01-collar-bore24`: a supported GN 705 collar with `bore_d=24 mm`; expected model decision is `answer`. CAD may run only after the owner reviews the extracted values and confirms this exact run.
2. `D02-collar-anodizing`: the same collar request plus anodizing; expected behavior is `refuse` or `ask` and the unsupported requirement must not be silently accepted. CAD is prohibited for this input ID regardless of the model response or user action.

The web UI must not accept arbitrary request text in this profile. It sends only a frozen input ID; the server loads the corresponding request text from the hashed input file. This avoids widening the approved scope during a live demonstration.

## Budget and execution boundary

- At most 2 logical inputs and 2 HTTP attempts per input; batch cap is **4 HTTP requests** total.
- One provider, one model, one condition (C0); no retrieval, image input, second family, prompt change, or automatic CAD.
- Browser-to-server requests carry only an allowlisted input ID and later an explicit confirmation for an eligible run. Browser code never receives provider credentials.
- Credential loading occurs server-side only after approval binding and offline preflight pass.
- D01 can enter the existing CAD pipeline only after the live extraction result passes parsing, envelope checks, Schema/rule validation, and a fresh per-run human confirmation.
- D02 is hard-denied from CAD before any confirmation is considered, even if the model returns a plausible `answer`.
- Raw response content, if retained under the reviewed runner policy, remains only in the ignored run directory; HTTP/UI and summaries expose only sanitized fields and hashes. Evaluator labels are physically separate and must never be opened by the runner or UI.
- The process binds localhost only. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.

## Expected deliverables and gates

1. This proposal plus physically separated model inputs and evaluator-only labels, with hashes recorded below.
2. A scope-bound authorization/profile and formal runner with an approval gate, offline preflight and hard 4-request budget.
3. A local web entry with visible source/status/parameter/confirmation/result states; no arbitrary prompt box and no credentials in browser traffic.
4. Tests proving normal extraction, refusal/ask handling, invalid JSON/transport failure, D02 hard CAD denial, D01 confirmation-only CAD, output isolation, and zero network/CAD/credential side effects before the formal gate.
5. Fixed-CAD-environment and browser smoke review before any real request.

This proposal does not create the batch directory, read credentials, run preflight, call the model/network, or execute CAD. The proposed batch ID remains unconsumed. After implementation and independent review, the owner must separately accept/freeze this scope and explicitly authorize that exact batch and budget before any formal preflight or real request. A separate per-run confirmation is still required before D01 CAD construction.

## Hashes

- model-inputs.json SHA-256: `4c97a043e1547831fd92f3f7a95ba65b6ea6734b073f2ce9687454143ed65841`
- evaluator-labels.json SHA-256: `4eff6146ee2b1809a9720407eceb605257340204fbca409a2c35e94295c5e091`

Any content change requires updating the hash and re-reviewing the scope.
