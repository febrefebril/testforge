"""TestForge E2E — Gravar fluxo no fake-react-bank-app."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright.sync_api import sync_playwright
from testforge.recorder import RecorderController

APP_URL = "http://localhost:8765"


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        recorder = RecorderController(page)

        print("Iniciando gravacao...")
        recorder.start(
            recording_id="REC-TEST-001",
            application="fake-react-bank-app",
            base_url=APP_URL,
        )

        page.goto(APP_URL)
        page.wait_for_timeout(500)

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)

        recorder.stop()
        recorder.finalize()
        print(f"Gravacao finalizada: {recorder.active_session}")

        session_dir = "recordings/REC-TEST-001"
        if os.path.exists(session_dir):
            files = os.listdir(session_dir)
            print(f"Arquivos gerados em {session_dir}/: {files}")
            for sub in ["screenshots", "dom_snapshots", "ax_snapshots"]:
                subdir = os.path.join(session_dir, sub)
                if os.path.exists(subdir):
                    print(f"  {sub}/: {len(os.listdir(subdir))} arquivos")

        browser.close()


if __name__ == "__main__":
    main()
