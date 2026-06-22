"""TestForge — Silent self-update via git pull on startup."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def check_and_apply_update(project_root: Path) -> None:
    """Fetch origin/main; if ahead, pull and re-exec. Never blocks startup."""
    try:
        # Skip if TESTFORGE_NO_UPDATE is set (useful for CI or offline use)
        if os.getenv("TESTFORGE_NO_UPDATE"):
            return

        # Require git repo
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(project_root),
            capture_output=True,
            timeout=3,
        )
        if r.returncode != 0:
            return

        # Fetch silently (short timeout — don't punish offline users)
        subprocess.run(
            ["git", "fetch", "origin", "main", "--quiet"],
            cwd=str(project_root),
            capture_output=True,
            timeout=5,
        )

        # Count commits we're behind
        r = subprocess.run(
            ["git", "rev-list", "HEAD..origin/main", "--count"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode != 0:
            return
        behind = int(r.stdout.strip() or "0")
        if behind == 0:
            return

        # Pull with rebase (keeps local commits on top, avoids merge commits)
        subprocess.run(
            ["git", "pull", "--rebase", "--quiet", "origin", "main"],
            cwd=str(project_root),
            capture_output=True,
            timeout=30,
        )

        print(f"[TestForge] Atualizado ({behind} commit(s)). Reiniciando...", file=sys.stderr)
        # Replace current process with updated code
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception:
        # Never block startup
        pass
