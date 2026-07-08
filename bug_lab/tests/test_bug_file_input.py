"""BUG: File Input — set_input_files vs fill(fakepath).

Symptom:
  Playwright recorder captures file input interaction as:
    fill('input[type="file"]', 'C:\\\\fakepath\\\\test-upload.txt')
  This fails at playback because browsers block programmatic value
  assignment on file inputs for security reasons.

Cause:
  Browser security model prevents setting file input .value via JS.
  When user selects a file, browser shows "C:\\fakepath\\filename" 
  as the displayed value (privacy measure — hides real path).
  Recorder sees this value and generates fill() action.
  fill() on file inputs is a no-op or throws — it cannot set files.

Fix:
  Use set_input_files() which uses Chrome DevTools Protocol (CDP)
  to set files directly, bypassing the browser's JS security restriction.
    page.locator('input[type="file"]').set_input_files('path/to/file')

Validation:
  pytest bug_lab/tests/test_bug_file_input.py -v
"""
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ── Fixture file path ───────────────────────────────────────────────────────

@pytest.fixture
def upload_file():
    """Absolute path to the test fixture file."""
    path = FIXTURES_DIR / "test-upload.txt"
    assert path.exists(), f"Fixture file missing: {path}"
    return str(path.resolve())


# ── Unit: set_input_files works correctly ───────────────────────────────────

