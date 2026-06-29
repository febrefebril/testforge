"""Testes do Semantic Intermediate Model e Compiler."""
import json
import os
import tempfile

from testforge.semantic import (
    LocatorCandidate, SemanticAction, SemanticTarget,
    SemanticTestCase, RecordingNormalizer, PlaywrightCompiler,
)
from testforge.semantic.recording_normalizer import _is_generic_text


def _create_raw_events(tmpdir: str):
    """Cria raw_events.jsonl simulado."""
    events = [
        {"event_id": "evt_0001", "type": "navigation", "timestamp": "2026-06-13T00:00:00",
         "url": "http://localhost:8765", "page_title": "Consulta"},
        {"event_id": "evt_0002", "type": "fill", "timestamp": "2026-06-13T00:00:01",
         "url": "http://localhost:8765", "page_title": "Consulta",
         "target": {"tag": "input", "id": "cpfField", "name": "cpf",
                    "placeholder": "000.000.000-00", "label": "CPF",
                    "role": "textbox"},
         "value": "12345678900"},
        {"event_id": "evt_0003", "type": "click", "timestamp": "2026-06-13T00:00:02",
         "url": "http://localhost:8765", "page_title": "Consulta",
         "target": {"tag": "button", "text": "Pesquisar", "id": "btnPesquisar",
                    "role": "button", "accessible_name": "Pesquisar"}},
    ]
    path = os.path.join(tmpdir, "raw_events.jsonl")
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    # steps.jsonl com asserts
    steps = [
        {"action": "assert", "assert_type": "textual",
         "selector": "#resultadoSection", "tagName": "div",
         "text": "CPF consultado: 12345678900",
         "expected_value": "CPF consultado", "assert_state": "",
         "timestamp": "2026-06-13T00:00:03"},
        {"action": "assert", "assert_type": "visivel",
         "selector": "#resultadoSection", "tagName": "div",
         "text": "", "expected_value": "visible", "assert_state": "",
         "timestamp": "2026-06-13T00:00:04"},
    ]
    with open(os.path.join(tmpdir, "steps.jsonl"), "w") as f:
        for s in steps:
            f.write(json.dumps(s) + "\n")


