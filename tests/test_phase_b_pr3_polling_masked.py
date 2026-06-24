"""Testes para PR 3 da Fase B — Polling Strategy + Masked Field Detection.

Story 2.1: _reconstruct_from_polling() — source=polling, score=50
Story 2.2: _detect_masked_field() — is_masked flag em value_mutations
"""

import json
import os
import tempfile

import pytest

from testforge.semantic.model import SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


# -- Fixtures ------------------------------------------------------------------


@pytest.fixture
def reconstructor():
    return RecordingNormalizer()


@pytest.fixture
def recording_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _make_step(action="click", tag="input", name="campo1", value="",
               timestamp="2026-06-18T10:00:00Z", label="Campo 1",
               placeholder="Digite", el_id="campo1"):
    target = SemanticTarget(
        tag=tag,
        name=name,
        element_id=el_id,
        label=label,
        placeholder=placeholder,
    )
    return SemanticAction(
        action=action,
        target=target,
        value=value,
        url="http://localhost:8765/test",
        page_title="Test Page",
        context={"timestamp": timestamp},
    )


def _make_polling_snapshot_line(fingerprint="input#valor[name=valor]", value="10.000,00",
                                 name="valor", label="Valor", interval_ms=500,
                                 timestamp="2026-06-18T10:00:01Z"):
    """Cria linha JSONL de field_snapshots com source=polling."""
    return json.dumps({
        "timestamp": timestamp,
        "source": "polling",
        "interval_ms": interval_ms,
        "snapshots": [{
            "timestamp": timestamp,
            "fingerprint": fingerprint,
            "source": "polling",
            "interval_ms": interval_ms,
            "identifiers": {
                "id": name,
                "name": name,
                "label": label,
                "placeholder": "Digite",
                "aria-label": None,
                "css_path": f"#{name}",
            },
            "tag": "input",
            "type": "text",
            "value": value,
            "checked": None,
            "visibility": "visible",
            "enabled": True,
        }],
        "count": 1,
    })


def _make_mutation_line(fingerprint="input#valor[name=valor]", name="valor",
                        new_value="10.000,00", old_value="10000",
                        timestamp="2026-06-18T10:00:01Z"):
    """Cria linha JSONL de value_mutations com valor mascarado."""
    return json.dumps({
        "type": "value_mutation",
        "timestamp": timestamp,
        "fingerprint": fingerprint,
        "tag": "input",
        "id": name,
        "name": name,
        "new_value": new_value,
        "old_value": old_value,
    })


# -- Story 2.1: Polling Strategy -----------------------------------------------


