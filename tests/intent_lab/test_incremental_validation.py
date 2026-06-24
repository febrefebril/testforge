"""TestForge — Incremental Validation Tests.

Tests integration between normalizer, completeness checker,
and readiness gate for end-to-end validation scenarios.
"""
from testforge.validation.readiness_gate import (
    RecordingReadinessGate,
    ReadinessVerdict,
)
from testforge.validation.intent_completeness import (
    CompletenessReport,
    FieldStatus,
    FieldCompleteness,
)
from testforge.recorder.recording_status import RecordingStatus


# -- Helpers ---------------------------------------------------------------

def _mock_step(step_num, action, status, blocking=False, healing=None, error_message=""):
    from dataclasses import dataclass
    @dataclass
    class MockHealing:
        attempted: bool = True
        oracle_passed: bool = True
        validated: bool = True
    @dataclass
    class MockStep:
        step_num: int
        action: str = "click"
        status: str = "passed"
        error_message: str = ""
        blocking: bool = False
        healing: object = None
        precondition: object = None
        postcondition: object = None
        value: str = ""
        original_locator: str = ""
        selected_locator: str = ""
        skip_reason: str = ""
    return MockStep(
        step_num=step_num, action=action, status=status,
        error_message=error_message,
        blocking=blocking,
        healing=healing or MockHealing(),
    )


def _ok_report():
    r = CompletenessReport(
        recording_id="test", total_fields=1, resolved_count=1,
        resolved_with_warning_count=0, review_required_count=0,
        missing_count=0, is_complete=True,
    )
    r.fields = [
        FieldStatus(
            field_key="f1", label="Field 1", value="v1",
            source="fill_event", completeness=FieldCompleteness.resolved,
        )
    ]
    return r


# -- Tests: validate → gate flow ------------------------------------------

class TestValidationPipeline:
    """Simulates the full validate() flow without browser."""

    def test_normalize_then_validate_passes(self):
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id="full-flow",
            application="web",
            base_url="http://localhost:8000",
            completeness_report=_ok_report(),
            step_results=[_mock_step(1, "fill", "passed")],
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.status == RecordingStatus.ready_for_team

    def test_normalize_fails(self):
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id="failing",
            application="web",
            base_url="http://localhost:8000",
            completeness_report=None,
            step_results=[],
        )
        assert report.verdict != ReadinessVerdict.PASS
        assert not report.completeness_passed

    def test_incomplete_steps_report(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "navigation", "passed"),
            _mock_step(2, "fill", "failed", error_message="Timeout: element not visible"),
            _mock_step(3, "click", "blocked"),
        ]
        report = gate.evaluate(
            recording_id="incomplete-run",
            application="web",
            base_url="http://localhost",
            completeness_report=_ok_report(),
            step_results=steps,
        )
        assert report.verdict != ReadinessVerdict.PASS
        assert report.failed_steps >= 1
        assert report.blocked_steps >= 1
        assert report.total_steps == 3


class TestEdgeCases:
    """Edge cases for the validation pipeline."""

    def test_all_skipped_steps(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "click", "skipped"),
            _mock_step(2, "fill", "skipped"),
        ]
        report = gate.evaluate(
            recording_id="all-skipped",
            application="web",
            base_url="http://localhost",
            completeness_report=_ok_report(),
            step_results=steps,
        )
        # Skipped steps are not executable => trivially passing
        assert report.verdict == ReadinessVerdict.PASS

    def test_mixed_skipped_and_passed(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "click", "skipped"),
            _mock_step(2, "fill", "passed"),
        ]
        report = gate.evaluate(
            recording_id="mixed",
            application="web",
            base_url="http://localhost",
            completeness_report=_ok_report(),
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.skipped_steps == 1
        assert report.passed_steps == 1

    def test_empty_recording_dir(self):
        import tempfile
        from testforge.validation.incremental_validator import (
            IncrementalRecordingValidator,
        )
        with tempfile.TemporaryDirectory() as tmp:
            v = IncrementalRecordingValidator(recording_dir=tmp, output_dir=tmp)
            assert v.recording_dir == tmp
            # Should not crash on init
            assert v.status_history is not None
