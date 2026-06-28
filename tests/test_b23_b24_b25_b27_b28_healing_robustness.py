"""Bugs found in test-pos-hotfix10 log:

* B23 — L0 catalog hit returned PASSED_STEP with proposal=None. The
  legacy run path then logged
    `Curador: PASSED_STEP [L0]
     Curador: REJEITADO — locator generico/perigoso: ''`
  The healed step was actually fine, but downstream display saw an
  empty selector. Fix: attach an LLMHealingProposal mirroring the
  recipe's solution_selector + strategy + confidence 0.95.

* B24/B25 — selector_agent._try_text accepted any text >= 2 chars,
  including "JAN", "1992", "1", and the bare "OK"/"Calcular" word.
  Result: heals against calendar cells and generic buttons that have
  nothing to do with the target. Fix: minimum length 6, reject pure
  numerics, reject a small blocklist of common UI verbs.

* B27 — L3 LLM intermittently emits {"new_selector": "..."} or
  {"selector": "..."} instead of {"new_locator": "..."}. Parser
  silently dropped the cure and reported UNRESOLVED with confidence 0.
  Fix: accept the full alias set.

* B28 — same parser bug as B27, surfaced as `Curador: UNRESOLVED [L3] →
  button.mat-calendar-previous-button (conf=0.00)` — the selector
  text leaked through but was not stored on the proposal.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from testforge.healing.agents.selector_agent import SelectorAgent
from testforge.healing.curator import (
    CuradorAutomatico,
    ProgressResult,
)
from testforge.healing.healing_catalog import HealingCatalog
from testforge.healing.llm_healer import _parse_response


# ---- B23: L0 attaches a proposal ----------------------------------------------


@dataclass
class _Recipe:
    recipe_id: str = "REC-001"
    priority: int = 9
    solution_selector: str = 'button[data-testid="continue"]'
    solution_strategy: str = "data_testid_fallback"
    taxonomy_id: str = "SEL-004"


class _FakeCatalog:
    def __init__(self, recipes: list[_Recipe]):
        self._recipes = recipes
        self.used: list[str] = []

    def match_recipes(self, error: str, family: str = ""):
        return self._recipes

    def record_usage(self, recipe_id: str):
        self.used.append(recipe_id)

    def record_success(self, recipe_id: str):
        self.used.append(recipe_id)


class TestL0CatalogAttachesProposal:
    def test_proposal_carries_solution_selector(self):
        catalog = _FakeCatalog([_Recipe()])
        curator = CuradorAutomatico(catalog=catalog, step_runner=None)
        # `family` argument is taken from inside the outcome; we only
        # need the private method to return a complete outcome.
        outcome = curator._try_layer0_catalog(
            family="FAM-01",
            step_data={"selector": "a.dead-link"},
            error_message="Locator not found",
        )
        assert outcome is not None
        assert outcome.status == ProgressResult.PASSED_STEP
        assert outcome.layer_used == "L0"
        assert outcome.proposal is not None, (
            "L0 hit must attach a proposal — empty proposal triggers "
            "the dangerous-locator filter downstream (B19/B20). See B23."
        )
        assert outcome.proposal.new_locator == 'button[data-testid="continue"]'
        assert outcome.proposal.confidence >= 0.5
        assert outcome.proposal.strategy == "data_testid_fallback"


# ---- B24/B25: text= fallback semantic guard ---------------------------------


class TestTextFallbackGuards:
    def _agent(self):
        return SelectorAgent()

    def test_three_letter_calendar_label_rejected(self):
        # "JAN" — month label on the SIOPI datepicker.
        assert self._agent()._try_text("JAN") is None

    def test_four_digit_year_rejected(self):
        assert self._agent()._try_text("1992") is None

    def test_pure_digits_rejected(self):
        assert self._agent()._try_text("1") is None
        assert self._agent()._try_text("123456") is None
        assert self._agent()._try_text("01/01/1992") is None

    def test_generic_ui_verbs_rejected(self):
        for word in ("OK", "Cancelar", "Continuar", "Home", "Calcular"):
            assert self._agent()._try_text(word) is None, (
                f"Generic verb {word!r} must be rejected"
            )

    def test_meaningful_label_is_accepted(self):
        proposal = self._agent()._try_text("Próximo passo")
        assert proposal is not None
        assert proposal.new_locator == 'text="Próximo passo"'
        assert proposal.strategy == "has_text_fallback"

    def test_long_meaningful_text_accepted(self):
        target = "Valor + renda Já escolheu a casa?"
        proposal = self._agent()._try_text(target)
        assert proposal is not None
        assert target.replace('"', '\\"') in proposal.new_locator


# ---- B27/B28: LLM key aliases ------------------------------------------------


class TestLLMParserAcceptsAllKeys:
    def _wrap(self, payload: dict) -> str:
        return json.dumps(payload)

    def test_canonical_new_locator_key_still_works(self):
        text = self._wrap({"new_locator": "a#x"})
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "a#x"

    def test_selector_alias_works(self):
        text = self._wrap({"selector": "a#x"})
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "a#x"

    def test_new_selector_alias_works(self):
        """The exact key observed in the SIOPI L3 log."""
        text = self._wrap({"new_selector": "button.mat-calendar-previous-button"})
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "button.mat-calendar-previous-button"

    def test_css_selector_alias_works(self):
        text = self._wrap({"css_selector": "input#cpf"})
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "input#cpf"

    def test_locator_alias_works(self):
        text = self._wrap({"locator": "[data-testid='x']"})
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "[data-testid='x']"

    def test_first_non_empty_alias_wins(self):
        text = self._wrap({
            "new_locator": "",
            "selector": "a#match",
            "new_selector": "should_not_win",
        })
        proposal = _parse_response(text)
        assert proposal is not None
        assert proposal.new_locator == "a#match"
