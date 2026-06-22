#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  TestForge — AI-Powered Test Recorder & Generator            ║
║  Record → Generate → Self-Heal → Optimize                    ║
╚══════════════════════════════════════════════════════════════╝

Usage:
  python testforge.py record   --url URL --name NAME --assert HINT
  python testforge.py generate --recording FILE
  python testforge.py heal     --test FILE
  python testforge.py optimize --test FILE
  python testforge.py run-all  --url URL --name NAME --assert HINT
  python testforge.py list
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

load_dotenv()

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("testforge")
console = Console()


def _load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text())
    return {}


def _banner():
    console.print(
        Panel.fit(
            "[bold cyan]TestForge[/bold cyan] [dim]v1.0[/dim]\n"
            "[dim]Record → Generate → Self-Heal → Optimize[/dim]",
            border_style="cyan",
        )
    )


# ── CLI group ────────────────────────────────────────────────────────────────
@click.group()
def cli():
    """TestForge — AI-powered test recorder and generator."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: record
# ══════════════════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--url", required=True, help="URL to record interactions on")
@click.option("--name", required=True, help='Test name, e.g. "Login inválido"')
@click.option("--assert", "assert_hint", default="",
              help='Expected assertion, e.g. "Error message must appear"')
@click.option("--description", "-d", default="",
              help="Optional description of what this test covers")
@click.option("--tags", "-t", default="",
              help="Comma-separated tags, e.g. auth,negativo")
@click.option("--output", "-o", default=None,
              help="Output JSON path (default: recordings/<name>_<ts>.json)")
@click.option("--recorder", default="auto",
              type=click.Choice(["auto", "codegen", "js"]),
              help="Recorder strategy (auto tries codegen first)")
@click.option("--browser", default="chromium",
              type=click.Choice(["chromium", "firefox", "webkit"]))
@click.option("--headless", is_flag=True, default=False,
              help="Run browser in headless mode (JS recorder only)")
def record(url, name, assert_hint, description, tags, output, recorder, browser, headless):
    """Phase 1 — Record user interactions on a page."""
    _banner()

    meta = {
        "name": name,
        "description": description,
        "expected_assert": assert_hint,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "url": url,
    }

    output_path = Path(output) if output else None

    # ── Choose recorder ──────────────────────────────────────────────────────
    recording = None

    if recorder in ("auto", "codegen"):
        console.print("[dim]Attempting Playwright codegen recorder...[/dim]")
        try:
            from recorder.codegen_recorder import record_with_codegen
            recording = record_with_codegen(url=url, meta=meta, browser=browser)

            if not recording.get("events") and not recording.get("raw_code"):
                console.print("[yellow]Codegen produced no output — switching to JS recorder[/yellow]")
                recording = None
        except Exception as e:
            console.print(f"[yellow]Codegen failed ({e}) — switching to JS recorder[/yellow]")
            recording = None

    if recording is None:
        from recorder.js_recorder import record_with_injection
        recording = record_with_injection(
            url=url,
            meta=meta,
            headless=headless,
            browser_type=browser,
        )

    # ── Save recording ───────────────────────────────────────────────────────
    from recording_manager import save_recording
    saved_path = save_recording(recording, output_path)

    n_events = len(recording.get("events", []))
    stack = recording.get("stack", {}).get("name", "unknown")

    console.print(
        f"\n[bold green]✓ Recording saved:[/bold green] [cyan]{saved_path}[/cyan]\n"
        f"  Events: [yellow]{n_events}[/yellow] | Stack: [yellow]{stack}[/yellow]"
    )

    return saved_path


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: generate
# ══════════════════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--recording", "-r", required=True,
              help="Path to recording JSON file")
@click.option("--output-dir", default="tests/generated",
              help="Directory for generated test files")
def generate(recording, output_dir):
    """Phase 2 — Generate pytest test from a recording."""
    _banner()

    rec_path = Path(recording)
    if not rec_path.exists():
        console.print(f"[red]Recording not found: {rec_path}[/red]")
        sys.exit(1)

    from recording_manager import load_recording
    rec_data = load_recording(rec_path)

    from generator.test_generator import generate_test
    test_path = generate_test(rec_data, output_dir=Path(output_dir))

    console.print(f"\n[bold green]✓ Test generated:[/bold green] [cyan]{test_path}[/cyan]")
    return test_path


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: heal
# ══════════════════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--test", "-t", required=True, help="Path to the generated test .py file")
@click.option("--recording", "-r", default=None,
              help="Path to the original recording JSON (auto-detected if omitted)")
@click.option("--no-llm", is_flag=True, default=False,
              help="Disable LLM healing (local fallbacks only)")
@click.option("--max-cycles", default=3, type=int,
              help="Maximum heal-and-retry cycles")
def heal(test, recording, no_llm, max_cycles):
    """Phase 3 — Run test with self-healing selector repair."""
    _banner()

    test_path = Path(test)
    if not test_path.exists():
        console.print(f"[red]Test file not found: {test_path}[/red]")
        sys.exit(1)

    rec_data = None
    if recording:
        from recording_manager import load_recording
        rec_data = load_recording(Path(recording))

    from healer.runner import run_with_healing
    report = run_with_healing(
        test_path=test_path,
        recording=rec_data,
        max_cycles=max_cycles,
        llm_heal=not no_llm,
    )

    status_color = "green" if report["final_status"] == "PASS" else "red"
    console.print(
        f"\n[bold {status_color}]Final status: {report['final_status']}[/bold {status_color}]\n"
        f"  Healed selectors: [yellow]{report['healed_selectors']}[/yellow]\n"
        f"  Failed heals: [red]{report['failed_heals']}[/red]"
    )

    return report


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: optimize
# ══════════════════════════════════════════════════════════════════════════════
@cli.command()
@click.option("--test", "-t", required=True, help="Path to the (healed) test .py file")
def optimize(test):
    """Phase 4 — Profile and optimize test performance."""
    _banner()

    test_path = Path(test)
    if not test_path.exists():
        console.print(f"[red]Test file not found: {test_path}[/red]")
        sys.exit(1)

    from optimizer.tuner import optimize as run_optimize
    report = run_optimize(test_path)

    if report.get("status") == "success":
        console.print(
            f"\n[bold green]✓ Optimization complete[/bold green]\n"
            f"  Estimated saving: [yellow]~{report.get('estimated_saving_ms', 0)}ms[/yellow] "
            f"([cyan]{report.get('reduction_pct', 0)}%[/cyan])\n"
            f"  Optimized test: [cyan]{report.get('optimized_path', '')}[/cyan]"
        )
    elif report.get("status") == "skipped":
        console.print("[dim]Nothing to optimize — no wait calls found.[/dim]")
    else:
        console.print(f"[yellow]Optimization status: {report.get('status')}[/yellow]")

    return report


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: run-all (full pipeline)
# ══════════════════════════════════════════════════════════════════════════════
@cli.command("run-all")
@click.option("--url", required=True, help="URL to record interactions on")
@click.option("--name", required=True, help='Test name')
@click.option("--assert", "assert_hint", default="",
              help="Expected assertion hint")
@click.option("--description", "-d", default="")
@click.option("--tags", "-t", default="")
@click.option("--recorder", default="auto",
              type=click.Choice(["auto", "codegen", "js"]))
@click.option("--browser", default="chromium",
              type=click.Choice(["chromium", "firefox", "webkit"]))
@click.option("--skip-optimize", is_flag=True, default=False)
@click.option("--no-llm-heal", is_flag=True, default=False)
def run_all(url, name, assert_hint, description, tags, recorder, browser,
            skip_optimize, no_llm_heal):
    """
    Full pipeline: Record → Generate → Heal → Optimize.
    Runs all 4 phases end-to-end for a single test case.
    """
    _banner()
    console.print(
        Panel.fit(
            f"[bold]Full Pipeline[/bold]\n"
            f"  Test: [cyan]{name}[/cyan]\n"
            f"  URL:  [yellow]{url}[/yellow]\n"
            f"  Assert hint: [dim]{assert_hint or '(none)'}[/dim]",
            title="[bold cyan]TestForge Run-All[/bold cyan]",
            border_style="cyan",
        )
    )

    meta = {
        "name": name,
        "description": description,
        "expected_assert": assert_hint,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "url": url,
    }

    # ── Phase 1: Record ──────────────────────────────────────────────────────
    recording = None

    if recorder in ("auto", "codegen"):
        try:
            from recorder.codegen_recorder import record_with_codegen
            recording = record_with_codegen(url=url, meta=meta, browser=browser)
            if not recording.get("events") and not recording.get("raw_code"):
                recording = None
        except Exception:
            recording = None

    if recording is None:
        from recorder.js_recorder import record_with_injection
        recording = record_with_injection(url=url, meta=meta, browser_type=browser)

    from recording_manager import save_recording
    rec_path = save_recording(recording)
    console.print(f"\n[green]Phase 1 complete:[/green] {rec_path}")

    # ── Phase 2: Generate ────────────────────────────────────────────────────
    from generator.test_generator import generate_test
    test_path = generate_test(recording)
    console.print(f"[green]Phase 2 complete:[/green] {test_path}")

    # ── Phase 3: Self-Heal ───────────────────────────────────────────────────
    from healer.runner import run_with_healing
    heal_report = run_with_healing(
        test_path=test_path,
        recording=recording,
        llm_heal=not no_llm_heal,
    )
    console.print(
        f"[green]Phase 3 complete:[/green] "
        f"Status={heal_report['final_status']} "
        f"Healed={heal_report['healed_selectors']}"
    )

    if heal_report["final_status"] != "PASS":
        console.print(
            "[red]⚠ Test still failing after healing — "
            "skipping optimization.[/red]"
        )
        _print_summary(name, rec_path, test_path, heal_report, None)
        return

    # ── Phase 4: Optimize ────────────────────────────────────────────────────
    opt_report = None
    if not skip_optimize:
        from optimizer.tuner import optimize as run_optimize
        opt_report = run_optimize(test_path)
        console.print(
            f"[green]Phase 4 complete:[/green] "
            f"Saving ~{opt_report.get('estimated_saving_ms', 0)}ms"
        )

    _print_summary(name, rec_path, test_path, heal_report, opt_report)


def _print_summary(name, rec_path, test_path, heal_report, opt_report):
    """Print a final summary table."""
    table = Table(title=f"[bold]TestForge Summary — {name}[/bold]", show_header=False)
    table.add_column("Phase", style="cyan")
    table.add_column("Result", style="white")

    table.add_row("Recording", str(rec_path))
    table.add_row("Generated test", str(test_path))
    table.add_row(
        "Self-healing",
        f"[green]{heal_report['final_status']}[/green] | "
        f"Healed: {heal_report['healed_selectors']} | "
        f"Failed: {heal_report['failed_heals']}",
    )

    if opt_report:
        status = opt_report.get("status", "unknown")
        saving = opt_report.get("estimated_saving_ms", 0)
        pct = opt_report.get("reduction_pct", 0)
        opt_str = (
            f"[green]{status}[/green] | ~{saving}ms saved ({pct}%)"
            if status == "success"
            else f"[dim]{status}[/dim]"
        )
        table.add_row("Optimization", opt_str)
        if opt_report.get("optimized_path"):
            table.add_row("Optimized test", opt_report["optimized_path"])

    console.print(table)


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: list
# ══════════════════════════════════════════════════════════════════════════════
@cli.command("list")
@click.option("--recordings", "show_rec", is_flag=True, default=False)
@click.option("--tests", "show_tests", is_flag=True, default=False)
@click.option("--reports", "show_reports", is_flag=True, default=False)
def list_items(show_rec, show_tests, show_reports):
    """List recordings, tests, and reports."""
    _banner()
    show_all = not any([show_rec, show_tests, show_reports])

    if show_all or show_rec:
        from recording_manager import list_recordings
        recs = list_recordings()
        t = Table(title="Recordings", show_header=True)
        t.add_column("File", style="cyan")
        t.add_column("Name", style="white")
        t.add_column("Events", style="yellow")
        t.add_column("Stack", style="dim")
        for r in recs:
            try:
                data = json.loads(r.read_text())
                t.add_row(
                    r.name,
                    data.get("meta", {}).get("name", "?"),
                    str(len(data.get("events", []))),
                    data.get("stack", {}).get("name", "?"),
                )
            except Exception:
                t.add_row(r.name, "?", "?", "?")
        console.print(t)

    if show_all or show_tests:
        tests = list(Path("tests/generated").glob("test_*.py")) + \
                list(Path("tests/optimized").glob("test_*.py"))
        t = Table(title="Test Files", show_header=True)
        t.add_column("File", style="cyan")
        t.add_column("Size", style="dim")
        for p in sorted(tests):
            t.add_row(str(p), f"{p.stat().st_size} bytes")
        console.print(t)

    if show_all or show_reports:
        reports = list(Path("reports").glob("*.json")) if Path("reports").exists() else []
        t = Table(title="Reports", show_header=True)
        t.add_column("File", style="cyan")
        t.add_column("Status", style="white")
        for p in sorted(reports):
            try:
                data = json.loads(p.read_text())
                status = data.get("final_status") or data.get("status", "?")
                color = "green" if status in ("PASS", "success") else "red"
                t.add_row(p.name, f"[{color}]{status}[/{color}]")
            except Exception:
                t.add_row(p.name, "?")
        console.print(t)


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND: show-recording (debug helper)
# ══════════════════════════════════════════════════════════════════════════════
@cli.command("show-recording")
@click.argument("recording_path")
@click.option("--events", is_flag=True, default=False, help="Show all events")
def show_recording(recording_path, events):
    """Display recording details."""
    path = Path(recording_path)
    if not path.exists():
        console.print(f"[red]Not found: {path}[/red]")
        sys.exit(1)

    from recording_manager import load_recording
    data = load_recording(path)
    meta = data.get("meta", {})
    stack = data.get("stack", {})
    ev_list = data.get("events", [])

    console.print(Panel.fit(
        f"[bold]Name:[/bold] {meta.get('name', '?')}\n"
        f"[bold]Description:[/bold] {meta.get('description', '?')}\n"
        f"[bold]Assert hint:[/bold] {meta.get('expected_assert', '?')}\n"
        f"[bold]Tags:[/bold] {', '.join(meta.get('tags', []))}\n"
        f"[bold]URL:[/bold] {meta.get('url', '?')}\n"
        f"[bold]Stack:[/bold] {stack.get('name', '?')} v{stack.get('version', '?')}\n"
        f"[bold]Events:[/bold] {len(ev_list)}\n"
        f"[bold]Recorder:[/bold] {data.get('recorder', '?')}",
        title="[cyan]Recording Details[/cyan]",
    ))

    if events:
        t = Table(title="Events", show_header=True)
        t.add_column("#", style="dim")
        t.add_column("Type", style="cyan")
        t.add_column("Element", style="white")
        t.add_column("Value", style="yellow")
        t.add_column("Selector (best)", style="dim")
        for ev in ev_list:
            ctx = ev.get("context", {})
            sels = ev.get("selectors", {})
            best_sel = (
                sels.get("data_testid")
                or sels.get("aria")
                or sels.get("text")
                or sels.get("css", "?")
            )
            t.add_row(
                str(ev.get("id", "?")),
                ev.get("type", "?"),
                f"{ctx.get('element_tag','?')} {ctx.get('element_text','')[:30]}",
                str(ev.get("value", ""))[:30],
                str(best_sel)[:50],
            )
        console.print(t)


if __name__ == "__main__":
    cli()
