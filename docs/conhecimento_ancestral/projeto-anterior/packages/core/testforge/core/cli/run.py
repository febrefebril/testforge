from __future__ import annotations

import logging
from typing import Optional

import typer
from typing_extensions import Annotated

from testforge.core.cli.app import app
from testforge.core.execution.runner import TestRunner
from testforge.core.notification import notify_all

logger = logging.getLogger("testforge.cli.run")


@app.command()
def run(
    script: Annotated[
        str,
        typer.Argument(help="Caminho do script .py gerado pelo testforge record"),
    ],
    headed: Annotated[
        bool,
        typer.Option("--headed", help="Abrir navegador visível durante a execução"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout global em ms"),
    ] = 30000,
    slow_mo: Annotated[
        int,
        typer.Option("--slow-mo", help="Atraso em ms entre cada passo (para visualização)"),
    ] = 0,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Modo debug com logs detalhados"),
    ] = False,
    notify: Annotated[
        bool,
        typer.Option("--notify", "-n", help="Enviar notificação ao finalizar"),
    ] = False,
) -> None:
    """Executar um teste gravado."""
    runner = TestRunner(
        script_path=script,
        headed=headed,
        timeout=timeout,
        slow_mo=slow_mo,
        debug=debug,
    )

    print(f"\n  TestForge — Executando: {script}")
    print(f"  {'═' * 50}\n")

    report = runner.run()

    if notify:
        results = notify_all(report)
        if results.get("email"):
            print(f"  📧 Notificação enviada por e-mail")
        if results.get("teams"):
            print(f"  💬 Notificação enviada para o Teams")

    print(f"\n  {'═' * 50}")
    status_icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"
    print(f"  {status_icon} Resultado: {report.summary.executive}")
    print(f"  ⏱️  Duração: {report.duration_ms}ms")
    print(f"  {'═' * 50}")
