"""BUG-REC-02: overlay_inject.js must ignore its own UI elements (tf-* prefix).

Static tests parse overlay_inject.js and verify:
- _isOverlayElement predicate exists
- click/input/change/paste listeners call it as early return
"""
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
class TestOverlayBlocklistPredicate:
    def test_isOverlayElement_function_exists(self, overlay_source):
        assert "function _isOverlayElement" in overlay_source, (
            "Missing _isOverlayElement predicate. BUG-REC-02 fix required."
        )

    def test_predicate_checks_id_tf_prefix(self, overlay_source):
        assert "'tf-'" in overlay_source and "el.id" in overlay_source, (
            "Predicate must check id.startsWith('tf-') for overlay elements."
        )

    def test_predicate_checks_ancestor_container(self, overlay_source):
        # Uses el.closest with tf-overlay/tf-assert-menu selectors
        assert re.search(
            r"closest\([^)]*tf-overlay[^)]*\)", overlay_source
        ), "Predicate must walk ancestors via closest() for overlay containers."


@pytest.mark.unit
class TestOverlayListenersUsePredicate:
    def test_click_listener_calls_isOverlayElement_early_return(self, overlay_source):
        # Find click listener block and verify predicate is called before capture
        click_block = re.search(
            r"addEventListener\('click',\s*function\(e\)\s*\{([^}]+?_isOverlayElement[^}]+?return[^}]+?\})",
            overlay_source,
            re.DOTALL,
        )
        assert click_block, (
            "click listener must call _isOverlayElement early. BUG-REC-02."
        )

    def test_input_listener_calls_isOverlayElement(self, overlay_source):
        input_block = re.search(
            r"addEventListener\('input',\s*function\(e\)\s*\{.*?_isOverlayElement",
            overlay_source,
            re.DOTALL,
        )
        assert input_block, "input listener must skip overlay elements."

    def test_change_listener_calls_isOverlayElement(self, overlay_source):
        change_block = re.search(
            r"addEventListener\('change',\s*function\(e\)\s*\{.*?_isOverlayElement",
            overlay_source,
            re.DOTALL,
        )
        assert change_block, "change listener must skip overlay elements."

    def test_paste_listener_calls_isOverlayElement(self, overlay_source):
        paste_block = re.search(
            r"addEventListener\('paste',\s*function\(e\)\s*\{.*?_isOverlayElement",
            overlay_source,
            re.DOTALL,
        )
        assert paste_block, "paste listener must skip overlay elements."

    def test_predicate_referenced_with_bug_rec_02_comment(self, overlay_source):
        # Traceability for future maintainers
        assert "BUG-REC-02" in overlay_source, (
            "Missing BUG-REC-02 traceability comment. Future maintainers "
            "need to know why the predicate exists."
        )
