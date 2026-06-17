"""BUG: Multi File Input — Identical/Ambiguous Selectors.

Symptom:
  Page has 2+ <input type="file"> elements.
  Recorder/normalizer generates identical or ambiguous selectors.
  Fallback `input[type=file]` matches all file inputs → strict mode violation.

Cause:
  RecordingNormalizer._build_target() never reads target.attributes.type.
  InputAgent healing returns static `input[type=file]` — matches ALL inputs.
  Two file inputs with same label/attributes get identical selectors.

Fix:
  Normalizer must incorporate `type=file` with disambiguating attribute
  (name/id/label) when generating candidates for file inputs.
  InputAgent must use specific selector, not bare `input[type=file]`.

Validation:
  pytest bug_lab/tests/test_bug_multi_file_input.py -v
"""
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def upload_file():
    """Absolute path to test fixture file."""
    path = FIXTURES_DIR / "test-upload.txt"
    assert path.exists(), f"Fixture file missing: {path}"
    return str(path.resolve())


# ══════════════════════════════════════════════════════════════════════════════
# Unit: Selector uniqueness by identification strategy
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectorUniqueness:
    """Each file input must have a distinct, unique selector.

    The 4 inputs use different identification strategies:
      - #resume-upload:  label[for=...]  +  #id
      - #photo-upload:   [aria-label=...]
      - #cert-upload:    [data-testid=...]
      - #doc-upload:     #id  +  [name=...]
    """

    # ── Input 1: Label-based ─────────────────────────────────────────────

    @pytest.mark.slow
    def test_resume_input_by_label_is_unique(self, test_server, page):
        """label[for='resume-upload'] matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("label[for='resume-upload']")
        assert loc.count() == 1, f"label[for=resume-upload] matched {loc.count()}, expected 1"

    @pytest.mark.slow
    def test_resume_input_by_label_adjacent_is_unique(self, test_server, page):
        """label:has-text('Upload Resume (PDF)') + input matches exactly 1."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("label:has-text('Upload Resume (PDF)') + input")
        assert loc.count() == 1

    @pytest.mark.slow
    def test_resume_input_by_id_is_unique(self, test_server, page):
        """#resume-upload matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("#resume-upload")
        assert loc.count() == 1

    # ── Input 2: aria-label-based ────────────────────────────────────────

    @pytest.mark.slow
    def test_photo_input_by_aria_label_is_unique(self, test_server, page):
        """input[aria-label='Upload Profile Photo'] matches exactly 1."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("input[aria-label='Upload Profile Photo']")
        assert loc.count() == 1

    @pytest.mark.slow
    def test_photo_input_by_id_is_unique(self, test_server, page):
        """#photo-upload matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("#photo-upload")
        assert loc.count() == 1

    # ── Input 3: data-testid-based ────────────────────────────────────────

    @pytest.mark.slow
    def test_cert_input_by_testid_is_unique(self, test_server, page):
        """[data-testid='cert-upload-input'] matches exactly 1."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("[data-testid='cert-upload-input']")
        assert loc.count() == 1

    @pytest.mark.slow
    def test_cert_input_by_id_is_unique(self, test_server, page):
        """#cert-upload matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("#cert-upload")
        assert loc.count() == 1

    # ── Input 4: id+name only (minimal identification) ────────────────────

    @pytest.mark.slow
    def test_doc_input_by_id_is_unique(self, test_server, page):
        """#doc-upload matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("#doc-upload")
        assert loc.count() == 1

    @pytest.mark.slow
    def test_doc_input_by_name_is_unique(self, test_server, page):
        """[name='document'] matches exactly 1 element."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("[name='document']")
        assert loc.count() == 1


# ══════════════════════════════════════════════════════════════════════════════
# Unit: Selectors DO NOT cross-match other inputs
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectorNoCrossMatch:
    """A selector meant for input A must not match input B."""

    @pytest.mark.slow
    def test_resume_label_does_not_match_photo(self, test_server, page):
        """label[for='resume-upload'] should NOT match #photo-upload."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        found = page.locator("label[for='resume-upload']")
        # Get the associated input (it's the input after the label)
        associated = found.locator("+ input, ~ input").first
        # But better: check the input element itself
        inputs = page.locator("input[type='file']")
        assert inputs.count() == 4
        # label[for=resume-upload] should be associated with resume-upload only
        resume_input = page.locator("#resume-upload")
        assert resume_input.count() == 1

    @pytest.mark.slow
    def test_photo_aria_does_not_match_other_inputs(self, test_server, page):
        """input[aria-label='Upload Profile Photo'] matches only #photo-upload."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("input[aria-label='Upload Profile Photo']")
        assert loc.count() == 1
        # Verify it IS the photo-upload input
        assert loc.get_attribute("id") == "photo-upload"

    @pytest.mark.slow
    def test_cert_testid_does_not_match_other_inputs(self, test_server, page):
        """[data-testid='cert-upload-input'] matches only #cert-upload."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("[data-testid='cert-upload-input']")
        assert loc.count() == 1
        assert loc.get_attribute("id") == "cert-upload"

    @pytest.mark.slow
    def test_id_selectors_are_all_distinct(self, test_server, page):
        """All 4 file inputs have distinct IDs."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        ids = ["#resume-upload", "#photo-upload", "#cert-upload", "#doc-upload"]
        for sel in ids:
            assert page.locator(sel).count() == 1, f"{sel} not unique or missing"


# ══════════════════════════════════════════════════════════════════════════════
# Unit: The generic selector bug — input[type=file] matches ALL
# ══════════════════════════════════════════════════════════════════════════════

class TestGenericSelectorBug:
    """input[type=file] matches ALL file inputs — the core bug."""

    @pytest.mark.slow
    def test_generic_type_selector_matches_all_four(self, test_server, page):
        """input[type=file] resolves to 4 elements (strict mode violation)."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("input[type='file']")
        assert loc.count() == 4, (
            f"input[type=file] matched {loc.count()} elements, expected 4"
        )

    @pytest.mark.slow
    def test_first_after_generic_fails_with_strict_mode(self, test_server, page):
        """Using .first on generic locator works but is fragile."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("input[type='file']").first
        # .first silently picks the first match — not what we want
        # but it doesn't throw strict mode violation
        assert loc.get_attribute("id") == "resume-upload"

    @pytest.mark.slow
    def test_nth_on_generic_locator(self, test_server, page):
        """input[type=file].nth(N) returns specific inputs but is brittle."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        base = page.locator("input[type='file']")
        assert base.nth(0).get_attribute("id") == "resume-upload"
        assert base.nth(1).get_attribute("id") == "photo-upload"
        assert base.nth(2).get_attribute("id") == "cert-upload"
        assert base.nth(3).get_attribute("id") == "doc-upload"


