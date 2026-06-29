"""Testes de regressão — Bugs 11-16: gravação e reprodução de <select>."""
import json
import os
import tempfile
import pytest


# ---- Bug 11: setTimeout adia contador de passos, pula clique em SELECT ----

def test_overlay_js_click_skips_select():
    """Handler de clique deve retornar cedo para elementos SELECT."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    click_block_start = src.find("// ---- Click capture (primary) ----")
    assert click_block_start != -1
    skip_select = src.find("if (el && el.tagName === 'SELECT') return;", click_block_start)
    push_click = src.find("_pushEvent('click', el)", click_block_start)
    assert skip_select != -1, "Handler de clique deve pular elementos SELECT"
    assert skip_select < push_click, "Pulo de SELECT deve vir antes de _pushEvent('click')"


def test_overlay_js_step_counter_uses_settimeout():
    """Incremento do contador de passos após clique deve ser adiado via setTimeout."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    push_click = src.find("_pushEvent('click', el)")
    assert push_click != -1
    settimeout_pos = src.find("setTimeout(function()", push_click)
    next_listener = src.find("window.addEventListener(", push_click + 1)
    assert settimeout_pos != -1, "setTimeout deve envolver atualização do contador de passos após clique"
    assert settimeout_pos < next_listener, "setTimeout deve estar dentro do listener de clique"
    # __tfStepCount deve estar dentro do callback do setTimeout
    step_count_pos = src.find("__tfStepCount", settimeout_pos)
    close_paren = src.find("}, 0);", settimeout_pos)
    assert step_count_pos != -1 and step_count_pos < close_paren, \
        "Incremento de __tfStepCount deve estar dentro do callback do setTimeout"


# ---- Bug 12: change em SELECT gera evento select_option ----

def test_overlay_js_change_generates_select_option():
    """Evento change em SELECT deve enviar 'select_option', não 'fill'."""
    from pathlib import Path
    src = (Path(__file__).parent.parent /
           "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")
    change_start = src.find("window.addEventListener('change'")
    assert change_start != -1
    evt_type_var = src.find("evtType", change_start)
    assert evt_type_var != -1, "handler de change deve usar variável evtType"
    select_branch = src.find("'select_option'", change_start)
    assert select_branch != -1, "handler de change deve emitir 'select_option' para SELECT"


def test_normalizer_maps_select_option_action():
    """recording_normalizer deve mapear eventos brutos select_option para ações select_option."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    select_target = {
        "tag": "select", "id": "lstUf", "name": "lstUf", "placeholder": "",
        "accessible_name": "", "label": "UF", "text": "DF", "class_list": [],
        "attributes": {}, "type": None, "css_path": "select#lstUf",
    }
    raw_events = [
        {
            "type": "select_option", "target": select_target, "value": "DF",
            "timestamp": "2026-06-24T10:00:00Z", "url": "http://x",
            "page_title": "Test",
        },
    ]

    with tempfile.TemporaryDirectory() as td:
        events_file = os.path.join(td, "raw_events.jsonl")
        with open(events_file, "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        meta_file = os.path.join(td, "recording_metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "recording_id": "test_so", "base_url": "http://x",
                "application": "web", "status": "stopped",
            }, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    non_nav = [s for s in stc.steps if s.action != "navigation"]
    assert non_nav, "Deve produzir ao menos um passo não-navegação"
    select_steps = [s for s in non_nav if s.action == "select_option"]
    assert select_steps, \
        f"evento bruto select_option deve produzir passo select_option; obtido: {[s.action for s in non_nav]}"


# ---- Bug 13: try_fill despacha select_option para elementos <select> ----

def test_try_fill_uses_select_option_for_select_tag():
    """FallbackRunner.try_fill deve chamar page.select_option, não page.fill, para tag=select."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import FallbackRunner

    page = MagicMock()
    page.select_option = MagicMock(return_value=None)
    page.fill = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()

    runner = FallbackRunner(page)
    candidates = [{"selector": "select#lstUf", "tag": "select"}]
    result = runner.try_fill(candidates, "DF")

    assert result is True
    page.select_option.assert_called_once_with("select#lstUf", "DF", timeout=5000)
    page.fill.assert_not_called()


