"""TestForge — Shadow Validator + Fallback Runner."""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from ..taxonomy.taxonomy import FailureClassifier, FailureClassification, FailureFamily


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
