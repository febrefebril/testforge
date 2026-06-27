"""B18+B19+B20 — protection against the SIOPI false-positive cascade.

A SIOPI run produced 26 consecutive L2 heals all resolving to
`a[href="/"]` (the site root link), oracle-approved as success because
the link existed on every page. Three structural causes:

  B18  selector_agent._try_href grepped the first <a href> in the DOM,
       which was the SIOPI logo (`<a href="/">`).
  B19  the dangerous-locator deny-list did not cover `a[href="/"]`.
  B20  the legacy `run` path didn't apply the dangerous-locator filter
       at all.

This file pins:
  * a[href="/"] is treated as dangerously generic.
  * Several related generic anchors are caught too.
  * selector_agent._try_href requires a semantic text overlap before
    proposing an anchor cure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

from testforge.runner.dangerous_locator import (
    DANGEROUS_LOCATORS,
    is_dangerously_generic,
)
from testforge.healing.agents.selector_agent import SelectorAgent


# ---- B19: dangerous-locator deny-list ----------------------------------------


class TestDangerousLocatorList:
    @pytest.mark.parametrize("selector", [
        'a[href="/"]',
        "a[href='/']",
        'a[href="#"]',
        'a[href=""]',
        'a[href="/home"]',
        'a[href="javascript:void(0)"]',
        '[role="button"]',
        '[role="link"]',
        '[role="listitem"]',
        "a", "body", "div", "span", "button",
        "text=ok", "text=cancelar", "text=continuar",
    ])
    def test_known_generic_selectors_are_rejected(self, selector):
        assert is_dangerously_generic(selector), (
            f"Expected {selector!r} to be rejected as dangerously generic"
        )

    @pytest.mark.parametrize("selector", [
        'input[aria-label="Renda mensal *"]',
        'a[href="/calculadora-egi"]',
        'button[data-testid="enviar-cadastro"]',
        '[role="button"]:has-text("Calculadora poder de compra")',
    ])
    def test_specific_selectors_are_accepted(self, selector):
        assert not is_dangerously_generic(selector), (
            f"Expected {selector!r} to be accepted"
        )

    def test_empty_or_none_is_dangerous(self):
        assert is_dangerously_generic("")
        assert is_dangerously_generic(None)

    def test_full_html_xpath_is_dangerous(self):
        assert is_dangerously_generic('/html/body/div[1]/div[2]')
        assert is_dangerously_generic('xpath=/html/body/div')

    def test_short_nth_child_is_dangerous(self):
        # Real SIOPI failure: 'a:nth-child(1)' as a cure proposal.
        assert is_dangerously_generic("a:nth-child(1)")
        # But a longer chain is allowed (qualifier present).
        assert not is_dangerously_generic(
            'div#formInit > div.bg-neutral-1 > a:nth-child(1)'
        )


class TestDangerousSetIsFrozen:
    def test_set_is_frozenset(self):
        # B19 invariant: deny-list is immutable. Tests cannot poison it
        # for sibling tests.
        assert isinstance(DANGEROUS_LOCATORS, frozenset)


# ---- B18: selector_agent._try_href requires semantic overlap -----------------


@dataclass
class _Payload:
    """Minimal stand-in for EvidencePayload used by SelectorAgent._try_href."""
    dom_snapshot: str = ""
    step_context: dict = field(default_factory=dict)
    is_sufficient: bool = True


def _agent() -> SelectorAgent:
    return SelectorAgent()


class TestTryHrefRequiresSemanticMatch:
    def test_site_root_anchor_no_longer_proposed(self):
        """The exact SIOPI failure mode: DOM has `<a href="/">`,
        step_context.text is something specific like "Calculadora poder
        de compra". The agent must NOT propose `a[href="/"]`."""
        dom = (
            '<header><a href="/"><img alt="logo"/></a></header>'
            '<main><a href="/calculadora-egi">Calculadora poder de compra</a></main>'
        )
        payload = _Payload(
            dom_snapshot=dom,
            step_context={
                "text": "Calculadora poder de compra",
                "selector": "app-root > app-simulacao-indice > div.foo",
            },
        )
        result = _agent()._try_href(payload)
        # Either: returns a specific match (a[href="/calculadora-egi"])
        # or returns None (if logic conservatively refused).
        if result is not None:
            assert 'href="/"' not in result.new_locator, (
                f"Agent proposed the dangerous site-root anchor: "
                f"{result.new_locator!r}"
            )
            assert result.new_locator == 'a[href="/calculadora-egi"]'

    def test_empty_target_text_refuses_to_propose(self):
        """Without target text, we can't tell a meaningful link from
        the site logo. Refuse to propose anything."""
        dom = '<header><a href="/">Home</a></header>'
        payload = _Payload(
            dom_snapshot=dom,
            step_context={"text": "", "selector": "app-root > div"},
        )
        assert _agent()._try_href(payload) is None

    def test_short_target_text_also_refuses(self):
        dom = '<header><a href="/somewhere">X</a></header>'
        payload = _Payload(
            dom_snapshot=dom,
            step_context={"text": "X", "selector": "div"},
        )
        # Less than 3 chars — too ambiguous.
        assert _agent()._try_href(payload) is None

    def test_no_semantic_match_returns_none(self):
        dom = (
            '<a href="/">Home</a>'
            '<a href="/about">Sobre nós</a>'
        )
        payload = _Payload(
            dom_snapshot=dom,
            step_context={
                "text": "Calculadora poder de compra",
                "selector": "div",
            },
        )
        assert _agent()._try_href(payload) is None, (
            "No anchor in the DOM matches the target text — agent "
            "must not propose anything."
        )

    def test_matching_anchor_is_proposed(self):
        dom = (
            '<a href="/">Home</a>'
            '<a href="/calc-egi">Calculadora poder de compra</a>'
        )
        payload = _Payload(
            dom_snapshot=dom,
            step_context={
                "text": "Calculadora poder de compra",
                "selector": "div",
            },
        )
        result = _agent()._try_href(payload)
        assert result is not None
        assert result.new_locator == 'a[href="/calc-egi"]'
        # Confidence stays in a reasonable band.
        assert 0.6 <= result.confidence <= 0.9
