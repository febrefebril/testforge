"""TestForge — CDK Overlay utilities for Angular Material."""
from __future__ import annotations


class CDKOverlayHandler:
    """Static helpers for interacting with Angular CDK overlay panels."""

    OVERLAY_SEL = ".cdk-overlay-pane"
    BACKDROP_SEL = ".cdk-overlay-backdrop"
    OPTION_SEL = "mat-option, [role='option']"

    @staticmethod
    def wait_for_open(page, timeout: int = 3000) -> bool:
        try:
            page.wait_for_selector(".cdk-overlay-pane", state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    def wait_for_close(page, timeout: int = 3000) -> bool:
        try:
            page.wait_for_selector(".cdk-overlay-pane", state="hidden", timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    def find_option(page, text: str):
        """Return first mat-option whose visible text matches exactly."""
        options = page.locator("mat-option, [role='option']")
        count = options.count()
        for i in range(count):
            opt = options.nth(i)
            if opt.inner_text().strip() == text:
                return opt
        return None

    @staticmethod
    def find_option_partial(page, text: str):
        """Return first mat-option whose visible text contains text (case-insensitive)."""
        options = page.locator("mat-option, [role='option']")
        count = options.count()
        needle = text.lower()
        for i in range(count):
            opt = options.nth(i)
            if needle in opt.inner_text().strip().lower():
                return opt
        return None

    @staticmethod
    def find_option_by_value(page, value: str):
        """Return mat-option by data-value attribute."""
        loc = page.locator(
            f"mat-option[data-value='{value}'], [role='option'][data-value='{value}']"
        )
        if loc.count() > 0:
            return loc.first
        return None
