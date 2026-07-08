"""Phase 5: LoadStage — read raw_events.jsonl into Context.raw_events."""
from __future__ import annotations

import json
import logging
import os

from .base import Stage
from .context import NormalizationContext

logger = logging.getLogger(__name__)


class LoadStage(Stage):
    name = "load"

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        events_path = os.path.join(ctx.recording_dir, "raw_events.jsonl")
        if not os.path.exists(events_path):
            raise FileNotFoundError(f"raw_events.jsonl not found in {ctx.recording_dir}")
        with open(events_path, encoding="utf-8") as f:
            ctx.raw_events = [json.loads(line) for line in f if line.strip()]
        ctx.initial_event_count = len(ctx.raw_events)
        type_counts: dict[str, int] = {}
        for ev in ctx.raw_events:
            t = ev.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        ctx.stats["initial_type_counts"] = type_counts
        logger.info(
            "LoadStage: read %d raw events from %s",
            ctx.initial_event_count, os.path.basename(ctx.recording_dir),
        )
        return ctx
