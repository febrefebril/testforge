"""TestForge — StepExecutor.

Executa um step com a estratégia apropriada por ação.
Não decide se o step passou semanticamente — isso é papel da pós-condição.
"""
from __future__ import annotations
from typing import Optional


class StepExecutor:
    """Executa uma única ação no browser via Playwright."""

    DEFAULT_TIMEOUT = 5000

    def __init__(self, page):
        self.page = page

    def _primary_selector(self, step) -> str:
        if step.target and getattr(step.target, "candidates", None):
            cands = step.target.candidates
            if cands:
                return cands[0].selector or ""
        return ""

    def execute(self, step, base_url: str = "", data_values: Optional[dict] = None) -> str:
        data_values = data_values or {}
        action = step.action
        selector = self._primary_selector(step)

        if action == "navigation":
            url = step.url or base_url
            if url and url != self.page.url:
                self.page.goto(url)
                self.page.wait_for_timeout(400)
            return ""

        if action == "click":
            tag = (step.target.tag or "").lower() if step.target else ""
            if tag in ("input", "textarea"):
                # Check if normalizer detected a missing fill (currency-masked inputs)
                ctx = getattr(step, "context", {}) or {}
                if ctx.get("missing_fill"):
                    fill_label = ctx.get("fill_label", "")
                    if fill_label and data_values:
                        # Search by fill_label (aria-label/placeholder) from recording
                        for k, v in data_values.items():
                            if fill_label and (k in fill_label or fill_label in k):
                                self._fill_input(page=self.page, label=k, value=str(v))
                                return selector
                # Fallback: try existing data-driven fill mechanisms
                if selector.startswith("[aria-"):
                    return self._fill_by_aria_label(step, data_values) or selector
                if data_values:
                    if self._try_data_fill(step, selector, data_values):
                        return selector
            return self._execute_click(step, selector)
        if action == "fill":
            return self._execute_fill(step, selector, data_values)
        if action == "select_option":
            return self._execute_select(step, selector)
        if action == "assert":
            if selector:
                try:
                    self.page.locator(selector).first.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
                except Exception:
                    pass
            return selector

        raise NotImplementedError(f"acao desconhecida: {action}")

    def _fill_input(self, page, label: str, value: str) -> bool:
        """Find and fill an input by aria-label or placeholder."""
        for sel_pattern in [f'input[aria-label="{label}"]', f'textarea[aria-label="{label}"]',
                            f'input[placeholder="{label}"]', f'textarea[placeholder="{label}"]']:
            try:
                el = page.locator(sel_pattern)
                if el.count() == 1:
                    has_mask = el.get_attribute("currencymask") is not None
                    if has_mask:
                        el.click()
                        page.wait_for_timeout(150)
                        raw = value.replace(".", "").replace(",", "").replace(" ", "")
                        try:
                            cents = str(int(float(raw) * 100))
                        except ValueError:
                            cents = raw
                        el.press_sequentially(cents, delay=50)
                        page.keyboard.press("Tab")
                        page.wait_for_timeout(200)
                    else:
                        el.fill(value, timeout=self.DEFAULT_TIMEOUT)
                        page.wait_for_timeout(150)
                    return True
            except Exception:
                continue
        return False

    def _fill_by_aria_label(self, step, data_values) -> Optional[str]:
        """Try to find and fill an input by aria-label from data_values keys."""
        if not data_values:
            return None
        for key, val in data_values.items():
            try:
                el = self.page.locator(f'input[aria-label="{key}"], textarea[aria-label="{key}"]')
                if el.count() == 1:
                    has_mask = el.get_attribute("currencymask") is not None
                    if has_mask:
                        el.click()
                        self.page.wait_for_timeout(150)
                        raw = str(val).replace(".", "").replace(",", "").replace(" ", "")
                        try:
                            cents = str(int(float(raw) * 100))
                        except ValueError:
                            cents = raw
                        el.press_sequentially(cents, delay=50)
                        self.page.keyboard.press("Tab")
                        self.page.wait_for_timeout(200)
                    else:
                        el.fill(str(val), timeout=self.DEFAULT_TIMEOUT)
                        self.page.wait_for_timeout(150)
                    return f'aria-label="{key}"'
            except Exception:
                continue
        return None

    def _try_data_fill(self, step, selector, data_values) -> bool:
        """Attempt to fill from data values. Returns True if fill was attempted."""
        if not data_values:
            return False
        label = ""
        if step.target:
            label = getattr(step.target, "label", "") or getattr(step.target, "placeholder", "")
        fill_val = data_values.get(label, "")
        if not fill_val:
            for k, v in data_values.items():
                if label and k in label:
                    fill_val = str(v)
                    break
        if not fill_val:
            return False

        try:
            el = self.page.locator(selector).first
            has_mask = el.get_attribute("currencymask") is not None
            if has_mask:
                el.click()
                self.page.wait_for_timeout(150)
                raw = str(fill_val).replace(".", "").replace(",", "").replace(" ", "")
                try:
                    cents = str(int(float(raw) * 100))
                except ValueError:
                    cents = raw
                el.press_sequentially(cents, delay=50)
                self.page.keyboard.press("Tab")
                self.page.wait_for_timeout(200)
            else:
                self.page.fill(selector, str(fill_val), timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(150)
            return True
        except Exception:
            return False

    def _execute_click(self, step, selector):
        if not selector:
            raise ValueError(f"click sem selector (step {step.action})")
        self.page.click(selector, timeout=self.DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(200)
        return selector

    def _execute_fill(self, step, selector, data_values):
        if not selector:
            raise ValueError("fill sem selector")
        value = step.value or ""
        if data_values and step.target:
            label = getattr(step.target, "label", "") or getattr(step.target, "placeholder", "")
            for k, v in data_values.items():
                if k == label or (label and (k in label or label in k)):
                    value = str(v)
                    break
        try:
            el = self.page.locator(selector).first
            has_mask = el.get_attribute("currencymask") is not None
            if has_mask:
                el.click()
                self.page.wait_for_timeout(150)
                el.press_sequentially(str(value), delay=50)
                self.page.keyboard.press("Tab")
                self.page.wait_for_timeout(200)
                return selector
        except Exception:
            pass
        self.page.fill(selector, value, timeout=self.DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(150)
        return selector

    def _execute_select(self, step, selector):
        if not selector:
            raise ValueError("select_option sem selector")
        value = step.value or ""
        try:
            self.page.select_option(selector, value=value, timeout=self.DEFAULT_TIMEOUT)
        except Exception:
            self.page.select_option(selector, label=value, timeout=self.DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(200)
        return selector