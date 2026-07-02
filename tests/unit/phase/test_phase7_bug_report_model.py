from testforge.models.bug_report import BugReport, BugSeverity, BugSignal, BugSource


def test_bug_report_to_jsonl_contains_expected_fields():
    report = BugReport(
        bug_id="BUG-20260701-00001",
        timestamp="2026-07-01T12:00:00Z",
        recording_id="rec-1",
        step_idx=12,
        signals=[
            BugSignal(type="network_5xx", timestamp="2026-07-01T12:00:01Z", payload={"status": 500}),
        ],
        observed_behavior="POST /api failed",
        user_expected_behavior="Should show success dialog",
        source=BugSource.APPLICATION,
        severity=BugSeverity.CRITICAL,
    )

    line = report.to_jsonl_line()

    assert '"bug_id": "BUG-20260701-00001"' in line
    assert '"source": "application_under_test"' in line
    assert '"severity": "critical"' in line
    assert '"signals": [' in line
