"""TestForge — Raw Recording Store (JSONL persistence)."""
import json
import os
from .raw_event import RawRecordedEvent


class RawRecordingStore:
    def __init__(self, session_dir: str):
        self._session_dir = session_dir
        self._events_path = os.path.join(session_dir, "raw_events.jsonl")
        self._quality_alerts: list[str] = []

    def append_event(self, event: RawRecordedEvent):
        with open(self._events_path, "a") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def save_metadata(self, key: str, data: dict):
        path = os.path.join(self._session_dir, f"{key}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def save_screenshot(self, event_id: str, data: bytes):
        path = os.path.join(self._session_dir, "screenshots", f"{event_id}.png")
        with open(path, "wb") as f:
            f.write(data)
        return os.path.relpath(path, self._session_dir)

    def save_dom(self, event_id: str, html: str) -> str:
        """Save DOM snapshot. Returns relative path, or empty string if DOM is empty."""
        path = os.path.join(self._session_dir, "dom_snapshots", f"{event_id}.html")
        # Validate content before saving — never write empty DOM files
        if not html or len(html.strip()) < 20:
            self._quality_alerts.append(f"DOM_SNAPSHOT_EMPTY:{event_id}")
            return ""
        with open(path, "w") as f:
            f.write(html)
        return os.path.relpath(path, self._session_dir)

    def save_ax_snapshot(self, event_id: str, data: dict):
        path = os.path.join(self._session_dir, "ax_snapshots", f"{event_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return os.path.relpath(path, self._session_dir)

    def save_network_log(self, entries: list):
        path = os.path.join(self._session_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump(entries, f, indent=2, default=str)

    def save_sensitive_data_alert(self, alerts: list):
        path = os.path.join(self._session_dir, "sensitive_data_alert.json")
        data = {
            "policy": "alert_only",
            "masking_applied": False,
            "alerts": alerts,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
