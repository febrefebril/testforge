"""TestForge — Tests for ScreenStateTracker (Sprint 1, screen-state).

Cobre:
- capture_screen_state com page mockada (url, title, top_roles)
- ScreenState.signature determinismo
- compare detecta url change, title change, role drift
- compare gracioso com None (no_baseline)
- IncrementalStepResult carrega screen_state_* fields
"""
from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from testforge.runner.screen_state import (
    ScreenState,
    capture_screen_state,
    compare,
)
from testforge.runner.step_result import IncrementalStepResult


class TestScreenStateDataclass:
    def test_to_dict_roundtrip(self):
        s = ScreenState(
            url="https://app/x",
            title="Home",
            top_roles=[{"role": "button", "name": "Salvar"}],
            timestamp="2026-06-29T00:00:00Z",
        )
        d = s.to_dict()
        assert d["url"] == "https://app/x"
        assert d["title"] == "Home"
        assert d["top_roles"] == [{"role": "button", "name": "Salvar"}]
        assert d["timestamp"] == "2026-06-29T00:00:00Z"

    def test_signature_stable_for_equal_states(self):
        s1 = ScreenState(url="a", title="t", top_roles=[{"role": "button", "name": "x"}])
        s2 = ScreenState(url="a", title="t", top_roles=[{"role": "button", "name": "x"}])
        assert s1.signature() == s2.signature()

    def test_signature_changes_with_role(self):
        s1 = ScreenState(url="a", title="t", top_roles=[{"role": "button", "name": "x"}])
        s2 = ScreenState(url="a", title="t", top_roles=[{"role": "link", "name": "x"}])
        assert s1.signature() != s2.signature()


class TestCaptureScreenState:
    def _mock_page(self, url="https://app/", title="Home", roles=None):
        page = MagicMock()
        page.url = url
        page.title.return_value = title
        page.evaluate.return_value = roles or []
        return page

    def test_capture_happy_path(self):
        page = self._mock_page(
            url="https://app/",
            title="Calculadora",
            roles=[{"role": "button", "name": "Calcular"}, {"role": "textbox", "name": "Valor"}],
        )
        state = capture_screen_state(page)
        assert state.url == "https://app/"
        assert state.title == "Calculadora"
        assert len(state.top_roles) == 2
        assert state.top_roles[0] == {"role": "button", "name": "Calcular"}
        assert state.timestamp

    def test_capture_swallows_page_url_error(self):
        page = MagicMock()
        type(page).url = property(lambda _: (_ for _ in ()).throw(RuntimeError("closed")))
        page.title.return_value = "ok"
        page.evaluate.return_value = []
        state = capture_screen_state(page)
        assert state.url == ""
        assert state.title == "ok"

    def test_capture_swallows_evaluate_error(self):
        page = self._mock_page()
        page.evaluate.side_effect = RuntimeError("no js")
        state = capture_screen_state(page)
        assert state.url == "https://app/"
        assert state.top_roles == []

    def test_capture_filters_non_dict_roles(self):
        page = self._mock_page(roles=[{"role": "button", "name": "ok"}, "garbage", None])
        state = capture_screen_state(page)
        assert state.top_roles == [{"role": "button", "name": "ok"}]


class TestCompare:
    def _state(self, url="u", title="t", roles=None):
        return ScreenState(url=url, title=title, top_roles=roles or [])

    def test_compare_none_baseline_matches(self):
        s = self._state()
        diff = compare(None, s)
        assert diff.matched
        assert diff.reason == "no_baseline"

    def test_compare_identical_matches(self):
        s = self._state(url="u", title="t", roles=[{"role": "button", "name": "x"}])
        diff = compare(s, s)
        assert diff.matched
        assert diff.role_overlap == 1.0

    def test_compare_url_change_flags(self):
        a = self._state(url="https://app/home")
        b = self._state(url="https://app/other")
        diff = compare(a, b)
        assert not diff.matched
        assert diff.url_changed
        assert "url:" in diff.reason

    def test_compare_query_string_ignored(self):
        a = self._state(url="https://app/x?a=1")
        b = self._state(url="https://app/x?a=2")
        diff = compare(a, b)
        assert diff.matched
        assert not diff.url_changed

    def test_compare_fragment_ignored(self):
        a = self._state(url="https://app/x#section1")
        b = self._state(url="https://app/x#section2")
        diff = compare(a, b)
        assert diff.matched

    def test_compare_title_change_flags(self):
        a = self._state(title="Home")
        b = self._state(title="Login")
        diff = compare(a, b)
        assert not diff.matched
        assert diff.title_changed
        assert "title:" in diff.reason

    def test_compare_role_drift_flags_when_below_threshold(self):
        a = self._state(roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "C"},
        ])
        b = self._state(roles=[
            {"role": "link", "name": "X"},
            {"role": "link", "name": "Y"},
        ])
        diff = compare(a, b)
        assert not diff.matched
        assert diff.role_overlap < 0.6
        assert "role_overlap:" in diff.reason

    def test_compare_role_partial_overlap_above_threshold_matches(self):
        a = self._state(roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "C"},
        ])
        b = self._state(roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "C"},
            {"role": "button", "name": "D"},
        ])
        diff = compare(a, b)
        assert diff.role_overlap >= 0.6
        assert diff.matched

    def test_compare_empty_roles_both_sides_matches(self):
        diff = compare(self._state(), self._state())
        assert diff.matched
        assert diff.role_overlap == 1.0

    def test_compare_one_side_empty_drifts(self):
        a = self._state(roles=[{"role": "button", "name": "x"}])
        b = self._state(roles=[])
        diff = compare(a, b)
        assert not diff.matched
        assert diff.role_overlap == 0.0


class TestStepResultCarriesScreenState:
    def test_default_fields_empty(self):
        r = IncrementalStepResult(step_num=1, action="click")
        assert r.screen_state_before == {}
        assert r.screen_state_after == {}
        assert r.screen_state_drift is False
        assert r.screen_state_drift_reason == ""

    def test_to_dict_includes_screen_state(self):
        r = IncrementalStepResult(step_num=1, action="click")
        r.screen_state_before = {"url": "a"}
        r.screen_state_after = {"url": "b"}
        r.screen_state_drift = True
        r.screen_state_drift_reason = "url:a->b"
        d = r.to_dict()
        assert d["screen_state_before"] == {"url": "a"}
        assert d["screen_state_after"] == {"url": "b"}
        assert d["screen_state_drift"] is True
        assert d["screen_state_drift_reason"] == "url:a->b"
