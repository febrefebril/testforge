"""
TestForge — Recording Manager
Handles saving, loading, and listing recording JSON files.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

RECORDINGS_DIR = Path("recordings")


def _safe_filename(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_") or "recording"


def save_recording(recording: dict[str, Any], output_path: Path | None = None) -> Path:
    """Persist a recording dict to JSON. Returns the path written."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        name = _safe_filename(recording.get("meta", {}).get("name", "recording"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RECORDINGS_DIR / f"{name}_{ts}.json"

    # Add saved_at timestamp
    recording["saved_at"] = datetime.now().isoformat()

    output_path.write_text(
        json.dumps(recording, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_recording(path: Path) -> dict[str, Any]:
    """Load a recording from JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def list_recordings() -> list[Path]:
    """Return all recording JSON files sorted by modification time."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(RECORDINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