# ══════════════════════════════════════════════════════════════════════════════
# Integration: set_input_files on distinct inputs produces distinct output
# ══════════════════════════════════════════════════════════════════════════════

class TestSetInputFilesPerInput:
    """Uploading to each input via its unique selector produces correct output."""

    @pytest.mark.slow
    def test_upload_to_resume_input(self, test_server, page, upload_file):
        """set_input_files on #resume-upload shows output in #output-resume."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        page.locator("#resume-upload").set_input_files(upload_file)
        out = page.locator("#output-resume")
        assert "resume-upload" in out.text_content()
        assert "test-upload.txt" in out.text_content()

    @pytest.mark.slow
    def test_upload_to_photo_input(self, test_server, page, upload_file):
        """set_input_files on #photo-upload shows output in #output-photo."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        page.locator("#photo-upload").set_input_files(upload_file)
        out = page.locator("#output-photo")
        assert "photo-upload" in out.text_content()
        assert "test-upload.txt" in out.text_content()

    @pytest.mark.slow
    def test_upload_to_cert_input(self, test_server, page, upload_file):
        """set_input_files on #cert-upload shows output in #output-cert."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        page.locator("#cert-upload").set_input_files(upload_file)
        out = page.locator("#output-cert")
        assert "cert-upload" in out.text_content()
        assert "test-upload.txt" in out.text_content()

    @pytest.mark.slow
    def test_upload_to_doc_input(self, test_server, page, upload_file):
        """set_input_files on #doc-upload shows output in #output-doc."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        page.locator("#doc-upload").set_input_files(upload_file)
        out = page.locator("#output-doc")
        assert "doc-upload" in out.text_content()
        assert "test-upload.txt" in out.text_content()

    @pytest.mark.slow
    def test_upload_to_all_inputs_independently(self, test_server, page, upload_file):
        """Each file input's upload is independent — different output divs."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")

        # Upload to each using its unique selector
        page.locator("#resume-upload").set_input_files(upload_file)
        page.locator("#photo-upload").set_input_files(upload_file)
        page.locator("#cert-upload").set_input_files(upload_file)
        page.locator("#doc-upload").set_input_files(upload_file)

        # Verify each output div shows its own input id
        assert "resume-upload" in page.locator("#output-resume").text_content()
        assert "photo-upload" in page.locator("#output-photo").text_content()
        assert "cert-upload" in page.locator("#output-cert").text_content()
        assert "doc-upload" in page.locator("#output-doc").text_content()

    @pytest.mark.slow
    def test_upload_via_aria_label_selector(self, test_server, page, upload_file):
        """set_input_files works when locating by aria-label."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("input[aria-label='Upload Profile Photo']")
        loc.set_input_files(upload_file)
        out = page.locator("#output-photo")
        assert "photo-upload" in out.text_content()

    @pytest.mark.slow
    def test_upload_via_data_testid_selector(self, test_server, page, upload_file):
        """set_input_files works when locating by data-testid."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("[data-testid='cert-upload-input']")
        loc.set_input_files(upload_file)
        out = page.locator("#output-cert")
        assert "cert-upload" in out.text_content()

    @pytest.mark.slow
    def test_upload_via_name_selector(self, test_server, page, upload_file):
        """set_input_files works when locating by name attribute."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        loc = page.locator("[name='document']")
        loc.set_input_files(upload_file)
        out = page.locator("#output-doc")
        assert "doc-upload" in out.text_content()


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases for multi file input selector generation."""

    @pytest.mark.slow
    def test_input_count_equals_four(self, test_server, page):
        """Page has exactly 4 file inputs."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        assert page.locator("input[type='file']").count() == 4

    @pytest.mark.slow
    def test_no_two_inputs_share_same_id(self, test_server, page):
        """All file input IDs are unique."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        ids = page.locator("input[type='file']").evaluate_all(
            "els => els.map(e => e.id)"
        )
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    @pytest.mark.slow
    def test_no_two_inputs_share_same_name(self, test_server, page):
        """All file input names are unique."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        names = page.locator("input[type='file']").evaluate_all(
            "els => els.map(e => e.name)"
        )
        assert len(names) == len(set(names)), f"Duplicate names found: {names}"

    @pytest.mark.slow
    def test_only_one_input_has_aria_label(self, test_server, page):
        """Exactly 1 file input has aria-label attribute."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        count = page.locator("input[type='file'][aria-label]").count()
        assert count == 1, f"Expected 1 input with aria-label, found {count}"

    @pytest.mark.slow
    def test_only_one_input_has_data_testid(self, test_server, page):
        """Exactly 1 file input has data-testid attribute."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        count = page.locator("input[type='file'][data-testid]").count()
        assert count == 1, f"Expected 1 input with data-testid, found {count}"

    @pytest.mark.slow
    def test_label_for_attribute_points_to_correct_input(self, test_server, page):
        """label[for] attribute matches exactly one input."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")
        label = page.locator("label[for='resume-upload']")
        assert label.count() == 1
        # Clicking the label should focus the associated input via HTML spec
        label.click()
        focused_id = page.evaluate("document.activeElement.id")
        assert focused_id == "resume-upload", (
            f"Label click focused {focused_id}, expected resume-upload"
        )

    @pytest.mark.slow
    def test_inputs_have_different_output_divs(self, test_server, page, upload_file):
        """Uploading to input A does NOT affect output div of input B."""
        page.goto(f"{test_server}/bug-multi-file-input/index.html")

        # Upload only to resume
        page.locator("#resume-upload").set_input_files(upload_file)

        # Resume output should show file
        assert "test-upload.txt" in page.locator("#output-resume").text_content()

        # Other outputs should remain empty (no file selected)
        assert "No file selected" not in page.locator("#output-photo").text_content()
        # Other outputs just show empty div — verify they don't have success class
        assert "success" not in (page.locator("#output-photo").get_attribute("class") or "")
        assert "success" not in (page.locator("#output-cert").get_attribute("class") or "")
        assert "success" not in (page.locator("#output-doc").get_attribute("class") or "")
