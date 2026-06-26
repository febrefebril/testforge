"""TestForge — StepExecutor.

Executa um step com a estratégia apropriada por ação.
Não decide se o step passou semanticamente — isso é papel da pós-condição.
Usa field_value_map para ligar campo → valor com intenção e fallback.
"""
from __future__ import annotations
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# CS-1 / hotfix 18: mask detection lives here, not in 4 different fill
# helpers. Anything that needs to know "is this input masked, and how?"
# calls _detect_mask_kind. Anything that needs to fill an input calls
# _fill_masked. There is no other path. Hotfix-per-helper recurrences
# (16, 17) happened because the same logic lived in 4 places and drifted.
_DATE_MASK_PLACEHOLDER_HINTS = (
    "dd/mm", "mm/dd", "aaaa", "yyyy", "__/__/____", "dd/mm/aaaa",
)
_CURRENCY_MASK_PLACEHOLDER_HINTS = ("r$", "0,00")


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
        """Find an input by aria-label / placeholder / name and fill it.

        CS-1: mask handling, clear-before-type and value normalization
        live in `_fill_masked`. This method's job is locator selection
        only.
        """
        patterns = [
            f'input[aria-label="{label}"]',
            f'textarea[aria-label="{label}"]',
            f'input[placeholder="{label}"]',
            f'textarea[placeholder="{label}"]',
        ]
        if label and not label.startswith("step_"):
            patterns.extend([
                f'input[name="{label}"]',
                f'textarea[name="{label}"]',
            ])
        for sel_pattern in patterns:
            try:
                el = page.locator(sel_pattern)
                if el.count() == 1:
                    self._fill_masked(
                        el, value,
                        fill_path="_fill_input",
                        selector_used=sel_pattern,
                    )
                    return True
            except Exception:
                continue
        return False

    def _fill_by_aria_label(self, step, data_values) -> Optional[str]:
        """Try to find and fill an input by aria-label from data_values keys.

        CS-1: mask handling delegated to `_fill_masked`.
        """
        if not data_values:
            return None
        for key, val in data_values.items():
            try:
                sel_pattern = (
                    f'input[aria-label="{key}"], textarea[aria-label="{key}"]'
                )
                el = self.page.locator(sel_pattern)
                if el.count() == 1:
                    self._fill_masked(
                        el, str(val),
                        fill_path="_fill_by_aria_label",
                        selector_used=sel_pattern,
                    )
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
            # CS-1: mask detection + clear + digit normalization in one place.
            self._fill_masked(
                el, str(fill_val),
                fill_path="_try_data_fill",
                selector_used=selector,
            )
            return True
        except Exception:
            return False

    # ----------------------------------------------------------------
    # CS-1 / hotfix 18 — single source of truth for masked-input fills.
    # The four fill helpers (_execute_fill, _fill_input,
    # _fill_by_aria_label, _try_data_fill) call _fill_masked. None of
    # them re-implement mask detection or the clear-and-press sequence.
    # When a bug surfaces it lives in exactly one place. CS-3 telemetry
    # is wired here so every fill is auditable from .testforge/spans.jsonl.
    # ----------------------------------------------------------------

    def _detect_mask_kind(self, el) -> tuple[str, str]:
        """Return (mask_kind, mask_detect) where:

        mask_kind   ∈ {"currency", "date", "none"}
        mask_detect ∈ {"attribute", "placeholder", "date_placeholder", "none"}

        Mask detection consults the `currencymask` HTML attribute first
        (legacy Caixa data layer) and falls back to placeholder
        inspection so that Material inputs without the attribute (e.g.
        SIOPI's `<input placeholder="R$0,00">`) are still recognized.
        """
        try:
            if el.get_attribute("currencymask") is not None:
                return "currency", "attribute"
        except Exception:
            pass
        try:
            placeholder = (el.get_attribute("placeholder") or "").lower()
        except Exception:
            placeholder = ""
        if any(p in placeholder for p in _DATE_MASK_PLACEHOLDER_HINTS):
            return "date", "date_placeholder"
        if any(p in placeholder for p in _CURRENCY_MASK_PLACEHOLDER_HINTS):
            return "currency", "placeholder"
        return "none", "none"

    def _fill_masked(self, el, value: str, *, fill_path: str,
                     selector_used: str = "") -> str:
        """Fill `el` with `value`, respecting mask kind. Returns mask_kind.

        Always:
        - Clears the field via triple-click before typing so re-runs
          and healing retries do not concatenate keystrokes.
        - For currency masks: types raw digits extracted via regex —
          mask formats them into "R$ X.XXX,XX".
        - For date masks: types the formatted value with slashes —
          the mask uses the slashes to position the cursor.
        - For unmasked inputs: calls `el.fill` which clears + sets.
        - Emits a `fill.attempted` span with the full audit trail.

        Single function. Four callers. No divergence possible by
        construction. See CS-1 / `.planning/CONSOLIDATION-SPRINT.md`.
        """
        value = "" if value is None else str(value)
        mask_kind, mask_detect = self._detect_mask_kind(el)
        cleared = False
        type_val: Optional[str] = None
        status = "ok"
        error_msg = ""

        try:
            if mask_kind == "none":
                el.fill(value, timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(150)
                # el.fill clears implicitly.
                cleared = True
                type_val = value
            else:
                el.click()
                self.page.wait_for_timeout(150)
                el.click(click_count=3)
                self.page.wait_for_timeout(80)
                cleared = True
                if mask_kind == "date":
                    type_val = value
                else:  # currency
                    digits = re.sub(r"[^0-9]", "", value)
                    type_val = digits if digits else value
                el.press_sequentially(type_val, delay=50)
                self.page.keyboard.press("Tab")
                self.page.wait_for_timeout(200)
        except Exception as exc:
            status = "error"
            error_msg = str(exc)[:200]
            raise
        finally:
            self._emit_fill_span(
                fill_path=fill_path, selector_used=selector_used,
                mask_kind=mask_kind, mask_detect=mask_detect,
                cleared=cleared, type_val=type_val, value=value,
                status=status, error_msg=error_msg,
            )
        return mask_kind

    def _emit_fill_span(self, *, fill_path: str, selector_used: str,
                        mask_kind: str, mask_detect: str, cleared: bool,
                        type_val: Optional[str], value: str,
                        status: str, error_msg: str) -> None:
        """CS-3 — JSONL fill.attempted span so the next debug session
        can answer "which fill path ran on step N?" without re-running.

        Raw `value` and `type_val` are redacted — only length and the
        value_kind bucket are logged. Selector strings are truncated.
        """
        try:
            from testforge.metrics.telemetry import get_tracer
            tracer = get_tracer()
            if not tracer.enabled:
                return
            attrs = {
                "fill_path": fill_path,
                "selector_used": (selector_used or "")[:200],
                "mask_kind": mask_kind,
                "mask_detect": mask_detect,
                "cleared": cleared,
                "value_len": len(value or ""),
                "type_val_len": len(type_val or "") if type_val is not None else 0,
                "status": status,
            }
            if error_msg:
                attrs["error.message"] = error_msg
            with tracer.start_span("fill.attempted") as span:
                for k, v in attrs.items():
                    span.set_attribute(k, v)
        except Exception:
            # Telemetry must never break execution.
            logger.debug("telemetry emit failed for fill.attempted", exc_info=True)

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
                # CS-1: single fill primitive. Handles mask detection,
                # triple-click clear, raw-digit / formatted-date /
                # plain-fill branches, and emits the fill.attempted span.
                mask_kind = self._fill_masked(
                    el, (step.value or value).strip(),
                    fill_path="_execute_fill",
                    selector_used=selector,
                )
                # Masked path returns immediately. Unmasked path also
                # succeeded if no exception bubbled up. Either way the
                # selector resolved and we wrote a value — return it.
                if mask_kind != "none":
                    self.page.wait_for_timeout(200)
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


def _inside_cdk_overlay(selector: str) -> bool:
    """Hotfix BUG 1 helper — detect selectors that live inside a CDK overlay."""
    if not selector:
        return False
    s = selector.lower()
    return any(token in s for token in (
        "cdk-overlay", "mat-calendar", "mat-datepicker",
        "mat-dialog", "mat-autocomplete-panel",
    ))