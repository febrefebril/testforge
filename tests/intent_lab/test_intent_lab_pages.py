"""TestForge — Intent Lab Pages Validation.

Verifies each Intent Lab page exists, has proper structure,
and contains the expected elements for its test scenario.

Unit tests (no browser): validate HTML content structure.
"""
import os
import re

import pytest

# Root directory for all Intent Lab pages
PAGES_DIR = os.path.join(os.path.dirname(__file__), "pages")

# Required pages (21 total — covers all technology LABs + edge cases)
REQUIRED_PAGES = {
    "ready-flow",
    "missing-fill-gap",
    "prevent-default-input",
    "currency-mask",
    "native-select",
    "custom-combobox",
    "contenteditable",
    "network-payload-only",
    "iframe-field",
    "shadow-dom-field",
    "upload-file",
    "two-similar-fields",
    "dynamic-result",
    "blocking-step-failure",
    "select-not-captured",
    "form-submit-values",
    "intent-complete-basic",
    # Technology LAB pages (LAB-02 to LAB-05, LAB-10)
    "angular-material",
    "react-mui",
    "vue-vuetify",
    "select2-plugin",
}


def _page_path(page_name: str) -> str:
    return os.path.join(PAGES_DIR, page_name, "index.html")


def _read_page(page_name: str) -> str:
    path = _page_path(page_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Page not found: {path}")
    with open(path) as f:
        return f.read()


# ── All pages exist ───────────────────────────────────────────────────────

class TestAllPagesExist:
    """All 21 required Intent Lab pages must be present."""

    @pytest.mark.parametrize("page_name", sorted(REQUIRED_PAGES))
    def test_page_exists(self, page_name):
        """Each required page has an index.html."""
        path = _page_path(page_name)
        assert os.path.exists(path), f"Missing page: {page_name} at {path}"

    def test_no_missing_pages(self):
        """No unexpected gaps in coverage."""
        existing = {
            d for d in os.listdir(PAGES_DIR)
            if os.path.isdir(os.path.join(PAGES_DIR, d))
        }
        missing = REQUIRED_PAGES - existing
        assert not missing, f"Missing required pages: {missing}"


# ── Page structure tests ──────────────────────────────────────────────────

class TestPageStructure:
    """Each page must have basic HTML structure."""

    @pytest.mark.parametrize("page_name", sorted(REQUIRED_PAGES))
    def test_has_doctype(self, page_name):
        """Page has DOCTYPE declaration."""
        html = _read_page(page_name)
        assert html.strip().startswith("<!DOCTYPE html>") or "<!DOCTYPE html>" in html[:50]

    @pytest.mark.parametrize("page_name", sorted(REQUIRED_PAGES))
    def test_has_title(self, page_name):
        """Page has <title> tag."""
        html = _read_page(page_name)
        assert re.search(r"<title>.*</title>", html, re.IGNORECASE)

    @pytest.mark.parametrize("page_name", sorted(REQUIRED_PAGES))
    def test_has_form_or_interaction(self, page_name):
        """Page has at least one form, input, button, or select."""
        html = _read_page(page_name)
        has_form = bool(re.search(r"<form", html, re.IGNORECASE))
        has_input = bool(re.search(r"<input", html, re.IGNORECASE))
        has_button = bool(re.search(r"<button", html, re.IGNORECASE))
        has_select = bool(re.search(r"<select", html, re.IGNORECASE))
        has_iframe = bool(re.search(r"<iframe", html, re.IGNORECASE))
        has_combobox = 'role="combobox"' in html
        has_shadow = "attachShadow" in html
        assert any([has_form, has_input, has_button, has_select, has_iframe, has_combobox, has_shadow]), \
            f"No interactive elements found in {page_name}"


# ── Page-specific tests ───────────────────────────────────────────────────

class TestReadyFlow:
    PAGES_DIR = PAGES_DIR

    def test_has_form_elements(self):
        html = _read_page("ready-flow")
        assert 'id="nome"' in html or 'name="nome"' in html
        assert 'id="cidade"' in html or 'name="cidade"' in html
        assert 'type="checkbox"' in html
        assert 'type="submit"' in html

    def test_has_submit_handler(self):
        html = _read_page("ready-flow")
        assert "addEventListener('submit'" in html or 'onsubmit' in html


class TestMissingFillGap:
    def test_has_input_with_gap_pattern(self):
        html = _read_page("missing-fill-gap")
        assert '<input' in html
        assert 'name=' in html or 'id=' in html


class TestPreventDefaultInput:
    def test_has_prevent_default(self):
        html = _read_page("prevent-default-input")
        assert "preventDefault" in html


class TestCurrencyMask:
    def test_has_mask(self):
        html = _read_page("currency-mask")
        assert "mask" in html.lower() or "currency" in html.lower()


class TestNativeSelect:
    def test_has_native_select(self):
        html = _read_page("native-select")
        assert '<select' in html


class TestCustomCombobox:
    def test_has_combobox_role(self):
        html = _read_page("custom-combobox")
        assert 'role="combobox"' in html

    def test_has_listbox(self):
        html = _read_page("custom-combobox")
        assert 'role="listbox"' in html


class TestContentEditable:
    def test_has_contenteditable(self):
        html = _read_page("contenteditable")
        assert "contenteditable" in html


class TestNetworkPayloadOnly:
    def test_has_fetch_or_xhr(self):
        html = _read_page("network-payload-only")
        # Accept form POST, fetch(), or XMLHttpRequest — any network submission
        has_post = 'method="POST"' in html or "method='POST'" in html
        has_fetch = "fetch(" in html
        has_xhr = "XMLHttpRequest" in html
        assert has_post or has_fetch or has_xhr, (
            "network-payload-only page must have a network submission mechanism"
        )


class TestIframeField:
    def test_has_iframe(self):
        html = _read_page("iframe-field")
        assert '<iframe' in html

    def test_has_srcdoc_or_src(self):
        html = _read_page("iframe-field")
        assert 'srcdoc=' in html or 'src=' in html


class TestShadowDomField:
    def test_has_shadow_dom(self):
        html = _read_page("shadow-dom-field")
        assert "attachShadow" in html

    def test_has_custom_element(self):
        html = _read_page("shadow-dom-field")
        assert "customElements.define" in html or "custom-input" in html


class TestUploadFile:
    def test_has_file_input(self):
        html = _read_page("upload-file")
        assert 'type="file"' in html


class TestTwoSimilarFields:
    def test_has_similar_labels(self):
        html = _read_page("two-similar-fields")
        # Both forms have 'Logradouro' and 'Número'
        assert html.count("Logradouro") >= 2
        assert html.count("Número") >= 2


class TestDynamicResult:
    def test_has_calculation(self):
        html = _read_page("dynamic-result")
        assert "type=\"number\"" in html
        assert '<select' in html

    def test_has_dynamic_result(self):
        html = _read_page("dynamic-result")
        assert "Resultado" in html or "result" in html.lower()


class TestBlockingStepFailure:
    def test_has_cascading_selects(self):
        html = _read_page("blocking-step-failure")
        assert '<select' in html

    def test_has_dependency(self):
        html = _read_page("blocking-step-failure")
        # Cascading selects: second depends on first
        assert "disabled" in html


# ── New technology LAB pages ────────────────────────────────────────────

class TestAngularMaterial:
    def test_has_mat_input(self):
        html = _read_page("angular-material")
        assert 'matInput' in html

    def test_has_mat_radio(self):
        html = _read_page("angular-material")
        assert 'mat-radio-button' in html

    def test_has_mat_checkbox(self):
        html = _read_page("angular-material")
        assert 'mat-checkbox' in html

    def test_has_mat_select(self):
        html = _read_page("angular-material")
        assert 'mat-select' in html or 'role="combobox"' in html


class TestReactMui:
    def test_has_mui_textfield(self):
        html = _read_page("react-mui")
        assert 'MuiInputBase-root' in html

    def test_has_mui_radio(self):
        html = _read_page("react-mui")
        assert 'MuiRadio-root' in html

    def test_has_mui_select(self):
        html = _read_page("react-mui")
        assert 'MuiSelect-root' in html or 'role="combobox"' in html


class TestVueVuetify:
    def test_has_v_text_field(self):
        html = _read_page("vue-vuetify")
        assert 'v-text-field' in html

    def test_has_v_radio(self):
        html = _read_page("vue-vuetify")
        assert 'v-radio' in html

    def test_has_v_select(self):
        html = _read_page("vue-vuetify")
        assert 'v-select' in html or 'role="combobox"' in html


class TestSelect2Plugin:
    def test_has_select2_container(self):
        html = _read_page("select2-plugin")
        assert 'select2-container' in html

    def test_has_hidden_select(self):
        html = _read_page("select2-plugin")
        assert 'select2-hidden-accessible' in html or 'style="display:none"' in html

    def test_has_combobox_role(self):
        html = _read_page("select2-plugin")
        assert 'role="combobox"' in html


class TestSelectNotCaptured:
    def test_has_native_select(self):
        html = _read_page("select-not-captured")
        assert '<select' in html


class TestFormSubmitValues:
    def test_has_form_with_action(self):
        html = _read_page("form-submit-values")
        assert 'method="POST"' in html or 'action=' in html

    def test_has_prevent_default_input(self):
        html = _read_page("form-submit-values")
        assert "preventDefault" in html


class TestIntentCompleteBasic:
    def test_has_form_elements(self):
        html = _read_page("intent-complete-basic")
        assert '<input' in html or '<form' in html
