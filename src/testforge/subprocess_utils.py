"""Helpers de subprocesso para evitar janelas de console no Windows."""
from __future__ import annotations

import os
import subprocess
from typing import Any


def windows_hidden_process_kwargs() -> dict[str, Any]:
    """Retorna kwargs para esconder janelas de subprocesso no Windows."""
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return {
        "startupinfo": startupinfo,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }


def run_hidden(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess:
    """Wrapper de subprocess.run com ocultacao de janela no Windows."""
    hidden = windows_hidden_process_kwargs()
    for key, value in hidden.items():
        kwargs.setdefault(key, value)
    return subprocess.run(*popenargs, **kwargs)


def popen_hidden(*popenargs: Any, **kwargs: Any) -> subprocess.Popen:
    """Wrapper de subprocess.Popen com ocultacao de janela no Windows."""
    hidden = windows_hidden_process_kwargs()
    for key, value in hidden.items():
        kwargs.setdefault(key, value)
    return subprocess.Popen(*popenargs, **kwargs)
