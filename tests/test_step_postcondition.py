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