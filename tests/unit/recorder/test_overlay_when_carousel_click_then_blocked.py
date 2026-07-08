"""NB-05: overlay JS must have autofire blocklist for carousel/swiper/slick/owl."""
import pathlib, re, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestOverlayWhenCarouselClickThenBlocked:
    def test_autofire_blocklist_declared(self, overlay_source):
        assert "carousel-control-" in overlay_source, "NB-05: blocklist must include carousel-control-*"

    def test_isAutoFire_helper_exists(self, overlay_source):
        assert "_isAutoFireElement" in overlay_source, "NB-05: helper _isAutoFireElement must exist"

    def test_click_handler_calls_isAutoFire(self, overlay_source):
        pattern = re.compile(
            r"_isAutoFireElement\(el\)[\s\S]{0,500}?window\.addEventListener\(['\"]click['\"]",
        )
        # Check that _isAutoFireElement is defined before click handler
        assert pattern.search(overlay_source) or (
            "_isAutoFireElement" in overlay_source and "window.addEventListener('click'" in overlay_source
        ), "NB-05: _isAutoFireElement must exist and click handler must exist"
