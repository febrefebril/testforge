"""REC-83: Alert when recording uses an old capture schema version."""
import pytest


@pytest.mark.unit
class TestOldSchemaWarningWhenV0ThenBannerShown:
    def test_warns_when_no_fingerprint(self, capsys):
        """Warn when metadata has no fingerprint block (v0 legacy)."""
        # Arrange
        from testforge.cli.app import _warn_old_schema
        # Act
        _warn_old_schema({}, "my_rec")
        out = capsys.readouterr().out
        # Assert
        assert "WARN" in out
        assert "schema v0" in out or "pre-fingerprint" in out

    def test_warns_when_schema_older(self, capsys):
        """Warn when schema_version < current."""
        # Arrange
        from testforge.cli.app import _warn_old_schema
        # Act
        _warn_old_schema({"fingerprint": {"capture_schema_version": 2}}, "my_rec")
        out = capsys.readouterr().out
        # Assert
        assert "WARN" in out

    def test_no_warn_when_current_schema(self, capsys):
        """No warning when schema_version equals current."""
        # Arrange
        from testforge.cli.app import _warn_old_schema
        # Act
        _warn_old_schema({"fingerprint": {"capture_schema_version": 4}}, "my_rec")
        out = capsys.readouterr().out
        # Assert
        assert "WARN" not in out
