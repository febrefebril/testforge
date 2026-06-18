"""TestForge — StepExecutor tests."""
import pytest
from unittest.mock import MagicMock
from testforge.runner.step_executor import StepExecutor
from tests.helpers.incremental_fakes import make_fake_step


def _mock_page():
    page = MagicMock()
    page.url = "http://localhost"
    locator = MagicMock()
    locator.first = MagicMock()
    locator.first.get_attribute = MagicMock(return_value=None)
    page.locator = MagicMock(return_value=locator)
    return page


def test_execute_click_success():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("click", "#btn")
    sel = ex.execute(step)
    assert sel == "#btn"
    page.click.assert_called_once()


def test_execute_click_raises_for_missing_selector():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("click", selector="")
    with pytest.raises(ValueError):
        ex.execute(step)


def test_execute_fill_success():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("fill", "#name", value="Joao")
    sel = ex.execute(step)
    assert sel == "#name"
    page.fill.assert_called_once()


def test_execute_select_option_uses_select_option_not_fill():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("select_option", selector="select[name=uf]", value="MT")
    sel = ex.execute(step)
    assert sel == "select[name=uf]"
    page.select_option.assert_called_once()
    page.fill.assert_not_called()
    page.click.assert_not_called()


def test_execute_navigation_only_when_url_differs():
    page = _mock_page()
    page.url = "http://localhost"
    ex = StepExecutor(page)
    step = make_fake_step("navigation", selector="")
    step.url = "http://localhost"
    ex.execute(step, base_url="http://localhost")
    page.goto.assert_not_called()