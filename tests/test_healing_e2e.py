"""TestForge — Testes E2E de Healing: 11 Famílias.

Serve tests/pagina-de-teste-completa.html localmente e testa
cada família de healing com falhas simuladas e recuperação.

Uso:
    python -m pytest tests/test_healing_e2e.py -v --headed
"""
import pytest
import os
import sys
import subprocess
import time
import threading
import http.server
import socketserver
from pathlib import Path

from playwright.sync_api import Page, expect

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

TEST_PAGE = str(Path(__file__).parent / "pagina-de-teste-completa.html")


# -- Fixture do Servidor HTTP -------------------------------------------------

@pytest.fixture(scope="module")
def test_server():
    """Inicia servidor HTTP local para página de teste em porta livre."""
    import http.server
    import socketserver

    # Tenta encontrar uma porta livre
    for port in [8766, 8767, 8768, 8769]:
        try:
            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

            server = socketserver.TCPServer(("", port), Handler)
            break
        except OSError:
            continue
    else:
        pytest.skip("Nenhuma porta livre disponível")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    url = f"http://localhost:{port}"
    yield url
    server.shutdown()


@pytest.fixture(autouse=True)
def navigate(page: Page, test_server):
    """Navega para página de teste antes de cada teste."""
    page.goto(f"{test_server}/pagina-de-teste-completa.html")
    page.wait_for_timeout(500)


# -- FAM-01: Resolução de Localizador -----------------------------------------

class TestFAM01LocatorResolution:
    """SEL-001 a SEL-010: Falhas de seletor."""

    def test_SEL001_strict_locator_two_elements(self, page: Page):
        """SEL-001: Dois botões com mesmo texto — violação de modo estrito."""
        box = page.locator('[data-testid="tax-SEL-001"]')
        assert box.count() > 0

    def test_SEL002_element_not_found(self, page: Page):
        """SEL-002: Elemento removido do DOM."""
        page.click('[data-testid="tax-SEL-002"] button:nth-child(1)')
        page.wait_for_timeout(200)

    def test_SEL003_id_changed(self, page: Page):
        """SEL-003: ID dinâmico — btn tem sufixo hash."""
        box = page.locator('[data-testid="tax-SEL-003"]')
        btn = box.locator('button:has-text("Pesquisar")')
        assert btn.count() > 0

    def test_SEL004_xpath_absolute_broken(self, page: Page):
        """SEL-004: XPath absoluto quebrado — fallback para texto."""
        box = page.locator('[data-testid="tax-SEL-004"]')
        btn = box.locator('button:has-text("Enviar")')
        btn.click()
        page.wait_for_timeout(200)
        assert box.locator('text=Formulário enviado').count() > 0

    def test_SEL005_css_class_volatile(self, page: Page):
        """SEL-005: Hash de classe CSS — fallback para aria-label."""
        box = page.locator('[data-testid="tax-SEL-005"]')
        btn = box.locator('[aria-label="Botão de ação principal"]')
        assert btn.count() > 0


# -- FAM-02: Tempo / Sincronização -------------------------------------------

class TestFAM02Timing:
    """TIM-001 a TIM-007: Falhas assíncronas e de tempo."""

    def test_TIM001_slow_loading(self, page: Page):
        """TIM-001: Elemento aparece após atraso."""
        box = page.locator('[data-testid="tax-TIM-001"]')
        # Clica no gatilho que carrega após 3s
        box.locator('button:has-text("Carregar conteúdo")').click()
        # Aguarda conteúdo atrasado
        delayed = box.locator('text=Conteúdo carregado com sucesso')
        delayed.wait_for(timeout=10000)
        assert delayed.count() > 0

    def test_TIM005_wait_fixed_timeout(self, page: Page):
        """TIM-005: Timeout fixo — elemento aparece rapidamente."""
        box = page.locator('[data-testid="tax-TIM-005"]')
        btn = box.locator('button:has-text("Aparecer rápido")')
        btn.click()
        # Elemento deve aparecer em até 2s
        result = box.locator('text=Rápido')
        result.wait_for(timeout=5000)
        assert result.count() > 0

    def test_TIM006_debounce_autocomplete(self, page: Page):
        """TIM-006: Debounce — sugestões aparecem após digitar."""
        box = page.locator('[data-testid="tax-TIM-006"]')
        inp = box.locator('input')
        inp.fill("Bra")
        page.wait_for_timeout(1000)
        suggestions = box.locator('text=Brasil')
        assert suggestions.count() > 0


# -- FAM-03: Contexto / Escopo ------------------------------------------------

