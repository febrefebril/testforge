"""BUG: Selector Escape — quotes in button text break selectors.

Symptom:
  Button text containing single or double quotes causes Playwright
  text/attribute selectors to fail or produce incorrect matches.
  CSS attribute selectors (e.g. [aria-label='Don't click']) break
  when the value contains the delimiter quote character.

Cause:
  SelectorAgent._try_text() only escapes double quotes (")
  for text="..." selectors. CSS attribute selectors in
  _try_testid(), _try_aria(), _try_placeholder() do NOT escape
  quote characters at all.

Reproduction:
  1. Load bug_lab/pages/bug-selector-escape/index.html
  2. Try page.locator('text="Click \\\"Me\\\""') — works
  3. Try page.locator("[aria-label='Don\\'t click']") — fails
  4. Try page.locator("[data-testid='it\\'s-a-test']") — fails

Fix:
  Properly escape quote characters in CSS attribute selectors.
  Choose delimiter (' or ") opposite to the quote type in value.
  For values with both quote types, use CSS.escape() or
  switch to text= / get_by_text() selector strategy.
"""
import pytest

from testforge.healing.agents.selector_agent import SelectorAgent
from testforge.healing.evidence_payload import EvidencePayload


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_payload(text_val="", dom_snapshot="", selector=""):
    """Build minimal EvidencePayload for SelectorAgent tests."""
    ctx = {
        "selector": selector,
        "text": text_val,
        "action": "click",
        "element_type": "button",
        "tag": "button",
        "role": "button",
    }
    return EvidencePayload(
        step_context=ctx,
        dom_snapshot=dom_snapshot,
    )


# ── Unit tests: text selector escaping ─────────────────────────────────────

class TestTextSelectorEscaping:
    """Verify text= selector works with quoted button text."""

    def test_text_selector_double_quotes(self):
        """Double quotes inside text= selector are escaped with backslash."""
        agent = SelectorAgent()
        proposal = agent._try_text('Click "Me"')
        assert proposal is not None, "Should produce text fallback"
        assert proposal.confidence == 0.70
        # The generated selector should use text="..." with \" escaping
        assert 'text="' in proposal.new_locator
        assert '\\"Me\\"' in proposal.new_locator or '"Me"' in proposal.new_locator

    def test_text_selector_single_quote(self):
        """Single quotes in text= selector work inside double-quoted delimiter."""
        agent = SelectorAgent()
        proposal = agent._try_text("Don't Click")
        assert proposal is not None, "Should produce text fallback"
        # Single quote inside double-quoted text= is valid HTML/Playwright
        assert "text=" in proposal.new_locator
        assert "Don't Click" in proposal.new_locator

    def test_text_selector_both_quotes(self):
        """Both quote types: double quotes get escaped, single quotes pass through."""
        agent = SelectorAgent()
        proposal = agent._try_text('He said "Don\'t go"')
        assert proposal is not None, "Should produce text fallback"
        assert "text=" in proposal.new_locator
        # Double quotes should be escaped
        assert '\\"' in proposal.new_locator

    def test_text_selector_empty_returns_none(self):
        """Empty text produces no fallback."""
        agent = SelectorAgent()
        proposal = agent._try_text("")
        assert proposal is None

    def test_text_selector_short_text_returns_none(self):
        """Text shorter than 2 chars produces no fallback."""
        agent = SelectorAgent()
        proposal = agent._try_text("x")
        assert proposal is None


# ── Unit tests: CSS attribute selector escaping ────────────────────────────

class TestAttributeSelectorEscaping:
    """Verify CSS attribute selectors handle quoted values."""

    def test_aria_label_double_quotes(self):
        """aria-label with double quotes: using single-quote delimiter works."""
        agent = SelectorAgent()
        dom = '<button aria-label=\'Alert "Warning"\'>Click</button>'
        payload = _make_payload(dom_snapshot=dom)
        proposal = agent._try_aria(payload)
        assert proposal is not None, "Should find aria-label"
        assert proposal.confidence == 0.75
        # Uses single-quote delimiter — value contains " which is fine
        assert "[aria-label='" in proposal.new_locator

    def test_aria_label_single_quote_truncated(self):
        """aria-label with single quote — BUG: regex [^"'] stops at quote char.

        The regex pattern r'["\\']([^"\\']{2,80})["\\']' captures only
        characters up to the first quote. Value "Can't touch this"
        becomes "Can" — losing the rest of the label.
        """
        agent = SelectorAgent()
        dom = "<button aria-label=\"Can't touch this\">Click</button>"
        payload = _make_payload(dom_snapshot=dom)
        proposal = agent._try_aria(payload)
        assert proposal is not None, "Should detect aria-label"
        # BUG: regex truncated at the quote, only "Can" captured
        locator = proposal.new_locator
        expected_broken = "[aria-label='Can']"
        assert locator == expected_broken, (
            f"BUG: regex [^\"'] stops at quote. "
            f"Expected broken selector '{expected_broken}', got '{locator}'"
        )

    def test_placeholder_double_quotes(self):
        """placeholder with double quotes: using single-quote delimiter works."""
        agent = SelectorAgent()
        dom = '<input placeholder=\'Type "hello"\' />'
        payload = _make_payload(dom_snapshot=dom)
        proposal = agent._try_placeholder(payload)
        assert proposal is not None, "Should find placeholder"
        assert "[placeholder='" in proposal.new_locator

    def test_testid_single_quote_truncated(self):
        """data-testid with single quote — BUG: regex [^"'] stops at quote char.

        Value "it's-a-test" becomes just "it" — testid lookup fails silently.
        """
        agent = SelectorAgent()
        dom = "<button data-testid=\"it's-a-test\">Click</button>"
        payload = _make_payload(dom_snapshot=dom)
        proposal = agent._try_testid(payload)
        assert proposal is not None, "Should detect testid"
        # BUG: regex truncated at the quote, only "it" captured
        locator = proposal.new_locator
        expected_broken = "[data-testid='it']"
        assert locator == expected_broken, (
            f"BUG: regex [^\"'] stops at quote. "
            f"Expected broken selector '{expected_broken}', got '{locator}'"
        )


