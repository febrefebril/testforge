"""Teste de regressão — Bug 3: eventos click/submit devem incrementar contador de passos no overlay."""
from pathlib import Path


OVERLAY = (Path(__file__).parent.parent / "src/testforge/recorder/overlay_inject.js").read_text(encoding="utf-8")


def test_overlay_js_increments_step_count_on_click():
    """overlay_inject.js deve conter incremento do contador de passos após _pushEvent('click', el)."""
    click_pos = OVERLAY.find("_pushEvent('click', el)")
    assert click_pos != -1, "_pushEvent click não encontrado no overlay"
    step_count_pos = OVERLAY.find("__tfStepCount", click_pos)
    next_listener = OVERLAY.find("window.addEventListener", click_pos + 1)
    assert step_count_pos != -1, "Incremento de __tfStepCount ausente após _pushEvent('click', el)"
    assert step_count_pos < next_listener, "Incremento de __tfStepCount deve estar dentro do listener de clique"


def test_overlay_js_increments_step_count_on_submit():
    """overlay_inject.js também deve incrementar contador de passos após _pushEvent('submit', el)."""
    submit_pos = OVERLAY.find("_pushEvent('submit', el)")
    assert submit_pos != -1, "_pushEvent submit não encontrado"
    step_count_pos = OVERLAY.find("__tfStepCount", submit_pos)
    fill_section = OVERLAY.find("// ---- Fill capture", submit_pos)
    assert step_count_pos != -1, "Incremento de __tfStepCount ausente após _pushEvent('submit', el)"
    assert step_count_pos < fill_section, "Incremento de __tfStepCount deve aparecer antes da seção fill"
