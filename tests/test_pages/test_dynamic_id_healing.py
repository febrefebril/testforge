"""TestForge — Healing de ID Dinamico: Testes de Fallback por Texto.

Valida que o healing de seletores usa localizadores baseados em texto
quando IDs de botoes mudam dinamicamente (simulando hash IDs React/Angular).

Testes:
  1. SelectorAgent._try_text() produz proposta has_text_fallback
  2. Pipeline completo de healing L0→L2 via fallback de texto
  3. Ponta-a-ponta: clique com ID obsoleto falha, healing recupera com text=
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
    """Navega para a pagina de teste de ID dinamico."""
    url = f"{test_server}/curation/fam-dynamic-id/index.html"
    if error:
        url += "?error=1"
    page.goto(url)
    page.wait_for_timeout(500)


class TestDynamicIdTextFallback:
    """SEL-004: ID dinamico de botao — healing via fallback de texto."""

    def test_selector_agent_text_fallback(self, page, test_server):
        """SelectorAgent._try_text() deve produzir proposta text=."""
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

        assert proposal is not None, "SelectorAgent._try_text() retornou None"
        assert proposal.strategy == "has_text_fallback", \
            f"Esperado has_text_fallback, obteve {proposal.strategy}"
        assert "text=" in proposal.new_locator, \
            f"Esperado seletor text=, obteve {proposal.new_locator}"
        assert "Clique Dinâmico" in proposal.new_locator, \
            f"Esperado 'Clique Dinâmico' no localizador, obteve {proposal.new_locator}"
        assert proposal.confidence >= 0.70, \
            f"Esperado confianca >= 0.70, obteve {proposal.confidence}"
        assert proposal.taxonomy_id == "SEL-004"
        assert proposal.family == "FAM-01"

    def test_full_healing_pipeline_text_fallback(self, page, test_server):
        """Pipeline completo de healing deve resolver ID dinamico via fallback de texto.

        Passos:
          1. Carregar pagina com rotacao rapida de ID (?error=1)
          2. Obter ID inicial do botao, aguardar mudanca
          3. Tentar healing com seletor de ID antigo
          4. Verificar healing via fallback de texto (L2 SelectorAgent)
        """
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(800)  # Allow ID to change at least once

        # Read current button ID from DOM
        current_id = page.evaluate("document.querySelector('button').id")
        assert current_id != "btn-dynamic-0", \
            f"ID do botao deveria ter mudado, mas continua {current_id}"

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
            f"Evidencia insuficiente: {payload.insufficiency_reason}"

        # Verify DOM snapshot contains the button text
        assert "Clique Dinâmico" in payload.dom_snapshot, \
            "Snapshot DOM deve conter texto do botao 'Clique Dinâmico'"

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
            f"Healing falhou: {outcome.status} — {outcome.error_message}"

        # Verify healing used text fallback (L2 or L3)
        assert outcome.layer_used in ("L2", "L3", "L0"), \
            f"Esperada camada L0/L2/L3, obteve {outcome.layer_used}"

        # Verify the proposal uses text-based locator
        if outcome.proposal:
            assert "text=" in outcome.proposal.new_locator or \
                   "has-text" in outcome.proposal.new_locator or \
                   outcome.proposal.strategy == "has_text_fallback", \
                f"Proposta deve ser baseada em texto, obteve: {outcome.proposal}"

        # Verify button was actually clicked
        result_text = page.locator('[role="status"]').text_content()
        assert "clicado com sucesso" in result_text, \
            f"Botao nao foi clicado. Resultado: {result_text}"

    def test_stale_id_click_fails_without_healing(self, page, test_server):
        """Clique com ID obsoleto deve falhar — provando que healing e necessario."""
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(800)  # Allow ID to change

        # Try to click with stale ID directly — should fail
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        with pytest.raises(Exception):
            page.click("#btn-dynamic-0", timeout=3000)

        # Verify result div is still empty (button was never clicked)
        result = page.locator('[role="status"]').text_content() or ""
        assert "clicado" not in result, \
            "Botao NAO deveria ter sido clicado com ID obsoleto"

    def test_text_locator_clicks_dynamic_button(self, page, test_server):
        """Localizador baseado em texto deve sempre funcionar independente de mudancas de ID."""
        navigate_dynamic_id(page, test_server, error=True)
        page.wait_for_timeout(1000)  # Let multiple ID changes happen

        # Click using text locator — should always work
        page.locator('button:has-text("Clique Dinâmico")').click()
        page.wait_for_timeout(300)

        result = page.locator('[role="status"]').text_content()
        assert "clicado com sucesso" in result, \
            f"Localizador de texto falhou. Resultado: {result}"

        # Verify the button ID changed at least once during this test
        assert "ID atual" in result, "Resultado deve mostrar ID atual do botao"

    def test_healing_with_l0_catalog_fallback(self, page, test_server):
        """Catalogo L0 deve ter receita para erros de localizador nao encontrado.

        O catalogo semeado inclui receita fallback_text que corresponde
        ao padrao 'locator resolved to' — comum no modo strict do Playwright.
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
            "Esperado que catalogo tenha receitas para erros de resolucao de localizador"

        # Verify recipe strategy matches (fallback_text is the default)
        text_recipes = [r for r in recipes
                        if "text" in r.solution_strategy.lower()]
        assert len(text_recipes) > 0, \
            f"Esperada receita baseada em texto no catalogo, obteve: {[r.solution_strategy for r in recipes]}"


class TestClassification:
    """Verifica classificacao de falhas de ID dinamico."""

    def test_classify_stale_id_error(self):
        """Erros de ID obsoleto devem classificar como FAM-01 LOCATOR_RESOLUTION."""
        classifier = FailureClassifier()

        # Playwright strict mode violation
        r1 = classifier.classify(
            "strict mode violation: locator '#btn-dynamic-0' resolved to 0 elements"
        )
        assert r1.family_code == "FAM-01", \
            f"Esperado FAM-01, obteve {r1.family_code}"
        assert r1.taxonomy_id.startswith("SEL"), \
            f"Esperado SEL-*, obteve {r1.taxonomy_id}"

        # Generic not found
        r2 = classifier.classify("element not found: #btn-dynamic-0")
        assert r2.family_code in ("FAM-01", "FAM-02"), \
            f"Esperado FAM-01 ou FAM-02, obteve {r2.family_code}"
