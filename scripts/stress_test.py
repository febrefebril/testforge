#!/usr/bin/env python3
"""Teste de stress — grava na pagina ancestral com 78 taxonomias e valida pipeline."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright.sync_api import sync_playwright
from testforge.recorder import RecorderController
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler

APP_URL = "http://localhost:8080"
RESULTS = []


def test_scenario(name: str, page, recorder, steps: list):
    rid = f"STRESS-{name.replace(' ', '-')}"
    for d in [f"recordings/{rid}", f"semantic_tests/ST-{rid}"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    recorder.start(recording_id=rid, application="pagina-teste", base_url=APP_URL)
    page.goto(APP_URL)
    page.wait_for_timeout(500)
    recorder.flush_events()

    for step in steps:
        stype = step["type"]
        try:
            if stype == "fill":
                page.get_by_placeholder(step["target"]).fill(step["value"])
            elif stype == "click_id":
                page.click(f"#{step['target']}")
            elif stype == "click_role":
                page.get_by_role("button", name=step["target"]).click()
            elif stype == "click_text":
                page.get_by_text(step["target"]).first.click()
            elif stype == "click_selector":
                page.click(step["target"])
            elif stype == "assert":
                page.evaluate("""([t, ev]) => {
                    var el = document.activeElement || document.body;
                    window.__tfStepQueue.push({
                        action: 'assert', assert_type: t,
                        selector: 'body', tagName: 'div', text: ev,
                        expected_value: ev, assert_state: '',
                        attrs: {}, timestamp: new Date().toISOString()
                    });
                }""", [step["assert_type"], step["value"]])
            page.wait_for_timeout(300)
            recorder.flush_events()
        except Exception as e:
            RESULTS.append(f"  ✗ {name}: {stype} '{step.get('target','')}' → {str(e)[:80]}")
            recorder.stop()
            return

    page.evaluate("window.__tfCommandQueue.push('STOP')")
    recorder.flush_events()
    recorder.stop()
    recorder.finalize()

    rec_dir = f"recordings/{rid}"
    if not os.path.exists(f"{rec_dir}/raw_events.jsonl"):
        RESULTS.append(f"  ✗ {name}: sem raw_events")
        return

    with open(f"{rec_dir}/raw_events.jsonl") as f:
        events = [json.loads(l) for l in f]
    etypes = [e["type"] for e in events]

    try:
        stc = RecordingNormalizer().normalize(rec_dir, f"ST-{rid}", "pagina-teste", APP_URL)
        path = PlaywrightCompiler().compile(stc, f"semantic_tests/ST-{rid}")
        with open(path) as f:
            code = f.read()
        compile(code, path, "exec")
        RESULTS.append(f"  ✓ {name}: {len(events)} eventos ({','.join(etypes[:4])}) → script compila")
    except Exception as e:
        RESULTS.append(f"  ✗ {name}: MIS/Compiler → {str(e)[:80]}")


def main():
    print("=" * 60)
    print("  TestForge — Stress Test na Pagina Ancestral")
    print("=" * 60)

    for d in ["recordings", "semantic_tests"]:
        if os.path.exists(d):
            for sub in os.listdir(d):
                p = os.path.join(d, sub)
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = RecorderController(page)

        # ── Cenario 1: Campo sem ID ──
        print("\n📋 Testando...")
        test_scenario("SEL-campo-sem-id", page, recorder, [
            {"type": "fill", "target": "sem id, sem name", "value": "teste 123"},
            {"type": "assert", "assert_type": "textual", "value": "teste"},
        ])

        # ── Cenario 2: Botao fora do form ──
        test_scenario("SEL-botao-fora-form", page, recorder, [
            {"type": "click_id", "target": "btn-fora-form"},
            {"type": "assert", "assert_type": "visivel", "value": "visible"},
        ])

        # ── Cenario 3: CPF com mascara ──
        test_scenario("INP-cpf-mask", page, recorder, [
            {"type": "fill", "target": "000.000.000-00", "value": "12345678901"},
            {"type": "assert", "assert_type": "textual", "value": "123.456.789"},
        ])

        # ── Cenario 4: Data ──
        test_scenario("INP-date", page, recorder, [
            {"type": "fill", "target": "dd/mm/aaaa", "value": "13062026"},
            {"type": "assert", "assert_type": "textual", "value": ""},
        ])

        # ── Cenario 5: Combobox ──
        test_scenario("INP-combobox", page, recorder, [
            {"type": "fill", "target": "Digite ou selecione", "value": "Python"},
            {"type": "assert", "assert_type": "textual", "value": "Python"},
        ])

        # ── Cenario 6: Checkbox ──
        test_scenario("STA-checkbox", page, recorder, [
            {"type": "click_selector", "target": "#campo-check-1"},
            {"type": "assert", "assert_type": "estado", "value": "checked"},
        ])

        browser.close()

    print()
    print("=" * 60)
    print("  Resultados")
    print("=" * 60)
    for r in RESULTS:
        print(r)

    passed = sum(1 for r in RESULTS if "✓" in r)
    failed = sum(1 for r in RESULTS if "✗" in r)
    print(f"\n  {passed}/{passed+failed} cenários passaram")


if __name__ == "__main__":
    main()
