from __future__ import annotations
from typing import Any, Optional

from testforge.core.config.schema import Config


class DefaultSource:
    def load(self) -> Config:
        return Config()

    @staticmethod
    def default_timeout_by_action() -> dict[str, int]:
        return {
            "navigation": 45000,
            "click": 15000,
            "upload": 60000,
            "assert": 15000,
            "fill": 15000,
            "download": 30000,
        }