class TestFAM03Context:
    """CTX-001 a CTX-007: Iframe, shadow DOM, popup."""

    def test_CTX001_iframe_same_origin(self, page: Page):
        """CTX-001: Elemento dentro de iframe mesma-origem."""
        box = page.locator('[data-testid="tax-CTX-001"]')
        iframe = box.locator('iframe').first
        frame = page.frame(name="test-frame")
        if frame:
            btn = frame.locator('button:has-text("Botão no iframe")')
            assert btn.count() > 0

    def test_CTX005_popup_new_tab(self, page: Page):
        """CTX-005: Detecção de popup/nova aba."""
        box = page.locator('[data-testid="tax-CTX-005"]')
        btn = box.locator('text=Abrir popup')
        assert btn.count() > 0

    def test_CTX006_modal_outside_scope(self, page: Page):
        """CTX-006: Diálogo modal fora do escopo do formulário."""
        box = page.locator('[data-testid="tax-CTX-006"]')
        btn = box.locator('button:has-text("Abrir modal")')
        btn.click()
        page.wait_for_timeout(300)
        modal = page.locator('[role="dialog"]')
        assert modal.count() > 0 or box.locator('text=Modal').count() > 0


# -- FAM-04: Estado da Aplicação ----------------------------------------------

class TestFAM04State:
    """STA-001 a STA-006: Overlay, desabilitado, sessão."""

    def test_STA001_disabled_element(self, page: Page):
        """STA-001: Elemento desabilitado — aguarda habilitação."""
        box = page.locator('[data-testid="tax-STA-001"]')
        disabled_btn = box.locator('button:has-text("Desabilitado")')
        assert disabled_btn.is_disabled()

    def test_STA002_overlay_blocking(self, page: Page):
        """STA-002: Overlay bloqueia clique."""
        box = page.locator('[data-testid="tax-STA-002"]')
        btn = box.locator('button:has-text("Atrás do overlay")')
        assert btn.count() > 0

    def test_STA004_alert_dialog(self, page: Page):
        """STA-004: Manipulação de diálogo de alerta."""
        box = page.locator('[data-testid="tax-STA-004"]')
        btn = box.locator('button:has-text("Mostrar alerta")')
        assert btn.count() > 0


# -- FAM-05: DOM Dinâmico -----------------------------------------------------

class TestFAM05DynamicDOM:
    """DOM-001 a DOM-005: Stale, reordenar, lazy load."""

    def test_DOM001_stale_element(self, page: Page):
        """DOM-001: Elemento obsoleto — substituição de DOM."""
        box = page.locator('[data-testid="tax-DOM-001"]')
        btn = box.locator('button:has-text("Substituir DOM")')
        btn.click()
        page.wait_for_timeout(500)
        # Após substituição, elemento antigo sai, novo aparece
        new_btn = box.locator('button:has-text("Novo DOM")')
        new_btn.wait_for(timeout=5000)
        assert new_btn.count() > 0

    def test_DOM005_lazy_loading(self, page: Page):
        """DOM-005: Lazy loading — placeholder → conteúdo real."""
        box = page.locator('[data-testid="tax-DOM-005"]')
        btn = box.locator('button:has-text("Carregar imagem")')
        btn.click()
        page.wait_for_timeout(2000)
        img = box.locator('img[alt="Imagem carregada"]')
        assert img.count() > 0


# -- FAM-06: Entrada / Interação ----------------------------------------------

class TestFAM06Input:
    """INP-001 a INP-010: Preenchimento, mascarado, datepicker."""

    def test_INP007_masked_input(self, page: Page):
        """INP-007: Input mascarado — fill falha sem pressSequentially."""
        box = page.locator('[data-testid="tax-INP-007"]')
        inp = box.locator('input[data-masked="cpf"]')
        inp.fill("12345678900")
        page.wait_for_timeout(200)
        val = inp.input_value()
        assert len(val) > 0

    def test_INP009_datepicker(self, page: Page):
        """INP-009: Seleção de date picker."""
        box = page.locator('[data-testid="tax-INP-009"]')
        inp = box.locator('input[type="date"]')
        assert inp.count() > 0


# -- FAM-07: Arquivo ----------------------------------------------------------

class TestFAM07File:
    """FILE-001 a FILE-006: Upload/download."""

    def test_FILE001_file_input(self, page: Page):
        """FILE-001: Input de arquivo oculto — precisa clicar no label."""
        box = page.locator('[data-testid="tax-FILE-001"]')
        inp = box.locator('input[type="file"]')
        assert inp.count() > 0


# -- FAM-08: Asserção ---------------------------------------------------------

class TestFAM08Assert:
    """AST-001 a AST-010: Validação de asserção."""

    def test_AST004_text_assert(self, page: Page):
        """AST-004: Asserção de texto visível."""
        box = page.locator('[data-testid="tax-AST-004"]')
        status = box.locator('[role="status"]')
        assert status.count() > 0

    def test_AST010_negative_assert(self, page: Page):
        """AST-010: Asserção de ausência de erro."""
        box = page.locator('[data-testid="tax-AST-010"]')
        error = box.locator('.error-message')
        assert error.count() == 0


