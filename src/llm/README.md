# APP-001 LLM Execution Adapter (`src/llm/`)

**Status:** APP-001 adapter and runner implementation are in review.
`APP-001 = planned`. The project owner has authorized a bounded Phase 1 run,
but no formal run starts until the runner safety review is complete.

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
| `gate.py` | Default-off global gate; direct non-FakeTransport calls fail closed |
| `adapter.py` | Orchestrating adapter with RetentionPolicy, prompt hashes, and runner-bound authorization checks |

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

**Authorized Phase 1 real-transport path:**
- Real transports are only permitted through `App001Runner.run_formal()` with
  the exact `FormalRunAuthorization` scope recorded in ADR-0014.
- Each physical `send()` is wrapped by `BudgetAwareTransport`, which reserves
  and records a durable budget slot before the request.
- The adapter never reads credentials itself; credentials are injected at the
  transport boundary only.
- Credentials must never appear in `RunRecord` JSON, stdout, exceptions,
  checkpoints, or tracked Git files.

---

## Formal evaluation gate

Any transport that is **not the exact type** `FakeTransport` is refused before
`send()` unless it is the runner-bound `BudgetAwareTransport` carrying the
matching Phase 1 authorization, exact provider/model, query, condition, run ID,
and real transport type. An arbitrary authorized custom transport is refused.

```python
# FakeTransport (exact type) -- always allowed:
adapter = Adapter(provider="DeepSeek", transport=FakeTransport(), ...)
adapter.run(...)  # OK

# MockTransport subclass -- refused (not exact FakeTransport type):
class MyMock(MockTransport):
    def send(self, req): ...
adapter = Adapter(provider="DeepSeek", transport=MyMock(), ...)
adapter.run(...)  # raises FormalEvaluationBlockedError BEFORE send()

# FakeTransport subclass -- also refused (exact type check):
class MyFake(FakeTransport):
    pass
adapter = Adapter(provider="DeepSeek", transport=MyFake(), ...)
adapter.run(...)  # raises FormalEvaluationBlockedError BEFORE send()

# Duck-type transport (plain class with send()) -- refused:
class HttpTransport:
    def send(self, req): ...  # NOT a MockTransport at all
adapter = Adapter(provider="DeepSeek", transport=HttpTransport(), ...)
adapter.run(...)  # raises FormalEvaluationBlockedError BEFORE send()

# Real calls are only allowed through App001Runner.run_formal(), which builds
# a matching real transport wrapped by BudgetAwareTransport.
```

This check uses exact type comparisons for `FakeTransport` and the controlled
wrapper, so a subclass or duck-typed transport cannot skip the budget ledger.
`FORMAL_EVALUATION_ALLOWED` remains `False`; ADR-0014 provides the narrow,
explicitly authorized Phase 1 path without opening the global gate.

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

## Prompt artifact verification (R3)

`Adapter.run()` **unconditionally** loads and verifies the frozen prompt
artifact (`agent-work/llm/APP-001-baseline-prep/prompt-v2.md`) before any
transport `send()` call.  There is **no parameter** to skip, replace, or bypass
this check -- `verify_frozen_prompt` and `_prompt_loader_path` were removed in
R3.

Verification checks:

1. **File-level SHA-256 anchor** (`FROZEN_PROMPT_FILE_SHA256`): the file bytes
   must match the pinned hash.  A tampered file that preserves the version
   string but changes content is rejected.
2. **Version marker**: the file must contain `app001-extraction.v2`.
3. **Parsed system prompt**: must match the `AdapterInput.system_prompt`.
4. **Parsed user template**: must match the `AdapterInput.user_prompt_template`
   (after `{{placeholder}}` → `{placeholder}` normalization).

Any mismatch raises `FrozenPromptMismatchError` before `send()` is called.
Tests that need synthetic prompts test the loader/verifier functions directly,
not via `Adapter.run()`.

Every `RunRecord` includes `prompt_hashes` with deterministic SHA-256 hashes
of:

- `system_prompt_sha256`: SHA-256(system_prompt.encode("utf-8"))
- `user_template_sha256`: SHA-256(user_prompt_template.encode("utf-8"))
- `rendered_payload_sha256`: SHA-256(JSON of {system_prompt, user_message})

**The prompt text itself is never stored in the run record.**

---

## Raw response retention

Raw model responses are **not retained by default**.  `RunRecord.raw_response_retention`
always contains non-sensitive metadata:

