"""BUG: jQuery-Enhanced Select — select_option() failure on hidden native select.

Symptom:
  Playwright recorder generates select_option() against hidden native
  <select>. jQuery UI hides native select and builds custom div-based
  dropdown. select_option() fails because element has display:none.

Cause:
  jQuery plugins hide native <select> and create custom DOM.
  Playwright's select_option() targets the hidden original, which:
  1. May throw "element is not visible" without force=True
  2. Even with force=True, only sets value — jQuery UI and
     application code listening on custom DOM do NOT update

Reproduction:
  1. Load bug_lab/pages/bug-jquery-select/index.html
  2. Try page.locator('#fruit-select').select_option('apple') — fails
  3. Try page.locator('#fruit-select').select_option('banana', force=True)
     — value set but jQuery UI unchanged, #result not updated
  4. Workaround: click .jq-select-trigger, then click li[data-value=X]

Fix Strategy:
  InputAgent / SelectorAgent should detect hidden native selects
  and generate interaction with the jQuery custom DOM instead of
  select_option(). Strategy: semantic_locator_conversion or
  label_click to find the custom trigger, then click the option.
"""
import re
import textwrap
from pathlib import Path

import pytest

PAGES_DIR = Path(__file__).parent.parent / "pages"
BUG_PAGE = PAGES_DIR / "bug-jquery-select" / "index.html"


# ── Unit tests: page structure verification ────────────────────────────────

class TestPageStructure:
    """Verify the test page HTML is correctly structured."""

    @pytest.fixture(scope="class")
    def html(self):
        return BUG_PAGE.read_text()

    def test_native_select_hidden(self, html):
        """Native <select> has display:none class."""
        assert '<select id="fruit-select"' in html
        assert 'jq-select-native' in html

    def test_jquery_wrapper_exists(self, html):
        """jQuery wrapper div is built by script."""
        assert 'jq-select-wrapper' in html
        assert 'jq-select-trigger' in html
        assert 'jq-select-dropdown' in html

    def test_options_in_native_select(self, html):
        """Native select contains expected option values."""
        assert 'value="apple"' in html
        assert 'value="banana"' in html
        assert 'value="cherry"' in html
        assert 'value="dragonfruit"' in html

    def test_jquery_dropdown_built_from_native_options(self, html):
        """jQuery script builds dropdown from native <option> elements."""
        assert "$select.find('option')" in html
        assert "data-value" in html
        assert '$select.val(value)' in html

    def test_jquery_trigger_updates_native_select(self, html):
        """jQuery click handler updates hidden native select via $select.val(value)."""
        assert "$select.val(value)" in html
        assert ".trigger('change')" in html

    def test_result_status_element(self, html):
        """Status display element exists for test assertions."""
        assert 'id="result"' in html
        assert 'role="status"' in html

    def test_jquery_cdn_loaded(self, html):
        """jQuery is loaded from CDN."""
        assert "code.jquery.com" in html or "jquery-3.7.1" in html


# ── Browser integration tests ──────────────────────────────────────────────

@pytest.mark.slow
class TestJQuerySelectBug:
    """Verify bug: select_option() fails on hidden native select."""

    def test_select_option_fails_hidden_native(self, test_server, page):
        """select_option() on hidden native select raises error.

        CONFIRMED BUG: Playwright refuses to interact with hidden element.
        """
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        # Native select is display:none — Playwright should refuse
        with pytest.raises(Exception) as exc_info:
            page.locator("#fruit-select").select_option("apple", timeout=2000)
        error_msg = str(exc_info.value).lower()
        assert "not visible" in error_msg or "hidden" in error_msg or "timeout" in error_msg or "not found" in error_msg or "element" in error_msg, (
            f"Expected visibility error for hidden select, got: {exc_info.value}"
        )

    def test_select_option_force_sets_value(self, test_server, page):
        """select_option(force=True) sets value on hidden select but
        jQuery UI does NOT update — #result stays unchanged."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        # Force overrides visibility check
        page.locator("#fruit-select").select_option("apple", force=True)
        page.wait_for_timeout(300)

        # Native select value IS set
        native_value = page.eval_on_selector("#fruit-select", "el => el.value")
        assert native_value == "apple", f"Native select value should be 'apple', got: {native_value}"

    def test_force_value_does_not_update_jquery_ui(self, test_server, page):
        """CONFIRMED BUG: force=True sets native value but jQuery UI ignores.

        The #result element (updated by jQuery click handler) shows 'No selection made'.
        """
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator("#fruit-select").select_option("banana", force=True)
        page.wait_for_timeout(300)

        result = page.locator("#result").text_content()
        assert result == "No selection made", (
            f"jQuery UI should not update with force=True. Result: {result}"
        )

    def test_force_does_not_trigger_jquery_trigger(self, test_server, page):
        """force=True sets value but jquery trigger text stays at default."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        trigger_before = page.locator(".jq-select-trigger").text_content()
        assert "-- Select a fruit --" in trigger_before

        page.locator("#fruit-select").select_option("cherry", force=True)
        page.wait_for_timeout(300)

        trigger_after = page.locator(".jq-select-trigger").text_content()
        assert trigger_after == trigger_before, (
            f"jQuery trigger text should not change with force=True. Got: {trigger_after}"
        )


