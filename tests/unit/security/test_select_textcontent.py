"""overlay_inject.js <select> textContent extraction (BUG-REC-30/69).

Static test — parses overlay_inject.js and asserts that the <select>
branch exists and does NOT use raw .textContent for elText.
"""
import re
from pathlib import Path

import pytest


OVERLAY_JS = Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestOverlaySelectTextContent:
    def test_select_branch_extracts_placeholder_plus_selected_only(self, overlay_source):
        # Assert — select branch exists
        assert "elTag === 'select'" in overlay_source, (
            "Missing <select> textContent extraction branch. BUG-REC-30/69 "
            "regression risk: select.textContent concatenates ALL options."
        )
        # Uses el.options + selectedIndex (not raw textContent)
        assert "el.selectedIndex" in overlay_source
        assert "_selOpt" in overlay_source

    def test_select_branch_references_bug_rec_docs(self, overlay_source):
        # Comment references the bug for future maintainers
        assert "BUG-REC-30" in overlay_source or "BUG-REC-69" in overlay_source, (
            "Missing traceability comment. Future maintainers need to know "
            "why <select> is special-cased."
        )

    def test_non_select_still_uses_textContent_fallback(self, overlay_source):
        # Regular elements use _getTextContent(el) (RC-19) — only <select> is
        # special-cased. Verify the else branch calls the helper (not raw .textContent
        # which would include <script>/<style>/<noscript> content).
        pattern = re.compile(
            r"else\s*\{\s*elText\s*=\s*\(\(_getTextContent\(el\)",
            re.MULTILINE,
        )
        assert pattern.search(overlay_source), (
            "Regular element path must use _getTextContent(el) (RC-19). "
            "BUG-REC-30 fix should ONLY special-case <select>, not break other tags."
        )
