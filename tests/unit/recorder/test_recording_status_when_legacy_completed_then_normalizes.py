"""REC-81: RecordingStatus.normalize() maps legacy status strings to canonical values."""
import pytest


@pytest.mark.unit
class TestRecordingStatusWhenLegacyCompletedThenNormalizes:
    def test_completed_maps_to_intent_complete(self):
        """Legacy 'completed' should map to 'intent_complete'."""
        # Arrange
        from testforge.recorder.recording_status import RecordingStatus
        # Act
        result = RecordingStatus.normalize("completed")
        # Assert
        assert result == RecordingStatus.intent_complete

    def test_completed_raw_maps_to_stopped(self):
        """Legacy 'completed_raw' should map to 'stopped'."""
        # Arrange
        from testforge.recorder.recording_status import RecordingStatus
        # Act
        result = RecordingStatus.normalize("completed_raw")
        # Assert
        assert result == RecordingStatus.stopped

    def test_current_status_unchanged(self):
        """Current canonical statuses should pass through unchanged."""
        # Arrange
        from testforge.recorder.recording_status import RecordingStatus
        # Act
        result = RecordingStatus.normalize("intent_complete")
        # Assert
        assert result == RecordingStatus.intent_complete

    def test_unknown_status_falls_back(self):
        """Unknown status strings should fall back to incomplete_intent."""
        # Arrange
        from testforge.recorder.recording_status import RecordingStatus
        # Act
        result = RecordingStatus.normalize("unknown_xyz")
        # Assert
        assert result == RecordingStatus.incomplete_intent
