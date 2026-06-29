"""TestForge — Sprint B: locator and post-condition resilience.

Two changes for SIOPI Material currencymask failure mode:

1. `_is_ambiguous_only_selector` + filtered `_top_css_selectors`: drops
   `input[placeholder="R$0,00"]`-style selectors from the cascade when a
   more specific candidate already exists, so healing does not pick a
   different input that happens to share the same placeholder.

2. Soft post-condition for click: when the next step's literal selector
   cannot be found (Angular Material aria-label volatilizes when focus
   moves), tries `get_by_label` / `get_by_role(name=)` as final native
   fallback; if still not found, returns passed=True with soft warning
   instead of failing. The click already executed — predicting the next
   step's visibility is a soft oracle, not a hard one. Failures of the
   next step itself are surfaced when that step runs.
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest

from testforge.semantic.compiler import PlaywrightCompiler
from testforge.runner.step_postcondition import StepPostconditionValidator
from testforge.runner.step_result import PostconditionResult


class TestAmbiguousSelectorDetection:
    def test_pure_currency_placeholder_is_ambiguous(self):
        assert PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder="R$0,00"]'
        )

    def test_currency_placeholder_with_aria_label_is_not_ambiguous(self):
        assert not PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder="R$0,00"][aria-label="Renda mensal *"]'
        )

    def test_date_placeholder_is_ambiguous(self):
        assert PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder="DD/MM/AAAA"]'
        )

    def test_cpf_placeholder_is_ambiguous(self):
        assert PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder="000.000.000-00"]'
        )

    def test_id_selector_is_not_ambiguous(self):
        assert not PlaywrightCompiler._is_ambiguous_only_selector("input#renda_mensal")

    def test_prefix_match_currency_is_ambiguous(self):
        assert PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder^="R$0,00"]'
        )

    def test_non_placeholder_attribute_not_filtered(self):
        # aria-label is not a generic placeholder — keep it
        assert not PlaywrightCompiler._is_ambiguous_only_selector(
            'input[aria-label="Renda mensal *"]'
        )

    def test_specific_placeholder_not_filtered(self):
        # Unusual placeholder, unlikely to clash — keep
        assert not PlaywrightCompiler._is_ambiguous_only_selector(
            'input[placeholder="Digite seu nome completo"]'
        )


class TestTopCssSelectorsFiltering:
    def _make_target(self, selectors_and_scores):
        target = MagicMock()
        candidates = []
        for sel, score in selectors_and_scores:
            c = MagicMock()
            c.selector = sel
            c.score = score
            candidates.append(c)
        target.candidates = candidates
        return target

    def test_keeps_specific_drops_ambiguous_when_both_present(self):
        compiler = PlaywrightCompiler()
        target = self._make_target([
            ('input[aria-label="Renda mensal *"]', 1.0),
            ('input[placeholder="R$0,00"][aria-label="Renda mensal *"]', 0.9),
            ('input[placeholder="R$0,00"]', 0.5),
            ('input[aria-label^="Renda mensal *"]', 0.4),
            ('input[placeholder^="R$0,00"]', 0.3),
        ])
        result = compiler._top_css_selectors(target)
        assert 'input[placeholder="R$0,00"]' not in result
        assert 'input[placeholder^="R$0,00"]' not in result
        assert 'input[aria-label="Renda mensal *"]' in result

    def test_keeps_ambiguous_when_no_specific_exists(self):
        # Degenerate case — only ambiguous selectors. Better to emit them
        # than emit nothing; healer fingerprint can still disambiguate.
        compiler = PlaywrightCompiler()
        target = self._make_target([
            ('input[placeholder="R$0,00"]', 0.5),
            ('input[placeholder^="R$0,00"]', 0.4),
        ])
        result = compiler._top_css_selectors(target)
        assert result == [
            'input[placeholder="R$0,00"]',
            'input[placeholder^="R$0,00"]',
        ]

    def test_empty_target_returns_empty(self):
        compiler = PlaywrightCompiler()
        target = MagicMock()
        target.candidates = []
        assert compiler._top_css_selectors(target) == []

    def test_none_target_returns_empty(self):
        compiler = PlaywrightCompiler()
        assert compiler._top_css_selectors(None) == []


class TestSoftPostConditionForClick:
    def _build_validator(self, page):
        return StepPostconditionValidator(page=page)

    def _make_step(self, action="click", context=None):
        step = MagicMock()
        step.action = action
        step.context = context or {}
        step.target = MagicMock()
        step.target.candidates = []
        return step

    def _make_next_step(self, candidates_selectors, role="", accessible_name="", label=""):
        step = MagicMock()
        step.action = "click"
        step.target = MagicMock()
        cands = []
        for sel in candidates_selectors:
            c = MagicMock()
            c.selector = sel
            cands.append(c)
        step.target.candidates = cands
        step.target.accessible_name = accessible_name
        step.target.role = role
        step.target.label = label
        return step

    def test_soft_pass_when_native_label_locator_matches(self):
        page = MagicMock()
        page.url = "https://app/x"
        # Original CSS selectors fail
        page.wait_for_selector.side_effect = Exception("not found")
        # get_by_label finds the element
        loc = MagicMock()
        loc.first.wait_for.return_value = None
        page.get_by_label.return_value = loc

        v = self._build_validator(page)
        step = self._make_step()
        next_step = self._make_next_step(
            ['input[aria-label="Renda mensal *"]'],
            accessible_name="Renda mensal *",
            label="Renda mensal *",
        )

        result = v._validate_click(step, next_step, url_before="https://app/x")
        assert result.passed
        assert result.checks.get("soft_match") in ("label", "name-as-label", "role+name")

    def test_soft_pass_when_native_role_locator_matches(self):
        page = MagicMock()
        page.url = "https://app/x"
        page.wait_for_selector.side_effect = Exception("not found")
        # Make get_by_label fail too so the role+name path is exercised
        page.get_by_label.side_effect = Exception("no label")
        role_loc = MagicMock()
        role_loc.first.wait_for.return_value = None
        page.get_by_role.return_value = role_loc

        v = self._build_validator(page)
        step = self._make_step()
        next_step = self._make_next_step(
            ['button[name="Calcular"]'],
            role="button",
            accessible_name="Calcular",
        )

        result = v._validate_click(step, next_step, url_before="https://app/x")
        assert result.passed
        assert result.checks.get("soft_match") == "role+name"

    def test_soft_pass_falls_back_to_unverified_when_everything_fails(self):
        page = MagicMock()
        page.url = "https://app/x"
        page.wait_for_selector.side_effect = Exception("not found")
        page.get_by_label.side_effect = Exception("no label")
        page.get_by_role.side_effect = Exception("no role")

        v = self._build_validator(page)
        step = self._make_step()
        next_step = self._make_next_step(
            ['input[aria-label="Renda mensal *"]'],
            accessible_name="Renda mensal *",
            label="Renda mensal *",
        )

        result = v._validate_click(step, next_step, url_before="https://app/x")
        # Sprint B: never FAIL on next-step prediction alone — click executed
        assert result.passed
        assert result.checks.get("next_step_soft_pass") is True
        assert result.checks.get("next_step_visible") is False

    def test_hard_fail_still_used_for_causes_navigation_url_check(self):
        page = MagicMock()
        page.url = "https://app/x"  # unchanged
        page.wait_for_selector.side_effect = Exception("not found")

        v = self._build_validator(page)
        step = self._make_step(context={"causes_navigation": True})
        next_step = self._make_next_step(['input[aria-label="X"]'])

        result = v._validate_click(step, next_step, url_before="https://app/x")
        # Soft pass does not apply to causes_navigation — URL change is the
        # actual oracle there. Next-step probing is fallback when URL same.
        assert not result.passed
        assert "url_not_changed" in result.failures

    def test_passes_when_first_selector_visible(self):
        page = MagicMock()
        page.url = "https://app/x"
        page.wait_for_selector.return_value = None  # found visible

        v = self._build_validator(page)
        step = self._make_step()
        next_step = self._make_next_step(['input[aria-label="OK"]'])

        result = v._validate_click(step, next_step, url_before="https://app/x")
        assert result.passed
        assert result.checks.get("next_step_visible") is True
        assert "soft" not in (result.message or "")
