"""TestForge — Material Component Handler.

Specializes in detecting and handling Angular Material components (mat-*).
Extracts Material-specific heuristics from step executors.
"""


class MaterialComponentDetector:
    """Detects Angular Material components without requiring candidates."""

    @staticmethod
    def is_material_radio_button(element_id: str, selector: str) -> bool:
        """Check if element is Angular Material radio button.

        Can detect via:
        - element_id prefix (mat-radio-*)
        - selector containing mat-radio-button
        - Does NOT require candidates to exist
        """
        if not element_id and not selector:
            return False
        if element_id and element_id.startswith("mat-radio-"):
            return True
        if selector and "mat-radio-button" in selector:
            return True
        return False

    @staticmethod
    def is_material_datepicker(selector: str) -> bool:
        """Check if element is Material datepicker component."""
        if not selector:
            return False
        return any(s in selector for s in ('cdk-overlay', 'mat-calendar', 'mat-datepicker'))

    @staticmethod
    def is_material_dialog(selector: str) -> bool:
        """Check if element is Material dialog."""
        if not selector:
            return False
        return 'mat-dialog-container' in selector or 'cdk-overlay-backdrop' in selector

    @staticmethod
    def is_material_form_field(selector: str) -> bool:
        """Check if element is Material form field."""
        if not selector:
            return False
        return 'mat-form-field' in selector or 'mat-mdc-form-field' in selector


class MaterialComponentHandler:
    """Handles execution of steps targeting Material components."""

    def __init__(self, page):
        self._page = page
        self._detector = MaterialComponentDetector()

    def handle_radio_button(self, selector: str, click_count: int = 1) -> bool:
        """Execute click for Material radio button using dispatch_event.

        Material radio buttons need dispatch_event for proper change detection,
        unlike standard HTML inputs which work with Playwright's click().
        """
        try:
            locator = self._page.locator(selector).first
            locator.dispatch_event("click")
            self._page.wait_for_timeout(300)
            return True
        except Exception:
            return False

    def handle_datepicker_overlay(self, selector: str) -> bool:
        """Wait for Material datepicker overlay to appear."""
        try:
            self._page.wait_for_selector(
                '.cdk-overlay-container',
                state='visible',
                timeout=5000
            )
            self._page.wait_for_timeout(500)
            return True
        except Exception:
            return False

    def handle_dialog_overlay(self) -> bool:
        """Try to close Material dialog overlays."""
        close_selectors = [
            '.mat-dialog-container .close',
            '.mat-dialog-container [mat-dialog-close]',
            '.cdk-overlay-backdrop',
        ]
        for selector in close_selectors:
            try:
                if self._page.locator(selector).count() > 0:
                    self._page.click(selector, timeout=2000)
                    self._page.wait_for_timeout(300)
                    return True
            except Exception:
                continue
        return False
