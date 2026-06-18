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
            import sys
            print(f"  ⚡ execute click: tag='{tag}' has_data={bool(data_values)} data_keys={list(data_values.keys()) if data_values else 'none'}", file=sys.stderr)
            if tag in ("input", "textarea") and data_values:
                filled = self._try_data_fill(step, selector, data_values)
                print(f"  ⚡ _try_data_fill returned: {filled}", file=sys.stderr)
                if filled:
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
        if not data_values:
            return False

        # Build list of (label_key, value) candidates from data file
        candidates = []
        label = ""
        if step.target:
            label = getattr(step.target, "label", "") or getattr(step.target, "placeholder", "")

        # Exact match on step's label/placeholder
        if label and label in data_values:
            candidates.append((label, str(data_values[label])))

        # Partial match
        for k, v in data_values.items():
            if k not in dict(candidates) and k in label:
                candidates.append((k, str(v)))

        # Remaining data keys (for aria-label fallback)
        for k, v in data_values.items():
            if k not in dict(candidates):
                candidates.append((k, str(v)))

        el = None
        fill_val = ""
        import sys
        print(f"  ⚡ _try_data_fill: candidates={[(k,v) for k,v in candidates]} selector={selector}", file=sys.stderr)
        # Try each key: first by step's selector, then by aria-label search
        for key, val in candidates:
            # Try step's selector
            if not el:
                try:
                    cand = self.page.locator(selector)
                    cnt = cand.count()
                    print(f"  ⚡   selector '{selector[:40]}' count={cnt}", file=sys.stderr)
                    if cnt > 0:
                        el = cand.first
                        fill_val = val
                        break
                except Exception as e:
                    print(f"  ⚡   selector error: {e}", file=sys.stderr)
            # Try aria-label fallback
            if not el:
                try:
                    sel2 = f'input[aria-label="{key}"], textarea[aria-label="{key}"]'
                    cand = self.page.locator(sel2)
                    cnt = cand.count()
                    print(f"  ⚡   aria-search '{key[:30]}' count={cnt}", file=sys.stderr)
                    if cnt > 0:
                        el = cand.first
                        fill_val = val
                        break
                except Exception as e:
                    print(f"  ⚡   aria-search error: {e}", file=sys.stderr)

        print(f"  ⚡ _try_data_fill result: el={el is not None} fill_val='{fill_val}'", file=sys.stderr)

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