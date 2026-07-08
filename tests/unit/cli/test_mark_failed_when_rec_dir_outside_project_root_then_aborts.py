"""NB-09: _mark_failed_recording must abort when rec_dir is outside _PROJECT_ROOT."""
import json, pytest


@pytest.mark.unit
class TestMarkFailedWhenRecDirOutsideProjectRootThenAborts:
    def test_aborts_when_rec_dir_outside_project(self, tmp_path, monkeypatch, capsys):
        from testforge.cli import app
        pr = tmp_path / "project"
        pr.mkdir()
        rec_outside = tmp_path / "elsewhere" / "rec"
        rec_outside.mkdir(parents=True)
        monkeypatch.setattr(app, "_PROJECT_ROOT", pr)
        app._mark_failed_recording(str(rec_outside), "rec")
        out = capsys.readouterr().out
        assert "ERRO" in out or "fora de" in out.lower()


@pytest.mark.unit
class TestFailedMarkerWhenPathHasWindowsDriveThenStripped:
    def test_source_dir_without_backslash(self, tmp_path, monkeypatch):
        from testforge.cli import app
        pr = tmp_path / "project"
        pr.mkdir()
        rec = pr / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        monkeypatch.setattr(app, "_PROJECT_ROOT", pr)
        app._mark_failed_recording(str(rec), "my_rec")
        failed = list((pr / "recordings_failed").glob("my_rec_*"))
        assert failed, "Failed dir not created"
        marker = json.loads((failed[0] / "FAILED_MARKER.json").read_text())
        assert "\\" not in marker["source_dir"], f"Backslash leaked: {marker['source_dir']}"


@pytest.mark.unit
class TestFailedMarkerWhenWouldNestThenAborts:
    def test_aborts_when_project_root_equals_rec_dir(self, tmp_path, monkeypatch, capsys):
        from testforge.cli import app
        rec = tmp_path / "rec"
        rec.mkdir()
        monkeypatch.setattr(app, "_PROJECT_ROOT", rec)
        (rec / "recording_metadata.json").write_text(json.dumps({}))
        (rec / "raw_events.jsonl").write_text("")
        app._mark_failed_recording(str(rec), "rec")
        nested = rec / "recordings_failed" / "rec"
        # Should not create nested recordings_failed inside rec itself
        assert not nested.exists() or not any(nested.rglob("FAILED_MARKER.json"))
