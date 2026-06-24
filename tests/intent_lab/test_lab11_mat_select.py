"""LAB-11 — Angular Material mat-select handler tests.

Unit tests — no browser required.
Tests cover: detect(), execute() happy path, error cases, and detect_handler() integration.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, call

from testforge.handlers import detect_handler
from testforge.handlers.angular_material import AngularMaterialHandler
from tests.helpers.incremental_fakes import FakeCandidate, FakeTarget, FakeStep


# -- Helpers ------------------------------------------------------------------

def _make_mat_select_step(selector="mat-select[formcontrolname='estado']", value="São Paulo",
                          tag="mat-select", element_id="mat-select-0"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag=tag)
    target.element_id = element_id  # type: ignore[attr-defined]
    return FakeStep(action="click", value=value, target=target)


def _mock_page_with_option(option_text: str = "São Paulo"):
    page = MagicMock()
    option = MagicMock()
    option.inner_text = MagicMock(return_value=option_text)

    options_locator = MagicMock()
    options_locator.count = MagicMock(return_value=1)
    options_locator.nth = MagicMock(return_value=option)

    page.locator = MagicMock(return_value=options_locator)
    page.wait_for_selector = MagicMock()  # overlay open/close succeed silently
    return page, option


# -- 1. detect() by tag -------------------------------------------------------

class TestDetectByTag:
    def test_detect_true_for_mat_select_tag(self):
        h = AngularMaterialHandler()
        assert h.detect([], "", "mat-select") is True

    def test_detect_true_case_insensitive_tag(self):
        h = AngularMaterialHandler()
        assert h.detect([], "", "MAT-SELECT") is True

    def test_detect_false_for_plain_input_tag(self):
        h = AngularMaterialHandler()
        assert h.detect(["#email"], "", "input") is False


# -- 2. detect() by element_id ------------------------------------------------

class TestDetectByElementId:
    def test_detect_true_for_mat_select_element_id(self):
        h = AngularMaterialHandler()
        assert h.detect([], "mat-select-0", "") is True

    def test_detect_true_for_mat_select_element_id_N(self):
        h = AngularMaterialHandler()
        assert h.detect([], "mat-select-42", "") is True

    def test_detect_false_for_unrelated_element_id(self):
        h = AngularMaterialHandler()
        assert h.detect(["#btn"], "btn-submit", "button") is False


# -- 3. detect() by candidate selector ----------------------------------------

class TestDetectBySelector:
    def test_detect_true_for_mat_select_in_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["mat-select[formcontrolname='estado']"], "", "") is True

    def test_detect_false_for_plain_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["#btn", "[name=submit]"], "", "button") is False

    def test_detect_false_for_mat_radio_selector(self):
        # mat-radio-button handled by MaterialComponentDetector, not this handler
        h = AngularMaterialHandler()
        assert h.detect(["mat-radio-button[value='A']"], "mat-radio-0", "") is False


# -- 4. detect_handler() integration ------------------------------------------

class TestDetectHandlerIntegration:
    def test_returns_angular_material_handler_for_mat_select_step(self):
        step = _make_mat_select_step()
        handler = detect_handler(step)
        assert isinstance(handler, AngularMaterialHandler)

    def test_returns_none_for_plain_button_step(self):
        from tests.helpers.incremental_fakes import make_fake_step
        step = make_fake_step("click", "#submit-btn")
        assert detect_handler(step) is None

    def test_returns_none_when_no_target(self):
        step = FakeStep(action="click", target=None)
        assert detect_handler(step) is None


# -- 5. execute() happy path ---------------------------------------------------

class TestExecuteHappyPath:
    def test_execute_clicks_trigger_and_option(self):
        step = _make_mat_select_step(value="São Paulo")
        page, option = _mock_page_with_option("São Paulo")
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert sel == "mat-select[formcontrolname='estado']"
        page.click.assert_called_once()
        option.click.assert_called_once()

    def test_execute_returns_trigger_selector(self):
        step = _make_mat_select_step(
            selector="mat-select[formcontrolname='banco']", value="Itaú"
        )
        page, option = _mock_page_with_option("Itaú")
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert "banco" in sel


# -- 6. execute() error cases --------------------------------------------------

class TestExecuteErrors:
    def test_execute_raises_if_no_selector(self):
        step = FakeStep(action="click", value="SP", target=FakeTarget(candidates=[], tag=""))
        h = AngularMaterialHandler()
        with pytest.raises(ValueError, match="no trigger selector"):
            h.execute(MagicMock(), step)

    def test_execute_raises_if_overlay_never_opens(self):
        step = _make_mat_select_step(value="SP")
        page = MagicMock()
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        page.wait_for_selector = MagicMock(side_effect=PlaywrightTimeout("timeout"))
        h = AngularMaterialHandler()
        with pytest.raises(ValueError, match="overlay did not open"):
            h.execute(page, step)

    def test_execute_raises_if_option_not_found(self):
        step = _make_mat_select_step(value="Opcao Inexistente")
        page = MagicMock()
        # wait_for_selector succeeds (overlay opens), but locator returns empty
        page.wait_for_selector = MagicMock()
        empty = MagicMock()
        empty.count = MagicMock(return_value=0)
        page.locator = MagicMock(return_value=empty)
        h = AngularMaterialHandler()
        with pytest.raises(ValueError, match="not found in overlay"):
            h.execute(page, step)
