"""Testes do Semantic Intermediate Model e Compiler."""
import json
import os
import tempfile

from testforge.semantic import (
    LocatorCandidate, SemanticAction, SemanticTarget,
    SemanticTestCase, RecordingNormalizer, PlaywrightCompiler,
)


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
