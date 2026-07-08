"""REC-87: Backward compat — old recording_id field should alias to test_case."""
import pytest


@pytest.mark.unit
class TestRecordingIdAliasWhenOldSchemaThenMapsToTestCase:
    def test_recording_id_used_when_test_case_absent(self):
        """Fall back to recording_id when test_case field is missing."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        meta = {"recording_id": "my_test", "system": "SYS", "suite": "S"}
        # Act
        tc = RecordingSession._read_meta_field(meta, "test_case", "recording_id")
        # Assert
        assert tc == "my_test"

    def test_test_case_takes_priority_over_recording_id(self):
        """test_case should be preferred over recording_id when both present."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        meta = {"recording_id": "old_id", "test_case": "new_id"}
        # Act
        tc = RecordingSession._read_meta_field(meta, "test_case", "recording_id")
        # Assert
        assert tc == "new_id"
