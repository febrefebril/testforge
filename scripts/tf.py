
#!/usr/bin/env python3
"""tf — ferramenta unica do TestForge: snapshot, patch, commit, rollback e log.

Substitui, com um so arquivo e sem dependencia externa:
  - code2txt2code.py / code2txt2code_corrigido.py  (snapshot + aplicacao semantica)
  - TestForge-PatchFlow.ps1                        (fluxo git, commits, rollback)

Funciona igual no Windows e no Linux. Usa apenas a biblioteca padrao do Python
3.10+. Nao exige privilegio administrativo, Docker nem rede.

Comandos
--------
  tf snapshot   Gera snapshot textual do projeto, por modulo ou de uma pasta.
  tf check      Valida patches sem tocar em nada.
  tf apply      Aplica patches em sequencia, roda gates e commita entre eles.
  tf rollback   Volta o repositorio ao estado anterior a um passo.
  tf status     Mostra o estado do fluxo e do repositorio.
  tf log        Mostra o log da ultima execucao (ou de uma execucao especifica).

Exemplos
--------
  python scripts/tf.py snapshot --out snapshots/
  python scripts/tf.py snapshot --by-module --out snapshots/
  python scripts/tf.py snapshot --path src/testforge/semantic --out sem.txt
  python scripts/tf.py check   --manifest patch-manifest.json
  python scripts/tf.py apply   --manifest patch-manifest.json
  python scripts/tf.py apply   --manifest patch-manifest.json --resume
  python scripts/tf.py rollback --to S1-05
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

TOOL_VERSION = "2.0.0"
SNAPSHOT_SCHEMA = 5
STATE_DIR = ".tf"

# --------------------------------------------------------------------------- #
# Selecao de conteudo do snapshot
# --------------------------------------------------------------------------- #

# Somente codigo e configuracao. Tudo que nao esta aqui fica de fora.
CODE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue",
    ".json", ".jsonc", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
    ".properties", ".env.example", ".md", ".rst", ".txt", ".feature",
    ".html", ".css", ".scss", ".xml", ".sql", ".sh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".gradle", ".java", ".cs", ".go", ".rs",
}

# Arquivos sem extensao que ainda sao configuracao relevante.
CODE_FILENAMES = {
    "VERSION", "Makefile", "Dockerfile", "Procfile", "requirements.txt",
    ".gitignore", ".gitattributes", ".editorconfig", ".dockerignore",
    "pyproject.toml", "setup.cfg", "tox.ini", "pytest.ini",
}

# Diretorios que nunca entram. Comparados por prefixo de caminho relativo.
EXCLUDED_DIR_PREFIXES = (
    ".git/", ".tf/", ".venv/", "venv/", "env/", "node_modules/",
    "dist/", "build/", "target/", "coverage/", "htmlcov/", "site-packages/",
    "recordings/", "recordings_failed/", "semantic_tests/", "submissions/",
    "workspace/", "runs/", "reports/", "golden_runs/", "patch-runs/",
    "_pilot_runs/", "_pilot_tmp/", "snapshots/", "wheelhouse/",
    "ax_snapshots/", "dom_snapshots/", "traces/", "trace/",
    "screenshots/", "screenshot/", "videos/", "video/", "downloads/",
    "diagnostic/", "readiness/", "completeness/",
    ".testforge/", ".testforge-patch-run/", ".planning/",
)

# Qualquer segmento do caminho que case aqui elimina o arquivo.
EXCLUDED_SEGMENTS = re.compile(
    r"(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|\.nox"
    r"|\.idea|\.vscode|\.ralphy-worktrees|\.ralphy-sandboxes)(/|$)"
)

# Ruido de alto volume e baixo valor para a LLM.
EXCLUDED_GLOBS = (
    "*snapshot*.txt", "snapshot_*.txt", "*_snapshot.txt", "todas_gravacoes.txt",
    "*.log", "*.lock", "package-lock.json", "poetry.lock", "uv.lock",
    "*.bak-*", "*.orig", "*.rej", "*.min.js", "*.min.css", "*.map",
    "steps.jsonl", "raw_events.jsonl", "rrweb_events.jsonl",
    "keystroke_buffer.jsonl", "field_snapshots.jsonl", "value_mutations.jsonl",
    "suggested_assertions.jsonl", "network_log.json", "healing-catalog.jsonl",
    "apply_report_*.json", "*-apply-report.json",
)

SNAPSHOT_BEGIN = "===== FILE: "
SNAPSHOT_END = "===== END FILE: "
MANIFEST_BEGIN = "===== SNAPSHOT MANIFEST JSON ====="
MANIFEST_END = "===== END SNAPSHOT MANIFEST JSON ====="


class TfError(Exception):
    """Erro de uso ou de validacao. Sempre com mensagem acionavel."""


# --------------------------------------------------------------------------- #
# Log
# --------------------------------------------------------------------------- #


class Log:
    """Log duplo: humano no console/arquivo e estruturado em JSONL.

    O JSONL existe para que uma falha de instalacao ou de envio possa ser
    diagnosticada depois sem depender de alguem ter copiado o terminal.
    """

    def __init__(self, run_dir: Path, quiet: bool = False):
        self.run_dir = run_dir
        self.quiet = quiet
        run_dir.mkdir(parents=True, exist_ok=True)
        self.text_path = run_dir / "tf.log"
        self.jsonl_path = run_dir / "tf.jsonl"
        self._text = self.text_path.open("a", encoding="utf-8", newline="\n")
        self._jsonl = self.jsonl_path.open("a", encoding="utf-8", newline="\n")

    def _write(self, level: str, event: str, message: str, console: bool = True, **fields: Any) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        line = f"{stamp} [{level:<5}] {message}"
        self._text.write(line + "\n")
        self._text.flush()
        record = {"ts": stamp, "level": level, "event": event, "message": message}
        record.update(fields)
        self._jsonl.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._jsonl.flush()
        if not self.quiet and console:
            prefix = {"INFO": "", "OK": "[OK] ", "WARN": "[AVISO] ", "ERROR": "[ERRO] "}.get(level, "")
            print(prefix + message, file=sys.stderr if level == "ERROR" else sys.stdout)

    def info(self, event: str, message: str, console: bool = True, **f: Any) -> None:
        self._write("INFO", event, message, console=console, **f)

    def ok(self, event: str, message: str, **f: Any) -> None:
        self._write("OK", event, message, **f)

    def warn(self, event: str, message: str, **f: Any) -> None:
        self._write("WARN", event, message, **f)

    def error(self, event: str, message: str, **f: Any) -> None:
        self._write("ERROR", event, message, **f)

    def step(self, title: str) -> None:
        if not self.quiet:
            print("\n=== " + title + " ===")
        self._write("INFO", "step", title)

    def close(self) -> None:
        self._text.close()
        self._jsonl.close()


# --------------------------------------------------------------------------- #
# Git
# --------------------------------------------------------------------------- #


@dataclass
class RunResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def out(self) -> str:
        return self.stdout.strip()


class Git:
    def __init__(self, root: Path, log: Log):
        self.root = root
        self.log = log
        self.exe = shutil.which("git") or "git"

    def run(self, *args: str, check: bool = False) -> RunResult:
        command = [self.exe, "-C", str(self.root), *args]
        try:
            proc = subprocess.run(
                command, capture_output=True, text=True,
                encoding="utf-8", errors="replace", check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise TfError("Git nao encontrado no PATH. Use --no-git para o modo sem Git.") from exc
        result = RunResult(command, proc.returncode, proc.stdout or "", proc.stderr or "")
        self.log.info(
            "git",
            "git " + " ".join(args) + " -> rc=" + str(result.returncode),
            console=False,
            rc=result.returncode,
            stdout=result.stdout[-2000:],
            stderr=result.stderr[-2000:],
        )
        if check and not result.ok:
            raise TfError(
                "Comando Git falhou (rc=" + str(result.returncode) + "): git "
                + " ".join(args) + "\n" + (result.stderr or result.stdout).strip()
            )
        return result

    @property
    def available(self) -> bool:
        return self.run("rev-parse", "--is-inside-work-tree").ok

    def head(self) -> str:
        return self.run("rev-parse", "HEAD", check=True).out

    def branch(self) -> str:
        return self.run("branch", "--show-current").out

    def dirty(self) -> list[str]:
        return [line for line in self.run("status", "--porcelain").stdout.splitlines() if line.strip()]

    def tracked_files(self) -> list[str]:
        cached = self.run("ls-files", "--cached", check=True).stdout.splitlines()
        others = self.run("ls-files", "--others", "--exclude-standard", check=True).stdout.splitlines()
        return sorted({line.strip() for line in cached + others if line.strip()})


# --------------------------------------------------------------------------- #
# Snapshot
# --------------------------------------------------------------------------- #


def _is_binary(path: Path) -> bool:
    try:
        return b"\0" in path.read_bytes()[:8192]
    except OSError:
        return True


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _relevant(rel: str) -> tuple[bool, str]:
    """Decide se um caminho relativo entra no snapshot. Retorna (entra, motivo)."""
    lowered = rel.lower()
    for prefix in EXCLUDED_DIR_PREFIXES:
        if lowered.startswith(prefix) or ("/" + prefix) in ("/" + lowered):
            return False, "diretorio_excluido"
    if EXCLUDED_SEGMENTS.search(rel):
        return False, "segmento_excluido"
    name = rel.rsplit("/", 1)[-1]
    for pattern in EXCLUDED_GLOBS:
        if fnmatch.fnmatch(name, pattern):
            return False, "ruido"
    if name in CODE_FILENAMES:
        return True, ""
    suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if suffix in CODE_EXTENSIONS:
        return True, ""
    return False, "extensao_nao_suportada"


def _outline_python(text: str) -> str:
    """Resumo estrutural de um .py grande: assinaturas em vez do corpo inteiro.

    Serve para caber arquivos como recording_normalizer.py (3.4k linhas) no
    contexto sem perder o mapa das APIs que a LLM precisa conhecer.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "# [outline indisponivel: arquivo com erro de sintaxe]"
    lines: list[str] = ["# [OUTLINE — corpo omitido por limite de tamanho]"]
    doc = ast.get_docstring(tree)
    if doc:
        lines.append('"""' + doc.strip().splitlines()[0] + '"""')

    def emit(node: ast.AST, indent: str = "") -> None:
        for child in getattr(node, "body", []):
            if isinstance(child, (ast.Import, ast.ImportFrom)) and not indent:
                lines.append(indent + ast.unparse(child))
            elif isinstance(child, ast.ClassDef):
                lines.append(indent + "class " + child.name + ":")
                emit(child, indent + "    ")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def " if isinstance(child, ast.AsyncFunctionDef) else "def "
                try:
                    signature = prefix + child.name + "(" + ast.unparse(child.args) + ")"
                except Exception:
                    signature = prefix + child.name + "(...)"
                body_doc = ast.get_docstring(child)
                lines.append(indent + signature + ":")
                if body_doc:
                    lines.append(indent + '    """' + body_doc.strip().splitlines()[0] + '"""')
                lines.append(indent + "    ...")
            elif isinstance(child, ast.Assign) and not indent:
                targets = [t.id for t in child.targets if isinstance(t, ast.Name)]
                if targets and targets[0].isupper():
                    lines.append(indent + targets[0] + " = ...")

    emit(tree)
    return "\n".join(lines)


