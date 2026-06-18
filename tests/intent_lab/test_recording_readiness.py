"""TestForge — Recording Readiness Integration Tests.

Tests the full readiness evaluation pipeline with realistic field
and step scenarios derived from Intent Lab page patterns.
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
from testforge.validation.incremental_validator import IncrementalRecordingValidator
from testforge.recorder.recording_status import RecordingStatus


# ── Helpers ───────────────────────────────────────────────────────────────

def _mock_step(step_num, action, status, blocking=False, healing=None, error_message=""):
    from dataclasses import dataclass, field
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
        step_num=step_num,
        action=action,
        status=status,
        error_message=error_message,
        blocking=blocking,
        healing=healing or MockHealing(),
    )


def _complete_report(**overrides):
    """Create a passing completeness report."""
    r = CompletenessReport(
        recording_id=overrides.get("recording_id", "test"),
        total_fields=overrides.get("total_fields", 1),
        resolved_count=overrides.get("resolved_count", 1),
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=0,
        is_complete=True,
    )
    r.fields = [
        FieldStatus(
            field_key="field1", label="Field 1",
            value="val1", source="fill_event",
            completeness=FieldCompleteness.resolved,
        )
    ]
    return r


# ── Tests ─────────────────────────────────────────────────────────────────

class TestReadyFlowScenario:
    """ready-flow page: normal input + select + checkbox → passes all."""

    def test_ready_flow_passes(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "fill", "passed"),
            _mock_step(2, "select_option", "passed"),
            _mock_step(3, "click", "passed"),
        ]
        report = gate.evaluate(
            recording_id="ready-flow",
            application="web",
            base_url="http://localhost",
            completeness_report=_complete_report(total_fields=3, resolved_count=3),
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.status == RecordingStatus.ready_for_team

    def test_ready_flow_with_healing(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "fill", "passed"),
            _mock_step(2, "select_option", "healed_validated", healing=None),
            _mock_step(3, "click", "passed"),
        ]
        report = gate.evaluate(
            recording_id="ready-flow-healed",
            application="web",
            base_url="http://localhost",
            completeness_report=_complete_report(total_fields=3, resolved_count=3),
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.healed_steps == 1


class TestMissingFillGapScenario:
    """missing-fill-gap: user clicks input, types (not captured), clicks next."""

    def test_missing_fill_detected(self):
        gate = RecordingReadinessGate()
        field = FieldStatus(
            field_key="valor", label="Valor",
            source="missing_fill",
            completeness=FieldCompleteness.missing,
            reason="typing_not_captured",
        )
        report = _complete_report(
            total_fields=1, resolved_count=0, missing_count=1,
        )
        report.fields = [field]
        report.is_complete = False

        steps = [_mock_step(1, "click", "passed")]
        r = gate.evaluate(
            recording_id="missing-fill",
            application="web",
            base_url="http://localhost",
            completeness_report=report,
            step_results=steps,
        )
        assert r.verdict != ReadinessVerdict.PASS
        assert r.completeness_passed is False
        assert len(r.missing_fields) >= 1


class TestPreventDefaultScenario:
    """prevent-default-input: JS sets value without DOM event."""

    def test_snapshot_diff_resolves(self):
        gate = RecordingReadinessGate()
        field = FieldStatus(
            field_key="campo1", label="Campo 1",
            value="ABC", source="snapshot_diff",
            completeness=FieldCompleteness.resolved_with_warning,
        )
        report = _complete_report(total_fields=1, resolved_count=0,
                                   resolved_with_warning_count=1)
        report.fields = [field]
        # resolved_with_warning counts as complete for the gate
        report.is_complete = True

        steps = [_mock_step(1, "click", "passed")]
        r = gate.evaluate(
            recording_id="prevent-default",
            application="web",
            base_url="http://localhost",
            completeness_report=report,
            step_results=steps,
        )
        assert r.verdict == ReadinessVerdict.PASS


class TestBlockingStepScenario:
    """blocking-step-failure: cascading selects with dependency."""

    def test_blocking_step_fails_readiness(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "select_option", "failed", blocking=True,
                       error_message="Element not found"),
            _mock_step(2, "select_option", "blocked"),
        ]
        r = gate.evaluate(
            recording_id="cascading-selects",
            application="web",
            base_url="http://localhost",
            completeness_report=_complete_report(),
            step_results=steps,
        )
        assert r.verdict != ReadinessVerdict.PASS
        assert r.blocking_steps_resolved is False
        assert r.blocked_steps >= 1

    def test_all_cascading_selects_work(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "select_option", "passed", blocking=True),
            _mock_step(2, "select_option", "passed"),
            _mock_step(3, "select_option", "passed"),
        ]
        r = gate.evaluate(
            recording_id="cascading-ok",
            application="web",
            base_url="http://localhost",
            completeness_report=_complete_report(),
            step_results=steps,
        )
        assert r.verdict == ReadinessVerdict.PASS
        assert r.blocking_steps_resolved is True


class TestTwoSimilarFieldsScenario:
    """two-similar-fields: wrong value mapping → needs_review."""

    def test_wrong_mapping_detected(self):
        gate = RecordingReadinessGate()
        steps = [
            _mock_step(1, "fill", "passed"),
            _mock_step(2, "fill", "healing_rejected",
                       error_message="Postcondition failed — wrong value applied"),
        ]
        r = gate.evaluate(
            recording_id="similar-fields",
            application="web",
            base_url="http://localhost",
            completeness_report=_complete_report(total_fields=2, resolved_count=2),
            step_results=steps,
        )
        assert r.verdict == ReadinessVerdict.NEEDS_REVIEW
        assert r.status == RecordingStatus.needs_review
        assert r.failed_steps >= 1


class TestValidatorInit:
    """IncrementalRecordingValidator initialization."""

    def test_validator_creation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            v = IncrementalRecordingValidator(
                recording_dir=tmp,
                output_dir=tmp,
                headless=True,
            )
            assert v.recording_dir == tmp
            assert v.output_dir == tmp
            assert v.headless is True
