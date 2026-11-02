"""Stable, bounded errors shared by the CAD-005/006 pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CadError:
    code: str
    stage: str
    message: str
    field: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class PipelineError(Exception):
    def __init__(self, error: CadError):
        super().__init__(error.message)
        self.error = error


def fail(code: str, stage: str, message: str, field: str | None = None) -> None:
    raise PipelineError(CadError(code, stage, message[:500], field))
