# APP-001 Prompt / output contract v0 (draft)

Status: `review`. The project owner has confirmed the initial extraction, confidence, retry, and cost/latency policy. The acceptance labels and exact run batch still require Codex review/freeze; do not run formal evaluation before that gate.

## Version and run boundary

- Contract version: `app001-io.v0-draft`.
- Prompt version: `app001-extraction.v0-draft` (content still requires owner review).
- Family: `set_screw_shaft_collar`; schema target: `set_screw_shaft_collar.v0`.
- Acceptance set: `acceptance-set-v0` (draft/review only).
- A run must record model identity, provider/runtime, prompt and input hashes, decoding settings, relevant software versions, condition, latency and available token/cost data. A changed identity or protocol starts a new run batch and requires review.
- Record configured provider/model name separately from provider/model returned at runtime. Do not collapse aliases or silently rewrite mismatches.
- DeepSeek cloud request configuration: provider `DeepSeek`, model ID `deepseek-flash`, OpenAI-compatible base URL `https://api.deepseek.com`; the official docs label this served version `DeepSeek-V4.1-Flash-1017`. Preserve the response `model` field. The documented Chat Completions response has no provider field, so record runtime provider as `not_exposed` unless the actual response supplies one.
- C0/C1 can only be compared when model, Prompt, natural-language payloads, decoding parameters, output contract and post-processing are identical. C1's retrieved material is separately recorded as reference context. Fair C2 is outside this task and remains undefined.

## Common input

The shared user payload consists of a `query_id`, `family_id`, and verbatim `natural_language_input`. Optional `reference_context` is absent in C0 and may contain only RET-002 candidates in C1; each candidate is clearly labeled as an untrusted example. No condition may place evaluator labels, held-out truth, complete directory rows, hidden parameters, or expected output in the model input. Keep input bytes/hash, condition ID, prompt version and context hash in the run record. Do not inject CAD/STEP, IR, private source samples, or oracle directory data.

## Required output envelope

The model returns one JSON object and no prose or code fences. Proposed envelope:

```json
{
  "contract_version": "app001-io.v0-draft",
  "prompt_version": "app001-extraction.v0-draft",
  "decision": "answer",
  "cad_parameters": {
    "schema_version": "set_screw_shaft_collar.v0",
    "family_id": "set_screw_shaft_collar",
    "parameters": {"bore_d": 20}
  },
  "evidence": [
    {"field": "bore_d", "quote": "轴孔直径 20 mm", "source": "user_input"}
  ],
  "missing_fields": [],
  "questions": [],
  "confidence": null
}
```

`decision` is one of `answer`, `ask`, or `refuse`. In an `ask`/`refuse` response, `cad_parameters` may be `null`; it must never be presented as construction-ready when a required selector is absent or a conflict remains. For an `answer`, `parameters` contains only values explicitly stated by the user. The frozen Schema/rule layer may derive catalog fields and `second_screw`, recording provenance; the model must not fabricate those as explicit claims. This extraction/derivation boundary is the project owner's initial choice.

The `cad_parameters` object is a projection into the CAD-003 formal envelope. Only that object is passed to CAD-003 validation; the outer transport metadata is not part of `schema-v0.json`, whose root is strict. Do not modify the frozen Schema to accommodate this draft. Where a future adapter adds normalized or derived values, preserve both raw model output and post-processed output with distinct stage labels.

## Field semantics

- `evidence`: array of field-level support. `source` may be `user_input` or `retrieval_reference`; a retrieval reference is not user intent and cannot justify copying a value that conflicts with the request. Use short verbatim quotes where possible. Empty evidence means no supported claim.
- `missing_fields`: fields needed to proceed but not present in the user request. Missing `bore_d` is critical: ask for it or refuse; never supply a default or nearest catalog value. Derived fields should not be mislabeled as missing user inputs.
- `questions`: concrete, minimal clarification questions tied to missing or conflicting fields. A conflict between explicit values and the selected catalog/rule must be surfaced, not silently corrected.
- `confidence`: optional and nullable. It is not used in decision routing, acceptance/scoring, Schema/CAD gating, or model comparison. It is not calibrated; safest default is `null`.
- Units: length output is normalized to mm only after preserving the original value/unit in evidence or provenance. CAD-003 accepts canonical bare numbers in mm or value/unit objects; exact-match scoring converts both reference and output to mm before comparison.
- Unknown or unsupported requests: use `ask` or `refuse`; do not invent a catalog row or extend the family schema.
- Never emit CAD code, Python, CadQuery, OpenSCAD, STEP, or free-form geometry instructions. This stage returns structured intent only.

## JSON validation and post-processing

