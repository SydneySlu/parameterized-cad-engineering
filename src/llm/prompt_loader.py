"""Frozen prompt artifact loader and verifier for APP-001.

This module loads the frozen system prompt and user message template from
``agent-work/llm/APP-001-v4-activation/prompt-v4.md`` and verifies that:

1. The artifact declares version ``app001-extraction.v4``.
2. The system message content matches exactly (after whitespace normalization).
3. The user message template content matches exactly (after normalization and
   placeholder form conversion).
4. The SHA-256 hashes in a run record match the actual content used.

**Normalization rules for template placeholders:**
The frozen prompt uses ``{{query_id}}``-style double-brace placeholders
(Markdown-safe).  The runtime ``AdapterInput.rendered_user_prompt()`` uses
Python ``.format()``-style single-brace ``{query_id}`` placeholders.  The
loader converts double-brace to single-brace before comparison.

**Security:**
- The frozen artifact's content is read from disk once and cached.
- Prompt content is never printed, logged, or stored in run records.
- Verification failures raise :class:`FrozenPromptMismatchError` before any
  transport ``send()`` is called.
- There is no ``skip_verification`` or ``allow_arbitrary_prompt`` parameter.

**History:**
- v3 activation (ADR-0016): prompt-v3.md, SHA-256
  3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b
- v4 activation (ADR-0017): prompt-v4.md, SHA-256
  73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import NamedTuple


_REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_PROMPT_PATH = (
    _REPO_ROOT
    / "agent-work"
    / "llm"
    / "APP-001-v4-activation"
    / "prompt-v4.md"
)

FROZEN_PROMPT_VERSION = "app001-extraction.v4"

# Known version string that must appear in the artifact.
_VERSION_MARKER = "app001-extraction.v4"

# Fixed SHA-256 anchor of the frozen prompt-v4.md file content (bytes).
# This is a separate integrity check from the parsed system_prompt/user_template
# hashes.  If the file is modified (even preserving the version string), the
# file-level hash will not match and loading fails closed.
#
# Update procedure: when a new frozen prompt version is approved via ADR,
# replace this constant with the new file's SHA-256 and update
# FROZEN_PROMPT_VERSION.  Do NOT change this value to match a modified file.
#
# v3 history (ADR-0016):
#   path: agent-work/llm/APP-001-v3-activation/prompt-v3.md
#   sha256: 3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b
FROZEN_PROMPT_FILE_SHA256 = "73cb6b8fbc38de09fe72a7714c172cf0598835dc845aca175c90cbd2f263a8bc"

# Regex to extract fenced Markdown code block content.
# Captures the text between ```...``` fences (the first code block found).
_FENCED_BLOCK = re.compile(r"```(?:[^\n]*)?\n(.*?)```", re.DOTALL)


class FrozenPromptMismatchError(RuntimeError):
    """Raised when the actual prompt does not match the frozen artifact.

    This must be raised before any transport ``send()`` call.
    """


class FrozenPromptArtifact(NamedTuple):
    """The parsed and verified frozen prompt artifact."""

    version: str
    system_prompt: str
    user_template: str  # single-brace {placeholder} form
    system_prompt_sha256: str
    user_template_sha256: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _double_brace_to_single(text: str) -> str:
    """Convert ``{{placeholder}}`` to ``{placeholder}`` for Python .format()."""
    return re.sub(r"\{\{(\w+)\}\}", r"{\1}", text)


def _extract_code_blocks(markdown: str) -> list[str]:
    """Return all fenced code block bodies (stripped of outer fence lines)."""
    return [m.group(1) for m in _FENCED_BLOCK.finditer(markdown)]


def _parse_artifact(text: str) -> tuple[str, str]:
    """Parse the frozen prompt-v4.md and extract (system_prompt, user_template).

    The artifact structure (as frozen):
    - Contains the literal version string ``app001-extraction.v4``.
    - The first fenced code block after ``## System message`` is the system
      prompt JSON envelope example.
    - The second fenced code block (```text) is the user message template.
    - The text between ``## System message`` and the first code block is the
      actual system message instructions that the model receives.

    Because the artifact mixes instructional prose with JSON example blocks,
    we parse it by section heading:
    - ``## System message`` section → system prompt instructions AND the
      fenced JSON envelope example content (only the ``` fence marker lines
      are removed; the fenced content is preserved so the model sees the bare
      JSON object naming ``contract_version`` and ``prompt_version``).
    - ``## User message template`` section → first code block body.

    This parsing is tied to the actual structure of prompt-v4.md.
    """
    lines = text.splitlines()
    system_lines: list[str] = []
    template_lines: list[str] = []
    section = None
    in_fence = False
    fence_content: list[str] = []
    template_captured = False

    for line in lines:
        stripped = line.strip()
        # Track sections by heading.
        if stripped.startswith("## System message"):
            section = "system"
            continue
        if stripped.startswith("## User message template"):
            section = "template"
            continue
        if stripped.startswith("## ") and section is not None:
            section = "other"
            continue

        if section == "system":
            # System section: take prose AND fenced code block content; skip
            # only the fence marker lines themselves.
            #
            # APP-001-PHASE1-ENVELOPE-FIX: the frozen prompt embeds the
            # JSON envelope example (the only place ``contract_version`` and
            # ``prompt_version`` appear) inside a fenced code block under
            # ``## System message``.  Stripping fenced-block content caused
            # the model to receive "Return this envelope, using exactly these
            # keys and literal values:" immediately followed by field
            # descriptions for decision/extracted_parameters/evidence/... but
            # NEVER the JSON object naming contract_version/prompt_version.
            # The second formal batch (app001-phase1-20261107-02) confirmed
            # this: all 32 model responses omitted those two keys and failed
            # with MISSING_ENVELOPE_KEY.  Keeping fence-internal lines (while
            # still dropping the ``` markers) sends the bare JSON object as the
            # template, consistent with the instruction "Return exactly one
            # UTF-8 JSON object, with no Markdown fences".
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            system_lines.append(line)

        elif section == "template" and not template_captured:
            # Template section: capture the first fenced block.
            if stripped.startswith("```") and not in_fence:
                in_fence = True
                fence_content = []
                continue
            if in_fence and stripped.startswith("```"):
                in_fence = False
                template_lines = fence_content
                template_captured = True
                continue
            if in_fence:
                fence_content.append(line)

    # Join and normalize.
    system_prompt = "\n".join(system_lines).strip()
    user_template_raw = "\n".join(template_lines).strip()
    # Convert {{placeholder}} → {placeholder} for runtime .format() calls.
    user_template = _double_brace_to_single(user_template_raw)
    return system_prompt, user_template


# Module-level cache so we only read/parse the file once.
_CACHED_ARTIFACT: FrozenPromptArtifact | None = None


def load_frozen_prompt(*, path: Path = FROZEN_PROMPT_PATH) -> FrozenPromptArtifact:
    """Load and parse the frozen prompt artifact from disk.

    Raises :class:`FrozenPromptMismatchError` if the artifact is missing,
    unreadable, or does not contain the frozen version marker.

    The result is cached after the first successful load.
    """
    global _CACHED_ARTIFACT
    if _CACHED_ARTIFACT is not None and path == FROZEN_PROMPT_PATH:
        return _CACHED_ARTIFACT

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact not found at {path}; "
            f"cannot label a run as {FROZEN_PROMPT_VERSION} without the artifact"
        )
    except OSError as exc:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact unreadable at {path}: {type(exc).__name__}"
        )

    # R3-A: Verify the file-level SHA-256 anchor.  This catches modifications
    # that preserve the version string but change the content.  Only the
    # canonical FROZEN_PROMPT_PATH is anchored; alternative paths (used only
    # by the loader's pure-function unit tests) skip this check.
    if path == FROZEN_PROMPT_PATH:
        _verify_file_hash(path, FROZEN_PROMPT_FILE_SHA256)

    if _VERSION_MARKER not in text:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact at {path} does not contain "
            f"version marker {_VERSION_MARKER!r}"
        )

    system_prompt, user_template = _parse_artifact(text)
    if not system_prompt:
        raise FrozenPromptMismatchError(
            "frozen prompt artifact: could not extract system prompt section"
        )
    if not user_template:
        raise FrozenPromptMismatchError(
            "frozen prompt artifact: could not extract user message template"
        )

    artifact = FrozenPromptArtifact(
        version=FROZEN_PROMPT_VERSION,
        system_prompt=system_prompt,
        user_template=user_template,
        system_prompt_sha256=_sha256(system_prompt),
        user_template_sha256=_sha256(user_template),
    )
    if path == FROZEN_PROMPT_PATH:
        _CACHED_ARTIFACT = artifact
    return artifact


def verify_adapter_input(
    adapter_input,
    *,
    path: Path = FROZEN_PROMPT_PATH,
) -> FrozenPromptArtifact:
    """Verify that ``adapter_input`` matches the frozen prompt artifact.

    Checks:
    1. The system prompt content matches (after strip normalization).
    2. The user template content matches (after strip normalization).
    3. The SHA-256 of the system prompt matches.
    4. The SHA-256 of the user template matches.

    Raises :class:`FrozenPromptMismatchError` on any mismatch.  This must be
    called before any transport ``send()`` to prevent mislabeling.

    Does NOT check version label -- version is fixed as a constant.
    """
    artifact = load_frozen_prompt(path=path)

    actual_system = adapter_input.system_prompt.strip()
    if actual_system != artifact.system_prompt:
        raise FrozenPromptMismatchError(
            "system_prompt does not match frozen artifact; "
            f"cannot label run as {FROZEN_PROMPT_VERSION}. "
            f"actual sha256={_sha256(actual_system)!r} "
            f"expected sha256={artifact.system_prompt_sha256!r}"
        )

    actual_template = adapter_input.user_prompt_template.strip()
    if actual_template != artifact.user_template:
        raise FrozenPromptMismatchError(
            "user_prompt_template does not match frozen artifact; "
            f"cannot label run as {FROZEN_PROMPT_VERSION}. "
            f"actual sha256={_sha256(actual_template)!r} "
            f"expected sha256={artifact.user_template_sha256!r}"
        )

    return artifact


def clear_cache() -> None:
    """Clear the module-level artifact cache (for testing only)."""
    global _CACHED_ARTIFACT
    _CACHED_ARTIFACT = None


def _verify_file_hash(path: Path, expected_sha256: str) -> None:
    """Private: verify that the file at ``path`` has the expected SHA-256.

    Raises :class:`FrozenPromptMismatchError` if the hash does not match.
    This is a pure function used by tests to verify tampered files without
    touching the canonical artifact.  It is NOT exposed as an Adapter bypass;
    the production loader always uses the fixed ``FROZEN_PROMPT_FILE_SHA256``.
    """
    try:
        file_bytes = path.read_bytes()
    except FileNotFoundError:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact not found at {path}"
        )
    except OSError as exc:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact unreadable at {path}: {type(exc).__name__}"
        )
    actual = hashlib.sha256(file_bytes).hexdigest()
    if actual != expected_sha256:
        raise FrozenPromptMismatchError(
            f"frozen prompt artifact file hash mismatch at {path}: "
            f"expected {expected_sha256!r}, got {actual!r}; "
            "the file has been modified and cannot be used as the frozen prompt"
        )