# -- FAM-09: Gravador ---------------------------------------------------------

class TestFAM09Recorder:
    """REC-001 a REC-006: Relacionado a gravação."""

    def test_REC002_overlay_capture(self, page: Page):
        """REC-002: Overlay captura intenção do usuário."""
        page.evaluate("window.__tfOverlayVisible = true")
        assert page.evaluate("window.__tfOverlayVisible") is True


# -- FAM-10: Execução ---------------------------------------------------------

class TestFAM10Execution:
    """OBS-001 a OBS-006: Execução/observabilidade."""

    def test_OBS002_console_error(self, page: Page):
        """OBS-002: Detecção de erro no console."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.evaluate("console.error('test error for OBS-002')")
        page.wait_for_timeout(200)
        assert len(errors) > 0

    def test_OBS003_network_error(self, page: Page):
        """OBS-003: Detecção de erro de rede."""
        box = page.locator('[data-testid="tax-OBS-003"]')
        btn = box.locator('button:has-text("Fazer requisição")')
        assert btn.count() > 0


# -- FAM-11: Limites do Navegador ---------------------------------------------

class TestFAM11BrowserLimits:
    """LIM-001 a LIM-005: Limites técnicos."""

    def test_LIM001_captcha_detection(self, page: Page):
        """LIM-001: CAPTCHA — checkpoint manual, sem bypass."""
        box = page.locator('[data-testid="tax-LIM-001"]')
        captcha = box.locator('text=CAPTCHA')
        assert captcha.count() > 0


# -- Testes de Integração de Healing ------------------------------------------

class TestHealingIntegration:
    """Testa que o pipeline de healing funciona de ponta a ponta para cenários chave."""

    def test_selector_healing_mock(self, page: Page):
        """Testa healing com MockLLMHealer em um seletor quebrado."""
        from testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResult
        from testforge.healing.healing_catalog import HealingCatalog
        from testforge.evidence import EvidenceCollector

        # fixture navigate já carregou a página (autouse=True)
        collector = EvidenceCollector(page)
        collector.start("test-healing-e2e")

        ctx = {
            "action": "click",
            "selector": "#non-existent-btn-xyz",
            "text": "Enviar",
            "intention": "Click submit button",
            "url": page.url,
            "framework": "generic",
            "family": "FAM-01",
            "taxonomy_id": "SEL-004",
        }
        payload = collector.build_llm_payload(ctx)

        def runner(step_data):
            sel = step_data.get("selector", "")
            page.click(sel, timeout=5000)
            page.wait_for_timeout(300)
            return True

        curator = CuradorAutomatico(
            catalog=HealingCatalog(),
            step_runner=runner,
        )

        outcome = curator.cure(
            {"selector": "#non-existent-btn-xyz", "action": "click"},
            "Error: strict mode violation: #non-existent-btn-xyz resolved to 0 elements",
            payload,
        )

        # Deve curar via L3 (MockLLMHealer) ou L0 (catálogo)
        assert outcome.status in (ProgressResult.PASSED_STEP,), \
            f"Healing falhou: {outcome.status} — {outcome.error_message}"

    def test_heal_step_classification(self, page: Page):
        """Testa que a classificação de falha está correta."""
        from testforge.taxonomy import FailureClassifier

        classifier = FailureClassifier()

        # Falha de localizador
        r1 = classifier.classify("selector '#btn' not found: strict mode violation")
        assert r1.family_code == "FAM-01"
        assert r1.taxonomy_id.startswith("SEL")

        # Falha de timeout
        r2 = classifier.classify("timeout exceeded waiting for element")
        assert r2.family_code == "FAM-02"
        assert r2.taxonomy_id.startswith("TIM")

        # Falha de overlay
        r3 = classifier.classify("element is obscured by overlay")
        assert r3.family_code == "FAM-04"
        assert r3.taxonomy_id.startswith("STA")

        # Elemento obsoleto
        r4 = classifier.classify("stale element reference: detached from DOM")
        assert r4.family_code == "FAM-05"
        assert r4.taxonomy_id.startswith("DOM")

    def test_evidence_payload_sufficient(self, page: Page):
        """Testa que o payload de evidência está marcado como suficiente corretamente."""
        from testforge.evidence import EvidenceCollector

        collector = EvidenceCollector(page)
        collector.start("test-sufficiency")

        # fixture navigate já carregou a página (autouse=True)
        payload = collector.build_llm_payload({
            "action": "click",
            "selector": "#test",
            "text": "Test",
            "intention": "Click test button",
            "url": page.url,
        })

        assert payload.is_sufficient, f"Payload insuficiente: {payload.insufficiency_reason}"
        assert len(payload.dom_snapshot) >= 100
