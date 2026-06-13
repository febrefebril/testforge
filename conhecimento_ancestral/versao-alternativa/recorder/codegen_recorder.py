"""
TestForge — Codegen Recorder
Launches `playwright codegen` as a subprocess and captures the generated code.
Falls back to js_recorder if codegen output is empty or unavailable.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("testforge.codegen_recorder")


def record_with_codegen(
    url: str,
    meta: dict[str, Any],
    browser: str = "chromium",
) -> dict[str, Any]:
    """
    Runs `playwright codegen <url>` and captures the generated Python script.
    Returns a recording dict compatible with the rest of the pipeline.
    """
    from rich.console import Console
    console = Console()

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        output_path = Path(f.name)

    console.print(
        f"\n[bold cyan]🎬 TestForge Codegen Recorder[/bold cyan]\n"
        f"  URL: [yellow]{url}[/yellow]\n"
        f"  Test: [green]{meta.get('name', 'unnamed')}[/green]\n"
        f"  [dim]A browser will open. Record your interactions, then close it.[/dim]\n"
    )

    cmd = [
        sys.executable, "-m", "playwright", "codegen",
        "--target", "python",
        "--output", str(output_path),
        "--browser", browser,
        url,
    ]

    start_ts = time.time()
    try:
        result = subprocess.run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        log.warning("Codegen timed out after 300s")
    except Exception as e:
        log.error(f"Codegen failed: {e}")
        return _empty_recording(meta)

    duration_ms = int((time.time() - start_ts) * 1000)

    raw_code = ""
    if output_path.exists():
        raw_code = output_path.read_text(encoding="utf-8").strip()
        output_path.unlink(missing_ok=True)

    if not raw_code:
        log.warning("Codegen produced no output — falling back to JS recorder")
        return _empty_recording(meta)

    log.info(f"Codegen captured {len(raw_code)} chars in {duration_ms}ms")

    # Parse codegen output into structured event list (best-effort)
    events = _parse_codegen_to_events(raw_code)

    return {
        "meta": meta,
        "recorder": "codegen",
        "raw_code": raw_code,
        "events": events,
        "stack": {"name": "unknown", "category": "unknown"},
        "duration_ms": duration_ms,
    }


def _empty_recording(meta: dict) -> dict:
    return {
        "meta": meta,
        "recorder": "codegen",
        "raw_code": "",
        "events": [],
        "stack": {},
        "duration_ms": 0,
    }


def _parse_codegen_to_events(code: str) -> list[dict]:
    """
    Best-effort parse of Playwright codegen Python output into
    a list of event dicts similar to the JS recorder format.
    """
    import re

    events = []
    lines = code.splitlines()
    ts = 0

    patterns = [
        # click
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.click\(\)', "click"),
        # fill / type
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.fill\("(.+?)"\)', "input"),
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.type\("(.+?)"\)', "input"),
        # press
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.press\("(.+?)"\)', "keydown"),
        # select_option
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.select_option\("(.+?)"\)', "change"),
        # check / uncheck
        (r'page\.(?:get_by_\w+|locator)\((.+?)\)\.check\(\)', "change"),
        # goto
        (r'page\.goto\("(.+?)"\)', "navigation"),
    ]

    for i, line in enumerate(lines):
        line = line.strip()
        for pattern, etype in patterns:
            m = re.search(pattern, line)
            if m:
                selector_raw = m.group(1).strip()
                value = m.group(2) if len(m.groups()) >= 2 else None

                # Derive selector dict from codegen selector string
                selectors = _codegen_selector_to_dict(selector_raw)

                event = {
                    "id": len(events),
                    "type": etype,
                    "timestamp_ms": ts,
                    "url": "",
                    "page_title": "",
                    "selectors": selectors,
                    "codegen_line": line,
                    "context": {"element_text": selector_raw},
                    "iframe": {"in_iframe": False},
                    "shadow": {"in_shadow": False},
                }
                if value:
                    event["value"] = value

                events.append(event)
                ts += 200
                break

    return events


def _codegen_selector_to_dict(raw: str) -> dict:
    """Convert a Playwright codegen selector string into our multi-selector dict."""
    import re

    sel = {}

    # get_by_role("button", name="Submit") → aria
    m = re.search(r'get_by_role\("(\w+)"(?:.*?name="(.+?)")?', raw)
    if m:
        role, name = m.group(1), m.group(2)
        sel["aria"] = f'[role="{role}"]' + (f'[name="{name}"]' if name else "")

    # get_by_text("Login") → text
    m = re.search(r'get_by_text\("(.+?)"', raw)
    if m:
        sel["text"] = f"text={m.group(1)}"

    # get_by_placeholder("Email") → text
    m = re.search(r'get_by_placeholder\("(.+?)"', raw)
    if m:
        sel["text"] = f'[placeholder="{m.group(1)}"]'

    # get_by_label("Password") → aria
    m = re.search(r'get_by_label\("(.+?)"', raw)
    if m:
        sel["aria"] = f'[aria-label="{m.group(1)}"]'

    # get_by_test_id("submit-btn") → data_testid
    m = re.search(r'get_by_test_id\("(.+?)"', raw)
    if m:
        sel["data_testid"] = f'[data-testid="{m.group(1)}"]'

    # locator("css=...") or locator("#id") or locator(".class")
    m = re.search(r'locator\("(.+?)"', raw)
    if m:
        raw_sel = m.group(1)
        if raw_sel.startswith("//") or raw_sel.startswith("xpath="):
            sel["xpath"] = raw_sel.replace("xpath=", "")
        else:
            sel["css"] = raw_sel.replace("css=", "")

    # Keep original as css fallback if nothing matched
    if not sel:
        sel["css"] = raw.strip('"\'')

    return sel
