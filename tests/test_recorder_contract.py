"""Testes de contrato do Recorder — cobre flush, navegacao, injecao de overlay e lacunas de serializacao.

Todos os testes sao unitarios; nenhum navegador necessario.
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
# Auxiliares
# ---------------------------------------------------------------------------

_EMPTY_PAYLOAD = {"events": [], "steps": [], "commands": [], "fieldSnapshots": [], "valueMutations": []}


def _make_ctrl(tmp_path, evaluate_return=None):
    page = MagicMock()
    page.evaluate.return_value = evaluate_return if evaluate_return is not None else dict(_EMPTY_PAYLOAD)
    page.url = "http://localhost"
    page.title.return_value = "Page"
    ctrl = RecorderController(page, recordings_root=str(tmp_path))
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    return ctrl, page


# ---------------------------------------------------------------------------
# B1: Integracao flush_events
# ---------------------------------------------------------------------------

class TestFlushEventsIntegration:
    """flush_events() le todas as filas JS em uma unica chamada CDP."""

    def test_flush_persists_field_snapshots_from_payload(self, tmp_path):
        snapshot = {"timestamp": "2026-01-01T00:00:00Z", "fingerprint": "input#x[name=x]",
                    "identifiers": {}, "tag": "input", "type": "text", "value": "v",
                    "visibility": "visible", "enabled": True, "bounding_box": {}}
        payload = {**_EMPTY_PAYLOAD, "fieldSnapshots": [snapshot]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        path = tmp_path / "field_snapshots.jsonl"
        assert path.exists()

    def test_flush_persists_value_mutations_from_payload(self, tmp_path):
        mutation = {"field": "x", "old_value": "", "new_value": "abc", "ts": "2026-01-01T00:00:00Z"}
        payload = {**_EMPTY_PAYLOAD, "valueMutations": [mutation]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        path = tmp_path / "value_mutations.jsonl"
        assert path.exists()

    def test_flush_events_js_exception_does_not_crash(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("page closed")
        ctrl.flush_events()  # must not raise


# ---------------------------------------------------------------------------
# B2: Flush de snapshots de campo
# ---------------------------------------------------------------------------

class TestFieldSnapshotFlushing:
    """flush_events() persiste snapshots de campo recebidos no payload em lote."""

    def test_happy_path_persists_to_file(self, tmp_path):
        snapshot = {"field": "cpf", "value": "123", "ts": "2026-01-01T00:00:00Z"}
        payload = {**_EMPTY_PAYLOAD, "fieldSnapshots": [snapshot]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        path = tmp_path / "field_snapshots.jsonl"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["field"] == "cpf"

    def test_multiple_snapshots_written_as_separate_lines(self, tmp_path):
        payload = {**_EMPTY_PAYLOAD, "fieldSnapshots": [
            {"field": "cpf", "value": "1"},
            {"field": "nome", "value": "2"},
        ]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        lines = (tmp_path / "field_snapshots.jsonl").read_text().splitlines()
        assert len(lines) == 2

    def test_empty_snapshots_writes_nothing(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        ctrl.flush_events()
        assert not (tmp_path / "field_snapshots.jsonl").exists()

    def test_js_exception_does_not_crash(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("detached")
        ctrl.flush_events()  # must not raise


# ---------------------------------------------------------------------------
# B3: Flush de mutacoes de valor
# ---------------------------------------------------------------------------

class TestValueMutationFlushing:
    """flush_events() persiste mutacoes de valor recebidas no payload em lote."""

    def test_happy_path_persists_to_file(self, tmp_path):
        mutation = {"field": "senha", "old": "", "new": "abc", "ts": "2026-01-01T00:00:00Z"}
        payload = {**_EMPTY_PAYLOAD, "valueMutations": [mutation]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        path = tmp_path / "value_mutations.jsonl"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["field"] == "senha"

    def test_multiple_mutations_appended(self, tmp_path):
        payload = {**_EMPTY_PAYLOAD, "valueMutations": [
            {"field": "a", "old": "", "new": "1"},
            {"field": "b", "old": "", "new": "2"},
        ]}
        ctrl, page = _make_ctrl(tmp_path, evaluate_return=payload)
        ctrl.flush_events()
        lines = (tmp_path / "value_mutations.jsonl").read_text().splitlines()
        assert len(lines) == 2

    def test_empty_mutations_writes_nothing(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        ctrl.flush_events()
        assert not (tmp_path / "value_mutations.jsonl").exists()

    def test_js_exception_does_not_crash(self, tmp_path):
        ctrl, page = _make_ctrl(tmp_path)
        page.evaluate.side_effect = Exception("closed")
        ctrl.flush_events()  # must not raise


# ---------------------------------------------------------------------------
# B4: Snapshot de estado final
# ---------------------------------------------------------------------------

class TestFinalStateSnapshot:
    """_capture_final_state_snapshot() escreve JSON apenas quando estado nao e nulo."""

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
# B5: Navegacao de frame
# ---------------------------------------------------------------------------

class TestFrameNavigation:
    """_on_framenavigated() ignora sub-frames; cria evento de navegacao para frame principal."""

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
# B6: Injecao de overlay via start()
# ---------------------------------------------------------------------------

class TestOverlayInjection:
    """start() deve injetar script de contexto e JS de overlay via add_init_script."""

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
# B7: Persistencia de configuracao do start
# ---------------------------------------------------------------------------

class TestStartConfigPersistence:
    """start() deve salvar evidence_level e headless nos metadados recording_config."""

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
# B8: Mapeamento de target de evento raw
# ---------------------------------------------------------------------------

class TestRawEventTargetMapping:
    """_persist_raw_event() deve mapear fielmente dict target do JS para TargetInfo."""

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
            "target": {"tag": "div"},  # minimo — maioria dos campos ausentes
        }
        with patch.object(ctrl, "_capture_snapshots"):
            ctrl._persist_raw_event(data)
        event = ctrl._store.append_event.call_args[0][0]
        assert event.target.tag == "div"
        assert event.target.aria_attrs == {}
        assert event.target.nth_child == 0


# ---------------------------------------------------------------------------
# B9: Comportamento do stop — alertas sensiveis
# ---------------------------------------------------------------------------

class TestStopSensitiveAlerts:
    """stop() salva sensitive_data_alert apenas quando alertas existem."""

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
# C1: Testes unitarios do auto-updater
# ---------------------------------------------------------------------------

class TestAutoUpdater:
    """comportamento do check_and_apply_update() sob varios estados de configuracao."""

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
        (tmp_path / "testforge_update.yml").write_text(": {\n")  # YAML invalido
        result = check_and_apply_update(tmp_path)
        assert result is False
