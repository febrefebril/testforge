"""TestForge — Sprint 8: Pilot Readiness Metrics Tests.

Tests the aggregated metrics collection, failure categorization,
and consolidated dashboard report generation.

CT-AUTO-8.1: Metrics reflect real results (ready, incomplete, failed)
CT-AUTO-8.2: Consolidated report generates pilot_readiness_report.md
"""
import json
import os
import tempfile

import pytest

from testforge.metrics.pilot_metrics import (
    PilotMetrics,
    collect_pilot_metrics,
    save_pilot_report,
)


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture
def recordings_dir():
    """Create a temporary recordings directory with mock readiness reports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Recording 1: READY
        _make_ready_recording(tmpdir, "REC-READY-001")
        # Recording 2: INCOMPLETE
        _make_incomplete_recording(tmpdir, "REC-INCOMPLETE-001")
        # Recording 3: NEEDS_REVIEW
        _make_needs_review_recording(tmpdir, "REC-REVIEW-001")
        yield tmpdir


def _make_ready_recording(base_dir: str, rec_id: str):
    """Create a recording with PASS readiness report."""
    rec_dir = os.path.join(base_dir, rec_id, "readiness")
    os.makedirs(rec_dir, exist_ok=True)

    report = {
        "readiness_report": {
            "metadata": {
                "recording_id": rec_id,
                "application": "web",
                "generated_at": "2026-06-18T12:00:00",
            },
            "status": "ready_for_team",
            "verdict": "pass",
            "criteria": {
                "completeness_passed": True,
                "all_steps_passed": True,
                "blocking_steps_resolved": True,
                "user_supplied_values_validated": True,
                "healing_oracles_passed": True,
            },
            "steps": {
                "total": 3,
                "passed": 3,
                "healed": 0,
                "failed": 0,
                "blocked": 0,
                "skipped": 0,
            },
            "failures": [],
        }
    }
    with open(os.path.join(rec_dir, "readiness_report.json"), "w") as f:
        json.dump(report, f)


def _make_incomplete_recording(base_dir: str, rec_id: str):
    """Create a recording with FAIL readiness report (missing fields)."""
    rec_dir = os.path.join(base_dir, rec_id, "readiness")
    os.makedirs(rec_dir, exist_ok=True)

    report = {
        "readiness_report": {
            "metadata": {
                "recording_id": rec_id,
                "application": "web",
                "generated_at": "2026-06-18T12:00:00",
            },
            "status": "incomplete_intent",
            "verdict": "fail",
            "criteria": {
                "completeness_passed": False,
                "all_steps_passed": True,
                "blocking_steps_resolved": True,
                "user_supplied_values_validated": True,
                "healing_oracles_passed": True,
            },
            "steps": {
                "total": 2,
                "passed": 2,
                "healed": 0,
                "failed": 0,
                "blocked": 0,
                "skipped": 0,
            },
            "failures": [
                "Completeness check failed: missing or unresolved fields exist",
                "Missing value for field 'valor' (typing_not_captured)",
            ],
        }
    }
    with open(os.path.join(rec_dir, "readiness_report.json"), "w") as f:
        json.dump(report, f)


def _make_needs_review_recording(base_dir: str, rec_id: str):
    """Create a recording with NEEDS_REVIEW readiness report (selector failures)."""
    rec_dir = os.path.join(base_dir, rec_id, "readiness")
    os.makedirs(rec_dir, exist_ok=True)

    report = {
        "readiness_report": {
            "metadata": {
                "recording_id": rec_id,
                "application": "web",
                "generated_at": "2026-06-18T12:00:00",
            },
            "status": "needs_review",
            "verdict": "needs_review",
            "criteria": {
                "completeness_passed": True,
                "all_steps_passed": False,
                "blocking_steps_resolved": False,
                "user_supplied_values_validated": True,
                "healing_oracles_passed": False,
            },
            "steps": {
                "total": 5,
                "passed": 2,
                "healed": 1,
                "failed": 1,
                "blocked": 1,
                "skipped": 0,
            },
            "failures": [
                "Selector failed for step 3: button#enviar not found",
                "Oracle validation failed for healed step 4",
            ],
        }
    }
    with open(os.path.join(rec_dir, "readiness_report.json"), "w") as f:
        json.dump(report, f)


# -- CT-AUTO-8.1: Metrics reflect results -----------------------------------

class TestMetricsReflectResults:
    """CT-AUTO-8.1: Metrics accurately reflect recording outcomes."""

    def test_ready_recording_increments_ready_count(self, recordings_dir):
        """A READY recording increments ready_for_team."""
        metrics = collect_pilot_metrics(recordings_dir)
        assert metrics.ready_for_team == 1
        assert metrics.total_recordings == 3

    def test_incomplete_recording_increments_incomplete_count(self, recordings_dir):
        """An incomplete recording increments incomplete_intent."""
        metrics = collect_pilot_metrics(recordings_dir)
        assert metrics.incomplete_intent == 1

    def test_needs_review_recording_increments_review_count(self, recordings_dir):
        """A needs_review recording increments needs_review."""
        metrics = collect_pilot_metrics(recordings_dir)
        assert metrics.needs_review == 1

    def test_failure_categories_are_counted(self, recordings_dir):
        """Failure categories are properly classified."""
        metrics = collect_pilot_metrics(recordings_dir)
        assert metrics.failures["missing_value"] >= 1
        assert metrics.failures["selector_failed"] >= 1

    def test_completion_rate(self, recordings_dir):
        """Completion rate = ready / total."""
        metrics = collect_pilot_metrics(recordings_dir)
        d = metrics.to_dict()
        assert abs(d["summary"]["completion_rate"] - 1/3) < 0.001


# -- CT-AUTO-8.2: Consolidated report ---------------------------------------

class TestConsolidatedReport:
    """CT-AUTO-8.2: Consolidated report generates correct files and content."""

    def test_generates_report_files(self, recordings_dir):
        """pilot_readiness_report.json and .md are created."""
        metrics = collect_pilot_metrics(recordings_dir)
        output_dir = os.path.join(recordings_dir, "..", "reports")
        json_path, md_path = save_pilot_report(metrics, output_dir)

        assert os.path.exists(json_path), f"JSON not found: {json_path}"
        assert os.path.exists(md_path), f"MD not found: {md_path}"

        with open(json_path) as f:
            data = json.load(f)
        assert data["summary"]["total_recordings"] == 3
        assert data["summary"]["ready_for_team"] == 1

    def test_markdown_contains_all_sections(self, recordings_dir):
        """Markdown report has summary, recordings, and failure sections."""
        metrics = collect_pilot_metrics(recordings_dir)
        output_dir = os.path.join(recordings_dir, "..", "reports")
        _, md_path = save_pilot_report(metrics, output_dir)

        with open(md_path) as f:
            md = f.read()

        assert "Pilot Readiness Dashboard" in md
        assert "Summary" in md
        assert "Recordings" in md
        assert "REC-READY-001" in md
        assert "REC-INCOMPLETE-001" in md
        assert "REC-REVIEW-001" in md

    def test_report_lists_status_per_recording(self, recordings_dir):
        """Report contains status breakdown per recording."""
        metrics = collect_pilot_metrics(recordings_dir)
        assert len(metrics.recordings) == 3

        statuses = {r["recording_id"]: r["status"] for r in metrics.recordings}
        assert statuses.get("REC-READY-001") == "ready_for_team"
        assert statuses.get("REC-INCOMPLETE-001") == "incomplete_intent"
        assert statuses.get("REC-REVIEW-001") == "needs_review"

    def test_empty_recordings_dir_returns_empty_metrics(self):
        """No recordings → empty metrics, no crash."""
        with tempfile.TemporaryDirectory() as empty_dir:
            metrics = collect_pilot_metrics(empty_dir)
            assert metrics.total_recordings == 0
            assert metrics.ready_for_team == 0
            assert len(metrics.recordings) == 0


# -- CLI argument parsing ---------------------------------------------------

class TestPilotReportCLI:
    """Verify the CLI correctly parses pilot-report arguments."""

    def test_pilot_report_command(self):
        """pilot-report command parses."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        pr = sub.add_parser("pilot-report")
        pr.add_argument("--recordings-dir", default="./recordings")
        pr.add_argument("--output", default="./reports")

        args = parser.parse_args(["pilot-report"])
        assert args.command == "pilot-report"
        assert args.recordings_dir == "./recordings"
        assert args.output == "./reports"

    def test_pilot_report_custom_paths(self):
        """pilot-report accepts custom paths."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        pr = sub.add_parser("pilot-report")
        pr.add_argument("--recordings-dir")
        pr.add_argument("--output")

        args = parser.parse_args([
            "pilot-report",
            "--recordings-dir", "/tmp/my-recordings",
            "--output", "/tmp/my-reports",
        ])
        assert args.recordings_dir == "/tmp/my-recordings"
        assert args.output == "/tmp/my-reports"
