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
        raise NotImplementedError(
            "PrimeFacesHandler.execute() not yet implemented. "
            "Falling through to default runner."
        )

    def heal(self, evidence, error: str) -> Optional[object]:
        return None
