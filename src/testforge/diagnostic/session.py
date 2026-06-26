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
        # Hotfix 15: snapshots taken before browser.close() so finalize()
        # can still write a complete session.json after the page is gone.
        self._cached_framework: Optional[dict] = None
        self._cached_url: Optional[str] = None
        # Totals updated as steps stream in
        self._totals = {
            "steps": 0, "asserts": 0,
            "value_captured": 0, "value_missing": 0,
            "selectors_generated": 0,
            "selectors_immediate_ok": 0, "selectors_immediate_fail": 0,
            "blind_spots": 0,
        }

    def start(self) -> None:
        from .capture_quality import CaptureQualityTracker
        from .framework_detector import FrameworkDetector
        from .gherkin_writer import GherkinWriter
        from .replay_check import ReplayCheck
        from .telemetry_store import DiagnosticTelemetryStore
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._detector = FrameworkDetector(self._page, self._cdp)
        self._detector.attach()
        self._tracker = CaptureQualityTracker()
        self._replay = ReplayCheck(self._page, mode=self._replay_mode)
        self._gherkin = GherkinWriter(self._dir, lang=self._gherkin_lang)
        self._store = DiagnosticTelemetryStore(self._dir)
        logger.info("DiagnosticSession started id=%s dir=%s replay=%s",
                     self._session_id, self._dir, self._replay_mode)

    # ------------------------------------------------------------------
    def on_navigation(self, url: str, title: Optional[str] = None) -> None:
        if self._gherkin is not None:
            self._gherkin.on_navigation(url, title)

    def assess_event(self, raw_event: dict, target_data: Optional[dict] = None,
                     candidates: Optional[list] = None) -> dict:
        """Called by RecorderController after each _persist_raw_event."""
        if self._tracker is None or self._store is None:
            return {}
        framework = self._detector.detect() if self._detector else None
        payload = self._tracker.assess(
            raw_event, target_data=target_data,
            candidates=candidates, framework=framework,
        )
        self._store.append_step(payload)
        # Update totals
        self._totals["steps"] += 1
        action = (raw_event.get("type") or "").lower()
        if action == "assert":
            self._totals["asserts"] += 1
        cq = payload.get("capture_quality") or {}
        if cq.get("value_captured_at_event"):
            self._totals["value_captured"] += 1
        else:
            self._totals["value_missing"] += 1
        sg = payload.get("selector_generated") or {}
        if sg.get("primary"):
            self._totals["selectors_generated"] += 1
        self._totals["blind_spots"] += len(payload.get("blind_spots") or [])
        # Gherkin live
        if self._gherkin is not None:
            self._gherkin.on_step(
                action=action, target=target_data or {},
                value=raw_event.get("value"),
            )
        # Replay check
        if self._replay is not None and candidates:
            rec = self._replay.check(payload.get("step_id") or raw_event.get("event_id"),
                                       candidates)
            if rec is not None:
                self._store.append_replay(rec)
                if rec.get("resolved"):
                    self._totals["selectors_immediate_ok"] += 1
                else:
                    self._totals["selectors_immediate_fail"] += 1
        return payload

    def precapture_for_close(self) -> None:
        """Hotfix 15: snapshot anything that requires a live page now, so
        finalize() can run after the browser has already been closed."""
        if self._cached_framework is not None:
            return
        try:
            self._cached_framework = (
                self._detector.detect() if self._detector else {}
            )
        except Exception as exc:
            logger.warning(
                "precapture_for_close: framework detect failed: %s", exc
            )
            self._cached_framework = {}
        try:
            self._cached_url = self._page.url
        except Exception:
            self._cached_url = ""

    def finalize(self,
                 funcionalidade_override: str = "",
                 cenario_override: str = "") -> dict:
        """Detect frameworks, write session.json, return the payload."""
        self._stopped_at = datetime.now(timezone.utc).isoformat()
        # Use the value snapshotted by precapture_for_close() if the browser
        # has already gone away; fall back to a live detect otherwise.
        if self._cached_framework is not None:
            framework = self._cached_framework
        else:
            framework = self._detector.detect() if self._detector else {}
        if self._detector:
            self._detector.detach()
        # Drain batched replay queue if any
        if self._replay is not None:
            for rec in self._replay.drain():
                if self._store is not None:
                    self._store.append_replay(rec)
        # Write Gherkin
        feature_path = ""
        if self._gherkin is not None:
            feature_path = self._gherkin.write(
                funcionalidade_override=funcionalidade_override,
                cenario_override=cenario_override,
            )
        if self._cached_url is not None:
            url = self._cached_url
        else:
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
            "totals": self._totals,
            "feature_path": feature_path,
        }
        if self._store is not None:
            self._store.write_session(payload)
        else:
            out = Path(self._dir) / "session.json"
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        logger.info("DiagnosticSession finalized id=%s primary_framework=%s steps=%d",
                     self._session_id, framework.get("primary"),
                     self._totals["steps"])
        return payload

    @property
    def gherkin(self):
        return self._gherkin

    @property
    def store(self):
        return self._store

    @property
    def totals(self) -> dict:
        return dict(self._totals)


def _normalize(url: str) -> str:
    """Reuse the same URL normalization as the Phase 4 SQLite catalog."""
    try:
        from ..healing.sqlite_intent_catalog import normalize_url
        return normalize_url(url)
    except Exception:
        return f"host= path={url}"
