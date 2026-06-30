"""TestForge — Comando CLI run-incremental."""
from __future__ import annotations
import glob
import os
import sys


def _resolve_script_path(script: str) -> str:
    """Aceita arquivo ou diretorio; resolve para o test_*.py dentro."""
    if os.path.isdir(script):
        candidates = sorted(glob.glob(os.path.join(script, "test_*.py")))
        if not candidates:
            raise FileNotFoundError(
                f"Diretorio sem script test_*.py: {script}"
            )
        if len(candidates) > 1:
            print(
                f"[TestForge] Aviso: {len(candidates)} scripts encontrados, usando {candidates[0]}",
                file=sys.stderr,
            )
        return candidates[0]
    return script


def cmd_run_incremental(args):
    from testforge.runner.incremental_runner import IncrementalRunner
    try:
        args.script = _resolve_script_path(args.script)
    except FileNotFoundError as exc:
        print(f"[TestForge] [X] {exc}", file=sys.stderr)
        sys.exit(2)
    _verify_ssl = getattr(args, 'verify_ssl', False)
    runner = IncrementalRunner(
        script_path=args.script,
        headless=args.headless,
        timeout=args.timeout,
        verbose=args.verbose,
        data=args.data,
        browser=args.browser,
        stop_on_failure=args.stop_on_failure,
        interactive=args.interactive,
        no_healing=args.no_healing,
        shadow=args.shadow,
        capture=args.capture,
        debug_healing=getattr(args, 'debug_healing', False),
        verify_ssl=_verify_ssl,
    )
    try:
        report = runner.run()
        summary = report.get("summary", {})
        failed = summary.get("failed", 0) + summary.get("healing_rejected", 0)
        # Sprint D (2026-06-30): --strict-asserts faz o run sair com codigo
        # nao-zero quando algum assert do script nao foi atingido. Sem isso
        # CI nao detecta regressao real (failed=0 nao significa assert_hit=1).
        # Default off para compat — pipelines existentes precisam optar.
        if getattr(args, "strict_asserts", False):
            asserts_total = summary.get("asserts_total", 0)
            asserts_hit = summary.get("asserts_hit", 0)
            if asserts_total > 0 and asserts_hit < asserts_total:
                print(
                    f"[TestForge] [STRICT] {asserts_hit} de {asserts_total} asserts atingidos"
                    f" — exit 1 (--strict-asserts)",
                    file=sys.stderr,
                )
                sys.exit(1)
        sys.exit(0 if failed == 0 else 1)
    except FileNotFoundError as exc:
        print(f"[TestForge] [X] {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"[TestForge] X Erro inesperado: {exc}", file=sys.stderr)
        sys.exit(3)


def register(sub):
    inc = sub.add_parser(
        "run-incremental",
        help="Executar teste passo a passo com pre/pos-condicoes e healing validado",
    )
    inc.add_argument("script", help="Caminho do script Python gerado")
    inc.add_argument("--headless", dest="headless", action="store_true", default=False,
                     help="Modo headless: viewport 1280x720 forcado (sem flicker, ideal para CI)")
    inc.add_argument("--headed", dest="headless", action="store_false",
                     help="Modo headed: viewport da janela real (padrao). Evita flicker no Windows.")
    inc.add_argument("--timeout", type=int, default=60)
    inc.add_argument("--verbose", action="store_true")
    inc.add_argument("--data", type=str, default="")
    inc.add_argument("--browser", choices=["chromium", "chrome", "edge"], default=os.environ.get("TESTFORGE_DEFAULT_BROWSER", "chromium"))
    inc.add_argument("--stop-on-failure", dest="stop_on_failure", action="store_true", default=True)
    inc.add_argument("--no-stop-on-failure", dest="stop_on_failure", action="store_false")
    inc.add_argument("--interactive", action="store_true")
    inc.add_argument("--no-healing", dest="no_healing", action="store_true")
    inc.add_argument("--shadow", action="store_true")
    inc.add_argument("--no-capture", dest="capture", action="store_false", default=True,
                     help="Desabilitar captura de telemetria de execucao")
    inc.add_argument("--debug-healing", dest="debug_healing", action="store_true",
                     help="Log payloads LLM + respostas brutas em stderr")
    inc.add_argument("--verify-ssl", action="store_true", default=False,
                     help="Verificar certificado SSL (default: ignorar certificados SSL)")
    inc.add_argument("--strict-asserts", dest="strict_asserts", action="store_true",
                     default=False,
                     help="Exit 1 quando asserts_hit < asserts_total (Sprint D 2026-06-30)")
    inc.set_defaults(func=cmd_run_incremental)
    return inc