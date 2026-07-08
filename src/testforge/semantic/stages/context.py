"""Phase 5: Shared context object threaded through the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..model import SemanticTestCase


@dataclass
class NormalizationContext:
    """Mutable state passed between stages.

    A stage reads what it needs and writes the next stage's input. Keeping
    the context flat (not nested) avoids accidental cross-stage coupling.
    """
    recording_dir: str
    test_id: str = ""
    application: str = ""
    base_url: str = ""

    # Populated by LoadStage
    raw_events: list = field(default_factory=list)
    initial_event_count: int = 0

    # Populated by Convert (still in RecordingNormalizer)
    test_case: Optional[SemanticTestCase] = None

    # Filled by AuditStage and any audit-adjacent step
    blind_spots: list = field(default_factory=list)

    # Free-form telemetry for stages that want to record counts
    stats: dict = field(default_factory=dict)
