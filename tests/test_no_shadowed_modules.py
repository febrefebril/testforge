"""Gate estrutural: nenhum modulo pode ser sombreado por um pacote de mesmo nome.

Motivacao (S1): `src/testforge/updater.py` coexistia com `src/testforge/updater/`.
O pacote vence no import system, entao o .py virava codigo morto com semantica
DIFERENTE (git pull --rebase origin main, em vez de merge --ff-only no perfil).
Duas verdades para "atualizar a aplicacao" e um arquivo que ninguem executa.
"""
from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "testforge"


def _shadowed() -> list[str]:
    found: list[str] = []
    for directory in PACKAGE_ROOT.rglob("*"):
        if not directory.is_dir() or directory.name == "__pycache__":
            continue
        sibling = directory.with_suffix(".py")
        if sibling.is_file():
            found.append(sibling.relative_to(PACKAGE_ROOT).as_posix())
    return sorted(found)


def test_no_module_is_shadowed_by_package():
    shadowed = _shadowed()
    assert not shadowed, (
        "Modulos sombreados por pacote de mesmo nome (codigo morto e ambiguo): "
        + ", ".join(shadowed)
        + ". Remova com: git rm src/testforge/<nome>.py"
    )
