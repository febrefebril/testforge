"""TestForge — Validador Shadow + Executor Fallback."""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from ..taxonomy.taxonomy import FailureClassifier, FailureClassification, FailureFamily
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout


class SmartStepRunner:
    """Executor de passo consciente da estratégia para pipeline de healing.

    Suporta todas as 10 estratégias de healing com implementação adequada do Playwright.
    Usado por CuradorAutomatico step_runner em cmd_run e testes de healing.
    """

    FILL_TIMEOUT = 5000
    CLICK_TIMEOUT = 5000
    WAIT_TIMEOUT = 10000

    def __init__(self, page: Page):
        self._page = page

    def execute(self, step_data: dict, strategy: str = "") -> bool:
        """Executa um passo usando a estratégia de healing especificada.

        Args:
            step_data: dict com 'selector', 'action', 'value', 'strategy'
            strategy: nome da estratégia de healing (sobrescreve step_data['strategy'])

        Returns True se passo sucesso, False caso contrário.
        """
        sel = step_data.get("selector", "")
        action = step_data.get("action", "click")
        value = step_data.get("value", "")
        strat = strategy or step_data.get("strategy", "")

        try:
            # Handle strategy-specific behaviors
            if strat == "visibility_wait" or strat == "wait_for_enabled":
                self._page.wait_for_selector(sel, state="visible", timeout=self.WAIT_TIMEOUT)

            if strat == "overlay_dismiss":
                self._dismiss_overlays()

            if strat == "dialog_handler":
                self._register_dialog_handler()

            if strat == "iframe_switch":
                sel = self._handle_iframe(sel)

            if strat == "synthetic_click":
                self._page.evaluate(f"document.querySelector('{sel}').click()")
                self._page.wait_for_timeout(300)
                return True

            # Execute the action
            if action == "fill":
                if strat == "press_sequentially" or strat == "masked_input_detection":
                    self._page.press_sequentially(sel, value, timeout=self.FILL_TIMEOUT)
                else:
                    self._page.fill(sel, value, timeout=self.FILL_TIMEOUT)
                # Trigger blur so Angular/React form validators run (marking field touched).
                # Playwright fill() does not dispatch blur, so validation errors won't appear
                # without this — asserts on error messages would always fail.
                try:
                    self._page.locator(sel).first.dispatch_event("blur")
                except Exception:
                    pass
                self._page.wait_for_timeout(300)

            elif action == "click":
                if strat == "label_click":
                    # Try clicking the label first
                    try:
                        label_sel = f"label[for='{sel.lstrip('#')}']"
                        self._page.click(label_sel, timeout=self.CLICK_TIMEOUT)
                    except Exception:
                        self._page.click(sel, timeout=self.CLICK_TIMEOUT)
                else:
                    self._page.click(sel, timeout=self.CLICK_TIMEOUT)
                self._page.wait_for_timeout(300)

            elif action == "assert":
                self._page.wait_for_selector(sel, state="visible", timeout=self.WAIT_TIMEOUT)
                text = self._page.locator(sel).first.text_content(timeout=3000)
                if value and value.lower() not in (text or "").lower():
                    return False

            return True

        except Exception:
            return False

    def _dismiss_overlays(self):
        """Try to dismiss overlays/modals."""
        # Try Escape key
        try:
            self._page.keyboard.press("Escape")
            self._page.wait_for_timeout(300)
        except Exception:
            pass
        # Try clicking common overlay close selectors
        for close_sel in ['.overlay', '[role="dialog"] .close', '.modal .close',
                          '.mat-dialog-container', '.cdk-overlay-backdrop']:
            try:
                if self._page.locator(close_sel).count() > 0:
                    self._page.click(close_sel, timeout=2000)
                    self._page.wait_for_timeout(300)
                    break
            except Exception:
                continue

    def _register_dialog_handler(self):
        """Register handler for native dialogs."""
        try:
            self._page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass

    def _handle_iframe(self, sel: str) -> str:
        """Try to switch to iframe context. Returns adjusted selector."""
        # Try to find and switch to iframe
        try:
            iframes = self._page.locator("iframe")
            count = iframes.count()
            for i in range(count):
                frame = self._page.frame_locator(f"iframe >> nth={i}")
                try:
                    element = frame.locator(sel)
                    if element.count() > 0:
                        sel = f"iframe >> nth={i} >> {sel}"
                        break
                except Exception:
                    continue
        except Exception:
            pass
        return sel


