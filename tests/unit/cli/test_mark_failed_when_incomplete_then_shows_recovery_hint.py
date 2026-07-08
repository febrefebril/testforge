"""REC-88: _mark_failed_recording must show recovery hints on how to iterate."""
import json
import pytest


@pytest.mark.unit
class TestMarkFailedWhenIncompleteThenShowsRecoveryHint:
    def test_prints_recovery_hint(self, tmp_path, capsys, monkeypatch):
        """After marking failed, output must include 'compile' and 'itere' hints."""
        # Arrange
        from testforge.cli import app as cli_app
        rec_dir = tmp_path / "recordings" / "my_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec_dir / "raw_events.jsonl").write_text("")
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        # Act
        cli_app._mark_failed_recording(str(rec_dir), "my_rec")
        out = capsys.readouterr().out
        # Assert
        assert "compile" in out.lower()
        assert "regravar" in out.lower() or "itere" in out.lower()
