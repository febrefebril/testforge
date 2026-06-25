"""Phase 5: Pipeline + Stage base classes."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable

from .context import NormalizationContext

logger = logging.getLogger(__name__)


class Stage(ABC):
    """One step in the normalization pipeline. Stateless preferred."""

    name: str = ""

    @abstractmethod
    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        """Mutate or replace `ctx` and return it."""


class Pipeline:
    """Runs stages in order and threads the same Context through each.

    A stage that raises propagates the exception; partial state in the
    context is preserved so callers can inspect what completed.
    """

    def __init__(self, stages: Iterable[Stage]) -> None:
        self._stages = list(stages)

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        for stage in self._stages:
            stage_name = stage.name or stage.__class__.__name__
            logger.debug("Pipeline running stage=%s", stage_name)
            ctx = stage.run(ctx)
        return ctx

    @property
    def stage_names(self) -> list[str]:
        return [s.name or s.__class__.__name__ for s in self._stages]
