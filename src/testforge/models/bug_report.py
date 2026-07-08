"""Data model for recording-time bug detection reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BugSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugSource(Enum):
    APPLICATION = "application_under_test"
    TESTFORGE = "testforge"
    UNKNOWN = "unknown"


@dataclass
class BugSignal:
    """One anomaly signal captured by AnomalyDetector."""

    type: str
    timestamp: str
    payload: dict = field(default_factory=dict)


@dataclass
class BugReport:
    """Structured bug report generated during recording."""

    bug_id: str
    timestamp: str
    recording_id: str
    step_idx: int
    signals: list[BugSignal] = field(default_factory=list)

    observed_behavior: str = ""
    user_expected_behavior: str = ""
    source: BugSource = BugSource.UNKNOWN
    severity: BugSeverity = BugSeverity.MEDIUM

    screenshot_path: Optional[str] = None
    network_trace_path: Optional[str] = None
    console_trace_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "bug_id": self.bug_id,
            "timestamp": self.timestamp,
            "recording_id": self.recording_id,
            "step_idx": self.step_idx,
            "signals": [
                {"type": s.type, "ts": s.timestamp, "payload": s.payload}
                for s in self.signals
            ],
            "observed_behavior": self.observed_behavior,
            "user_expected_behavior": self.user_expected_behavior,
            "source": self.source.value,
            "severity": self.severity.value,
            "screenshot_path": self.screenshot_path,
            "network_trace_path": self.network_trace_path,
            "console_trace_path": self.console_trace_path,
        }

    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
