"""TestForge — Gerenciamento de Sessão de Gravação."""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .recording_status import RecordingStatus, RecordingStatusHistory

logger = logging.getLogger(__name__)


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
    status_history: RecordingStatusHistory = field(
        default_factory=RecordingStatusHistory
    )

    @property
    def recording_status(self) -> Optional[RecordingStatus]:
        """Obtém RecordingStatus atual (semântico) do histórico."""
        return self.status_history.current

    @recording_status.setter
    def recording_status(self, value: RecordingStatus):
        """Define RecordingStatus atual e registra no histórico."""
        self.status_history.record(value, reason=f"set to {value.value}")

    def to_metadata_dict(self) -> dict:
        """Serializa sessão para dict de metadados incluindo histórico de status."""
        return {
            "recording_id": self.recording_id,
            "application": self.application,
            "base_url": self.base_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "recording_status": (
                self.recording_status.value if self.recording_status else None
            ),
            "status_history": self.status_history.to_dict() if self.status_history.entries else [],
        }


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

    def start(self, recording_id: str, application: str = "",
              base_url: str = "") -> RecordingSession:
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

        session.status_history.record(
            RecordingStatus.recording,
            reason="Recording started",
            metadata={"application": application, "base_url": base_url},
        )

        metadata = session.to_metadata_dict()
        metadata_path = os.path.join(session_dir, "recording_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        session.metadata_path = metadata_path
        self._active_session = session
        logger.info("Session started id=%s app=%s url=%s dir=%s",
                     recording_id, application, base_url, session_dir)
        return session

    def stop(self) -> RecordingSession:
        if not self._active_session:
            raise RuntimeError("Nenhuma sessao ativa")
        session = self._active_session
        session.finished_at = datetime.now(timezone.utc).isoformat()
        session.status = "stopped"
        session.status_history.record(
            RecordingStatus.stopped,
            reason="Recording stopped by user",
        )
        self._update_metadata(session)
        elapsed = ""
        if session.started_at and session.finished_at:
            try:
                s = datetime.fromisoformat(session.started_at)
                f = datetime.fromisoformat(session.finished_at)
                elapsed = f" duration={(f-s).total_seconds():.1f}s"
            except: pass
        logger.info("Session stopped id=%s%s", session.recording_id, elapsed)
        return session

    def finalize(self, recording_status: Optional[RecordingStatus] = None) -> RecordingSession:
        if not self._active_session:
            raise RuntimeError("Nenhuma sessao ativa")
        session = self._active_session
        session.status = "completed"

        # Use provided semantic status or default to completed_raw
        final_status = recording_status or RecordingStatus.completed_raw
        session.status_history.record(
            final_status,
            reason="Recording finalized",
        )
        session.status_history.lock()

        self._update_metadata(session)
        self._active_session = None
        return session

    def update_recording_status(self, status: RecordingStatus, reason: str = "",
                                 metadata: Optional[dict] = None) -> None:
        """Update the recording status in metadata and history.

        Can be called after finalization (no active session) to update
        e.g. from intent_reconstructed -> needs_user_input -> intent_complete.
        """
        # Try active session first, then scan recordings
        session = self._active_session
        if session:
            session.status_history.record(status, reason=reason, metadata=metadata)
            self._update_metadata(session)
            return

    def update_metadata_status(self, recording_id: str, status: RecordingStatus,
                                reason: str = "") -> bool:
        """Update metadata file directly for a finalized recording."""
        session_dir = os.path.join(self._recordings_root, recording_id)
        meta_path = os.path.join(session_dir, "recording_metadata.json")
        if not os.path.exists(meta_path):
            return False

        with open(meta_path) as f:
            metadata = json.load(f)

        if "status_history" not in metadata:
            metadata["status_history"] = []

        metadata["status_history"].append({
            "status": status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "metadata": {},
        })
        metadata["recording_status"] = status.value
        metadata["status"] = status.value

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)
        return True

    @property
    def active_session(self) -> Optional[RecordingSession]:
        return self._active_session

    def _update_metadata(self, session: RecordingSession):
        if session.metadata_path:
            with open(session.metadata_path, "w") as f:
                json.dump(session.to_metadata_dict(), f, indent=2, default=str)

    @staticmethod
    def load_metadata(recording_dir: str) -> Optional[dict]:
        """Load recording metadata from a directory."""
        meta_path = os.path.join(recording_dir, "recording_metadata.json")
        if not os.path.exists(meta_path):
            return None
        with open(meta_path) as f:
            return json.load(f)
