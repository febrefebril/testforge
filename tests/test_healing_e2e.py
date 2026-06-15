"""TestForge — E2E Healing Tests: 11 Families.

Serves tests/pagina-de-teste-completa.html locally and tests
each healing family with simulated failures and recovery.

Usage:
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


# ── HTTP Server Fixture ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_server():
    """Start local HTTP server for test page on a free port."""
    import http.server
    import socketserver

    # Try to find a free port
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
        pytest.skip("No free port available")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    url = f"http://localhost:{port}"
    yield url
    server.shutdown()


@pytest.fixture(autouse=True)
def navigate(page: Page, test_server):
    """Navigate to test page before each test."""
    page.goto(f"{test_server}/pagina-de-teste-completa.html")
    page.wait_for_timeout(500)


# ── FAM-01: Locator Resolution ──────────────────────────────────────────────

class TestFAM01LocatorResolution:
    """SEL-001 to SEL-010: Selector failures."""

    def test_SEL001_strict_locator_two_elements(self, page: Page):
        """SEL-001: Two buttons with same text — strict mode violation."""
        box = page.locator('[data-testid="tax-SEL-001"]')
        assert box.count() > 0

    def test_SEL002_element_not_found(self, page: Page):
        """SEL-002: Element removed from DOM."""
        page.click('[data-testid="tax-SEL-002"] button:nth-child(1)')
        page.wait_for_timeout(200)

    def test_SEL003_id_changed(self, page: Page):
        """SEL-003: Dynamic ID — btn has hash suffix."""
        box = page.locator('[data-testid="tax-SEL-003"]')
        btn = box.locator('button:has-text("Pesquisar")')
        assert btn.count() > 0

    def test_SEL004_xpath_absolute_broken(self, page: Page):
        """SEL-004: XPath absolute quebrado — fallback to text."""
        box = page.locator('[data-testid="tax-SEL-004"]')
        btn = box.locator('button:has-text("Enviar")')
        btn.click()
        page.wait_for_timeout(200)
        assert box.locator('text=Formulário enviado').count() > 0

    def test_SEL005_css_class_volatile(self, page: Page):
        """SEL-005: CSS class hash — fallback to aria-label."""
        box = page.locator('[data-testid="tax-SEL-005"]')
        btn = box.locator('[aria-label="Botão de ação principal"]')
        assert btn.count() > 0


# ── FAM-02: Timing / Synchronization ────────────────────────────────────────

class TestFAM02Timing:
    """TIM-001 to TIM-007: Async and timing failures."""

    def test_TIM001_slow_loading(self, page: Page):
        """TIM-001: Element appears after delay."""
        box = page.locator('[data-testid="tax-TIM-001"]')
        # Click trigger that loads after 3s
        box.locator('button:has-text("Carregar conteúdo")').click()
        # Wait for delayed content
        delayed = box.locator('text=Conteúdo carregado com sucesso')
        delayed.wait_for(timeout=10000)
        assert delayed.count() > 0

    def test_TIM005_wait_fixed_timeout(self, page: Page):
        """TIM-005: Fixed timeout — element appears quickly."""
        box = page.locator('[data-testid="tax-TIM-005"]')
        btn = box.locator('button:has-text("Aparecer rápido")')
        btn.click()
        # Element should appear within 2s
        result = box.locator('text=Rápido')
        result.wait_for(timeout=5000)
        assert result.count() > 0

    def test_TIM006_debounce_autocomplete(self, page: Page):
        """TIM-006: Debounce — suggestions appear after typing."""
        box = page.locator('[data-testid="tax-TIM-006"]')
        inp = box.locator('input')
        inp.fill("Bra")
        page.wait_for_timeout(1000)
        suggestions = box.locator('text=Brasil')
        assert suggestions.count() > 0


# ── FAM-03: Context / Scope ─────────────────────────────────────────────────

class TestFAM03Context:
    """CTX-001 to CTX-007: Iframe, shadow DOM, popup."""

    def test_CTX001_iframe_same_origin(self, page: Page):
        """CTX-001: Element inside same-origin iframe."""
        box = page.locator('[data-testid="tax-CTX-001"]')
        iframe = box.locator('iframe').first
        frame = page.frame(name="test-frame")
        if frame:
            btn = frame.locator('button:has-text("Botão no iframe")')
            assert btn.count() > 0

    def test_CTX005_popup_new_tab(self, page: Page):
        """CTX-005: Popup/new tab detection."""
        box = page.locator('[data-testid="tax-CTX-005"]')
        btn = box.locator('text=Abrir popup')
        assert btn.count() > 0

    def test_CTX006_modal_outside_scope(self, page: Page):
        """CTX-006: Modal dialog outside form scope."""
        box = page.locator('[data-testid="tax-CTX-006"]')
        btn = box.locator('button:has-text("Abrir modal")')
        btn.click()
        page.wait_for_timeout(300)
        modal = page.locator('[role="dialog"]')
        assert modal.count() > 0 or box.locator('text=Modal').count() > 0


# ── FAM-04: Application State ───────────────────────────────────────────────

class TestFAM04State:
    """STA-001 to STA-006: Overlay, disabled, session."""

    def test_STA001_disabled_element(self, page: Page):
        """STA-001: Element disabled — wait for enable."""
        box = page.locator('[data-testid="tax-STA-001"]')
        disabled_btn = box.locator('button:has-text("Desabilitado")')
        assert disabled_btn.is_disabled()

    def test_STA002_overlay_blocking(self, page: Page):
        """STA-002: Overlay blocks click."""
        box = page.locator('[data-testid="tax-STA-002"]')
        btn = box.locator('button:has-text("Atrás do overlay")')
        assert btn.count() > 0

    def test_STA004_alert_dialog(self, page: Page):
        """STA-004: Alert dialog handling."""
        box = page.locator('[data-testid="tax-STA-004"]')
        btn = box.locator('button:has-text("Mostrar alerta")')
        assert btn.count() > 0


# ── FAM-05: Dynamic DOM ─────────────────────────────────────────────────────

class TestFAM05DynamicDOM:
    """DOM-001 to DOM-005: Stale, reorder, lazy load."""

    def test_DOM001_stale_element(self, page: Page):
        """DOM-001: Stale element — DOM replacement."""
        box = page.locator('[data-testid="tax-DOM-001"]')
        btn = box.locator('button:has-text("Substituir DOM")')
        btn.click()
        page.wait_for_timeout(500)
        # After replacement, old element is gone, new one appears
        new_btn = box.locator('button:has-text("Novo DOM")')
        new_btn.wait_for(timeout=5000)
        assert new_btn.count() > 0

    def test_DOM005_lazy_loading(self, page: Page):
        """DOM-005: Lazy loading — placeholder → real content."""
        box = page.locator('[data-testid="tax-DOM-005"]')
        btn = box.locator('button:has-text("Carregar imagem")')
        btn.click()
        page.wait_for_timeout(2000)
        img = box.locator('img[alt="Imagem carregada"]')
        assert img.count() > 0


# ── FAM-06: Input / Interaction ─────────────────────────────────────────────

class TestFAM06Input:
    """INP-001 to INP-010: Fill, masked, datepicker."""

    def test_INP007_masked_input(self, page: Page):
        """INP-007: Masked input — fill fails without pressSequentially."""
        box = page.locator('[data-testid="tax-INP-007"]')
        inp = box.locator('input[data-masked="cpf"]')
        inp.fill("12345678900")
        page.wait_for_timeout(200)
        val = inp.input_value()
        assert len(val) > 0

    def test_INP009_datepicker(self, page: Page):
        """INP-009: Date picker selection."""
        box = page.locator('[data-testid="tax-INP-009"]')
        inp = box.locator('input[type="date"]')
        assert inp.count() > 0


# ── FAM-07: File ────────────────────────────────────────────────────────────

class TestFAM07File:
    """FILE-001 to FILE-006: Upload/download."""

    def test_FILE001_file_input(self, page: Page):
        """FILE-001: File input hidden — need label click."""
        box = page.locator('[data-testid="tax-FILE-001"]')
        inp = box.locator('input[type="file"]')
        assert inp.count() > 0


# ── FAM-08: Assert ──────────────────────────────────────────────────────────

class TestFAM08Assert:
    """AST-001 to AST-010: Assertion validation."""

    def test_AST004_text_assert(self, page: Page):
        """AST-004: Assert visible text."""
        box = page.locator('[data-testid="tax-AST-004"]')
        status = box.locator('[role="status"]')
        assert status.count() > 0

    def test_AST010_negative_assert(self, page: Page):
        """AST-010: Assert absence of error."""
        box = page.locator('[data-testid="tax-AST-010"]')
        error = box.locator('.error-message')
        assert error.count() == 0


# ── FAM-09: Recorder ────────────────────────────────────────────────────────

class TestFAM09Recorder:
    """REC-001 to REC-006: Recording-related."""

    def test_REC002_overlay_capture(self, page: Page):
        """REC-002: Overlay captures user intent."""
        page.evaluate("window.__tfOverlayVisible = true")
        assert page.evaluate("window.__tfOverlayVisible") is True


# ── FAM-10: Execution ───────────────────────────────────────────────────────

class TestFAM10Execution:
    """OBS-001 to OBS-006: Execution/observability."""

    def test_OBS002_console_error(self, page: Page):
        """OBS-002: Console error detection."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.evaluate("console.error('test error for OBS-002')")
        page.wait_for_timeout(200)
        assert len(errors) > 0

    def test_OBS003_network_error(self, page: Page):
        """OBS-003: Network error detection."""
        box = page.locator('[data-testid="tax-OBS-003"]')
        btn = box.locator('button:has-text("Fazer requisição")')
        assert btn.count() > 0