def test_try_fill_uses_fill_for_non_select():
    """FallbackRunner.try_fill deve usar page.fill para tags não-select."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import FallbackRunner

    page = MagicMock()
    page.fill = MagicMock(return_value=None)
    page.select_option = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()

    runner = FallbackRunner(page)
    candidates = [{"selector": "input#name", "tag": "input"}]
    result = runner.try_fill(candidates, "André")

    assert result is True
    page.fill.assert_called_once_with("input#name", "André", timeout=5000)
    page.select_option.assert_not_called()


# ---- Bug 14: SmartStepRunner lida com ação select_option ----

def test_smart_step_runner_handles_select_option():
    """SmartStepRunner deve despachar page.select_option para action='select_option'."""
    from unittest.mock import MagicMock
    from testforge.runner.fallback_runner import SmartStepRunner

    page = MagicMock()
    page.select_option = MagicMock(return_value=None)
    page.fill = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()
    page.wait_for_selector = MagicMock(return_value=None)

    runner = SmartStepRunner(page)
    step_data = {"selector": "select#lstUf", "action": "select_option", "value": "DF"}
    result = runner.execute(step_data)

    assert result is True
    page.select_option.assert_called_once_with("select#lstUf", "DF", timeout=SmartStepRunner.FILL_TIMEOUT)
    page.fill.assert_not_called()


# ---- Bug 15: label preservado em SemanticTarget para elementos select ----

def test_normalizer_preserves_label_for_select():
    """label do target em raw_events deve aparecer em SemanticTarget para elementos select."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    select_target = {
        "tag": "select", "name": "lstUf", "label": "UF",
        "text": "DF", "id": "lstUf", "placeholder": "",
        "accessible_name": None, "attributes": {}, "css_path": "select#lstUf",
    }
    raw_events = [
        {
            "type": "select_option", "target": select_target, "value": "DF",
            "timestamp": "2026-06-24T10:00:00Z", "url": "http://x",
            "page_title": "Test",
        },
    ]

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "raw_events.jsonl"), "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        with open(os.path.join(td, "recording_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "recording_id": "test_label", "base_url": "http://x",
                "application": "web", "status": "stopped",
            }, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    select_steps = [s for s in stc.steps if s.action == "select_option" and s.target]
    assert select_steps, "Deve produzir um passo select_option com target"
    t = select_steps[0].target
    assert t.label == "UF", f"label deve ser 'UF', obtido: {t.label!r}"
    assert t.name == "lstUf", f"name deve ser 'lstUf', obtido: {t.name!r}"


# ---- Bug 16: cliques redundantes em select eliminados antes de select_option ----

def test_eliminate_prefill_clicks_removes_select_clicks():
    """_eliminate_prefill_clicks deve pular passos de clique antes de select_option no mesmo <select>."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer
    from testforge.semantic.model import (
        SemanticAction, SemanticTarget, LocatorCandidate,
    )

    cand = LocatorCandidate("name", "select#lstUf", 0.93, "name=lstUf")
    target = SemanticTarget(tag="select", name="lstUf", label="UF", candidates=[cand])

    click1 = SemanticAction(action="click", target=target)
    click2 = SemanticAction(action="click", target=target)
    select_op = SemanticAction(action="select_option", value="DF", target=target)
    steps = [click1, click2, select_op]

    norm = RecordingNormalizer()
    norm._eliminate_prefill_clicks(steps)

    skipped = [s for s in steps if s.skip_reason]
    kept = [s for s in steps if not s.skip_reason]
    # Pelo menos o clique imediatamente antes de select_option deve ser pulado
    assert len(kept) <= 2, f"Muitos passos mantidos: {[(s.action, s.skip_reason) for s in steps]}"
    assert any(s.action == "select_option" and not s.skip_reason for s in steps), \
        "passo select_option não deve ser pulado"
