"""H22a — reordenacao de prioridade de fonte apos spike currencymask Material.

Contexto: veja .planning/spikes/SPIKE-keyboard-type-mask.md (secao H22)
e a entrada H22 de 2026-06-27 em .planning/DECISIONS-LOG.md.

O spike mostrou que `value_mutations.jsonl` (fonte=`setter_hook`) apenas
captura escritas dirigidas por mascara que delegam ao setter `value` do
prototipo. Para sobrescritas de instancia estilo ng2-currency-mask (e para
digitacao real via teclado em inputs simples) o hook nao captura nada.
`final_state_snapshot` le `el.value` via o getter canonico da instancia,
entao sobrevive a todo padrao de mascara que exibe um valor na tela.

Decisao: promover `final_state` acima de `setter_hook` na tabela de prioridade.

Este arquivo fixa:
1. A nova ordenacao (para que uma refatoracao futura nao a reverta silenciosamente).
2. O comportamento de mesclagem quando ambas as fontes tem valor para o mesmo
   campo fisico — `final_state` deve vencer.
3. O invariante de fonte-unica-de-verdade (apenas `IR_SOURCE_PRIORITY`
   deve conduzir a prioridade).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
)


# ---- 1. Invariante de ordenacao -------------------------------------------------


class TestIR_SOURCE_PRIORITY_ranking:
    def test_final_state_above_setter_hook(self):
        """H22a: final_state deve superar setter_hook porque setter_hook
        perde os modos de falha de sobrescrita de instancia e digitacao simples."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["final_state"] > p["setter_hook"], (
            "final_state deve superar setter_hook (H22a). O setter hook "
            "e estruturalmente insuficiente para mascaras que nao delegam "
            "ao setter do prototipo. Veja SPIKE-keyboard-type-mask.md."
        )

    def test_form_values_remains_top(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        for other in ("fill_event", "final_state", "setter_hook",
                      "snapshot_diff", "network_payload",
                      "polling", "missing_fill"):
            assert p["form_values"] > p[other], (
                f"form_values deve superar {other}; e a unica fonte "
                "que reflete o que o navegador realmente submeteu."
            )

    def test_fill_event_above_final_state(self):
        """fill_event representa uma acao de usuario explicita capturada no
        momento certo; final_state e um instantaneo de fim de sessao. fill_event
        ainda deve vencer quando presente."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["fill_event"] > p["final_state"]

    def test_missing_fill_remains_bottom(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        for other in [k for k in p if k != "missing_fill"]:
            assert p["missing_fill"] < p[other], (
                f"missing_fill deve ficar abaixo de {other} para que qualquer fonte real "
                "possa substituir um placeholder."
            )

    def test_no_collisions(self):
        """Fontes distintas devem ter numeros de prioridade distintos —
        empates em `_ir_dedupe_entries` recorrem a comparacao de comprimento
        de valor, o que e fragil."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert len(set(p.values())) == len(p), (
            "Valores de prioridade duplicados em IR_SOURCE_PRIORITY: " + repr(p)
        )


# ---- 2. Comportamento de mesclagem (integracao) --------------------------------------


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


class TestFinalStateBeatsSetterHookOnMerge:
    """Fixa comportamento H22a: quando ambas as fontes disparam para o mesmo
    campo fisico, o valor de final_state deve ser o armazenado em field_values."""

    def test_final_state_wins_when_both_sources_present(self, tmp_path):
        # value_mutations.jsonl — fonte setter_hook
        _write_jsonl(tmp_path / "value_mutations.jsonl", [
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T10:00:00Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "1,00",  # instantaneo obsoleto de meio de digitacao
            },
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T10:00:01Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "10,00",  # tambem obsoleto; mascara ficou reformatando
            },
        ])
        # final_state_snapshot.json — fonte final_state, verdade absoluta
        _write_json(tmp_path / "final_state_snapshot.json", {
            "reason": "session_end",
            "timestamp": "2026-06-27T10:05:00Z",
            "url": "https://example.test/calc",
            "page_title": "Calc",
            "fields": [
                {
                    "fingerprint": "input#mat-input-1[name=]",
                    "identifiers": {
                        "id": "mat-input-1",
                        "name": None,
                        "label": "Valor do imóvel *",
                        "placeholder": "0,00",
                        "aria-label": None,
                    },
                    "tag": "input",
                    "type": "text",
                    "value": "10.000,00",  # canonical formatted value
                    "checked": None,
                    "visibility": "visible",
                    "enabled": True,
                },
            ],
        })

        target = SemanticTarget(
            accessible_name="Valor do imóvel *",
            placeholder="0,00",
            element_id="mat-input-1",
            tag="input",
            candidates=[LocatorCandidate(
                strategy="css", score=1.0,
                selector="input#mat-input-1",
            )],
        )
        step = SemanticAction(action="click", target=target)

        n = RecordingNormalizer()
        entries = n._ir_all(str(tmp_path), [step])
        # Encontra a entrada que aponta para nosso input mascarado.
        candidates = [
            e for e in entries
            if e.get("identifiers", {}).get("id") == "mat-input-1"
            or "mat-input-1" in e.get("fingerprint", "")
            or "valor" in e.get("field_key", "").lower()
        ]
        assert candidates, (
            f"_ir_all descartou ambas as fontes para o input mascarado. Obteve: {entries}"
        )

        # Apos dedup, o vencedor para este campo fisico deve ser final_state.
        winner = n._ir_dedupe_entries(candidates)
        assert len(winner) >= 1
        chosen = winner[0]
        assert chosen["source"] == "final_state", (
            f"setter_hook ({chosen.get('value')!r}) venceu final_state — "
            f"regressao H22a. Vencedor: {chosen}"
        )
        assert chosen["value"] == "10.000,00", (
            f"Valor incorreto selecionado: {chosen.get('value')!r}"
        )


# ---- 3. Invariante de fonte-unica-de-verdade -----------------------------------


class TestNoInlinePriorityMaps:
    """Fixa: nenhuma copia inline do mapa de prioridade deve sobreviver em
    recording_normalizer.py. H22a os unificou em `IR_SOURCE_PRIORITY`.

    Um PR futuro que copie a tabela inline (um padrao comum de
    refatoracao-sem-pensar) refaria silenciosamente os rankings. Este
    invariante detecta isso em tempo de CI.
    """

    def test_no_competing_priority_dicts_in_normalizer(self):
        src = Path(
            "src/testforge/semantic/recording_normalizer.py"
        ).read_text(encoding="utf-8")
        # O literal `"form_values": 100` pareado com `"setter_hook":`
        # no MESMO bloco e a assinatura de copia inline que removemos.
        # Permite exatamente uma ocorrencia (a constante IR_SOURCE_PRIORITY).
        marker = '"form_values": 100'
        count = src.count(marker)
        assert count == 1, (
            f"Esperava exatamente 1 ocorrencia de {marker!r} (a constante "
            f"IR_SOURCE_PRIORITY). Encontrada {count}. Uma nova copia "
            "inline do mapa de prioridade foi adicionada — incorpore-a em "
            "RecordingNormalizer.IR_SOURCE_PRIORITY em vez disso."
        )