@dataclass
class SnapshotOptions:
    root: Path
    max_file_kb: int = 256
    max_total_mb: int = 8
    outline_over_kb: int = 96
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    use_git: bool = True


def _candidate_files(options: SnapshotOptions, git: Git, log: Log) -> list[str]:
    if options.use_git and git.available:
        files = git.tracked_files()
        log.info("snapshot", "fonte de arquivos: git ls-files (" + str(len(files)) + " candidatos)")
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk(options.root):
            here = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not d.startswith(".") or d in {".github"}]
            for filename in filenames:
                rel = (here / filename).relative_to(options.root).as_posix()
                files.append(rel)
        files.sort()
        log.info("snapshot", "fonte de arquivos: varredura do disco (" + str(len(files)) + " candidatos)")
    return files


def build_snapshot(options: SnapshotOptions, git: Git, log: Log, title: str = "",
                   candidates: list[str] | None = None) -> tuple[str, dict]:
    max_file = options.max_file_kb * 1024
    max_total = options.max_total_mb * 1024 * 1024
    outline_over = options.outline_over_kb * 1024

    skipped: dict[str, int] = {}
    included: list[dict] = []
    outlined: list[str] = []
    total = 0

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    body: list[str] = []
    for rel in (candidates if candidates is not None else _candidate_files(options, git, log)):
        if options.paths and not any(
            rel == p or rel.startswith(p.rstrip("/") + "/") for p in options.paths
        ):
            continue
        if options.exclude and any(fnmatch.fnmatch(rel, g) for g in options.exclude):
            skip("excluido_pelo_usuario")
            continue
        if options.include and not any(fnmatch.fnmatch(rel, g) for g in options.include):
            continue
        keep, reason = _relevant(rel)
        if not keep:
            skip(reason)
            continue
        path = options.root / rel
        if not path.is_file():
            skip("ausente")
            continue
        size = path.stat().st_size
        if _is_binary(path):
            skip("binario")
            continue
        if size > max_file:
            skip("acima_do_limite_por_arquivo")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skip("erro_de_leitura")
            continue
        mode = "full"
        if size > outline_over and rel.endswith(".py"):
            text = _outline_python(text)
            mode = "outline"
            outlined.append(rel)
        payload = len(text.encode("utf-8"))
        if total + payload > max_total:
            skip("acima_do_limite_total")
            continue
        total += payload
        digest = _sha256_text(text)
        included.append({"file": rel, "sha256": digest, "bytes": payload, "mode": mode})
        body.append(SNAPSHOT_BEGIN + rel + " =====")
        body.append("# sha256: " + digest)
        if mode == "outline":
            body.append("# mode: outline (arquivo grande — apenas assinaturas)")
        body.append("")
        body.append(text if text.endswith("\n") else text + "\n")
        body.append(SNAPSHOT_END + rel + " =====")
        body.append("")

    manifest = {
        "schema_version": SNAPSHOT_SCHEMA,
        "tool": "tf",
        "tool_version": TOOL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(options.root),
        "title": title,
        "git": {
            "branch": git.branch() if git.available else "",
            "commit": git.head() if git.available else "",
            "dirty": git.dirty() if git.available else [],
        },
        "limits": {
            "max_file_kb": options.max_file_kb,
            "max_total_mb": options.max_total_mb,
            "outline_over_kb": options.outline_over_kb,
        },
        "filters": {"paths": options.paths, "include": options.include, "exclude": options.exclude},
        "included_count": len(included),
        "included_bytes": total,
        "outlined_files": outlined,
        "skipped": skipped,
        "included_files": included,
    }

    header = [
        "# TestForge snapshot (tf " + TOOL_VERSION + ")",
        "# title: " + (title or "projeto completo"),
        "# generated_at: " + manifest["generated_at"],
        "# branch: " + manifest["git"]["branch"],
        "# commit: " + manifest["git"]["commit"],
        "# files: " + str(len(included)) + "  bytes: " + str(total),
        "# ATENCAO: arquivos marcados 'mode: outline' tiveram o corpo omitido.",
        "",
    ]
    tail = [MANIFEST_BEGIN, json.dumps(manifest, ensure_ascii=False, indent=2), MANIFEST_END, ""]
    return "\n".join(header + body + tail), manifest


