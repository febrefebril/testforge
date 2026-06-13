"""Teste E2E do Recorder Sensorial contra fake-react-bank-app."""
import json
import os

from playwright.sync_api import sync_playwright

from testforge.recorder import RecorderController

APP_URL = "http://localhost:8765"


def test_recorder_e2e_fake_bank():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = RecorderController(page)

        # Start
        recorder.start(recording_id="REC-E2E-001", application="fake-bank", base_url=APP_URL)

        # Navigate
        page.goto(APP_URL)
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Fill CPF
        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(300)
        recorder.flush_events()

        # Click
        page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Stop
        recorder.stop()
        recorder.finalize()
        browser.close()

    # Verify artifacts
    session_dir = "recordings/REC-E2E-001"
    assert os.path.isdir(session_dir), f"Diretorio nao criado: {session_dir}"

    # metadata
    with open(os.path.join(session_dir, "recording_metadata.json")) as f:
        meta = json.load(f)
    assert meta["status"] == "completed"

    # events
    with open(os.path.join(session_dir, "raw_events.jsonl")) as f:
        events = [json.loads(line) for line in f]
    assert len(events) > 0, "Nenhum evento capturado"

    event_types = [e["type"] for e in events]
    assert "navigation" in event_types, f"Sem evento navigation em {event_types}"

    # screenshots
    screenshots = os.listdir(os.path.join(session_dir, "screenshots"))
    assert len(screenshots) > 0, "Nenhum screenshot capturado"

    # network log
    assert os.path.exists(os.path.join(session_dir, "network_log.json"))
