"""TestForge — Pilot Readiness Metrics.

Tracks recording-level readiness metrics across all pilot recordings.
Used to generate the aggregated pilot readiness dashboard.

History 9.1 — Recording completion metrics
History 9.2 — Failure reason categories
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PilotMetrics:
    """Aggregated readiness metrics across all pilot recordings.

    Metrics:
        total_recordings: Total number of recordings evaluated.
        ready_for_team: Recordings that passed all readiness criteria.
        incomplete_intent: Recordings with unresolved/missing fields.
        needs_review: Recordings that require human review.
        fields_auto_resolved: Fields resolved automatically (fill_event, snapshot_diff, etc.).
        fields_user_supplied: Fields resolved via user input (CLI prompt).
        fields_missing: Fields still missing after user input.
        incremental_validation_passed: Recordings where incremental validation passed.
        incremental_validation_failed: Recordings where incremental validation failed.
    """
    total_recordings: int = 0
    ready_for_team: int = 0
    incomplete_intent: int = 0
    needs_review: int = 0
    fields_auto_resolved: int = 0
    fields_user_supplied: int = 0
    fields_missing: int = 0
    incremental_validation_passed: int = 0
    incremental_validation_failed: int = 0

    # Failure reason categories (History 9.2)
    failures: dict = field(default_factory=lambda: {
        "missing_value": 0,
        "selector_failed": 0,
        "actionability_failed": 0,
        "postcondition_failed": 0,
        "network_wait_failed": 0,
        "dynamic_assert_failed": 0,
        "wrong_field_mapping": 0,
    })

    recordings: list = field(default_factory=list)

    def ingest_recording(self, recording_id: str, readiness_path: str):
        """Ingest a single recording's readiness report into aggregate metrics.

        Args:
            recording_id: Recording identifier.
            readiness_path: Path to readiness_report.json.
        """
        if not os.path.exists(readiness_path):
            return

        with open(readiness_path) as f:
            data = json.load(f)

        rr = data.get("readiness_report", data)
        status = rr.get("status", "")
        verdict = rr.get("verdict", "")

        self.total_recordings += 1
        self.recordings.append({
            "recording_id": recording_id,
            "status": status,
            "verdict": verdict,
            "criteria": rr.get("criteria", {}),
            "steps": rr.get("steps", {}),
            "failures": rr.get("failures", []),
        })

        # Count status
        status_map = {
            "ready_for_team": "ready_for_team",
            "incomplete_intent": "incomplete_intent",
            "needs_review": "needs_review",
        }
        for key, attr in status_map.items():
            if status == key or (verdict == "pass" and key == "ready_for_team"):
                setattr(self, attr, getattr(self, attr, 0) + 1)
                break

        # Count failures by category
        for failure in rr.get("failures", []):
            fl = failure.lower()
            if "selector" in fl:
                self.failures["selector_failed"] += 1
            elif "missing" in fl or "value" in fl:
                self.failures["missing_value"] += 1
            elif "actionability" in fl:
                self.failures["actionability_failed"] += 1
            elif "postcondition" in fl:
                self.failures["postcondition_failed"] += 1
            elif "network" in fl or "wait" in fl:
                self.failures["network_wait_failed"] += 1
            elif "assert" in fl or "dynamic" in fl:
                self.failures["dynamic_assert_failed"] += 1
            elif "mapping" in fl or "field" in fl:
                self.failures["wrong_field_mapping"] += 1

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "summary": {
                "total_recordings": self.total_recordings,
                "ready_for_team": self.ready_for_team,
                "incomplete_intent": self.incomplete_intent,
                "needs_review": self.needs_review,
                "completion_rate": round(self.ready_for_team / max(self.total_recordings, 1), 4),
            },
            "fields": {
                "auto_resolved": self.fields_auto_resolved,
                "user_supplied": self.fields_user_supplied,
                "missing": self.fields_missing,
            },
            "incremental_validation": {
                "passed": self.incremental_validation_passed,
                "failed": self.incremental_validation_failed,
            },
            "failures": dict(sorted(
                self.failures.items(),
                key=lambda x: x[1],
                reverse=True,
            )),
            "recordings": self.recordings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def to_markdown(self) -> str:
        """Generate QA-friendly markdown dashboard."""
        d = self.to_dict()
        s = d["summary"]

        lines = [
            f"# Pilot Readiness Dashboard",
            f"",
            f"**Generated:** {d['generated_at']}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Recordings | {s['total_recordings']} |",
            f"| ✅ Ready for Team | {s['ready_for_team']} |",
            f"| ⚠ Incomplete Intent | {s['incomplete_intent']} |",
            f"| 🔍 Needs Review | {s['needs_review']} |",
            f"| Completion Rate | {s['completion_rate']:.1%} |",
            f"",
            f"## Fields",
            f"",
            f"| Category | Count |",
            f"|----------|-------|",
            f"| Auto-resolved | {d['fields']['auto_resolved']} |",
            f"| User-supplied | {d['fields']['user_supplied']} |",
            f"| Missing | {d['fields']['missing']} |",
            f"",
            f"## Incremental Validation",
            f"",
            f"| Outcome | Count |",
            f"|---------|-------|",
            f"| ✅ Passed | {d['incremental_validation']['passed']} |",
            f"| ❌ Failed | {d['incremental_validation']['failed']} |",
            f"",
        ]

        failures = d["failures"]
        if any(failures.values()):
            lines.extend([
                f"## Failure Reasons",
                f"",
                f"| Category | Count | Priority |",
                f"|----------|-------|----------|",
            ])
            # Sort by count descending, add priority tag
            sorted_fails = sorted(failures.items(), key=lambda x: x[1], reverse=True)
            for i, (cat, count) in enumerate(sorted_fails):
                if count == 0:
                    continue
                priority = "🔴 HIGH" if i < 2 else "🟡 MEDIUM" if i < 4 else "🟢 LOW"
                lines.append(f"| {cat.replace('_', ' ').title()} | {count} | {priority} |")
            lines.append("")

        lines.append(f"## Recordings")
        lines.append(f"")
        if self.recordings:
            lines.extend([
                f"| Recording | Status | Verdict | Steps | Failures |",
                f"|-----------|--------|---------|-------|----------|",
            ])
            for r in self.recordings:
                steps = r.get("steps", {})
                step_str = f"{steps.get('passed', 0)}/{steps.get('total', 0)}"
                fails = len(r.get("failures", []))
                lines.append(
                    f"| {r['recording_id']} | {r['status']} | {r['verdict']} "
                    f"| {step_str} | {fails} |"
                )
        else:
            lines.append("_(No recordings ingested yet)_")
        lines.append("")

        return "\n".join(lines)


def collect_pilot_metrics(recordings_dir: str) -> PilotMetrics:
    """Walk a recordings directory and collect metrics from all readiness reports.

    Args:
        recordings_dir: Root directory containing recording subdirectories.

    Returns:
        Aggregated PilotMetrics instance.
    """
    metrics = PilotMetrics()

    if not os.path.isdir(recordings_dir):
        return metrics

    for entry in sorted(os.listdir(recordings_dir)):
        entry_path = os.path.join(recordings_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        # Try both readiness report locations
        readiness_path = os.path.join(entry_path, "readiness", "readiness_report.json")
        if not os.path.exists(readiness_path):
            # Fallback: look in recording root
            readiness_path = os.path.join(entry_path, "readiness_report.json")
        if not os.path.exists(readiness_path):
            continue

        metrics.ingest_recording(entry, readiness_path)

    return metrics


def save_pilot_report(
    metrics: PilotMetrics,
    output_dir: str,
    filename_prefix: str = "pilot_readiness",
) -> tuple[str, str]:
    """Save pilot readiness report to JSON and Markdown.

    Args:
        metrics: Aggregated PilotMetrics.
        output_dir: Directory to save reports.
        filename_prefix: Base name for output files.

    Returns:
        Tuple of (json_path, md_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"{filename_prefix}_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2, default=str)

    md_path = os.path.join(output_dir, f"{filename_prefix}_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(metrics.to_markdown())

    return json_path, md_path
