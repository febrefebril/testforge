"""TestForge — Sprint 2: screen-state drift escalation to L3 healer.

Sprint 1 (commit daba777) added passive screen-state observation. Sprint 2
threads the drift into the healing payload so L3 LLM knows whether the
step is failing because the locator is broken (same screen, wrong selector)
or because a previous heal sent us to the wrong screen entirely (different
URL/title/roles than the recording expected). The latter case wants the
LLM to propose navigation back, not yet another locator.

Tests cover:
- Drift fields appended to step_context when current_step_drift exists
- No drift fields when matched
- Signature truncation
"""
from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from testforge.runner.incremental_runner import IncrementalRunner
from testforge.runner.screen_state import ScreenState, ScreenStateDiff


@pytest.fixture
def runner():
    """Minimal IncrementalRunner with just enough wiring to exercise
    _build_healing_payload. Bypasses __init__ so we don't load Playwright."""
    r = IncrementalRunner.__new__(IncrementalRunner)
    r.evidence_collector = MagicMock()
    r.evidence_collector.build_llm_payload = lambda step_context, include_screenshot=False: step_context
    r.page = MagicMock()
    r.page.url = "https://app/x"
    r.app_name = "siopi"
    r._current_step_state_before = None
    r._current_step_drift = None
    return r


def _step(action="click", value=""):
    s = MagicMock()
    s.action = action
    s.value = value
    s.target = MagicMock()
    s.target.text = "Calcular"
    s.target.label = ""
    s.target.accessible_name = "Calcular"
    s.target.candidates = []
    s.context = {}
    return s


def test_drift_fields_present_when_current_step_has_drift(runner):
    runner._current_step_state_before = ScreenState(
        url="https://app/home",
        title="Home",
        top_roles=[{"role": "button", "name": "Login"}],
    )
    runner._current_step_drift = ScreenStateDiff(
        matched=False,
        url_changed=True,
        reason="url:https://app/calculadora->https://app/home",
    )

    ctx = runner._build_healing_payload(
        _step(), step_num=13, original_error="not found", failure_phase="execution"
    )
    assert ctx["screen_state_drift"] is True
    assert "url:https://app/calculadora->https://app/home" in ctx["screen_state_drift_reason"]
    assert "current_screen_signature" in ctx
    assert "https://app/home" in ctx["current_screen_signature"]


def test_no_drift_fields_when_matched(runner):
    runner._current_step_state_before = ScreenState(url="https://app/x", title="X")
    runner._current_step_drift = ScreenStateDiff(matched=True, reason="match")

    ctx = runner._build_healing_payload(
        _step(), step_num=1, original_error="x", failure_phase="execution"
    )
    assert "screen_state_drift" not in ctx
    assert "screen_state_drift_reason" not in ctx
    assert "current_screen_signature" not in ctx


def test_no_drift_fields_when_no_baseline(runner):
    runner._current_step_state_before = None
    runner._current_step_drift = None

    ctx = runner._build_healing_payload(
        _step(), step_num=1, original_error="x", failure_phase="execution"
    )
    assert "screen_state_drift" not in ctx


def test_signature_truncated_to_200_chars(runner):
    big_roles = [{"role": "button", "name": "x" * 100} for _ in range(20)]
    runner._current_step_state_before = ScreenState(
        url="https://app/x", title="Y", top_roles=big_roles,
    )
    runner._current_step_drift = ScreenStateDiff(matched=False, reason="role_overlap:0.10")

    ctx = runner._build_healing_payload(
        _step(), step_num=1, original_error="x", failure_phase="execution"
    )
    assert len(ctx["current_screen_signature"]) <= 200
