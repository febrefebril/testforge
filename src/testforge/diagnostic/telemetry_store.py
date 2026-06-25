"""Sprint 0 commit 4 — DiagnosticTelemetryStore (E4 hybrid).

JSONL files are the source of truth; OTel-shape spans (via the Phase 6
tracer) carry the same metrics so the existing dashboard can show
diagnostic data with no new consumer logic.

Files written per session:
    session_dir/
    ├── session.json          (one shot, written by DiagnosticSession)
    ├── steps.jsonl           (one line per assess() call)
    ├── replay_check.jsonl    (one line per ReplayCheck record)
    └── scenario.feature      (Gherkin live, written by GherkinWriter)
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class DiagnosticTelemetryStore:
    """JSONL persistence + Phase 6 span emission."""

    def __init__(self, session_dir: str) -> None:
        self._dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
        self._steps_path = os.path.join(session_dir, "steps.jsonl")
        self._replay_path = os.path.join(session_dir, "replay_check.jsonl")
        self._session_path = os.path.join(session_dir, "session.json")
        self._tracer = self._get_tracer_safe()

    # ------------------------------------------------------------------
    @property
    def session_dir(self) -> str:
        return self._dir

    @property
    def steps_path(self) -> str:
        return self._steps_path

    @property
    def replay_path(self) -> str:
        return self._replay_path

    # ------------------------------------------------------------------
    def append_step(self, payload: dict) -> None:
        """Write one step row + emit OTel-shape span."""
        self._append_json(self._steps_path, payload)
        self._emit_span("diagnostic.step", payload)

    def append_replay(self, payload: dict) -> None:
        """Write one replay-check row + emit span."""
        self._append_json(self._replay_path, payload)
        self._emit_span("diagnostic.replay", payload)

    def write_session(self, payload: dict) -> None:
        """Overwrite session.json with the final summary."""
        Path(self._session_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2,
                        default=str),
            encoding="utf-8",
        )

    def files(self) -> dict:
        """Inventory paths (used by the publisher in commit 6)."""
        return {
            "session": self._session_path if os.path.exists(self._session_path) else None,
            "steps": self._steps_path if os.path.exists(self._steps_path) else None,
            "replay": self._replay_path if os.path.exists(self._replay_path) else None,
            "feature": os.path.join(self._dir, "scenario.feature")
                       if os.path.exists(os.path.join(self._dir, "scenario.feature"))
                       else None,
        }

    # ------------------------------------------------------------------
    def _append_json(self, path: str, payload: dict) -> None:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logger.warning("Telemetry append failed (%s): %s", path, exc)

    def _emit_span(self, name: str, payload: dict) -> None:
        if not self._tracer:
            return
        try:
            with self._tracer.start_span(name) as span:
                self._set_span_attrs(span, payload, prefix="")
        except Exception as exc:
            logger.debug("Span emit failed: %s", exc)

    def _set_span_attrs(self, span, payload: dict, prefix: str) -> None:
        for k, v in payload.items():
            key = f"{prefix}{k}" if prefix else k
            if isinstance(v, dict):
                self._set_span_attrs(span, v, prefix=f"{key}.")
            elif isinstance(v, (str, int, float, bool)) or v is None:
                span.set_attribute(key, v)
            elif isinstance(v, list):
                span.set_attribute(key, ",".join(str(x) for x in v[:10]))

    @staticmethod
    def _get_tracer_safe():
        try:
            from ..metrics.telemetry import get_tracer
            return get_tracer()
        except Exception:
            return None
