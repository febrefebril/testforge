"""TestForge — Status Enum e Histórico de Gravação.

Estados formais para ciclo de vida de gravação. Evita que gravações incompletas
sejam tratadas como prontas.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# REC-81: legacy status strings from pre-schema-4 recordings.
# normalize() in RecordingStatus maps these to current canonical values.
# Defined OUTSIDE the enum to prevent enum-member auto-registration.
_LEGACY_STATUS_MAP = {
    "completed": "intent_complete",
    "completed_raw": "stopped",
}


class RecordingStatus(str, Enum):
    """Status formal de gravação com significado semântico para gates de prontidão.
    ...
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
        """Estados que indicam gravação pronta para o time ou precisa de intervenção."""
        return {cls.ready_for_team, cls.incomplete_intent, cls.needs_review}

    @classmethod
    def blocked_compile_states(cls) -> set:
        """Estados que BLOQUEIAM compilação. Não pode produzir script de teste."""
        return {cls.incomplete_intent, cls.needs_review}

    @classmethod
    def active_states(cls) -> set:
        """Estados onde gravação está em andamento (não terminal)."""
        return {
            cls.completed_raw, cls.intent_reconstructed, cls.needs_user_input,
            cls.intent_complete, cls.incremental_validation_running,
            cls.incrementally_validated,
        }

    @classmethod
    def normalize(cls, value: str) -> "RecordingStatus":
        """Map legacy status strings to current enum values.
        
        Returns canonical RecordingStatus for known legacy values;
        falls back to incomplete_intent for unrecognized strings.
        """
        mapped = _LEGACY_STATUS_MAP.get(value, value)
        try:
            return cls(mapped)
        except ValueError:
            return cls.incomplete_intent


@dataclass
class RecordingStatusEntry:
    """Entrada única no histórico de status."""
    status: RecordingStatus
    timestamp: str = ""
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RecordingStatusHistory:
    """Trilha auditável de transições de status."""
    entries: list = field(default_factory=list)
    _locked: bool = False

    def record(self, status: RecordingStatus, reason: str = "",
               metadata: Optional[dict] = None) -> RecordingStatusEntry:
        """Registra uma transição de status. Lança erro se histórico está bloqueado."""
        if self._locked:
            raise RuntimeError("Histórico de status está bloqueado — gravação finalizada.")
        entry = RecordingStatusEntry(
            status=status,
            reason=reason,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        return entry

    @property
    def current(self) -> Optional[RecordingStatus]:
        """Status mais recente, ou None se sem entradas."""
        if not self.entries:
            return None
        return self.entries[-1].status

    @property
    def current_entry(self) -> Optional[RecordingStatusEntry]:
        """Entrada mais recente, ou None."""
        if not self.entries:
            return None
        return self.entries[-1]

    def lock(self):
        """Bloqueia histórico — não são permitidas mais transições."""
        self._locked = True

    def to_dict(self) -> list:
        """Serializa para lista compatível com JSON."""
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
        """Desserializa da lista de dicionários."""
        history = RecordingStatusHistory()
        for entry in data:
            history.entries.append(RecordingStatusEntry(
                status=RecordingStatus(entry["status"]),
                timestamp=entry.get("timestamp", ""),
                reason=entry.get("reason", ""),
                metadata=entry.get("metadata", {}),
            ))
        return history
