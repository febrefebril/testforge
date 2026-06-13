"""
TestForge — JS Recorder
Records user interactions via injected JavaScript when Playwright codegen
is not viable (iframes, legacy stacks, shadow DOM, etc.).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page, Browser

from recorder.stack_detector import detect_stack, StackInfo

log = logging.getLogger("testforge.js_recorder")

INJECTION_JS_PATH = Path(__file__).parent / "injection.js"


def _load_injection_script() -> str:
    return INJECTION_JS_PATH.read_text(encoding="utf-8")


def _collect_events(page: Page) -> list[dict]:
    try:
        events = page.evaluate("window.__testforge_events__ || []")
        return events if isinstance(events, list) else []
    except Exception as e:
        log.warning(f"Could not collect events: {e}")
        return []


def record_with_injection(
    url: str,
    meta: dict[str, Any],
    headless: bool = False,
    browser_type: str = "chromium",
) -> dict[str, Any]:
    """
    Opens a browser, injects the recording script, and waits for the user
    to interact. Returns a structured recording dict.
    """
    script = _load_injection_script()

    from rich.console import Console
    console = Console()
    console.print(
        f"\n[bold cyan]🔴 TestForge JS Recorder[/bold cyan]\n"
        f"  URL: [yellow]{url}[/yellow]\n"
        f"  Test: [green]{meta.get('name', 'unnamed')}[/green]\n"
        f"  [dim]Interact with the page, then press ENTER here to stop recording.[/dim]\n"
    )

    recording: dict[str, Any] = {
        "meta": meta,
        "recorder": "js_injection",
        "events": [],
        "stack": {},
        "duration_ms": 0,
    }

    with sync_playwright() as pw:
        browser: Browser = getattr(pw, browser_type).launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # Inject recorder on every navigation
        page.add_init_script(script)
        page.goto(url, wait_until="domcontentloaded")

        # Detect stack after page loads
        stack: StackInfo = detect_stack(page)
        recording["stack"] = {
            "name": stack.name,
            "version": stack.version,
            "category": stack.category,
            "has_shadow_dom": stack.has_shadow_dom,
            "has_iframes": stack.has_iframes,
            "notes": stack.notes,
        }

        log.info(f"Stack detected: {stack.name}")

        # Handle iframes — inject into each
        def inject_into_frames():
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                try:
                    frame.evaluate(script)
                    log.debug(f"Injected into iframe: {frame.url}")
                except Exception:
                    pass

        page.on("framenavigated", lambda _: inject_into_frames())
        inject_into_frames()

        start_ts = time.time()

        console.print("[bold yellow]  ▶ Recording... Press ENTER when done.[/bold yellow]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass

        duration_ms = int((time.time() - start_ts) * 1000)

        # Collect from main frame and iframes
        all_events = _collect_events(page)
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                iframe_events = frame.evaluate("window.__testforge_events__ || []")
                if isinstance(iframe_events, list):
                    for ev in iframe_events:
                        ev["iframe"]["in_iframe"] = True
                    all_events.extend(iframe_events)
            except Exception:
                pass

        # Sort by timestamp
        all_events.sort(key=lambda e: e.get("timestamp_ms", 0))

        recording["events"] = all_events
        recording["duration_ms"] = duration_ms

        log.info(f"Recorded {len(all_events)} events in {duration_ms}ms")

        browser.close()

    return recording
