"""TestForge — PrimeFaces component handler skeleton.

Detects PrimeFaces widgets by their characteristic class patterns.
execute() raises NotImplementedError until full implementation.
"""
from __future__ import annotations
from typing import Optional
from .component_handler import ComponentHandler

_PF_CLASSES = (
    "ui-selectonemenu",
    "ui-selectmanymenu",
    "ui-datepicker",
    "ui-autocomplete",
    "ui-dropdown",
    "ui-multiselect",
    "p-dropdown",
    "p-autocomplete",
    "p-calendar",
    "p-multiselect",
    "p-selectbutton",
)

_PF_ELEMENT_IDS = (
    "j_idt",
    "ui-datepicker",
)


class PrimeFacesHandler(ComponentHandler):
    """Skeleton handler for PrimeFaces JSF widgets.

    Covers: SelectOneMenu, SelectManyMenu, Calendar/DatePicker,
    AutoComplete, Dropdown, MultiSelect (PF 6–14 + PrimeTek p-* variants).
    """

    @property
    def component_type(self) -> str:
        return "primefaces"

    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        for sel in candidates:
            if not sel:
                continue
            sel_lower = sel.lower()
            if any(cls in sel_lower for cls in _PF_CLASSES):
                return True
            if "primefaces" in sel_lower or "ui-widget" in sel_lower:
                return True
        element_id_lower = (element_id or "").lower()
        if any(pfx in element_id_lower for pfx in _PF_ELEMENT_IDS):
            return True
        return False

    def normalize(self, steps: list) -> None:
        pass

    def execute(self, page, step) -> str:
        """MVP (2026-06-30): cobre SelectOneMenu + Dropdown + Calendar.

        PrimeFaces patterns:
        - SelectOneMenu / p-dropdown: trigger eh `.ui-selectonemenu` /
          `.p-dropdown`, listbox abre como sibling `.ui-selectonemenu-panel`.
        - Calendar / p-calendar: trigger eh icon clickable; panel `.ui-datepicker`
          aparece como floating. Para data direta, fill no input nativo
          `<input id="..._input">` funciona.
        - AutoComplete / p-autocomplete: typing + click suggestion.
        """
        target = getattr(step, "target", None)
        value = (getattr(step, "value", "") or "").strip()
        candidates = []
        if target and getattr(target, "candidates", None):
            candidates = [c.selector for c in target.candidates if c.selector]
        primary = candidates[0] if candidates else ""
        primary_lower = (primary or "").lower()
        # SelectOneMenu / Dropdown
        if any(cls in primary_lower for cls in ("ui-selectonemenu", "p-dropdown")):
            page.locator(primary).first.click(timeout=5000)
            # Panel selectonemenu / dropdown-panel
            panel_sel = '.ui-selectonemenu-panel:visible, .p-dropdown-panel:visible'
            page.wait_for_selector(panel_sel, state="visible", timeout=4000)
            if value:
                page.get_by_text(value, exact=False).first.click(timeout=4000)
                return f"pf_dropdown:{value}"
            return primary
        # Calendar — preenche input nativo associado
        if any(cls in primary_lower for cls in ("ui-datepicker", "p-calendar")):
            input_sel = (primary.split(' ')[0] + "_input"
                         if "_input" not in primary else primary)
            try:
                page.locator(input_sel).first.fill(value, timeout=5000)
                return f"pf_calendar:{value}"
            except Exception:
                page.locator(primary).first.click(timeout=5000)
                return primary
        # AutoComplete — typing
        if "p-autocomplete" in primary_lower or "ui-autocomplete" in primary_lower:
            page.locator(primary).first.fill(value, timeout=5000)
            page.wait_for_timeout(400)
            page.get_by_text(value, exact=False).first.click(timeout=3000)
            return f"pf_autocomplete:{value}"
        raise NotImplementedError(
            f"PrimeFacesHandler.execute(): padrao PF nao mapeado em '{primary[:80]}'. "
            "Cai pro default runner."
        )

    def heal(self, evidence, error: str) -> Optional[object]:
        return None
