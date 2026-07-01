"""Hotfix 22: `_remove_snapshot_duplicates` key precisa incluir accessible_name
+ placeholder para nao colidir campos Material currencymask com id/name vazios.

Regressao: em Angular Material a maioria dos inputs currencymask nao tem `id`
ou `name` HTML (apenas `formControlName` que nao aparece em raw target). Antes
do fix, a key de dedup era `(id, name, value)`, entao Prestação=1.000,00
anulava Renda=1.000,00 quando ambas usavam id="" name="". Resultado: normalizer
descartava o burst final da segunda field, o compiler emitia fill com valor
intermediario, o calculador produzia resultado diferente do gravado, e todos
os asserts textuais falhavam.

Este teste locka a key nova: (id, name, placeholder, accessible_name, value).
Campos com mesmo id/name mas accessible_name diferente NAO colidem.
"""
from __future__ import annotations

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _fill_event(event_id: str, ts: str, value: str, accessible_name: str,
                placeholder: str = "R$0,00"):
    """Build a fill raw event as the recorder overlay would emit it, with
    id/name blank (Material currencymask pattern)."""
    return {
        "event_id": event_id,
        "type": "fill",
        "timestamp": ts,
        "value": value,
        "target": {
            "tag": "input",
            "id": "",
            "name": "",
            "placeholder": placeholder,
            "accessible_name": accessible_name,
        },
    }


def test_material_currencymask_fields_do_not_collide_in_dedup():
    """Prestação=1.000,00 seguido de Renda=1.000,00 deve manter AMBOS os
    eventos — ate o hotfix 22 o segundo era removido como duplicado."""
    n = RecordingNormalizer()
    events = [
        _fill_event("evt_01", "2026-07-01T13:00:00Z", " 1.000,00 ", "Prestação desejada *"),
        _fill_event("evt_02", "2026-07-01T13:01:00Z", " 1.000,00 ", "Renda mensal *"),
        _fill_event("evt_03", "2026-07-01T13:02:00Z", " 1.000,00 ", "Valor do imóvel *"),
    ]
    result = n._remove_snapshot_duplicates(events)
    ids = [e["event_id"] for e in result]
    assert ids == ["evt_01", "evt_02", "evt_03"], (
        f"campos diferentes com mesmo valor foram indevidamente colapsados: {ids}"
    )


def test_true_duplicate_same_field_same_value_still_deduped():
    """Repetido do MESMO campo com mesmo valor (spam de snapshot periodico
    DOM) ainda deve colapsar — a intencao original do dedup."""
    n = RecordingNormalizer()
    events = [
        _fill_event("evt_01", "2026-07-01T13:00:00Z", " 1.000,00 ", "Prestação desejada *"),
        _fill_event("evt_02", "2026-07-01T13:00:01Z", " 1.000,00 ", "Prestação desejada *"),
        _fill_event("evt_03", "2026-07-01T13:00:02Z", " 1.000,00 ", "Prestação desejada *"),
    ]
    result = n._remove_snapshot_duplicates(events)
    ids = [e["event_id"] for e in result]
    assert ids == ["evt_01"], (
        f"true duplicates should collapse to first, got: {ids}"
    )


def test_same_field_different_values_preserved():
    """Rajada de digitacao (0,01 -> 10 -> 100 -> 1.000,00) no mesmo campo
    deve preservar todos os valores no dedup — compaction posterior colapsa."""
    n = RecordingNormalizer()
    events = [
        _fill_event(f"evt_0{i}", f"2026-07-01T13:00:0{i}Z", val, "Prestação desejada *")
        for i, val in enumerate([" 0,01 ", " 10,00 ", " 100,00 ", " 1.000,00 "], start=1)
    ]
    result = n._remove_snapshot_duplicates(events)
    assert len(result) == 4, (
        f"burst com valores diferentes nao deve deduplicar: {len(result)} eventos preservados"
    )


def test_field_with_id_still_uses_id_component():
    """Campos com id explicito continuam sendo distinguidos pelo id — a
    inclusao de accessible_name nao regride o comportamento antigo."""
    n = RecordingNormalizer()
    # Same placeholder + accessible_name mas ids DIFERENTES → nao colide
    events = [
        {
            "event_id": "evt_01",
            "type": "fill",
            "value": "foo",
            "target": {"id": "field_a", "name": "", "placeholder": "", "accessible_name": ""},
        },
        {
            "event_id": "evt_02",
            "type": "fill",
            "value": "foo",
            "target": {"id": "field_b", "name": "", "placeholder": "", "accessible_name": ""},
        },
    ]
    result = n._remove_snapshot_duplicates(events)
    assert [e["event_id"] for e in result] == ["evt_01", "evt_02"]
