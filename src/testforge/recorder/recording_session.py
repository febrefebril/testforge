"""TestForge — Recording Session management."""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RecordingSession:
    recording_id: str
    application: str = ""
    base_url: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str = "idle"
    metadata_path: Optional[str] = None
    session_dir: Optional[str] = None


class RecordingSessionManager:
    def __init__(self, recordings_root: str = "recordings"):
        self._recordings_root = recordings_root
        self._active_session: Optional[RecordingSession] = None

    @staticmethod
    def _resolve_name(recordings_root: str, base_name: str) -> str:
        """Find next available recording name.

        If recordings/{base_name} does not exist, returns base_name.
        Otherwise returns base_name_2, base_name_3, etc.
        """
        if not os.path.isdir(os.path.join(recordings_root, base_name)):
            return base_name
        i = 2
        while True:
            candidate = f"{base_name}_{i}"
            if not os.path.isdir(os.path.join(recordings_root, candidate)):
                return candidate
            i += 1

    def start(self, recording_id: str, application: str = "", base_url: str = "") -> RecordingSession:
        if self._active_session and self._active_session.status in ("recording", "paused"):
            raise RuntimeError(f"Sessao ativa: {self._active_session.recording_id}")

        recording_id = self._resolve_name(self._recordings_root, recording_id)
        session_dir = os.path.join(self._recordings_root, recording_id)
        os.makedirs(session_dir, exist_ok=True)
        os.makedirs(os.path.join(session_dir, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "dom_snapshots"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "ax_snapshots"), exist_ok=True)

        session = RecordingSession(
            recording_id=recording_id,
            application=application,
            base_url=base_url,
            started_at=datetime.now(timezone.utc).isoformat(),
            status="recording",
            session_dir=session_dir,
        )

        metadata = {
            "recording_id": recording_id,
            "application": application,
            "base_url": base_url,
            "started_at": session.started_at,
            "status": "recording",
        }
        metadata_path = os.path.join(session_dir, "recording_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        session.metadata_path = metadata_path
        self._active_session = session
        return session

    def stop(self) -> RecordingSession:
        if not self._active_session:
            raise RuntimeError("Nenhuma sessao ativa")
        session = self._active_session
        session.finished_at = datetime.now(timezone.utc).isoformat()
        session.status = "stopped"
        self._update_metadata(session)
        return session

    def finalize(self) -> RecordingSession:
        if not self._active_session:
            raise RuntimeError("Nenhuma sessao ativa")
        session = self._active_session
        session.status = "completed"
        self._update_metadata(session)
        self._active_session = None
        return session

    @property
    def active_session(self) -> Optional[RecordingSession]:
        return self._active_session

    def _update_metadata(self, session: RecordingSession):
        if session.metadata_path:
            with open(session.metadata_path, "w") as f:
                json.dump({
                    "recording_id": session.recording_id,
                    "application": session.application,
                    "base_url": session.base_url,
                    "started_at": session.started_at,
                    "finished_at": session.finished_at,
                    "status": session.status,
                }, f, indent=2, default=str)
