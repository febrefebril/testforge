"""
TestForge — Profiler (Phase 4)
Instruments the test to measure wait durations and identify optimization targets.
"""
from __future__ import annotations

import ast
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("testforge.profiler")


# Playwright wait calls we want to profile
WAIT_CALLS = [
    "wait_for_load_state",
    "wait_for_selector",
    "wait_for_timeout",
    "wait_for_url",
    "wait_for_function",
]


def _inject_timing_wrappers(source: str) -> str:
    """
    Wrap every wait_for_* call with a timing print so we can measure durations.
    E.g.:
        page.wait_for_timeout(1000)
    becomes:
        __t0 = time.time(); page.wait_for_timeout(1000); print(f"[TIMING] wait_for_timeout 1000 {(time.time()-__t0)*1000:.0f}ms")
    """
    lines = source.splitlines()
    result = []
    import_injected = False

    for line in lines:
        stripped = line.strip()

        # Inject import time after first import block
        if not import_injected and stripped.startswith(("import ", "from ")):
            result.append(line)
            continue
        if not import_injected and stripped and not stripped.startswith(("#", "import", "from", '"""', "'''")):
            result.append("import time as _time  # TestForge profiler")
            import_injected = True

        # Check if line contains a wait call
        matched = False
        for wc in WAIT_CALLS:
            if wc in stripped:
                indent = len(line) - len(line.lstrip())
                pad = " " * indent
                # Extract the wait call argument(s) for the label
                m = re.search(rf'{wc}\(([^)]*)\)', stripped)
                args_str = m.group(1) if m else "?"
                # Wrap with timing
                var = f"_tf_t{abs(hash(line)) % 9999}"
                result.append(f"{pad}{var} = _time.time()")
                result.append(line)
                result.append(
                    f'{pad}print(f"[TIMING] {wc}({args_str[:40]}) '
                    f'{{(_time.time()-{var})*1000:.0f}}ms")'
                )
                matched = True
                break

        if not matched:
            result.append(line)

    if not import_injected:
        result.insert(0, "import time as _time  # TestForge profiler")

    return "\n".join(result)


def run_profiled(test_path: Path) -> dict[str, Any]:
    """
    Run the test with timing injection and return profiling metrics.
    """
    source = test_path.read_text(encoding="utf-8")
    instrumented = _inject_timing_wrappers(source)

    # Write to temp file
    profiled_path = test_path.with_suffix(".profiled.py")
    profiled_path.write_text(instrumented, encoding="utf-8")

    cmd = [
        sys.executable, "-m", "pytest",
        str(profiled_path),
        "-v", "--tb=short", "-s", "--no-header",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    finally:
        profiled_path.unlink(missing_ok=True)

    combined = result.stdout + "\n" + result.stderr

    # Parse [TIMING] lines
    timings = []
    for m in re.finditer(r'\[TIMING\] (\S+)\(([^)]*)\) (\d+)ms', combined):
        timings.append({
            "call": m.group(1),
            "args": m.group(2),
            "duration_ms": int(m.group(3)),
        })

    return {
        "returncode": result.returncode,
        "timings": timings,
        "total_wait_ms": sum(t["duration_ms"] for t in timings),
        "stdout": combined[:3000],
    }
