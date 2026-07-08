from __future__ import annotations

import asyncio
from typing import Optional

import typer
from typing_extensions import Annotated

from testforge.core.cli.app import app
from testforge.core.recording.session import RecordingSession


@app.command()
def record(
    url: Annotated[
        str,
        typer.Argument(help="URL do sistema alvo para gravar o teste"),
    ],
    headed: Annotated[
        bool,
        typer.Option("--headed", help="Abrir navegador visível"),
    ] = True,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Diretório de saída para os artefatos"),
    ] = "./testes",
    name: Annotated[
        Optional[str],
        typer.Option("--name", help="Nome do caso de teste (diretório + script)"),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout máximo da gravação em minutos"),
    ] = 30,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Modo debug com logs detalhados"),
    ] = False,
    mode: Annotated[
        str,
        typer.Option("--mode", help="Modo do overlay: 'full' (padrão) ou 'shortcuts' (atalhos sem UI)"),
    ] = "full",
) -> None:
    """Gravar um teste navegando pelo sistema alvo."""
    session = RecordingSession(
        url=url,
        output_dir=output,
        test_name=name,
        max_duration_minutes=timeout,
        headed=headed,
        debug=debug,
        mode=mode,
    )
    asyncio.run(session.start())
