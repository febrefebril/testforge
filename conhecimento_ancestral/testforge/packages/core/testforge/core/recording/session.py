from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

from testforge.core.models.step import RecordedStep
from testforge.core.script.builder import ScriptBuilder
from testforge.core.browser_config import get_launch_args, get_context_options


class RecordingSession:
    def __init__(
        self,
        url: str,
        output_dir: str = "./testes",
        test_name: Optional[str] = None,
        max_duration_minutes: int = 30,
        headed: bool = True,
        debug: bool = False,
        mode: str = "full",
    ):
        self.url = url
        self.output_dir = Path(output_dir)
        self.test_name = test_name
        self.max_duration_seconds = max_duration_minutes * 60
        self.headed = headed
        self.debug = debug
        self.mode = mode if mode in ("full", "shortcuts") else "full"

        self.state = "idle"
        self.steps: list[RecordedStep] = []
        self._page: Page | None = None
        self._ctx: BrowserContext | None = None

    async def start(self) -> None:
        print(f"\n  TestForge — Gravando: {self.url}")
        if self.mode == "shortcuts":
            print(f"  Modo: atalhos apenas (sem interface visual)")
        print(f"  {'═' * 50}")
        print("  Shift+P pausar/retomar | Shift+S finalizar")
        print("  Shift+A assert | Shift+H ocultar/mostrar overlay")
        print(f"  {'═' * 50}\n")

        self.state = "connecting"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not self.headed, **get_launch_args())
            self._ctx = await browser.new_context(**get_context_options())
            page = await self._ctx.new_page()
            self._page = page

            overlay_js = self._load_overlay_js()
            init_script_ok = False
            if overlay_js:
                try:
                    await page.add_init_script(overlay_js)
                    print("  ✅ Overlay injetado via add_init_script")
                    init_script_ok = True
                except Exception as e:
                    print(f"  ⚠️  add_init_script falhou: {e}")
            else:
                print("  ⚠️  overlay.js não encontrado")

            page.on("dialog", self._on_dialog)
            page.on("popup", self._on_popup)
            page.on("close", self._on_close)
            page.on("download", self._on_download)

            self.state = "recording"
            print(f"  ✅ Gravando... (navegando para {self.url})")

            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"  ⚠️  Aviso: página demorou para carregar: {e}")

            await asyncio.sleep(1)

            if not init_script_ok and overlay_js:
                try:
                    await page.evaluate(overlay_js)
                    print("  ✅ Overlay injetado via evaluate após load")
                except Exception as e:
                    print(f"  ⚠️  Injeção pós-load falhou: {e}")

            overlay_active = False
            try:
                overlay_active = await page.evaluate("() => window.__tfReady === true")
            except Exception:
                pass
            if not overlay_active:
                print("  ⚠️  Overlay não está ativo — gravação pode não capturar passos. Clique com Shift+S para finalizar.")

            start_time = time.time()
            poll_task = asyncio.create_task(self._poll_steps(page))
            keyboard_task = asyncio.create_task(self._listen_keyboard())

            try:
                while self.state in ("recording", "paused"):
                    elapsed = time.time() - start_time
                    if elapsed > self.max_duration_seconds:
                        print(f"\n  ⏰ Tempo máximo de gravação atingido ({self.max_duration_seconds // 60} min).")
                        break

                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                pass
            finally:
                poll_task.cancel()
                keyboard_task.cancel()

            await self._finalize()
            await browser.close()

    def _load_overlay_js(self) -> str:
        js_path = Path(__file__).parent / "overlay.js"
        if js_path.exists():
            js_content = js_path.read_text()
            return f"window.__tfMode = '{self.mode}'; {js_content}"
        return ""

    async def _poll_steps(self, page: Page) -> None:
        last_count = 0
        while self.state in ("recording", "paused"):
            try:
                current = await page.evaluate("() => window.__tfSteps ? window.__tfSteps.length : 0")
                if current > last_count:
                    raw_steps = await page.evaluate("() => window.__tfSteps")
                    for s in raw_steps[last_count:]:
                        action = s.get("action", "unknown")
                        assert_type = s.get("assert_type", "")
                        if action == "assert":
                            status_label = f"assert_{assert_type}"
                            extra = s.get("expected_value", s.get("text", ""))
                        else:
                            status_label = action
                            extra = s.get("text", "") or s.get("value", "") or s.get("selector", "")

                        attrs = s.get("attrs", {})
                        step = RecordedStep(
                            step_id=f"step_{uuid.uuid4().hex[:12]}",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            action=action,
                            selector_used=s.get("selector", ""),
                            raw_selector=s.get("rawSelector", ""),
                            tag_name=s.get("tagName", ""),
                            text=s.get("text", ""),
                            value=s.get("value", ""),
                            url=s.get("url", page.url),
                            page_title=await page.title(),
                            page_technology="",
                            assert_type=assert_type,
                            assert_state=s.get("assert_state", ""),
                            expected_value=s.get("expected_value", ""),
                            attrs=attrs,
                        )
                        self.steps.append(step)
                        print(f"  📝 [{len(self.steps)}] {status_label}: {step.tag_name} — {extra}")
                    last_count = current
            except Exception as e:
                if self.debug:
                    print(f"  ⚠️  poll_steps: {e}")
            await asyncio.sleep(0.3)

    async def _listen_keyboard(self) -> None:
        if self._page is None:
            return
        page = self._page
        while self.state in ("recording", "paused"):
            try:
                cmd = await page.evaluate("""
                    () => {
                        const cmds = window.__tfCommands || [];
                        if (cmds.length === 0) return null;
                        return cmds.shift();
                    }
                """)
                if cmd == "TOGGLE_PAUSE":
                    if self.state == "recording":
                        self.state = "paused"
                        await page.evaluate("() => { const e = document.getElementById('tf-status'); if(e) e.textContent = 'Pausado'; }")
                        print("  ⏸️  Gravação pausada")
                    elif self.state == "paused":
                        self.state = "recording"
                        await page.evaluate("() => { const e = document.getElementById('tf-status'); if(e) e.textContent = 'Gravando...'; }")
                        print("  ▶️  Gravação retomada")
                elif cmd == "ASSERT":
                    print("  🔍 Modo assert ativado — clique em um elemento na página")
                elif cmd == "STOP":
                    print("\n  🛑 Finalizando gravação...")
                    self.state = "idle"
                    break
            except Exception as e:
                if self.debug:
                    print(f"  ⚠️  listen_keyboard: {e}")
            await asyncio.sleep(0.2)

    async def _on_dialog(self, dialog) -> None:
        print(f"  💬 Dialog detectado: {dialog.type} — \"{dialog.message[:100]}\"")
        try:
            await dialog.accept()
        except Exception:
            pass

    async def _on_download(self, download) -> None:
        filename = download.suggested_filename or f"download_{uuid.uuid4().hex[:8]}"
        print(f"  ⬇️  Download detectado: {filename}")
        step = RecordedStep(
            step_id=f"step_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="download",
            selector_used="",
            tag_name="",
            text=filename,
            value=filename,
            url=self._page.url if self._page else "",
            page_title="",
            page_technology="",
        )
        self.steps.append(step)

    async def _on_popup(self, popup: Page) -> None:
        print("  🪟 Nova janela/popup detectada")
        try:
            await popup.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            if self.debug:
                print(f"  ⚠️  popup load: {e}")

    async def _on_close(self) -> None:
        print("\n  🛑 Navegador fechado. Finalizando...")
        self.state = "idle"

    def _merge_download_steps(self) -> None:
        merged: list[RecordedStep] = []
        i = 0
        while i < len(self.steps):
            step = self.steps[i]
            if step.action == "click" and i + 1 < len(self.steps) and self.steps[i + 1].action == "download":
                download_step = self.steps[i + 1]
                download_step.selector_used = step.selector_used
                download_step.tag_name = step.tag_name
                print(f"  🔄 Mesclado: clique + download → {step.selector_used} ({download_step.text})")
                merged.append(download_step)
                i += 2
            else:
                merged.append(step)
                i += 1
        self.steps = merged

    async def _finalize(self) -> None:
        self.state = "finalizing"

        self._merge_download_steps()

        test_name = self.test_name or f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_path = self.output_dir / test_name
        output_path.mkdir(parents=True, exist_ok=True)

        builder = ScriptBuilder(test_name)
        for step in self.steps:
            builder.add_step(step)

        script_content = builder.serialize()
        data_content = builder.build_data_json()

        script_path = output_path / f"{test_name}.py"
        data_path = output_path / f"{test_name}.data.json"

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data_content, f, ensure_ascii=False, indent=2)

        self.state = "completed"
        print(f"\n  {'═' * 50}")
        print("  ✅ Gravação concluída!")
        print(f"  📄 Script: {script_path}")
        print(f"  📦 Dados:  {data_path}")
        print(f"  📊 Passos: {len(self.steps)}")
        print(f"  {'═' * 50}")

