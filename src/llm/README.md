# APP-001 LLM Execution Adapter (`src/llm/`)

**Status:** `APP-001-ADAPTER` complete, pending Codex hub review.
`APP-001 = planned`. Formal evaluation is **not authorized**.

This package implements the injectable adapter layer for the frozen APP-001
extraction protocol (`app001-io.v1` / `app001-extraction.v2`, ADR-0013).  It
never performs real network calls by default, never reads credentials, and the
formal evaluation gate is always closed in this task.

---

## Modules

| Module | Purpose |
|---|---|
| `contract.py` | Frozen constants: versions, providers, decode settings, rate card |
| `parser.py` | Strict pure-function response parser (no repair/fix) |
| `projector.py` | Deterministic CAD-003 projection from explicit extracted params |
| `transport.py` | Injectable `Transport` protocol + `FakeTransport` for tests |
| `providers.py` | DeepSeek + Ollama request builders with param isolation |
| `retry.py` | Transient-fault retry with injectable clock/sleeper |
| `runrecord.py` | Versioned, staged run-record data model |
| `cost.py` | DeepSeek cost from actual usage + dated rate card |
| `gate.py` | Default-off formal evaluation gate (always closed) |
| `adapter.py` | Orchestrating adapter tying all stages together |

---

## Running tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
```

No `pytest` required. All tests use `unittest` + `FakeTransport`.  No real
network calls, no credential reads, no writes to tracked outputs.

---

## Security and retention policy

- **No real API/Ollama calls** during tests or by default.  A real HTTP
  transport can be injected in a future authorized run; the `gate.py`
  `require_formal_evaluation_allowed()` guard will fail closed.
- **Secrets never logged:** API keys are resolved from the environment inside
  `providers.py` but held only on the `PreparedRequest.authorization` field;
  they are never serialized into a run record, test fixture, or error message.
- **Sensitive fields in run records:** `authorization`, full provider error
  bodies, `thinking` content, and verbatim user input are excluded.  Stable
  `error_code`/`stage`/`fields` plus redacted summaries are sufficient.
- **Raw model responses** are written only to the git-ignored
  `work/app001-runs/` directory when a real authorized run executes.  No raw
  responses, private data, or generated CAD/STEP files are committed.

---

## IR / CAD / STEP status

These stages are always `not_run` or `blocked` in this task because no
frozen, reviewed, src-level parameter-to-IR adapter exists:

```
ir     → blocked   (blocked_no_approved_ir_mapping)
cad    → not_run
geometry → not_run
step   → not_run
```

To unblock: the Codex hub must freeze a src-level mapping contract in
`src/llm/` (or a designated module), referenced by ADR, before this adapter
can drive end-to-end CAD/STEP.

---

## Run record fields

Each `RunRecord` captures (non-exhaustive):

- `run_id`, `condition_id`, `query_id`, `timestamp_utc`
- `configured_provider`, `configured_model_name`
- `runtime_returned_provider`, `runtime_returned_model`, `local_digest`
- `contract_version`, `prompt_version`, `adapter_version`
- `input_payload_sha256`, `reference_context_sha256`
- `decoding_parameters`, `software_versions`
- `attempts[]` (per-attempt: timestamp, latency, outcome, http_status, error)
- `attempt_count`, `total_elapsed_ms`
- `stages[]` (model_call, parse, contract, projection, schema,
  construction_gate, ir, cad, geometry, step — each with status, error_code,
  error_fields, detail)
- `cloud_input_tokens`, `cloud_cached_input_tokens`,
  `cloud_cache_miss_input_tokens`, `cloud_output_tokens`, `cloud_total_tokens`
- `cloud_cost_amount`, `cloud_cost_currency`, `cloud_cost_source`
- `local_wall_time_ms`
- `construction_ready` (bool)
- `formal_evaluation_allowed` (always `false`)

---

## Formal evaluation gate

```python
from src.llm.gate import formal_evaluation_allowed, require_formal_evaluation_allowed

formal_evaluation_allowed()  # always False in this task
require_formal_evaluation_allowed("run a model")  # raises FormalEvaluationBlockedError
```

Any runnable model entry point must call `require_formal_evaluation_allowed()`
before touching the transport.

---

## Provider-specific parameter isolation

| Parameter | DeepSeek | Ollama |
|---|---|---|
| `thinking: {type: disabled}` | ✓ | ✗ |
| `response_format: {type: json_object}` | ✓ | ✗ |
| `max_tokens` | ✓ | ✗ |
| `think: false` | ✗ | ✓ |
| `format: "json"` | ✗ | ✓ |
| `num_predict` (in `options`) | ✗ | ✓ |
| `seed: 271828` | ✓ (in top-level body) | ✓ (in `options`) |
| `temperature: 0` | ✓ | ✓ (in `options`) |
| `top_p: 1` | ✓ | ✓ (in `options`) |
