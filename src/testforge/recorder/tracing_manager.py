"""TestForge — Phase 1: Playwright Tracing Manager.

Wraps `BrowserContext.tracing` to produce a Playwright-native trace.zip
per recording session. The zip contains DOM snapshots (before/at/after each
action), network, console, screenshots, and sources — viewable at
https://trace.playwright.dev without any installation.

This is the modern replacement for our hand-rolled DOM/screenshot snapshot
pipeline. We keep both paths during Phase 1; the legacy path is removed
in Phase 2 once the extractor consumes the trace artifacts.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TracingManager:
    """Encapsulates Playwright tracing lifecycle for a single recording.

    Usage:
        tm = TracingManager(page)
        tm.start(session_dir, recording_id)
        # ... user interacts ...
        tm.stop()  # writes <session_dir>/trace.zip
    """

    def __init__(self, page) -> None:
        self._page = page
        self._context = page.context
        self._session_dir: Optional[str] = None
        self._recording_id: Optional[str] = None
        self._started = False
        self._chunked = False

    def start(
        self,
        session_dir: str,
        recording_id: str,
        screenshots: bool = True,
        snapshots: bool = True,
        sources: bool = True,
    ) -> None:
        """Start a fresh trace. Safe to call once per session."""
        if self._started:
            logger.warning("TracingManager.start called twice; ignoring")
            return
        self._session_dir = session_dir
        self._recording_id = recording_id
        try:
            self._context.tracing.start(
                name=recording_id,
                screenshots=screenshots,
                snapshots=snapshots,
                sources=sources,
            )
            self._started = True
            logger.info(
                "Tracing started (snapshots=%s screenshots=%s sources=%s) for %s",
                snapshots, screenshots, sources, recording_id,
            )
        except Exception as exc:
            logger.error("TracingManager.start failed: %s", exc, exc_info=True)

    def chunk(self, label: str) -> None:
        """Optional: split the trace at meaningful boundaries (page nav)."""
        if not self._started:
            return
        try:
            self._context.tracing.start_chunk(name=label)
            self._chunked = True
        except Exception:
            pass

    def stop(self) -> Optional[str]:
        """Stop tracing and write trace.zip into the session directory."""
        if not self._started or not self._session_dir:
            return None
        out_path = Path(self._session_dir) / "trace.zip"
        try:
            os.makedirs(self._session_dir, exist_ok=True)
            self._context.tracing.stop(path=str(out_path))
            self._started = False
            logger.info("Tracing stopped; trace.zip at %s", out_path)
            return str(out_path)
        except Exception as exc:
            # Hotfix 22: TargetClosedError comum quando usuario fecha browser
            # antes do Shift+S. Rebaixado para warning — trace.zip nao vira
            # nesse caso mas isso nao eh erro fatal (recording ja salvou tudo
            # via overlay). Outros erros continuam como ERROR full traceback.
            msg = str(exc) or exc.__class__.__name__
            if "TargetClosedError" in exc.__class__.__name__ or "Target page" in msg or "browser has been closed" in msg:
                logger.warning("Tracing.stop skipped: browser already closed — trace.zip not written")
            else:
                logger.error("TracingManager.stop failed: %s", exc, exc_info=True)
            self._started = False
            return None

    @property
    def is_active(self) -> bool:
        return self._started
