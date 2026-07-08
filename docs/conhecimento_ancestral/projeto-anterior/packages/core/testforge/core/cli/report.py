from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from testforge.core.cli.app import app
from testforge.core.models.report import Report


REPORT_GLOB = "*_report.json"


def _scan_reports(directory: Path) -> list[dict]:
    reports = []
    for p in directory.rglob(REPORT_GLOB):
        try:
            data = json.loads(p.read_text())
            started_at = data.get("started_at", "")
            ts = datetime.fromisoformat(started_at) if started_at else datetime.min.replace(tzinfo=timezone.utc)
            curation = data.get("curation", {}) or {}
            reports.append({
                "path": str(p),
                "test_name": data.get("test_name", p.stem.replace("_report", "")),
                "started_at": started_at,
                "timestamp": ts,
                "duration_ms": data.get("duration_ms", 0),
                "status": data.get("status", "unknown"),
                "mode": data.get("mode", ""),
                "executive": data.get("summary", {}).get("executive", ""),
                "taxonomy_id": curation.get("taxonomy_id", ""),
                "family": curation.get("family", ""),
            })
        except Exception:
            pass
    reports.sort(key=lambda r: r["timestamp"], reverse=True)
    return reports


@app.command()
def report(
    path: Annotated[
        Optional[str],
        typer.Argument(help="Caminho do arquivo _report.json"),
    ] = None,
    history: Annotated[
        bool,
        typer.Option("--history", "-l", help="Listar histórico de execuções"),
    ] = False,
    period: Annotated[
        Optional[str],
        typer.Option("--period", "-p", help="Filtrar por período: 1d, 7d, 30d"),
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filtrar por status: passed, failed, partial"),
    ] = None,
    taxonomy: Annotated[
        Optional[str],
        typer.Option("--taxonomy", help="Filtrar por ID taxonômico (ex: SEL-004)"),
    ] = None,
    family: Annotated[
        Optional[str],
        typer.Option("--family", help="Filtrar por família (ex: FAM-01)"),
    ] = None,
    directory: Annotated[
        str,
        typer.Option("--directory", "-d", help="Diretório para escanear relatórios"),
    ] = ".",
) -> None:
    """Exibir relatório ou histórico de execuções."""

    if history:
        _show_history(directory, period, status, taxonomy, family)
    elif path:
        _show_report(path)
    else:
        print("  Use: testforge report <caminho-do-relatorio>")
        print("  Ou:  testforge report --history")
        raise typer.Exit()


def _show_report(report_path: str) -> None:
    rp = Path(report_path)
    if not rp.exists():
        print(f"  ❌ Relatório não encontrado: {report_path}")
        raise typer.Exit(code=1)

    report = Report.load(str(rp))
    status_icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"

    print(f"\n  {status_icon} TestForge — Relatório de Execução")
    print(f"  {'═' * 60}")

    print(f"  Teste:    {report.test_name}")
    print(f"  Data:     {report.started_at}")
    print(f"  Duração:  {report.duration_ms}ms")
    print(f"  Status:   {status_icon} {report.status}")
    print(f"  Modo:     {report.mode}")
    print(f"  Navegador: {report.browser}")
    print(f"")

    print(f"  📊 {report.summary.executive}")
    print(f"")

    if report.steps:
        print(f"  Detalhamento dos passos:")
        print(f"  {'─' * 60}")
        for i, step in enumerate(report.steps):
            icon = "✅" if step.status == "passed" else "❌" if step.status == "failed" else "⏭️"
            name = step.intention or step.name
            line = f"  {icon} [{i+1}] {name}: {step.status} ({step.duration_ms}ms)"
            print(line)
            if step.error_message:
                print(f"       ⚠️  {step.error_message}")
            if step.screenshot_path:
                print(f"       📸 Screenshot: {step.screenshot_path}")
        print(f"  {'─' * 60}")

    if report.trace_path and Path(report.trace_path).exists():
        print(f"\n  🔍 Trace: {report.trace_path}")

    print(f"")


def _show_history(
    directory: str,
    period: Optional[str],
    status_filter: Optional[str],
    taxonomy_filter: Optional[str] = None,
    family_filter: Optional[str] = None,
) -> None:
    scan_dir = Path(directory)
    if not scan_dir.exists():
        print(f"  ❌ Diretório não encontrado: {directory}")
        raise typer.Exit(code=1)

    reports = _scan_reports(scan_dir)

    if period:
        days = _parse_period(period)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        reports = [r for r in reports if r["timestamp"] >= cutoff]

    if status_filter:
        reports = [r for r in reports if r["status"] == status_filter]

    if taxonomy_filter:
        reports = [r for r in reports if r.get("taxonomy_id", "") == taxonomy_filter]

    if family_filter:
        reports = [r for r in reports if r.get("family", "") == family_filter]

    if not reports:
        print(f"\n  📋 Nenhum relatório encontrado.")
        return

    print(f"\n  📋 Histórico de Execuções ({len(reports)} registro(s))")
    print(f"  {'═' * 80}")

    for r in reports:
        icon = "✅" if r["status"] == "passed" else "⚠️" if r["status"] == "partial" else "❌"
        ts = r["started_at"][:19] if r["started_at"] else "sem data"
        dur = f"{r['duration_ms']}ms"
        tid = r.get("taxonomy_id", "") or ""
        fam = r.get("family", "") or ""
        tag = f" [{fam}/{tid}]" if fam or tid else ""
        print(f"  {icon} {ts}  {dur:>8}  {r['status']:<8}{tag}  {r['test_name']}")
        print(f"     📄 {r['path']}")

    print(f"  {'═' * 80}\n")


def _parse_period(period: str) -> int:
    period = period.strip().lower()
    if period.endswith("d"):
        return int(period[:-1])
    if period.endswith("h"):
        return int(period[:-1]) // 24
    if period.endswith("w"):
        return int(period[:-1]) * 7
    return 7
