from __future__ import annotations

import typer

app = typer.Typer(
    name="testforge",
    help="TestForge — gravação inteligente de testes com Playwright + LLM",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    pass


import testforge.core.cli.record  # noqa: E402, F401
import testforge.core.cli.run  # noqa: E402, F401
import testforge.core.cli.report  # noqa: E402, F401


if __name__ == "__main__":
    app()