class TestSemanticModel:
    def test_locator_candidate(self):
        c = LocatorCandidate("id", "#btn", 0.95, "unique id")
        assert c.strategy == "id"
        assert c.score == 0.95

    def test_semantic_target(self):
        t = SemanticTarget(role="button", label="Enviar")
        assert t.role == "button"
        assert t.label == "Enviar"

    def test_semantic_test_case_to_dict(self):
        tc = SemanticTestCase(test_id="ST-001", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        step = SemanticAction(action="click", target=SemanticTarget(role="button", label="Pesquisar"))
        step.target.candidates.append(LocatorCandidate("role", "button", 0.95))
        tc.steps.append(step)

        d = tc.to_dict()
        assert d["semantic_test_case"]["metadata"]["test_id"] == "ST-001"
        assert len(d["semantic_test_case"]["steps"]) == 1


class TestRecordingNormalizer:
    def test_normalize_creates_stc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_raw_events(tmpdir)
            normalizer = RecordingNormalizer()
            stc = normalizer.normalize(tmpdir, "ST-TEST", "fake-bank", "http://localhost:8765")

            assert stc.test_id == "ST-TEST"
            assert stc.source_recording_id == os.path.basename(tmpdir)
            assert len(stc.steps) >= 3  # nav + fill + click + 2 asserts = 5

            # Verifica que fill step tem candidatos
            fill_step = None
            for s in stc.steps:
                if s.action == "fill":
                    fill_step = s
                    break
            assert fill_step is not None
            assert fill_step.target is not None
            assert len(fill_step.target.candidates) > 0

            # Verifica candidatos ordenados por score
            scores = [c.score for c in fill_step.target.candidates]
            assert scores == sorted(scores, reverse=True), f"Scores nao ordenados: {scores}"

            # Verifica que click step capturou role
            click_step = next(s for s in stc.steps if s.action == "click")
            assert click_step.target.role == "button"
            assert click_step.target.accessible_name == "Pesquisar"

    def test_asserts_from_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_raw_events(tmpdir)
            normalizer = RecordingNormalizer()
            stc = normalizer.normalize(tmpdir)

            assert_steps = [s for s in stc.steps if s.action == "assert"]
            assert len(assert_steps) >= 2

    def test_compact_fill_events_same_selector(self):
        """Fills sequenciais no mesmo target em ate 500ms: mantem apenas o ultimo evento."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "1"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "input", "id": "cpfField"}, "value": "12"},
            {"event_id": "e3", "type": "fill", "timestamp": "2026-06-13T00:00:00.200",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 1
        assert result[0]["value"] == "123"

    def test_compact_fill_events_keypress_included(self):
        """Eventos keypress tambem sao compactados como fill."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "name"}, "value": "A"},
            {"event_id": "e2", "type": "keypress", "timestamp": "2026-06-13T00:00:00.050",
             "target": {"tag": "input", "id": "name"}, "value": "AB"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 1
        assert result[0]["value"] == "AB"

    def test_compact_fill_events_leave_last_only(self):
        """Multiplos fills rapidos: apenas o ultimo sobrevive."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "field"}, "value": "x"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:00.050",
             "target": {"tag": "input", "id": "field"}, "value": "xy"},
            {"event_id": "e3", "type": "fill", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "input", "id": "field"}, "value": "xyz"},
            {"event_id": "e4", "type": "fill", "timestamp": "2026-06-13T00:00:00.150",
             "target": {"tag": "input", "id": "field"}, "value": "xyzz"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 1
        assert result[0]["value"] == "xyzz"

    def test_compact_fill_events_different_selectors_not_merged(self):
        """Fills em elementos diferentes NAO sao compactados juntos."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "input", "id": "nameField"}, "value": "João"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 2
        assert result[0]["value"] == "123"
        assert result[1]["value"] == "João"

    def test_compact_fill_events_same_placeholder_different_accessible_name(self):
        """Dois campos compartilhando placeholder mas accessible_name diferente NAO devem ser mesclados.

        Regression: campos monetarios como 'Renda' e 'Imovel' usam placeholder
        'R$0,00' sem id/name. Sem accessible_name em _target_key, todos os fills
        colapsam no valor final do ultimo campo, descartando silenciosamente o primeiro.
        """
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-23T00:00:00.000",
             "target": {"tag": "input", "placeholder": "R$0,00",
                        "accessible_name": "Renda mensal *"}, "value": " 0,01 "},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-23T00:00:01.000",
             "target": {"tag": "input", "placeholder": "R$0,00",
                        "accessible_name": "Renda mensal *"}, "value": " 1.000,00 "},
            {"event_id": "e3", "type": "fill", "timestamp": "2026-06-23T00:00:02.000",
             "target": {"tag": "input", "placeholder": "R$0,00",
                        "accessible_name": "Valor do imovel *"}, "value": " 0,01 "},
            {"event_id": "e4", "type": "fill", "timestamp": "2026-06-23T00:00:03.000",
             "target": {"tag": "input", "placeholder": "R$0,00",
                        "accessible_name": "Valor do imovel *"}, "value": " 100.000,00 "},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 2, f"Esperado 2 fills (um por campo), obtido {len(result)}"
        assert result[0]["value"] == " 1.000,00 "
        assert result[1]["value"] == " 100.000,00 "

    def test_compact_fill_events_non_fill_preserved(self):
        """Eventos nao-fill (navigation, click) passam inalterados."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "navigation", "timestamp": "2026-06-13T00:00:00.000"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
            {"event_id": "e3", "type": "click", "timestamp": "2026-06-13T00:00:00.200",
             "target": {"tag": "button", "id": "btn"}},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 3

    def test_compact_fill_events_window_boundary(self):
        """Fills no mesmo elemento são compactados independente do intervalo de tempo.

        A janela de 500ms foi removida — slow typists podem ter gaps maiores.
        O heurístico atual usa mesmo-target, não timestamp.
        """
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:01.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "456"},
        ]
        result = normalizer._compact_fill_events(events)
        # Mesmo target → compactado para o último evento (comportamento atual)
        assert len(result) == 1
        assert result[0]["value"] == "456"

    def test_compact_fill_events_multiple_groups(self):
        """Multiplos grupos de fill em elementos diferentes."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "a"}, "value": "1"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "input", "id": "a"}, "value": "12"},
            {"event_id": "e3", "type": "fill", "timestamp": "2026-06-13T00:00:00.200",
             "target": {"tag": "input", "id": "b"}, "value": "x"},
            {"event_id": "e4", "type": "fill", "timestamp": "2026-06-13T00:00:00.300",
             "target": {"tag": "input", "id": "b"}, "value": "xy"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 2
        assert result[0]["value"] == "12"
        assert result[1]["value"] == "xy"

    def test_compact_fill_events_click_resets_group(self):
        """Um click entre fills no mesmo target reseta o grupo."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
            {"event_id": "e2", "type": "click", "timestamp": "2026-06-13T00:00:00.100",
             "target": {"tag": "button", "id": "btn"}},
            {"event_id": "e3", "type": "fill", "timestamp": "2026-06-13T00:00:00.200",
             "target": {"tag": "input", "id": "cpfField"}, "value": "456"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 3
        fill_values = [e["value"] for e in result if e["type"] == "fill"]
        assert fill_values == ["123", "456"]

    def test_compact_fill_events_empty_list(self):
        """Lista vazia retorna lista vazia."""
        normalizer = RecordingNormalizer()
        result = normalizer._compact_fill_events([])
        assert result == []

    def test_compact_fill_events_no_targets(self):
        """Eventos sem targets sao tratados."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "value": "something"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 1
        assert result[0]["value"] == "something"


class TestGenericTextDetection:
    """Testes para _is_generic_text — penaliza rotulos UI genericos e fragieis."""

    def test_generic_portuguese_ok(self):
        assert _is_generic_text("OK") is True
        assert _is_generic_text("ok") is True
        assert _is_generic_text("Ok") is True

    def test_generic_portuguese_cancelar(self):
        assert _is_generic_text("Cancelar") is True
        assert _is_generic_text("cancelar") is True

    def test_generic_portuguese_selecione(self):
        assert _is_generic_text("Selecione") is True
        assert _is_generic_text("SELECIONE") is True

    def test_generic_portuguese_pagina_inicial(self):
        assert _is_generic_text("Página inicial") is True
        assert _is_generic_text("pagina inicial") is True

    def test_generic_portuguese_calcular(self):
        # "Calcular" não está no conjunto genérico — é específico o suficiente
        assert _is_generic_text("Calcular") is False
        assert _is_generic_text("calcular") is False

    def test_generic_english_labels(self):
        assert _is_generic_text("Cancel") is True
        assert _is_generic_text("Select") is True
        assert _is_generic_text("Submit") is True
        assert _is_generic_text("Home") is True

    def test_empty_and_whitespace(self):
        assert _is_generic_text("") is True
        assert _is_generic_text("   ") is True
        assert _is_generic_text(None) is True  # type: ignore

    def test_single_char(self):
        assert _is_generic_text("x") is True
        assert _is_generic_text("1") is True

    def test_digits_only(self):
        assert _is_generic_text("12345") is True

    def test_non_generic_text(self):
        assert _is_generic_text("Pesquisar CPF") is False
        assert _is_generic_text("Nome completo do cliente") is False
        assert _is_generic_text("123.456.789-00") is False
        assert _is_generic_text("btnSubmitForm") is False

    def test_build_target_penalizes_generic_text(self):
        """Candidatos text-based com texto generico recebem score 0.10."""
        normalizer = RecordingNormalizer()
        target_data = {
            "tag": "button",
            "text": "OK",
        }
        target = normalizer._build_target(target_data)
        text_candidate = next(
            (c for c in target.candidates if c.strategy == "text"), None
        )
        assert text_candidate is not None
        assert text_candidate.score == 0.10, (
            f"Esperado 0.10 para texto generico, obtido {text_candidate.score}"
        )

    def test_build_target_normal_text_unchanged(self):
        """Texto nao-generico mantem score normal 0.55."""
        normalizer = RecordingNormalizer()
        target_data = {
            "tag": "button",
            "text": "Pesquisar CPF",
        }
        target = normalizer._build_target(target_data)
        text_candidate = next(
            (c for c in target.candidates if c.strategy == "text"), None
        )
        assert text_candidate is not None
        assert text_candidate.score == 0.55, (
            f"Esperado 0.55 para texto nao-generico, obtido {text_candidate.score}"
        )


class TestSkipReason:
    """Testes para deteccao de motivo de skip em RecordingNormalizer."""

    def _make_events_with_duplicates(self, tmpdir: str) -> str:
        """Cria raw_events.jsonl com steps de click duplicados."""
        events = [
            {"event_id": "e1", "type": "navigation", "timestamp": "2026-06-13T00:00:00",
             "url": "http://localhost:8765", "page_title": "Test"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:01",
             "url": "http://localhost:8765", "page_title": "Test",
             "target": {"tag": "input", "id": "field", "placeholder": "Digite...",
                        "role": "textbox"},
             "value": "123"},
            {"event_id": "e3", "type": "click", "timestamp": "2026-06-13T00:00:02",
             "url": "http://localhost:8765", "page_title": "Test",
             "target": {"tag": "button", "text": "Pesquisar", "id": "btn",
                        "role": "button", "accessible_name": "Pesquisar"}},
            # Click duplicado no mesmo botao
            {"event_id": "e4", "type": "click", "timestamp": "2026-06-13T00:00:03",
             "url": "http://localhost:8765", "page_title": "Test",
             "target": {"tag": "button", "text": "Pesquisar", "id": "btn",
                        "role": "button", "accessible_name": "Pesquisar"}},
        ]
        path = os.path.join(tmpdir, "raw_events.jsonl")
        with open(path, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        return path

    def test_detect_duplicate_clicks(self):
        """Steps de click identicos consecutivos sao marcados como duplicata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_events_with_duplicates(tmpdir)
            normalizer = RecordingNormalizer()
            stc = normalizer.normalize(tmpdir, "ST-DUP", "test", "http://localhost:8765")

            # Deve ter 4 steps: nav, fill, click, click
            assert len(stc.steps) == 4

            # Primeiro click — sem skip_reason
            click_steps = [s for s in stc.steps if s.action == "click"]
            assert len(click_steps) == 2
            assert click_steps[0].skip_reason == ""
            # Segundo click — duplicata
            assert "duplicate" in click_steps[1].skip_reason
            assert "Step" in click_steps[1].skip_reason

    def test_navigation_not_duplicate_of_click(self):
        """Tipos de acao diferentes nunca sao duplicatas."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="click",
                           target=SemanticTarget(role="button", text="OK",
                                                 candidates=[LocatorCandidate("text", "text=OK", 0.55)])),
            SemanticAction(action="navigation", url="http://localhost"),
        ]
        normalizer._deduplicate_steps(steps)
        assert steps[0].skip_reason == ""
        assert steps[1].skip_reason == ""

    def test_different_values_not_duplicate(self):
        """Mesmo target mas valores diferentes nao sao duplicatas."""
        normalizer = RecordingNormalizer()
        target = SemanticTarget(role="textbox", placeholder="CPF",
                                candidates=[LocatorCandidate("placeholder", "[placeholder='CPF']", 0.85)])
        steps = [
            SemanticAction(action="fill", target=target, value="123"),
            SemanticAction(action="fill", target=target, value="456"),
        ]
        normalizer._deduplicate_steps(steps)
        assert steps[0].skip_reason == ""
        assert steps[1].skip_reason == ""

    def test_non_consecutive_not_duplicate(self):
        """Mesmos steps separados por um step diferente nao sao duplicatas."""
        normalizer = RecordingNormalizer()
        target = SemanticTarget(role="button", text="OK",
                                candidates=[LocatorCandidate("text", "text=OK", 0.55)])
        steps = [
            SemanticAction(action="click", target=target),
            SemanticAction(action="fill", target=SemanticTarget(placeholder="x",
                                candidates=[LocatorCandidate("placeholder", "[placeholder='x']", 0.85)]),
                           value="data"),
            SemanticAction(action="click", target=target),  # igual ao primeiro mas nao consecutivo
        ]
        normalizer._deduplicate_steps(steps)
        assert steps[0].skip_reason == ""
        assert steps[1].skip_reason == ""
        assert steps[2].skip_reason == ""  # nao consecutivo, nao marcado

    def test_already_skipped_not_rechecked(self):
        """Steps ja marcados com skip_reason nao sao reavaliados."""
        normalizer = RecordingNormalizer()
        target = SemanticTarget(role="button", text="OK",
                                candidates=[LocatorCandidate("text", "text=OK", 0.55)])
        steps = [
            SemanticAction(action="click", target=target, skip_reason="non-actionable target"),
            SemanticAction(action="click", target=target),  # identical to first
        ]
        normalizer._deduplicate_steps(steps)
        # Primeiro ja tem skip_reason, entao segundo nao e comparado contra ele
        assert "non-actionable target" in steps[0].skip_reason
        assert steps[1].skip_reason == ""

    def test_non_actionable_target_no_candidates(self):
        """Step com target mas zero candidatos recebe 'non-actionable target'."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="click",
                           target=SemanticTarget(role="button", text="Invisible",
                                                 candidates=[])),
            SemanticAction(action="fill",
                           target=SemanticTarget(tag="input", placeholder="...",
                                                 candidates=[]),
                           value="test"),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == "non-actionable target"
        assert steps[1].skip_reason == "non-actionable target"

    def test_assert_not_flagged_non_actionable(self):
        """Steps de assert nunca sao marcados como non-actionable."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="assert",
                           target=SemanticTarget(text="some text", candidates=[]),
                           value="expected"),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == ""

    def test_actionable_with_candidates_not_flagged(self):
        """Step com candidatos nao e marcado."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="click",
                           target=SemanticTarget(role="button",
                                                 candidates=[LocatorCandidate("role", "role=button", 0.90)])),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == ""

    def test_navigation_not_flagged_non_actionable(self):
        """Steps de navegacao (sem target necessario) nao sao marcados."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="navigation", url="http://localhost"),
            SemanticAction(action="click", target=None),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == ""
        assert steps[1].skip_reason == ""


