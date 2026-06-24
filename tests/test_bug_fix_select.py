"""Regression tests — Bugs 11-16: <select> recording and playback."""
import json
import os
import tempfile
import pytest


# ---- Bug 11: setTimeout defers step counter, skip click on SELECT ----

def test_overlay_js_click_skips_select():
    """Click handler must return early for SELECT elements."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    click_block_start = src.find("// ---- Click capture (primary) ----")
    assert click_block_start != -1
    skip_select = src.find("if (el && el.tagName === 'SELECT') return;", click_block_start)
    push_click = src.find("_pushEvent('click', el)", click_block_start)
    assert skip_select != -1, "Click handler must skip SELECT elements"
    assert skip_select < push_click, "SELECT skip must come before _pushEvent('click')"


def test_overlay_js_step_counter_uses_settimeout():
    """Step counter increment after click must be deferred via setTimeout."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    push_click = src.find("_pushEvent('click', el)")
    assert push_click != -1
    settimeout_pos = src.find("setTimeout(function()", push_click)
    next_listener = src.find("window.addEventListener(", push_click + 1)
    assert settimeout_pos != -1, "setTimeout must wrap step counter update after click"
    assert settimeout_pos < next_listener, "setTimeout must be inside click listener"
    # __tfStepCount must be inside the setTimeout callback
    step_count_pos = src.find("__tfStepCount", settimeout_pos)
    close_paren = src.find("}, 0);", settimeout_pos)
    assert step_count_pos != -1 and step_count_pos < close_paren, \
        "__tfStepCount increment must be inside setTimeout callback"


# ---- Bug 12: change on SELECT generates select_option event ----

def test_overlay_js_change_generates_select_option():
    """Change event on SELECT must push 'select_option', not 'fill'."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    change_start = src.find("window.addEventListener('change'")
    assert change_start != -1
    evt_type_var = src.find("evtType", change_start)
    assert evt_type_var != -1, "change handler must use evtType variable"
    select_branch = src.find("'select_option'", change_start)
    assert select_branch != -1, "change handler must emit 'select_option' for SELECT"


def test_normalizer_maps_select_option_action():
    """recording_normalizer must map select_option raw events to select_option actions."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    select_target = {
        "tag": "select", "id": "lstUf", "name": "lstUf", "placeholder": "",
        "accessible_name": "", "label": "UF", "text": "DF", "class_list": [],
        "attributes": {}, "type": None, "css_path": "select#lstUf",
    }
    raw_events = [
        {
            "type": "select_option", "target": select_target, "value": "DF",
            "timestamp": "2026-06-24T10:00:00Z", "url": "http://x",
            "page_title": "Test",
        },
    ]

    with tempfile.TemporaryDirectory() as td:
        events_file = os.path.join(td, "raw_events.jsonl")
        with open(events_file, "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        meta_file = os.path.join(td, "recording_metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "recording_id": "test_so", "base_url": "http://x",
                "application": "web", "status": "stopped",
            }, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    non_nav = [s for s in stc.steps if s.action != "navigation"]
    assert non_nav, "Must produce at least one non-navigation step"
    select_steps = [s for s in non_nav if s.action == "select_option"]
    assert select_steps, \
        f"select_option raw event must produce select_option step; got: {[s.action for s in non_nav]}"


# ---- Bug 13: try_fill dispatches select_option for <select> elements ----

def test_try_fill_uses_select_option_for_select_tag():
    """FallbackRunner.try_fill must call page.select_option, not page.fill, for tag=select."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import FallbackRunner

    page = MagicMock()
    page.select_option = MagicMock(return_value=None)
    page.fill = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()

    runner = FallbackRunner(page)
    candidates = [{"selector": "select#lstUf", "tag": "select"}]
    result = runner.try_fill(candidates, "DF")

    assert result is True
    page.select_option.assert_called_once_with("select#lstUf", "DF", timeout=5000)
    page.fill.assert_not_called()


def test_try_fill_uses_fill_for_non_select():
    """FallbackRunner.try_fill must use page.fill for non-select tags."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import FallbackRunner

    page = MagicMock()
    page.fill = MagicMock(return_value=None)
    page.select_option = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()

    runner = FallbackRunner(page)
    candidates = [{"selector": "input#name", "tag": "input"}]
    result = runner.try_fill(candidates, "André")

    assert result is True
    page.fill.assert_called_once_with("input#name", "André", timeout=5000)
    page.select_option.assert_not_called()


# ---- Bug 14: SmartStepRunner handles select_option action ----

def test_smart_step_runner_handles_select_option():
    """SmartStepRunner must dispatch page.select_option for action='select_option'."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import SmartStepRunner

    page = MagicMock()
    page.select_option = MagicMock(return_value=None)
    page.fill = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()
    page.wait_for_selector = MagicMock(return_value=None)

    runner = SmartStepRunner(page)
    step_data = {"selector": "select#lstUf", "action": "select_option", "value": "DF"}
    result = runner.execute(step_data)

    assert result is True
    page.select_option.assert_called_once_with("select#lstUf", "DF", timeout=SmartStepRunner.FILL_TIMEOUT)
    page.fill.assert_not_called()


# ---- Bug 15: label preserved in SemanticTarget for select elements ----

def test_normalizer_preserves_label_for_select():
    """label from raw_events target must appear in SemanticTarget for select elements."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    select_target = {
        "tag": "select", "name": "lstUf", "label": "UF",
        "text": "DF", "id": "lstUf", "placeholder": "",
        "accessible_name": None, "attributes": {}, "css_path": "select#lstUf",
    }
    raw_events = [
        {
            "type": "select_option", "target": select_target, "value": "DF",
            "timestamp": "2026-06-24T10:00:00Z", "url": "http://x",
            "page_title": "Test",
        },
    ]

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "raw_events.jsonl"), "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        with open(os.path.join(td, "recording_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "recording_id": "test_label", "base_url": "http://x",
                "application": "web", "status": "stopped",
            }, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    select_steps = [s for s in stc.steps if s.action == "select_option" and s.target]
    assert select_steps, "Must produce a select_option step with target"
    t = select_steps[0].target
    assert t.label == "UF", f"label must be 'UF', got: {t.label!r}"
    assert t.name == "lstUf", f"name must be 'lstUf', got: {t.name!r}"


# ---- Bug 16: redundant select clicks eliminated before select_option ----

def test_eliminate_prefill_clicks_removes_select_clicks():
    """_eliminate_prefill_clicks must skip click steps before select_option on same <select>."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer
    from testforge.semantic.model import (
        SemanticAction, SemanticTarget, LocatorCandidate,
    )

    cand = LocatorCandidate("name", "select#lstUf", 0.93, "name=lstUf")
    target = SemanticTarget(tag="select", name="lstUf", label="UF", candidates=[cand])

    click1 = SemanticAction(action="click", target=target)
    click2 = SemanticAction(action="click", target=target)
    select_op = SemanticAction(action="select_option", value="DF", target=target)
    steps = [click1, click2, select_op]

    norm = RecordingNormalizer()
    norm._eliminate_prefill_clicks(steps)

    skipped = [s for s in steps if s.skip_reason]
    kept = [s for s in steps if not s.skip_reason]
    # At least the click immediately before select_option should be skipped
    assert len(kept) <= 2, f"Too many steps kept: {[(s.action, s.skip_reason) for s in steps]}"
    assert any(s.action == "select_option" and not s.skip_reason for s in steps), \
        "select_option step must not be skipped"
