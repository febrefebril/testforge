"""BUG: Empty Selector — test fails when Playwright locator resolves to zero elements.

Symptom:
  Playwright throws TimeoutError or strict mode violation when attempting
  to interact with a locator that matches no elements in the DOM. The
  action (click, fill, text_content) never completes because the target
  does not exist.

Cause:
  The test uses a CSS selector that does not match any element on the
  page. Common causes:
    1. Selector typo or naming mismatch (e.g. `#saveButton` vs `#save-btn`).
    2. Element not yet rendered when locator is resolved.
    3. Wrong page or route loaded.
    4. Dynamic ID generation that changed between recordings.

Reproduction:
  1. Load bug_lab/pages/bug-empty-selector/index.html
     — Page has <button id="save-btn">Save</button> and <p id="status">
  2. Try to locate element using selector "#saveButton" (camelCase)
     — Page only has id="save-btn" (kebab-case)
  3. Call .click() on the locator
     — Playwright waits for element, never finds it, throws TimeoutError

Fix guidance:
  - Use the correct selector matching the actual DOM: "#save-btn"
  - In TestForge self-healing: the selector_agent should detect the
    empty match and fall back to alternative selectors (data-testid,
    text content, aria-label, etc.).
"""
import pytest


@pytest.mark.xfail(reason="BUG: selector '#saveButton' matches no element — empty selector", strict=True)
@pytest.mark.slow
def test_empty_selector_reproduces_failure(test_server, page):
    """Reproduce: locator resolves to 0 elements → .click() throws TimeoutError."""
    # Step 1: Load the page
    page.goto(f"{test_server}/bug-empty-selector/index.html")

    # Step 2: Verify page loaded correctly
    assert page.locator("#status").text_content() == "Ready."

    # Step 3: Attempt to click element using wrong selector
    # "#saveButton" does NOT exist on the page — only "#save-btn" exists.
    # This .click() will throw because Playwright waits for the element
    # and strict mode requires exactly 1 match.
    page.locator("#saveButton").click()

    # Step 4: This assertion never runs — the test fails at step 3
    assert page.locator("#status").text_content() == "Saved."


@pytest.mark.slow
def test_correct_selector_works(test_server, page):
    """Validate: correct selector '#save-btn' finds the element and click succeeds."""
    page.goto(f"{test_server}/bug-empty-selector/index.html")

    assert page.locator("#status").text_content() == "Ready."

    # Use the correct kebab-case selector matching the actual DOM
    page.locator("#save-btn").click()

    # Assert the click handler updated the status
    assert page.locator("#status").text_content() == "Saved."
