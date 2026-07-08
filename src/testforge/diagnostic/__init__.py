"""TestForge Sprint 0 — Diagnostic Recorder.

Adds a rich-telemetry capture mode to the existing recorder. Does NOT
generate tests by itself — designed to ship to teams as a data
collection tool so we can prioritize the next-phase bug fixes based on
real-world evidence rather than hypothesis.

Public surface:
- DiagnosticSession           lifecycle wrapping framework + capture +
                              replay + Gherkin under one object
- FrameworkDetector           A3 (HTTP bundle analysis via CDP) +
                              A4 (window.* sniff + DOM markers + custom elements)
- CaptureQualityTracker       per-step assessment of what the recorder
                              actually captured
- ReplayCheck                 immediate (B1) or batched (B4) locator probe
- GherkinWriter               live "Quando clico no botão X" lines (PT, C4b+C4c)
- DiagnosticTelemetryStore    JSONL primary + OTel-compatible spans (E4)
"""
from .capture_quality import CaptureQualityTracker
from .framework_detector import FrameworkDetector
from .gherkin_writer import GherkinWriter
from .replay_check import ReplayCheck
from .session import DiagnosticSession
from .telemetry_store import DiagnosticTelemetryStore

__all__ = [
    "DiagnosticSession",
    "FrameworkDetector",
    "CaptureQualityTracker",
    "ReplayCheck",
    "GherkinWriter",
    "DiagnosticTelemetryStore",
]
