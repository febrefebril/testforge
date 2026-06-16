"""TestForge Run Report — Captures full step execution details for audit.

BUG-016: Terminal shows summary (truncated candidates, errors, LLM responses).
Full report saved to JSON file with untruncated data.

Usage:
    report = RunReport(recording_id="REC-001", base_url="http://localhost")
    report.add_step(StepReport(...))
    report_path = report.save(output_dir="recordings/REC-001/")
"""
from dataclasses import dataclass, field
import json
import os
import time
from typing import Optional


@dataclass
class StepReport:
    """Full details for a single step execution — no truncation."""
    step_num: int
    action: str
    success: bool = False
    error_message: str = ""
    # Candidates: full list of {selector, score} (not truncated to [:3] or [:40])
    candidates: list[dict] = field(default_factory=list)
    selector_used: str = ""
    value: str = ""
    # Healing details (full, untruncated)
    healing_attempted: bool = False
    healing_success: bool = False
    healing_layer: str = ""
    healing_family: str = ""
    healing_proposal_locator: str = ""
    healing_confidence: float = 0.0
    healing_raw_response: str = ""
    # Step execution context
    skip_reason: str = ""
    assert_type: str = ""
    assert_expected: str = ""
    assert_actual: str = ""
    is_submit: bool = False

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "action": self.action,
            "success": self.success,
            "error_message": self.error_message,
            "candidates": self.candidates,
            "selector_used": self.selector_used,
            "value": self.value,
            "healing_attempted": self.healing_attempted,
            "healing_success": self.healing_success,
            "healing_layer": self.healing_layer,
            "healing_family": self.healing_family,
            "healing_proposal_locator": self.healing_proposal_locator,
            "healing_confidence": self.healing_confidence,
            "healing_raw_response": self.healing_raw_response,
            "skip_reason": self.skip_reason,
            "assert_type": self.assert_type,
            "assert_expected": self.assert_expected,
            "assert_actual": self.assert_actual,
            "is_submit": self.is_submit,
        }


@dataclass
class RunReport:
    """Full execution report for a test run.

    Captures all step details without truncation, saved to JSON file.
    Terminal output stays as human-friendly summary.
    """
    recording_id: str
    base_url: str
    script_path: str = ""
    total_steps: int = 0
    failed_steps: int = 0
    healed_steps: int = 0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    steps: list[StepReport] = field(default_factory=list)

    def add_step(self, step: StepReport) -> None:
        """Add a step report to the run."""
        self.steps.append(step)

    def to_dict(self) -> dict:
        return {
            "recording_id": self.recording_id,
            "base_url": self.base_url,
            "script_path": self.script_path,
            "total_steps": self.total_steps,
            "failed_steps": self.failed_steps,
            "healed_steps": self.healed_steps,
            "timestamp": self.timestamp,
            "steps": [s.to_dict() for s in self.steps],
        }

    def save(self, output_dir: str) -> str:
        """Save full report to JSON file. Returns the file path."""
        os.makedirs(output_dir, exist_ok=True)
        safe_ts = time.strftime("%Y%m%d-%H%M%S")
        filename = f"run_report_{safe_ts}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        return filepath


def save_report(report: RunReport, output_dir: str) -> str:
    """Convenience function to save a RunReport and return path."""
    return report.save(output_dir)
