"""CS-2 — production-shaped fixture for the 4 fill helpers.

Reproduces the SIOPI bug class: Material currency / date / CPF inputs
that implement their mask in JS without exposing the `currencymask`
attribute. The fixture lives at
`tests/test_pages/runner_fills/index.html` and is served via file://.

Each of the four fill helpers (_execute_fill, _fill_input,
_fill_by_aria_label, _try_data_fill) is exercised against each input.
After each helper runs, the DOM value is read back and compared to the
expected formatted output. Divergence between helpers fails the test.

This is the regression guard for CS-1 + CS-2 + CS-3: if any future
contributor breaks _fill_masked or re-introduces inline mask logic in
a helper, one of these cases goes red in CI.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


_FIXTURE = (
    Path(__file__).resolve().parent / "test_pages" / "runner_fills" / "index.html"
)
_FIXTURE_URL = "file://" + str(_FIXTURE)


def _make_step(action, selector, value=None):
    from tests.helpers.incremental_fakes import make_fake_step
    return make_fake_step(action, selector, value=value)


@pytest.fixture(scope="module")
def browser_page():
    """Module-scoped browser to keep startup cost amortized."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        try:
            browser.close()
        except Exception:
            pass


def _reload(page):
    page.goto(_FIXTURE_URL)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(150)


@pytest.mark.slow
class TestCS2CurrencyMaskAllHelpers:
    """SIOPI shape: input placeholder=R$0,00, no currencymask attr."""

    def test_execute_fill_writes_currency_value(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        step = _make_step("fill", "#prestacao", value="1.000,00")
        ex._execute_fill(step, ["#prestacao"], data_values=None, field_value_map=None)
        assert browser_page.locator("#prestacao").input_value() == "R$ 1.000,00"

    def test_fill_input_writes_currency_value(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        assert ex._fill_input(browser_page, label="Prestação desejada *", value="1.000,00")
        assert browser_page.locator("#prestacao").input_value() == "R$ 1.000,00"

    def test_fill_by_aria_label_writes_currency_value(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        step = _make_step("click", "#prestacao")
        ex._fill_by_aria_label(step, {"Prestação desejada *": "1.000,00"})
        assert browser_page.locator("#prestacao").input_value() == "R$ 1.000,00"

    def test_try_data_fill_writes_currency_value(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        step = _make_step("click", "#prestacao")
        step.target.label = "Prestação desejada *"
        ex._try_data_fill(step, "#prestacao", {"Prestação desejada *": "1.000,00"})
        assert browser_page.locator("#prestacao").input_value() == "R$ 1.000,00"


@pytest.mark.slow
class TestCS2DateMaskAllHelpers:
    """Date mask: placeholder=DD/MM/AAAA."""

    def test_execute_fill_writes_date(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        step = _make_step("fill", "#nascimento", value="03/03/1994")
        ex._execute_fill(step, ["#nascimento"], data_values=None, field_value_map=None)
        assert browser_page.locator("#nascimento").input_value() == "03/03/1994"

    def test_fill_input_writes_date(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        assert ex._fill_input(browser_page, label="Data de nascimento", value="03/03/1994")
        assert browser_page.locator("#nascimento").input_value() == "03/03/1994"


@pytest.mark.slow
class TestCS2CpfMask:
    """CPF: strip-to-digits mask but placeholder is 000.000.000-00."""

    def test_execute_fill_writes_cpf(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        step = _make_step("fill", "#cpf", value="12345678900")
        ex._execute_fill(step, ["#cpf"], data_values=None, field_value_map=None)
        assert browser_page.locator("#cpf").input_value() == "123.456.789-00"

    def test_fill_input_writes_cpf_from_formatted(self, browser_page):
        """User supplies the formatted string; runner strips and types digits."""
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        assert ex._fill_input(browser_page, label="CPF", value="123.456.789-00")
        assert browser_page.locator("#cpf").input_value() == "123.456.789-00"


@pytest.mark.slow
class TestCS2PlainText:
    """Unmasked input — el.fill path."""

    def test_fill_input_writes_plain_text(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        assert ex._fill_input(browser_page, label="Nome completo", value="Joao Silva")
        assert browser_page.locator("#nome").input_value() == "Joao Silva"


@pytest.mark.slow
class TestCS2RerunDoesNotConcatenate:
    """The pivotal failure shape: healing retry calling a helper twice
    must NOT produce 'R$ 1.000.001.000,00'. Triple-click clear is the
    guard. This case explicitly fails on pre-hotfix-16 code."""

    def test_two_fills_overwrite_not_append(self, browser_page):
        from testforge.runner.step_executor import StepExecutor
        _reload(browser_page)
        ex = StepExecutor(browser_page)
        # First fill
        ex._fill_input(browser_page, label="Prestação desejada *", value="1.000,00")
        assert browser_page.locator("#prestacao").input_value() == "R$ 1.000,00"
        # Second fill — must replace, not append
        ex._fill_input(browser_page, label="Prestação desejada *", value="2.500,75")
        assert browser_page.locator("#prestacao").input_value() == "R$ 2.500,75"
