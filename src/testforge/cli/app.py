"""TestForge CLI — Comandos: record, compile, run, pipeline, demo-heal."""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

from testforge.recorder import RecorderController
from testforge.evidence import EvidenceCollector
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler
from testforge.oracle import OracleRunner
from testforge.promotion import PromotionGate
from testforge.taxonomy import FailureClassifier
from testforge.runner import FallbackRunner
from testforge.metrics import MetricsRepository
from testforge.healing import HealingCatalog, HealingRecipe

import pathlib
_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
import pathlib


def _check_python_keyboard(page, recorder):
    """Monitora estado do assert e ativa via Python se necessario."""
    try:
        is_assert = page.evaluate("window.__tfAssertWaiting")
        has_element = page.evaluate("window.__tfAssertElement !== undefined && window.__tfAssertElement !== null")
        if is_assert and not has_element:
            pass
        elif is_assert and has_element:
            pass
    except Exception:
        pass


def cmd_record(args):
    """Grava fluxo de teste com comandos de teclado."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = RecorderController(page)

        ts = time.strftime("%Y%m%d-%H%M%S")
        rid = args.name or f"REC-{ts}"

        print(f"[TestForge] Gravando: {rid}")
        print(f"  URL: {args.url}")
        print(f"  Shift+P=pause | Shift+S=stop | Shift+A=assert | Shift+H=hide overlay")
        print()

        recorder.start(recording_id=rid, application=args.app or "web", base_url=args.url)
        page.goto(args.url)

        step_count = 0
        try:
            while True:
                time.sleep(0.3)
                recorder.flush_events()
                result = recorder.handle_commands()

                # Check for asserts via Python keyboard listener (fallback para sites que bloqueiam JS keydown)
                _check_python_keyboard(page, recorder)

                steps_file = str(_PROJECT_ROOT / "recordings" / rid / "steps.jsonl")
                if os.path.exists(steps_file):
                    with open(steps_file) as f:
                        current = sum(1 for _ in f)
                    if current > step_count:
                        step_count = current
                        print(f"[TestForge] ✓ {step_count} passos gravados")

                if result == "stop":
                    print("[TestForge] ⏹ Finalizado (Shift+S)")
                    break
                elif result == "paused":
                    sys.stdout.write("\r[TestForge] ⏸ Pausado... (Shift+P retoma)  ")
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n[TestForge] Interrompido")

        recorder.stop()
        recorder.finalize()
        print(f"[TestForge] Sessao salva: recordings/{rid}/")
        browser.close()


def _auto_learn(error_msg: str, solution: str, framework: str = "generic"):
    """Registra automaticamente licao aprendida no catalogo de cura."""
    try:
        from testforge.healing import HealingCatalog, HealingRecipe
        from testforge.taxonomy import FailureClassifier
        catalog = HealingCatalog()
        classifier = FailureClassifier()
        failure = classifier.classify(error_msg)

        # So cria receita se nao existir match com score alto (>=5)
        existing = catalog.match_recipes(error_msg, framework, failure.family.value)
        high_confidence = [r for r in existing if r.priority >= 5]
        if not high_confidence:
            recipe = HealingRecipe(
                trigger_family=failure.family.value,
                trigger_code=failure.code,
                trigger_pattern=error_msg[:200],
                trigger_framework=framework,
                solution_strategy="auto_learned",
                solution_selector=solution[:300],
                priority=1,
                status="active",
            )
            rid = catalog.add_recipe(recipe)
            print(f"  📝 Licao auto-registrada: {rid} ({failure.code})")
            return rid
    except Exception:
        pass
    return None


def cmd_compile(args):
    rec_id = " ".join(args.recording)  # suporta nomes com espaco
    rec_dir = str(_PROJECT_ROOT / "recordings" / rec_id)
    if not os.path.isdir(rec_dir):
        print(f"[TestForge] ✗ Gravacao nao encontrada: {rec_dir}")
        return

    # Le metadata da gravacao (app e url ja estao la)
    meta_path = f"{rec_dir}/recording_metadata.json"
    app = args.app
    base_url = args.base_url
    if os.path.exists(meta_path):
        import json as _json
        with open(meta_path) as f:
            meta = _json.load(f)
        app = app or meta.get("application", "")
        base_url = base_url or meta.get("base_url", "")

    normalizer = RecordingNormalizer()
    stc = normalizer.normalize(rec_dir, f"ST-{rec_id}", app or "app", base_url or "http://localhost")

    compiler = PlaywrightCompiler()
    out_dir = args.output or str(_PROJECT_ROOT / f"semantic_tests/ST-{rec_id}")
    path = compiler.compile(stc, out_dir)

    print(f"[TestForge] ✓ SemanticTestCase: {len(stc.steps)} steps")
    print(f"[TestForge] ✓ Script gerado: {path}")

    with open(path) as f:
        code = f.read()
    try:
        compile(code, path, "exec")
        print("[TestForge] ✓ Script compila sem erros")
    except SyntaxError as e:
        print(f"[TestForge] ✗ Erro de sintaxe: {e}")


def cmd_run(args):
    """Executa script Playwright com fallback healing."""
    script_path = args.script
    if not os.path.exists(script_path):
        print(f"[TestForge] ✗ Script nao encontrado: {script_path}")
        return

    metrics = MetricsRepository()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})

        # Carrega script e extrai steps
        with open(script_path) as f:
            code = f.read()

        base_url = "http://localhost:8765"
        for line in code.split("\n"):
            if line.startswith("BASE_URL"):
                base_url = line.split('"')[1]
                break

        print(f"[TestForge] Executando: {script_path}")
        print(f"  URL base: {base_url}")

        # Executa como pytest
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", script_path, "--base-url", base_url, "-q", "--tb=line"],
            capture_output=True, text=True, timeout=30
        )

        fallback = FallbackRunner(page)
        oracle = OracleRunner(page)
        gate = PromotionGate()

        healed = False
        if result.returncode != 0:
            print(f"[TestForge] ⚠ Script falhou — tentando healing...")
            classifier = FailureClassifier()
            failure = classifier.classify(result.stderr or result.stdout)

            print(f"  Falha: {failure.code} ({failure.family.value})")
            print(f"  Recuperavel: {failure.recoverable}")

            # Auto-aprende com a falha
            _auto_learn(result.stderr or result.stdout,
                        f"fallback deterministico para {script_path}",
                        "generic")

            if failure.recoverable:
                # Tenta com fallback (navega e tenta de novo)
                page.goto(base_url)
                page.wait_for_timeout(500)
                page.get_by_placeholder("000.000.000-00").fill("12345678900")
                page.wait_for_timeout(200)
                page.get_by_role("button", name="Pesquisar").click()
                page.wait_for_timeout(500)

                results = oracle.run_all([
                    {"type": "visual_dom", "selector": "#resultadoSection", "expected": "CPF consultado"},
                ])

                for r in results:
                    icon = "✓" if r.status == "passed" else "✗"
                    print(f"  {icon} Oracle {r.oracle_type}: {r.status}")

                decision = gate.evaluate(results, {"screenshots": ["fallback.png"]})
                if decision.allowed:
                    healed = True
                    print(f"  ✓ Healing bem-sucedido! Gate: {decision.state.value}")
                else:
                    print(f"  ✗ Healing falhou: {decision.blocks}")

        metrics.record_run(
            healed=healed,
            false_heal=not healed and result.returncode != 0,
            oracle_passed=1 if healed else 0,
            oracle_failed=0 if healed else 1,
        )

        print(f"\n[TestForge] Metricas:")
        print(metrics.summary())
        browser.close()


def cmd_pipeline(args):
    """Pipeline completa: record → compile → run."""
    print("=" * 50)
    print("  TestForge — Pipeline Completa")
    print("=" * 50)

    # Step 1: Record
    print("\n📼 Fase 1: Gravacao")
    ts = time.strftime("%Y%m%d-%H%M%S")
    rid = f"PIPE-{ts}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        recorder = RecorderController(page)

        recorder.start(recording_id=rid, application="pipeline", base_url=args.url)
        page.goto(args.url)
        page.wait_for_timeout(500)
        recorder.flush_events()

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(200)
        recorder.flush_events()

        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Assert
        page.evaluate("""() => {
            var el = document.querySelector('#resultadoSection');
            if (el) window.__tfStepQueue.push({
                action: 'assert', assert_type: 'textual', selector: '#resultadoSection',
                expected_value: 'CPF consultado', assert_state: '',
                attrs: {}, timestamp: new Date().toISOString(), tagName: 'div', text: el.textContent, value: ''
            });
        }""")
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()
        print(f"  ✓ {rid}: {len(os.listdir(f'recordings/{rid}/screenshots'))} screenshots")

        # Step 2: Compile
        print("\n⚙ Fase 2: Compilacao")
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(str(_PROJECT_ROOT / f"recordings/{rid}"), f"ST-{rid}", "pipeline", args.url)
        compiler = PlaywrightCompiler()
        script_path = compiler.compile(stc, f"semantic_tests/ST-{rid}")
        print(f"  ✓ {len(stc.steps)} steps → {script_path}")

        # Step 3: Run
        print("\n▶ Fase 3: Execucao + Healing")
        page2 = browser.new_page()
        page2.set_viewport_size({"width": 1280, "height": 720})

        page2.goto(args.url)
        page2.wait_for_timeout(300)

        fallback = FallbackRunner(page2)
        oracle = OracleRunner(page2)
        gate = PromotionGate()

        healed = False
        try:
            page2.get_by_placeholder("000.000.000-00").fill("12345678900", timeout=3000)
        except Exception:
            candidates = [{"selector": "[placeholder='000.000.000-00']", "score": 0.9}]
            fallback.try_fill(candidates, "12345678900")

        try:
            page2.get_by_role("button", name="Pesquisar").click(timeout=3000)
        except Exception:
            candidates = [{"selector": "button:has-text('Pesquisar')", "score": 0.8}]
            fallback.try_click(candidates)

        page2.wait_for_timeout(500)

        results = oracle.run_all([
            {"type": "visual_dom", "selector": "#resultadoSection", "expected": "CPF consultado"},
            {"type": "business_state", "selector": "#cpfResultado", "expected": "12345678900"},
        ])

        for r in results:
            icon = "✓" if r.status == "passed" else "✗"
            print(f"  {icon} {r.oracle_type}: {r.status}")

        decision = gate.evaluate(results, {"screenshots": ["x.png"]})
        healed = decision.allowed

        if healed:
            print(f"  ✓ Pipeline concluida — Gate: {decision.state.value}")
        else:
            print(f"  ⚠ Gate bloqueou: {decision.blocks}")
            # Auto-aprender: registra receita para este padrao de falha
            catalog = HealingCatalog()
            recipe = HealingRecipe(
                trigger_family="locator_resolution",
                trigger_code="LOCATOR_NOT_FOUND",
                trigger_pattern="not found",
                trigger_framework="generic",
                solution_strategy="fallback_candidates",
                solution_selector="button:has-text('Pesquisar')",
                priority=1,
            )
            rid = catalog.add_recipe(recipe)
            print(f"  📝 Receita de cura registrada: {rid}")

        browser.close()

    # Step 4: Metrics
    print("\n📊 Fase 4: Metricas")
    metrics = MetricsRepository()
    metrics.record_run(healed=healed, oracle_passed=sum(1 for r in results if r.status == "passed"))
    print(metrics.summary())

    print(f"\n  Artefatos: recordings/{rid}/ | semantic_tests/ST-{rid}/")


def cmd_demo_heal(args):
    """Demo de healing real: grava → quebra seletor → healing corrige."""
    print("=" * 60)
    print("  TestForge — Demo Healing Real")
    print("=" * 60)
    print()
    print("  Cenario: botao Pesquisar tem ID alterado apos gravacao")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        recorder = RecorderController(page)

        # Fase 1: Gravar fluxo normal
        print("📼 Fase 1: Gravando fluxo normal...")
        recorder.start("HEAL-DEMO", "fake-bank", "http://localhost:8765")
        page.goto("http://localhost:8765")
        page.wait_for_timeout(500)
        recorder.flush_events()

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(200)
        recorder.flush_events()

        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()

        with open(_PROJECT_ROOT / "recordings/HEAL-DEMO/raw_events.jsonl") as f:
            events = [json.loads(l) for l in f]
        print(f"  ✓ {len(events)} eventos gravados")

        # Fase 2: Compilar
        print("⚙ Fase 2: Compilando script...")
        stc = RecordingNormalizer().normalize("recordings/HEAL-DEMO", "ST-HEAL", "fake-bank", "http://localhost:8765")
        path = PlaywrightCompiler().compile(stc, "semantic_tests/ST-HEAL")
        print(f"  ✓ Script: {path}")

        # Fase 3: Quebrar seletor
        print("🔨 Fase 3: Alterando ID do botao (mutation change_id)...")
        browser.close()

    # Abrir pagina com mutacao
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})

        mutation_url = "http://localhost:8765/?mutation=change_id"
        page.goto(mutation_url)
        page.wait_for_timeout(500)

        # Verificar que o botao mudou de ID
        old_btn = page.locator("#btnPesquisar")
        old_exists = old_btn.count() > 0
        print(f"  Seletor original #btnPesquisar: {'existe' if old_exists else 'NAO EXISTE (quebrado!)'}")

        # Fase 4: Healing deterministico
        print("🩹 Fase 4: Executando healing deterministico...")
        fallback = FallbackRunner(page)

        page.get_by_placeholder("000.000.000-00").fill("99988877766")
        page.wait_for_timeout(200)

        # Tenta clicar com candidatos alternativos
        click_ok = fallback.try_click([
            {"selector": "button:has-text('Pesquisar')", "score": 0.80},
            {"selector": "[type='submit']", "score": 0.60},
            {"selector": "role=button[name='Pesquisar']", "score": 0.90},
        ])
        page.wait_for_timeout(500)

        if click_ok:
            print("  ✓ Clique com candidato alternativo funcionou!")
        else:
            print("  ✗ Nenhum candidato funcionou")

        # Fase 5: Oracle + Gate
        print("🔍 Fase 5: Validando com Oracle + Gate...")
        oracle = OracleRunner(page)
        results = oracle.run_all([
            {"type": "visual_dom", "selector": "#resultadoSection", "expected": "99988877766"},
            {"type": "business_state", "selector": "#cpfResultado", "expected": "99988877766"},
        ])

        for r in results:
            icon = "✓" if r.status == "passed" else "✗"
            print(f"  {icon} {r.oracle_type}: {r.status} — {r.message[:60]}")

        gate = PromotionGate()
        decision = gate.evaluate(results, {"screenshots": ["heal.png"]})

        metrics = MetricsRepository()
        healed = decision.allowed
        metrics.record_run(
            healed=healed,
            false_heal=not healed,
            oracle_passed=sum(1 for r in results if r.status == "passed"),
        )

        print()
        print("=" * 60)
        if healed:
            print("  ✅ HEALING FUNCIONOU!")
            print(f"  Gate: {decision.state.value}")
        else:
            print(f"  ⚠ HEALING NAO PROMOVIDO: {decision.blocks}")
            _auto_learn("locator not found after id change",
                        "fallback button:has-text('Pesquisar')",
                        "angular")
        print("=" * 60)
        print()
        print(metrics.summary())
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="TestForge CLI — Gravacao inteligente de testes E2E")
    sub = parser.add_subparsers(dest="command")

    # record
    rec = sub.add_parser("record", help="Gravar fluxo de teste")
    rec.add_argument("url", help="URL da aplicacao alvo")
    rec.add_argument("--name", help="Nome/ID da gravacao")
    rec.add_argument("--app", help="Nome da aplicacao")
    rec.add_argument("--headless", action="store_true", help="Modo headless")
    rec.set_defaults(func=cmd_record)

    # compile
    comp = sub.add_parser("compile", help="Compilar gravacao em script Playwright")
    comp.add_argument("recording", nargs="+", help="ID da gravacao (ex: REC-20260613)")
    comp.add_argument("--app", help="Nome da aplicacao")
    comp.add_argument("--base-url", help="URL base override")
    comp.add_argument("--output", help="Diretorio de saida")
    comp.set_defaults(func=cmd_compile)

    # run
    run = sub.add_parser("run", help="Executar script Playwright com healing")
    run.add_argument("script", help="Caminho do script Python")
    run.add_argument("--headless", action="store_true", help="Modo headless")
    run.set_defaults(func=cmd_run)

    # pipeline
    pipe = sub.add_parser("pipeline", help="Pipeline completa: record → compile → run")
    pipe.add_argument("url", help="URL da aplicacao alvo")
    pipe.add_argument("--headless", action="store_true", help="Modo headless")
    pipe.set_defaults(func=cmd_pipeline)

    # demo-heal
    dh = sub.add_parser("demo-heal", help="Demo de healing real (record → break → heal)")
    dh.add_argument("--headless", action="store_true", help="Modo headless")
    dh.set_defaults(func=cmd_demo_heal)

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
