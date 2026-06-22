from __future__ import annotations

import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Generator

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEST_PAGES_DIR = PROJECT_ROOT / "tests" / "test_pages"


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TEST_PAGES_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass


@pytest.fixture(scope="session")
def test_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def healing_catalog(tmp_path):
    from testforge.core.healing.storage import HealingCatalog
    db_path = tmp_path / "test_healing.jsonl"
    return HealingCatalog(str(db_path))
