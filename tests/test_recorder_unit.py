"""Testes unitarios do Recorder Sensorial."""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from testforge.recorder.raw_event import RawRecordedEvent, TargetInfo
from testforge.recorder.recording_session import RecordingSessionManager
from testforge.recorder.raw_recording_store import RawRecordingStore
from testforge.recorder.recorder_controller import RecorderController


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


class TestRecordingNameResolution:
    """Tests for preventing silent overwrite of existing recordings."""

    def test_no_conflict_returns_original_name(self):
        """When directory does not exist, original name is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test"

    def test_conflict_returns_suffixed_name(self):
        """When directory exists, returns name_2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "my_test"))
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test_2"

    def test_multiple_conflicts_returns_next_available(self):
        """When name and name_2 exist, returns name_3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "my_test"))
            os.makedirs(os.path.join(tmpdir, "my_test_2"))
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test_3"

    def test_name_with_trailing_suffix(self):
        """When base name already has _N suffix and that dir also exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "login_flow_2"))
            result = RecordingSessionManager._resolve_name(tmpdir, "login_flow_2")
            assert result == "login_flow_2_2"

    def test_start_uses_resolved_name(self):
        """RecordingSessionManager.start() must create dir with resolved name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            # First session
            s1 = mgr.start("demo", "app", "http://localhost")
            assert s1.recording_id == "demo"
            assert os.path.isdir(os.path.join(tmpdir, "demo"))
            mgr.stop()
            mgr.finalize()

            # Second session with same name — must get _2
            s2 = mgr.start("demo", "app", "http://localhost")
            assert s2.recording_id == "demo_2"
            assert os.path.isdir(os.path.join(tmpdir, "demo_2"))
            assert not os.path.isdir(os.path.join(tmpdir, "demo", "raw_events.jsonl"))  # untouched


class TestRecorderControllerEventId:
    """Tests for monotonic event_id within a recording session."""

    def _make_mock_event_data(self, event_type="click", url="http://localhost/test"):
        """Create minimal event data as received from JS."""
        return {
            "event_id": "evt_ignored",  # JS-generated ID — should be ignored by Python
            "type": event_type,
            "timestamp": "2025-01-01T00:00:00Z",
            "url": url,
            "page_title": "Test Page",
            "target": None,
            "value": None,
        }

    def test_event_ids_monotonic_across_flushes(self):
        """event_id must be unique and monotonic — never reset within a recording session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            # Patch _capture_snapshots to avoid real Playwright calls
            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-MONO-001")

                # Simulate 3 separate flush cycles (like after navigation)
                for _ in range(3):
                    recorder._persist_raw_event(self._make_mock_event_data("navigation"))
                    recorder._persist_raw_event(self._make_mock_event_data("click"))
                    recorder._persist_raw_event(self._make_mock_event_data("fill"))

            # Read stored events
            events_path = os.path.join(tmpdir, "REC-MONO-001", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            assert len(event_ids) == 9, f"Expected 9 events, got {len(event_ids)}"

            # All IDs must be unique
            assert len(set(event_ids)) == len(event_ids), (
                f"Duplicate event_ids found: {event_ids}"
            )

            # Monotonic sequence: evt_00001, evt_00002, ...
            expected_ids = [f"evt_{i:05d}" for i in range(1, 10)]
            assert event_ids == expected_ids, (
                f"Expected {expected_ids}, got {event_ids}"
            )

    def test_event_counter_does_not_reset_on_multiple_starts(self):
        """Calling start() must not reset the event counter — it keeps monotonic across the session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-NORESET-001")
                recorder._persist_raw_event(self._make_mock_event_data("click"))
                recorder._persist_raw_event(self._make_mock_event_data("click"))

                # Simulate end of first session
                recorder._session_manager.stop()
                recorder._session_manager.finalize()

                # Start another recording — counter must continue, not reset
                recorder.start(recording_id="REC-NORESET-002")
                recorder._persist_raw_event(self._make_mock_event_data("click"))

            events_path = os.path.join(tmpdir, "REC-NORESET-002", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            # First recording had evt_00001, evt_00002; second should start at evt_00003
            assert event_ids[0] == "evt_00003", (
                f"Counter reset! Expected evt_00003, got {event_ids[0]}"
            )

    def test_js_generated_event_id_is_ignored(self):
        """Python-side counter must be the single source of truth — JS event_id discarded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-IGNOREJS-001")

                # JS sends event_id="evt_bad_js_id" — Python must ignore it
                data = self._make_mock_event_data("click")
                data["event_id"] = "evt_bad_js_id"
                recorder._persist_raw_event(data)

                data2 = self._make_mock_event_data("fill")
                data2["event_id"] = "evt_bad_js_id"  # JS counter "reset" on navigation
                recorder._persist_raw_event(data2)

            events_path = os.path.join(tmpdir, "REC-IGNOREJS-001", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            assert event_ids == ["evt_00001", "evt_00002"], (
                f"JS event_id leaked! Expected unique IDs, got {event_ids}"
            )


class TestRecorderH1BrowserCloseGracefulStop:
    """Hotfix H1: closing the browser/page is equivalent to Shift+S."""

    def test_target_closed_handler_sets_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            assert recorder._closed is False
            recorder._on_target_closed()
            assert recorder._closed is True

    def test_handle_commands_returns_stop_when_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            recorder._closed = True
            assert recorder.handle_commands() == "stop"

    def test_handle_commands_normal_when_not_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            assert recorder.handle_commands() == "continue"

    def test_start_registers_close_listeners(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-H1-001")
            # page.on('close', ...) must be among page.on calls
            event_names = [call.args[0] for call in mock_page.on.call_args_list]
            assert "close" in event_names

    def test_target_closed_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            recorder._on_target_closed()
            recorder._on_target_closed()
            recorder._on_target_closed()
            assert recorder._closed is True
