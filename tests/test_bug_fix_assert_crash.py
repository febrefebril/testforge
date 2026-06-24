"""Regression test — Bug 1: _persist_step must not propagate exceptions."""
import json
import os
import builtins
import pytest
from unittest.mock import MagicMock


def test_persist_step_survives_page_title_error(tmp_path):
    """If page.title() raises (browser closed), _persist_step must not propagate."""
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
        pytest.fail(f"_persist_step propagated exception: {exc}")


def test_persist_step_survives_encoding_error(tmp_path, monkeypatch):
    """If file write fails, _persist_step must not propagate."""
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
            raise IOError("Simulated disk full")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)

    step_data = {"action": "fill", "selector": "input", "tagName": "input",
                 "text": "", "value": "teste", "timestamp": "T1"}
    try:
        ctrl._persist_step(step_data)
    except Exception as exc:
        pytest.fail(f"_persist_step propagated IOError: {exc}")
