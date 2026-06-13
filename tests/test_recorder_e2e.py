"""Teste E2E do Recorder — fluxo completo com asserts.

Usa pytest-playwright fixtures para evitar conflito de event loop.
"""
import json
import os
import pytest
from playwright.sync_api import Page

from testforge.recorder import RecorderController

APP_URL = "http://localhost:8765"


@pytest.fixture
def browser_context(page: Page):
    """Fornece pagina Playwright gerenciada pelo pytest-playwright."""
    page.set_viewport_size({"width": 1280, "height": 720})
    yield page


def _simulate_assert(page: Page, assert_type: str):
    page.evaluate("""(assertType) => {
        var el = document.querySelector('#resultadoSection') || document.querySelector('.result');
        if (!el) return;
        window.__tfAssertElement = el;
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


def test_recorder_complete_flow(browser_context):
    """Fluxo completo: navegar, fill, click, assert textual, assert visivel."""
    page = browser_context
    recorder = RecorderController(page)
    recorder.start(recording_id="REC-FULL-001", application="fake-bank", base_url=APP_URL)

    page.goto(APP_URL)
    page.wait_for_timeout(500)
    recorder.flush_events()

    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    page.wait_for_timeout(300)
    recorder.flush_events()

    page.get_by_role("button", name="Pesquisar").click()
    page.wait_for_timeout(500)
    recorder.flush_events()

    _simulate_assert(page, "textual")
    recorder.flush_events()

    _simulate_assert(page, "visivel")
    recorder.flush_events()

    page.evaluate("window.__tfCommandQueue.push('STOP')")
    recorder.flush_events()
    recorder.stop()
    recorder.finalize()

    # Validacoes
    session_dir = "recordings/REC-FULL-001"
    assert os.path.isdir(session_dir)

    with open(os.path.join(session_dir, "recording_metadata.json")) as f:
        meta = json.load(f)
    assert meta["status"] == "completed"

    with open(os.path.join(session_dir, "raw_events.jsonl")) as f:
        raw = [json.loads(l) for l in f]
    assert len(raw) >= 2, f"Apenas {len(raw)} eventos raw"

    steps_path = os.path.join(session_dir, "steps.jsonl")
    assert os.path.exists(steps_path)

    with open(steps_path) as f:
        steps = [json.loads(l) for l in f]
    types = [s["assert_type"] for s in steps if s["action"] == "assert"]
    assert "textual" in types
    assert "visivel" in types

    textual = next(s for s in steps if s.get("assert_type") == "textual")
    assert "CPF consultado" in str(textual.get("expected_value", ""))


def test_assert_types_all(browser_context):
    """Valida os 4 tipos de assert."""
    page = browser_context
    recorder = RecorderController(page)
    recorder.start(recording_id="REC-ASSERT-001", application="fake-bank", base_url=APP_URL)

    page.goto(APP_URL)
    page.wait_for_timeout(500)

    for atype in ["textual", "estado", "visivel", "automatico"]:
        page.evaluate("""(t) => {
            var el = document.querySelector('#btnPesquisar') || document.querySelector('button');
            if (!el) return;
            window.__tfStepQueue.push({
                action: 'assert', selector: 'button', tagName: 'button',
                text: 'Pesquisar', value: '', attrs: {},
                timestamp: new Date().toISOString(),
                assert_type: t,
                assert_state: t === 'estado' ? 'enabled' : '',
                expected_value: t === 'textual' || t === 'automatico' ? 'Pesquisar'
                    : (t === 'visivel' ? 'visible' : '')
            });
        }""", atype)
    recorder.flush_events()
    recorder.stop()
    recorder.finalize()

    with open("recordings/REC-ASSERT-001/steps.jsonl") as f:
        steps = [json.loads(l) for l in f]

    types = [s["assert_type"] for s in steps if s["action"] == "assert"]
    for expected in ["textual", "estado", "visivel", "automatico"]:
        assert expected in types, f"Faltou {expected} em {types}"
