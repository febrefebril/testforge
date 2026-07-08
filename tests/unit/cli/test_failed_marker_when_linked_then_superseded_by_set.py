"""REC-90: link-failed CLI must update superseded_by in FAILED_MARKER.json."""
import json
import argparse
import pytest


@pytest.mark.unit
class TestFailedMarkerWhenLinkedThenSupersededBySet:
    def test_link_failed_updates_marker(self, tmp_path, monkeypatch):
        """Calling _cmd_link_failed must set superseded_by on the marker."""
        # Arrange
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        failed_dir = tmp_path / "recordings_failed" / "rec_old_20260703-202821"
        failed_dir.mkdir(parents=True)
        (failed_dir / "FAILED_MARKER.json").write_text(
            json.dumps({"recording_id": "rec_old", "superseded_by": None})
        )
        args = argparse.Namespace(failed_id="rec_old_20260703-202821", canonical_id="rec_new")
        # Act
        cli_app._cmd_link_failed(args)
        marker = json.loads((failed_dir / "FAILED_MARKER.json").read_text())
        # Assert
        assert marker["superseded_by"] == "rec_new"
