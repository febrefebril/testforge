"""Phase 5: DedupStage — delegates to RecordingNormalizer._remove_snapshot_duplicates.

Mechanical extraction. The actual deduplication logic stays in the
legacy module to avoid duplicating heuristics; the stage is a thin
wrapper that calls it. Future work can fully inline the logic here.
"""
from __future__ import annotations

import logging

from .base import Stage
from .context import NormalizationContext

logger = logging.getLogger(__name__)


class DedupStage(Stage):
    name = "dedup"

    def __init__(self, normalizer) -> None:
        # Avoid circular import: type hinting only.
        self._normalizer = normalizer

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        pre = len(ctx.raw_events)
        ctx.raw_events = self._normalizer._remove_snapshot_duplicates(ctx.raw_events)
        post = len(ctx.raw_events)
        ctx.stats["dedup_removed"] = pre - post
        logger.debug("DedupStage: %d -> %d (-%d)", pre, post, pre - post)
        return ctx
