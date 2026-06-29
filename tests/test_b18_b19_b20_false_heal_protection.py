"""B18+B19+B20 — protecao contra cascata de falso-positivo SIOPI.

Uma execucao SIOPI produziu 26 curas L2 consecutivas resolvendo para
`a[href="/"]` (link raiz do site), aprovado pelo oraculo como sucesso porque
o link existia em todas as paginas. Tres causas estruturais:

  B18  selector_agent._try_href capturava o primeiro <a href> no DOM,
       que era o logo SIOPI (`<a href="/">`).
  B19  a lista de negacao de localizadores perigosos nao cobria `a[href="/"]`.
  B20  o caminho legado `run` nao aplicava o filtro de localizador perigoso.

Este arquivo fixa:
  * a[href="/"] e tratado como genericamente perigoso.
  * Varios anchors genericos relacionados tambem sao capturados.
  * selector_agent._try_href exige sobreposicao de texto semantico antes
    de propor uma cura por anchor.
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


# ---- B19: lista de negacao de localizadores perigosos --------------------------


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
            f"Esperado {selector!r} ser rejeitado como genericamente perigoso"
        )

    @pytest.mark.parametrize("selector", [
        'input[aria-label="Renda mensal *"]',
        'a[href="/calculadora-egi"]',
        'button[data-testid="enviar-cadastro"]',
        '[role="button"]:has-text("Calculadora poder de compra")',
    ])
    def test_specific_selectors_are_accepted(self, selector):
        assert not is_dangerously_generic(selector), (
            f"Esperado {selector!r} ser aceito"
        )

    def test_empty_or_none_is_dangerous(self):
        assert is_dangerously_generic("")
        assert is_dangerously_generic(None)

    def test_full_html_xpath_is_dangerous(self):
        assert is_dangerously_generic('/html/body/div[1]/div[2]')
        assert is_dangerously_generic('xpath=/html/body/div')

    def test_short_nth_child_is_dangerous(self):
        # Falha SIOPI real: 'a:nth-child(1)' como proposta de cura.
        assert is_dangerously_generic("a:nth-child(1)")
        # Mas uma cadeia mais longa e permitida (qualificador presente).
        assert not is_dangerously_generic(
            'div#formInit > div.bg-neutral-1 > a:nth-child(1)'
        )


class TestDangerousSetIsFrozen:
    def test_set_is_frozenset(self):
        # Invariante B19: lista de negacao e imutavel. Testes nao podem
        # envenena-la para testes irmaos.
        assert isinstance(DANGEROUS_LOCATORS, frozenset)


# ---- B18: selector_agent._try_href exige sobreposicao semantica -----------------


@dataclass
class _Payload:
    """Substituto minimo para EvidencePayload usado por SelectorAgent._try_href."""
    dom_snapshot: str = ""
    step_context: dict = field(default_factory=dict)
    is_sufficient: bool = True


def _agent() -> SelectorAgent:
    return SelectorAgent()


class TestTryHrefRequiresSemanticMatch:
    def test_site_root_anchor_no_longer_proposed(self):
        """Modo de falha SIOPI exato: DOM tem `<a href="/">`,
        step_context.text e algo especifico como "Calculadora poder
        de compra". O agente NAO deve propor `a[href="/"]`."""
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
        # Ou: retorna uma correspondencia especifica (a[href="/calculadora-egi"])
        # ou retorna None (se a logica conservadoramente recusou).
        if result is not None:
            assert 'href="/"' not in result.new_locator, (
                f"Agente propos o anchor perigoso de raiz do site: "
                f"{result.new_locator!r}"
            )
            assert result.new_locator == 'a[href="/calculadora-egi"]'

    def test_empty_target_text_refuses_to_propose(self):
        """Sem texto alvo, nao podemos distinguir um link significativo
        do logo do site. Recusar propor qualquer coisa."""
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
        # Menos de 3 caracteres — muito ambíguo.
        assert _agent()._try_href(payload) is None

    def test_no_semantic_match_returns_none(self):
        dom = (
            '<a href="/">Home</a>'
            '<a href="/about">Sobre nos</a>'
        )
        payload = _Payload(
            dom_snapshot=dom,
            step_context={
                "text": "Calculadora poder de compra",
                "selector": "div",
            },
        )
        assert _agent()._try_href(payload) is None, (
            "Nenhum anchor no DOM corresponde ao texto alvo — agente "
            "nao deve propor nada."
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
        # Confianca permanece em uma faixa razoavel.
        assert 0.6 <= result.confidence <= 0.9
