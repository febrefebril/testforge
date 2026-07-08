"""NB-01: _pushEvent + submit path + delegate root must guard against overlay elements."""
import pathlib
import re
import pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestOverlayEventsWhenTfElementThenNeverPushed:
    def test_push_event_first_line_guards_overlay(self, overlay_source):
        pattern = re.compile(
            r"function _pushEvent\(type, el\)\s*\{[\s\S]{0,300}?_isOverlayElement\(el\)",
        )
        assert pattern.search(overlay_source), (
            "NB-01: _pushEvent must guard _isOverlayElement(el) near function start."
        )

    def test_submit_trigger_rechecks_after_closest(self, overlay_source):
        pattern = re.compile(
            r"if \(interactive\) el = interactive;[\s\S]{0,150}?_isOverlayElement\(el\)[\s\S]{0,100}?_isSubmitTrigger",
        )
        assert pattern.search(overlay_source), (
            "NB-01: after reassigning el via closest(), must re-check overlay before _isSubmitTrigger."
        )

    def test_delegate_root_uses_canonical_helper(self, overlay_source):
        assert 'el.id === "tf-panel"' not in overlay_source, (
            "NB-01: delegate root must use _isOverlayElement (canonical), not id === 'tf-panel' check."
        )