class TestCompiler:
    def test_compile_generates_file(self):
        tc = SemanticTestCase(test_id="ST-001", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")

        # Navigation
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765"))

        # Fill step
        fill_target = SemanticTarget(role="textbox", label="CPF", placeholder="000.000.000-00", element_id="cpfField")
        fill_target.candidates = [
            LocatorCandidate("label", "label:has-text(\"CPF\") + input", 0.90),
            LocatorCandidate("placeholder", "[placeholder=\"000.000.000-00\"]", 0.85),
            LocatorCandidate("id", "#cpfField", 0.75),
        ]
        tc.steps.append(SemanticAction(action="fill", target=fill_target, value="12345678900"))

        # Click step
        click_target = SemanticTarget(role="button", accessible_name="Pesquisar", text="Pesquisar", element_id="btnPesquisar")
        click_target.candidates = [
            LocatorCandidate("role", "role=button[name=\"Pesquisar\"]", 0.95),
            LocatorCandidate("id", "#btnPesquisar", 0.75),
        ]
        tc.steps.append(SemanticAction(action="click", target=click_target))

        # Assert textual
        tc.steps.append(SemanticAction(action="assert", target=SemanticTarget(text="CPF consultado"), value="CPF consultado"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            assert os.path.exists(path)

            with open(path) as f:
                code = f.read()

            # Verifica elementos chave
            assert "from playwright.sync_api import Page, expect" in code
            assert "def test_st_001" in code
            assert "page.goto(BASE_URL)" in code
            # Verifica apenas um page.goto (navegacao inicial; navegacoes redundantes puladas)
            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Esperado exatamente 1 page.goto(), obtido {code.count('page.goto(BASE_URL)')}"
            )
            # Fill com fallback loop
            assert "for _sel in _sels" in code
            assert "page.fill(_sel" in code
            assert "break" in code
            assert "continue" in code
            # Click com fallback loop
            assert "page.click(_sel)" in code
            # Assert
            assert "to_contain_text" in code
            assert "CPF consultado" in code

    def test_compile_assert_visivel(self):
        tc = SemanticTestCase(test_id="ST-VIS", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="assert", target=SemanticTarget(text="resultado"), value="visible", context={"assert_type": "visivel"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "to_be_visible" in code

    def test_compile_assert_estado(self):
        tc = SemanticTestCase(test_id="ST-EST", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="assert", target=SemanticTarget(text="checkbox"), value="checked", context={"assert_type": "estado", "assert_state": "checked"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "to_be_checked" in code

    def test_compile_submit_click_uses_expect_navigation(self):
        """Clicks de submit usam expect_navigation em vez de wait_for_load_state."""
        tc = SemanticTestCase(test_id="ST-SUB", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # Navigation (pulado — goto inicial emitido incondicionalmente)
        tc.steps.append(SemanticAction(action="navigation"))
        # Submit click com contexto is_submit
        click_target = SemanticTarget(role="button", text="Pesquisar", element_id="btnPesquisar")
        click_target.candidates = [
            LocatorCandidate("role", "role=button[name=\"Pesquisar\"]", 0.95),
        ]
        tc.steps.append(SemanticAction(
            action="click", target=click_target,
            context={"is_submit": True},
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            # Deve usar expect_navigation para submit
            assert "expect_navigation" in code
            assert "wait_until='load'" in code
            # Nao deve usar padrao antigo wait_for_load_state
            assert "wait_for_load_state" not in code
            # Apenas um goto (o inicial)
            assert code.count("page.goto(BASE_URL)") == 1

    def test_compile_non_submit_click_no_expect_navigation(self):
        """Clicks regulares (nao submit) NAO usam expect_navigation."""
        tc = SemanticTestCase(test_id="ST-CLK", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        click_target = SemanticTarget(role="button", text="Cancelar")
        click_target.candidates = [
            LocatorCandidate("text", "text=Cancelar", 0.90),
        ]
        tc.steps.append(SemanticAction(
            action="click", target=click_target,
            context={"is_submit": False},
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            # Click regular: sem expect_navigation
            assert "expect_navigation" not in code
            assert "page.click(_sel)" in code
            assert "page.wait_for_timeout(800)" in code  # 800ms para DOM render

    def test_compile_multiple_navigation_skipped(self):
        """Multiplas acoes de navegacao produzem apenas um page.goto()."""
        tc = SemanticTestCase(test_id="ST-MNAV", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # 3 steps de navegacao — apenas o primeiro (inicial) deve produzir goto
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="navigation"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Esperado 1 goto, obtido {code.count('page.goto(BASE_URL)')}"
            )

    def test_compile_navigation_skip_with_different_url(self):
        """Acao de navegacao com URL diferente de base_url ainda e pulada."""
        tc = SemanticTestCase(test_id="ST-NAVURL", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # Navegacao inicial (pagina ja carregada via page.goto)
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765"))
        # Click em link que navega para URL diferente
        click_target = SemanticTarget(role="link", text="Go to Page 2")
        click_target.candidates = [
            LocatorCandidate("text", "text=Go to Page 2", 0.85),
        ]
        tc.steps.append(SemanticAction(action="click", target=click_target))
        # Evento de navegacao capturado apos o click (redundante — ja navegou)
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765/page2"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            # Apenas UM page.goto (navegacao inicial)
            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Esperado 1 goto, obtido {code.count('page.goto(BASE_URL)')}"
            )
            # Acoes de navegacao (inicial e pos-click) sao puladas
            # Sem navegacao explicita para /page2 — o click ja a causa
            assert "page.goto" not in code.replace("page.goto(BASE_URL)", "")
            # Click esta presente
            assert "page.click" in code

    def test_compile_submit_with_postback_url(self):
        """Submit click com postback_url usa expect_navigation."""
        tc = SemanticTestCase(test_id="ST-PBACK", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        click_target = SemanticTarget(role="button", text="Pesquisar", element_id="btnSubmit")
        click_target.candidates = [
            LocatorCandidate("role", "role=button[name=\"Pesquisar\"]", 0.95),
        ]
        tc.steps.append(SemanticAction(
            action="click", target=click_target,
            context={"is_submit": True, "postback_url": "http://localhost:8765/resultado"},
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            # Deve usar expect_navigation para submit
            assert "expect_navigation" in code
            assert "wait_until='load'" in code
            # Apenas um goto
            assert code.count("page.goto(BASE_URL)") == 1
            # Sem goto redundante para URL de postback
            assert "resultado" not in code.lower().replace("page.goto(base_url)", "")


class TestL0_5AccessibilityResolution:
    """Testes para L0.5 get_by_role com correspondencia fuzzy regex de nome."""

    def test_l0_5_role_expr_with_role_and_name(self):
        """_l0_5_role_expr retorna regex get_by_role quando role+nome presentes."""
        compiler = PlaywrightCompiler()
        target = SemanticTarget(role="button", accessible_name="Enviar formulario")
        expr = compiler._l0_5_role_expr(target)
        assert expr is not None
        assert "get_by_role" in expr
        assert "re.compile" in expr
        assert "re.escape" in expr
        assert "re.I" in expr
        assert "Enviar" in expr  # first 40 chars

    def test_l0_5_role_expr_without_role(self):
        """_l0_5_role_expr retorna None quando role ausente."""
        compiler = PlaywrightCompiler()
        target = SemanticTarget(accessible_name="Enviar")
        assert compiler._l0_5_role_expr(target) is None

    def test_l0_5_role_expr_without_name(self):
        """_l0_5_role_expr retorna None quando accessible_name muito curto."""
        compiler = PlaywrightCompiler()
        target = SemanticTarget(role="button")
        assert compiler._l0_5_role_expr(target) is None
        target = SemanticTarget(role="button", accessible_name="A")
        assert compiler._l0_5_role_expr(target) is None

    def test_l0_5_role_expr_truncates_long_name(self):
        """_l0_5_role_expr trunca accessible_name para 40 caracteres."""
        compiler = PlaywrightCompiler()
        long_name = "A" * 100
        target = SemanticTarget(role="button", accessible_name=long_name)
        expr = compiler._l0_5_role_expr(target)
        assert expr is not None
        assert "A" * 40 in expr
        assert "A" * 41 not in expr

    def test_compiled_code_imports_re(self):
        """Script de teste gerado importa re para suporte a regex L0.5."""
        tc = SemanticTestCase(test_id="ST-L05", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "import json, os, re" in code or "import re" in code

    def test_compiled_fill_includes_l0_5_regex(self):
        """Step fill com role+nome gera fallback re.compile."""
        tc = SemanticTestCase(test_id="ST-L05-FILL", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        target = SemanticTarget(role="textbox", accessible_name="Renda mensal",
                                placeholder="R$0,00")
        target.candidates = [
            LocatorCandidate("placeholder", "input[placeholder='R$0,00']", 0.85),
            LocatorCandidate("id", "#renda", 0.75),
        ]
        tc.steps.append(SemanticAction(action="fill", target=target, value="5000"))
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "re.compile(re.escape" in code, f"L0.5 re.compile nao encontrado em:\n{code}"

    def test_compiled_click_includes_l0_5_regex(self):
        """Step click com role+nome gera fallback re.compile."""
        tc = SemanticTestCase(test_id="ST-L05-CLK", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        target = SemanticTarget(role="button", accessible_name="Continuar",
                                text="Continuar", tag="button")
        target.candidates = [
            LocatorCandidate("role", "role=button[name='Continuar']", 0.95),
            LocatorCandidate("text", "button:has-text('Continuar')", 0.55),
        ]
        tc.steps.append(SemanticAction(action="click", target=target))
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "re.compile(re.escape" in code, f"L0.5 re.compile nao encontrado em:\n{code}"

    def test_compiled_fill_without_role_no_l0_5(self):
        """Fill sem role+nome nao gera re.compile."""
        tc = SemanticTestCase(test_id="ST-L05-NO", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        tc.steps.append(SemanticAction(action="navigation"))
        target = SemanticTarget(placeholder="R$0,00")
        target.candidates = [
            LocatorCandidate("placeholder", "input[placeholder='R$0,00']", 0.85),
        ]
        tc.steps.append(SemanticAction(action="fill", target=target, value="5000"))
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()
            assert "re.compile" not in code, f"re.compile inesperado em:\n{code}"


class TestCompoundSelectors:
    """Testes para seletores compostos por atributos (combinacao de 2 atributos)."""

    def _run_compound_test(self, target_data: dict, expected_count: int = 0):
        """Helper: executa _build_target e conta candidatos compostos."""
        normalizer = RecordingNormalizer()
        target = normalizer._build_target(target_data)
        compounds = [c for c in target.candidates if c.strategy == "compound"]
        return compounds

    def test_compound_placeholder_aria_label(self):
        """Composto gerado quando placeholder + accessible_name existem."""
        compounds = self._run_compound_test({
            "tag": "input", "placeholder": "R$0,00",
            "accessible_name": "Renda mensal *",
            "name": "renda",
        })
        assert len(compounds) >= 1
        compound = [c for c in compounds if "placeholder" in c.selector and "aria-label" in c.selector]
        assert compound, f"Nenhum composto placeholder+aria-label encontrado entre: {[c.selector for c in compounds]}"
        assert compound[0].score >= 0.85

    def test_compound_placeholder_name(self):
        """Composto gerado quando placeholder + name existem."""
        compounds = self._run_compound_test({
            "tag": "input", "placeholder": "R$0,00",
            "name": "renda",
        })
        compound = [c for c in compounds if "placeholder" in c.selector and "[name=" in c.selector]
        assert compound, f"Nenhum composto placeholder+name encontrado entre: {[c.selector for c in compounds]}"
        assert compound[0].score >= 0.70

    def test_compound_aria_label_name(self):
        """Composto gerado quando accessible_name + name existem."""
        compounds = self._run_compound_test({
            "tag": "input", "accessible_name": "Renda mensal *",
            "name": "renda",
        })
        compound = [c for c in compounds if "aria-label" in c.selector and "[name=" in c.selector]
        assert compound, f"Nenhum composto aria-label+name encontrado entre: {[c.selector for c in compounds]}"

    def test_compound_no_overlap_produces_none(self):
        """Nenhum composto gerado quando nao existem atributos pareados."""
        compounds = self._run_compound_test({
            "tag": "input", "placeholder": "R$0,00",
        })
        assert len(compounds) == 0

    def test_compound_selector_has_correct_tag(self):
        """Seletor composto inclui prefixo de tag."""
        compounds = self._run_compound_test({
            "tag": "input", "placeholder": "R$0,00",
            "accessible_name": "Renda mensal *",
            "name": "renda",
        })
        assert compounds
        for c in compounds:
            assert c.selector.startswith("input["), f"Composto sem prefixo de tag: {c.selector}"

    def test_compound_score_is_higher_than_single(self):
        """Score composto e maior que o score minimo de atributo unico."""
        compounds = self._run_compound_test({
            "tag": "input", "placeholder": "R$0,00",
            "accessible_name": "Renda mensal *",
        })
        assert compounds
        # placeholder unico = 0.85, aria-label unico = 0.90
        # composto deve ser min(0.85, 0.90) + 0.05 = 0.90
        assert any(c.score >= 0.88 for c in compounds), f"Scores muito baixos: {[c.score for c in compounds]}"


class TestFingerprint:
    """Testes para impressao digital multi-atributo em SemanticTarget."""

    def test_fingerprint_populated_in_build_target(self):
        """_build_target retorna SemanticTarget com dicionario fingerprint."""
        normalizer = RecordingNormalizer()
        target = normalizer._build_target({
            "tag": "input", "placeholder": "R$0,00",
            "accessible_name": "Renda mensal *", "name": "renda",
            "role": "textbox", "label": "Renda mensal",
        })
        assert hasattr(target, "fingerprint")
        assert isinstance(target.fingerprint, dict)
        assert len(target.fingerprint) > 0

    def test_fingerprint_contains_key_attributes(self):
        """Fingerprint inclui tag, role, accessible_name, placeholder."""
        normalizer = RecordingNormalizer()
        target = normalizer._build_target({
            "tag": "input", "role": "textbox",
            "accessible_name": "Renda mensal *",
            "placeholder": "R$0,00", "name": "renda",
        })
        fp = target.fingerprint
        assert fp.get("tag") == "input"
        assert fp.get("role") == "textbox"
        assert fp.get("accessible_name") == "Renda mensal *"
        assert fp.get("placeholder") == "R$0,00"
        assert fp.get("name") == "renda"

    def test_fingerprint_empty_values_filtered(self):
        """Valores vazios sao filtrados do fingerprint para mante-lo compacto."""
        normalizer = RecordingNormalizer()
        target = normalizer._build_target({
            "tag": "input", "placeholder": "R$0,00",
        })
        fp = target.fingerprint
        assert "tag" in fp
        assert "placeholder" in fp
        # role, accessible_name, label, test_id, name devem estar ausentes (vazios)
        for key in ("role", "accessible_name", "label", "test_id", "name"):
            assert key not in fp, f"Chave '{key}' deveria ser filtrada"

    def test_fingerprint_in_to_dict(self):
        """Fingerprint e serializado em SemanticTestCase.to_dict()."""
        tc = SemanticTestCase(test_id="ST-FP", source_recording_id="REC-FP",
                              application="test", base_url="http://localhost")
        target = SemanticTarget(role="button", accessible_name="Submit",
                                fingerprint={"tag": "button", "role": "button"})
        target.candidates = [LocatorCandidate("role", "role=button", 0.95)]
        tc.steps.append(SemanticAction(action="click", target=target))
        d = tc.to_dict()
        steps = d["semantic_test_case"]["steps"]
        assert len(steps) == 1
        assert "fingerprint" in steps[0]["target"]
        assert steps[0]["target"]["fingerprint"]["tag"] == "button"

    def test_fingerprint_nth_child_preserved(self):
        """Fingerprint inclui nth_child quando > 0."""
        normalizer = RecordingNormalizer()
        target = normalizer._build_target({
            "tag": "button", "text": "OK",
            "nth_child": 3,
        })
        fp = target.fingerprint
        assert fp.get("nth_child") == 3


class TestSemanticStepsJsonl:
    """Testes para geracao de semantic_steps.jsonl junto com script compilado."""

    def _build_test_case(self) -> SemanticTestCase:
        """Constroi um SemanticTestCase com steps de fill, click, assert."""
        tc = SemanticTestCase(
            test_id="ST-JSONL", source_recording_id="REC-JSONL",
            application="fake-bank", base_url="http://localhost:8765",
        )
        # Navigation
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765"))
        # Fill
        fill_target = SemanticTarget(role="textbox", label="CPF", placeholder="000.000.000-00", element_id="cpfField")
        fill_target.candidates = [
            LocatorCandidate("label", 'label:has-text("CPF") + input', 0.90),
            LocatorCandidate("placeholder", '[placeholder="000.000.000-00"]', 0.85),
        ]
        tc.steps.append(SemanticAction(action="fill", target=fill_target, value="12345678900"))
        # Click
        click_target = SemanticTarget(role="button", accessible_name="Pesquisar", text="Pesquisar")
        click_target.candidates = [
            LocatorCandidate("role", 'role=button[name="Pesquisar"]', 0.95),
        ]
        tc.steps.append(SemanticAction(action="click", target=click_target))
        # Assert
        tc.steps.append(SemanticAction(
            action="assert",
            target=SemanticTarget(text="resultado", element_id="result"),
            value="CPF consultado",
            context={"assert_type": "textual"},
        ))
        return tc

    def test_generates_file(self):
        """compile_semantic_steps gera semantic_steps.jsonl."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)
            assert os.path.exists(path)
            assert path.endswith("semantic_steps.jsonl")

    def test_metadata_header_line(self):
        """Primeira linha e um registro JSON de metadados."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            assert len(lines) >= 5  # metadata + 4 steps
            header = json.loads(lines[0])
            assert header["type"] == "metadata"
            assert header["test_id"] == "ST-JSONL"
            assert header["source_recording_id"] == "REC-JSONL"
            assert header["application"] == "fake-bank"
            assert header["base_url"] == "http://localhost:8765"
            assert header["step_count"] == 4

    def test_fill_step_serialized(self):
        """Step fill tem action, value, target com candidates."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            fill_line = json.loads(lines[2])  # linha 3: fill (apos metadata, nav)
            assert fill_line["action"] == "fill"
            assert fill_line["value"] == "12345678900"
            target = fill_line["target"]
            assert target["role"] == "textbox"
            assert target["label"] == "CPF"
            assert target["id"] == "cpfField"
            assert len(target["candidates"]) == 2
            assert target["candidates"][0]["strategy"] == "label"
            assert target["candidates"][0]["score"] == 0.90

    def test_click_step_serialized(self):
        """Step click tem action, target com role e candidates."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            click_line = json.loads(lines[3])  # linha 4: click
            assert click_line["action"] == "click"
            target = click_line["target"]
            assert target["role"] == "button"
            assert target["accessible_name"] == "Pesquisar"
            assert len(target["candidates"]) == 1

    def test_assert_step_serialized(self):
        """Step assert tem action, value, context."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            assert_line = json.loads(lines[4])  # linha 5: assert
            assert assert_line["action"] == "assert"
            assert assert_line["value"] == "CPF consultado"
            assert assert_line["context"]["assert_type"] == "textual"
            target = assert_line["target"]
            assert target["text"] == "resultado"

    def test_skip_reason_included(self):
        """Steps com skip_reason o incluem no registro JSONL."""
        tc = SemanticTestCase(test_id="ST-SKIP", source_recording_id="REC-001",
                              application="test", base_url="http://localhost")
        step = SemanticAction(
            action="click",
            target=SemanticTarget(role="button", text="OK", candidates=[]),
            skip_reason="non-actionable target",
        )
        tc.steps.append(step)

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            assert len(lines) == 2  # metadata + 1 step
            step_line = json.loads(lines[1])
            assert step_line["skip_reason"] == "non-actionable target"

    def test_every_line_is_valid_json(self):
        """Toda linha em semantic_steps.jsonl e JSON valido."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    assert line, f"Linha {i + 1} esta vazia"
                    obj = json.loads(line)
                    assert isinstance(obj, dict), f"Linha {i + 1} nao e um dicionario"

    def test_generated_alongside_compiled_script(self):
        """compile() ja gera o script; compile_semantic_steps()
        gera o JSONL no mesmo diretorio de saida."""
        tc = self._build_test_case()
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            script_path = compiler.compile(tc, tmpdir)
            semantic_path = compiler.compile_semantic_steps(tc, tmpdir)

            assert os.path.exists(script_path)
            assert os.path.exists(semantic_path)
            assert os.path.dirname(script_path) == os.path.dirname(semantic_path)

    def test_empty_steps(self):
        """TestCase sem steps ainda gera JSONL valido (apenas metadata)."""
        tc = SemanticTestCase(test_id="ST-EMPTY", source_recording_id="REC-001",
                              application="test", base_url="http://localhost")
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            assert len(lines) == 1  # apenas metadata
            header = json.loads(lines[0])
            assert header["step_count"] == 0

    def test_navigation_step_no_target(self):
        """Step de navegacao serializa sem chave target."""
        tc = SemanticTestCase(test_id="ST-NAV", source_recording_id="REC-001",
                              application="test", base_url="http://localhost")
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost/page"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile_semantic_steps(tc, tmpdir)

            with open(path) as f:
                lines = f.readlines()

            nav_line = json.loads(lines[1])
            assert nav_line["action"] == "navigation"
            assert nav_line["url"] == "http://localhost/page"
            assert "target" not in nav_line

    def test_step_to_record_omits_empty_values(self):
        """_step_to_record omite chaves com valores vazios/falsos."""
        compiler = PlaywrightCompiler()
        step = SemanticAction(action="click")
        record = compiler._step_to_record(step)
        assert record == {"action": "click"}
        assert "value" not in record
        assert "target" not in record
        assert "context" not in record
        assert "url" not in record
        assert "blocking" not in record
        assert "depends_on" not in record

    def test_step_to_record_blocking(self):
        """_step_to_record inclui blocking quando True."""
        compiler = PlaywrightCompiler()
        step = SemanticAction(action="click", blocking=True)
        record = compiler._step_to_record(step)
        assert record["blocking"] is True

    def test_step_to_record_depends_on(self):
        """_step_to_record inclui depends_on quando definido."""
        compiler = PlaywrightCompiler()
        step = SemanticAction(action="click", depends_on="step_0003")
        record = compiler._step_to_record(step)
        assert record["depends_on"] == "step_0003"


class TestStepDependencyDetection:
    """Testes para _detect_step_dependencies em RecordingNormalizer."""

    def _make_select_step(self, action="select_option", tag="select",
                          element_id="uf", text=""):
        """Helper para criar um SemanticAction para steps select/fill."""
        target = SemanticTarget(
            tag=tag, element_id=element_id, text=text,
            candidates=[LocatorCandidate("id", f"#{element_id}", 0.90)],
        )
        return SemanticAction(action=action, target=target)

    def test_single_step_no_dependency(self):
        """Step select unico: nenhuma dependencia criada."""
        normalizer = RecordingNormalizer()
        steps = [self._make_select_step(element_id="uf")]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is False
        assert steps[0].depends_on == ""

    def test_two_select_steps_create_dependency(self):
        """Dois steps select consecutivos: primeiro e blocking, segundo depende."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf", text="UF"),
            self._make_select_step(element_id="edificio", text="Edificio"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is True
        assert steps[0].depends_on == ""
        assert steps[1].blocking is False
        assert steps[1].depends_on == "step_0001"

    def test_three_select_steps_chain(self):
        """Tres selects consecutivos: primeiro bloqueia, outros dependem do primeiro."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf", text="UF"),
            self._make_select_step(element_id="edificio", text="Edificio"),
            self._make_select_step(element_id="data", text="Data"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is True
        assert steps[1].depends_on == "step_0001"
        assert steps[2].depends_on == "step_0001"

    def test_navigation_breaks_chain(self):
        """Navegacao entre selects quebra a cadeia de dependencia."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf"),
            SemanticAction(action="navigation", url="http://localhost/page2"),
            self._make_select_step(element_id="edificio"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is False  # chain length 1 (parou no nav)
        assert steps[2].blocking is False  # chain length 1

    def test_assert_breaks_chain(self):
        """Assert entre selects quebra a cadeia de dependencia."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf"),
            SemanticAction(action="assert", value="visible",
                          target=SemanticTarget(text="resultado")),
            self._make_select_step(element_id="edificio"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is False  # chain length 1
        assert steps[2].blocking is False  # chain length 1

    def test_fill_and_select_in_same_chain(self):
        """Fill e select na mesma cadeia com <select>: primeiro e blocking."""
        normalizer = RecordingNormalizer()
        fill_step = SemanticAction(
            action="fill", value="123",
            target=SemanticTarget(tag="input", element_id="cpf",
                                  candidates=[LocatorCandidate("id", "#cpf", 0.90)]),
        )
        select_step = self._make_select_step(element_id="uf")
        steps = [fill_step, select_step]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is True
        assert steps[1].depends_on == "step_0001"

    def test_fills_only_no_select_no_dependency(self):
        """Multiplos fills na mesma pagina sem <select>: sem dependencia."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(
                action="fill", value="123",
                target=SemanticTarget(tag="input", element_id="cpf",
                                      candidates=[LocatorCandidate("id", "#cpf", 0.90)]),
            ),
            SemanticAction(
                action="fill", value="Joao",
                target=SemanticTarget(tag="input", element_id="nome",
                                      candidates=[LocatorCandidate("id", "#nome", 0.90)]),
            ),
            SemanticAction(
                action="fill", value="Silva",
                target=SemanticTarget(tag="input", element_id="sobrenome",
                                      candidates=[LocatorCandidate("id", "#sobrenome", 0.90)]),
            ),
        ]
        normalizer._detect_step_dependencies(steps)
        assert all(s.blocking is False for s in steps)
        assert all(s.depends_on == "" for s in steps)

    def test_click_in_chain(self):
        """Click na cadeia de entrada de dados: incluido na dependencia."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf"),
            SemanticAction(
                action="click",
                target=SemanticTarget(role="button", text="OK",
                                      candidates=[LocatorCandidate("text", "text=OK", 0.55)]),
            ),
            self._make_select_step(element_id="edificio"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is True
        assert steps[1].depends_on == "step_0001"
        assert steps[2].depends_on == "step_0001"

    def test_explicit_dependency_preserved(self):
        """Step com depends_on explicito nao e autodetectado."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf"),
            SemanticAction(
                action="select_option", depends_on="step_0005",
                target=SemanticTarget(tag="select", element_id="edificio",
                                      candidates=[LocatorCandidate("id", "#edificio", 0.90)]),
            ),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is False  # cadeia quebrada por dep explicito
        assert steps[1].depends_on == "step_0005"  # preservado

    def test_explicit_blocking_preserved(self):
        """Step com blocking=True explicito nao e autodetectado."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(
                action="select_option", blocking=True,
                target=SemanticTarget(tag="select", element_id="uf",
                                      candidates=[LocatorCandidate("id", "#uf", 0.90)]),
            ),
            self._make_select_step(element_id="edificio"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is True  # preservado
        assert steps[1].depends_on == ""  # segundo faz parte de cadeia diferente

    def test_skipped_step_breaks_chain(self):
        """Step com skip_reason quebra a cadeia."""
        normalizer = RecordingNormalizer()
        steps = [
            self._make_select_step(element_id="uf"),
            SemanticAction(
                action="select_option", skip_reason="non-actionable target",
                target=SemanticTarget(tag="select", element_id="edificio",
                                      candidates=[]),
            ),
            self._make_select_step(element_id="data"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert steps[0].blocking is False  # cadeia quebrada por skipped step

    def test_empty_steps(self):
        """Lista de steps vazia: sem erro."""
        normalizer = RecordingNormalizer()
        steps = []
        normalizer._detect_step_dependencies(steps)
        assert steps == []

    def test_only_navigation(self):
        """Steps apenas de navegacao: sem dependencias."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="navigation", url="http://localhost"),
            SemanticAction(action="navigation", url="http://localhost/page2"),
        ]
        normalizer._detect_step_dependencies(steps)
        assert all(s.blocking is False for s in steps)
        assert all(s.depends_on == "" for s in steps)


class TestStepsJsonlDependencies:
    """Testes para leitura de blocking/depends_on de steps.jsonl."""

    def test_steps_jsonl_with_blocking(self):
        """Converte step de steps.jsonl com blocking=True."""
        normalizer = RecordingNormalizer()
        step_data = {
            "action": "select_option",
            "value": "SP",
            "tagName": "select",
            "id": "ufSelect",
            "blocking": True,
        }
        result = normalizer._convert_step(step_data)
        assert result is not None
        assert result.action == "select_option"
        assert result.blocking is True
        assert result.depends_on == ""

    def test_steps_jsonl_with_depends_on(self):
        """Converte step de steps.jsonl com depends_on."""
        normalizer = RecordingNormalizer()
        step_data = {
            "action": "select_option",
            "value": "Edificio A",
            "tagName": "select",
            "id": "edificioSelect",
            "depends_on": "step_0003",
        }
        result = normalizer._convert_step(step_data)
        assert result is not None
        assert result.depends_on == "step_0003"
        assert result.blocking is False

    def test_steps_jsonl_with_context(self):
        """Converte step com dicionario context de steps.jsonl."""
        normalizer = RecordingNormalizer()
        step_data = {
            "action": "click",
            "tagName": "button",
            "text": "Pesquisar",
            "context": {"is_submit": True, "postback_url": "http://localhost/result"},
        }
        result = normalizer._convert_step(step_data)
        assert result is not None
        assert result.context.get("is_submit") is True
        assert result.context.get("postback_url") == "http://localhost/result"


class TestCompilerFieldValues:
    """Testes de integracao do PlaywrightCompiler com field_values."""

    def _make_fill_tc(self, value: str = "12345678900") -> SemanticTestCase:
        """Cria SemanticTestCase com um step de fill (CPF)."""
        tc = SemanticTestCase(
            test_id="ST-FV",
            source_recording_id="REC-FV",
            application="fake-bank",
            base_url="http://localhost:8765",
        )
        fill_target = SemanticTarget(
            role="textbox",
            label="CPF",
            placeholder="000.000.000-00",
            element_id="cpfField",
        )
        fill_target.candidates = [
            LocatorCandidate("label", 'label:has-text("CPF") + input', 0.90),
            LocatorCandidate("id", "#cpfField", 0.75),
        ]
        tc.steps.append(SemanticAction(action="fill", target=fill_target, value=value))
        return tc

    def test_compiler_uses_field_values(self):
        """fill usa o valor de field_values quando disponivel."""
        from testforge.semantic.model import FieldValueMap

        tc = self._make_fill_tc(value="original_value")
        field_values = {
            "cpf": FieldValueMap(
                field_key="cpf",
                value="98765432100",
                source="form_values",
            )
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir, field_values=field_values)

            with open(path) as f:
                code = f.read()

            # Valor do field_values deve aparecer no script gerado
            assert "98765432100" in code
            # Valor original NÃO deve aparecer (foi substituído)
            assert "original_value" not in code

    def test_compiler_fallback_without_field_values(self):
        """Sem field_values, usa o valor original do step."""
        tc = self._make_fill_tc(value="12345678900")

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)  # sem field_values

            with open(path) as f:
                code = f.read()

            # Valor original preservado
            assert "12345678900" in code

    def test_compiler_data_file_injection(self):
        """data_file_dict preenche missing_fill quando field_value esta vazio."""
        from testforge.semantic.model import FieldValueMap

        tc = self._make_fill_tc(value="")  # valor vazio — missing_fill
        # field_values existe mas com value vazio (capturado como missing)
        field_values = {
            "cpf": FieldValueMap(
                field_key="cpf",
                value="",  # vazio — missing_fill
                source="missing_fill",
            )
        }
        # data_file_dict fornece o valor real para o campo vazio
        data_file_dict = {"cpf": "11122233344"}

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(
                tc, tmpdir,
                field_values=field_values,
                data_file_dict=data_file_dict,
            )

            with open(path) as f:
                code = f.read()

            # data_file_dict deve preencher o missing_fill
            assert "11122233344" in code
