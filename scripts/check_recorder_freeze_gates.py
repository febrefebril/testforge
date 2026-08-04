
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TestForge Recorder Freeze Gate.

Audita os gates necessários para declarar o núcleo do gravador de intenção
funcionalmente congelado. Usa somente a biblioteca padrão do Python e executa
pytest/compileall por subprocess quando disponíveis no ambiente corrente.

Uso:
    python scripts/check_recorder_freeze_gates.py --src .
    python scripts/check_recorder_freeze_gates.py --src . --full
    python scripts/check_recorder_freeze_gates.py --src . --json reports/recorder_freeze.json --md reports/recorder_freeze.md

Códigos de saída:
    0 = todos os gates obrigatórios passaram
    1 = há gate obrigatório com falha
    2 = erro de configuração/execução do auditor
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class GateResult:
    gate_id: str
    title: str
    status: Status
    mandatory: bool
    summary: str
    details: list[str] = field(default_factory=list)
    command: str = ""
    duration_ms: int = 0


@dataclass
class FreezeReport:
    schema_version: int
    generated_at: str
    project_root: str
    python: str
    full_mode: bool
    status: str
    counts: dict[str, int]
    gates: list[GateResult]


SPECIALIZED_SYMBOLS = (
    "normalize_specialized_event",
    "emit_specialized_python",
    "default_specialized_registry",
    "SpecializedActionType",
)

RECORDER_FORBIDDEN_EXECUTION_PATTERNS = {
    "expect_popup": re.compile(r"\bexpect_popup\s*\("),
    "expect_download": re.compile(r"\bexpect_download\s*\("),
    "set_input_files": re.compile(r"\bset_input_files\s*\("),
    "frame_locator": re.compile(r"\bframe_locator\s*\("),
}

RECORDER_FORBIDDEN_FRAMEWORK_PATTERNS = {
    "PrimeFaces": re.compile(r"\bPrimeFaces\b|PrimeFacesHandler"),
    "AngularMaterial": re.compile(r"\bAngularMaterial\b|AngularMaterialHandler"),
    "ReactMUI": re.compile(r"\bReactMUI\b|ReactMUIHandler"),
}

SECRET_PATTERNS = {
    "password literal": re.compile(r"(?i)[\"'](?:password|senha)[\"']\s*:\s*[\"'][^\"']+[\"']"),
    "bearer token literal": re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{16,}"),
    "JWT literal": re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{8,}"),
}

EXPECTED_SPECIALIZED_TESTS = (
    "tests/semantic/test_specialized_actions.py",
    "tests/handlers/test_handler_contracts.py",
)

