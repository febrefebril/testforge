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

class TestHotfix16FillInputClearAndDigits:
    """Hotfix 16: _fill_input must clear field and strip to raw digits."""

    def _masked_input(self, currencymask=True, date=False):
        page = MagicMock()
        page.url = "http://localhost"
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(side_effect=lambda attr: (
            "true" if attr == "currencymask" and currencymask
            else ("DD/MM/AAAA" if attr == "placeholder" and date else None)
        ))
        page.locator = MagicMock(return_value=el)
        return page, el

    def test_currency_mask_clears_with_triple_click(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        assert ex._fill_input(page, label="Renda", value="1.000,00") is True
        # First click focuses; triple-click selects all.
        click_calls = el.click.call_args_list
        assert any(
            call.kwargs.get("click_count") == 3 for call in click_calls
        ), f"expected click_count=3, got {click_calls}"

    def test_currency_mask_types_raw_digits_not_inflated(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Renda", value="1.000,00")
        # Must type "100000" — the raw digits — NOT "10000000".
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["100000"], f"got {typed}"

    def test_currency_mask_pure_digits_pass_through(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Renda", value="500000")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["500000"], f"got {typed}"

    def test_date_mask_keeps_slashes(self):
        page, el = self._masked_input(currencymask=False, date=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nascimento", value="03/03/1994")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["03/03/1994"], f"got {typed}"

    def test_date_mask_clears_with_triple_click(self):
        page, el = self._masked_input(currencymask=False, date=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nascimento", value="03/03/1994")
        assert any(
            c.kwargs.get("click_count") == 3 for c in el.click.call_args_list
        )

    def test_non_masked_uses_fill(self):
        page = MagicMock()
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(return_value=None)
        page.locator = MagicMock(return_value=el)
        ex = StepExecutor(page)
        assert ex._fill_input(page, label="Nome", value="Joao") is True
        el.fill.assert_called_once()


class TestHotfix17PlaceholderMaskFallback:
    """Hotfix 17: currency mask detected by placeholder when attribute missing."""

    def _placeholder_input(self, placeholder):
        page = MagicMock()
        page.url = "http://localhost"
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(side_effect=lambda attr: (
            placeholder if attr == "placeholder" else None
        ))
        page.locator = MagicMock(return_value=el)
        return page, el

    def test_caixa_r_placeholder_triggers_currency_path(self):
        """Caixa SIOPI inputs use placeholder R$0,00 without currencymask attr."""
        page, el = self._placeholder_input("R$0,00")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Prestação", value="1.000,00")
        # Should have typed raw digits, not the formatted string.
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["100000"], f"got {typed}"
        # And cleared via triple-click first.
        assert any(
            c.kwargs.get("click_count") == 3
            for c in el.click.call_args_list
        )

    def test_lowercase_0_00_placeholder_triggers_mask_path(self):
        page, el = self._placeholder_input("0,00")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Valor", value="5.000,50")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["500050"], f"got {typed}"

    def test_plain_text_placeholder_uses_fill(self):
        page, el = self._placeholder_input("Nome completo")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nome", value="Joao Silva")
        # No press_sequentially — non-masked path goes through el.fill
        el.fill.assert_called_once()
        el.press_sequentially.assert_not_called()
