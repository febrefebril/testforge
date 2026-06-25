"""Sprint 0 — DiagnosticSession lifecycle (placeholder skeleton).

Will grow over commits 2-6. This commit lands a minimal skeleton with
just the framework-detection wiring so the build stays green between
commits.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _tester_hash() -> str:
    """Anonymous per-machine identifier (no PII)."""
    seed = f"{platform.node()}|{os.environ.get('USER', '')}"
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


class DiagnosticSession:
    """High-level wrapper. Threads framework, capture, replay, gherkin."""

    def __init__(self, page, cdp_session=None,
                 session_dir: str = ".testforge/diagnostic/default",
                 replay_mode: str = "immediate",
                 gherkin_lang: str = "pt") -> None:
        self._page = page
        self._cdp = cdp_session
        self._dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
        self._replay_mode = replay_mode
        self._gherkin_lang = gherkin_lang
        self._session_id = str(uuid.uuid4())
        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None

        # Late-bound — populated by start()
        self._detector = None
        self._tracker = None
        self._replay = None
        self._gherkin = None
        self._store = None

    def start(self) -> None:
        from .framework_detector import FrameworkDetector
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._detector = FrameworkDetector(self._page, self._cdp)
        self._detector.attach()
        logger.info("DiagnosticSession started id=%s dir=%s",
                     self._session_id, self._dir)

    def finalize(self) -> dict:
        """Detect frameworks, write session.json, return the payload."""
        self._stopped_at = datetime.now(timezone.utc).isoformat()
        framework = self._detector.detect() if self._detector else {}
        if self._detector:
            self._detector.detach()
        try:
            url = self._page.url
        except Exception:
            url = ""
        payload = {
            "session_id": self._session_id,
            "tester_hash": _tester_hash(),
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "app_url_signature": _normalize(url),
            "framework_detection": framework,
            "replay_mode": self._replay_mode,
            "gherkin_lang": self._gherkin_lang,
        }
        out = Path(self._dir) / "session.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        logger.info("DiagnosticSession finalized id=%s primary_framework=%s",
                     self._session_id, framework.get("primary"))
        return payload


def _normalize(url: str) -> str:
    """Reuse the same URL normalization as the Phase 4 SQLite catalog."""
    try:
        from ..healing.sqlite_intent_catalog import normalize_url
        return normalize_url(url)
    except Exception:
        return f"host= path={url}"
