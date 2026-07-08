"""NB-02: All overlay <button> elements must have type="button"."""
import pathlib
import re
import pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestOverlayButtonsWhenDeclaredThenTypeButton:
    def test_all_tf_btn_have_type_button(self, overlay_source):
        matches = list(re.finditer(r'<button id="(tf-btn-[a-z]+)"([^>]*)>', overlay_source))
        assert matches, "NB-02: no tf-btn-* buttons found in overlay source."
        missing = [m.group(1) for m in matches if 'type="button"' not in m.group(2)]
        assert not missing, f"NB-02: overlay buttons without type='button': {missing}"
