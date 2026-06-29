"""Bugs encontrados no log test-pos-hotfix10:

* B23 — acerto no catalogo L0 retornou PASSED_STEP com proposal=None. O
  caminho legado entao logou
    `Curador: PASSED_STEP [L0]
     Curador: REJEITADO — locator generico/perigoso: ''`
  O passo curado estava realmente ok, mas a exibicao downstream via um
  seletor vazio. Correcao: anexar um LLMHealingProposal espelhando o
  solution_selector + strategy + confidence 0.95 da receita.

* B24/B25 — selector_agent._try_text aceitava qualquer texto >= 2 caracteres,
  incluindo "JAN", "1992", "1", e as palavras simples "OK"/"Calcular".
  Resultado: curas contra celulas de calendario e botoes genericos que nao
  tem nada a ver com o alvo. Correcao: tamanho minimo 6, rejeitar numericos
  puros, rejeitar uma pequena lista de verbos de UI comuns.

* B27 — L3 LLM intermitentemente emite {"new_selector": "..."} ou
  {"selector": "..."} ao inves de {"new_locator": "..."}. O parser
  silenciosamente descartava a cura e reportava UNRESOLVED com confianca 0.
  Correcao: aceitar o conjunto completo de alias.

* B28 — mesmo bug de parser do B27, manifestado como `Curador: UNRESOLVED [L3] →
  button.mat-calendar-previous-button (conf=0.00)` — o texto do seletor
  vazou mas nao foi armazenado na proposta.
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


# ---- B23: L0 anexa uma proposta -------------------------------------------------


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
        # O argumento `family` e extraido de dentro do outcome; precisamos
        # apenas que o metodo privado retorne um outcome completo.
        outcome = curator._try_layer0_catalog(
            family="FAM-01",
            step_data={"selector": "a.dead-link"},
            error_message="Locator not found",
        )
        assert outcome is not None
        assert outcome.status == ProgressResult.PASSED_STEP
        assert outcome.layer_used == "L0"
        assert outcome.proposal is not None, (
            "Acerto L0 deve anexar uma proposta — proposta vazia aciona "
            "o filtro de localizador perigoso downstream (B19/B20). Veja B23."
        )
        assert outcome.proposal.new_locator == 'button[data-testid="continue"]'
        assert outcome.proposal.confidence >= 0.5
        assert outcome.proposal.strategy == "data_testid_fallback"


# ---- B24/B25: guarda semantico do fallback text= --------------------------------


class TestTextFallbackGuards:
    def _agent(self):
        return SelectorAgent()

    def test_three_letter_calendar_label_rejected(self):
        # "JAN" — rotulo de mes no datepicker SIOPI.
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
                f"Verbo generico {word!r} deve ser rejeitado"
            )

    def test_meaningful_label_is_accepted(self):
        proposal = self._agent()._try_text("Proximo passo")
        assert proposal is not None
        assert proposal.new_locator == 'text="Proximo passo"'
        assert proposal.strategy == "has_text_fallback"

    def test_long_meaningful_text_accepted(self):
        target = "Valor + renda Ja escolheu a casa?"
        proposal = self._agent()._try_text(target)
        assert proposal is not None
        assert target.replace('"', '\\"') in proposal.new_locator


# ---- B27/B28: aliases de chave LLM -----------------------------------------------


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
        """A chave exata observada no log SIOPI L3."""
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
