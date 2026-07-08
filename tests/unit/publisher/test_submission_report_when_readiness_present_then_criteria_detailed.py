"""REC-84: submission_report must include detailed criteria and failing_criteria list."""
import json
from pathlib import Path

import pytest


@pytest.mark.unit
class TestSubmissionReportWhenReadinessPresentThenCriteriaDetailed:
    def _setup_recording(self, tmp_path, criteria: dict) -> tuple[Path, Path]:
        recordings_dir = tmp_path / "recordings"
        rec_dir = recordings_dir / "my_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        readiness_dir = rec_dir / "readiness"
        readiness_dir.mkdir()
        (readiness_dir / "readiness_report.json").write_text(json.dumps({
            "readiness_report": {"criteria": criteria, "verdict": "needs_review"}
        }))
        return recordings_dir, rec_dir

    def test_criteria_propagated_from_readiness(self, tmp_path):
        """Criteria dict from readiness_report must appear in submission report."""
        # Arrange
        from testforge.publisher.git_publisher import GitPublisher
        criteria = {
            "completeness_passed": True,
            "all_steps_passed": False,
        }
        recordings_dir, _ = self._setup_recording(tmp_path, criteria)
        pub = GitPublisher(url="x", token="x")
        # Act
        report = pub._generate_submission_report("my_rec", {"recording_id": "my_rec"}, str(recordings_dir))
        # Assert
        assert "criteria" in report
        assert report["criteria"]["completeness_passed"] is True
        assert report["criteria"]["all_steps_passed"] is False

    def test_failing_criteria_list_populated(self, tmp_path):
        """failing_criteria must list all criteria with value=False."""
        # Arrange
        from testforge.publisher.git_publisher import GitPublisher
        criteria = {
            "completeness_passed": True,
            "all_steps_passed": False,
            "blocking_steps_resolved": True,
            "user_supplied_values_validated": False,
            "healing_oracles_passed": True,
        }
        recordings_dir, _ = self._setup_recording(tmp_path, criteria)
        pub = GitPublisher(url="x", token="x")
        # Act
        report = pub._generate_submission_report("my_rec", {"recording_id": "my_rec"}, str(recordings_dir))
        # Assert
        assert set(report["failing_criteria"]) == {"all_steps_passed", "user_supplied_values_validated"}

    def test_missing_readiness_does_not_break(self, tmp_path):
        """When no readiness_report exists, criteria must be empty dict, not crash."""
        # Arrange
        from testforge.publisher.git_publisher import GitPublisher
        recordings_dir = tmp_path / "recordings"
        rec_dir = recordings_dir / "my_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        pub = GitPublisher(url="x", token="x")
        # Act
        report = pub._generate_submission_report("my_rec", {"recording_id": "my_rec"}, str(recordings_dir))
        # Assert
        assert report["criteria"] == {}
        assert report["failing_criteria"] == []