1. Parse exactly one UTF-8 JSON object. Trailing prose, multiple objects, invalid JSON, missing required envelope keys, invalid decision values, or wrong JSON types are protocol errors.
2. Preserve raw response. Record parse/schema/adapter outcomes separately; do not repair silently.
3. Only for `decision=answer` and non-null `cad_parameters`, project the inner formal envelope to CAD-003. CAD-003 checks `bore_d`, allowed units, catalog-row consistency, `second_screw` threshold and family inequalities. A structured refusal/ask is not counted as schema pass or CAD input.
4. The future deterministic chain, using the exact same model output, is `Schema/rules → Typed CAD IR → CadQuery/OCP → geometry/family rules → STEP export/readback`. This draft does not execute or measure any stage.

## Error and timeout records

Every attempted request, including failures, gets one record. Suggested stable shape:

```json
{
  "run_id": "pending",
  "query_id": "APP001-A04-missing-bore-d",
  "condition_id": "pending",
  "status": "error",
  "stage": "model_request",
  "error_code": "TIMEOUT",
  "fields": [],
  "retry_count": 0,
  "latency_ms": 0,
  "provider_request_id": null,
  "raw_response_sha256": null,
  "message_redacted": "request timed out"
}
```

At most 2 retries are allowed after the initial attempt (3 total attempts), only for transient failures: connection/read timeout, connection interruption, HTTP 429, or HTTP 5xx. Use fixed backoff of 1 second before retry 1 and 2 seconds before retry 2. Do not retry authentication/permission errors, malformed requests, context overflow, invalid JSON, contract/schema/rule rejection, or CAD failures. Record each attempt plus sample-level attempt count and total elapsed time. Exhausted transient failures remain in the evaluation denominator.

Stages are `input`, `model_request`, `json_parse`, `contract_validation`, `schema`, `typed_cad_ir`, `cad_build`, `geometry_rules`, `step_export`, and `step_readback`. Error codes should be stable and stage-local; keep `fields` empty if no parameter field applies. Distinguish `TIMEOUT`, `RATE_LIMIT`, `PROVIDER_ERROR`, `INVALID_JSON`, `CONTRACT_ERROR`, and downstream validation/build errors. Do not store secrets, authorization headers, private raw prompts/responses beyond approved sample data, or provider error bodies that may contain sensitive content. Missing cloud token/cost metadata is `null`/`not_available`, never estimated.

For cloud requests, record per-attempt input/output/total tokens and cost/currency when supplied. If cost is calculated, include the dated/versioned provider price source and calculation. For local Ollama runs, record per-sample inference wall time, attempt count and total elapsed time; cloud token/fee fields are not applicable. Keep configured provider/model name separate from runtime-returned provider/model fields.

- For DeepSeek costs, retain `prompt_cache_hit_tokens` and `prompt_cache_miss_tokens` (and `prompt_tokens_details.cached_tokens` when present), plus request timestamp. The official price card observed 2026-11-05 lists CNY/1M tokens with peak/off-peak rates; use the versioned rate card matching the request period rather than applying a single flat price.
- DeepSeek documentation says thinking is enabled by default and supports disabled mode. Do not assume the selected mode; record the actual request setting after owner confirmation. `seed` support remains a runtime-probe item.
- Secret setup: place the real key only in the repository-root `.env` as `DEEPSEEK_API_KEY=...`, or export that environment variable in the shell. `.env` is ignored by Git. Never place a real key in `.env.example`, tracked config, command history, logs, reports, or chat.

## Measurement order and status

1. After a formally approved model run, measure normalized field exact match, critical missing-field recognition, correct ask/refuse behavior, Schema/rule pass rate, latency and cost. Retain failed/time-out rows in the denominator and report them as failures or separately under the frozen denominator rule.
2. Then, for the same model output and same deterministic path, measure Typed CAD IR acceptance, CAD construction success, geometry/family-rule pass, and STEP readback pass. A language/schema result is not CAD/STEP success.
3. Compare C0/C1 only with fully common model, input, Prompt, decode settings and post-processing. C1 context is separately disclosed. Fair C2 is not defined here.

Current values for all language, Schema, IR, CAD, geometry, STEP, latency and cost outcomes are `not_measured`. This draft creates no C0/C1 result and makes no end-to-end claim.

## Project-owner decisions recorded

- Extract only user-explicit parameters; deterministic Schema/rules derive catalog and threshold fields.
- Confidence is not used for decisions or scoring; return `null` by default.
- Retry only transient call failures, at most 2 retries after the first request, with fixed 1s/2s backoff.
- Record cloud token usage and traceable fees separately from local elapsed inference time.
- Record configured provider/model name and runtime-returned provider/model fields separately.

Remaining freeze checks: prompt wording, sample labels and sufficiency, provider/API runtime identity, applied decoding values and seed support, and technical review of the run logger/output adapter.
