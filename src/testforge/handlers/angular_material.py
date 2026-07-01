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

        self._dedup_datepicker_sequences(steps)

    def _dedup_datepicker_sequences(self, steps: list) -> None:
        """Collapse Angular Material datepicker calendar navigation into the text fill.

        Pattern: (open toggle) + (calendar nav clicks) + (fill on date input)
        Only the fill is the canonical intent. Calendar navigation is fragile because it
        depends on which month/year the calendar opens at, which changes between runs.

        Three cases:

        - **Fill follow-up**: toggle + nav + date fill → suppress toggle+nav,
          keep fill. The fill is the canonical intent and reproduces deterministically.

        - **Click-only completion** (e.g. Caixa SIOPI): the date input has a
          mask that suppresses the input event, so no fill is ever recorded.
          The user navigates the calendar with clicks and picks a day cell.
          The LAST click in the sequence lands on a `mat-calendar-body-cell`
          (the day picker). In this case the click sequence IS the canonical
          intent — there is no other way to set the date — so we KEEP the
          clicks. Suppressing them (the pre-hotfix-20 behavior) left the
          date input empty at run time.

        - **True abandoned**: user clicked outside the calendar without
          picking a day → suppress the calendar nav clicks. The non-calendar
          click that ended the sequence is kept.
        """
        import re

        _DP_MARKERS = ("mat-datepicker-toggle", "mat-calendar", "cdk-overlay", "data-mat-calendar")
        # The day picker that completes a click-only date selection. After
        # a user clicks one of these cells the value lands on the date
        # input via the picker, no input event fires (mask suppresses it).
        _DAY_CELL_MARKERS = (
            "mat-calendar-body-cell", "mat-calendar-body-cell-content",
        )

        def _step_sels(step) -> list:
            if not step.target or not step.target.candidates:
                return []
            return [c.selector for c in step.target.candidates if c.selector]

        def _has_dp_marker(step) -> bool:
            return any(m in sel for sel in _step_sels(step) for m in _DP_MARKERS)

        def _is_calendar_step(step) -> bool:
            return _has_dp_marker(step) or bool(step.context.get("overlay_step"))

        def _is_day_cell_click(step) -> bool:
            """The terminal click of a click-only date selection."""
            if step.action != "click":
                return False
            if any(m in sel for sel in _step_sels(step) for m in _DAY_CELL_MARKERS):
                return True
            # Fallback: target text is a 1-2 digit number (day of month) and
            # the step is inside the overlay. This catches the case where
            # the selector chain does not carry mat-calendar-body-cell but
            # the rendered cell still produced a numeric click target.
            if step.context.get("overlay_step") and step.target is not None:
                text = (getattr(step.target, "text", "") or "").strip()
                if re.fullmatch(r"\d{1,2}", text):
                    return True
            return False

        def _is_date_value(val: str) -> bool:
            val = (val or "").strip()
            # BR DD/MM/YYYY or ISO YYYY-MM-DD
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', val) or re.match(r'\d{4}-\d{2}-\d{2}', val):
                return True
            # Hotfix 22 (legacy): recordings gravados antes do date-skip fix
            # em overlay tinham raw_value com todos os digitos concatenados
            # (`01011968`). Aceita 6-8 digitos consecutivos como candidato
            # a data (DDMMYY/DDMMYYYY/YYYYMMDD).
            if re.fullmatch(r'\d{6,8}', val):
                return True
            return False

        _DATE_PLACEHOLDER_RE = re.compile(
            r'^\s*[DdMmAaYy][DdMmAaYyHhSs/\-\.]{5,}\s*$'
        )

        def _fill_target_is_material_datepicker(step) -> bool:
            """Detect if a fill target is a Material datepicker input (readonly-ish).

            When the user picks a date via calendar clicks, Angular Material writes
            the value back to the bound input which fires an input event — the
            recorder captures this as a `fill`, but at runtime the input often
            rejects direct writes (mask + validators + sometimes readonly). In
            those cases the click sequence IS the canonical intent, not the fill.
            """
            tgt = getattr(step, "target", None)
            if tgt is None:
                return False
            ph = (getattr(tgt, "placeholder", "") or "").strip()
            if ph and _DATE_PLACEHOLDER_RE.match(ph):
                return True
            eid = (getattr(tgt, "element_id", "") or "").strip()
            if eid.startswith("mat-input-"):
                return True
            for sel in _step_sels(step):
                if "matDatepicker" in sel or "mat-datepicker-input" in sel:
                    return True
            return False

        i = 0
        while i < len(steps):
            step = steps[i]
            if step.skip_reason or step.action != "click":
                i += 1
                continue
            if not _has_dp_marker(step):
                i += 1
                continue

            # Found a datepicker-related click. Scan forward.
            seq_start = i
            found_fill = -1
            last_calendar_click = -1  # hotfix 20: track last calendar click
            j = i + 1

            while j < len(steps) and j < i + 20:
                s = steps[j]

                if s.action == "fill":
                    if _is_date_value(s.value or ""):
                        found_fill = j
                    # Stop at any fill: date fill = success, non-date fill = calendar abandoned
                    break

                if s.action == "navigation":
                    break

                if s.action == "click" and not s.skip_reason:
                    if _is_calendar_step(s):
                        last_calendar_click = j
                    else:
                        # User clicked outside the calendar — sequence abandoned
                        break

                j += 1

            picker_echo_fill = (
                found_fill > seq_start
                and last_calendar_click > seq_start
                and _is_day_cell_click(steps[last_calendar_click])
                and _fill_target_is_material_datepicker(steps[found_fill])
            )

            if picker_echo_fill:
                # Hotfix 22: Material datepicker input received a fill because
                # the picker wrote to it — the click sequence is the canonical
                # intent. Keep clicks; skip the picker-echo fill (input is
                # effectively readonly at runtime).
                steps[found_fill].skip_reason = "datepicker_picker_echo_fill"
                i = found_fill + 1
            elif found_fill > seq_start:
                # Completed via fill: suppress toggle + nav, keep date fill.
                for k in range(seq_start, found_fill):
                    if not steps[k].skip_reason:
                        steps[k].skip_reason = "datepicker_dedup"
                i = found_fill + 1
            elif (
                last_calendar_click > seq_start
                and _is_day_cell_click(steps[last_calendar_click])
            ):
                # Hotfix 20: click-only completion (e.g. SIOPI). The last
                # click was on a day cell — the picker delivers the date
                # without any fill event. KEEP every click in the
                # sequence; they ARE the canonical intent. Re-running them
                # at runtime reproduces the recorded selection.
                i = last_calendar_click + 1
            else:
                # True abandoned: suppress only the calendar steps in range.
                # The non-calendar click that ended the sequence is kept.
                for k in range(seq_start, j):
                    if not steps[k].skip_reason and _is_calendar_step(steps[k]):
                        steps[k].skip_reason = "datepicker_dedup"
                i = j

    def heal(self, evidence, error: str) -> Optional[object]:
        return None


# -- type predicates -----------------------------------------------------------

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


# -- execute helpers -----------------------------------------------------------

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
