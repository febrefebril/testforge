"""NB-12: recording_scanner varre keystroke_buffer.jsonl e alerta senha."""
import json
import pytest


@pytest.mark.unit
class TestScannerWhenKeystrokeBufferPasswordThenAlerts:
    def test_password_keystrokes_generate_hits(self, tmp_path):
        """Scanner must emit hits when keystroke_buffer has password field."""
        # Arrange
        from testforge.security.recording_scanner import scan_recording
        rec = tmp_path / "test_rec"
        rec.mkdir()
        (rec / "recording_metadata.json").write_text(
            json.dumps({"base_url": "https://tqs.example.com/", "recording_id": "test_rec"})
        )
        (rec / "keystroke_buffer.jsonl").write_text("\n".join(json.dumps({
            "fingerprint": "input#password[name=password]",
            "key": k, "kind": "char",
        }) for k in "teste04"))
        (rec / "raw_events.jsonl").write_text("")
        # Act
        report = scan_recording(str(rec))
        # Assert
        sources_with_pwd = [s for s in report.hits_by_source if "password" in s.lower()]
        assert sources_with_pwd, (
            "NB-12: scanner must emit at least one hit source with 'password' "
            "when keystroke_buffer contains password field keystrokes."
        )

    def test_non_password_field_not_flagged_as_password(self, tmp_path):
        """Username keystrokes must not be flagged as password."""
        # Arrange
        from testforge.security.recording_scanner import scan_recording
        rec = tmp_path / "test_rec"
        rec.mkdir()
        (rec / "recording_metadata.json").write_text(json.dumps({"base_url": "https://tqs.x/"}))
        (rec / "keystroke_buffer.jsonl").write_text(json.dumps({
            "fingerprint": "input#username[name=username]",
            "key": "a", "kind": "char",
        }))
        (rec / "raw_events.jsonl").write_text("")
        # Act
        report = scan_recording(str(rec))
        # Assert
        pwd_sources = [s for s in report.hits_by_source if "password" in s.lower()]
        assert not pwd_sources, "NB-12: username field must not be classified as password."
