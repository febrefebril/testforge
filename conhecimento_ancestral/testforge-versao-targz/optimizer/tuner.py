"""
TestForge — Tuner (Phase 4)
Sends profiling metrics to LLM, receives optimization suggestions,
applies them to the test file, and re-runs to validate.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.llm_client import chat
from optimizer.profiler import run_profiled

log = logging.getLogger("testforge.tuner")

REPORTS_DIR = Path("reports")
OPTIMIZED_DIR = Path("tests/optimized")

TUNER_SYSTEM = """You are a Playwright test performance optimizer.
You receive timing data from a test run and must suggest specific code changes
to reduce total execution time without breaking the test.

RULES:
1. Only suggest reducing timeouts that completed in less than 30% of their configured value
2. Suggest replacing `wait_for_load_state("networkidle")` with `wait_for_load_state("domcontentloaded")`
   only if the page is NOT making critical background XHR after load
3. Suggest removing `wait_for_timeout(N)` calls under 500ms that appear redundant
4. Suggest replacing fixed timeouts with event-based waits where possible
5. Never remove waits that are clearly necessary for page stability

RESPOND ONLY with a JSON object (no markdown):
{
  "suggestions": [
    {
      "original": "exact string to replace",
      "replacement": "new string",
      "reason": "short explanation",
      "estimated_saving_ms": 200
    }
  ],
  "summary": "one sentence summary of changes"
}"""


def _apply_suggestions(source: str, suggestions: list[dict]) -> tuple[str, list[dict]]:
    """Apply LLM optimization suggestions to source code. Returns (new_source, applied_list)."""
    applied = []
    current = source

    for s in suggestions:
        original = s.get("original", "")
        replacement = s.get("replacement", "")
        if not original or original == replacement:
            continue
        if original in current:
            current = current.replace(original, replacement, 1)
            applied.append(s)
            log.info(f"Applied: {original!r} → {replacement!r}")
        else:
            log.debug(f"Not found in source: {original!r}")

    return current, applied


def _run_pytest_quick(test_path: Path) -> tuple[int, float]:
    """Run pytest and return (returncode, duration_seconds)."""
    import time
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_path),
        "-v", "--tb=line", "--no-header", "-q",
    ]
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return result.returncode, time.time() - t0


def optimize(test_path: Path) -> dict[str, Any]:
    """
    Full Phase 4 pipeline:
    1. Profile the test
    2. Send metrics to LLM for suggestions
    3. Apply suggestions
    4. Re-run to validate
    5. Save optimized version
    Returns a performance report dict.
    """
    from rich.console import Console
    console = Console()

    console.print(f"\n[bold yellow]⚡ Phase 4 — Performance Optimization:[/bold yellow] [cyan]{test_path.name}[/cyan]")

    # ── Step 1: Profile ────────────────────────────────────────────────────────
    console.print("  [dim]Running profiled test...[/dim]")
    profile_data = run_profiled(test_path)

    if profile_data["returncode"] != 0:
        console.print("  [red]✗ Test failed during profiling — cannot optimize a broken test[/red]")
        return {
            "status": "error",
            "reason": "test_failed_during_profiling",
            "test_path": str(test_path),
        }

    timings = profile_data["timings"]
    total_wait_ms = profile_data["total_wait_ms"]
    console.print(f"  Total wait time: [yellow]{total_wait_ms}ms[/yellow] across {len(timings)} wait calls")

    if not timings:
        console.print("  [dim]No wait calls detected — nothing to optimize[/dim]")
        return {
            "status": "skipped",
            "reason": "no_waits_detected",
            "original_duration_ms": total_wait_ms,
        }

    # ── Step 2: Ask LLM ────────────────────────────────────────────────────────
    source = test_path.read_text(encoding="utf-8")

    user_prompt = f"""## TEST FILE
```python
{source[:6000]}
```

## TIMING DATA (actual wait durations measured at runtime)
{json.dumps(timings, indent=2)}

