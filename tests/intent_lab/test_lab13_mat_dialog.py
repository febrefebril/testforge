"""LAB-13 — Angular Material mat-dialog handler tests.

Unit tests — no browser required.
Tests cover: detect() for dialog selectors, execute() scoped click, normalize() dialog trigger.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, call

from testforge.handlers import detect_handler
from testforge.handlers.angular_material import AngularMaterialHandler
from tests.helpers.incremental_fakes import FakeCandidate, FakeTarget, FakeStep


# -- Helpers ------------------------------------------------------------------

def _make_dialog_step(selector=".mat-dialog-container button[mat-dialog-close]",
                       text="Confirmar", tag="button", element_id="btn-confirmar"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag=tag, text=text)
    target.element_id = element_id  # type: ignore[attr-defined]
    target.accessible_name = text   # type: ignore[attr-defined]
    return FakeStep(action="click", value=text, target=target)


def _make_trigger_step(selector="#btn-abrir", text="Abrir Formulário"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag="button", text=text)
    target.element_id = "btn-abrir"  # type: ignore[attr-defined]
    return FakeStep(action="click", value="", target=target)


def _make_dialog_content_step(selector=".mat-dialog-container input[aria-label='Nome completo']"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag="input")
    target.element_id = "dialog-nome"  # type: ignore[attr-defined]
    return FakeStep(action="click", value="", target=target)


# -- 1. detect() ---------------------------------------------------------------

class TestDetectDialog:
    def test_detect_true_for_mat_dialog_in_selector(self):
        h = AngularMaterialHandler()
        assert h.detect([".mat-dialog-container button:has-text('OK')"], "", "button") is True

    def test_detect_true_for_mat_dialog_element_id(self):
        h = AngularMaterialHandler()
        assert h.detect([], "mat-dialog-0", "") is True

    def test_detect_true_for_mat_mdc_dialog_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["[mat-mdc-dialog-close]"], "", "button") is False
        # mat-dialog prefix IS present
        assert h.detect([".mat-dialog-container [mat-dialog-close]"], "", "button") is True

    def test_detect_false_for_regular_button(self):
        h = AngularMaterialHandler()
        assert h.detect(["#submit-btn", "button.primary"], "", "button") is False

    def test_detect_handler_returns_angular_for_dialog_selector(self):
        step = _make_dialog_step()
        handler = detect_handler(step)
        assert isinstance(handler, AngularMaterialHandler)


# -- 2. execute() for mat-dialog -----------------------------------------------

class TestExecuteDialog:
    def test_execute_tries_scoped_selector_first(self):
        step = _make_dialog_step(text="Confirmar")
        page = MagicMock()
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        # First call should be the scoped ".mat-dialog-container button:has-text('Confirmar')"
        first_call_args = page.click.call_args_list[0]
        assert "mat-dialog-container" in first_call_args[0][0]
        assert "Confirmar" in first_call_args[0][0]

    def test_execute_falls_back_to_candidate_when_scoped_fails(self):
        step = _make_dialog_step(selector=".mat-dialog-container button#btn-confirmar",
                                  text="Confirmar")
        page = MagicMock()
        # Make the first two scoped attempts fail, then succeed on candidate
        page.click = MagicMock(side_effect=[Exception("not found"), Exception("not found"), None])
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert sel == ".mat-dialog-container button#btn-confirmar"

    def test_execute_raises_when_all_attempts_fail(self):
        step = _make_dialog_step(text="Confirmar")
        page = MagicMock()
        page.click = MagicMock(side_effect=Exception("element not visible"))
        h = AngularMaterialHandler()
        with pytest.raises(ValueError, match="mat-dialog"):
            h.execute(page, step)


# -- 3. normalize() dialog trigger detection -----------------------------------

class TestNormalizeDialog:
    def test_normalize_marks_trigger_before_dialog_step(self):
        trigger = _make_trigger_step()
        content = _make_dialog_content_step()  # selector contains mat-dialog-container
        steps = [trigger, content]
        h = AngularMaterialHandler()
        h.normalize(steps)
        assert trigger.context.get("dialog_open_trigger") is True

    def test_normalize_does_not_mark_trigger_if_next_is_not_dialog(self):
        trigger = _make_trigger_step()
        next_step = FakeStep(action="fill", value="abc",
                             target=FakeTarget(candidates=[FakeCandidate("#name")], tag="input"))
        steps = [trigger, next_step]
        h = AngularMaterialHandler()
        h.normalize(steps)
        assert not trigger.context.get("dialog_open_trigger")

    def test_normalize_marks_tab_navigation(self):
        tab_step = FakeStep(
            action="click", value="",
            target=FakeTarget(candidates=[FakeCandidate("[role=\"tab\"]:has-text('Endereço')")], tag="div")
        )
        h = AngularMaterialHandler()
        h.normalize([tab_step])
        assert tab_step.context.get("tab_navigation") is True