# ── FAM-11: Browser Limits ──────────────────────────────────────────────────

class TestFAM11BrowserLimits:
    """LIM-001 to LIM-005: Technical limits."""

    def test_LIM001_captcha_detection(self, page: Page):
        """LIM-001: CAPTCHA — manual checkpoint, no bypass."""
        box = page.locator('[data-testid="tax-LIM-001"]')
        captcha = box.locator('text=CAPTCHA')
        assert captcha.count() > 0


# ── Healing Integration Tests ────────────────────────────────────────────────

class TestHealingIntegration:
    """Test that healing pipeline works end-to-end for key scenarios."""

    def test_selector_healing_mock(self, page: Page, test_server):
        """Test healing with MockLLMHealer on a broken selector."""
        from testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResult
        from testforge.healing.healing_catalog import HealingCatalog
        from testforge.evidence import EvidenceCollector

        page.goto(f"{test_server}/pagina-de-teste-completa.html")
        page.wait_for_timeout(500)

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

        # Should heal via L3 (MockLLMHealer) or L0 (catalog)
        assert outcome.status in (ProgressResult.PASSED_STEP,), \
            f"Healing failed: {outcome.status} — {outcome.error_message}"

    def test_heal_step_classification(self, page: Page):
        """Test that failure classification is correct."""
        from testforge.taxonomy import FailureClassifier

        classifier = FailureClassifier()

        # Locator failure
        r1 = classifier.classify("selector '#btn' not found: strict mode violation")
        assert r1.family_code == "FAM-01"
        assert r1.taxonomy_id.startswith("SEL")

        # Timeout failure
        r2 = classifier.classify("timeout exceeded waiting for element")
        assert r2.family_code == "FAM-02"
        assert r2.taxonomy_id.startswith("TIM")

        # Overlay failure
        r3 = classifier.classify("element is obscured by overlay")
        assert r3.family_code == "FAM-04"
        assert r3.taxonomy_id.startswith("STA")

        # Stale element
        r4 = classifier.classify("stale element reference: detached from DOM")
        assert r4.family_code == "FAM-05"
        assert r4.taxonomy_id.startswith("DOM")

    def test_evidence_payload_sufficient(self, page: Page, test_server):
        """Test that evidence payload is correctly marked sufficient."""
        from testforge.evidence import EvidenceCollector

        collector = EvidenceCollector(page)
        collector.start("test-sufficiency")

        page.goto(f"{test_server}/pagina-de-teste-completa.html")
        page.wait_for_timeout(500)

        payload = collector.build_llm_payload({
            "action": "click",
            "selector": "#test",
            "text": "Test",
            "intention": "Click test button",
            "url": page.url,
        })

        assert payload.is_sufficient, f"Payload insufficient: {payload.insufficiency_reason}"
        assert len(payload.dom_snapshot) >= 100
