"""Testes unitarios do Recorder Sensorial."""
import json
import os
import tempfile

import pytest
from testforge.recorder.raw_event import RawRecordedEvent, TargetInfo
from testforge.recorder.recording_session import RecordingSessionManager
from testforge.recorder.raw_recording_store import RawRecordingStore


class TestRecordingSession:
    def test_start_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            session = mgr.start("REC-001", "test-app", "http://localhost")
            assert session.status == "recording"
            assert os.path.isdir(session.session_dir)
            assert os.path.isfile(os.path.join(session.session_dir, "recording_metadata.json"))

    def test_stop_updates_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            mgr.start("REC-001")
            session = mgr.stop()
            assert session.status == "stopped"
            assert session.finished_at is not None

    def test_finalize_sets_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            mgr.start("REC-001")
            mgr.stop()
            session = mgr.finalize()
            assert session.status == "completed"
            assert mgr.active_session is None

    def test_cannot_start_while_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            mgr.start("REC-001")
            with pytest.raises(RuntimeError):
                mgr.start("REC-002")

    def test_metadata_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            mgr.start("REC-001", "fake-app", "http://localhost:8765")
            path = os.path.join(tmpdir, "REC-001", "recording_metadata.json")
            with open(path) as f:
                meta = json.load(f)
            assert meta["recording_id"] == "REC-001"
            assert meta["application"] == "fake-app"
            assert meta["status"] == "recording"


class TestRawEvent:
    def test_to_dict_minimal(self):
        evt = RawRecordedEvent(event_id="evt_0001", event_type="click")
        d = evt.to_dict()
        assert d["event_id"] == "evt_0001"
        assert d["type"] == "click"

    def test_to_dict_with_target(self):
        target = TargetInfo(tag="button", text="Pesquisar", role="button")
        evt = RawRecordedEvent(event_id="evt_0001", event_type="click", target=target)
        d = evt.to_dict()
        assert d["target"]["tag"] == "button"
        assert d["target"]["role"] == "button"


class TestRawRecordingStore:
    def test_append_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RawRecordingStore(tmpdir)
            evt = RawRecordedEvent(event_id="evt_0001", event_type="click")
            store.append_event(evt)
            evt2 = RawRecordedEvent(event_id="evt_0002", event_type="fill")
            store.append_event(evt2)

            path = os.path.join(tmpdir, "raw_events.jsonl")
            assert os.path.isfile(path)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            data = json.loads(lines[0])
            assert data["event_id"] == "evt_0001"

    def test_save_network_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RawRecordingStore(tmpdir)
            store.save_network_log([{"url": "http://test"}])
            path = os.path.join(tmpdir, "network_log.json")
            assert os.path.isfile(path)

    def test_save_sensitive_data_alert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RawRecordingStore(tmpdir)
            store.save_sensitive_data_alert([{"type": "CPF"}])
            path = os.path.join(tmpdir, "sensitive_data_alert.json")
            with open(path) as f:
                data = json.load(f)
            assert data["policy"] == "alert_only"
            assert data["masking_applied"] is False