# ── Integration tests: browser-based selector verification ─────────────────

@pytest.mark.slow
class TestBrowserTextSelectorQuotes:
    """Verify Playwright text= selectors work with quoted button text in browser."""

    def test_double_quote_button_click(self, test_server, page):
        """Click button with double quotes using text= selector."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Escape \" for Playwright text= selector
        page.locator('text="Click \\"Me\\""').click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "double" in result, f"Expected 'double' click result, got: {result}"

    def test_single_quote_button_click(self, test_server, page):
        """Click button with apostrophe using text= selector."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Single quote inside double-quoted text= is fine
        page.locator("text=\"Don't Click\"").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "single" in result, f"Expected 'single' click result, got: {result}"

    def test_both_quotes_button_click(self, test_server, page):
        """Click button with both quote types using text= selector."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Double quotes escaped, single quote fine inside "..."
        page.locator('text="He said \\"Don\'t go\\""').click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "both" in result, f"Expected 'both' click result, got: {result}"

    def test_get_by_text_handles_quotes_auto(self, test_server, page):
        """get_by_text() auto-escapes — no manual escaping needed."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # get_by_text handles escaping internally
        page.get_by_text('Click "Me"').click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "double" in result, f"Expected 'double' click result, got: {result}"

    def test_get_by_text_apostrophe(self, test_server, page):
        """get_by_text() with apostrophe works without escaping."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        page.get_by_text("Don't Click").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "single" in result, f"Expected 'single' click result, got: {result}"

    def test_locator_has_text_works_with_quotes(self, test_server, page):
        """has-text works with quoted strings."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        page.locator('button:has-text("Click \\"Me\\"")').click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "double" in result, f"Expected 'double' click result, got: {result}"


@pytest.mark.slow
class TestBrowserAttributeSelectorQuotes:
    """Verify CSS attribute selectors work (or fail) with quoted values."""

    def test_aria_label_double_quote_works(self, test_server, page):
        """aria-label with double quotes: single-quote delimiter works."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        page.locator("[aria-label='Alert \"Warning\"']").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "aria-double" in result, f"Expected 'aria-double', got: {result}"

    def test_aria_label_single_quote_with_escape_works(self, test_server, page):
        """aria-label with single quote: Playwright handles \\' escaping correctly.

        NOTE: Playwright's CSS engine properly parses [attr='val\\'ue'].
        The real bug is in SelectorAgent regex that truncates at the quote
        (see unit test test_aria_label_single_quote_truncated).
        """
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Properly escaped CSS attribute selector works in Playwright
        page.locator("[aria-label='Can\\'t touch this']").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "aria-single" in result, (
            f"Expected 'aria-single' with escaped selector, got: {result}"
        )

    def test_testid_single_quote_with_escape_works(self, test_server, page):
        """data-testid with single quote: Playwright handles \\' escaping.

        NOTE: Playwright's CSS engine properly parses [attr='val\\'ue'].
        The real bug is in SelectorAgent regex that truncates at the quote
        (see unit test test_testid_single_quote_truncated).
        """
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Properly escaped CSS attribute selector works in Playwright
        page.locator("[data-testid='it\\'s-a-test']").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "testid-quote" in result, (
            f"Expected 'testid-quote' with escaped selector, got: {result}"
        )

    def test_aria_label_get_by_role_works(self, test_server, page):
        """get_by_role with name handles quotes correctly (workaround)."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # get_by_role auto-handles name escaping
        page.get_by_role("button", name="Can't touch this").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "aria-single" in result, f"Expected 'aria-single', got: {result}"

    def test_testid_fallback_works(self, test_server, page):
        """Use ID selector as workaround when testid has quotes."""
        page.goto(f"{test_server}/bug-selector-escape/index.html")

        # Fallback to ID selector (no quotes issue)
        page.locator("#btn-testid-quote").click()
        page.wait_for_timeout(200)

        result = page.locator("#result").text_content()
        assert "testid-quote" in result, f"Expected 'testid-quote', got: {result}"
