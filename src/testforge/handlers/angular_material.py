"""TestForge — Angular Material component handler."""
from __future__ import annotations
from typing import Optional
from .component_handler import ComponentHandler

_MAT_SELECT_TAG = "mat-select"
_MAT_OPTION_TAG = "mat-option"
_MAT_OPTION_SIGNALS = ("mat-option",)
_MAT_AUTOCOMPLETE_SIGNALS = ("aria-autocomplete", "mat-autocomplete", "aria-owns")


class AngularMaterialHandler(ComponentHandler):
    """Handles Angular Material components: mat-select, mat-autocomplete, mat-option."""

    @property
    def component_type(self) -> str:
        return "angular-material"

    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        tag_low = tag.lower()
        if tag_low in (_MAT_SELECT_TAG, _MAT_OPTION_TAG):
            return True
        if element_id and element_id.startswith(("mat-select-", "mat-option-")):
            return True
        for sel in candidates:
            if not sel:
                continue
            if "mat-radio" in sel:
                continue  # handled by MaterialComponentDetector
            if "mat-select" in sel or "mat-option" in sel:
                return True
            if "aria-autocomplete" in sel or "mat-autocomplete" in sel:
                return True
        return False

    def execute(self, page, step) -> str:
        tag = (getattr(step.target, "tag", "") or "").lower() if step.target else ""
        element_id = (getattr(step.target, "element_id", "") or "") if step.target else ""
        candidates: list[str] = []
        if step.target and getattr(step.target, "candidates", None):
            candidates = [c.selector for c in step.target.candidates if c.selector]

        if _is_mat_option(tag, element_id, candidates):
            return _execute_mat_option(page, step, candidates)
        return _execute_mat_select(page, step, candidates)

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


# ── private helpers ───────────────────────────────────────────────────────────

def _is_mat_option(tag: str, element_id: str, candidates: list[str]) -> bool:
    if tag == _MAT_OPTION_TAG:
        return True
    if element_id.startswith("mat-option-"):
        return True
    return any("mat-option" in sel for sel in candidates if sel)


def _execute_mat_option(page, step, candidates: list[str]) -> str:
    """Click a mat-option — wait for overlay visibility, then select by text or selector."""
    from .cdk_overlay import CDKOverlayHandler

    text = (
        (getattr(step, "value", "") or "").strip()
        or (getattr(step.target, "text", "") or "").strip()
        or (getattr(step.target, "accessible_name", "") or "").strip()
    )

    if text:
        option = CDKOverlayHandler.find_option(page, text)
        if option is None:
            option = CDKOverlayHandler.find_option_partial(page, text)
        if option is not None:
            option.click()
            page.wait_for_timeout(200)
            CDKOverlayHandler.wait_for_close(page, timeout=2000)
            return f"mat-option:text={text}"

    # Fallback: try candidate selectors
    for sel in candidates:
        if not sel:
            continue
        try:
            page.click(sel, timeout=3000)
            page.wait_for_timeout(200)
            return sel
        except Exception:
            continue

    raise ValueError(f"mat-option: could not click option — text='{text}'")


def _execute_mat_select(page, step, candidates: list[str]) -> str:
    """Open a mat-select dropdown, find the option, click it."""
    from .cdk_overlay import CDKOverlayHandler

    trigger_sel = _pick_mat_select_trigger(candidates)
    if not trigger_sel:
        raise ValueError("mat-select: no trigger selector found")

    value = (getattr(step, "value", "") or "").strip()

    page.click(trigger_sel, timeout=5000)
    page.wait_for_timeout(200)

    if not CDKOverlayHandler.wait_for_open(page):
        raise ValueError(
            f"mat-select: CDK overlay did not open after clicking '{trigger_sel}'"
        )

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


def _pick_mat_select_trigger(candidates: list[str]) -> str:
    """Pick best mat-select trigger selector from candidates."""
    for sel in candidates:
        if "mat-select" in sel:
            return sel
    for sel in candidates:
        if sel and ("role=\"combobox\"" in sel or "role='combobox'" in sel.lower()):
            return sel
    return candidates[0] if candidates else ""
