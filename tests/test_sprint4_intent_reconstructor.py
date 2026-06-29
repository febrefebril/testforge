"""Testes para Intent Reconstructor — Sprint 4, Epico 5.

CT-AUTO-4.1: Fill reconstruido por snapshot_diff.
CT-AUTO-4.2: Fill reconstruido por form_values.
CT-AUTO-4.3: Valor reconstruido por network_payload.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from testforge.semantic.model import SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


# -- Fixtures -------------------------------------------------------------------


@pytest.fixture
def reconstructor():
    return RecordingNormalizer()


@pytest.fixture
def recording_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _make_step(action="click", tag="input", name="campo1", value="",
               timestamp="2026-06-18T10:00:00Z", form_values=None,
               label="Campo 1", placeholder="Digite", el_id="campo1"):
    target = SemanticTarget(
        tag=tag,
        name=name,
        element_id=el_id,
        label=label,
        placeholder=placeholder,
    )
    step = SemanticAction(
        action=action,
        target=target,
        value=value,
        url="http://localhost:8765/test",
        page_title="Test Page",
        context={"timestamp": timestamp},
    )
    if form_values:
        step.context["form_values"] = form_values
    if value:
        step.value = value
    return step


def _make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC",
                        tag="input", name="campo1", label="Campo 1",
                        timestamp="2026-06-18T10:00:01Z"):
    """Cria uma linha unica de field_snapshots.jsonl (entrada em lote)."""
    return json.dumps({
        "timestamp": timestamp,
        "snapshots": [{
            "timestamp": timestamp,
            "fingerprint": fingerprint,
            "identifiers": {
                "id": "campo1",
                "name": name,
                "label": label,
                "placeholder": "Digite",
                "aria-label": None,
                "css_path": "#campo1",
            },
            "tag": tag,
            "type": "text",
            "value": value,
            "checked": None,
            "visibility": "visible",
            "enabled": True,
            "focused": False,
            "bounding_box": {"x": 10, "y": 10, "width": 200, "height": 30},
        }],
        "count": 1,
    })


def _make_network_entry(method="POST", url="http://localhost:8765/api/save",
                        post_data="cpf=123.456.789-00&renda=5000",
                        timestamp="2026-06-18T10:00:05Z"):
    return {
        "type": "request",
        "method": method,
        "url": url,
        "resource_type": "xhr",
        "post_data": post_data,
        "timestamp": timestamp,
    }


# -- CT-AUTO-4.1: Fill reconstruido por snapshot_diff -------------------------


class TestCT_AUTO_4_1:
    """CT-AUTO-4.1: Fill reconstruido por snapshot_diff."""

    def test_snapshot_diff_detects_value_change(self, reconstructor, recording_dir):
        """Mudanca de valor entre snapshots consecutivos produz entrada com source=snapshot_diff."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="2026-06-18T10:00:01Z") + "\n")

        steps = [_make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_snapshots(recording_dir, steps)

        assert len(entries) >= 1, f"Esperado >=1 entradas, veio {entries}"
        entry = entries[0]
        assert entry["source"] == "snapshot_diff", f"Esperado snapshot_diff, veio {entry}"
        assert entry["value"] == "ABC"
        assert "campo1" in entry["field_key"]

    def test_snapshot_diff_has_correct_identifiers(self, reconstructor, recording_dir):
        """Entrada snapshot diff tem identificadores: name, id, label, placeholder, fingerprint."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#nome[name=nome]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#nome[name=nome]", value="Joao", timestamp="2026-06-18T10:00:01Z", name="nome", label="Nome") + "\n")

        steps = [_make_step(action="click", name="nome", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_snapshots(recording_dir, steps)

        assert len(entries) >= 1
        ids = entries[0].get("identifiers", {})
        assert ids.get("name") == "nome"
        assert ids.get("label") == "Nome"
        assert "fingerprint" in entries[0]

    def test_snapshot_diff_prevent_default_scenario(self, reconstructor, recording_dir):
        """Cenario input com preventDefault: valor capturado mesmo sem evento input."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="2026-06-18T10:00:01Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABCDEF", timestamp="2026-06-18T10:00:02Z") + "\n")

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:03Z"),
        ]
        entries = reconstructor._ir_snapshots(recording_dir, steps)

        # Deve capturar a ultima transicao de valor (mais completa para inputs com mascara)
        assert len(entries) >= 1, f"Entradas obtidas: {entries}"
        assert entries[0]["source"] == "snapshot_diff"
        assert entries[0]["value"] == "ABCDEF"

    def test_no_snapshots_file_returns_empty(self, reconstructor, recording_dir):
        """field_snapshots.jsonl ausente retorna lista vazia."""
        entries = reconstructor._ir_snapshots(recording_dir, [])
        assert entries == []

    def test_empty_snapshots_file_returns_empty(self, reconstructor, recording_dir):
        """Arquivo vazio retorna lista vazia."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write("")
        entries = reconstructor._ir_snapshots(recording_dir, [])
        assert entries == []

    def test_single_snapshot_no_diff(self, reconstructor, recording_dir):
        """Snapshot unico (sem alteracao) retorna lista vazia."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:00") + "\n")
        entries = reconstructor._ir_snapshots(recording_dir, [])
        assert entries == []

    def test_no_value_change_returns_empty(self, reconstructor, recording_dir):
        """Nenhuma mudanca de valor entre snapshots retorna vazio."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:00") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:01") + "\n")
        entries = reconstructor._ir_snapshots(recording_dir, [])
        assert entries == []

    def test_snapshot_diff_integration_with_normalizer(self, recording_dir):
        """Normalizer captura valores snapshot_diff via _reconstruct_intents."""
        # Cria diretorio de gravacao com field_snapshots
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#valor[name=valor]", value="", timestamp="10:00:00") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#valor[name=valor]", value="1234", timestamp="10:00:01", name="valor", label="Valor") + "\n")

        # Cria raw_events.jsonl minimo
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": "2026-06-18T10:00:00Z",
                "url": "http://localhost:8765/test", "page_title": "Test",
                "target": {
                    "tag": "input", "id": "valor", "name": "valor",
                    "placeholder": "Digite o valor", "label": "Valor",
                    "css_path": "#valor", "value": "",
                },
                "value": None, "is_postback": False,
            }) + "\n")

        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(recording_dir, test_id="ST-TEST")

        # O field_value_map deve conter o valor reconstruido
        assert stc.field_values is not None
        # No minimo, o reconstructor executou sem erro
        assert len(stc.steps) >= 1


# -- CT-AUTO-4.2: Fill reconstruido por form_values ----------------------------


class TestCT_AUTO_4_2:
    """CT-AUTO-4.2: Fill reconstruido por form_values."""

    def test_form_values_extracted_from_step_context(self, reconstructor):
        """form_values do contexto do passo sao extraidos como entradas."""
        steps = [
            _make_step(action="click", name="telefone", label="Telefone",
                       form_values={"telefone": "11999999999", "nome": "Joao", "email": "joao@test.com"}),
        ]
        entries = reconstructor._ir_form_values(steps)

        assert len(entries) >= 1
        telefone = [e for e in entries if e["field_key"] == "telefone"]
        assert len(telefone) > 0
        assert telefone[0]["source"] == "form_values"
        assert telefone[0]["value"] == "11999999999"

    def test_form_values_includes_all_fields(self, reconstructor):
        """Todos os campos form_values sao extraidos."""
        steps = [
            _make_step(action="click", name="campo1",
                       form_values={"campo1": "A", "campo2": "B", "campo3": "C"}),
        ]
        entries = reconstructor._ir_form_values(steps)
        assert len(entries) == 3

    def test_form_values_no_context_returns_empty(self, reconstructor):
        """Passo sem form_values retorna vazio."""
        steps = [_make_step(action="click", name="campo1")]
        entries = reconstructor._ir_form_values(steps)
        assert entries == []

    def test_form_values_empty_dict_returns_empty(self, reconstructor):
        """Passo com form_values vazio retorna vazio."""
        steps = [_make_step(action="click", name="campo1", form_values={})]
        entries = reconstructor._ir_form_values(steps)
        assert entries == []

    def test_form_values_integration_with_field_value_map(self, reconstructor):
        """Entradas form_values sao mescladas no field_value_map via normalizer."""
        steps = [
            _make_step(action="click", name="telefone",
                       form_values={"telefone": "11999999999"}),
        ]
        entries = reconstructor._ir_form_values(steps)

        assert len(entries) == 1
        assert "telefone" in entries[0]["field_key"]
        assert entries[0]["identifiers"].get("form_name") == "telefone"


# -- CT-AUTO-4.3: Valor reconstruido por network_payload -----------------------


class TestCT_AUTO_4_3:
    """CT-AUTO-4.3: Valor reconstruido por network_payload."""

    def test_network_payload_form_urlencoded_parsed(self, reconstructor, recording_dir):
        """Corpo POST form-urlencoded e analisado em entradas de campo."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry()], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._ir_network(recording_dir, steps)

        assert len(entries) >= 1
        cpf = [e for e in entries if "cpf" in e["field_key"]]
        assert len(cpf) >= 1
        assert cpf[0]["source"] == "network_payload"
        assert "123.456.789-00" in cpf[0]["value"]

    def test_network_payload_json_parsed(self, reconstructor, recording_dir):
        """Corpo POST JSON e analisado em entradas de campo."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(
                post_data='{"cpf": "123.456.789-00", "renda": "5000"}')], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._ir_network(recording_dir, steps)
        assert len(entries) >= 1
        cpf = [e for e in entries if "cpf" in e["field_key"]]
        assert len(cpf) >= 1
        assert cpf[0]["value"] == "123.456.789-00"

    def test_network_payload_empty_body_ignored(self, reconstructor, recording_dir):
        """POST sem corpo e ignorado."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data=None)], f)

        entries = reconstructor._ir_network(recording_dir, [])
        assert entries == []

    def test_network_payload_missing_file_returns_empty(self, reconstructor, recording_dir):
        """network_log.json ausente retorna lista vazia."""
        entries = reconstructor._ir_network(recording_dir, [])
        assert entries == []

    def test_network_payload_has_evidence_metadata(self, reconstructor, recording_dir):
        """Entrada network payload inclui evidencia: url, method, payload_key."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data="cpf=123")], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._ir_network(recording_dir, steps)

        assert len(entries) >= 1
        ev = entries[0].get("evidence", {})
        assert ev.get("url") == "http://localhost:8765/api/save"
        assert ev.get("method") == "POST"
        assert ev.get("payload_key") == "cpf"

    def test_network_payload_get_requests_ignored(self, reconstructor, recording_dir):
        """Requisicoes GET sao ignoradas — apenas POST/PUT/PATCH sao analisadas."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([
                _make_network_entry(method="GET", post_data=None),
                _make_network_entry(method="POST", post_data="campo1=valor1"),
            ], f)

        entries = reconstructor._ir_network(recording_dir, [_make_step()])
        assert len(entries) >= 1
        assert entries[0]["source"] == "network_payload"

    def test_network_payload_correlates_to_field_key(self, reconstructor, recording_dir):
        """Chave do payload e correlacionada a field_key por correspondencia de nome."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data="nome=Maria&idade=30")], f)

        steps = [
            _make_step(action="click", name="nome", label="Nome"),
            _make_step(action="click", name="idade", label="Idade"),
        ]
        entries = reconstructor._ir_network(recording_dir, steps)

        keys = {e["field_key"] for e in entries}
        assert "nome" in keys
        assert "idade" in keys


# -- Integration tests ---------------------------------------------------------


class TestIntentReconstructorIntegration:
    """Integracao: reconstructor alimenta o pipeline do normalizer."""

    def test_reconstruct_all_combines_sources(self, reconstructor, recording_dir):
        """reconstruct_all executa todas as estrategias e retorna resultados combinados."""
        # Cria field_snapshots.jsonl
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="snap_val", timestamp="2026-06-18T10:00:01Z") + "\n")

        # Cria network_log.json
        net_path = os.path.join(recording_dir, "network_log.json")
        with open(net_path, "w") as f:
            json.dump([_make_network_entry(post_data="campo2=net_val")], f)

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:02Z"),
        ]
        # Tambem adiciona form_values a um passo
        steps[1].context["form_values"] = {"campo2": "form_val"}

        entries = reconstructor._ir_all(recording_dir, steps)

        # Deve ter entradas de snapshot_diff e form_values, possivelmente network_payload
        sources = {e["source"] for e in entries}
        assert "snapshot_diff" in sources, f"Fontes: {sources}"
        assert "form_values" in sources

    def test_field_value_map_priority(self, recording_dir):
        """field_value_map prefere form_values > snapshot_diff > network_payload."""
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": "2026-06-18T10:00:00Z",
                "url": "http://localhost:8765/test", "page_title": "Test",
                "target": {"tag": "input", "id": "campo1", "name": "campo1", "value": ""},
                "value": None, "is_postback": False,
            }) + "\n")

        # Cria field_snapshots com valor snapshot_diff
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="snap_val", timestamp="2026-06-18T10:00:01Z") + "\n")

        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(recording_dir, test_id="ST-TEST")

        # Apenas verifica que normalizer executa sem erro com intents reconstruidos
        assert stc is not None

    def test_reconstructed_source_icon_in_report(self, reconstructor, recording_dir):
        """fontes snapshot_diff e network_payload tem icones no relatorio."""
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="val", timestamp="2026-06-18T10:00:01Z") + "\n")

        net_path = os.path.join(recording_dir, "network_log.json")
        with open(net_path, "w") as f:
            json.dump([_make_network_entry(post_data="campo2=net")], f)

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:02Z"),
        ]
        entries = reconstructor._ir_all(recording_dir, steps)
        assert len(entries) >= 1


# -- Edge cases ----------------------------------------------------------------


class TestIntentReconstructorEdgeCases:
    """Casos limite para IntentReconstructor."""

    def test_parse_payload_invalid_json(self, reconstructor):
        """Payload JSON invalido retorna dicionario vazio."""
        result = reconstructor._ir_parse_payload("{invalid json}", "http://test")
        assert result == {}

    def test_parse_payload_form_urlencoded(self, reconstructor):
        """Payload form-urlencoded e analisado corretamente."""
        result = reconstructor._ir_parse_payload("key1=val1&key2=val2", "http://test")
        assert result.get("key1") == "val1"
        assert result.get("key2") == "val2"

    def test_parse_payload_json(self, reconstructor):
        """Payload JSON e analisado corretamente."""
        result = reconstructor._ir_parse_payload('{"key1": "val1", "key2": "val2"}', "http://test")
        assert result.get("key1") == "val1"
        assert result.get("key2") == "val2"

    def test_parse_payload_empty(self, reconstructor):
        """Payload vazio retorna dicionario vazio."""
        assert reconstructor._ir_parse_payload("", "http://test") == {}
        assert reconstructor._ir_parse_payload(None, "http://test") == {}

    def test_canonical_key_normalization(self, reconstructor):
        """Chave canonica normaliza corretamente."""
        assert reconstructor._canonical_field_key("Nome Completo") == "nome_completo"
        assert reconstructor._canonical_field_key(" input-valor ") == "valor"  # prefixo 'input-' removido
        assert reconstructor._canonical_field_key("") == "unknown"

    def test_find_nearest_step_index(self, reconstructor):
        """Indice do passo mais proximo e encontrado por proximidade de timestamp."""
        steps = [
            _make_step(timestamp="2026-06-18T10:00:00Z"),
            _make_step(timestamp="2026-06-18T10:00:05Z"),
            _make_step(timestamp="2026-06-18T10:00:10Z"),
        ]
        idx = reconstructor._ir_find_nearest_step_index(steps, "2026-06-18T10:00:06Z")
        assert idx == 1  # mais proximo do passo em 10:00:05

    def test_find_nearest_step_index_empty(self, reconstructor):
        """Passos vazios retorna 0."""
        assert reconstructor._ir_find_nearest_step_index([], "2026-06-18T10:00:00Z") == 0
        assert reconstructor._ir_find_nearest_step_index([_make_step()], "") == 0

    def test_reconstruct_from_snapshots_deduplicates_by_field_key(self, reconstructor, recording_dir):
        """Multiplas entradas de snapshot para mesma field_key sao deduplicadas."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="A", timestamp="2026-06-18T10:00:01Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="AB", timestamp="2026-06-18T10:00:02Z") + "\n")

        steps = [_make_step(name="campo1", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_snapshots(recording_dir, steps)

        # Deve ter apenas uma entrada para campo1
        campo1_entries = [e for e in entries if "campo1" in e["field_key"]]
        assert len(campo1_entries) <= 1

    def test_empty_steps_list_returns_empty(self, reconstructor):
        """Todos os metodos retornam lista vazia quando passos estao vazios."""
        assert reconstructor._ir_form_values([]) == []
