"""BUG: Dynamic Button ID — selector healing via text fallback.

Symptom:
  Playwright throws strict mode violation when clicking a button whose
  `id` attribute changes dynamically after page load. Simulates
  React/Angular hash-based IDs that invalidate recorded selectors.

Cause:
  Button ID changes from `btn-dynamic-0` → `btn-dynamic-1` → ...
  every 2 seconds. Selector `#btn-dynamic-0` resolves to 0 elements
  after the first rotation, causing Playwright strict mode failure.

Reproduction:
  1. Load bug_lab/pages/bug-dynamic-id/index.html
  2. Wait 3+ seconds for ID to change
  3. Try page.locator("#btn-dynamic-0").click() → fails
  4. Use text fallback page.locator('text="Clique Dinâmico"').click() → succeeds

Fix:
  SelectorAgent._try_text() produces has_text_fallback proposal
  converting stale ID selector to exact text selector text="..."
  with confidence 0.70. Healing pipeline L2 resolves via text fallback.
"""
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout


@pytest.mark.slow
def test_stale_id_click_reproduces_failure(test_server, page):
    """Reproduce: stale ID click fails after dynamic ID rotation."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    # Wait long enough for ID to change (2s interval + margin)
    page.wait_for_timeout(3500)

    # Verify the button ID has changed from initial value
    current_id = page.evaluate("document.querySelector('button').id")
    assert current_id != "btn-dynamic-0", \
        f"Button ID should have changed, still {current_id}"

    # Confirm result is empty (button never clicked)
    result = page.locator('[role="status"]').text_content() or ""
    assert "Clicado" not in result, "Result should be empty before click"

    # Click with stale ID — must fail
    with pytest.raises(PlaywrightTimeout):
        page.locator("#btn-dynamic-0").click(timeout=2000)


@pytest.mark.slow
def test_text_locator_clicks_succeeds(test_server, page):
    """Validate: text-based selector always works regardless of ID changes."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    # Wait for at least one ID rotation
    page.wait_for_timeout(3500)

    # Verify ID actually changed
    current_id = page.evaluate("document.querySelector('button').id")
    assert current_id != "btn-dynamic-0", \
        f"Button ID should have changed, got {current_id}"

    # Click using text locator — always valid
    page.locator('text="Clique Dinâmico"').click()
    page.wait_for_timeout(300)

    result = page.locator('[role="status"]').text_content()
    assert "Clicado!" in result, \
        f"Text locator click failed. Result: {result}"
    assert "ID atual" in result, \
        f"Result should show current ID. Got: {result}"


@pytest.mark.slow
def test_initial_id_click_succeeds_before_rotation(test_server, page):
    """Validate: initial ID click works before rotation begins."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    # Click immediately — before ID has time to change
    page.locator("#btn-dynamic-0").click()
    page.wait_for_timeout(300)

    result = page.locator('[role="status"]').text_content()
    assert "Clicado!" in result, \
        f"Initial ID click failed. Result: {result}"
