# APP-001 Prompt / output contract v1

Status: frozen for the first APP-001 run protocol. This freeze covers the model output contract and nine-case acceptance set only; formal evaluation remains disallowed until the execution adapter/logger is implemented and reviewed and the project owner explicitly authorizes a run.

## Versions and baselines

- Contract: `app001-io.v1`.
- Prompt: `app001-extraction.v2` (`prompt-v2.md`).
- Acceptance set: `acceptance-set-v0` (frozen evaluator-only labels).
- Family/schema: `set_screw_shaft_collar` / `set_screw_shaft_collar.v0`.
- Cloud: DeepSeek request model `deepseek-flash`, documented service version DeepSeek-V4.1-Flash-1017. Save configured identity and runtime response fields separately.
- Local: Ollama `qwen3:8b`, ID `500a1f067a9f`, on MacBook Air M5 16 GB/512 GB. Windows CPU is a separate migration exploration.
- DeepSeek requests explicitly use `thinking: {"type":"disabled"}`; Ollama uses its separately verified `think=false` setting. These provider-specific settings are not claimed to be semantically equivalent.

## Model output and deterministic post-processing

The model returns one JSON object and no prose/code fences. The required shape is:

```json
{
  "contract_version": "app001-io.v1",
  "prompt_version": "app001-extraction.v2",
  "decision": "answer",
  "extracted_parameters": {"bore_d": 20},
  "unsupported_requests": [],
  "evidence": [
    {"field": "bore_d", "quote": "轴孔直径 20 mm", "source": "user_input"}
  ],
  "missing_fields": [],
  "questions": [],
  "confidence": null
}
```

The model's `extracted_parameters` contains only explicitly stated claims mapped to CAD-003 fields. It may preserve claims that conflict with catalog/rule constraints; it must not invent missing values or add derived catalog values. Explicit statements about a supported parameter, including `second_screw`, remain claims for deterministic validation. Unsupported features are recorded separately in `unsupported_requests` and never projected into CAD-003.

The model output does **not** contain `cad_parameters`. The adapter preserves the raw response, then deterministically projects `extracted_parameters` into `{schema_version, family_id, parameters}` and records that separate payload plus the CAD-003 result. The adapter runs deterministic validation to classify missing selectors, catalog/rule conflicts, and invalid values, including when the model's conversational decision is `ask` or `refuse`. A result is construction-ready only when `decision=answer`, `unsupported_requests` is empty, and CAD-003 passes. Only then may it proceed to Typed CAD IR/CAD. Ask/refuse, unsupported, or rejected results never reach CAD construction. Keep raw model output, projected payload, and validation result as distinct stages.

Score `extracted_parameters` against the evaluator's explicit user-claim labels before post-processing, including ask/refuse and invalid cases. Score `decision`, missing/unsupported detection, and evidence separately. Score deterministic CAD-003/schema outcomes after projection; do not count a correct ask/refuse as a schema pass or as CAD input. Catalog/rule-derived values are assessed in the post-processing stage, not as model extraction claims.

## Input isolation and retrieval

The common model input contains `query_id`, fixed `family_id`, verbatim natural-language input, and optional reference context. C0 has no reference context. C1 may include only RET-002 candidates labeled as untrusted examples. Never expose evaluator labels, held-out truth, complete catalog rows, expected outputs, derived-value labels, private source samples, IR, CAD, or STEP data to the model. Save input/context hashes and condition ID in the run record.

## Parsing, errors, retries, and logging

Parse exactly one UTF-8 JSON object. Invalid JSON, extra prose/objects, missing keys, invalid enums, or wrong types are protocol failures; do not silently repair. Preserve the raw response under the approved retention policy and record parse, contract, adapter, and downstream outcomes separately. Never log secrets, authorization headers, or sensitive provider error bodies.

Allow at most two retries after the initial attempt (three total), only for connection/read timeout, connection interruption, HTTP 429, or HTTP 5xx, with fixed 1s/2s backoff. Do not retry authentication/permission errors, malformed requests, context overflow, invalid JSON, contract/schema/rule rejection, or CAD failures. Keep exhausted failures in the denominator.

Record per attempt: run/query/condition IDs, UTC timestamp, configured and runtime provider/model identities, local digest if applicable, prompt/contract/acceptance versions, input/context hashes, actual decode/runtime settings, software versions, latency, attempt number, outcome, stage and stable error code/fields. For cloud, record input/output/total and cache-hit/cache-miss token counts and traceable cost/currency. Compute cost only from actual usage and the dated rate-card snapshot matching request time; otherwise use `not_available`. For local, record per-sample inference wall time, attempts and total elapsed time; cloud fee/token fields are not applicable.

Shared decode values are `temperature=0`, `top_p=1`, `max_output_tokens=512`, and seed `271828` because both runtimes accepted it in non-evaluation capability probes. Parameter acceptance is not a determinism guarantee. Save the actual runtime-specific field names/settings; any rejected or unavailable shared setting triggers review before comparison.

## Metrics and run gate

Keep separate denominators and report: explicit field extraction exact match after unit normalization; evidence support; missing-field and conflict handling; unsupported-request handling; decision/clarification correctness; JSON/contract validity; CAD-003 validation; then, on the same accepted projected output, Typed CAD IR acceptance, CAD build, geometry/family-rule validation, and STEP export/readback. Report failures by stage. Do not call a Schema pass a CAD/STEP success.

C0/C1 can be compared only with the same model, prompt, natural-language inputs, decode settings, output contract, adapter, and deterministic downstream path; disclose C1 reference context separately. Cloud/local are practical deployment baselines with provider-specific thinking controls, not a claim of perfectly matched runtime semantics. Fair C2 is undefined and out of scope.

No formal model, Schema, IR, CAD, geometry, STEP, latency, or cost performance result exists yet. This contract and acceptance set do not themselves authorize evaluation. The remaining gate is adapter/logger implementation and review, followed by explicit run authorization.
