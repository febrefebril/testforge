"""TestForge — Sprint A: recorder fill capture for Material currencymask.

Bug: forms with Material currencymask + datepicker had raw_events.jsonl with
zero fill events. The native value setter on those inputs is overridden
per-instance, so addEventListener('input', ..., true) at window-capture
never fires. The setter hook captured to value_mutations.jsonl but did not
push a fill event to raw_events.

Sprint A fix in overlay_inject.js:
1. setter hook now schedules a debounced _pushEvent('fill', el)
2. periodic 500ms scan over visible inputs as defensive fallback
3. shared __tfLastFillValue cache prevents double-emit between paths

Tests cover:
- static presence of the three patch elements in overlay_inject.js
- end-to-end via Playwright + Material currencymask fixture: fill event
  reaches __tfEventQueue when value is written through a per-instance
  setter override (the SIOPI failure mode)
"""
from __future__ import annotations
from pathlib import Path

import pytest


OVERLAY_PATH = Path(__file__).parent.parent / "src" / "testforge" / "recorder" / "overlay_inject.js"


class TestOverlayInjectStatic:
    @pytest.fixture(scope="class")
    def src(self) -> str:
        return OVERLAY_PATH.read_text(encoding="utf-8")

    def test_setter_hook_calls_schedule_fill(self, src):
        assert "_scheduleFillFromMutation(this)" in src, (
            "setter hook must call _scheduleFillFromMutation so currencymask "
            "writes land in raw_events.jsonl, not just value_mutations.jsonl"
        )

    def test_schedule_fill_function_defined(self, src):
        assert "function _scheduleFillFromMutation(" in src

    def test_debounce_cache_initialized(self, src):
        assert "__tfFillDebounceTimers" in src
        assert "__tfFillDebounceMs" in src

    def test_periodic_scan_interval_armed(self, src):
        assert "function _periodicFillScan(" in src
        assert "setInterval(_periodicFillScan" in src

    def test_periodic_scan_skips_hidden_and_non_text_inputs(self, src):
        assert "el.type === 'checkbox'" in src or 'el.type === "checkbox"' in src
        assert "el.type === 'radio'" in src or 'el.type === "radio"' in src
        assert "el.type === 'hidden'" in src or 'el.type === "hidden"' in src
        assert "rect.width === 0" in src

    def test_dedup_against_last_fill_value(self, src):
        # Both paths (debounced setter + periodic scan) must consult the
        # same cache, otherwise mat-input writes will be emitted twice.
        scheduled_block = src.split("function _scheduleFillFromMutation(")[1].split("\n  }\n")[0]
        scan_block = src.split("function _periodicFillScan(")[1].split("\n  }\n")[0]
        assert "__tfLastFillValue[key]" in scheduled_block
        assert "__tfLastFillValue[key]" in scan_block


# ---------------------------------------------------------------------------
# Integration: real Material currencymask fixture + Playwright
# ---------------------------------------------------------------------------


PAGE_URI = (
    Path(__file__).parent / "intent_lab" / "pages" / "material-currencymask" / "index.html"
).absolute().as_uri()


@pytest.fixture
def page_with_overlay():
    """Loads the Material currencymask fixture with overlay_inject.js installed
    BEFORE the page's own setter override fires. This mirrors how
    RecorderController injects via add_init_script.
    """
    from playwright.sync_api import sync_playwright

    overlay_src = OVERLAY_PATH.read_text(encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_init_script(overlay_src)
        page = context.new_page()
        page.goto(PAGE_URI)
        yield page
        browser.close()


class TestSprintAFillCaptureE2E:
    def _drain_queue(self, page) -> list[dict]:
        return page.evaluate("() => (window.__tfEventQueue || []).slice()") or []

    def _fill_events(self, queue: list[dict]) -> list[dict]:
        return [e for e in queue if e.get("type") == "fill"]

    def test_setter_hook_emits_fill_for_currencymask(self, page_with_overlay):
        """Writing through the per-instance setter override (the SIOPI failure
        mode) must produce at least one fill event in __tfEventQueue.
        """
        page = page_with_overlay
        page.evaluate("""() => {
            const el = document.querySelector('#valor_imovel');
            el.value = ' 1.000.000,00 ';
        }""")
        page.wait_for_timeout(600)
        events = self._fill_events(self._drain_queue(page))
        assert len(events) >= 1, (
            f"setter hook fix should produce at least 1 fill event; "
            f"got queue={self._drain_queue(page)}"
        )

    def test_dedup_does_not_double_emit_same_value(self, page_with_overlay):
        page = page_with_overlay
        page.evaluate("""() => {
            const el = document.querySelector('#valor_imovel');
            el.value = ' 1.000.000,00 ';
            el.value = ' 1.000.000,00 ';
            el.value = ' 1.000.000,00 ';
        }""")
        page.wait_for_timeout(700)
        events = self._fill_events(self._drain_queue(page))
        same_value = [e for e in events if (e.get("value") or "").strip() == "1.000.000,00"]
        assert len(same_value) == 1, (
            f"identical writes must dedup to 1 fill event; got {len(same_value)}: {same_value}"
        )

    def test_distinct_values_each_emit(self, page_with_overlay):
        page = page_with_overlay
        page.evaluate("""() => {
            const el = document.querySelector('#valor_imovel');
            el.value = ' 100,00 ';
        }""")
        page.wait_for_timeout(400)
        page.evaluate("""() => {
            const el = document.querySelector('#valor_imovel');
            el.value = ' 100.000,00 ';
        }""")
        page.wait_for_timeout(600)
        events = self._fill_events(self._drain_queue(page))
        last_two_vals = [(e.get("value") or "").strip() for e in events[-2:]]
        assert "100.000,00" in last_two_vals, f"final value must be captured; events={events}"

    def test_periodic_scan_catches_silent_assignment(self, page_with_overlay):
        """If something bypasses both addEventListener('input') and the setter
        hook (e.g. a brand-new input added to the DOM after our prototype hook
        was already wrapped by a downstream framework), the 500ms scan still
        catches the value as long as the input is visible and non-empty.

        Uses a fresh, mask-free input so el.value reads cleanly without the
        fixture's per-instance display/raw split.
        """
        page = page_with_overlay
        page.evaluate("""() => {
            const el = document.createElement('input');
            el.id = 'sprint_a_silent_input';
            el.style.width = '200px';
            el.style.height = '24px';
            el.style.display = 'block';
            document.body.appendChild(el);
            // Bypass our prototype setter wrapper by attacking the textContent
            // path: defineProperty on this instance with a setter that updates
            // an internal store and exposes via getter, but never calls _push.
            let stored = '';
            Object.defineProperty(el, 'value', {
                configurable: true,
                get: function() { return stored; },
                set: function(v) { stored = String(v); },
            });
            el.value = '9.999,00';
        }""")
        page.wait_for_timeout(900)
        events = self._fill_events(self._drain_queue(page))
        captured_vals = [(e.get("value") or "").strip() for e in events]
        assert "9.999,00" in captured_vals, (
            f"periodic scan should capture silent value on input bypassing "
            f"both event listener and prototype setter; "
            f"captured_vals={captured_vals}"
        )
