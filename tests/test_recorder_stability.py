"""Stability tests for critical recorder paths: listeners, commands, step persistence,
evidence level branching, and network capture.

All tests are unit tests — no Playwright browser required.
"""
import json
import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from testforge.recorder.recorder_controller import RecorderController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(evaluate_return=None):
    page = MagicMock()
    page.evaluate.return_value = evaluate_return
    page.url = "http://localhost"
    page.title.return_value = "Test Page"
    return page


def _fake_session(recording_id: str = "REC-001"):
    session = MagicMock()
    session.session_dir = "/tmp/fake_rec"
    session.recording_id = recording_id
    return session


# ---------------------------------------------------------------------------
# A1: Listener lifecycle
# ---------------------------------------------------------------------------

class TestListenerLifecycle:
    """page.on() / page.remove_listener() called correctly — no leak risk."""

    def _start(self, ctrl, rid="REC-001"):
        """Call ctrl.start() with RawRecordingStore patched out."""
        with patch("testforge.recorder.recorder_controller.RawRecordingStore"):
            ctrl.start(rid)

    def _make_ctrl(self):
        page = _make_page()
        ctrl = RecorderController(page)
        ctrl._session_manager = MagicMock()
        ctrl._session_manager.start.return_value = _fake_session()
        ctrl._session_manager.stop.return_value = _fake_session()
        return ctrl, page

    def test_start_registers_request_listener(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl)
        page.on.assert_any_call("request", ctrl._on_request)

    def test_start_registers_response_listener(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl)
        page.on.assert_any_call("response", ctrl._on_response)

    def test_stop_removes_request_listener(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl)
        ctrl.stop()
        page.remove_listener.assert_any_call("request", ctrl._on_request)

    def test_stop_removes_response_listener(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl)
        ctrl.stop()
        page.remove_listener.assert_any_call("response", ctrl._on_response)

    def test_second_start_registers_exactly_two_listeners(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl, "REC-001")
        ctrl.stop()
        page.on.reset_mock()
        self._start(ctrl, "REC-002")
        assert page.on.call_count == 2

    def test_stop_with_remove_listener_exception_does_not_raise(self):
        ctrl, page = self._make_ctrl()
        self._start(ctrl)
        page.remove_listener.side_effect = Exception("no such listener")
        ctrl.stop()  # must not propagate


# ---------------------------------------------------------------------------
# A2: Command control flow
# ---------------------------------------------------------------------------

