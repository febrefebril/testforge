"""TestForge — Test fixtures for curation pages."""
import pytest
import os
import threading
import time
import socketserver
import http.server
from pathlib import Path

TEST_PAGES_DIR = str(Path(__file__).parent / "test_pages")


@pytest.fixture(scope="module")
def test_server():
    """Start local HTTP server serving test_pages/ directory."""
    for port in [8770, 8771, 8772, 8773, 8774, 8775]:
        try:
            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=TEST_PAGES_DIR, **kwargs)

            server = socketserver.TCPServer(("", port), Handler)
            break
        except OSError:
            continue
    else:
        pytest.skip("No free port available for test server")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    url = f"http://localhost:{port}"
    yield url
    server.shutdown()
