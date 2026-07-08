"""TestForge — Validador de Acionabilidade.

Valida se elemento é acionável antes de executar ações na página.
Verifica: visível, habilitado, área > 0 (rejeita bb width=height=0).
"""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout


@dataclass
class ActionabilityResult:
    """Resultado de uma verificação de acionabilidade."""

    selector: str
    actionable: bool
    visible: bool = False
    enabled: bool = False
    area_positive: bool = False
    bounding_box: Optional[dict] = None
    failures: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def status(self) -> str:
        return "passed" if self.actionable else "failed"


class ActionabilityValidator:
    """Valida se elemento é acionável antes de executar ações na página.

    Verifica:
      - visível (is_visible)
      - habilitado (is_enabled)
      - área > 0 (largura e altura da caixa delimitadora > 0)
      - rejeita bb width=height=0
    """

    def __init__(self, page: Page):
        self._page = page

    def validate(self, selector: str, timeout: int = 5000) -> ActionabilityResult:
        """Verifica se elemento no seletor é acionável.

        Args:
            selector: Seletor CSS ou de texto.
            timeout: Tempo máximo de espera em ms.

        Returns:
            ActionabilityResult com flag acionável e detalhes de cada verificação.
        """
        result = ActionabilityResult(selector=selector, actionable=False)

        try:
            locator = self._page.locator(selector)
        except Exception as e:
            result.failures.append(f"invalid_selector: {e}")
            result.message = f"Seletor invalido '{selector}': {e}"
            return result

        # Presença: elemento deve existir no DOM
        try:
            locator.first.wait_for(state="attached", timeout=timeout)
        except (PlaywrightTimeout, Exception):
            result.failures.append("not_attached")
            result.message = f"Elemento '{selector}' nao encontrado no DOM"
            return result

        el = locator.first

        # Verificação de visibilidade
        try:
            el.wait_for(state="visible", timeout=timeout)
            result.visible = True
        except (PlaywrightTimeout, Exception):
            result.failures.append("not_visible")
            result.visible = False

        # Verificação de habilitação
        try:
            if el.is_enabled(timeout=timeout):
                result.enabled = True
            else:
                result.failures.append("not_enabled")
        except Exception:
            result.failures.append("not_enabled")

        # Verificação de área: caixa delimitadora deve ter largura e altura positivas
        try:
            bb = el.bounding_box(timeout=timeout)
            result.bounding_box = bb
            if bb is None:
                result.failures.append("no_bounding_box")
            elif bb["width"] <= 0 or bb["height"] <= 0:
                result.failures.append(f"zero_area: w={bb['width']}, h={bb['height']}")
            else:
                result.area_positive = True
        except Exception as e:
            result.failures.append(f"bounding_box_error: {e}")

        result.actionable = len(result.failures) == 0

        if result.actionable:
            result.message = f"Elemento '{selector}' esta acionavel"
        else:
            result.message = f"Elemento '{selector}' nao esta acionavel: {'; '.join(result.failures)}"

        return result

    def check(self, selector: str, timeout: int = 5000) -> bool:
        """Atalho: retorna True se acionável, False caso contrário."""
        return self.validate(selector, timeout=timeout).actionable
