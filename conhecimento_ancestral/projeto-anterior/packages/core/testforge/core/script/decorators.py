from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class StepMetadata:
    timeout: int = 30000
    intention: str = ""
    retry_on_failure: bool = True
    screenshot_on_fail: bool = True


def step(
    timeout: int = 30000,
    intention: str = "",
    **kwargs: Any,
) -> Callable:
    metadata = StepMetadata(timeout=timeout, intention=intention, **kwargs)
    def decorator(func: Callable) -> Callable:
        func.__testforge_metadata__ = metadata
        return func
    return decorator
