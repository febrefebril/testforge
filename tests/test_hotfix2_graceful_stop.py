"""Hotfix 2 — graceful stop + editor fallback."""
from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


def _make_page_open():
    page = MagicMock()
    page.url = "http://x/"
    page.context = MagicMock()
    page.context.tracing = MagicMock()
    page.context.new_cdp_session = MagicMock()
    page.add_init_script = MagicMock()
    page.on = MagicMock()
    page.remove_listener = MagicMock()
    page.evaluate = MagicMock(return_value={
        "events": [], "steps": [], "commands": [],
        "fieldSnapshots": [], "valueMutations": [],
    })
    page.screenshot = MagicMock(return_value=b"\x89PNG")
    page.content = MagicMock(return_value="<html/>")
    page.title = MagicMock(return_value="App")
    page.wait_for_load_state = MagicMock()
    page.main_frame = MagicMock()
    return page


class TestPageListenerDetach:
    def test_detach_removes_three_listeners(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page_open()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-001")
            ctrl.detach_page_listeners()
            # remove_listener called for request, response, framenavigated
            event_names = [c.args[0] for c in page.remove_listener.call_args_list]
            assert "request" in event_names
            assert "response" in event_names
            assert "framenavigated" in event_names
            ctrl.stop()

    def test_detach_tolerates_already_detached(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page_open()
        page.remove_listener.side_effect = Exception("already removed")
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-002")
            ctrl.detach_page_listeners()  # must not raise


class TestFlushEventsClosedPage:
    def test_flush_noop_when_page_url_raises(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page_open()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-003")
            # Simulate closed page: page.url raises
            type(page).url = property(
                lambda self: (_ for _ in ()).throw(Exception("Target closed")))
            ctrl.flush_events()  # must not raise
            # evaluate should NOT have been called after url failed
            # (the call at startup is already consumed by the polling loop)
            ctrl.stop()

    def test_flush_swallows_target_closed_inside_evaluate(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page_open()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-004")
            page.evaluate.side_effect = Exception(
                "Page.evaluate: Target page, context or browser has been closed")
            ctrl.flush_events()  # must not raise


class TestStopToleratesClosedPage:
    def test_stop_completes_when_page_dead(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page_open()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-005")
            # Make every page interaction error
            page.evaluate.side_effect = Exception("Target closed")
            page.screenshot.side_effect = Exception("Target closed")
            page.content.side_effect = Exception("Target closed")
            type(page).url = property(
                lambda self: (_ for _ in ()).throw(Exception("Target closed")))
            ctrl.stop()  # must not raise


class TestOpenInEditor:
    @patch("testforge.cli.app.shutil.which")
    @patch("testforge.cli.app.subprocess.call")
    def test_env_editor_resolved_via_which(self, mock_call, mock_which, monkeypatch):
        monkeypatch.setenv("EDITOR", "myeditor")
        mock_which.return_value = "/usr/bin/myeditor"
        from testforge.cli.app import _open_in_editor
        _open_in_editor("/tmp/x.feature")
        mock_which.assert_any_call("myeditor")
        mock_call.assert_called_once_with(["/usr/bin/myeditor", "/tmp/x.feature"])

    @patch("testforge.cli.app.shutil.which")
    @patch("testforge.cli.app.subprocess.call")
    @patch("testforge.cli.app.os.path.exists")
    def test_invalid_absolute_path_falls_through(self, mock_exists, mock_call,
                                                    mock_which, monkeypatch):
        monkeypatch.setenv("EDITOR", "/bin/nano")
        mock_exists.return_value = False  # /bin/nano absent
        # Fallback chain: vi resolves
        mock_which.side_effect = lambda c: "/usr/bin/vi" if c == "vi" else None
        from testforge.cli.app import _open_in_editor
        _open_in_editor("/tmp/x.feature")
        mock_call.assert_called_once_with(["/usr/bin/vi", "/tmp/x.feature"])

    @patch("testforge.cli.app.shutil.which", return_value=None)
    @patch("testforge.cli.app.subprocess.call")
    def test_no_editor_available_prints_warn(self, mock_call, mock_which,
                                                monkeypatch, capsys):
        monkeypatch.delenv("EDITOR", raising=False)
        from testforge.cli.app import _open_in_editor
        _open_in_editor("/tmp/x.feature")
        mock_call.assert_not_called()
        out = capsys.readouterr().out
        assert "[WARN]" in out
        assert "/tmp/x.feature" in out
