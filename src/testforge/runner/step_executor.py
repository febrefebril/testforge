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
            # Data-driven fill: if clicking an input and we have data, fill it first
            tag = (step.target.tag or "").lower() if step.target else ""
            if tag in ("input", "textarea") and data_values:
                filled = self._try_data_fill(step, selector, data_values)
                if filled:
                    # Value was filled — don't click again (would clear/refocus)
                    return selector
            return self._execute_click(step, selector)
        if action == "fill":
            return self._execute_fill(step, selector, data_values)
        if action == "select_option":
            return self._execute_select(step, selector)
        if action == "assert":
            if selector:
                try:
                    self.page.locator(selector).first.wait_for(
                        state="visible", timeout=self.DEFAULT_TIMEOUT
                    )
                except Exception:
                    pass
            return selector

        raise NotImplementedError(f"acao desconhecida: {action}")

    def _try_data_fill(self, step, selector, data_values) -> bool:
        """Attempt to fill an input/textarea from data values before clicking."""
        label = ""
        if step.target:
            label = getattr(step.target, "label", "") or getattr(step.target, "placeholder", "")
        fill_val = data_values.get(label, "")
        if not fill_val:
            for k, v in data_values.items():
                if k in label or (label and label in k):
                    fill_val = str(v)
                    break

        # Determine which element to fill
        el = None
        if fill_val:
            try:
                el = self.page.locator(selector).first
                if el.count() == 0:
                    el = None
            except Exception:
                el = None

        # Fallback: search by aria-label from data keys
        if not el and data_values:
            for k, v in data_values.items():
                try:
                    cand = self.page.locator(f'input[aria-label="{k}"], textarea[aria-label="{k}"]')
                    if cand.count() > 0:
                        el = cand.first
                        fill_val = str(v)
                        break
                except Exception:
                    continue

        if not el or not fill_val:
            return False

        try:
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
                # Debug: verify value was set
                import sys
                actual = el.input_value()
                dirty = el.evaluate("el => el.className.includes('ng-dirty')")
                print(f"  ⚡ data-fill debug: value='{actual}' ng-dirty={dirty}", file=sys.stderr)
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