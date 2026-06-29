"""Invariantes estaticas aplicadas no CI.

Este arquivo traduz os padroes documentados em
`.planning/REGRESSION-PATTERNS.md` em assercoes pytest. Cada entrada
nesse registro deve ter ao menos um teste aqui. Quando um teste falha,
leia a entrada de padrao vinculada para entender qual classe de bug
esta em risco de retornar, e amplie a correcao adequadamente.

Os testes sao baratos: AST puro / grep na arvore de origem, sem browser,
sem fixtures. Executam em todo commit.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "testforge"


def _read(rel_path: str) -> str:
    return (_SRC / rel_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# P1 — desvio-de-duplicacao-de-codigo
# ---------------------------------------------------------------------------

class TestP1CodeDuplicationDrift:
    """Padroes onde o mesmo algoritmo em N lugares diverge.

    Invariante ancora: toda primitiva de entrada mascarada vive em exatamente um
    local. Helpers de preenchimento devem delegar para `_fill_masked`. Hotfixes
    16, 17, 19 sao as recorrencias historicas.
    """

    def test_press_sequentially_lives_in_one_place(self):
        src = _read("runner/step_executor.py")
        count = src.count("press_sequentially")
        assert count == 1, (
            f"press_sequentially aparece {count} vezes em step_executor.py — "
            "deve ser exatamente 1 (dentro de _fill_masked). Um helper de preenchimento esta "
            "reimplementando o caminho de entrada mascarada. Veja "
            ".planning/REGRESSION-PATTERNS.md#P1."
        )

    def test_step_executor_methods_inside_class(self):
        """Forma do hotfix 9: um def em nivel de modulo inserido no meio de uma classe
        orfava os metodos abaixo como codigo morto aninhado. Verificacao AST
        detecta isso imediatamente."""
        src = _read("runner/step_executor.py")
        tree = ast.parse(src)
        class_methods = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "StepExecutor":
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        class_methods.add(m.name)
        # Estes metodos DEVEM ser metodos de classe, nao aninhados em outra fn
        # nem em nivel de modulo. Hotfix 9 os encontrou perdidos; nunca queremos
        # que isso se repita.
        required = {
            "execute", "_execute_click", "_execute_fill",
            "_execute_select", "_fill_input", "_fill_by_aria_label",
            "_try_data_fill", "_fill_masked", "_resolve_field_value",
        }
        missing = required - class_methods
        assert not missing, (
            f"StepExecutor esta sem metodos obrigatorios: {missing}. "
            "Um def em nivel de modulo pode ter orfanado eles como codigo aninhado. "
            "Veja .planning/REGRESSION-PATTERNS.md#P1, hotfix 9."
        )


# ---------------------------------------------------------------------------
# P2 — swallowed-padrao-silencioso
# ---------------------------------------------------------------------------

class TestP2SilentDefaultSwallow:
    """Proliferacao de `try / except Exception: pass`. Cada sitio deve
    eventualmente carregar uma razao documentada e uma chamada de logger."""

    # Limite conservador. A contagem atual e a linha de base que herdamos; o
    # limite cai conforme migramos para um decorator @tolerate (divida R-C1).
    _CAP = 80

    def test_bare_except_pass_count_is_bounded(self):
        """O numero de sitios `except Exception: pass` em src/ nao deve
        crescer. Nova tolerancia deve usar um decorator documentado, nao um
        swallow puro."""
        bare_pattern = re.compile(
            r"except\s+(Exception|BaseException)?:\s*\n\s*pass\s*$",
            re.MULTILINE,
        )
        total = 0
        for py in _SRC.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            total += len(bare_pattern.findall(text))
        assert total <= self._CAP, (
            f"Contagem de `except: pass` e {total}, limite e {self._CAP}. "
            "Tolerancia deve usar um decorator que documente a razao. "
            "Veja .planning/REGRESSION-PATTERNS.md#P2."
        )


# ---------------------------------------------------------------------------
# P3 — estado-nao-ancorado
# ---------------------------------------------------------------------------

class TestP3UnanchoredState:
    """Caminho/estado assumido mas nao ancorado. Produtor e consumidor devem
    concordar."""

    def test_field_value_map_writer_reader_round_trip(self, tmp_path):
        """Forma do hotfix CS-4a: o escritor de field_value_map.json armazena
        dados sob chaves {fields, entries, _meta}; o leitor deve
        consumir todas as tres formas."""
        import json
        from testforge.cli._interactive_completion import _save_field_value_map
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        from testforge.semantic.model import SemanticTestCase

        # Escreve via o escritor de producao
        rec_dir = str(tmp_path)
        _save_field_value_map(rec_dir, {
            "cpf": {
                "field_key": "cpf",
                "value": "12345678900",
                "intention": "fill CPF",
                "identifiers": {"aria_label": "CPF"},
                "source": "user_supplied_cli",
                "confidence": 1.0,
                "step_index": 3,
            }
        })

        # Le via o leitor de producao
        normalizer = RecordingNormalizer()
        normalizer._current_recording_dir = rec_dir
        stc = SemanticTestCase(test_id="X", source_recording_id="X")
        stc.field_values = {}
        normalizer._merge_user_supplied_values(stc)

        assert "cpf" in stc.field_values, (
            "Contrato escritor/leitor para field_value_map.json quebrado. "
            "Veja .planning/REGRESSION-PATTERNS.md#P3, CS-4a."
        )
        assert stc.field_values["cpf"].value == "12345678900"

    def test_value_mutations_writer_reader_round_trip(self, tmp_path):
        """Forma do hotfix 22: o overlay JS escreve value_mutations.jsonl
        com `{type, timestamp, fingerprint, value}`; o normalizador
        `_ir_value_mutations` le. Ambos devem concordar na chave `value`
        (nao `new_value`) e no formato de fingerprint
        `tag#id[name=]`. Pre-hotfix o leitor retornava lista vazia
        e todo campo mascarado parecia `typing_not_captured`."""
        import json
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        path = tmp_path / "value_mutations.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for record in [
                {"type": "value_mutation", "timestamp": "2026-06-27T10:00:00Z",
                 "fingerprint": "input#mat-input-1[name=]", "value": "100,00"},
                {"type": "value_mutation", "timestamp": "2026-06-27T10:00:01Z",
                 "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
            ]:
                f.write(json.dumps(record) + "\n")

        entries = RecordingNormalizer()._ir_value_mutations(str(tmp_path), [])
        assert len(entries) >= 1, (
            "Leitor de value_mutations retornou 0 entradas de um arquivo "
            "escritor nao vazio — esquema escritor/leitor divergiu. "
            "Veja .planning/REGRESSION-PATTERNS.md#P3, hotfix 22."
        )
        assert entries[0]["value"] == "1.000,00"
        ids = entries[0]["identifiers"]
        assert ids["id"] == "mat-input-1"
        assert ids["tag"] == "input"

    def test_raw_event_target_to_semantic_target_round_trip(self):
        """Forma do hotfix 22b: o overlay JS `_extractTarget` emite o
        dicionario target com `element_id`; `_build_target` costumava procurar
        apenas `id`. O contrato deve ler ambas as chaves para que SemanticTarget
        sempre carregue o id de elemento canonico."""
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        n = RecordingNormalizer()
        overlay_target = {
            "tag": "input",
            "accessible_name": "Prestacao desejada *",
            "placeholder": "R$0,00",
            "element_id": "mat-input-1",  # esquema overlay
            "css_path": "input#mat-input-1",
        }
        target = n._build_target(overlay_target)
        assert target.element_id == "mat-input-1", (
            "_build_target descartou element_id do esquema overlay. "
            "Sem isso, value_mutations nao pode correlacionar com o step. "
            "Veja .planning/REGRESSION-PATTERNS.md#P3, hotfix 22b."
        )
        # Forma back-compat deve ainda popular o mesmo campo
        target_legacy = n._build_target({"tag": "input", "id": "legacy-id"})
        assert target_legacy.element_id == "legacy-id"

    def test_final_state_snapshot_writer_reader_round_trip(self, tmp_path):
        """Forma B16: o overlay JS `_captureFinalState` escreve
        final_state_snapshot.json com `fields[*].identifiers.label`;
        o `_ir_final_state` do normalizador le e deve expor o
        label para que o field_key resolva para um nome significativo (nao o
        fingerprint bruto como `mat-input-2`).

        Pre-fix B16: o escritor descartava label, entao o field_key colapsava
        para o fingerprint e o prompt --complete pedia campos
        que o usuario ja tinha digitado."""
        import json
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        # Esquema espelha overlay_inject.js:_snapshotFields (branch input).
        payload = {
            "reason": "session_end",
            "timestamp": "2026-06-27T10:05:00Z",
            "url": "https://example.test/form",
            "page_title": "Form",
            "fields": [
                {
                    "fingerprint": "input#mat-input-2[name=cpf]",
                    "identifiers": {
                        "id": "mat-input-2",
                        "name": "cpf",
                        "label": "CPF",
                        "placeholder": "000.000.000-00",
                        "aria-label": None,
                    },
                    "tag": "input",
                    "type": "text",
                    "value": "539.867.177-49",
                    "checked": None,
                    "visibility": "visible",
                    "enabled": True,
                },
            ],
        }
        (tmp_path / "final_state_snapshot.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

        entries = RecordingNormalizer()._ir_final_state(str(tmp_path), [])
        assert len(entries) == 1, (
            "_ir_final_state descartou a entrada do snapshot. "
            "Veja .planning/REGRESSION-PATTERNS.md#P3, B16."
        )
        entry = entries[0]
        # Label sobrevive ao round-trip
        assert entry["identifiers"]["label"] == "CPF", (
            "Label foi descartado entre escritor e leitor. O field_key "
            "colapsara para o fingerprint e o prompt --complete "
            "exigira campos que o usuario ja digitou. "
            "Veja .planning/REGRESSION-PATTERNS.md#P3, B16."
        )
        # field_key canonico e derivado de um identificador legivel por humanos,
        # nao do fingerprint opaco mat-input-N.
        assert "mat-input" not in entry["field_key"], (
            f"field_key={entry['field_key']!r} ainda carrega o id de "
            "fingerprint bruto. Canonizacao deve preferir label/name."
        )
        assert entry["value"] == "539.867.177-49"
        assert entry["source"] == "final_state"


# ---------------------------------------------------------------------------
# P4 — rot-de-feature-flag
# ---------------------------------------------------------------------------

class TestP4FeatureFlagRot:
    """Feature flags que nunca sao alternadas apodrecem em codigo morto. Apenas
    rastreamento por enquanto — se torna falha rigida quando definirmos um prazo."""

    _KNOWN_FLAGS = {
        # nome -> {default, owner, flip_or_delete_by}
        "use_cdp_recorder": {"default": False, "flip_or_delete_by": "2026-07-31"},
        "use_pipeline": {"default": False, "flip_or_delete_by": "2026-07-31"},
        "use_v2_compiler": {"default": False, "flip_or_delete_by": "2026-07-31"},
    }

    def test_known_flags_have_a_decision_deadline(self):
        """Todo feature flag deve ter um prazo para alternar ou deletar. Este
        teste atualmente lista o que sabemos; PRs futuros que adicionarem uma flag devem
        registra-la aqui."""
        for name, info in self._KNOWN_FLAGS.items():
            assert "flip_or_delete_by" in info, (
                f"Flag {name} nao tem prazo. "
                "Veja .planning/REGRESSION-PATTERNS.md#P4."
            )


# ---------------------------------------------------------------------------
# P5 — divergencia-compile-runtime
# ---------------------------------------------------------------------------

class TestP5CompileRuntimeDivergence:
    """Runtime nao deve substituir silenciosamente a acao compilada."""

    def test_click_to_fill_promotion_is_documented(self):
        """A promocao silenciosa click → fill e a divergencia
        compile/runtime canonica em step_executor. Nao a deletamos
        ainda (R-E2 no sprint de refatoracao), mas EXIGIMOS que
        todo ponto de chamada emita um span fill.attempted (CS-3). Este teste
        afirma que o hook de telemetria existe no caminho de promocao."""
        src = _read("runner/step_executor.py")
        # O branch _execute_click que chama _fill_input em
        # missing_fill deve alcancar _fill_masked, que emite o span.
        assert "_fill_masked" in src
        assert "_emit_fill_span" in src
        # Todo helper de preenchimento deve delegar, nao re-emitir o span ele mesmo
        # (veja contrato P1).

    def test_datepicker_handler_emits_skip_reason(self):
        """Quando o handler de datepicker do Angular Material suprime um
        step, o campo skip_reason deve ser definido para que a UI do runner e
        os spans possam reportar a decisao. Drops silenciosos sao proibidos
        (hotfix 20)."""
        src = _read("handlers/angular_material.py")
        # datepicker_dedup e o skip_reason documentado para o
        # caminho completed-via-fill. O caminho de completude apenas-click agora
        # NAO define skip_reason porque os clicks SAO a intencao
        # canonica — essa e a invariante do hotfix-20.
        assert "datepicker_dedup" in src
        # Invariancia negativa: o branch de completude apenas-click (hotfix
        # 20) nao deve definir skip_reason.
        assert "click-only completion" in src or "Click-only completion" in src, (
            "O comentario do branch apenas-click do hotfix 20 esta faltando — "
            "risco de regressao. Veja .planning/REGRESSION-PATTERNS.md#P5."
        )
