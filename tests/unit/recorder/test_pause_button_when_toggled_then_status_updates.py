"""NB-04: Pause button must toggle visual status between Gravando and Pausado."""
import pathlib
import re
import pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestPauseButtonWhenToggledThenStatusUpdates:
    def test_pause_handler_sets_paused_text(self, overlay_source):
        pattern = re.compile(
            r"tf-btn-pause[\s\S]{0,400}?['\"]Pausado['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause handler must set 'Pausado' text."

    def test_pause_handler_reverts_gravando(self, overlay_source):
        pattern = re.compile(
            r"tf-btn-pause[\s\S]{0,600}?['\"]Gravando\.\.\.['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause handler must revert to 'Gravando...' on toggle."

    def test_paused_local_state_initialized(self, overlay_source):
        assert "__tfPausedLocal" in overlay_source, "NB-04: __tfPausedLocal state var must be declared."

    def test_pause_button_toggles_to_zero_when_paused(self, overlay_source):
        """When paused, button text must change from || to 0 in red."""
        pattern = re.compile(
            r"textContent\s*=\s*['\"]0['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause button must show '0' when paused."

    def test_pause_button_reverts_to_pause_when_resumed(self, overlay_source):
        """When resumed, button text must revert to ||."""
        pattern = re.compile(
            r"textContent\s*=\s*['\"]\|\|['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause button must revert to '||' when resumed."