class TestCommandControlFlow:
    """handle_commands() branches and wait_for_command() exception safety."""

    def _ctrl(self):
        page = _make_page(evaluate_return=[])
        return RecorderController(page)

    def test_stop_command_returns_stop(self):
        ctrl = self._ctrl()
        ctrl._command_queue = ["STOP"]
        assert ctrl.handle_commands() == "stop"

    def test_toggle_pause_returns_paused(self):
        ctrl = self._ctrl()
        ctrl._command_queue = ["TOGGLE_PAUSE"]
        assert ctrl.handle_commands() == "paused"

    def test_toggle_pause_twice_returns_continue(self):
        ctrl = self._ctrl()
        ctrl._command_queue = ["TOGGLE_PAUSE"]
        ctrl.handle_commands()
        ctrl._command_queue = ["TOGGLE_PAUSE"]
        assert ctrl.handle_commands() == "continue"

    def test_empty_queue_returns_continue(self):
        ctrl = self._ctrl()
        assert ctrl.handle_commands() == "continue"

    def test_js_commands_processed(self):
        page = _make_page(evaluate_return=["STOP"])
        ctrl = RecorderController(page)
        assert ctrl.handle_commands() == "stop"

    def test_wait_for_command_js_exception_returns_empty_list(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("page closed")
        ctrl = RecorderController(page)
        result = ctrl.wait_for_command()
        assert result == []

    def test_paused_state_persists_across_calls(self):
        ctrl = self._ctrl()
        ctrl._command_queue = ["TOGGLE_PAUSE"]
        ctrl.handle_commands()
        # No command this time — still paused
        assert ctrl.handle_commands() == "paused"


# ---------------------------------------------------------------------------
# A3: Step persistence
# ---------------------------------------------------------------------------

class TestStepPersistence:
    """_persist_step() writes JSONL correctly and counter is monotonic."""

    def _ctrl(self, tmp_path):
        page = _make_page()
        ctrl = RecorderController(page)
        ctrl._store = MagicMock()
        ctrl._store._session_dir = str(tmp_path)
        return ctrl

    def test_counter_starts_at_zero_increments_on_each_step(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        assert ctrl._step_counter == 0
        ctrl._persist_step({"action": "click"})
        assert ctrl._step_counter == 1
        ctrl._persist_step({"action": "fill"})
        assert ctrl._step_counter == 2
        ctrl._persist_step({"action": "assert"})
        assert ctrl._step_counter == 3

    def test_step_id_formatted_with_four_digits(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        ctrl._persist_step({"action": "click"})
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        with open(steps_file) as f:
            data = json.loads(f.readline())
        assert data["step_id"] == "step_0001"

    def test_all_14_fields_present(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        ctrl._persist_step({
            "action": "click",
            "selector": "#submit",
            "tagName": "button",
            "text": "Enviar",
            "value": "",
            "assert_type": "textual",
            "assert_state": "visible",
            "expected_value": "Sucesso",
            "attrs": {"class": "btn"},
            "fallbacks": ["//button[@type='submit']"],
        })
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        with open(steps_file) as f:
            data = json.loads(f.readline())
        expected_fields = {
            "step_id", "timestamp", "action", "selector", "tag_name",
            "text", "value", "url", "page_title", "assert_type",
            "assert_state", "expected_value", "attrs", "fallbacks",
            "element_id", "aria_label", "role", "css_path", "accessible_name",
        }
        assert set(data.keys()) == expected_fields

    def test_fallbacks_list_serializes_correctly(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        ctrl._persist_step({"action": "click", "fallbacks": ["#a", "#b", "#c"]})
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        with open(steps_file) as f:
            data = json.loads(f.readline())
        assert data["fallbacks"] == ["#a", "#b", "#c"]

    def test_attrs_dict_serializes_correctly(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        ctrl._persist_step({"action": "click", "attrs": {"class": "btn-primary", "type": "submit"}})
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        with open(steps_file) as f:
            data = json.loads(f.readline())
        assert data["attrs"] == {"class": "btn-primary", "type": "submit"}

    def test_multiple_steps_appended_to_same_file(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        ctrl._persist_step({"action": "click"})
        ctrl._persist_step({"action": "fill", "value": "test"})
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        with open(steps_file) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 2

    def test_step_ids_are_unique_and_ordered(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        for _ in range(5):
            ctrl._persist_step({"action": "click"})
        steps_file = os.path.join(str(tmp_path), "steps.jsonl")
        ids = []
        with open(steps_file) as f:
            for line in f:
                ids.append(json.loads(line)["step_id"])
        assert ids == ["step_0001", "step_0002", "step_0003", "step_0004", "step_0005"]


# ---------------------------------------------------------------------------
# A4: Evidence level branching
# ---------------------------------------------------------------------------

class TestEvidenceLevel:
    """Screenshot capture gated by evidence_level (full vs light)."""

    def _ctrl_with_level(self, level: str):
        page = _make_page()
        page.screenshot.return_value = b"\x89PNG\r\n\x1a\n"
        page.content.return_value = "<html><body>real page content here</body></html>"
        ctrl = RecorderController(page)
        ctrl._store = MagicMock()
        ctrl._evidence_level = level
        event = MagicMock()
        event.event_id = "evt_00001"
        return ctrl, page, event

    def test_full_level_calls_screenshot(self):
        ctrl, page, event = self._ctrl_with_level("full")
        ctrl._capture_snapshots(event)
        page.screenshot.assert_called_once()

    def test_full_level_saves_screenshot(self):
        ctrl, page, event = self._ctrl_with_level("full")
        ctrl._capture_snapshots(event)
        ctrl._store.save_screenshot.assert_called_once()

    def test_light_level_skips_screenshot_call(self):
        ctrl, page, event = self._ctrl_with_level("light")
        ctrl._capture_snapshots(event)
        page.screenshot.assert_not_called()

    def test_light_level_does_not_call_save_screenshot(self):
        ctrl, page, event = self._ctrl_with_level("light")
        ctrl._capture_snapshots(event)
        ctrl._store.save_screenshot.assert_not_called()

    def test_both_levels_capture_dom(self):
        for level in ("light", "full"):
            ctrl, page, event = self._ctrl_with_level(level)
            ctrl._capture_snapshots(event)
            ctrl._store.save_dom.assert_called_once()

    def test_screenshot_exception_does_not_crash(self):
        ctrl, page, event = self._ctrl_with_level("full")
        page.screenshot.side_effect = Exception("screenshot failed")
        ctrl._capture_snapshots(event)  # must not raise


# ---------------------------------------------------------------------------
# A5: Network capture
# ---------------------------------------------------------------------------

class TestNetworkCapture:
    """_on_request() and _on_response() capture entries correctly."""

    def _ctrl(self):
        return RecorderController(_make_page())

    def test_post_request_captures_body(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "POST"
        req.url = "http://example.com/api/simulate"
        req.resource_type = "xhr"
        req.post_data = '{"cpf":"12345678900"}'
        ctrl._on_request(req)
        assert ctrl._network_entries[0]["post_data"] == '{"cpf":"12345678900"}'

    def test_put_request_captures_body(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "PUT"
        req.url = "http://example.com/api/update"
        req.resource_type = "xhr"
        req.post_data = '{"value": 42}'
        ctrl._on_request(req)
        assert ctrl._network_entries[0]["post_data"] == '{"value": 42}'

    def test_get_request_has_no_post_data(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "GET"
        req.url = "http://example.com/page"
        req.resource_type = "document"
        ctrl._on_request(req)
        assert ctrl._network_entries[0]["post_data"] is None

    def test_request_entry_has_required_fields(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "GET"
        req.url = "http://example.com/"
        req.resource_type = "document"
        ctrl._on_request(req)
        entry = ctrl._network_entries[0]
        assert entry["type"] == "request"
        assert "method" in entry
        assert "url" in entry
        assert "timestamp" in entry

    def test_response_records_status_code(self):
        ctrl = self._ctrl()
        resp = MagicMock()
        resp.url = "http://example.com/api"
        resp.status = 200
        ctrl._on_response(resp)
        assert ctrl._network_entries[0]["status"] == 200

    def test_response_4xx_still_captured(self):
        ctrl = self._ctrl()
        resp = MagicMock()
        resp.url = "http://example.com/api"
        resp.status = 404
        ctrl._on_response(resp)
        assert ctrl._network_entries[0]["status"] == 404

    def test_response_entry_has_required_fields(self):
        ctrl = self._ctrl()
        resp = MagicMock()
        resp.url = "http://example.com/api"
        resp.status = 201
        ctrl._on_response(resp)
        entry = ctrl._network_entries[0]
        assert entry["type"] == "response"
        assert "url" in entry
        assert "timestamp" in entry

    def test_post_data_access_exception_does_not_crash(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "POST"
        req.url = "http://example.com/api"
        req.resource_type = "xhr"
        type(req).post_data = PropertyMock(side_effect=Exception("access denied"))
        ctrl._on_request(req)
        # Entry still appended, post_data is None
        assert len(ctrl._network_entries) == 1
        assert ctrl._network_entries[0]["post_data"] is None

    def test_requests_and_responses_accumulate(self):
        ctrl = self._ctrl()
        req = MagicMock()
        req.method = "GET"
        req.url = "http://x.com/a"
        req.resource_type = "document"
        resp = MagicMock()
        resp.url = "http://x.com/a"
        resp.status = 200
        ctrl._on_request(req)
        ctrl._on_response(resp)
        assert len(ctrl._network_entries) == 2
        assert ctrl._network_entries[0]["type"] == "request"
        assert ctrl._network_entries[1]["type"] == "response"
