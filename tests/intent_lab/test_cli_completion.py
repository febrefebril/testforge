"""TestForge — CLI Completion Integration Tests.

Tests that the interactive completion prompt correctly integrates
with completeness checking and field_value_map updates.

These are unit tests (no actual CLI invocation) that verify
the data flow between completeness detection and user input.
"""
from testforge.validation.intent_completeness import (
    IntentCompletenessChecker,
    CompletenessReport,
    FieldStatus,
    FieldCompleteness,
)
from testforge.validation.readiness_gate import (
    RecordingReadinessGate,
    ReadinessVerdict,
)
from testforge.recorder.recording_status import RecordingStatus


class TestCompletenessToGateFlow:
    """Flow from completeness check → readiness gate."""

    def test_incomplete_triggers_needs_review(self):
        """Missing fields block readiness."""
        gate = RecordingReadinessGate()
        report = CompletenessReport(
            recording_id="test",
            total_fields=2,
            resolved_count=1,
            resolved_with_warning_count=0,
            review_required_count=0,
            missing_count=1,
            is_complete=False,
        )
        report.fields = [
            FieldStatus(
                field_key="valor", label="Valor",
                source="missing_fill",
                completeness=FieldCompleteness.missing,
                reason="typing_not_captured",
            ),
            FieldStatus(
                field_key="nome", label="Nome",
                value="João", source="fill_event",
                completeness=FieldCompleteness.resolved,
            ),
        ]
        r = gate.evaluate(
            recording_id="incomplete-cli",
            application="web",
            base_url="http://localhost",
            completeness_report=report,
            step_results=[],
        )
        assert r.verdict != ReadinessVerdict.PASS
        assert r.completeness_passed is False
        assert len(r.missing_fields) == 1

    def test_user_supplied_value_in_report(self):
        """User-supplied values appear in readiness report."""
        gate = RecordingReadinessGate()
        from dataclasses import dataclass, field
        @dataclass
        class MockFV:
            field_key: str
            value: str = ""
            source: str = ""
            intention: str = ""
            step_index: int = 0
            identifiers: dict = field(default_factory=dict)

        field_values = {
            "valor": MockFV(
                field_key="valor",
                value="1234",
                source="user_supplied_cli",
            ),
        }
        report = CompletenessReport(
            recording_id="cli-test",
            total_fields=1, resolved_count=0,
            resolved_with_warning_count=0,
            review_required_count=1, missing_count=0,
            is_complete=False,
        )
        report.fields = [
            FieldStatus(
                field_key="valor", label="Valor",
                value="1234", source="user_supplied_cli",
                completeness=FieldCompleteness.review_required,
                reason="user_supplied_cli_not_validated",
            ),
        ]
        r = gate.evaluate(
            recording_id="cli-test",
            application="web",
            base_url="http://localhost",
            completeness_report=report,
            step_results=[],
            field_values=field_values,
        )
        assert r.user_supplied_values_validated is False
        assert len(r.warnings) >= 1
