"""TestForge — CLI run-incremental command."""
from __future__ import annotations
import os
import sys


def cmd_run_incremental(args):
    from testforge.runner.incremental_runner import IncrementalRunner
    try:
        from testforge.cdp_launcher import ensure_cdp_ready, is_windows_caixa_mode, get_preferred_browser
        if is_windows_caixa_mode(args):
            ok, msg = ensure_cdp_ready(preferred_browser=get_preferred_browser(args), quiet=False)
            if not ok:
                print(f"[TestForge] X CDP falhou: {msg}", file=sys.stderr)
    except ImportError:
        pass
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
    )
    try:
        report = runner.run()
        summary = report.get("summary", {})
        failed = summary.get("failed", 0) + summary.get("healing_rejected", 0)
        sys.exit(0 if failed == 0 else 1)
    except FileNotFoundError as exc:
        print(f"[TestForge] X {exc}", file=sys.stderr)
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
    inc.add_argument("--headless", action="store_true")
    inc.add_argument("--timeout", type=int, default=60)
    inc.add_argument("--verbose", action="store_true")
    inc.add_argument("--data", type=str, default="")
    inc.add_argument("--browser", choices=["chromium", "chrome", "edge"], default=os.environ.get("TESTFORGE_DEFAULT_BROWSER", "chromium"))
    inc.add_argument("--stop-on-failure", dest="stop_on_failure", action="store_true", default=True)
    inc.add_argument("--no-stop-on-failure", dest="stop_on_failure", action="store_false")
    inc.add_argument("--interactive", action="store_true")
    inc.add_argument("--no-healing", dest="no_healing", action="store_true")
    inc.add_argument("--shadow", action="store_true")
    inc.add_argument("--windows-caixa", action="store_true",
                     help="Modo CAIXA: abre Edge/Chrome corporativo via CDP")
    inc.add_argument("--cdp-browser", choices=["edge", "chrome", "auto"], default=None,
                     help="Browser CDP: edge, chrome ou auto")
    inc.set_defaults(func=cmd_run_incremental)
    return inc