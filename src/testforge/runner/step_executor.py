"""TestForge — StepExecutor.

Executa um step com a estratégia apropriada por ação.
Não decide se o step passou semanticamente — isso é papel da pós-condição.
Usa field_value_map para ligar campo → valor com intenção e fallback.
"""
from __future__ import annotations
import re
from typing import Optional


class StepExecutor:
    """Executa uma única ação no browser via Playwright."""

    DEFAULT_TIMEOUT = 5000

    def __init__(self, page):
        self.page = page

    def _primary_selector(self, step) -> str:
        cands = self._all_selectors(step)
        return cands[0] if cands else ""

    def _all_selectors(self, step) -> list:
        """Retorna TODOS os seletores candidatos do alvo do passo, melhor primeiro."""
        if step.target and getattr(step.target, "candidates", None):
            return [c.selector for c in step.target.candidates if c.selector]
        return []

    def _canonical(self, s: str) -> str:
        """Normaliza string para comparação — minúscula, remove espaços, colapsa whitespace."""
        if not s:
            return ""
        import re
        return re.sub(r'[-_\s]+', '_', s.strip().lower())

    def _resolve_field_value(self, step, data_values: dict, field_value_map: dict) -> tuple:
        """Resolve valor e intenção para campo do passo usando field_value_map + data_values.

        Prioridade:
        1. Correspondência exata em field_value_map por identificadores de alvo (name, aria_label, placeholder, id)
        2. Correspondência exata em data_values pelos mesmos identificadores
        3. Correspondência de chave canônica em field_value_map
        4. Correspondência de chave canônica em data_values
        5. Correspondência de substring em data_values (fallback legado)

        Retorna (value, intention) — ambas strings vazias se sem correspondência.
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

        # Auxiliar: tenta correspondência contra um dict (field_value_map ou data_values)
        def _match(identifiers: dict, target_dict: dict) -> tuple:
            # Tenta cada identificador em ordem de prioridade
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
        selectors = self._all_selectors(step)
        selector = selectors[0] if selectors else ""

        # Delegate to registered component handler when the step targets a known framework component.
        # Handlers declare ownership via detect() — only the first matching handler is used.
        if action == "click":
            from ..handlers import detect_handler
            _handler = detect_handler(step)
            if _handler is not None:
                return _handler.execute(self.page, step)

        if action == "navigation":
            url = step.url or base_url
            if url and url != self.page.url:
                self.page.goto(url)
                self.page.wait_for_timeout(400)
            return ""

        if action == "click":
            from ..healing import MaterialComponentDetector
            detector = MaterialComponentDetector()

            tag = (step.target.tag or "").lower() if step.target else ""
            # Radio buttons (Angular Material mat-radio-button) must be clicked, not filled.
            # Detected by element_id prefix or top candidate selector containing mat-radio-button.
            # No candidates guard needed — detector checks both element_id and selector.
            _el_id = (getattr(step.target, "element_id", "") or "") if step.target else ""
            _top_sel = (step.target.candidates[0].selector if step.target and step.target.candidates else "")
            _is_radio = detector.is_material_radio_button(_el_id, _top_sel)
            if tag in ("input", "textarea") and not _is_radio:
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

                # Priority 2: resolved value from field_value_map.
                # Use accessible_name/label/placeholder from the target as the fill label —
                # the intention string is a human-readable description, not a valid aria-label.
                if resolved_val:
                    fill_label = (
                        ((step.target.accessible_name or "") if step.target else "")
                        or ((step.target.label or "") if step.target else "")
                        or ((step.target.placeholder or "") if step.target else "")
                        or intention
                    )
                    if self._fill_input(self.page, label=fill_label, value=resolved_val):
                        return f"field_map:{fill_label}"

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
            return self._execute_click(step, selectors)

        if action == "fill":
            # Resolve value + intention
            resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
            # step.value has priority — field_value_map only fills when step is empty.
            # This prevents field_value_map from overwriting later fills of same field
            # (e.g. recording has 3 fills: 10.000 → 100.000 → 1.000.000 on same input).
            use_val = step.value or resolved_val
            self._inject_intention(step, use_val, intention)
            return self._execute_fill(step, selectors, data_values, field_value_map)

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

    def _execute_click(self, step, selectors):
        if not selectors:
            raise ValueError(f"click sem selector (step {step.action})")

        from ..healing import MaterialComponentDetector
        detector = MaterialComponentDetector()

        # Hotfix BUG 1: when the click target lives inside a CDK overlay
        # (Angular Material datepicker calendar, dialog, autocomplete panel),
        # the first interaction is racy — the overlay starts animating in
        # AFTER the previous trigger click resolved, and the immediate next
        # click lands either on nothing or on the still-fading backdrop.
        # Wait for the overlay container to be visible (best effort) before
        # any click whose selector mentions cdk-overlay or mat-calendar.
        try:
            if any(_inside_cdk_overlay(s) for s in selectors if s):
                self.page.wait_for_selector(
                    ".cdk-overlay-container .cdk-overlay-pane",
                    state="visible", timeout=2500,
                )
                # Also wait for any CDK animation to settle.
                self.page.wait_for_timeout(250)
        except Exception:
            # If the wait fails just proceed — the click loop below has
            # its own retry behavior.
            pass

        last_error = None
        for sel in selectors:
            if not sel:
                continue
            try:
                # Check if this is a Material radio button (no candidates guard needed)
                if detector.is_material_radio_button("", sel):
                    loc = self.page.locator(sel).first
                    loc.dispatch_event("click")
                    self.page.wait_for_timeout(300)
                    return sel
                self.page.click(sel, timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(200)
                return sel
            except Exception as e:
                last_error = e
                continue
        raise last_error or ValueError(f"click falhou — todos os selectores tentados ({len(selectors)})")


def _inside_cdk_overlay(selector: str) -> bool:
    """Hotfix BUG 1 helper — detect selectors that live inside a CDK overlay."""
    if not selector:
        return False
    s = selector.lower()
    return any(token in s for token in (
        "cdk-overlay", "mat-calendar", "mat-datepicker",
        "mat-dialog", "mat-autocomplete-panel",
    ))

    def _execute_fill(self, step, selectors, data_values, field_value_map=None):
        if not selectors:
            raise ValueError("fill sem selector")
        field_value_map = field_value_map or {}

        # Resolve value — step.value has priority over field_value_map.
        # field_value_map only fills when step value is empty (e.g. placeholder from
        # IntentReconstructor). This prevents overwriting later fills on same field
        # (e.g. 3 fills: 10.000 → 100.000 → 1.000.000 on same currency input).
        resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
        value = (step.value or resolved_val or "").strip()

        if not value:
            raise ValueError(f"fill sem valor: step='{step.action}'")

        last_error = None
        for selector in selectors:
            if not selector:
                continue
            try:
                el = self.page.locator(selector).first
                # Detect masked inputs: currencymask attribute OR placeholder patterns
                has_mask = el.get_attribute("currencymask") is not None
                placeholder = (el.get_attribute("placeholder") or "").lower()
                is_date_mask = any(p in placeholder for p in (
                    "dd/mm", "mm/dd", "aaaa", "__/__/____", "dd/mm/aaaa",
                ))
                if not has_mask and not is_date_mask:
                    has_mask = any(p in placeholder for p in ("r$", "0,00"))
                if has_mask or is_date_mask:
                    masked_val = (step.value or value).strip()
                    if is_date_mask:
                        # Date masks expect formatted string with slashes (e.g. "10/06/2026")
                        # Do NOT strip slashes — they position the cursor in the mask.
                        type_val = masked_val
                    else:
                        # Currency masks: type ONLY raw digits; mask adds formatting.
                        # "10.000,00" → "1000000"
                        digits = re.sub(r"[^0-9]", "", masked_val)
                        type_val = digits if digits else masked_val
                    el.click()
                    self.page.wait_for_timeout(150)
                    # Triple-click selects all existing content before overwriting
                    el.click(click_count=3)
                    self.page.wait_for_timeout(80)
                    el.press_sequentially(type_val, delay=60)
                    self.page.keyboard.press("Tab")
                    self.page.wait_for_timeout(400)
                    return selector
            except Exception:
                pass
            try:
                self.page.fill(selector, value, timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(150)
                return selector
            except Exception as e:
                last_error = e
                continue
        raise last_error or ValueError(
            f"fill falhou — todos os {len(selectors)} selectores tentados"
        )

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