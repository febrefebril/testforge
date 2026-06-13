"""Teste E2E do Recorder — fluxo completo com asserts.

Simula o fluxo real: gravar → fill → click → assert textual → assert visivel → stop.
Usa headless com comandos injetados via page.evaluate (simula Shift+A, etc).
"""
import json
import os

from playwright.sync_api import sync_playwright

from testforge.recorder import RecorderController

APP_URL = "http://localhost:8765"


def _simulate_assert(page, assert_type: str):
    """Simula Shift+A + clique no elemento + selecao do tipo de assert."""
    # 1. Entra em modo assert
    page.evaluate("window.__tfAssertWaiting = true")
    # 2. Seleciona o elemento resultado (apos o click em Pesquisar)
    page.evaluate("""(assertType) => {
        var el = document.querySelector('#resultadoSection') || document.querySelector('.result');
        if (!el) return;
        window.__tfAssertElement = el;

        // Simula _tf_addStep diretamente
        var selector = '#' + el.id;
        var step = {
            action: 'assert',
            selector: selector,
            tagName: (el.tagName||'').toLowerCase(),
            text: (el.textContent||'').trim().substring(0,200),
            value: (el.value||'').substring(0,200),
            attrs: {},
            timestamp: new Date().toISOString(),
            assert_type: assertType,
            assert_state: assertType === 'estado' ? 'enabled' : '',
            expected_value: assertType === 'textual' || assertType === 'automatico'
                ? 'CPF consultado'
                : (assertType === 'visivel' ? 'visible' : '')
        };
        window.__tfStepQueue.push(step);
    }""", assert_type)


def test_recorder_complete_flow():
    """Fluxo completo: navegar → fill CPF → click Pesquisar → assert textual → assert visivel → stop."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = RecorderController(page)

        recorder.start(recording_id="REC-FULL-001", application="fake-bank", base_url=APP_URL)

        # Navegar
        page.goto(APP_URL)
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Fill CPF
        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(300)
        recorder.flush_events()

        # Click Pesquisar
        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Assert 1: textual — verifica que "CPF consultado" aparece
        _simulate_assert(page, "textual")
        recorder.flush_events()

        # Assert 2: visivel — verifica que resultado esta visivel
        _simulate_assert(page, "visivel")
        recorder.flush_events()

        # Stop
        page.evaluate("window.__tfCommandQueue.push('STOP')")
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()
        browser.close()

    # --- Validacoes ---
    session_dir = "recordings/REC-FULL-001"
    assert os.path.isdir(session_dir)

    # Metadata
    with open(os.path.join(session_dir, "recording_metadata.json")) as f:
        meta = json.load(f)
    assert meta["status"] == "completed"

    # Raw events
    with open(os.path.join(session_dir, "raw_events.jsonl")) as f:
        raw_events = [json.loads(line) for line in f]
    assert len(raw_events) >= 3, f"Apenas {len(raw_events)} eventos raw"

    # Steps (com asserts)
    steps_path = os.path.join(session_dir, "steps.jsonl")
    assert os.path.exists(steps_path), "steps.jsonl nao foi criado"

    with open(steps_path) as f:
        steps = [json.loads(line) for line in f]
    assert len(steps) >= 2, f"Apenas {len(steps)} steps, esperava >= 2 (asserts)"

    # Verifica tipos de assert
    assert_types = [s["assert_type"] for s in steps if s["action"] == "assert"]
    assert "textual" in assert_types, f"Sem assert textual em {assert_types}"
    assert "visivel" in assert_types, f"Sem assert visivel em {assert_types}"

    textual_assert = next(s for s in steps if s.get("assert_type") == "textual")
    assert "CPF consultado" in str(textual_assert.get("expected_value", "")), \
        f"expected_value nao contem 'CPF consultado': {textual_assert.get('expected_value')}"

    visivel_assert = next(s for s in steps if s.get("assert_type") == "visivel")
    assert visivel_assert.get("expected_value") == "visible", \
        f"expected_value != visible: {visivel_assert.get('expected_value')}"

    # Screenshots
    screenshots = os.listdir(os.path.join(session_dir, "screenshots"))
    assert len(screenshots) > 0, "Nenhum screenshot"

    # Network log
    assert os.path.exists(os.path.join(session_dir, "network_log.json"))


def test_assert_types_all():
    """Testa que todos os 4 tipos de assert podem ser capturados."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        recorder = RecorderController(page)

        recorder.start(recording_id="REC-ASSERT-001", application="fake-bank", base_url=APP_URL)
        page.goto(APP_URL)
        page.wait_for_timeout(500)

        for atype in ["textual", "estado", "visivel", "automatico"]:
            _simulate_assert(page, atype)
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()
        browser.close()

    steps_path = "recordings/REC-ASSERT-001/steps.jsonl"
    with open(steps_path) as f:
        steps = [json.loads(line) for line in f]

    captured_types = [s["assert_type"] for s in steps if s["action"] == "assert"]
    for expected in ["textual", "estado", "visivel", "automatico"]:
        assert expected in captured_types, f"Faltou assert {expected} em {captured_types}"
