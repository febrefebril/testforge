"""Hotfix 22: Material datepicker picker-echo fill deve preservar cliques.

Regressao (test-pos-hotfix22, SIOPI): quando o usuario seleciona uma data via
cliques no calendario Material, o Angular Material escreve o valor de volta no
input vinculado, disparando um `input` event que o gravador captura como
`fill`. A logica pre-hotfix-22 no `_dedup_datepicker_sequences` via o fill,
tratava-o como "usuario digitou a data diretamente" e suprimia todos os
cliques de navegacao. Em runtime, o resolver tentava preencher
`input[placeholder="DD/MM/AAAA"]` mas o input Material rejeita (mask +
validators + readonly-ish), gerando `healing_rejected`. Resultado: nenhuma
data selecionada → botao Calcular disabled → fluxo end-to-end quebrado.

Hotfix 22: quando a sequencia de calendario termina com clique em celula de
dia AND o `fill` target parece um input Material datepicker (placeholder
casa DD/MM/AAAA, id `mat-input-*`, ou `matDatepicker`/`mat-datepicker-input`
em seletor), o fill e classificado como picker-echo → suprimimos o fill,
mantemos os cliques. Cliques SAO a intencao canonica.
"""
from __future__ import annotations

from testforge.handlers.angular_material import AngularMaterialHandler
from testforge.semantic.model import (
    SemanticAction, SemanticTarget, LocatorCandidate,
)


def _make_step(
    action,
    selector,
    value="",
    overlay=False,
    text="",
    placeholder=None,
    element_id="",
    tag="input",
):
    target = SemanticTarget(
        candidates=[LocatorCandidate(strategy="css", selector=selector, score=1.0)],
        text=text,
        placeholder=placeholder,
        element_id=element_id,
        tag=tag,
    )
    step = SemanticAction(action=action, target=target, value=value)
    if overlay:
        step.context["overlay_step"] = True
    return step


def _siopi_sequence(fill_placeholder="DD/MM/AAAA", fill_element_id=""):
    """SIOPI datepicker sequence: toggle + period + prev*2 + year + month + day + fill echo."""
    return [
        _make_step("click", "span.mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-period-button",
                   overlay=True, text="JUL 2026"),
        _make_step("click", "button.mat-calendar-previous-button span",
                   overlay=True),
        _make_step("click", "button.mat-calendar-previous-button span",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="1968"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="JAN"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="1"),
        _make_step("fill", "input[placeholder=\"DD/MM/AAAA\"]",
                   value="01/01/1968",
                   placeholder=fill_placeholder,
                   element_id=fill_element_id,
                   tag="input"),
    ]


def test_picker_echo_fill_via_placeholder_keeps_clicks():
    """SIOPI-shaped: placeholder DD/MM/AAAA on fill target → picker echo.
    Direct-fill nao funciona (Material datepicker rejeita fill direto quando
    bind ativo). Volta ao click-based path.
    """
    handler = AngularMaterialHandler()
    steps = _siopi_sequence(fill_placeholder="DD/MM/AAAA")
    handler._dedup_datepicker_sequences(steps)

    for i, s in enumerate(steps[:7]):
        assert s.skip_reason != "datepicker_dedup", (
            f"step {i} calendar click was wrongly suppressed: {s.skip_reason}"
        )
    assert steps[7].skip_reason == "datepicker_picker_echo_fill", (
        f"echo fill should be marked as picker echo, got: {steps[7].skip_reason!r}"
    )


def test_picker_echo_fill_via_mat_input_id_keeps_clicks():
    """Material datepicker detection also via id starting with mat-input-."""
    handler = AngularMaterialHandler()
    steps = _siopi_sequence(fill_placeholder=None, fill_element_id="mat-input-0")
    handler._dedup_datepicker_sequences(steps)

    for i, s in enumerate(steps[:7]):
        assert s.skip_reason != "datepicker_dedup", (
            f"step {i} was wrongly suppressed: {s.skip_reason}"
        )
    assert steps[7].skip_reason == "datepicker_picker_echo_fill"


def test_fill_without_picker_signal_still_suppresses_clicks():
    """Legacy path: plain input[name='date'] fill — no Material picker signal.
    In this case the fill IS the canonical intent (user typed) so clicks are
    suppressed. This locks in the pre-hotfix-22 behavior for non-Material
    date inputs."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="15"),
        _make_step("fill", "input[name='date']",
                   value="15/03/2026",
                   placeholder=None,
                   element_id="",
                   tag="input"),
    ]
    handler._dedup_datepicker_sequences(steps)
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    assert steps[2].skip_reason == "datepicker_dedup"
    assert steps[3].skip_reason == "", (
        f"non-Material fill should stay canonical, got: {steps[3].skip_reason!r}"
    )


def test_picker_echo_detection_ignored_without_day_cell():
    """If sequence didn't end with a day-cell click, don't apply echo path —
    the fill really is the terminal action (rare)."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),  # NOT a day cell
        _make_step("fill", "input[placeholder=\"DD/MM/AAAA\"]",
                   value="15/03/2026",
                   placeholder="DD/MM/AAAA",
                   tag="input"),
    ]
    handler._dedup_datepicker_sequences(steps)
    # Original fill-followup path applies: clicks suppressed, fill kept
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    assert steps[2].skip_reason == "", (
        "no day-cell click → fill is canonical (not picker echo)"
    )
