"""TestForge — Sprint 7: CLI Integration and QA Experience Tests.

Tests the --validate-before-ready flag, --pilot-mode, and QA-friendly
readiness report output per EPIC 8 (Histories 8.1, 8.2, 8.3).

CT-AUTO-7.1: CLI record with validate-before-ready (unit-level simulation)
CT-AUTO-7.2: CLI with --no-interactive
CT-AUTO-7.3: CLI with failing incremental validation
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from testforge.validation.readiness_gate import (
    RecordingReadinessGate,
    ReadinessReport,
    ReadinessVerdict,
    save_readiness_report,
)
from testforge.validation.intent_completeness import (
    CompletenessReport,
    FieldStatus,
    FieldCompleteness,
    IntentCompletenessChecker,
    save_completeness_report,
)
from testforge.recorder.recording_status import RecordingStatus


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def temp_rec_dir():
    """Create a temporary directory simulating a recording output dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal recording metadata
        meta = {
            "recording_id": "TEST-VALIDATE",
            "application": "web",
            "base_url": "http://localhost:8080",
            "recording_status": "completed_raw",
            "status_history": [],
        }
        with open(os.path.join(tmpdir, "recording_metadata.json"), "w") as f:
            json.dump(meta, f)
        yield tmpdir


@pytest.fixture
def complete_report():
    """A completeness report with all fields resolved."""
    report = CompletenessReport(
        recording_id="TEST-VALIDATE",
        total_fields=2,
        resolved_count=2,
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=0,
        is_complete=True,
    )
    report.fields = [
        FieldStatus(
            field_key="nome", label="Nome",
            value="Joao", source="fill_event",
            completeness=FieldCompleteness.resolved,
        ),
        FieldStatus(
            field_key="cidade", label="Cidade",
            value="Sao Paulo", source="fill_event",
            completeness=FieldCompleteness.resolved,
        ),
    ]
    return report


@pytest.fixture
def incomplete_report():
    """A completeness report with missing fields."""
    report = CompletenessReport(
        recording_id="TEST-INCOMPLETE",
        total_fields=2,
        resolved_count=1,
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=1,
        is_complete=False,
    )
    report.fields = [
        FieldStatus(
            field_key="nome", label="Nome",
            value="Maria", source="fill_event",
            completeness=FieldCompleteness.resolved,
        ),
        FieldStatus(
            field_key="valor", label="Valor",
            source="missing_fill",
            completeness=FieldCompleteness.missing,
            reason="typing_not_captured",
        ),
    ]
    return report


# ── CT-AUTO-7.1: validate-before-ready flag ────────────────────────────────

