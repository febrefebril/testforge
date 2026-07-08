"""H21 — prompt de valor inline como nova fonte primaria.

Quando o overlay detecta teclas pressionadas seguidas de input vazio no blur,
ele pergunta ao usuario inline ("mascara interceptou — digite o valor"). O
valor digitado vai para raw_events.jsonl como `inline_field_value` e o
normalizer o apresenta como `user_supplied_inline` — a maior prioridade de
fonte unica abaixo de form_values.

Este arquivo fixa:
1. user_supplied_inline supera fill_event / setter_hook / final_state.
2. O normalizer analisa o evento bruto em uma entrada FieldValueMap com
   a fonte, valor e formato de identificador corretos.
3. user_supplied_inline vence setter_hook no mesmo campo.
4. Valores vazios sao descartados.
"""
from __future__ import annotations

import json
from pathlib import Path

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _write_raw_events(tmp_path: Path, events: list[dict]) -> Path:
    rec = tmp_path / "rec"
    rec.mkdir()
    with open(rec / "raw_events.jsonl", "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return rec


def _inline(label: str, value: str, ts: str = "2026-06-27T22:00:00Z") -> dict:
    fp = f"input#mat-input-1[name=]"
    return {
        "type": "inline_field_value",
        "timestamp": ts,
        "fingerprint": fp,
        "label": label,
        "placeholder": "0,00",
        "aria_label": label,
        "element_id": "mat-input-1",
        "name": "",
        "tag": "input",
        "value": value,
        "source": "user_supplied_inline",
    }


class TestPriorityRanking:
    def test_user_supplied_inline_above_fill_event(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["user_supplied_inline"] > p["fill_event"]
        assert p["user_supplied_inline"] > p["final_state"]
        assert p["user_supplied_inline"] > p["setter_hook"]

    def test_form_values_still_top(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["form_values"] > p["user_supplied_inline"]

    def test_no_priority_collision(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert len(set(p.values())) == len(p)


class TestNormalizerReadsInlineEvents:
    def test_inline_event_surfaces_as_user_supplied_inline(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", "2500"),
        ])
        n = RecordingNormalizer()
        entries = n._ir_inline_field_values(str(rec), [])
        assert len(entries) == 1
        e = entries[0]
        assert e["source"] == "user_supplied_inline"
        assert e["value"] == "2500"
        # Chave canonica e construida a partir do rotulo, nao do fingerprint.
        assert "mat-input" not in e["field_key"]
        assert "renda" in e["field_key"].lower()
        # Identificadores preservados para o resolver downstream.
        assert e["identifiers"]["label"] == "Renda mensal *"
        assert e["identifiers"]["id"] == "mat-input-1"

    def test_empty_value_is_dropped(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", ""),
            _inline("Valor do imóvel *", "1000000"),
        ])
        n = RecordingNormalizer()
        entries = n._ir_inline_field_values(str(rec), [])
        labels = [e["identifiers"]["label"] for e in entries]
        assert "Renda mensal *" not in labels
        assert "Valor do imóvel *" in labels

    def test_inline_beats_setter_hook_on_same_field(self, tmp_path):
        """Quando ambas as fontes disparam para o mesmo campo mascarado, o
        valor digitado pelo usuario deve vencer a deduplicacao."""
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", "2500"),
            # Tambem uma value_mutation (setter_hook) que a mascara
            # produziu — geralmente um valor parcial / incorreto.
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T22:00:01Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "25,00",  # mascara produziu isto; usuario queria 2500
            },
        ])
        n = RecordingNormalizer()
        # Executa o pipeline IR completo para que a dedup rode.
        entries = n._ir_all(str(rec), [])
        # A entrada mesclada para o campo renda deve ser o valor do usuario.
        target = next(
            (e for e in entries if "renda" in e["field_key"].lower()),
            None,
        )
        assert target is not None
        assert target["source"] == "user_supplied_inline"
        assert target["value"] == "2500"


class TestSchemaBumped:
    def test_capture_schema_v4(self):
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 4, (
            "H21 adicionou o tipo de evento bruto inline_field_value. Aumente "
            "CAPTURE_SCHEMA_VERSION quando a forma do evento mudar."
        )
