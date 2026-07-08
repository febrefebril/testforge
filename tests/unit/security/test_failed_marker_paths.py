"""Failed marker must not leak absolute Windows paths (BUG-REC-89)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestFailedMarkerRelativePath:
    def test_when_recording_moved_then_source_dir_is_relative(self, tmp_path, monkeypatch):
        # Arrange — build minimal recording dir
        rec_dir = tmp_path / "recordings" / "test_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text("{}")

        from testforge.cli import app as cli_app

        # Point _PROJECT_ROOT to tmp_path so relative_to works
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)

        # Act
        cli_app._mark_failed_recording(str(rec_dir), "test_rec", reason="unit_test")

        # Assert — marker file exists with relative source_dir
        failed_root = tmp_path / "recordings_failed"
        markers = list(failed_root.glob("*/FAILED_MARKER.json"))
        assert markers, "FAILED_MARKER.json not written"
        marker = json.loads(markers[0].read_text())
        assert not Path(marker["source_dir"]).is_absolute(), (
            f"CONTRACT VIOLATION: source_dir must be relative to project root, "
            f"got absolute path: {marker['source_dir']!r} (BUG-REC-89)"
        )
        assert "\\" not in marker["source_dir"], (
            f"CONTRACT VIOLATION: source_dir must not contain Windows backslash, "
            f"got: {marker['source_dir']!r} (BUG-REC-36)"
        )

    def test_when_recording_outside_project_then_aborts(self, tmp_path, monkeypatch):
        """NB-09: recording outside _PROJECT_ROOT must abort, not create nested failed."""
        # Arrange
        rec_dir = tmp_path / "external" / "recordings" / "external_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text("{}")

        from testforge.cli import app as cli_app

        # Set project root to somewhere unrelated
        project_root = tmp_path / "project"
        project_root.mkdir()
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", project_root)

        # Act
        cli_app._mark_failed_recording(str(rec_dir), "external_rec", reason="unit_test")

        # Assert — NB-09: abort, no markers created
        failed_root = project_root / "recordings_failed"
        markers = list(failed_root.glob("*/FAILED_MARKER.json"))
        assert not markers, "NB-09: must not create marker when rec_dir is outside project root"
