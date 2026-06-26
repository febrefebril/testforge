"""Smoke E2E: record → normalize → compile → run-incremental round-trip.

Walks the full TestForge pipeline on a controlled synthetic fixture
(file://-served HTML with two inputs and a button whose JS handler
renders an assertion target). No external HTTP server, no SIOPI.

Marked browser-dependent — relies on Playwright Chromium.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest
from playwright.sync_api import sync_playwright


_FIXTURE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Smoke Flow</title></head>
<body>
  <h1>Cadastro</h1>
  <label for="nome">Nome</label>
  <input id="nome" placeholder="Nome completo">
  <label for="cpf">CPF</label>
  <input id="cpf" placeholder="000.000.000-00">
  <button id="enviar" type="button">Enviar</button>
  <div id="output"></div>
  <script>
    document.getElementById('enviar').addEventListener('click', () => {
      const nome = document.getElementById('nome').value || '';
      const cpf = document.getElementById('cpf').value || '';
      document.getElementById('output').textContent =
        'Cadastrado: ' + nome + ' (' + cpf + ')';
    });
  </script>
</body>
</html>
"""


def _record(file_url: str, recordings_root: str, recording_id: str) -> str:
    from testforge.recorder.recorder_controller import RecorderController

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        recorder = RecorderController(page, recordings_root=recordings_root)
        recorder.start(recording_id=recording_id)
        page.goto(file_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(400)

        page.click("#nome")
        page.wait_for_timeout(80)
        page.fill("#nome", "Joao Silva")
        page.wait_for_timeout(120)
        page.click("#cpf")
        page.wait_for_timeout(80)
        page.fill("#cpf", "12345678900")
        page.wait_for_timeout(120)
        page.click("#enviar")
        page.wait_for_timeout(400)
        recorder.flush_events()
        page.wait_for_timeout(200)

        recorder.stop()
        recorder.finalize()
        try:
            browser.close()
        except Exception:
            pass
    return os.path.join(recordings_root, recording_id)


@pytest.mark.slow
def test_smoke_pipeline_record_compile_run_incremental(tmp_path):
    from testforge.semantic.recording_normalizer import RecordingNormalizer
    from testforge.semantic.compiler import PlaywrightCompiler
    from testforge.runner.incremental_runner import IncrementalRunner

    work = str(tmp_path)
    fixture_path = os.path.join(work, "smoke.html")
    with open(fixture_path, "w", encoding="utf-8") as f:
        f.write(_FIXTURE_HTML)
    file_url = "file://" + fixture_path
    recordings_root = os.path.join(work, "recordings")
    os.makedirs(recordings_root, exist_ok=True)
    rid = "REC-SMOKE-001"
    out_root = os.path.join(work, "semantic_tests")
    os.makedirs(out_root, exist_ok=True)

    # --- Stage 1: record ---
    rec_dir = _record(file_url, recordings_root, rid)
    raw_events_path = os.path.join(rec_dir, "raw_events.jsonl")
    assert os.path.exists(raw_events_path), "raw_events.jsonl not written"
    with open(raw_events_path) as f:
        raw_events = [json.loads(line) for line in f if line.strip()]
    assert len(raw_events) >= 5, f"expected >=5 raw events, got {len(raw_events)}"
    by_type = {}
    for ev in raw_events:
        t = ev.get("type", "?")
        by_type[t] = by_type.get(t, 0) + 1
    assert by_type.get("click", 0) >= 2, by_type
    assert by_type.get("fill", 0) >= 2, by_type

    # --- Stage 2: normalize ---
    normalizer = RecordingNormalizer()
    stc = normalizer.normalize(rec_dir, f"ST-{rid}", "smoke", file_url)
    assert len(stc.steps) >= 3, f"expected >=3 steps, got {len(stc.steps)}"
    actions = [s.action for s in stc.steps]
    assert "fill" in actions and "click" in actions, actions

    # --- Stage 3: compile ---
    out_dir = os.path.join(out_root, f"ST-{rid}")
    os.makedirs(out_dir, exist_ok=True)
    script_path = PlaywrightCompiler().compile(stc, out_dir)
    assert os.path.exists(script_path), "compiler did not write a script"
    src = open(script_path).read()
    assert "page.goto" in src

    # --- Stage 4: run-incremental ---
    # IncrementalRunner._find_recording_dir resolves <cwd>/recordings/<rid>
    # or <script>/parent/parent/recordings/<rid>; chdir to the smoke
    # workspace so the first candidate hits.
    old_cwd = os.getcwd()
    os.chdir(work)
    try:
        runner = IncrementalRunner(
            script_path=script_path,
            headless=True,
            timeout=30,
            verbose=False,
            stop_on_failure=False,
            no_healing=True,
            capture=False,
            output_root=os.path.join(work, "runs"),
        )
        report = runner.run()
    finally:
        os.chdir(old_cwd)

    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    assert summary, "runner returned empty summary"
    failed = summary.get("failed", 0) + summary.get("healing_rejected", 0)
    passed = summary.get("passed", 0)
    assert failed == 0, f"smoke pipeline failed: {summary}"
    assert passed >= 3, f"smoke produced too few passed steps: {summary}"
