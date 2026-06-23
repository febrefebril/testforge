"""TestForge — Angular Material component handler."""
from __future__ import annotations
from typing import Optional
from .component_handler import ComponentHandler

_MAT_SELECT_TAG = "mat-select"
_MAT_SELECT_SIGNALS = ("mat-select",)
_MAT_RADIO_SIGNALS = ("mat-radio-button",)


class AngularMaterialHandler(ComponentHandler):
    """Handles Angular Material components: mat-select, mat-autocomplete, mat-dialog, etc."""

    @property
    def component_type(self) -> str:
        return "angular-material"

    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        if tag.lower() == _MAT_SELECT_TAG:
            return True
        if element_id and element_id.startswith("mat-select-"):
            return True
        for sel in candidates:
            if not sel:
                continue
            if "mat-select" in sel:
                # Exclude radio buttons — handled by MaterialComponentDetector in step_executor
                if "mat-radio" not in sel:
                    return True
        return False

    def execute(self, page, step) -> str:
        from .cdk_overlay import CDKOverlayHandler

        candidates: list[str] = []
        if step.target and getattr(step.target, "candidates", None):
            candidates = [c.selector for c in step.target.candidates if c.selector]

        trigger_sel = _pick_trigger(candidates)
        if not trigger_sel:
            raise ValueError("mat-select: no trigger selector found")

        value = (getattr(step, "value", "") or "").strip()

        # Open overlay
        page.click(trigger_sel, timeout=5000)
        page.wait_for_timeout(200)

        if not CDKOverlayHandler.wait_for_open(page):
            raise ValueError(
                f"mat-select: CDK overlay did not open after clicking '{trigger_sel}'"
            )

        # Select option if value provided
        if value:
            option = CDKOverlayHandler.find_option(page, value)
            if option is None:
                option = CDKOverlayHandler.find_option_partial(page, value)
            if option is None:
                raise ValueError(f"mat-select: option '{value}' not found in overlay")
            option.click()
            page.wait_for_timeout(200)

        CDKOverlayHandler.wait_for_close(page)
        return trigger_sel

    def normalize(self, steps: list) -> None:
        for step in steps:
            if not step.target:
                continue
            cands = getattr(step.target, "candidates", None) or []
            for c in cands:
                sel = getattr(c, "selector", "") or ""
                if "cdk-overlay-backdrop" in sel:
                    ctx = getattr(step, "context", {}) or {}
                    ctx["overlay_nav_noise"] = True
                    step.context = ctx
                    break

    def heal(self, evidence, error: str) -> Optional[object]:
        return None


def _pick_trigger(candidates: list[str]) -> str:
    """Pick the best mat-select trigger selector from candidates list."""
    for sel in candidates:
        if "mat-select" in sel:
            return sel
    for sel in candidates:
        if sel and ("role=\"combobox\"" in sel or "role='combobox'" in sel.lower()):
            return sel
    return candidates[0] if candidates else ""
