"""Hotfix 20: AngularMaterialHandler must keep click-only datepicker sequences.

Regression: pre-hotfix-20 the handler's _dedup_datepicker_sequences method
classified any datepicker sequence with no follow-up `fill` step as
"abandoned" and suppressed every calendar nav click. In production
(Caixa SIOPI), the date input has a mask that suppresses the input event,
so the user selects a date entirely by clicking calendar cells — the
recorder captures clicks, no fill ever fires. The handler's abandoned
branch suppressed those clicks at runtime, leaving the date input empty
and breaking the downstream Calcular button.

Hotfix 20 adds a third branch: if the last calendar click in the
sequence landed on a day cell (mat-calendar-body-cell or a numeric text
target inside the overlay), the sequence is treated as click-only
completion. All clicks are kept. Tests below pin both this case and
the original two (fill follow-up; truly abandoned).
"""
from __future__ import annotations

from testforge.handlers.angular_material import AngularMaterialHandler
from testforge.semantic.model import (
    SemanticAction, SemanticTarget, LocatorCandidate,
)


def _make_step(action, selector, value="", overlay=False, text=""):
    target = SemanticTarget(
        candidates=[LocatorCandidate(strategy="css", selector=selector, score=1.0)],
        text=text,
    )
    step = SemanticAction(action=action, target=target, value=value)
    if overlay:
        step.context["overlay_step"] = True
    return step


def test_click_only_date_selection_keeps_all_clicks():
    """SIOPI shape: toggle + nav + day-cell click, no fill follow-up."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "span.mat-mdc-button-touch-target"
                            ".mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-period-button",
                   overlay=True, text="JUN 2026"),
        _make_step("click", "button.mat-calendar-previous-button span",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="1994"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="MAR"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="3"),
        _make_step("click", "input[aria-label='Prestação']"),  # next field
    ]
    handler._dedup_datepicker_sequences(steps)
    # The datepicker steps must NOT be marked datepicker_dedup
    for i, s in enumerate(steps[:6]):
        assert s.skip_reason != "datepicker_dedup", (
            f"step {i} was wrongly suppressed: {s.skip_reason}"
        )
    # The next-field click stays as-is
    assert steps[6].skip_reason == ""


def test_fill_followup_still_suppresses_clicks():
    """Classic shape: toggle + nav + date fill — clicks suppressed."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="15"),
        _make_step("fill", "input[name='date']", value="15/03/2026"),
    ]
    handler._dedup_datepicker_sequences(steps)
    # Clicks before the fill are suppressed
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    assert steps[2].skip_reason == "datepicker_dedup"
    # The date fill is the canonical intent — kept
    assert steps[3].skip_reason == ""


def test_truly_abandoned_sequence_still_suppresses_calendar():
    """User opened the picker, navigated, then clicked outside without
    picking a day. The non-calendar click is kept; calendar nav is
    suppressed."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),
        # Calendar previous-button without a day cell at the end
        _make_step("click", "button#somewhere-else"),  # non-calendar click
    ]
    handler._dedup_datepicker_sequences(steps)
    # The two calendar steps are suppressed
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    # The escape click stays
    assert steps[2].skip_reason == ""


def test_day_cell_detected_by_numeric_text_in_overlay():
    """Some selector chains do not carry mat-calendar-body-cell. The
    fallback detection uses numeric text inside an overlay step."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        # No mat-calendar-body-cell in the selector, but text is a day
        _make_step("click", "span.some-other-class", overlay=True, text="15"),
        _make_step("click", "input[aria-label='Prestação']"),
    ]
    handler._dedup_datepicker_sequences(steps)
    assert steps[0].skip_reason == ""
    assert steps[1].skip_reason == ""
    assert steps[2].skip_reason == ""
