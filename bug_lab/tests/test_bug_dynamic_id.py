"""BUG: Dynamic Button ID — selector healing via text fallback.

Symptom:
  Playwright throws strict mode violation when clicking a button whose
  `id` attribute changes dynamically after page load. Simulates
  React/Angular hash-based IDs that invalidate recorded selectors.

Cause:
  Button ID changes from `btn-dynamic-0` → `btn-dynamic-1` → ...
  every 2 seconds. Selector `#btn-dynamic-0` resolves to 0 elements
  after the first rotation, causing Playwright strict mode failure.

Fix:
  SelectorAgent._try_text() produces has_text_fallback proposal
  converting stale ID selector to exact text selector text="..."
  with confidence 0.70. Healing pipeline L2 resolves via text fallback.
"""
import sys
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# ── Existing: reproduction + fix validation ───────────────────────────

@pytest.mark.slow
def test_stale_id_click_reproduces_failure(test_server, page):
    """Reproduce: stale ID click fails after dynamic ID rotation."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    page.wait_for_timeout(3500)

    current_id = page.evaluate("document.querySelector('button').id")
    assert current_id != "btn-dynamic-0", \
        f"Button ID should have changed, still {current_id}"

    result = page.locator('[id="result"]').text_content() or ""
    assert "Clicado" not in result, "Result should be empty before click"

    with pytest.raises(PlaywrightTimeout):
        page.locator("#btn-dynamic-0").click(timeout=2000)


@pytest.mark.slow
def test_text_locator_clicks_succeeds(test_server, page):
    """Validate: text-based selector always works regardless of ID changes."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    page.wait_for_timeout(3500)

    current_id = page.evaluate("document.querySelector('button').id")
    assert current_id != "btn-dynamic-0", \
        f"Button ID should have changed, got {current_id}"

    page.locator('text="Clique Dinâmico"').click()
    page.wait_for_timeout(300)

    result = page.locator('[id="result"]').text_content()
    assert "Clicado" in result, \
        f"Text locator click failed. Result: {result}"
    assert "ID atual" in result, \
        f"Result should show current ID. Got: {result}"


@pytest.mark.slow
def test_initial_id_click_succeeds_before_rotation(test_server, page):
    """Validate: initial ID click works before rotation begins."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html")

    page.locator("#btn-dynamic-0").click()
    page.wait_for_timeout(300)

    result = page.locator('[id="result"]').text_content()
    assert "Clicado" in result, \
        f"Initial ID click failed. Result: {result}"


# ── Enhanced: error mode, secondary button, multi-click ───────────────

@pytest.mark.slow
def test_error_mode_stale_id_faster_failure(test_server, page):
    """Error mode (?error=1): ID rotates every 500ms — stale faster."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html?error=1")

    # Wait for at least 2 rotations (500ms * 2 = 1s + margin)
    page.wait_for_timeout(1500)

    current_id = page.evaluate("document.querySelector('#btn-dynamic-0')")
    # With ID rotation, #btn-dynamic-0 should no longer exist
    assert current_id is None, \
        f"Expected #btn-dynamic-0 to be gone after fast rotation"

    # Stale ID click must fail
    with pytest.raises(PlaywrightTimeout):
        page.locator("#btn-dynamic-0").click(timeout=1000)


@pytest.mark.slow
def test_error_mode_text_fallback_still_works(test_server, page):
    """Error mode: text fallback succeeds even with fast ID rotation."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html?error=1")

    page.wait_for_timeout(1500)

    # Primary button — text stable even with fast rotation
    page.locator('text="Clique Dinâmico"').click()
    page.wait_for_timeout(200)

    result = page.locator('[id="result"]').text_content()
    assert "Clicado" in result, \
        f"Text fallback failed in error mode. Result: {result}"

    # Secondary button — also works
    page.locator('text="Ação Secundária"').click()
    page.wait_for_timeout(200)

    result2 = page.locator('[id="result-secondary"]').text_content()
    assert "Secundário clicado" in result2, \
        f"Secondary text fallback failed. Result: {result2}"


@pytest.mark.slow
def test_multi_click_tracking_via_text_fallback(test_server, page):
    """Multi-click: text fallback works for repeated interactions."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html?error=1")

    page.wait_for_timeout(1000)

    # Click 3 times via text fallback — each should register
    for i in range(3):
        page.locator('text="Clique Dinâmico"').click()
        page.wait_for_timeout(150)

    result = page.locator('[id="result"]').text_content()
    assert "Clicado 3x" in result, \
        f"Expected 3 clicks tracked. Result: {result}"


@pytest.mark.slow
def test_two_buttons_distinct_text_fallback(test_server, page):
    """Two buttons with rotating IDs: each has distinct text fallback."""
    page.goto(f"{test_server}/bug-dynamic-id/index.html?error=1")

    page.wait_for_timeout(1500)

    # Click primary via text
    page.locator('text="Clique Dinâmico"').click()
    page.wait_for_timeout(200)

    # Click secondary via text
    page.locator('text="Ação Secundária"').click()
    page.wait_for_timeout(200)

    primary = page.locator('[id="result"]').text_content()
    secondary = page.locator('[id="result-secondary"]').text_content()

    assert "Clicado" in primary, \
        f"Primary button not clicked. Got: {primary}"
    assert "Secundário" in secondary, \
        f"Secondary button not clicked. Got: {secondary}"


# ── Healing pipeline integration ──────────────────────────────────────

@pytest.mark.slow
def test_healing_pipeline_text_fallback_integration(test_server, page):
    """End-to-end: SelectorAgent heals stale ID via text fallback.

    Validates that the same pipeline used by curation tests produces
    a valid text fallback proposal when given the bug_lab page.
    """
    from testforge.healing.agents.selector_agent import SelectorAgent

    page.goto(f"{test_server}/bug-dynamic-id/index.html?error=1")
    page.wait_for_timeout(1200)

    # Build a minimal evidence context
    agent = SelectorAgent()
    proposal = agent._try_text("Clique Dinâmico")

    assert proposal is not None, \
        "SelectorAgent._try_text() returned None — cannot heal"
    assert proposal.strategy == "has_text_fallback", \
        f"Expected has_text_fallback, got {proposal.strategy}"
    assert proposal.confidence >= 0.70, \
        f"Expected confidence >= 0.70, got {proposal.confidence}"
    assert "text=" in proposal.new_locator, \
        f"Expected text= selector, got {proposal.new_locator}"

    # Execute the healed locator — must succeed
    page.locator(proposal.new_locator).click()
    page.wait_for_timeout(300)

    result = page.locator('[id="result"]').text_content()
    assert "Clicado" in result, \
        f"Healed locator click failed. Result: {result}"


def test_classify_stale_id_error():
    """Stale ID errors should classify as FAM-01 LOCATOR_RESOLUTION."""
    from testforge.taxonomy import FailureClassifier

    classifier = FailureClassifier()

    # Playwright strict mode violation
    r1 = classifier.classify(
        "strict mode violation: locator '#btn-dynamic-0' resolved to 0 elements"
    )
    assert r1.family_code == "FAM-01", \
        f"Expected FAM-01, got {r1.family_code}"
    assert r1.taxonomy_id.startswith("SEL"), \
        f"Expected SEL-*, got {r1.taxonomy_id}"

    # Generic not found
    r2 = classifier.classify("element not found: #btn-dynamic-0")
    assert r2.family_code in ("FAM-01", "FAM-02"), \
        f"Expected FAM-01 or FAM-02, got {r2.family_code}"
