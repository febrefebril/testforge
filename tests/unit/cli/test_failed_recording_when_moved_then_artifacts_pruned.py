"""REC-92: Heavy derived artifacts must be pruned when moving to recordings_failed."""
import json
import pytest


@pytest.mark.unit
class TestFailedRecordingWhenMovedThenArtifactsPruned:
    def test_dom_snapshots_removed_after_move(self, tmp_path, monkeypatch):
        """dom_snapshots directory must be deleted from failed copy."""
        # Arrange
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        (rec / "dom_snapshots").mkdir()
        (rec / "dom_snapshots" / "snap_001.html").write_text("<html/>")
        # Act
        cli_app._mark_failed_recording(str(rec), "my_rec")
        # Assert
        failed = list((tmp_path / "recordings_failed").glob("my_rec*"))
        assert failed, "No failed dir created"
        assert not (failed[0] / "dom_snapshots").exists()

    def test_raw_events_preserved_after_move(self, tmp_path, monkeypatch):
        """Essential files (raw_events.jsonl) must survive the prune."""
        # Arrange
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text('{"type":"nav"}')
        # Act
        cli_app._mark_failed_recording(str(rec), "my_rec")
        # Assert
        failed = list((tmp_path / "recordings_failed").glob("my_rec*"))
        assert (failed[0] / "raw_events.jsonl").exists()
