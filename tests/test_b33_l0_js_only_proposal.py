"""B33 — L0 catalog js-only recipes carried empty new_locator.

After B23 attached an LLMHealingProposal to every L0 hit, the legacy
run still rejected three SIOPI asserts with
  `Curador: PASSED_STEP [L0] →  (conf=0.95)
   Curador: REJEITADO — locator generico/perigoso: ''`

Root cause: some catalog recipes fix the step via `solution_js`
(e.g. `el.click()` force-click) and leave `solution_selector` empty.
B23 mirrored that empty value into the proposal; the dangerous-
locator filter (B19/B20) then rejected the cure even though the
step actually passed.

Fix: when `solution_selector` is empty, fall back to the step's
original selector. It's already passing through the runner's own
sanity checks, the filter accepts long-but-specific CSS paths, and
the cure is real (the JS ran).

This file pins:
1. Recipes WITH a solution_selector still carry it (back-compat).
2. Recipes WITHOUT a solution_selector carry the step's original
   selector instead of the empty string.
3. The rationale notes "js-only" so the operator can see why.
"""
from __future__ import annotations

from dataclasses import dataclass

from testforge.healing.curator import CuradorAutomatico, ProgressResult


@dataclass
class _Recipe:
    recipe_id: str = "REC-001"
    priority: int = 9
    solution_selector: str = ""
    solution_strategy: str = "force_click"
    solution_js: str = "el.click()"
    taxonomy_id: str = "ACT-001"


class _FakeCatalog:
    def __init__(self, recipes):
        self._recipes = recipes
        self.used = []

    def match_recipes(self, error, family=""):
        return self._recipes

    def record_usage(self, recipe_id):
        self.used.append(recipe_id)

    def record_success(self, recipe_id):
        self.used.append(recipe_id)


class TestB33EmptySelectorFallsBack:
    def test_js_only_recipe_borrows_step_selector(self):
        catalog = _FakeCatalog([_Recipe(solution_selector="")])
        curator = CuradorAutomatico(catalog=catalog, step_runner=None)
        original = ('app-root > app-calculadora > div.bg-highlight-1 > '
                    'div.bg-neutral-1 > button.calc-btn')
        outcome = curator._try_layer0_catalog(
            family="FAM-02",
            step_data={"selector": original},
            error_message="Element not clickable",
        )
        assert outcome is not None
        assert outcome.status == ProgressResult.PASSED_STEP
        assert outcome.proposal is not None
        # Empty solution_selector → use the step's original selector.
        assert outcome.proposal.new_locator == original
        assert "js-only" in outcome.proposal.rationale

    def test_recipe_with_selector_unchanged(self):
        recipe = _Recipe(
            solution_selector='button[data-testid="continue"]',
            solution_strategy="data_testid_fallback",
            solution_js="",
        )
        catalog = _FakeCatalog([recipe])
        curator = CuradorAutomatico(catalog=catalog, step_runner=None)
        outcome = curator._try_layer0_catalog(
            family="FAM-01",
            step_data={"selector": "a.dead-link"},
            error_message="Locator not found",
        )
        assert outcome is not None
        assert outcome.proposal.new_locator == 'button[data-testid="continue"]'
        # No "js-only" tag when solution_selector is present.
        assert "js-only" not in outcome.proposal.rationale


class TestNoStepSelectorYieldsEmpty:
    def test_step_with_no_selector_leaves_locator_empty(self):
        catalog = _FakeCatalog([_Recipe(solution_selector="")])
        curator = CuradorAutomatico(catalog=catalog, step_runner=None)
        outcome = curator._try_layer0_catalog(
            family="FAM-02",
            step_data={},   # no selector
            error_message="Element not clickable",
        )
        assert outcome is not None
        assert outcome.proposal.new_locator == ""
        # Filter will reject this downstream, which is correct: there's
        # genuinely no locator to display.
