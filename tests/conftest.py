
"""Test-wide pytest hooks for TestForge-specific markers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


PATH_MARKERS = {
    "tests/unit/": "unit",
    "tests/integration/": "integration",
    "tests/e2e/": "e2e",
    "tests/regression/": "regression",
    "tests/contract/": "contract",
}

# Fixtures do pytest-playwright que exigem um navegador real.
BROWSER_FIXTURES = {
    "page",
    "browser",
    "context",
    "browser_type",
    "new_context",
    "new_page",
    "browser_context_args",
}

_BROWSER_STATE: dict[str, object] = {}


def _detect_channel() -> str:
    """Canal do navegador instalado no sistema.

    Neste ambiente os bundles do Playwright nao podem ser baixados, entao a
    unica pergunta valida e: existe Edge/Chrome instalado? Reusa a deteccao do
    doctor para nao manter duas listas de caminhos.
    """
    if "channel" in _BROWSER_STATE:
        return str(_BROWSER_STATE["channel"])
    channel = ""
    if not os.getenv("TESTFORGE_SKIP_E2E", "").strip():
        try:
            from testforge.installer_doctor import preferred_channel

            channel = preferred_channel()
        except Exception:
            for executable, name in (
                ("microsoft-edge", "msedge"),
                ("microsoft-edge-stable", "msedge"),
                ("google-chrome", "chrome"),
                ("chromium", "chromium"),
            ):
                if shutil.which(executable):
                    channel = name
                    break
    _BROWSER_STATE["channel"] = channel
    return channel


def browsers_available() -> bool:
    """True quando ha navegador do sistema utilizavel.

    Sem isso a suite quebrava com ERROR no setup da fixture `browser`, como
    registrado em recorder_submit_first_error.txt. Um teste que nao pode rodar
    deve virar SKIP, nunca ERROR.
    """
    return bool(_detect_channel())


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Forca o canal do navegador instalado, ja que nao ha bundle disponivel."""
    channel = _detect_channel()
    if channel and channel != "chromium":
        return {**browser_type_launch_args, "channel": channel}
    return browser_type_launch_args


def pytest_collection_modifyitems(config, items):
    """Marca por caminho, marca testes de navegador como e2e e aplica xfail
    estrito aos testes marcados como known_bug."""

    for item in items:
        path = str(item.fspath).replace("\\", "/")
        for prefix, marker in PATH_MARKERS.items():
            if prefix in path:
                item.add_marker(getattr(pytest.mark, marker))

        if BROWSER_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.e2e)

        mark = item.get_closest_marker("known_bug")
        if not mark:
            continue

        bug_id = mark.kwargs.get("bug_id", "UNKNOWN")
        observed = mark.kwargs.get("observed", "")
        reason = f"Known bug {bug_id}"
        if observed:
            reason = f"{reason}: {observed}"

        item.add_marker(pytest.mark.xfail(reason=reason, strict=True))


def pytest_runtest_setup(item):
    """Pula testes e2e quando nao ha navegador instalado no sistema."""
    if item.get_closest_marker("e2e") is None:
        return
    if browsers_available():
        return
    pytest.skip(
        "nenhum navegador do sistema encontrado (Edge/Chrome). "
        'Rode a suite offline com: python -m pytest -m "not e2e"'
    )
