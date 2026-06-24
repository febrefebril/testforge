"""Phase 3: Runtime errors raised by LocatorResolver and step helpers."""
from __future__ import annotations


class LocatorNotFoundError(RuntimeError):
    """Raised when no candidate locator resolves to a usable element.

    Carries enough context (intent text, attempted candidates, last error)
    that an L2/L3 healer can pick up the failure without re-parsing the
    traceback.
    """

    def __init__(
        self,
        intent: str,
        candidates: list,
        last_error: str = "",
    ) -> None:
        self.intent = intent
        self.candidates = candidates
        self.last_error = last_error
        attempted = ", ".join(c.get("strategy", "?") for c in candidates[:5])
        super().__init__(
            f'LocatorNotFound: intent="{intent}" tried=[{attempted}] '
            f'last_error="{last_error[:120]}"'
        )


class StepExecutionError(RuntimeError):
    """Raised when a resolved locator throws on the actual action (fill, click)."""

    def __init__(self, intent: str, action: str, message: str) -> None:
        self.intent = intent
        self.action = action
        super().__init__(f'StepExecution failed: action={action} intent="{intent}" — {message}')
