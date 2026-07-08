"""RC-19: _getTextContent helper skips <script>/<style>/<noscript> children."""
import re
from pathlib import Path

import pytest

OVERLAY_JS = (
    Path(__file__).resolve().parents[3]
    / "src" / "testforge" / "recorder" / "overlay_inject.js"
)


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestGetTextContentWhenScriptChildThenExcluded:

    def test_helper_function_defined(self, overlay_source):
        """RC-19: _getTextContent must be defined."""
        assert "function _getTextContent(el)" in overlay_source, (
            "Missing _getTextContent helper. RC-19: inline <script> in CADASTRO/GESTAO "
            "leaks JS source into div.text signals."
        )

    def test_script_tag_excluded(self, overlay_source):
        """RC-19: helper must skip script elements."""
        assert "'script'" in overlay_source and "_getTextContent" in overlay_source, (
            "RC-19: _getTextContent must filter 'script' tag."
        )
        pattern = re.compile(
            r"_tag\s*===\s*['\"]script['\"]",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "RC-19: _getTextContent must check for 'script' tag and skip it."
        )

    def test_style_tag_excluded(self, overlay_source):
        """RC-19: helper must skip style elements."""
        pattern = re.compile(
            r"_tag\s*===\s*['\"]style['\"]",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "RC-19: _getTextContent must check for 'style' tag and skip it."
        )

    def test_noscript_tag_excluded(self, overlay_source):
        """RC-19: helper must skip noscript elements."""
        pattern = re.compile(
            r"_tag\s*===\s*['\"]noscript['\"]",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "RC-19: _getTextContent must check for 'noscript' tag and skip it."
        )

    def test_extract_target_uses_helper(self, overlay_source):
        """RC-19: _extractTarget must use _getTextContent instead of .textContent for elText."""
        assert "_getTextContent(el)" in overlay_source, (
            "RC-19: _extractTarget must call _getTextContent(el) for elText computation."
        )
