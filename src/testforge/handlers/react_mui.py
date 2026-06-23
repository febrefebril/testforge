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
        raise NotImplementedError(
            "ReactMUIHandler.execute() not yet implemented. "
            "Falling through to default runner."
        )

    def heal(self, evidence, error: str) -> Optional[object]:
        return None