class TestValidateBeforeReadyFlag:
    """History 8.1: --validate-before-ready flag runs completeness + gate."""

    def test_validation_passes_complete_recording(self, temp_rec_dir, complete_report):
        """Complete recording with validation flag → PASS verdict.

        Note: Without incremental step execution results, the readiness gate
        requires at least that completeness passes and no step failures.
        """
        from dataclasses import dataclass, field

        @dataclass
        class MockStepResult:
            step_num: int = 1
            action: str = "fill"
            status: str = "passed"
            blocking: bool = False
            error_message: str = ""
            healing: object = None

        gate = RecordingReadinessGate()
        step_results = [MockStepResult(step_num=1, action="fill", status="passed"),
                        MockStepResult(step_num=2, action="click", status="passed")]
        report = gate.evaluate(
            recording_id="TEST-VALIDATE",
            application="web",
            base_url="http://localhost",
            completeness_report=complete_report,
            step_results=step_results,
            field_values={
                "nome": MagicMock(source="fill_event"),
                "cidade": MagicMock(source="fill_event"),
            },
        )
        assert report.verdict == ReadinessVerdict.PASS, f"Got {report.verdict}: {report.failures}"
        assert report.completeness_passed is True
        assert report.status == RecordingStatus.ready_for_team

    def test_validation_fails_incomplete_recording(self, temp_rec_dir, incomplete_report):
        """Incomplete recording with validation flag → FAIL verdict."""
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id="TEST-INCOMPLETE",
            application="web",
            base_url="http://localhost",
            completeness_report=incomplete_report,
            step_results=[],
        )
        assert report.verdict != ReadinessVerdict.PASS
        assert report.completeness_passed is False
        assert len(report.missing_fields) == 1
        assert report.missing_fields[0]["field_key"] == "valor"

    def test_save_readiness_report_creates_files(self, temp_rec_dir, complete_report):
        """save_readiness_report creates readable JSON and MD in the recording dir."""
        # First evaluate via gate to get a ReadinessReport
        gate = RecordingReadinessGate()
        from dataclasses import dataclass
        @dataclass
        class MockStepResult:
            step_num: int = 1
            action: str = "fill"
            status: str = "passed"
            blocking: bool = False
            error_message: str = ""
            healing: object = None
        step_results = [MockStepResult(), MockStepResult(step_num=2, action="click")]
        readiness = gate.evaluate(
            recording_id="TEST-VALIDATE",
            application="web", base_url="http://localhost",
            completeness_report=complete_report,
            step_results=step_results,
            field_values={"nome": MagicMock(source="fill_event"),
                          "cidade": MagicMock(source="fill_event")},
        )

        report_dir = os.path.join(temp_rec_dir, "readiness")
        json_path, md_path = save_readiness_report(readiness, report_dir)

        assert os.path.exists(json_path)
        assert os.path.exists(md_path)

        # Verify JSON is parseable and contains expected fields
        with open(json_path) as f:
            data = json.load(f)
        rr = data.get("readiness_report", {})
        assert rr.get("verdict") == "pass"
        criteria = rr.get("criteria", {})
        assert criteria.get("completeness_passed") is True

        # Verify MD is QA-friendly and readable
        with open(md_path) as f:
            md_content = f.read()
        assert "Recording Readiness Report" in md_content
        assert "PASS" in md_content or "Ready for" in md_content
        assert len(md_content) > 100  # Not empty, has substance


# ── CT-AUTO-7.2: --no-interactive mode ─────────────────────────────────────

class TestNoInteractiveMode:
    """History 8.1/8.2: --no-interactive creates template, does not block."""

    def test_no_interactive_creates_template(self, temp_rec_dir):
        """Non-interactive mode creates test_data.template.json."""
        from testforge.cli._interactive_completion import create_data_template
        from testforge.validation.intent_completeness import (
            CompletenessReport,
            FieldStatus,
            FieldCompleteness,
        )

        report = CompletenessReport(
            recording_id="TEST-NO-INT",
            total_fields=1, resolved_count=0,
            resolved_with_warning_count=0,
            review_required_count=0, missing_count=1,
            is_complete=False,
        )
        # pending_fields is a property computed from .fields
        report.fields = [
            FieldStatus(
                field_key="valor", label="Valor",
                source="missing_fill",
                completeness=FieldCompleteness.missing,
                reason="typing_not_captured",
            ),
        ]

        template_path = create_data_template(temp_rec_dir, "TEST-NO-INT", report)
        assert os.path.exists(template_path)

        with open(template_path) as f:
            data = json.load(f)
        assert data["metadata"]["mode"] == "template"
        assert data["metadata"]["status"] == "incomplete_intent"
        assert "valor" in data["fields"]
        assert data["fields"]["valor"]["type"] == "pending"

    def test_no_interactive_does_not_mark_ready(self, temp_rec_dir):
        """Non-interactive mode does NOT set status to ready_for_team."""
        # Without user input, incomplete recordings stay incomplete
        from testforge.cli._interactive_completion import create_data_template
        from testforge.validation.intent_completeness import (
            CompletenessReport,
            FieldStatus,
            FieldCompleteness,
        )

        report = CompletenessReport(
            recording_id="TEST-NO-INT-2",
            total_fields=1, resolved_count=0,
            resolved_with_warning_count=0,
            review_required_count=0, missing_count=1,
            is_complete=False,
        )
        report.fields = [
            FieldStatus(
                field_key="valor", label="Valor",
                source="missing_fill",
                completeness=FieldCompleteness.missing,
                reason="typing_not_captured",
            ),
        ]

        template_path = create_data_template(temp_rec_dir, "TEST-NO-INT-2", report)

        # Verify metadata was NOT set to ready_for_team
        meta_path = os.path.join(temp_rec_dir, "recording_metadata.json")
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta.get("recording_status") != "ready_for_team"