class TestSetInputFilesCorrect:
    """Verify that set_input_files() works for file uploads."""

    @pytest.mark.slow
    def test_set_input_files_uploads_file(self, test_server, page, upload_file):
        """set_input_files sets the file on the input element."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")
        file_input.set_input_files(upload_file)

        # After upload, the page JS shows file info
        file_name_div = page.locator("#file-name")
        assert "test-upload.txt" in file_name_div.text_content(), (
            f"Expected filename in output, got: {file_name_div.text_content()}"
        )

    @pytest.mark.slow
    def test_set_input_files_triggers_page_js(self, test_server, page, upload_file):
        """set_input_files triggers the onchange handler and displays file info."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")
        file_input.set_input_files(upload_file)

        # Page JavaScript should display file name and size
        file_name_div = page.locator("#file-name")
        text = file_name_div.text_content()
        assert "Arquivo:" in text, f"Expected 'Arquivo:' prefix, got: {text}"

        # Content div should be visible and show file contents
        content_div = page.locator("#file-content")
        content_div.wait_for(state="visible", timeout=5000)
        content = content_div.text_content()
        assert "Hello from TestForge" in content, (
            f"Expected file content in output, got: {content}"
        )

    @pytest.mark.slow
    def test_set_input_files_reads_correct_content(self, test_server, page, upload_file):
        """File content read by page JS matches the fixture file."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")
        file_input.set_input_files(upload_file)

        content_div = page.locator("#file-content")
        content_div.wait_for(state="visible", timeout=5000)

        # Read the fixture file directly for comparison
        expected_content = Path(upload_file).read_text()
        displayed = content_div.text_content()
        assert expected_content in displayed, (
            f"Content mismatch. Expected '{expected_content}' in '{displayed}'"
        )


# ── Unit: fill() does NOT work for file inputs (the bug) ────────────────────

class TestFillDoesNotWork:
    """Verify that fill() is NOT a valid approach for file inputs.

    This is the core of the bug: recording fill('C:\\\\fakepath\\\\...') 
    will fail at playback because browsers block value assignment on file inputs.
    """

    @pytest.mark.slow
    def test_fill_does_not_set_file(self, test_server, page, upload_file):
        """fill() on file input does NOT set the file."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")

        # Attempt fill() — Playwright may throw or silently fail
        # depending on browser and version. Either way, file is NOT set.
        try:
            file_input.fill("C:\\\\fakepath\\\\test-upload.txt")
        except Exception:
            pass  # Expected: fill may throw on file inputs

        # Verify that no file was actually set
        file_name_div = page.locator("#file-name")
        text = file_name_div.text_content() or ""

        # fill() should NOT have triggered the onchange handler,
        # so no file info should be displayed
        assert "Arquivo:" not in text, (
            f"fill() unexpectedly set the file! Text: {text}. "
            "This means the browser allowed programmatic value assignment."
        )

    @pytest.mark.slow
    def test_fill_fakepath_produces_wrong_output(self, test_server, page, upload_file):
        """Reproduce the exact bug: fill('C:\\\\fakepath\\\\...') does nothing useful."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")

        # Simulate what the buggy recorder generates
        fakepath_value = "C:\\\\fakepath\\\\test-upload.txt"

        try:
            file_input.fill(fakepath_value)
        except Exception:
            pass

        # The content div should remain hidden (no file was loaded)
        content_div = page.locator("#file-content")
        assert not content_div.is_visible(), (
            "fill(fakepath) should NOT trigger file reading. "
            "Content div should be hidden."
        )

        # The file-name div should show default/empty state
        file_name_div = page.locator("#file-name")
        text = file_name_div.text_content() or ""
        assert "test-upload.txt" not in text, (
            f"fill(fakepath) unexpectedly set a file! Text: {text}"
        )

    @pytest.mark.slow
    def test_fill_then_set_input_files_works(self, test_server, page, upload_file):
        """After a failed fill(), set_input_files still works correctly."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")

        # First, try the broken approach (fill)
        try:
            file_input.fill("C:\\\\fakepath\\\\test-upload.txt")
        except Exception:
            pass

        # Then, use the correct approach
        file_input.set_input_files(upload_file)

        # Verify it works
        content_div = page.locator("#file-content")
        content_div.wait_for(state="visible", timeout=5000)
        assert "Hello from TestForge" in content_div.text_content()


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestFileInputEdgeCases:
    """Edge cases around file input handling."""

    @pytest.mark.slow
    def test_input_value_contains_fakepath_after_set_input_files(
        self, test_server, page, upload_file
    ):
        """After set_input_files, input.value still shows fakepath (browser privacy).

        This is WHY the bug exists: the recorder sees fakepath in the value
        and incorrectly generates fill() instead of set_input_files().
        """
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")
        file_input.set_input_files(upload_file)

        # Browser privacy: value shows "C:\\fakepath\\filename" not real path
        input_value = file_input.input_value()
        assert "fakepath" in input_value.lower() or "test-upload" in input_value, (
            f"Expected fakepath prefix in input value, got: {input_value}"
        )
        # Real file path should NOT leak
        assert str(FIXTURES_DIR) not in input_value, (
            f"Real path leaked into input value: {input_value}"
        )

    @pytest.mark.slow
    def test_set_input_files_multiple_calls(self, test_server, page, upload_file):
        """Calling set_input_files twice overwrites with the second file."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")

        # Upload the fixture file
        file_input.set_input_files(upload_file)

        content_div = page.locator("#file-content")
        content_div.wait_for(state="visible", timeout=5000)
        first_content = content_div.text_content()

        # Upload again (same file — content should still be correct)
        file_input.set_input_files(upload_file)

        content_div.wait_for(state="visible", timeout=5000)
        second_content = content_div.text_content()

        assert first_content == second_content, (
            "Content should be consistent across multiple uploads"
        )

    @pytest.mark.slow
    def test_empty_set_input_files_clears(self, test_server, page, upload_file):
        """set_input_files([]) clears the file input."""
        page.goto(f"{test_server}/bug-file-input/index.html")

        file_input = page.locator("#file-upload")

        # Upload a file
        file_input.set_input_files(upload_file)
        content_div = page.locator("#file-content")
        content_div.wait_for(state="visible", timeout=5000)

        # Clear the input
        file_input.set_input_files([])

        # After clearing, content div should be hidden or show empty state
        file_name_div = page.locator("#file-name")
        text = file_name_div.text_content() or ""

        # Page may or may not re-hide the div — depends on browser event behavior
        # At minimum, "Arquivo:" prefix should not appear with the old file
        assert "test-upload.txt" not in text or content_div.is_visible() is False, (
            "After clearing, file info should not show the old file"
        )
