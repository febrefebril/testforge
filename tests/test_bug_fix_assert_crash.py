"""Teste de regressão — Bug 1: _persist_step não deve propagar exceções."""
import json
import os
import builtins
import pytest
from unittest.mock import MagicMock


def test_persist_step_survives_page_title_error(tmp_path):
    """Se page.title() lança exceção (browser fechado), _persist_step não deve propagar."""
    from testforge.recorder.recorder_controller import RecorderController

    page = MagicMock()
    page.add_init_script = MagicMock()
    page.title.side_effect = Exception("Target page, context or browser has been closed")
    page.url = "http://localhost"

    ctrl = RecorderController(page)
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    step_data = {"action": "assert", "selector": "button", "tagName": "button",
                 "text": "Enviar", "value": "", "timestamp": "T1",
                 "assert_type": "visivel", "assert_state": "visible"}

    try:
        ctrl._persist_step(step_data)
    except Exception as exc:
        pytest.fail(f"_persist_step propagou exceção: {exc}")


def test_persist_step_survives_encoding_error(tmp_path, monkeypatch):
    """Se escrita de arquivo falha, _persist_step não deve propagar."""
    from testforge.recorder.recorder_controller import RecorderController

    page = MagicMock()
    page.add_init_script = MagicMock()
    page.title.return_value = "Página de teste"
    page.url = "http://localhost"

    ctrl = RecorderController(page)
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    original_open = builtins.open

    def failing_open(path, *args, **kwargs):
        if "steps.jsonl" in str(path):
            raise IOError("Simulação de disco cheio")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)

    step_data = {"action": "fill", "selector": "input", "tagName": "input",
                 "text": "", "value": "teste", "timestamp": "T1"}
    try:
        ctrl._persist_step(step_data)
    except Exception as exc:
        pytest.fail(f"_persist_step propagou IOError: {exc}")
