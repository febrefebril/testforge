"""TestForge CLI — Comando record com keyboard shortcuts."""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright.sync_api import sync_playwright
from testforge.recorder import RecorderController


def cmd_record(args):
    """Grava fluxo de teste com comandos de teclado (Shift+P, Shift+S, Shift+A)."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = RecorderController(page)

        ts = time.strftime("%Y%m%d-%H%M%S")
        rid = args.name or f"REC-{ts}"

        print(f"[TestForge] Iniciando gravacao: {rid}")
        print(f"  URL: {args.url}")
        print(f"  Comandos: Shift+P = pause | Shift+S = stop | Shift+A = assert")
        print()

        recorder.start(recording_id=rid, application=args.app or "web", base_url=args.url)
        page.goto(args.url)

        step_count = 0
        try:
            while True:
                time.sleep(0.3)
                recorder.flush_events()
                result = recorder.handle_commands()

                # Check for new steps
                steps_file = os.path.join("recordings", rid, "steps.jsonl")
                if os.path.exists(steps_file):
                    with open(steps_file) as f:
                        current = sum(1 for _ in f)
                    if current > step_count:
                        step_count = current
                        print(f"[TestForge] Passos: {step_count}")

                if result == "stop":
                    print("[TestForge] Gravacao finalizada pelo usuario (Shift+S)")
                    break
                elif result == "paused":
                    sys.stdout.write("\r[TestForge] ⏸ Pausado... (Shift+P para retomar)  ")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            print("\n[TestForge] Interrompido pelo usuario")

        recorder.stop()
        recorder.finalize()
        print(f"[TestForge] Sessao salva em recordings/{rid}/")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description="TestForge CLI")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record", help="Gravar fluxo de teste")
    rec.add_argument("url", help="URL da aplicacao alvo")
    rec.add_argument("--name", help="Nome/ID da gravacao")
    rec.add_argument("--app", help="Nome da aplicacao")
    rec.add_argument("--headless", action="store_true", help="Modo headless")

    rec.set_defaults(func=cmd_record)
    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
