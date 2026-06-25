"""Phase 5: Pipes & Filters refactor of `RecordingNormalizer`.

The legacy `RecordingNormalizer.normalize()` is a 1.4 K-line god method
that interleaves IO, deduplication, compaction, semantic conversion,
intent reconstruction, post-processing and auditing. This package
breaks it into testable stages with a shared `Context` object.

Stages implemented in Phase 5 (lowest-risk first):

    LoadStage       reads raw_events.jsonl into Context.raw_events
    DedupStage      removes periodic snapshot cycles
    CompactStage    collapses keypress sequences and fill events
    AuditStage      blind-spot audit (terminal)

Stages NOT extracted yet (next sprint): convert, intent reconstruction,
post-process. They remain inside `RecordingNormalizer`, called by the
orchestrator after the extracted stages run.

Opt in via `RecordingNormalizer(use_pipeline=True)`. Output must match
the legacy path exactly — covered by the parity test suite.
"""
from .base import Pipeline, Stage
from .context import NormalizationContext
from .stage_audit import AuditStage
from .stage_compact import CompactStage
from .stage_dedup import DedupStage
from .stage_load import LoadStage

__all__ = [
    "Pipeline",
    "Stage",
    "NormalizationContext",
    "AuditStage",
    "CompactStage",
    "DedupStage",
    "LoadStage",
]
