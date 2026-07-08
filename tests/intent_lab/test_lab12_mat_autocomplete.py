"""LAB-12 — Angular Material mat-autocomplete handler + keypress collapse tests.

Unit tests — no browser required.
Tests cover: detect() for autocomplete/mat-option, execute() happy path + errors,
and _compact_keypress_sequences() normalizer method.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock

from testforge.handlers import detect_handler
from testforge.handlers.angular_material import AngularMaterialHandler
from testforge.semantic.recording_normalizer import RecordingNormalizer
from tests.helpers.incremental_fakes import FakeCandidate, FakeTarget, FakeStep


# -- Helpers ------------------------------------------------------------------

def _make_mat_option_step(value="São Paulo", tag="mat-option", element_id="mat-option-0",
                           selector="mat-option[data-value='SP']"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag=tag, text=value)
    target.element_id = element_id  # type: ignore[attr-defined]
    target.accessible_name = value  # type: ignore[attr-defined]
    return FakeStep(action="click", value=value, target=target)


def _make_autocomplete_step(selector="input[aria-autocomplete='list']",
                             value="São Paulo", element_id="cidade-input"):
    cands = [FakeCandidate(selector=selector)]
    target = FakeTarget(candidates=cands, tag="input")
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
    page.wait_for_selector = MagicMock()
    return page, option


def _make_keypress_event(char: str, target: dict = None, key: str = None) -> dict:
    target = target or {"id": "cidade-input", "tag": "input", "name": "cidade", "placeholder": ""}
    return {"type": "keypress", "target": target, "value": char, "key": key or char}


# -- 1. detect() for mat-option by tag ----------------------------------------

class TestDetectMatOption:
    def test_detect_true_for_mat_option_tag(self):
        h = AngularMaterialHandler()
        assert h.detect([], "", "mat-option") is True

    def test_detect_true_for_mat_option_element_id(self):
        h = AngularMaterialHandler()
        assert h.detect([], "mat-option-5", "") is True

    def test_detect_true_for_mat_option_in_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["mat-option[data-value='SP']"], "", "span") is True

    def test_detect_false_for_unrelated_element(self):
        h = AngularMaterialHandler()
        assert h.detect(["#submit-btn"], "", "button") is False


# -- 2. detect() for autocomplete input ---------------------------------------

class TestDetectAutocomplete:
    def test_detect_true_for_aria_autocomplete_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["input[aria-autocomplete='list']"], "", "input") is True

    def test_detect_true_for_mat_autocomplete_selector(self):
        h = AngularMaterialHandler()
        assert h.detect(["[aria-owns='mat-autocomplete-0']"], "", "input") is True

    def test_detect_handler_returns_angular_for_mat_option(self):
        step = _make_mat_option_step()
        handler = detect_handler(step)
        assert isinstance(handler, AngularMaterialHandler)


# -- 3. execute() for mat-option — happy path ---------------------------------

class TestExecuteMatOption:
    def test_execute_clicks_option_by_text(self):
        step = _make_mat_option_step(value="São Paulo")
        page, option = _mock_page_with_option("São Paulo")
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert "São Paulo" in sel
        option.click.assert_called_once()

    def test_execute_uses_partial_match_when_exact_fails(self):
        step = _make_mat_option_step(value="São")
        page, option = _mock_page_with_option("São Paulo")
        h = AngularMaterialHandler()
        sel = h.execute(page, step)
        assert sel  # did not raise
        option.click.assert_called_once()

    def test_execute_raises_when_no_option_found(self):
        step = _make_mat_option_step(value="Cidade Inexistente")
        page = MagicMock()
        page.wait_for_selector = MagicMock()
        empty = MagicMock()
        empty.count = MagicMock(return_value=0)
        page.locator = MagicMock(return_value=empty)
        # Also make page.click fail so selector fallback fails
        page.click = MagicMock(side_effect=Exception("not found"))
        h = AngularMaterialHandler()
        with pytest.raises((ValueError, Exception)):
            h.execute(page, step)


# -- 4. _compact_keypress_sequences -------------------------------------------

class TestCompactKeypressSequences:
    def _normalizer(self):
        return RecordingNormalizer()

    def _target(self):
        return {"id": "input-1", "tag": "input", "name": "cidade", "placeholder": ""}

    def test_collapse_individual_chars_to_fill(self):
        """20 single-char keypress events → 1 fill event with full value."""
        normalizer = self._normalizer()
        target = self._target()
        text = "São Paulo"
        events = [_make_keypress_event(c, target) for c in text]
        result = normalizer._compact_keypress_sequences(events)
        assert len(result) == 1
        assert result[0]["type"] == "fill"
        assert result[0]["value"] == text

    def test_backspace_removes_last_char(self):
        normalizer = self._normalizer()
        target = self._target()
        events = [
            _make_keypress_event("S", target),
            _make_keypress_event("P", target),
            _make_keypress_event("", target, key="Backspace"),  # remove P
            _make_keypress_event("ã", target),
        ]
        result = normalizer._compact_keypress_sequences(events)
        assert len(result) == 1
        assert result[0]["value"] == "Sã"

    def test_enter_terminates_sequence(self):
        normalizer = self._normalizer()
        target = self._target()
        events = [
            _make_keypress_event("S", target),
            _make_keypress_event("P", target),
            _make_keypress_event("", target, key="Enter"),
            # This would be on a different step in reality, but test the termination
        ]
        result = normalizer._compact_keypress_sequences(events)
        assert len(result) == 1
        assert result[0]["type"] == "fill"

    def test_accumulated_fill_events_pass_through(self):
        """Accumulated fill events (value len > 1) are NOT compacted — left for _compact_fill_events."""
        normalizer = self._normalizer()
        target = self._target()
        # Accumulated values: each is full string so far
        events = [
            {"type": "keypress", "target": target, "value": "Sã", "key": "ã"},
            {"type": "keypress", "target": target, "value": "São", "key": "o"},
        ]
        result = normalizer._compact_keypress_sequences(events)
        # Both have value > 1 char → not classified as individual → pass through
        assert len(result) == 2

    def test_non_keypress_events_pass_through(self):
        normalizer = self._normalizer()
        events = [
            {"type": "click", "target": {"id": "btn"}, "value": ""},
            {"type": "navigation", "url": "http://x.com"},
        ]
        result = normalizer._compact_keypress_sequences(events)
        assert len(result) == 2

    def test_different_targets_not_merged(self):
        normalizer = self._normalizer()
        t1 = {"id": "input-1", "tag": "input", "name": "a", "placeholder": ""}
        t2 = {"id": "input-2", "tag": "input", "name": "b", "placeholder": ""}
        events = [
            _make_keypress_event("S", t1),
            _make_keypress_event("P", t2),  # different target → break
        ]
        result = normalizer._compact_keypress_sequences(events)
        # First group: only 1 event → pass through; second: same
        assert len(result) == 2