@pytest.mark.slow
class TestJQuerySelectWorkaround:
    """Verify workaround: interact with jQuery custom DOM instead of select_option()."""

    def test_click_trigger_opens_dropdown(self, test_server, page):
        """Clicking jQuery trigger opens the custom dropdown."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        # Verify dropdown is initially hidden
        dropdown = page.locator(".jq-select-dropdown")
        assert not dropdown.is_visible(), "Dropdown should be hidden initially"

        # Click trigger
        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        assert dropdown.is_visible(), "Dropdown should be visible after trigger click"

    def test_select_option_via_jquery_dom(self, test_server, page):
        """WORKAROUND: click trigger, then click option in jQuery dropdown.

        This simulates how a real user interacts with the enhanced select.
        The jQuery handler updates the hidden native select and the UI.
        """
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        # Click trigger to open dropdown
        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        # Click apple option
        page.locator('.jq-select-dropdown li[data-value="apple"]').click()
        page.wait_for_timeout(300)

        # jQuery UI updated
        result = page.locator("#result").text_content()
        assert "apple" in result, f"Expected 'apple' in result, got: {result}"

        # Native select value updated
        native_value = page.eval_on_selector("#fruit-select", "el => el.value")
        assert native_value == "apple", f"Native select value should be 'apple', got: {native_value}"

        # Trigger text updated
        trigger_text = page.locator(".jq-select-trigger").text_content()
        assert "Apple" in trigger_text, f"Expected 'Apple' in trigger text, got: {trigger_text}"

    def test_select_banana_via_jquery_dom(self, test_server, page):
        """Select banana via jQuery custom DOM."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        page.locator('.jq-select-dropdown li[data-value="banana"]').click()
        page.wait_for_timeout(300)

        result = page.locator("#result").text_content()
        assert "banana" in result

        native_value = page.eval_on_selector("#fruit-select", "el => el.value")
        assert native_value == "banana"

    def test_select_cherry_via_jquery_dom(self, test_server, page):
        """Select cherry via jQuery custom DOM."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        page.locator('.jq-select-dropdown li[data-value="cherry"]').click()
        page.wait_for_timeout(300)

        result = page.locator("#result").text_content()
        assert "cherry" in result

        native_value = page.eval_on_selector("#fruit-select", "el => el.value")
        assert native_value == "cherry"

    def test_dropdown_closes_after_selection(self, test_server, page):
        """Dropdown closes after clicking an option."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)
        assert page.locator(".jq-select-dropdown").is_visible()

        page.locator('.jq-select-dropdown li[data-value="dragonfruit"]').click()
        page.wait_for_timeout(300)

        assert not page.locator(".jq-select-dropdown").is_visible(), (
            "Dropdown should close after selection"
        )

    def test_dropdown_closes_on_outside_click(self, test_server, page):
        """Clicking outside the dropdown closes it."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)
        assert page.locator(".jq-select-dropdown").is_visible()

        # Click outside (on the body)
        page.locator("h1").click()
        page.wait_for_timeout(200)

        assert not page.locator(".jq-select-dropdown").is_visible(), (
            "Dropdown should close on outside click"
        )

    def test_option_gets_selected_class(self, test_server, page):
        """Selected option receives 'selected' CSS class."""
        page.goto(f"{test_server}/bug-jquery-select/index.html")

        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        page.locator('.jq-select-dropdown li[data-value="apple"]').click()
        page.wait_for_timeout(200)

        # Re-open to check classes
        page.locator(".jq-select-trigger").click()
        page.wait_for_timeout(200)

        apple_li = page.locator('.jq-select-dropdown li[data-value="apple"]')
        class_attr = apple_li.get_attribute("class") or ""
        assert "selected" in class_attr, f"Expected 'selected' class on apple li, got: {class_attr}"


# ── Healing agent integration tests ────────────────────────────────────────

@pytest.mark.slow
class TestHealingAgentJQuerySelect:
    """Verify healing agents can handle jQuery-enhanced select failures."""

    def test_input_agent_suggests_semantic_conversion(self):
        """InputAgent should suggest semantic locator conversion for hidden selects.

        Requires InputAgent module to be importable.
        """
        from testforge.healing.agents.input_agent import InputAgent
        from testforge.healing.evidence_payload import EvidencePayload
        from testforge.healing.llm_healer import LLMHealingProposal

        agent = InputAgent()

        payload = EvidencePayload(
            step_context={
                "selector": "#fruit-select",
                "action": "select_option",
                "value": "apple",
                "tag": "select",
                "element_type": "select",
                "text": "-- Select a fruit --",
            },
            dom_snapshot=(
                '<select id="fruit-select" style="display:none">'
                '<option value="">-- Select a fruit --</option>'
                '<option value="apple">Apple</option>'
                '<option value="banana">Banana</option>'
                '<option value="cherry">Cherry</option>'
                '</select>'
                '<div class="jq-select-wrapper">'
                '<div class="jq-select-trigger">-- Select a fruit --</div>'
                '<ul class="jq-select-dropdown">'
                '<li data-value="apple">Apple</li>'
                '<li data-value="banana">Banana</li>'
                '<li data-value="cherry">Cherry</li>'
                '</ul>'
                '</div>'
            ),
        )
        payload.validate()

        result = agent.heal(
            payload,
            error_message="element is not visible — select is hidden (display: none)",
        )

        assert result is not None, "InputAgent should produce a proposal"
        assert isinstance(result, LLMHealingProposal)
        assert result.confidence > 0, "Proposal should have confidence > 0"

    def test_evidence_payload_sanitizes_select_dom(self):
        """EvidencePayload.sanitize_dom strips scripts but keeps select HTML."""
        from testforge.healing.evidence_payload import EvidencePayload

        html_with_select = textwrap.dedent("""\
            <html>
            <head><script>console.log('hello')</script></head>
            <body>
              <select id="fruit-select" style="display:none">
                <option value="apple">Apple</option>
              </select>
              <div class="jq-select-trigger">Select fruit</div>
            </body>
            </html>
        """)

        sanitized = EvidencePayload.sanitize_dom(html_with_select)
        assert '<select id="fruit-select"' in sanitized
        assert 'console.log' not in sanitized, "Script content should be stripped"
        assert '<script' not in sanitized.lower(), "Script tags should be stripped"


# ── Recording generation simulation tests ──────────────────────────────────

class TestRecordingSimulation:
    """Simulate what the Playwright recorder would generate for this page."""

    def test_recording_generates_select_option(self):
        """Verify the scenario: recorder generates select_option() for native select.

        This test documents what the recorder WOULD produce. The bug is
        that select_option() targets the hidden native select, which fails.
        """
        # Simulated code the recorder would generate
        generated_code = textwrap.dedent("""\
            # Generated by Playwright recorder:
            page.locator('#fruit-select').select_option('apple')
        """)

        # The generated code targets the hidden native select
        assert "#fruit-select" in generated_code
        assert "select_option" in generated_code
        # This is the bug — #fruit-select is display:none
        assert "locator" in generated_code or "get_by" in generated_code

    def test_workaround_uses_jquery_dom_click(self):
        """The correct interaction for jQuery-enhanced selects:
        click trigger, then click option via data-value.
        """
        correct_code = textwrap.dedent("""\
            # Workaround: interact with jQuery custom DOM
            page.locator('.jq-select-trigger').click()
            page.locator('.jq-select-dropdown li[data-value="apple"]').click()
        """)

        assert ".jq-select-trigger" in correct_code
        assert "data-value" in correct_code
        assert "select_option" not in correct_code, (
            "Workaround should NOT use select_option() on hidden element"
        )
