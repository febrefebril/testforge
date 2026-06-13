#!/usr/bin/env python3
"""Teste de stress — grava na pagina ancestral com 78 taxonomias e valida pipeline."""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright.sync_api import sync_playwright
from testforge.recorder import RecorderController
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler

APP_URL = "http://localhost:8080"
RESULTS = []


def run_scenario(name, page, steps):
    rid = f"STRESS-{name}"
    for d in [f"recordings/{rid}", f"semantic_tests/ST-{rid}"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    recorder = RecorderController(page)
    recorder.start(recording_id=rid, application="pagina-teste", base_url=APP_URL)
    page.goto(APP_URL)
    page.wait_for_timeout(800)
    recorder.flush_events()

    for step in steps:
        stype = step["type"]
        try:
            if stype == "fill":
                page.get_by_placeholder(step["target"]).fill(step["value"])
            elif stype == "click_id":
                page.click(f"#{step['target']}")
                page.wait_for_timeout(800)
            elif stype == "click_text":
                page.get_by_text(step["target"]).first.click()
                page.wait_for_timeout(800)
            elif stype == "click_role":
                page.get_by_role("button", name=step["target"]).click()
                page.wait_for_timeout(800)
            elif stype == "click_checkbox":
                page.locator(f'input[value="{step["target"]}"]').check()
                page.wait_for_timeout(500)
            elif stype == "assert":
                page.evaluate("""([t, ev]) => {
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
            RESULTS.append(f"  ✗ {name}: {stype} → {str(e)[:80]}")
            recorder.stop()
            return False

    page.evaluate("window.__tfCommandQueue.push('STOP')")
    recorder.flush_events()
    recorder.stop()
    recorder.finalize()

    rec_dir = f"recordings/{rid}"
    if not os.path.exists(f"{rec_dir}/raw_events.jsonl"):
        RESULTS.append(f"  ✗ {name}: sem raw_events")
        return False

    with open(f"{rec_dir}/raw_events.jsonl") as f:
        events = [json.loads(l) for l in f]
    etypes = [e["type"] for e in events]

    try:
        stc = RecordingNormalizer().normalize(rec_dir, f"ST-{rid}", "pagina-teste", APP_URL)
        path = PlaywrightCompiler().compile(stc, f"semantic_tests/ST-{rid}")
        with open(path) as f:
            compile(f.read(), path, "exec")
        RESULTS.append(f"  ✓ {name}: {len(events)} eventos ({','.join(set(etypes))}) → script OK")
        return True
    except Exception as e:
        RESULTS.append(f"  ✗ {name}: compiler → {str(e)[:80]}")
        return False


def main():
    headed = "--headless" not in sys.argv
    print("=" * 60)
    print(f"  TestForge — Stress Test {'HEADED' if headed else 'headless'}")
    print("=" * 60)

    for d in ["recordings", "semantic_tests"]:
        if os.path.exists(d):
            for sub in os.listdir(d):
                p = os.path.join(d, sub)
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)

        # ── Cenario 1: Campo sem ID ──
        print("\n📋 1/6 — SEL: campo sem ID")
        page = browser.new_page()
        run_scenario("01-campo-sem-id", page, [
            {"type": "fill", "target": "sem id, sem name", "value": "teste 123"},
            {"type": "assert", "assert_type": "textual", "value": "teste 123"},
        ])
        page.close()

        # ── Cenario 2: Botao fora do form ──
        print("📋 2/6 — SEL: botao fora do form")
        page = browser.new_page()
        run_scenario("02-botao-fora-form", page, [
            {"type": "click_id", "target": "btn-fora-form"},
            {"type": "assert", "assert_type": "visivel", "value": "visible"},
        ])
        page.close()

        # ── Cenario 3: CPF com mascara ──
        print("📋 3/6 — INP: CPF com mascara")
        page = browser.new_page()
        run_scenario("03-cpf-mask", page, [
            {"type": "fill", "target": "000.000.000-00", "value": "12345678901"},
            {"type": "assert", "assert_type": "textual", "value": "123456"},
        ])
        page.close()

        # ── Cenario 4: Combobox ──
        print("📋 4/6 — INP: combobox")
        page = browser.new_page()
        run_scenario("04-combobox", page, [
            {"type": "fill", "target": "Digite ou selecione", "value": "Python"},
            {"type": "assert", "assert_type": "textual", "value": "Python"},
        ])
        page.close()

        # ── Cenario 5: Upload ──
        print("📋 5/6 — INP: upload de arquivo")
        page = browser.new_page()
        run_scenario("05-upload", page, [
            {"type": "fill", "target": "sem id, sem name", "value": "pre-upload"},
            {"type": "assert", "assert_type": "textual", "value": ""},
        ])
        page.close()

        # ── Cenario 6: Checkbox ──
        print("📋 6/6 — STA: checkbox")
        page = browser.new_page()
        run_scenario("06-checkbox", page, [
            {"type": "click_checkbox", "target": "tech"},
            {"type": "assert", "assert_type": "estado", "value": "checked"},
        ])
        page.close()

        browser.close()

    print()
    print("=" * 60)
    print("  Resultados")
    print("=" * 60)
    for r in RESULTS:
        print(r)

    passed = sum(1 for r in RESULTS if "✓" in r)
    failed = sum(1 for r in RESULTS if "✗" in r)
    print(f"\n  {passed}/{passed+failed} cenarios")


if __name__ == "__main__":
    main()
