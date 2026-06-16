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
        """Sequential fills on same target within 500ms: keep only final event."""
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
        """keypress events are also compacted as fill."""
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
        """Multiple rapid fills: only the last one survives."""
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
        """Fills on different elements are NOT compacted together."""
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

    def test_compact_fill_events_non_fill_preserved(self):
        """Non-fill events (navigation, click) pass through unchanged."""
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
        """Fills > 500ms apart are NOT compacted."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "123"},
            {"event_id": "e2", "type": "fill", "timestamp": "2026-06-13T00:00:01.000",
             "target": {"tag": "input", "id": "cpfField"}, "value": "456"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 2

    def test_compact_fill_events_multiple_groups(self):
        """Multiple fill groups on different elements."""
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
        """A click between fills on same target resets the group."""
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
        """Empty list returns empty list."""
        normalizer = RecordingNormalizer()
        result = normalizer._compact_fill_events([])
        assert result == []

    def test_compact_fill_events_no_targets(self):
        """Events without targets are handled."""
        normalizer = RecordingNormalizer()
        events = [
            {"event_id": "e1", "type": "fill", "timestamp": "2026-06-13T00:00:00.000",
             "value": "something"},
        ]
        result = normalizer._compact_fill_events(events)
        assert len(result) == 1
        assert result[0]["value"] == "something"


class TestGenericTextDetection:
    """Tests for _is_generic_text — penalizes brittle generic UI labels."""

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
        assert _is_generic_text("Calcular") is True
        assert _is_generic_text("calcular") is True

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
        """Text-based candidates with generic text get score 0.10."""
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
            f"Expected 0.10 for generic text, got {text_candidate.score}"
        )

    def test_build_target_normal_text_unchanged(self):
        """Non-generic text keeps normal score 0.55."""
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
            f"Expected 0.55 for non-generic text, got {text_candidate.score}"
        )


class TestSkipReason:
    """Tests for step skip reason detection in RecordingNormalizer."""

    def _make_events_with_duplicates(self, tmpdir: str) -> str:
        """Create raw_events.jsonl with duplicate click steps."""
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
            # Duplicate click on same button
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
        """Consecutive identical click steps get marked as duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_events_with_duplicates(tmpdir)
            normalizer = RecordingNormalizer()
            stc = normalizer.normalize(tmpdir, "ST-DUP", "test", "http://localhost:8765")

            # Should have 4 steps: nav, fill, click, click
            assert len(stc.steps) == 4

            # First click — no skip_reason
            click_steps = [s for s in stc.steps if s.action == "click"]
            assert len(click_steps) == 2
            assert click_steps[0].skip_reason == ""
            # Second click — duplicate
            assert "duplicate" in click_steps[1].skip_reason
            assert "Step" in click_steps[1].skip_reason

    def test_navigation_not_duplicate_of_click(self):
        """Different action types are never duplicates."""
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
        """Same target but different values are not duplicates."""
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
        """Same steps separated by a different step are not duplicates."""
        normalizer = RecordingNormalizer()
        target = SemanticTarget(role="button", text="OK",
                                candidates=[LocatorCandidate("text", "text=OK", 0.55)])
        steps = [
            SemanticAction(action="click", target=target),
            SemanticAction(action="fill", target=SemanticTarget(placeholder="x",
                                candidates=[LocatorCandidate("placeholder", "[placeholder='x']", 0.85)]),
                           value="data"),
            SemanticAction(action="click", target=target),  # same as first but not consecutive
        ]
        normalizer._deduplicate_steps(steps)
        assert steps[0].skip_reason == ""
        assert steps[1].skip_reason == ""
        assert steps[2].skip_reason == ""  # not consecutive, not marked

    def test_already_skipped_not_rechecked(self):
        """Steps already marked with skip_reason are not re-evaluated."""
        normalizer = RecordingNormalizer()
        target = SemanticTarget(role="button", text="OK",
                                candidates=[LocatorCandidate("text", "text=OK", 0.55)])
        steps = [
            SemanticAction(action="click", target=target, skip_reason="non-actionable target"),
            SemanticAction(action="click", target=target),  # identical to first
        ]
        normalizer._deduplicate_steps(steps)
        # First already has skip_reason, so second is not compared against it
        assert "non-actionable target" in steps[0].skip_reason
        assert steps[1].skip_reason == ""

    def test_non_actionable_target_no_candidates(self):
        """Step with target but zero candidates gets 'non-actionable target'."""
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
        """Assert steps are never flagged as non-actionable."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="assert",
                           target=SemanticTarget(text="some text", candidates=[]),
                           value="expected"),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == ""

    def test_actionable_with_candidates_not_flagged(self):
        """Step with candidates is not flagged."""
        normalizer = RecordingNormalizer()
        steps = [
            SemanticAction(action="click",
                           target=SemanticTarget(role="button",
                                                 candidates=[LocatorCandidate("role", "role=button", 0.90)])),
        ]
        normalizer._mark_non_actionable(steps)
        assert steps[0].skip_reason == ""

    def test_navigation_not_flagged_non_actionable(self):
        """Navigation steps (no target needed) are not flagged."""
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
            # Verify only one page.goto (initial navigation; redundant navigations skipped)
            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Expected exactly 1 page.goto(), got {code.count('page.goto(BASE_URL)')}"
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
        """Submit clicks use expect_navigation instead of wait_for_load_state."""
        tc = SemanticTestCase(test_id="ST-SUB", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # Navigation (skipped — initial goto emitted unconditionally)
        tc.steps.append(SemanticAction(action="navigation"))
        # Submit click with is_submit context
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

            # Must use expect_navigation for submit
            assert "expect_navigation" in code
            assert "wait_until='load'" in code
            # Must NOT use old wait_for_load_state pattern
            assert "wait_for_load_state" not in code
            # Only one goto (the initial)
            assert code.count("page.goto(BASE_URL)") == 1

    def test_compile_non_submit_click_no_expect_navigation(self):
        """Regular clicks (not submit) do NOT use expect_navigation."""
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

            # Regular click: no expect_navigation
            assert "expect_navigation" not in code
            assert "page.click(_sel)" in code
            assert "page.wait_for_timeout(300)" in code

    def test_compile_multiple_navigation_skipped(self):
        """Multiple navigation actions produce only one page.goto()."""
        tc = SemanticTestCase(test_id="ST-MNAV", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # 3 navigation steps — only first (initial) should produce goto
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="navigation"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Expected 1 goto, got {code.count('page.goto(BASE_URL)')}"
            )

    def test_compile_navigation_skip_with_different_url(self):
        """Navigation action with a URL different from base_url is still skipped."""
        tc = SemanticTestCase(test_id="ST-NAVURL", source_recording_id="REC-001",
                              application="fake-bank", base_url="http://localhost:8765")
        # Initial navigation (page already loaded via page.goto)
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765"))
        # Click a link that navigates to a different URL
        click_target = SemanticTarget(role="link", text="Go to Page 2")
        click_target.candidates = [
            LocatorCandidate("text", "text=Go to Page 2", 0.85),
        ]
        tc.steps.append(SemanticAction(action="click", target=click_target))
        # Navigation event captured after the click (redundant — already navigated)
        tc.steps.append(SemanticAction(action="navigation", url="http://localhost:8765/page2"))

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = PlaywrightCompiler()
            path = compiler.compile(tc, tmpdir)
            with open(path) as f:
                code = f.read()

            # Only ONE page.goto (initial navigation)
            assert code.count("page.goto(BASE_URL)") == 1, (
                f"Expected 1 goto, got {code.count('page.goto(BASE_URL)')}"
            )
            # Navigation actions (both initial and post-click) are skipped
            # No explicit navigation to /page2 — the click already causes it
            assert "page.goto" not in code.replace("page.goto(BASE_URL)", "")
            # Click is present
            assert "page.click" in code

    def test_compile_submit_with_postback_url(self):
        """Submit click with postback_url uses expect_navigation."""
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

            # Must use expect_navigation for submit
            assert "expect_navigation" in code
            assert "wait_until='load'" in code
            # Only one goto
            assert code.count("page.goto(BASE_URL)") == 1
            # No redundant goto to postback URL
            assert "resultado" not in code.lower().replace("page.goto(base_url)", "")
