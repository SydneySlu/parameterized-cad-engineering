# APP-001 LLM Execution Adapter (`src/llm/`)

**Status:** `APP-001-ADAPTER-R1` corrected; pending Codex hub review.
`APP-001 = planned`. Formal evaluation is **not authorized**.

This package implements the injectable adapter layer for the frozen APP-001
extraction protocol (`app001-io.v1` / `app001-extraction.v2`, ADR-0013).  It
never performs real network calls by default, never reads credentials in the
mock path, and the formal evaluation gate is always closed in this task.

---

## Modules

| Module | Purpose |
|---|---|
| `contract.py` | Frozen constants: versions, providers, decode settings, rate card |
| `parser.py` | Strict pure-function response parser (no repair; rejects NaN/Inf; strict element types) |
| `projector.py` | Deterministic CAD-003 projection from explicit extracted params |
| `transport.py` | `Transport` protocol + `MockTransport` base + `FakeTransport` for tests |
| `providers.py` | DeepSeek + Ollama request builders (credential-free; param isolated) |
| `retry.py` | Transient-fault retry with injectable clock/sleeper; total_elapsed_ms includes backoff |
| `runrecord.py` | Versioned, staged run-record; includes prompt_hashes and raw_response_retention |
| `cost.py` | DeepSeek cost from actual usage + dated rate card; not_available on any missing/invalid field |
| `gate.py` | Default-off formal evaluation gate (always closed); non-MockTransport refused before send() |
| `adapter.py` | Orchestrating adapter with RetentionPolicy, prompt hash recording, gate enforcement |

---

## Running tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/llm -v
```

No `pytest` required. All tests use `unittest` + `FakeTransport`.  No real
network calls, no credential reads, no writes to tracked outputs.

---

## Security and credential handling

**Mock path (current, default):**
- `build_deepseek_request()` and `build_ollama_request()` never read
  environment variables, `.env`, or any credential store.
- All returned `PreparedRequest` objects have `authorization=None`.
- `FakeTransport.calls` stores sanitized copies (authorization cleared),
  so assertion on stored calls cannot leak credential values.

**Future real-transport path (not yet authorized):**
- Credential injection is the responsibility of a real transport
  implementation that must only be instantiated *after* the formal evaluation
  gate is open (see Gate section below).
- The adapter never reads credentials itself; credentials are injected at the
  transport boundary only.
- Credentials must never appear in `RunRecord` JSON, stdout, exceptions,
  checkpoints, or tracked Git files.

---

## Formal evaluation gate

Any transport that is **not** a subclass of `MockTransport` is refused before
`send()` is called, regardless of the gate state argument:

```python
# FakeTransport (MockTransport subclass) -- always allowed:
adapter = Adapter(provider="DeepSeek", transport=FakeTransport(), ...)
adapter.run(...)  # OK

# Custom/real transport -- refused while gate is closed:
class MyHttpTransport:
    def send(self, req): ...  # NOT a MockTransport

adapter = Adapter(provider="DeepSeek", transport=MyHttpTransport(), ...)
adapter.run(...)  # raises FormalEvaluationBlockedError BEFORE send() is called
```

This check is unconditional and cannot be bypassed by a caller argument or
environment variable.  To use a real transport, the formal evaluation gate
must be opened via a new ADR and explicit project-owner authorization.

```python
from src.llm.gate import formal_evaluation_allowed, require_formal_evaluation_allowed
formal_evaluation_allowed()  # always False in this task
require_formal_evaluation_allowed("run a model")  # raises FormalEvaluationBlockedError
```

---

## Cost calculation

Cloud cost is computed only from **actual API response fields** using the
dated rate card.  The following conditions all result in `cloud_cost_amount=None`
(not_available):

- `prompt_tokens`, `cached_input_tokens`, `cache_miss_input_tokens`, or
  `output_tokens` are absent from the response usage.
- Any of these values is not a non-negative integer (bool, float, str, or
  negative values are all invalid).
- `cached_input_tokens + cache_miss_input_tokens != prompt_tokens` (inconsistent split).

**No estimation or fallback splitting is performed.**  The not_available reason
string records which field(s) were missing or invalid.

Rate card: DeepSeek official snapshot 2026-11-05 (CNY/1M tokens).  Peak
windows: Beijing time Mon-Fri 09:00-12:00, 14:00-18:00 (excl. public holidays).
See `contract.py` for the rate tables.

---

## Total elapsed time

`RunRecord.total_elapsed_ms` is the wall-clock time from **before the first
attempt** to **after the final outcome**, including all backoff waits (1s after
attempt 1, 2s after attempt 2).  Per-attempt `latency_ms` values record only
the individual transport call duration.  These two values should never be
conflated.

For local Ollama runs, `local_wall_time_ms` equals `total_elapsed_ms` (the
same complete wall clock, including any backoff on retried requests).

---

## Prompt hash recording

Every `RunRecord` includes `prompt_hashes` with deterministic SHA-256 hashes
of:

- `system_prompt_sha256`: SHA-256(system_prompt.encode("utf-8"))
- `user_template_sha256`: SHA-256(user_prompt_template.encode("utf-8"))
- `rendered_payload_sha256`: SHA-256(JSON of {system_prompt, user_message})

These hashes allow auditing whether the actual prompt used matches the frozen
artifact, independent of the version label.  **The prompt text itself is never
stored in the run record.**

The `prompt_version` field still records the frozen version label
(`app001-extraction.v2`).  A formal run entry point must verify the actual
prompt hash against the frozen artifact hash; if they do not match, it must
fail closed or record the discrepancy.

---

## Raw response retention

Raw model responses are **not retained by default**.  `RunRecord.raw_response_retention`
always contains non-sensitive metadata:

- `retained: false` (default)
- `body_length`: byte length of the response body
- `body_sha256`: SHA-256 hash of the response body (for integrity tracking)

**Opt-in retention** (future authorized runs only):
When `RetentionPolicy(retain_raw=True, base_dir="work/app001-runs")` is passed
to the adapter, the raw body is written to the git-ignored `work/app001-runs/`
directory.  The record then contains `retained: true` and the path.

If writing fails (permission error, disk full, etc.), `retention_failed: true`
is recorded; the run is **not** silently marked as fully retained.

The raw body is never written to `RunRecord` fields, stdout, exceptions,
checkpoints, or tracked Git files.  `work/app001-runs/` is confirmed
git-ignored by `.gitignore` line `work/`.

---

## IR / CAD / STEP status

These stages are always `not_run` or `blocked` in this task:

```
ir     → blocked   (blocked_no_approved_ir_mapping)
cad    → not_run
geometry → not_run
step   → not_run
```

To unblock: the Codex hub must freeze a src-level mapping contract before
this adapter can drive end-to-end CAD/STEP.

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
| `seed: 271828` | ✓ (body) | ✓ (`options`) |
| `temperature: 0` | ✓ (body) | ✓ (`options`) |
| `top_p: 1` | ✓ (body) | ✓ (`options`) |
| `authorization` | None (mock path) | None (always) |
