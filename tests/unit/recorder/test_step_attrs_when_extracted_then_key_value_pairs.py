"""NB-14: step.attrs must use .name/.value loop, not raw attributes assignment."""
import pathlib, re, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestStepAttrsWhenExtractedThenKeyValuePairs:
    def test_ref_node_string_not_present_in_source(self, overlay_source):
        assert "step.attrs = el.attributes" not in overlay_source
        assert 'attrs = el.attributes;' not in overlay_source

    def test_attrs_populated_via_loop(self, overlay_source):
        pattern = re.compile(r"attrs\[.*attributes\[.*]\.name]\s*=\s*.*attributes\[.*]\.value")
        assert pattern.search(overlay_source), "NB-14: attrs must be populated via .name/.value loop"
