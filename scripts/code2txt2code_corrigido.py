
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
code2txt2code.py — snapshot de código + aplicador semântico local.

Objetivo:
  1) Exportar um snapshot textual do projeto para ser enviado a uma LLM externa.
  2) Aplicar localmente um arquivo JSON de mudanças semânticas devolvido pela LLM.

Sem dependências externas. Usa apenas biblioteca padrão do Python.

Exemplos:
  # Exportar snapshot único
  python scripts/code2txt2code.py --snapshot --src . --output testforge_snapshot.txt

  # Exportar snapshots separados por módulo/diretório de topo
  python scripts/code2txt2code.py --snapshot --snapshot-by-module --src . --output snapshots

  # Validar mudanças sem aplicar
  python scripts/code2txt2code.py --input semantic_changes.json --src . --check

  # Aplicar mudanças
  python scripts/code2txt2code.py --input semantic_changes.json --src . --apply

  # Aplicar, validar py_compile e gerar relatório
  python scripts/code2txt2code.py --input semantic_changes.json --src . --apply --compile --report apply_report.json
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import py_compile
import re
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
    "dist", "build", ".idea", ".vscode", "htmlcov", ".tox",
}

DEFAULT_INCLUDE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".md", ".txt", ".bat", ".ps1", ".sh",
    ".html", ".css", ".scss", ".xml", ".feature",
}

SNAPSHOT_BEGIN = "===== FILE: "
SNAPSHOT_END = "===== END FILE: "


@dataclass
class ChangeResult:
    file: str
    type: str
    status: str
    message: str
    changed: bool = False
    backup: str | None = None
    before_sha256: str | None = None
    after_sha256: str | None = None


class Code2Txt2CodeError(Exception):
    pass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_binary(path: Path) -> bool:
    try:
        data = path.read_bytes()[:4096]
    except Exception:
        return True
    return b"\0" in data


def normalize_rel_path(raw: str) -> Path:
    if not raw or not isinstance(raw, str):
        raise Code2Txt2CodeError("Campo 'file' inválido ou ausente.")
    p = Path(raw.replace("\\", "/"))
    if p.is_absolute():
        raise Code2Txt2CodeError(f"Caminho absoluto não permitido: {raw}")
    if ".." in p.parts:
        raise Code2Txt2CodeError(f"Caminho com '..' não permitido: {raw}")
    return p


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def make_backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak-{stamp}")
    shutil.copy2(path, backup)
    return backup


def iter_project_files(
    root: Path,
    include_exts: set[str],
    exclude_dirs: set[str],
    include_globs: list[str],
    exclude_globs: list[str],
    max_file_bytes: int,
) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for filename in filenames:
            path = here / filename
            rel = path.relative_to(root).as_posix()
            if exclude_globs and any(fnmatch.fnmatch(rel, g) for g in exclude_globs):
                continue
            if include_globs and not any(fnmatch.fnmatch(rel, g) for g in include_globs):
                continue
            if path.suffix.lower() not in include_exts:
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            if is_binary(path):
                continue
            yield path


def safe_snapshot_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "_root"


