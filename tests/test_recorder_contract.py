"""Recorder contract tests — covers flush, navigation, overlay injection, and serialization gaps.

All tests are unit tests; no browser required.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from testforge.recorder.recorder_controller import RecorderController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctrl(tmp_path, evaluate_return=None):
    page = MagicMock()
    page.evaluate.return_value = evaluate_return
    page.url = "http://localhost"
    page.title.return_value = "Page"
    ctrl = RecorderController(page, recordings_root=str(tmp_path))
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    return ctrl, page


# ---------------------------------------------------------------------------
# B1: flush_events integration
# ---------------------------------------------------------------------------

class TestFlushEventsIntegration:
    """flush_events() must call field/mutation flush regardless of JS event outcome."""

    def test_flush_calls_field_snapshot_flush(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path, evaluate_return={"events": [], "steps": []})
        with patch.object(ctrl, "_flush_field_snapshots", return_value=0) as mock_fsnap:
            with patch.object(ctrl, "_flush_value_mutations", return_value=0):
                ctrl.flush_events()
        mock_fsnap.assert_called_once()

    def test_flush_calls_value_mutation_flush(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path, evaluate_return={"events": [], "steps": []})
        with patch.object(ctrl, "_flush_field_snapshots", return_value=0):
            with patch.object(ctrl, "_flush_value_mutations", return_value=0) as mock_vmut:
                ctrl.flush_events()
        mock_vmut.assert_called_once()

    def test_flush_events_js_exception_does_not_crash(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("page closed")
        ctrl.flush_events()  # must not raise

    def test_flush_events_js_exception_still_runs_field_flush(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("page closed")
        with patch.object(ctrl, "_flush_field_snapshots", return_value=0) as mock_fsnap:
            with patch.object(ctrl, "_flush_value_mutations", return_value=0):
                ctrl.flush_events()
        mock_fsnap.assert_called_once()


# ---------------------------------------------------------------------------
# B2: Field snapshot flushing
# ---------------------------------------------------------------------------

class TestFieldSnapshotFlushing:
    """_flush_field_snapshots() reads JS queue, persists, and returns count."""

    def test_happy_path_persists_to_file(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        snapshot = {"field": "cpf", "value": "123", "ts": "2026-01-01T00:00:00Z"}
        page.evaluate.return_value = [snapshot]

        count = ctrl._flush_field_snapshots()

        assert count == 1
        path = tmp_path / "field_snapshots.jsonl"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["field"] == "cpf"

    def test_multiple_snapshots_written_as_separate_lines(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = [
            {"field": "cpf", "value": "1"},
            {"field": "nome", "value": "2"},
        ]
        count = ctrl._flush_field_snapshots()
        assert count == 2
        lines = (tmp_path / "field_snapshots.jsonl").read_text().splitlines()
        assert len(lines) == 2

    def test_empty_queue_returns_zero(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = []
        assert ctrl._flush_field_snapshots() == 0

    def test_none_queue_returns_zero(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = None
        assert ctrl._flush_field_snapshots() == 0

    def test_js_exception_returns_zero(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("detached")
        assert ctrl._flush_field_snapshots() == 0


# ---------------------------------------------------------------------------
# B3: Value mutation flushing
# ---------------------------------------------------------------------------

class TestValueMutationFlushing:
    """_flush_value_mutations() reads JS queue, persists, and returns count."""

    def test_happy_path_persists_to_file(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        mutation = {"field": "senha", "old": "", "new": "abc", "ts": "2026-01-01T00:00:00Z"}
        page.evaluate.return_value = [mutation]

        count = ctrl._flush_value_mutations()

        assert count == 1
        path = tmp_path / "value_mutations.jsonl"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["field"] == "senha"

    def test_multiple_mutations_appended(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = [
            {"field": "a", "old": "", "new": "1"},
            {"field": "b", "old": "", "new": "2"},
        ]
        ctrl._flush_value_mutations()
        lines = (tmp_path / "value_mutations.jsonl").read_text().splitlines()
        assert len(lines) == 2

    def test_empty_queue_returns_zero(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = []
        assert ctrl._flush_value_mutations() == 0

    def test_js_exception_returns_zero(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("closed")
        assert ctrl._flush_value_mutations() == 0


# ---------------------------------------------------------------------------
# B4: Final state snapshot
# ---------------------------------------------------------------------------

class TestFinalStateSnapshot:
    """_capture_final_state_snapshot() writes JSON only when state is non-null."""

    def test_writes_file_when_state_present(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        state = {"fields": {"cpf": "123"}, "url": "http://localhost/result"}
        page.evaluate.return_value = state

        ctrl._capture_final_state_snapshot("test_reason")

        path = tmp_path / "final_state_snapshot.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["url"] == "http://localhost/result"

    def test_no_file_when_state_is_null(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.return_value = None

        ctrl._capture_final_state_snapshot("test_reason")

        path = tmp_path / "final_state_snapshot.json"
        assert not path.exists()

    def test_js_exception_does_not_raise(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("session closed")
        ctrl._capture_final_state_snapshot("reason")  # must not raise


# ---------------------------------------------------------------------------
# B5: Frame navigation
# ---------------------------------------------------------------------------

class TestFrameNavigation:
    """_on_framenavigated() ignores sub-frames; creates navigation event for main frame."""

    def _ctrl_for_nav(self, tmp_path):
        page = MagicMock()
        page.url = "http://localhost/after"
        page.title.return_value = "After Page"
        ctrl = RecorderController(page, recordings_root=str(tmp_path))
        ctrl._store = MagicMock()
        ctrl._store._session_dir = str(tmp_path)
        return ctrl, page

    def test_sub_frame_ignored(self, tmp_path):
        ctrl, page = self._ctrl_for_nav(tmp_path)
        sub_frame = MagicMock()
        page.main_frame = MagicMock()  # different object from sub_frame
        initial_counter = ctrl._event_counter
        ctrl._on_framenavigated(sub_frame)
        assert ctrl._event_counter == initial_counter

    def test_main_frame_increments_event_counter(self, tmp_path):
        ctrl, page = self._ctrl_for_nav(tmp_path)
        main_frame = MagicMock()
        page.main_frame = main_frame
        ctrl._on_framenavigated(main_frame)
        assert ctrl._event_counter == 1

    def test_main_frame_appends_navigation_event(self, tmp_path):
        ctrl, page = self._ctrl_for_nav(tmp_path)
        main_frame = MagicMock()
        page.main_frame = main_frame
        ctrl._on_framenavigated(main_frame)
        ctrl._store.append_event.assert_called_once()
        event = ctrl._store.append_event.call_args[0][0]
        assert event.event_type == "navigation"

    def test_navigation_event_uses_page_url(self, tmp_path):
        ctrl, page = self._ctrl_for_nav(tmp_path)
        main_frame = MagicMock()
        page.main_frame = main_frame
        page.url = "http://localhost/success"
        ctrl._on_framenavigated(main_frame)
        event = ctrl._store.append_event.call_args[0][0]
        assert event.url == "http://localhost/success"

    def test_navigation_falls_back_to_frame_url_on_page_exception(self, tmp_path):
        ctrl, page = self._ctrl_for_nav(tmp_path)
        main_frame = MagicMock()
        main_frame.url = "http://localhost/fallback"
        page.main_frame = main_frame
        type(page).url = property(lambda self: (_ for _ in ()).throw(Exception("closed")))
        ctrl._on_framenavigated(main_frame)
        event = ctrl._store.append_event.call_args[0][0]
        assert event.url == "http://localhost/fallback"


# ---------------------------------------------------------------------------
# B6: Overlay injection via start()
# ---------------------------------------------------------------------------

class TestOverlayInjection:
    """start() must inject context script and overlay JS via add_init_script."""

    def _start_ctrl(self, tmp_path, **kwargs):
        page = MagicMock()
        page.evaluate.return_value = None
        ctrl = RecorderController(page, recordings_root=str(tmp_path))
        with patch("testforge.recorder.recorder_controller.RawRecordingStore"):
            ctrl.start(recording_id="REC-INJ-001", **kwargs)
        return ctrl, page

    def test_add_init_script_called_at_least_twice(self, tmp_path):
        _, page = self._start_ctrl(tmp_path)
        assert page.add_init_script.call_count >= 2

    def test_context_script_contains_recording_id(self, tmp_path):
        _, page = self._start_ctrl(tmp_path)
        first_call_arg = page.add_init_script.call_args_list[0][0][0]
        assert "REC-INJ-001" in first_call_arg

    def test_context_script_contains_system(self, tmp_path):
        _, page = self._start_ctrl(tmp_path, system="SIOPI")
        first_call_arg = page.add_init_script.call_args_list[0][0][0]
        assert "SIOPI" in first_call_arg

    def test_context_script_contains_suite(self, tmp_path):
        _, page = self._start_ctrl(tmp_path, suite="cadastro")
        first_call_arg = page.add_init_script.call_args_list[0][0][0]
        assert "cadastro" in first_call_arg

    def test_context_script_contains_test_case(self, tmp_path):
        _, page = self._start_ctrl(tmp_path, test_case="login_cpf")
        first_call_arg = page.add_init_script.call_args_list[0][0][0]
        assert "login_cpf" in first_call_arg

    def test_overlay_js_injected_as_second_init_script(self, tmp_path):
        from testforge.recorder.recorder_controller import _OVERLAY_JS
        _, page = self._start_ctrl(tmp_path)
        second_call_arg = page.add_init_script.call_args_list[1][0][0]
        assert second_call_arg == _OVERLAY_JS


# ---------------------------------------------------------------------------
# B7: Start config persistence
# ---------------------------------------------------------------------------

class TestStartConfigPersistence:
    """start() must save evidence_level and headless to recording_config metadata."""

    def test_metadata_config_saved_on_start(self, tmp_path):
        page = MagicMock()
        ctrl = RecorderController(page, recordings_root=str(tmp_path))
        store_mock = MagicMock()
        with patch("testforge.recorder.recorder_controller.RawRecordingStore", return_value=store_mock):
            ctrl.start("REC-CFG-001", evidence_level="full", headless=True)
        store_mock.save_metadata.assert_called_once_with(
            "recording_config",
            {"evidence_level": "full", "headless": True},
        )

    def test_default_evidence_level_is_light(self, tmp_path):
        page = MagicMock()
        ctrl = RecorderController(page, recordings_root=str(tmp_path))
        store_mock = MagicMock()
        with patch("testforge.recorder.recorder_controller.RawRecordingStore", return_value=store_mock):
            ctrl.start("REC-CFG-002")
        call_kwargs = store_mock.save_metadata.call_args[0][1]
        assert call_kwargs["evidence_level"] == "light"
        assert call_kwargs["headless"] is False


# ---------------------------------------------------------------------------
# B8: Raw event target mapping
# ---------------------------------------------------------------------------

class TestRawEventTargetMapping:
    """_persist_raw_event() must faithfully map JS target dict to TargetInfo."""

    def _ctrl(self, tmp_path):
        ctrl, _ = _make_ctrl(tmp_path)
        with patch.object(ctrl, "_capture_snapshots"):
            pass
        return ctrl

    def test_full_target_all_fields_preserved(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        data = {
            "type": "click",
            "timestamp": "2026-01-01T00:00:00Z",
            "url": "http://localhost",
            "page_title": "Test",
            "target": {
                "tag": "button",
                "text": "Enviar",
                "role": "button",
                "accessible_name": "Enviar formulário",
                "id": "btn-submit",
                "name": "submit",
                "test_id": "btn-submit-data",
                "placeholder": None,
                "label": "Enviar",
                "className": "btn btn-primary",
                "type": "submit",
                "value": None,
                "all_attributes": {"data-action": "submit"},
                "class_list": ["btn", "btn-primary"],
                "aria_attrs": {"aria-disabled": "false"},
                "data_attrs": {"data-action": "submit"},
                "parent_text": "Form section",
                "css_path": "#btn-submit",
                "xpath": "//button[@id='btn-submit']",
                "nth_child": 3,
                "sibling_summary": ["input", "span"],
                "inner_html": "Enviar",
                "bounding_box": {"x": 10, "y": 20, "width": 100, "height": 40},
            },
        }
        with patch.object(ctrl, "_capture_snapshots"):
            ctrl._persist_raw_event(data)
        ctrl._store.append_event.assert_called_once()
        event = ctrl._store.append_event.call_args[0][0]
        t = event.target
        assert t.tag == "button"
        assert t.role == "button"
        assert t.accessible_name == "Enviar formulário"
        assert t.aria_attrs == {"aria-disabled": "false"}
        assert t.data_attrs == {"data-action": "submit"}
        assert t.nth_child == 3
        assert t.sibling_summary == ["input", "span"]

    def test_none_target_creates_event_with_no_target(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        data = {
            "type": "navigation",
            "timestamp": "2026-01-01T00:00:00Z",
            "url": "http://localhost/page2",
            "page_title": "Page 2",
            "target": None,
        }
        with patch.object(ctrl, "_capture_snapshots"):
            ctrl._persist_raw_event(data)
        event = ctrl._store.append_event.call_args[0][0]
        assert event.target is None

    def test_missing_target_fields_default_gracefully(self, tmp_path):
        ctrl = self._ctrl(tmp_path)
        data = {
            "type": "click",
            "timestamp": "2026-01-01T00:00:00Z",
            "target": {"tag": "div"},  # minimal — most fields absent
        }
        with patch.object(ctrl, "_capture_snapshots"):
            ctrl._persist_raw_event(data)
        event = ctrl._store.append_event.call_args[0][0]
        assert event.target.tag == "div"
        assert event.target.aria_attrs == {}
        assert event.target.nth_child == 0


# ---------------------------------------------------------------------------
# B9: Stop behavior — sensitive alerts
# ---------------------------------------------------------------------------

class TestStopSensitiveAlerts:
    """stop() saves sensitive_data_alert only when alerts exist."""

    def _ctrl_with_alerts(self, tmp_path, alerts):
        page = MagicMock()
        page.evaluate.return_value = None
        ctrl = RecorderController(page, recordings_root=str(tmp_path))
        ctrl._store = MagicMock()
        ctrl._session_manager = MagicMock()
        ctrl._session_manager.stop.return_value = MagicMock(recording_id="REC-ALERT-001")
        ctrl._sensitive_alerts = alerts
        return ctrl

    def test_stop_saves_sensitive_alerts_when_present(self, tmp_path):
        ctrl = self._ctrl_with_alerts(tmp_path, [{"type": "CPF", "field": "cpf"}])
        ctrl.stop()
        ctrl._store.save_sensitive_data_alert.assert_called_once()

    def test_stop_does_not_save_sensitive_alert_when_empty(self, tmp_path):
        ctrl = self._ctrl_with_alerts(tmp_path, [])
        ctrl.stop()
        ctrl._store.save_sensitive_data_alert.assert_not_called()

    def test_stop_saves_network_log_always(self, tmp_path):
        ctrl = self._ctrl_with_alerts(tmp_path, [])
        ctrl.stop()
        ctrl._store.save_network_log.assert_called_once()


# ---------------------------------------------------------------------------
# C1: Auto-updater unit tests
# ---------------------------------------------------------------------------

class TestAutoUpdater:
    """check_and_apply_update() behavior under various config states."""

    def test_no_config_file_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        assert check_and_apply_update(tmp_path) is False

    def test_disabled_config_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text("enabled: false\n")
        assert check_and_apply_update(tmp_path) is False

    def test_enabled_config_calls_git_pull(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Already up to date.\n", stderr=""
            )
            check_and_apply_update(tmp_path)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "pull", "origin", "main"]

    def test_already_up_to_date_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Already up to date.\n", stderr=""
            )
            result = check_and_apply_update(tmp_path)
        assert result is False

    def test_git_pull_with_changes_returns_true(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Updating abc123..def456\nFast-forward\n", stderr=""
            )
            result = check_and_apply_update(tmp_path)
        assert result is True

    def test_git_not_found_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_and_apply_update(tmp_path)
        assert result is False

    def test_git_timeout_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            result = check_and_apply_update(tmp_path)
        assert result is False

    def test_git_nonzero_exit_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: origin\nbranch: main\nquiet: true\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="fatal: not a git repo\n"
            )
            result = check_and_apply_update(tmp_path)
        assert result is False

    def test_custom_remote_and_branch_used(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(
            "enabled: true\nremote: upstream\nbranch: hotfix/recorder-v2\nquiet: true\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Already up to date.\n", stderr=""
            )
            check_and_apply_update(tmp_path)
        args = mock_run.call_args[0][0]
        assert args == ["git", "pull", "upstream", "hotfix/recorder-v2"]

    def test_corrupt_yaml_returns_false(self, tmp_path):
        from testforge.updater.auto_updater import check_and_apply_update
        (tmp_path / "testforge_update.yml").write_text(": {\n")  # invalid YAML
        result = check_and_apply_update(tmp_path)
        assert result is False
