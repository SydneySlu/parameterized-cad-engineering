"""Small, fail-closed loader for credentials used by formal entry points.

The transport layer deliberately reads credentials from ``os.environ`` at
request time.  Formal runners may use this module to load a repository-local
``.env`` file after their authorization and offline preflight gates have
passed.  The loader never returns, prints, or logs secret values.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, MutableMapping


class EnvironmentConfigurationError(RuntimeError):
    """Raised when a required credential is absent or empty."""


_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    """Parse one conservative dotenv assignment without interpreting secrets."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_RE.fullmatch(key):
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_required_environment(
    *,
    dotenv_path: Path,
    required_keys: Iterable[str],
    environ: MutableMapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Load required keys from ``dotenv_path`` without exposing their values.

    Existing non-empty process environment values take precedence.  Empty
    process values are treated as unset so a non-empty value from ``.env`` can
    supply the formal entry point.  A missing file is allowed only when every
    required key is already present in the process environment.

    Returns the sorted names that are available after loading.  Missing or
    empty required values raise :class:`EnvironmentConfigurationError` and
    never create a batch directory or make network requests.
    """
    env = os.environ if environ is None else environ
    required = tuple(dict.fromkeys(str(key).strip() for key in required_keys if str(key).strip()))
    if not required:
        raise EnvironmentConfigurationError("no required environment keys were specified")

    required_set = set(required)
    parsed: dict[str, str] = {}
    try:
        if dotenv_path.is_file():
            for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                item = _parse_dotenv_line(line)
                if item is not None and item[0] in required_set:
                    parsed[item[0]] = item[1]
    except OSError as exc:
        raise EnvironmentConfigurationError(
            f"unable to read credential configuration file {dotenv_path}"
        ) from exc

    for key in required:
        if not str(env.get(key, "")).strip() and parsed.get(key, "").strip():
            env[key] = parsed[key]

    missing = [key for key in required if not str(env.get(key, "")).strip()]
    if missing:
        names = ", ".join(missing)
        raise EnvironmentConfigurationError(
            f"required credential environment variable(s) missing or empty: {names}"
        )
    return tuple(sorted(required))


def load_deepseek_environment(
    *,
    repo_root: Path,
    environ: MutableMapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Make ``DEEPSEEK_API_KEY`` available for an authorized formal run."""
    return load_required_environment(
        dotenv_path=repo_root / ".env",
        required_keys=("DEEPSEEK_API_KEY",),
        environ=environ,
    )
