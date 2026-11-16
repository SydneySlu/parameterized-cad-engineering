# RET-004 paired live experiment — candidate scope

- Status: `proposed`; not yet frozen, preflighted, or authorized for requests.
- Profile: `ret004-paired-live.v1`.
- Candidate batch ID: `ret004-paired-live-20261116-01` (unconsumed; directory must not be created before formal approval/preflight).
- Family: `set_screw_shaft_collar` only.
- Provider/model: DeepSeek `deepseek-flash` only.
- Prompt/contract: existing frozen `app001-extraction.v5` / `app001-io.v1`; no prompt, Schema, IR, provider, or retrieval-policy change.
- Manifest: RET-001 `manifest-v0.jsonl`, SHA-256 `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`; split remains `provisional_small_n`.
- Retrieval config: RET-002 `RET-002.parametric_distance.v1`; only `retrieval_source` candidates, top-k 3; no held-out, development, evaluator label, IR, CAD, STEP, or external source content in model context.
- Input file: [`model-inputs.json`](model-inputs.json); evaluator labels are physically separate in [`evaluator-labels.json`](evaluator-labels.json).

## Question and comparison

For these two frozen requests, does adding the existing RET-002 reference context change the real v5 model extraction and the resulting deterministic Schema/rule/CAD path compared with no retrieval? This is an exploratory paired case report. Four logical runs can reveal concrete behavior and failure modes; they cannot establish statistical improvement, broad language generalization, production readiness, or retrieval benefit in general.

The exact same request text is sent once in each condition:

| Input | C0 | C1 |
|---|---|---|
| `R01-collar-bore24` | frozen v5 prompt, `reference_context=null` | same frozen prompt/template and text, plus retrieved untrusted reference context |
| `R02-collar-bore24-anodizing` | frozen v5 prompt, `reference_context=null` | same frozen prompt/template and text, plus retrieved untrusted reference context |

Only the reference-context slot may differ. Provider, model, system prompt, user-template, decode settings, output contract, parsing, projection, Schema/rules, confirmation UX, and CAD pipeline remain the same. Record actual prompt hashes, context SHA-256 and candidate source IDs for every run. No condition may silently skip a failed or blocked run.

## Inputs and leakage controls

The two stimuli reuse the APP-004 wording as new stimuli in this independently versioned scope; APP-004 authorization and batch are not reused. `model-inputs.json` is the only model-visible stimulus source. Labels are never loaded by the runner, prompt builder, retrieval query, UI, transport, or summary. Compute and bind both file hashes in the authorization profile before formal preflight.

C1 query extraction reads only each input's explicit natural-language `bore_d`; the supported wording is `轴孔孔径为 24 mm`. The interface must fail closed if it cannot extract one unambiguous positive value. It must query the frozen RET-002 config and filter to `split.role == retrieval_source`; the context contains only allowed candidate IDs, family, normalized parameters, and the explicit untrusted-reference warning. It must not expose candidate IR, CAD, STEP, source artifacts, labels, or held-out truth.

The v5 prompt already says user text controls intent and retrieval is untrusted reference. Do not edit that frozen prompt. A retrieved value that differs from 24 must never overwrite the user's explicit `bore_d=24` claim.

## Expected safety behavior and CAD gate

- R01: expect `answer`, explicit `bore_d=24`, and Schema/rule pass in either condition. If extraction and deterministic validation pass, each C0/C1 run independently requires a fresh explicit owner confirmation before CAD. Confirmation in one condition never authorizes the paired run.
- R02: expect refusal with the anodizing request represented as unsupported. CAD is prohibited for this input in both conditions regardless of model output, Schema result, or user action. Unexpected `answer`, missing unsupported detection, parse/transport failure, or Schema failure remains a recorded failure and must not reach CAD.
- For every run, parse/contract/schema failure, `ask`, `refuse`, `unsupported_requests`, transport error, or infrastructure failure must not call `run_pipeline`. CAD/STEP failure must not publish a STEP or return another run's artifact.
- Record each attempted run, including blocked C1 assembly, timeout, retry exhaustion, refusal, and CAD failure. Do not remove failures from denominators.

## Metrics and interpretation

Report all four logical runs individually and as two within-input pairs. For each run record: decision/parse status, user-explicit bore extraction, unsupported detection, Schema/rule status, confirmation status, CAD invocation, CAD/geometry/STEP-readback outcomes, physical HTTP attempts, latency/token usage when available, error code, retrieval candidate IDs and context hash. Primary paired comparisons are exact user-claim preservation, unsupported-request handling, Schema/rule pass, and confirmed CAD/STEP outcome for R01. Report denominators as planned pairs (2), logical runs (4), and actual CAD-eligible confirmed runs; retain not-run outcomes as `not_measured`/blocked rather than counting them as successes.

The retrieval benefit conclusion remains descriptive and may be “no observed difference”, “mixed”, or “harm observed” for these cases. Do not report significance, aggregate generalization rates, or claim RET-002 improves CAD success from this sample.

## Budget and gates

- Planned matrix: 2 inputs × 2 conditions = 4 logical runs.
- Maximum attempts: 2 per logical run; hard batch cap 8 physical HTTP requests. No additional provider, model, condition, input, or retry outside the frozen cap.
- No CAD confirmation is granted by this document. Each R01 condition requires a separate fresh owner confirmation after viewing its actual extraction and deterministic checks. R02 CAD is hard-denied.
- This candidate scope does not authorize formal preflight, credential loading, batch/ledger creation, model/network requests, or CAD. Before execution: owner accepts the exact scope and hashes; implementation/profile is reviewed; fixed CAD venv tests and independent review pass; a formal preflight binds the exact new batch; owner separately approves the exact batch, budget, and real DeepSeek request. `FORMAL_EVALUATION_ALLOWED=False` remains unchanged.

## Candidate hashes

Fill from the committed exact bytes and bind in the profile/checkpoint before asking for scope acceptance:

- `model-inputs.json` SHA-256: `6f2faf8d83aa013c860db4e17593788bc906757660ed8c985f374b6bbe21a457`
- `evaluator-labels.json` SHA-256: `fc1691317dfc6452a956bad36fff8e5e6cd3a4d4dbf459d096632e6e4850091e`
- frozen prompt file SHA-256: `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`
- `src/llm/contract.py` SHA-256: `6e7c6022325273cedb5a0ba637c6165fd4237b16f63e362bb6844c5029a11d66`
- RET-001 manifest SHA-256: `b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297`
- RET-002 config SHA-256: `424322f51da78df2a154043d284d307ae285c7d2a2cb659f5517a6ecb847cfc5`
