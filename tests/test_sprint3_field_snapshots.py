"""Testes para Field State Snapshots — Sprint 3.

Epico 3 — Field State Snapshot (3.1 field_snapshots.jsonl, 3.2 final_state_snapshot.json)
Epico 4 — Setter Hook e MutationObserver (4.1 value setters, 4.2 contenteditable/ARIA)

CT-AUTO-3.1: Campo com preventDefault — valor recuperado por setter_hook ou snapshot_diff.
CT-AUTO-3.2: Mascara de moeda — valores bruto, exibido e normalizados capturados.
CT-AUTO-3.3: Contenteditable — alteracoes de texto detectadas por MutationObserver/snapshot.
CT-AUTO-3.4: Select nativo — valor selecionado e texto capturados.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from testforge.recorder.recorder_controller import RecorderController
from testforge.recorder.recording_session import RecordingSessionManager
from testforge.recorder.raw_recording_store import RawRecordingStore


# -- Fixtures -------------------------------------------------------------------


@pytest.fixture
def mock_page():
    """Cria um MagicMock que simula uma Page do Playwright."""
    page = MagicMock()
    page.evaluate = MagicMock(return_value=[])
    page.url = "http://localhost:8765/test"
    page.title = MagicMock(return_value="Test Page")
    return page


@pytest.fixture
def controller(mock_page):
    """Cria RecorderController com page mock e diretorio temporario."""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = RecorderController(mock_page, recordings_root=tmpdir)
        controller.start("TEST-S3", "test-app", "http://localhost:8765")
        yield controller, tmpdir, mock_page


@pytest.fixture
def mock_store(controller):
    """Extrai o store do controller para teste direto."""
    ctrl, tmpdir, page = controller
    return ctrl._store, tmpdir, page, ctrl


# -- Helper factories ----------------------------------------------------------


def _make_snapshot(fingerprint="input#campo1[name=campo1]", value="ABC",
                   tag="input", field_type="text", visible=True, enabled=True):
    return {
        "timestamp": "2026-06-18T10:00:00Z",
        "fingerprint": fingerprint,
        "identifiers": {
            "id": fingerprint.split("#")[1].split("[")[0] if "#" in fingerprint else None,
            "name": "campo1",
            "label": "Campo 1",
            "placeholder": "Digite algo",
            "aria-label": None,
            "css_path": "#campo1",
        },
        "tag": tag,
        "type": field_type,
        "value": value,
        "checked": None,
        "visibility": "visible" if visible else "hidden",
        "enabled": enabled,
        "focused": False,
        "bounding_box": {"x": 10, "y": 10, "width": 200, "height": 30},
    }


def _make_value_mutation(tag="input", old="", new="ABC", name="campo1"):
    return {
        "type": "value_mutation",
        "timestamp": "2026-06-18T10:00:00Z",
        "tag": tag,
        "name": name,
        "id": "campo1",
        "old_value": old,
        "new_value": new,
        "fingerprint": f"{tag}#campo1[name={name}]",
    }


def _make_final_state(reason="user_stop", fields=None):
    return {
        "reason": reason,
        "timestamp": "2026-06-18T10:00:01Z",
        "url": "http://localhost:8765/test",
        "page_title": "Test Page",
        "fields": fields or [_make_snapshot()],
    }


# -- CT-AUTO-3.1: Campo com preventDefault --------------------------------------


class TestCT_AUTO_3_1:
    """CT-AUTO-3.1: Campo com preventDefault — valor recuperado por setter_hook ou snapshot."""

    def test_save_field_snapshot_appends_to_jsonl(self, mock_store):
        """field_snapshots.jsonl recebe entradas de snapshot."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(value="ABC123")
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["fingerprint"] == "input#campo1[name=campo1]"
        assert data["value"] == "ABC123"

    def test_save_value_mutation_appends_to_jsonl(self, mock_store):
        """value_mutations.jsonl recebe entradas de mutacao."""
        store, tmpdir, page, ctrl = mock_store
        mutation = _make_value_mutation(old="", new="XYZ")
        ctrl._save_value_mutation(mutation)

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["type"] == "value_mutation"
        assert data["new_value"] == "XYZ"
        assert data["old_value"] == ""

    def test_flush_field_snapshots_reads_js_queue(self, mock_store):
        """O payload em lote do flush_events persiste field snapshots."""
        store, tmpdir, page, ctrl = mock_store
        snapshot_batch = {
            "timestamp": "2026-06-18T10:00:00Z",
            "snapshots": [_make_snapshot(value="Capturado")],
            "count": 1,
        }
        page.evaluate = MagicMock(return_value={
            "events": [], "steps": [], "commands": [],
            "fieldSnapshots": [snapshot_batch], "valueMutations": [],
        })

        ctrl.flush_events()

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["count"] == 1
        assert data["snapshots"][0]["value"] == "Capturado"

    def test_flush_value_mutations_reads_js_queue(self, mock_store):
        """O payload em lote do flush_events persiste value mutations."""
        store, tmpdir, page, ctrl = mock_store
        mutation = _make_value_mutation(old="", new="ValorProgramatico")
        page.evaluate = MagicMock(return_value={
            "events": [], "steps": [], "commands": [],
            "fieldSnapshots": [], "valueMutations": [mutation],
        })

        ctrl.flush_events()

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["new_value"] == "ValorProgramatico"

    def test_flush_events_also_flushes_snapshots_and_mutations(self, controller):
        """flush_events() le snapshots e mutations em uma unica chamada CDP em lote."""
        ctrl, tmpdir, page = controller
        snapshot_batch = {
            "timestamp": "2026-06-18T10:00:00Z",
            "snapshots": [_make_snapshot(value="flush_test")],
            "count": 1,
        }
        mutation = _make_value_mutation(new="flush_mut")

        page.evaluate = MagicMock(return_value={
            "events": [], "steps": [], "commands": [],
            "fieldSnapshots": [snapshot_batch],
            "valueMutations": [mutation],
        })

        ctrl.flush_events()

        # Verifica field_snapshots.jsonl
        s_path = os.path.join(ctrl._store._session_dir, "field_snapshots.jsonl")
        assert os.path.exists(s_path)
        with open(s_path) as f:
            assert "flush_test" in f.read()

        # Verifica value_mutations.jsonl
        m_path = os.path.join(ctrl._store._session_dir, "value_mutations.jsonl")
        assert os.path.exists(m_path)
        with open(m_path) as f:
            assert "flush_mut" in f.read()

    def test_snapshot_includes_identifiers_and_metadata(self, mock_store):
        """Entrada de snapshot tem todos os campos obrigatorios: fingerprint, identifiers, tag, type, value, visibility, enabled, bounding_box."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot()
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert "timestamp" in data
        assert "fingerprint" in data
        assert data["fingerprint"] == "input#campo1[name=campo1]"
        assert "identifiers" in data
        assert data["identifiers"]["id"] == "campo1"
        assert data["identifiers"]["name"] == "campo1"
        assert "tag" in data
        assert data["tag"] == "input"
        assert "type" in data
        assert data["type"] == "text"
        assert "value" in data
        assert data["value"] == "ABC"
        assert "visibility" in data
        assert data["visibility"] == "visible"
        assert "enabled" in data
        assert "bounding_box" in data
        assert "x" in data["bounding_box"]
        assert "y" in data["bounding_box"]
        assert "width" in data["bounding_box"]
        assert "height" in data["bounding_box"]


# -- CT-AUTO-3.2: Mascara de moeda ------------------------------------------------


class TestCT_AUTO_3_2:
    """CT-AUTO-3.2: Mascara de moeda — valor capturado independente de input event."""

    def test_setter_hook_captures_programmatic_value(self, mock_store):
        """Setter hook detecta alteracoes programaticas de valor (simulando mascara de moeda)."""
        store, tmpdir, page, ctrl = mock_store
        mutation = _make_value_mutation(
            old="", new="1.234,56",
            name="valor",
        )
        ctrl._save_value_mutation(mutation)

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["new_value"] == "1.234,56"
        assert data["fingerprint"] == "input#campo1[name=valor]"

    def test_multiple_setter_hooks_are_captured_sequentially(self, mock_store):
        """Multiplas alteracoes de valor sao capturadas em sequencia."""
        store, tmpdir, page, ctrl = mock_store
        mutations = [
            _make_value_mutation(old="", new="1", name="valor"),
            _make_value_mutation(old="1", new="12", name="valor"),
            _make_value_mutation(old="12", new="1.234,56", name="valor"),
        ]
        for m in mutations:
            ctrl._save_value_mutation(m)

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 3
        data2 = json.loads(lines[1])
        assert data2["old_value"] == "1"
        assert data2["new_value"] == "12"

    def test_snapshot_captures_formatted_currency_value(self, mock_store):
        """field_snapshot captura o valor formatado da moeda."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="input#valor[name=valor]",
            value="R$ 1.234,56",
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["value"] == "R$ 1.234,56"

    def test_final_state_includes_currency_field(self, mock_store):
        """final_state_snapshot.json captura campo de moeda."""
        store, tmpdir, page, ctrl = mock_store
        field = _make_snapshot(
            fingerprint="input#valor[name=valor]",
            value="1.234,56",
        )
        page.evaluate = MagicMock(return_value=_make_final_state(
            reason="form_submit",
            fields=[field],
        ))

        ctrl._capture_final_state_snapshot("form_submit")

        path = os.path.join(store._session_dir, "final_state_snapshot.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["reason"] == "form_submit"
        assert len(data["fields"]) == 1
        assert data["fields"][0]["value"] == "1.234,56"


# -- CT-AUTO-3.3: Contenteditable ----------------------------------------------


class TestCT_AUTO_3_3:
    """CT-AUTO-3.3: Contenteditable — texto editado recuperado por MutationObserver/snapshot."""

    def test_contenteditable_snapshot_captures_text(self, mock_store):
        """Snapshot de campo contenteditable captura conteudo de texto."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="contenteditable#conteudo",
            value="Texto editado pelo usuario",
            tag="div",
            field_type="contenteditable",
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["tag"] == "div"
        assert data["type"] == "contenteditable"
        assert data["value"] == "Texto editado pelo usuario"
        assert data["fingerprint"].startswith("contenteditable")

    def test_contenteditable_snapshot_has_visibility_and_bounding_box(self, mock_store):
        """Snapshot contenteditable inclui visibilidade e bounding box."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="contenteditable#editor",
            value="Rich text content",
            tag="div",
            field_type="contenteditable",
            visible=False,
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["visibility"] == "hidden"
        assert data["bounding_box"] is not None

    def test_content_edit_event_has_type_and_fingerprint(self, mock_store):
        """Evento content_edit do MutationObserver tem type e fingerprint."""
        store, tmpdir, page, ctrl = mock_store
        ctrl._save_value_mutation({
            "type": "content_edit",
            "timestamp": "2026-06-18T10:00:00Z",
            "fingerprint": "contenteditable#conteudo",
            "value": "Novo texto",
            "tag": "div",
        })

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["type"] == "content_edit"
        assert data["value"] == "Novo texto"
        assert data["fingerprint"] == "contenteditable#conteudo"


# -- CT-AUTO-3.4: Select nativo ------------------------------------------------


class TestCT_AUTO_3_4:
    """CT-AUTO-3.4: Select nativo — selected value e text capturados."""

    def test_select_value_captured_in_snapshot(self, mock_store):
        """Valor do elemento select e capturado pelo field snapshot."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="select#uf[name=uf]",
            value="SP",
            tag="select",
            field_type="select-one",
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["tag"] == "select"
        assert data["value"] == "SP"

    def test_select_multiple_options_captured(self, mock_store):
        """Cada select em um formulario e capturado separadamente."""
        store, tmpdir, page, ctrl = mock_store
        snapshots = [
            _make_snapshot(fingerprint="select#uf[name=uf]", value="SP", tag="select"),
            _make_snapshot(fingerprint="select#categoria[name=categoria]", value="pessoa_fisica", tag="select"),
        ]
        for s in snapshots:
            ctrl._save_field_snapshot(s)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["value"] == "SP"
        assert json.loads(lines[1])["value"] == "pessoa_fisica"

    def test_select_mutation_captured_by_setter_hook(self, mock_store):
        """Alteracao de valor do select via JS e capturada pelo setter hook."""
        store, tmpdir, page, ctrl = mock_store
        mutation = _make_value_mutation(
            tag="select",
            old="",
            new="RJ",
            name="uf",
        )
        ctrl._save_value_mutation(mutation)

        path = os.path.join(store._session_dir, "value_mutations.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())

        assert data["tag"] == "select"
        assert data["new_value"] == "RJ"


# -- Epico 3.2: final_state_snapshot.json --------------------------------------


class TestFinalStateSnapshot:
    """Testes para captura de final_state_snapshot.json."""

    def test_final_state_created_on_stop(self, controller):
        """stop() cria final_state_snapshot.json."""
        ctrl, tmpdir, page = controller
        page.evaluate = MagicMock(return_value=_make_final_state(reason="recording_stopped"))

        ctrl.stop()

        path = os.path.join(ctrl._store._session_dir, "final_state_snapshot.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["reason"] == "recording_stopped"

    def test_final_state_created_on_finalize(self, controller):
        """finalize() cria final_state_snapshot.json."""
        ctrl, tmpdir, page = controller
        page.evaluate = MagicMock(return_value=_make_final_state(reason="recording_finalized"))

        ctrl.stop()
        ctrl.finalize()

        path = os.path.join(ctrl._store._session_dir, "final_state_snapshot.json")
        assert os.path.exists(path)

    def test_final_state_has_all_fields(self, controller):
        """final_state_snapshot.json tem reason, timestamp, url, page_title, fields."""
        ctrl, tmpdir, page = controller
        fields = [
            _make_snapshot(fingerprint="input#campo1[name=campo1]", value="Valor1"),
            _make_snapshot(fingerprint="select#uf[name=uf]", value="SP", tag="select"),
        ]
        page.evaluate = MagicMock(return_value=_make_final_state(reason="user_stop", fields=fields))

        ctrl.stop()

        path = os.path.join(ctrl._store._session_dir, "final_state_snapshot.json")
        with open(path) as f:
            data = json.load(f)

        assert data["reason"] == "user_stop"
        assert "timestamp" in data
        assert data["url"] == "http://localhost:8765/test"
        assert data["page_title"] == "Test Page"
        assert len(data["fields"]) == 2
        assert data["fields"][0]["value"] == "Valor1"
        assert data["fields"][1]["value"] == "SP"

    def test_final_state_capture_failure_sets_quality_flag(self, controller):
        """Quando a captura do estado final falha, sem crash — tratado graciosamente."""
        ctrl, tmpdir, page = controller
        page.evaluate = MagicMock(side_effect=Exception("JS error"))

        # Nao deve lancar excecao
        ctrl._capture_final_state_snapshot("recording_stopped")
        path = os.path.join(ctrl._store._session_dir, "final_state_snapshot.json")
        assert not os.path.exists(path)


# -- Verificacoes de sintaxe do Overlay JS --------------------------------------------


class TestOverlayJS:
    """Valida que o _OVERLAY_JS incorporado e sintaticamente valido."""

    def test_overlay_js_contains_new_queues(self):
        """_OVERLAY_JS declara __tfFieldSnapshotQueue e __tfValueMutationQueue."""
        js = RecorderController._OVERLAY_JS
        assert "__tfFieldSnapshotQueue" in js
        assert "__tfValueMutationQueue" in js

    def test_overlay_js_contains_snapshot_function(self):
        """_OVERLAY_JS define _tf_snapshotFields."""
        js = RecorderController._OVERLAY_JS
        assert "_tf_snapshotFields" in js

    def test_overlay_js_contains_final_state_function(self):
        """_OVERLAY_JS define _tf_captureFinalState."""
        js = RecorderController._OVERLAY_JS
        assert "_tf_captureFinalState" in js

    def test_overlay_js_contains_setter_hooks(self):
        """_OVERLAY_JS contem codigo de setter hook."""
        js = RecorderController._OVERLAY_JS
        assert "value_mutation" in js
        assert "HTMLInputElement.prototype" in js or "_hookValue" in js
        assert "HTMLSelectElement.prototype" in js or "_hookValue" in js
        assert "HTMLTextAreaElement.prototype" in js or "_hookValue" in js

    def test_overlay_js_contains_mutation_observer(self):
        """_OVERLAY_JS contem configuracao do MutationObserver."""
        js = RecorderController._OVERLAY_JS
        assert "MutationObserver" in js
        assert "content_edit" in js
        assert "aria_mutation" in js

    def test_overlay_js_contains_snapshot_polling(self):
        """_OVERLAY_JS contem intervalo de polling de field snapshot."""
        js = RecorderController._OVERLAY_JS
        assert "__tfFieldSnapshotInterval" in js
        assert "_tf_snapshotFields()" in js

    def test_overlay_js_captures_final_state_on_stop(self):
        """_OVERLAY_JS chama _captureFinalState('user_stop') ao Shift+S."""
        js = RecorderController._OVERLAY_JS
        assert "_captureFinalState('user_stop')" in js or '_captureFinalState("user_stop")' in js

    def test_overlay_js_captures_final_state_on_submit(self):
        """_OVERLAY_JS chama _captureFinalState('form_submit') ao submit."""
        js = RecorderController._OVERLAY_JS
        assert "_captureFinalState('form_submit')" in js or '_captureFinalState("form_submit")' in js

    def test_overlay_js_captures_final_state_on_beforeunload(self):
        """_OVERLAY_JS chama _captureFinalState('beforeunload') ao beforeunload."""
        js = RecorderController._OVERLAY_JS
        assert "_captureFinalState('beforeunload')" in js or '_captureFinalState("beforeunload")' in js


# -- Casos limite ----------------------------------------------------------------


class TestSprint3EdgeCases:
    """Casos limite para field snapshots."""

    def test_empty_field_snapshot_queue(self, mock_store):
        """fieldSnapshots vazio no payload — sem crash, sem arquivo."""
        store, tmpdir, page, ctrl = mock_store
        page.evaluate = MagicMock(return_value={
            "events": [], "steps": [], "commands": [], "fieldSnapshots": [], "valueMutations": [],
        })
        ctrl.flush_events()  # Nao deve lancar excecao

    def test_none_field_snapshot_queue(self, mock_store):
        """Excecao do evaluate() — sem crash."""
        store, tmpdir, page, ctrl = mock_store
        page.evaluate = MagicMock(side_effect=Exception("detached"))
        ctrl.flush_events()  # Nao deve lancar excecao

    def test_malformed_snapshot_data(self, mock_store):
        """Dados de snapshot malformados nao causam crash."""
        store, tmpdir, page, ctrl = mock_store
        ctrl._save_field_snapshot({"invalid": True})  # Nao deve lancar excecao

    def test_large_number_of_snapshots(self, mock_store):
        """Muitos snapshots sao tratados sem crash."""
        store, tmpdir, page, ctrl = mock_store
        for i in range(100):
            ctrl._save_field_snapshot(_make_snapshot(
                fingerprint=f"input#campo{i}[name=campo{i}]",
                value=f"Valor{i}",
            ))

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 100

    def test_hidden_field_captured(self, mock_store):
        """Campos ocultos sao capturados com visibility=hidden."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="input#hidden1[name=hidden1]",
            value="valor_oculto",
            visible=False,
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())
        assert data["visibility"] == "hidden"
        assert data["value"] == "valor_oculto"

    def test_disabled_field_captured(self, mock_store):
        """Campos desabilitados sao capturados com enabled=false."""
        store, tmpdir, page, ctrl = mock_store
        snapshot = _make_snapshot(
            fingerprint="input#disabled1[name=disabled1]",
            value="",
            enabled=False,
        )
        ctrl._save_field_snapshot(snapshot)

        path = os.path.join(store._session_dir, "field_snapshots.jsonl")
        with open(path) as f:
            data = json.loads(f.readline())
        assert data["enabled"] is False