def build_snapshot_text(root: Path, files: list[Path], title: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    parts: list[str] = []
    parts.append("# code2txt2code snapshot\n")
    if title:
        parts.append(f"# module: {title}\n")
    parts.append(f"# generated_at: {datetime.now(timezone.utc).isoformat()}\n")
    parts.append(f"# root_name: {root.name}\n")
    parts.append(f"# file_count: {len(files)}\n\n")

    for path in files:
        rel = path.relative_to(root).as_posix()
        content = read_text(path)
        digest = sha256_text(content)
        manifest.append({"file": rel, "sha256": digest, "bytes": len(content.encode("utf-8"))})
        parts.append(f"{SNAPSHOT_BEGIN}{rel} =====\n")
        parts.append(f"# sha256: {digest}\n")
        parts.append(content)
        if content and not content.endswith("\n"):
            parts.append("\n")
        parts.append(f"{SNAPSHOT_END}{rel} =====\n\n")

    parts.append("===== MANIFEST JSON =====\n")
    parts.append(json.dumps({"files": manifest}, ensure_ascii=False, indent=2))
    parts.append("\n===== END MANIFEST JSON =====\n")
    return "".join(parts), manifest


def module_key_for_path(root: Path, path: Path) -> str:
    rel_parts = path.relative_to(root).parts
    if len(rel_parts) <= 1:
        return "_root"
    return rel_parts[0]


def create_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.src).resolve()
    out = Path(args.output).resolve()
    include_exts = set(DEFAULT_INCLUDE_EXTS)
    if args.ext:
        include_exts = {e if e.startswith(".") else "." + e for e in args.ext.split(",") if e.strip()}
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if args.exclude_dir:
        exclude_dirs.update(x.strip() for x in args.exclude_dir.split(",") if x.strip())

    files = sorted(iter_project_files(
        root=root,
        include_exts=include_exts,
        exclude_dirs=exclude_dirs,
        include_globs=args.include or [],
        exclude_globs=args.exclude or [],
        max_file_bytes=args.max_file_bytes,
    ), key=lambda p: p.relative_to(root).as_posix())

    if args.snapshot_by_module:
        out.mkdir(parents=True, exist_ok=True)
        groups: dict[str, list[Path]] = {}
        for path in files:
            groups.setdefault(module_key_for_path(root, path), []).append(path)

        index: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "root_name": root.name,
            "file_count": len(files),
            "module_count": len(groups),
            "modules": [],
        }
        for module, module_files in sorted(groups.items()):
            filename = f"{safe_snapshot_name(module)}_snapshot.txt"
            target = out / filename
            text, manifest = build_snapshot_text(root, module_files, title=module)
            target.write_text(text, encoding="utf-8", newline="\n")
            index["modules"].append({
                "module": module,
                "snapshot": filename,
                "file_count": len(module_files),
                "files": manifest,
            })

        index_path = out / "index.json"
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        print(f"[OK] Snapshots por módulo gerados em: {out}")
        print(f"[OK] Módulos: {len(groups)}")
        print(f"[OK] Arquivos incluídos: {len(files)}")
        print(f"[OK] Índice: {index_path}")
        return 0

    text, _manifest = build_snapshot_text(root, files)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] Snapshot gerado: {out}")
    print(f"[OK] Arquivos incluídos: {len(files)}")
    return 0

def load_changes(path: Path) -> dict[str, Any]:
    text = read_text(path).strip()
    # Permite colar JSON dentro de bloco ```json ... ```.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise Code2Txt2CodeError(f"JSON inválido em {path}: {e}") from e
    if not isinstance(data, dict):
        raise Code2Txt2CodeError("Arquivo de mudanças deve ser um objeto JSON.")
    if data.get("version") != 1:
        raise Code2Txt2CodeError("Versão não suportada. Use: {\"version\": 1, \"changes\": [...]}")
    if not isinstance(data.get("changes"), list):
        raise Code2Txt2CodeError("Campo 'changes' deve ser uma lista.")
    return data