@dataclass
class HealingSuggestion:
    """Sugestao de healing — registrada em shadow mode, nao aplicada automaticamente."""
    step_id: str
    original_selector: str
    failure: FailureClassification
    candidates: list = field(default_factory=list)  # list[dict] com selector+score
    suggested_selector: str = ""
    mode: str = "shadow"
    status: str = "pending_review"


class ShadowValidator:
    """Sugere healing para LOCATOR_NOT_FOUND. NAO aplica auto-heal."""

    def __init__(self, page: Page):
        self._page = page
        self._classifier = FailureClassifier()
        self._suggestions: list[HealingSuggestion] = []

    def evaluate_failure(self, step_id: str, error: str, original_selector: str = "",
                         candidates: list = None) -> Optional[HealingSuggestion]:
        classification = self._classifier.classify(error)

        if classification.family == FailureFamily.LOCATOR_RESOLUTION and candidates:
            return HealingSuggestion(
                step_id=step_id,
                original_selector=original_selector,
                failure=classification,
                candidates=candidates,
                suggested_selector=candidates[0].get("selector", "") if candidates else "",
                mode="shadow",
                status="pending_review",
            )

        if classification.family in (FailureFamily.STATE, FailureFamily.DYNAMIC_DOM, FailureFamily.INPUT):
            return HealingSuggestion(
                step_id=step_id,
                original_selector=original_selector,
                failure=classification,
                suggested_selector=original_selector,
                mode="shadow",
                status="pending_review",
            )

        return None

    @property
    def suggestions(self) -> list[HealingSuggestion]:
        return self._suggestions

    def add_suggestion(self, s: HealingSuggestion):
        self._suggestions.append(s)

    def pending_reviews(self) -> list[HealingSuggestion]:
        return [s for s in self._suggestions if s.status == "pending_review"]


class FallbackRunner:
    """Tenta candidatos de locator em ordem de score. Deterministico, sem LLM."""

    def __init__(self, page: Page):
        self._page = page

    def try_fill(self, candidates: list[dict], value: str) -> bool:
        """Tenta preencher com cada candidato ate funcionar."""
        for c in candidates:
            try:
                self._page.fill(c["selector"], value, timeout=5000)
                self._page.wait_for_timeout(100)
                return True
            except Exception:
                continue
        return False

    def try_click(self, candidates: list[dict]) -> bool:
        """Tenta clicar com cada candidato ate funcionar."""
        for c in candidates:
            try:
                self._page.click(c["selector"], timeout=5000)
                self._page.wait_for_timeout(100)
                return True
            except Exception:
                continue
        return False

    def try_fill_with_fallback(self, primary: str, fallbacks: list[str], value: str) -> tuple[bool, str]:
        """Tenta fill com seletor primario e fallbacks."""
        all_selectors = [primary] + fallbacks
        for sel in all_selectors:
            try:
                self._page.fill(sel, value, timeout=5000)
                self._page.wait_for_timeout(100)
                return True, sel
            except Exception:
                continue
        return False, ""

    def try_click_with_fallback(self, primary: str, fallbacks: list[str]) -> tuple[bool, str]:
        """Tenta click com seletor primario e fallbacks."""
        all_selectors = [primary] + fallbacks
        for sel in all_selectors:
            try:
                self._page.click(sel, timeout=5000)
                self._page.wait_for_timeout(100)
                return True, sel
            except Exception:
                continue
        return False, ""
