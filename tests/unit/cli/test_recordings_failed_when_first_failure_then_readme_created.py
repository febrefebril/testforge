"""REC-91: README.md must be created in recordings_failed on first use."""
import json
import pytest


@pytest.mark.unit
class TestRecordingsFailedWhenFirstFailureThenReadmeCreated:
    def test_readme_created_on_first_move(self, tmp_path, monkeypatch):
        """README.md must exist and contain recovery instructions after first failure."""
        # Arrange
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        # Act
        cli_app._mark_failed_recording(str(rec), "my_rec")
        # Assert
        readme = tmp_path / "recordings_failed" / "README.md"
        assert readme.exists()
        assert "testforge compile" in readme.read_text()
