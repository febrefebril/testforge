"""
TestForge — Runner (Phase 3)
Executes generated tests with pytest, detects selector failures,
triggers self-healing, and re-runs until passing or max attempts reached.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("testforge.runner")

REPORTS_DIR = Path("reports")
MAX_HEAL_CYCLES = 3


def _run_pytest(test_path: Path, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    """Run pytest on a file. Returns (returncode, stdout, stderr)."""
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_path),
        "-v", "--tb=short", "--no-header",
        *(extra_args or []),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode, result.stdout, result.stderr


def _extract_failure_info(stdout: str, stderr: str) -> list[dict]:
    """
    Parse pytest output to extract failing actions and selector info.
    Returns list of {selector, line, error} dicts.
    """
    failures = []
    combined = stdout + "\n" + stderr

    # Pattern: "TimeoutError" or "ElementNotFound" lines near selector strings
    timeout_pattern = re.compile(
        r'(TimeoutError|ElementNotFound|Error).*?"([^"]{5,})"', re.IGNORECASE
    )
    for m in timeout_pattern.finditer(combined):
        failures.append({
            "error_type": m.group(1),
            "selector": m.group(2),
            "line": m.group(0)[:200],
        })

    # Also capture FAILED test lines
    failed_lines = [l for l in combined.splitlines() if "FAILED" in l or "ERROR" in l]
    if failed_lines and not failures:
        failures.append({"error_type": "generic", "selector": "", "line": failed_lines[0]})

    return failures


def _load_recording_for_test(test_path: Path) -> dict:
    """
    Try to find the matching recording JSON for a test file.
    """
    name = test_path.stem.replace("test_", "")
    for rec_dir in [Path("recordings")]:
        candidates = list(rec_dir.glob(f"{name}.json")) + list(rec_dir.glob(f"*{name}*.json"))
        if candidates:
            return json.loads(candidates[0].read_text())
    return {}


def run_with_healing(
    test_path: Path,
    recording: dict | None = None,
    max_cycles: int = MAX_HEAL_CYCLES,
    llm_heal: bool = True,
) -> dict[str, Any]:
    """
    Execute the test, detect failures, run healing, re-execute.
    Returns a healing report dict.
    """
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()

    console.print(f"\n[bold magenta]🔧 Phase 3 — Self-Healing Run:[/bold magenta] [cyan]{test_path.name}[/cyan]")

    if recording is None:
        recording = _load_recording_for_test(test_path)

    events = recording.get("events", [])
    selector_map: dict[str, dict] = {}
    context_map: dict[str, dict] = {}
    for ev in events:
        for sel_type, sel_val in ev.get("selectors", {}).items():
            if sel_val:
                selector_map[sel_val] = ev.get("selectors", {})
                context_map[sel_val] = ev.get("context", {})

    report = {
        "test_name": test_path.stem,
        "test_path": str(test_path),
        "timestamp": datetime.now().isoformat(),
        "total_actions": len(events),
        "cycles": [],
        "healed_selectors": 0,
        "failed_heals": 0,
        "final_status": "UNKNOWN",
        "selector_effectiveness": {},
    }

    for cycle in range(1, max_cycles + 1):
        console.print(f"  [dim]Run cycle {cycle}/{max_cycles}...[/dim]")
        rc, stdout, stderr = _run_pytest(test_path)

        cycle_info: dict[str, Any] = {
            "cycle": cycle,
            "returncode": rc,
            "failures": [],
            "heals": [],
        }

        if rc == 0:
            console.print(f"  [green]✓ Tests PASSED on cycle {cycle}[/green]")
            report["final_status"] = "PASS"
            report["cycles"].append(cycle_info)
            break

        # Extract failures
        failures = _extract_failure_info(stdout, stderr)
        cycle_info["failures"] = failures
        console.print(f"  [yellow]  {len(failures)} failure(s) detected[/yellow]")

        if not failures:
            report["final_status"] = "FAIL"
            report["cycles"].append(cycle_info)
            break

        # Attempt self-healing for each failure
        healed_any = False
        for failure in failures:
            failing_sel = failure.get("selector", "")
            if not failing_sel:
                continue

            all_selectors = selector_map.get(failing_sel, {})
            context = context_map.get(failing_sel, {})

            if not all_selectors:
                log.warning(f"No selector map for: {failing_sel!r} — skipping heal")
                report["failed_heals"] += 1
                continue

            # Run healing inside a live browser session
            from playwright.sync_api import sync_playwright
            meta = recording.get("meta", {})
            url = meta.get("url", events[0].get("url", "") if events else "")

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                if url:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        pass

                from healer.self_healer import heal_selector
                heal_result = heal_selector(
                    page=page,
                    test_path=test_path,
                    failing_selector=failing_sel,
                    selectors=all_selectors,
                    context=context,
                    llm_enabled=llm_heal,
                )
                browser.close()

            heal_info = {
                "original": failing_sel,
                "healed": heal_result.healed,
                "new_selector": heal_result.new_selector,
                "method": heal_result.method,
                "attempts": heal_result.attempts,
            }
            cycle_info["heals"].append(heal_info)

            if heal_result.healed:
                report["healed_selectors"] += 1
                healed_any = True
                console.print(
                    f"  [green]  ✓ Healed via [{heal_result.method}]:[/green] "
                    f"[dim]{failing_sel[:40]} → {heal_result.new_selector[:40]}[/dim]"
                )
            else:
                report["failed_heals"] += 1
                console.print(f"  [red]  ✗ Could not heal:[/red] [dim]{failing_sel[:60]}[/dim]")

        report["cycles"].append(cycle_info)

        if not healed_any:
            report["final_status"] = "FAIL"
            break
    else:
        # Final run after all healing cycles
        rc, _, _ = _run_pytest(test_path)
        report["final_status"] = "PASS" if rc == 0 else "FAIL"

    # Save report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"healing_report_{test_path.stem}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print(f"  [dim]Report saved: {report_path}[/dim]")

    return report
