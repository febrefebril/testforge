"""TestForge — Angular Material component handler."""
from __future__ import annotations
from typing import Optional
from .component_handler import ComponentHandler

_MAT_SELECT_TAG = "mat-select"
_MAT_OPTION_TAG = "mat-option"


class AngularMaterialHandler(ComponentHandler):
    """Handles Angular Material: mat-select, mat-option, mat-autocomplete,
    mat-dialog, mat-tab-group, mat-slide-toggle."""

    @property
    def component_type(self) -> str:
        return "angular-material"

    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        tag_low = tag.lower()
        if tag_low in (_MAT_SELECT_TAG, _MAT_OPTION_TAG, "mat-slide-toggle"):
            return True
        if element_id and element_id.startswith(
            ("mat-select-", "mat-option-", "mat-dialog-", "mat-tab-")
        ):
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
            if "mat-dialog" in sel:
                return True
            if "[role=\"tab\"]" in sel or "mat-tab-label" in sel or "mat-tab-header" in sel:
                return True
            if "mat-slide-toggle" in sel or "[role=\"switch\"]" in sel:
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
        if _is_mat_dialog(candidates):
            return _execute_mat_dialog(page, step, candidates)
        if _is_mat_tab(candidates):
            return _execute_mat_tab(page, step, candidates)
        if _is_mat_toggle(tag, candidates):
            return _execute_mat_toggle(page, step, candidates)
        return _execute_mat_select(page, step, candidates)

    def normalize(self, steps: list) -> None:
        for i, step in enumerate(steps):
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

                if "[role=\"tab\"]" in sel or "mat-tab-label" in sel:
                    ctx = getattr(step, "context", {}) or {}
                    ctx["tab_navigation"] = True
                    step.context = ctx
                    break

        # Mark dialog-open triggers: if step N is a click that is immediately
        # followed by dialog content steps, annotate step N.
        for i in range(len(steps) - 1):
            step = steps[i]
            if step.action != "click" or step.skip_reason:
                continue
            nxt = steps[i + 1]
            if not nxt.target:
                continue
            nxt_cands = getattr(nxt.target, "candidates", None) or []
            nxt_in_dialog = any(
                "mat-dialog" in (getattr(c, "selector", "") or "")
                for c in nxt_cands
            )
            if nxt_in_dialog:
                ctx = getattr(step, "context", {}) or {}
                ctx["dialog_open_trigger"] = True
                step.context = ctx

    def heal(self, evidence, error: str) -> Optional[object]:
        return None


# ── type predicates ───────────────────────────────────────────────────────────

def _is_mat_option(tag: str, element_id: str, candidates: list[str]) -> bool:
    if tag == _MAT_OPTION_TAG:
        return True
    if element_id.startswith("mat-option-"):
        return True
    return any("mat-option" in sel for sel in candidates if sel)


def _is_mat_dialog(candidates: list[str]) -> bool:
    return any("mat-dialog" in sel for sel in candidates if sel)


def _is_mat_tab(candidates: list[str]) -> bool:
    for sel in candidates:
        if not sel:
            continue
        if "[role=\"tab\"]" in sel or "mat-tab-label" in sel or "mat-tab-header" in sel:
            return True
    return False


def _is_mat_toggle(tag: str, candidates: list[str]) -> bool:
    if tag == "mat-slide-toggle":
        return True
    for sel in candidates:
        if not sel:
            continue
        if "mat-slide-toggle" in sel or "[role=\"switch\"]" in sel:
            return True
    return False


# ── execute helpers ───────────────────────────────────────────────────────────

def _execute_mat_option(page, step, candidates: list[str]) -> str:
    """Click a mat-option by text match, then candidate selectors as fallback."""
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


def _execute_mat_dialog(page, step, candidates: list[str]) -> str:
    """Click a button inside a mat-dialog-container, scoped to avoid outside matches."""
    text = (
        (getattr(step.target, "text", "") or "").strip()
        or (getattr(step.target, "accessible_name", "") or "").strip()
        or (getattr(step, "value", "") or "").strip()
    )

    # Playwright frame-scoped selector: dialog >> button
    if text:
        scoped = f".mat-dialog-container button:has-text('{text}')"
        try:
            page.click(scoped, timeout=3000)
            page.wait_for_timeout(200)
            return scoped
        except Exception:
            pass
        # Try mdc variant
        scoped_mdc = f".mat-mdc-dialog-container button:has-text('{text}')"
        try:
            page.click(scoped_mdc, timeout=3000)
            page.wait_for_timeout(200)
            return scoped_mdc
        except Exception:
            pass

    for sel in candidates:
        if not sel:
            continue
        try:
            page.click(sel, timeout=3000)
            page.wait_for_timeout(200)
            return sel
        except Exception:
            continue

    raise ValueError(f"mat-dialog: could not click action — text='{text}'")


def _execute_mat_tab(page, step, candidates: list[str]) -> str:
    """Click a tab by text, then wait for its panel to become active."""
    text = (
        (getattr(step.target, "text", "") or "").strip()
        or (getattr(step.target, "accessible_name", "") or "").strip()
        or (getattr(step, "value", "") or "").strip()
    )

    if text:
        tab_sel = f"[role='tab']:has-text('{text}')"
        try:
            page.click(tab_sel, timeout=3000)
            page.wait_for_timeout(300)
            return tab_sel
        except Exception:
            pass

    for sel in candidates:
        if not sel:
            continue
        try:
            page.click(sel, timeout=3000)
            page.wait_for_timeout(300)
            return sel
        except Exception:
            continue

    raise ValueError(f"mat-tab: could not click tab — text='{text}'")


def _execute_mat_toggle(page, step, candidates: list[str]) -> str:
    """Click mat-slide-toggle; read aria-checked before+after and store in step context."""
    toggle_sel = None
    for sel in candidates:
        if not sel:
            continue
        if "mat-slide-toggle" in sel or "[role=\"switch\"]" in sel:
            toggle_sel = sel
            break
    if toggle_sel is None and candidates:
        toggle_sel = candidates[0]
    if not toggle_sel:
        raise ValueError("mat-slide-toggle: no selector found")

    try:
        loc = page.locator(toggle_sel).first
        before = loc.get_attribute("aria-checked")
        loc.click()
        page.wait_for_timeout(200)
        after = loc.get_attribute("aria-checked")
        ctx = getattr(step, "context", {}) or {}
        ctx["toggle_before"] = before
        ctx["toggle_after"] = after
        ctx["toggle_target_state"] = after == "true"
        step.context = ctx
        return toggle_sel
    except Exception:
        pass

    # Fallback: plain click
    for sel in candidates:
        if not sel:
            continue
        try:
            page.click(sel, timeout=3000)
            page.wait_for_timeout(200)
            return sel
        except Exception:
            continue

    raise ValueError(f"mat-slide-toggle: could not click toggle")


def _execute_mat_select(page, step, candidates: list[str]) -> str:
    """Open mat-select dropdown, find the option by value, click it."""
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
    for sel in candidates:
        if "mat-select" in sel:
            return sel
    for sel in candidates:
        if sel and ("role=\"combobox\"" in sel or "role='combobox'" in sel.lower()):
            return sel
    return candidates[0] if candidates else ""
