"""REC-75/76: _resolve_name must use timestamp suffix instead of _2/_3/_N."""
import re
import pytest


@pytest.mark.unit
class TestResolveNameWhenDuplicateThenTimestampSuffix:
    def test_unique_name_returned_unchanged(self, tmp_path):
        """When base_name doesn't exist, return it unchanged."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSessionManager
        # Act
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        # Assert
        assert result == "my_test"

    def test_duplicate_gets_timestamp_suffix(self, tmp_path):
        """When base_name exists, append YYYYMMDD-HHMMSS timestamp."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSessionManager
        (tmp_path / "my_test").mkdir()
        # Act
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        # Assert
        assert result.startswith("my_test_")
        assert re.match(r"my_test_\d{8}-\d{6}$", result), f"Got: {result}"

    def test_no_incremental_suffix_pattern(self, tmp_path):
        """Must NOT produce _2, _3, _4 legacy pattern."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSessionManager
        (tmp_path / "my_test").mkdir()
        # Act
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        # Assert
        assert not re.match(r"my_test_\d+$", result), f"Got incremental suffix: {result}"
