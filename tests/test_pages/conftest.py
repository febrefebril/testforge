"""TestForge — Test fixtures for curation pages."""
import pytest
import os
import threading
import time
import socketserver
import http.server
from pathlib import Path

TEST_PAGES_DIR = str(Path(__file__).parent)


@pytest.fixture(scope="module")
def test_server():
    """Start local HTTP server serving test_pages/ directory."""
    # Change to test_pages dir so SimpleHTTPRequestHandler serves from there
    orig_dir = os.getcwd()
    os.chdir(TEST_PAGES_DIR)

    for port in [8770, 8771, 8772, 8773, 8774, 8775]:
        try:
            server = socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler)
            break
        except OSError:
            continue
    else:
        os.chdir(orig_dir)
        pytest.skip("No free port available for test server")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    url = f"http://localhost:{port}"
    yield url
    server.shutdown()
    os.chdir(orig_dir)
