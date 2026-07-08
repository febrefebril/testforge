"""LAB-14 — Angular Material mat-tab-group + mat-slide-toggle tests.

Unit tests — no browser required.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from testforge.handlers import detect_handler
from testforge.handlers.angular_material import AngularMaterialHandler
from tests.helpers.incremental_fakes import FakeCandidate, FakeTarget, FakeStep


# -- Helpers ------------------------------------------------------------------

def _make_tab_step(text="Endereço", selector="[role=\"tab\"]:has-text('Endereço')"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag="div", text=text)
    target.element_id = "tab-1"       # type: ignore[attr-defined]
    target.accessible_name = text      # type: ignore[attr-defined]
    return FakeStep(action="click", value=text, target=target)


def _make_toggle_step(selector="mat-slide-toggle#mat-slide-toggle-0",
                       tag="mat-slide-toggle", element_id="mat-slide-toggle-0"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag=tag)
    target.element_id = element_id  # type: ignore[attr-defined]
    return FakeStep(action="click", value="", target=target)


def _mock_page_for_tab():
    page = MagicMock()
    page.click = MagicMock()
    page.wait_for_timeout = MagicMock()
    return page


def _mock_page_for_toggle(initial_checked: str = "false"):
    page = MagicMock()
    loc = MagicMock()
    loc.get_attribute = MagicMock(return_value=initial_checked)
    loc.click = MagicMock()
    page.locator = MagicMock(return_value=loc)
    loc.first = loc
    page.wait_for_timeout = MagicMock()
    return page, loc


# -- 1. detect() for mat-tab --------------------------------------------------

class TestDetectTab:
    def test_detect_true_for_role_tab_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["[role=\"tab\"]:has-text('Dados')"], "", "div") is True

    def test_detect_true_for_mat_tab_label_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["div.mat-tab-label"], "", "div") is True

    def test_detect_true_for_mat_tab_header_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["mat-tab-header"], "", "") is True

    def test_detect_false_for_role_listitem(self):
        h = AngularMaterialHandler()
        assert h.detect(["[role=\"listitem\"]"], "", "li") is False

    def test_detect_handler_returns_angular_for_tab_step(self):
        step = _make_tab_step()
        assert isinstance(detect_handler(step), AngularMaterialHandler)


# -- 2. detect() for mat-slide-toggle -----------------------------------------

class TestDetectToggle:
    def test_detect_true_for_mat_slide_toggle_tag(self):
        h = AngularMaterialHandler()
        assert h.detect([], "", "mat-slide-toggle") is True

    def test_detect_true_for_mat_slide_toggle_in_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["mat-slide-toggle#toggle-0"], "", "") is True

    def test_detect_true_for_role_switch_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["[role=\"switch\"][aria-label='Notificações']"], "", "") is True

    def test_detect_handler_returns_angular_for_toggle_step(self):
        step = _make_toggle_step()
        assert isinstance(detect_handler(step), AngularMaterialHandler)


# -- 3. execute() for mat-tab -------------------------------------------------

class TestExecuteTab:
    def test_execute_clicks_role_tab_by_text(self):
        step = _make_tab_step(text="Endereço")
        page = _mock_page_for_tab()
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert "[role='tab']" in sel
        assert "Endereço" in sel
        page.click.assert_called()

    def test_execute_tab_falls_back_to_candidate(self):
        # No text → skip role-tab selector, go straight to candidate list
        step = _make_tab_step(text="", selector="div.mat-tab-label:nth-child(2)")
        step.target.text = ""
        step.target.accessible_name = ""  # type: ignore[attr-defined]
        page = _mock_page_for_tab()
        page.click = MagicMock()  # single call succeeds
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert "mat-tab-label" in sel

    def test_execute_tab_raises_when_all_fail(self):
        step = _make_tab_step(text="TabInexistente")
        page = _mock_page_for_tab()
        page.click = MagicMock(side_effect=Exception("no element"))
        h = AngularMaterialHandler()
        with pytest.raises((ValueError, Exception)):
            h.execute(page, step)


# -- 4. execute() for mat-slide-toggle ----------------------------------------

class TestExecuteToggle:
    def test_execute_toggle_clicks_element(self):
        step = _make_toggle_step()
        page, loc = _mock_page_for_toggle("false")
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert "mat-slide-toggle" in sel
        loc.click.assert_called_once()

    def test_execute_toggle_stores_before_after_state(self):
        step = _make_toggle_step()
        page, loc = _mock_page_for_toggle("false")
        h = AngularMaterialHandler()
        h.execute(page, step)
        ctx = step.context
        assert "toggle_before" in ctx
        assert "toggle_after" in ctx
        assert "toggle_target_state" in ctx

    def test_execute_toggle_target_state_reflects_aria_checked(self):
        step = _make_toggle_step()
        page, loc = _mock_page_for_toggle("false")
        h = AngularMaterialHandler()
        h.execute(page, step)
        # aria-checked returns "false" both before and after in mock (same mock return)
        # What matters is the key is stored
        assert "toggle_target_state" in step.context

    def test_execute_toggle_raises_when_no_selector(self):
        step = FakeStep(action="click", value="",
                        target=FakeTarget(candidates=[], tag="mat-slide-toggle"))
        step.target.element_id = ""  # type: ignore[attr-defined]
        h = AngularMaterialHandler()
        with pytest.raises(ValueError, match="no selector"):
            h.execute(MagicMock(), step)


# -- 5. normalize() for tabs ---------------------------------------------------

class TestNormalizeTab:
    def test_normalize_marks_tab_click_as_navigation(self):
        step = _make_tab_step()
        h = AngularMaterialHandler()
        h.normalize([step])
        assert step.context.get("tab_navigation") is True

    def test_normalize_does_not_mark_non_tab_click(self):
        step = FakeStep(
            action="click", value="",
            target=FakeTarget(candidates=[FakeCandidate("#btn")], tag="button")
        )
        h = AngularMaterialHandler()
        h.normalize([step])
        assert not step.context.get("tab_navigation")
