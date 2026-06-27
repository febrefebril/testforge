"""H16 — Readiness verdict semantics pin.

Bug: `deve_logar_no_gas_do_povo_3` reported verdict=pass with steps=0.
Dashboards showed green for recordings nothing executed. Pilot QA cannot
trust verdicts.

New rule (NEXT-SESSION.md):
    verdict == "pass" iff (
        criteria_passed == criteria_total
        AND steps.passed + steps.healed > 0
        AND (steps.failed + steps.healing_rejected) == 0
    )

Otherwise:
    - 5 criteria green, 0 executable steps  → GATED_ONLY (new)
    - any failed or healing_rejected step    → FAIL
    - criteria fail                          → FAIL or NEEDS_REVIEW
"""
from __future__ import annotations

from dataclasses import dataclass, field

from testforge.validation.readiness_gate import (
    ReadinessVerdict,
    RecordingReadinessGate,
)
from testforge.validation.intent_completeness import (
    CompletenessReport,
    FieldCompleteness,
    FieldStatus,
)
from testforge.recorder.recording_status import RecordingStatus


@dataclass
class StepStub:
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


def _complete_report() -> CompletenessReport:
    fields = [
        FieldStatus(
            field_key="nome",
            label="Nome",
            value="X",
            source="fill_event",
            completeness=FieldCompleteness.resolved,
            reason="ok",
        ),
    ]
    report = CompletenessReport(
        recording_id="rec-h16",
        total_fields=len(fields),
        resolved_count=len(fields),
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=0,
        is_complete=True,
    )
    report.fields = fields
    return report


def _eval(steps, completeness=None) -> object:
    gate = RecordingReadinessGate()
    return gate.evaluate(
        recording_id="rec-h16",
        application="web",
        base_url="http://localhost",
        completeness_report=completeness or _complete_report(),
        step_results=steps,
    )


# ---- Core H16 invariants ----------------------------------------------------


def test_criteria_green_zero_steps_returns_gated_only():
    """5 criteria pass, 0 step results → GATED_ONLY (was PASS pre-H16)."""
    report = _eval(steps=[])
    assert report.verdict == ReadinessVerdict.GATED_ONLY, (
        f"Expected GATED_ONLY when no steps ran, got {report.verdict}"
    )
    assert report.status == RecordingStatus.needs_review


def test_criteria_green_only_skipped_steps_returns_gated_only():
    """All skipped → no successful executions → GATED_ONLY."""
    steps = [
        StepStub(step_num=1, status="skipped", skip_reason="duplicate"),
        StepStub(step_num=2, status="skipped", skip_reason="duplicate"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.GATED_ONLY


def test_criteria_green_one_passed_zero_failed_returns_pass():
    """Minimum success bar: at least 1 step actually executed and no failures."""
    steps = [StepStub(step_num=1, status="passed")]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS
    assert report.status == RecordingStatus.ready_for_team


def test_criteria_green_many_passed_zero_failed_returns_pass():
    steps = [StepStub(step_num=i, status="passed") for i in range(1, 6)]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS


def test_healed_validated_counts_as_successful_execution():
    """healed_validated is a successful execution (passed via healing)."""
    steps = [StepStub(step_num=1, status="healed_validated")]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS


def test_any_failed_step_returns_fail():
    """1 passed + 1 failed → FAIL, even with criteria green."""
    steps = [
        StepStub(step_num=1, status="passed"),
        StepStub(step_num=2, status="failed", error_message="timeout"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


def test_healing_rejected_step_returns_fail():
    """healing_rejected counts as failure under H16."""
    steps = [
        StepStub(step_num=1, status="passed"),
        StepStub(step_num=2, status="healing_rejected",
                 error_message="oracle failed"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


def test_all_failed_returns_fail():
    steps = [
        StepStub(step_num=1, status="failed", error_message="boom"),
        StepStub(step_num=2, status="failed", error_message="boom"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


# ---- Criteria failure paths ------------------------------------------------


def test_completeness_failure_returns_fail():
    fields = [
        FieldStatus(
            field_key="uf",
            label="UF",
            value="",
            source="fill_event",
            completeness=FieldCompleteness.missing,
            reason="absent",
        ),
    ]
    incomplete = CompletenessReport(
        recording_id="rec-h16",
        total_fields=1,
        resolved_count=0,
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=1,
        is_complete=False,
    )
    incomplete.fields = fields
    steps = [StepStub(step_num=1, status="passed")]
    report = _eval(steps, completeness=incomplete)
    assert report.verdict == ReadinessVerdict.FAIL


# ---- Reporting integrity --------------------------------------------------


def test_gated_only_emits_warning():
    """GATED_ONLY surfaces a warning explaining the missing execution evidence."""
    report = _eval(steps=[])
    assert any(
        "no executable step" in w.lower() or "dashboard" in w.lower()
        for w in report.warnings
    ), f"Expected warning about empty execution, got {report.warnings}"


def test_gated_only_markdown_renders_new_section():
    """to_markdown emits a dedicated GATED block (not the green PASS section)."""
    report = _eval(steps=[])
    md = report.to_markdown()
    assert "GATED" in md or "gated" in md.lower()
    assert "Ready for Team" not in md
