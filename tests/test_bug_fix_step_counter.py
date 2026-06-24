"""Regression test — Bug 3: click/submit events must increment step counter in overlay."""
from pathlib import Path


OVERLAY = (Path(__file__).parent.parent / "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")


def test_overlay_js_increments_step_count_on_click():
    """overlay_inject.js must contain step counter increment after _pushEvent('click', el)."""
    click_pos = OVERLAY.find("_pushEvent('click', el)")
    assert click_pos != -1, "_pushEvent click not found in overlay"
    step_count_pos = OVERLAY.find("__tfStepCount", click_pos)
    next_listener = OVERLAY.find("window.addEventListener", click_pos + 1)
    assert step_count_pos != -1, "__tfStepCount increment missing after _pushEvent('click', el)"
    assert step_count_pos < next_listener, "__tfStepCount increment must be inside the click listener"


def test_overlay_js_increments_step_count_on_submit():
    """overlay_inject.js must also increment step counter after _pushEvent('submit', el)."""
    submit_pos = OVERLAY.find("_pushEvent('submit', el)")
    assert submit_pos != -1, "_pushEvent submit not found"
    step_count_pos = OVERLAY.find("__tfStepCount", submit_pos)
    fill_section = OVERLAY.find("// ---- Fill capture", submit_pos)
    assert step_count_pos != -1, "__tfStepCount increment missing after _pushEvent('submit', el)"
    assert step_count_pos < fill_section, "__tfStepCount increment must appear before fill section"
