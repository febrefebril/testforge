"""TestForge — StepPostconditionValidator tests."""
from unittest.mock import MagicMock
from testforge.runner.step_postcondition import StepPostconditionValidator
from tests.helpers.incremental_fakes import make_fake_step


def _mock_page(url="http://localhost"):
    page = MagicMock()
    page.url = url
    return page


def test_fill_postcondition_validates_value():
    page = _mock_page()
    page.locator.return_value.first.input_value = MagicMock(return_value="12345")
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#cpf", value="12345")
    r = val.validate(step)
    assert r.passed is True


def test_fill_postcondition_value_mismatch():
    page = _mock_page()
    page.locator.return_value.first.input_value = MagicMock(return_value="99999")
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#cpf", value="12345")
    r = val.validate(step)
    assert r.passed is False
    assert "value_mismatch" in r.failures


def test_select_postcondition_validates_selected_value():
    page = _mock_page()
    page.locator.return_value.first.evaluate = MagicMock(
        return_value={"value": "MT", "text": "MT"}
    )
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("select_option", "select[name=uf]", value="MT")
    r = val.validate(step)
    assert r.passed is True


def test_select_postcondition_selected_value_mismatch():
    page = _mock_page()
    page.locator.return_value.first.evaluate = MagicMock(
        return_value={"value": "DF", "text": "DF"}
    )
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("select_option", "select[name=uf]", value="MT")
    r = val.validate(step)
    assert r.passed is False


def test_click_with_causes_navigation_requires_url_change():
    page = _mock_page(url="http://localhost/result")
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("click", "#btn", context={"causes_navigation": True})
    r = val.validate(step, url_before="http://localhost/form")
    assert r.passed is True


def test_click_navigation_fails_when_url_unchanged():
    page = _mock_page(url="http://localhost/same")
    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("click", "#btn", context={"causes_navigation": True})
    r = val.validate(step, url_before="http://localhost/same")
    assert r.passed is False
    assert "url_not_changed" in r.failures


def test_fill_mask_currency_matches_by_numeric_magnitude():
    page = _mock_page()
    el = page.locator.return_value.first
    el.input_value = MagicMock(return_value="R$ 1.000.000,00")

    def _attr(name, timeout=200):
        return "currency" if name == "currencymask" else None

    el.get_attribute = MagicMock(side_effect=_attr)

    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#valor", value="1000000.00")
    r = val.validate(step)
    assert r.passed is True
    assert r.checks.get("mask_amount_matches") is True


def test_fill_mask_currency_detects_mismatch():
    page = _mock_page()
    el = page.locator.return_value.first
    el.input_value = MagicMock(return_value="R$ 900,00")

    def _attr(name, timeout=200):
        return "currency" if name == "currencymask" else None

    el.get_attribute = MagicMock(side_effect=_attr)

    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#valor", value="1000,00")
    r = val.validate(step)
    assert r.passed is False
    assert "mask_amount_mismatch" in r.failures


def test_fill_mask_date_matches_after_normalization():
    page = _mock_page()
    el = page.locator.return_value.first
    el.input_value = MagicMock(return_value="31/12/2026")

    def _attr(name, timeout=200):
        if name == "currencymask":
            return None
        if name == "mask":
            return "99/99/9999"
        return None

    el.get_attribute = MagicMock(side_effect=_attr)

    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#data", value="2026-12-31")
    r = val.validate(step)
    assert r.passed is True
    assert r.checks.get("mask_date_matches") is True


def test_fill_mask_falls_back_to_non_empty_when_not_parseable():
    page = _mock_page()
    el = page.locator.return_value.first
    el.input_value = MagicMock(return_value="abc")

    def _attr(name, timeout=200):
        return "custom-mask" if name == "mask" else None

    el.get_attribute = MagicMock(side_effect=_attr)

    val = StepPostconditionValidator(page, oracle_runner=None)
    step = make_fake_step("fill", "#campo", value="zzz")
    r = val.validate(step)
    assert r.passed is True
    assert r.checks.get("mask_input_non_empty") is True