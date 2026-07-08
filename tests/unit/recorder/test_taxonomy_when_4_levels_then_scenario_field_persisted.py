"""REC-22: RecordingSession must support 4-level taxonomy with scenario field."""
import pytest


@pytest.mark.unit
class TestTaxonomyWhen4LevelsThenScenarioFieldPersisted:
    def test_recording_session_has_scenario_field(self):
        """scenario field must be present and serialized in to_metadata_dict()."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        # Act
        s = RecordingSession(recording_id="x", system="SYS", suite="SUITE",
                             test_case="TC", scenario="SC")
        d = s.to_metadata_dict()
        # Assert
        assert d["scenario"] == "SC"

    def test_scenario_empty_by_default(self):
        """Default scenario must be empty string for backward compat."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        # Act
        s = RecordingSession(recording_id="x")
        # Assert
        assert s.to_metadata_dict()["scenario"] == ""
