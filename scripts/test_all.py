#!/usr/bin/env python3
"""TestForge — Teste completo da aplicacao.
Executa todos os testes e valida a pipeline end-to-end.
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, "src")

from playwright.sync_api import sync_playwright
from testforge.recorder import RecorderController
from testforge.evidence import EvidenceCollector, EvidenceStore
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler
from testforge.oracle import OracleRunner
from testforge.promotion import PromotionGate
from testforge.taxonomy import FailureClassifier
from testforge.runner import FallbackRunner, ShadowValidator
from testforge.metrics import MetricsRepository

APP_URL = "http://localhost:8765"

PASS, FAIL, SKIP = 0, 0, 0
RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        RESULTS.append(f"  [OK] {name}")
        PASS += 1
    else:
        RESULTS.append(f"  [X] {name}: {detail}")
        FAIL += 1


def cleanup():
    for d in ["recordings", "evidence", "semantic_tests", "generated_tests"]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def run_pytest() -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
        capture_output=True, text=True, timeout=120
    )
    return r.returncode == 0


def main():
    global PASS, FAIL
    print("=" * 60)
    print("  TestForge v1 — Teste Completo da Aplicacao")
    print("=" * 60)

    # ── Setup ──
    print("\n[TESTE] Fase 1: Setup")
    cleanup()

    check("Servidor fake-bank acessivel",
          os.system("curl -s -o /dev/null -w '%{http_code}' http://localhost:8765 | grep -q 200") == 0,
          "Inicie: cd synthetic_lab/fake-react-bank-app && python3 -m http.server 8765")

    check("Playwright instalado",
          os.system(f"{sys.executable} -c 'from playwright.sync_api import sync_playwright'") == 0)

    # ── Testes Unitarios ──
    print("\n[TESTE] Fase 2: Testes Unitarios (pytest)")
    if run_pytest():
        check("pytest tests/ passou", True, "")
    else:
        check("pytest tests/", False, "Alguns testes falharam — rode manualmente")

    # ── Pipeline E2E ──
    print("\n[TESTE] Fase 3: Pipeline Completa E2E")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})

        # -- 3.1 Recorder --
        print("  3.1 Recorder + Asserts...")
        recorder = RecorderController(page)
        recorder.start("FULLTEST-001", "fake-bank", APP_URL)
        page.goto(APP_URL)
        page.wait_for_timeout(500)
        recorder.flush_events()

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(200)
        recorder.flush_events()

        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Assert textual
        page.evaluate("""() => {
            var el = document.querySelector('#resultadoSection');
            if (el) window.__tfStepQueue.push({
                action: 'assert', assert_type: 'textual', selector: '#resultadoSection',
                tagName: 'div', text: el.textContent.trim(),
                expected_value: 'CPF consultado', assert_state: '',
                attrs: {}, timestamp: new Date().toISOString()
            });
        }""")
        recorder.flush_events()
        recorder.stop()
        recorder.finalize()

        rec_dir = "recordings/FULLTEST-001"
        with open(f"{rec_dir}/raw_events.jsonl") as f:
            events = [json.loads(l) for l in f]
        check("  3.1 Recorder: eventos capturados", len(events) >= 2,
              f"Esperado >=2, obteve {len(events)}")
        check("  3.1 Recorder: evento fill", "fill" in [e["type"] for e in events])
        check("  3.1 Recorder: evento click", "click" in [e["type"] for e in events])

        steps = f"{rec_dir}/steps.jsonl"
        if os.path.exists(steps):
            with open(steps) as f:
                st = [json.loads(l) for l in f]
            check(f"  3.1 Recorder: assert textual", any(s.get("assert_type") == "textual" for s in st))

        # -- 3.2 Evidence --
        print("  3.2 Coletor de Evidencias...")
        evidence = EvidenceCollector(page)
        evidence.start("FULLTEST-001")
        evidence.capture_screenshot("final", "after")
        evidence.capture_dom("final", "after")
        evidence.add_step_evidence({"action": "fill", "value": "12345678900"})
        evidence.add_step_evidence({"action": "click", "target": "btnPesquisar"})
        evidence.add_step_evidence({"action": "assert", "type": "textual"})
        evidence.finalize()

        ev_dir = "evidence/FULLTEST-001"
        check("  3.2 Evidence: manifest", os.path.exists(f"{ev_dir}/manifest.json"))
        check("  3.2 Evidence: screenshots", len(os.listdir(f"{ev_dir}/screenshots")) > 0)
        check("  3.2 Evidence: steps.jsonl", os.path.exists(f"{ev_dir}/steps.jsonl"))

        # EvidenceStore
        store = EvidenceStore()
        runs = store.list_runs()
        check("  3.2 EvidenceStore: listar runs", "FULLTEST-001" in runs)

        # -- 3.3 MIS + Compiler --
        print("  3.3 MIS + Compilador...")
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(rec_dir, "ST-FULLTEST", "fake-bank", APP_URL)
        check("  3.3 MIS: caso de teste semantico", len(stc.steps) >= 2, f"Esperado >=2, obteve {len(stc.steps)}")

        compiler = PlaywrightCompiler()
        script_path = compiler.compile(stc, "semantic_tests/ST-FULLTEST")
        with open(script_path) as f:
            code = f.read()
        check("  3.3 Compiler: script gerado", os.path.exists(script_path))
        check("  3.3 Compiler: fallback loop", "for _sel in _sels" in code, "Script sem fallback loop")
        check("  3.3 Compiler: assert presente", "to_contain_text" in code or "to_be_visible" in code)
        try:
            compile(code, script_path, "exec")
            check("  3.3 Compiler: Python sintaxe valida", True)
        except SyntaxError as e:
            check("  3.3 Compiler: Python sintaxe valida", False, str(e))

        # -- 3.4 Oracle --
        print("  3.4 Oracle + Gate...")
        oracle = OracleRunner(page)
        results = oracle.run_all([
            {"type": "visual_dom", "selector": "#resultadoSection", "expected": "CPF consultado"},
            {"type": "business_state", "selector": "#cpfResultado", "expected": "12345678900"},
        ])
        check("  3.4 Oracle: visual_dom passou", any(r.status == "passed" and r.oracle_type == "visual_dom" for r in results))
        check("  3.4 Oracle: business_state passou", any(r.status == "passed" and r.oracle_type == "business_state" for r in results))

        gate = PromotionGate()
        decision = gate.evaluate(results, {"screenshots": ["x.png"]})
        check("  3.4 Gate: promovido", decision.allowed, f"Estado: {decision.state.value}")

        # -- 3.5 Taxonomy + Fallback --
        print("  3.5 Taxonomia + Fallback...")
        classifier = FailureClassifier()
        c1 = classifier.classify("element not found", {"count": 0})
        check("  3.5 Taxonomia: LOCATOR_NOT_FOUND", c1.code == "LOCATOR_NOT_FOUND")
        check("  3.5 Taxonomia: recuperavel", c1.recoverable)

        c2 = classifier.classify("element is obscured by overlay")
        check("  3.5 Taxonomia: ACTIONABILITY_OBSCURED", c2.code == "ACTIONABILITY_OBSCURED")

        fallback = FallbackRunner(page)
        ok = fallback.try_fill([
            {"selector": "#cpfField", "score": 0.95}
        ], "99988877766")
        check("  3.5 Fallback: fill funciona", ok)

        # ShadowValidator
        sv = ShadowValidator(page)
        sug = sv.evaluate_failure("step_1", "locator not found",
                                   original_selector="#old",
                                   candidates=[{"selector": "#new", "score": 0.9}])
        check("  3.5 Shadow: sugestao gerada", sug is not None and sug.mode == "shadow")

        # -- 3.6 Metrics --
        print("  3.6 Metrics...")
        metrics = MetricsRepository()
        metrics.record_run(healed=True, false_heal=False, oracle_passed=2)
        metrics.record_run(healed=True, false_heal=True, oracle_passed=1)
        check("  3.6 Metrics: precision calculada", metrics.snapshot.precision == 0.5)
        check("  3.6 Metrics: summary gerado", "Precision" in metrics.summary())

        browser.close()

    # ── Relatorio Final ──
    print()
    print("=" * 60)
    print("  Resultado Final")
    print("=" * 60)
    for r in RESULTS:
        print(r)
    print()
    print(f"  {PASS} passaram, {FAIL} falharam")
    print(f"  Pipeline: BMAD [SETA] GSD [SETA] GIT")
    if FAIL == 0:
        print("  [OK] TODOS OS TESTES PASSARAM!")
    else:
        print(f"  [AVISO] {FAIL} falhas encontradas")


if __name__ == "__main__":
    main()
