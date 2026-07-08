#!/usr/bin/env python3
"""Gravação automatizada da Página de Teste com verificação de captura do overlay."""
import asyncio, json, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "core"))

from playwright.async_api import async_playwright
from testforge.core.browser_config import get_launch_args, get_context_options, ANTI_DETECTION_SCRIPT
from testforge.core.models.step import RecordedStep
from testforge.core.script.builder import ScriptBuilder

OVERLAY_JS = Path(__file__).resolve().parents[2] / "packages" / "core" / "testforge" / "core" / "recording" / "overlay.js"
TEST_PAGE = os.environ.get("TEST_PAGE_URL", "http://localhost:8000/index.html")
CI_MODE = os.environ.get("CI", "").lower() in ("true", "1", "yes")
HEADLESS = CI_MODE or os.environ.get("TF_HEADLESS", "").lower() in ("true", "1", "yes")
OUTPUT = Path(__file__).parent

FIXTURE_FILE = OUTPUT / "fixture_upload.txt"


def make_step(action, selector, **kw):
    return RecordedStep(
        step_id=f"step_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action, selector_used=selector, **kw,
    )


async def main():
    overlay_js = OVERLAY_JS.read_text()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIXTURE_FILE.write_text("Conteúdo do arquivo de teste para upload (INP-002).")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, **get_launch_args())
        ctx = await browser.new_context(**get_context_options())
        page = await ctx.new_page()

        await page.add_init_script(ANTI_DETECTION_SCRIPT)
        await page.add_init_script(f'window.__tfMode = "shortcuts";\n{overlay_js}')

        async def auto_dialog(dialog):
            await dialog.accept()
        page.on("dialog", auto_dialog)

        print(f"Navegando para {TEST_PAGE}...")
        await page.goto(TEST_PAGE, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        ready = await page.evaluate("window.__tfReady === true")
        assert ready, "Overlay não iniciou!"

        steps = []
        last_count = 0

        async def poll():
            nonlocal last_count
            while True:
                try:
                    n = await page.evaluate("window.__tfSteps ? window.__tfSteps.length : 0")
                    if n > last_count:
                        raw = await page.evaluate("window.__tfSteps")
                        for s in raw[last_count:]:
                            step = RecordedStep(
                                step_id=f"step_{uuid.uuid4().hex[:12]}",
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                action=s.get("action", "click"),
                                selector_used=s.get("selector", ""),
                                raw_selector=s.get("rawSelector", ""),
                                tag_name=s.get("tagName", ""),
                                text=s.get("text", ""),
                                value=s.get("value", ""),
                                url=s.get("url", page.url),
                                page_title=await page.title(),
                                assert_type=s.get("assert_type", ""),
                                assert_state=s.get("assert_state", ""),
                                expected_value=s.get("expected_value", ""),
                                attrs=s.get("attrs", {}),
                            )
                            steps.append(step)
                            print(f"  [{len(steps)}] {step.action}: {step.selector_used}")
                        last_count = n
                except Exception:
                    pass
                await asyncio.sleep(0.3)

        poll_task = asyncio.create_task(poll())

        coverage = []

        async def interact(name, coro):
            before = await page.evaluate("window.__tfSteps ? window.__tfSteps.length : 0")
            try:
                await asyncio.wait_for(coro, timeout=15)
                await asyncio.sleep(1.2)
            except Exception as e:
                coverage.append((name, "FAIL", str(e)))
                return
            after = await page.evaluate("window.__tfSteps ? window.__tfSteps.length : 0")
            captured = after - before
            if captured > 0:
                coverage.append((name, "OK", captured))
            else:
                coverage.append((name, "GAP", 0))

        async def click(sel, **kw):
            await interact(f"click {sel}", page.click(sel, **kw))

        async def fill(sel, val):
            await interact(f"fill {sel}={val}", page.fill(sel, val))

        async def select(sel, val):
            await interact(f"select {sel}={val}", page.select_option(sel, val))

        async def upload(sel):
            loc = page.locator(sel)
            await interact(f"upload {sel}", loc.set_input_files(str(FIXTURE_FILE)))

        async def js_click(js):
            await interact(f"js_click", page.evaluate(js))

        # ====== 1. SELEÇÃO (SEL) ======
        print("\n--- SELEÇÃO (SEL) ---")
        await click("input[placeholder='sem id, sem name']")
        await fill("input[placeholder='sem id, sem name']", "texto sem id")

        await click("#campo-label-for")
        await fill("#campo-label-for", "texto label for")

        await click("label:has-text('Opção A')")
        await click("button:has-text('Confirmar')")
        await js_click("document.querySelector('#secao-seletores .field-row:last-child span')?.click()")
        await click("#btn-fora-form")

        # ====== 2. INPUT (INP) ======
        print("\n--- INPUT (INP) ---")
        await click("#campo-cpf")
        await page.fill("#campo-cpf", "12345678901")
        await asyncio.sleep(2)

        await click("#campo-data")
        await asyncio.sleep(0.8)
        try:
            await page.click("a:has-text('15')", timeout=3000)
            coverage.append(("datepicker select 15", "OK", 1))
        except Exception:
            coverage.append(("datepicker select 15", "GAP", 0))
        await asyncio.sleep(0.5)

        await click("#campo-combobox")
        await asyncio.sleep(0.3)
        await click(".combobox-item:has-text('Python')")

        await upload("#campo-upload")

        await click("#campo-richedit")
        await page.fill("#campo-richedit", "Texto rich edit")
        await asyncio.sleep(1)

        # Drag-and-drop: overlay não captura, mas fazemos a interação
        await interact("drag item 1 to drop-zone",
            page.locator('ul.sortable-list li[data-id="1"]').drag_to(page.locator("#drop-zone")))

        await click("#campo-autocomplete")
        await page.type("#campo-autocomplete", "Bra", delay=50)
        await asyncio.sleep(1.5)
        try:
            await page.click("#ui-id-1", timeout=3000)
            coverage.append(("autocomplete select Brasília", "OK", 1))
        except Exception:
            coverage.append(("autocomplete select Brasília", "GAP", 0))
        await asyncio.sleep(0.8)

        # ====== 3. TIMING (TIM) ======
        print("\n--- TIMING (TIM) ---")
        await click("#campo-lazy")
        await fill("#campo-lazy", "campo tardio")

        await select("#select-assincrono", "opcao2")

        # ====== 4. CONTEXTO (CTX) ======
        print("\n--- CONTEXTO (CTX) ---")
        await interact("shadow btn click",
            page.locator("#shadow-host").locator("button").click())
        await interact("shadow fill",
            page.locator("#shadow-host").locator("input").fill("texto shadow"))

        await interact("iframe btn click",
            page.frame_locator("#iframe-teste").locator("button").click())

        await click("#btn-abrir-modal")
        await asyncio.sleep(0.5)
        await click("#campo-modal")
        await fill("#campo-modal", "texto no modal")
        await click("#btn-confirmar-modal")
        await asyncio.sleep(0.5)

        # ====== 5. ESTADO (STA) ======
        print("\n--- ESTADO (STA) ---")
        await click("#btn-mostrar-overlay")
        await asyncio.sleep(0.3)
        try:
            await page.click("#btn-atras-overlay", timeout=2000)
        except Exception:
            pass
        await click("#btn-fechar-overlay")

        await click("#btn-alert")
        await click("#btn-confirm")
        await click("#btn-prompt")

        # ====== 6. DOM DINÂMICO (DOM) ======
        print("\n--- DOM (DOM) ---")
        await click("button:has-text('Remover')")
        await click("#btn-reordenar")

        await click("#btn-carregar-conteudo")
        await asyncio.sleep(0.5)
        await click("#campo-dinamico")
        await fill("#campo-dinamico", "campo dinamico")

        # ====== 7. FORMULÁRIO ======
        print("\n--- FORMULÁRIO ---")
        await click("#nome-completo")
        await fill("#nome-completo", "João Silva")
        await page.fill("#email-contato", "joao@teste.com")
        await asyncio.sleep(0.5)
        await page.fill("#telefone", "11999999999")
        await asyncio.sleep(1)
        await select("#select-estado", "SP")
        await click("input[name='genero']")
        await click("input[name='interesse']")
        await click("#mensagem")
        await fill("#mensagem", "Mensagem de teste para validação completa do formulário integrado")
        await click("button:has-text('Enviar')")

        # ====== STOP ======
        await page.evaluate("window.__tfCommands.push('STOP')")
        await asyncio.sleep(1)
        poll_task.cancel()

        # ====== REPORT ======
        print(f"\n{'='*60}")
        print(f"  RELATÓRIO DE CAPTURA DO OVERLAY")
        print(f"{'='*60}")
        ok = sum(1 for _, s, _ in coverage if s == "OK")
        gap = sum(1 for _, s, _ in coverage if s == "GAP")
        fail = sum(1 for _, s, _ in coverage if s == "FAIL")
        print(f"  Total: {len(coverage)}  OK: {ok}  GAP: {gap}  FAIL: {fail}")

        if gap > 0:
            print(f"\n  GAPS (não capturados pelo overlay):")
            for name, status, _ in coverage:
                if status == "GAP":
                    print(f"    ⚠️  {name}")

        # ====== GERAR TESTE ======
        print(f"\n  Gerando script de teste com {len(steps)} passos...")
        for s in steps:
            print(f"    {s.action:10s} {s.selector_used}")

        builder = ScriptBuilder("test_gravacao_auto")
        for s in steps:
            builder.add_step(s)

        script = builder.serialize()
        data = builder.build_data_json()

        script_path = OUTPUT / "teste_gerado.py"
        data_path = OUTPUT / "teste_gerado.data.json"
        script_path.write_text(script)
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"\n  Script: {script_path}")
        print(f"  Dados:  {data_path}")

        await browser.close()

    # ====== EXECUTAR ======
    print(f"\n{'='*60}")
    print(f"  EXECUTANDO TESTE GERADO...")
    print(f"{'='*60}")
    import subprocess
    env = os.environ.copy()
    pytest_flags = ["-v", "-x", "--tb=long"]
    if not HEADLESS:
        pytest_flags.append("--headed")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(script_path), *pytest_flags],
        capture_output=True, text=True,
        cwd=Path(__file__).parent,
    )
    print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
    if result.stderr:
        print(result.stderr[-1000:])

    passed = "passed" in result.stdout and "failed" not in result.stdout.split("\n")[-3]
    print(f"\n{'='*60}")
    print(f"  TESTE: {'✅ PASSED' if passed else '❌ FAILED'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
