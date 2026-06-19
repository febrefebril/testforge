"""TestForge — StepExecutor.

Executa um step com a estratégia apropriada por ação.
Não decide se o step passou semanticamente — isso é papel da pós-condição.
Usa field_value_map para ligar campo → valor com intenção e fallback.
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

    def _canonical(self, s: str) -> str:
        """Normalize string for matching — lowercase, strip, collapse whitespace."""
        if not s:
            return ""
        import re
        return re.sub(r'[-_\s]+', '_', s.strip().lower())

    def _resolve_field_value(self, step, data_values: dict, field_value_map: dict) -> tuple:
        """Resolve value and intention for a step's field using field_value_map + data_values.

        Priority:
        1. Exact match in field_value_map by target identifiers (name, aria_label, placeholder, id)
        2. Exact match in data_values by same identifiers
        3. Canonical key match in field_value_map
        4. Canonical key match in data_values
        5. Substring match in data_values (legacy fallback)

        Returns (value, intention) — both empty strings if no match.
        """
        # Collect identifiers from step target (use getattr for test fakes)
        ids = {}
        if step.target:
            for attr, key in [('name', 'name'), ('accessible_name', 'aria_label'),
                              ('placeholder', 'placeholder'), ('element_id', 'id'),
                              ('label', 'label')]:
                val = getattr(step.target, attr, None) or ''
                if val:
                    ids[key] = val

        if not ids and not data_values and not field_value_map:
            return ("", "")

        # Helper: try to match against a dict (field_value_map or data_values)
        def _match(identifiers: dict, target_dict: dict) -> tuple:
            # Try each identifier in priority order
            for id_type in ("name", "aria_label", "label", "placeholder", "id"):
                id_val = identifiers.get(id_type, "")
                if not id_val:
                    continue
                # Exact match
                if id_val in target_dict:
                    entry = target_dict[id_val]
                    if isinstance(entry, dict):
                        return (entry.get("value", ""), entry.get("intention", ""))
                    return (str(entry), "")
                # Canonical match
                cid = self._canonical(id_val)
                for key in target_dict:
                    if self._canonical(key) == cid:
                        entry = target_dict[key]
                        if isinstance(entry, dict):
                            return (entry.get("value", ""), entry.get("intention", ""))
                        return (str(entry), "")
                # Substring match (data_values only, not field_value_map)
                if target_dict is data_values:
                    for key, val in target_dict.items():
                        if cid and (cid in self._canonical(key) or self._canonical(key) in cid):
                            return (str(val), "")
            return ("", "")

        if field_value_map:
            val, intention = _match(ids, field_value_map)
            if val:
                return (val, intention)

        if data_values:
            val, intention = _match(ids, data_values)
            if val:
                return (val, intention)

        # Last resort: try data_values by canonical step index
        ctx = getattr(step, "context", {}) or {}
        if data_values and ctx.get("missing_fill"):
            fill_label = ctx.get("fill_label", "")
            if fill_label:
                for key, val in data_values.items():
                    if fill_label and (key in fill_label or fill_label in key):
                        return (str(val), fill_label)

        return ("", "")

    def _inject_intention(self, step, value: str, intention: str) -> None:
        """Store resolved intention in step context for healing/fallback."""
        ctx = getattr(step, "context", {}) or {}
        if value:
            ctx["resolved_value"] = value
        if intention:
            ctx["resolved_intention"] = intention
        step.context = ctx

    def execute(self, step, base_url: str = "", data_values: Optional[dict] = None,
                field_value_map: Optional[dict] = None) -> str:
        data_values = data_values or {}
        field_value_map = field_value_map or {}
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
                ctx = getattr(step, "context", {}) or {}

                # Resolve value + intention from field_value_map + data_values
                resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
                self._inject_intention(step, resolved_val, intention)

                # Priority 1: form_values from submit capture
                form_vals = ctx.get("form_values") or {}
                if form_vals:
                    for name, val in form_vals.items():
                        if self._fill_input(self.page, label=name, value=val):
                            return f"submit_form:{name}"

                # Priority 2: resolved value from field_value_map
                if resolved_val:
                    if self._fill_input(self.page, label=intention or "", value=resolved_val):
                        return f"field_map:{intention}"

                # Priority 3: missing_fill → match data_values by fill_label
                if ctx.get("missing_fill"):
                    fill_label = ctx.get("fill_label", "")
                    if fill_label and data_values:
                        for k, v in data_values.items():
                            if fill_label and (k in fill_label or fill_label in k):
                                self._fill_input(page=self.page, label=k, value=str(v))
                                return selector

                # Priority 4: aria-label fallback
                if selector.startswith("[aria-"):
                    return self._fill_by_aria_label(step, data_values) or selector

                # Priority 5: try data fill by label/placeholder
                if data_values:
                    if self._try_data_fill(step, selector, data_values):
                        return selector

                # Priority 6: if we have a resolved value but all strategies failed,
                # raise with intention context for healing fallback
                if resolved_val:
                    raise ValueError(
                        f"fill_failed: '{intention or 'unknown'}' value='{resolved_val}' "
                        f"selector='{selector}' — nenhuma estrategia funcionou"
                    )
            return self._execute_click(step, selector)

        if action == "fill":
            # Resolve value + intention
            resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
            self._inject_intention(step, resolved_val or step.value, intention)
            return self._execute_fill(step, selector, data_values, field_value_map)

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
        patterns = [
            f'input[aria-label="{label}"]',
            f'textarea[aria-label="{label}"]',
            f'input[placeholder="{label}"]',
            f'textarea[placeholder="{label}"]',
        ]
        # Also try by name if label looks like a name
        if label and not label.startswith("step_"):
            patterns.extend([
                f'input[name="{label}"]',
                f'textarea[name="{label}"]',
            ])
        for sel_pattern in patterns:
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

    def _execute_fill(self, step, selector, data_values, field_value_map=None):
        if not selector:
            raise ValueError("fill sem selector")
        field_value_map = field_value_map or {}

        # Resolve value from field_value_map first, then data_values
        resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
        value = (resolved_val or step.value or "").strip()

        if not value:
            raise ValueError(f"fill sem valor: step='{step.action}' selector='{selector}'")

        try:
            el = self.page.locator(selector).first
            # Detect masked inputs: currencymask attribute OR placeholder patterns
            has_mask = el.get_attribute("currencymask") is not None
            if not has_mask:
                placeholder = (el.get_attribute("placeholder") or "").lower()
                has_mask = any(p in placeholder for p in ("r$", "0,00", "__/__/____"))
            if has_mask:
                # For masked inputs, use the recorded display value (with mask formatting
                # like dots and commas) instead of resolved raw value. press_sequentially
                # needs formatted characters so the mask interprets them correctly.
                masked_val = (step.value or value).strip()
                el.click()
                self.page.wait_for_timeout(150)
                # Clear existing value before typing — press_sequentially appends otherwise
                el.fill("")
                self.page.wait_for_timeout(80)
                el.press_sequentially(str(masked_val), delay=50)
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