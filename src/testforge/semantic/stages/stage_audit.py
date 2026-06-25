"""Phase 5: AuditStage — terminal blind-spot audit.

Delegates to the legacy `_audit_blind_spots` so that the resulting
`SemanticTestCase.blind_spots` list is byte-identical to the
legacy path.
"""
from __future__ import annotations

import logging

from .base import Stage
from .context import NormalizationContext

logger = logging.getLogger(__name__)


class AuditStage(Stage):
    name = "audit"

    def __init__(self, normalizer) -> None:
        self._normalizer = normalizer

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        if ctx.test_case is None:
            logger.warning("AuditStage skipped: ctx.test_case is None")
            return ctx
        self._normalizer._audit_blind_spots(ctx.test_case)
        ctx.blind_spots = list(getattr(ctx.test_case, "blind_spots", []) or [])
        ctx.stats["blind_spot_count"] = len(ctx.blind_spots)
        logger.debug("AuditStage: %d blind spots", len(ctx.blind_spots))
        return ctx
