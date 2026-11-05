"""Shared test helpers for APP-001-ADAPTER R3 tests.

Provides a ``_frozen_input`` factory that builds an :class:`AdapterInput`
using the *real* frozen prompt artifact content, so tests can call
``Adapter.run()`` without bypassing prompt verification.

This module is test-only and is never imported by production code.
"""

from __future__ import annotations

from src.llm.adapter import AdapterInput
from src.llm.prompt_loader import load_frozen_prompt


def _frozen_input(**overrides) -> AdapterInput:
    """Build an AdapterInput using the real frozen prompt content.

    All keyword arguments accepted by AdapterInput are available as overrides;
    ``system_prompt`` and ``user_prompt_template`` default to the frozen
    artifact values and should not be overridden in tests that call
    ``Adapter.run()`` directly.
    """
    artifact = load_frozen_prompt()
    defaults = dict(
        query_id="q1",
        natural_language_input="bore_d=20 mm",
        reference_context=None,
        system_prompt=artifact.system_prompt,
        user_prompt_template=artifact.user_template,
        condition_id="c0",
    )
    defaults.update(overrides)
    return AdapterInput(**defaults)


def frozen_system_prompt() -> str:
    """Return the real frozen system prompt text (test-only)."""
    artifact = load_frozen_prompt()
    return artifact.system_prompt


def frozen_user_template() -> str:
    """Return the real frozen user template text (test-only)."""
    artifact = load_frozen_prompt()
    return artifact.user_template