E2E_KEYWORDS = {
    "frame": ("frame", "iframe"),
    "popup/new-page": ("popup", "new_page", "new-page", "new_tab"),
    "upload": ("upload", "set_input_files"),
    "download": ("download", "expect_download"),
    "redirect/auth": ("redirect", "authentication", "auth_redirect", "sso"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_text_files(base: Path, suffixes: set[str] | None = None) -> Iterable[Path]:
    if not base.exists():
        return
    excluded = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"}
    for path in base.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def search_patterns(base: Path, patterns: dict[str, re.Pattern[str]], root: Path) -> list[str]:
    findings: list[str] = []
    for path in iter_text_files(base, {".py", ".js", ".ts", ".json", ".yaml", ".yml"}):
        text = read_text(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern in patterns.items():
                if pattern.search(line):
                    findings.append(f"{rel(path, root)}:{lineno}: {name}: {line.strip()[:180]}")
    return findings


def run_command(args: Sequence[str], cwd: Path, timeout: int) -> tuple[int, str, int]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            list(args), cwd=str(cwd), text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False,
        )
        output = completed.stdout or ""
        return completed.returncode, output, int((time.perf_counter() - started) * 1000)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n[TIMEOUT] comando excedeu o limite"
        return 124, output, int((time.perf_counter() - started) * 1000)
    except OSError as exc:
        return 127, f"[ERRO] não foi possível executar: {exc}", int((time.perf_counter() - started) * 1000)


def tail(text: str, lines: int = 35) -> list[str]:
    data = text.strip().splitlines()
    return data[-lines:] if data else []


def result(gate_id: str, title: str, status: Status, mandatory: bool, summary: str,
           details: Iterable[str] = (), command: str = "", duration_ms: int = 0) -> GateResult:
    return GateResult(gate_id, title, status, mandatory, summary, list(details), command, duration_ms)


def gate_structure(root: Path) -> GateResult:
    required = [
        root / "src/testforge/semantic/specialized_actions.py",
        root / "src/testforge/semantic/__init__.py",
        root / "src/testforge/semantic/recording_normalizer.py",
        root / "src/testforge/semantic/compiler.py",
        root / "src/testforge/recorder",
    ]
    missing = [rel(p, root) for p in required if not p.exists()]
    if missing:
        return result("G01", "Estrutura obrigatória", Status.FAIL, True,
                      "Arquivos/diretórios obrigatórios ausentes.", missing)
    return result("G01", "Estrutura obrigatória", Status.PASS, True,
                  "Estrutura mínima do pipeline encontrada.", [rel(p, root) for p in required])


def gate_python_syntax(root: Path) -> GateResult:
    errors: list[str] = []
    checked = 0
    for base in (root / "src/testforge", root / "tests"):
        for path in iter_text_files(base, {".py"}):
            checked += 1
            try:
                ast.parse(read_text(path), filename=str(path))
            except SyntaxError as exc:
                errors.append(f"{rel(path, root)}:{exc.lineno}: {exc.msg}")
    if errors:
        return result("G02", "Sintaxe Python", Status.FAIL, True,
                      f"{len(errors)} arquivo(s) com erro de sintaxe entre {checked} verificados.", errors)
    return result("G02", "Sintaxe Python", Status.PASS, True,
                  f"{checked} arquivo(s) Python analisados por AST sem erro.")


def gate_handler_contracts(root: Path) -> GateResult:
    cmd = [sys.executable, "-c", (
        "from testforge.handlers import HANDLERS; "
        "print([(type(h).__name__, h.component_type) for h in HANDLERS])"
    )]
    code, output, duration = run_command(cmd, root, 60)
    status = Status.PASS if code == 0 else Status.FAIL
    return result("G03", "Contratos dos handlers", status, True,
                  "Handlers concretos podem ser instanciados." if code == 0
                  else "Falha ao importar/instanciar handlers concretos.",
                  tail(output), " ".join(cmd), duration)


def gate_targeted_tests(root: Path) -> GateResult:
    existing = [p for p in EXPECTED_SPECIALIZED_TESTS if (root / p).exists()]
    missing = [p for p in EXPECTED_SPECIALIZED_TESTS if not (root / p).exists()]
    if missing:
        return result("G04", "Testes especializados", Status.FAIL, True,
                      "Testes obrigatórios ausentes.", missing)
    cmd = [sys.executable, "-m", "pytest", *existing, "-q"]
    code, output, duration = run_command(cmd, root, 300)
    return result("G04", "Testes especializados", Status.PASS if code == 0 else Status.FAIL, True,
                  "Suíte especializada passou." if code == 0 else "Suíte especializada falhou.",
                  tail(output), " ".join(cmd), duration)


def production_consumers(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    base = root / "src/testforge"
    own = (root / "src/testforge/semantic/specialized_actions.py").resolve()
    init = (root / "src/testforge/semantic/__init__.py").resolve()
    hits: dict[str, list[str]] = {symbol: [] for symbol in SPECIALIZED_SYMBOLS}
    for path in iter_text_files(base, {".py"}):
        if path.resolve() in {own, init}:
            continue
        text = read_text(path)
        for symbol in SPECIALIZED_SYMBOLS:
            for lineno, line in enumerate(text.splitlines(), 1):
                if re.search(rf"\b{re.escape(symbol)}\b", line):
                    hits[symbol].append(f"{rel(path, root)}:{lineno}")
    missing = [symbol for symbol, locations in hits.items() if not locations]
    return hits, missing


def gate_productive_consumption(root: Path) -> GateResult:
    hits, missing = production_consumers(root)
    details = [f"{symbol}: {', '.join(locations) if locations else 'SEM CONSUMIDOR PRODUTIVO'}"
               for symbol, locations in hits.items()]
    if missing:
        details.append("Símbolos sem consumidor: " + ", ".join(missing))
        return result("G05", "Consumo produtivo da camada especializada", Status.FAIL, True,
                      "A camada especializada ainda está isolada de parte do pipeline.", details)
    return result("G05", "Consumo produtivo da camada especializada", Status.PASS, True,
                  "Normalizer/compiler/runtime possuem referências produtivas à camada especializada.", details)


def gate_recorder_decoupling(root: Path) -> GateResult:
    recorder = root / "src/testforge/recorder"
    execution = search_patterns(recorder, RECORDER_FORBIDDEN_EXECUTION_PATTERNS, root)
    frameworks = search_patterns(recorder, RECORDER_FORBIDDEN_FRAMEWORK_PATTERNS, root)
    findings = execution + frameworks
    if findings:
        return result("G06", "Desacoplamento do recorder", Status.FAIL, True,
                      "Foram encontradas decisões de execução/framework dentro do recorder.", findings)
    return result("G06", "Desacoplamento do recorder", Status.PASS, True,
                  "Nenhuma decisão Playwright especializada ou regra de framework foi encontrada no recorder.")


def gate_no_silent_specialized_fallback(root: Path) -> GateResult:
    path = root / "src/testforge/semantic/specialized_actions.py"
    if not path.exists():
        return result("G07", "Falha explícita para tipos especializados", Status.FAIL, True,
                      "Módulo specialized_actions.py ausente.")
    text = read_text(path)
    required = ("SpecializedActionError", "sem handler", "Tipo especializado sem emissor")
    absent = [token for token in required if token not in text]
    suspicious = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.search(r"except\s+Exception\s*:\s*(?:pass)?\s*$", line.strip()):
            suspicious.append(f"{rel(path, root)}:{lineno}: {line.strip()}")
    if absent:
        return result("G07", "Falha explícita para tipos especializados", Status.FAIL, True,
                      "Contratos de falha explícita ausentes.", absent + suspicious)
    status = Status.WARN if suspicious else Status.PASS
    return result("G07", "Falha explícita para tipos especializados", status, True,
                  "Tipos não suportados falham explicitamente." if not suspicious
                  else "Falha explícita presente, mas há except genérico para revisão.", suspicious)


def gate_e2e_matrix(root: Path) -> GateResult:
    test_base = root / "tests"
    corpus: list[tuple[str, str]] = []
    for path in iter_text_files(test_base, {".py", ".html", ".js", ".json", ".yaml", ".yml"}):
        corpus.append((rel(path, root), read_text(path).lower()))
    details: list[str] = []
    missing: list[str] = []
    for family, keywords in E2E_KEYWORDS.items():
        locations = sorted({name for name, text in corpus if any(k.lower() in text or k.lower() in name.lower() for k in keywords)})
        if locations:
            details.append(f"{family}: {', '.join(locations[:8])}")
        else:
            missing.append(family)
            details.append(f"{family}: SEM COBERTURA LOCAL DETECTADA")
    if missing:
        return result("G08", "Matriz E2E local", Status.FAIL, True,
                      "Famílias sem fixture/teste local detectável: " + ", ".join(missing), details)
    return result("G08", "Matriz E2E local", Status.PASS, True,
                  "Há evidência estática de cobertura local para todas as famílias.", details)


def gate_backward_compatibility(root: Path) -> GateResult:
    candidates = []
    for base in (root / "tests", root / "recordings"):
        for path in iter_text_files(base, {".jsonl", ".json", ".py"}):
            text = read_text(path).lower()
            if all(token in text for token in ("click", "fill")) and "specialized" not in path.name.lower():
                candidates.append(rel(path, root))
                if len(candidates) >= 10:
                    break
        if candidates:
            break
    if not candidates:
        return result("G09", "Compatibilidade regressiva", Status.WARN, True,
                      "Não foi encontrado artefato legado detectável para prova automática.",
                      ["Adicione uma golden recording com navigation/click/fill/select/assert e recompile-a no CI."])
    return result("G09", "Compatibilidade regressiva", Status.PASS, True,
                  "Artefato(s) legado(s) detectado(s) para regressão.", candidates)


def gate_traceability(root: Path) -> GateResult:
    path = root / "src/testforge/semantic/specialized_actions.py"
    if not path.exists():
        return result("G10", "Rastreabilidade", Status.FAIL, True, "Módulo especializado ausente.")
    text = read_text(path)
    required = ("write_trace", '"event_id"', '"specialized_type"', '"page_id"', '"frame_id"', '"decision"', '"result"')
    absent = [token for token in required if token not in text]
    if absent:
        return result("G10", "Rastreabilidade", Status.FAIL, True,
                      "Campos obrigatórios de rastreabilidade ausentes.", absent)
    return result("G10", "Rastreabilidade", Status.PASS, True,
                  "Contrato mínimo de trace especializado encontrado.")


def gate_secret_literals(root: Path) -> GateResult:
    findings: list[str] = []
    for base in (root / "src/testforge/semantic", root / "tests/semantic"):
        findings.extend(search_patterns(base, SECRET_PATTERNS, root))
    if findings:
        return result("G11", "Segredos e dados sensíveis", Status.FAIL, True,
                      "Possíveis segredos literais encontrados no escopo do épico.", findings)
    return result("G11", "Segredos e dados sensíveis", Status.PASS, True,
                  "Nenhum segredo literal óbvio foi encontrado no escopo auditado.")


def gate_full_suite(root: Path, full: bool, timeout: int) -> GateResult:
    if not full:
        return result("G12", "Regressão completa", Status.SKIP, False,
                      "Não executada. Use --full para rodar toda a suíte.")
    cmd = [sys.executable, "-m", "pytest", "tests", "-q"]
    code, output, duration = run_command(cmd, root, timeout)
    return result("G12", "Regressão completa", Status.PASS if code == 0 else Status.FAIL, True,
                  "Toda a suíte passou." if code == 0 else "A suíte completa possui falhas.",
                  tail(output, 60), " ".join(cmd), duration)


def gate_git_state(root: Path) -> GateResult:
    cmd = ["git", "status", "--porcelain"]
    code, output, duration = run_command(cmd, root, 30)
    if code == 127:
        return result("G13", "Estado do Git", Status.SKIP, False,
                      "Git não está disponível; gate informativo ignorado.", tail(output), " ".join(cmd), duration)
    if code != 0:
        return result("G13", "Estado do Git", Status.WARN, False,
                      "Não foi possível verificar o estado do Git.", tail(output), " ".join(cmd), duration)
    changed = [line for line in output.splitlines() if line.strip()]
    return result("G13", "Estado do Git", Status.WARN if changed else Status.PASS, False,
                  "Há arquivos modificados/não rastreados." if changed else "Árvore de trabalho limpa.",
                  changed[:50], " ".join(cmd), duration)


def evaluate(gates: list[GateResult]) -> tuple[str, dict[str, int]]:
    counts = {status.value: sum(g.status is status for g in gates) for status in Status}
    mandatory_fail = any(g.mandatory and g.status is Status.FAIL for g in gates)
    mandatory_warn = any(g.mandatory and g.status is Status.WARN for g in gates)
    if mandatory_fail:
        return "NOT_READY", counts
    if mandatory_warn:
        return "CONDITIONALLY_READY", counts
    return "RECORDER_CORE_FROZEN", counts


def to_markdown(report: FreezeReport) -> str:
    lines = [
        "# TestForge — Recorder Freeze Gate",
        "",
        f"- Resultado: **{report.status}**",
        f"- Gerado em: `{report.generated_at}`",
        f"- Projeto: `{report.project_root}`",
        f"- Python: `{report.python}`",
        f"- Modo completo: `{report.full_mode}`",
        "",
        "## Resumo",
        "",
        *[f"- {key}: {value}" for key, value in report.counts.items()],
        "",
        "## Gates",
        "",
    ]
    for gate in report.gates:
        required = "obrigatório" if gate.mandatory else "informativo"
        lines.extend([
            f"### {gate.gate_id} — {gate.title}: {gate.status.value}",
            "",
            f"**Tipo:** {required}",
            "",
            gate.summary,
            "",
        ])
        if gate.command:
            lines.extend(["**Comando:**", "", f"```text\n{gate.command}\n```", ""])
        if gate.details:
            lines.append("**Detalhes:**")
            lines.append("")
            lines.extend(f"- `{item}`" for item in gate.details)
            lines.append("")
    lines.extend([
        "## Regra de decisão",
        "",
        "- `RECORDER_CORE_FROZEN`: nenhum gate obrigatório falhou ou ficou pendente.",
        "- `CONDITIONALLY_READY`: não há falha obrigatória, mas há aviso que exige decisão registrada.",
        "- `NOT_READY`: ao menos um gate obrigatório falhou.",
        "",
    ])
    return "\n".join(lines)


def write_report(report: FreezeReport, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(report)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")


def print_console(report: FreezeReport) -> None:
    icons = {Status.PASS: "OK", Status.FAIL: "FAIL", Status.WARN: "WARN", Status.SKIP: "SKIP"}
    print("\nTestForge Recorder Freeze Gate")
    print("=" * 72)
    for gate in report.gates:
        print(f"[{icons[gate.status]:4}] {gate.gate_id} {gate.title}: {gate.summary}")
        if gate.status in {Status.FAIL, Status.WARN}:
            for item in gate.details[:8]:
                print(f"       - {item}")
            if len(gate.details) > 8:
                print(f"       - ... e mais {len(gate.details) - 8} ocorrência(s)")
    print("=" * 72)
    print(f"RESULTADO: {report.status}")
    print("Contagens: " + ", ".join(f"{k}={v}" for k, v in report.counts.items()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audita gates para congelamento do gravador de intenção do TestForge.")
    parser.add_argument("--src", default=".", help="Raiz do projeto TestForge.")
    parser.add_argument("--full", action="store_true", help="Executa também toda a suíte tests/.")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout em segundos da suíte completa.")
    parser.add_argument("--json", default="reports/recorder_freeze_gate.json", help="Relatório JSON.")
    parser.add_argument("--md", default="reports/recorder_freeze_gate.md", help="Relatório Markdown.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.src).resolve()
    if not (root / "src/testforge").is_dir():
        print(f"[ERRO] Projeto inválido: não encontrei src/testforge em {root}", file=sys.stderr)
        return 2

    gates = [
        gate_structure(root),
        gate_python_syntax(root),
        gate_handler_contracts(root),
        gate_targeted_tests(root),
        gate_productive_consumption(root),
        gate_recorder_decoupling(root),
        gate_no_silent_specialized_fallback(root),
        gate_e2e_matrix(root),
        gate_backward_compatibility(root),
        gate_traceability(root),
        gate_secret_literals(root),
        gate_full_suite(root, args.full, args.timeout),
        gate_git_state(root),
    ]
    final_status, counts = evaluate(gates)
    report = FreezeReport(
        schema_version=1,
        generated_at=now_iso(),
        project_root=str(root),
        python=sys.executable,
        full_mode=bool(args.full),
        status=final_status,
        counts=counts,
        gates=gates,
    )
    json_path = Path(args.json)
    md_path = Path(args.md)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not md_path.is_absolute():
        md_path = root / md_path
    write_report(report, json_path, md_path)
    print_console(report)
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 1 if final_status == "NOT_READY" else 0


if __name__ == "__main__":
    raise SystemExit(main())

