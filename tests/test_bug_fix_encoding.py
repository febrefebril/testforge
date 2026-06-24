"""Regression test — Bug 5: encoding utf-8 explicit in all write paths."""
import json
import os
import pytest
from unittest.mock import MagicMock


def test_compiler_writes_utf8(tmp_path):
    """Compiled test file must be readable as utf-8 even with accented chars."""
    from testforge.semantic.compiler import PlaywrightCompiler
    from testforge.semantic.model import (
        SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate,
    )

    target = SemanticTarget(
        role="textbox",
        accessible_name="Renda mensal",
        placeholder="R$0,00",
        tag="input",
        candidates=[
            LocatorCandidate(strategy="aria_label", selector='input[aria-label="Renda mensal *"]', score=9)
        ],
    )
    action = SemanticAction(action="fill", target=target, value="1.000,00 — ação de preenchimento")
    stc = SemanticTestCase(
        test_id="test_enc",
        source_recording_id="test_enc",
        base_url="http://localhost:8765",
        steps=[action],
    )
    compiler = PlaywrightCompiler()
    path = compiler.compile(stc, str(tmp_path))
    content = open(path, encoding="utf-8").read()
    assert "1.000,00" in content


def test_persist_step_writes_utf8(tmp_path):
    """_persist_step must not raise on accented text."""
    from testforge.recorder.recorder_controller import RecorderController

    page = MagicMock()
    page.add_init_script = MagicMock()
    page.title.return_value = "Página de teste"
    page.url = "http://localhost"

    ctrl = RecorderController(page)
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    step_data = {
        "action": "fill",
        "selector": 'input[aria-label="Valor do imóvel *"]',
        "tagName": "input",
        "text": "Imóvel com ação especial",
        "value": "500.000,00",
        "timestamp": "2026-06-24T00:00:00Z",
    }
    ctrl._persist_step(step_data)
    steps_file = tmp_path / "steps.jsonl"
    assert steps_file.exists()
    content = steps_file.read_text(encoding="utf-8")
    data = json.loads(content.strip())
    assert data["text"] == "Imóvel com ação especial"