class TestPollingStrategy:
    """CT-PR3-2.1: Entradas de polling em field_snapshots.jsonl."""

    def test_polling_entries_create_field_values(self, reconstructor, recording_dir):
        """Entradas com source=polling produzem field_values com score=50."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_polling_snapshot_line(
                fingerprint="input#valor[name=valor]",
                value="10.000,00",
                name="valor",
                label="Valor do Empréstimo",
                timestamp="2026-06-18T10:00:01Z",
            ) + "\n")

        steps = [_make_step(name="valor", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_polling(recording_dir, steps)

        assert len(entries) >= 1, f"Esperava >=1 entrada, obteve: {entries}"
        entry = entries[0]
        assert entry["source"] == "polling", f"source esperado 'polling', obteve: {entry['source']}"
        assert entry["value"] == "10.000,00"

    def test_polling_source_score_is_50(self, reconstructor):
        """Score/prioridade de 'polling' é 50 (menor que snapshot_diff=70)."""
        assert RecordingNormalizer.IR_SOURCE_PRIORITY["polling"] == 50
        assert RecordingNormalizer.IR_SOURCE_PRIORITY["polling"] < RecordingNormalizer.IR_SOURCE_PRIORITY["snapshot_diff"]
        assert RecordingNormalizer.IR_SOURCE_PRIORITY["polling"] < RecordingNormalizer.IR_SOURCE_PRIORITY["final_state"]

    def test_polling_via_interval_ms(self, reconstructor, recording_dir):
        """Entradas com interval_ms>0 (sem source=polling) também são capturadas."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        entry = {
            "timestamp": "2026-06-18T10:00:01Z",
            "interval_ms": 300,
            "snapshots": [{
                "timestamp": "2026-06-18T10:00:01Z",
                "fingerprint": "input#cpf[name=cpf]",
                "interval_ms": 300,
                "identifiers": {
                    "id": "cpf", "name": "cpf", "label": "CPF",
                    "placeholder": "", "aria-label": None, "css_path": "#cpf",
                },
                "tag": "input",
                "type": "text",
                "value": "123.456.789-00",
                "checked": None,
            }],
            "count": 1,
        }
        with open(path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        steps = [_make_step(name="cpf", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_polling(recording_dir, steps)

        assert len(entries) >= 1
        assert entries[0]["source"] == "polling"
        assert entries[0]["value"] == "123.456.789-00"

    def test_polling_missing_file_returns_empty(self, reconstructor, recording_dir):
        """Sem field_snapshots.jsonl retorna lista vazia."""
        entries = reconstructor._ir_polling(recording_dir, [])
        assert entries == []

    def test_polling_empty_file_returns_empty(self, reconstructor, recording_dir):
        """Arquivo vazio retorna lista vazia."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write("")
        entries = reconstructor._ir_polling(recording_dir, [])
        assert entries == []

    def test_polling_no_polling_entries_returns_empty(self, reconstructor, recording_dir):
        """Snapshots sem source=polling e sem interval_ms não geram entradas polling."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        entry = {
            "timestamp": "2026-06-18T10:00:01Z",
            "snapshots": [{
                "timestamp": "2026-06-18T10:00:01Z",
                "fingerprint": "input#campo1[name=campo1]",
                "identifiers": {"id": "campo1", "name": "campo1", "label": "Campo"},
                "tag": "input",
                "type": "text",
                "value": "abc",
                "checked": None,
            }],
        }
        with open(path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        entries = reconstructor._ir_polling(recording_dir, [])
        assert entries == []

    def test_polling_entry_has_correct_identifiers(self, reconstructor, recording_dir):
        """Entrada de polling tem identifiers corretos (name, id, label, fingerprint)."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_polling_snapshot_line(
                fingerprint="input#renda[name=renda]",
                value="5.000,00",
                name="renda",
                label="Renda Mensal",
            ) + "\n")

        entries = reconstructor._ir_polling(recording_dir, [])

        assert len(entries) >= 1
        ids = entries[0]["identifiers"]
        assert ids["name"] == "renda"
        assert ids["label"] == "Renda Mensal"
        assert "fingerprint" in ids

    def test_polling_integrated_in_reconstruct_all(self, reconstructor, recording_dir):
        """reconstruct_all inclui entradas de polling."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_polling_snapshot_line(
                fingerprint="input#prazo[name=prazo]",
                value="24",
                name="prazo",
                label="Prazo",
            ) + "\n")

        steps = [_make_step(name="prazo")]
        entries = reconstructor._ir_all(recording_dir, steps)

        sources = {e["source"] for e in entries}
        assert "polling" in sources, f"Polling não encontrado nas fontes: {sources}"

    def test_polling_deduped_by_priority(self, reconstructor, recording_dir):
        """Polling (score=50) perde para snapshot_diff (score=70) no mesmo campo."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        # Adiciona snapshot normal (sem polling)
        normal_entry = {
            "timestamp": "2026-06-18T10:00:00Z",
            "snapshots": [{
                "timestamp": "2026-06-18T10:00:00Z",
                "fingerprint": "input#valor[name=valor]",
                "identifiers": {"id": "valor", "name": "valor", "label": "Valor"},
                "tag": "input", "type": "text",
                "value": "",
                "checked": None,
            }],
        }
        snap_entry = {
            "timestamp": "2026-06-18T10:00:01Z",
            "snapshots": [{
                "timestamp": "2026-06-18T10:00:01Z",
                "fingerprint": "input#valor[name=valor]",
                "identifiers": {"id": "valor", "name": "valor", "label": "Valor"},
                "tag": "input", "type": "text",
                "value": "snap_value",
                "checked": None,
            }],
        }
        polling_entry = json.loads(_make_polling_snapshot_line(
            fingerprint="input#valor[name=valor]",
            value="polling_value",
            name="valor",
        ))

        with open(path, "w") as f:
            f.write(json.dumps(normal_entry) + "\n")
            f.write(json.dumps(snap_entry) + "\n")
            f.write(json.dumps(polling_entry) + "\n")

        steps = [_make_step(name="valor")]
        entries = reconstructor._ir_all(recording_dir, steps)

        valor_entries = [e for e in entries if "valor" in e["field_key"]]
        assert len(valor_entries) == 1
        # snapshot_diff deve ganhar (score=70 > polling=50)
        assert valor_entries[0]["source"] == "snapshot_diff"


# -- Story 2.2: Masked Field Detection -----------------------------------------


class TestMaskedFieldDetection:
    """CT-PR3-2.2: Detecção de campos mascarados via _detect_masked_field()."""

    def test_masked_field_currency_detected(self, reconstructor):
        """'10.000,00' com padrão de moeda brasileira é detectado como mascarado."""
        assert reconstructor._ir_detect_masked_field("10.000,00") is True

    def test_masked_field_cpf_detected(self, reconstructor):
        """CPF mascarado '123.456.789-00' é detectado como mascarado."""
        assert reconstructor._ir_detect_masked_field("123.456.789-00") is True

    def test_masked_field_cnpj_detected(self, reconstructor):
        """CNPJ '12.345.678/0001-99' é detectado como mascarado."""
        assert reconstructor._ir_detect_masked_field("12.345.678/0001-99") is True

    def test_masked_field_telefone_detected(self, reconstructor):
        """Telefone '11 99999-9999' é detectado como mascarado."""
        assert reconstructor._ir_detect_masked_field("11 99999-9999") is True

    def test_masked_field_data_detected(self, reconstructor):
        """Data '01/06/2026' é detectada como mascarada."""
        assert reconstructor._ir_detect_masked_field("01/06/2026") is True

    def test_masked_field_plain_text_not_masked(self, reconstructor):
        """Texto simples sem separadores não é mascarado."""
        assert reconstructor._ir_detect_masked_field("João Silva") is False
        assert reconstructor._ir_detect_masked_field("abc") is False

    def test_masked_field_plain_number_not_masked(self, reconstructor):
        """Número sem separadores não é mascarado."""
        assert reconstructor._ir_detect_masked_field("10000") is False
        assert reconstructor._ir_detect_masked_field("123") is False

    def test_masked_field_empty_not_masked(self, reconstructor):
        """Valor vazio retorna False."""
        assert reconstructor._ir_detect_masked_field("") is False

    def test_masked_field_raw_value_different(self, reconstructor):
        """Se raw_value difere do value mascarado, retorna True."""
        assert reconstructor._ir_detect_masked_field("10.000,00", raw_value="10000") is True

    def test_masked_field_raw_value_same_as_value(self, reconstructor):
        """Se raw_value igual ao value com separadores simples, depende do padrão."""
        # Mesmo valor = sem transformação de máscara
        # "1.5" não é padrão de moeda BR nem CPF, mas tem separador
        # O resultado depende se bate num known_mask — não deve bater
        result = reconstructor._ir_detect_masked_field("1.5", raw_value="1.5")
        # Não bate em nenhum KNOWN_MASK → False
        assert result is False

    def test_value_mutations_has_is_masked_flag(self, reconstructor, recording_dir):
        """value_mutations.jsonl com campo mascarado gera entrada com is_masked=True."""
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(path, "w") as f:
            f.write(_make_mutation_line(
                fingerprint="input#valor[name=valor]",
                name="valor",
                new_value="10.000,00",
                old_value="10000",
            ) + "\n")

        steps = [_make_step(name="valor")]
        entries = reconstructor._ir_value_mutations(recording_dir, steps)

        assert len(entries) >= 1, f"Esperava >=1 entrada, obteve: {entries}"
        entry = entries[0]
        assert entry.get("is_masked") is True, (
            f"Esperava is_masked=True, obteve: {entry.get('is_masked')}"
        )

    def test_value_mutations_plain_value_not_masked(self, reconstructor, recording_dir):
        """value_mutations com texto simples gera is_masked=False."""
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(path, "w") as f:
            f.write(_make_mutation_line(
                fingerprint="input#nome[name=nome]",
                name="nome",
                new_value="Maria",
                old_value="",
            ) + "\n")

        steps = [_make_step(name="nome")]
        entries = reconstructor._ir_value_mutations(recording_dir, steps)

        assert len(entries) >= 1
        entry = entries[0]
        assert entry.get("is_masked") is False

    def test_is_masked_propagated_to_identifiers(self, reconstructor, recording_dir):
        """Flag is_masked também aparece em identifiers para uso pelo Compiler."""
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(path, "w") as f:
            f.write(_make_mutation_line(
                fingerprint="input#cpf[name=cpf]",
                name="cpf",
                new_value="123.456.789-00",
                old_value="12345678900",
            ) + "\n")

        steps = [_make_step(name="cpf")]
        entries = reconstructor._ir_value_mutations(recording_dir, steps)

        assert len(entries) >= 1
        ids = entries[0]["identifiers"]
        assert ids.get("is_masked") is True