def _group_key(rel: str, depth: int) -> str:
    parts = rel.split("/")
    if len(parts) == 1:
        return "_raiz"
    # src/<pacote>/<modulo>/... agrupa por <modulo>, que e o que interessa.
    if parts[0] == "src" and len(parts) > 2:
        parts = parts[2:]
        if len(parts) == 1:
            return "src_raiz"
        return "src_" + "_".join(parts[:depth])
    return "_".join(parts[:depth])


def cmd_snapshot(args: argparse.Namespace, ctx: "Context") -> int:
    options = SnapshotOptions(
        root=ctx.root,
        max_file_kb=args.max_file_kb,
        max_total_mb=args.max_total_mb,
        outline_over_kb=args.outline_over_kb,
        include=args.include or [],
        exclude=args.exclude or [],
        paths=[p.replace("\\", "/").strip("/") for p in (args.path or [])],
        use_git=not args.no_git,
    )
    out = Path(args.out)
    if not out.is_absolute():
        out = ctx.root / out

    if not args.by_module:
        text, manifest = build_snapshot(options, ctx.git, ctx.log, title=args.title or "")
        if out.suffix == "":
            out.mkdir(parents=True, exist_ok=True)
            out = out / ("snapshot_" + time.strftime("%Y%m%d-%H%M%S") + ".txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        ctx.log.ok("snapshot", "Snapshot: " + str(out))
        _report_snapshot(ctx.log, manifest, out)
        return 0

    # Modo por modulo: um arquivo por grupo + index.json
    out.mkdir(parents=True, exist_ok=True)
    candidates = _candidate_files(options, ctx.git, ctx.log)
    all_files = [
        rel for rel in candidates
        if _relevant(rel)[0]
        and (not options.paths or any(rel == p or rel.startswith(p + "/") for p in options.paths))
    ]
    groups: dict[str, list[str]] = {}
    for rel in all_files:
        groups.setdefault(_group_key(rel, args.group_depth), []).append(rel)

    index: dict[str, Any] = {
        "tool_version": TOOL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "group_depth": args.group_depth,
        "modules": [],
    }
    for group, members in sorted(groups.items()):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", group).strip("._-") or "_raiz"
        module_options = SnapshotOptions(
            root=options.root,
            max_file_kb=options.max_file_kb,
            max_total_mb=options.max_total_mb,
            outline_over_kb=options.outline_over_kb,
            include=[],
            exclude=options.exclude,
            paths=[],
            use_git=options.use_git,
        )
        text, manifest = build_snapshot(module_options, ctx.git, ctx.log, title=group,
                                        candidates=members)
        target = out / (safe + "_snapshot.txt")
        target.write_text(text, encoding="utf-8", newline="\n")
        index["modules"].append({
            "module": group,
            "snapshot": target.name,
            "files": manifest["included_count"],
            "bytes": manifest["included_bytes"],
            "outlined": manifest["outlined_files"],
        })
        ctx.log.ok("snapshot", (
            group.ljust(28) + " -> " + target.name
            + "  (" + str(manifest["included_count"]) + " arq, "
            + str(round(manifest["included_bytes"] / 1024)) + " KB)"
        ))
    (out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    total_bytes = sum(m["bytes"] for m in index["modules"])
    ctx.log.ok("snapshot", (
        "Modulos: " + str(len(index["modules"]))
        + " | total " + str(round(total_bytes / 1024 / 1024, 2)) + " MB | indice: "
        + str(out / "index.json")
    ))
    return 0


def _report_snapshot(log: Log, manifest: dict, out: Path) -> None:
    log.ok("snapshot", "Arquivos incluidos: " + str(manifest["included_count"]))
    log.ok("snapshot", "Conteudo: " + str(round(manifest["included_bytes"] / 1024 / 1024, 2)) + " MB")
    if manifest["outlined_files"]:
        log.warn("snapshot", (
            "Resumidos por tamanho (" + str(len(manifest["outlined_files"])) + "): "
            + ", ".join(manifest["outlined_files"][:5])
            + ("..." if len(manifest["outlined_files"]) > 5 else "")
        ))
    for reason, count in sorted(manifest["skipped"].items(), key=lambda kv: -kv[1]):
        log.info("snapshot", "  ignorados por " + reason + ": " + str(count))
    log.info("snapshot", "Log detalhado: " + str(log.text_path))


# --------------------------------------------------------------------------- #
# Patches
# --------------------------------------------------------------------------- #


def _safe_target(root: Path, rel: str) -> Path:
    if not rel or not isinstance(rel, str):
        raise TfError("Campo 'file' ausente ou invalido no patch.")
    candidate = Path(rel.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise TfError("Caminho invalido no patch (absoluto ou com '..'): " + rel)
    target = (root / candidate).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise TfError("Patch tenta escrever fora do repositorio: " + rel)
    return target


def _replace_symbol(source: str, new_code: str, name: str, kind: str, in_class: str | None) -> str:
    wanted = (ast.FunctionDef, ast.AsyncFunctionDef) if kind == "function" else (ast.ClassDef,)
    tree = ast.parse(source)
    node = None
    if in_class:
        for candidate in ast.walk(tree):
            if isinstance(candidate, ast.ClassDef) and candidate.name == in_class:
                for child in candidate.body:
                    if isinstance(child, wanted) and child.name == name:
                        node = child
    else:
        matches = [n for n in tree.body if isinstance(n, wanted) and n.name == name]
        if len(matches) > 1:
            raise TfError("Simbolo ambiguo: " + name + ". Informe 'in_class'.")
        node = matches[0] if matches else None
        if node is None:
            deep = [n for n in ast.walk(tree) if isinstance(n, wanted) and getattr(n, "name", "") == name]
            if len(deep) == 1:
                node = deep[0]
    if node is None:
        raise TfError("Simbolo nao encontrado: " + kind + " " + name)

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    indent = re.match(r"\s*", lines[start]).group(0)
    code = new_code.strip("\n") + "\n"
    if indent and not re.match(r"\s", code.splitlines()[0]):
        code = "".join(indent + ln if ln.strip() else ln for ln in code.splitlines(True))
    return "".join(lines[:start]) + code + "".join(lines[node.end_lineno:])


@dataclass
class ChangeOutcome:
    index: int
    type: str
    file: str
    status: str
    detail: str = ""
    before_sha256: str | None = None
    after_sha256: str | None = None


def apply_change(root: Path, change: dict, index: int, do_apply: bool,
                 overlay: dict[str, str | None] | None = None) -> ChangeOutcome:
    ctype = str(change.get("type", "")).strip()
    rel = str(change.get("file", ""))
    target = _safe_target(root, rel)
    overlay = overlay if overlay is not None else {}
    key = str(target)
    if key in overlay:
        before = overlay[key]
        exists = before is not None
    else:
        exists = target.is_file()
        before = target.read_text(encoding="utf-8", errors="replace") if exists else None
    before_sha = _sha256_text(before) if before is not None else None

    expected = change.get("expected_sha256")
    if expected and before_sha and expected != before_sha:
        raise TfError(
            "SHA divergente em " + rel + ". Esperado " + str(expected) + ", atual " + str(before_sha)
            + ". Gere um snapshot novo antes de reconstruir o patch."
        )

    if ctype == "delete_file":
        if not exists:
            raise TfError("delete_file: arquivo ausente: " + rel)
        if do_apply:
            target.unlink()
        overlay[key] = None
        return ChangeOutcome(index, ctype, rel, "applied" if do_apply else "checked",
                             "arquivo removido", before_sha, None)

    if ctype in {"create_file", "add_file", "replace_file"}:
        content = change.get("content")
        if not isinstance(content, str):
            raise TfError(ctype + " exige 'content' (string): " + rel)
        if ctype == "create_file" and exists and not change.get("overwrite", False):
            raise TfError("create_file: arquivo ja existe: " + rel + ". Use overwrite=true ou replace_file.")
        after = content if content.endswith("\n") or not content else content + "\n"
    elif ctype == "append_to_file":
        if not exists:
            raise TfError("append_to_file: arquivo ausente: " + rel)
        content = str(change.get("content", ""))
        separator = "" if (before or "").endswith("\n") or not before else "\n"
        after = (before or "") + separator + content
        if not after.endswith("\n"):
            after += "\n"
    elif ctype == "text_replace":
        if not exists:
            raise TfError("text_replace: arquivo ausente: " + rel)
        old = change.get("old")
        new = change.get("new")
        if not isinstance(old, str) or not old:
            raise TfError("text_replace exige 'old' nao vazio: " + rel)
        if not isinstance(new, str):
            raise TfError("text_replace exige 'new': " + rel)
        wanted = int(change.get("count", 1))
        found = (before or "").count(old)
        if found != wanted:
            raise TfError(
                "text_replace em " + rel + ": encontradas " + str(found)
                + " ocorrencias, esperadas " + str(wanted)
                + ". A base mudou ou a ancora esta ambigua."
            )
        for anchor in change.get("must_contain", []) or []:
            if str(anchor) not in (before or ""):
                raise TfError("text_replace em " + rel + ": ancora obrigatoria ausente: " + str(anchor))
        after = (before or "").replace(old, new)
    elif ctype == "regex_replace":
        if not exists:
            raise TfError("regex_replace: arquivo ausente: " + rel)
        pattern = change.get("pattern")
        replacement = change.get("replacement")
        if not isinstance(pattern, str) or not isinstance(replacement, str):
            raise TfError("regex_replace exige 'pattern' e 'replacement': " + rel)
        flags = re.S if change.get("dotall", True) else 0
        after, count = re.subn(pattern, replacement, before or "", count=int(change.get("count", 1)), flags=flags)
        if count == 0:
            raise TfError("regex_replace: padrao nao encontrado em " + rel + ". A base mudou.")
    elif ctype in {"replace_function", "replace_class"}:
        if not exists:
            raise TfError(ctype + ": arquivo ausente: " + rel)
        name = change.get("name") or change.get("function") or change.get("class")
        content = change.get("content")
        if not name or not isinstance(content, str) or not content.strip():
            raise TfError(ctype + " exige 'name' e 'content': " + rel)
        kind = "function" if ctype == "replace_function" else "class"
        after = _replace_symbol(before or "", content, str(name), kind, change.get("in_class"))
    else:
        raise TfError("Tipo de mudanca nao suportado: " + repr(ctype) + " (arquivo " + rel + ")")

    after_sha = _sha256_text(after)
    if before_sha == after_sha:
        raise TfError("Mudanca " + str(index) + " nao alterou " + rel + ". Patch provavelmente ja aplicado.")

    overlay[key] = after
    if do_apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(after, encoding="utf-8", newline="")

    if after.strip() and rel.endswith(".py"):
        try:
            ast.parse(after)
        except SyntaxError as exc:
            raise TfError("Resultado nao e Python valido em " + rel + ": " + str(exc)) from exc

    return ChangeOutcome(index, ctype, rel, "applied" if do_apply else "checked",
                         "ok", before_sha, after_sha)


def load_patch(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TfError("Nao foi possivel ler o patch " + str(path) + ": " + str(exc)) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Tolera JSON colado dentro de cerca de codigo. Tentado SO depois de
        # falhar: o proprio conteudo dos patches contem cercas, e strippa-las
        # antes destruiria patches validos.
        fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.S | re.I)
        if not fenced:
            raise TfError("JSON invalido em " + str(path) + ". Verifique virgulas e aspas.")
        try:
            data = json.loads(fenced.group(1))
        except json.JSONDecodeError as exc:
            raise TfError("JSON invalido em " + str(path) + ": " + str(exc)) from exc
    if not isinstance(data, dict) or not isinstance(data.get("changes"), list):
        raise TfError("Patch " + str(path) + " precisa ter a chave 'changes' com uma lista.")
    return data


def process_patch(root: Path, path: Path, do_apply: bool, log: Log) -> list[ChangeOutcome]:
    patch = load_patch(path)
    outcomes: list[ChangeOutcome] = []
    overlay: dict[str, str | None] = {}
    for index, change in enumerate(patch["changes"], start=1):
        outcome = apply_change(root, change, index, do_apply, overlay)
        outcomes.append(outcome)
        log.info(
            "patch",
            "  " + str(index) + ": " + outcome.type + " -> " + outcome.file + " (" + outcome.status + ")",
            patch=path.name, change=index, file=outcome.file, type=outcome.type,
        )
    return outcomes


# --------------------------------------------------------------------------- #
# Manifesto e fluxo
# --------------------------------------------------------------------------- #


@dataclass
class Step:
    id: str
    name: str
    patch: str | None
    commit: str
    tests: list[list[str]]
    depends_on: list[str]


def load_manifest(path: Path) -> list[Step]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TfError("Manifesto invalido: " + str(exc)) from exc
    entries = data.get("steps") or data.get("increments")
    if not isinstance(entries, list) or not entries:
        raise TfError("Manifesto sem 'steps' (ou 'increments').")
    steps: list[Step] = []
    for raw in entries:
        if not raw.get("enabled", True):
            continue
        identifier = str(raw.get("id") or raw.get("patch") or "").strip()
        if not identifier:
            raise TfError("Passo sem 'id' no manifesto.")
        tests_raw = raw.get("tests") or []
        tests: list[list[str]] = []
        for item in tests_raw:
            if isinstance(item, dict) and item.get("cmd"):
                tests.append(["@cmd", *[str(a) for a in item["cmd"]]])
            elif isinstance(item, dict):
                tests.append([str(a) for a in item.get("args", [])])
            elif isinstance(item, list):
                tests.append([str(a) for a in item])
            elif isinstance(item, str):
                tests.append(item.split())
        steps.append(Step(
            id=identifier,
            name=str(raw.get("name") or raw.get("gate") or identifier),
            patch=raw.get("patch"),
            commit=str(raw.get("commit") or (identifier + ": " + str(raw.get("name") or "incremento"))),
            tests=tests,
            depends_on=[str(d) for d in raw.get("depends_on", [])],
        ))
    seen: set[str] = set()
    for step in steps:
        for dependency in step.depends_on:
            if dependency not in seen:
                raise TfError("Passo " + step.id + " depende de " + dependency + ", que nao vem antes dele.")
        seen.add(step.id)
    return steps


class State:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {"schema_version": 2, "completed": [], "baselines": {}, "history": []}
        if path.is_file():
            try:
                self.data.update(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    @property
    def completed(self) -> list[str]:
        return list(self.data.get("completed", []))

    def record(self, step: Step, baseline: str, result_commit: str) -> None:
        self.data.setdefault("baselines", {})[step.id] = baseline
        completed = self.data.setdefault("completed", [])
        if step.id not in completed:
            completed.append(step.id)
        self.data.setdefault("history", []).append({
            "id": step.id, "baseline": baseline, "commit": result_commit,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self.save()


def _run_tests(ctx: "Context", step: Step) -> None:
    for argv in step.tests:
        if argv and argv[0] == "@cmd":
            command = [sys.executable, *argv[1:]]
        else:
            command = [sys.executable, "-m", "pytest", *argv]
        ctx.log.info("test", "> " + " ".join(command))
        proc = subprocess.run(command, cwd=str(ctx.root), text=True, encoding="utf-8",
                              errors="replace", capture_output=True, check=False)
        (ctx.run_dir / (step.id + "-tests.log")).write_text(
            (proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8", newline="\n"
        )
        tail = "\n".join((proc.stdout or "").strip().splitlines()[-12:])
        ctx.log.info("test", tail)
        if proc.returncode != 0:
            raise TfError(
                "Gate de testes falhou no passo " + step.id + " (rc=" + str(proc.returncode)
                + "). Log completo: " + str(ctx.run_dir / (step.id + "-tests.log"))
            )


def cmd_check(args: argparse.Namespace, ctx: "Context") -> int:
    targets: list[Path] = []
    if args.patch:
        targets = [Path(p) if Path(p).is_absolute() else ctx.root / p for p in args.patch]
    else:
        manifest_path = _resolve(ctx.root, args.manifest)
        base = manifest_path.parent
        for step in load_manifest(manifest_path):
            if step.patch:
                targets.append(_resolve(base, step.patch))
    failures = 0
    for path in targets:
        ctx.log.step("check " + path.name)
        try:
            process_patch(ctx.root, path, do_apply=False, log=ctx.log)
            ctx.log.ok("check", "patch valido: " + path.name)
        except TfError as exc:
            failures += 1
            ctx.log.error("check", str(exc), patch=path.name)
    if failures:
        ctx.log.error("check", str(failures) + " patch(es) reprovado(s).")
        return 1
    ctx.log.ok("check", "Todos os patches passaram na validacao: " + str(len(targets)))
    return 0


def cmd_apply(args: argparse.Namespace, ctx: "Context") -> int:
    manifest_path = _resolve(ctx.root, args.manifest)
    base = manifest_path.parent
    steps = load_manifest(manifest_path)
    state = State(ctx.root / STATE_DIR / "state.json")

    if args.only:
        steps = [s for s in steps if s.id in set(args.only)]
    if args.start_at:
        identifiers = [s.id for s in steps]
        if args.start_at not in identifiers:
            raise TfError("Passo inicial desconhecido: " + args.start_at)
        steps = steps[identifiers.index(args.start_at):]
    if args.stop_at:
        identifiers = [s.id for s in steps]
        if args.stop_at not in identifiers:
            raise TfError("Passo final desconhecido: " + args.stop_at)
        steps = steps[: identifiers.index(args.stop_at) + 1]

    use_git = ctx.git.available and not args.no_git
    if not use_git:
        ctx.log.warn("apply", "Sem Git: nao havera commit nem rollback automatico. Backups em " + str(ctx.run_dir / "backup"))
    else:
        dirty = ctx.git.dirty()
        if dirty and not args.allow_dirty:
            raise TfError(
                "Arvore Git suja (" + str(len(dirty)) + " arquivo(s)). Commite, guarde em stash "
                "ou use --allow-dirty. Primeiros: " + ", ".join(dirty[:5])
            )
        if args.branch:
            current = ctx.git.branch()
            if current != args.branch:
                exists = ctx.git.run("rev-parse", "--verify", args.branch).ok
                ctx.git.run("switch", args.branch, check=True) if exists else \
                    ctx.git.run("switch", "-c", args.branch, check=True)
                ctx.log.ok("apply", "Branch: " + args.branch)

    applied = 0
    for step in steps:
        if args.resume and step.id in state.completed:
            ctx.log.warn("apply", "SKIP " + step.id + " (ja concluido)")
            continue
        ctx.log.step(step.id + " — " + step.name)
        baseline = ctx.git.head() if use_git else ""
        backup_dir = ctx.run_dir / "backup" / step.id
        try:
            if step.patch:
                patch_path = _resolve(base, step.patch)
                process_patch(ctx.root, patch_path, do_apply=False, log=ctx.log)
                ctx.log.ok("apply", "check aprovado: " + patch_path.name)
                if not use_git:
                    _backup_files(ctx.root, load_patch(patch_path), backup_dir)
                if args.dry_run:
                    ctx.log.warn("apply", "--dry-run: nada foi escrito")
                    continue
                outcomes = process_patch(ctx.root, patch_path, do_apply=True, log=ctx.log)
                (ctx.run_dir / (step.id + "-report.json")).write_text(
                    json.dumps({
                        "step": step.id, "patch": patch_path.name, "baseline": baseline,
                        "changes": [o.__dict__ for o in outcomes],
                    }, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
            if args.dry_run:
                continue
            _run_tests(ctx, step)
            result_commit = baseline
            if use_git:
                if ctx.git.dirty():
                    if args.no_commit:
                        ctx.log.warn("apply", "--no-commit: alteracoes deixadas na arvore")
                    else:
                        ctx.git.run("add", "--all", check=True)
                        ctx.git.run("commit", "-m", step.commit, check=True)
                        result_commit = ctx.git.head()
                        ctx.log.ok("apply", "commit " + result_commit[:8] + " — " + step.commit)
                elif step.patch:
                    raise TfError("Passo " + step.id + " nao produziu alteracao alguma.")
                state.record(step, baseline, result_commit)
            applied += 1
            ctx.log.ok("apply", step.id + " concluido")
        except TfError as exc:
            ctx.log.error("apply", "FALHA em " + step.id + ": " + str(exc), step=step.id)
            if args.keep_on_failure:
                ctx.log.warn("apply", "--keep-on-failure: arvore preservada para diagnostico")
            elif use_git and baseline:
                ctx.git.run("reset", "--hard", baseline)
                ctx.git.run("clean", "-fd")
                ctx.log.warn("apply", "rollback automatico para " + baseline[:8])
            elif backup_dir.is_dir():
                _restore_files(ctx.root, backup_dir)
                ctx.log.warn("apply", "rollback por backup de arquivos")
            ctx.log.error("apply", "Diagnostico completo em: " + str(ctx.run_dir))
            return 1
    ctx.log.ok("apply", "Passos concluidos nesta execucao: " + str(applied))
    return 0


def _backup_files(root: Path, patch: dict, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for change in patch.get("changes", []):
        rel = str(change.get("file", ""))
        source = root / rel
        if source.is_file():
            destination = backup_dir / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _restore_files(root: Path, backup_dir: Path) -> None:
    for path in backup_dir.rglob("*"):
        if path.is_file():
            destination = root / path.relative_to(backup_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def cmd_rollback(args: argparse.Namespace, ctx: "Context") -> int:
    if not ctx.git.available:
        raise TfError("rollback automatico exige Git. Restaure manualmente a partir de " + str(ctx.run_dir / "backup"))
    state = State(ctx.root / STATE_DIR / "state.json")
    if args.to_commit:
        target = args.to_commit
        label = "commit " + target[:8]
    else:
        if not args.to:
            raise TfError("Informe --to <ID do passo> ou --to-commit <sha>.")
        baselines = state.data.get("baselines", {})
        if args.to not in baselines:
            raise TfError(
                "Passo " + args.to + " nao tem baseline registrado. Conhecidos: "
                + (", ".join(baselines) or "nenhum")
            )
        target = baselines[args.to]
        label = "estado anterior ao passo " + args.to + " (" + target[:8] + ")"

    dirty = ctx.git.dirty()
    if dirty and not args.force:
        raise TfError("Arvore suja. Use --force para descartar " + str(len(dirty)) + " alteracao(oes).")
    ctx.log.step("rollback para " + label)
    ctx.git.run("reset", "--hard", target, check=True)
    ctx.git.run("clean", "-fd", check=True)
    if args.to:
        completed = state.data.get("completed", [])
        if args.to in completed:
            state.data["completed"] = completed[: completed.index(args.to)]
            state.save()
    ctx.log.ok("rollback", "Repositorio em " + ctx.git.head()[:8] + " (" + label + ")")
    return 0


def cmd_status(args: argparse.Namespace, ctx: "Context") -> int:
    state = State(ctx.root / STATE_DIR / "state.json")
    print("raiz    : " + str(ctx.root))
    print("git     : " + ("sim" if ctx.git.available else "nao"))
    if ctx.git.available:
        print("branch  : " + ctx.git.branch())
        print("commit  : " + ctx.git.head()[:12])
        dirty = ctx.git.dirty()
        print("arvore  : " + ("limpa" if not dirty else str(len(dirty)) + " alteracao(oes)"))
        for line in dirty[:10]:
            print("          " + line)
    print("passos  : " + (", ".join(state.completed) or "nenhum concluido"))
    runs = sorted((ctx.root / STATE_DIR / "runs").glob("*"), reverse=True) if (ctx.root / STATE_DIR / "runs").is_dir() else []
    print("execucoes: " + str(len(runs)) + (("  ultima: " + runs[0].name) if runs else ""))
    if ctx.git.available:
        print("\nultimos commits:")
        print(ctx.git.run("log", "--oneline", "--decorate", "-10").stdout.rstrip())
    return 0


def cmd_log(args: argparse.Namespace, ctx: "Context") -> int:
    runs_dir = ctx.root / STATE_DIR / "runs"
    if not runs_dir.is_dir():
        raise TfError("Nenhuma execucao registrada em " + str(runs_dir))
    runs = sorted(runs_dir.glob("*"), reverse=True)
    chosen = runs_dir / args.run if args.run else (runs[0] if runs else None)
    if chosen is None or not chosen.is_dir():
        raise TfError("Execucao nao encontrada: " + str(chosen))
    if args.errors:
        path = chosen / "tf.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("level") in {"ERROR", "WARN"}:
                print(record["ts"] + " [" + record["level"] + "] " + record["message"])
                if record.get("stderr"):
                    print("    stderr: " + str(record["stderr"])[:500])
        return 0
    print((chosen / "tf.log").read_text(encoding="utf-8"))
    return 0


# --------------------------------------------------------------------------- #
# Contexto e CLI
# --------------------------------------------------------------------------- #


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path)


def find_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file() or (candidate / ".git").exists():
            return candidate
    return current


@dataclass
class Context:
    root: Path
    log: Log
    git: Git
    run_dir: Path


def _ensure_local_ignore(root: Path, log: Log) -> None:
    """Garante que .tf/ nao suje a arvore Git, sem editar o .gitignore do time."""
    exclude = root / ".git" / "info" / "exclude"
    entry = "/" + STATE_DIR + "/"
    try:
        if not exclude.parent.is_dir():
            return
        current = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        if entry in current.splitlines():
            return
        separator = "" if current.endswith("\n") or not current else "\n"
        exclude.write_text(current + separator + entry + "\n", encoding="utf-8", newline="\n")
        log.info("setup", "adicionado " + entry + " a .git/info/exclude", console=False)
    except OSError as exc:
        log.warn("setup", "nao foi possivel atualizar .git/info/exclude: " + str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tf",
        description="Snapshot, patches, commits, rollback e log — em um unico script multiplataforma.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Exemplos")[-1],
    )
    parser.add_argument("--root", default="", help="Raiz do projeto (padrao: detecta pyproject.toml/.git)")
    parser.add_argument("--quiet", action="store_true", help="Somente arquivos de log, sem saida no console")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Gera snapshot textual de codigo e configuracao")
    snap.add_argument("--out", default="snapshots", help="Arquivo .txt ou pasta (padrao: snapshots/)")
    snap.add_argument("--by-module", action="store_true", help="Um arquivo por modulo + index.json")
    snap.add_argument("--group-depth", type=int, default=1, help="Profundidade do agrupamento por modulo")
    snap.add_argument("--path", action="append", help="Limita a uma pasta. Pode repetir.")
    snap.add_argument("--include", action="append", help="Glob de inclusao. Pode repetir.")
    snap.add_argument("--exclude", action="append", help="Glob de exclusao. Pode repetir.")
    snap.add_argument("--max-file-kb", type=int, default=256, help="Limite por arquivo (padrao: 256 KB)")
    snap.add_argument("--max-total-mb", type=int, default=8, help="Limite total (padrao: 8 MB)")
    snap.add_argument("--outline-over-kb", type=int, default=96,
                      help="Acima disso, .py entra como assinaturas em vez do corpo (padrao: 96 KB)")
    snap.add_argument("--no-git", action="store_true", help="Varre o disco em vez de usar git ls-files")
    snap.add_argument("--title", default="", help="Rotulo gravado no cabecalho")
    snap.set_defaults(func=cmd_snapshot)

    check = sub.add_parser("check", help="Valida patches sem escrever nada")
    check.add_argument("--manifest", default="patch-manifest.json")
    check.add_argument("--patch", action="append", help="Valida patches avulsos. Pode repetir.")
    check.set_defaults(func=cmd_check)

    apply_cmd = sub.add_parser("apply", help="Aplica patches, roda gates e commita entre eles")
    apply_cmd.add_argument("--manifest", default="patch-manifest.json")
    apply_cmd.add_argument("--branch", default="", help="Garante/cria a branch antes de aplicar")
    apply_cmd.add_argument("--only", action="append", help="Aplica apenas estes IDs")
    apply_cmd.add_argument("--start-at", default="", help="Comeca neste ID")
    apply_cmd.add_argument("--stop-at", default="", help="Para neste ID (inclusive)")
    apply_cmd.add_argument("--resume", action="store_true", help="Pula passos ja concluidos")
    apply_cmd.add_argument("--dry-run", action="store_true", help="So valida, nao escreve")
    apply_cmd.add_argument("--no-commit", action="store_true", help="Aplica sem commitar")
    apply_cmd.add_argument("--no-git", action="store_true", help="Modo sem Git, com backup de arquivos")
    apply_cmd.add_argument("--allow-dirty", action="store_true", help="Permite arvore suja")
    apply_cmd.add_argument("--keep-on-failure", action="store_true", help="Nao desfaz em caso de falha")
    apply_cmd.set_defaults(func=cmd_apply)

    rollback = sub.add_parser("rollback", help="Volta ao estado anterior a um passo")
    rollback.add_argument("--to", default="", help="ID do passo")
    rollback.add_argument("--to-commit", default="", help="SHA especifico")
    rollback.add_argument("--force", action="store_true", help="Descarta alteracoes locais")
    rollback.set_defaults(func=cmd_rollback)

    status = sub.add_parser("status", help="Estado do fluxo e do repositorio")
    status.set_defaults(func=cmd_status)

    log_cmd = sub.add_parser("log", help="Mostra o log da execucao")
    log_cmd.add_argument("--run", default="", help="Nome da execucao (padrao: a ultima)")
    log_cmd.add_argument("--errors", action="store_true", help="So avisos e erros")
    log_cmd.set_defaults(func=cmd_log)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    if not root.is_dir():
        print("[ERRO] Raiz inexistente: " + str(root), file=sys.stderr)
        return 2

    run_dir = root / STATE_DIR / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-" + args.command)
    log = Log(run_dir, quiet=args.quiet)
    ctx = Context(root=root, log=log, git=Git(root, log), run_dir=run_dir)
    _ensure_local_ignore(root, log)
    log.info("start", "tf " + TOOL_VERSION + " | comando=" + args.command + " | raiz=" + str(root),
             argv=list(argv or sys.argv[1:]), python=sys.version.split()[0], platform=sys.platform)
    try:
        code = args.func(args, ctx)
    except TfError as exc:
        log.error("fatal", str(exc))
        log.error("fatal", "Log desta execucao: " + str(run_dir / "tf.log"))
        code = 1
    except KeyboardInterrupt:
        log.error("fatal", "Interrompido pelo usuario.")
        code = 130
    except Exception as exc:  # noqa: BLE001 — falha inesperada tambem precisa virar log
        import traceback

        log.error("fatal", "Erro inesperado: " + type(exc).__name__ + ": " + str(exc))
        (run_dir / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        log.error("fatal", "Traceback completo: " + str(run_dir / "traceback.txt"))
        code = 1
    finally:
        log.info("end", "fim | rc=" + str(locals().get("code", 1)))
        log.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())

