
"""TestForge — Acoes de arquivo (upload/download) deterministicas.

Cobre: upload via set_input_files (input direto ou file chooser);
parametrizacao do caminho; download via expect_download; validacao do
arquivo baixado (existencia, tamanho, extensao, sha256).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class FileActionError(Exception):
    """Erro em acao de upload/download."""


def resolve_path(raw: str, *, data: Optional[dict] = None,
                 base_dir: Optional[str] = None) -> str:
    """Parametriza caminho: substitui ${VAR} (data->env), expande ~ e
    resolve relativo contra base_dir (TESTFORGE_FILES ou cwd)."""
    data = data or {}

    def _sub(key: str) -> str:
        if key in data:
            return str(data[key])
        return os.environ.get(key, "")

    value = re.sub(r"\$\{([A-Za-z0-9_]+)\}", lambda m: _sub(m.group(1)), raw)
    value = os.path.expanduser(value)
    p = Path(value)
    if not p.is_absolute():
        base = base_dir or os.environ.get("TESTFORGE_FILES") or os.getcwd()
        p = Path(base) / p
    return str(p)


def upload_files(page: Page, selector: str,
                 files: Union[str, Sequence[str]], *,
                 data: Optional[dict] = None, base_dir: Optional[str] = None,
                 via_chooser: bool = False, chooser_trigger=None,
                 timeout_ms: int = 15_000) -> list:
    """Upload de 1..N arquivos. via_chooser usa expect_file_chooser."""
    raw_list = [files] if isinstance(files, str) else list(files)
    resolved = [resolve_path(f, data=data, base_dir=base_dir) for f in raw_list]
    for f in resolved:
        if not os.path.isfile(f):
            raise FileActionError(f"Arquivo para upload inexistente: {f}")
    if via_chooser:
        if chooser_trigger is None:
            raise FileActionError("via_chooser=True requer chooser_trigger.")
        with page.expect_file_chooser(timeout=timeout_ms) as info:
            chooser_trigger()
        info.value.set_files(resolved)
    else:
        page.set_input_files(selector, resolved, timeout=timeout_ms)
    logger.info("Upload de %d arquivo(s) em %s", len(resolved), selector)
    return resolved


@dataclass
class DownloadResult:
    path: str
    suggested_filename: str
    size_bytes: int
    sha256: str = ""


def download_file(page: Page, trigger, *, save_dir: Optional[str] = None,
                  timeout_ms: int = 30_000) -> "DownloadResult":
    """Aciona trigger() e captura/salva o download resultante."""
    save_dir = save_dir or os.environ.get("TESTFORGE_DOWNLOADS") or os.getcwd()
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    with page.expect_download(timeout=timeout_ms) as info:
        trigger()
    download = info.value
    suggested = download.suggested_filename or "download.bin"
    target = os.path.join(save_dir, suggested)
    download.save_as(target)
    size = os.path.getsize(target) if os.path.exists(target) else 0
    return DownloadResult(path=target, suggested_filename=suggested, size_bytes=size)


def validate_downloaded_file(result: "DownloadResult", *, min_bytes: int = 1,
                             allowed_ext: Optional[Sequence[str]] = None,
                             expected_sha256: str = "") -> "DownloadResult":
    """Valida arquivo baixado: existencia, tamanho, extensao e hash."""
    if not os.path.isfile(result.path):
        raise FileActionError(f"Arquivo baixado nao encontrado: {result.path}")
    if result.size_bytes < min_bytes:
        raise FileActionError(
            f"Arquivo baixado muito pequeno: {result.size_bytes} bytes (min {min_bytes})."
        )
    if allowed_ext:
        ext = Path(result.path).suffix.lower().lstrip(".")
        norm = {e.lower().lstrip('.') for e in allowed_ext}
        if ext not in norm:
            raise FileActionError(f"Extensao inesperada: .{ext} (esperado {sorted(norm)}).")
    if expected_sha256:
        h = hashlib.sha256()
        with open(result.path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        result.sha256 = h.hexdigest()
        if result.sha256.lower() != expected_sha256.lower():
            raise FileActionError(
                f"sha256 divergente: obtido {result.sha256}, esperado {expected_sha256}."
            )
    logger.info("Download validado: %s (%d bytes)", result.path, result.size_bytes)
    return result

