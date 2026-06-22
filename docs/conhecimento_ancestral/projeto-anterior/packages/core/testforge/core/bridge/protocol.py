from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BridgeMessage:
    type: str
    id: str = ""
    timestamp: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
