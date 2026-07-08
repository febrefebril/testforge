"""RC-15: SmartStepRunner adaptive timeout — networkidle before visible."""
import pytest
from unittest.mock import MagicMock, call, patch


@pytest.fixture
def page():
    return MagicMock()


@pytest.fixture
def runner(page):
    from testforge.runner.fallback_runner import SmartStepRunner
    return SmartStepRunner(page)


@pytest.mark.unit
class TestWaitForWhenAngularHydrationThenAdaptiveTimeout:

    def test_networkidle_called_before_visible(self, runner, page):
        """RC-15: visibility_wait strategy calls networkidle then wait_for_selector."""
        # Arrange
        page.wait_for_load_state.return_value = None
        page.wait_for_selector.return_value = None
        page.fill.return_value = None

        # Act
        runner.execute({"selector": "#campo", "action": "fill", "value": "x"}, strategy="visibility_wait")

        # Assert — networkidle must precede wait_for_selector
        page.wait_for_load_state.assert_called_once_with("networkidle", timeout=5000)
        page.wait_for_selector.assert_called_once_with("#campo", state="visible", timeout=runner.WAIT_TIMEOUT)
        load_call_idx = page.method_calls.index(call.wait_for_load_state("networkidle", timeout=5000))
        visible_call_idx = page.method_calls.index(call.wait_for_selector("#campo", state="visible", timeout=runner.WAIT_TIMEOUT))
        assert load_call_idx < visible_call_idx

    def test_networkidle_timeout_swallowed(self, runner, page):
        """RC-15: networkidle timeout does not abort step — still tries visible."""
        from playwright.sync_api import TimeoutError as PWTimeout
        page.wait_for_load_state.side_effect = PWTimeout("networkidle timeout")
        page.wait_for_selector.return_value = None
        page.fill.return_value = None

        result = runner.execute({"selector": "#f", "action": "fill", "value": "v"}, strategy="visibility_wait")

        assert result is True
        page.wait_for_selector.assert_called_once_with("#f", state="visible", timeout=runner.WAIT_TIMEOUT)

    def test_wait_for_enabled_also_adaptive(self, runner, page):
        """RC-15: wait_for_enabled strategy uses same adaptive path."""
        page.wait_for_load_state.return_value = None
        page.wait_for_selector.return_value = None
        page.fill.return_value = None

        runner.execute({"selector": "#btn", "action": "click"}, strategy="wait_for_enabled")

        page.wait_for_load_state.assert_called_once_with("networkidle", timeout=5000)
        page.wait_for_selector.assert_called_once_with("#btn", state="visible", timeout=runner.WAIT_TIMEOUT)
