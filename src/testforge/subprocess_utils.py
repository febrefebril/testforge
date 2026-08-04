
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
    # Windows default text decoding follows active code page (cp1252), which
    # can break when child processes emit UTF-8 logs. Default to UTF-8 in
    # text mode unless caller explicitly sets encoding.
    text_mode = bool(kwargs.get("text") or kwargs.get("universal_newlines"))
    if text_mode and "encoding" not in kwargs:
        kwargs["encoding"] = "utf-8"
        kwargs.setdefault("errors", "replace")
    return subprocess.Popen(*popenargs, **kwargs)

