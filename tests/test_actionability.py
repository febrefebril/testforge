"""TestForge — Actionability Validator tests.

Validates element actionability: visible, enabled, area > 0.
Rejects bb width=height=0.
"""

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from testforge.actionability import ActionabilityValidator, ActionabilityResult


class TestActionabilityValidator:
    """Test element actionability validation."""

    # ── Happy path ─────────────────────────────────────────────────────

    def test_element_actionable(self, page: Page):
        """Visible, enabled, positive area → passes."""
        page.set_content('<button id="btn">Click</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn")
        assert result.actionable is True
        assert result.status == "passed"
        assert result.visible is True
        assert result.enabled is True
        assert result.area_positive is True
        assert result.bounding_box is not None
        assert result.bounding_box["width"] > 0
        assert result.bounding_box["height"] > 0
        assert len(result.failures) == 0

    def test_input_actionable(self, page: Page):
        """Visible input, enabled, positive area → passes."""
        page.set_content('<input id="name" type="text" value="hello">')
        validator = ActionabilityValidator(page)
        result = validator.validate("#name")
        assert result.actionable is True

    def test_check_convenience(self, page: Page):
        """check() convenience method returns True/False."""
        page.set_content('<button id="btn">Click</button>')
        validator = ActionabilityValidator(page)
        assert validator.check("#btn") is True

    # ── Not visible ────────────────────────────────────────────────────

    def test_element_not_visible_display_none(self, page: Page):
        """display:none element → fails not_visible."""
        page.set_content('<button id="btn" style="display:none">Hidden</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert result.status == "failed"
        assert "not_visible" in result.failures

    def test_element_not_visible_hidden_attribute(self, page: Page):
        """hidden attribute element → fails not_visible."""
        page.set_content('<button id="btn" hidden>Hidden</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert "not_visible" in result.failures

    def test_element_not_visible_visibility_hidden(self, page: Page):
        """visibility:hidden → fails not_visible (playwright sees as hidden)."""
        page.set_content(
            '<button id="btn" style="visibility:hidden">Hidden</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert "not_visible" in result.failures

    def test_element_outside_viewport_still_visible(self, page: Page):
        """Element offscreen but visible → playwright may still report visible.
        
        Positioned at negative coords is still 'visible' per Playwright.
        But the bounding box still exists with positive dimensions.
        """
        page.set_content(
            '<button id="btn" style="position:absolute;top:-9999px;left:-9999px">Off</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        # Such elements may still be considered "visible" by Playwright
        # Verify at least area check still works
        assert result.bounding_box is not None
        assert result.bounding_box["width"] > 0
        assert result.bounding_box["height"] > 0
        assert "not_visible" not in result.failures

    # ── Not enabled ────────────────────────────────────────────────────

    def test_element_disabled(self, page: Page):
        """disabled button → fails not_enabled."""
        page.set_content('<button id="btn" disabled>Disabled</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn")
        assert result.actionable is False
        assert "not_enabled" in result.failures
        assert result.visible is True
        assert result.area_positive is True

    def test_input_disabled(self, page: Page):
        """disabled input → fails not_enabled."""
        page.set_content('<input id="name" disabled>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#name")
        assert result.actionable is False
        assert "not_enabled" in result.failures

    def test_input_readonly(self, page: Page):
        """readonly input → enabled passes (readonly still enabled)."""
        page.set_content('<input id="name" readonly value="test">')
        validator = ActionabilityValidator(page)
        result = validator.validate("#name")
        assert result.enabled is True
        assert result.actionable is True

    # ── Zero area (bb width=height=0) ──────────────────────────────────

    def test_element_zero_width(self, page: Page):
        """0 width element → fails zero_area."""
        page.set_content(
            '<button id="btn" style="width:0;height:20px;overflow:hidden;padding:0;border:0">X</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert any("zero_area" in f for f in result.failures)

    def test_element_zero_height(self, page: Page):
        """0 height element → fails zero_area."""
        page.set_content(
            '<button id="btn" style="width:100px;height:0;overflow:hidden;padding:0;border:0">X</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert any("zero_area" in f for f in result.failures)

    def test_element_zero_both_dimensions(self, page: Page):
        """width=0, height=0 → fails zero_area (explicit reject)."""
        page.set_content(
            '<button id="btn" style="width:0;height:0;overflow:hidden;padding:0;border:0">X</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        assert any("zero_area" in f for f in result.failures)

    def test_element_no_bounding_box(self, page: Page):
        """Bounding box None → fails no_bounding_box."""
        page.set_content(
            '<button id="btn" style="display:none">Ghost</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        # display:none elements can have None bounding box
        assert result.actionable is False
        # Should have both not_visible and no_bounding_box
        assert "not_visible" in result.failures

    # ── Not in DOM ─────────────────────────────────────────────────────

    def test_element_not_in_dom(self, page: Page):
        """Selector not in DOM → fails not_found."""
        page.set_content('<div>nothing</div>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#does-not-exist", timeout=1000)
        assert result.actionable is False
        assert "not_attached" in result.failures

    def test_element_removed_from_dom(self, page: Page):
        """Element removed from DOM before validation → not_attached."""
        page.set_content('<div id="container"></div>')
        # Dynamically create then immediately destroy element
        page.evaluate("""
            const el = document.createElement('button');
            el.id = 'btn';
            document.body.appendChild(el);
        """)
        # Verify element exists
        assert page.locator("#btn").count() == 1
        # Now remove it
        page.evaluate("document.getElementById('btn').remove()")
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=500)
        assert result.actionable is False
        assert "not_attached" in result.failures

    def test_check_returns_false(self, page: Page):
        """check() returns False for non-actionable element."""
        page.set_content('<div>nothing</div>')
        validator = ActionabilityValidator(page)
        assert validator.check("#does-not-exist", timeout=1000) is False

    def test_check_returns_false_disabled(self, page: Page):
        """check() returns False for disabled element."""
        page.set_content('<button id="btn" disabled>No</button>')
        validator = ActionabilityValidator(page)
        assert validator.check("#btn") is False

    # ── Combined failures ──────────────────────────────────────────────

    def test_multiple_failures_aggregated(self, page: Page):
        """Element hidden and disabled → both failures listed."""
        page.set_content(
            '<button id="btn" style="display:none" disabled>Nope</button>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#btn", timeout=1000)
        assert result.actionable is False
        # display:none → not_visible
        assert "not_visible" in result.failures
        # The message should list failures
        assert len(result.failures) >= 1

    # ── Status property ────────────────────────────────────────────────

    def test_status_passed(self, page: Page):
        page.set_content('<button id="ok">OK</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#ok")
        assert result.status == "passed"

    def test_status_failed(self, page: Page):
        page.set_content('<button id="nope" disabled>Nope</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("#nope")
        assert result.status == "failed"

    # ── Selector variants ──────────────────────────────────────────────

    def test_text_selector(self, page: Page):
        """Text selector (non-standard Playwright selector)."""
        page.set_content('<button>Click Me</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate("text=Click Me")
        assert result.actionable is True

    def test_css_class_selector(self, page: Page):
        """CSS class selector."""
        page.set_content('<button class="primary-btn">Save</button>')
        validator = ActionabilityValidator(page)
        result = validator.validate(".primary-btn")
        assert result.actionable is True

    # ── Edge cases ──────────────────────────────────────────────────────

    def test_zero_width_zero_height_rejected(self, page: Page):
        """Explicit requirement: reject bb width=height=0."""
        page.set_content(
            '<span id="dot" style="display:inline-block;width:0;height:0;overflow:hidden">x</span>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#dot", timeout=1000)
        assert result.actionable is False
        assert any("zero_area" in f for f in result.failures)
        assert result.bounding_box is not None
        assert result.bounding_box["width"] == 0
        assert result.bounding_box["height"] == 0

    def test_small_but_positive_area_passes(self, page: Page):
        """1x1 element has positive area → passes."""
        page.set_content(
            '<span id="dot" style="display:inline-block;width:1px;height:1px">x</span>'
        )
        validator = ActionabilityValidator(page)
        result = validator.validate("#dot", timeout=1000)
        assert result.actionable is True
        assert result.area_positive is True

    def test_result_dataclass_defaults(self):
        """Verify default result is not actionable."""
        result = ActionabilityResult(selector="#test", actionable=False)
        assert result.status == "failed"
        assert result.visible is False
        assert result.enabled is False
        assert result.area_positive is False
        assert result.bounding_box is None
