"""RC-13: calendar nav + valid DD/MM/YYYY fill → single select_date action."""
import pytest
from testforge.semantic.model import SemanticAction, SemanticTarget, LocatorCandidate
from testforge.handlers.angular_material import AngularMaterialHandler


def _cal_click(selector, text=""):
    """Calendar click step."""
    return SemanticAction(
        action="click",
        target=SemanticTarget(
            text=text,
            candidates=[LocatorCandidate(strategy="css_path", selector=selector, score=0.6)],
        ),
    )


def _dp_toggle():
    return _cal_click("mat-datepicker-toggle button", text="")


def _period_button():
    return _cal_click(".mat-calendar-period-button", text="Choose month and year")


def _prev_button():
    return _cal_click(".mat-calendar-previous-button > span", text="")


def _cell_click(selector, text=""):
    return _cal_click(selector + " .mat-calendar-body-cell-content", text=text)


def _date_fill(value, selector=".mat-datepicker-input"):
    return SemanticAction(
        action="fill",
        value=value,
        target=SemanticTarget(
            placeholder="DD/MM/AAAA",
            candidates=[LocatorCandidate(strategy="css_path", selector=selector, score=0.7)],
        ),
    )


@pytest.fixture
def handler():
    return AngularMaterialHandler()


@pytest.mark.unit
class TestDatePickerWhen7ClicksMaterialThenAggregates:

    def test_select_date_action_replaces_fill(self, handler):
        """RC-13: 7-click calendar sequence → fill action becomes select_date."""
        # Arrange — mirrors R7a SIMULADOR recording sequence
        steps = [
            _dp_toggle(),
            _period_button(),
            _prev_button(),
            _prev_button(),
            _cell_click("tr:nth-of-type(5) > td:nth-of-type(1)", text="1984"),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(1)", text="JAN"),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(3)", text="3"),
            _date_fill("03/01/1984"),
        ]

        # Act
        handler.normalize(steps)

        # Assert — fill converted to select_date
        fill_step = steps[-1]
        assert fill_step.action == "select_date"
        assert fill_step.value == "03/01/1984"

    def test_calendar_nav_clicks_suppressed(self, handler):
        """RC-13: calendar navigation clicks get skip_reason=datepicker_aggregated."""
        steps = [
            _dp_toggle(),
            _period_button(),
            _prev_button(),
            _cell_click("tr:nth-of-type(5) > td", text="1984"),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(1)", text="JAN"),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(3)", text="3"),
            _date_fill("03/01/1984"),
        ]

        handler.normalize(steps)

        # Nav clicks 0-5 must be suppressed; fill (now select_date) must not be
        for step in steps[:-1]:
            assert step.skip_reason in ("datepicker_aggregated", "datepicker_dedup"), (
                f"expected suppressed, got {step.skip_reason!r} for {step!r}"
            )
        assert not steps[-1].skip_reason

    def test_context_flag_set(self, handler):
        """RC-13: select_date carries date_from_calendar=True in context."""
        steps = [
            _dp_toggle(),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(3)", text="15"),
            _date_fill("15/06/2024"),
        ]

        handler.normalize(steps)

        assert steps[-1].action == "select_date"
        assert steps[-1].context.get("date_from_calendar") is True

    def test_raw_digit_fill_not_aggregated(self, handler):
        """RC-13: garbled fill ('01011984') keeps old behavior — clicks kept, fill skipped."""
        steps = [
            _dp_toggle(),
            _cell_click("tr:nth-of-type(2) > td:nth-of-type(3)", text="1"),
            _date_fill("01011984"),  # raw digits, no slash
        ]

        handler.normalize(steps)

        # Old behavior: fill gets datepicker_picker_echo_fill, clicks are kept
        fill_step = steps[-1]
        assert fill_step.skip_reason == "datepicker_picker_echo_fill"
        assert fill_step.action == "fill"

    def test_non_material_datepicker_fill_unaffected(self, handler):
        """RC-13: regular fill after non-datepicker click unchanged."""
        steps = [
            SemanticAction(
                action="click",
                target=SemanticTarget(
                    candidates=[LocatorCandidate(strategy="css_path", selector="#regular-btn", score=0.8)],
                ),
            ),
            SemanticAction(
                action="fill",
                value="hello",
                target=SemanticTarget(
                    candidates=[LocatorCandidate(strategy="css_path", selector="#name-input", score=0.8)],
                ),
            ),
        ]

        handler.normalize(steps)

        assert steps[1].action == "fill"
        assert not steps[1].skip_reason
