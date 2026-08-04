
"""Runtime anomaly detector used during recording sessions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from playwright.sync_api import ConsoleMessage, Page, Response

from ..models.bug_report import BugSignal

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Subscribe to page events and emit anomaly signals via callback."""

    def __init__(self, page: Page, on_signal: Callable[[BugSignal], None]):
        self._page = page
        self._on_signal = on_signal
        self._last_action_ts: Optional[datetime] = None
        self._last_action_target: Optional[str] = None
        self._register_listeners()

    def _register_listeners(self):
        self._page.on("console", self._on_console)
        self._page.on("pageerror", self._on_page_error)
        self._page.on("crash", self._on_page_crash)
        self._page.on("response", self._on_response)

    def _on_console(self, msg: ConsoleMessage):
        if getattr(msg, "type", "") in ("error", "assert"):
            self._emit(
                BugSignal(
                    type="console_error",
                    timestamp=self._now_iso(),
                    payload={
                        "level": getattr(msg, "type", "unknown"),
                        "text": getattr(msg, "text", ""),
                        "location": str(getattr(msg, "location", "")),
                    },
                )
            )

    def _on_page_error(self, exception):
        self._emit(
            BugSignal(
                type="page_error",
                timestamp=self._now_iso(),
                payload={"error": str(exception)},
            )
        )

    def _on_page_crash(self):
        self._emit(
            BugSignal(type="page_crash", timestamp=self._now_iso(), payload={})
        )

    def _on_response(self, response: Response):
        status = getattr(response, "status", 0)
        if status >= 400:
            self._emit(
                BugSignal(
                    type=f"network_{status // 100}xx",
                    timestamp=self._now_iso(),
                    payload={
                        "url": getattr(response, "url", ""),
                        "status": status,
                        "method": getattr(getattr(response, "request", None), "method", ""),
                        "body_snippet": self._safe_body_snippet(response),
                    },
                )
            )

    def notify_action(self, target_desc: str):
        self._last_action_ts = datetime.now(timezone.utc)
        self._last_action_target = target_desc

    def check_dom_expectation(self, expected: dict, timeout_ms: int = 3000):
        role = expected.get("role")
        if role:
            self._page.wait_for_selector(f'[role="{role}"]', timeout=timeout_ms)

    def _emit(self, signal: BugSignal):
        logger.info("anomaly signal: %s", signal.type)
        self._on_signal(signal)

    def _safe_body_snippet(self, response: Response) -> str:
        try:
            body = response.body() or b""
            return body[:500].decode("utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

