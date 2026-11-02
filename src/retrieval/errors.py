"""Structured, serializable errors for the RET-002 retrieval baseline.

Every failure in this package is expressed as a :class:`RetrievalError` with a
stable code, a stage, the affected fields and JSON-safe details.  Callers get
one error channel for configuration, index construction and query handling
instead of a mix of `KeyError`, `TypeError` and `ValueError`.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


STAGES = ("config", "index", "query")


class RetrievalError(Exception):
    """A deterministic retrieval failure with a machine-readable payload."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        fields: Sequence[str] = (),
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown retrieval error stage: {stage!r}")
        self.code = code
        self.message = message
        self.stage = stage
        self.fields = tuple(str(field) for field in fields)
        self.details = dict(details or {})
        super().__init__(f"{code}: {message}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "stage": self.stage,
                "fields": list(self.fields),
                "message": self.message,
                "details": self.details,
            },
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=indent, sort_keys=False)