## SUMMARY
- Total wait time: {total_wait_ms}ms
- Number of wait calls: {len(timings)}
- Average wait: {total_wait_ms // max(len(timings), 1)}ms

Suggest optimizations to reduce total wait time.
Focus on waits that completed MUCH faster than their timeout (quick completions = timeout is too high).
"""

    console.print("  [dim]Asking LLM for optimization suggestions...[/dim]")
    try:
        response = chat(
            system=TUNER_SYSTEM,
            user=user_prompt,
            temperature=0.1,
            max_tokens=2048,
        )
        clean = re.sub(r"```json?\n?|```", "", response).strip()
        llm_result = json.loads(clean)
        suggestions = llm_result.get("suggestions", [])
        summary = llm_result.get("summary", "")
    except Exception as e:
        log.error(f"LLM optimization failed: {e}")
        suggestions = []
        summary = "LLM unavailable"

    console.print(f"  [cyan]{len(suggestions)} suggestion(s) received:[/cyan] {summary}")

    if not suggestions:
        console.print("  [dim]No optimizations suggested[/dim]")
        return {
            "status": "no_suggestions",
            "original_duration_ms": total_wait_ms,
            "optimized_duration_ms": total_wait_ms,
            "reduction_pct": 0.0,
            "optimizations_applied": [],
        }

    # ── Step 3: Apply suggestions ──────────────────────────────────────────────
    optimized_source, applied = _apply_suggestions(source, suggestions)

    if not applied:
        console.print("  [yellow]  No suggestions could be applied (patterns not found)[/yellow]")
        return {
            "status": "no_changes",
            "original_duration_ms": total_wait_ms,
            "optimized_duration_ms": total_wait_ms,
            "reduction_pct": 0.0,
            "optimizations_applied": [],
        }

    # Write optimized version to temp path for validation
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    optimized_name = test_path.stem + "_optimized.py"
    optimized_path = OPTIMIZED_DIR / optimized_name
    optimized_path.write_text(optimized_source, encoding="utf-8")

    # ── Step 4: Validate optimized version ────────────────────────────────────
    console.print(f"  [dim]Validating optimized test: {optimized_path.name}...[/dim]")
    import time as _time
    t0 = _time.time()
    rc, _ = _run_pytest_quick(optimized_path)
    optimized_duration_ms = int((_time.time() - t0) * 1000)

    if rc != 0:
        console.print("  [red]✗ Optimized test FAILED — reverting[/red]")
        optimized_path.unlink(missing_ok=True)
        # Keep original, mark suggestions as invalid
        return {
            "status": "optimization_broke_test",
            "original_duration_ms": total_wait_ms,
            "optimized_duration_ms": optimized_duration_ms,
            "reduction_pct": 0.0,
            "optimizations_applied": [],
            "failed_suggestions": [s["reason"] for s in applied],
        }

    # ── Step 5: Save & report ──────────────────────────────────────────────────
    estimated_saving = sum(s.get("estimated_saving_ms", 0) for s in applied)
    reduction_pct = round(estimated_saving / max(total_wait_ms, 1) * 100, 1)

    for s in applied:
        console.print(
            f"  [green]  ✓[/green] [dim]{s['original'][:50]!r} → {s['replacement'][:50]!r}[/dim] "
            f"[yellow](~{s.get('estimated_saving_ms', 0)}ms saved)[/yellow]"
        )

    console.print(
        f"\n  [bold green]Optimization complete![/bold green] "
        f"Estimated saving: [yellow]~{estimated_saving}ms[/yellow] "
        f"([cyan]{reduction_pct}%[/cyan] of wait time)"
    )
    console.print(f"  [dim]Saved: {optimized_path}[/dim]")

    # ── Save performance report ────────────────────────────────────────────────
    report = {
        "test_name": test_path.stem,
        "timestamp": datetime.now().isoformat(),
        "original_total_wait_ms": total_wait_ms,
        "optimized_duration_ms": optimized_duration_ms,
        "estimated_saving_ms": estimated_saving,
        "reduction_pct": reduction_pct,
        "optimizations_applied": [
            {
                "original": s["original"][:100],
                "replacement": s["replacement"][:100],
                "reason": s.get("reason", ""),
                "estimated_saving_ms": s.get("estimated_saving_ms", 0),
            }
            for s in applied
        ],
        "optimized_path": str(optimized_path),
        "status": "success",
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"performance_report_{test_path.stem}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print(f"  [dim]Report: {report_path}[/dim]")

    return report