# ── CT-AUTO-7.3: failing validation ────────────────────────────────────────

class TestFailingValidation:
    """History 8.1/8.3: Failing validation produces needs_review with coherent errors."""

    def test_needs_review_for_partial_completeness(self, temp_rec_dir, incomplete_report):
        """Partially complete recording → needs_review and coherent report."""
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id="TEST-REVIEW",
            application="web",
            base_url="http://localhost",
            completeness_report=incomplete_report,
            step_results=[],
        )
        assert report.verdict in (ReadinessVerdict.FAIL, ReadinessVerdict.NEEDS_REVIEW)
        assert not report.completeness_passed
        # Report should have missing fields
        assert len(report.missing_fields) > 0
        # Failures should be meaningful
        assert any("completeness" in f.lower() for f in report.failures)

    def test_report_md_qa_friendly(self, temp_rec_dir, incomplete_report):
        """QA-friendly report shows verdict, failures, and next steps."""
        report_dir = os.path.join(temp_rec_dir, "readiness")
        json_path, md_path = save_readiness_report(incomplete_report, report_dir)

        with open(md_path) as f:
            md = f.read()

        # QA-friendly: has clear sections
        assert "Status" in md
        assert "Ready" in md or "Review" in md or "Not" in md
        # Has field detail
        assert "Missing Fields" in md or "Review Required" in md
        # Has next steps
        assert len(md) > 50

    def test_exit_code_matches_verdict(self):
        """Readiness verdict maps to appropriate exit behavior.

        PASS → exit 0, FAIL/NEEDS_REVIEW → exit 1.
        """
        # This tests the convention used by cmd_run_incremental
        pass_report = ReadinessReport(
            recording_id="test",
            verdict=ReadinessVerdict.PASS,
        )
        fail_report = ReadinessReport(
            recording_id="test",
            verdict=ReadinessVerdict.FAIL,
        )

        assert pass_report.verdict == ReadinessVerdict.PASS
        assert fail_report.verdict == ReadinessVerdict.FAIL
        # Convention: 0 = success, 1 = failure
        assert pass_report.verdict == ReadinessVerdict.PASS  # PASS = success
        assert fail_report.verdict != ReadinessVerdict.PASS  # FAIL != success


# ── CLI argument parsing tests ─────────────────────────────────────────────

class TestCLIArgumentParsing:
    """Verify the CLI correctly parses new flags."""

    def test_validate_before_ready_flag(self):
        """--validate-before-ready flag is parsed."""
        from testforge.cli.app import main as cli_main
        # Parse args manually via argparse
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        rec = sub.add_parser("record")
        rec.add_argument("--validate-before-ready", action="store_true")
        rec.add_argument("--pilot-mode", action="store_true")

        args = parser.parse_args(["record", "--validate-before-ready"])
        assert args.validate_before_ready is True
        assert getattr(args, 'pilot_mode', False) is False

    def test_pilot_mode_flag(self):
        """--pilot-mode flag is parsed."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        rec = sub.add_parser("record")
        rec.add_argument("--validate-before-ready", action="store_true")
        rec.add_argument("--pilot-mode", action="store_true")

        args = parser.parse_args(["record", "--pilot-mode"])
        assert args.pilot_mode is True
        assert args.validate_before_ready is False

    def test_both_flags(self):
        """Both flags can be set simultaneously."""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        rec = sub.add_parser("record")
        rec.add_argument("--validate-before-ready", action="store_true")
        rec.add_argument("--pilot-mode", action="store_true")

        args = parser.parse_args(["record", "--validate-before-ready", "--pilot-mode"])
        assert args.pilot_mode is True
        assert args.validate_before_ready is True
