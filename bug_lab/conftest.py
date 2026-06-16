"""TestForge Bug Lab — test fixtures for bug reproduction pages."""
import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

import pytest

PAGES_DIR = str(Path(__file__).parent / "pages")


@pytest.fixture(scope="module")
def test_server():
    """Start local HTTP server serving bug_lab/pages/ directory."""
    orig_dir = os.getcwd()
    os.chdir(PAGES_DIR)

    for port in [8700, 8701, 8702, 8703, 8704, 8705]:
        try:
            server = socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler)
            break
        except OSError:
            continue
    else:
        os.chdir(orig_dir)
        pytest.skip("No free port available for bug lab test server")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    url = f"http://localhost:{port}"
    yield url
    server.shutdown()
    os.chdir(orig_dir)


@pytest.fixture(scope="module")
def browser():
    """Module-scoped Playwright chromium browser. Skips if not installed."""
    pw = pytest.importorskip("playwright.sync_api", reason="playwright not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    """Per-test browser page."""
    ctx = browser.new_context()
    pg = ctx.new_page()
    yield pg
    pg.close()
    ctx.close()
