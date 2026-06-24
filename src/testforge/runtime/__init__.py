"""TestForge Runtime — self-healing and runtime utilities.

Phase 3 additions:
- step.{go,click,fill,select,assert_text,assert_visible} — high-level
  helpers consumed by compiled v2 tests
- LocatorResolver — runtime fallback chain (L0 cache + L1 candidates)
- LocatorNotFoundError, StepExecutionError — diagnostic exceptions
"""
from . import step  # noqa: F401
from .errors import LocatorNotFoundError, StepExecutionError  # noqa: F401
from .resolver import LocatorResolver, ResolveResult  # noqa: F401

__all__ = [
    "step",
    "LocatorResolver",
    "ResolveResult",
    "LocatorNotFoundError",
    "StepExecutionError",
]
