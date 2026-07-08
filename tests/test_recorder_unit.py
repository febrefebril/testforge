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
    """Testes para prevenir sobrescrita silenciosa de gravacoes existentes."""

    def test_no_conflict_returns_original_name(self):
        """Quando o diretorio nao existe, o nome original e retornado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test"

    def test_conflict_returns_suffixed_name(self):
        """Quando o diretorio existe, retorna name_2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "my_test"))
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test_2"

    def test_multiple_conflicts_returns_next_available(self):
        """Quando name e name_2 existem, retorna name_3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "my_test"))
            os.makedirs(os.path.join(tmpdir, "my_test_2"))
            result = RecordingSessionManager._resolve_name(tmpdir, "my_test")
            assert result == "my_test_3"

    def test_name_with_trailing_suffix(self):
        """Quando o nome base ja tem sufixo _N e esse diretorio tambem existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "login_flow_2"))
            result = RecordingSessionManager._resolve_name(tmpdir, "login_flow_2")
            assert result == "login_flow_2_2"

    def test_start_uses_resolved_name(self):
        """RecordingSessionManager.start() deve criar diretorio com nome resolvido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RecordingSessionManager(tmpdir)
            # Primeira sessao
            s1 = mgr.start("demo", "app", "http://localhost")
            assert s1.recording_id == "demo"
            assert os.path.isdir(os.path.join(tmpdir, "demo"))
            mgr.stop()
            mgr.finalize()

            # Segunda sessao com mesmo nome — deve obter _2
            s2 = mgr.start("demo", "app", "http://localhost")
            assert s2.recording_id == "demo_2"
            assert os.path.isdir(os.path.join(tmpdir, "demo_2"))
            assert not os.path.isdir(os.path.join(tmpdir, "demo", "raw_events.jsonl"))  # intacto


class TestRecorderControllerEventId:
    """Testes para event_id monotono dentro de uma sessao de gravacao."""

    def _make_mock_event_data(self, event_type="click", url="http://localhost/test"):
        """Cria dados minimos de evento conforme recebido do JS."""
        return {
            "event_id": "evt_ignored",  # ID gerado pelo JS — deve ser ignorado pelo Python
            "type": event_type,
            "timestamp": "2025-01-01T00:00:00Z",
            "url": url,
            "page_title": "Test Page",
            "target": None,
            "value": None,
        }

    def test_event_ids_monotonic_across_flushes(self):
        """event_id deve ser unico e monotono — nunca resetado dentro de uma sessao de gravacao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            # Patch _capture_snapshots para evitar chamadas reais do Playwright
            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-MONO-001")

                # Simula 3 ciclos de flush separados (como apos navegacao)
                for _ in range(3):
                    recorder._persist_raw_event(self._make_mock_event_data("navigation"))
                    recorder._persist_raw_event(self._make_mock_event_data("click"))
                    recorder._persist_raw_event(self._make_mock_event_data("fill"))

            # Le eventos armazenados
            events_path = os.path.join(tmpdir, "REC-MONO-001", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            assert len(event_ids) == 9, f"Esperados 9 eventos, obtidos {len(event_ids)}"

            # Todos os IDs devem ser unicos
            assert len(set(event_ids)) == len(event_ids), (
                f"event_ids duplicados encontrados: {event_ids}"
            )

            # Sequencia monotona: evt_00001, evt_00002, ...
            expected_ids = [f"evt_{i:05d}" for i in range(1, 10)]
            assert event_ids == expected_ids, (
                f"Esperado {expected_ids}, obtido {event_ids}"
            )

    def test_event_counter_does_not_reset_on_multiple_starts(self):
        """Chamar start() nao deve resetar o contador de eventos — ele permanece monotono ao longo da sessao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-NORESET-001")
                recorder._persist_raw_event(self._make_mock_event_data("click"))
                recorder._persist_raw_event(self._make_mock_event_data("click"))

                # Simula fim da primeira sessao
                recorder._session_manager.stop()
                recorder._session_manager.finalize()

                # Inicia outra gravacao — contador deve continuar, sem resetar
                recorder.start(recording_id="REC-NORESET-002")
                recorder._persist_raw_event(self._make_mock_event_data("click"))

            events_path = os.path.join(tmpdir, "REC-NORESET-002", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            # Primeira gravacao teve evt_00001, evt_00002; segunda deve comecar em evt_00003
            assert event_ids[0] == "evt_00003", (
                f"Contador resetado! Esperado evt_00003, obtido {event_ids[0]}"
            )

    def test_js_generated_event_id_is_ignored(self):
        """Contador do Python deve ser a unica fonte da verdade — event_id do JS descartado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)

            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-IGNOREJS-001")

                # JS envia event_id="evt_bad_js_id" — Python deve ignorar
                data = self._make_mock_event_data("click")
                data["event_id"] = "evt_bad_js_id"
                recorder._persist_raw_event(data)

                data2 = self._make_mock_event_data("fill")
                data2["event_id"] = "evt_bad_js_id"  # Contador JS "resetou" na navegacao
                recorder._persist_raw_event(data2)

            events_path = os.path.join(tmpdir, "REC-IGNOREJS-001", "raw_events.jsonl")
            with open(events_path) as f:
                events = [json.loads(line) for line in f]

            event_ids = [e["event_id"] for e in events]
            assert event_ids == ["evt_00001", "evt_00002"], (
                f"Event_id do JS vazou! Esperados IDs unicos, obtidos {event_ids}"
            )


