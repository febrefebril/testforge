"""REC-71/82: Duplicate recording detection by event sequence hash."""
import json
import pathlib
import pytest


@pytest.mark.unit
class TestDuplicateDetectionWhenSameSequenceThenWarns:
    def _write_events(self, path, events):
        pathlib.Path(path).write_text("\n".join(json.dumps(e) for e in events))

    def test_identical_sequences_produce_same_hash(self, tmp_path):
        """Same event sequence must produce identical hash."""
        # Arrange
        from testforge.cli.app import _compute_recording_hash
        events = [{"type": "fill", "target": {"element_id": "cpf"}, "value": "123"}]
        p1 = tmp_path / "raw1.jsonl"
        p2 = tmp_path / "raw2.jsonl"
        self._write_events(str(p1), events)
        self._write_events(str(p2), events)
        # Act & Assert
        assert _compute_recording_hash(str(p1)) == _compute_recording_hash(str(p2))

    def test_different_sequences_produce_different_hash(self, tmp_path):
        """Different event sequences must produce different hashes."""
        # Arrange
        from testforge.cli.app import _compute_recording_hash
        p1 = tmp_path / "raw1.jsonl"
        p2 = tmp_path / "raw2.jsonl"
        self._write_events(str(p1), [{"type": "fill", "value": "AAA"}])
        self._write_events(str(p2), [{"type": "fill", "value": "BBB"}])
        # Act & Assert
        assert _compute_recording_hash(str(p1)) != _compute_recording_hash(str(p2))

    def test_check_warns_when_duplicate_found(self, tmp_path, capsys):
        """_check_duplicate_recording must print WARN on match."""
        # Arrange
        from testforge.cli.app import _check_duplicate_recording
        events = [{"type": "click", "target": {"element_id": "btn"}, "value": None}]
        existing = tmp_path / "existing_rec"
        existing.mkdir()
        (existing / "raw_events.jsonl").write_text(json.dumps(events[0]))
        new_raw = tmp_path / "new_raw.jsonl"
        new_raw.write_text(json.dumps(events[0]))
        # Act
        _check_duplicate_recording(str(tmp_path), str(new_raw), "new_rec")
        out = capsys.readouterr().out
        # Assert
        assert "WARN" in out or "identica" in out
