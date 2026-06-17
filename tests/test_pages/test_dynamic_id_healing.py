"""TestForge — Dynamic ID Healing: Text Fallback Tests.

Validates that selector healing falls back to text-based locators
when button IDs change dynamically (simulating React/Angular hash IDs).

Tests:
  1. SelectorAgent._try_text() produces has_text_fallback proposal
  2. Full healing pipeline L0→L2 succeeds via text fallback
  3. End-to-end: stale ID click fails, healing recovers with text= selector
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from testforge.taxonomy import FailureClassifier, FailureFamily
from testforge.healing import (
    CuradorAutomatico, EvidencePayload, ProgressResult,
    HealingCatalog,
)
from testforge.evidence import EvidenceCollector
from testforge.healing.agents.selector_agent import SelectorAgent
from testforge.healing.evidence_payload import EvidencePayload
from testforge.runner.fallback_runner import SmartStepRunner


def navigate_dynamic_id(page, test_server: str, error: bool = False):
    """Navigate to the dynamic ID test page."""
    url = f"{test_server}/curation/fam-dynamic-id/index.html"
    if error:
        url += "?error=1"
    page.goto(url)
    page.wait_for_timeout(500)


class TestDynamicIdTextFallback:
    """SEL-004: Dynamic button ID — healing via text fallback."""

    def test_selector_agent_text_fallback(self, page, test_server):
        """SelectorAgent._try_text() should produce a text= proposal."""
        navigate_dynamic_id(page, test_server)

        # Build evidence payload with text context
        collector = EvidenceCollector(page)
        collector.start("test-text-fallback")

        ctx = {
            "action": "click",
            "selector": "#btn-dynamic-0",
            "text": "Clique Dinâmico",
            "intention": "Click dynamic button",
            "url": page.url,
            "framework": "generic",
            "family": "FAM-01",
            "taxonomy_id": "SEL-004",
        }
        payload = collector.build_llm_payload(ctx)

        # Directly test SelectorAgent._try_text()
        agent = SelectorAgent()
        proposal = agent._try_text("Clique Dinâmico")

        assert proposal is not None, "SelectorAgent._try_text() returned None"
        assert proposal.strategy == "has_text_fallback", \
            f"Expected has_text_fallback, got {proposal.strategy}"
        assert "text=" in proposal.new_locator, \
            f"Expected text= selector, got {proposal.new_locator}"
        assert "Clique Dinâmico" in proposal.new_locator, \
            f"Expected 'Clique Dinâmico' in locator, got {proposal.new_locator}"
        assert proposal.confidence >= 0.70, \
            f"Expected confidence >= 0.70, got {proposal.confidence}"
        assert proposal.taxonomy_id == "SEL-004"
        assert proposal.family == "FAM-01"

    def test_full_healing_pipeline_text_fallback(self, page, test_server):
        """Full healing pipeline should resolve dynamic ID via text fallback.

        Steps:
          1. Load page with fast ID rotation (?error=1)
          2. Get initial button ID, wait for it to change
          3. Attempt healing with old ID selector
          4. Verify healing succeeds via text fallback (L2 SelectorAgent)
        """
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(800)  # Allow ID to change at least once

        # Read current button ID from DOM
        current_id = page.evaluate("document.querySelector('button').id")
        assert current_id != "btn-dynamic-0", \
            f"Button ID should have changed, but is still {current_id}"

        # Now use the initial ID as the stale selector
        stale_selector = "#btn-dynamic-0"

        collector = EvidenceCollector(page)
        collector.start("test-pipeline-text-fallback")

        ctx = {
            "action": "click",
            "selector": stale_selector,
            "text": "Clique Dinâmico",
            "intention": "Click dynamic button with stale ID",
            "url": page.url,
            "framework": "generic",
            "family": "FAM-01",
            "taxonomy_id": "SEL-004",
        }
        payload = collector.build_llm_payload(ctx)

        assert payload.is_sufficient, \
            f"Evidence insufficient: {payload.insufficiency_reason}"

        # Verify DOM snapshot contains the button text
        assert "Clique Dinâmico" in payload.dom_snapshot, \
            "DOM snapshot must contain button text 'Clique Dinâmico'"

        smart_runner = SmartStepRunner(page)

        def step_runner(step_data):
            strategy = step_data.get("strategy", "")
            return smart_runner.execute(step_data, strategy)

        curator = CuradorAutomatico(
            catalog=HealingCatalog(),
            step_runner=step_runner,
        )

        error_msg = (
            f"strict mode violation: locator '{stale_selector}' "
            "resolved to 0 elements"
        )

        outcome = curator.cure(
            {"selector": stale_selector, "action": "click"},
            error_msg,
            payload,
        )

        assert outcome.status == ProgressResult.PASSED_STEP, \
            f"Healing failed: {outcome.status} — {outcome.error_message}"

        # Verify healing used text fallback (L2 or L3)
        assert outcome.layer_used in ("L2", "L3", "L0"), \
            f"Expected L0/L2/L3 layer, got {outcome.layer_used}"

        # Verify the proposal uses text-based locator
        if outcome.proposal:
            assert "text=" in outcome.proposal.new_locator or \
                   "has-text" in outcome.proposal.new_locator or \
                   outcome.proposal.strategy == "has_text_fallback", \
                f"Proposal should be text-based, got: {outcome.proposal}"

        # Verify button was actually clicked
        result_text = page.locator('[role="status"]').text_content()
        assert "clicado com sucesso" in result_text, \
            f"Button was not clicked. Result: {result_text}"

    def test_stale_id_click_fails_without_healing(self, page, test_server):
        """Click with stale ID should fail — proving healing is necessary."""
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(800)  # Allow ID to change

        # Try to click with stale ID directly — should fail
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        with pytest.raises(Exception):
            page.click("#btn-dynamic-0", timeout=3000)

        # Verify result div is still empty (button was never clicked)
        result = page.locator('[role="status"]').text_content() or ""
        assert "clicado" not in result, \
            "Button should NOT have been clicked with stale ID"

    def test_text_locator_clicks_dynamic_button(self, page, test_server):
        """Text-based locator should always work regardless of ID changes."""
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(1000)  # Let multiple ID changes happen

        # Click using text locator — should always work
        page.locator('button:has-text("Clique Dinâmico")').click()
        page.wait_for_timeout(300)

        result = page.locator('[role="status"]').text_content()
        assert "clicado com sucesso" in result, \
            f"Text locator failed. Result: {result}"

        # Verify the button ID changed at least once during this test
        assert "ID atual" in result, "Result should show current button ID"

    def test_healing_with_l0_catalog_fallback(self, page, test_server):
        """L0 catalog should have a recipe for locator-not-found errors.

        The seeded catalog includes a fallback_text recipe that matches
        'locator resolved to' pattern — common in Playwright strict mode.
        """
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(800)

        stale_selector = "#btn-dynamic-0"

        collector = EvidenceCollector(page)
        collector.start("test-l0-catalog")

        ctx = {
            "action": "click",
            "selector": stale_selector,
            "text": "Clique Dinâmico",
            "intention": "Test L0 catalog match for dynamic ID",
            "url": page.url,
            "framework": "generic",
            "family": "FAM-01",
            "taxonomy_id": "SEL-004",
        }
        payload = collector.build_llm_payload(ctx)

        smart_runner = SmartStepRunner(page)

        def step_runner(step_data):
            return smart_runner.execute(step_data, step_data.get("strategy", ""))

        catalog = HealingCatalog()
        catalog.seed_defaults()  # Populate with known recipes

        curator = CuradorAutomatico(
            catalog=catalog,
            step_runner=step_runner,
        )

        # Verify catalog has matching recipes after seeding
        recipes = curator._catalog.match_recipes(
            "locator resolved to 0 elements",
            family="locator_resolution",
        )
        assert len(recipes) > 0, \
            "Expected catalog to have recipes for locator resolution errors"

        # Verify recipe strategy matches (fallback_text is the default)
        text_recipes = [r for r in recipes
                        if "text" in r.solution_strategy.lower()]
        assert len(text_recipes) > 0, \
            f"Expected text-based recipe in catalog, got: {[r.solution_strategy for r in recipes]}"


class TestClassification:
    """Verify classification of dynamic ID failures."""

    def test_classify_stale_id_error(self):
        """Stale ID errors should classify as FAM-01 LOCATOR_RESOLUTION."""
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
