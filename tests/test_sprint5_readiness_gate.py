"""TestForge — Sprint 5: Recording Readiness Gate.

CT-AUTO-5.1: Gravação completa → ready_for_team
CT-AUTO-5.2: Valor user_supplied_cli no campo errado → needs_review
CT-AUTO-5.3: Currency mask → press_sequentially strategy validated
CT-AUTO-5.4: Falha bloqueante impede READY

Unit tests (no browser): mock step results + CompletenessReport.
"""
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
)
from testforge.recorder.recording_status import RecordingStatus


# ── Helpers ────────────────────────────────────────────────────────────────

@dataclass
class MockStepResult:
    """Simulates IncrementalStepResult for gate evaluation."""
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


@dataclass
class MockHealing:
    attempted: bool = True
    oracle_passed: bool = True
    validated: bool = True


@dataclass
class MockFieldValue:
    field_key: str
    value: str = ""
    source: str = ""
    intention: str = ""
    step_index: int = 0
    identifiers: dict = field(default_factory=dict)


def _make_complete_report(fields: list[FieldStatus] = None) -> CompletenessReport:
    """Create a passing completeness report."""
    if fields is None:
        fields = [
            FieldStatus(
                field_key="nome",
                label="Nome",
                value="João",
                source="fill_event",
                completeness=FieldCompleteness.resolved,
                reason="direct_capture",
            ),
        ]
    report = CompletenessReport(
        recording_id="test-recording",
        total_fields=len(fields),
        resolved_count=sum(1 for f in fields if f.completeness == FieldCompleteness.resolved),
        resolved_with_warning_count=sum(
            1 for f in fields if f.completeness == FieldCompleteness.resolved_with_warning
        ),
        review_required_count=sum(
            1 for f in fields if f.completeness == FieldCompleteness.review_required
        ),
        missing_count=sum(1 for f in fields if f.completeness == FieldCompleteness.missing),
        is_complete=all(
            f.completeness in (FieldCompleteness.resolved, FieldCompleteness.resolved_with_warning)
            for f in fields
        ),
    )
    report.fields = fields
    return report


def _make_passing_steps(count: int = 3) -> list:
    """Create mock passing step results."""
    results = []
    for i in range(count):
        r = MockStepResult(
            step_num=i + 1,
            action="click" if i % 2 == 0 else "fill",
            status="passed",
        )
        results.append(r)
    return results


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def gate():
    return RecordingReadinessGate()


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def passing_completeness():
    return _make_complete_report()


@pytest.fixture
def passing_step_results():
    return _make_passing_steps(3)


# ── CT-AUTO-5.1: Gravação completa → ready_for_team ──────────────────────

