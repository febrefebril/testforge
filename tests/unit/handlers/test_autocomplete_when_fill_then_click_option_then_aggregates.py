"""RC-22: fill on autocomplete + mat-option click → search_and_select."""
import pytest
from testforge.semantic.model import SemanticAction, SemanticTarget, LocatorCandidate
from testforge.handlers.angular_material import AngularMaterialHandler


def _autocomplete_fill(value, selector="input[aria-autocomplete]"):
    return SemanticAction(
        action="fill",
        value=value,
        target=SemanticTarget(
            candidates=[LocatorCandidate(strategy="css_path", selector=selector, score=0.7)],
        ),
    )


def _option_click(text="Option A", selector="mat-option:nth-of-type(1)"):
    return SemanticAction(
        action="click",
        target=SemanticTarget(
            text=text,
            accessible_name=text,
            candidates=[LocatorCandidate(strategy="css_path", selector=selector, score=0.7)],
        ),
    )


@pytest.fixture
def handler():
    return AngularMaterialHandler()


@pytest.mark.unit
class TestAutocompleteWhenFillThenClickOptionThenAggregates:

    def test_action_becomes_search_and_select(self, handler):
        """RC-22: fill + mat-option click → search_and_select action."""
        # Arrange
        steps = [
            _autocomplete_fill("Lisboa"),
            _option_click("Lisboa - PT"),
        ]

        # Act
        handler.normalize(steps)

        # Assert
        assert steps[0].action == "search_and_select"

    def test_search_term_in_context(self, handler):
        """RC-22: context.search_term = original fill value."""
        steps = [
            _autocomplete_fill("Lisboa"),
            _option_click("Lisboa - PT"),
        ]

        handler.normalize(steps)

        assert steps[0].context["search_term"] == "Lisboa"

    def test_option_text_in_context(self, handler):
        """RC-22: context.option_text = clicked option text."""
        steps = [
            _autocomplete_fill("SP"),
            _option_click("São Paulo - SP"),
        ]

        handler.normalize(steps)

        assert steps[0].context["option_text"] == "São Paulo - SP"

    def test_option_click_suppressed(self, handler):
        """RC-22: option click step suppressed after aggregation."""
        steps = [
            _autocomplete_fill("t"),
            _option_click("Test Company"),
        ]

        handler.normalize(steps)

        assert steps[1].skip_reason == "autocomplete_aggregated"

    def test_non_autocomplete_fill_not_affected(self, handler):
        """RC-22: fill on regular input (no autocomplete marker) unchanged."""
        steps = [
            SemanticAction(
                action="fill",
                value="regular text",
                target=SemanticTarget(
                    candidates=[LocatorCandidate(strategy="css_path", selector="#nome", score=0.8)],
                ),
            ),
            _option_click("Some Option"),
        ]

        handler.normalize(steps)

        assert steps[0].action == "fill"

    def test_short_search_term_aggregated(self, handler):
        """RC-22: even a single-char fill ('t') aggregates when followed by option click."""
        steps = [
            _autocomplete_fill("t", selector="input[aria-autocomplete='list']"),
            _option_click("Test User"),
        ]

        handler.normalize(steps)

        assert steps[0].action == "search_and_select"
        assert steps[0].context["search_term"] == "t"

    def test_fill_without_option_unchanged(self, handler):
        """RC-22: autocomplete fill not followed by option click stays as fill."""
        steps = [
            _autocomplete_fill("São Paulo"),
            SemanticAction(
                action="click",
                target=SemanticTarget(
                    candidates=[LocatorCandidate(strategy="css_path", selector="#submit-btn", score=0.8)],
                ),
            ),
        ]

        handler.normalize(steps)

        assert steps[0].action == "fill"
