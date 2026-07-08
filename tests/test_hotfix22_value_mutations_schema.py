"""Hotfix 22: contrato escritor/leitor value_mutations.jsonl + element_id.

O JS do overlay (_hookValue em overlay_inject.js) e o metodo
_ir_value_mutations do normalizer tinham esquemas diferentes — o escritor
gravava `{type, timestamp, fingerprint, value}`, o leitor esperava
`new_value`, `tag`, `id`, `name`, `old_value`. O leitor retornava
silenciosamente uma lista vazia, entao todo campo mascarado que o gravador
havia capturado com sucesso acabava no prompt --complete como
`typing_not_captured`.

A mesma classe de bug produziu uma segunda incompatibilidade: _extractTarget
emite `element_id` enquanto o construtor de SemanticTarget do normalizer
procurava por `id`. Ambas as correcoes fixam o contrato escritor/leitor.
"""
from __future__ import annotations

import json
from testforge.semantic.recording_normalizer import RecordingNormalizer


def _write_mutations(tmp_path, mutations):
    path = tmp_path / "value_mutations.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for m in mutations:
            f.write(json.dumps(m) + "\n")


def test_value_mutations_reader_uses_value_key(tmp_path):
    """O leitor deve consumir a chave `value` — nao `new_value`."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": " 1.000,00 "},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "1.000,00"
    # Fingerprint analisado corretamente
    ids = entries[0]["identifiers"]
    assert ids["id"] == "mat-input-1"
    assert ids["tag"] == "input"


def test_value_mutations_keeps_last_value_per_fingerprint(tmp_path):
    """Mascaras emitem valores parciais durante a digitacao; apenas o ultimo e
    o valor final pretendido pelo usuario."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "100,00"},
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:01Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:02Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "10.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "10.000,00"


def test_value_mutations_empty_values_are_skipped(tmp_path):
    """Estado inicial vazio (focus, blur) nao deve produzir entradas."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-1[name=]", "value": ""},
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "1.000,00"


def test_value_mutations_correlates_by_element_id(tmp_path):
    """Quando target.element_id do passo corresponde ao id do fingerprint
    da mutacao, o aria_label / placeholder daquele passo se torna a chave
    canonica da entrada. E assim que um fingerprint `mat_input_1` e
    renomeado para `prestacao_desejada_*` para que o resolver em tempo de
    execucao possa encontra-lo."""
    from testforge.semantic.model import SemanticAction, SemanticTarget

    target = SemanticTarget(
        accessible_name="Prestação desejada *",
        placeholder="R$0,00",
        element_id="mat-input-1",
        tag="input",
    )
    step = SemanticAction(action="click", target=target)

    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [step])
    assert len(entries) == 1
    assert entries[0]["field_key"] == "prestação_desejada_*"
    assert entries[0]["value"] == "1.000,00"


def test_value_mutations_correlates_via_selector_chain(tmp_path):
    """Quando element_id nao esta no target mas aparece em um seletor
    candidato, a correlacao ainda encontra o passo correto."""
    from testforge.semantic.model import (
        SemanticAction, SemanticTarget, LocatorCandidate,
    )

    target = SemanticTarget(
        accessible_name="Renda mensal *",
        placeholder="R$0,00",
        element_id="",
        candidates=[LocatorCandidate(
            strategy="css", score=1.0,
            selector="form > mat-form-field > input#mat-input-3.mat-mdc-input-element",
        )],
    )
    step = SemanticAction(action="click", target=target)

    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-3[name=]", "value": "2.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [step])
    assert len(entries) == 1
    assert entries[0]["field_key"] == "renda_mensal_*"


def test_build_target_reads_element_id_from_overlay_schema():
    """O JS do overlay escreve element_id; o construtor de SemanticTarget
    costumava procurar por `id`. Ambas as chaves devem popular element_id."""
    n = RecordingNormalizer()
    target_data = {
        "tag": "input",
        "accessible_name": "Prestação desejada *",
        "placeholder": "R$0,00",
        "element_id": "mat-input-1",   # chave estilo overlay
        "css_path": "input#mat-input-1",
    }
    target = n._build_target(target_data)
    assert target.element_id == "mat-input-1"


def test_build_target_falls_back_to_id_key():
    """Retrocompatibilidade: eventos legados com `id` ainda populam element_id."""
    n = RecordingNormalizer()
    target = n._build_target({
        "tag": "input",
        "id": "legacy-id-format",
        "css_path": "input#legacy-id-format",
    })
    assert target.element_id == "legacy-id-format"
