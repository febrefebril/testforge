"""REC-64: Cross-check metadata.system against page_title of first raw event."""
import json
import pytest


@pytest.mark.unit
class TestMetadataReconciliationWhenSystemVsTitleDivergesThenWarns:
    def test_warns_when_system_not_in_title(self, tmp_path, capsys):
        """Alert when metadata.system absent from page_title of first event."""
        # Arrange
        from testforge.cli.app import _warn_system_title_mismatch
        raw = tmp_path / "raw_events.jsonl"
        raw.write_text(json.dumps({"page_title": "Sistema de Gestao de Honras", "type": "nav"}) + "\n")
        # Act
        _warn_system_title_mismatch({"system": "GESTAO"}, str(raw))
        out = capsys.readouterr().out
        # Assert
        assert "WARN" in out
        assert "diverge" in out

    def test_no_warn_when_system_in_title(self, tmp_path, capsys):
        """No alert when page_title contains the system name."""
        # Arrange
        from testforge.cli.app import _warn_system_title_mismatch
        raw = tmp_path / "raw_events.jsonl"
        raw.write_text(json.dumps({"page_title": "SIMULADOR - Login", "type": "nav"}) + "\n")
        # Act
        _warn_system_title_mismatch({"system": "SIMULADOR"}, str(raw))
        out = capsys.readouterr().out
        # Assert
        assert "WARN" not in out
