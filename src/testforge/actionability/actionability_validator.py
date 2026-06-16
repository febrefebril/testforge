"""TestForge — Actionability Validator.

Validates element is actionable before performing page actions.
Checks: visible, enabled, area > 0 (rejects bb width=height=0).
"""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout


@dataclass
class ActionabilityResult:
    """Result of an actionability check."""

    selector: str
    actionable: bool
    visible: bool = False
    enabled: bool = False
    area_positive: bool = False
    bounding_box: Optional[dict] = None
    failures: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def status(self) -> str:
        return "passed" if self.actionable else "failed"


class ActionabilityValidator:
    """Validates element is actionable before performing page actions.

    Checks:
      - visible (is_visible)
      - enabled (is_enabled)
      - area > 0 (bounding box width > 0 and height > 0)
      - rejects bb width=height=0
    """

    def __init__(self, page: Page):
        self._page = page

    def validate(self, selector: str, timeout: int = 5000) -> ActionabilityResult:
        """Check if element at selector is actionable.

        Args:
            selector: CSS or text selector.
            timeout: Max wait time in ms.

        Returns:
            ActionabilityResult with actionable flag and per-check details.
        """
        result = ActionabilityResult(selector=selector, actionable=False)

        try:
            locator = self._page.locator(selector)
        except Exception as e:
            result.failures.append(f"invalid_selector: {e}")
            result.message = f"Invalid selector '{selector}': {e}"
            return result

        # Presence: element must exist in DOM
        try:
            locator.first.wait_for(state="attached", timeout=timeout)
        except (PlaywrightTimeout, Exception):
            result.failures.append("not_attached")
            result.message = f"Element '{selector}' not attached to DOM"
            return result

        if locator.count() == 0:
            result.failures.append("not_found")
            result.message = f"Element '{selector}' not found in DOM"
            return result

        el = locator.first

        # Visibility check
        try:
            el.wait_for(state="visible", timeout=timeout)
            result.visible = True
        except (PlaywrightTimeout, Exception):
            result.failures.append("not_visible")
            result.visible = False

        # Enabled check
        try:
            if el.is_enabled(timeout=timeout):
                result.enabled = True
            else:
                result.failures.append("not_enabled")
        except Exception:
            result.failures.append("not_enabled")

        # Area check: bounding box must have positive width and height
        try:
            bb = el.bounding_box(timeout=timeout)
            result.bounding_box = bb
            if bb is None:
                result.failures.append("no_bounding_box")
            elif bb["width"] <= 0 or bb["height"] <= 0:
                result.failures.append(f"zero_area: w={bb['width']}, h={bb['height']}")
            else:
                result.area_positive = True
        except Exception as e:
            result.failures.append(f"bounding_box_error: {e}")

        result.actionable = len(result.failures) == 0

        if result.actionable:
            result.message = f"Element '{selector}' is actionable"
        else:
            result.message = f"Element '{selector}' not actionable: {'; '.join(result.failures)}"

        return result

    def check(self, selector: str, timeout: int = 5000) -> bool:
        """Convenience: return True if actionable, False otherwise."""
        return self.validate(selector, timeout=timeout).actionable