def find_symbol_node(tree: ast.AST, name: str, kind: str, in_class: str | None = None) -> ast.AST:
    wanted = (ast.FunctionDef, ast.AsyncFunctionDef) if kind == "function" else (ast.ClassDef,)
    if in_class:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == in_class:
                for child in node.body:
                    if isinstance(child, wanted) and getattr(child, "name", None) == name:
                        return child
        raise Code2Txt2CodeError(f"Símbolo não encontrado: classe {in_class}, {kind} {name}")
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, wanted) and getattr(node, "name", None) == name:
            return node
    # fallback: busca recursiva, mas evita pegar método errado caso não haja in_class.
    matches = [n for n in ast.walk(tree) if isinstance(n, wanted) and getattr(n, "name", None) == name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise Code2Txt2CodeError(f"Símbolo não encontrado: {kind} {name}")
    raise Code2Txt2CodeError(f"Símbolo ambíguo: {kind} {name}. Informe 'in_class'.")


def replace_ast_symbol(original: str, new_code: str, name: str, kind: str, in_class: str | None = None) -> str:
    try:
        tree = ast.parse(original)
    except SyntaxError as e:
        raise Code2Txt2CodeError(f"Arquivo Python inválido antes da alteração: {e}") from e
    node = find_symbol_node(tree, name=name, kind=kind, in_class=in_class)
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno") or node.end_lineno is None:
        raise Code2Txt2CodeError("Python sem suporte a end_lineno. Use Python 3.8+.")

    lines = original.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    indent = re.match(r"\s*", lines[start]).group(0)

    clean_code = new_code.strip("\n") + "\n"
    # Se estamos substituindo método dentro de classe e o código veio sem indentação,
    # ajusta para a indentação do símbolo original.
    incoming_first = clean_code.splitlines()[0]
    incoming_indent = re.match(r"\s*", incoming_first).group(0)
    if indent and not incoming_indent:
        clean_code = "".join(indent + ln if ln.strip() else ln for ln in clean_code.splitlines(True))

    # Valida se o bloco novo isolado é Python válido no nível correto.
    try:
        ast.parse(clean_code if not indent else text_unindent(clean_code))
    except SyntaxError as e:
        raise Code2Txt2CodeError(f"Novo código para {name} é Python inválido: {e}") from e

    new_lines = clean_code.splitlines(keepends=True)
    return "".join(lines[:start] + new_lines + lines[end:])


def text_unindent(text: str) -> str:
    lines = text.splitlines(True)
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return text
    min_indent = min(len(re.match(r"\s*", ln).group(0)) for ln in non_empty)
    return "".join(ln[min_indent:] if len(ln) >= min_indent else ln for ln in lines)


def apply_one_change(root: Path, change: dict[str, Any], do_apply: bool, backup: bool) -> ChangeResult:
    ctype = change.get("type")
    rel = normalize_rel_path(change.get("file"))
    path = root / rel

    
    if ctype == "add_file":
        content = change.get("content", "")
        exists = path.exists()
        before = read_text(path) if exists else None
        result = ChangeResult(
            file=str(rel), type=ctype, status="checked",
            message=("arquivo existente sera sobrescrito" if exists
                        else "arquivo novo sera criado"),
            changed=(before != content),
        )
        if before is not None:
            result.before_sha256 = sha256_text(before)
        result.after_sha256 = sha256_text(content)
        if not do_apply:
            return result
        if exists and backup:
            result.backup = str(make_backup(path))
        write_text(path, content)
        result.status = "applied"
        result.message = ("arquivo sobrescrito" if exists else "arquivo criado")
        return result


    if ctype in {"replace_function", "replace_class", "replace_file", "append_to_file", "regex_replace"} and not path.exists():
        raise Code2Txt2CodeError(f"Arquivo não encontrado: {rel.as_posix()}")

    before_text = read_text(path) if path.exists() else ""
    before_sha = sha256_text(before_text) if path.exists() else None
    expected = change.get("expected_sha256")
    if expected and before_sha != expected:
        raise Code2Txt2CodeError(
            f"SHA divergente para {rel.as_posix()}. Esperado {expected}, atual {before_sha}. Gere novo snapshot."
        )

    after_text = before_text

    if ctype == "replace_function":
        name = change.get("name") or change.get("function")
        if not name:
            raise Code2Txt2CodeError("replace_function exige 'name'.")
        content = change.get("content")
        if not isinstance(content, str) or not content.strip():
            raise Code2Txt2CodeError("replace_function exige 'content'.")
        after_text = replace_ast_symbol(before_text, content, name=name, kind="function", in_class=change.get("in_class"))

    elif ctype == "replace_class":
        name = change.get("name") or change.get("class")
        if not name:
            raise Code2Txt2CodeError("replace_class exige 'name'.")
        content = change.get("content")
        if not isinstance(content, str) or not content.strip():
            raise Code2Txt2CodeError("replace_class exige 'content'.")
        after_text = replace_ast_symbol(before_text, content, name=name, kind="class")

    elif ctype == "create_file":
        if path.exists() and not change.get("overwrite", False):
            raise Code2Txt2CodeError(f"Arquivo já existe: {rel.as_posix()}. Use overwrite=true se desejar substituir.")
        content = change.get("content")
        if not isinstance(content, str):
            raise Code2Txt2CodeError("create_file exige 'content'.")
        after_text = content
        if after_text and not after_text.endswith("\n"):
            after_text += "\n"

    elif ctype == "replace_file":
        content = change.get("content")
        if not isinstance(content, str):
            raise Code2Txt2CodeError("replace_file exige 'content'.")
        after_text = content
        if after_text and not after_text.endswith("\n"):
            after_text += "\n"

    elif ctype == "append_to_file":
        content = change.get("content")
        if not isinstance(content, str):
            raise Code2Txt2CodeError("append_to_file exige 'content'.")
        sep = "" if before_text.endswith("\n") or not before_text else "\n"
        after_text = before_text + sep + content
        if after_text and not after_text.endswith("\n"):
            after_text += "\n"

    elif ctype == "regex_replace":
        pattern = change.get("pattern")
        replacement = change.get("replacement")
        count = int(change.get("count", 1))
        flags = re.S if change.get("dotall", True) else 0
        if not isinstance(pattern, str) or not isinstance(replacement, str):
            raise Code2Txt2CodeError("regex_replace exige 'pattern' e 'replacement'.")
        after_text, n = re.subn(pattern, replacement, before_text, count=count, flags=flags)
        if n == 0:
            raise Code2Txt2CodeError(f"regex_replace não encontrou padrão em {rel.as_posix()}.")

    else:
        raise Code2Txt2CodeError(f"Tipo de mudança não suportado: {ctype}")

    after_sha = sha256_text(after_text)
    changed = before_sha != after_sha
    if not changed:
        raise Code2Txt2CodeError(f"Mudança não alterou o arquivo: {rel.as_posix()}.")

    backup_path = None
    if do_apply:
        if backup and path.exists():
            backup_path = make_backup(path)
        write_text(path, after_text)

    return ChangeResult(
        file=rel.as_posix(),
        type=ctype,
        status="applied" if do_apply else "checked",
        message="alteração aplicada" if do_apply else "alteração validada, não aplicada",
        changed=changed,
        backup=str(backup_path) if backup_path else None,
        before_sha256=before_sha,
        after_sha256=after_sha,
    )


def compile_python_files(root: Path, files: list[str]) -> list[str]:
    errors = []
    for rel in files:
        if not rel.endswith(".py"):
            continue
        path = root / rel
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{rel}: {e.msg}")
    return errors


def apply_changes(args: argparse.Namespace) -> int:
    root = Path(args.src).resolve()
    data = load_changes(Path(args.input).resolve())
    do_apply = bool(args.apply)
    if args.check:
        do_apply = False

    results: list[ChangeResult] = []
    changed_files: list[str] = []
    errors: list[str] = []

    for i, change in enumerate(data["changes"], start=1):
        try:
            result = apply_one_change(root, change, do_apply=do_apply, backup=args.backup)
            results.append(result)
            changed_files.append(result.file)
            print(f"[OK] {i}: {result.type} -> {result.file} ({result.status})")
        except Exception as e:
            msg = f"[ERRO] {i}: {e}"
            print(msg)
            errors.append(msg)
            if not args.continue_on_error:
                break

    compile_errors: list[str] = []
    if not errors and args.compile:
        compile_errors = compile_python_files(root, changed_files)
        for err in compile_errors:
            print(f"[ERRO] py_compile: {err}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if do_apply else "check",
        "ok": not errors and not compile_errors,
        "results": [asdict(r) for r in results],
        "errors": errors,
        "compile_errors": compile_errors,
    }

    if args.report:
        report_path = Path(args.report).resolve()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] Relatório: {report_path}")

    if errors or compile_errors:
        return 1
    if not results:
        print("[ERRO] Nenhuma mudança foi validada/aplicada.")
        return 1
    print("[OK] Finalizado sem erros.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Snapshot de código e aplicador semântico local.")
    p.add_argument("--src", default=".", help="Raiz do projeto. Padrão: diretório atual.")

    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", action="store_true", help="Gera snapshot textual do projeto.")
    mode.add_argument("--input", help="Arquivo JSON de mudanças semânticas.")

    p.add_argument("--output", default="code_snapshot.txt", help="Arquivo de saída do snapshot. Com --snapshot-by-module, informe uma pasta de saída.")
    p.add_argument("--snapshot-by-module", action="store_true", help="Com --snapshot, gera um .txt por módulo/diretório de topo e um index.json.")
    p.add_argument("--include", action="append", help="Glob de inclusão. Pode repetir. Ex.: src/testforge/semantic/*.py")
    p.add_argument("--exclude", action="append", help="Glob de exclusão. Pode repetir.")
    p.add_argument("--exclude-dir", help="Diretórios a excluir, separados por vírgula.")
    p.add_argument("--ext", help="Extensões a incluir, separadas por vírgula. Ex.: .py,.js,.md")
    p.add_argument("--max-file-bytes", type=int, default=250_000, help="Tamanho máximo por arquivo no snapshot.")

    p.add_argument("--check", action="store_true", help="Valida mudanças sem aplicar.")
    p.add_argument("--apply", action="store_true", help="Aplica mudanças.")
    p.add_argument("--backup", action="store_true", help="Cria backup .bak antes de alterar arquivo existente.")
    p.add_argument("--compile", action="store_true", help="Executa py_compile nos arquivos Python alterados.")
    p.add_argument("--report", help="Salva relatório JSON.")
    p.add_argument("--continue-on-error", action="store_true", help="Continua processando mudanças após erro.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.snapshot:
            return create_snapshot(args)
        if not args.apply and not args.check:
            print("[ERRO] Para --input, informe --check ou --apply.")
            return 2
        return apply_changes(args)
    except Code2Txt2CodeError as e:
        print(f"[ERRO] {e}")
        return 1
    except KeyboardInterrupt:
        print("[ERRO] Interrompido pelo usuário.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

