"""APP-001 LLM execution adapter package.

This package implements the injectable, mock-testable adapter layer for the
frozen APP-001 extraction protocol (`app001-io.v1` / `app001-extraction.v2`).
It never performs real network calls or reads credentials by default; the
formal evaluation gate is closed and every runnable entry point fails closed.

Public modules:

- :mod:`src.llm.contract` -- frozen contract constants and envelope shapes.
- :mod:`src.llm.parser` -- strict, pure-function model-response parser.
- :mod:`src.llm.projector` -- deterministic CAD-003 projection from explicit
  extracted parameters.
- :mod:`src.llm.transport` -- injectable transport abstraction and a fake
  transport for tests.
- :mod:`src.llm.providers` -- DeepSeek and Ollama request builders with
  provider-specific parameter isolation.
- :mod:`src.llm.retry` -- transient-fault retry loop with injectable clock.
- :mod:`src.llm.runrecord` -- versioned, staged run-record data model.
- :mod:`src.llm.adapter` -- the orchestrating adapter tying the stages
  together and emitting staged records.
- :mod:`src.llm.gate` -- the default-off formal evaluation gate.
"""

__all__ = [
    "contract",
    "parser",
    "projector",
    "transport",
    "providers",
    "retry",
    "runrecord",
    "adapter",
    "gate",
]