class TestRecorderH1BrowserCloseGracefulStop:
    """Hotfix H1: fechar o navegador/pagina equivale a Shift+S."""

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
            # page.on('close', ...) deve estar entre as chamadas page.on
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


class TestHotfix14ShiftSOverlayUX:
    """Hotfix 14: Shift+S atualiza interface do overlay antes do navegador fechar."""

    def test_overlay_js_defines_showStoppingUI(self):
        """Garante que o JS do overlay expoe o helper que atualiza o banner."""
        from testforge.recorder.recorder_controller import RecorderController
        assert "_showStoppingUI" in RecorderController._OVERLAY_JS

    def test_confirmStop_paths_call_showStoppingUI(self):
        """Ambos os ramos do _confirmStop (com/sem asserts) acionam a atualizacao da interface."""
        from testforge.recorder.recorder_controller import RecorderController
        js = RecorderController._OVERLAY_JS
        # Os dois locais de STOP push devem ambos seguir uma chamada _showStoppingUI.
        # Usa verificacao grossa: conta invocacoes _showStoppingUI() >= 2.
        invocations = js.count("_showStoppingUI()")
        assert invocations >= 2, (
            f"esperadas pelo menos 2 chamadas _showStoppingUI(), encontradas {invocations}"
        )

    def test_showStoppingUI_disables_buttons_and_shows_notice(self):
        """O helper alterna estado do botao e injeta #tf-stop-notice."""
        from testforge.recorder.recorder_controller import RecorderController
        js = RecorderController._OVERLAY_JS
        # O corpo deve desabilitar o botao de parada, alterar o texto de status,
        # e adicionar um elemento de aviso.
        assert "tf-stop-notice" in js
        assert "Encerrando" in js
        assert "btnStop.disabled = true" in js


class TestHotfix15RecordingsRoot:
    """Hotfix 15: recordings_root deve ser absoluto, ancorado na raiz do projeto."""

    def test_recorder_uses_passed_recordings_root(self):
        """RecorderController respeita um caminho recordings_root explicito."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_page = MagicMock()
            recorder = RecorderController(mock_page, recordings_root=tmpdir)
            with patch.object(recorder, "_capture_snapshots"):
                recorder.start(recording_id="REC-PATH-001")
            # Verifica se o diretorio da gravacao esta dentro de tmpdir
            assert os.path.isdir(os.path.join(tmpdir, "REC-PATH-001"))

    def test_recorder_default_recordings_root_is_relative(self):
        """'recordings' padrao e relativo (protecao de regressao para o hotfix 15)."""
        # Se alguem mudar o padrao para absoluto sem pensar, a
        # ancoragem da CLI vira um no-op. Fixa o contrato.
        import inspect
        sig = inspect.signature(RecorderController.__init__)
        default = sig.parameters["recordings_root"].default
        assert default == "recordings"
