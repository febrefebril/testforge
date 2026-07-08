"""REC-80: Deprecate application field misuse with warning on system names."""
import logging
import pytest


@pytest.mark.unit
class TestApplicationFieldWhenSystemNameThenWarns:
    def test_warns_when_application_looks_like_system(self, caplog):
        """Log warning when 'application' field contains a system name."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        # Act
        with caplog.at_level(logging.WARNING):
            s = RecordingSession(recording_id="x", application="SIMULADOR")
            s.to_metadata_dict()
        # Assert
        assert "REC-80" in caplog.text or "application" in caplog.text.lower()

    def test_no_warn_for_valid_application_type(self, caplog):
        """No warning when 'application' is a valid type (web/mobile/desktop/api)."""
        # Arrange
        from testforge.recorder.recording_session import RecordingSession
        # Act
        with caplog.at_level(logging.WARNING):
            s = RecordingSession(recording_id="x", application="web")
            s.to_metadata_dict()
        # Assert
        assert "REC-80" not in caplog.text
