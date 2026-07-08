"""TestForge — React MUI (Material-UI) component handler skeleton.

Detects MUI components by Mui* class prefixes and role/listbox patterns.
execute() raises NotImplementedError until full implementation.
MUI uses Popper.js overlays — not CDK — so detection differs from Angular Material.
"""
from __future__ import annotations
from typing import Optional
from .component_handler import ComponentHandler

_MUI_CLASS_PREFIXES = (
    "MuiSelect",
    "MuiAutocomplete",
    "MuiMenuItem",
    "MuiMenu",
    "MuiPopover",
    "MuiPopper",
    "MuiInputBase",
    "MuiFormControl",
    "MuiDatePicker",
    "MuiTimePicker",
    "MuiDateTimePicker",
    "MuiMultiSelect",
    "MuiToggleButton",
    "MuiSwitch",
)

_MUI_TAGS = (
    "MuiSelect-root",
    "MuiAutocomplete-root",
)


class ReactMUIHandler(ComponentHandler):
    """Skeleton handler for React MUI (Material-UI v5+) components.

    Covers: Select, Autocomplete, DatePicker, TimePicker, MenuItem,
    ToggleButton, Switch — all using Popper.js overlay (not CDK).
    """

    @property
    def component_type(self) -> str:
        return "react-mui"

    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        for sel in candidates:
            if not sel:
                continue
            if any(prefix in sel for prefix in _MUI_CLASS_PREFIXES):
                return True
            # MUI listbox overlay: role="listbox" without CDK markers
            if "role=\"listbox\"" in sel or "role='listbox'" in sel.lower():
                if not any(cdk in sel for cdk in ("cdk-overlay", "mat-", "mat_")):
                    return True
            # MUI Popper: data-popper-placement without Angular CDK
            if "data-popper-placement" in sel:
                return True
        return False

    def normalize(self, steps: list) -> None:
        pass

    def execute(self, page, step) -> str:
        """MVP (2026-06-30): cobre Select + Autocomplete + MenuItem click.

        Strategy: MUI Select abre Popper listbox -> esperar role=listbox ->
        clicar option com text-is. Autocomplete eh igual. MenuItem direto
        eh so click. Fallback para default runner se padrao nao reconhecido.
        """
        target = getattr(step, "target", None)
        value = (getattr(step, "value", "") or "").strip()
        candidates = []
        if target and getattr(target, "candidates", None):
            candidates = [c.selector for c in target.candidates if c.selector]
        primary = candidates[0] if candidates else ""
        text_label = (
            (getattr(target, "accessible_name", "") if target else "")
            or value
            or (getattr(target, "text", "") if target else "")
        )
        # MUI Select / Autocomplete: click no trigger, espera listbox, clica option
        if primary and ("MuiSelect" in primary or "MuiAutocomplete" in primary):
            page.locator(primary).first.click(timeout=5000)
            page.wait_for_selector('[role="listbox"]', state="visible", timeout=4000)
            if text_label:
                opt = page.get_by_role("option", name=text_label)
                opt.first.click(timeout=4000)
                return f"mui_select:{text_label}"
            return primary
        # MenuItem / option direto
        if primary and ("MuiMenuItem" in primary or "role=\"option\"" in primary.lower()):
            page.locator(primary).first.click(timeout=5000)
            return primary
        # Switch / ToggleButton — click no trigger
        if primary and ("MuiSwitch" in primary or "MuiToggleButton" in primary):
            page.locator(primary).first.click(timeout=5000)
            return primary
        # Padrao nao reconhecido — devolve para default runner
        raise NotImplementedError(
            f"ReactMUIHandler.execute(): padrao MUI nao mapeado em '{primary[:80]}'. "
            "Cai pro default runner."
        )

    def heal(self, evidence, error: str) -> Optional[object]:
        return None
