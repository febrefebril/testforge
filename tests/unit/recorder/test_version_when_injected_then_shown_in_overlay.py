"""Version display: overlay and recorder must carry the current testforge version."""
import pathlib
import re
import pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"
RECORDER_PY = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "recorder_controller.py"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def recorder_source() -> str:
    return RECORDER_PY.read_text(encoding="utf-8")


@pytest.mark.unit
class TestOverlayWhenRenderedThenVersionDisplayed:
    def test_overlay_reads_version_variable(self, overlay_source):
        """Overlay must reference window.__tfVersion."""
        assert "__tfVersion" in overlay_source, "Overlay must display version from __tfVersion"

    def test_overlay_has_version_html_element(self, overlay_source):
        """Overlay HTML must include a version label element."""
        assert "versionHtml" in overlay_source, "Overlay must render versionHtml element"

    def test_recorder_injects_version(self, recorder_source):
        """Recorder must inject __tfVersion into page context."""
        assert "__tfVersion" in recorder_source, "Recorder must set window.__tfVersion"


@pytest.mark.unit
class TestTestforgeVersionImportable:
    def test_version_importable(self):
        """__version__ must be importable from testforge package."""
        from testforge import __version__
        assert __version__ == "0.1.0", f"Expected 0.1.0, got {__version__}"

    def test_version_not_empty(self):
        """__version__ must be a non-empty string."""
        from testforge import __version__
        assert isinstance(__version__, str)
        assert len(__version__) > 0
        assert "." in __version__  # semver-like
