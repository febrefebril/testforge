"""TestForge — ReplayRecorder.

Captura telemetria de execução no mesmo formato da gravação original
(raw_events.jsonl, field_snapshots.jsonl, network_log.json, screenshots,
dom_snapshots) para que a execução possa ser diferenciada da gravação original.

Uso:
    recorder = ReplayRecorder(page, recording_id, output_root="recordings")
    recorder.start()
    # ... executar passos de teste ...
    recorder.capture_step(i, step, page)
    recorder.finish()
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, Request, Response


class ReplayRecorder:
    """Captura telemetria de execução em formato compatível com gravação."""

    def __init__(
        self,
        page: Page,
        recording_id: str,
        output_root: str = "recordings",
    ):
        self._page = page
        self._recording_id = recording_id
        self._output_root = Path(output_root)
        self._session_dir: Optional[Path] = None
        self._network_entries: list = []
        self._started_at: Optional[str] = None
        self._step_counter = 0
        self._listeners_active = False

    @property
    def session_dir(self) -> Optional[Path]:
        return self._session_dir

    def start(self) -> Path:
        """Cria diretório de sessão de captura, inicia listeners de rede."""
        self._started_at = datetime.now(timezone.utc).isoformat()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_dir = (
            self._output_root / self._recording_id / "capture_runs" / f"run_{ts}"
        )
        self._session_dir.mkdir(parents=True, exist_ok=True)
        (self._session_dir / "screenshots").mkdir(exist_ok=True)
        (self._session_dir / "dom_snapshots").mkdir(exist_ok=True)
        (self._session_dir / "field_snapshots").mkdir(exist_ok=True)

        # Start network capture
        self._network_entries = []
        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)
        self._listeners_active = True

        # Write session metadata
        meta = {
            "capture_id": f"replay_{ts}",
            "recording_id": self._recording_id,
            "started_at": self._started_at,
            "type": "replay_capture",
            "page_url": self._page.url,
        }
        self._write_json("capture_metadata.json", meta)

        return self._session_dir

    def finish(self) -> dict:
        """Finalize capture: save network log, write summary."""
        self._remove_listeners()
        finished_at = datetime.now(timezone.utc).isoformat()

        # Save network log
        self._write_json("network_log.json", self._network_entries)

        # Save metadata with end time
        meta_path = self._session_dir / "capture_metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
        else:
            meta = {}
        meta["finished_at"] = finished_at
        meta["steps_captured"] = self._step_counter
        self._write_json("capture_metadata.json", meta)

        return {
            "session_dir": str(self._session_dir),
            "steps_captured": self._step_counter,
            "network_entries": len(self._network_entries),
        }

    def capture_step(self, step_index: int, step, status: str = "",
                     error_message: str = "") -> None:
        """Capture telemetry for one step execution."""
        self._step_counter += 1
        step_num = step_index + 1
        ts = datetime.now(timezone.utc).isoformat()

        # 1. DOM snapshot before action
        dom_path = self._capture_dom(f"step_{step_num:04d}_before")

        # 2. Field snapshot before action
        fields_before = self._capture_fields()

        # 3. Screenshot after action
        screenshot_path = self._capture_screenshot(f"step_{step_num:04d}")

        # 4. Field snapshot after action
        fields_after = self._capture_fields()

        # 5. Write step event to raw_events.jsonl
        event = {
            "event_id": f"replay_step_{self._step_counter:05d}",
            "type": "replay_step",
            "timestamp": ts,
            "step_num": step_num,
            "action": getattr(step, "action", ""),
            "value": getattr(step, "value", ""),
            "selector": self._resolve_selector(step),
            "status": status,
            "error_message": error_message,
            "screenshot": screenshot_path,
            "dom_snapshot": dom_path,
            "url": self._page.url,
            "page_title": self._page.title(),
        }
        self._append_jsonl("raw_events.jsonl", event)

        # 6. Write field snapshots
        self._append_jsonl("field_snapshots.jsonl", {
            "capture_type": "step_fields",
            "step_num": step_num,
            "timestamp": ts,
            "fields_before": fields_before,
            "fields_after": fields_after,
        })

        # Also save per-step field snapshot as individual JSON
        self._write_json(
            f"field_snapshots/step_{step_num:04d}.json",
            {"step_num": step_num, "before": fields_before, "after": fields_after},
        )

    # --- Internal ---

    def _on_request(self, request: Request):
        post_data = None
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                post_data = request.post_data
        except Exception:
            pass
        self._network_entries.append({
            "type": "request",
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "post_data": post_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_response(self, response: Response):
        self._network_entries.append({
            "type": "response",
            "url": response.url,
            "status": response.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _remove_listeners(self):
        if self._listeners_active:
            try:
                self._page.remove_listener("request", self._on_request)
            except Exception:
                pass
            try:
                self._page.remove_listener("response", self._on_response)
            except Exception:
                pass
            self._listeners_active = False

    def _capture_dom(self, name: str) -> str:
        """Capture DOM snapshot, return relative path or empty."""
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        try:
            html = self._page.content()
            if not html or len(html.strip()) < 20:
                return ""
            path = self._session_dir / "dom_snapshots" / f"{name}.html"
            path.write_text(html, encoding="utf-8")
            return str(path.relative_to(self._session_dir))
        except Exception:
            return ""

    def _capture_screenshot(self, name: str) -> str:
        """Capture screenshot, return relative path or empty."""
        try:
            data = self._page.screenshot(type="png", full_page=False)
            path = self._session_dir / "screenshots" / f"{name}.png"
            path.write_bytes(data)
            return str(path.relative_to(self._session_dir))
        except Exception:
            return ""

    def _capture_fields(self) -> list:
        """Capture current field values from the page."""
        try:
            fields = self._page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    const tag = el.tagName.toLowerCase();
                    const rect = el.getBoundingClientRect();
                    results.push({
                        tag: tag,
                        name: el.name || null,
                        id: el.id || null,
                        placeholder: el.placeholder || null,
                        'aria-label': el.getAttribute('aria-label') || null,
                        type: el.getAttribute('type') || null,
                        value: (el.value || '').substring(0, 200),
                        checked: (el.type === 'checkbox' || el.type === 'radio') ? el.checked : null,
                        visible: (rect.width > 0 && rect.height > 0),
                        enabled: !el.disabled,
                        focused: el === document.activeElement,
                    });
                });
                return results;
            }""")
            return fields or []
        except Exception:
            return []

    def _resolve_selector(self, step) -> str:
        """Extract primary selector from step."""
        try:
            if hasattr(step, "target") and step.target:
                if step.target.candidates:
                    return step.target.candidates[0].selector or ""
                if hasattr(step.target, "css_path") and step.target.css_path:
                    return step.target.css_path
            return getattr(step, "selector", "")
        except Exception:
            return ""

    def _write_json(self, name: str, data):
        path = self._session_dir / name
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _append_jsonl(self, name: str, data):
        path = self._session_dir / name
        with open(path, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")
