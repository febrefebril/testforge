
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TestForge — Snapshot de gravacoes em arquivo unico (formato code2txt2code).

Aponta para a pasta com TODAS as gravacoes e gera UM unico arquivo .txt (ou
varios, com --split-mb) no mesmo formato do snapshot do projeto:

    # code2txt2code snapshot
    # generated_at: <ISO-8601>
    # root_name: <nome da pasta raiz>
    # profile: <perfil>
    # file_count: <N>

    ===== FILE: <caminho/relativo> =====
    # sha256: <hash>
    <conteudo do arquivo>
    ===== END FILE: <caminho/relativo> =====

--------------------------------------------------------------------------
PROBLEMA QUE ESTE SCRIPT RESOLVE
--------------------------------------------------------------------------
Gravacoes do TestForge contem dumps BRUTOS pesados (ax_snapshots/*.json,
dom_snapshots/*.html, rrweb_events.jsonl, raw_events.jsonl) que respondem por
~85% do tamanho e NAO sao necessarios para diagnosticar falhas de
seletor/healing. O diagnostico real esta nos artefatos destilados
(readiness_report, execution_report, replay_check, steps, completeness...).

Por isso o script classifica os arquivos em CAMADAS e usa PERFIS:

  --profile diag  (PADRAO)  Artefatos de diagnostico VERBATIM;
                            dumps brutos e binarios entram como STUB
                            (nome + tamanho + sha256). Gera arquivo pequeno.
  --profile full            Inclui tudo que for texto verbatim
                            (dumps brutos inclusos). Pode ficar enorme.
  --profile min             Apenas uma allowlist curada dos artefatos-chave.

--------------------------------------------------------------------------
USO (Windows PowerShell / cmd)
--------------------------------------------------------------------------
    python tf_snapshot.py --root C:\\...\\recordings --out gravacoes.txt
    python tf_snapshot.py --root C:\\...\\recordings --profile full
    python tf_snapshot.py --root C:\\...\\recordings --split-mb 20
    python tf_snapshot.py --root C:\\...\\recordings --only-failed

Sem dependencias externas — apenas a biblioteca padrao do Python 3.8+.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Classificacao de camadas
# ---------------------------------------------------------------------------

# Extensoes tratadas como TEXTO.
TEXT_EXT = {
    ".txt", ".json", ".jsonl", ".ndjson", ".py", ".js", ".ts", ".mjs",
    ".yaml", ".yml", ".md", ".html", ".htm", ".csv", ".tsv", ".log",
    ".xml", ".ini", ".cfg", ".toml", ".env", ".sql", ".css", ".puml",
    ".gherkin", ".feature",
}

# Binarios tipicos — sempre STUB (a menos de --include-binary).
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".webm", ".mp4", ".avi", ".mov",
    ".zip", ".gz", ".tar", ".7z",
    ".sqlite", ".sqlite3", ".db",
    ".pdf", ".woff", ".woff2", ".ttf",
}

# Dumps BRUTOS pesados (Camada 2). Casados por caminho relativo (glob).
# Em --profile diag/min entram como STUB; em --profile full sao incluidos.
HEAVY_GLOBS = [
    "*/ax_snapshots/*", "ax_snapshots/*",
    "*/dom_snapshots/*", "dom_snapshots/*",
    "*rrweb_events.jsonl",
    "*raw_events.jsonl",
    "*field_snapshots.jsonl",
    "*value_mutations.jsonl",
    "*final_state_snapshot.json",
    "*/screenshots/*", "screenshots/*",
    "*/trace*/*",
]

# Allowlist curada (Camada 1) usada pelo --profile min. Casada por basename
# ou por sufixo de caminho.
MIN_ALLOW = [
    "FAILED_MARKER.json",
    "readiness_report.json", "readiness_report.md",
    "execution_report.json",
    "healing_report.md",
    "metrics.json",
    "replay_check.jsonl",
    "steps.jsonl",
    "intent_completeness_report.json", "intent_completeness_report.md",
    "session.json",
    "audit_report.json",
    "recording_metadata.json",
    "recording_config.json",
    "suggested_assertions.jsonl",
    "scenario.feature",
    "screen_states.jsonl",
    "network_log.json",
    "test_*.py",
]


def _match_any(rel: str, globs) -> bool:
    rel_norm = rel.replace(os.sep, "/")
    base = os.path.basename(rel_norm)
    for g in globs:
        if fnmatch.fnmatch(rel_norm, g) or fnmatch.fnmatch(base, g):
            return True
    return False


def is_heavy(rel: str) -> bool:
    return _match_any(rel, HEAVY_GLOBS)


def is_min_allowed(rel: str) -> bool:
    return _match_any(rel, MIN_ALLOW)


def is_text_ext(path: str, extra_binary: set) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in extra_binary or ext in BINARY_EXT:
        return False
    if ext in TEXT_EXT:
        return True
    # Desconhecido: sniff dos primeiros bytes.
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def truncate_text(content: str, max_bytes: int) -> str:
    raw = content.encode("utf-8", errors="replace")
    if len(raw) <= max_bytes:
        return content
    half = max_bytes // 2
    head = raw[:half].decode("utf-8", errors="ignore")
    tail = raw[-half:].decode("utf-8", errors="ignore")
    return head + "\n\n...[TRUNCADO por tf_snapshot — %d bytes omitidos]...\n\n" % (
        len(raw) - max_bytes) + tail


def iter_files(root: str):
    for dirpath, dirs, files in os.walk(root):
        dirs.sort()
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for fn in sorted(files):
            yield os.path.join(dirpath, fn)


def recording_failed(rec_dir: str) -> bool:
    """Heuristica p/ --only-failed: procura FAILED_MARKER ou readiness fail."""
    for dp, _d, files in os.walk(rec_dir):
        for fn in files:
            low = fn.lower()
            if low == "failed_marker.json":
                return True
            if low == "readiness_report.json":
                try:
                    data = json.load(open(os.path.join(dp, fn), encoding="utf-8"))
                    rr = data.get("readiness_report", data)
                    if rr.get("verdict") == "fail" or rr.get("failures"):
                        return True
                except Exception:
                    pass
    return False


# ---------------------------------------------------------------------------
# Renderizacao de um bloco de arquivo
# ---------------------------------------------------------------------------

def render_block(rel: str, path: str, profile: str, max_bytes: int,
                 extra_binary: set, include_binary: bool):
    """Retorna (texto_do_bloco, kind). kind in text|trunc|heavy_stub|bin_stub|bin_b64|skip"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return None, "skip"

    try:
        digest = sha256_of(path)
    except Exception:
        digest = "(erro sha256)"

    header = f"===== FILE: {rel} =====\n# sha256: {digest}\n"
    footer = f"===== END FILE: {rel} =====\n\n"

    text_ok = is_text_ext(path, extra_binary)
    heavy = is_heavy(rel)

    # Binario
    if not text_ok:
        if include_binary:
            b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
            return header + f"# [BINARIO base64: {size} bytes]\n{b64}\n" + footer, "bin_b64"
        return header + f"# [BINARIO OMITIDO: {size/1024/1024:.3f} MB ({size} bytes) — stub]\n" + footer, "bin_stub"

    # Texto pesado (dump bruto) em perfil diag/min -> stub
    if heavy and profile in ("diag", "min"):
        return header + f"# [DUMP BRUTO OMITIDO ({profile}): {size/1024/1024:.3f} MB ({size} bytes) — stub. Use --profile full para incluir]\n" + footer, "heavy_stub"

    # Texto normal
    content = read_text(path)
    if max_bytes > 0 and len(content.encode("utf-8", "replace")) > max_bytes:
        content = truncate_text(content, max_bytes)
        kind = "trunc"
    else:
        kind = "text"
    if not content.endswith("\n"):
        content += "\n"
    return header + content + footer, kind


# ---------------------------------------------------------------------------
# Escrita (com suporte a split)
# ---------------------------------------------------------------------------

class SplitWriter:
    """Escreve em um ou varios arquivos, quebrando por tamanho (--split-mb)."""

    def __init__(self, out_path: str, split_bytes: int, header_lines: list):
        self.base = out_path
        self.split_bytes = split_bytes
        self.header_lines = header_lines
        self.part = 0
        self.count_in_part = 0
        self.bytes_in_part = 0
        self.fh = None
        self.paths = []
        self._open_new()

    def _path_for(self, part: int) -> str:
        if self.split_bytes <= 0:
            return self.base
        root, ext = os.path.splitext(self.base)
        return f"{root}.part{part:02d}{ext}"

    def _open_new(self):
        if self.fh:
            self.fh.close()
        self.part += 1
        p = self._path_for(self.part)
        self.paths.append(p)
        self.fh = open(p, "w", encoding="utf-8")
        for l in self.header_lines:
            self.fh.write(l)
        self.bytes_in_part = sum(len(l.encode("utf-8")) for l in self.header_lines)
        self.count_in_part = 0

    def write_block(self, block: str):
        b = len(block.encode("utf-8", "replace"))
        if (self.split_bytes > 0 and self.count_in_part > 0
                and self.bytes_in_part + b > self.split_bytes):
            self._open_new()
        self.fh.write(block)
        self.bytes_in_part += b
        self.count_in_part += 1

    def close(self):
        if self.fh:
            self.fh.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Gera snapshot unico (code2txt2code) das gravacoes do TestForge.")
    ap.add_argument("--root", default=".", help="Pasta raiz das gravacoes")
    ap.add_argument("--out", default="gravacoes_snapshot.txt", help="Arquivo de saida")
    ap.add_argument("--profile", choices=["diag", "full", "min"], default="diag",
                    help="diag (padrao): diagnostico verbatim + dumps como stub | "
                         "full: tudo verbatim | min: so allowlist curada")
    ap.add_argument("--max-kb", type=int, default=768,
                    help="Trunca arquivos texto acima deste tamanho (KB). 0 = sem limite")
    ap.add_argument("--split-mb", type=float, default=0,
                    help="Divide a saida em partes de ate N MB (0 = arquivo unico)")
    ap.add_argument("--only-failed", action="store_true",
                    help="Inclui apenas gravacoes com FAILED_MARKER / readiness=fail")
    ap.add_argument("--include-binary", action="store_true",
                    help="Embute binarios em base64 (infla muito — evite)")
    ap.add_argument("--exclude-ext", default="",
                    help="Extensoes extras a pular como binario (ex: .zip,.mp4)")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[ERRO] root nao e uma pasta valida: {root}", file=sys.stderr)
        return 2

    extra_binary = {e if e.startswith(".") else "." + e
                    for e in (x.strip().lower() for x in args.exclude_ext.split(",")) if e}
    max_bytes = args.max_kb * 1024
    split_bytes = int(args.split_mb * 1024 * 1024)
    out_abs = os.path.abspath(args.out)

    # --only-failed: pre-seleciona diretorios de gravacao (nivel imediato).
    allowed_dirs = None
    if args.only_failed:
        allowed_dirs = set()
        for d in sorted(os.listdir(root)):
            full = os.path.join(root, d)
            if os.path.isdir(full) and recording_failed(full):
                allowed_dirs.add(os.path.abspath(full))

    # Coleta
    selected = []
    for path in iter_files(root):
        if os.path.abspath(path) == out_abs:
            continue
        if allowed_dirs is not None:
            ap_ = os.path.abspath(path)
            if not any(ap_.startswith(d + os.sep) for d in allowed_dirs):
                continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if args.profile == "min" and not is_min_allowed(rel) and not is_heavy(rel):
            # em 'min', so allowlist; tudo mais (menos heavy stub) e pulado
            continue
        selected.append((rel, path))

    root_name = os.path.basename(root.rstrip("/\\")) or "recordings"
    header_lines = [
        "# code2txt2code snapshot\n",
        f"# generated_at: {datetime.now(timezone.utc).isoformat()}\n",
        f"# root_name: {root_name}\n",
        f"# profile: {args.profile}\n",
        f"# file_count: {len(selected)}\n\n",
    ]

    writer = SplitWriter(out_abs, split_bytes, header_lines)
    stats = {"text": 0, "trunc": 0, "heavy_stub": 0, "bin_stub": 0,
             "bin_b64": 0, "skip": 0}
    total_in = 0
    for rel, path in selected:
        try:
            total_in += os.path.getsize(path)
        except OSError:
            pass
        block, kind = render_block(rel, path, args.profile, max_bytes,
                                   extra_binary, args.include_binary)
        stats[kind] = stats.get(kind, 0) + 1
        if block:
            writer.write_block(block)
    writer.close()

    out_size = sum(os.path.getsize(p) for p in writer.paths)
    print(f"[OK] Perfil: {args.profile}")
    print(f"[OK] Gravacoes/arquivos processados: {len(selected)}")
    print(f"[OK] Entrada total: {total_in/1024/1024:.2f} MB  ->  Saida: {out_size/1024/1024:.2f} MB "
          f"({100*out_size/max(total_in,1):.1f}% do original)")
    print(f"[OK] Detalhe: verbatim={stats['text']}, truncados={stats['trunc']}, "
          f"dumps-stub={stats['heavy_stub']}, bin-stub={stats['bin_stub']}, "
          f"bin-b64={stats['bin_b64']}")
    if len(writer.paths) == 1:
        print(f"[OK] Arquivo: {writer.paths[0]}")
    else:
        print(f"[OK] {len(writer.paths)} partes:")
        for p in writer.paths:
            print(f"     - {p}  ({os.path.getsize(p)/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