- `retained: false` (default)
- `body_length`: byte length of the response body
- `body_sha256`: SHA-256 hash of the response body (for integrity tracking)

**Opt-in retention** (future authorized runs only):
When `RetentionPolicy(retain_raw=True)` is used, raw responses are written inside
the canonical git-ignored `work/app001-runs/` directory.  The `base_dir` field
on `RetentionPolicy` defaults to `"work/app001-runs"` and **must** resolve to a
path inside that canonical root.  External absolute paths, path traversal
(`..`), and symlink escapes are all rejected before any write via
`_resolve_canonical_path()`.

There is **no public parameter** to specify an arbitrary directory outside the
canonical root.  There is no `_test_only` field, no `for_test()` factory, and
no `validate_for_production()` method on `RetentionPolicy`.  The private
`_write_raw_to_dir()` function is used internally by the production writer and
by tests (with a test-controlled tempdir); it is **not** a production bypass
interface.

If writing fails (permission error, disk full, path escape after resolve
detected via TOCTOU re-check, etc.), `retention_failed: true` is recorded; the
run is **not** silently marked as fully retained.

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
| `format` (structured JSON Schema, `OLLAMA_FORMAT_SCHEMA`) | ✗ | ✓ |
| `num_predict` (in `options`) | ✗ | ✓ |
| `seed: 271828` | ✓ (body) | ✓ (`options`) |
| `temperature: 0` | ✓ (body) | ✓ (`options`) |
| `top_p: 1` | ✓ (body) | ✓ (`options`) |
| `authorization` | None (mock path) | None (always) |

---

## Ollama structured output schema (APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX)

`build_ollama_request()` sets `body["format"]` to `OLLAMA_FORMAT_SCHEMA`, a JSON
Schema object aligned with the `app001-io.v1` envelope contract.  This is a
generation constraint (sampling hint), not a guarantee; `parse_response()` remains
the authoritative gating layer.

### Schema alignment with parser contract

| Field | Schema constraint | Parser enforcement |
|---|---|---|
| Top-level keys | `required` = all 9 ENVELOPE_KEYS; `additionalProperties: false` | `MISSING_ENVELOPE_KEY` / `EXTRA_ENVELOPE_KEY` |
| `contract_version` | `const: "app001-io.v1"` | `CONTRACT_VERSION_MISMATCH` |
| `prompt_version` | `const: "app001-extraction.v2"` | `PROMPT_VERSION_MISMATCH` |
| `decision` | `enum: [answer, ask, refuse]` | `DECISION_INVALID` |
| Length fields (5) | `oneOf: [number, {value, unit}]` — string excluded | `EXTRACTED_TYPE_ERROR` |
| `second_screw` | `integer` | `EXTRACTED_TYPE_ERROR` |
| `confidence` | `null` | `CONFIDENCE_NOT_NULL` |
| Array fields | `string` items | `ARRAY_ELEMENT_TYPE_ERROR` |
| `evidence` entries | `additionalProperties: false`; `field/quote/source` required strings; `source` enum | `EVIDENCE_ENTRY_*` |

### Schema does NOT encode

- Numeric value ranges, catalog rows, or CAD-003 rules (those remain in the deterministic Schema/adapter layer).
- Evaluator-only labels, expected outputs, or derived-value annotations.

### Snapshot

`decoding_parameters_snapshot(OLLAMA_PROVIDER)` records:

- `format_schema_sha256`: SHA-256 of the serialised schema (sorted keys)
- `format_schema_version`: `"ollama-app001-io-v1.0"`

These are computed from `OLLAMA_FORMAT_SCHEMA` / `OLLAMA_FORMAT_SCHEMA_SHA256` in
`providers.py`, ensuring the snapshot cannot drift from the actual request body.

### Ollama version compatibility

The active APP-001 local runtime is the Homebrew formula `ollama` **0.40.14**
(`sh.brew.ollama`, API `http://127.0.0.1:11434`).  The exact model is
`qwen3:8b`, whose frozen digest prefix is `500a1f067a9f`.  The schema fingerprint
is `d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043`.

On 2026-11-07, a no-key, no-artifact compatibility smoke using the frozen
Prompt and this schema returned HTTP 200 with all nine envelope keys and an
integer `bore_d`.  This proves runtime acceptance of the schema-object
`format` on 0.40.14; it does not authorize a new formal batch or establish
model-quality results.  The old Ollama.app 0.33.2 remains historical evidence
only.  See ADR-0015 for the frozen runtime boundary.
