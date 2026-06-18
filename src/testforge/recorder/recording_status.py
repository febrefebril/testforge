"""TestForge — Recording Status Enum and History.

Formal states for recording lifecycle. Prevents incomplete recordings
from being treated as ready.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class RecordingStatus(str, Enum):
    """Formal recording status with semantic meaning for readiness gates.

    State machine (forward transitions):
        completed_raw
            → intent_reconstructed  (normalizer ran)
            → needs_user_input      (missing fields detected)
            → intent_complete       (all fields resolved)
            → incremental_validation_running
            → incrementally_validated
            → ready_for_team        (final pass)

    Alternative terminal states:
        incomplete_intent  (recording has unresolved fields, cannot be compiled)
        needs_review       (validation failed or user supplied values misapplied)
    """
    # --- Recording phase ---
    completed_raw = "completed_raw"
    intent_reconstructed = "intent_reconstructed"
    needs_user_input = "needs_user_input"
    intent_complete = "intent_complete"
    incremental_validation_running = "incremental_validation_running"
    incrementally_validated = "incrementally_validated"
    ready_for_team = "ready_for_team"

    # --- Terminal / error states ---
    incomplete_intent = "incomplete_intent"
    needs_review = "needs_review"

    # --- Legacy aliases (backward compat) ---
    idle = "idle"
    recording = "recording"
    stopped = "stopped"
    completed = "completed"

    @classmethod
    def terminal_states(cls) -> set:
        """States that indicate recording is ready for team or needs intervention."""
        return {cls.ready_for_team, cls.incomplete_intent, cls.needs_review}

    @classmethod
    def blocked_compile_states(cls) -> set:
        """States that BLOCK compilation. Cannot produce test script."""
        return {cls.incomplete_intent, cls.needs_review}

    @classmethod
    def active_states(cls) -> set:
        """States where recording is in progress (not terminal)."""
        return {
            cls.completed_raw, cls.intent_reconstructed, cls.needs_user_input,
            cls.intent_complete, cls.incremental_validation_running,
            cls.incrementally_validated,
        }


@dataclass
class RecordingStatusEntry:
    """Single entry in status history."""
    status: RecordingStatus
    timestamp: str = ""
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RecordingStatusHistory:
    """Auditable trail of status transitions."""
    entries: list = field(default_factory=list)
    _locked: bool = False

    def record(self, status: RecordingStatus, reason: str = "",
               metadata: Optional[dict] = None) -> RecordingStatusEntry:
        """Record a status transition. Raises if history is locked."""
        if self._locked:
            raise RuntimeError("Status history is locked — recording finalized.")
        entry = RecordingStatusEntry(
            status=status,
            reason=reason,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        return entry

    @property
    def current(self) -> Optional[RecordingStatus]:
        """Most recent status, or None if no entries."""
        if not self.entries:
            return None
        return self.entries[-1].status

    @property
    def current_entry(self) -> Optional[RecordingStatusEntry]:
        """Most recent entry, or None."""
        if not self.entries:
            return None
        return self.entries[-1]

    def lock(self):
        """Lock history — no more transitions allowed."""
        self._locked = True

    def to_dict(self) -> list:
        """Serialize to JSON-friendly list."""
        return [
            {
                "status": e.status.value,
                "timestamp": e.timestamp,
                "reason": e.reason,
                "metadata": e.metadata,
            }
            for e in self.entries
        ]

    @staticmethod
    def from_dict(data: list) -> "RecordingStatusHistory":
        """Deserialize from list of dicts."""
        history = RecordingStatusHistory()
        for entry in data:
            history.entries.append(RecordingStatusEntry(
                status=RecordingStatus(entry["status"]),
                timestamp=entry.get("timestamp", ""),
                reason=entry.get("reason", ""),
                metadata=entry.get("metadata", {}),
            ))
        return history
