from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

from testforge.core.models.step import StepResult
from testforge.core.models.report import Report, ExecutionSummary
from testforge.core.browser_config import get_launch_args, get_context_options


class TestRunner:
    def __init__(
        self,
        script_path: str,
        headed: bool = False,
        timeout: int = 30000,
        slow_mo: int = 0,
        debug: bool = False,
    ):
        self.script_path = Path(script_path)
        self.data_path = self.script_path.with_suffix(".data.json")
        self.headed = headed
        self.global_timeout = timeout
        self.slow_mo = slow_mo
        self.debug = debug
        self.results: list[StepResult] = []
        self._screenshot_dir: Path | None = None

    def run(self) -> Report:
        start_time = time.time()

        if not self.script_path.exists():
            return self._error_report(f"Script não encontrado: {self.script_path}")

        if not self.data_path.exists():
            return self._error_report(f"Dados não encontrados: {self.data_path}")

        with open(self.data_path, encoding="utf-8") as f:
            data = json.load(f)

        steps = data.get("steps", [])
        if not steps:
            return self._error_report("Nenhum passo encontrado no arquivo de dados.")

        started_at = datetime.now(timezone.utc).isoformat()
        test_name = self.script_path.stem
        report_dir = self.script_path.parent / f"{test_name}_artifacts"
        self._screenshot_dir = report_dir / "screenshots"
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        trace_path = report_dir / "trace.zip"

        def _dialog_handler(dialog):
            try:
                dialog.accept()
            except Exception:
                pass

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not self.headed, **get_launch_args())
            context = browser.new_context(**get_context_options())
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on("dialog", _dialog_handler)

            for i, step_data in enumerate(steps):
                step_result = self._execute_step(page, i, step_data, steps)
                self.results.append(step_result)
                if self.slow_mo > 0:
                    time.sleep(self.slow_mo / 1000)

            context.tracing.stop(path=str(trace_path))
            browser.close()

        total_duration = int((time.time() - start_time) * 1000)
        report = self._build_report(test_name, started_at, total_duration)
        report.report_dir = str(report_dir)
        report.trace_path = str(trace_path)

        report_path = report_dir / f"{test_name}_report.json"
        report.save(str(report_path))

        return report

    def _execute_step(self, page, index: int, step_data: dict, all_steps: list[dict]) -> StepResult:
        action = step_data.get("action", "")
        selector = step_data.get("selector", "")
        value = step_data.get("value", "")
        url = step_data.get("url", "")
        name = f"passo_{index + 1}"

        print(f"  [{index + 1}/{len(all_steps)}] {action}", end="", flush=True)

        step_start = time.time()
        step_timeout = self._timeout_for_action(action)

        try:
            if action == "navigate" or (index == 0 and url):
                if index == 0 and not url:
                    pass
                else:
                    page.goto(url, wait_until="domcontentloaded", timeout=step_timeout)

            elif action == "click":
                if selector:
                    selector = self._try_with_fallbacks(page, step_data, lambda sel: page.click(sel, timeout=step_timeout))
                else:
                    raise ValueError("Seletor vazio para clique")

            elif action in ("fill", "input"):
                if selector:
                    selector = self._try_with_fallbacks(page, step_data, lambda sel: page.fill(sel, value, timeout=step_timeout))
                else:
                    raise ValueError("Seletor vazio para preenchimento")

            elif action == "select":
                if selector:
                    tag = (step_data.get("tag_name", "") or "").lower()
                    input_type = (step_data.get("attrs", {}) or {}).get("type", "")
                    if (tag == "input" and input_type in ("radio", "checkbox")) or tag == "label":
                        selector = self._try_with_fallbacks(page, step_data, lambda sel: page.click(sel, timeout=step_timeout))
                    else:
                        label = step_data.get("text", "")
                        if label:
                            selector = self._try_with_fallbacks(page, step_data, lambda sel: page.select_option(sel, label=label, timeout=step_timeout))
                        else:
                            selector = self._try_with_fallbacks(page, step_data, lambda sel: page.select_option(sel, value, timeout=step_timeout))
                else:
                    raise ValueError("Seletor vazio para seleção")

            elif action == "upload":
                if selector:
                    selector = self._try_with_fallbacks(page, step_data, lambda sel: page.set_input_files(sel, value, timeout=step_timeout))
                else:
                    raise ValueError("Seletor vazio para upload")

            elif action == "download":
                if selector:
                    with page.expect_download(timeout=step_timeout) as download_info:
                        selector = self._try_with_fallbacks(page, step_data, lambda sel: page.click(sel, timeout=step_timeout))
                    suggested = download_info.value.suggested_filename
                    expected = step_data.get("text", "")
                    if expected and suggested != expected:
                        print(f" 📛 nome diferente: esperado '{expected}', obtido '{suggested}'")
                else:
                    raise ValueError("Seletor vazio para download")

            elif action == "assert":
                assert_type = step_data.get("assert_type", "textual")
                expected = step_data.get("expected_value", "")
                state = step_data.get("assert_state", "")
                def run_assert(sel):
                    locator = page.locator(sel)
                    if assert_type == "textual" or assert_type == "automatico":
                        expect(locator).to_contain_text(expected, timeout=step_timeout)
                    elif assert_type == "estado":
                        if state == "checked":
                            expect(locator).to_be_checked(timeout=step_timeout)
                        elif state == "unchecked":
                            expect(locator).not_to_be_checked(timeout=step_timeout)
                        elif state == "disabled":
                            expect(locator).to_be_disabled(timeout=step_timeout)
                        else:
                            expect(locator).to_be_enabled(timeout=step_timeout)
                    elif assert_type == "visivel":
                        expect(locator).to_be_visible(timeout=step_timeout)
                    else:
                        expect(locator).to_contain_text(expected, timeout=step_timeout)
                selector = self._try_with_fallbacks(page, step_data, run_assert)
            else:
                print(f" — ⏭️ ignorado (ação desconhecida: {action})")
                return StepResult(
                    name=name,
                    status="skipped",
                    intention=step_data.get("intention", ""),
                )

            duration = int((time.time() - step_start) * 1000)
            sel_display = selector[:50] if selector else "(none)"
            print(f" ✅ ({duration}ms) [{sel_display}]")
            return StepResult(
                name=name,
                status="passed",
                duration_ms=duration,
                intention=step_data.get("intention", ""),
                selector_used=selector,
            )

        except Exception as e:
            duration = int((time.time() - step_start) * 1000)
            error_msg = str(e)
            is_timeout = "Timeout" in error_msg or "timeout" in error_msg

            if is_timeout:
                display_msg = f"Tempo limite excedido para {name}"
            else:
                display_msg = error_msg.split("\n")[0][:120]

            screenshot_path = ""
            if self._screenshot_dir:
                try:
                    ss_path = self._screenshot_dir / f"{name}_fail.png"
                    page.screenshot(path=str(ss_path))
                    screenshot_path = str(ss_path)
                except Exception:
                    pass

            print(f" ❌ {display_msg}")
            return StepResult(
                name=name,
                status="failed",
                duration_ms=duration,
                intention=step_data.get("intention", ""),
                error_message=display_msg,
                selector_used=selector,
                screenshot_path=screenshot_path,
                recoverable=True,
            )

    def _try_with_fallbacks(self, page, step_data: dict, action_fn) -> str:
        selector = step_data.get("selector", "")
        fallbacks = step_data.get("fallbacks", [])
        candidates = [selector] + [f for f in fallbacks if f and f != selector]
        first_error = None
        for sel in candidates:
            try:
                action_fn(sel)
                if sel != selector:
                    print(f" 🔄 fallback: {sel[:60]}")
                return sel
            except Exception as e:
                if first_error is None:
                    first_error = e
                continue
        raise first_error

    def _timeout_for_action(self, action: str) -> int:
        timeouts = {
            "navigate": 45000,
            "click": 15000,
            "fill": 15000,
            "input": 15000,
            "select": 15000,
            "upload": 60000,
            "download": 60000,
            "assert": 20000,
        }
        return timeouts.get(action, self.global_timeout)

    def _build_report(self, test_name: str, started_at: str, total_duration: int) -> Report:
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        if failed > 0 and passed > 0:
            status = "partial"
        elif failed > 0:
            status = "failed"
        else:
            status = "passed"

        return Report(
            test_name=test_name,
            test_path=str(self.script_path),
            started_at=started_at,
            duration_ms=total_duration,
            status=status,
            browser="chromium",
            mode="headless" if not self.headed else "headed",
            steps=self.results,
            summary=ExecutionSummary(
                total=len(self.results),
                passed=passed,
                failed=failed,
                warnings=skipped,
                executive=self._build_executive(passed, failed, len(self.results)),
            ),
        )

    def _build_executive(self, passed: int, failed: int, total: int) -> str:
        if failed == 0:
            return f"{total} de {total} passos passaram. Teste concluído com sucesso."
        elif failed == total:
            return f"{total} de {total} passos falharam. Teste falhou."
        else:
            return f"{passed} de {total} passos passaram. {failed} falha(s) detectada(s)."

    def _error_report(self, message: str) -> Report:
        print(f"  ❌ {message}")
        return Report(
            status="failed",
            summary=ExecutionSummary(
                executive=message,
            ),
        )
