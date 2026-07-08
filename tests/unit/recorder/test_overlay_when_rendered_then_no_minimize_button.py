"""NB-08: tf-btn-minimize, tf-restore-badge, and _toggleMinimizeOverlay must be removed."""
import pathlib
import pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestOverlayWhenRenderedThenNoMinimizeButton:
    def test_minimize_button_removed(self, overlay_source):
        assert 'tf-btn-minimize' not in overlay_source, "NB-08: tf-btn-minimize must be removed."

    def test_restore_badge_removed(self, overlay_source):
        assert 'tf-restore-badge' not in overlay_source, "NB-08: tf-restore-badge must be removed."

    def test_toggle_minimize_function_removed(self, overlay_source):
        assert '_toggleMinimizeOverlay' not in overlay_source, "NB-08: _toggleMinimizeOverlay must be removed."
