"""TestForge — Auto-atualizacao silenciosa via git pull na inicializacao."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def check_and_apply_update(project_root: Path) -> None:
    """Busca origin/main; se a frente, faz pull e re-executa. Nunca bloqueia inicializacao."""
    try:
        # Pula se TESTFORGE_NO_UPDATE estiver definido (util para CI ou offline)
        if os.getenv("TESTFORGE_NO_UPDATE"):
            return

        # Requer repo git
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(project_root),
            capture_output=True,
            timeout=3,
        )
        if r.returncode != 0:
            return

        # Fetch silencioso (timeout curto — nao punir usuarios offline)
        subprocess.run(
            ["git", "fetch", "origin", "main", "--quiet"],
            cwd=str(project_root),
            capture_output=True,
            timeout=5,
        )

        # Conta commits que estamos atras
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

        # Pull com rebase (mantem commits locais no topo, evita merge commits)
        subprocess.run(
            ["git", "pull", "--rebase", "--quiet", "origin", "main"],
            cwd=str(project_root),
            capture_output=True,
            timeout=30,
        )

        print(f"[TestForge] Atualizado ({behind} commit(s)). Reiniciando...", file=sys.stderr)
        # Substitui processo atual pelo codigo atualizado
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception:
        # Nunca bloqueia inicializacao
        pass
