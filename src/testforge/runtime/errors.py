"""Phase 3: Erros de runtime levantados por LocatorResolver e step helpers."""
from __future__ import annotations


class LocatorNotFoundError(RuntimeError):
    """Levantado quando nenhum locator candidato resolve para um elemento utilizavel.

    Carrega contexto suficiente (texto de intent, candidatos tentados, ultimo erro)
    para que um healer L2/L3 possa pegar a falha sem re-interpretar o
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
    """Levantado quando um locator resolvido lanca erro na acao real (fill, click)."""

    def __init__(self, intent: str, action: str, message: str) -> None:
        self.intent = intent
        self.action = action
        super().__init__(f'StepExecution failed: action={action} intent="{intent}" — {message}')
