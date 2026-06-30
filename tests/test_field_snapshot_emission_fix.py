"""TestForge — Confirma que field_snapshots.jsonl agora eh emitido.

Bug original (2026-06-30): overlay_inject.js:1083 chamava
`setInterval(function() { _tf_snapshotFields(); }, 2000)` mas o
return de `_snapshotFields()` (array de snapshots) era descartado.
Resultado: `__tfFieldSnapshotQueue` nunca recebia entradas, entao
`field_snapshots.jsonl` nunca era escrito.

Consequencia: Sprint A2 (input_visibility_check) dependia desse
arquivo para decidir entre prefill_click_noise e preserve_revealer.
Sem o arquivo, _input_visible_at_click sempre retornava True (legacy),
e A2 era no-op em recordings reais — confirmado em test-pos-hotfix14a-16d.

Este teste static-check confirma o wrap acumulador.
"""
from __future__ import annotations
from pathlib import Path

OVERLAY = Path(__file__).parent.parent / "src" / "testforge" / "recorder" / "overlay_inject.js"


def test_field_snapshot_interval_pushes_to_queue():
    src = OVERLAY.read_text(encoding="utf-8")
    # O setInterval deve chamar _tf_snapshotFields E empilhar o resultado
    # em __tfFieldSnapshotQueue (com batch timestamp).
    assert "setInterval" in src
    assert "__tfFieldSnapshotQueue.push" in src, (
        "setInterval do field snapshot deve pushar resultado em "
        "__tfFieldSnapshotQueue, senao field_snapshots.jsonl fica vazio"
    )
    # E o batch tem que carregar o array `snapshots` para o flush
    # iterar (recorder_controller._save_field_snapshot recebe batches).
    assert "snapshots: snaps" in src or "snapshots:snaps" in src, (
        "batch deve carregar a chave 'snapshots' com o array retornado, "
        "compativel com recorder_controller._save_field_snapshot"
    )


def test_no_naked_discard_pattern():
    """Garante que a forma antiga (chamar _tf_snapshotFields e descartar
    silenciosamente) nao reapareca em uma refatoracao futura."""
    src = OVERLAY.read_text(encoding="utf-8")
    bad = "setInterval(function() { _tf_snapshotFields(); }, 2000)"
    assert bad not in src, (
        "Padrao bug detectado: setInterval descartando o retorno de "
        "_tf_snapshotFields. Use wrap que pushe em __tfFieldSnapshotQueue."
    )


def test_asserts_total_uses_script_steps_not_executed():
    """Denominador de assert_hit_rate vem do script compilado, nao dos
    asserts que conseguiram executar. Garante visibilidade de regressao
    quando stop-on-failure aborta antes dos asserts.
    """
    from unittest.mock import MagicMock
    from testforge.runner.incremental_runner import IncrementalRunner
    from testforge.runner.step_result import IncrementalStepResult

    r = IncrementalRunner.__new__(IncrementalRunner)
    # 3 asserts no script, mas execucao parou antes deles
    def mock_step(action):
        s = MagicMock()
        s.action = action
        return s
    r.steps = [
        mock_step("click"),
        mock_step("fill"),
        mock_step("assert"),
        mock_step("assert"),
        mock_step("assert"),
    ]
    r.step_results = [
        IncrementalStepResult(step_num=1, action="click", status="passed"),
        IncrementalStepResult(step_num=2, action="fill", status="healing_rejected"),
    ]
    r.metrics = None
    totals = r._compute_totals()
    assert totals["asserts_total"] == 3, (
        "denominador deve ser asserts no script (3), nao asserts executados (0)"
    )
    assert totals["asserts_hit"] == 0
