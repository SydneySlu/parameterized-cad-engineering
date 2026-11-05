"""The default-off formal evaluation gate.

The gate is a module-level flag that is always ``False`` in this task.  Any
runnable model CLI/API entry point must check this flag and fail closed.  The
flag has no override environment variable or CLI argument in this task;
unlocking requires a new ADR and explicit project-owner authorization.
"""

from __future__ import annotations

from .contract import FORMAL_EVALUATION_ALLOWED


def formal_evaluation_allowed() -> bool:
    """Return whether formal model evaluation is allowed.

    Always ``False`` in this task.  This is the single source of truth for the
    formal-run gate; runnable entry points must call this and fail closed.
    """
    return FORMAL_EVALUATION_ALLOWED


class FormalEvaluationBlockedError(RuntimeError):
    """Raised when a runnable entry point is reached while the gate is closed."""


def require_formal_evaluation_allowed(action: str = "run a model") -> None:
    """Fail closed unless :func:`formal_evaluation_allowed` is True.

    This is the guard every runnable model entry point must call before doing
    any work that could contact a real provider.
    """
    if not formal_evaluation_allowed():
        raise FormalEvaluationBlockedError(
            f"formal evaluation is not authorized; {action} is blocked. "
            "APP-001 remains 'planned' until the adapter/logger is reviewed and "
            "the project owner explicitly authorizes a run."
        )
