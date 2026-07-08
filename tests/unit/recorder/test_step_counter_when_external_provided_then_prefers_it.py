"""NB-03: overlay must prefer __tfExternalStepCount over sessionStorage."""
import pathlib, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestStepCounterWhenExternalProvidedThenPrefersIt:
    def test_overlay_reads_external_step_count(self, overlay_source):
        assert "__tfExternalStepCount" in overlay_source, "NB-03: overlay must reference __tfExternalStepCount"

    def test_recorder_injects_external_step_count(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "recorder_controller.py"
        content = src.read_text()
        assert "__tfExternalStepCount" in content, "NB-03: recorder must inject __tfExternalStepCount"