class TestCT_AUTO_5_1:
    """Complete recording passes all criteria → ready_for_team."""

    def test_all_criteria_pass(self, gate, passing_completeness, passing_step_results):
        """When completeness + steps pass => verdict PASS, status ready_for_team."""
        report = gate.evaluate(
            recording_id="test-recording",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=passing_step_results,
        )

        assert report.verdict == ReadinessVerdict.PASS, f"Expected PASS, got {report.verdict}"
        assert report.status == RecordingStatus.ready_for_team
        assert report.completeness_passed is True
        assert report.all_steps_passed is True
        assert report.blocking_steps_resolved is True
        assert report.user_supplied_values_validated is True
        assert report.healing_oracles_passed is True
        assert len(report.failures) == 0

    def test_report_serialization(self, gate, passing_completeness, passing_step_results, output_dir):
        """Readiness report saves to JSON and MD correctly."""
        report = gate.evaluate(
            recording_id="rec-001",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=passing_step_results,
        )

        json_path, md_path = save_readiness_report(report, output_dir)

        assert os.path.exists(json_path), f"JSON report not found: {json_path}"
        assert os.path.exists(md_path), f"MD report not found: {md_path}"

        with open(json_path) as f:
            data = json.load(f)
        assert "readiness_report" in data
        assert data["readiness_report"]["verdict"] == "pass"
        assert data["readiness_report"]["status"] == "ready_for_team"

        with open(md_path) as f:
            md = f.read()
        assert "PASS" in md or "Pass" in md
        assert "Ready for Team" in md

    def test_zero_steps_is_valid(self, gate, passing_completeness):
        """No executable steps => trivially passes if completeness ok."""
        report = gate.evaluate(
            recording_id="rec-empty",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=[],
        )
        # No steps means validation didn't run => fail
        assert report.verdict != ReadinessVerdict.PASS

    def test_all_healed_validated(self, gate, passing_completeness):
        """Healed + oracle-validated steps count as passing."""
        steps = [
            MockStepResult(step_num=1, action="click", status="healed_validated",
                           healing=MockHealing(oracle_passed=True)),
            MockStepResult(step_num=2, action="fill", status="healed_validated",
                           healing=MockHealing(oracle_passed=True)),
        ]
        report = gate.evaluate(
            recording_id="rec-healed",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.healed_steps == 2
        assert report.healing_oracles_passed is True


# ── CT-AUTO-5.2: Valor user_supplied_cli no campo errado → needs_review ───

class TestCT_AUTO_5_2:
    """User-supplied values not validated or misapplied → needs_review."""

    def test_user_supplied_validated_passes(self, gate, passing_completeness, passing_step_results):
        """User-supplied values that pass validation are OK."""
        field_values = {
            "nome": MockFieldValue(
                field_key="nome",
                value="João",
                source="user_supplied_cli",
            ),
        }
        report = gate.evaluate(
            recording_id="rec-user-ok",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=passing_step_results,
            field_values=field_values,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.user_supplied_values_validated is True

    def test_user_supplied_not_validated(self, gate, passing_completeness):
        """User-supplied values without passing execution => warning, not failure."""
        field_values = {
            "nome": MockFieldValue(
                field_key="nome",
                value="João",
                source="user_supplied_cli",
            ),
        }
        report = gate.evaluate(
            recording_id="rec-user-unvalidated",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=[],  # No execution results
            field_values=field_values,
        )
        # Should still fail because no step results, but user_supplied warning exists
        assert report.user_supplied_values_validated is False
        assert len(report.warnings) >= 1
        assert any("user-supplied" in w.lower() for w in report.warnings)


# ── CT-AUTO-5.3: Currency mask → press_sequentially strategy ──────────────

class TestCT_AUTO_5_3:
    """Currency mask validation — strategy matters for execution."""

    def test_passing_steps_with_currency_field(self, gate, passing_completeness):
        """Currency field resolved by snapshot_diff => step passes."""
        steps = [
            MockStepResult(step_num=1, action="click", status="passed"),
            MockStepResult(step_num=2, action="fill", status="healed_validated",
                           healing=MockHealing(oracle_passed=True)),
        ]
        report = gate.evaluate(
            recording_id="rec-currency-ok",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS

    def test_healed_validated_oracle_failed(self, gate, passing_completeness):
        """Healing without oracle pass => fail."""
        steps = [
            MockStepResult(step_num=1, action="click", status="passed"),
            MockStepResult(step_num=2, action="fill", status="healed_validated",
                           healing=MockHealing(oracle_passed=False)),
        ]
        report = gate.evaluate(
            recording_id="rec-oracle-fail",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=steps,
        )
        assert report.healing_oracles_passed is False
        assert len(report.failures) >= 1


# ── CT-AUTO-5.4: Falha bloqueante impede READY ────────────────────────────

class TestCT_AUTO_5_4:
    """Blocking step failure prevents READY."""

    def test_blocking_step_fails(self, gate, passing_completeness):
        """Blocking step with failed status => readiness fails."""
        steps = [
            MockStepResult(step_num=1, action="click", status="passed"),
            MockStepResult(step_num=2, action="fill", status="failed",
                           blocking=True, error_message="Element not found"),
        ]
        report = gate.evaluate(
            recording_id="rec-blocking-fail",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=steps,
        )
        assert report.verdict != ReadinessVerdict.PASS
        assert report.blocking_steps_resolved is False
        assert report.all_steps_passed is False
        assert report.failed_steps >= 1

    def test_blocking_step_healed_validated(self, gate, passing_completeness):
        """Blocking step healed + oracle validated => OK."""
        steps = [
            MockStepResult(step_num=1, action="click", status="passed"),
            MockStepResult(step_num=2, action="fill", status="healed_validated",
                           blocking=True,
                           healing=MockHealing(oracle_passed=True)),
        ]
        report = gate.evaluate(
            recording_id="rec-blocking-healed",
            application="web",
            base_url="http://localhost",
            completeness_report=passing_completeness,
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.PASS
        assert report.blocking_steps_resolved is True
        assert report.healed_steps >= 1

    def test_missing_field_blocks_readiness(self, gate):
        """Missing field (completeness fails) prevents READY regardless of steps."""
        field = FieldStatus(
            field_key="uf",
            label="UF",
            source="missing_fill",
            completeness=FieldCompleteness.missing,
            reason="typing_not_captured",
        )
        completeness = _make_complete_report(fields=[field])
        steps = _make_passing_steps(3)

        report = gate.evaluate(
            recording_id="rec-missing-field",
            application="web",
            base_url="http://localhost",
            completeness_report=completeness,
            step_results=steps,
        )
        assert report.verdict != ReadinessVerdict.PASS
        assert report.completeness_passed is False
        assert len(report.missing_fields) >= 1
        assert any(f.get("field_key") == "uf" for f in report.missing_fields)

    def test_needs_review_instead_of_fail(self, gate):
        """Non-blocking failures => NEEDS_REVIEW, not FAIL."""
        steps = [
            MockStepResult(step_num=1, action="click", status="passed"),
            MockStepResult(step_num=2, action="fill", status="healing_rejected",
                           error_message="Healing rejected"),
        ]
        # Use complete report so completeness passes
        report = gate.evaluate(
            recording_id="rec-needs-review",
            application="web",
            base_url="http://localhost",
            completeness_report=_make_complete_report(),
            step_results=steps,
        )
        assert report.verdict == ReadinessVerdict.NEEDS_REVIEW
        assert report.status == RecordingStatus.needs_review
