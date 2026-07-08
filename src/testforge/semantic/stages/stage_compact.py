"""Phase 5: CompactStage — runs keypress sequence + fill event collapse.

Delegates to the legacy normalizer methods to preserve identical
behavior. The stage exists so a future change to compaction is
localized to a single class.
"""
from __future__ import annotations

import logging

from .base import Stage
from .context import NormalizationContext

logger = logging.getLogger(__name__)


class CompactStage(Stage):
    name = "compact"

    def __init__(self, normalizer) -> None:
        self._normalizer = normalizer

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        pre = len(ctx.raw_events)
        # Collapse individual-key keypress sequences first so that
        # fill-event compaction sees the rebuilt typed strings.
        ctx.raw_events = self._normalizer._compact_keypress_sequences(ctx.raw_events)
        ctx.raw_events = self._normalizer._compact_fill_events(ctx.raw_events)
        post = len(ctx.raw_events)
        ctx.stats["compact_removed"] = pre - post
        logger.info(
            "CompactStage: %d -> %d (reduced %d%%)",
            pre, post, int((1 - post / max(pre, 1)) * 100),
        )
        return ctx
